#!/usr/bin/env python3
"""Generate one scene card per chapter (PIL, same visual language as cover).

  python3 scenes.py            -> scenes/scene_00.png ... scene_11.png
"""
import json, math, os, random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
OUT = "/home/zaq/bedtime-studio/scenes"
FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
NAVY_TOP = (5, 9, 22)
NAVY_BOT = (13, 27, 52)
GOLD = (212, 175, 94)
GREEN = (86, 226, 140)
MUTED = (140, 160, 190)
DEEP = (8, 14, 32)

CHAPTERS = [
    ("intro",    "Intro / wind-down"),
    ("gen11",    "Genesis 1:1"),
    ("day1",     "Day 1 — Let there be light"),
    ("day2",     "Day 2 — The sky"),
    ("day3",     "Day 3 — Land + vegetation"),
    ("day4",     "Day 4 — Sun, moon, stars"),
    ("day5",     "Day 5 — Fish and birds"),
    ("day6",     "Day 6 — Animals + humanity"),
    ("imago",    "Made in God's image"),
    ("eden",     "The Garden / Eden"),
    ("closing",  "Closing — rest here"),
    ("preview",  "Next episode preview"),
]


def gradient(draw):
    for y in range(H):
        k = y / H
        k = k * k * (3 - 2 * k)
        r = int(NAVY_TOP[0] + (NAVY_BOT[0] - NAVY_TOP[0]) * k)
        g = int(NAVY_TOP[1] + (NAVY_BOT[1] - NAVY_TOP[1]) * k)
        b = int(NAVY_TOP[2] + (NAVY_BOT[2] - NAVY_TOP[2]) * k)
        draw.line([(0, y), (W, y)], fill=(r, g, b))


def stars(draw, n=380, seed=7, ymax=0.72):
    rnd = random.Random(seed)
    for _ in range(n):
        x, y = rnd.randint(0, W), rnd.randint(0, int(H * ymax))
        b = rnd.randint(60, 235)
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


def motif_intro(img):
    glow(img, W // 2, int(H * 0.42), 520, (40, 90, 160), alpha=42)
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT_MONO, 64)
    centered(d, "$ ./genesis.sh --begin", int(H * 0.36), f, GREEN)
    centered(d, "wind-down mode engaged", int(H * 0.46), ImageFont.truetype(FONT_SANS, 34), MUTED)


def motif_gen11(img):
    glow(img, W // 2, int(H * 0.38), 600, GOLD, alpha=26)
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT_SERIF, 56)
    centered(d, "\u201cIn the beginning God created", int(H * 0.30), f, GOLD)
    centered(d, "the heaven and the earth.\u201d", int(H * 0.38), f, GOLD)
    centered(d, "Genesis 1:1  ·  KJV", int(H * 0.50), ImageFont.truetype(FONT_MONO, 36), MUTED)


def motif_day1(img):
    glow(img, W // 2, int(H * 0.40), 430, GOLD, alpha=85)
    glow(img, W // 2, int(H * 0.40), 190, (255, 236, 170), alpha=110)
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT_SERIF, 72)
    centered(d, "Let there be light", int(H * 0.60), f, GOLD)
    centered(d, "$ emit photon_stream --unbound", int(H * 0.70), ImageFont.truetype(FONT_MONO, 40), GREEN)


def motif_day2(img):
    d = ImageDraw.Draw(img)
    for i, (y0, y1, col) in enumerate([
        (0.22, 0.34, (16, 32, 64)), (0.34, 0.46, (22, 44, 86)),
        (0.46, 0.58, (30, 58, 108)), (0.58, 0.70, (40, 74, 128))]):
        d.rectangle([0, int(H * y0), W, int(H * y1)], fill=col)
        for x in range(0, W, 160):
            d.line([(x + i * 40, int(H * (y0 + y1) / 2)),
                    (x + 90 + i * 40, int(H * (y0 + y1) / 2))],
                   fill=(70, 110, 160), width=2)
    centered(d, "Let there be a firmament", int(H * 0.76),
             ImageFont.truetype(FONT_SERIF, 64), GOLD)
    centered(d, "sky.expanse = divide(waters_above, waters_below)",
             int(H * 0.86), ImageFont.truetype(FONT_MONO, 34), GREEN)


def motif_day3(img):
    d = ImageDraw.Draw(img)
    pts = [(0, H)]
    rnd = random.Random(3)
    x = 0
    while x <= W:
        pts.append((x, int(H * 0.62) + rnd.randint(-40, 40)))
        x += 60
    pts.append((W, H))
    d.polygon(pts, fill=(12, 26, 20))
    for gx, hgt in [(300, 90), (640, 130), (980, 70), (1340, 110), (1650, 85)]:
        base = int(H * 0.62) + 10
        d.line([(gx, base), (gx, base - hgt)], fill=(60, 140, 90), width=6)
        d.ellipse([gx - 28, base - hgt - 28, gx + 28, base - hgt + 28], fill=(86, 200, 120))
    centered(d, "Let the dry land appear", int(H * 0.28),
             ImageFont.truetype(FONT_SERIF, 68), GOLD)
    centered(d, "seed.commit(ground) -> vegetation++",
             int(H * 0.40), ImageFont.truetype(FONT_MONO, 38), GREEN)


def motif_day4(img):
    d = ImageDraw.Draw(img)
    glow(img, int(W * 0.30), int(H * 0.36), 200, GOLD, alpha=110)
    glow(img, int(W * 0.70), int(H * 0.34), 150, (170, 200, 255), alpha=80)
    rnd = random.Random(9)
    for _ in range(160):
        x, y = rnd.randint(0, W), rnd.randint(0, int(H * 0.55))
        b = rnd.randint(120, 255)
        d.point((x, y), fill=(b, b, min(255, b + 15)))
    centered(d, "Let there be lights in the firmament", int(H * 0.62),
             ImageFont.truetype(FONT_SERIF, 58), GOLD)
    centered(d, "sun.launch()  moon.launch()  stars.scatter()",
             int(H * 0.74), ImageFont.truetype(FONT_MONO, 38), GREEN)


def motif_day5(img):
    d = ImageDraw.Draw(img)
    for row in range(4):
        y = int(H * (0.46 + row * 0.07))
        for x in range(-40, W + 40, 60):
            off = 18 if row % 2 else 0
            d.arc([x + off, y - 14, x + off + 56, y + 14], 200, 340,
                  fill=(50, 110, 170), width=3)
    for bx, by in [(360, 220), (520, 190), (900, 210), (1180, 180), (1500, 230)]:
        d.arc([bx, by, bx + 46, by + 30], 200, 340, fill=MUTED, width=4)
        d.arc([bx + 40, by, bx + 86, by + 30], 200, 340, fill=MUTED, width=4)
    centered(d, "Let the waters swarm with living creatures", int(H * 0.70),
             ImageFont.truetype(FONT_SERIF, 52), GOLD)
    centered(d, "fish.spawn()  birds.fly()",
             int(H * 0.80), ImageFont.truetype(FONT_MONO, 40), GREEN)


def motif_day6(img):
    d = ImageDraw.Draw(img)
    rnd = random.Random(5)
    for _ in range(46):
        x = rnd.randint(80, W - 80)
        y = rnd.randint(int(H * 0.30), int(H * 0.58))
        s = rnd.randint(4, 9)
        d.ellipse([x, y, x + s * 2, y + s], fill=(70, 130, 100))
    d.ellipse([W // 2 - 34, int(H * 0.40), W // 2 + 34, int(H * 0.40) + 68],
              outline=GOLD, width=5)
    d.line([(W // 2, int(H * 0.40) + 68), (W // 2, int(H * 0.40) + 150)],
           fill=GOLD, width=5)
    centered(d, "Let us make humanity", int(H * 0.66),
             ImageFont.truetype(FONT_SERIF, 68), GOLD)
    centered(d, "cattle.wild() + imago_dei.init()",
             int(H * 0.76), ImageFont.truetype(FONT_MONO, 40), GREEN)


def motif_imago(img):
    glow(img, W // 2, int(H * 0.40), 480, GOLD, alpha=34)
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT_MONO, 56)
    centered(d, "function imago_dei(self) {", int(H * 0.28), f, GREEN)
    centered(d, "    return self.copy(bearing=Creator);", int(H * 0.38), f, MUTED)
    centered(d, "}", int(H * 0.48), f, GREEN)
    centered(d, "So God created man in his own image",
             int(H * 0.62), ImageFont.truetype(FONT_SERIF, 54), GOLD)
    centered(d, "Genesis 1:27", int(H * 0.72),
             ImageFont.truetype(FONT_MONO, 36), MUTED)


def motif_eden(img):
    d = ImageDraw.Draw(img)
    ground = int(H * 0.68)
    d.rectangle([0, ground, W, H], fill=(10, 24, 18))
    for tx, th, col in [(int(W * 0.32), 220, (40, 110, 70)),
                        (int(W * 0.52), 300, (55, 150, 90)),
                        (int(W * 0.70), 190, (36, 100, 64))]:
        d.line([(tx, ground), (tx, ground - th)], fill=(70, 50, 34), width=14)
        d.ellipse([tx - 80, ground - th - 80, tx + 80, ground - th + 40], fill=col)
    d.arc([int(W * 0.18), int(H * 0.20), int(W * 0.82), int(H * 0.80)],
          200, 340, fill=(90, 130, 90), width=6)
    centered(d, "And the Lord planted a garden in Eden",
             int(H * 0.12), ImageFont.truetype(FONT_SERIF, 52), GOLD)
    centered(d, "edEn.encode(seed=4)  // one restriction inside",
             int(H * 0.82), ImageFont.truetype(FONT_MONO, 36), GREEN)


def motif_closing(img):
    d = ImageDraw.Draw(img)
    glow(img, int(W * 0.72), int(H * 0.28), 170, (200, 220, 255), alpha=70)
    d.ellipse([int(W * 0.66), int(H * 0.18), int(W * 0.78), int(H * 0.38)],
              fill=(220, 230, 250))
    d.ellipse([int(W * 0.63), int(H * 0.16), int(W * 0.74), int(H * 0.35)],
              fill=NAVY_TOP)
    centered(d, "session paused — rest here", int(H * 0.52),
             ImageFont.truetype(FONT_SERIF, 64), GOLD)
    centered(d, "$ sleep --in-peace   zZz", int(H * 0.64),
             ImageFont.truetype(FONT_MONO, 46), GREEN)


def motif_preview(img):
    d = ImageDraw.Draw(img)
    glow(img, W // 2, int(H * 0.42), 420, (40, 90, 160), alpha=40)
    f = ImageFont.truetype(FONT_MONO, 52)
    centered(d, "$ cat next_episode.txt", int(H * 0.32), f, GREEN)
    centered(d, "Genesis 2 — the garden expands,", int(H * 0.44), f, MUTED)
    centered(d, "and a choice is written in code.", int(H * 0.52), f, MUTED)
    centered(d, "subscribe so you don't miss it _", int(H * 0.66),
             ImageFont.truetype(FONT_SANS, 40), GOLD)


MOTIFS = {
    "intro": motif_intro, "gen11": motif_gen11, "day1": motif_day1,
    "day2": motif_day2, "day3": motif_day3, "day4": motif_day4,
    "day5": motif_day5, "day6": motif_day6, "imago": motif_imago,
    "eden": motif_eden, "closing": motif_closing, "preview": motif_preview,
}


def build_scene(idx, slug, title):
    img = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(img)
    gradient(d)
    stars(d, n=400, seed=11 + idx)
    MOTIFS[slug](img)

    d = ImageDraw.Draw(img)
    # chapter badge
    f_badge = ImageFont.truetype(FONT_MONO, 34)
    badge = f"{idx + 1:02d} / {len(CHAPTERS):02d}"
    bw = d.textlength(badge, font=f_badge)
    d.text((72, 56), badge, font=f_badge, fill=MUTED)
    d.line([(72, 104), (72 + bw, 104)], fill=GOLD, width=2)

    # title (skip motifs that already draw their own big title mid-screen)
    f_title = ImageFont.truetype(FONT_SERIF, 44)
    centered(d, title, H - 150, f_title, GOLD, tracking=2)

    # footer
    f_foot = ImageFont.truetype(FONT_SANS, 26)
    centered(d, "BEDTIME BIBLE CODERS  \u00b7  EPISODE 1  \u00b7  GENESIS 1",
             H - 84, f_foot, (95, 115, 150))

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"scene_{idx:02d}_{slug}.png")
    img.convert("RGB").save(path, optimize=True)
    print(path)


def main():
    for i, (slug, title) in enumerate(CHAPTERS):
        build_scene(i, slug, title)
    manifest = {"scenes": [{"file": f"scene_{i:02d}_{s}.png", "slug": s, "title": t}
                           for i, (s, t) in enumerate(CHAPTERS)]}
    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print("manifest.json")


if __name__ == "__main__":
    main()
