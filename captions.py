#!/usr/bin/env python3
"""Word-level SRT -> karaoke ASS (phrase-grouped, brand-styled).

  python3 captions.py ep1_andrew.srt ep1_andrew.ass --playres 1920x1080 --margin-v 180

Phrases: 3-5 words or ~2.4s. Each word gets \\k duration; spoken words turn
gold (Primary), pending stay white (Secondary).
"""
import argparse, re


def load_words(path):
    srt = open(path, encoding="utf-8").read()
    words = []
    for b in re.split(r"\n\n+", srt.strip()):
        lines = b.split("\n")
        if len(lines) < 3:
            continue
        m = re.match(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", lines[1].split(" --> ")[0])
        if not m:
            continue
        h, mn, s, ms = map(int, m.groups())
        t = h * 3600 + mn * 60 + s + ms / 1000
        end_m = re.match(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", lines[1].split(" --> ")[1])
        if end_m:
            eh, emn, es, ems = map(int, end_m.groups())
            tend = eh * 3600 + emn * 60 + es + ems / 1000
        else:
            tend = t + 0.3
        txt = lines[2].strip()
        if txt and txt not in {"[MUSIC]", "[Music]", "[music]"}:
            words.append((t, tend, txt))
    return words


def group_phrases(words, max_words=5, max_span=2.4):
    phrases, cur = [], []
    for t, tend, w in words:
        if cur:
            span = tend - cur[0][0]
            n = len(cur)
            ends = w.endswith((".", ",", "!", "?", ";", ":", "..."))
            if n >= max_words or span >= max_span or ends:
                phrases.append(cur)
                cur = []
        cur.append((t, tend, w))
    if cur:
        phrases.append(cur)
    # drop crumbs < 0.35s single words unless sentence start
    return [p for p in phrases if len(p) >= 1 and (len(p) > 1 or p[0][1] - p[0][0] > 0.4)]


def ass_time(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_ass(phrases, w, h, margin_v, font_size, outfile, slice_start=0.0, slice_dur=None):
    if slice_dur is not None:
        end = slice_start + slice_dur
        phrases = [[(t - slice_start, te - slice_start, x) for t, te, x in p]
                   for p in phrases if p[0][0] >= slice_start - 0.05 and p[-1][1] <= end + 0.6]
        phrases = [p for p in phrases if p and p[0][0] >= 0]
        phrases = [[(max(t, 0.0), max(te, 0.05), x) for t, te, x in p] for p in phrases]
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Kara,DejaVu Sans,{font_size},&H005EAFD4,&H00FFFFFF,&H00140A05,&H66140A05,-1,0,0,0,100,100,0.5,0,3,14,0,2,60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for p in phrases:
        t0 = max(p[0][0], 0.0)
        # end = word end + small hold
        t1 = max(p[-1][1] + 0.35, t0 + 0.2)
        parts = []
        for i, (wt, wend, word) in enumerate(p):
            dur_cs = max(int(round((wend - wt) * 100)), 1)
            if i == 0:
                # first word: hold from phrase start
                lead = max(int(round((wt - t0) * 100)), 0)
                if lead:
                    parts.append(f"{{\\k{lead}}}")
            elif i > 0:
                gap = max(int(round((wt - p[i - 1][1]) * 100)), 0)
                if gap:
                    parts.append(f"{{\\k{gap}}}")
            parts.append(f"{{\\k{dur_cs}}}{word}")
            if i < len(p) - 1:
                parts.append(" ")
        text = "".join(parts).replace("\n", " ")
        lines.append(f"Dialogue: 0,{ass_time(t0)},{ass_time(t1)},Kara,,0,0,0,,{text}\n")
    open(outfile, "w", encoding="utf-8").write("".join(lines))
    print(f"{outfile}: {len(phrases)} phrases")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("srt")
    ap.add_argument("ass")
    ap.add_argument("--playres", default="1920x1080")
    ap.add_argument("--margin-v", type=int, default=180)
    ap.add_argument("--font-size", type=int, default=62)
    ap.add_argument("--slice", nargs=2, type=float, metavar=("START", "DUR"),
                    help="rebase and keep phrases inside [START, START+DUR]")
    a = ap.parse_args()
    w, h = map(int, a.playres.split("x"))
    words = load_words(a.srt)
    phrases = group_phrases(words)
    if a.slice:
        build_ass(phrases, w, h, a.margin_v, a.font_size, a.ass,
                  slice_start=a.slice[0], slice_dur=a.slice[1])
    else:
        build_ass(phrases, w, h, a.margin_v, a.font_size, a.ass)


if __name__ == "__main__":
    main()
