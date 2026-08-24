# Context: SILBERSALZ, 2011–2026

A dated, sourced timeline. Kept separate from the README on purpose: the project is about the photographs, not the dispute. Facts only; no names of community members; customer correspondence paraphrased.

| When | What | Source |
|---|---|---|
| 2011 | SILBERSALZ Film GmbH founded in Stuttgart (as "Herr Bergmann und Herr Bramsche Die Filmemacher GmbH"), a commercial film-production and post-production company. | German commercial register (public filings) |
| ~2018–2019 | SILBERSALZ35 launched: Kodak Vision3 motion-picture stock respooled for 35 mm stills, ECN-2 processing, scanning, graded delivery. | Kodak feature on the service; lab product pages |
| 2020–2022 | Strong growth of the still-film service; international adoption. Reviews praise the look and the flat 16-bit option for self-grading. | Kodak blog; photography press reviews |
| 2019–Aug 2022 | "Classic" scanner era: 5900 × 3800 px 8-bit JPEG (later JP2), filenames `silbersalz35_<film>_<stock>_bild_NN` — the stock written into every filename. Delivered graded. | Author's deliveries Aug 2020 – Aug 2022 |
| September 2022 | APOLLON 14K scans reach customers ("you are among the first customers to receive our revolutionary new scans … a free upgrade this week"): 14204 × 9043 px 16-bit JP2, a 4K gallery plus a full-resolution download. The first APOLLON filenames still carried the stock (`NNN_FULL_<film>_<stock>`); from November 2022 the stock slot reads `XXX` and the stock moves to the info-card frame at the start of each roll. | Lab delivery e-mail of 29 Sep 2022; author's deliveries |
| 2023 | APOLLON delivery as the standard: paid full-resolution upgrade (`HIGH` / `FULL`), 16-bit JP2/JXL + 8-bit JPG, Display P3. | Customer delivery e-mails; lab product pages |
| late 2023 | Customers told of high demand and significant delays. | Customer correspondence |
| 2024 | Company relocates to Goerzallee 311, Berlin; "SILBERSALZ CINELAB" branding. | Commercial register; lab website |
| Feb 2026 | LUMIÈRE motion-picture scanner unveiled at Berlinale. | Lab announcement |
| June 2026 | Lab warns customers of "massive shortages in staff". | Customer correspondence |
| July–Aug 2026 | A customer group (>130 people) forms to retrieve negatives and files; films picked up in person; many deliveries arrive as flat ("raw colour") scans with grading "to follow". | Community group (paraphrased) |
| Aug 2026 | This project starts: first 27 Gold 200 flat/graded pairs contributed; Vision3 pairs sought. | This repository |

What this timeline does *not* say: anything about the company's finances, legal status or intentions. The evidence available to us is consistent with demand outgrowing an operation — not with a lack of care for the work.

## What the deliveries looked like, era by era

Useful if you are digging through an old download and trying to work out what you are holding. Established from the lab's own filenames, info-card frames and correspondence rather than from memory.

| Era | Files | Where the stock is written |
|---|---|---|
| ~2019 – Aug 2022 ("classic" scanner) | 5900 × 3800 px, 8-bit JPEG, later JP2 | **in every filename**: `silbersalz35_<film>_<stock>_bild_NN` |
| Sep 2022 – Oct 2022 (first APOLLON deliveries) | ≈14200 × 9000 px, 16-bit JP2, sRGB-tagged | still in the filename: `NNN_FULL_<film>_<stock>` |
| Nov 2022 onward | ≈14000 px wide, 16-bit JP2/JXL + 8-bit JPG, **Display P3**-tagged | filename stock slot reads `XXX`; the real stock is on the **info-card frame** at the start of the roll, whose third line lists the films of that order (e.g. `250-250-050-050`) |

Three things worth knowing, each of which cost us time:

- **The APOLLON scanner reached customers in September 2022**, not 2023 — the delivery mail for the first one says "you are among the first customers to receive our revolutionary new scans".
- **The 2022 JP2s are sRGB-tagged; from 2023 they are Display P3.** Mixing the two eras without converting will shift your colours.
- **The `_Exported.json` sidecar is not a stock record.** Its `Film_1_Stock` field reads `XXX` on every delivery we have seen.

Two further notes for anyone matching files to stocks: the lab also processed film that was not its own when sent in without a voucher, so a "Silbersalz scan" is not automatically a Silbersalz stock; and the tungsten "125T Special / Edition Vivid" is a Fuji stock rather than a Kodak Vision3 one, in the lab's own words.

