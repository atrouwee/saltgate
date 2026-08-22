import numpy as np

from silbersalz_look import lut


def test_roundtrip_bit_identical(tmp_path):
    lattice = lut.identity_lattice(17)
    rng = np.random.default_rng(1)
    lattice = np.clip(lattice + rng.normal(0, 0.02, lattice.shape), 0, 1).astype(
        np.float32
    )
    p = tmp_path / "t.cube"
    lut.write_cube(p, lattice, "test")
    back, title = lut.read_cube(p)
    assert title == "test"
    assert np.allclose(back, lattice, atol=1e-6)


def test_axis_order_against_hand_computed_2cube(tmp_path):
    # 2^3 identity: .cube iterates red fastest, so line order is
    # (r,g,b) = 000,100,010,110,001,101,011,111 -> outputs equal the coords.
    lattice = lut.identity_lattice(2)
    p = tmp_path / "id2.cube"
    lut.write_cube(p, lattice, "id2")
    data_lines = [
        l
        for l in p.read_text().splitlines()
        if l and not l.startswith(("#", "TITLE", "LUT", "DOMAIN"))
    ]
    expect = [
        (0, 0, 0),
        (1, 0, 0),
        (0, 1, 0),
        (1, 1, 0),
        (0, 0, 1),
        (1, 0, 1),
        (0, 1, 1),
        (1, 1, 1),
    ]
    got = [tuple(float(v) for v in l.split()) for l in data_lines]
    assert got == [tuple(float(v) for v in e) for e in expect]


def test_trilinear_identity():
    lattice = lut.identity_lattice(33)
    rng = np.random.default_rng(2)
    rgb = rng.random((1000, 3)).astype(np.float32)
    out = lut.apply_trilinear(lattice, rgb)
    assert np.allclose(out, rgb, atol=1e-5)


def test_trilinear_matches_interpn():
    from scipy.interpolate import RegularGridInterpolator

    rng = np.random.default_rng(3)
    n = 9
    lattice = np.clip(
        lut.identity_lattice(n) + rng.normal(0, 0.05, (n, n, n, 3)), 0, 1
    ).astype(np.float32)
    rgb = rng.random((500, 3)).astype(np.float32)
    ours = lut.apply_trilinear(lattice, rgb)
    ax = np.linspace(0, 1, n)
    for c in range(3):
        ref = RegularGridInterpolator((ax, ax, ax), lattice[..., c])(rgb)
        assert np.allclose(ours[:, c], ref, atol=1e-5)
