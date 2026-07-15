#!/usr/bin/env python3
"""Mirror the live MOKIPOPS Facebook page posts into this repo.

Facebook serves post media from signed fbcdn URLs that expire within days, so
they can never be referenced directly from storefront-feed.json. This script
pulls each live published reel, transcodes it to a small web-friendly clip, and
writes it under assets/facebook/ where GitHub Pages serves it from a permanent
URL. It then rewrites the `gallery` channel of storefront-feed.json so the
storefront shows only real, already-published page posts.

Re-run it to pick up new posts:  python3 sync_facebook.py

Requires: yt-dlp (python3 -m yt_dlp), ffmpeg.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "assets" / "facebook"
FEED = ROOT / "storefront-feed.json"
PAGE = "https://www.facebook.com/mokipops"

# Live published reels on the MokiPops page, newest first. Nothing scheduled or
# from the content calendar belongs in here — only posts that are already public.
REELS = [
    "4410882532560355",
    "921647757546415",
    "844385741572870",
    "1183326977227331",
    "1162337872541076",
    "1213637517291982",
    "2112073225992851",
    "935132228068433",
    "414246087977226",
    "283209953801948",
]

# Tiles render ~240px square and autoplay muted, so a 480px short side with no
# audio track is plenty and keeps the whole strip light.
SHORT_SIDE = 480
CRF = "30"


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


# yt-dlp hands back this placeholder when a reel carries no real caption.
JUNK_TITLES = {"mokipops on reels", "mokipops", "facebook", ""}
FALLBACK = "MOKIPOPS on Facebook"


def caption_of(meta):
    """Facebook stuffs reaction counts into the title; keep the human sentence."""
    raw = (meta.get("description") or meta.get("title") or "").strip()
    # strip leading "12 reactions | " / "45 reactions · 11 shares | " noise
    if "|" in raw[:60]:
        head, _, tail = raw.partition("|")
        if "reaction" in head or "share" in head or "comment" in head:
            raw = tail.strip()
    # U+FFFD shows up where FB's emoji survived encoding badly; drop it and any
    # gap it leaves behind rather than shipping a mojibake caption as alt text.
    line = raw.replace("�", " ").replace("\n", " ")
    line = " ".join(line.split())
    if line.lower().strip(" .!") in JUNK_TITLES:
        return FALLBACK
    return (line[:117] + "...") if len(line) > 120 else line


def main():
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found")
    OUT.mkdir(parents=True, exist_ok=True)
    work = OUT / ".work"
    work.mkdir(exist_ok=True)

    entries = []
    for rid in REELS:
        url = f"https://www.facebook.com/reel/{rid}/"
        meta_raw = run([sys.executable, "-m", "yt_dlp", "--no-warnings", "--quiet",
                        "--skip-download", "--dump-single-json", url])
        if meta_raw.returncode != 0:
            print(f"  !! {rid}: metadata failed, skipped")
            continue
        meta = json.loads(meta_raw.stdout)

        mp4 = OUT / f"fb-{rid}.mp4"
        jpg = OUT / f"fb-{rid}.jpg"
        if mp4.exists() and jpg.exists():
            print(f"  -- {rid}  cached")
        else:
            src = work / f"{rid}.src"
            got = run([sys.executable, "-m", "yt_dlp", "--no-warnings", "--quiet",
                       "-f", "mp4/best", "-o", str(src), url])
            if got.returncode != 0 or not src.exists():
                print(f"  !! {rid}: download failed, skipped")
                continue
            # -an drops audio (tiles are muted); scale keeps the short side at 480
            run(["ffmpeg", "-y", "-i", str(src), "-an",
                 "-vf", f"scale='if(gt(iw,ih),-2,{SHORT_SIDE})':'if(gt(iw,ih),{SHORT_SIDE},-2)'",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", CRF,
                 "-movflags", "+faststart", str(mp4)])
            run(["ffmpeg", "-y", "-i", str(mp4), "-frames:v", "1", "-q:v", "4", str(jpg)])
            src.unlink(missing_ok=True)

        if not mp4.exists():
            print(f"  !! {rid}: transcode failed, skipped")
            continue

        entries.append({
            "mediaType": "video",
            "mediaUrl": f"assets/facebook/fb-{rid}.mp4",
            "thumbnail": f"assets/facebook/fb-{rid}.jpg",
            "title": caption_of(meta),
            "postUrl": f"https://www.facebook.com/reel/{rid}/",
            "posted": meta.get("upload_date"),
        })
        kb = mp4.stat().st_size / 1024
        print(f"  ok {rid}  {kb:7.0f}K  {entries[-1]['title'][:44]}")

    shutil.rmtree(work, ignore_errors=True)
    if not entries:
        sys.exit("no posts mirrored — aborting rather than emptying the feed")

    entries.sort(key=lambda e: e.get("posted") or "", reverse=True)

    feed = json.loads(FEED.read_text())
    feed["channels"]["gallery"] = entries
    feed["source"] = {"facebook": PAGE, "note": "gallery = live published page posts, mirrored locally"}
    FEED.write_text(json.dumps(feed, indent=1) + "\n")
    print(f"\ngallery channel rebuilt with {len(entries)} live Facebook posts")


if __name__ == "__main__":
    main()
