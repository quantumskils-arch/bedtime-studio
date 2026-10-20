#!/usr/bin/env python3
"""Extract vertical 9:16 shorts from a long-form episode, with burned captions.

  python3 shorts.py --video episode1_andrew.mp4 --srt ep1_andrew.srt \
      --start 243 --dur 42 --title "In the beginning was the Code" --out short_1
"""
import argparse, os, re, subprocess


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
        words.append((h * 3600 + mn * 60 + s + ms / 1000, lines[2].strip()))
    return words


def slice_srt(words, start, dur, out):
    """Word cues inside [start, start+dur], re-based to 0, grouped into ~4-word cues."""
    sel = [(t - start, w) for t, w in words if start <= t < start + dur]
    if not sel:
        return False
    groups = []
    for i in range(0, len(sel), 4):
        chunk = sel[i:i + 4]
        groups.append((chunk[0][0], chunk[-1][0] + 0.55,
                       " ".join(w for _, w in chunk)))
    def ts(t):
        h, rem = divmod(t, 3600)
        mn, s = divmod(rem, 60)
        return f"{int(h):02d}:{int(mn):02d}:{int(s):02d},{int((s - int(s))*1000):03d}"
    with open(out, "w", encoding="utf-8") as f:
        for i, (a, b, txt) in enumerate(groups, 1):
            f.write(f"{i}\n{ts(a)} --> {ts(b)}\n{txt}\n\n")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--srt", required=True)
    ap.add_argument("--start", type=float, required=True)
    ap.add_argument("--dur", type=float, default=40)
    ap.add_argument("--title", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    seg_srt = a.out + "_cap.srt"
    words = load_words(a.srt)
    if not slice_srt(words, a.start, a.dur, seg_srt):
        print(f"no words in window for {a.out}")
        return

    # vertical composition: blurred fill of the source + sharp centred copy on top
    vf = (
        "split[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,boxblur=28:6,eq=brightness=-0.22:saturation=0.7[vbg];"
        "[fg]scale=1080:-2[vfg];"
        "[vbg][vfg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]"
    )
    # captions styled for vertical
    style = ("FontSize=17,PrimaryColour=&HFFFFFF,OutlineColour=&H0A000000,"
             "BorderStyle=1,Outline=2,Shadow=0,Alignment=5,MarginV=46,Bold=1")
    srt_path = os.path.abspath(seg_srt)
    cmd = ["ffmpeg", "-y", "-ss", f"{a.start:.3f}", "-t", f"{a.dur:.3f}",
           "-i", a.video,
           "-filter_complex",
           f"[0:v]{vf};[v]subtitles='{srt_path}':force_style='{style}'[vout]",
           "-map", "[vout]", "-map", "0:a",
           "-t", f"{a.dur:.3f}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
           "-c:a", "aac", "-b:a", "160k",
           "-movflags", "+faststart", a.out + ".mp4"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-2500:])
        raise SystemExit(1)
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", a.out + ".mp4"],
                       capture_output=True, text=True).stdout.strip()
    print(f"{a.out}.mp4  {float(d):.1f}s" + (f"  title={a.title!r}" if a.title else ""))


if __name__ == "__main__":
    main()
