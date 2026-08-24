# Contributing flat/graded pairs

First step: get in touch — [open an issue](https://github.com/atrouwee/saltgate/issues) or message Adriaan in the Silbersalz community group — and I'll confirm what to send. The details below are for reference.

The paired fit (the real reverse-engineering) needs examples of the **same frame** delivered by SILBERSALZ35 both **flat (ungraded)** and **graded**. Roughly 10 pairs per film stock give a solid LUT; even 1–2 pairs help.

## Got flat scans in 2026 and graded ones later?

Several customers received their 2026 rolls as flat scans first, with graded versions promised to follow. If both arrive, you hold exactly what this project needs — the same frames raw *and* graded, from the same scan. Keep both deliveries as downloaded and get in touch.

## What makes a valid pair

- Both files must come **straight from the lab** — original downloads, not re-exports.
- **Do not edit either file.** No exposure tweaks, no crops, no "just a little contrast". Hand-edited grades poison the fit (we do detect outliers, but clean data beats cleanup).
- Any of the lab's delivery formats is fine: `.jpg` / `.jpeg`, `.jp2`, `.jxl`, `.tif`.
- Resized or cropped versions are usable (our aligner handles scale/crop/rotation), but originals are best.
- Please note the **film stock** and roughly **when the roll was delivered** (the scanner era matters — deliveries before the APOLLON scanner, i.e. before about September 2022 — 5900 × 3800 px files — differ from APOLLON-era scans).
- **Any stock the lab scanned is useful** — the Vision3 stocks (50D / 200T / 250D / 500T / 125 Special) *and* consumer C-41 films they processed (Kodak Gold, Portra, Ultramax, Fuji…). Pairs from other stocks still reveal the structure of the lab's grade, and let us test whether the house look transfers between stocks. Just tag the stock in `meta.yaml`.

## Which frames help most

The lab treated frames differently depending on the light, so variety beats volume. If you can choose, send pairs that cover different situations — ideally one or two of each:

- direct daylight / sunshine
- overcast or open shade
- golden hour / low warm sun
- indoor tungsten (warm lamps) at night
- direct **flash**
- mixed light (window + lamps)
- and at least one clearly **underexposed** and one **overexposed** frame

Frames with people (skin) are especially valuable. Note the situation in `meta.yaml` if you can (see below).

## How to structure a donation

One folder per pair:

```
pairs/
  <your-name>/
    <pair-name>/            # e.g. roll42-frame017
      flat.jpg              # the ungraded delivery (any supported extension)
      graded.jpg            # the graded delivery of the SAME frame
      meta.yaml             # optional but appreciated
```

`meta.yaml`:

```yaml
donor: your-name
stock: 250D            # 50D | 200T | 250D | 500T | 125special | gold200 | portra400 | ... (any tag)
use: true             # set false to keep a pair on disk but leave it out of fits (blank frames, test shots)
era: apollon14k        # apollon14k (Sep 2022 onward, ~14K raw files) | classic (earlier scanner, 5900 × 3800) — omit if unsure, we auto-detect
delivery_date: 2024-08
illuminant: flash        # daylight | overcast-shade | golden-lowsun | tungsten | flash | fluorescent | mixed
exposure: normal         # under | normal | over
skin: faces-skin         # faces-skin | no-skin
notes: anything relevant (push/pull, special instructions, ...)
```

## What happens when they arrive

Every pair goes through the same intake check: the two files are aligned, verified to really be the same frame, and scored for how much usable colour they contribute. You get that back as a short report — which lighting conditions and materials your frames cover, and what would help most next.

Nothing to run yourself. Send the files as the lab delivered them.

## Privacy

Donated images are used **only** to fit the colour transform. They never appear in this repository, are never published, and are never shared onward with anyone.

The originals are kept privately, on the author's own storage, for one reason: when the method improves the fits get re-run from the original files, so a LUT you helped build keeps getting better without you having to send anything again. Ask at any time and your files are deleted.

The published LUTs contain no recoverable image content — only the colour mapping — and the statistics shipped alongside them are anonymised. Fit reports credit donors by the name they choose (or stay anonymous — say so in `meta.yaml`).
