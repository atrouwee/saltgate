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

**Caveat.** ΔE is a per-pixel colour distance. It does not weigh *where* the error is — a ΔE of 3 on a face matters more than 3 in a shadow — which is why results are also checked per material (skin, sky, foliage, neutrals) and by eye against real lab frames of the same kind of scene.

## What pairs buy — measured

Bare-LUT median ΔE2000 against the lab's graded files, from `scripts/learning_curve.py` on the pairs we have (Gold 200: 27 pairs over two rolls; 500T: 5 pairs, one roll). Donated images are never published; only these statistics are.

### 500T: what one donation did (same frames, before vs after)

The walkthrough's fallback before the donation was the 250D proxy (nearest daylight stock). Scored on the donor's five scenes against the lab's own graded files:

| frame | 250D proxy (before) | pair-fitted 500T, frame held out (after) |
|---|---|---|
| candle-lit interior | 23.9 | 2.0 |
| sunset lake | 23.1 | 2.1 |
| mixed-light interior | 17.0 | 2.5 |
| daylight market | 18.1 | 8.6* |
| dusk campfire | 21.2 | 3.3 |
| **median** | **21.2 — a different grade** | **2.5 — trained eye, side by side** |

\* the lab lifted black on this frame by ~0.04 linear — a per-frame decision a shared LUT cannot know.

### Gold 200: error vs number of pairs (27 pairs, two rolls)

Fit on k pairs from one roll, test on frames the fit never saw. Averaged over both directions:

| pairs fitted (one roll) | same roll, remaining frames | the other roll |
|---|---|---|
| 1 | 1.5 | 4.4 |
| 2 | 1.4 | 4.4 |
| 3 | 1.1 | 4.4 |
| 5 | 1.1 | 4.2 |
| 8 | 1.0 | 4.3 |
| 13 | 1.0 | 4.2 |

(One LUT fitted on all 27 pairs across both rolls sits at 2.3 on its own training frames — it splits the difference between the two rolls' densities.)

### What this means

1. **The first three pairs of a roll do almost all the work.** By three pairs the rest of that roll is predicted at the measurement floor (~1.0). Frames four onward barely move anything.
2. **New rolls beat new frames.** The ~4.3 against the other roll does not budge from 1 pair to 13 — it is the lab's per-roll density decision, and only pairs from more rolls can teach it (and eventually let a per-roll density estimator remove it).
3. **Never borrow across balance families.** Daylight ↔ tungsten measured 20+ ΔE (the 500T "before" above); the two daylight stocks (250D ↔ 50D proxies) sit 3.3 apart. The walkthrough borrows only within a family.
4. **What this predicts for 250D and 50D:** their proxies today are statistical stand-ins — the honest expectation from the 500T experiment is that the first donated roll of 250D pairs takes it to ~2–3 on held-out frames of similar scenes, and a second roll starts closing the roll-to-roll gap. Ten frames across two rolls beat thirty frames from one.

### The ask, in one line

**3+ pairs per roll, 2+ rolls per stock, untouched lab files.** That is the whole recipe.

