#!/usr/bin/env python3
"""Bedtime Bible Coders — episode pipeline (v1, minimal).

  python3 studio.py adapt  <ep.md>        -> prints/saves clean narration text
  python3 studio.py sample <narr.txt>     -> renders voice samples (two voices)
  python3 studio.py tts <narr.txt> --voice <voice> --out <base>  -> mp3 + srt

Adaptation rules: strip code fences (code lives on the blog, never read aloud),
music/direction brackets, section headers, reflection questions, meta lines;
keep scripture verses and the next-episode preview.
"""
import asyncio, re, sys, subprocess, os

edge_tts = __import__("edge_tts")
STUDIO = os.path.dirname(os.path.abspath(__file__))


def adapt(md_text: str) -> str:
    t = md_text
    t = re.sub(r"```.*?```", "\n", t, flags=re.S)                      # code blocks
    # producer-only tail: PRODUCTION NOTES section up to the preview
    t = re.sub(r"^#+\s*PRODUCTION NOTES.*?(?=Next Episode Preview|\Z)",
               "", t, flags=re.S | re.M | re.I)
    t = re.sub(r"\*\*\[.*?\]\*\*", "", t)                              # [MUSIC ...] cues
    t = re.sub(r"^#{1,4}\s*.*$", "", t, flags=re.M)                    # headers
    t = re.sub(r"^---+\s*$", "", t, flags=re.M)                        # rules
    # cut reflection-questions block (up to next preview or EOF)
    t = re.sub(r"\*\*Reflection Questions.*?(?=\*\*Next Episode Preview|\Z)",
               "", t, flags=re.S | re.I)
    # cut music-cue bullet lists (e.g. "- Garden: Peaceful, serene ambient")
    t = re.sub(r"^-\s+.*(ambient|fade|silence|music|soundscape).*$", "",
               t, flags=re.M | re.I)
    t = re.sub(r"^Available wherever you listen.*$", "", t, flags=re.M | re.I)
    t = re.sub(r"^\*{0,2}(END OF EPISODE.*|Runtime:.*)", "", t, flags=re.M | re.I)
    # cut study-material tail blocks (sources, music cues) up to the preview
    t = re.sub(r"^\*{0,2}(Sources Referenced|Music Cues)\*{0,2}\s*:?.*?(?=Next Episode Preview|\Z)",
               "", t, flags=re.S | re.M | re.I)
    t = re.sub(r"\*\*NARRATOR[^*]*:\*\*", "\n", t)                     # NARRATOR labels
    t = re.sub(r"^NARRATOR[^:\n]*:\s*$", "", t, flags=re.M)            # bare NARRATOR lines
    t = re.sub(r"\*\*(.*?)\*\*", r"\1", t)                             # bold -> plain
    t = re.sub(r"`([^`]+)`", r"\1", t)                                 # inline code -> plain
    t = re.sub(r"(?<!\w)\*([^*\n]+)\*(?!\w)", r"\1", t)                # italics -> plain
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"\*{0,2}Next Episode Preview:\*{0,2}", "Next Episode Preview:", t)
    return t.strip()


def load_narration(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


async def tts(text: str, voice: str, out_mp3: str, out_srt: str | None = None,
              rate: str = "-8%", tries: int = 4) -> None:
    last = None
    for attempt in range(tries):
        try:
            sub = edge_tts.SubMaker()
            comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
            with open(out_mp3, "wb") as f:
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary" and out_srt:
                        sub.feed(chunk)
            if out_srt:
                with open(out_srt, "w", encoding="utf-8") as f:
                    f.write(sub.get_srt())
            return
        except Exception as e:
            last = e
            if attempt < tries - 1:
                await asyncio.sleep(4 * (attempt + 1))
    raise last


def duration(path: str) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "adapt":
        md = open(sys.argv[2], encoding="utf-8").read()
        narr = adapt(md)
        out = sys.argv[3] if len(sys.argv) > 3 else sys.argv[2].replace(".md", "_narration.txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write(narr)
        words = len(narr.split())
        print(f"{out}: {words} words, ~{words/110:.0f} min at bedtime pace")
    elif mode == "sample":
        narr = load_narration(sys.argv[2])
        head = " ".join(narr.split()[:330])  # ~3 min of audio
        for tag, voice in [("andrew", "en-US-AndrewNeural"), ("ryan", "en-GB-RyanNeural")]:
            out = os.path.join(STUDIO, f"sample_{tag}.mp3")
            asyncio.run(tts(head, voice, out))
            print(f"{tag}: {out} ({duration(out):.1f}s) voice={voice}")
    elif mode == "tts":
        narr = load_narration(sys.argv[2])
        voice = sys.argv[sys.argv.index("--voice") + 1] if "--voice" in sys.argv else "en-US-AndrewNeural"
        base = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(STUDIO, "ep1")
        asyncio.run(tts(narr, voice, base + ".mp3", base + ".srt"))
        print(f"{base}.mp3 ({duration(base+'.mp3'):.0f}s = {duration(base+'.mp3')/60:.1f} min) + .srt")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
