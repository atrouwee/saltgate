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


def _band_bounds(profile: np.ndarray) -> tuple[int, int]:
    """Interior run where the profile departs from the border level.

    The rebate is near-black in graded scans but near-WHITE in flat scans, so
    we look for deviation from the outermost rows/cols rather than for a
    brightness threshold: score = |profile - border_median|."""
    n = len(profile)
    edge = max(2, int(0.03 * n))
    border = float(np.median(np.concatenate([profile[:edge], profile[-edge:]])))
    score = np.abs(profile - border)
    thresh = 0.25 * float(np.percentile(score, 95))
    if thresh < 0.02:  # no rebate visible at all
        return 0, n
    above = np.where(score > thresh)[0]
    if len(above) == 0:
        return 0, n
    return int(above[0]), int(above[-1]) + 1


def detect_image_area(rgb: np.ndarray, margin_frac: float = 0.01) -> tuple[int, int, int, int]:
    """Return (x, y, w, h) of the image area on this preview (float [0,1]).

    Works for graded scans (dark rebate) and flat scans (bright rebate)."""
    luma = rgb.mean(axis=-1)
    col = np.median(luma, axis=0)  # profile across x
    row = np.median(luma, axis=1)  # profile across y
    x0, x1 = _band_bounds(col)
    y0, y1 = _band_bounds(row)

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


def detect_image_area_fractions(rgb: np.ndarray) -> tuple[float, float, float, float] | None:
    """detect_image_area as fractions of the frame, or None if it misfires.

    Fractions travel between resolutions, so a box found on a preview can be
    applied to the full-resolution frame. A detection covering less than half
    the frame on either axis is a misfire (a large soft shadow can do this) and
    returns None so the caller can fall back rather than crop a third of the
    picture away.
    """
    h, w = rgb.shape[:2]
    x, y, bw, bh = detect_image_area(rgb)
    if bw < 0.5 * w or bh < 0.5 * h:
        return None
    return x / w, y / h, bw / w, bh / h


def dark_margins(rgb: np.ndarray) -> tuple[int, int, int, int]:
    """(top, bottom, left, right) thickness of the dark film border, in pixels.

    Walks each edge inward while the line's median stays far below the picture's
    own core, so it measures the unexposed rebate rather than a dark subject.
    """
    from . import color as _color

    L = _color.p3_codes_to_lab(np.clip(rgb, 0, 1).astype(np.float64))[..., 0]
    h, w = L.shape
    core = float(np.median(L[h // 3:2 * h // 3, w // 3:2 * w // 3]))
    thr = max(12.0, core * 0.35)

    def run(get, n):
        k = 0
        while k < n // 3 and float(np.median(get(k))) < thr:
            k += 1
        return k

    return (run(lambda i: L[i], h), run(lambda i: L[h - 1 - i], h),
            run(lambda i: L[:, i], w), run(lambda i: L[:, w - 1 - i], w))


def centering_shift(rgb: np.ndarray, limit_frac: float = 0.06) -> tuple[int, int]:
    """(dy, dx) to move a crop window so the dark border is even on both sides.

    detect_image_area's box sits slightly off the picture on one axis -- measured
    on roll 26.18_077, every frame carried ~2.4% of dark border on one side and
    none on the other (the left on portrait frames, the bottom on landscape:
    the same film edge, rotated). Shifting by half the imbalance evens it
    without changing the crop's size. Bounded, so a misread cannot slide the
    window off the picture.
    """
    t, b, l, r = dark_margins(rgb)
    h, w = rgb.shape[:2]
    dy = int(np.clip((t - b) // 2, -limit_frac * h, limit_frac * h))
    dx = int(np.clip((l - r) // 2, -limit_frac * w, limit_frac * w))
    return dy, dx


def crop_to_area(rgb: np.ndarray, frac: tuple[float, float, float, float]) -> np.ndarray:
    x, y, w, h = fractions_to_area(frac, rgb.shape)
    return rgb[y : y + h, x : x + w]


def looks_like_info_card(rgb: np.ndarray) -> bool:
    """Detect the lab's info-card leader frames (orange, green or red fields
    with printed order text): a near-uniform, saturated, single-hue field."""
    luma = rgb.mean(axis=-1)
    bright = luma > 0.15
    if float(bright.mean()) < 0.15:
        return False
    px = rgb[bright]
    mx, mn = px.max(axis=-1), px.min(axis=-1)
    sat = mx - mn
    if float(np.median(sat)) < 0.08 or float(luma[bright].std()) > 0.15:
        return False
    # hue concentration: >80% of saturated pixels within +/-30 deg of the median hue
    r, g, b = px[:, 0], px[:, 1], px[:, 2]
    h = np.degrees(np.arctan2(np.sqrt(3) * (g - b), 2 * r - g - b)) % 360.0
    hs = h[sat > 0.08]
    if len(hs) < 100:
        return False
    med = np.degrees(np.arctan2(np.sin(np.radians(hs)).mean(), np.cos(np.radians(hs)).mean())) % 360.0
    d = np.abs((hs - med + 180.0) % 360.0 - 180.0)
    return float((d < 30.0).mean()) > 0.8


def looks_white(rgb: np.ndarray) -> bool:
    """Blown/empty frame: almost entirely near-white."""
    luma = rgb.mean(axis=-1)
    return float((luma > 0.9).mean()) > 0.4


def looks_blank(rgb: np.ndarray) -> bool:
    """Unexposed/blank frame: near-black with no content, or near-white."""
    luma = rgb.mean(axis=-1)
    return float(np.percentile(luma, 95)) < 0.18 or looks_white(rgb)


def is_content_frame(rgb: np.ndarray) -> bool:
    return not (looks_blank(rgb) or looks_like_info_card(rgb))


def base_estimate(rgb: np.ndarray) -> np.ndarray | None:
    """Median P3 code of the film base, from the thin clear band between the
    picture area and the sprocket row. Measurement utility only: base density
    SHOULD fingerprint stock and push/pull, but the lab normalised each
    roll's scan, so in these deliverables it does not (within-stock roll
    medians span 10 L* / 8 b* -- as wide as between stocks; see FINDINGS).
    The working mismatch guard is stock_check.py. Returns None when no
    picture box is found or the band is degenerate."""
    box = detect_image_area_fractions(rgb)
    if box is None:
        return None
    bx, by, bw, bh = box
    h, w = rgb.shape[:2]
    y0, y1 = round(by * h), round((by + bh) * h)
    x0, x1 = round(bx * w), round((bx + bw) * w)
    band = max(2, round(0.012 * h))
    strips = []
    if y0 - band >= 0:
        strips.append(rgb[max(0, y0 - band):y0, x0:x1])
    if y1 + band <= h:
        strips.append(rgb[y1:min(h, y1 + band), x0:x1])
    if not strips:
        return None
    px = np.concatenate([s.reshape(-1, 3) for s in strips])
    if len(px) < 200:
        return None
    return np.median(px, axis=0)
