"""Labeled contact/judgement sheets: every tile captioned with what it is."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def _font(size: int):
    for path in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
                 "/System/Library/Fonts/Helvetica.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def build_sheet(rows: list[dict], tile_h: int = 300, pad: int = 8, caption_h: int = 26, title_h: int = 30,
                bg=(26, 26, 26)) -> Image.Image:
    """rows: [{"title": str, "tiles": [(rgb_float_img, caption_str, color_rgb|None), ...]}]"""
    font_c, font_t = _font(15), _font(18)
    row_imgs = []
    for row in rows:
        tiles = []
        for img, cap, col in row["tiles"]:
            h, w = img.shape[:2]
            s = tile_h / h
            t = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).resize((max(8, round(w * s)), tile_h), Image.LANCZOS)
            tiles.append((t, cap, col or (70, 70, 70)))
        W = sum(t.width for t, _, _ in tiles) + pad * (len(tiles) + 1)
        H = title_h + tile_h + caption_h + pad
        canvas = Image.new("RGB", (W, H), bg)
        d = ImageDraw.Draw(canvas)
        d.text((pad, 6), row["title"], fill=(235, 235, 235), font=font_t)
        x = pad
        for t, cap, col in tiles:
            canvas.paste(t, (x, title_h))
            d.rectangle([x, title_h + tile_h, x + t.width, title_h + tile_h + caption_h - 2], fill=col)
            d.text((x + 6, title_h + tile_h + 4), cap, fill=(255, 255, 255), font=font_c)
            x += t.width + pad
        row_imgs.append(canvas)
    W = max(r.width for r in row_imgs)
    sheet = Image.new("RGB", (W, sum(r.height for r in row_imgs)), bg)
    y = 0
    for r in row_imgs:
        sheet.paste(r, (0, y)); y += r.height
    return sheet


# caption colours by tile role
COLORS = {"input": (90, 90, 90), "lut": (40, 110, 170), "lab": (40, 140, 80), "ours": (150, 90, 30)}
