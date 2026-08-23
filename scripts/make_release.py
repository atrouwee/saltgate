"""Build release/open-silbersalz-luts-<version>.zip: all paired/provisional
LUTs, HaldCLUT PNGs, the usage guide and changelog."""
import shutil, sys, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from silbersalz_look import lut, __version__

root = Path(__file__).resolve().parents[1]; out = root / "release"; out.mkdir(exist_ok=True)
stage = out / f"open-silbersalz-luts-{__version__}"; shutil.rmtree(stage, ignore_errors=True); stage.mkdir()
for cube in sorted((root / "luts").glob("*.cube")):
    if "bridged" in cube.name or "structured" in cube.name:   # experimental, not shipped
        continue
    shutil.copy(cube, stage / cube.name)
    lut.write_hald_png(stage / cube.name.replace(".cube", ".hald.png"), lut.read_cube(cube)[0])
shutil.copy(root / "docs/USING_THE_LUTS.md", stage / "USING_THE_LUTS.md")
shutil.copy(root / "luts/CHANGELOG.md", stage / "CHANGELOG.md")
zip_path = out / f"{stage.name}.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for f in stage.iterdir(): z.write(f, f"{stage.name}/{f.name}")
print("wrote", zip_path, [f.name for f in stage.iterdir()])
