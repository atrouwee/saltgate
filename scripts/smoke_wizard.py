"""Smoke test of the guided walkthrough on synthetic 'flat scans' — no real photos needed.
Creates 4 milky JPGs with a bright rebate, pipes answers (folder, stock 1, no rotation,
look 1, yes), checks output.

HOME *and* USERPROFILE point into the temp dir: the walkthrough remembers the chosen look,
and a smoke test must not rewrite the preference of whoever happens to run it. Windows
reads USERPROFILE and ignores HOME, so setting only HOME redirected nothing there.

Set SALTGATE_SMOKE_CMD=saltgate to run the walkthrough through the installed console
script instead of this interpreter. That is the Windows-shaped test: the grade runs in a
ProcessPoolExecutor, and Windows spawns its workers rather than forking them, so it is the
launcher a user actually types that has to survive being re-entered."""
import json, os, shlex, subprocess, sys, tempfile
from pathlib import Path

# this script prints the walkthrough's own output back out, ░▒▓█ and all, and in
# CI its stdout is a pipe -- which on Windows means the legacy code page
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image

tmp = Path(tempfile.mkdtemp()); scans = tmp / "01_XXX"; scans.mkdir()
rng = np.random.default_rng(0)
for i in range(4):
    h, w = 600, 800
    img = np.full((h, w, 3), 0.97, np.float32)                      # bright film base
    inner = 0.55 + 0.25 * rng.random((h - 60, w - 60, 3)).astype(np.float32)  # milky flat content
    inner = np.clip(inner + rng.normal(0, 0.01, inner.shape), 0, 1); img[30:-30, 30:-30] = inner
    Image.fromarray((img * 255).astype(np.uint8)).save(scans / f"26.00_000_00000G_{i+1:04d}-0004.jpg", quality=92)
answers = f"{scans}\n1\nn\n1\n1\nn\ny\n"   # folder · 250D · no rotation · look · edge · no density · grade
env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"),
           SALTGATE_NO_OPEN="1", SALTGATE_NO_UPDATE="1", HOME=str(tmp), USERPROFILE=str(tmp))
cmd = shlex.split(os.environ["SALTGATE_SMOKE_CMD"]) if os.environ.get("SALTGATE_SMOKE_CMD") else \
      [sys.executable, "-c", "from silbersalz_look.cli import main; raise SystemExit(main([]))"]
print("running:", " ".join(cmd))
# not text=True: that decodes the child with the machine's locale encoding, and
# on Windows the walkthrough deliberately writes utf-8 down a redirected pipe.
r = subprocess.run(cmd, input=answers, capture_output=True, encoding="utf-8", errors="replace",
                   env=env, timeout=600)
out = tmp / "01_XXX_saltgate"
state = out / "saltgate.json"
ok = (r.returncode == 0 and out.exists() and len(list(out.glob("26.*.jpg"))) == 4
      and (out / "preview.jpg").exists()
      # every optional step must be reachable AND skippable: the look choice and
      # the per-roll density both land in saltgate.json, so a step that silently
      # stopped appearing would fail here rather than in someone's terminal
      and state.exists() and {"look", "density", "bits", "edge"} <= set(json.loads(state.read_text(encoding="utf-8"))))
print(r.stdout[-1500:]); print(r.stderr[-800:])
print("SMOKE", "OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
