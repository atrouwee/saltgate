# LUT changelog

| LUT | Date | Cohort | Fitted on | Validation |
|---|---|---|---|---|
| `silbersalz-250d_v0-statistical_33.cube` | 2026-08-22 | 250D, APOLLON 14K era | Distribution match: 1 flat roll (130 frames) vs 13 graded rolls (~800 frames, 2023–2026), no pairs | Distribution report + contact sheets only — provisional, superseded by v1-paired when donations arrive |
| `silbersalz-250d_v0.2-structured_33.cube` | 2026-08-22 | 250D, APOLLON 14K era | Parametric grade (26 params) fitted to situation-matched perceptual statistics (8-cluster catalog of 700 lab frames); exposure-only balance | Judgement sheets vs lab frames of the same situation — fixes cast (a*/b* deviation ≈ 0) but loses vividness; midtones still ~7 L* lighter than the lab. Provisional. |
| *(v0.3-situational — not shipped)* | 2026-08-22 | 250D | Parametric fit against by-eye situation profiles, clean flat crops | Regressed visually (chroma collapse); v0.2 stays the provisional LUT. Statistical track frozen until pairs. |
| `silbersalz-gold200_v1-paired_33.cube` | 2026-08-23 | **Kodak Gold 200 (C-41)**, APOLLON 14K era | **27 real flat/graded pairs** (donor: Cody, rolls 057 + 067), Stage C (shared LUT + per-shot gains) | **5-fold held-out median ΔE2000 1.62, p90 2.15** (graded side from 16-bit JXL; 1.79 with 8-bit JPG). Per-shot gains tiny and roll-consistent (≈ −0.08 / +0.08 stop, R=G=B within 1%) → the lab applied one base look + per-roll density, no per-frame white balance. |
| `silbersalz-250d_v1-bridged_33.cube` | 2026-08-23 | 250D, APOLLON 14K era | Gold 200 pair LUT + 9-param statistical tone bridge fitted to the 250D archive profiles | Density now matches the lab (±3 L*); a residual lilac cast remains — not yet better than v0 by eye. Needs 250D pairs. |
