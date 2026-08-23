"""The guided walkthrough: `saltgate` with no arguments.

Plain prompts, no tracebacks, nothing written next to the originals except a
new `<folder>_saltgate/` directory. Designed for people who have never used a
terminal: drag the folder in, answer three questions, look at a preview.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

BOLD, DIM, GREEN, YELLOW, RED, RESET = "\033[1m", "\033[2m", "\033[32m", "\033[33m", "\033[31m", "\033[0m"

# stock -> (LUT file, status label, one-line honesty)
LUTS = {
    "250d": ("silbersalz-250d_v0-statistical_33.cube", "PROVISIONAL",
             "a statistical approximation of the 250D look — close in tone, skin a little light, skies a little dark. Real 250D pairs will replace it."),
    "gold200": ("silbersalz-gold200_v1-paired_33.cube", "BETA",
                "fitted from 27 real flat/graded pairs (one donor, two rolls). Close to the lab on its own rolls; other rolls may need a small exposure nudge."),
}
STOCK_CHOICES = [("250d", "Kodak Vision3 250D (Silbersalz daylight film)"), ("gold200", "Kodak Gold 200 (C-41)"),
                 ("50d", "Vision3 50D"), ("200t", "Vision3 200T"), ("500t", "Vision3 500T"), ("125special", "Silbersalz 125 Special"), ("other", "Something else / I don't know")]
LAB_STOCK_CODES = {"XXX": "250d"}   # codes seen in the lab's *_Exported.json; extend as we learn them


def say(msg: str = "") -> None:
    print(msg, flush=True)


def working(msg: str) -> None:
    """Immediate feedback before anything that takes more than a second."""
    print(f"{DIM}{msg}{RESET}", flush=True)


class Progress:
    """Single updating line: label  done/total · ~N min left."""

    def __init__(self, label: str, total: int):
        self.label, self.total, self.t0, self.n = label, total, time.time(), 0
        self._draw()

    def step(self, n: int = 1) -> None:
        self.n += n
        self._draw()

    def _draw(self) -> None:
        rate = (time.time() - self.t0) / max(self.n, 1)
        left = rate * (self.total - self.n) if self.n else 0
        eta = "" if self.n == 0 else (f" · about {max(1, round(left / 60))} min left" if left > 50 else f" · {int(left)} s left")
        bar = "#" * int(24 * self.n / max(self.total, 1)) + "-" * (24 - int(24 * self.n / max(self.total, 1)))
        print(f"\r{DIM}{self.label}  [{bar}] {self.n}/{self.total}{eta}   {RESET}", end="", flush=True)
        if self.n >= self.total:
            print(flush=True)


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" {DIM}[{default}]{RESET}" if default else ""
    try:
        ans = input(f"{BOLD}{prompt}{RESET}{suffix} ").strip()
    except (EOFError, KeyboardInterrupt):
        say(f"\n{DIM}Okay, stopping here. Nothing was changed.{RESET}")
        sys.exit(0)
    return ans or (default or "")


def yes(prompt: str, default: bool = True) -> bool:
    ans = ask(prompt + (" (Y/n)" if default else " (y/N)")).lower()
    return default if not ans else ans.startswith("y")


def choose(prompt: str, options: list[tuple[str, str]], default_idx: int = 0) -> str:
    say(f"{BOLD}{prompt}{RESET}")
    for i, (_, label) in enumerate(options, 1):
        say(f"  {i}) {label}")
    while True:
        ans = ask("Type a number", str(default_idx + 1))
        if ans.isdigit() and 1 <= int(ans) <= len(options):
            return options[int(ans) - 1][0]
        say(f"{YELLOW}Please type a number between 1 and {len(options)}.{RESET}")


def clean_path(raw: str) -> Path:
    p = raw.strip().strip("'\"").replace("\\ ", " ")
    return Path(os.path.expanduser(p))


def open_file(path: Path) -> None:
    if os.environ.get("SALTGATE_NO_OPEN"):   # tests / headless runs
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


def lut_dir() -> Path:
    here = Path(__file__).resolve()
    for cand in (here.parents[2] / "luts", here.parent / "luts"):
        if cand.exists():
            return cand
    return here.parents[2] / "luts"


def detect_stock_from_sidecars(folder: Path) -> str | None:
    for d in (folder, folder.parent):
        for js in d.glob("*Exported.json"):
            try:
                data = json.loads(js.read_text())
                code = str(data.get("Film_1_Stock", "")).strip()
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


def looks_flat(files: list[Path]) -> tuple[int, int]:
    """(n_flat_looking, n_checked) via mean saturation of a few previews."""
    from . import imgio
    sample = files[:: max(1, len(files) // 6)][:6]
    n_flat = 0
    prog = Progress("Looking at a few frames", len(sample))
    for f in sample:
        rgb = imgio.read_image(f, max_px=400).rgb
        sat = float((rgb.max(-1) - rgb.min(-1)).mean())
        n_flat += int(sat < 0.08)
        prog.step()
    return n_flat, len(sample)


def ensure_rotation_deps() -> bool:
    try:
        import torch, torchvision  # noqa: F401
        return True
    except ImportError:
        pass
    say(f"{YELLOW}Orientation needs two extra libraries (about 200 MB, one-time download).{RESET}")
    if not yes("Download them now?", default=True):
        return False
    # Install INTO the environment we are running in (never reinstall the tool itself).
    import shutil
    uv = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
    if Path(uv).exists():
        cmd = [uv, "pip", "install", "--python", sys.executable, "torch", "torchvision"]
    else:
        cmd = [sys.executable, "-m", "pip", "install", "--quiet", "torch", "torchvision"]
    say(f"{DIM}Installing… this can take a few minutes (about 200 MB).{RESET}")
    import threading
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    t0 = time.time()
    spinner = "|/-\\"
    i = 0
    while proc.poll() is None:
        print(f"\r{DIM}  {spinner[i % 4]} downloading and installing… {int(time.time() - t0)} s{RESET}   ", end="", flush=True)
        i += 1
        time.sleep(0.5)
    print("\r" + " " * 60 + "\r", end="", flush=True)
    out = proc.stdout.read() if proc.stdout else ""

    class _R:  # minimal stand-in for subprocess.run's result
        returncode = proc.returncode; stdout = out; stderr = ""
    r = _R()
    if r.returncode != 0:
        log_path = write_log("rotation-install", r.stdout + "\n" + r.stderr)
        say(f"{RED}The download didn't work. Continuing without orientation — you can try again later.{RESET}")
        say(f"{DIM}Details saved to {log_path}{RESET}")
        return False
    import importlib
    importlib.invalidate_caches()
    try:
        import torch, torchvision  # noqa: F401
        from . import orient
        orient.OrientationModel()   # fail here, not mid-roll, if anything is missing
        return True
    except Exception:
        say(f"{YELLOW}Installed, but it needs a restart: run `saltgate` again to use orientation.{RESET}")
        return False


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
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    try:
        import cv2
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
    except Exception:
        pass


def run() -> int:
    """Entry point with a safety net: never show a traceback, always save one."""
    quiet_libraries()
    try:
        return _run()
    except KeyboardInterrupt:
        say(f"\n{DIM}Stopped. Frames finished so far are kept; run `saltgate` again to continue where you left off.{RESET}")
        return 130
    except SystemExit:
        raise
    except Exception as e:
        import traceback
        log_path = write_log("error", traceback.format_exc())
        say(f"\n{RED}Something went wrong and I stopped. Nothing of yours was modified.{RESET}")
        say(f"{BOLD}{explain(e)}{RESET}")
        say(f"{DIM}Details are saved in {log_path} — attach that file if you report it: https://github.com/atrouwee/saltgate/issues{RESET}\n")
        return 1


def explain(e: Exception) -> str:
    """One plain sentence about what went wrong and what to do."""
    name = type(e).__name__
    msg = str(e)
    if isinstance(e, (ImportError, ModuleNotFoundError)):
        return "Part of the installation is missing. Re-run the installer line from the README, then try again."
    if isinstance(e, PermissionError):
        return "I'm not allowed to write next to your scans (read-only disk or folder?). Copy the folder somewhere like your Desktop and try again."
    if isinstance(e, OSError) and ("No space" in msg or getattr(e, "errno", None) == 28):
        return "The disk is full. Graded frames need roughly 30 MB each; free some space and run again — it continues where it stopped."
    if isinstance(e, FileNotFoundError):
        return "A file disappeared while I was working (moved, renamed, or a disconnected drive). Check the folder and run again."
    if isinstance(e, MemoryError):
        return "The computer ran out of memory. Close other apps and run again — it continues where it stopped."
    if "CUDA" in msg or "torch" in msg.lower():
        return "The orientation step hit a problem. Run again and answer 'n' to the orientation question to grade without it."
    return f"Unexpected problem ({name}). Running again usually helps; it continues where it stopped."


def check_for_update() -> None:
    """One quick request; silent when offline."""
    try:
        import urllib.request
        from . import __version__
        with urllib.request.urlopen("https://raw.githubusercontent.com/atrouwee/saltgate/main/pyproject.toml", timeout=2) as r:
            txt = r.read().decode()
        latest = txt.split('version = "', 1)[1].split('"', 1)[0]
        if latest != __version__:
            say(f"{YELLOW}A newer version ({latest}) is available — you have {__version__}. To update, paste the installer line from the README again.{RESET}\n")
    except Exception:
        pass


def fix_rotation(args: list[str]) -> int:
    """saltgate fix-rotation <output folder> 0026=1 0031=2 — re-grade those frames from the originals with a new orientation."""
    if len(args) < 2:
        say("Usage: saltgate fix-rotation <graded folder> <frame>=<quarter turns> …   e.g. 0026=1"); return 1
    out_dir = clean_path(args[0])
    state_path = out_dir / "saltgate.json"
    if not state_path.exists():
        say(f"{RED}That folder wasn't made by the walkthrough (no saltgate.json inside).{RESET}"); return 1
    state = json.loads(state_path.read_text()); rot_path = out_dir / "rotations.json"
    rotations = json.loads(rot_path.read_text()) if rot_path.exists() else {}
    from . import apply as ap, lut as lutmod, lut, rebate, imgio, orient
    src = Path(state["source"]); lattice = lutmod.read_cube(state["lut"])[0]
    files = {f.name: f for f in imgio.list_images(src) if f.suffix.lower() in (".jpg", ".jpeg")}
    for spec in args[1:]:
        if "=" not in spec:
            say(f"{YELLOW}Skipping '{spec}' — write it as 0026=1{RESET}"); continue
        tag, k = spec.split("=", 1)
        matches = [n for n in files if f"_{tag}-" in n or n.startswith(tag)]
        if not matches:
            say(f"{YELLOW}No frame matching '{tag}'.{RESET}"); continue
        for n in matches:
            cur = rotations.get(n, {}).get("k", 0)
            new_k = (cur + int(k)) % 4
            rotations[n] = {"k": new_k, "confidence": 1.0, "manual": True}
            ap.grade_one(files[n], out_dir / n, lattice, None, "off", 1.0, None, 95, 0.0, new_k)
            say(f"{GREEN}re-graded {n} turned {int(k)} quarter turn(s) anticlockwise{RESET}")
    rot_path.write_text(json.dumps(rotations, indent=1))
    return 0


def _run() -> int:
    say(f"\n{BOLD}SALTGATE{RESET} — finish your flat SILBERSALZ scans.")
    say(f"{DIM}The name is a wink. The work is sincere. Your originals are never modified.{RESET}\n")
    check_for_update()

    # 1. folder
    from . import imgio
    while True:
        raw = ask("Where are your scans? Drag the folder into this window and press Enter:")
        folder = clean_path(raw)
        if folder.is_file():
            say(f"{YELLOW}That's a single file — please drag the whole folder that contains your scans.{RESET}")
            continue
        if not folder.is_dir():
            say(f"{YELLOW}I can't find a folder there. Try dragging it from Finder.{RESET}")
            continue
        files = [f for f in imgio.list_images(folder) if f.suffix.lower() in (".jpg", ".jpeg")]
        if not files:
            # maybe they dragged the delivery folder that CONTAINS the scan folder(s)
            subs = [d for d in sorted(folder.iterdir()) if d.is_dir() and not d.name.startswith(".")
                    and any(f.suffix.lower() in (".jpg", ".jpeg") for f in imgio.list_images(d))]
            if subs:
                say(f"No JPGs directly in that folder, but these folders inside it have some:")
                choice = choose("Which one are the flat scans?", [(str(d), f"{d.name}  ({len([f for f in imgio.list_images(d) if f.suffix.lower() in ('.jpg', '.jpeg')])} JPGs)") for d in subs])
                folder = Path(choice); files = [f for f in imgio.list_images(folder) if f.suffix.lower() in (".jpg", ".jpeg")]
            else:
                others = [f.suffix.lower() for f in imgio.list_images(folder)]
                if any(x in (".jxl", ".jp2") for x in others):
                    say(f"{YELLOW}This folder holds the lab's 16-bit files (.jxl/.jp2) — those are the GRADED deliveries. The LUT is for the raw JPG scans (usually named …_RAW_COLOR.jpg).{RESET}")
                else:
                    say(f"{YELLOW}No JPG files in that folder. The LUTs work on the lab's JPG 'raw colour' scans.{RESET}")
                continue
        raw_named = [f for f in files if "RAW" in f.name.upper()]
        graded_named = [f for f in files if f.name.upper().endswith("_HIGH.JPG") and "RAW" not in f.name.upper()]
        if raw_named and graded_named:
            say(f"This folder has both raw ({len(raw_named)}) and graded ({len(graded_named)}) files — using the raw ones.")
            files = raw_named
        break
    say(f"\nFound {BOLD}{len(files)}{RESET} JPG frames.")
    n_flat, n_checked = looks_flat(files)
    if n_flat == 0:
        say(f"{YELLOW}These don't look like flat scans — they already seem graded. The LUT would double-grade them.{RESET}")
        if not yes("Continue anyway?", default=False):
            return 0
    elif n_flat < n_checked // 2:
        say(f"{YELLOW}Several frames look graded rather than flat; results may vary for those.{RESET}")
    else:
        say(f"{GREEN}They look like flat (raw colour) scans — good.{RESET}")

    # 2. stock
    detected = detect_stock_from_sidecars(folder)
    if detected:
        label = dict(STOCK_CHOICES).get(detected, detected)
        say(f"\nThe lab's sidecar file says this roll is {BOLD}{label}{RESET}.")
        stock = detected if yes("Is that right?", default=True) else choose("Which film was it?", STOCK_CHOICES)
    else:
        say("")
        stock = choose("Which film was this roll?", STOCK_CHOICES)
    if stock not in LUTS:
        say(f"\n{YELLOW}There is no LUT for this stock yet.{RESET} It needs real flat + graded pairs of the same frames.")
        say("If you have any, you can help: https://github.com/atrouwee/saltgate/blob/main/docs/DONATING_PAIRS.md")
        say("More pairs, less guesswork.")
        return 0
    cube_name, status, honesty = LUTS[stock]
    cube = lut_dir() / cube_name
    if not cube.exists():
        say(f"{RED}LUT file missing: {cube}{RESET}"); return 1
    say(f"\nUsing {BOLD}{cube_name}{RESET} — status {BOLD}{status}{RESET}: {honesty}")

    # 3. orientation
    rotations = None
    say("")
    if yes("Also put the frames upright automatically? (the lab delivers them in film-strip orientation)", default=True):
        if ensure_rotation_deps():
            from . import orient, rebate
            working("Loading the orientation model…")
            frac = rebate.roll_area_fractions(files, cache_dir=None)
            model = orient.OrientationModel()
            rotations = {}
            prog = Progress("Working out which way is up", len(files))
            for f in files:
                area = rebate.crop_to_area(imgio.read_image(f, max_px=900).rgb, frac)
                rotations[f.name] = {"k": 0, "confidence": 1.0} if rebate.looks_blank(area) else model.predict(area)
                prog.step()
            low = sum(1 for r in rotations.values() if r.get("confidence", 1) < 0.5)
            say(f"{GREEN}Done.{RESET} {low} frames were hard to judge; check them on the preview and in the result.")

    # 4. preview
    out_dir = folder.parent / f"{folder.name}_saltgate"
    out_dir.mkdir(exist_ok=True)
    from . import lut as lutmod, rebate, sheet, orient as orient_mod
    lattice = lutmod.read_cube(cube)[0]
    working("Measuring the frame borders…")
    frac = rebate.roll_area_fractions(files, cache_dir=None)
    picks = [f for f in files[:: max(1, len(files) // 6)][:8]]
    rows = []
    say("")
    prog = Progress("Rendering a preview of 6 frames", min(6, len(picks)))
    for f in picks:
        a = rebate.crop_to_area(imgio.read_image(f, max_px=900).rgb, frac)
        if rebate.looks_blank(a):
            continue
        if rotations:
            a = orient_mod.apply_rotation(a, rotations[f.name]["k"])
        r = lutmod.apply_trilinear(lattice, a)
        rows.append({"title": f.name, "tiles": [(a, "flat scan", sheet.COLORS["input"]), (r, f"SALTGATE · {stock} · {status}", sheet.COLORS["lut"])]})
        prog.step()
        if len(rows) >= 6:
            break
    while prog.n < prog.total:
        prog.step()
    preview = out_dir / "preview.jpg"
    sheet.save_sheet(sheet.build_sheet(rows, tile_h=260), preview, quality=85)
    open_file(preview)
    say(f"Preview saved and opened: {preview}")
    already = [f for f in files if (out_dir / f.name).exists()]
    todo = len(files) - len(already)
    import shutil as _sh
    free_gb = _sh.disk_usage(out_dir).free / 1e9
    need_gb = todo * 0.035
    mins = max(1, round(todo * 25 / 60))
    say(f"\nThis will take about {BOLD}{mins} minute{'s' if mins != 1 else ''}{RESET} and roughly {need_gb:.1f} GB of disk space ({free_gb:.0f} GB free).")
    if already:
        say(f"{DIM}{len(already)} frames were already graded earlier and will be kept.{RESET}")
    if need_gb > free_gb:
        say(f"{RED}Not enough free disk space. Free up about {need_gb - free_gb + 1:.0f} GB and run again.{RESET}")
        return 1
    if not yes(f"Happy with the preview? Grade {todo} frames into {out_dir.name}/?", default=True):
        say(f"{DIM}Okay — nothing else was written. The preview stays in {out_dir}.{RESET}")
        return 0

    # 5. batch
    from . import apply as ap
    prog = Progress("Grading", todo)
    def log(msg: str) -> None:
        if msg.startswith("  ["):
            prog.step()
    try:
        ap.grade_folder(folder, out_dir, cube, balance_mode="off", resume=True, rotations=rotations, log=log)
    except Exception as e:  # never show a traceback to this audience
        say(f"{RED}Something went wrong while grading: {e}{RESET}")
        say("Frames finished so far are in the output folder; run `saltgate` again to continue (it resumes).")
        return 1
    if rotations:
        (out_dir / "rotations.json").write_text(json.dumps(rotations, indent=1))
    (out_dir / "saltgate.json").write_text(json.dumps({"source": str(folder), "lut": str(cube), "stock": stock, "rotated": bool(rotations)}, indent=1))
    say(f"\n{GREEN}{BOLD}Done.{RESET} {len(files)} graded frames are in {out_dir}")
    if rotations:
        say(f"{DIM}A frame the wrong way up? Type:  saltgate fix-rotation \"{out_dir}\" 0026=1   (frame number = quarter turns anticlockwise: 1, 2 or 3){RESET}")
    say("They are JPEGs tagged Display P3, with the original EXIF, ready for Capture One / Lightroom / anything.")
    say(f"\n{DIM}If you ever receive the lab's graded versions of these frames, keep both: flat + graded pairs make this better for everyone.")
    say(f"https://github.com/atrouwee/saltgate{RESET}\n")
    open_file(out_dir)
    return 0
