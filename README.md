<h1 align="center">open-silbersalz</h1>
<p align="center"><b>The SILBERSALZ35 lab look, reconstructed — for the flat scans the lab never got to grade.</b></p>
<p align="center">
  <a href="#get-the-look-in-5-minutes">Get the look</a> ·
  <a href="#what-exists-and-how-good-it-is">LUTs &amp; fidelity</a> ·
  <a href="#help-we-need-vision3-pairs">Donate pairs</a> ·
  <a href="#for-tinkerers-run-the-tools">Run the tools</a> ·
  <a href="docs/FINDINGS.md">What we learned</a>
</p>

<p align="center"><img src="docs/examples/hero_250d_before_after.jpg" width="900" alt="lab flat scan (left) and open-silbersalz render (right), three frames of Vision3 250D"></p>

[SILBERSALZ35](https://silbersalz35.com/) sold Kodak Vision3 cine film for stills, developed it in ECN-2, scanned it and applied a much-loved cinematic grade. The lab has closed. Many of us received our last rolls as **flat ("raw") scans only** — the graded versions will never come.

This project rebuilds the grade in the open: standard `.cube` LUTs you can drop into your editing app, a batch tool that also fixes orientation, and the method and data behind it so the community can extend it to every stock the lab scanned.

---

## Get the look in 5 minutes

1. **Find your stock** in the table below and download its `.cube` from [`luts/`](luts/) (or the latest [release](../../releases)).
2. **Apply it to the untouched flat scan** — the lab's `…_RAW_COLOR.jpg` / raw delivery, before any adjustment of your own. The LUT expects exactly that file (Display P3 tagged) and outputs the look in Display P3.
3. Follow the two-line recipe for your app in **[docs/USING_THE_LUTS.md](docs/USING_THE_LUTS.md)** — Resolve, Photoshop, Affinity, Capture One, Lightroom (via a Camera Raw profile), darktable, RawTherapee.
4. Nudge exposure ±0.1–0.2 stop to taste. The lab also set a per-roll density and a per-frame black point; the batch tool reproduces those, a LUT in a host app does not.

> **Rotation:** the lab's raw scans are delivered in film-strip orientation. The LUT doesn't care; if you want whole rolls upright automatically, see the batch tool below.

## What exists, and how good it is

Honest labels. *Paired* LUTs are fitted on real raw/graded pairs of the same frames and validated on frames the fit never saw. *Provisional* LUTs are statistical approximations — the character, not the grade.

| Stock | LUT | Status | Fidelity |
|---|---|---|---|
| **Kodak Gold 200** (C-41) | `silbersalz-gold200_v1-paired_33.cube` | **Paired** — 27 pairs (thanks Cody) | held-out median ΔE2000 **1.5** — visually indistinguishable from the lab's files |
| **Vision3 250D** | `silbersalz-250d_v0-statistical_33.cube` | Provisional — no pairs yet | matches tone and cast; renders skin ~8 L\* lighter and skies ~7 L\* darker than the lab |
| Vision3 250D | `silbersalz-250d_v1-bridged_33.cube` | Experimental — Gold look + statistical bridge | not recommended (colour cast) |
| Vision3 50D / 200T / 500T / 125 Special | — | **needs pairs** | — |
| other C-41 stocks the lab scanned | — | needs pairs | — |

The lab changed scanners around 2021; all LUTs so far are for the **APOLLON 14K era** (the 14012×10508 raw files). Full history: [`luts/CHANGELOG.md`](luts/CHANGELOG.md).

## Help: we need Vision3 pairs

One thing turns a provisional LUT into a real one: **frames the lab delivered both raw and graded**. Five to ten frames of a stock are enough for a first LUT; a mix of light (sun, shade, tungsten, flash, under/over-exposed) and some people in them help most. The graded `.jxl` beats the `.jpg` if you have it.

**[How to donate pairs →](docs/DONATING_PAIRS.md)** (what to send, how it's used, privacy — images are used only to fit the transform and are never published.)

## For tinkerers: run the tools

```bash
pipx install open-silbersalz            # core: numpy/scipy/pillow/opencv
pipx inject open-silbersalz torch torchvision   # optional: content-based auto-rotation

sslook apply --lut silbersalz-gold200_v1-paired_33.cube --in ~/scans/roll12      # grade a folder -> Graded_v1-paired/
python scripts/auto_rotate.py --in ~/scans/roll12 --out rotations.json --sheet review.jpg
sslook apply --lut ... --in ~/scans/roll12 --rotations rotations.json

sslook validate-pair pairs/you/frame017/          # check a donated pair (alignment, sample count)
sslook fit-pairs --pairs pairs --stock 250d --holdout --out luts/silbersalz-250d_v1-paired_33.cube
sslook export-hald luts/...cube                   # HaldCLUT PNG for RawTherapee / G'MIC
```

Memory-aware by default (147-MP frames are processed in strips, 2–3 workers). Pairs go in `pairs/<donor>/<name>/{flat.*, graded.*, meta.yaml}`; every fit prints a per-band / per-hue residual table and writes a labeled fit-check sheet. Details: [docs/METHOD.md](docs/METHOD.md).

## What we learned

The pairs settled what the lab actually did: a **global, colour-only transform** (no local contrast, no sharpening), **per-roll density**, a **per-frame black point**, and **no per-shot white balance** — golden light stays warm, overcast stays cool. Every stock has its own raw encoding, so LUTs don't transfer between stocks; statistics can match tone but not the colour structure of the look. The full research log with numbers: **[docs/FINDINGS.md](docs/FINDINGS.md)**.

## Credits, privacy, license

Built by Adriaan Trouwee with the Silbersalz community. Pairs: Cody (Gold 200). Donated images are used only for fitting and never redistributed; the LUTs contain no image content. Code and LUTs: **MIT**. "SILBERSALZ35" is the lab's name, used here descriptively; this is an independent community project.
