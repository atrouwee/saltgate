"""Per-image exposure / white-balance normalization at apply time.

Mimics the lab's per-shot balancing: estimate diagonal linear-light gains
that bring a frame's midtone medians to the anchors stored in the LUT's
.stats.json sidecar, then apply them before the LUT.
"""
from __future__ import annotations

import numpy as np

from . import color


def estimate_gains(
    rgb_area: np.ndarray,
    anchors: dict,
    mode: str = "auto",
    strength: float = 1.0,
    clamp: tuple[float, float] = (0.5, 2.0),
) -> np.ndarray:
    """Per-channel linear gains for one frame (rgb_area: image-area preview)."""
    if mode == "off" or not anchors:
        return np.ones(3)
    target = np.asarray(anchors["p50_linear"], dtype=np.float64)
    lin = color.eotf(rgb_area.reshape(-1, 3).astype(np.float64))
    luma = lin.mean(axis=1)
    lo, hi = np.quantile(luma, [0.25, 0.75])
    mid = lin[(luma >= lo) & (luma <= hi)]
    if len(mid) < 100:
        mid = lin
    current = np.median(mid, axis=0)
    gains = target / np.maximum(current, 1e-6)
    if mode == "wb-only":
        gains = gains / np.exp(np.mean(np.log(np.maximum(gains, 1e-6))))
    gains = np.clip(gains, clamp[0], clamp[1])
    if strength != 1.0:
        gains = gains ** float(strength)
    return gains


def apply_gains(rgb: np.ndarray, gains: np.ndarray) -> np.ndarray:
    """Apply linear-light diagonal gains to display-encoded rgb."""
    if np.allclose(gains, 1.0):
        return rgb
    lin = color.eotf(rgb) * gains.astype(np.float32)
    return color.oetf(np.clip(lin, 0.0, 1.0))
