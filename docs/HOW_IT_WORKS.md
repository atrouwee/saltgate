# How it works

A short version, so you can judge the LUTs rather than take them on faith. If you only read one thing, read [how close the results are](DELTA_E.md).

## The problem

SILBERSALZ scanned your negatives and then graded them — the "raw colour" flat scan and the finished file are the same pixels with a colour transform in between. When the lab stopped, a lot of people were left holding flats and no way to finish them.

That transform is what this project reconstructs.

## What we do

**Where we have pairs.** Some photographers still have both files for the same frame: the flat scan *and* the lab's graded version. Those pairs are the evidence. We line the two files up, compare the colours across the whole frame, and fit a single colour transform that takes one to the other — then bake it into a standard `.cube` LUT.

**Checking it honestly.** A transform that reproduces the frames it was fitted on proves nothing. So we hold frames back, apply the LUT to those, and compare against the lab's own output for them. Every fidelity number published here is measured that way — on frames the fit never saw. The scale and the current per-stock numbers are in [DELTA_E.md](DELTA_E.md).

**Where we have no pairs.** For some stocks nobody has sent pairs yet. There we approximate: match the colour distribution of flat scans to a large body of the lab's graded output for that stock. That produces something with the right character but not the actual grade, and it is labelled **proxy** everywhere it appears — never presented as measured.

## What the lab actually did (and what we therefore don't do)

Measuring real pairs told us the lab's pipeline was simpler than folklore suggested: a global colour transform, a small density decision per roll, black set per frame, and no per-shot white balance. Nothing spatial — no sharpening, no vignetting, no local masks.

That is why a single LUT per stock is the right shape for this, and why **automatic per-frame balancing is off by default**: we tried it, measured it, and it made results markedly worse than applying the LUT as-is. The lab's own per-frame corrections were far smaller than any estimator could infer from a flat scan alone.

## Why each film stock needs its own pairs

Different negatives have different curves, so the flat-to-graded transform genuinely differs between them. We measured how far apart: two daylight Vision3 stocks render about 3 ΔE apart, but daylight versus tungsten is over 20 — a different grade entirely. So a LUT is only borrowed *within* a balance family, never across, and a stock is only finished when it has pairs of its own.

## Where the limits are

- Fidelity is stated for the **bare LUT**, applied as-is. That is what you get.
- The remaining error on a roll the fit never saw is mostly the lab's per-roll density choice, which no shared LUT can know. More rolls close it; more frames from the same roll do not.
- Every number is a colour distance, which does not care *where* the error falls. A shift on skin matters more than the same shift in a shadow, so results are also checked per material and by eye against real lab frames.

## Help finish the rest

Pairs are the whole bottleneck. If the lab ever delivered your frames both flat and graded, [that is what turns a proxy into a measured LUT](DONATING_PAIRS.md) — for everyone shooting that stock, not just you.

Full method, measurements and research tooling are kept in a private working repo; the LUTs, the numbers behind them and this tool are the public output of that work.
