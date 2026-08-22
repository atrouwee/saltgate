"""Decide the upright rotation of every frame in a folder, write
rotations.json next to the frames (or --out), and render a review sheet
where low-confidence decisions are marked for manual correction.

  python scripts/auto_rotate.py --in FLATDIR [--out rotations.json] [--sheet sheet.jpg]
  python scripts/auto_rotate.py --set rotations.json 0026=1 0031=2   # manual fixes (k = 90deg CCW steps)
"""
import argparse, json, sys, time
from pathlib import Path
import numpy as np, cv2
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from silbersalz_look import imgio, rebate, orient

ap = argparse.ArgumentParser()
ap.add_argument("--in", dest="in_dir"); ap.add_argument("--out", default=None); ap.add_argument("--sheet", default=None)
ap.add_argument("--preview", type=int, default=900); ap.add_argument("--set", nargs="+", default=None)
ap.add_argument("--cache", default="cache"); ap.add_argument("--lut", default="luts/silbersalz-250d_v0-statistical_33.cube", help="LUT used only to make the review sheet legible")
a = ap.parse_args()

if a.set:
    path = Path(a.set[0]); rot = json.loads(path.read_text())
    for kv in a.set[1:]:
        key, k = kv.split("="); 
        for name in rot:
            if key in name: rot[name]["k"] = int(k) % 4; rot[name]["confidence"] = 1.0; rot[name]["manual"] = True
    path.write_text(json.dumps(rot, indent=1)); print("updated", path); sys.exit(0)

in_dir = Path(a.in_dir); out = Path(a.out) if a.out else in_dir.parent / f"rotations_{in_dir.name}.json"
files = [f for f in imgio.list_images(in_dir) if f.suffix.lower() in (".jpg", ".jpeg")]
frac = rebate.roll_area_fractions(files, cache_dir=Path(a.cache))
model = orient.OrientationModel()
lat, anchors = None, None
if a.sheet and a.lut and Path(a.lut).exists():
    from silbersalz_look import lut as _lut, balance as _bal
    lat = _lut.read_cube(a.lut)[0]; anchors = _lut.read_stats_sidecar(a.lut)["balance_anchors"]
rot, thumbs = {}, []
t0 = time.time()
for i, f in enumerate(files):
    area = rebate.crop_to_area(imgio.read_image(f, max_px=a.preview).rgb, frac)
    if rebate.looks_blank(area):
        rot[f.name] = {"k": 0, "confidence": 1.0, "blank": True}
    else:
        rot[f.name] = model.predict(area)
    s = 200 / max(area.shape[:2])
    if lat is not None and not rebate.looks_blank(area):
        area = _lut.apply_trilinear(lat, _bal.apply_gains(area, _bal.estimate_gains(area, anchors)))
    thumbs.append(cv2.resize(area, (max(8, round(area.shape[1] * s)), max(8, round(area.shape[0] * s))), interpolation=cv2.INTER_AREA))
    if (i + 1) % 20 == 0: print(f"  {i+1}/{len(files)} ({time.time()-t0:.0f}s)", flush=True)
out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(rot, indent=1))
low = [n for n, r in rot.items() if r.get("confidence", 1) < 0.5 and not r.get("blank")]
print(f"wrote {out}: {len(files)} frames, {len(low)} low-confidence (review): {', '.join(n.split('_')[-1].split('-')[0] for n in low)}")

if a.sheet:
    cols, TH = 8, 200
    tiles = []
    for f, t in zip(files, thumbs):
        r = rot[f.name]; up = orient.apply_rotation(t, r["k"])
        canvas = np.full((TH + 22, TH + 6, 3), 0.1, np.float32)
        h, w = up.shape[:2]; s = min(TH / h, TH / w)
        up = cv2.resize(up, (max(8, round(w * s)), max(8, round(h * s))), interpolation=cv2.INTER_AREA)
        canvas[22:22 + up.shape[0], 3:3 + up.shape[1]] = up
        tiles.append(canvas)
    rows = int(np.ceil(len(tiles) / cols))
    sheet = np.full((rows * (TH + 26), cols * (TH + 10), 3), 0.1, np.float32)
    for i, t in enumerate(tiles):
        r_, c_ = divmod(i, cols); sheet[r_ * (TH + 26):r_ * (TH + 26) + t.shape[0], c_ * (TH + 10):c_ * (TH + 10) + t.shape[1]] = t
    img = Image.fromarray((np.clip(sheet, 0, 1) * 255).astype(np.uint8)); d = ImageDraw.Draw(img)
    for i, f in enumerate(files):
        r_, c_ = divmod(i, cols); r = rot[f.name]
        tag = f.name.split("_")[-1].split("-")[0]
        col = (80, 220, 120) if r.get("confidence", 1) >= 0.5 else (255, 80, 80)
        d.rectangle([c_ * (TH + 10), r_ * (TH + 26), c_ * (TH + 10) + 120, r_ * (TH + 26) + 18], fill=col)
        d.text((c_ * (TH + 10) + 3, r_ * (TH + 26) + 3), f"{tag}  k={r['k']}  {r.get('confidence', 1):.2f}", fill=(0, 0, 0))
    Path(a.sheet).parent.mkdir(parents=True, exist_ok=True); img.save(a.sheet, quality=85); print("sheet:", a.sheet, "(red = review)")
