"""A 16-bit JXL source must decode at 16-bit precision (more than 256 distinct values)."""
import numpy as np
import imagecodecs

from silbersalz_look import imgio


def test_jxl_16bit_roundtrip(tmp_path):
    rng = np.random.default_rng(0)
    ramp = np.linspace(0, 65535, 2048, dtype=np.uint16)
    img = np.stack([ramp] * 3, axis=-1)[None].repeat(8, axis=0)   # 8 x 2048 x 3 uint16 ramp
    p = tmp_path / "ramp.jxl"
    p.write_bytes(imagecodecs.jpegxl_encode(img, lossless=True))
    d = imgio.read_image(p)
    assert d.bit_depth == 16
    assert len(np.unique((d.rgb[..., 1] * 65535).round())) > 1000
