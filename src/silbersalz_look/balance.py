"""Per-image exposure / white-balance normalization at apply time.

OFF BY DEFAULT. Measured on 27 real pairs, normalising each frame toward a
fixed anchor made results far WORSE than the bare LUT (median dE2000 6.5 vs
2.5): the lab's own per-frame corrections were only +/-0.04 stop, while this
estimator swings +/-0.35 stop with no correlation to them. The modes remain
available for manual/experimental use (`exposure`: one scalar gain; `auto`:
per-channel; `wb-only`).
"""
from __future__ import annotations

import numpy as np

from . import color

DEFAULT_MODE = "off"
EXPOSURE_CLAMP = (0.75, 1.33)   # +/- ~0.4 stop: flats have little highlight headroom
CHANNEL_CLAMP = (0.5, 2.0)


LUMA_P3 = np.array([0.2289746, 0.6917385, 0.0792869])  # Display P3 -> Y (linear)


def _midtone_linear(rgb_area: np.ndarray) -> np.ndarray:
    lin = color.eotf(rgb_area.reshape(-1, 3).astype(np.float64))
    luma = lin @ LUMA_P3
    lo, hi = np.quantile(luma, [0.25, 0.75])
    mid = lin[(luma >= lo) & (luma <= hi)]
    return mid if len(mid) >= 100 else lin


def anchors_from_pixels(rgb_px: np.ndarray) -> dict:
    """Anchor statistics stored in a LUT's .stats.json (from fitting flats)."""
    mid = _midtone_linear(rgb_px)
    return {
        "p50_linear": [float(np.median(mid[:, c])) for c in range(3)],
        "luma_p50_linear": float(np.median(mid @ LUMA_P3)),
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
        current = float(np.median(mid @ LUMA_P3))
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

    gains is [gR,gG,gB] or [gR,gG,gB,black]; black is subtracted in linear
    light before the gains -- the same convention as models.apply_gains_to_x,
    so a black measured against pairs applies identically here.

    Clip-safe: values a positive gain pushes above ~0.95 linear are rolled
    off with a soft knee instead of hard-clipped, so highlight detail keeps
    its ordering for the LUT."""
    gains = np.asarray(gains, dtype=np.float32)
    black = float(gains[3]) if len(gains) > 3 else 0.0
    gains = gains[:3]
    if np.allclose(gains, 1.0) and black == 0.0:
        return rgb
    lin = (color.eotf(rgb) - black) * gains
    if float(np.max(gains)) > 1.0:
        lin = color.soft_clip(lin, knee=0.05, low_end=False).astype(np.float32)
    return color.oetf(np.clip(lin, 0.0, 1.0))
