#!/usr/bin/env python3
"""Native 9:16 shorts: vertical gradient bg + framed scene card + karaoke captions.

  python3 shorts_native.py --video episode1_andrew.mp4 --ass ep1_andrew_short.ass \
      --scene scenes/scene_01_gen11.png --start 243 --dur 42 --out short_1

Audio is cut from the (loudnormed) long-form. Captions come from captions.py
rendered at --playres 1080x1920 --margin-v ~660 --font-size ~70.
"""
import argparse, os, random, subprocess
from PIL import Image, ImageDraw, ImageFilter

VW, VH = 1080, 1920
NAVY_TOP = (5, 9, 22)
NAVY_BOT = (13, 27, 52)
GOLD = (212, 175, 94)


def vertical_bg(seed=7):
    img = Image.new("RGB", (VW, VH))
    d = ImageDraw.Draw(img)
    for y in range(VH):
        k = y / VH
        k = k * k * (3 - 2 * k)
        r = int(NAVY_TOP[0] + (NAVY_BOT[0] - NAVY_TOP[0]) * k)
        g = int(NAVY_TOP[1] + (NAVY_BOT[1] - NAVY_TOP[1]) * k)
        b = int(NAVY_TOP[2] + (NAVY_BOT[2] - NAVY_TOP[2]) * k)
        d.line([(0, y), (VW, y)], fill=(r, g, b))
    rnd = random.Random(seed)
    for _ in range(260):
        x, y = rnd.randint(0, VW), rnd.randint(0, int(VH * 0.9))
        b = rnd.randint(60, 235)
        s = rnd.choice([1, 1, 2])
        d.ellipse([x, y, x + s, y + s], fill=(b, b, min(255, b + 20)))
    return img


def compose_panel(scene_path, out_png, seed=11):
    card = Image.open(scene_path).convert("RGB")
    # scale card to panel 984x554, place upper-middle with gold frame
    pw, ph = 984, 554
    card = card.resize((pw, ph), Image.LANCZOS)
    bg = vertical_bg(seed)
    # soft shadow
    sh = Image.new("RGB", (pw + 40, ph + 40), (0, 0, 0))
    sh = sh.filter(ImageFilter.GaussianBlur(18))
    bg.paste(sh, (48, 430))
    bg.paste(card, (48, 440))
    d = ImageDraw.Draw(bg)
    d.rectangle([44, 436, 44 + pw + 8, 436 + ph + 8], outline=GOLD, width=3)
    # brand strip under panel
    try:
        from PIL import ImageFont
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
        from PIL.ImageFont import FreeTypeFont  # noqa
        tw = d.textlength("BEDTIME BIBLE CODERS · GENESIS 1", font=f)
        d.text(((VW - tw) / 2, 440 + ph + 36), "BEDTIME BIBLE CODERS · GENESIS 1",
               font=f, fill=(140, 160, 190))
    except Exception:
        pass
    bg.save(out_png, optimize=True)
    return out_png


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--ass", required=True)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--start", type=float, required=True)
    ap.add_argument("--dur", type=float, default=40)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=11)
    a = ap.parse_args()

    panel = a.out + "_panel.png"
    compose_panel(a.scene, panel, seed=a.seed)
    ass = os.path.abspath(a.ass)
    filt = f"[1:v]ass='{ass}'[vout]"
    cmd = ["ffmpeg", "-y",
           "-ss", f"{a.start:.3f}", "-t", f"{a.dur:.3f}", "-i", a.video,
           "-loop", "1", "-t", f"{a.dur:.3f}", "-i", panel,
           "-filter_complex", filt,
           "-map", "[vout]", "-map", "0:a",
           "-t", f"{a.dur:.3f}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
           "-c:a", "aac", "-b:a", "160k",
           "-movflags", "+faststart", a.out + ".mp4"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-2500:])
        raise SystemExit(1)
    os.unlink(panel)
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", a.out + ".mp4"],
                       capture_output=True, text=True).stdout.strip()
    print(f"{a.out}.mp4  {float(d):.1f}s")


if __name__ == "__main__":
    main()
