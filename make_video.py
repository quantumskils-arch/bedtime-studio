#!/usr/bin/env python3
"""Compose Bedtime Bible Coders video.

Single-cover (legacy):
  python3 make_video.py --audio ep1.mp3 --cover cover.png --music ambient.wav --out ep.mp4

Multi-scene (chapter cards + crossfades):
  python3 make_video.py --audio ep1_andrew.mp3 --music ambient.wav \
      --chapters ep1_andrew --out episode1_andrew.mp4

Scenes are scenes/scene_NN_*.png in chapters.json order. 1.5s xfade between
scenes; each scene gets its own gentle ken-burns (alternating in/out).
"""
import argparse, json, os, subprocess, sys

FPS = 25
FADE = 1.5
SCENES_DIR = "/home/zaq/bedtime-studio/scenes"
CHAPTERS_JSON = "/home/zaq/bedtime-studio/chapters.json"
W, H = 1920, 1080
PAD_W, PAD_H = 2112, 1188  # pre-zoom pad so pan stays clean


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def load_scene_files():
    with open(os.path.join(SCENES_DIR, "manifest.json")) as f:
        man = json.load(f)
    return [os.path.join(SCENES_DIR, s["file"]) for s in man["scenes"]]


def load_chapter_times(key):
    with open(CHAPTERS_JSON) as f:
        ch = json.load(f)
    return [t for _, t in ch[key]["chapters"]]


def scene_spans(times, audio_dur, n):
    """Raw display seconds per scene from chapter start times."""
    spans = []
    for i in range(n):
        start = times[i]
        end = times[i + 1] if i + 1 < len(times) else audio_dur
        spans.append(end - start)
    # last scene absorbs xfade debt so total == audio_dur
    debt = (n - 1) * FADE
    spans[-1] = audio_dur - sum(spans[:-1]) + debt
    return spans


def zoom_expr(i, frames):
    # alternate slow zoom-in / zoom-out with a gentle lateral sway (bedtime-safe)
    sway = f"+sin(on/{frames}*PI*2)*30"
    x = f"iw/2-(iw/zoom/2){sway}"
    y = "ih/2-(ih/zoom/2)"
    if i % 2 == 0:
        return f"min(1.0+0.05*on/{frames},1.05)", x, y
    return f"max(1.05-0.05*on/{frames},1.0)", x, y


def build_multiscene(a, dur):
    files = load_scene_files()
    times = load_chapter_times(a.chapters)
    n = len(files)
    if len(times) < n:
        print(f"error: {a.chapters} has {len(times)} chapters, need {n}", file=sys.stderr)
        sys.exit(1)
    spans = scene_spans(times, dur, n)
    # inputs need span+FADE of material so xfade never starves
    needs = [s + FADE for s in spans]

    parts = []
    for i, (path, need) in enumerate(zip(files, needs)):
        fframes = max(int(need * FPS) + 5, 2)
        z, x, y = zoom_expr(i, fframes)
        vf = (f"scale={PAD_W}:{PAD_H},"
              f"zoompan=z='{z}':x='{x}':y='{y}':d={fframes}:s={W}x{H}:fps={FPS},"
              f"format=yuv420p,setsar=1[v{i}]")
        parts.append(vf)

    cur = "v0"
    for k in range(1, n):
        offset = sum(spans[:k]) - k * FADE
        out = f"x{k}" if k < n - 1 else "vout"
        parts.append(f"[{cur}][v{k}]xfade=transition=fade:duration={FADE}:"
                     f"offset={offset:.3f}[{out}]")
        cur = out

    vfinal = "vfinal"
    if getattr(a, "ass", None):
        parts.append(f"[vout]ass='{os.path.abspath(a.ass)}'[vfinal]")
    else:
        parts.append("[vout]null[vfinal]")

    parts.append(f"[{n + 1}:a]aresample=48000,volume=1.0[voice]")
    parts.append(f"[{n}:a]aresample=48000,volume=0.11[mus]")
    parts.append("[voice][mus]amix=inputs=2:duration=first:normalize=0[mixed]")
    parts.append("[mixed]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[aout]")

    fpath = "/tmp/opencode/filter_multiscene.txt"
    os.makedirs("/tmp/opencode", exist_ok=True)
    with open(fpath, "w") as f:
        f.write(";\n".join(parts))

    with open(fpath) as f:
        filt = f.read()

    cmd = ["ffmpeg", "-y"]
    for path in files:
        cmd += ["-i", path]
    cmd += ["-stream_loop", "-1", "-i", a.music, "-i", a.audio,
            "-filter_complex", filt,
             "-map", "[vfinal]", "-map", "[aout]",
            "-t", f"{dur:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", a.out]
    print(f"multiscene: {n} scenes, fade={FADE}s, spans={[round(s,1) for s in spans]}")
    return cmd


def build_single(a, dur):
    frames = int(dur * FPS)
    zexpr = "min(1.0+0.0000012*on,1.06)"
    vf = (f"scale={PAD_W}:{PAD_H},zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':"
          f"y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},"
          f"format=yuv420p[v]")
    filt = (f"[0:v]{vf};"
            f"[1:a]aresample=48000,volume=1.0[voice];"
            f"[2:a]aresample=48000,volume=0.11[mus];"
            f"[voice][mus]amix=inputs=2:duration=first:normalize=0[a]")
    fpath = "/tmp/opencode/filter_single.txt"
    os.makedirs("/tmp/opencode", exist_ok=True)
    with open(fpath, "w") as f:
        f.write(filt)
    with open(fpath) as f:
        filt = f.read()
    return ["ffmpeg", "-y", "-i", a.cover,
            "-stream_loop", "-1", "-i", a.music,
            "-i", a.audio,
            "-filter_complex", filt,
            "-map", "[v]", "-map", "[a]",
            "-t", f"{dur:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", a.out]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--cover")
    ap.add_argument("--music", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--chapters", help="chapters.json key, e.g. ep1_andrew")
    ap.add_argument("--ass", help="karaoke captions file to burn (from captions.py)")
    a = ap.parse_args()

    if not a.chapters and not a.cover:
        ap.error("need --chapters (multi-scene) or --cover (single)")

    dur = probe(a.audio)
    cmd = build_multiscene(a, dur) if a.chapters else build_single(a, dur)
    print(" ".join(cmd[:10]), "...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-4000:], file=sys.stderr)
        sys.exit(1)
    print(f"done: {a.out}  duration={probe(a.out):.0f}s ({probe(a.out)/60:.1f} min)")


if __name__ == "__main__":
    main()
