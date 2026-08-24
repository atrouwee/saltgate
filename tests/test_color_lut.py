"""Runtime colour + lattice invariants.

Both tests were previously stranded in tests/test_statistical.py, which is a
research-side file; they exercise only public runtime modules, so they live
here and stay with the public distribution.
"""
import numpy as np

from silbersalz_look import color, lut


def test_soft_clip_smooth_and_bounded():
    x = np.linspace(-0.2, 1.2, 1000)
    y = color.soft_clip(x)
    assert y.min() >= 0.0 and y.max() <= 1.0
    mid = (x > 0.1) & (x < 0.9)
    assert np.allclose(y[mid], x[mid], atol=1e-9)


def test_smooth_lattice_no_nans_and_bounded_change():
    rng = np.random.default_rng(2)
    n = 17
    lattice = np.clip(
        lut.identity_lattice(n) + rng.normal(0, 0.02, (n, n, n, 3)), 0, 1
    ).astype(np.float32)
    sm = lut.smooth_lattice(lattice, lam=0.3)
    assert np.isfinite(sm).all()
    assert np.abs(sm - lattice).max() < 0.1
