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
    from . import imgio, rebate
    sample = files[:: max(1, len(files) // 6)][:6]
    n_flat = 0
    for f in sample:
        rgb = imgio.read_image(f, max_px=400).rgb
        sat = float((rgb.max(-1) - rgb.min(-1)).mean())
        n_flat += int(sat < 0.08)
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
    uv = subprocess.run(["which", "uv"], capture_output=True, text=True).stdout.strip()
    cmd = ([uv, "tool", "install", "--force", "saltgate[rotate] @ git+https://github.com/atrouwee/saltgate.git"] if uv
           else [sys.executable, "-m", "pip", "install", "--quiet", "torch", "torchvision"])
    say(f"{DIM}Installing… this can take a few minutes.{RESET}")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        say(f"{RED}The download didn't work. Continuing without orientation — you can try again later.{RESET}")
        return False
    try:
        import torch, torchvision  # noqa: F401
        return True
    except ImportError:
        say(f"{YELLOW}Installed, but it needs a restart: run `saltgate` again to use orientation.{RESET}")
        return False


def run() -> int:
    say(f"\n{BOLD}SALTGATE{RESET} — finish your flat SILBERSALZ scans.")
    say(f"{DIM}The name is a wink. The work is sincere. Your originals are never modified.{RESET}\n")

    # 1. folder
    while True:
        raw = ask("Where are your scans? Drag the folder into this window and press Enter:")
        folder = clean_path(raw)
        if folder.is_dir():
            break
        say(f"{YELLOW}I can't find a folder there. Try dragging it from Finder.{RESET}")
    from . import imgio
    files = [f for f in imgio.list_images(folder) if f.suffix.lower() in (".jpg", ".jpeg")]
    if not files:
        say(f"{RED}No JPG files in that folder. The LUTs work on the lab's JPG 'raw colour' scans.{RESET}")
        return 1
    n_flat, n_checked = looks_flat(files)
    say(f"\nFound {BOLD}{len(files)}{RESET} JPG frames.", )
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
            say(f"{DIM}Looking at each frame… (~1 s per frame){RESET}")
            frac = rebate.roll_area_fractions(files, cache_dir=None)
            model = orient.OrientationModel()
            rotations = {}
            for i, f in enumerate(files):
                area = rebate.crop_to_area(imgio.read_image(f, max_px=900).rgb, frac)
                rotations[f.name] = {"k": 0, "confidence": 1.0} if rebate.looks_blank(area) else model.predict(area)
                if (i + 1) % 25 == 0:
                    say(f"{DIM}  {i + 1}/{len(files)}{RESET}")
            low = sum(1 for r in rotations.values() if r.get("confidence", 1) < 0.5)
            say(f"{GREEN}Done.{RESET} {low} frames were hard to judge; check them on the preview and in the result.")

    # 4. preview
    out_dir = folder.parent / f"{folder.name}_saltgate"
    out_dir.mkdir(exist_ok=True)
    from . import lut as lutmod, rebate, sheet, orient as orient_mod
    lattice = lutmod.read_cube(cube)[0]
    frac = rebate.roll_area_fractions(files, cache_dir=None)
    picks = [f for f in files[:: max(1, len(files) // 6)][:8]]
    rows = []
    say(f"\n{DIM}Rendering a preview of 6 frames…{RESET}")
    for f in picks:
        a = rebate.crop_to_area(imgio.read_image(f, max_px=900).rgb, frac)
        if rebate.looks_blank(a):
            continue
        if rotations:
            a = orient_mod.apply_rotation(a, rotations[f.name]["k"])
        r = lutmod.apply_trilinear(lattice, a)
        rows.append({"title": f.name, "tiles": [(a, "flat scan", sheet.COLORS["input"]), (r, f"SALTGATE · {stock} · {status}", sheet.COLORS["lut"])]})
        if len(rows) >= 6:
            break
    preview = out_dir / "preview.jpg"
    sheet.save_sheet(sheet.build_sheet(rows, tile_h=260), preview, quality=85)
    open_file(preview)
    say(f"Preview saved and opened: {preview}")
    if not yes(f"\nHappy with it? Grade all {len(files)} frames into {out_dir.name}/?", default=True):
        say(f"{DIM}Okay — nothing else was written. The preview stays in {out_dir}.{RESET}")
        return 0

    # 5. batch
    from . import apply as ap
    t0 = time.time()
    done = [0]
    def log(msg: str) -> None:
        if msg.startswith("  ["):
            done[0] += 1
            if done[0] % 10 == 0 or done[0] == len(files):
                say(f"{DIM}  {done[0]}/{len(files)} frames ({time.time() - t0:.0f}s){RESET}")
    try:
        ap.grade_folder(folder, out_dir, cube, balance_mode="off", resume=True, rotations=rotations, log=log)
    except Exception as e:  # never show a traceback to this audience
        say(f"{RED}Something went wrong while grading: {e}{RESET}")
        say("Frames finished so far are in the output folder; run `saltgate` again to continue (it resumes).")
        return 1
    if rotations:
        (out_dir / "rotations.json").write_text(json.dumps(rotations, indent=1))
    say(f"\n{GREEN}{BOLD}Done.{RESET} {len(files)} graded frames are in {out_dir}")
    say("They are JPEGs tagged Display P3, with the original EXIF, ready for Capture One / Lightroom / anything.")
    say(f"\n{DIM}If you ever receive the lab's graded versions of these frames, keep both: flat + graded pairs make this better for everyone.")
    say(f"https://github.com/atrouwee/saltgate{RESET}\n")
    open_file(out_dir)
    return 0
