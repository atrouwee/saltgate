"""Does this roll behave like the pairs the chosen look was measured from?

The film base can't tell us -- the lab's scanner normalises each roll, so
rebate density carries no fingerprint (measured; see FINDINGS). What does
discriminate is the SHADOW CHROMATICITY of the graded render: a wrong stock
or a pushed/pulled roll drags the shadows' a*b* far outside anything the
fitting pairs contain (mismatches measure 1.8-2.8x the envelope's own p90
spread; correct rolls 0.3-0.5x, including a summer roll against a winter
envelope). Content leaks into whole-frame statistics; the L* 15-45 band is
where scene colour matters least and mask/crossover errors show most.

data/stock_check.json holds, per fitted stock, the envelope median a*b* and
p90 spread of the pairs' graded sides -- aggregate numbers only, no donor
pixels. Regenerate with scripts/build_stock_check.py after new pairs land.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import color, imgio, lut as lutmod, rebate

def _data_path() -> Path:
    """Repo data/ when running from a checkout, else the copy shipped inside
    the installed package -- same arrangement as looks.lut_dir()."""
    here = Path(__file__).resolve()
    for cand in (here.parents[2] / "data/stock_check.json",
                 here.parent / "data/stock_check.json"):
        if cand.exists():
            return cand
    return here.parents[2] / "data/stock_check.json"


DATA = _data_path()
THRESHOLD = 1.2          # ratio of roll distance to envelope p90 spread
L_BAND = (15.0, 45.0)


def shadow_ab(lab: np.ndarray) -> np.ndarray | None:
    m = (lab[:, 0] >= L_BAND[0]) & (lab[:, 0] <= L_BAND[1])
    if m.sum() < 200:
        return None
    return lab[m, 1:].mean(axis=0)


def roll_shadow_ab(files, lattice: np.ndarray, max_frames: int = 6) -> np.ndarray | None:
    picks = list(files)[:: max(1, len(files) // max_frames)][:max_frames]
    out = []
    for f in picks:
        a = imgio.read_image(f, max_px=500).rgb
        box = rebate.detect_image_area_fractions(a)
        if box is not None:
            a = rebate.crop_to_area(a, box)
        g = np.clip(lutmod.apply_trilinear(lattice, a), 0, 1)
        v = shadow_ab(color.p3_codes_to_lab(g.reshape(-1, 3).astype(np.float64)))
        if v is not None:
            out.append(v)
    if len(out) < 3:
        return None
    return np.median(np.array(out), axis=0)


def check(files, lattice: np.ndarray, stock: str) -> dict | None:
    """None when no envelope exists for this stock or the roll gave no
    usable shadows; otherwise {"ratio", "dist", "ok"}."""
    try:
        env = json.loads(DATA.read_text()).get(stock)
    except OSError:
        return None
    if not env:
        return None
    rm = roll_shadow_ab(files, lattice)
    if rm is None:
        return None
    d = float(np.linalg.norm(rm - np.array(env["ab"])))
    ratio = d / max(float(env["p90"]), 1e-6)
    return {"ratio": round(ratio, 2), "dist": round(d, 1), "ok": ratio < THRESHOLD}
