"""Smoke test of the guided walkthrough on synthetic 'flat scans' — no real photos needed.
Creates 4 milky JPGs with a bright rebate, pipes answers (folder, stock 1, no rotation, yes), checks output."""
import os, subprocess, sys, tempfile
from pathlib import Path
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
answers = f"{scans}\n1\nn\ny\n"
env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"), SALTGATE_NO_OPEN="1")
r = subprocess.run([sys.executable, "-c", "from silbersalz_look.cli import main; raise SystemExit(main([]))"],
                   input=answers, capture_output=True, text=True, env=env, timeout=600)
out = tmp / "01_XXX_saltgate"
ok = r.returncode == 0 and out.exists() and len(list(out.glob("26.*.jpg"))) == 4 and (out / "preview.jpg").exists()
print(r.stdout[-1500:]); print(r.stderr[-800:])
print("SMOKE", "OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
