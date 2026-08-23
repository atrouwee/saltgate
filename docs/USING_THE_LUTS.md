# Using the LUTs in your app

Every LUT here expects the **untouched flat scan** from the lab (the `…_RAW_COLOR.jpg` / "raw" delivery, tagged Display P3) and outputs the graded look in Display P3. Apply the LUT **before** any adjustment of your own; do exposure, crop and retouching afterwards.

Pick the LUT for your **film stock** (see the coverage table in the README). A LUT for another stock will look wrong — the lab's raw files differ per stock.

## Which files do I have?

- `…_HIGH_RAW_COLOR.jpg` (or a delivery simply called *raw* / *flat*): the ungraded scan — **this is the LUT's input.**
- `…_HIGH.jpg`, `….jxl`, `….jp2`: the lab's **graded** deliveries (full-res "HIGH"/"FULL", or the 4K gallery version). Nothing to apply; but if you have a graded *and* a raw file of the same frame, you hold a pair — see the donation guide.
- `.dng` straight from the scanner: a different, earlier stage of the pipeline; the LUTs don't apply to it. Please open an issue with a sample so we can look.

## Capture One
Recent versions import `.cube` files as Styles: Adjustments → Styles and Presets → ⋯ → *Import LUT…* (menu wording varies by version). Apply on the untouched flat. Capture One applies the LUT inside its own working space, so expect a very slight difference from the reference renders in this repo.

## DaVinci Resolve (free)
1. Download the `.cube` → Project Settings → Color Management → *Open LUT Folder* → drop it there → *Update Lists*.
2. Import your flat JPGs into the media pool; on the clip, Color page → LUTs panel → right-click the LUT → *Apply LUT to Current Node*.
3. Set the timeline/output colour space to **Display P3** (or export with the P3 profile) so the colours match the lab's own files.

## Photoshop
Layer → New Adjustment Layer → **Color Lookup** → *3DLUT File* → *Load 3D LUT…* → choose the `.cube`. Keep the document in its embedded Display P3 profile.

## Affinity Photo
Adjustments → **LUT** → *Load LUT* → choose the `.cube`.

## Lightroom Classic / Lightroom / Camera Raw
Lightroom cannot load `.cube` directly; it needs a **profile** (`.xmp`) with the LUT embedded. Create it once in Adobe Camera Raw (Photoshop):
1. Open any of your flat JPGs in Camera Raw (Photoshop → File → Open, or Filter → Camera Raw Filter).
2. In the *Presets* panel, **Alt/Option-click** the *Create Preset* (+) button → the hidden **Create Profile** dialog opens.
3. Name it (e.g. `Open Silbersalz · 250D`), set Profile Group, tick **Look Table** → *Load 3D LUT* → choose the `.cube`; leave other adjustments off.
4. Save → it appears in Lightroom's *Profile Browser* (restart Lightroom if needed). Apply it to the flat JPG with all sliders at zero.
We publish the resulting `.xmp` profiles here as community members create and verify them (see `profiles/`).

## darktable
*lut 3D* module → load the `.cube`; set the module's colour space to match (the LUT is in display code values, not linear).

## RawTherapee
RawTherapee uses **HaldCLUT** PNGs: `sslook export-hald LUT.cube` writes one; put it in your HaldCLUT folder and pick it in *Film Simulation*.

## Command line (any OS, batch, with auto-rotation)
```bash
pipx install open-silbersalz              # or: pip install open-silbersalz
sslook apply --lut silbersalz-gold200_v1-paired_33.cube --in ~/scans/roll12
```
Output goes to a sibling folder `Graded_<version>/`, ICC and EXIF preserved (JPEG q95, 4:4:4; 16-bit output is on the roadmap). Add `--rotations rotations.json` after running `scripts/auto_rotate.py` for content-based upright orientation.

## Expectations
- Fidelity is stated per LUT in the README (held-out ΔE2000 against the lab's own graded files where pairs exist; "provisional" where they don't).
- The lab also applied a small per-roll density offset and set black per frame (≈ ±0.04 stop). Nothing here reproduces that automatically — we measured that automatic per-frame balancing makes results *worse* than the bare LUT — so `sslook apply` and a host app give the same result. Nudge exposure to taste.
