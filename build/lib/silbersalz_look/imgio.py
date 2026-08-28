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

try:  # optional: registers JXL support in Pillow (only used for metadata); decoding uses imagecodecs
    import pillow_jxl  # noqa: F401

    HAVE_JXL_PLUGIN = True
except ImportError:  # pragma: no cover - depends on environment
    HAVE_JXL_PLUGIN = False

SUPPORTED_EXTS = {".jpg", ".jpeg", ".jp2", ".j2k", ".jxl", ".tif", ".tiff", ".png"}
# What the tool will grade. Narrower than SUPPORTED_EXTS (no .png: the lab never
# ships one) and defined ONCE -- the wizard and apply.grade_folder each used to
# carry their own .jpg-only copy, so accepting 16-bit input in one of them left
# the other raising "no JPEGs found".
GRADEABLE_EXTS = {".jpg", ".jpeg", ".jxl", ".jp2", ".j2k", ".tif", ".tiff"}


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


def _decode_jxl_16(path: Path) -> tuple[np.ndarray, int, bytes | None]:
    """True 16-bit JXL decode via imagecodecs (Pillow's plugin returns 8-bit)."""
    import imagecodecs

    arr = imagecodecs.jpegxl_decode(path.read_bytes())
    icc = None
    try:
        icc = Image.open(path).info.get("icc_profile")
    except Exception:
        pass
    if arr.dtype == np.uint16:
        return arr[..., :3].astype(np.float32) / 65535.0, 16, icc
    return arr[..., :3].astype(np.float32) / 255.0, 8, icc


def read_image(path: str | Path, max_px: int | None = None) -> ImageData:
    """Decode any supported format to float32 [0,1] RGB code values.

    max_px: optional cap on the long edge; decoders downsample when they can
    (JPEG draft mode, JP2 reduced-resolution decode), else we resize after.
    JXL is decoded at true bit depth via imagecodecs (Pillow's plugin is 8-bit).
    """
    path = Path(path)
    ext = path.suffix.lower()
    icc = exif = None
    rgb = None
    depth = 8

    if ext == ".jxl":
        try:
            rgb, depth, icc = _decode_jxl_16(path)
        except Exception:
            rgb = None
    if ext in (".tif", ".tiff"):
        # Pillow has no 16-bit RGB mode, so it silently hands back 8 bits and the
        # depth we just wrote is lost. tifffile reads the real samples.
        try:
            import tifffile
            with tifffile.TiffFile(str(path)) as tf:
                arr = tf.asarray()
                page = tf.pages[0]
                tag = page.tags.get(34675)
                icc = bytes(tag.value) if tag is not None else None
            if arr.ndim == 2:
                arr = arr[..., None].repeat(3, axis=-1)
            arr = arr[..., :3]
            if arr.dtype == np.uint16:
                rgb, depth = arr.astype(np.float32) / 65535.0, 16
            elif arr.dtype == np.uint8:
                rgb, depth = arr.astype(np.float32) / 255.0, 8
            else:
                rgb, depth = np.clip(arr.astype(np.float32), 0, 1), 16
        except Exception:
            rgb = None
    if rgb is None:
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
                    # Pillow's JPEG 2000 plugin decodes at 1/2^reduce when `reduce`
                    # (number of resolution levels to discard) is set before load().
                    img.reduce = reduce
            rgb, depth = _pil_to_float(img)
        except Exception:
            if ext in (".jp2", ".j2k"):
                rgb, depth = _decode_via_opj(path, 3 if max_px else 0)
            else:
                rgb, depth = _decode_via_sips(path, max_px)

    if max_px and max(rgb.shape[:2]) > max_px:
        import cv2

        scale = max_px / max(rgb.shape[:2])
        rgb = cv2.resize(
            rgb,
            (max(1, round(rgb.shape[1] * scale)), max(1, round(rgb.shape[0] * scale))),
            interpolation=cv2.INTER_AREA,
        )

    return ImageData(
        rgb=np.ascontiguousarray(rgb[..., :3], dtype=np.float32),
        icc_bytes=icc,
        exif_bytes=exif,
        bit_depth=depth,
        source=path,
    )


def original_size(path: str | Path) -> tuple[int, int]:
    """(width, height) from the file header, without decoding pixels."""
    path = Path(path)
    if path.suffix.lower() == ".jxl":
        try:
            import imagecodecs
            arr = imagecodecs.jpegxl_decode(path.read_bytes())  # no header-only API; decode is the honest path
            return arr.shape[1], arr.shape[0]
        except Exception:
            pass
    with Image.open(path) as im:
        return im.size


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


def write_image(path, rgb: np.ndarray, bit_depth: int = 8, icc_bytes: bytes | None = None,
                exif_bytes: bytes | None = None, quality: int = 95) -> None:
    """Write float32 [0,1] RGB out at 8 or 16 bits.

    16-bit goes to TIFF, because it is the one lossless 16-bit container every
    editor reads. The lab's own 8-bit 4:2:0 delivery costs 2.2 dE against a
    16-bit original -- measured -- so re-imposing that on our own output would
    add more error than the colour transform still has in it.
    """
    path = Path(path)
    a = np.clip(rgb, 0.0, 1.0)
    if bit_depth >= 16:
        import tifffile
        extratags = [(34675, "B", len(icc_bytes), icc_bytes, True)] if icc_bytes else []
        tifffile.imwrite(str(path), (a * 65535.0 + 0.5).astype(np.uint16),
                         photometric="rgb", compression="zlib", extratags=extratags)
        return
    im = Image.fromarray((a * 255.0 + 0.5).astype(np.uint8), mode="RGB")
    kw = {"quality": quality, "subsampling": 0}
    if icc_bytes:
        kw["icc_profile"] = icc_bytes
    if exif_bytes:
        kw["exif"] = exif_bytes
    im.save(str(path), "JPEG", **kw)


def output_suffix(bit_depth: int) -> str:
    return ".tif" if bit_depth >= 16 else ".jpg"
