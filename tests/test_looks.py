"""The look registry is a promise: every key it advertises must load.

A stale entry here is worse than a missing feature — the walkthrough offers the
choice, the photographer picks it, and grading dies on a FileNotFoundError after
they have already waited through the preview.
"""
import pytest

from silbersalz_look import looks as looksmod, lut


def test_every_look_points_at_a_cube_that_exists_and_parses():
    for stock, candidates in looksmod.LOOKS.items():
        for look in candidates:
            path = looksmod.cube_path(look)
            assert path.exists(), f"{stock}:{look.key} -> {path} is missing"
            lattice, _ = lut.read_cube(path)
            assert lattice.shape == (33, 33, 33, 3)


def test_keys_are_unique_within_a_stock():
    for stock, candidates in looksmod.LOOKS.items():
        keys = [c.key for c in candidates]
        assert len(keys) == len(set(keys)), f"{stock} has duplicate look keys: {keys}"


def test_every_stock_has_a_default_and_it_is_the_first_entry():
    for stock, candidates in looksmod.LOOKS.items():
        assert candidates, f"{stock} has no looks at all"
        assert looksmod.default_look(stock) is candidates[0]
        assert looksmod.resolve(stock) is candidates[0]


def test_status_words_are_ones_the_walkthrough_can_render():
    from silbersalz_look import wizard
    for candidates in looksmod.LOOKS.values():
        for look in candidates:
            assert look.status in wizard.READINESS


@pytest.mark.parametrize("bad", ["nope", "", "PROXY", "250d:proxy"])
def test_unknown_key_falls_back_to_the_default_rather_than_raising(bad):
    """A key can outlive its LUT — an old saltgate.json, a remembered
    preference, a retired cube. None of those may break someone's install."""
    assert looksmod.resolve("250d", bad) is looksmod.default_look("250d")


def test_unknown_stock_has_no_looks_and_does_not_raise():
    assert looksmod.looks_for("kodachrome") == []


@pytest.mark.parametrize("spec,expect", [
    ("250d:paired", ("250d", "paired")),
    ("250d", ("250d", None)),
    ("250D:PAIRED".lower(), ("250d", "paired")),
    (" 500t : v1 ", ("500t", "v1")),
])
def test_parse_spec(spec, expect):
    assert looksmod.parse_spec(spec) == expect


def test_wizard_default_view_agrees_with_the_registry():
    """wizard.LUTS is a derived view; if it drifts, the film step and the look
    step would disagree about what the default is."""
    from silbersalz_look import wizard
    for stock, (cube, status, note) in wizard.LUTS.items():
        d = looksmod.default_look(stock)
        assert (cube, status, note) == (d.cube, d.status, d.note)
