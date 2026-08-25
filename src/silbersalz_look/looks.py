"""Which LUTs a photographer is actually offered, per film stock.

This is a CURATED list, not the full history. A LUT that is simply worse (a
crushed-shadow fit, a colour cast) is not a choice and is not listed; those stay
in the project's research record.

Where a second entry exists it is there for a REASON that is not "it might be
better". 250D keeps the old statistical proxy so a project begun on it can be
finished on it — the walkthrough renders both on the photographer's own frames
and lets them choose, and says plainly which one the measurements favour.

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
        Look("paired", "pair-fitted", "silbersalz-250d_v2-paired_33.cube", "BETA",
             "fitted from 22 real flat/graded pairs — two photographers, four rolls, daylight "
             "through tungsten. on the donated frames it lands within ~2 ΔE of the lab once each "
             "frame gets its own exposure, which is the limit an 8-bit scan can even measure."),
        Look("proxy", "v0.1 · the old stand-in", "silbersalz-250d_v0.1-statistical_33.cube", "PROXY",
             "what saltgate shipped before any real 250D pairs existed — estimated from ~700 graded "
             "frames rather than measured. kept so a project started on it can be finished on it; "
             "it is not the better LUT."),
        # v1-paired is gone: fitted on six indoor/warm pairs, visibly cyan-green in
        # daylight, and v2 supersedes it on the same donor's frames. Old release
        # zips still carry it for anyone re-grading an older project.
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
