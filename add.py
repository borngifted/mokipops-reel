#!/usr/bin/env python3
"""Add new content to the MOKIPOPS living reel.

Videos are re-encoded for web (576px, streaming-friendly), a poster frame is
extracted, and the original is kept as a downloadable master. Audio is encoded
to AAC. Images are copied as-is. Everything lands in content.json under a drop.

Usage:
  python3 add.py video path/to/clip.mp4 --drop summer-drop --title "The Remix" --tag "House · vocal" --blurb "..."
  python3 add.py track path/to/song.mp3 --drop summer-drop --title "New Song" --desc "R&B · full length"
  python3 add.py image path/to/graphic.jpg --drop summer-drop --title "New Packaging"
  python3 add.py drop  --drop summer-drop --title "Summer Drop" --date 2026-08-01 --eyebrow "..." --intro "..."

Then:  ./publish.sh   (rebuilds the page, commits, and pushes live)
"""
import argparse, json, os, re, shutil, subprocess, sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(HERE, "content.json")
GRADIENTS = ["#F5A623,#E23A23", "#FF2E63,#FFD000", "#4CAF50,#00A6FB", "#FF6B35,#FF2E63", "#FFD000,#4CAF50"]

def load():
    with open(CONTENT, encoding="utf-8") as f:
        return json.load(f)

def save(data):
    with open(CONTENT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def get_drop(data, drop_id, create=False, **kw):
    for d in data["drops"]:
        if d["id"] == drop_id:
            return d
    if not create:
        sys.exit(f"Drop '{drop_id}' not found. Create it first:\n  python3 add.py drop --drop {drop_id} --title \"...\" [--date YYYY-MM-DD]")
    d = {"id": drop_id, "date": kw.get("date") or date.today().isoformat(),
         "title": kw.get("title") or drop_id.replace("-", " ").title(),
         "eyebrow": kw.get("eyebrow") or "", "intro": kw.get("intro") or "",
         "videos": [], "tracks": [], "images": []}
    data["drops"].append(d)
    return d

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"command failed: {' '.join(cmd)}\n{r.stderr[-800:]}")

def duration_str(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        s = float(r.stdout.strip())
        return f"{int(s // 60)}:{int(s % 60):02d}"
    except ValueError:
        return "?:??"

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("kind", choices=["video", "track", "image", "drop"])
    p.add_argument("file", nargs="?", help="source media file (not needed for 'drop')")
    p.add_argument("--drop", required=True, help="drop id, e.g. summer-drop")
    p.add_argument("--title", help="display title")
    p.add_argument("--tag", default="", help="short tag under a video title")
    p.add_argument("--blurb", default="", help="one-line description")
    p.add_argument("--desc", default="", help="track description")
    p.add_argument("--date", help="drop date YYYY-MM-DD (drop only, default today)")
    p.add_argument("--eyebrow", default="", help="drop eyebrow line")
    p.add_argument("--intro", default="", help="drop intro paragraph")
    p.add_argument("--poster-at", default="1.0", help="video poster timestamp seconds")
    args = p.parse_args()

    data = load()

    if args.kind == "drop":
        get_drop(data, args.drop, create=True, title=args.title, date=args.date,
                 eyebrow=args.eyebrow, intro=args.intro)
        save(data)
        print(f"drop '{args.drop}' ready")
        return

    if not args.file or not os.path.exists(args.file):
        sys.exit("source file missing or not found")
    title = args.title or os.path.splitext(os.path.basename(args.file))[0]
    sl = slug(title)
    drop = get_drop(data, args.drop, create=True)
    os.makedirs(os.path.join(HERE, "assets"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "masters"), exist_ok=True)

    if args.kind == "video":
        web = f"assets/{args.drop}-{sl}.mp4"
        poster = f"assets/{args.drop}-{sl}-poster.jpg"
        master = f"masters/MOKIPOPS-{args.drop}-{sl}.mp4"
        run(["ffmpeg", "-y", "-i", args.file, "-c:v", "libx264", "-crf", "26", "-preset", "slow",
             "-vf", "scale=576:-2", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
             os.path.join(HERE, web)])
        run(["ffmpeg", "-y", "-ss", args.poster_at, "-i", os.path.join(HERE, web),
             "-frames:v", "1", "-q:v", "4", os.path.join(HERE, poster)])
        shutil.copy(args.file, os.path.join(HERE, master))
        drop.setdefault("videos", []).append({
            "num": f"{len(drop.get('videos', [])) + 1:02d}", "title": title, "tag": args.tag,
            "blurb": args.blurb, "src": web, "poster": poster, "master": master})
        print(f"video '{title}' added to '{args.drop}'")

    elif args.kind == "track":
        web = f"assets/{args.drop}-{sl}.m4a"
        run(["ffmpeg", "-y", "-i", args.file, "-vn", "-c:a", "aac", "-b:a", "112k",
             os.path.join(HERE, web)])
        n = len(drop.get("tracks", []))
        drop.setdefault("tracks", []).append({
            "title": title, "desc": args.desc or args.blurb, "dur": duration_str(args.file),
            "gradient": GRADIENTS[n % len(GRADIENTS)], "src": web})
        print(f"track '{title}' added to '{args.drop}'")

    elif args.kind == "image":
        ext = os.path.splitext(args.file)[1].lower() or ".jpg"
        web = f"assets/{args.drop}-{sl}{ext}"
        shutil.copy(args.file, os.path.join(HERE, web))
        drop.setdefault("images", []).append({
            "title": title, "tag": args.tag, "blurb": args.blurb, "src": web})
        print(f"image '{title}' added to '{args.drop}'")

    save(data)
    print("now run: ./publish.sh")

if __name__ == "__main__":
    main()
