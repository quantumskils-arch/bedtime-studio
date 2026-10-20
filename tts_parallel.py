#!/usr/bin/env python3
"""Parallel segmented TTS — renders long narration 10x faster than serial edge-tts.

  python3 tts_parallel.py ep1_narration.txt --voice en-US-AndrewNeural --out ep1

Splits at paragraph boundaries into ~equal chunks, renders N chunks with bounded
concurrency (survives edge-tts throttling via per-chunk retries), merges audio
with ffmpeg concat and merges word-timestamp SRTs with correct time offsets.
"""
import argparse, asyncio, os, re, subprocess, sys

edge_tts = __import__("edge_tts")
CONCURRENCY = 4


def probe(path: str) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def split_paragraphs(text: str, n: int) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    total = sum(len(p.split()) for p in paras)
    target = total / n
    chunks, cur, curw = [], [], 0
    for p in paras:
        w = len(p.split())
        if cur and curw + w > target and len(chunks) < n - 1:
            chunks.append("\n\n".join(cur))
            cur, curw = [], 0
        cur.append(p)
        curw += w
    if cur:
        chunks.append("\n\n".join(cur))
    return chunks


async def render_chunk(text: str, voice: str, mp3: str, srt: str, sem: asyncio.Semaphore,
                       idx: int, tries: int = 6) -> None:
    last = None
    async with sem:
        for attempt in range(tries):
            try:
                sub = edge_tts.SubMaker()
                comm = edge_tts.Communicate(text, voice, rate="-8%",
                                            boundary="WordBoundary")
                n = 0
                with open(mp3, "wb") as f:
                    async for ch in comm.stream():
                        if ch["type"] == "audio":
                            f.write(ch["data"])
                            n += 1
                        elif ch["type"] == "WordBoundary":
                            sub.feed(ch)
                if n < 10:
                    raise RuntimeError(f"too few audio chunks ({n})")
                with open(srt, "w", encoding="utf-8") as f:
                    f.write(sub.get_srt())
                print(f"  chunk {idx} ok ({os.path.getsize(mp3)//1024} KB)",
                      flush=True)
                return
            except Exception as e:
                last = e
                print(f"  chunk {idx} attempt {attempt+1} failed: {e}", flush=True)
                await asyncio.sleep(3 * (attempt + 1))
        raise RuntimeError(f"chunk {idx} failed after {tries} tries: {last}")


def offset_srt(srt_text: str, offset: float) -> str:
    """Shift all SRT timestamps by offset seconds."""
    def shift(m):
        h, mn, s, ms = (int(x) for x in m.groups())
        t = h * 3600 + mn * 60 + s + ms / 1000 + offset
        h, rem = divmod(t, 3600)
        mn, s = divmod(rem, 60)
        ms = round((s - int(s)) * 1000)
        return f"{int(h):02d}:{int(mn):02d}:{int(s):02d},{ms:03d}"
    pat = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})")
    return pat.sub(shift, srt_text)


async def run(text: str, voice: str, base: str, chunks_n: int) -> None:
    work = base + "_chunks"
    os.makedirs(work, exist_ok=True)
    chunks = split_paragraphs(text, chunks_n)
    print(f"{len(chunks)} chunks, concurrency {CONCURRENCY}", flush=True)
    sem = asyncio.Semaphore(CONCURRENCY)
    jobs = []
    for i, c in enumerate(chunks):
        mp3 = os.path.join(work, f"chunk_{i:02d}.mp3")
        srt = os.path.join(work, f"chunk_{i:02d}.srt")
        if os.path.exists(mp3) and os.path.getsize(mp3) > 4000:
            print(f"  chunk {i} cached", flush=True)
            continue
        jobs.append(render_chunk(c, voice, mp3, srt, sem, i))
    if jobs:
        await asyncio.gather(*jobs)

    # merge in order: audio concat + srt offset merge
    mp3s = [os.path.join(work, f"chunk_{i:02d}.mp3") for i in range(len(chunks))]
    concat_list = os.path.join(work, "list.txt")
    with open(concat_list, "w") as f:
        for p in mp3s:
            f.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i",
                    concat_list, "-c", "copy", base + ".mp3"], check=True)

    merged, t_off = [], 0.0
    for i in range(len(chunks)):
        sp = os.path.join(work, f"chunk_{i:02d}.srt")
        if os.path.exists(sp):
            with open(sp, encoding="utf-8") as f:
                merged.append(offset_srt(f.read(), t_off).strip())
        t_off += probe(mp3s[i])
    with open(base + ".srt", "w", encoding="utf-8") as f:
        f.write("\n\n".join(merged) + "\n")
    dur = probe(base + ".mp3")
    print(f"TOTAL {base}.mp3 = {dur:.0f}s ({dur/60:.1f} min)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("narration")
    ap.add_argument("--voice", default="en-US-AndrewNeural")
    ap.add_argument("--out", required=True)
    ap.add_argument("--chunks", type=int, default=12)
    a = ap.parse_args()
    text = open(a.narration, encoding="utf-8").read().strip()
    asyncio.run(run(text, a.voice, a.out, a.chunks))


if __name__ == "__main__":
    main()
