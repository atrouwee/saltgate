"""Auto-orientation of scans (0/90/180/270) from image content.

Cues per candidate rotation, fused:
  probe  - logistic-regression probe on spatially pooled (2x2) ResNet-50
           features, self-supervised on the archive (every frame x 4
           rotations); keeps the top/bottom layout that pooled features lose
  faces  - YuNet face detector (models/face_detection_yunet_2023mar.onnx):
           upright faces only appear in the correct rotation
Rotation k means np.rot90(img, k) makes the image upright. Each decision
carries a confidence so uncertain frames can be reviewed on a sheet.

The backbone runs as ONNX through OpenCV's dnn module -- the same way the face
detector already did. It used to run under torch, which cost 529 MB installed
plus a 98 MB weight download plus a full restart of the walkthrough, all to
evaluate a frozen conv stack. The ONNX carries the identical weights, so the
probe in models/rotation_probe.npz stays valid: on 80 archive frames the two
backends chose the same rotation 80/80 times.

torch is still honoured if it happens to be installed and the ONNX is missing,
so nobody who has rotation working today loses it. Nothing installs it.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = Path(__file__).resolve().parent / "models"
PROBE_PATH = MODEL_DIR / "rotation_probe.npz"   # plain numpy weights: no scikit-learn at runtime
YUNET_PATH = MODEL_DIR / "face_detection_yunet_2023mar.onnx"

# The backbone is 47 MB, so it is fetched once rather than carried in the repo,
# where a binary of that size would sit in the history forever. It has its own
# release tag rather than a code version: the weights do not change when the
# code does, and pinning to a code tag would mean re-uploading 47 MB per patch.
# Third-party weights: torchvision's ResNet-50 IMAGENET1K_V2, BSD-3-Clause,
# trained on ImageNet-1K. Attribution and provenance: THIRD-PARTY-NOTICES.md.
BACKBONE = {
    "file": "orient-resnet50-body-fp16.onnx",
    "url": "https://github.com/atrouwee/saltgate/releases/download/orient-model-v1/orient-resnet50-body-fp16.onnx",
    "sha256": "818e29fe77ea228d64fcf04f7798c98f4838a7a66385209c70785472321b2a49",
    "bytes": 46990034,
}
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], np.float32)


def model_cache_dir() -> Path:
    base = (Path.home() / "Library/Application Support/saltgate" if sys.platform == "darwin"
            else Path.home() / ".saltgate")
    return base / "models"


def backbone_path() -> Path:
    return model_cache_dir() / BACKBONE["file"]


def have_backbone() -> bool:
    return backbone_path().exists()


def ensure_backbone(progress=None) -> bool:
    """Fetch the backbone into the model cache. Returns True if it downloaded.

    `progress(done_bytes, total_bytes)` is called as bytes arrive. The file is
    written to a .part and renamed only after the digest matches, so an
    interrupted or tampered download can never be loaded.
    """
    import urllib.request

    dst = backbone_path()
    if dst.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    part = dst.with_suffix(dst.suffix + ".part")
    digest = hashlib.sha256()
    with urllib.request.urlopen(BACKBONE["url"], timeout=30) as r, open(part, "wb") as f:
        total = int(r.headers.get("Content-Length") or BACKBONE["bytes"])
        done = 0
        if progress:
            progress(0, total)
        while chunk := r.read(1 << 18):
            f.write(chunk)
            digest.update(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    if digest.hexdigest() != BACKBONE["sha256"]:
        part.unlink(missing_ok=True)
        raise RuntimeError("the downloaded orientation model does not match its checksum")
    part.replace(dst)
    return True


def _adaptive_avg_pool_2x2(fm: np.ndarray) -> np.ndarray:
    """torch.nn.functional.adaptive_avg_pool2d(fm, 2).flatten(1), in numpy.

    The bins overlap: 7 -> 2 gives rows [0,4) and [3,7), not a half split. Get
    that wrong and the features are plausible but meaningless to the probe.
    """
    n, c, h, w = fm.shape

    def bins(size: int):
        return [(int(np.floor(i * size / 2)), int(np.ceil((i + 1) * size / 2))) for i in range(2)]

    out = np.empty((n, c, 2, 2), np.float32)
    for i, (r0, r1) in enumerate(bins(h)):
        for j, (c0, c1) in enumerate(bins(w)):
            out[:, :, i, j] = fm[:, :, r0:r1, c0:c1].mean(axis=(2, 3))
    return out.reshape(n, -1)


class OrientationModel:
    def __init__(self, use_faces: bool = True):
        self.backend = self._load_backbone()
        self.probe = None
        if PROBE_PATH.exists():
            d = np.load(PROBE_PATH)
            self.probe = (d["W"], d["b"], d["classes"])
        self.det = None
        if use_faces and YUNET_PATH.exists() and hasattr(cv2, "FaceDetectorYN"):
            try:  # OpenCV prints internal '[ WARN ... ]' lines for the DNN back-end; they mean nothing to users
                cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
            except Exception:
                pass
            self.det = cv2.FaceDetectorYN.create(str(YUNET_PATH), "", (320, 320), score_threshold=0.6)

    # --- backbone -----------------------------------------------------------
    def _load_backbone(self) -> str:
        if have_backbone():
            self.net = cv2.dnn.readNetFromONNX(str(backbone_path()))
            return "onnx"
        try:                     # only if someone already has it; nothing installs torch
            import torch, torchvision
            torch.set_num_threads(4)
            net = torchvision.models.resnet50(
                weights=torchvision.models.ResNet50_Weights.IMAGENET1K_V2).eval()
            self.body = torch.nn.Sequential(*list(net.children())[:-2])
            return "torch"
        except Exception as e:
            raise RuntimeError(
                "the orientation model is not downloaded yet "
                f"({backbone_path()})"
            ) from e

    # --- features -----------------------------------------------------------
    def _preprocess(self, rgb: np.ndarray) -> np.ndarray:
        from PIL import Image

        im = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).resize((224, 224), Image.BILINEAR)
        a = (np.asarray(im, np.float32) / 255.0 - IMAGENET_MEAN) / IMAGENET_STD
        return np.ascontiguousarray(np.transpose(a, (2, 0, 1))[None])

    def spatial_features(self, views: list[np.ndarray]) -> np.ndarray:
        """Pooled, L2-normalised backbone features -- one row per view.

        Run one view at a time on purpose: cv2.dnn returns wrong values for this
        graph at batch > 1 and is exact at batch 1.
        """
        fms = []
        for v in views:
            blob = self._preprocess(v)
            if self.backend == "onnx":
                self.net.setInput(blob)
                fms.append(self.net.forward())
            else:
                import torch
                with torch.no_grad():
                    fms.append(self.body(torch.from_numpy(blob)).numpy())
        pooled = _adaptive_avg_pool_2x2(np.concatenate(fms, axis=0))
        return pooled / (np.linalg.norm(pooled, axis=1, keepdims=True) + 1e-6)

    def face_score(self, rgb: np.ndarray) -> float:
        if self.det is None:
            return 0.0
        img = cv2.cvtColor((np.clip(rgb, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
        h, w = img.shape[:2]
        s = 640 / max(h, w)
        img = cv2.resize(img, (max(32, round(w * s)), max(32, round(h * s))))
        self.det.setInputSize((img.shape[1], img.shape[0]))
        _, faces = self.det.detect(img)
        if faces is None:
            return 0.0
        return float(sum(f[14] * (f[2] * f[3]) ** 0.5 for f in faces))

    # --- decision -----------------------------------------------------------
    def predict(self, rgb: np.ndarray, w_face: float = 2.0) -> dict:
        """rgb: image-area preview (any orientation). Returns decision dict."""
        views = [np.rot90(rgb, k) for k in range(4)]
        p_probe = np.full(4, 0.25)
        if self.probe is not None:
            # probe was trained on views labeled "rotation needed to fix"; run it on the
            # unrotated frame: class c = rotate by c to make upright (softmax over a linear probe)
            W, b, classes = self.probe
            z = self.spatial_features([rgb])[0] @ W.T + b
            z = z - z.max(); pr = np.exp(z) / np.exp(z).sum()
            p_probe = np.zeros(4); p_probe[classes] = pr
        faces = np.array([self.face_score(v) for v in views])
        face_term = np.zeros(4)
        if faces.max() > 0:
            face_term = faces / faces.max()
        score = np.log(p_probe + 1e-6) + w_face * face_term
        k = int(np.argmax(score))
        srt = np.sort(score)[::-1]
        margin = float(srt[0] - srt[1])
        conf = float(1.0 - np.exp(-margin))  # 0..1
        return {
            "k": k, "confidence": round(conf, 3),
            "probe": [round(float(v), 3) for v in p_probe],
            "faces": [round(float(v), 3) for v in faces],
        }


# train_probe() lives in scripts/train_orient_probe.py (research-only: it needs
# scikit-learn). Runtime inference below is numpy + OpenCV only, by design.


def apply_rotation(arr: np.ndarray, k: int) -> np.ndarray:
    return np.ascontiguousarray(np.rot90(arr, k)) if k % 4 else arr
