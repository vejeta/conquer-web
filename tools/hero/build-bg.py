#!/usr/bin/env python3.13
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
"""Draw web/hero/map.json as a faint terminal-glyph texture, one tile per race:
web/bg/map-<race>.webp (1600 px wide), glyphs in VT323 in the race phosphor on
the race --bg. theme.css lays it, at a few percent, behind the page margins.

    tools/hero/build-bg.py            (needs Pillow with WebP and fontTools)
"""
import json, os, sys, io
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RACES = {  # race: (--bg, --phos), as in web/theme.css
    "human": ("#0b1210", "#8fe3a0"), "elf": ("#0b1016", "#a9d3e6"),
    "dwarf": ("#100e0b", "#f2a93b"), "orc": ("#0e0b0b", "#e07a5a"),
}
W, ROWH, ROWS, SIZE = 1600, 20, 52, 26
# glyph strength by altitude: the water is a whisper, the peaks the loudest
ALPHA = {"~": .30, "-": .42, "%": .62, "^": .85, "#": 1.0}

def mix(fg, bg, a):
    f = [int(fg[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(bg[i:i + 2], 16) for i in (1, 3, 5)]
    return tuple(round(a * x + (1 - a) * y) for x, y in zip(f, b))

def main():
    m = json.load(open(os.path.join(ROOT, "web", "hero", "map.json")))
    cols, cell = m["w"], W / m["w"]
    ttf = os.path.join(os.environ.get("TMPDIR", "/tmp"), "vt323.ttf")
    f = TTFont(os.path.join(ROOT, "web", "fonts", "vt323-latin.woff2")); f.flavor = None; f.save(ttf)
    vt = ImageFont.truetype(ttf, SIZE)
    try:
        mono = ImageFont.truetype("DejaVuSansMono.ttf", int(SIZE * .8))  # VT323's tilde reads as an N
    except OSError:
        mono = vt
    grid = [[(r[i], r[i + 1]) for i in range(0, len(r), 4)] for r in m["rows"]]
    land = [sum(1 for a, d in row if a != "~") for row in grid]
    y0 = max(range(len(grid) - ROWS + 1), key=lambda y: sum(land[y:y + ROWS]))
    for race, (bg, ph) in RACES.items():
        im = Image.new("RGB", (W, ROWS * ROWH), bg)
        d = ImageDraw.Draw(im)
        for r in range(ROWS):
            for c in range(cols):
                alt, des = grid[y0 + r][c]
                ch, a, font = alt, ALPHA.get(alt, .4), vt
                if alt == "~": font = mono
                if des != "-": ch, a = des, 1.0
                d.text((c * cell, r * ROWH + (2 if alt == "~" else 0)), ch, font=font, fill=mix(ph, bg, a))
        im = im.quantize(6, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGB")
        out = os.path.join(ROOT, "web", "bg", "map-%s.webp" % race)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        for q in (100, 80, 60, 40, 25, 10):  # a handful of flat colours: lossless first
            buf = io.BytesIO(); im.save(buf, "WEBP", lossless=(q == 100), quality=q, method=6)
            if buf.tell() <= 60000: break
        open(out, "wb").write(buf.getvalue())
        print(race, im.size, buf.tell(), "bytes, q", q)

main()
