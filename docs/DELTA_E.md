# How close is close? ΔE2000, and what pairs buy

Every fidelity number in this project is a **ΔE2000** — the standard way to put a number on "how different do these two colours *look* to a person". This page explains the scale, how we measure it, and what the measurements say about the value of donated pairs.

## The idea

Take two colours and convert each into CIELAB, a colour space built so that equal distances mean roughly equal *perceived* differences: L\* is lightness (0–100), a\* runs green ↔ red, b\* runs blue ↔ yellow. ΔE is the distance between the two points. The original 1976 version was the plain straight-line distance; the 2000 revision (CIEDE2000) corrects for where the eye is more or less sensitive — it tones down differences in saturated colours, sharpens them in neutrals, and handles blues and lightness more faithfully. A ruler calibrated to human vision rather than to code values.

## The scale

| ΔE2000 | what it means |
|---|---|
| < 1 | not distinguishable, even side by side |
| 1–2 | visible only in a direct A/B on the same screen |
| 2–4 | a trained eye sees it side by side; nobody notices on its own |
| 4–8 | clearly a different rendering — typically a density or cast shift |
| > 10 | a different grade; the casual viewer sees it |

## How we measure it

For each donated pair we have the lab's graded file and our render of the same flat scan, aligned pixel for pixel. We compute ΔE2000 at each sampled pixel and take the **median per frame**, then the median over frames. Median rather than mean, so a few bad pixels (edges, grain, JPEG blocks) don't dominate. The floor is about **1.0** — what is left from JPEG compression and alignment, not from the LUT.

Numbers are always for the **bare LUT**, applied as-is, with no per-frame correction — what you actually get. Where we quote a held-out number, the frame (or the whole roll) was excluded from the fit that is being scored, so the number is a prediction, not a memory.

**Caveat.** ΔE is a per-pixel colour distance. It does not weigh *where* the error is — a ΔE of 3 on a face matters more than 3 in a shadow — which is why the benchmark also reports per material (skin, sky, foliage, neutrals; [`docs/FINDINGS.md`](FINDINGS.md)) and why a visual judgement sheet stays in the loop.

## What pairs buy — measured

Bare-LUT median ΔE2000 against the lab's graded files, from `scripts/learning_curve.py` on the pairs we have (Gold 200: 27 pairs over two rolls; 500T: 5 pairs, one roll). Donated images are never published; only these statistics are.

_Run in progress — table follows._
