"""Shareable 2:3 portrait card explaining ΔE2000 and the current per-stock
numbers — for the Instagram community chat, not the repo. Draws directly with
PIL (no browser dependency) in the wizard's amber/dark palette.

Usage: python scripts/delta_e_card.py [out.png]
"""
from __future__ import annotations

import sys
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W, H = 1200, 1800  # 2:3 portrait

BG = (13, 13, 13)
FG = (238, 235, 228)
GREY = (140, 138, 132)
DIM = (90, 88, 84)
AMBER = (255, 175, 0)
AMBER_DIM = (168, 116, 10)
LINE = (44, 43, 40)

F = "/System/Library/Fonts/Supplemental/SF-Pro-Display-{}.otf"
FT = "/System/Library/Fonts/Supplemental/SF-Pro-Text-{}.otf"
M = "/System/Library/Fonts/Supplemental/SF-Mono-{}.otf"


def font(path_tpl, weight, size):
    return ImageFont.truetype(path_tpl.format(weight), size)


black = font(F, "Black", 30)
title = font(F, "Bold", 66)
subtitle = font(FT, "Regular", 33)
subtitle_b = font(FT, "Semibold", 33)
label = font(M, "Semibold", 22)
scale_num = font(M, "Bold", 26)
scale_word = font(FT, "Regular", 20)
stock = font(FT, "Semibold", 34)
stock_sub = font(M, "Regular", 22)
de_num = font(M, "Bold", 44)
de_unit = font(M, "Regular", 22)
footer_b = font(FT, "Semibold", 26)
footer = font(FT, "Regular", 24)
wordmark = font(M, "Bold", 26)


def wrap(draw, text, fnt, max_w):
    words = text.split(" ")
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("report/delta_e_card.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    M_X = 80
    y = 90

    # ── wordmark ──────────────────────────────────────────────────────────
    d.rectangle([M_X, y, M_X + 34, y + 34], fill=AMBER)
    d.text((M_X + 46, y - 2), "saltgate", font=wordmark, fill=AMBER)
    d.text((M_X, y + 46), "reverse-engineering the silbersalz35 grade", font=footer, fill=GREY)
    y += 110

    # ── title ────────────────────────────────────────────────────────────
    d.text((M_X, y), "how close is close?", font=title, fill=FG)
    y += 84
    d.text((M_X, y), "ΔE2000, explained", font=subtitle_b, fill=AMBER)
    y += 56

    # ── two-sentence explainer ──────────────────────────────────────────
    body = ("it's the distance between two colours the way a person actually "
             "sees them — not just their numbers. below 1, two renders look "
             "identical side by side. at 2, a careful look starts to show it — "
             "but neither looks wrong on its own.")
    for line in wrap(d, body, subtitle, W - 2 * M_X):
        d.text((M_X, y), line, font=subtitle, fill=FG)
        y += 44
    y += 30

    # ── scale strip ──────────────────────────────────────────────────────
    scale = [
        ("<1", "identical", (60, 140, 90)),
        ("2", "barely visible", (168, 150, 40)),
        ("4–8", "a shift", (196, 120, 40)),
        ("10+", "different grade", (176, 60, 50)),
    ]
    seg_w = (W - 2 * M_X) / len(scale)
    bar_y = y
    for i, (num, word, col) in enumerate(scale):
        x0 = M_X + i * seg_w
        d.rectangle([x0, bar_y, x0 + seg_w - 6, bar_y + 10], fill=col)
        d.text((x0, bar_y + 26), num, font=scale_num, fill=FG)
        d.text((x0, bar_y + 58), word, font=scale_word, fill=GREY)
    y = bar_y + 100

    d.line([M_X, y, W - M_X, y], fill=LINE, width=2)
    y += 44

    # ── table ────────────────────────────────────────────────────────────
    def held(cube, kind="by_frame"):
        j = json.loads((ROOT / "luts" / cube).read_text())["holdout_median_dE2000"]
        s = j.get(kind, {}).get("_summary")
        return f"{s['bare_lut']['median']:.1f}" if s else "—"

    G, T, D = ("silbersalz-gold200_v1-paired_33.stats.json",
               "silbersalz-500t_v1.1-paired_33.stats.json",
               "silbersalz-250d_v4-jxl_33.stats.json")
    rows = [
        ("kodak gold 200", held(G), "· within roll", f"{held(G,'by_roll')} across rolls", "27 pairs · 2 rolls", True),
        ("vision3 500t", held(T), "", "one roll so far", "5 pairs · 1 roll", True),
        ("vision3 250d", held(D), "", f"{held(D,'by_roll')} across rolls · 2 donors", "22 pairs · 4 rolls · 2 photographers · 16-bit", True),
        ("vision3 50d", "—", "", "no pairs yet", "102 graded frames (proxy)", False),
        ("200t · 125t", "—", "", "borrows 500t", "no pairs of their own yet", False),
    ]
    row_h = 122
    for name, de, dequal, note, prov, has_pairs in rows:
        d.text((M_X, y), name, font=stock, fill=FG)
        num_x = W - M_X - 210
        col = AMBER if has_pairs else DIM
        d.text((num_x, y - 6), de, font=de_num, fill=col)
        if de != "—":
            nw = d.textlength(de, font=de_num)
            d.text((num_x + nw + 10, y + 8), "ΔE", font=de_unit, fill=GREY)
        d.text((M_X, y + 40), note, font=stock_sub, fill=GREY)
        d.text((M_X, y + 68), prov, font=stock_sub, fill=DIM)
        y += row_h
        if name != rows[-1][0]:
            d.line([M_X, y - 18, W - M_X, y - 18], fill=LINE, width=1)

    y += 34
    d.line([M_X, y, W - M_X, y], fill=LINE, width=2)
    y += 56

    # ── footer / ask ─────────────────────────────────────────────────────
    d.text((M_X, y), "what closes the gap:", font=footer_b, fill=AMBER)
    y += 48
    ask = ("2 rolls, 3+ flat + graded pairs each, untouched lab files — new rolls beat new frames. "
           "and the 16-bit jp2/jxl if your delivery has them: the 8-bit gallery jpeg costs 2.2 ΔE on its own, "
           "which is now bigger than the error we are trying to measure.")
    for line in wrap(d, ask, footer, W - 2 * M_X):
        d.text((M_X, y), line, font=footer, fill=FG)
        y += 40
    y += 34
    d.text((M_X, y), "github.com/atrouwee/saltgate", font=footer_b, fill=AMBER)
    y += 46
    d.text((M_X, y), "full breakdown \u2192 docs/DELTA_E.md", font=stock_sub, fill=DIM)

    y += 90
    d.line([M_X, y, W - M_X, y], fill=LINE, width=2)
    y += 40
    d.rectangle([M_X, y + 6, M_X + 22, y + 28], fill=AMBER_DIM)
    d.text((M_X + 34, y), "we couldn\u2019t ask the lab, so we asked the frames", font=footer, fill=DIM)

    img.save(out, "PNG")
    print(f"wrote {out} ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
