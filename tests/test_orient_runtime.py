import sys
import numpy as np
import pytest

torch = pytest.importorskip("torch")


def test_orientation_model_has_no_sklearn_dependency(monkeypatch):
    monkeypatch.setitem(sys.modules, "sklearn", None)   # make any sklearn import fail
    from silbersalz_look import orient
    m = orient.OrientationModel(use_faces=True)
    assert m.probe is not None
    rgb = np.random.default_rng(0).random((120, 160, 3)).astype(np.float32)
    r = m.predict(rgb)
    assert r["k"] in (0, 1, 2, 3) and abs(sum(r["probe"]) - 1) < 1e-3
