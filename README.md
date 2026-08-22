# silbersalz-look

**Community reverse-engineering of the SILBERSALZ35 film-lab color grade.**

[SILBERSALZ35](https://silbersalz35.com/) sold Kodak Vision3 motion-picture film for stills, developed it in true ECN-2 chemistry, scanned it, and applied a beloved signature cinematic grade. The lab has ceased operating; many of us received our final rolls as **flat (ungraded) scans only** — the graded versions will never come.

This project rebuilds that grade, openly:

- **`.cube` 3D LUTs** that transform Silbersalz flat scans toward the lab's look — usable in DaVinci Resolve, Lightroom (as profiles), Capture One, RawTherapee, Affinity, etc.
- **`sslook`**, a Python CLI that batch-grades whole folders of flat JPGs, with optional per-shot auto exposure/white-balance (the lab balanced every shot).
- The **full method and fitting code**, so anyone can reproduce, improve, or extend it.

## How the grade is recovered

Two tracks, honestly labeled:

| Track | LUT tag | Data it needs | Fidelity |
|---|---|---|---|
| **A — paired fit** | `v1-paired` | Donated **flat + graded pairs** of the same frame | High: it directly fits the lab's transform, separating the shared base look from per-shot balancing |
| **B — statistical fallback** | `v0-statistical` | Flat scans + a library of graded-only deliveries | Provisional: matches color *distributions*, not the actual transform. Superseded by v1 as pairs arrive |

**We need pair donations!** If you have any frame delivered both flat and graded, see [docs/DONATING_PAIRS.md](docs/DONATING_PAIRS.md). Around 10 pairs per film stock is enough to fit a solid LUT.

## LUT coverage

| Stock | classic era (pre-APOLLON) | APOLLON 14K era |
|---|---|---|
| 250D | — | `v0-statistical`, `v0.2-structured` (both provisional) |
| 50D | *needs pairs* | *needs pairs* |
| 200T | *needs pairs* | *needs pairs* |
| 500T | *needs pairs* | *needs pairs* |
| 125 Special | *needs pairs* | *needs pairs* |

The lab switched scanners around 2021 (older deliveries are lower-resolution); the grade may differ between eras, so LUTs are fitted per *(stock, era)* cohort and merged only when a cross-era holdout test shows the grades actually agree.

## LUT conventions (important)

- **Input**: the flat scan's code values, normalized to [0,1], as delivered — Silbersalz flats are tagged **Display P3**. Apply the LUT directly to the untouched flat scan.
- **Output**: graded display code values, **Display P3** (the same tagging the lab's own graded JPEGs carried).
- Domain `[0,1]³`, size 33³, trilinear interpolation. Every `.cube` ships with a `.stats.json` sidecar recording provenance, fit metrics, and the auto-balance anchors `sslook` uses.
- In Resolve: set the clip/timeline color space to Display P3 (or work device-agnostically and judge by eye). In Lightroom/Capture One, apply to the original flat JPG without prior adjustments.

Because the LUT is fitted on the *unmodified* flat scans, apply it **before** any of your own corrections.

## Quickstart

```bash
python3 -m venv .venv && .venv/bin/pip install -e .

# grade a folder of flat scans with the current 250D LUT
.venv/bin/sslook apply \
  --lut luts/silbersalz-250d_v0-statistical_33.cube \
  --in  /path/to/your/flat/scans \
  --balance exposure        # default; --density -0.3 for a denser print

# outputs land in a sibling folder Graded_<version>/, ICC+EXIF preserved
```

Other commands:

```bash
sslook validate-pair pairs/<you>/<pair-name>/   # QA a donated pair (alignment check)
sslook fit-pairs --pairs pairs/ --stock 250d --out luts/silbersalz-250d_v1-paired_33.cube --holdout
sslook fit-statistical --flats FLATDIR --archive GRADEDDIR --out luts/...cube
sslook report --in FLATDIR --compare GRADEDDIR --out report/
```

## Situation catalog (analysis tool)

`scripts/build_catalog.py` clusters a graded archive into *situations* (k-means on perceptual + layout features) and writes per-cluster contact sheets and grade fingerprints (`report/catalog/`). It showed that the lab **preserved scene color temperature** (golden scenes stay warm, overcast stays cool) and corrected mostly exposure per shot — which is why `sslook apply` defaults to `--balance exposure` (scalar gain, clamped to ±0.4 stop, soft highlight knee) rather than gray-world white balance. `sslook fit-structured` fits a parametric grade against those situation profiles (`v0.2-structured`).

## Caveats of the current no-pair LUTs (`v0-statistical`, `v0.2-structured`)

- It was fitted by matching the color distribution of one flat roll against ~700 graded frames from 13 past deliveries (all 250D, APOLLON era). Distribution matching cannot capture hue-dependent nonlinearities of the true grade, and scene-content differences between rolls bias it despite robust trimming.
- Treat it as "the Silbersalz *character*", not "the Silbersalz *grade*". The paired fit will replace it.

## Contributing

- **Most valuable**: donate flat/graded pairs — [docs/DONATING_PAIRS.md](docs/DONATING_PAIRS.md).
- Method details and math: [docs/METHOD.md](docs/METHOD.md).
- Issues and PRs welcome — especially per-app LUT installation notes and validation on your own rolls.

## License

MIT for all code and LUTs. Donated images are used only for fitting and are never redistributed — see the privacy note in the donation guide.

## Auto-rotation (run first)

Scans are delivered in film-strip orientation; portrait and upside-down frames are not rotated. Decide rotations once per roll, review, then grade:

```bash
.venv/bin/python scripts/auto_rotate.py --in FLATDIR --out rotations.json --sheet review.jpg
.venv/bin/python scripts/auto_rotate.py --set rotations.json 0026=2 0044=1    # fix flagged frames (k = 90° CCW steps)
.venv/bin/sslook apply --lut luts/...cube --in FLATDIR --rotations rotations.json
```

Cues: a rotation probe on spatially pooled ResNet-50 features (self-supervised on the graded archive) fused with a YuNet face detector (`models/`). Confident decisions are ~90% right; low-confidence frames are marked red on the review sheet for a manual `--set`.
