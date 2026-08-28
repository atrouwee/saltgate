"""Batch application of a LUT to folders of full-resolution flat scans.

Memory discipline (147 MP frames): the decoded uint8 array is processed in
row strips *in place* (no second full-frame buffer), the PIL image is closed
right after decode, and the worker count defaults to what the machine's RAM
can hold (~1 GB peak per worker).
"""
from __future__ import annotations

import concurrent.futures as cf
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

from . import balance, imgio, lut as lutmod, rebate

STRIP_ROWS = 384
PEAK_GB_PER_WORKER = 1.1


def ram_gb() -> float:
    """Installed RAM in GB, or a conservative 8 if the machine won't say.

    This is not trivia: default_workers() divides it, so the macOS-only `sysctl`
    this used to be meant every Windows and Linux machine fell back to 8 GB and
    graded on exactly ONE worker, however much memory it actually had. A 32 GB
    PC was running a roll at a quarter speed for no reason.
    """
    try:
        if sys.platform == "darwin":
            import subprocess

            out = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True)
            return int(out.stdout.strip()) / 1073741824
        if os.name == "nt":
            import ctypes

            class _MemoryStatusEx(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_uint32), ("dwMemoryLoad", ctypes.c_uint32),
                            ("ullTotalPhys", ctypes.c_uint64), ("ullAvailPhys", ctypes.c_uint64),
                            ("ullTotalPageFile", ctypes.c_uint64), ("ullAvailPageFile", ctypes.c_uint64),
                            ("ullTotalVirtual", ctypes.c_uint64), ("ullAvailVirtual", ctypes.c_uint64),
                            ("ullAvailExtendedVirtual", ctypes.c_uint64)]

            status = _MemoryStatusEx()
            status.dwLength = ctypes.sizeof(_MemoryStatusEx)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return 8.0
            return status.ullTotalPhys / 1073741824
        return (os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")) / 1073741824
    except Exception:
        return 8.0


def default_workers() -> int:
    cpu = os.cpu_count() or 4
    by_ram = int((ram_gb() - 6.0) // 2.5)
    return max(1, min(cpu // 3, by_ram, 4))


def grade_one(
    src: Path,
    dst: Path,
    lattice: np.ndarray,
    anchors: dict | None,
    balance_mode: str = balance.DEFAULT_MODE,
    balance_strength: float = 1.0,
    area_frac: tuple | None = None,
    quality: int = 95,
    density: float = 0.0,
    rotate_k: int = 0,
    bits: int = 8,
    crop_edge: float | None = None,
) -> dict:
    t0 = time.time()
    if bits >= 16:
        return _grade_one_16(src, dst, lattice, gains_density=density, quality=quality,
                             rotate_k=rotate_k, t0=t0)
    gains = np.ones(3)
    if balance_mode != "off" and anchors:
        preview = imgio.read_image(src, max_px=1200)
        area = rebate.crop_to_area(preview.rgb, area_frac) if area_frac else preview.rgb
        gains = balance.estimate_gains(area, anchors, mode=balance_mode, strength=balance_strength)
        del preview, area
    gains = gains * (2.0 ** density)  # print density: negative = denser/darker

    with Image.open(src) as img:
        icc = img.info.get("icc_profile")
        exif = img.info.get("exif")
        arr = np.asarray(img.convert("RGB"), dtype=np.uint8).copy()
    crop_note = "off"
    if crop_edge is not None:
        crop_note = "nofit"
        # Trim the film rebate, leaving `crop_edge` of the frame as border.
        # Measured per frame on the flat scan itself: the roll median forces
        # symmetric side insets, and frame spacing drifts along the strip, so a
        # roll-wide box leaves a slit down one edge of some frames.
        box = rebate.detect_image_area_fractions(arr.astype(np.float32) / 255.0)
        if box is not None:
            bx, by, bw, bh = box
            g = crop_edge
            bx, by, bw, bh = bx + g, by + g, bw - 2 * g, bh - 2 * g
            H, W = arr.shape[:2]
            y0, y1 = max(0, int(by * H)), min(H, int((by + bh) * H))
            x0, x1 = max(0, int(bx * W)), min(W, int((bx + bw) * W))
            if (y1 - y0) > 0.3 * H and (x1 - x0) > 0.3 * W:
                cropped = arr[y0:y1, x0:x1]
                # the detected box sits off-picture on one axis; even the border
                dy, dx = rebate.centering_shift(cropped.astype(np.float32) / 255.0)
                crop_note = "cropped"
                if dy or dx:
                    ny0, ny1 = y0 + dy, y1 + dy
                    nx0, nx1 = x0 + dx, x1 + dx
                    if 0 <= ny0 and ny1 <= H and 0 <= nx0 and nx1 <= W:
                        y0, y1, x0, x1 = ny0, ny1, nx0, nx1
                        crop_note = "centred"
                arr = arr[y0:y1, x0:x1].copy()
    h = arr.shape[0]
    import hashlib
    rng = np.random.default_rng(int(hashlib.sha1(src.name.encode()).hexdigest()[:8], 16))
    for y0 in range(0, h, STRIP_ROWS):
        strip = arr[y0 : y0 + STRIP_ROWS].astype(np.float32) / 255.0
        strip = balance.apply_gains(strip, gains)
        graded = lutmod.apply_trilinear(lattice, strip)
        graded += imgio.triangular_dither(graded.shape, rng)
        arr[y0 : y0 + STRIP_ROWS] = np.clip(np.rint(graded * 255.0), 0, 255).astype(np.uint8)
        del strip, graded

    if rotate_k % 4:
        from . import orient
        arr = orient.apply_rotation(arr, rotate_k)
    res = Image.fromarray(arr, mode="RGB")
    kwargs: dict = {"quality": quality, "subsampling": 0}
    if icc:
        kwargs["icc_profile"] = icc
    if exif:
        kwargs["exif"] = exif
    res.save(str(dst), "JPEG", **kwargs)
    del res, arr
    return {
        "file": src.name,
        "crop": crop_note,
        "gains": [round(float(g), 4) for g in gains],
        "seconds": round(time.time() - t0, 1),
    }


def _grade_one_16(src: Path, dst: Path, lattice, gains_density: float, quality: int,
                  rotate_k: int, t0: float) -> dict:
    """16-bit path: decode at true depth, grade in float, write 16-bit TIFF.

    Kept separate from the 8-bit path on purpose. That one processes uint8 strips
    in place to hold a 147 MP frame in ~1 GB; a 16-bit frame cannot use the same
    trick because the decoders (JXL, JP2) only hand back whole images, so this
    branch trades memory for depth and the worker count is reduced to match.
    """
    img = imgio.read_image(src)
    rgb = img.rgb
    g = np.float32(2.0 ** gains_density)
    if gains_density:
        rgb = balance.apply_gains(rgb, np.full(3, g, np.float32))
    out = np.empty_like(rgb)
    for y0 in range(0, rgb.shape[0], STRIP_ROWS):
        out[y0:y0 + STRIP_ROWS] = lutmod.apply_trilinear(lattice, rgb[y0:y0 + STRIP_ROWS])
    del rgb
    if rotate_k % 4:
        from . import orient
        out = orient.apply_rotation(out, rotate_k)
    imgio.write_image(dst, out, bit_depth=16, icc_bytes=img.icc_bytes, exif_bytes=img.exif_bytes)
    del out
    return {"file": src.name, "gains": [round(float(g), 4)] * 3, "seconds": round(time.time() - t0, 1)}


def grade_folder(
    in_dir: Path,
    out_dir: Path,
    cube_path: Path,
    balance_mode: str = balance.DEFAULT_MODE,
    balance_strength: float = 1.0,
    workers: int | None = None,
    quality: int = 95,
    resume: bool = False,
    image_area: tuple | None = None,
    cache_dir: Path | None = None,
    limit: int | None = None,
    density: float = 0.0,
    rotations: dict | None = None,
    bits: int = 8,
    crop_edge: float | None = None,
    log=print,
) -> list[dict]:
    lattice, title = lutmod.read_cube(cube_path)
    stats = lutmod.read_stats_sidecar(cube_path) or {}
    anchors = stats.get("balance_anchors")
    if balance_mode != "off" and not anchors:
        log(f"[apply] WARNING: --balance {balance_mode} requested but {cube_path.name} has no .stats.json anchors; no balancing will be applied")

    files = [f for f in imgio.list_images(in_dir) if f.suffix.lower() in imgio.GRADEABLE_EXTS]
    if not files:
        raise RuntimeError(f"no scans found in {in_dir} "
                           f"(looked for {', '.join(sorted(imgio.GRADEABLE_EXTS))})")
    out_dir.mkdir(parents=True, exist_ok=True)

    area_frac = image_area
    if area_frac is None and balance_mode != "off":
        area_frac = rebate.roll_area_fractions(files, cache_dir=cache_dir)

    todo = []
    for f in files:
        dst = (out_dir / f.name).with_suffix(imgio.output_suffix(bits))
        if resume and dst.exists():
            continue
        todo.append((f, dst))
    if limit is not None:
        todo = todo[:limit]

    if workers is None:
        workers = default_workers()
    if bits >= 16:
        # a 16-bit frame is decoded whole (float32 in, uint16 out), not in strips
        workers = max(1, min(workers, 2))
    log(
        f"[apply] {len(todo)} of {len(files)} frames with '{title}' "
        f"(balance={balance_mode}, workers={workers}, est. peak ~{workers * PEAK_GB_PER_WORKER:.1f} GB "
        f"of {ram_gb():.0f} GB RAM)"
    )

    results = []
    with cf.ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {
            ex.submit(grade_one, src, dst, lattice, anchors, balance_mode,
                      balance_strength, area_frac, quality, density,
                      (rotations or {}).get(src.name, {}).get("k", 0), bits, crop_edge): src
            for src, dst in todo
        }
        done = 0
        for fut in cf.as_completed(futs):
            r = fut.result()
            results.append(r)
            done += 1
            log(f"  [{done}/{len(todo)}] {r['file']} gains={r['gains']} ({r['seconds']}s)")
    if crop_edge is not None and results:
        n_centred = sum(1 for r in results if r.get("crop") == "centred")
        n_nofit = sum(1 for r in results if r.get("crop") == "nofit")
        log(f"[crop] {len(results) - n_nofit} cropped, {n_centred} re-centred, {n_nofit} left whole")
    return results
