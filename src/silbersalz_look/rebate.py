"""Film rebate (border + sprocket) detection: find the exposed image area.

Silbersalz scans include the full film strip: dark rebate bands top/bottom
(with sprocket holes) and frame edges left/right. The image area is a bright
interior rectangle; we find it from luminance profiles on a small preview.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from . import imgio


def _band_bounds(profile: np.ndarray, thresh: float) -> tuple[int, int]:
    """First/last index where the profile exceeds thresh (interior run)."""
    above = np.where(profile > thresh)[0]
    if len(above) == 0:
        return 0, len(profile)
    return int(above[0]), int(above[-1]) + 1

def detect_image_area(rgb: np.ndarray, margin_frac: float = 0.01) -> tuple[int, int, int, int]:
    """Return (x, y, w, h) of the image area as fractions applied to this image.

    Works on a decoded preview (float [0,1]). Robust to both flat scans
    (bright, milky interior) and graded scans (darker interior but still far
    brighter than the near-black rebate).
    """
    luma = rgb.mean(axis=-1)
    col = np.median(luma, axis=0)  # profile across x
    row = np.median(luma, axis=1)  # profile across y

    def thresh_for(profile: np.ndarray) -> float:
        lo, hi = np.percentile(profile, [5, 95])
        return lo + 0.25 * (hi - lo)

    x0, x1 = _band_bounds(col, thresh_for(col))
    y0, y1 = _band_bounds(row, thresh_for(row))

    # shave a safety margin off each side (frame edges bleed light)
    mx = int(round((x1 - x0) * margin_frac))
    my = int(round((y1 - y0) * margin_frac))
    x0, x1 = x0 + mx, x1 - mx
    y0, y1 = y0 + my, y1 - my
    return x0, y0, max(1, x1 - x0), max(1, y1 - y0)


def area_as_fractions(
    area: tuple[int, int, int, int], shape: tuple[int, int]
) -> tuple[float, float, float, float]:
    h, w = shape[:2]
    x, y, aw, ah = area
    return x / w, y / h, aw / w, ah / h


def fractions_to_area(
    frac: tuple[float, float, float, float], shape: tuple[int, int]
) -> tuple[int, int, int, int]:
    h, w = shape[:2]
    fx, fy, fw, fh = frac
    return (
        int(round(fx * w)),
        int(round(fy * h)),
        int(round(fw * w)),
        int(round(fh * h)),
    )


def roll_area_fractions(
    files: list[Path],
    cache_dir: Path | None = None,
    sample_n: int = 5,
    preview_px: int = 800,
) -> tuple[float, float, float, float]:
    """Median image-area rectangle (as fractions) across sample frames of a roll.

    Cached by a hash of the file list so repeated runs are free.
    """
    key = hashlib.sha1("|".join(str(f) for f in files).encode()).hexdigest()[:16]
    cache_file = (cache_dir / f"rebate_{key}.json") if cache_dir else None
    if cache_file and cache_file.exists():
        return tuple(json.loads(cache_file.read_text()))

    # spread candidates across the roll; skip blank/dark frames (no bright
    # interior means no geometry signal — rolls often start with unexposed
    # frames and the lab's info card)
    candidates = files[:: max(1, len(files) // (sample_n * 4))][: sample_n * 4]
    fracs = []
    for f in candidates:
        img = imgio.read_image(f, max_px=preview_px)
        if float(np.percentile(img.rgb.mean(axis=-1), 95)) < 0.3:
            continue
        area = detect_image_area(img.rgb)
        fracs.append(area_as_fractions(area, img.rgb.shape))
        if len(fracs) >= sample_n:
            break
    if not fracs:
        fracs = [(0.02, 0.02, 0.96, 0.96)]  # conservative fallback
    med = tuple(float(np.median([fr[i] for fr in fracs])) for i in range(4))
    if cache_file:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(med))
    return med


def crop_to_area(rgb: np.ndarray, frac: tuple[float, float, float, float]) -> np.ndarray:
    x, y, w, h = fractions_to_area(frac, rgb.shape)
    return rgb[y : y + h, x : x + w]


def looks_like_info_card(rgb: np.ndarray) -> bool:
    """Detect the lab's orange info-card leader frame (frame 001 of a roll).

    The card is a near-uniform strong-orange field: orange hue dominant, low
    texture, saturated.
    """
    luma = rgb.mean(axis=-1)
    bright = luma > 0.15
    if float(bright.mean()) < 0.15:
        return False
    px = rgb[bright]
    r, g, b = px[:, 0], px[:, 1], px[:, 2]
    orange = (r > g) & (g > b)
    sat = px.max(axis=-1) - px.min(axis=-1)
    return (
        float(orange.mean()) > 0.8
        and float(np.median(sat)) > 0.12
        and float(luma[bright].std()) < 0.15
    )


def looks_blank(rgb: np.ndarray) -> bool:
    """Unexposed/blank frame: near-black with no content."""
    luma = rgb.mean(axis=-1)
    return float(np.percentile(luma, 95)) < 0.15
