"""sslook command-line interface."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import imgio


def _cmd_apply(args) -> int:
    from . import apply as ap

    in_dir = Path(args.in_dir)
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
        rotations=(__import__("json").loads(Path(args.rotations).read_text()) if args.rotations else None),
    )
    print(f"[done] graded frames in {out_dir}")
    return 0


def _cmd_export_hald(args) -> int:
    from . import lut

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
    p.add_argument("--lut", required=True)
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
    p.add_argument("--image-area", default=None, help="fx,fy,fw,fh fractions")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--cache", default="cache")
    p.set_defaults(fn=_cmd_apply)

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
