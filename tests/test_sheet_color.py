import numpy as np
from PIL import Image

from silbersalz_look import color, sheet


def test_sheet_embeds_srgb_profile_and_converts(tmp_path):
    # a saturated P3 green: in sRGB it must be clipped/less saturated, and the file tagged sRGB
    tile = np.zeros((20, 30, 3), np.float32); tile[..., 1] = 0.9; tile[..., 0] = 0.2; tile[..., 2] = 0.2
    img = sheet.build_sheet([{"title": "t", "tiles": [(tile, "x", None)]}], tile_h=20)
    out = tmp_path / "s.jpg"; sheet.save_sheet(img, out)
    im = Image.open(out)
    assert im.info.get("icc_profile"), "no ICC profile embedded"
    from PIL import ImageCms
    import io
    desc = ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(io.BytesIO(im.info["icc_profile"])))
    assert "sRGB" in desc
    expected = color.convert_p3_to_srgb(np.array([[0.2, 0.9, 0.2]]))[0]
    got = np.asarray(im)[40, 15] / 255.0   # inside the tile (below the 30px title bar)
    assert np.abs(got - expected).max() < 0.04


def test_p3_to_srgb_known_values():
    # neutral grey is unchanged; pure P3 red maps to an out-of-gamut (clipped) sRGB red
    grey = color.convert_p3_to_srgb(np.array([[0.5, 0.5, 0.5]]))[0]
    assert np.allclose(grey, 0.5, atol=2e-3)
    red = color.convert_p3_to_srgb(np.array([[1.0, 0.0, 0.0]]))[0]
    assert red[0] > 0.99 and red[1] < 0.05
