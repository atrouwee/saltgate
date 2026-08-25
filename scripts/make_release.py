"""Build release/saltgate-luts-<version>.zip: every LUT the tool actually
offers, plus HaldCLUT PNGs, the usage guide and changelog.

The contents are an ALLOWLIST read from `looks.LOOKS` — the same registry the
walkthrough and `saltgate looks` use — so the zip cannot drift from what the
tool offers. This used to filter by filename ("bridged"/"structured"/a
superseded set), which meant any research cube left in luts/ would ship.
"""
import shutil, sys, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from silbersalz_look import looks, lut, __version__

root = Path(__file__).resolve().parents[1]; out = root / "release"; out.mkdir(exist_ok=True)
stage = out / f"saltgate-luts-{__version__}"; shutil.rmtree(stage, ignore_errors=True); stage.mkdir()
SHIPPED = {l.cube for candidates in looks.LOOKS.values() for l in candidates}
absent = sorted(n for n in SHIPPED if not (root / "luts" / n).exists())
if absent:
    sys.exit(f"looks.LOOKS names cubes that are not in luts/: {absent}")
for cube in sorted((root / "luts").glob("*.cube")):
    if cube.name not in SHIPPED:
        continue
    shutil.copy(cube, stage / cube.name)
    side = cube.with_suffix(".stats.json")
    if side.exists():
        shutil.copy(side, stage / side.name)
    lut.write_hald_png(stage / cube.name.replace(".cube", ".hald.png"), lut.read_cube(cube)[0])
shutil.copy(root / "docs/USING_THE_LUTS.md", stage / "USING_THE_LUTS.md")
shutil.copy(root / "luts/CHANGELOG.md", stage / "CHANGELOG.md")
zip_path = out / f"{stage.name}.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for f in stage.iterdir(): z.write(f, f"{stage.name}/{f.name}")
print("wrote", zip_path, [f.name for f in stage.iterdir()])
backbone = out / "orient-resnet50-body-fp16.onnx"
if backbone.exists():
    print(f"orientation backbone: {backbone.name} ({backbone.stat().st_size / 1e6:.1f} MB)")
    notice = out / "THIRD-PARTY-NOTICES.md"
    shutil.copy(root / "THIRD-PARTY-NOTICES.md", notice)
    print(f"attribution: {notice.name} -- upload it ALONGSIDE the model, BSD-3 requires the notice")
    print("upload both as release assets; src/silbersalz_look/orient.py pins the model url and sha256")
else:
    print("orientation backbone MISSING -- run scripts/export_orient_backbone.py before publishing,"
          " or auto-rotation will 404 for everyone on a fresh install")
