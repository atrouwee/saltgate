"""Nothing the walkthrough does may happen in silence.

The contract is structural rather than remembered: work sits inside a named
`step(...)`, and a watchdog puts that name on screen if the step goes quiet.
These tests pin both halves — that every step in the wizard actually names
itself, and that the watchdog speaks when (and only when) it should.
"""
import ast
import time
from pathlib import Path

import pytest

from silbersalz_look import wizard


@pytest.fixture(autouse=True)
def fast_and_visible(monkeypatch):
    """A terminal, and a watchdog impatient enough to test in milliseconds."""
    monkeypatch.setattr(wizard, "interactive", lambda: True)
    monkeypatch.setattr(wizard, "QUIET_AFTER", 0.05)
    monkeypatch.setattr(wizard, "TICK", 0.02)
    wizard.SILENCE = wizard.Silence()
    yield
    wizard.SILENCE.stop()


# --- the label contract ---------------------------------------------------

def _step_calls():
    """Every `step(...)` call in wizard.py — the bare function, not Wedge.step."""
    tree = ast.parse(Path(wizard.__file__).read_text(encoding="utf-8"))
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "step"]


def test_the_wizard_actually_uses_steps():
    assert len(_step_calls()) >= 10, "the walkthrough stopped declaring what it is doing"


def test_every_step_names_what_it_is_doing():
    for call in _step_calls():
        assert call.args, f"step() with no label at line {call.lineno}"
        arg = call.args[0]
        if isinstance(arg, ast.Constant):
            assert isinstance(arg.value, str) and arg.value.strip(), f"empty label at line {arg.lineno}"
        elif isinstance(arg, ast.JoinedStr):          # f-string
            assert arg.values, f"empty f-string label at line {arg.lineno}"
        else:
            raise AssertionError(f"step() label at line {arg.lineno} is not a literal — it may be empty at runtime")


def test_an_empty_label_is_refused_at_runtime():
    with pytest.raises(ValueError):
        with wizard.step(""):
            pass


# --- the watchdog ---------------------------------------------------------

def test_it_speaks_when_a_step_goes_quiet(capsys):
    wizard.SILENCE.start()
    with wizard.step("measuring the roll"):
        time.sleep(0.3)
    assert "measuring the roll" in capsys.readouterr().out


def test_it_stays_quiet_through_a_fast_step(capsys):
    wizard.SILENCE.start()
    with wizard.step("something instant"):
        pass
    time.sleep(0.15)
    assert "something instant" not in capsys.readouterr().out


def test_a_better_indicator_suspends_it(capsys):
    """A progress bar or a spinner already says more than the watchdog can."""
    wizard.SILENCE.start()
    with wizard.step("grading"):
        with wizard.SILENCE.indicator():
            time.sleep(0.3)
    assert "grading" not in capsys.readouterr().out


def test_waiting_for_a_person_is_not_silence(capsys, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _="": (time.sleep(0.3), "y")[1])
    wizard.SILENCE.start()
    with wizard.step("waiting on the film question"):
        assert wizard.prompt() == "y"
    assert "waiting on the film question" not in capsys.readouterr().out


def test_an_abandoned_indicator_does_not_mute_the_rest_of_the_run(capsys):
    """A bar left open by an error must not silence every later step."""
    wizard.SILENCE.start()
    with wizard.step("the step that leaks"):
        wizard.SILENCE.indicator().__enter__()      # entered, never exited
    capsys.readouterr()
    with wizard.step("the step after it"):
        time.sleep(0.3)
    assert "the step after it" in capsys.readouterr().out


def test_steps_nest_and_the_inner_label_wins(capsys):
    wizard.SILENCE.start()
    with wizard.step("outer"):
        with wizard.step("inner"):
            time.sleep(0.25)
        out = capsys.readouterr().out
    assert "inner" in out and "outer" not in out


def test_nothing_is_drawn_when_output_is_piped(capsys, monkeypatch):
    monkeypatch.setattr(wizard, "interactive", lambda: False)
    s = wizard.Silence()
    s.start()
    with s.step("a log file does not want a spinner"):
        time.sleep(0.2)
    s.stop()
    assert "a log file" not in capsys.readouterr().out


# --- the bar --------------------------------------------------------------

def test_wedge_holds_an_indicator_until_it_completes():
    w = wizard.Wedge(2)
    assert wizard.SILENCE.indicators == 1
    w.step()
    assert wizard.SILENCE.indicators == 1, "still working — the watchdog must stay down"
    w.step()
    assert wizard.SILENCE.indicators == 0, "finished — the watchdog may speak again"


def test_wedge_close_is_idempotent():
    w = wizard.Wedge(1)
    w.step()
    w.close()
    w.close()
    assert wizard.SILENCE.indicators == 0


def test_wedge_edge_moves_while_the_count_stands_still(capsys):
    """A 30-second frame must not look like a hang."""
    w = wizard.Wedge(10)
    capsys.readouterr()
    frames = set()
    for _ in range(4):
        w.phase += 1
        w._draw()
        frames.add(capsys.readouterr().out)
    w.close()
    assert len(frames) > 1, "the bar drew the same thing every time"


# --- motion, not just presence --------------------------------------------

def _frames(text):
    """Distinct redraws in a carriage-return animated line."""
    return [f for f in text.split("\r") if f.strip()]


def _glyphs(text, label):
    """Which spinner characters were actually drawn next to this label."""
    return {c for f in _frames(text) if label in f for c in f if c in wizard.SPIN}


def test_the_watchdog_glyph_actually_moves(capsys):
    """A label that sits still reads as a hang; the glyph has to cycle."""
    wizard.SILENCE.start()
    with wizard.step("thinking"):
        time.sleep(0.4)
    assert len(_glyphs(capsys.readouterr().out, "thinking")) > 1, \
        "the watchdog drew the same glyph every tick"


def test_spinner_moves_and_clears(capsys):
    with wizard.Spinner("working"):
        time.sleep(0.4)
    out = capsys.readouterr().out
    assert len(_glyphs(out, "working")) > 1, "spinner drew the same glyph every tick"
    assert out.rstrip().endswith(" " * 10) or out.endswith("\r"), "spinner left its line behind"


def test_spinner_restarts_after_being_stopped_to_print(capsys):
    """The CLI stops the spinner to print a finished frame, then resumes."""
    s = wizard.Spinner("grading", indent="")
    s.start(); time.sleep(0.2); s.stop()
    capsys.readouterr()
    s.start(); time.sleep(0.2); s.stop()
    assert len(_frames(capsys.readouterr().out)) > 1, "spinner did not come back"


def test_spinner_tail_lets_a_counter_move(capsys):
    ticks = iter(["1 s", "2 s", "3 s", "4 s", "5 s", "6 s"])
    s = wizard.Spinner("updating", tail=lambda: next(ticks, "6 s"))
    s.start(); time.sleep(0.4); s.stop()
    out = capsys.readouterr().out
    assert "1 s" in out and "2 s" in out


def test_busy_and_spinner_while_use_the_one_moving_primitive():
    """Two spinner implementations drift; there is only one."""
    src = Path(wizard.__file__).read_text(encoding="utf-8")
    body = src[src.index("def busy("):src.index("def open_file(")]
    assert body.count("Spinner(") == 2
    assert "while not stop.is_set()" not in body, "a second hand-rolled spin loop came back"


def test_every_animated_line_goes_through_the_screen_lock():
    """Two threads writing escape sequences to one line garble it."""
    src = Path(wizard.__file__).read_text(encoding="utf-8")
    animated = src[src.index("class Spinner"):src.index("# ── helpers")]
    for line in animated.splitlines():
        if "print(" in line and "\\r" in line:
            assert "paint(" in line or "with SCREEN" in src[:src.index(line)][-400:], \
                f"unlocked animated write: {line.strip()}"
