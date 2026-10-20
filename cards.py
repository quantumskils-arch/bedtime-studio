#!/usr/bin/env python3
"""Generate cover art + thumbnail for Bedtime Bible Coders (PIL, zero API).

  python3 cards.py cover   -> cover.png 1920x1080 (video background)
  python3 cards.py thumb   -> thumb.jpg 1280x720  (YouTube thumbnail, bolder)
"""
import math, random, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
NAVY_TOP = (5, 9, 22)
NAVY_BOT = (13, 27, 52)
GOLD = (212, 175, 94)
GREEN = (86, 226, 140)
MUTED = (140, 160, 190)


def gradient(draw):
    for y in range(H):
        k = y / H
        k = k * k * (3 - 2 * k)  # smoothstep
        r = int(NAVY_TOP[0] + (NAVY_BOT[0] - NAVY_TOP[0]) * k)
        g = int(NAVY_TOP[1] + (NAVY_BOT[1] - NAVY_TOP[1]) * k)
        b = int(NAVY_TOP[2] + (NAVY_BOT[2] - NAVY_TOP[2]) * k)
        draw.line([(0, y), (W, y)], fill=(r, g, b))


def stars(draw, n=340, seed=7):
    rnd = random.Random(seed)
    for _ in range(n):
        x, y = rnd.randint(0, W), rnd.randint(0, int(H * 0.72))
        b = rnd.randint(70, 235)
        s = rnd.choice([1, 1, 1, 2])
        draw.ellipse([x, y, x + s, y + s], fill=(b, b, min(255, b + 20)))


def glow(img, cx, cy, radius, color, alpha=46):
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    d.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
              fill=color + (alpha,))
    g = g.filter(ImageFilter.GaussianBlur(radius / 2.2))
    img.alpha_composite(g)


def centered(draw, text, y, font, fill, tracking=0):
    if tracking <= 0:
        w = draw.textlength(text, font=font)
        draw.text(((W - w) / 2, y), text, font=font, fill=fill)
        return
    total = sum(draw.textlength(c, font=font) + tracking for c in text) - tracking
    x = (W - total) / 2
    for c in text:
        draw.text((x, y), c, font=font, fill=fill)
        x += draw.textlength(c, font=font) + tracking


def frame_text(img, title_lines, sub, footer, thumb=False):
    d = ImageDraw.Draw(img)
    f_title = ImageFont.truetype(FONT_SERIF, 150 if thumb else 128)
    f_ep = ImageFont.truetype(FONT_MONO, 46 if thumb else 38)
    f_foot = ImageFont.truetype(FONT_SANS, 34 if thumb else 28)

    glow(img, W // 2, int(H * 0.40), 560, (40, 90, 160), alpha=40)
    glow(img, int(W * 0.78), int(H * 0.30), 300, GOLD, alpha=22)

    y = int(H * 0.24)
    for i, line in enumerate(title_lines):
        col = GOLD if i == 0 else GREEN
        centered(d, line, y, f_title, col, tracking=6 if thumb else 3)
        y += f_title.size + (26 if thumb else 18)

    y += 34 if thumb else 26
    centered(d, sub, y, f_ep, MUTED)

    # terminal cursor accent
    cw = d.textlength("_", font=f_ep)
    sw = d.textlength(sub, font=f_ep)
    d.text(((W - sw) / 2 + sw + 14, y), "_", font=f_ep, fill=GREEN)

    centered(d, footer, H - int(150 if thumb else 118), f_foot, (95, 115, 150))


def build(kind):
    img = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(img)
    gradient(d)
    stars(d, n=420 if kind == "cover" else 300, seed=11 if kind == "cover" else 22)
    if kind == "thumb":
        frame_text(img, ["BEDTIME", "BIBLE CODERS"], "EP 1 | GENESIS 1: THE FIRST COMMIT",
                   "Code \u00b7 Faith \u00b7 The Architecture of Creation", thumb=True)
        img.convert("RGB").save("/home/zaq/bedtime-studio/thumb.jpg", quality=92)
        print("thumb.jpg")
    else:
        frame_text(img, ["BEDTIME", "BIBLE CODERS"], "EPISODE 1  |  GENESIS 1 - THE FIRST COMMIT",
                   "Code, faith, and the architecture of creation")
        img.save("/home/zaq/bedtime-studio/cover.png")
        print("cover.png")


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "cover")
