"""Per-image exposure / white-balance normalization at apply time.

Mimics the lab's per-shot correction. The archive catalog shows the lab
*preserved scene color temperature* (golden scenes stay warm, overcast stays
cool), so the default mode is `exposure`: one scalar linear gain per frame.
`auto` (per-channel gray-world style) and `wb-only` remain available.
"""
from __future__ import annotations

import numpy as np

from . import color

DEFAULT_MODE = "exposure"
EXPOSURE_CLAMP = (0.75, 1.33)   # +/- ~0.4 stop: flats have little highlight headroom
CHANNEL_CLAMP = (0.5, 2.0)


def _midtone_linear(rgb_area: np.ndarray) -> np.ndarray:
    lin = color.eotf(rgb_area.reshape(-1, 3).astype(np.float64))
    luma = lin.mean(axis=1)
    lo, hi = np.quantile(luma, [0.25, 0.75])
    mid = lin[(luma >= lo) & (luma <= hi)]
    return mid if len(mid) >= 100 else lin


def anchors_from_pixels(rgb_px: np.ndarray) -> dict:
    """Anchor statistics stored in a LUT's .stats.json (from fitting flats)."""
    mid = _midtone_linear(rgb_px)
    return {
        "p50_linear": [float(np.median(mid[:, c])) for c in range(3)],
        "luma_p50_linear": float(np.median(mid.mean(axis=1))),
    }


def estimate_gains(
    rgb_area: np.ndarray,
    anchors: dict,
    mode: str = DEFAULT_MODE,
    strength: float = 1.0,
    clamp: tuple[float, float] | None = None,
) -> np.ndarray:
    """Per-channel linear gains for one frame (rgb_area: image-area preview)."""
    if mode == "off" or not anchors:
        return np.ones(3)
    if clamp is None:
        clamp = EXPOSURE_CLAMP if mode == "exposure" else CHANNEL_CLAMP
    mid = _midtone_linear(rgb_area)
    if mode == "exposure":
        target = anchors.get("luma_p50_linear")
        if target is None:
            target = float(np.mean(anchors["p50_linear"]))
        current = float(np.median(mid.mean(axis=1)))
        gains = np.full(3, target / max(current, 1e-6))
    else:
        target = np.asarray(anchors["p50_linear"], dtype=np.float64)
        current = np.median(mid, axis=0)
        gains = target / np.maximum(current, 1e-6)
        if mode == "wb-only":
            gains = gains / np.exp(np.mean(np.log(np.maximum(gains, 1e-6))))
    gains = np.clip(gains, clamp[0], clamp[1])
    if strength != 1.0:
        gains = gains ** float(strength)
    return gains


def apply_gains(rgb: np.ndarray, gains: np.ndarray) -> np.ndarray:
    """Apply linear-light diagonal gains to display-encoded rgb.

    Clip-safe: values a positive gain pushes above ~0.95 linear are rolled
    off with a soft knee instead of hard-clipped, so highlight detail keeps
    its ordering for the LUT."""
    if np.allclose(gains, 1.0):
        return rgb
    lin = color.eotf(rgb) * gains.astype(np.float32)
    if float(np.max(gains)) > 1.0:
        lin = color.soft_clip(lin, knee=0.05, low_end=False).astype(np.float32)
    return color.oetf(np.clip(lin, 0.0, 1.0))
