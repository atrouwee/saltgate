"""Color science primitives: transfer functions, matrices, Lab, dE2000, soft clip.

Working convention throughout the package: "code values" are display-encoded
RGB floats in [0, 1]. Both the Silbersalz flat scans and the lab's graded
deliveries are tagged Display P3, which shares the sRGB transfer curve but
uses DCI-P3 primaries with a D65 white point.
"""
from __future__ import annotations

import numpy as np

# --- transfer functions (sRGB curve, shared by Display P3) ------------------


def eotf(codes: np.ndarray) -> np.ndarray:
    """Display-encoded [0,1] -> linear light [0,1] (sRGB piecewise curve)."""
    c = np.clip(codes, 0.0, 1.0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def oetf(linear: np.ndarray) -> np.ndarray:
    """Linear light [0,1] -> display-encoded [0,1] (sRGB piecewise curve)."""
    l = np.clip(linear, 0.0, 1.0)
    return np.where(l <= 0.0031308, l * 12.92, 1.055 * l ** (1.0 / 2.4) - 0.055)


# --- primaries (linear RGB <-> XYZ, D65) ------------------------------------

# sRGB / Rec.709 primaries, D65
SRGB_TO_XYZ = np.array(
    [
        [0.4123908, 0.3575843, 0.1804808],
        [0.2126390, 0.7151687, 0.0721923],
        [0.0193308, 0.1191948, 0.9505322],
    ]
)
# Display P3 (P3 primaries, D65 white)
P3_TO_XYZ = np.array(
    [
        [0.4865709, 0.2656677, 0.1982173],
        [0.2289746, 0.6917385, 0.0792869],
        [0.0000000, 0.0451134, 1.0439444],
    ]
)
XYZ_TO_SRGB = np.linalg.inv(SRGB_TO_XYZ)
XYZ_TO_P3 = np.linalg.inv(P3_TO_XYZ)

D65_WHITE_XYZ = np.array([0.95047, 1.00000, 1.08883])


def _apply_matrix(m: np.ndarray, rgb: np.ndarray) -> np.ndarray:
    return rgb @ m.T


def convert_srgb_to_p3(codes: np.ndarray) -> np.ndarray:
    """sRGB code values -> Display P3 code values (colorimetric)."""
    lin = eotf(codes)
    xyz = _apply_matrix(SRGB_TO_XYZ, lin)
    lin_p3 = np.clip(_apply_matrix(XYZ_TO_P3, xyz), 0.0, 1.0)
    return oetf(lin_p3)


def convert_p3_to_srgb(codes: np.ndarray) -> np.ndarray:
    """Display P3 code values -> sRGB code values (colorimetric, gamut-clipped)."""
    lin = eotf(codes)
    xyz = _apply_matrix(P3_TO_XYZ, lin)
    lin_s = np.clip(_apply_matrix(XYZ_TO_SRGB, xyz), 0.0, 1.0)
    return oetf(lin_s)


# --- Lab / dE2000 -----------------------------------------------------------


def p3_codes_to_lab(codes: np.ndarray) -> np.ndarray:
    """Display P3 code values -> CIELAB (D65). Shape (..., 3)."""
    xyz = _apply_matrix(P3_TO_XYZ, eotf(codes)) / D65_WHITE_XYZ
    eps, kappa = 216.0 / 24389.0, 24389.0 / 27.0
    f = np.where(xyz > eps, np.cbrt(xyz), (kappa * xyz + 16.0) / 116.0)
    L = 116.0 * f[..., 1] - 16.0
    a = 500.0 * (f[..., 0] - f[..., 1])
    b = 200.0 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def delta_e_2000(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    """CIEDE2000 (Sharma et al. formulation). Inputs shape (..., 3)."""
    L1, a1, b1 = lab1[..., 0], lab1[..., 1], lab1[..., 2]
    L2, a2, b2 = lab2[..., 0], lab2[..., 1], lab2[..., 2]

    C1 = np.hypot(a1, b1)
    C2 = np.hypot(a2, b2)
    Cbar = 0.5 * (C1 + C2)
    G = 0.5 * (1.0 - np.sqrt(Cbar ** 7 / (Cbar ** 7 + 25.0 ** 7)))
    a1p, a2p = (1.0 + G) * a1, (1.0 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360.0
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360.0

    dLp = L2 - L1
    dCp = C2p - C1p
    dhp = h2p - h1p
    dhp = np.where(dhp > 180.0, dhp - 360.0, dhp)
    dhp = np.where(dhp < -180.0, dhp + 360.0, dhp)
    dhp = np.where(C1p * C2p == 0.0, 0.0, dhp)
    dHp = 2.0 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp) / 2.0)

    Lbarp = 0.5 * (L1 + L2)
    Cbarp = 0.5 * (C1p + C2p)
    hsum = h1p + h2p
    hdiff = np.abs(h1p - h2p)
    hbarp = np.where(
        C1p * C2p == 0.0,
        hsum,
        np.where(
            hdiff <= 180.0,
            0.5 * hsum,
            np.where(hsum < 360.0, 0.5 * (hsum + 360.0), 0.5 * (hsum - 360.0)),
        ),
    )
    T = (
        1.0
        - 0.17 * np.cos(np.radians(hbarp - 30.0))
        + 0.24 * np.cos(np.radians(2.0 * hbarp))
        + 0.32 * np.cos(np.radians(3.0 * hbarp + 6.0))
        - 0.20 * np.cos(np.radians(4.0 * hbarp - 63.0))
    )
    dtheta = 30.0 * np.exp(-(((hbarp - 275.0) / 25.0) ** 2))
    Rc = 2.0 * np.sqrt(Cbarp ** 7 / (Cbarp ** 7 + 25.0 ** 7))
    Sl = 1.0 + 0.015 * (Lbarp - 50.0) ** 2 / np.sqrt(20.0 + (Lbarp - 50.0) ** 2)
    Sc = 1.0 + 0.045 * Cbarp
    Sh = 1.0 + 0.015 * Cbarp * T
    Rt = -np.sin(np.radians(2.0 * dtheta)) * Rc

    return np.sqrt(
        (dLp / Sl) ** 2
        + (dCp / Sc) ** 2
        + (dHp / Sh) ** 2
        + Rt * (dCp / Sc) * (dHp / Sh)
    )


# --- soft clip --------------------------------------------------------------


def soft_clip(x: np.ndarray, knee: float = 0.02) -> np.ndarray:
    """Smoothly compress values outside [0,1] into the last `knee` of range.

    Identity on [knee, 1-knee]; rational soft knee at both ends so LUT
    lattices contain no hard clipping cliffs.
    """
    lo = knee
    hi = 1.0 - knee

    def _knee_high(v):
        t = (v - hi) / knee  # 0 at knee start, can exceed 1
        return hi + knee * (t / (1.0 + t))

    def _knee_low(v):
        t = (lo - v) / knee
        return lo - knee * (t / (1.0 + t))

    out = np.asarray(x, dtype=np.float64).copy()
    high = out > hi
    low = out < lo
    out[high] = _knee_high(out[high])
    out[low] = _knee_low(out[low])
    return np.clip(out, 0.0, 1.0)
