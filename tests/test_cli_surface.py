"""The public/private CLI boundary.

The public distribution ships only the runtime modules; the research
subcommands must disappear cleanly rather than crash on import. `cli.py` is
byte-identical in both repos, so this contract is what keeps them honest.
"""
import argparse

import pytest

from silbersalz_look import cli


RUNTIME_COMMANDS = {"apply", "export-hald", "looks"}
RESEARCH_COMMANDS = {
    "fit-statistical", "fit-structured", "fit-adapter", "fit-pairs",
    "report", "validate-pair", "donor-report",
}


@pytest.mark.skipif(not cli._has_research(), reason="research half not installed (public build)")
def test_research_commands_present_when_installed(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    out = capsys.readouterr().out
    for c in RUNTIME_COMMANDS | RESEARCH_COMMANDS:
        assert c in out, f"{c} missing from --help"


def test_help_matches_whichever_half_is_installed(capsys):
    """The same test file ships to both repos; --help must match reality."""
    has = cli._has_research()
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    out = capsys.readouterr().out
    for c in RUNTIME_COMMANDS:
        assert c in out, f"runtime command {c} missing"
    for c in RESEARCH_COMMANDS:
        assert (c in out) is has, f"{c} presence ({c in out}) disagrees with _has_research() ({has})"


def test_public_build_exposes_only_runtime_commands(capsys, monkeypatch):
    # simulate the published package, where the research modules are absent
    monkeypatch.setattr(cli, "_has_research", lambda: False)
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    out = capsys.readouterr().out
    for c in RUNTIME_COMMANDS:
        assert c in out, f"runtime command {c} vanished"
    for c in RESEARCH_COMMANDS:
        assert c not in out, f"research command {c} leaked into the public CLI"


def test_public_build_rejects_a_research_command(capsys, monkeypatch):
    monkeypatch.setattr(cli, "_has_research", lambda: False)
    with pytest.raises(SystemExit) as e:
        cli.main(["fit-pairs", "--pairs", "x", "--out", "y.cube"])
    assert e.value.code != 0, "a research command must be a clean argparse error, not a crash"
    assert "invalid choice" in capsys.readouterr().err


def test_has_research_reflects_module_presence():
    import importlib.util
    present = importlib.util.find_spec("silbersalz_look.research_cli") is not None
    assert cli._has_research() is present


def test_runtime_parsers_are_registered_without_importing_research(monkeypatch):
    """Building the public parser must not import any research module."""
    import builtins
    forbidden = {"silbersalz_look.research_cli"}
    real_import = builtins.__import__
    seen = []

    def watch(name, *a, **kw):
        seen.append(name)
        return real_import(name, *a, **kw)

    monkeypatch.setattr(cli, "_has_research", lambda: False)
    monkeypatch.setattr(builtins, "__import__", watch)
    try:
        with pytest.raises(SystemExit):
            cli.main(["--help"])
    finally:
        monkeypatch.setattr(builtins, "__import__", real_import)
    leaked = forbidden & set(seen)
    assert not leaked, f"public parser imported the research half: {leaked}"
