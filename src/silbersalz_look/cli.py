"""sslook command-line interface."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import imgio


def _cmd_fit_statistical(args) -> int:
    from . import fit_statistical as fs
    from . import lut

    flat_files = [
        f
        for f in imgio.list_images(args.flats)
        if f.suffix.lower() in (".jpg", ".jpeg")
    ]
    archive = {}
    for d in args.archive:
        d = Path(d)
        files = imgio.list_images(d)
        jpg_sub = d / "_JPG"
        if jpg_sub.is_dir():
            files = imgio.list_images(jpg_sub)
        # prefer 8-bit jpegs (fast decode, identical grade to the 16-bit files)
        jpegs = [f for f in files if f.suffix.lower() in (".jpg", ".jpeg")]
        archive[d.name] = jpegs or files
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    lattice, stats = fs.fit_statistical(
        flat_files, archive, cache, beta=args.beta, size=args.size
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    lut.write_cube(out, lattice, out.stem, comments={"track": "v0-statistical"})
    lut.write_stats_sidecar(out, stats)
    print(f"[done] wrote {out} and {out.with_suffix('.stats.json')}")
    return 0


def _archive_files(dirs) -> list[Path]:
    out = []
    for d in dirs:
        d = Path(d)
        sub = d / "_JPG"
        files = imgio.list_images(sub if sub.is_dir() else d)
        jpegs = [f for f in files if f.suffix.lower() in (".jpg", ".jpeg")]
        out += jpegs or files
    return out


def _cmd_fit_structured(args) -> int:
    from . import fit_structured as fst
    from . import lut

    flat_files = [f for f in imgio.list_images(args.flats) if f.suffix.lower() in (".jpg", ".jpeg")]
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    proxy = lut.read_cube(args.proxy)[0] if args.proxy else None
    lattice, stats, _ = fst.fit_structured(
        flat_files, _archive_files(args.archive), cache,
        proxy_lattice=proxy, catalog_dir=Path(args.catalog) if args.catalog else None,
        situations_json=Path(args.situations) if args.situations else None,
        profiles_json=Path(args.profiles) if args.profiles else None,
        max_flats=args.max_flats,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    lut.write_cube(out, lattice, out.stem, comments={"track": "v0.2-structured"})
    lut.write_stats_sidecar(out, stats)
    print(f"[done] wrote {out} and {out.with_suffix('.stats.json')}")
    return 0


def _cmd_fit_adapter(args) -> int:
    from . import fit_adapter as fa
    from . import lut

    flat_files = [f for f in imgio.list_images(args.flats) if f.suffix.lower() in (".jpg", ".jpeg")]
    cache = Path(args.cache); cache.mkdir(parents=True, exist_ok=True)
    lattice, stats = fa.fit_adapter(flat_files, Path(args.lut), cache, Path(args.labels), Path(args.profiles), max_flats=args.max_flats)
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    lut.write_cube(out, lattice, out.stem, comments={"track": "v1-bridged", "base": Path(args.lut).name})
    lut.write_stats_sidecar(out, stats)
    print(f"[done] wrote {out}")
    return 0


def _cmd_fit_pairs(args) -> int:
    from . import fit_pairs as fp

    pairs = fp.discover_pairs(Path(args.pairs))
    if not pairs:
        print("no pairs found (expect pairs/<donor>/<name>/{flat.*,graded.*})")
        return 1
    print(f"[pairs] discovered {len(pairs)}")
    for p in pairs:
        fp.prepare_pair(p)

    live = [p for p in pairs if p.excluded is None]
    if args.stock != "all":
        live = [p for p in live if p.stock in (args.stock, "unknown")]
    if args.era != "auto":
        live = [p for p in live if p.era == args.era]
    if not live:
        print("no usable pairs after filtering")
        return 1

    lattice, stats = fp.fit_cohort(live, size=args.size, stage=args.stage)
    if args.holdout:
        stats["holdout_median_dE2000"] = fp.holdout_report(live, size=args.size)
    from . import pair_report
    stats["residuals"] = pair_report.residual_report(live, lattice)
    print("[report] residual anatomy (training pairs):\n" + pair_report.format_report(stats["residuals"]))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fp.save_fit(out, lattice, stats, out.stem)
    sheet_path = pair_report.fit_check_sheet(live, lattice, Path("report/pairs") / f"fitcheck_{out.stem}.jpg")
    print(f"[report] fit-check sheet: {sheet_path}")
    print(f"[done] wrote {out} and {out.with_suffix('.stats.json')}")
    return 0


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


def _cmd_report(args) -> int:
    from . import report as rp

    in_dir = Path(args.in_dir)
    out_dir = Path(args.out)
    flats = [f for f in imgio.list_images(in_dir) if f.suffix.lower() in (".jpg", ".jpeg")]
    rp.contact_sheet(flats, out_dir / "contact_flat.jpg", cols=args.cols)
    if args.compare:
        comp = [
            f
            for f in imgio.list_images(args.compare)
            if f.suffix.lower() in (".jpg", ".jpeg")
        ]
        rp.contact_sheet(comp, out_dir / "contact_graded.jpg", cols=args.cols)
        rp.before_after_sheet(flats, comp, out_dir / "before_after.jpg")
    print(f"[done] report in {out_dir}")
    return 0


def _cmd_export_hald(args) -> int:
    from . import lut

    lattice, _ = lut.read_cube(args.lut)
    out = Path(args.out) if args.out else Path(args.lut).with_suffix(".hald.png")
    lut.write_hald_png(out, lattice, level=args.level)
    print(f"[done] wrote {out}")
    return 0


def _cmd_validate_pair(args) -> int:
    from . import fit_pairs as fp

    pair_dir = Path(args.pair_dir)
    flats = [f for f in imgio.list_images(pair_dir) if f.stem.lower().startswith("flat")]
    grades = [f for f in imgio.list_images(pair_dir) if f.stem.lower().startswith("graded")]
    if len(flats) != 1 or len(grades) != 1:
        print(f"INVALID: need exactly one flat.* and one graded.* in {pair_dir}")
        return 1
    pair = fp.Pair(
        donor=pair_dir.parent.name,
        name=pair_dir.name,
        flat_path=flats[0],
        graded_path=grades[0],
        meta=fp._read_meta(pair_dir),
    )
    fp.prepare_pair(pair)
    if pair.excluded:
        print(f"VERDICT: REJECTED - {pair.excluded}")
        return 1
    print(
        f"VERDICT: OK - NCC {pair.align_info['ncc']}, scale {pair.align_info['scale']}, "
        f"{len(pair.x):,} samples, cohort=({pair.stock}, {pair.era})"
    )
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv == ["wizard"]:
        from . import wizard
        return wizard.run()
    ap = argparse.ArgumentParser(prog="saltgate", description="SALTGATE tools (run with no arguments for the guided walkthrough)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("fit-statistical", help="fit v0 LUT by distribution matching")
    p.add_argument("--flats", required=True)
    p.add_argument("--archive", action="append", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--beta", type=float, default=0.7)
    p.add_argument("--size", type=int, default=33)
    p.add_argument("--cache", default="cache")
    p.set_defaults(fn=_cmd_fit_statistical)

    p = sub.add_parser("fit-structured", help="fit parametric grade to situation-matched statistics")
    p.add_argument("--flats", required=True)
    p.add_argument("--archive", action="append", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--catalog", default=None, help="dir with catalog_model.npz + cluster_profiles.npy")
    p.add_argument("--proxy", default=None, help="LUT used to render flats for situation classification")
    p.add_argument("--situations", default=None, help="labels_all.json (by-eye situation labels)")
    p.add_argument("--profiles", default=None, help="situation_profiles.json")
    p.add_argument("--max-flats", type=int, default=60)
    p.add_argument("--cache", default="cache")
    p.set_defaults(fn=_cmd_fit_structured)

    p = sub.add_parser("fit-adapter", help="bridge a pairless stock to a pair-fitted LUT of another stock")
    p.add_argument("--flats", required=True); p.add_argument("--lut", required=True)
    p.add_argument("--labels", required=True); p.add_argument("--profiles", required=True)
    p.add_argument("--out", required=True); p.add_argument("--max-flats", type=int, default=70)
    p.add_argument("--cache", default="cache")
    p.set_defaults(fn=_cmd_fit_adapter)

    p = sub.add_parser("fit-pairs", help="fit LUT from donated flat/graded pairs")
    p.add_argument("--pairs", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--stock", default="all",
                   help="50d|200t|250d|500t|125special|all")
    p.add_argument("--era", default="auto", help="auto|apollon14k|classic")
    p.add_argument("--stage", default="auto", help="auto|A|B|C")
    p.add_argument("--holdout", action="store_true")
    p.add_argument("--size", type=int, default=33)
    p.set_defaults(fn=_cmd_fit_pairs)

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

    p = sub.add_parser("report", help="contact sheets / before-after grids")
    p.add_argument("--in", dest="in_dir", required=True)
    p.add_argument("--compare", default=None)
    p.add_argument("--out", default="report")
    p.add_argument("--cols", type=int, default=6)
    p.set_defaults(fn=_cmd_report)

    p = sub.add_parser("export-hald", help="export a .cube as a HaldCLUT PNG (RawTherapee, G'MIC)")
    p.add_argument("lut"); p.add_argument("--out", default=None); p.add_argument("--level", type=int, default=8)
    p.set_defaults(fn=_cmd_export_hald)

    p = sub.add_parser("validate-pair", help="QA one donated pair directory")
    p.add_argument("pair_dir")
    p.set_defaults(fn=_cmd_validate_pair)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
