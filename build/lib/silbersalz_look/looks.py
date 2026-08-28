"""Which LUTs a photographer is actually offered, per film stock.

This is a CURATED list, not the full history. A LUT that is simply worse (a
crushed-shadow fit, a colour cast) is not a choice and is not listed; those stay
in the project's research record.

Where a second entry exists it is there for a REASON that is not "it might be
better". On 250D the two entries render about 10 b* apart on identical frames,
and we cannot say which is right: the pair fit reproduces a measured flat→graded
transform, the archive-matched LUT reproduces the distribution of one archive,
and comparing them needs flat/graded pairs from the roll in question. So the
walkthrough renders both on the photographer's own frames and asks.

The pair fit leads because it is the one with ground truth behind it. That is a
statement about evidence, not about taste, and the ordering should change the
moment the evidence does.

Deliberately free of heavy imports: `cli.py` reads this on every invocation and
must not pay for scipy to print --help.
"""
from __future__ import annotations

from pathlib import Path
from typing import NamedTuple


class Look(NamedTuple):
    key: str        # stable id, stored in saltgate.json and the user's config
    label: str      # what the walkthrough shows
    cube: str       # file name inside the LUT directory
    status: str     # PROXY | BETA | VALIDATED -- drives the readiness wording
    note: str       # one honest line, shown before the choice is made


# First entry per stock is the default. Order is what the menu shows.
LOOKS: dict[str, list[Look]] = {
    "250d": [
        Look("paired", "pair-fitted", "silbersalz-250d_v4-jxl_33.cube", "BETA",
             "the DEFAULT since v0.2.0. fitted from 22 real flat/graded pairs, two "
             "photographers, four rolls -- the only 250D LUT measured against what the lab "
             "actually returned rather than inferred from finished frames. against that "
             "ground truth it is by far the closest look here. caveat worth knowing: 16 of "
             "the 22 pairs are a single roll, and on the author's own rolls it renders "
             "warmer and lighter than the archive-matched LUT. which is right for YOUR roll "
             "is not something anyone can measure without pairs from it."),
        Look("hybrid", "cooled hybrid", "silbersalz-250d_hybrid-cool_33.cube", "HYBRID",
             "the default with its colour cooled toward the author's 668-frame graded archive, the "
             "amount set by measurement rather than by eye. the tone is untouched, and it holds the "
             "same fidelity to the 22 real pairs as the default. the difference is deliberate and "
             "small: about 1 dE, all of it colour, most visible as cooler large neutral fields -- "
             "skies, walls, fabric. pick it if the default reads a touch warm on your roll; the two "
             "are siblings, not rivals."),
        Look("proxy", "archive-matched", "silbersalz-250d_v0.1-statistical_33.cube", "PROXY",
             "what shipped as the default up to v0.1.26. estimated from 668 of the author's own "
             "lab-graded 250D frames -- 16 rolls, Sep 2022 to Mar 2026, all APOLLON-era deliveries, "
             "shot on two bodies: 180 frames on a Canonet QL17, 488 on a Contax T2 -- rather than "
             "measured from pairs, so it carries that archive's cameras, light and subjects with "
             "it. renders cooler and darker than both looks above. no ground truth stands behind "
             "it, but if the pair-fitted looks read too warm on your roll, this is the alternative."),
    ],
    "50d": [
        Look("proxy", "proxy", "silbersalz-50d_v0-statistical_33.cube", "PROXY",
             "a thin statistical stand-in from ~100 graded 50D frames (three rolls). same "
             "caveats as 250D, less data behind it. real 50D pairs will replace it."),
    ],
    "500t": [
        Look("v1.1", "v1.1", "silbersalz-500t_v1.1-paired_33.cube", "BETA",
             "fitted from 5 real flat/graded pairs (one donor, one roll). held-out frames "
             "within ΔE 1.5 of the lab; a second roll is needed before it can be called "
             "validated."),
        # 500T v1 is NOT listed. It is the same fit with a black point that was
        # later shown to be wrong -- every held-out number improved in v1.1 and
        # no scene favours v1, so it is superseded, not an alternative. Older
        # release zips still carry it for anyone re-grading an old project.
    ],
    "colorplus200": [
        Look("v1", "v1", "silbersalz-colorplus200_v1-paired_33.cube", "BETA",
             "fitted from 13 real flat/graded pairs (one donor, one roll -- Cairo, Jan 2026, "
             "PUSHED +2 stops, so this describes pushed ColorPlus under the lab's grade). "
             "held-out frames median dE 4.9; black point matches the lab at L* 4.1. "
             "a normal-dev roll would likely trip the mismatch check -- honestly, since "
             "no normal-dev pairs exist yet."),
    ],
    "gold200": [
        Look("v1", "v1", "silbersalz-gold200_v1-paired_33.cube", "BETA",
             "fitted from 27 real flat/graded pairs (one donor, two rolls). close to the lab "
             "on its own rolls; other rolls may want a small exposure nudge."),
    ],
}


def looks_for(stock: str) -> list[Look]:
    return LOOKS.get(stock, [])


def default_look(stock: str) -> Look:
    return LOOKS[stock][0]


def resolve(stock: str, key: str | None = None) -> Look:
    """The chosen look, or the default.

    Never raises on an unknown key. A key can outlive the LUT it named — a
    remembered preference in someone's config, or a saltgate.json from an older
    version — and a retired LUT must not break their install.
    """
    for look in looks_for(stock):
        if look.key == key:
            return look
    return default_look(stock)


def lut_dir() -> Path:
    """Where the .cube files live: the repo's luts/ when running from a checkout,
    otherwise the copies shipped inside the installed package."""
    here = Path(__file__).resolve()
    for cand in (here.parents[2] / "luts", here.parent / "luts"):
        if cand.exists():
            return cand
    return here.parents[2] / "luts"


def cube_path(look: Look) -> Path:
    return lut_dir() / look.cube


def parse_spec(spec: str) -> tuple[str, str | None]:
    """'250d:paired' -> ('250d', 'paired'); '250d' -> ('250d', None)."""
    stock, _, key = spec.partition(":")
    return stock.strip().lower(), (key.strip() or None)
