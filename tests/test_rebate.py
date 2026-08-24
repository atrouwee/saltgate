"""Film-border (rebate) detection and frame classification.

The regression that matters historically: the detector originally assumed a
DARK rebate, which is true of graded scans but not of flats, where the film
base reads near-white. Both polarities are tested here.
"""
import numpy as np

from silbersalz_look import rebate


def _frame(border_level, content_seed=0, w=400, h=300, bx=60, by=40):
    """Synthetic scan: a uniform border of `border_level` around textured content."""
    rng = np.random.default_rng(content_seed)
    img = np.full((h, w, 3), border_level, np.float32)
    content = rng.uniform(0.25, 0.75, size=(h - 2 * by, w - 2 * bx, 3)).astype(np.float32)
    img[by : h - by, bx : w - bx] = content
    return img


def test_detects_dark_rebate_graded_scan():
    img = _frame(border_level=0.02)
    x, y, w, h = rebate.detect_image_area(img)
    assert abs(x - 60) <= 8 and abs(y - 40) <= 8
    assert abs((x + w) - 340) <= 8 and abs((y + h) - 260) <= 8


def test_detects_bright_rebate_flat_scan():
    # the bug that shipped once: flats have a near-WHITE film base
    img = _frame(border_level=0.97)
    x, y, w, h = rebate.detect_image_area(img)
    assert abs(x - 60) <= 8 and abs(y - 40) <= 8
    assert abs((x + w) - 340) <= 8 and abs((y + h) - 260) <= 8


def test_no_visible_rebate_returns_full_frame():
    rng = np.random.default_rng(1)
    img = rng.uniform(0.3, 0.7, size=(200, 300, 3)).astype(np.float32)
    x, y, w, h = rebate.detect_image_area(img, margin_frac=0.0)
    assert (x, y, w, h) == (0, 0, 300, 200)


def test_fraction_round_trip_and_crop():
    img = _frame(border_level=0.02)
    area = rebate.detect_image_area(img)
    frac = rebate.area_as_fractions(area, img.shape)
    assert all(0.0 <= f <= 1.0 for f in frac)
    assert rebate.fractions_to_area(frac, img.shape) == area
    crop = rebate.crop_to_area(img, frac)
    assert crop.shape[:2] == (area[3], area[2])
    # the crop must contain content, not border
    assert crop.mean() > 0.2


def test_blank_and_white_frames_are_not_content():
    black = np.full((120, 160, 3), 0.03, np.float32)
    white = np.full((120, 160, 3), 0.98, np.float32)
    assert rebate.looks_blank(black) and rebate.looks_blank(white)
    assert rebate.looks_white(white) and not rebate.looks_white(black)
    assert not rebate.is_content_frame(black)
    assert not rebate.is_content_frame(white)


def test_info_card_detected_across_hues_but_photos_are_not():
    # the lab's leader frames are near-uniform saturated single-hue fields;
    # they appeared orange, green and red across eras, so hue must not matter
    for rgb in [(0.85, 0.45, 0.10), (0.20, 0.70, 0.55), (0.75, 0.20, 0.18)]:
        card = np.zeros((150, 200, 3), np.float32)
        card[..., :] = rgb
        card += np.random.default_rng(0).normal(0, 0.01, card.shape).astype(np.float32)
        assert rebate.looks_like_info_card(np.clip(card, 0, 1)), f"missed card {rgb}"
        assert not rebate.is_content_frame(np.clip(card, 0, 1))

    rng = np.random.default_rng(2)
    photo = rng.uniform(0.1, 0.9, size=(150, 200, 3)).astype(np.float32)
    assert not rebate.looks_like_info_card(photo)
    assert rebate.is_content_frame(photo)
