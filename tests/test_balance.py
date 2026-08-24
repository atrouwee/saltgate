"""Per-frame balancing. The load-bearing fact here is that it is OFF by
default: measured on 27 real pairs, normalising each frame toward a fixed
anchor was far worse than the bare LUT (dE2000 6.5 vs 2.5). These tests pin
that default and the clamps, so a future refactor can't quietly re-enable it.
"""
import numpy as np

from silbersalz_look import balance, color


def _pixels(median_linear=(0.18, 0.18, 0.18), n=4000, seed=0):
    """Display-encoded pixels whose linear midtone median is known."""
    rng = np.random.default_rng(seed)
    lin = np.asarray(median_linear, np.float64) * rng.lognormal(0.0, 0.25, size=(n, 3))
    return color.oetf(np.clip(lin, 0.0, 1.0)).astype(np.float32)


def test_default_is_off_and_off_is_a_no_op():
    assert balance.DEFAULT_MODE == "off"
    px = _pixels()
    anchors = balance.anchors_from_pixels(px)
    # explicitly off, and the "no anchors" fallback, both mean identity
    assert np.allclose(balance.estimate_gains(px, anchors, mode="off"), 1.0)
    assert np.allclose(balance.estimate_gains(px, {}, mode="exposure"), 1.0)


def test_anchors_round_trip():
    px = _pixels(median_linear=(0.20, 0.18, 0.16))
    a = balance.anchors_from_pixels(px)
    assert np.allclose(a["p50_linear"], [0.20, 0.18, 0.16], rtol=0.06)
    expected_luma = float(np.asarray([0.20, 0.18, 0.16]) @ balance.LUMA_P3)
    assert abs(a["luma_p50_linear"] - expected_luma) / expected_luma < 0.06


def test_exposure_mode_is_one_scalar_gain():
    # a frame 1.5 stops under the anchor must come back as ONE gain on all
    # three channels (no per-channel white balance), clamped to +/-~0.4 stop
    anchors = balance.anchors_from_pixels(_pixels(0.18 * np.ones(3)))
    dark = _pixels(0.18 * np.ones(3) / 2.8, seed=1)
    g = balance.estimate_gains(dark, anchors, mode="exposure")
    assert np.allclose(g, g[0]), "exposure mode must not shift channels relative to each other"
    lo, hi = balance.EXPOSURE_CLAMP
    assert lo <= g[0] <= hi, f"gain {g[0]} escaped the exposure clamp {balance.EXPOSURE_CLAMP}"


def test_wb_only_is_neutral_in_overall_level():
    # wb-only corrects colour but must not change exposure: geometric mean == 1
    anchors = balance.anchors_from_pixels(_pixels((0.18, 0.18, 0.18)))
    cast = _pixels((0.26, 0.18, 0.12), seed=2)   # warm frame
    g = balance.estimate_gains(cast, anchors, mode="wb-only")
    assert abs(float(np.exp(np.mean(np.log(g)))) - 1.0) < 1e-6
    assert g[0] < g[2], "a warm frame should be pulled back toward neutral"


def test_channel_clamp_bounds_auto_mode():
    anchors = balance.anchors_from_pixels(_pixels((0.5, 0.5, 0.5)))
    tiny = _pixels((0.002, 0.002, 0.002), seed=3)   # absurdly far from anchor
    g = balance.estimate_gains(tiny, anchors, mode="auto")
    lo, hi = balance.CHANNEL_CLAMP
    assert np.all(g >= lo) and np.all(g <= hi)


def test_apply_gains_identity_and_highlight_knee():
    rgb = np.linspace(0.0, 1.0, 300, dtype=np.float32).reshape(-1, 1).repeat(3, axis=1)
    # unity gain is a bit-exact no-op (the fast path)
    assert balance.apply_gains(rgb, np.ones(3)) is rgb
    # a lifting gain must stay in range AND keep highlight ordering (soft knee,
    # not a hard clip) so the LUT still sees distinct highlight values
    out = balance.apply_gains(rgb, np.full(3, 1.3))
    assert out.min() >= 0.0 and out.max() <= 1.0
    top = out[-40:, 0]
    assert np.all(np.diff(top) > 0), "highlights were hard-clipped; ordering lost"
    # the low end is untouched by the knee (low_end=False)
    assert np.allclose(out[:5, 0], color.oetf(color.eotf(rgb[:5]) * 1.3)[:, 0], atol=2e-3)
