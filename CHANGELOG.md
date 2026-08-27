# What changed

Written for photographers, not from the commit log. Versions marked **renders
change** will make your files look different; everything else is the tool
around them.

Full technical history: `luts/CHANGELOG.md` for the LUTs themselves.

## 0.3.0 — the film edge, cropped like the lab did · **renders change**
Your graded frames are now **cropped** by default — just outside the picture,
keeping the camera gate's rounded corners and a sliver of film. The lab did
the same before grading: an uncropped grade renders the unexposed rebate near
white (L\* 77–96 measured, against the lab's own L\* 6 borders). The walkthrough
previews all three treatments on your own frames — just outside · film edge ·
whole scan — and whichever you pick, the crop is **centred on the film itself**:
35 mm rarely sits square on the strip, so a scan-centred crop leaves a dark bar
down one edge. After grading it reports what happened ("88 cropped, 61
re-centred, 5 left whole"). Choose *whole scan* and nothing is cropped at all.

A third 250D look joins the picker: **cooled hybrid** — the default with its
colour cooled toward the maintainer's 668-frame graded archive, the amount set
by measurement rather than by eye. Same fidelity to the 22 real pairs as the
default; about 1 ΔE apart, all colour. The archive-matched look's description
now carries its exact provenance: 668 frames, 16 rolls, Sep 2022–Mar 2026, all
APOLLON-era; 180 frames on a Canonet QL17, 488 on a Contax T2.

Also: a new hero image rendered with the shipped default, and a new line under
the name — *we couldn't ask the lab, so we asked the frames.*

## 0.2.1 — check the frames it wasn't sure about
Auto-rotation is right about 95% of the time, and it knows which frames it is
unsure of: on a test roll, five of the six it got wrong were among the six it
was least confident about.

So it now asks. The handful it is unsure of get graded small and on their own —
a second or two, not the full run — into `check-upright.jpg`, and you answer one
question per frame: already upright, turn left, turn right, upside down. The
full roll grades the whole time you are looking, and each question shows how far
it has got. Anything you turn is re-graded at the end.

Nothing about how your files look has changed.

## 0.2.0 — 250D fitted on the lab's own files · **renders change**
The default 250D LUT changes. Your 250D frames will look different: warmer and
lighter than before, and less green in the neutrals.

It is fitted on 22 real flat/graded pairs from two photographers across four
rolls — and most of those pairs are now the lab's original 16-bit files instead
of re-compressed JPEGs. That mostly buys a cleaner *measurement*: given its own
exposure per frame the fit now reads 0.8 ΔE2000 against the lab, which the
previous version could not show because its own reference files carried
compression error. The rendering itself moved very little.

If it reads too warm on your roll, the previous look is still there: pick
**archive-matched** in the walkthrough, or `saltgate apply --look 250d:proxy`.
Neither is provably right for a roll we have no pairs from, which is why the
walkthrough shows you both on your own frames before writing anything.

Also: every prompt now moves with ← → ↑ ↓ and explains each option as you land
on it, and density is a scale you slide rather than a list of numbers.

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
