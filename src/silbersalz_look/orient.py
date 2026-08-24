"""Auto-orientation of scans (0/90/180/270) from image content.

Cues per candidate rotation, fused:
  probe  - logistic-regression probe on spatially pooled (2x2) ResNet-50
           features, self-supervised on the archive (every frame x 4
           rotations); keeps the top/bottom layout that pooled features lose
  faces  - YuNet face detector (models/face_detection_yunet_2023mar.onnx):
           upright faces only appear in the correct rotation
Rotation k means np.rot90(img, k) makes the image upright. Each decision
carries a confidence so uncertain frames can be reviewed on a sheet.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = Path(__file__).resolve().parent / "models"
PROBE_PATH = MODEL_DIR / "rotation_probe.npz"   # plain numpy weights: no scikit-learn at runtime
YUNET_PATH = MODEL_DIR / "face_detection_yunet_2023mar.onnx"


class OrientationModel:
    def __init__(self, use_faces: bool = True):
        import torch, torchvision
        from torchvision import transforms

        torch.set_num_threads(4)
        net = torchvision.models.resnet50(weights=torchvision.models.ResNet50_Weights.IMAGENET1K_V2)
        net.eval()
        self.body = torch.nn.Sequential(*list(net.children())[:-2])
        self.pre = transforms.Compose([
            transforms.Resize((224, 224)), transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
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

    # --- features -----------------------------------------------------------
    def spatial_features(self, views: list[np.ndarray]) -> np.ndarray:
        import torch
        from PIL import Image

        batch = torch.stack([self.pre(Image.fromarray((np.clip(v, 0, 1) * 255).astype(np.uint8))) for v in views])
        with torch.no_grad():
            fm = self.body(batch)
            pooled = torch.nn.functional.adaptive_avg_pool2d(fm, 2).flatten(1).numpy().astype(np.float32)
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
