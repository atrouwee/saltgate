<h1 align="center">SALTGATE</h1>
<p align="center"><b>Open tools for finishing flat SILBERSALZ scans — and preserving a colour workflow photographers love.</b></p>
<p align="center"><i>The name is a wink. The work is sincere.</i></p>
<p align="center">
  <a href="#get-the-look-in-5-minutes">Get the look</a> ·
  <a href="#lut-status-and-evidence">LUT status &amp; evidence</a> ·
  <a href="#pass-the-salt-contribute-a-pair">Contribute a pair</a> ·
  <a href="#for-tinkerers-run-the-tools">Run the tools</a> ·
  <a href="docs/FINDINGS.md">Findings</a> ·
  <a href="docs/CONTEXT.md">Context</a>
</p>

<p align="center"><img src="docs/examples/hero_250d_before_after.jpg" width="900" alt="lab flat scan and SALTGATE render, six Vision3 250D frames across daylight, overcast, indoor and tungsten light — provisional 250D LUT"></p>

SALTGATE is an independent community project built with appreciation for what SILBERSALZ brought to still photography: motion-picture film, ECN-2 processing, exceptionally detailed scans, and a distinctive approach to colour.

Using contributed flat/graded pairs, we measure parts of that workflow and reconstruct them as open, standard colour transforms (`.cube` LUTs), plus a batch tool that also fixes orientation. The immediate goal is practical: help photographers finish flat scans of photographs that cannot be taken again.

This project is independent and unaffiliated with SILBERSALZ. It contains none of the lab's software, confidential material or proprietary files. It exists because we believe what they created is worth understanding and preserving.

## Why this exists

For a few years, [SILBERSALZ35](https://silbersalz35.com/) was the most interesting thing happening to 35 mm colour film. A small Stuttgart film-production company took Kodak's Vision3 motion-picture stock — the film Hollywood shoots on — respooled it into still cartridges, processed it in real ECN-2 chemistry, and scanned it on a scanner of their own design. What came back was unlike any lab scan most of us had seen: enormous files with the full dynamic range of the negative, and a grade drawn from motion-picture colour work — warm skin, olive greens, soft periwinkle skies, shadows that stayed open and a little warm. People shot their families, their travels and their years on it because of that look.

The lab's own success outgrew it. Demand kept rising, the scanning got more ambitious (the APOLLON 14K scanner from 2023, a move to a new Berlin lab in 2024), and by 2026 the operation could no longer keep up: staff shortages, months of silence, and hundreds of rolls waiting in a backlog. A customer group of well over a hundred people formed to get negatives back and, through a lot of goodwill on both sides, films were picked up and scans trickled out — but mostly as **flat, ungraded files**, with the grading "to follow". For many of us it never will. As one member put it, what was at stake wasn't money but *photographs that can't be taken again*.

This project is the constructive answer. We take the lab's raw scans and the graded files it did deliver over the years, and reconstruct aspects of the grade as open, standard LUTs — so anyone holding flat scans can finish their rolls toward the familiar SILBERSALZ rendering, in whatever software they use. It is not a replacement for the lab, and it takes nothing away from the people who built that look; it's a community keeping it alive for the pictures already on film. Everything here — the LUTs, the tools, the method and what we learned about how the grade actually worked — is public under MIT.

## Get the look in 5 minutes

1. **Find your stock** in the table below and download its `.cube` from [`luts/`](luts/) (or the latest [release](../../releases)).
2. **Apply it to the untouched flat scan** — the lab's `…_RAW_COLOR.jpg` / raw delivery, before any adjustment of your own. The LUT expects exactly that file (Display P3 tagged) and outputs the look in Display P3.
3. Follow the two-line recipe for your app in **[docs/USING_THE_LUTS.md](docs/USING_THE_LUTS.md)** — Capture One, DaVinci Resolve, Photoshop, Affinity, Lightroom (via a Camera Raw profile), darktable, RawTherapee.
4. Nudge exposure ±0.1–0.2 stop to taste if needed. (The lab also applied a small per-roll density and per-frame black adjustment — on the order of ±0.04 stop — which nothing here reproduces automatically; we measured that automatic balancing does more harm than good, so the tools apply the LUT as-is.)

> **Rotation:** the lab's raw scans are delivered in film-strip orientation. The LUT doesn't care; if you want whole rolls upright automatically, see the batch tool below.

## LUT status and evidence

| Label | Meaning |
|---|---|
| **Measured** | fitted from genuine flat/graded pairs and evaluated on rolls and donors the fit never saw |
| **Beta** | pair-fitted, but from too few rolls or donors for a broad claim |
| **Provisional** | statistical approximation without pairs — the character, not the grade |
| **Experimental** | research result kept for comparison; not recommended for photographs |

Fidelity is stated as the ΔE2000 of the *bare LUT* against the lab's own graded files — what you actually get — under the stated validation. "Close" means close under those conditions, not identical.

| Stock | LUT | Status | Evidence |
|---|---|---|---|
| **Kodak Gold 200** (C-41) | `silbersalz-gold200_v1-paired_33.cube` | **Beta** — 27 pairs, one donor, two rolls (thanks Cody) | leave-one-roll-out median ΔE2000 **4.1** (p90 4.7); 1.4 with an oracle per-frame density/black (upper bound); frame-level on the same rolls 1.7. The roll-to-roll gap is per-roll density the LUT can't know — more rolls and donors will close it |
| **Vision3 250D** | `silbersalz-250d_v0-statistical_33.cube` | **Provisional** — no pairs yet | matches tone and cast of the author's graded archive; renders skin ~8 L\* lighter and skies ~7 L\* darker than the lab |
| Vision3 250D | `silbersalz-250d_v1-bridged_33.cube` | **Experimental** | Gold look + statistical tone bridge; colour cast, not recommended |
| Vision3 50D / 200T / 500T / 125 Special | — | **needs pairs** | — |
| other C-41 stocks the lab scanned | — | needs pairs | — |

The lab introduced its APOLLON scanner in 2023; all LUTs so far are for **APOLLON-era raw files** (14012 × 10508 px). Earlier deliveries came from a different scanner and will need their own pairs. Full history: [`luts/CHANGELOG.md`](luts/CHANGELOG.md).

<details><summary><b>About SILBERSALZ35 (context)</b></summary>

SILBERSALZ Film GmbH was founded in 2011 as a commercial film-production company and moved into analog stills with SILBERSALZ35: Vision3 50D / 250D / 200T / 500T (plus a "125 Special"), ECN-2 processing, and scanning. From 2023 the scans came from APOLLON, a custom scanner built around a 150-MP Phase One sensor array, delivered as a 4K gallery with a paid full-resolution upgrade (the `HIGH` / `FULL` in the filenames), 16-bit JP2/JXL plus 8-bit JPG, tagged Display P3. Graded files were the default; "raw colour" flats were available on request — and became the only thing many customers got in 2026. Sources: Kodak's [feature on the service](https://www.kodak.com/en/motion/blog-post/silbersalz35/), the lab's product pages, and customers' delivery archives.
</details>

## What this is — and isn't

SALTGATE **is**:

- an independent, open-source colour-reconstruction project;
- based on measurements from contributor-owned flat/graded deliveries;
- intended to help finish existing photographs and preserve technical knowledge;
- explicit about which results are measured, beta, provisional or experimental.

SALTGATE **is not**:

- affiliated with or endorsed by SILBERSALZ;
- a copy of the lab's software or scanning pipeline;
- a publication of donated photographs or proprietary material;
- evidence that every creative decision made by the lab reduces to one LUT;
- an attempt to diminish or replace the people who created the original workflow.

## Pass the salt: contribute a pair

The most valuable contribution is not code. It is a frame that the lab delivered **both flat and graded**.

Each genuine pair replaces guesswork with measurement. A few diverse frames can start a beta; multiple rolls, photographers, lighting conditions and skin tones are what make a transform dependable. **More pairs, less guesswork.** If you received flat scans in 2026 and the lab later sends the graded versions of the same roll, keep both — that's a perfect pair set. The graded `.jxl` (16-bit) beats the `.jpg` if you have it.

**[How to contribute pairs →](docs/DONATING_PAIRS.md)** — what to send, how it's used, privacy: images are used only to fit the transform and are never published.

## For tinkerers: run the tools

```bash
pipx install saltgate                   # core: numpy/scipy/pillow/opencv
pipx inject saltgate torch torchvision   # optional: content-based auto-rotation

sslook apply --lut silbersalz-gold200_v1-paired_33.cube --in ~/scans/roll12      # grade a folder -> Graded_v1-paired/
python scripts/auto_rotate.py --in ~/scans/roll12 --out rotations.json --sheet review.jpg
sslook apply --lut ... --in ~/scans/roll12 --rotations rotations.json

sslook validate-pair pairs/you/frame017/          # check a donated pair (alignment, sample count)
sslook fit-pairs --pairs pairs --stock 250d --holdout --out luts/silbersalz-250d_v1-paired_33.cube
sslook export-hald luts/...cube                   # HaldCLUT PNG for RawTherapee / G'MIC
```

Memory-aware by default (147-MP frames are processed in strips, 2–3 workers). Pairs go in `pairs/<donor>/<name>/{flat.*, graded.*, meta.yaml}`; every fit prints a per-band / per-hue residual table and writes a labeled fit-check sheet. Details: [docs/METHOD.md](docs/METHOD.md).

## Method and findings

The pairs settled what the lab actually did: a **global, colour-only transform** (no local contrast, no sharpening), tiny **per-roll density** and **per-frame black** adjustments (≈ ±0.04 stop), and **no per-shot white balance** — golden light stays warm, overcast stays cool. Every stock has its own raw encoding, so LUTs don't transfer between stocks; statistics can match tone but not the colour structure of the look. And a lesson at our own expense: automatic per-frame "balancing" made results worse than the bare LUT, so it's off. The full research log with numbers: **[docs/FINDINGS.md](docs/FINDINGS.md)**.

## Why "SALTGATE"?

Silver salts sit at the heart of analogue photography. The "-gate" is a small community wink at an unexpectedly complicated chapter in this story.

It is not an accusation. SALTGATE is a preservation project: appreciative of the original work, honest about what can and cannot be reconstructed, and focused on helping people complete their photographs.

## With appreciation

SALTGATE would not exist without the work of the people who created SILBERSALZ35, its scanning systems and its colour workflow. Making motion-picture film and ECN-2 processing approachable for still photographers introduced many people to a way of working they would otherwise never have experienced.

This project is our way of taking that influence seriously: studying it carefully, crediting its source, and helping the resulting photographs survive an uncertain moment.

## Independence, privacy, trademark, license

Built by Adriaan Trouwee with the Silbersalz community. Pairs: Cody (Gold 200) — donated images are never published; pair identifiers in the shipped statistics are anonymised. Independent of and unaffiliated with SILBERSALZ Film GmbH; "SILBERSALZ" and "SILBERSALZ35" are the lab's names, used here descriptively. Donated images are used only for fitting and never redistributed; the LUTs contain no image content. Code and LUTs: **MIT**. Tools are distributed under the package name `saltgate` (Python package `silbersalz_look`, commands `sslook` / `saltgate`).

A dated, sourced timeline of what happened at the lab — kept separate from this README on purpose — is in [docs/CONTEXT.md](docs/CONTEXT.md).
