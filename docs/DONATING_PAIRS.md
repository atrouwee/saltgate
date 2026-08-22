# Donating flat/graded pairs

The paired fit (the real reverse-engineering) needs examples of the **same frame** delivered by SILBERSALZ35 both **flat (ungraded)** and **graded**. Roughly 10 pairs per film stock give a solid LUT; even 1–2 pairs help.

## What makes a valid pair

- Both files must come **straight from the lab** — original downloads, not re-exports.
- **Do not edit either file.** No exposure tweaks, no crops, no "just a little contrast". Hand-edited grades poison the fit (we do detect outliers, but clean data beats cleanup).
- Any of the lab's delivery formats is fine: `.jpg` / `.jpeg`, `.jp2`, `.jxl`, `.tif`.
- Resized or cropped versions are usable (our aligner handles scale/crop/rotation), but originals are best.
- Please note the **film stock** (50D / 200T / 250D / 500T / 125 Special) and roughly **when the roll was delivered** (the scanner era matters — pre-2021 scans differ from the APOLLON 14K scans).

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
stock: 250D            # 50D | 200T | 250D | 500T | 125special
era: apollon14k        # apollon14k | classic   (omit if unsure — we auto-detect)
delivery_date: 2024-08
illuminant: flash        # daylight | overcast-shade | golden-lowsun | tungsten | flash | fluorescent | mixed
exposure: normal         # under | normal | over
skin: faces-skin         # faces-skin | no-skin
notes: anything relevant (push/pull, special instructions, ...)
```

## Validating before you send

If you run the tooling yourself:

```bash
sslook validate-pair pairs/<you>/<pair-name>/
```

This aligns the two files, verifies they really are the same frame (correlation gate), and reports the sample count and detected cohort. Otherwise just send the files — we run the same check on intake.

## Privacy

Donated images are used **only** to fit the color transform. They are never committed to the repository, never republished, and never shared onward. The published LUTs contain no recoverable image content — only the color mapping. Fit reports credit donors by the name they choose (or stay anonymous — say so in `meta.yaml`).
