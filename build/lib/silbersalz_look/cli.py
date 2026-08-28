"""sslook command-line interface."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import imgio


def _cmd_looks(args) -> int:
    from . import looks as looksmod

    for stock, candidates in looksmod.LOOKS.items():
        print(f"\n{stock}")
        for i, look in enumerate(candidates):
            mark = "  (default)" if i == 0 else ""
            print(f"  {stock}:{look.key}{mark}")
            print(f"      {look.cube}  [{look.status}]")
            print(f"      {look.note}")
    print("\nuse one with:  saltgate apply --look 250d:paired --in <folder>")
    return 0


def _cmd_apply(args) -> int:
    from . import apply as ap
    from . import looks as looksmod

    in_dir = Path(args.in_dir)
    if args.look:
        stock, key = looksmod.parse_spec(args.look)
        if not looksmod.looks_for(stock):
            print(f"no looks for stock '{stock}' — run `saltgate looks` to see what exists")
            return 1
        look = looksmod.resolve(stock, key)
        if key and look.key != key:
            print(f"no look '{key}' for {stock} — run `saltgate looks` to see what exists")
            return 1
        lut_path = looksmod.cube_path(look)
    else:
        lut_path = Path(args.lut)
    version = lut_path.stem.split("_")[1] if "_" in lut_path.stem else lut_path.stem
    out_dir = Path(args.out) if args.out else in_dir.parent / f"Graded_{version}"
    if out_dir.exists() and any(out_dir.iterdir()) and not (args.resume or args.force):
        print(f"refusing to write into non-empty {out_dir} (use --resume or --force)")
        return 1
    image_area = None
    if args.image_area:
        image_area = tuple(float(v) for v in args.image_area.split(","))
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    # A 150 MP frame takes ~30 s, so nothing is reported until the first one
    # lands. Spin until then, and hand over to grade_folder's own per-frame
    # lines once they start arriving -- a static banner reads as a hang.
    from .wizard import Spinner

    import time as _t
    t0 = _t.time()
    spin = Spinner("starting the workers", indent="", tail=lambda: f"{int(_t.time() - t0)} s").start()

    def log(msg: str) -> None:
        # grade_folder's first call is its banner, not a finished frame; stopping
        # there would kill the spinner exactly when the 30 s wait begins. Pause
        # only long enough to print, then keep moving -- frames land ~30 s apart.
        spin.stop()
        print(msg, flush=True)
        if msg.startswith("  ["):
            spin.label = "grading"
        spin.start()

    try:
        ap.grade_folder(
            in_dir,
            out_dir,
            lut_path,
            balance_mode=args.balance,
            balance_strength=args.balance_strength,
            workers=args.workers,
            quality=args.quality,
            resume=args.resume,
            image_area=image_area,
            cache_dir=cache,
            limit=args.limit,
            density=args.density,
            bits=args.bits,
            rotations=(__import__("json").loads(Path(args.rotations).read_text()) if args.rotations else None),
            log=log,
        )
    finally:
        spin.stop()
    print(f"[done] graded frames in {out_dir}")
    return 0


def _cmd_export_hald(args) -> int:
    from . import lut

    from .wizard import Spinner

    with Spinner(f"rendering the grid from {Path(args.lut).name}", indent=""):
        lattice, _ = lut.read_cube(args.lut)
        out = Path(args.out) if args.out else Path(args.lut).with_suffix(".hald.png")
        lut.write_hald_png(out, lattice, level=args.level)
    print(f"[done] wrote {out}")
    return 0


def _has_research() -> bool:
    """Is the research half of the package installed?

    The public distribution ships only the runtime modules, so the fitting and
    donor-intake subcommands register only where their code actually exists.
    Same cli.py in both repos; no forked copy to keep in sync.
    """
    import importlib.util
    return importlib.util.find_spec("silbersalz_look.research_cli") is not None


def main(argv=None) -> int:
    from .wizard import enable_ansi

    enable_ansi()     # Windows: the spinners and the receipt are ANSI too
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv == ["wizard"]:
        from . import wizard
        return wizard.run()
    if argv[0] == "fix-rotation":
        from . import wizard
        return wizard.fix_rotation(argv[1:])
    ap = argparse.ArgumentParser(prog="saltgate", description="SALTGATE tools (run with no arguments for the guided walkthrough)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("apply", help="batch-apply a LUT to a folder of flat JPGs")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--lut", help="path to a .cube file")
    src.add_argument("--look", help="a shipped look, e.g. 250d:paired (see `saltgate looks`)")
    p.add_argument("--in", dest="in_dir", required=True)
    p.add_argument("--out", default=None)
    p.add_argument("--balance", default="off",
                   choices=["off", "exposure", "auto", "wb-only"],
                   help="off (default, recommended): apply the LUT as-is. Automatic per-frame balancing measured WORSE than the bare LUT on real pairs; experimental modes kept for manual use")
    p.add_argument("--balance-strength", type=float, default=1.0)
    p.add_argument("--workers", type=int, default=None, help="default: RAM-aware")
    p.add_argument("--limit", type=int, default=None, help="grade at most N frames")
    p.add_argument("--rotations", default=None, help="rotations.json from scripts/auto_rotate.py")
    p.add_argument("--density", type=float, default=0.0,
                   help="print density in stops (negative = denser/darker), e.g. -0.3")
    p.add_argument("--quality", type=int, default=95)
    p.add_argument("--bits", type=int, default=8, choices=[8, 16],
                   help="16 writes lossless 16-bit TIFF; only meaningful from 16-bit input (jxl/jp2/tif)")
    p.add_argument("--image-area", default=None, help="fx,fy,fw,fh fractions")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--cache", default="cache")
    p.set_defaults(fn=_cmd_apply)

    p = sub.add_parser("looks", help="list the shipped looks, per film stock")
    p.set_defaults(fn=_cmd_looks)

    p = sub.add_parser("export-hald", help="export a .cube as a HaldCLUT PNG (RawTherapee, G'MIC)")
    p.add_argument("lut"); p.add_argument("--out", default=None); p.add_argument("--level", type=int, default=8)
    p.set_defaults(fn=_cmd_export_hald)

    if _has_research():
        from . import research_cli
        research_cli.add_parsers(sub)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
