"""Unified image I/O: decode jpg/jpeg/jp2/jxl/tif/png -> float32 [0,1] RGB,
preserve ICC/EXIF on encode, with macOS `sips` / `opj_decompress` fallbacks.
"""
from __future__ import annotations

import dataclasses
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms

Image.MAX_IMAGE_PIXELS = None  # Silbersalz scans are ~150 MP; that's expected

try:  # registers JXL support in Pillow when the wheel is present
    import pillow_jxl  # noqa: F401

    HAVE_JXL_PLUGIN = True
except ImportError:  # pragma: no cover - depends on environment
    HAVE_JXL_PLUGIN = False

SUPPORTED_EXTS = {".jpg", ".jpeg", ".jp2", ".j2k", ".jxl", ".tif", ".tiff", ".png"}


@dataclasses.dataclass
class ImageData:
    rgb: np.ndarray  # float32, (H, W, 3), [0,1], display code values
    icc_bytes: bytes | None
    exif_bytes: bytes | None
    bit_depth: int
    source: Path

    @property
    def size(self) -> tuple[int, int]:
        return self.rgb.shape[1], self.rgb.shape[0]


def is_appledouble(path: Path) -> bool:
    return path.name.startswith("._")


def list_images(folder: str | Path, recursive: bool = False) -> list[Path]:
    folder = Path(folder)
    it = folder.rglob("*") if recursive else folder.iterdir()
    files = [
        p
        for p in it
        if p.is_file()
        and p.suffix.lower() in SUPPORTED_EXTS
        and not is_appledouble(p)
    ]
    return sorted(files)


def _pil_to_float(img: Image.Image) -> tuple[np.ndarray, int]:
    """PIL image -> float32 [0,1] RGB + source bit depth."""
    if img.mode in ("I;16", "I;16B", "I;16L"):
        arr = np.asarray(img, dtype=np.uint16)
        return (arr.astype(np.float32) / 65535.0)[..., None].repeat(3, axis=-1), 16
    if img.mode == "RGB":
        return np.asarray(img, dtype=np.uint8).astype(np.float32) / 255.0, 8
    if img.mode in ("RGBA", "P", "L", "CMYK"):
        return (
            np.asarray(img.convert("RGB"), dtype=np.uint8).astype(np.float32) / 255.0,
            8,
        )
    # 16-bit multichannel (e.g. from JP2/JXL/TIFF decoders)
    arr = np.asarray(img)
    if arr.dtype == np.uint16:
        if arr.ndim == 2:
            arr = arr[..., None].repeat(3, axis=-1)
        return arr[..., :3].astype(np.float32) / 65535.0, 16
    if arr.dtype == np.uint8:
        if arr.ndim == 2:
            arr = arr[..., None].repeat(3, axis=-1)
        return arr[..., :3].astype(np.float32) / 255.0, 8
    raise ValueError(f"unsupported PIL mode/dtype: {img.mode}/{arr.dtype}")


def _decode_via_sips(path: Path, max_px: int | None) -> tuple[np.ndarray, int]:
    """Fallback decoder using macOS sips -> 16-bit TIFF -> tifffile."""
    import tifffile

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / (path.stem + ".tif")
        cmd = ["sips", "-s", "format", "tiff", str(path), "--out", str(out)]
        if max_px:
            cmd = [
                "sips",
                "-s",
                "format",
                "tiff",
                "--resampleHeightWidthMax",
                str(max_px),
                str(path),
                "--out",
                str(out),
            ]
        subprocess.run(cmd, check=True, capture_output=True)
        arr = tifffile.imread(out)
    if arr.dtype == np.uint16:
        return arr[..., :3].astype(np.float32) / 65535.0, 16
    return arr[..., :3].astype(np.float32) / 255.0, 8


def _decode_via_opj(path: Path, reduce: int) -> tuple[np.ndarray, int]:
    """Fallback JP2 decoder: opj_decompress -r N (decode at 1/2^N)."""
    import tifffile

    opj = shutil.which("opj_decompress") or "/opt/homebrew/bin/opj_decompress"
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / (path.stem + ".tif")
        subprocess.run(
            [opj, "-i", str(path), "-o", str(out), "-r", str(reduce)],
            check=True,
            capture_output=True,
        )
        arr = tifffile.imread(out)
    if arr.dtype == np.uint16:
        return arr[..., :3].astype(np.float32) / 65535.0, 16
    return arr[..., :3].astype(np.float32) / 255.0, 8


def read_image(path: str | Path, max_px: int | None = None) -> ImageData:
    """Decode any supported format to float32 [0,1] RGB code values.

    max_px: optional cap on the long edge; decoders downsample when they can
    (JPEG draft mode, JP2 reduced-resolution decode), else we resize after.
    """
    path = Path(path)
    ext = path.suffix.lower()
    icc = exif = None
    rgb = None
    depth = 8

    try:
        img = Image.open(path)
        icc = img.info.get("icc_profile")
        exif = img.info.get("exif")
        if max_px and ext in (".jpg", ".jpeg"):
            img.draft("RGB", (max_px, max_px))
        if ext in (".jp2", ".j2k") and max_px:
            full = max(img.size)
            reduce = 0
            while full / (2 ** (reduce + 1)) >= max_px:
                reduce += 1
            if reduce:
                try:
                    img.reduce_factor = 2 ** reduce  # openjpeg plugin hint
                except Exception:
                    pass
        rgb, depth = _pil_to_float(img)
    except Exception:
        if ext in (".jp2", ".j2k"):
            reduce = 0
            if max_px:
                reduce = 3
            rgb, depth = _decode_via_opj(path, reduce)
        else:
            rgb, depth = _decode_via_sips(path, max_px)

    if max_px and max(rgb.shape[:2]) > max_px:
        import cv2

        scale = max_px / max(rgb.shape[:2])
        rgb = cv2.resize(
            rgb,
            (
                max(1, round(rgb.shape[1] * scale)),
                max(1, round(rgb.shape[0] * scale)),
            ),
            interpolation=cv2.INTER_AREA,
        )

    return ImageData(
        rgb=np.ascontiguousarray(rgb[..., :3], dtype=np.float32),
        icc_bytes=icc,
        exif_bytes=exif,
        bit_depth=depth,
        source=path,
    )


def icc_description(icc_bytes: bytes | None) -> str:
    if not icc_bytes:
        return "untagged"
    try:
        import io

        prof = ImageCms.ImageCmsProfile(io.BytesIO(icc_bytes))
        return ImageCms.getProfileDescription(prof).strip()
    except Exception:
        return "unreadable-profile"


def is_srgb_tagged(icc_bytes: bytes | None) -> bool:
    return "srgb" in icc_description(icc_bytes).lower()


def triangular_dither(shape: tuple, rng: np.random.Generator | None = None) -> np.ndarray:
    """Triangular-PDF dither in units of one 8-bit LSB (float, /255)."""
    rng = rng or np.random.default_rng(0)
    return (rng.random(shape) - rng.random(shape)) / 255.0


def write_jpeg(
    path: str | Path,
    rgb: np.ndarray,
    icc_bytes: bytes | None = None,
    exif_bytes: bytes | None = None,
    quality: int = 95,
    dither: bool = True,
) -> None:
    out = np.clip(rgb, 0.0, 1.0)
    if dither:
        out = out + triangular_dither(out.shape)
    arr = np.clip(np.rint(out * 255.0), 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, mode="RGB")
    kwargs: dict = {"quality": quality, "subsampling": 0}
    if icc_bytes:
        kwargs["icc_profile"] = icc_bytes
    if exif_bytes:
        kwargs["exif"] = exif_bytes
    img.save(str(path), "JPEG", **kwargs)
