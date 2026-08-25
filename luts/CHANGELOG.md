# LUT changelog

What ships, what it was built from, and how it was checked. Fidelity is the **bare LUT** measured against the lab's own graded files on frames the fit never saw — see [`docs/DELTA_E.md`](../docs/DELTA_E.md) for the scale.

| LUT | Date | Stock / era | Built from | How close |
|---|---|---|---|---|
| `silbersalz-gold200_v1-paired_33.cube` | 2026-08-23 | **Kodak Gold 200** (C-41), APOLLON era | 27 real flat/graded pairs from one donor across two rolls (thanks Cody), 16-bit files on both sides | Held out a whole roll at a time: median ΔE2000 **4.1** (p90 4.7). Within a roll it already reaches **1.7**. The roll-to-roll gap is the lab's own per-roll density decision, which no shared LUT can know — more rolls close it. **Beta** |
| `silbersalz-500t_v1.1-paired_33.cube` | 2026-08-24 | **Vision3 500T**, APOLLON era | 5 real flat/graded pairs from one donor, one roll (thanks Faraz), 16-bit files on both sides | Held out one frame at a time: median ΔE2000 **1.5** (p90 6.1 — one frame where the lab lifted black by hand). Black point within 0.1 L\* of the lab. Improves on v1 after a correction to how per-frame density and black are separated from the shared transform. **Beta** — a second roll is what makes it *validated* |
| `silbersalz-250d_v0.1-statistical_33.cube` | 2026-08-23 | **Vision3 250D**, APOLLON era | No pairs. Approximated from 16 graded 250D rolls (~650 frames, Sep 2022 – Mar 2026), with the stock of every roll established from the lab's own filenames and info cards | **Proxy** — matches the lab's tone and cast, but renders skin ~8 L\* lighter and skies ~7 L\* darker. Replaces the earlier v0, which had 72 frames of a different stock mixed into its references |
| `silbersalz-250d_v1-paired_33.cube` | 2026-08-25 | **Vision3 250D**, APOLLON era | 6 real flat/graded pairs (donor: Sebastian, three rolls). | Held out a whole roll at a time: median ΔE2000 **3.7** (p90 7.7), against **8.1** for the statistical proxy on the same held-out pixels. **Offered as a second look, not a replacement:** all six pairs were shot indoors, and in open daylight this renders cooler and greener than the proxy. The walkthrough shows both on your own frames and asks. |
| `silbersalz-50d_v0-statistical_33.cube` | 2026-08-23 | **Vision3 50D**, APOLLON era | No pairs. Approximated from 3 graded 50D rolls (~102 frames) | **Proxy, thin** — two of the three rolls are from one holiday, so its references are narrow. Before this, 50D borrowed the 250D proxy |

**Choosing.** Where a stock has two entries above, the walkthrough renders both on six of your own frames and asks which you prefer; `saltgate looks` lists them and `saltgate apply --look 250d:paired` picks one on the command line. The answer is stored on your machine only.

**Not shipped:** several experimental 250D LUTs were fitted and rejected — a parametric variant that fixed the colour cast but lost vividness, and a bridge from the Gold 200 pair-LUT that left a lilac cast. Neither beat the proxy by eye. The statistical track is frozen until real 250D pairs arrive.

**Borrowing.** 200T and the tungsten 125T Special have no pairs and no LUT of their own; the walkthrough uses the 500T LUT for them, because they share its tungsten balance. Nothing ever borrows across balance families — daylight and tungsten stocks measured more than 20 ΔE apart.
