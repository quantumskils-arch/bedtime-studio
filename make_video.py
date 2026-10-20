#!/usr/bin/env python3
"""Compose final Episode 1 video: cover ken-burns + narration + ambient bed.

  python3 make_video.py --audio ep1.mp3 --cover cover.png --music ambient.wav \
      --out episode1.mp4

1080p25 H.264/AAC. Captions are NOT burned (YouTube SRT upload instead).
"""
import argparse, subprocess, sys

FPS = 25


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--cover", required=True)
    ap.add_argument("--music", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    dur = probe(a.audio)
    frames = int(dur * FPS)
    # gentle zoom-in capped at +6% over the whole episode (long-form safe).
    # single image frame -> zoompan d=<total frames> produces the full clip.
    zexpr = "min(1.0+0.0000012*on,1.06)"
    vf = (f"scale=2112:1188,zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':"
          f"y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps={FPS},"
          f"format=yuv420p")
    filt = (f"[0:v]{vf}[v];"
            f"[1:a]aresample=48000,volume=1.0[voice];"
            f"[2:a]aresample=48000,volume=0.11[mus];"
            f"[voice][mus]amix=inputs=2:duration=first:normalize=0[a]")

    cmd = ["ffmpeg", "-y", "-i", a.cover,
           "-stream_loop", "-1", "-i", a.music,
           "-i", a.audio,
           "-filter_complex", filt,
           "-map", "[v]", "-map", "[a]",
           "-t", f"{dur:.3f}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
           "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", a.out]
    print(" ".join(cmd[:8]), "...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3000:], file=sys.stderr)
        sys.exit(1)
    print(f"done: {a.out}  duration={probe(a.out):.0f}s ({probe(a.out)/60:.1f} min)")


if __name__ == "__main__":
    main()
