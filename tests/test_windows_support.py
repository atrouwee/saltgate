"""Windows is a supported platform, and these are the places it used not to be.

A user on Windows reported the second line of the README — `saltgate` — as an
unrecognised command, because there was no installer that could put it there:
`install.sh` needs `curl` and `sh`, which Windows has neither of. That is the
headline, and it is fixed by `install.ps1`; the rest of this file pins the
smaller things behind it, each of which was a silent degradation rather than an
error message:

  * key reading fell back to `None` off termios, which does not only lose the
    arrow keys — it is also the flag that switches OFF the rotation review, the
    one question the tool cannot answer for itself;
  * `ram_gb()` was macOS-only, so every PC graded a whole roll on one worker;
  * the installer and the code have to agree about where the 47 MB orientation
    model lives, in three files that cannot import each other.
"""
import os
import sys
import types
from pathlib import Path

import pytest

from silbersalz_look import apply as ap
from silbersalz_look import orient, wizard

ROOT = Path(__file__).resolve().parents[1]


# ── the installers ─────────────────────────────────────────────────────────
def test_windows_has_an_installer_of_its_own():
    ps1 = (ROOT / "install.ps1").read_text()
    assert "uv tool install" in ps1
    assert "saltgate" in ps1


def test_readme_sends_windows_to_it():
    readme = (ROOT / "README.md").read_text()
    assert "install.ps1" in readme, "the Windows install line is what was missing"
    assert "install.sh" in readme


def test_both_installers_fetch_the_model_the_code_expects():
    """Three files, no shared import: a changed URL or digest must fail here.

    The installer downloads the backbone so the walkthrough never has to stop
    and ask. If its digest drifts from orient.BACKBONE the download is thrown
    away as tampered — quietly, on someone else's machine.
    """
    for name in ("install.sh", "install.ps1"):
        text = (ROOT / name).read_text()
        assert orient.BACKBONE["sha256"] in text, f"{name} has a stale checksum"
        assert orient.BACKBONE["url"] in text, f"{name} has a stale model URL"
        assert orient.BACKBONE["file"] in text


def test_installers_write_where_the_model_cache_reads():
    sh, ps1 = (ROOT / "install.sh").read_text(), (ROOT / "install.ps1").read_text()
    assert "Library/Application Support/saltgate/models" in sh   # the darwin branch
    assert ".saltgate/models" in sh                              # everything else
    assert r".saltgate\models" in ps1
    # and the code agrees, whichever platform is asking
    assert orient.model_cache_dir().parts[-2:] == (
        "saltgate" if sys.platform == "darwin" else ".saltgate", "models")


def test_an_update_without_git_still_has_something_to_install_from():
    """Most Windows machines have no git, and `git+https://` cannot work without one."""
    assert wizard.install_spec() == wizard.GIT_SPEC or wizard.install_spec() == wizard.ZIP_SPEC
    assert wizard.ZIP_SPEC.endswith(".zip")


# ── keys ───────────────────────────────────────────────────────────────────
class _FakeMsvcrt(types.ModuleType):
    def __init__(self, keys):
        super().__init__("msvcrt")
        self._keys = list(keys)

    def getwch(self):
        return self._keys.pop(0)


@pytest.mark.parametrize("keys, expected", [
    (["\x00", "H"], "up"),        # arrows arrive as a lead byte and a letter
    (["\xe0", "P"], "down"),      # ...from either of two lead bytes
    (["\xe0", "K"], "up"),        # left folds into up, as it does on POSIX
    (["\xe0", "M"], "down"),
    (["\r"], "enter"),
    (["\x1b"], "quit"),
    (["q"], "quit"),
    (["\x03"], "quit"),
    (["3"], "3"),                 # typing the number still chooses
])
def test_windows_keys_speak_the_same_vocabulary(keys, expected):
    assert wizard._read_key(_FakeMsvcrt(keys)) == expected


def test_a_windows_terminal_counts_as_a_keyboard(monkeypatch):
    """`_keyboard() is None` also turns the rotation review off — so on Windows
    it used to take away the review as well as the arrow keys."""
    monkeypatch.setitem(sys.modules, "msvcrt", _FakeMsvcrt([]))
    monkeypatch.setattr(wizard.os, "name", "nt")
    monkeypatch.setattr(wizard.sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(wizard, "interactive", lambda: True)
    assert wizard._keyboard() is not None


def test_a_pipe_is_still_not_a_keyboard(monkeypatch):
    """The smoke test, CI and anyone scripting this answer with a pipe."""
    monkeypatch.setattr(wizard, "interactive", lambda: False)
    assert wizard._keyboard() is None


# ── paths ──────────────────────────────────────────────────────────────────
def test_a_dragged_folder_loses_its_quotes():
    assert wizard.clean_path('  "/Users/me/My Scans" ') == Path("/Users/me/My Scans")


def test_backslashes_are_a_separator_on_windows_not_an_escape(monkeypatch):
    """A POSIX shell escapes spaces with backslashes; Windows builds paths with them.

    Unescaping on Windows turned `C:\\Users\\me\\ scans` into a folder that does
    not exist, and the walkthrough answered "I can't find a folder there".
    """
    monkeypatch.setattr(wizard.os, "name", "nt")
    assert str(wizard.clean_path(r"C:\Users\me\ scans")) == r"C:\Users\me\ scans"
    monkeypatch.setattr(wizard.os, "name", "posix")
    assert str(wizard.clean_path(r"/Users/me/My\ Scans")) == "/Users/me/My Scans"


def test_short_uses_this_platforms_separator():
    assert wizard.short(Path("a") / "b" / "c" / "d" / "e") == "…" + os.sep + os.sep.join(("c", "d", "e"))


# ── how many workers a machine gets ────────────────────────────────────────
def test_ram_is_measured_not_assumed():
    assert ap.ram_gb() > 0


def test_a_big_machine_gets_more_than_one_worker(monkeypatch):
    """`sysctl` exists only on macOS, so this used to read 8 GB everywhere else
    — and (8 - 6) // 2.5 == 0 pinned every PC and every Linux box to one worker."""
    monkeypatch.setattr(ap, "ram_gb", lambda: 32.0)
    monkeypatch.setattr(ap.os, "cpu_count", lambda: 12)
    assert ap.default_workers() == 4


def test_a_small_machine_still_gets_one(monkeypatch):
    monkeypatch.setattr(ap, "ram_gb", lambda: 8.0)
    monkeypatch.setattr(ap.os, "cpu_count", lambda: 2)
    assert ap.default_workers() == 1


# ── the small courtesies must never be preconditions ───────────────────────
def test_enabling_ansi_is_safe_everywhere():
    wizard.enable_ansi()          # a no-op off Windows, and never raises on it


def test_staying_awake_is_optional():
    release = wizard.stay_awake()
    release()                     # grading goes ahead whether or not this worked


def test_the_machine_has_a_name_in_every_sentence():
    assert wizard.machine_word() and wizard.file_manager()
