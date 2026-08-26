# What changed

Written for photographers, not from the commit log. Versions marked **renders
change** will make your files look different; everything else is the tool
around them.

Full technical history: `luts/CHANGELOG.md` for the LUTs themselves.

## 0.1.25 — arrow through it
Every choice in the walkthrough now moves with ↑↓ and confirms with Enter — film,
look, density, yes/no. Typing the number still works. The 250D look selector
explains each option as you land on it instead of stacking both explanations
above the choice. And the restart after a self-update finally says what it did,
instead of replaying "checking for updates" when it wasn't.

## 0.1.22 — 16-bit, and a density you can set
If the lab gave you 16-bit scans (`.jxl` / `.jp2`), the walkthrough can now read
them at all — it used to only accept `.jpg` and told you the 16-bit files were
the graded ones, which was wrong. Feed it 16-bit and you get 16-bit TIFF back,
or JPEG if you'd rather.

New optional step: **per-roll density**. The lab set print density per roll and
a colour transform cannot know what yours was — it is the single biggest
difference left between our render and the lab's. Five-step ladder on your own
frames, skipped with one Enter.

## 0.1.21 — 250D fitted on real pairs · **renders change**
250D stopped being an estimate. Fitted on 22 flat/graded pairs from two
photographers instead of inferred from graded frames alone.

## 0.1.23–0.1.24 — 250D back to the safer default · **renders change**
And then reverted, honestly. On the donated pairs the new fit is much closer to
the lab; on the author's own rolls it renders noticeably warmer, and we cannot
measure which is right for *your* roll without pairs from it. The estimate is
the default again; the pair-fitted version is one keypress away
(`--look 250d:paired`). Both are described for what they are.

## 0.1.19 — pick your look, and no more PyTorch
Auto-rotation used to install 529 MB of PyTorch mid-walkthrough and then restart,
losing every answer you had given. It now runs a 47 MB model through the
libraries already installed. No install, no restart.

Where a stock has more than one credible LUT, the walkthrough renders them side
by side on six of your own frames and asks.

## 0.1.18 and earlier
500T refit with a corrected black point; the first 50D LUT; the guided
walkthrough; the first Gold 200 and 250D LUTs. See the releases page.
