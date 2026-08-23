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

# stock -> (LUT file, status, one-line honesty)
LUTS = {
    "250d": ("silbersalz-250d_v0-statistical_33.cube", "PROXY",
             "a statistical approximation — close in tone, skin a little light, skies a little dark. real 250D pairs will replace it."),
    "gold200": ("silbersalz-gold200_v1-paired_33.cube", "BETA",
                "fitted from 27 real flat/graded pairs (one donor, two rolls). close to the lab on its own rolls; other rolls may want a small exposure nudge."),
}
STOCK_CHOICES = [("250d", "Vision3 250D"), ("50d", "Vision3 50D"), ("200t", "Vision3 200T"),
                 ("500t", "Vision3 500T"), ("gold200", "Kodak Gold 200"), ("125special", "125 Special"),
                 ("other", "something else / I don't know")]
# readiness, derived from LUTS: validated (real pairs, checked on rolls the fit never saw) · beta (real pairs,
# one donor so far) · proxy (no pairs — a stand-in estimated from the author's graded archive). Vision3 stocks
# without their own LUT borrow the 250D proxy: same negative family, same scan encoding. Gold (C-41) is a
# different curve and never borrows.
READINESS = {"PROXY": "proxy", "BETA": "beta", "VALIDATED": "validated"}
BORROWS = {"50d": "250d", "200t": "250d", "500t": "250d", "125special": "250d", "other": "250d"}
READINESS_LEGEND = ("validated = fitted on real flat + graded pairs and checked on rolls it never saw · "
                    "beta = fitted on real pairs, one donor so far\n"
                    "proxy = no pairs yet, a stand-in estimated from the author's ~700 graded lab scans · "
                    "proxy (250D) = borrows the 250D proxy, same Vision3 family · more pairs, less guesswork")


def ask_stock() -> str:
    receipt("film", "which film was this roll?")
    return options(STOCK_CHOICES, tags={k: readiness(k) for k, _ in STOCK_CHOICES}, legend=READINESS_LEGEND)


def readiness(stock: str) -> str | None:
    if stock in LUTS:
        return READINESS.get(LUTS[stock][1], "proxy")
    if stock == "other":
        return None
    return f"{readiness(BORROWS[stock])} (250D)"
LAB_STOCK_CODES = {"XXX": "250d"}   # codes seen in the lab's *_Exported.json; extend as we learn them
SECONDS_PER_FRAME = 25              # rough; used for the time estimate only


# ── output primitives ─────────────────────────────────────────────────────
def out(text: str = "") -> None:
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
    try:
        ans = input(f"  {AMBER}›{RESET}{hint} ").strip()
    except (EOFError, KeyboardInterrupt):
        out(f"\n  {GREY}okay, stopping here. nothing was changed.{RESET}")
        sys.exit(0)
    return ans or (default or "")


def yes(default: bool = True) -> bool:
    ans = prompt("Y/n" if default else "y/N").lower()
    if ans in ("y/n", "y/N".lower()):
        return default
    return default if not ans else ans.startswith("y")


def options(items: list[tuple[str, str]], per_row: int = 3, default_idx: int = 0,
            tags: dict[str, str | None] | None = None, legend: str | None = None) -> str:
    """Render [1] [2] [3] in columns under the current receipt line; return the chosen key.

    tags: optional grey word after each label (readiness); legend: grey line under the list.
    """
    tags = tags or {}
    plain = {k: f"{lbl}{' · ' + tags[k] if tags.get(k) else ''}" for k, lbl in items}
    width = max(len(v) for v in plain.values()) + 3
    for i in range(0, len(items), per_row):
        cells = []
        for j, (key, lbl) in enumerate(items[i:i + per_row], start=i):
            tag = f"{GREY} · {tags[key]}{RESET}" if tags.get(key) else ""
            pad = " " * (width - len(plain[key]))
            cells.append(f"{AMBER}[{j + 1}]{RESET} {lbl}{tag}{pad}")
        out(f"  {' ' * COL}{''.join(cells).rstrip()}")
    if legend:
        note(legend)
    while True:
        ans = prompt(str(default_idx + 1))
        if ans.isdigit() and 1 <= int(ans) <= len(items):
            return items[int(ans) - 1][0]
        note(f"type a number between 1 and {len(items)}")


class Wedge:
    """Density-wedge progress bar: █ done · ▓▒░ working edge · frame and time left underneath."""

    def __init__(self, total: int, width: int = 40):
        self.total, self.width, self.t0, self.n = max(total, 1), width, time.time(), 0
        self.detail = ""
        self._draw()

    def step(self, n: int = 1, detail: str = "") -> None:
        self.n += n
        self.detail = detail
        self._draw()

    def _draw(self) -> None:
        filled = int(self.width * self.n / self.total)
        edge = "▓▒░"[: max(0, min(3, self.width - filled))] if self.n < self.total else ""
        bar = "█" * filled + edge
        rate = (time.time() - self.t0) / max(self.n, 1)
        left = rate * (self.total - self.n) if self.n else 0
        eta = "" if self.n == 0 or self.n >= self.total else (f"about {max(1, round(left / 60))} min left" if left > 50 else f"{int(left)} s left")
        sub = " · ".join(x for x in (self.detail, eta) if x)
        line1 = f"  {' ' * COL}{AMBER}{bar.ljust(self.width)}{RESET}  {self.n}/{self.total}"
        print("\r" + line1.ljust(100), end="", flush=True)
        if self.n >= self.total:
            print(flush=True)
        elif sub:
            print(f"\n  {' ' * COL}{GREY}{sub.ljust(60)}{RESET}\033[F", end="", flush=True)  # write sub-line, move back up


import contextlib
import threading


@contextlib.contextmanager
def busy(label: str):
    """Transient status line with a density spinner while the main thread works."""
    stop = threading.Event()

    def spin():
        i, frames = 0, "░▒▓█▓▒"
        while not stop.is_set():
            print(f"\r  {' ' * COL}{AMBER}{frames[i % 6]}{RESET} {GREY}{label}{RESET}   ", end="", flush=True)
            i += 1
            stop.wait(0.15)
        print("\r" + " " * 90 + "\r", end="", flush=True)

    t = threading.Thread(target=spin, daemon=True)
    t.start()
    try:
        yield
    finally:
        stop.set()
        t.join()


def spinner_while(proc: subprocess.Popen, label: str) -> None:
    t0, i, frames = time.time(), 0, "░▒▓█▓▒"
    while proc.poll() is None:
        print(f"\r  {' ' * COL}{AMBER}{frames[i % 6]}{RESET} {GREY}{label} · {int(time.time() - t0)} s{RESET}   ", end="", flush=True)
        i += 1
        time.sleep(0.4)
    print("\r" + " " * 90 + "\r", end="", flush=True)


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


def lut_dir() -> Path:
    here = Path(__file__).resolve()
    for cand in (here.parents[2] / "luts", here.parent / "luts"):
        if cand.exists():
            return cand
    return here.parents[2] / "luts"


def log_dir() -> Path:
    d = Path.home() / "Library/Logs/saltgate" if sys.platform == "darwin" else Path.home() / ".saltgate/logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


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
    note(f"updated to v{latest} · relaunching")
    out()
    env = dict(os.environ, SALTGATE_NO_UPDATE="1")
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


def ensure_rotation_deps() -> bool:
    try:
        import torch, torchvision  # noqa: F401
        from . import orient
        orient.OrientationModel()
        return True
    except Exception:
        pass
    note("this needs two extra libraries (about 200 MB, one-time download) · download now?")
    if not yes(True):
        return False
    uv = _uv()
    if uv and _in_uv_tool():
        # re-install the tool WITH the extra libraries recorded, so future `uv tool upgrade` keeps them
        cmd = [uv, "tool", "install", "--force", "--python", "3.12", "--with", "torch", "--with", "torchvision", GIT_SPEC]
    else:
        cmd = [sys.executable, "-m", "pip", "install", "--quiet", "torch", "torchvision"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    spinner_while(proc, "downloading and installing")
    log_text = proc.stdout.read() if proc.stdout else ""
    if proc.returncode != 0:
        p = write_log("rotation-install", log_text)
        receipt("upright", "the download didn't work — continuing without it", "warn")
        note(f"details: {p}")
        return False
    if uv and _in_uv_tool():
        note("installed · relaunching with orientation enabled")
        out()
        env = dict(os.environ, SALTGATE_NO_UPDATE="1", SALTGATE_WANT_ROTATE="1")
        os.execve(sys.argv[0], [sys.argv[0]] + sys.argv[1:], env)
    import importlib
    importlib.invalidate_caches()
    try:
        import torch, torchvision  # noqa: F401
        from . import orient
        orient.OrientationModel()
        return True
    except Exception:
        receipt("upright", "installed, but needs a restart — run saltgate again to use it", "warn")
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
    out()
    out(f"  {AMBER}░▒▓█{RESET}  {BOLD}SALTGATE{RESET}{' ' * 44}{GREY}v{__version__}{RESET}")
    out(f"        finish your flat SILBERSALZ scans")
    out(f"        {GREY}the name is a wink · the work is sincere{RESET}")
    out()
    # the slow part of starting up (loading image libraries, checking for updates) happens
    # behind a status line so the window is never silent
    with busy("warming up · checking for updates"):
        quiet_libraries()
        from . import imgio  # noqa: F401  (loads numpy / PIL / opencv)
        latest = _fetch_latest()
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
        files = [f for f in imgio.list_images(folder) if f.suffix.lower() in (".jpg", ".jpeg")]
        if not files:
            subs = [d for d in sorted(folder.iterdir()) if d.is_dir() and not d.name.startswith(".")
                    and any(f.suffix.lower() in (".jpg", ".jpeg") for f in imgio.list_images(d))]
            if subs:
                note("no JPGs directly in that folder, but these folders inside it have some — which one holds the flat scans?")
                choice = options([(str(d), f"{d.name} ({len([f for f in imgio.list_images(d) if f.suffix.lower() in ('.jpg', '.jpeg')])})") for d in subs], per_row=2)
                folder = Path(choice); files = [f for f in imgio.list_images(folder) if f.suffix.lower() in (".jpg", ".jpeg")]
            else:
                if any(f.suffix.lower() in (".jxl", ".jp2") for f in imgio.list_images(folder)):
                    note("this folder holds the lab's 16-bit .jxl/.jp2 files — those are the GRADED deliveries.\nthe LUT is for the raw JPG scans (usually named …_RAW_COLOR.jpg)")
                else:
                    note("no JPG files in that folder — the LUTs work on the lab's JPG 'raw colour' scans")
                continue
        raw_named = [f for f in files if "RAW" in f.name.upper()]
        graded_named = [f for f in files if f.name.upper().endswith("_HIGH.JPG") and "RAW" not in f.name.upper()]
        if raw_named and graded_named:
            note(f"both raw ({len(raw_named)}) and graded ({len(graded_named)}) files here — using the raw ones")
            files = raw_named
        break
    sample = files[:: max(1, len(files) // 6)][:6]
    w = Wedge(len(sample))
    n_flat = 0
    for f in sample:
        rgb = imgio.read_image(f, max_px=400).rgb
        n_flat += int(float((rgb.max(-1) - rgb.min(-1)).mean()) < 0.08)
        w.step()
    if n_flat == 0:
        receipt("scans", f"{len(files)} frames · these look GRADED already — the LUT would double-grade them", "warn")
        note("continue anyway?")
        if not yes(False):
            return 0
    else:
        receipt("scans", f"{len(files)} frames · flat (raw colour)" + (" ✓" if n_flat == len(sample) else " · a few look graded"), "ok" if n_flat == len(sample) else "warn")
    out()

    # ◆ film
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
    cube_name, status, honesty = LUTS[stock]
    cube = lut_dir() / cube_name
    if not cube.exists():
        raise FileNotFoundError(str(cube))
    receipt("film", f"{cube_name.split('_')[0]} · {AMBER}{status}{RESET}")
    if borrowed == "other":
        note("most Silbersalz rolls were Vision3, so this starts from the 250D proxy.")
    elif borrowed:
        note(f"no {dict(STOCK_CHOICES)[borrowed]} pairs yet — borrowing the 250D proxy. same Vision3 family, same scan encoding,\n"
             "so it is a fair first pass; real pairs of this stock would replace it. if you have any, please get in touch:\n"
             "https://github.com/atrouwee/saltgate")
    note(honesty)
    out()

    # ◆ upright
    rotations = None
    receipt("upright", "put the frames the right way up automatically?")
    if yes(True):
        if ensure_rotation_deps():
            from . import orient, rebate
            frac = rebate.roll_area_fractions(files, cache_dir=None)
            model = orient.OrientationModel()
            rotations = {}
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
    from . import lut as lutmod, rebate, sheet, orient as orient_mod
    out_dir = folder.parent / f"{folder.name}_saltgate"
    out_dir.mkdir(exist_ok=True)
    lattice = lutmod.read_cube(cube)[0]
    frac = rebate.roll_area_fractions(files, cache_dir=None)
    picks = files[:: max(1, len(files) // 6)][:8]
    receipt("preview", "rendering six frames")
    w = Wedge(6)
    rows = []
    for f in picks:
        a = rebate.crop_to_area(imgio.read_image(f, max_px=900).rgb, frac)
        if rebate.looks_blank(a):
            continue
        if rotations:
            a = orient_mod.apply_rotation(a, rotations[f.name]["k"])
        r = lutmod.apply_trilinear(lattice, a)
        rows.append({"title": f.name, "tiles": [(a, "flat scan", sheet.COLORS["input"]), (r, f"SALTGATE · {stock} · {status}", sheet.COLORS["lut"])]})
        w.step()
        if len(rows) >= 6:
            break
    while w.n < w.total:
        w.step()
    preview = out_dir / "preview.jpg"
    sheet.save_sheet(sheet.build_sheet(rows, tile_h=260), preview, quality=85)
    open_file(preview)
    note(f"opened · {short(preview)}")
    out()

    # ◆ grade
    import shutil as _sh
    already = [f for f in files if (out_dir / f.name).exists()]
    todo = len(files) - len(already)
    free_gb = _sh.disk_usage(out_dir).free / 1e9
    need_gb = todo * 0.035
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

    def log(msg: str) -> None:
        if msg.startswith("  ["):
            name = msg.split("]", 1)[1].strip().split(" ")[0]
            w.step(detail=f"frame {name.split('_')[-1].split('-')[0] if '_' in name else name}")

    keep_awake = None
    if sys.platform == "darwin":
        try:
            keep_awake = subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())])
        except Exception:
            keep_awake = None
    try:
        ap.grade_folder(folder, out_dir, cube, balance_mode="off", resume=True, rotations=rotations, limit=limit, log=lambda m: log(m))
    except Exception as e:
        write_log("grading", repr(e))
        out()
        receipt("stopped", "frames finished so far are kept", "err")
        note(explain(e))
        note("run saltgate again to continue")
        out()
        return 1
    finally:
        if keep_awake is not None:
            keep_awake.terminate()
    if rotations:
        (out_dir / "rotations.json").write_text(json.dumps(rotations, indent=1))
    (out_dir / "saltgate.json").write_text(json.dumps({"source": str(folder), "lut": str(cube), "stock": stock, "film": borrowed or stock, "rotated": bool(rotations)}, indent=1))

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
    state = json.loads(state_path.read_text()); rot_path = out_dir / "rotations.json"
    rotations = json.loads(rot_path.read_text()) if rot_path.exists() else {}
    from . import apply as ap, lut as lutmod, imgio
    src = Path(state["source"]); lattice = lutmod.read_cube(state["lut"])[0]
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
            ap.grade_one(files[n], out_dir / n, lattice, None, "off", 1.0, None, 95, 0.0, new_k)
            receipt("fixed", f"{n} · turned {int(k)} quarter turn(s) anticlockwise", "ok")
    rot_path.write_text(json.dumps(rotations, indent=1))
    return 0
