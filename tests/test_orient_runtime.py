"""The orientation runtime is numpy + OpenCV. Nothing heavier.

It used to need torch (529 MB) plus a 98 MB weight download plus a restart of
the walkthrough, all to evaluate a frozen conv stack. The backbone now runs as
ONNX through the OpenCV that is already a hard dependency. These tests hold that
line: no sklearn, no torch, and the pooling that feeds the probe stays exactly
what the probe was fitted on.
"""
import sys

import numpy as np
import pytest

from silbersalz_look import orient


def _model_available():
    if orient.have_backbone():
        return True
    try:
        import torch, torchvision  # noqa: F401
        return True
    except Exception:
        return False


needs_model = pytest.mark.skipif(not _model_available(),
                                 reason="orientation backbone not downloaded and torch not installed")


# --- the pooling the probe was fitted on ----------------------------------

def test_adaptive_pool_bins_overlap():
    """7 -> 2 gives rows [0,4) and [3,7), not a half split.

    A naive half split produces plausible-looking features that mean nothing to
    the probe, and nothing downstream would flag it.
    """
    fm = np.arange(7 * 7, dtype=np.float32).reshape(1, 1, 7, 7)
    got = orient._adaptive_avg_pool_2x2(fm).reshape(2, 2)
    expect = np.array([[fm[0, 0, 0:4, 0:4].mean(), fm[0, 0, 0:4, 3:7].mean()],
                       [fm[0, 0, 3:7, 0:4].mean(), fm[0, 0, 3:7, 3:7].mean()]], np.float32)
    assert np.allclose(got, expect)
    half = np.array([[fm[0, 0, 0:3, 0:3].mean(), fm[0, 0, 0:3, 3:7].mean()],
                     [fm[0, 0, 3:7, 0:3].mean(), fm[0, 0, 3:7, 3:7].mean()]], np.float32)
    assert not np.allclose(got, half), "the test would not catch a half-split regression"


def test_adaptive_pool_flattens_channel_major():
    fm = np.zeros((1, 3, 4, 4), np.float32)
    fm[0, 1] = 1.0
    out = orient._adaptive_avg_pool_2x2(fm)[0]
    assert out.shape == (12,)
    assert out[:4].sum() == 0 and out[4:8].sum() == 4 and out[8:].sum() == 0


# --- the runtime ----------------------------------------------------------

@needs_model
def test_predict_needs_no_sklearn(monkeypatch):
    monkeypatch.setitem(sys.modules, "sklearn", None)   # make any sklearn import fail
    m = orient.OrientationModel(use_faces=True)
    assert m.probe is not None
    assert m.backend in ("onnx", "torch")
    rgb = np.random.default_rng(0).random((120, 160, 3)).astype(np.float32)
    r = m.predict(rgb)
    assert r["k"] in (0, 1, 2, 3)
    # predict() rounds each probability to 3 dp, so four of them sum to 1 +/- 0.002
    assert abs(sum(r["probe"]) - 1) <= 2e-3


@pytest.mark.skipif(not orient.have_backbone(), reason="backbone not downloaded")
def test_the_onnx_path_does_not_touch_torch(monkeypatch):
    """The point of the migration: torch must be unnecessary, not merely optional."""
    monkeypatch.setitem(sys.modules, "torch", None)
    monkeypatch.setitem(sys.modules, "torchvision", None)
    m = orient.OrientationModel(use_faces=False)
    assert m.backend == "onnx"
    rgb = np.random.default_rng(1).random((100, 140, 3)).astype(np.float32)
    assert m.predict(rgb)["k"] in (0, 1, 2, 3)


# --- the fetch ------------------------------------------------------------

def test_backbone_is_pinned_by_digest():
    """A 47 MB binary pulled over the network is verified before it is used."""
    assert len(orient.BACKBONE["sha256"]) == 64
    assert orient.BACKBONE["url"].startswith("https://")
    assert orient.BACKBONE["bytes"] > 1_000_000


def test_a_corrupt_download_is_refused_and_leaves_nothing_behind(tmp_path, monkeypatch):
    import io

    dst = tmp_path / "models" / orient.BACKBONE["file"]
    monkeypatch.setattr(orient, "backbone_path", lambda: dst)

    class FakeResponse(io.BytesIO):
        headers = {"Content-Length": "9"}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: FakeResponse(b"not-a-net"))
    with pytest.raises(RuntimeError, match="checksum"):
        orient.ensure_backbone()
    assert not dst.exists(), "a mismatched download must not be left where it would be loaded"
    assert not list(dst.parent.glob("*.part")), "the partial file was left behind"


def test_the_installer_pins_the_same_file_as_the_runtime():
    """install.sh fetches the backbone ahead of time; a drifted url or digest
    there would silently install a model the runtime then rejects."""
    from pathlib import Path
    sh = Path(__file__).resolve().parents[1] / "install.sh"
    if not sh.exists():                      # the LUT release zip ships without it
        import pytest
        pytest.skip("install.sh not in this tree")
    text = sh.read_text()
    assert orient.BACKBONE["url"] in text, "install.sh points at a different url"
    assert orient.BACKBONE["sha256"] in text, "install.sh pins a different digest"
    assert orient.BACKBONE["file"] in text, "install.sh writes a different filename"


def test_third_party_notices_cover_both_shipped_models():
    """BSD-3 requires the notice to travel with the binary, and the YuNet file
    has shipped since v0.1.17 with no attribution at all."""
    from pathlib import Path
    n = Path(__file__).resolve().parents[1] / "THIRD-PARTY-NOTICES.md"
    assert n.exists(), "the attribution file is missing"
    text = n.read_text()
    assert "BSD 3-Clause" in text, "torchvision's licence text is not reproduced"
    assert "Redistribution and use in source and binary forms" in text
    assert orient.BACKBONE["sha256"] in text, "the notice does not identify the file we ship"
    assert orient.YUNET_PATH.name in text, "the shipped face detector is unattributed"
    assert "ImageNet" in text, "the training-data provenance is not stated"
