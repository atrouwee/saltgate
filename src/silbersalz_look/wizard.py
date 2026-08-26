"""The guided walkthrough: `saltgate` with no arguments.

Design: a darkroom "receipt". Each step leaves one amber ◆ line on screen, the
only prompt glyph is ›, options are ①②③, and progress is a density wedge
(█▓▒░). Lowercase throughout; one accent colour; no emoji; plain sentences for
errors with a log file behind them. Nothing is written next to the originals
except a new `<folder>_saltgate/` directory.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# ── palette ────────────────────────────────────────────────────────────────
AMBER, GREY, RED, BOLD, RESET = "\033[38;5;214m", "\033[38;5;245m", "\033[38;5;203m", "\033[1m", "\033[0m"
COL = 12  # receipt label column width

from . import looks as looksmod

# stock -> (LUT file, status, one-line honesty) for the DEFAULT look of each
# stock. Kept in this shape because readiness() and the film step read it;
# the full per-stock list lives in looks.py.
LUTS = {s: (v[0].cube, v[0].status, v[0].note) for s, v in looksmod.LOOKS.items()}
STOCK_CHOICES = [("250d", "Vision3 250D"), ("50d", "Vision3 50D"), ("200t", "Vision3 200T"),
                 ("500t", "Vision3 500T"), ("gold200", "Kodak Gold 200"), ("125special", "125T Special"),
                 ("other", "something else / I don't know")]
# readiness, derived from LUTS: validated (real pairs, checked on rolls the fit never saw) · beta (real pairs,
# one donor so far) · proxy (no pairs — a stand-in estimated from the author's graded archive). Vision3 stocks
# without their own LUT borrow the 250D proxy: same negative family, same scan encoding. Gold (C-41) is a
# different curve and never borrows.
READINESS = {"PROXY": "proxy", "BETA": "beta", "VALIDATED": "validated"}
BORROWS = {"200t": "500t", "125special": "500t", "other": "250d"}   # borrow within the balance family: tungsten ← 500T, daylight ← 250D
READINESS_LEGEND = ("validated = fitted on real flat + graded pairs and checked on rolls it never saw · "
                    "beta = fitted on real pairs, one donor so far\n"
                    "proxy = no pairs yet, a stand-in estimated from the author's ~700 graded lab scans · "
                    "(250D) / (500T) = borrows that stock's LUT — same balance family; daylight ↔ tungsten measured 20+ ΔE apart · more pairs, less guesswork")


def ask_stock() -> str:
    receipt("film", "which film was this roll?")
    return options(STOCK_CHOICES, tags={k: readiness(k) for k, _ in STOCK_CHOICES}, legend=READINESS_LEGEND)


def readiness(stock: str) -> str | None:
    if stock in LUTS:
        return READINESS.get(LUTS[stock][1], "proxy")
    if stock == "other":
        return None
    base = BORROWS[stock]
    return f"{readiness(base)} ({dict(STOCK_CHOICES)[base].split()[-1]})"
# What the walkthrough grades is imgio.GRADEABLE_EXTS -- one definition, shared
# with apply.grade_folder. This used to be .jpg only here, so a 16-bit RAW_COLOR
# .jxl (which the lab genuinely delivers) could not be loaded, and the empty-folder
# branch told the user that .jxl/.jp2 are the GRADED files. Both were wrong.
LAB_STOCK_CODES = {"XXX": "250d"}   # codes seen in the lab's *_Exported.json; extend as we learn them
SECONDS_PER_FRAME = 25              # rough; used for the time estimate only


# ── never silent ──────────────────────────────────────────────────────────
# The rule this enforces: every section of the walkthrough declares what it is
# doing, and if that section goes quiet the declaration appears on screen by
# itself. A slow call added later is covered because it sits inside a step —
# not because someone remembered to wrap it in a spinner.
#
# Explicit indicators are better than the watchdog whenever a count is known
# (Wedge) or a subprocess is running (spinner_while), so those suspend it.
# So does the input prompt: a person thinking is not the tool hanging.
import contextlib
import threading

QUIET_AFTER = 0.4       # seconds of silence a step is allowed before it speaks
TICK = 0.12             # how often the watchdog looks
SPIN = "░▒▓█▓▒"

# Three things animate one line each (watchdog, spinner, progress bar) and two of
# them run on their own threads. Without this they interleave inside an escape
# sequence, which looks worse than a frozen line.
SCREEN = threading.Lock()


def interactive() -> bool:
    """Animation belongs on a terminal; piped output gets the plain lines only."""
    return sys.stdout.isatty()


def paint(text: str, end: str = "") -> None:
    with SCREEN:
        print(text, end=end, flush=True)


class Spinner:
    """A moving glyph on one line, started and stopped explicitly.

    Whenever the tool is busy something must be MOVING — a label that merely
    sits there reads as a hang. This is the primitive for waits with no
    countable progress; `Wedge` covers the ones that can be counted.
    """

    def __init__(self, label: str, indent: str | None = None, tail=None):
        self.label = label
        self.indent = f"  {' ' * COL}" if indent is None else indent
        self.tail = tail          # optional callable -> extra text, e.g. elapsed seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> "Spinner":
        if self._thread is not None or not interactive():
            return self
        self._stop.clear()          # restartable: stop to print a line, start again
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def _loop(self) -> None:
        i = 0
        while not self._stop.is_set():
            extra = f" · {self.tail()}" if self.tail else ""
            paint(f"\r{self.indent}{AMBER}{SPIN[i % len(SPIN)]}{RESET} {GREY}{self.label}{extra}{RESET}   ")
            i += 1
            self._stop.wait(0.15)

    def stop(self) -> None:
        if self._thread is None:
            self._stop.set()
            return
        self._stop.set()
        self._thread.join(timeout=1.0)
        self._thread = None
        paint("\r" + " " * 90 + "\r")

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()


class Silence:
    """Watchdog that speaks the current step's label when nothing else is on screen."""

    def __init__(self):
        self.label: str | None = None
        self.indicators = 0
        self.since = time.time()
        self.showing = False
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # -- state the rest of the module updates ------------------------------
    def touch(self) -> None:
        """Something was written to the screen; the clock restarts."""
        with self._lock:
            self.since = time.time()
            if self.showing:
                self.showing = False

    @contextlib.contextmanager
    def indicator(self):
        """A better indicator is on screen (bar, spinner, prompt) — stand down."""
        with self._lock:
            self.indicators += 1
        self._erase()
        try:
            yield
        finally:
            with self._lock:
                self.indicators -= 1
                self.since = time.time()

    @contextlib.contextmanager
    def step(self, label: str):
        if not label:
            raise ValueError("a step must say what it is doing")
        with self._lock:
            previous, held = self.label, self.indicators
            self.label, self.since = label, time.time()
        try:
            yield
        finally:
            self._erase()
            with self._lock:
                # an indicator abandoned mid-step (a bar left open by an error)
                # would otherwise mute the watchdog for the rest of the run
                self.label, self.indicators, self.since = previous, held, time.time()

    # -- the thread --------------------------------------------------------
    def start(self) -> None:
        if self._thread is not None or not interactive():
            return          # piped output: a spinner would just be noise in a log
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        self._erase()

    def _erase(self) -> None:
        with self._lock:
            if not self.showing:
                return
            self.showing = False
        paint("\r" + " " * 90 + "\r")

    def _loop(self) -> None:
        i = 0
        while not self._stop.wait(TICK):
            with self._lock:
                quiet = (self.label and self.indicators <= 0
                         and time.time() - self.since > QUIET_AFTER)
                label = self.label
            if quiet:
                with self._lock:
                    self.showing = True
                paint(f"\r  {' ' * COL}{AMBER}{SPIN[i % len(SPIN)]}{RESET} {GREY}{label}{RESET}   ")
                i += 1
            else:
                self._erase()


SILENCE = Silence()


def step(label: str):
    """Declare what this section of the walkthrough is doing. Never optional."""
    return SILENCE.step(label)


# ── output primitives ─────────────────────────────────────────────────────
def out(text: str = "") -> None:
    SILENCE.touch()
    print(text, flush=True)


def receipt(label: str, text: str, tone: str = "accent") -> None:
    """◆ label   text   (the lines that stay on screen)."""
    mark = {"accent": f"{AMBER}◆{RESET}", "ok": f"{AMBER}✓{RESET}", "warn": f"{AMBER}!{RESET}", "err": f"{RED}✗{RESET}"}[tone]
    out(f"  {mark} {label.ljust(COL - 2)}{text}")


def note(text: str) -> None:
    """Secondary text under a receipt line."""
    for line in text.split("\n"):
        out(f"  {' ' * COL}{GREY}{line}{RESET}")


def prompt(default: str | None = None) -> str:
    hint = f" {GREY}[{default}]{RESET}" if default else ""
    with SILENCE.indicator():          # waiting for a person is not the tool going quiet
        try:
            ans = input(f"  {AMBER}›{RESET}{hint} ").strip()
        except (EOFError, KeyboardInterrupt):
            out(f"\n  {GREY}okay, stopping here. nothing was changed.{RESET}")
            sys.exit(0)
    return ans or (default or "")


def yes(default: bool = True) -> bool:
    """A two-option choice, driven the same way as every other one.

    The piped path is untouched: an empty line takes the default and y/n still
    work, because the smoke test, CI and anyone scripting this depend on it.
    """
    if _keyboard() is None:
        ans = prompt("Y/n" if default else "y/N").lower()
        if ans in ("y/n", "y/N".lower()):
            return default
        return default if not ans else ans.startswith("y")
    return options([("y", "yes"), ("n", "no")], per_row=2,
                   default_idx=0 if default else 1) == "y"


INVERT = "\033[7m"


def _keyboard():
    """Raw single-key reading, or None where that is not possible.

    Returns None when stdin is not a terminal -- piped answers (the smoke test,
    CI, anyone scripting the walkthrough) must keep working exactly as before,
    so arrow keys are an enhancement for people at a keyboard and never a
    requirement.
    """
    if not (sys.stdin.isatty() and interactive()):
        return None
    try:
        import termios, tty  # noqa: F401
    except ImportError:
        return None          # Windows: fall back to typing a number
    return termios


def _read_key(termios) -> str:
    """One keypress -> 'up' | 'down' | 'enter' | 'quit' | a single character."""
    import tty
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":                       # escape: an arrow, or a bare Esc
            nxt = sys.stdin.read(1)
            if nxt != "[":
                return "quit"
            return {"A": "up", "B": "down", "C": "down", "D": "up"}.get(sys.stdin.read(1), "")
        if ch in ("\r", "\n"):
            return "enter"
        if ch in ("\x03", "\x04", "q"):       # ctrl-c, ctrl-d, q
            return "quit"
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)


def _fit_per_row(items, tags, per_row: int) -> int:
    """How many options fit across this terminal.

    The redraw moves the cursor up by a fixed number of LOGICAL lines, so a row
    that wraps would put it in the wrong place and shred the display. Reflowing
    to the real width is what keeps that from ever happening.
    """
    import shutil
    width = shutil.get_terminal_size((100, 24)).columns
    cell = max(len(f"{lbl}{' · ' + tags[k] if tags.get(k) else ''}") for k, lbl in items) + 6
    return max(1, min(per_row, (width - COL - 4) // max(cell, 1)))


def _option_rows(items, per_row, tags, selected=None) -> list[str]:
    """One line per row of options; the selected one is a filled amber block.

    Padding sits OUTSIDE the inverted run so the highlight is a rectangle around
    the item rather than a bar across the column.
    """
    def visible(key, lbl):
        t = f" · {tags[key]}" if tags.get(key) else ""
        return f"{lbl}{t}"

    width = max(len(visible(k, l)) for k, l in items) + 6
    rows = []
    for i in range(0, len(items), per_row):
        cells = []
        for j, (key, lbl) in enumerate(items[i:i + per_row], start=i):
            body = f"{j + 1} {visible(key, lbl)}"
            pad = " " * max(0, width - len(body) - 3)
            if j == selected:
                # whole item negative: amber ground, terminal ink, snug border
                cells.append(f"{AMBER}{INVERT} {body} {RESET}{pad}")
            else:
                # the leading space matches the highlight's left edge, so columns
                # do not jump sideways as the selection moves
                t = f"{GREY} · {tags[key]}{RESET}" if tags.get(key) else ""
                cells.append(f" {GREY}{j + 1}{RESET} {lbl}{t} {pad}")
        rows.append(f"  {' ' * COL}{''.join(cells).rstrip()}")
    return rows


def _wrap_to_width(text: str, indent: int) -> list[str]:
    import shutil, textwrap
    width = shutil.get_terminal_size((100, 24)).columns - indent - 2
    return textwrap.wrap(text, max(30, width)) or [""]


def options(items: list[tuple[str, str]], per_row: int = 3, default_idx: int = 0,
            tags: dict[str, str | None] | None = None, legend: str | None = None,
            details: dict[str, str] | None = None) -> str:
    """Choose one option; return its key.

    At a terminal: arrow keys move, Enter confirms, and the number still works
    for anyone who would rather type it. Piped in: exactly the old behaviour.
    """
    tags = tags or {}
    details = details or {}
    kb = _keyboard()
    if kb is not None:
        per_row = _fit_per_row(items, tags, per_row)
    if kb is None:
        for line in _option_rows(items, per_row, tags):
            out(line)
        for k, lbl in items:          # piped: no hover, so every detail is printed
            if details.get(k):
                note(f"[{[i for i,(kk,_) in enumerate(items) if kk==k][0]+1}] {lbl} — {details[k]}")
        if legend:
            note(legend)
        while True:
            ans = prompt(str(default_idx + 1))
            if ans.isdigit() and 1 <= int(ans) <= len(items):
                return items[int(ans) - 1][0]
            note(f"type a number between 1 and {len(items)}")

    sel = max(0, min(default_idx, len(items) - 1))
    rows = _option_rows(items, per_row, tags, sel)
    detail_h = max((len(_wrap_to_width(d, COL + 2)) for d in details.values()), default=0)
    for line in rows:
        out(line)
    for _ in range(detail_h):
        out("")
    if legend:
        note(legend)
    firsts = [lbl.strip().lower()[:1] for _, lbl in items]
    by_letter = {c: i for i, c in enumerate(firsts) if firsts.count(c) == 1}
    shortcut = ("or press " + "/".join(sorted(by_letter))) if len(by_letter) == len(items) <= 3 \
        else "or type a number"
    hint = f"  {' ' * COL}{GREY}↑↓ to move · Enter to choose · {shortcut}{RESET}"
    out(hint)

    def repaint(i):
        paint("\033[F" * (len(rows) + detail_h + 1))
        for line in _option_rows(items, per_row, tags, i):
            paint(line + "\033[K\n")
        body = _wrap_to_width(details.get(items[i][0], ""), COL + 2) if details else []
        for n in range(detail_h):
            txt = body[n] if n < len(body) else ""
            paint(f"  {' ' * COL}{GREY}{txt}{RESET}\033[K\n")
        paint(hint + "\033[K\n")

    if detail_h:
        repaint(sel)
    with SILENCE.indicator():
        while True:
            key = _read_key(kb)
            if key == "enter":
                break
            if key == "quit":
                out(f"\n  {GREY}okay, stopping here. nothing was changed.{RESET}")
                sys.exit(0)
            if key == "up":
                sel = (sel - 1) % len(items)
            elif key == "down":
                sel = (sel + 1) % len(items)
            elif key.isdigit() and 1 <= int(key) <= len(items):
                sel = int(key) - 1
            elif key.lower() in by_letter:
                sel = by_letter[key.lower()]
            else:
                continue
            repaint(sel)
    # leave the chosen state on screen, without the hint line
    repaint(sel)
    paint("\033[F" + "\033[K")
    SILENCE.touch()
    return items[sel][0]


class Wedge:
    """Density-wedge progress bar: █ done · ▓▒░ working edge · frame and time left underneath.

    A frame of a 150 MP scan takes ~30 s, so between two steps the bar would sit
    perfectly still for half a minute and read as a hang. A heartbeat thread
    keeps the working edge moving while the count stands still.
    """

    def __init__(self, total: int, width: int = 40, unit: str = ""):
        self.total, self.width, self.t0, self.n = max(total, 1), width, time.time(), 0
        self.detail, self.unit, self.phase = "", unit, 0
        self._hold = SILENCE.indicator()
        self._hold.__enter__()
        self._stop = threading.Event()
        self._beat = None
        if interactive():
            self._beat = threading.Thread(target=self._heartbeat, daemon=True)
            self._beat.start()
        self._draw()

    def _heartbeat(self) -> None:
        while not self._stop.wait(0.2):
            if self.n < self.total:
                self.phase += 1
                self._draw()

    def step(self, n: int = 1, detail: str = "") -> None:
        self.n += n
        self.detail = detail
        self._draw()
        if self.n >= self.total:
            self.close()

    def close(self) -> None:
        if self._stop.is_set():
            return
        self._stop.set()
        if self._beat is not None:
            self._beat.join(timeout=0.5)
        self._hold.__exit__(None, None, None)

    def _draw(self) -> None:
        filled = int(self.width * self.n / self.total)
        room = max(0, min(3, self.width - filled))
        # the edge glyphs rotate on the heartbeat, so stillness still looks alive
        edge = "".join("▓▒░"[(self.phase + i) % 3] for i in range(room)) if self.n < self.total else ""
        bar = "█" * filled + edge
        rate = (time.time() - self.t0) / max(self.n, 1)
        left = rate * (self.total - self.n) if self.n else 0
        eta = "" if self.n == 0 or self.n >= self.total else (f"about {max(1, round(left / 60))} min left" if left > 50 else f"{int(left)} s left")
        sub = " · ".join(x for x in (self.detail, eta) if x)
        line1 = f"  {' ' * COL}{AMBER}{bar.ljust(self.width)}{RESET}  {self.n}/{self.total}{self.unit}"
        with SCREEN:
            print("\r" + line1.ljust(100), end="", flush=True)
            if self.n >= self.total:
                print(flush=True)
            elif sub:
                print(f"\n  {' ' * COL}{GREY}{sub.ljust(60)}{RESET}\033[F", end="", flush=True)  # sub-line, then back up


@contextlib.contextmanager
def busy(label: str):
    """Transient status line with a density spinner while the main thread works."""
    with SILENCE.indicator(), Spinner(label):
        yield


def spinner_while(proc: subprocess.Popen, label: str) -> None:
    t0 = time.time()
    with SILENCE.indicator(), Spinner(label, tail=lambda: f"{int(time.time() - t0)} s"):
        while proc.poll() is None:
            time.sleep(0.15)


def open_file(path: Path) -> None:
    if os.environ.get("SALTGATE_NO_OPEN"):
        return
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        elif sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", str(path)], check=False)
        else:
            os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        pass


# ── helpers ───────────────────────────────────────────────────────────────
def clean_path(raw: str) -> Path:
    return Path(os.path.expanduser(raw.strip().strip("'\"").replace("\\ ", " ")))


def short(path: Path, keep: int = 3) -> str:
    parts = path.parts
    return str(path) if len(parts) <= keep + 1 else "…/" + "/".join(parts[-keep:])


def log_dir() -> Path:
    d = Path.home() / "Library/Logs/saltgate" if sys.platform == "darwin" else Path.home() / ".saltgate/logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    """Where a remembered look preference lives. Same platform split as log_dir."""
    base = Path.home() / "Library/Application Support/saltgate" if sys.platform == "darwin" else Path.home() / ".saltgate"
    return base / "config.json"


def load_config() -> dict:
    """Never raises. A corrupt or unreadable config must not stop someone grading."""
    try:
        d = json.loads(config_path().read_text())
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_config(cfg: dict) -> None:
    try:
        p = config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cfg, indent=1))
    except Exception:
        pass   # a preference is a convenience; failing to store it is not an error


def remembered_look(stock: str) -> str | None:
    key = load_config().get("looks", {}).get(stock)
    return key if any(l.key == key for l in looksmod.looks_for(stock)) else None


def remember_look(stock: str, key: str) -> None:
    cfg = load_config()
    cfg.setdefault("looks", {})[stock] = key
    save_config(cfg)


def write_log(kind: str, text: str) -> Path:
    from . import __version__
    p = log_dir() / f"{kind}-{time.strftime('%Y%m%d-%H%M%S')}.log"
    p.write_text(f"saltgate {__version__} · python {sys.version.split()[0]} · {sys.platform}\n\n{text}")
    return p


def quiet_libraries() -> None:
    """Library chatter (OpenCV '[ WARN ]', torch/numpy UserWarnings) is noise for this audience."""
    import warnings
    warnings.filterwarnings("ignore")
    os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
    try:
        import cv2
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
    except Exception:
        pass


GIT_SPEC = "saltgate @ git+https://github.com/atrouwee/saltgate.git"


def _uv() -> str | None:
    import shutil
    uv = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
    return uv if Path(uv).exists() else None


def _in_uv_tool() -> bool:
    return (Path(sys.prefix) / "uv-receipt.toml").exists()


def _vtuple(v: str) -> tuple:
    return tuple(int(x) for x in v.split(".") if x.isdigit())


def _fetch_latest() -> str | None:
    """Newer published version, or None (offline, disabled, up to date)."""
    if os.environ.get("SALTGATE_NO_UPDATE"):
        return None
    try:
        import urllib.request
        from . import __version__
        with urllib.request.urlopen("https://raw.githubusercontent.com/atrouwee/saltgate/main/pyproject.toml", timeout=2) as r:
            latest = r.read().decode().split('version = "', 1)[1].split('"', 1)[0]
        latest = os.environ.get("SALTGATE_FAKE_LATEST", latest)   # test hook
    except Exception:
        return None
    return latest if _vtuple(latest) > _vtuple(__version__) else None


def _apply_update(latest: str) -> None:
    """With uv, update in place and relaunch; otherwise just say so."""
    from . import __version__
    uv = _uv()
    if uv is None or not _in_uv_tool():
        note(f"v{latest} is available (you have v{__version__}) · paste the installer line from the README again to update")
        out()
        return
    receipt("update", f"v{latest} is available — updating from v{__version__}")
    # `uv tool upgrade` keeps the git commit recorded at install time, so reinstall from main instead,
    # carrying the orientation libraries along when they are present.
    import importlib.util
    # transitional: carry torch along for anyone who installed it back when
    # rotation needed it, so an update cannot take their rotation away before
    # they have fetched the ONNX. Drop once the release asset has been live a while.
    extras = ["--with", "torch", "--with", "torchvision"] if importlib.util.find_spec("torch") else []
    proc = subprocess.Popen([uv, "tool", "install", "--force", "--python", "3.12", *extras, GIT_SPEC],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    spinner_while(proc, "updating")
    text = proc.stdout.read() if proc.stdout else ""
    if proc.returncode != 0:
        write_log("update", text)
        note("the update didn't work — continuing with the current version")
        out()
        return
    note(f"restarting on v{latest}")
    out()
    # the relaunched process is told BOTH that it must not check again and what
    # it came from, so it can say "updated" instead of silently replaying the
    # banner and a checking-for-updates line it is not actually running
    env = dict(os.environ, SALTGATE_NO_UPDATE="1", SALTGATE_UPDATED_FROM=__version__)
    os.execve(sys.argv[0], [sys.argv[0]] + sys.argv[1:], env)


def explain(e: Exception) -> str:
    msg = str(e)
    if isinstance(e, (ImportError, ModuleNotFoundError)):
        return "part of the installation is missing — paste the installer line from the README again, then retry"
    if isinstance(e, PermissionError):
        return "I'm not allowed to write next to your scans (read-only disk or folder?) — copy the folder to your Desktop and retry"
    if isinstance(e, OSError) and ("No space" in msg or getattr(e, "errno", None) == 28):
        return "the disk is full — graded frames need about 35 MB each; free some space and run again, it continues where it stopped"
    if isinstance(e, FileNotFoundError):
        return "a file disappeared while I was working (moved, renamed, or a disconnected drive) — check the folder and run again"
    if isinstance(e, MemoryError):
        return "the computer ran out of memory — close other apps and run again, it continues where it stopped"
    if "torch" in msg.lower() or "CUDA" in msg:
        return "the orientation step hit a problem — run again and answer n to the upright question"
    return f"unexpected problem ({type(e).__name__}) — running again usually helps; it continues where it stopped"


def detect_stock_from_sidecars(folder: Path) -> str | None:
    for d in (folder, folder.parent):
        for js in d.glob("*Exported.json"):
            try:
                code = str(json.loads(js.read_text()).get("Film_1_Stock", "")).strip()
                if code in LAB_STOCK_CODES:
                    return LAB_STOCK_CODES[code]
            except Exception:
                pass
        info = d / "info.txt"
        if info.exists():
            t = info.read_text().lower()
            for key in ("250d", "50d", "200t", "500t", "125"):
                if key in t:
                    return "125special" if key == "125" else key
    return None


def ensure_orientation() -> bool:
    """Make the orientation model available. Returns False if we must go without.

    This used to install torch (529 MB) through `uv tool install --force`, which
    rebuilt the whole tool environment out from under the running process and so
    needed an os.execve to continue -- restarting the walkthrough from question
    one and losing every answer already given. The backbone is now a 47 MB ONNX
    run by the OpenCV that is already installed: one download, no install, no
    restart.
    """
    from . import orient

    if not orient.have_backbone():
        # No second confirmation: saying yes to "put the frames the right way up"
        # is the decision. The model normally arrives with the installer, so this
        # runs only when that was skipped, and answering no there would just
        # leave the feature they asked for broken.
        mb = round(orient.BACKBONE["bytes"] / 1e6)
        receipt("upright", f"fetching the orientation model · {mb} MB, once")
        bar = {}

        def on_progress(done: int, total: int) -> None:
            total_mb = max(1, round((total or orient.BACKBONE["bytes"]) / 1e6))
            if "w" not in bar:
                bar["w"] = Wedge(total_mb, unit=" MB")
            w = bar["w"]
            want = min(total_mb, round(done / 1e6))
            if want > w.n:
                w.step(want - w.n)

        try:
            # reaching the release asset (DNS, TLS, first byte) happens before any
            # byte count exists, so the step covers it until the bar takes over
            with step("reaching github.com"):
                orient.ensure_backbone(on_progress)
        except Exception as e:
            if "w" in bar:
                bar["w"].close()
            p = write_log("orientation-download", repr(e))
            receipt("upright", "the download didn't work — continuing without it", "warn")
            note(f"you can run saltgate again to retry · details: {p}")
            return False
        finally:
            if "w" in bar:
                bar["w"].close()
        out()

    try:
        with step("loading the orientation model"):
            orient.OrientationModel()
        return True
    except Exception as e:
        write_log("orientation-load", repr(e))
        receipt("upright", "the orientation model wouldn't load — continuing without it", "warn")
        return False


# ── the walkthrough ───────────────────────────────────────────────────────
def run() -> int:
    """Entry point with a safety net: never show a traceback, always save one."""
    try:
        return _run()
    except KeyboardInterrupt:
        out(f"\n  {GREY}stopped. frames finished so far are kept — run saltgate again to continue where you left off.{RESET}\n")
        return 130
    except SystemExit:
        raise
    except Exception as e:
        import traceback
        p = write_log("error", traceback.format_exc())
        out()
        receipt("stopped", "nothing of yours was modified", "err")
        note(explain(e))
        note(f"details: {p}  ·  report: https://github.com/atrouwee/saltgate/issues")
        out()
        return 1


def _run() -> int:
    from . import __version__
    SILENCE.start()
    out()
    out(f"  {AMBER}░▒▓█{RESET}  {BOLD}SALTGATE{RESET}{' ' * 44}{GREY}v{__version__}{RESET}")
    out(f"        finish your flat SILBERSALZ scans")
    out(f"        {GREY}the name is a wink · the work is sincere{RESET}")
    out()
    # the slow part of starting up (loading image libraries, checking for updates)
    # happens behind a status line so the window is never silent. The label has to
    # match what is actually happening: after a self-update the check is skipped,
    # and claiming otherwise made the relaunch look like a loop.
    came_from = os.environ.pop("SALTGATE_UPDATED_FROM", None)
    checking = not os.environ.get("SALTGATE_NO_UPDATE")
    with busy("warming up · checking for updates" if checking else "warming up"):
        quiet_libraries()
        from . import imgio  # noqa: F401  (loads numpy / PIL / opencv)
        latest = _fetch_latest() if checking else None
    if came_from:
        receipt("update", f"updated from v{came_from} — you are on v{__version__}", "ok")
        out()
    if latest:
        _apply_update(latest)

    # ◆ scans
    receipt("scans", "drag the folder into this window and press Enter")
    while True:
        folder = clean_path(prompt())
        if folder.is_file():
            note("that's a single file — drag the whole folder that contains your scans"); continue
        if not folder.is_dir():
            note("I can't find a folder there — try dragging it from Finder"); continue
        gradeable = lambda d: [f for f in imgio.list_images(d) if f.suffix.lower() in imgio.GRADEABLE_EXTS]
        with step(f"looking through {folder.name}"):
            files = gradeable(folder)
        if not files:
            with step("looking in the folders inside it"):
                subs = [d for d in sorted(folder.iterdir()) if d.is_dir() and not d.name.startswith(".")
                        and gradeable(d)]
            if subs:
                note("no scans directly in that folder, but these folders inside it have some — which one holds the flat scans?")
                choice = options([(str(d), f"{d.name} ({len(gradeable(d))})") for d in subs], per_row=2)
                folder = Path(choice)
                with step(f"looking through {folder.name}"):
                    files = gradeable(folder)
            else:
                note("no scans in that folder — the LUTs work on the lab's 'raw colour' files\n"
                     "(jpg, or the 16-bit jxl / jp2 if your delivery has them)")
                continue
        # flat vs graded is decided by the name where the lab gives one, and by the
        # milky look of a flat scan below where it does not -- never by extension
        raw_named = [f for f in files if "RAW" in f.name.upper()]
        graded_named = [f for f in files if "RAW" not in f.name.upper()
                        and (f.stem.upper().endswith("_HIGH") or f.stem.upper().endswith("_FULL"))]
        if raw_named and graded_named:
            note(f"both raw ({len(raw_named)}) and graded ({len(graded_named)}) files here — using the raw ones")
            files = raw_named
        break
    sample = files[:: max(1, len(files) // 6)][:6]
    with step("checking whether these are flat scans"):
        w = Wedge(len(sample))
        n_flat = 0
        depths = []
        for f in sample:
            got = imgio.read_image(f, max_px=400)
            depths.append(got.bit_depth)
            n_flat += int(float((got.rgb.max(-1) - got.rgb.min(-1)).mean()) < 0.08)
            w.step()
    src_bits = max(depths) if depths else 8
    if n_flat == 0:
        receipt("scans", f"{len(files)} frames · these look GRADED already — the LUT would double-grade them", "warn")
        note("continue anyway?")
        if not yes(False):
            return 0
    else:
        receipt("scans", f"{len(files)} frames · flat (raw colour)" + (" ✓" if n_flat == len(sample) else " · a few look graded"), "ok" if n_flat == len(sample) else "warn")
    out()

    # ◆ film
    with step("reading the lab's delivery notes"):
        detected = detect_stock_from_sidecars(folder)
    if detected:
        receipt("film", f"the lab's sidecar says {dict(STOCK_CHOICES).get(detected, detected)} — is that right?")
        stock = detected if yes(True) else None
        if stock is None:
            stock = ask_stock()
    else:
        stock = ask_stock()
    borrowed = None
    if stock not in LUTS:
        borrowed, stock = stock, BORROWS[stock]
    candidates = looksmod.looks_for(stock)
    look = looksmod.resolve(stock, remembered_look(stock))
    cube = looksmod.cube_path(look)
    if not cube.exists():
        raise FileNotFoundError(str(cube))
    receipt("film", f"{look.cube.split('_')[0]} · {AMBER}{look.status}{RESET}")
    if borrowed == "other":
        note("most Silbersalz rolls were Vision3 daylight stock, so this starts from the 250D proxy. tungsten film (200T/500T) would look blue with it — pick the stock if you can.")
    elif borrowed:
        base_name = dict(STOCK_CHOICES)[stock]
        if borrowed == "125special":
            note(f"no 125T pairs yet — borrowing the {base_name} LUT: also tungsten-balanced, but 125T 'Edition Vivid' is a Fuji stock,\n"
                 "not Vision3, so expect a larger difference than between two Kodak stocks. real 125T pairs would replace it:\n"
                 "https://github.com/atrouwee/saltgate")
        else:
            note(f"no {dict(STOCK_CHOICES)[borrowed]} pairs yet — borrowing the {base_name} LUT: same balance family, same scan encoding,\n"
                 "so it is a fair first pass (daylight and tungsten stocks are 20+ ΔE apart; within a family it is ~3).\n"
                 "real pairs of this stock would replace it. if you have any, please get in touch: https://github.com/atrouwee/saltgate")
    if len(candidates) > 1:
        note(f"{len(candidates)} versions of this look exist — the preview renders them side by side and you pick.")
    note(look.note)
    out()

    # the film gate does not move between frames of one roll, so this is measured
    # once and handed to both the rotation pass and the preview. It used to be
    # recomputed for each, uncached, and both runs were silent.
    from . import rebate
    out_dir = folder.parent / f"{folder.name}_saltgate"
    out_dir.mkdir(exist_ok=True)
    frac = None

    def roll_geometry():
        nonlocal frac
        if frac is None:
            with step("measuring where the picture sits on the film"):
                # hidden subfolder: the output directory holds the user's graded
                # frames plus saltgate.json / rotations.json, all of which mean
                # something to them. A hashed cache file does not.
                frac = rebate.roll_area_fractions(files, cache_dir=out_dir / ".cache")
        return frac

    # ◆ upright
    rotations = None
    receipt("upright", "put the frames the right way up automatically?")
    if yes(True):
        if ensure_orientation():
            from . import orient
            roll_geometry()
            with step("loading the orientation model"):
                model = orient.OrientationModel()
            rotations = {}
            with step("reading the frames"):
                w = Wedge(len(files))
                for f in files:
                    area = rebate.crop_to_area(imgio.read_image(f, max_px=900).rgb, frac)
                    rotations[f.name] = {"k": 0, "confidence": 1.0} if rebate.looks_blank(area) else model.predict(area)
                    w.step(detail=f"frame {f.name.split('_')[-1].split('-')[0]}")
            low = sum(1 for r in rotations.values() if r.get("confidence", 1) < 0.5)
            note(f"{low} frames were hard to judge · check them on the preview and in the result")
    else:
        note("keeping the film-strip orientation")
    out()

    # ◆ preview
    from . import balance as balmod, lut as lutmod, sheet, orient as orient_mod
    import numpy as np
    with step(f"loading the look{'s' if len(candidates) > 1 else ''}"):
        lattices = [lutmod.read_cube(looksmod.cube_path(c))[0] for c in candidates]
    lattice_of = lambda lk: lattices[[c.key for c in candidates].index(lk.key)]
    roll_geometry()
    picks = files[:: max(1, len(files) // 6)][:8]
    receipt("preview", "rendering six frames" + (f" · {len(candidates)} versions" if len(candidates) > 1 else ""))
    with step("rendering the preview"):
        w = Wedge(6)
        rows = []
        for f in picks:
            a = rebate.crop_to_area(imgio.read_image(f, max_px=900).rgb, frac)
            if rebate.looks_blank(a):
                continue
            if rotations:
                a = orient_mod.apply_rotation(a, rotations[f.name]["k"])
            tiles = [(a, "flat scan", sheet.COLORS["input"])]
            for j, (c, lat) in enumerate(zip(candidates, lattices)):
                colour = sheet.COLORS["lut"] if j == 0 else sheet.COLORS["alt"]
                tiles.append((lutmod.apply_trilinear(lat, a), f"[{j + 1}] {stock} · {c.label}", colour))
            rows.append({"title": f.name, "tiles": tiles})
            w.step()
            if len(rows) >= 6:
                break
        while w.n < w.total:
            w.step()
    preview = out_dir / "preview.jpg"
    with step("building the contact sheet"):
        sheet.save_sheet(sheet.build_sheet(rows, tile_h=260), preview, quality=85)
    open_file(preview)
    note(f"opened · {short(preview)}")
    out()

    # ◆ look — only where a real second candidate exists; one stock, one LUT stays silent
    if len(candidates) > 1:
        remembered = remembered_look(stock)
        receipt("look", "which one fits this roll?")
        if remembered:
            note(f"remembered from last time: {look.label}")
        # the honest note follows the highlight rather than sitting above it as a
        # wall of prose -- six lines of caveat used to bury the choice itself
        chosen = options([(c.key, c.label) for c in candidates],
                         default_idx=candidates.index(look),
                         tags={c.key: READINESS.get(c.status, "proxy") for c in candidates},
                         details={c.key: c.note for c in candidates})
        look = looksmod.resolve(stock, chosen)
        cube = looksmod.cube_path(look)
        remember_look(stock, look.key)
        receipt("look", f"{look.label} · {AMBER}{look.status}{RESET}", "ok")
        note("remembered for next time")
        out()

    # ◆ format — only asked when the input carries more than 8 bits.
    # Writing 8-bit out of a 16-bit scan re-imposes the same 2.2 dE the lab's own
    # gallery jpeg costs, which is larger than the colour error still left in the
    # LUT, so 16-bit is the default when 16-bit came in.
    bits = 8
    if src_bits >= 16:
        bits = 16
        receipt("format", f"these are {src_bits}-bit scans — keeping 16-bit out")
        note("a jpeg would throw away most of that depth. keep 16-bit TIFF? (files are ~10x larger)")
        if not yes(True):
            bits = 8
            note("writing 8-bit JPEG instead")
        else:
            note("16-bit TIFF, Display P3, one file per frame")
        out()

    # ◆ density — optional, and skipped by a single Enter.
    # Measured worth: the bare LUT sits at dE 5.65 against the lab, and 2.0-2.4
    # once each roll gets its own density. It is the largest remaining difference
    # and the one thing a colour transform structurally cannot carry, so it is
    # offered -- but never forced, because most people will not want a decision.
    density = 0.0
    receipt("density", "the lab set print density per roll — set yours? (optional)")
    note("a colour transform can't know how dense your roll was; it's the biggest\n"
         "single difference left between this and the lab's own file.")
    if yes(False):
        steps = [(-0.30, "denser"), (-0.15, ""), (0.0, "as the LUT renders it"), (+0.15, ""), (+0.30, "lighter")]
        with step("rendering the density ladder"):
            lad_rows = []
            w = Wedge(min(3, len(rows)))
            for r in rows[:3]:
                a0 = r["tiles"][0][0]
                tiles = []
                for dv, tag in steps:
                    g = np.ones(3, np.float32) * (2.0 ** dv)
                    tiles.append((lutmod.apply_trilinear(lattice_of(look), balmod.apply_gains(a0, g)),
                                  f"{dv:+.2f} stops" + (f" · {tag}" if tag else ""),
                                  sheet.COLORS["lut"] if dv == 0 else sheet.COLORS["alt"]))
                lad_rows.append({"title": r["title"], "tiles": tiles})
                w.step()
        ladder = out_dir / "density.jpg"
        with step("building the density sheet"):
            sheet.save_sheet(sheet.build_sheet(lad_rows, tile_h=230), ladder, quality=85)
        open_file(ladder)
        note(f"opened · {short(ladder)}")
        pick = options([(f"{dv}", f"{dv:+.2f}") for dv, _ in steps], default_idx=2)
        density = float(pick)
        receipt("density", f"{density:+.2f} stops for the whole roll", "ok")
        note("applied to every frame; the lab set it per roll too")
    else:
        note("leaving it as the LUT renders it")
    out()

    # ◆ grade
    import shutil as _sh
    already = [f for f in files if (out_dir / f.name).with_suffix(imgio.output_suffix(bits)).exists()]
    todo = len(files) - len(already)
    free_gb = _sh.disk_usage(out_dir).free / 1e9
    need_gb = todo * (0.9 if bits >= 16 else 0.035)
    mins = max(1, round(todo * SECONDS_PER_FRAME / 60))
    receipt("grade", f"about {mins} min · {need_gb:.1f} GB needed · {free_gb:.0f} GB free")
    if already:
        note(f"{len(already)} frames were graded earlier and will be kept")
    if need_gb > free_gb:
        receipt("grade", f"not enough free disk space — free about {need_gb - free_gb + 1:.0f} GB and run again", "warn")
        return 1
    batch = 20
    if todo > batch:
        how = options([("all", f"all {todo} frames now (the Mac is kept awake)"),
                       ("batch", f"a first batch of {batch} (~{max(1, round(batch * SECONDS_PER_FRAME / 60))} min), continue later"),
                       ("stop", "not now — keep the preview only")], per_row=1)
    else:
        note("happy with the preview? go ahead?")
        how = "all" if yes(True) else "stop"
    if how == "stop":
        note(f"okay — nothing else was written. the preview stays in {short(out_dir)}")
        out()
        return 0
    limit = batch if how == "batch" else None
    n_run = min(todo, limit) if limit else todo

    from . import apply as ap
    w = Wedge(n_run)
    # nothing completes for the first ~30 s (workers start, frame 1 decodes), so the
    # bar would otherwise sit at 0/N looking stuck; its heartbeat and this line cover it
    w.detail = "starting"

    def log(msg: str) -> None:
        if msg.startswith("  ["):
            name = msg.split("]", 1)[1].strip().split(" ")[0]
            w.step(detail=f"frame {name.split('_')[-1].split('-')[0] if '_' in name else name}")
        elif msg.startswith("[apply]"):
            w.detail = "starting the workers"

    keep_awake = None
    if sys.platform == "darwin":
        try:
            keep_awake = subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())])
        except Exception:
            keep_awake = None
    try:
        with step(f"grading {n_run} frames"):
            ap.grade_folder(folder, out_dir, cube, balance_mode="off", resume=True, rotations=rotations,
                        limit=limit, density=density, bits=bits, log=lambda m: log(m))
    except Exception as e:
        write_log("grading", repr(e))
        out()
        receipt("stopped", "frames finished so far are kept", "err")
        note(explain(e))
        note("run saltgate again to continue")
        out()
        return 1
    finally:
        w.close()
        if keep_awake is not None:
            keep_awake.terminate()
    if rotations:
        (out_dir / "rotations.json").write_text(json.dumps(rotations, indent=1))
    (out_dir / "saltgate.json").write_text(json.dumps({"source": str(folder), "lut": str(cube), "stock": stock,
                                                      "look": look.key, "density": density, "bits": bits, "film": borrowed or stock,
                                                      "rotated": bool(rotations)}, indent=1))

    # ◆ done
    remaining = len([f for f in files if not (out_dir / f.name).exists()])
    if remaining:
        receipt("batch", f"{len(files) - remaining} of {len(files)} graded → {short(out_dir)}", "ok")
        note(f"run saltgate again whenever you like to continue with the remaining {remaining}")
    else:
        receipt("done", f"{len(files)} frames → {short(out_dir)}", "ok")
        note("JPEGs in Display P3 with the original EXIF · ready for Capture One, Lightroom, anything")
    if rotations:
        note(f'a frame the wrong way up?  saltgate fix-rotation "{out_dir}" 0026=1   (quarter turns anticlockwise: 1, 2 or 3)')
    out()
    out(f"        {GREY}if the lab ever sends graded versions of these frames, keep both —\n        flat + graded pairs make this better for everyone.  https://github.com/atrouwee/saltgate{RESET}")
    out()
    open_file(out_dir)
    return 0


def fix_rotation(args: list[str]) -> int:
    """saltgate fix-rotation <graded folder> 0026=1 0031=2 — re-grade those frames from the originals with a new orientation."""
    if len(args) < 2:
        out("  usage: saltgate fix-rotation <graded folder> <frame>=<quarter turns> …   e.g. 0026=1"); return 1
    out_dir = clean_path(args[0])
    state_path = out_dir / "saltgate.json"
    if not state_path.exists():
        receipt("stopped", "that folder wasn't made by the walkthrough (no saltgate.json inside)", "err"); return 1
    SILENCE.start()
    state = json.loads(state_path.read_text()); rot_path = out_dir / "rotations.json"
    rotations = json.loads(rot_path.read_text()) if rot_path.exists() else {}
    from . import apply as ap, lut as lutmod, imgio
    src = Path(state["source"])
    with step("loading the look and finding the originals"):
        lattice = lutmod.read_cube(state["lut"])[0]
        files = {f.name: f for f in imgio.list_images(src) if f.suffix.lower() in (".jpg", ".jpeg")}
    for spec in args[1:]:
        if "=" not in spec:
            receipt("skipped", f"'{spec}' — write it as 0026=1", "warn"); continue
        tag, k = spec.split("=", 1)
        matches = [n for n in files if f"_{tag}-" in n or n.startswith(tag)]
        if not matches:
            receipt("skipped", f"no frame matching '{tag}'", "warn"); continue
        for n in matches:
            new_k = (rotations.get(n, {}).get("k", 0) + int(k)) % 4
            rotations[n] = {"k": new_k, "confidence": 1.0, "manual": True}
            # a full-resolution frame is ~30 s; without this the terminal is dead
            with step(f"re-grading {n}"):
                ap.grade_one(files[n], out_dir / n, lattice, None, "off", 1.0, None, 95, 0.0, new_k)
            receipt("fixed", f"{n} · turned {int(k)} quarter turn(s) anticlockwise", "ok")
    rot_path.write_text(json.dumps(rotations, indent=1))
    return 0
