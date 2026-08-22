"""Batch application of a LUT to folders of full-resolution flat scans.

147 MP frames are processed in row strips to bound memory; ICC + EXIF are
copied from the source so outputs stay tagged like the lab's deliveries.
"""
from __future__ import annotations

import concurrent.futures as cf
import time
from pathlib import Path

import numpy as np
from PIL import Image

from . import balance, imgio, lut as lutmod, rebate

STRIP_ROWS = 512


def grade_one(
    src: Path,
    dst: Path,
    lattice: np.ndarray,
    anchors: dict | None,
    balance_mode: str = "auto",
    balance_strength: float = 1.0,
    area_frac: tuple | None = None,
    quality: int = 95,
) -> dict:
    t0 = time.time()
    img = Image.open(src)
    icc = img.info.get("icc_profile")
    exif = img.info.get("exif")
    w, h = img.size

    gains = np.ones(3)
    if balance_mode != "off" and anchors:
        preview = imgio.read_image(src, max_px=1200)
        area = (
            rebate.crop_to_area(preview.rgb, area_frac) if area_frac else preview.rgb
        )
        gains = balance.estimate_gains(
            area, anchors, mode=balance_mode, strength=balance_strength
        )

    arr = np.asarray(img.convert("RGB"), dtype=np.uint8)
    out = np.empty_like(arr)
    rng = np.random.default_rng(hash(src.name) & 0xFFFFFFFF)
    for y0 in range(0, h, STRIP_ROWS):
        strip = arr[y0 : y0 + STRIP_ROWS].astype(np.float32) / 255.0
        strip = balance.apply_gains(strip, gains)
        graded = lutmod.apply_trilinear(lattice, strip)
        graded += imgio.triangular_dither(graded.shape, rng)
        out[y0 : y0 + STRIP_ROWS] = np.clip(np.rint(graded * 255.0), 0, 255).astype(
            np.uint8
        )

    res = Image.fromarray(out, mode="RGB")
    kwargs: dict = {"quality": quality, "subsampling": 0}
    if icc:
        kwargs["icc_profile"] = icc
    if exif:
        kwargs["exif"] = exif
    res.save(str(dst), "JPEG", **kwargs)
    return {
        "file": src.name,
        "gains": [round(float(g), 4) for g in gains],
        "seconds": round(time.time() - t0, 1),
    }


def grade_folder(
    in_dir: Path,
    out_dir: Path,
    cube_path: Path,
    balance_mode: str = "auto",
    balance_strength: float = 1.0,
    workers: int = 4,
    quality: int = 95,
    resume: bool = False,
    image_area: tuple | None = None,
    cache_dir: Path | None = None,
    log=print,
) -> list[dict]:
    lattice, title = lutmod.read_cube(cube_path)
    stats = lutmod.read_stats_sidecar(cube_path) or {}
    anchors = stats.get("balance_anchors")

    files = [f for f in imgio.list_images(in_dir) if f.suffix.lower() in (".jpg", ".jpeg")]
    if not files:
        raise RuntimeError(f"no JPEGs found in {in_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    area_frac = image_area
    if area_frac is None and balance_mode != "off":
        area_frac = rebate.roll_area_fractions(files, cache_dir=cache_dir)

    todo = []
    for f in files:
        dst = out_dir / f.name
        if resume and dst.exists():
            continue
        todo.append((f, dst))
    log(f"[apply] {len(todo)} of {len(files)} frames to grade with '{title}' "
        f"(balance={balance_mode}, workers={workers})")

    results = []
    with cf.ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {
            ex.submit(
                grade_one,
                src,
                dst,
                lattice,
                anchors,
                balance_mode,
                balance_strength,
                area_frac,
                quality,
            ): src
            for src, dst in todo
        }
        done = 0
        for fut in cf.as_completed(futs):
            r = fut.result()
            results.append(r)
            done += 1
            log(f"  [{done}/{len(todo)}] {r['file']} gains={r['gains']} ({r['seconds']}s)")
    return results
