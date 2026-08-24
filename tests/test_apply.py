"""The grading path: strip-wise LUT application, metadata preservation,
rotation, and the folder driver's resume/limit behaviour.

`grade_one` processes the frame in horizontal strips to bound memory on
147 MP scans. The invariant worth pinning is that striping is invisible in the
output — no seams, no channel drift — and that the lab's ICC/EXIF survive.
"""
import numpy as np
import pytest
from PIL import Image

from silbersalz_look import apply as ap
from silbersalz_look import imgio, lut as lutmod


def _write_jpeg(path, arr_u8, icc=None, exif=None):
    kwargs = {"quality": 98, "subsampling": 0}
    if icc:
        kwargs["icc_profile"] = icc
    if exif:
        kwargs["exif"] = exif
    Image.fromarray(arr_u8, "RGB").save(str(path), "JPEG", **kwargs)


def _gradient(h=900, w=160, seed=0):
    """Tall enough to span several 384-row strips.

    Deliberately SMOOTH: high-frequency noise is destroyed by JPEG, so noisy
    content would make these tests measure the codec instead of the LUT.
    """
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    x = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    phase = 0.7 * seed
    img = np.stack([
        y.repeat(w, 1),
        x.repeat(h, 0),
        0.5 + 0.45 * np.sin(6.0 * (y + x) + phase).repeat(w, 1)[:, :w],
    ], -1)
    return np.clip(np.rint(img * 255), 0, 255).astype(np.uint8)


def test_identity_lut_is_a_no_op_across_strip_boundaries(tmp_path):
    src, dst = tmp_path / "in.jpg", tmp_path / "out.jpg"
    arr = _gradient()
    _write_jpeg(src, arr)
    ap.grade_one(src, dst, lutmod.identity_lattice(33), anchors=None, balance_mode="off")

    got = np.asarray(Image.open(dst).convert("RGB")).astype(np.int16)
    ref = np.asarray(Image.open(src).convert("RGB")).astype(np.int16)
    # only dither (+/-1 LSB) and one JPEG re-encode separate them; a real
    # defect (channel swap, gamma slip, bad strip index) is off by tens
    assert np.abs(got - ref).max() <= 6
    assert np.abs(got - ref).mean() < 1.0
    # and no horizontal seam: row-mean must not jump at a strip boundary
    rows = got.reshape(got.shape[0], -1).mean(1)
    for y0 in range(ap.STRIP_ROWS, got.shape[0], ap.STRIP_ROWS):
        step = abs(rows[y0] - rows[y0 - 1])
        neighbourhood = np.abs(np.diff(rows[max(0, y0 - 20) : y0 + 20])).max()
        assert step <= neighbourhood + 2.0, f"seam at strip boundary row {y0}"


def test_lut_is_actually_applied(tmp_path):
    # a lattice that halves every channel must show up as a halved output
    src, dst = tmp_path / "in.jpg", tmp_path / "out.jpg"
    _write_jpeg(src, _gradient(h=400))
    ap.grade_one(src, dst, (lutmod.identity_lattice(33) * 0.5).astype(np.float32),
                 anchors=None, balance_mode="off")
    ref = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
    got = np.asarray(Image.open(dst).convert("RGB")).astype(np.float32)
    assert np.abs(got - ref * 0.5).max() <= 5


def test_icc_and_exif_survive(tmp_path):
    from PIL import ImageCms
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    exif = Image.Exif()
    exif[271] = "SALTGATE-TEST"      # Make
    src, dst = tmp_path / "in.jpg", tmp_path / "out.jpg"
    _write_jpeg(src, _gradient(h=400), icc=icc, exif=exif.tobytes())

    ap.grade_one(src, dst, lutmod.identity_lattice(33), anchors=None, balance_mode="off")
    out = Image.open(dst)
    assert out.info.get("icc_profile") == icc, "ICC profile lost"
    assert out.getexif().get(271) == "SALTGATE-TEST", "EXIF lost"


def test_rotation_swaps_dimensions(tmp_path):
    pytest.importorskip("cv2")
    src = tmp_path / "in.jpg"
    _write_jpeg(src, _gradient(h=400, w=160))
    for k, expect in [(0, (400, 160)), (1, (160, 400)), (2, (400, 160)), (3, (160, 400))]:
        dst = tmp_path / f"out{k}.jpg"
        ap.grade_one(src, dst, lutmod.identity_lattice(33), anchors=None,
                     balance_mode="off", rotate_k=k)
        assert np.asarray(Image.open(dst)).shape[:2] == expect


def test_density_darkens(tmp_path):
    src = tmp_path / "in.jpg"
    _write_jpeg(src, _gradient(h=400))
    means = {}
    for d in (-0.5, 0.0):
        dst = tmp_path / f"d{d}.jpg"
        ap.grade_one(src, dst, lutmod.identity_lattice(33), anchors=None,
                     balance_mode="off", density=d)
        means[d] = np.asarray(Image.open(dst).convert("RGB")).mean()
    assert means[-0.5] < means[0.0] - 5, "negative density should darken the frame"


def test_grade_folder_limit_and_resume(tmp_path):
    in_dir, out_dir = tmp_path / "in", tmp_path / "out"
    in_dir.mkdir()
    for i in range(4):
        _write_jpeg(in_dir / f"{i:03d}.jpg", _gradient(h=200, seed=i))
    cube = tmp_path / "id.cube"
    lutmod.write_cube(cube, lutmod.identity_lattice(9), "identity")

    res = ap.grade_folder(in_dir, out_dir, cube, workers=1, limit=2)
    assert len(res) == 2 and len(list(out_dir.glob("*.jpg"))) == 2

    # resume must skip what already exists and finish the rest
    res2 = ap.grade_folder(in_dir, out_dir, cube, workers=1, resume=True)
    assert len(res2) == 2
    assert len(list(out_dir.glob("*.jpg"))) == 4


def test_grade_folder_rejects_empty_and_warns_without_anchors(tmp_path, capsys):
    empty, out = tmp_path / "empty", tmp_path / "out"
    empty.mkdir()
    cube = tmp_path / "id.cube"
    lutmod.write_cube(cube, lutmod.identity_lattice(9), "identity")
    with pytest.raises(RuntimeError):
        ap.grade_folder(empty, out, cube, workers=1)

    # balancing asked for but the LUT carries no anchors -> must warn, not fail
    in_dir = tmp_path / "in"; in_dir.mkdir()
    _write_jpeg(in_dir / "a.jpg", _gradient(h=200))
    msgs = []
    ap.grade_folder(in_dir, out, cube, workers=1, balance_mode="exposure", log=msgs.append)
    assert any("no .stats.json anchors" in m for m in msgs)


def test_default_workers_is_bounded():
    n = ap.default_workers()
    assert isinstance(n, int)
    assert 1 <= n <= 4, "workers must stay capped; an 18 GB machine crashed at 7"
