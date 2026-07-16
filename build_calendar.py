#!/usr/bin/env python3
"""Generate the selectable MOKIPOPS media picker page.

The page is intentionally served at calendar.html to keep the existing link,
but it is no longer date-based. It scans public site media, imports optimized
copies of external photos from the MOKIPOPS folder, and lets selected assets
be sent to Blotato as drafts.
"""

import base64
import json
import re
import hashlib
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT.parent
OUT = ROOT / "calendar.html"
SYNC_CONFIG = ROOT / "calendar-sync.json"
LIBRARY_DIR = ROOT / "assets" / "library"
IMPORTED_PHOTOS = LIBRARY_DIR / "imported" / "photos"
VIDEO_THUMBS = LIBRARY_DIR / "imported" / "video-thumbs"
EXTERNAL_VIDEOS_JSON = LIBRARY_DIR / "imported" / "external-videos.json"
DATA_JS = LIBRARY_DIR / "library-data.js"

PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v"}
MEDIA_EXTS = PHOTO_EXTS | VIDEO_EXTS
SCAN_DIRS = [ROOT / "assets", ROOT / "masters", ROOT / "social"]
EXTERNAL_SKIP = {
    ".git",
    "__pycache__",
    "Adobe Premiere Pro Audio Previews",
    "Adobe Premiere Pro Auto-Save",
    "mokipops-reel-site",
}
MAX_VIDEO_BYTES = 100 * 1024 * 1024

VIDEO_POSTERS = {
    "reel-anthem.mp4": "assets/poster-v1.jpg",
    "reel-beat.mp4": "assets/poster-v2.jpg",
    "reel-groove.mp4": "assets/poster-v3.jpg",
    "reel-original.mp4": "assets/poster-v4.jpg",
    "reel-bounce.mp4": "assets/poster-v6.jpg",
    "reel-step.mp4": "assets/poster-v7.jpg",
    "reel-wave.mp4": "assets/poster-v8.jpg",
    "reel-carnival.mp4": "assets/poster-v9.jpg",
    "reel-drift.mp4": "assets/poster-v10.jpg",
    "reel-piano.mp4": "assets/poster-v5.jpg",
    "final-post.mp4": "assets/poster-v1.jpg",
    "mokipops-waymo-reel-anthem.mp4": "assets/poster-v1.jpg",
    "mokipops-waymo-reel-beat.mp4": "assets/poster-v2.jpg",
    "mokipops-waymo-reel-groove.mp4": "assets/poster-v3.jpg",
    "mokipops-waymo-reel-original.mp4": "assets/poster-v4.jpg",
    "mokipops-waymo-reel-bounce.mp4": "assets/poster-v6.jpg",
    "mokipops-waymo-reel-step.mp4": "assets/poster-v7.jpg",
    "mokipops-waymo-reel-wave.mp4": "assets/poster-v8.jpg",
    "mokipops-waymo-reel-carnival.mp4": "assets/poster-v9.jpg",
    "mokipops-waymo-reel-drift.mp4": "assets/poster-v10.jpg",
    "mokipops-waymo-reel-piano.mp4": "assets/poster-v5.jpg",
}


def sync_settings():
    """Supabase connection for shared picks; empty values = browser-only mode."""
    if not SYNC_CONFIG.exists():
        return {"supabaseUrl": "", "anonKey": "", "table": "calendar_picks"}
    cfg = json.loads(SYNC_CONFIG.read_text())
    key = cfg.get("anonKey") or ""
    # Supabase keys are JWTs whose payload carries the role. Decode it rather
    # than string-matching the file, so a service_role key can never be baked
    # into a public page by mistake (it bypasses row-level security entirely).
    if key.count(".") == 2:
        try:
            body = key.split(".")[1]
            body += "=" * (-len(body) % 4)
            role = json.loads(base64.urlsafe_b64decode(body)).get("role")
        except Exception:
            role = None
        if role and role != "anon":
            raise SystemExit(
                f"{SYNC_CONFIG.name}: anonKey is a '{role}' key. That bypasses "
                "row-level security and must never ship to the browser — copy the "
                "anon/public key from Supabase > Project Settings > API instead."
            )
    return {
        "supabaseUrl": (cfg.get("supabaseUrl") or "").rstrip("/"),
        "anonKey": cfg.get("anonKey") or "",
        "table": cfg.get("table") or "calendar_picks",
    }


def safe_name(value):
    stem = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return stem[:70] or "asset"


def rel(path):
    return path.relative_to(ROOT).as_posix()


def write_if_changed(path, content):
    data = content.encode("utf-8")
    if path.exists() and path.read_bytes() == data:
        return
    path.write_bytes(data)


def is_external_photo(path):
    if path.suffix.lower() not in PHOTO_EXTS:
        return False
    parts = set(path.relative_to(SOURCE_ROOT).parts)
    return not bool(parts & EXTERNAL_SKIP)


def optimize_photo(source, dest):
    try:
        with Image.open(source) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
            dest.parent.mkdir(parents=True, exist_ok=True)
            img.save(dest, format="JPEG", quality=84, optimize=True, progressive=True)
            return True
    except Exception:
        return False


def source_token(source):
    stat = source.stat()
    value = f"{source.relative_to(SOURCE_ROOT).as_posix()}|{stat.st_size}|{int(stat.st_mtime)}"
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def import_external_photos():
    IMPORTED_PHOTOS.mkdir(parents=True, exist_ok=True)
    imported = 0
    skipped = 0
    for source in sorted(SOURCE_ROOT.rglob("*")):
        if not source.is_file() or not is_external_photo(source):
            continue
        try:
            digest = source_token(source)
        except OSError:
            skipped += 1
            continue
        prefix = f"{safe_name(source.stem)}-"
        if any(IMPORTED_PHOTOS.glob(f"{prefix}*.jpg")):
            imported += 1
            continue
        dest = IMPORTED_PHOTOS / f"{prefix}{digest}.jpg"
        if dest.exists():
            imported += 1
            continue
        if optimize_photo(source, dest):
            imported += 1
        else:
            skipped += 1
    return {"importedPhotos": imported, "skippedPhotos": skipped}


def pretty_title(path):
    stem = path.stem
    stem = re.sub(r"^(post|photo|video|prod|life|brand)[-_]?\d*", "", stem, flags=re.I)
    stem = stem.replace("_", " ").replace("-", " ")
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem.title() or path.name


def poster_for_video(path):
    name = path.name.lower()
    if name in VIDEO_POSTERS and (ROOT / VIDEO_POSTERS[name]).exists():
        return VIDEO_POSTERS[name]

    if "assets/calendar/interstitial/videos/" in rel(path):
        thumb = path.name.replace(".mp4", "_thumbnail.jpg")
        thumb = thumb.replace(".mov", "_thumbnail.jpg").replace(".m4v", "_thumbnail.jpg")
        candidate = ROOT / "assets" / "calendar" / "interstitial" / "thumbnails" / thumb
        if candidate.exists():
            return rel(candidate)

    if path.suffix.lower() == ".mp4":
        tokens = name.replace(".mp4", "").split("-")
        for token in reversed(tokens):
            candidate_name = f"poster-{token}.jpg"
            candidate = ROOT / "assets" / candidate_name
            if candidate.exists():
                return rel(candidate)
    return ""


def scan_public_media():
    files = []
    for folder in SCAN_DIRS:
        if not folder.exists():
            continue
        for path in folder.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in MEDIA_EXTS:
                continue
            if path.name.startswith("."):
                continue
            if VIDEO_THUMBS in path.parents:
                continue
            if path.suffix.lower() in VIDEO_EXTS and path.stat().st_size > MAX_VIDEO_BYTES:
                continue
            files.append(path)

    records = []
    seen = set()
    for path in sorted(files, key=lambda item: rel(item).lower()):
        relative = rel(path)
        if relative in seen:
            continue
        seen.add(relative)
        media_type = "video" if path.suffix.lower() in VIDEO_EXTS else "photo"
        folder = path.parent.relative_to(ROOT).as_posix()
        record = {
            "id": f"asset-{len(records) + 1:04d}",
            "mediaType": media_type,
            "title": pretty_title(path),
            "filename": path.name,
            "folder": folder,
            "extension": path.suffix.lower().lstrip("."),
            "sizeMb": round(path.stat().st_size / 1024 / 1024, 2),
            "mediaUrl": relative,
            "thumbnail": relative if media_type == "photo" else poster_for_video(path),
            "text": "MOKIPOPS — Bliss on a Stick\n\n#mokipops #blissonastick #atlanta #fruitpops",
        }
        records.append(record)
    return records


def scan_external_videos(start_index):
    """Videos too large for GitHub Pages, hosted on Blotato media storage.

    external-videos.json maps each original file to its hosted mediaUrl and a
    repo-local poster thumbnail generated at import time.
    """
    if not EXTERNAL_VIDEOS_JSON.exists():
        return []
    entries = json.loads(EXTERNAL_VIDEOS_JSON.read_text(encoding="utf-8"))
    records = []
    for entry in sorted(entries, key=lambda item: item["filename"].lower()):
        source = Path(entry["filename"])
        title = pretty_title(source)
        if re.fullmatch(r"[0-9A-Fa-f\s-]{12,}", title):
            title = f"Clip {source.stem[:8]}"
        thumb = entry.get("thumbnail", "")
        if thumb and not (ROOT / thumb).exists():
            thumb = ""
        records.append({
            "id": f"asset-{start_index + len(records) + 1:04d}",
            "mediaType": "video",
            "title": title,
            "filename": source.name,
            "folder": entry.get("folder", "icloud-photos"),
            "extension": source.suffix.lower().lstrip("."),
            "sizeMb": entry.get("sizeMb", 0),
            "mediaUrl": entry["mediaUrl"],
            "thumbnail": thumb,
            "text": "MOKIPOPS — Bliss on a Stick\n\n#mokipops #blissonastick #atlanta #fruitpops",
        })
    return records


def build_payload(records, scan):
    folders = sorted({record["folder"] for record in records})
    counts = {
        "total": len(records),
        "photo": sum(1 for record in records if record["mediaType"] == "photo"),
        "video": sum(1 for record in records if record["mediaType"] == "video"),
        "folders": len(folders),
    }
    return {
        "source": SOURCE_ROOT.as_posix(),
        "count": len(records),
        "counts": counts,
        "scan": scan,
        "folders": folders,
        "items": records,
    }


def render_page(payload):
    sync = sync_settings()
    sync_json = json.dumps(sync)
    # Blotato blocks browser calls from any origin but its own app, so route the
    # calendar's Blotato requests through the Supabase edge proxy that adds the
    # CORS header. With no Supabase URL configured, fall back to calling Blotato
    # directly (works for local server-side testing, blocked in a browser).
    if sync.get("supabaseUrl"):
        blotato_base = sync["supabaseUrl"].rstrip("/") + "/functions/v1/blotato-proxy"
    else:
        blotato_base = "https://backend.blotato.com/v2"
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>MOKIPOPS - Media Picker</title>
<meta name="robots" content="noindex">
<style>
@font-face {{ font-family:'Fraunces'; src:url(assets/fraunces.woff2) format('woff2'); font-weight:100 900; font-display:swap; }}
@font-face {{ font-family:'Archivo'; src:url(assets/archivo.woff2) format('woff2'); font-weight:100 900; font-display:swap; }}
:root {{
  --bg:#FFF6E9; --panel:#FBEAD0; --ink:#2A1A12; --sub:#5A463B; --line:rgba(42,26,18,.13);
  --card:#fff; --mango:#F5A623; --orange:#EE6C2B; --chili:#E23A23; --green:#5DA869; --teal:#4FB6A1; --pink:#EE5A8A;
  --shadow:0 18px 42px -30px rgba(120,50,10,.55);
}}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#211714; --panel:#2A1A12; --ink:#FFF6E9; --sub:#cdbba8; --line:rgba(255,246,233,.15); --card:#33211a; --shadow:0 18px 42px -30px rgba(0,0,0,.9); }}
}}
* {{ box-sizing:border-box; margin:0; padding:0; -webkit-tap-highlight-color:transparent; }}
body {{ font-family:'Archivo',-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif; background:var(--bg); color:var(--ink); line-height:1.42; padding-bottom:98px; -webkit-font-smoothing:antialiased; }}
h1,h2,h3 {{ font-family:'Fraunces',Georgia,serif; }}
button,input,select,textarea {{ font:inherit; }}
.top {{ position:sticky; top:0; z-index:40; display:flex; align-items:center; justify-content:space-between; gap:18px; padding:13px clamp(16px,4vw,40px); backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px); background:color-mix(in srgb,var(--bg) 84%,transparent); border-bottom:1px solid var(--line); }}
.wordmark {{ font-family:'Fraunces',Georgia,serif; font-weight:900; font-size:17px; white-space:nowrap; }}
.wordmark em {{ font-style:normal; color:var(--mango); }}
.nav {{ display:flex; flex-wrap:wrap; align-items:center; justify-content:flex-end; gap:14px; }}
.nav a {{ color:var(--chili); text-decoration:none; font-size:13px; font-weight:850; }}
.wrap {{ max-width:1380px; margin:0 auto; padding:0 clamp(16px,4vw,40px); }}
.hero {{ padding:clamp(32px,5vw,58px) 0 20px; text-align:center; }}
.eyebrow {{ display:inline-block; color:var(--chili); background:rgba(245,166,35,.16); border:1px solid rgba(245,166,35,.36); border-radius:999px; padding:7px 15px; font-size:12px; font-weight:850; letter-spacing:.09em; text-transform:uppercase; margin-bottom:18px; }}
h1 {{ font-size:clamp(34px,7vw,62px); line-height:1.02; font-weight:900; }}
.soft {{ background:linear-gradient(92deg,var(--mango),var(--orange) 48%,var(--chili)); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }}
.lede {{ max-width:780px; margin:18px auto 0; color:var(--sub); font-size:clamp(15px,2vw,18px); }}
.stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; max-width:860px; margin:24px auto 0; }}
.stat {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:11px 13px; text-align:left; box-shadow:var(--shadow); }}
.stat span {{ display:block; font-size:11px; color:var(--sub); font-weight:850; text-transform:uppercase; letter-spacing:.07em; }}
.stat b {{ display:block; font-size:18px; margin-top:2px; }}
.tools {{ display:grid; gap:14px; margin:20px 0 24px; }}
.panel {{ background:var(--card); border:1px solid var(--line); border-radius:16px; padding:16px; box-shadow:var(--shadow); }}
.filters {{ display:grid; grid-template-columns:minmax(190px,1fr) 150px minmax(160px,.7fr) 150px auto auto; gap:10px; align-items:end; }}
.field label {{ display:block; color:var(--sub); font-size:11px; font-weight:850; letter-spacing:.07em; text-transform:uppercase; margin:0 0 6px 2px; }}
.field input,.field select,.field textarea {{ width:100%; border:1.5px solid var(--line); background:var(--bg); color:var(--ink); border-radius:12px; padding:10px 12px; min-height:42px; }}
.draft-grid {{ display:grid; grid-template-columns:1.2fr .75fr .85fr .85fr .75fr; gap:10px; align-items:end; }}
.actions {{ display:flex; flex-wrap:wrap; gap:9px; align-items:center; }}
.btn {{ border:1.5px solid var(--line); background:var(--card); color:var(--ink); border-radius:999px; min-height:42px; padding:10px 16px; font-weight:850; cursor:pointer; }}
.btn.primary {{ border-color:transparent; color:#fff; background:linear-gradient(90deg,var(--mango),var(--chili)); }}
.btn.warn {{ border-color:rgba(226,58,35,.35); color:var(--chili); }}
.btn:disabled {{ opacity:.46; cursor:not-allowed; }}
.status {{ margin-top:12px; color:var(--sub); font-size:13px; min-height:20px; }}
.log {{ margin-top:10px; display:grid; gap:6px; max-height:170px; overflow:auto; }}
.log div {{ border:1px solid var(--line); border-radius:10px; padding:8px 10px; font-size:12px; background:color-mix(in srgb,var(--bg) 72%,var(--card)); }}
.log .ok {{ border-color:rgba(93,168,105,.45); color:var(--green); }}
.log .bad {{ border-color:rgba(226,58,35,.45); color:var(--chili); }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(168px,1fr)); gap:12px; }}
.asset {{ position:relative; text-align:left; border:1px solid var(--line); background:var(--card); color:var(--ink); border-radius:14px; overflow:hidden; cursor:pointer; box-shadow:var(--shadow); }}
.sync {{ font-weight:600; font-size:12px; padding:3px 9px; border-radius:999px; margin-left:8px; }}
.sync.ok {{ color:#0a7d4b; background:rgba(10,125,75,.12); }}
.sync.warn {{ color:#8a5a00; background:rgba(245,166,35,.16); }}
.sync.err {{ color:#a32116; background:rgba(226,58,35,.12); }}
.adopt {{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin:10px 0;
  padding:10px 14px; border-radius:10px; background:rgba(245,166,35,.14); border:1px solid rgba(245,166,35,.4); font-size:13px; }}
.asset .by {{ position:absolute; left:8px; top:8px; z-index:2; max-width:60%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
  padding:3px 8px; border-radius:999px; font-size:11px; font-weight:700;
  color:#fff; background:rgba(20,12,8,.72); backdrop-filter:blur(2px); }}
.asset[aria-pressed="true"] {{ border-color:var(--mango); outline:2px solid rgba(245,166,35,.24); }}
.thumb {{ position:relative; aspect-ratio:4/5; background:var(--panel); overflow:hidden; }}
.thumb img {{ width:100%; height:100%; object-fit:cover; display:block; }}
.placeholder {{ width:100%; height:100%; display:grid; place-items:center; padding:18px; color:#fff; text-align:center; font-weight:900; background:linear-gradient(135deg,var(--orange),var(--chili)); }}
.badge {{ position:absolute; left:8px; top:8px; z-index:2; display:inline-flex; align-items:center; gap:4px; color:#fff; border-radius:999px; padding:5px 8px; font-size:10px; line-height:1; font-weight:900; letter-spacing:.06em; background:rgba(42,26,18,.82); }}
.asset[data-media="video"] .badge {{ background:linear-gradient(90deg,var(--orange),var(--chili)); }}
.play {{ position:absolute; inset:0; display:grid; place-items:center; color:#fff; font-size:36px; text-shadow:0 2px 14px rgba(0,0,0,.65); background:radial-gradient(circle,rgba(0,0,0,.2),rgba(0,0,0,0) 45%); }}
.check {{ position:absolute; top:9px; right:9px; z-index:3; width:30px; height:30px; border-radius:50%; display:grid; place-items:center; font-weight:900; color:transparent; background:rgba(255,255,255,.88); border:1px solid var(--line); }}
.asset[aria-pressed="true"] .check {{ color:#fff; border-color:transparent; background:linear-gradient(135deg,var(--mango),var(--chili)); }}
.meta {{ display:grid; gap:5px; padding:10px; min-height:116px; }}
.title {{ font-size:13px; font-weight:900; overflow-wrap:anywhere; }}
.folder {{ color:var(--sub); font-size:11px; overflow-wrap:anywhere; }}
.size {{ color:#a57942; font-size:11px; font-weight:850; }}
.empty {{ text-align:center; color:var(--sub); padding:32px; border:1px dashed var(--line); border-radius:16px; }}
.bar {{ position:fixed; left:0; right:0; bottom:0; z-index:50; display:flex; align-items:center; justify-content:space-between; gap:12px; padding:12px clamp(16px,4vw,40px) calc(12px + env(safe-area-inset-bottom)); background:color-mix(in srgb,var(--bg) 88%,transparent); backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px); border-top:1px solid var(--line); }}
.count {{ font-weight:900; }}
.count b {{ color:var(--chili); font-variant-numeric:tabular-nums; }}
.eye {{ position:absolute; right:9px; bottom:9px; z-index:3; width:32px; height:32px; border-radius:50%; display:grid; place-items:center; font-size:14px; background:rgba(255,255,255,.92); color:#2A1A12; border:1px solid var(--line); cursor:zoom-in; }}
.lightbox {{ position:fixed; inset:0; z-index:100; display:none; align-items:center; justify-content:center; padding:18px; background:rgba(18,9,5,.88); backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px); }}
.lightbox.open {{ display:flex; }}
.lb-inner {{ width:min(1080px,96vw); display:grid; gap:12px; }}
.lb-media {{ display:grid; place-items:center; }}
.lb-media img, .lb-media video {{ max-width:100%; max-height:72vh; border-radius:14px; background:#000; }}
.lb-bar {{ display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap; color:#fff; }}
.lb-title {{ font-weight:900; font-size:14px; overflow-wrap:anywhere; }}
.lb-sub {{ color:rgba(255,255,255,.72); font-size:12px; }}
.lb-actions {{ display:flex; gap:8px; }}
.lb-btn {{ border:1.5px solid rgba(255,255,255,.35); background:rgba(255,255,255,.12); color:#fff; border-radius:999px; min-height:40px; padding:8px 15px; font-weight:850; cursor:pointer; }}
.lb-btn.primary {{ border-color:transparent; background:linear-gradient(90deg,var(--mango),var(--chili)); }}
.lb-x {{ position:fixed; top:14px; right:16px; z-index:101; width:42px; height:42px; border-radius:50%; border:1.5px solid rgba(255,255,255,.35); background:rgba(255,255,255,.12); color:#fff; font-size:18px; font-weight:900; cursor:pointer; }}
.lb-nav {{ position:fixed; top:50%; transform:translateY(-50%); z-index:101; width:44px; height:44px; border-radius:50%; border:1.5px solid rgba(255,255,255,.35); background:rgba(255,255,255,.12); color:#fff; font-size:18px; cursor:pointer; }}
.lb-prev {{ left:14px; }}
.lb-next {{ right:14px; }}
@media (max-width:620px) {{ .lb-nav {{ top:auto; bottom:calc(16px + env(safe-area-inset-bottom)); }} }}
@media (max-width:1050px) {{
  .filters,.draft-grid {{ grid-template-columns:1fr 1fr; }}
  .stats {{ grid-template-columns:repeat(2,1fr); }}
}}
@media (max-width:620px) {{
  .top {{ align-items:flex-start; flex-direction:column; gap:8px; }}
  .nav {{ justify-content:flex-start; }}
  .filters,.draft-grid,.stats {{ grid-template-columns:1fr; }}
  .grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }}
  .bar {{ align-items:stretch; flex-direction:column; }}
  .bar .actions {{ width:100%; }}
  .bar .btn {{ flex:1; }}
}}
</style>
</head>
<body>
<div class="top">
  <div class="wordmark">MOKI<em>POPS</em></div>
  <nav class="nav" aria-label="Site">
    <a href="index.html">Reel</a>
    <a href="picks.html">Quick Picks</a>
    <a href="status.html">Posting Status</a>
  </nav>
</div>

<main class="wrap">
  <header class="hero">
    <span class="eyebrow">Media Picker</span>
    <h1>All postable <span class="soft">MOKIPOPS media.</span></h1>
    <p class="lede">Select photos or videos from the scanned asset library and create Blotato drafts from public media URLs. Tap ⛶ on any card to view the photo or play the video.</p>
    <div class="stats" aria-label="Media stats">
      <div class="stat"><span>Total assets</span><b id="statTotal">{payload["counts"]["total"]}</b></div>
      <div class="stat"><span>Photos</span><b id="statPhotos">{payload["counts"]["photo"]}</b></div>
      <div class="stat"><span>Videos</span><b id="statVideos">{payload["counts"]["video"]}</b></div>
      <div class="stat"><span>Folders</span><b id="statFolders">{payload["counts"]["folders"]}</b></div>
    </div>
  </header>

  <section class="tools" aria-label="Media controls">
    <div class="panel">
      <div class="filters">
        <div class="field"><label for="q">Search</label><input id="q" type="search" placeholder="Filename, title, folder"></div>
        <div class="field"><label for="mediaType">Media</label><select id="mediaType"><option value="">Photos + videos</option><option value="photo">Photos only</option><option value="video">Videos only</option></select></div>
        <div class="field"><label for="folder">Folder</label><select id="folder"></select></div>
        <div class="field"><label for="sort">Sort</label><select id="sort"><option value="folder">Folder</option><option value="type">Type</option><option value="name">Name</option><option value="size">Size</option></select></div>
        <button class="btn" id="selectVisible" type="button">Select Visible</button>
        <button class="btn warn" id="clear" type="button">Clear</button>
      </div>
    </div>

    <div class="panel">
      <div class="draft-grid">
        <div class="field"><label for="apiKey">Blotato API key</label><input id="apiKey" type="password" placeholder="Stored in this browser"></div>
        <div class="field"><label for="platform">Platform</label><select id="platform">
          <option value="instagram">Instagram</option>
          <option value="facebook">Facebook</option>
          <option value="linkedin">LinkedIn</option>
          <option value="twitter">X / Twitter</option>
          <option value="threads">Threads</option>
          <option value="bluesky">Bluesky</option>
          <option value="pinterest">Pinterest</option>
          <option value="tiktok">TikTok</option>
        </select></div>
        <div class="field"><label for="accountId">Account ID</label><input id="accountId" list="accounts" placeholder="Load or paste ID"><datalist id="accounts"></datalist></div>
        <div class="field"><label for="subId" id="subLabel">Page / board ID</label><input id="subId" placeholder="If required"></div>
        <div class="field"><label for="postMode">Post mode</label><select id="postMode"><option value="draft">Draft only</option><option value="next">Next free slot</option></select></div>
      </div>
      <div class="actions" style="margin-top:12px">
        <button class="btn" id="loadAccounts" type="button">Load Accounts</button>
        <button class="btn" id="downloadPayloads" type="button">Download Payloads</button>
        <button class="btn primary" id="createDrafts" type="button" disabled>Create Drafts</button>
        <select id="feedChannel" aria-label="Storefront feed channel" style="border:1.5px solid var(--line);background:var(--bg);color:var(--ink);border-radius:999px;min-height:42px;padding:8px 14px;">
          <option value="gallery">Store: Gallery</option>
          <option value="lifestyle-events">Store: Events</option>
          <option value="lifestyle-markets">Store: Markets</option>
          <option value="lifestyle-waymo">Store: Waymo</option>
          <option value="lifestyle-bts">Store: Behind the Scenes</option>
        </select>
        <button class="btn" id="downloadFeed" type="button">Download Storefront Feed</button>
      </div>
      <div class="status" id="status">Ready.</div>
      <div class="log" id="log" aria-live="polite"></div>
    </div>
  </section>

  <section class="grid" id="grid" aria-label="Media assets"></section>
</main>

<div class="lightbox" id="lightbox" role="dialog" aria-modal="true" aria-label="Media preview">
  <button class="lb-x" id="lbClose" type="button" aria-label="Close preview">✕</button>
  <button class="lb-nav lb-prev" id="lbPrev" type="button" aria-label="Previous asset">‹</button>
  <button class="lb-nav lb-next" id="lbNext" type="button" aria-label="Next asset">›</button>
  <div class="lb-inner">
    <div class="lb-media" id="lbMedia"></div>
    <div class="lb-bar">
      <div>
        <div class="lb-title" id="lbTitle"></div>
        <div class="lb-sub" id="lbSub"></div>
      </div>
      <div class="lb-actions">
        <button class="lb-btn" id="lbOpen" type="button">Open File</button>
        <button class="lb-btn primary" id="lbSelect" type="button">Select</button>
      </div>
    </div>
  </div>
</div>

<div class="bar">
  <div class="count"><b id="selectedCount">0</b> selected <span id="syncStatus" class="sync">…</span>
    <button class="btn" id="whoami" type="button" title="Change the name saved with your picks">Who am I?</button>
  </div>
  <div class="adopt" id="adoptBanner" hidden>
    <span><b id="adoptCount">0</b> selections saved in this browser aren't in the shared list yet.</span>
    <button class="btn" id="adoptYes" type="button">Add them to the shared list</button>
    <button class="btn warn" id="adoptNo" type="button">Keep them local</button>
  </div>
  <div class="actions">
    <button class="btn" id="selectedOnly" type="button" aria-pressed="false">Selected Only</button>
    <button class="btn primary" id="createDraftsBottom" type="button" disabled>Create Drafts</button>
  </div>
</div>

<script src="assets/library/library-data.js"></script>
<script>
const API_BASE = "{blotato_base}";
const data = window.MOKIPOPS_LIBRARY;
const items = data.items;
const byId = new Map(items.map(item => [item.id, item]));
const selectedKey = "mokipops-media-selected-v1";
const settingsKey = "mokipops-media-settings-v1";
const reviewerKey = "mokipops-reviewer-v1";
const adoptedKey = "mokipops-adopted-v1";
const selected = new Set(JSON.parse(localStorage.getItem(selectedKey) || "[]").filter(id => byId.has(id)));
/* Whatever this browser had picked before it could ever sync. The first
   pullPicks() rewrites localStorage from the shared list, so this snapshot is
   the only surviving record of picks made back when the page saved nowhere —
   offerAdoption() reads this, never localStorage. */
const localAtBoot = [...selected];
let selectedOnly = false;
let visibleIds = [];

/* ---- shared picks (Supabase) -------------------------------------------
   The calendar is a static GitHub Pages file, so it cannot store anything
   itself. Picks live in a Supabase table instead, which is what lets several
   reviewers in different places build one shared list. With no credentials
   configured everything below no-ops and selections stay browser-only.       */
const SYNC = {sync_json};
const syncOn = () => Boolean(SYNC.supabaseUrl && SYNC.anonKey);
const pickedBy = new Map();      // item id -> {{ by, at }}
const inFlight = new Set();      // ids mid-write; a poll must not clobber them
let reviewer = localStorage.getItem(reviewerKey) || "";
let lastSync = null;
let syncErr = null;

function sbUrl(qs) {{
  return SYNC.supabaseUrl + "/rest/v1/" + SYNC.table + (qs ? "?" + qs : "");
}}

function sbFetch(qs, options) {{
  const opts = options || {{}};
  return fetch(sbUrl(qs), Object.assign({{}}, opts, {{
    headers: Object.assign({{
      apikey: SYNC.anonKey,
      Authorization: "Bearer " + SYNC.anonKey,
      "Content-Type": "application/json"
    }}, opts.headers || {{}})
  }}));
}}

/* Pull the shared list and rebuild local state from it. Ids with a write in
   flight keep their optimistic value so a poll can't undo a fresh click. */
async function pullPicks() {{
  if (!syncOn()) return;
  try {{
    const res = await sbFetch("select=item_id,picked_by,picked_at");
    if (!res.ok) throw new Error("HTTP " + res.status);
    const rows = await res.json();
    pickedBy.clear();
    const remote = new Set();
    for (const row of rows) {{
      if (!byId.has(row.item_id)) continue;   // asset removed from the library
      remote.add(row.item_id);
      pickedBy.set(row.item_id, {{ by: row.picked_by, at: row.picked_at }});
    }}
    for (const id of selected) if (inFlight.has(id)) remote.add(id);
    for (const id of inFlight) if (!selected.has(id)) remote.delete(id);
    selected.clear();
    remote.forEach(id => selected.add(id));
    saveSelected();
    lastSync = new Date();
    syncErr = null;
    render();
    offerAdoption();
  }} catch (err) {{
    syncErr = err.message;
    updateSyncStatus();
  }}
}}

async function pushPick(id) {{
  if (!syncOn()) return true;
  inFlight.add(id);
  try {{
    // ignore-duplicates, not merge: if someone already added this item the row
    // stays credited to them. merge would rewrite picked_by to whoever raced in
    // last, and it also needs an UPDATE policy the table deliberately lacks.
    const res = await sbFetch("", {{
      method: "POST",
      headers: {{ Prefer: "resolution=ignore-duplicates" }},
      body: JSON.stringify([{{ item_id: id, picked_by: reviewer || "unknown" }}])
    }});
    if (!res.ok) throw new Error("HTTP " + res.status);
    pickedBy.set(id, {{ by: reviewer, at: new Date().toISOString() }});
    lastSync = new Date();
    syncErr = null;
    return true;
  }} catch (err) {{
    syncErr = err.message;
    return false;
  }} finally {{
    inFlight.delete(id);
    updateSyncStatus();
  }}
}}

async function dropPick(id) {{
  if (!syncOn()) return true;
  inFlight.add(id);
  try {{
    const res = await sbFetch("item_id=eq." + encodeURIComponent(id), {{ method: "DELETE" }});
    if (!res.ok) throw new Error("HTTP " + res.status);
    pickedBy.delete(id);
    lastSync = new Date();
    syncErr = null;
    return true;
  }} catch (err) {{
    syncErr = err.message;
    return false;
  }} finally {{
    inFlight.delete(id);
    updateSyncStatus();
  }}
}}

/* Picks made before this page could save are still sitting in the reviewer's
   own browser. Offer to lift them into the shared list rather than lose them. */
function offerAdoption() {{
  if (!syncOn() || localStorage.getItem(adoptedKey)) return;
  const local = localAtBoot.filter(id => byId.has(id) && !pickedBy.has(id));
  const banner = document.getElementById("adoptBanner");
  if (!banner) return;
  if (!local.length) {{ banner.hidden = true; return; }}
  document.getElementById("adoptCount").textContent = local.length;
  banner.hidden = false;
  banner.dataset.ids = JSON.stringify(local);
}}

async function adoptLocal() {{
  const banner = document.getElementById("adoptBanner");
  const ids = JSON.parse(banner.dataset.ids || "[]");
  if (!(await ensureReviewer())) return;
  for (const id of ids) {{ selected.add(id); await pushPick(id); }}
  localStorage.setItem(adoptedKey, "1");
  banner.hidden = true;
  render();
}}

async function ensureReviewer() {{
  if (reviewer) return true;
  const name = window.prompt("Your name (saved with each pick so everyone can see who chose what):", "");
  if (!name || !name.trim()) return false;
  reviewer = name.trim().slice(0, 40);
  localStorage.setItem(reviewerKey, reviewer);
  updateSyncStatus();
  return true;
}}

function updateSyncStatus() {{
  const el = document.getElementById("syncStatus");
  if (!el) return;
  if (!syncOn()) {{
    el.textContent = "browser-only — picks are not shared";
    el.className = "sync warn";
    return;
  }}
  const who = reviewer ? reviewer : "not signed in";
  if (syncErr) {{
    el.textContent = "offline · saved in this browser · " + who;
    el.className = "sync err";
  }} else {{
    const t = lastSync ? lastSync.toLocaleTimeString() : "…";
    el.textContent = "shared · synced " + t + " · " + who;
    el.className = "sync ok";
  }}
}}

const els = {{
  q: document.getElementById("q"),
  mediaType: document.getElementById("mediaType"),
  folder: document.getElementById("folder"),
  sort: document.getElementById("sort"),
  grid: document.getElementById("grid"),
  selectedCount: document.getElementById("selectedCount"),
  selectedOnly: document.getElementById("selectedOnly"),
  selectVisible: document.getElementById("selectVisible"),
  clear: document.getElementById("clear"),
  apiKey: document.getElementById("apiKey"),
  platform: document.getElementById("platform"),
  accountId: document.getElementById("accountId"),
  accounts: document.getElementById("accounts"),
  subId: document.getElementById("subId"),
  subLabel: document.getElementById("subLabel"),
  postMode: document.getElementById("postMode"),
  loadAccounts: document.getElementById("loadAccounts"),
  createDrafts: document.getElementById("createDrafts"),
  createDraftsBottom: document.getElementById("createDraftsBottom"),
  downloadPayloads: document.getElementById("downloadPayloads"),
  status: document.getElementById("status"),
  log: document.getElementById("log"),
  lightbox: document.getElementById("lightbox"),
  lbMedia: document.getElementById("lbMedia"),
  lbTitle: document.getElementById("lbTitle"),
  lbSub: document.getElementById("lbSub"),
  lbSelect: document.getElementById("lbSelect"),
  lbOpen: document.getElementById("lbOpen"),
  lbClose: document.getElementById("lbClose"),
  lbPrev: document.getElementById("lbPrev"),
  lbNext: document.getElementById("lbNext")
}};

const settings = JSON.parse(localStorage.getItem(settingsKey) || "{{}}");
for (const key of ["apiKey", "platform", "accountId", "subId", "postMode"]) {{
  if (settings[key]) els[key].value = settings[key];
}}

function escapeHtml(value) {{
  return String(value || "").replace(/[&<>"']/g, char => ({{"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}}[char]));
}}

function saveSelected() {{
  localStorage.setItem(selectedKey, JSON.stringify([...selected]));
}}

function saveSettings() {{
  const next = {{
    apiKey: els.apiKey.value.trim(),
    platform: els.platform.value,
    accountId: els.accountId.value.trim(),
    subId: els.subId.value.trim(),
    postMode: els.postMode.value
  }};
  localStorage.setItem(settingsKey, JSON.stringify(next));
  updateActions();
}}

function fillFolders() {{
  els.folder.innerHTML = '<option value="">All folders</option>' + data.folders.map(folder => `<option value="${{escapeHtml(folder)}}">${{escapeHtml(folder)}}</option>`).join("");
}}

function matches(item) {{
  if (selectedOnly && !selected.has(item.id)) return false;
  if (els.mediaType.value && item.mediaType !== els.mediaType.value) return false;
  if (els.folder.value && item.folder !== els.folder.value) return false;
  const query = els.q.value.trim().toLowerCase();
  if (!query) return true;
  return [item.title, item.filename, item.folder, item.extension, item.mediaType].join(" ").toLowerCase().includes(query);
}}

function sorted(list) {{
  const next = [...list];
  const mode = els.sort.value;
  next.sort((a, b) => {{
    if (mode === "size") return b.sizeMb - a.sizeMb || a.filename.localeCompare(b.filename);
    if (mode === "type") return a.mediaType.localeCompare(b.mediaType) || a.folder.localeCompare(b.folder) || a.filename.localeCompare(b.filename);
    if (mode === "name") return a.filename.localeCompare(b.filename);
    return a.folder.localeCompare(b.folder) || a.filename.localeCompare(b.filename);
  }});
  return next;
}}

function mediaThumb(item) {{
  const label = item.mediaType === "video" ? "VIDEO" : "PHOTO";
  const icon = item.mediaType === "video" ? "▶" : "●";
  const image = item.thumbnail ? `<img src="${{escapeHtml(item.thumbnail)}}" alt="" loading="lazy">` : `<span class="placeholder">${{escapeHtml(item.extension.toUpperCase())}}</span>`;
  return `
    <span class="thumb">
      ${{image}}
      <span class="badge">${{icon}} ${{label}}</span>
      ${{item.mediaType === "video" ? '<span class="play" aria-hidden="true">▶</span>' : ''}}
    </span>`;
}}

function render() {{
  const filtered = sorted(items.filter(matches));
  visibleIds = filtered.map(item => item.id);
  if (!filtered.length) {{
    els.grid.innerHTML = '<div class="empty">No assets match the current filters.</div>';
    updateActions();
    return;
  }}
  els.grid.innerHTML = "";
  const fragment = document.createDocumentFragment();
  for (const item of filtered) {{
    const card = document.createElement("button");
    card.type = "button";
    card.className = "asset";
    card.dataset.id = item.id;
    card.dataset.media = item.mediaType;
    card.setAttribute("aria-pressed", selected.has(item.id) ? "true" : "false");
    const mark = pickedBy.get(item.id);
    card.innerHTML = `
      ${{mediaThumb(item)}}
      <span class="check" aria-hidden="true">✓</span>
      <span class="eye" data-eye role="button" aria-label="Preview ${{escapeHtml(item.title)}}" title="Preview">⛶</span>
      ${{mark ? `<span class="by" title="Picked by ${{escapeHtml(mark.by)}}">${{escapeHtml(mark.by)}}</span>` : ""}}
      <span class="meta">
        <span class="title">${{escapeHtml(item.title)}}</span>
        <span class="folder">${{escapeHtml(item.folder)}}</span>
        <span class="size">${{escapeHtml(item.extension.toUpperCase())}} · ${{item.sizeMb}} MB</span>
      </span>`;
    card.addEventListener("click", event => {{
      if (event.target.closest("[data-eye]")) {{
        openPreview(item.id);
        return;
      }}
      toggle(item.id, card);
    }});
    fragment.appendChild(card);
  }}
  els.grid.appendChild(fragment);
  updateActions();
}}

async function toggle(id, card) {{
  const adding = !selected.has(id);
  // A pick is worthless without knowing whose it is, so get a name up front.
  if (adding && syncOn() && !(await ensureReviewer())) return;

  if (adding) selected.add(id); else selected.delete(id);   // optimistic
  saveSelected();
  if (card) card.setAttribute("aria-pressed", String(adding));
  updateActions();

  const ok = adding ? await pushPick(id) : await dropPick(id);
  if (!ok) {{
    // Roll the UI back so it never claims a pick the shared list didn't take.
    if (adding) selected.delete(id); else selected.add(id);
    saveSelected();
    render();
  }} else {{
    render();
  }}
}}

function selectedItems() {{
  return items.filter(item => selected.has(item.id));
}}

function updateActions() {{
  const canDraft = selected.size > 0 && els.apiKey.value.trim() && els.accountId.value.trim();
  els.selectedCount.textContent = selected.size;
  els.createDrafts.disabled = !canDraft;
  els.createDraftsBottom.disabled = !canDraft;
  els.downloadPayloads.disabled = selected.size === 0;
  updateSubLabel();
}}

function updateSubLabel() {{
  const labels = {{
    facebook: "Facebook page ID",
    linkedin: "LinkedIn page ID",
    pinterest: "Pinterest board ID",
    tiktok: "TikTok options",
  }};
  els.subLabel.textContent = labels[els.platform.value] || "Page / board ID";
}}

function targetFor(platform) {{
  const subId = els.subId.value.trim();
  const target = {{ targetType: platform }};
  if (platform === "facebook") {{
    if (!subId) throw new Error("Facebook needs a page ID.");
    target.pageId = subId;
  }}
  if (platform === "linkedin" && subId) target.pageId = subId;
  if (platform === "pinterest") {{
    if (!subId) throw new Error("Pinterest needs a board ID.");
    target.boardId = subId;
  }}
  if (platform === "tiktok") {{
    Object.assign(target, {{
      privacyLevel: "SELF_ONLY",
      disabledComments: false,
      disabledDuet: false,
      disabledStitch: false,
      isBrandedContent: true,
      isYourBrand: true,
      isAiGenerated: false,
      isDraft: true
    }});
  }}
  return target;
}}

function payloadFor(item) {{
  const platform = els.platform.value;
  const payload = {{
    post: {{
      accountId: els.accountId.value.trim(),
      content: {{
        text: item.text,
        mediaUrls: [new URL(item.mediaUrl, window.location.href).href],
        platform
      }},
      target: targetFor(platform)
    }}
  }};
  if (els.postMode.value === "next") payload.useNextFreeSlot = true;
  return payload;
}}

async function blotato(path, options = {{}}) {{
  const headers = Object.assign({{
    "Content-Type": "application/json",
    "blotato-api-key": els.apiKey.value.trim()
  }}, options.headers || {{}});
  const response = await fetch(API_BASE + path, Object.assign({{}}, options, {{ headers }}));
  if (!response.ok) {{
    let detail = "";
    try {{
      const error = await response.json();
      detail = error.message || error.errorMessage || JSON.stringify(error);
    }} catch (_) {{
      detail = await response.text();
    }}
    throw new Error(`${{response.status}} ${{detail || response.statusText}}`);
  }}
  if (response.status === 204) return {{}};
  return response.json();
}}

function setBusy(isBusy) {{
  for (const button of [els.loadAccounts, els.createDrafts, els.createDraftsBottom, els.downloadPayloads]) {{
    button.disabled = isBusy || (button !== els.loadAccounts && selected.size === 0);
  }}
  if (!isBusy) updateActions();
}}

function logLine(message, type = "") {{
  const line = document.createElement("div");
  line.className = type;
  line.textContent = message;
  els.log.prepend(line);
}}

function sleep(ms) {{
  return new Promise(resolve => setTimeout(resolve, ms));
}}

async function loadAccounts() {{
  if (!els.apiKey.value.trim()) {{
    els.status.textContent = "Add a Blotato API key first.";
    return;
  }}
  saveSettings();
  setBusy(true);
  els.status.textContent = "Loading Blotato accounts...";
  try {{
    const result = await blotato(`/users/me/accounts?platform=${{encodeURIComponent(els.platform.value)}}`, {{ method:"GET" }});
    const accounts = result.items || [];
    els.accounts.innerHTML = accounts.map(item => `<option value="${{escapeHtml(item.id)}}">${{escapeHtml([item.fullname, item.username, item.platform].filter(Boolean).join(" - "))}}</option>`).join("");
    if (accounts.length && !els.accountId.value.trim()) {{
      els.accountId.value = accounts[0].id;
      saveSettings();
    }}
    els.status.textContent = `${{accounts.length}} account${{accounts.length === 1 ? "" : "s"}} loaded.`;
  }} catch (error) {{
    els.status.textContent = "Could not load accounts.";
    logLine(error.message || String(error), "bad");
  }} finally {{
    setBusy(false);
  }}
}}

async function createDrafts() {{
  const chosen = selectedItems();
  if (!chosen.length) return;
  saveSettings();
  els.log.innerHTML = "";
  setBusy(true);
  let ok = 0;
  let failed = 0;
  els.status.textContent = `Creating ${{chosen.length}} Blotato draft${{chosen.length === 1 ? "" : "s"}}...`;
  for (const [index, item] of chosen.entries()) {{
    try {{
      const result = await blotato("/posts", {{
        method: "POST",
        body: JSON.stringify(payloadFor(item))
      }});
      ok += 1;
      logLine(`${{item.filename}} - draft queued${{result.postSubmissionId ? " (" + result.postSubmissionId + ")" : ""}}`, "ok");
    }} catch (error) {{
      failed += 1;
      logLine(`${{item.filename}} failed - ${{error.message || error}}`, "bad");
      if (/401|403/.test(String(error.message))) break;
    }}
    if (index < chosen.length - 1) await sleep(2200);
  }}
  els.status.textContent = `${{ok}} draft${{ok === 1 ? "" : "s"}} created${{failed ? ", " + failed + " failed" : ""}}.`;
  setBusy(false);
}}

let previewId = null;

function mediaUrlFor(item) {{
  return new URL(item.mediaUrl, window.location.href).href;
}}

function openPreview(id) {{
  previewId = id;
  renderPreview();
  els.lightbox.classList.add("open");
  document.body.style.overflow = "hidden";
}}

function renderPreview() {{
  const item = byId.get(previewId);
  if (!item) return;
  const url = escapeHtml(mediaUrlFor(item));
  if (item.mediaType === "video") {{
    const poster = item.thumbnail ? ` poster="${{escapeHtml(item.thumbnail)}}"` : "";
    els.lbMedia.innerHTML = `<video src="${{url}}" controls autoplay playsinline preload="metadata"${{poster}}></video>`;
  }} else {{
    els.lbMedia.innerHTML = `<img src="${{url}}" alt="${{escapeHtml(item.title)}}">`;
  }}
  els.lbTitle.textContent = item.title;
  els.lbSub.textContent = `${{item.folder}} · ${{item.extension.toUpperCase()}} · ${{item.sizeMb}} MB · ${{item.mediaType}}`;
  updatePreviewSelect();
}}

function updatePreviewSelect() {{
  els.lbSelect.textContent = selected.has(previewId) ? "✓ Selected" : "Select";
}}

function closePreview() {{
  els.lightbox.classList.remove("open");
  els.lbMedia.innerHTML = "";
  document.body.style.overflow = "";
  previewId = null;
}}

function stepPreview(delta) {{
  if (!visibleIds.length || previewId === null) return;
  const index = visibleIds.indexOf(previewId);
  previewId = visibleIds[(index + delta + visibleIds.length) % visibleIds.length];
  renderPreview();
}}

function downloadPayloads() {{
  const payloads = selectedItems().map(item => ({{ mediaAsset: item, blotatoPayload: payloadFor(item) }}));
  const blob = new Blob([JSON.stringify(payloads, null, 2)], {{ type:"application/json" }});
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "mokipops-blotato-media-payloads.json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}}

async function downloadFeed() {{
  const channel = document.getElementById("feedChannel").value;
  if (!selected.size) {{
    els.status.textContent = "Select assets first, then download the storefront feed.";
    return;
  }}
  let feed = {{ updated: "", channels: {{ "lifestyle-events": [], "lifestyle-markets": [], "lifestyle-waymo": [], "lifestyle-bts": [], gallery: [] }} }};
  try {{
    const existing = await fetch(new URL("storefront-feed.json", window.location.href), {{ cache: "no-store" }});
    if (existing.ok) feed = await existing.json();
  }} catch (_) {{ /* start fresh if the published feed is unreachable */ }}
  feed.updated = new Date().toISOString();
  feed.channels[channel] = [...selected];
  const blob = new Blob([JSON.stringify(feed, null, 1) + "\\n"], {{ type: "application/json" }});
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "storefront-feed.json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  els.status.textContent = `Storefront feed downloaded - ${{selected.size}} asset(s) in "${{channel}}". Send it to the studio to update the store.`;
}}

document.getElementById("adoptYes").addEventListener("click", adoptLocal);
document.getElementById("adoptNo").addEventListener("click", () => {{
  localStorage.setItem(adoptedKey, "1");
  document.getElementById("adoptBanner").hidden = true;
}});
document.getElementById("whoami").addEventListener("click", async () => {{
  reviewer = "";
  localStorage.removeItem(reviewerKey);
  await ensureReviewer();
}});

fillFolders();
render();
updateSyncStatus();
if (syncOn()) {{
  pullPicks();
  // Reviewers are in different places, so poll to surface each other's picks.
  setInterval(() => {{ if (!document.hidden && !inFlight.size) pullPicks(); }}, 15000);
  window.addEventListener("focus", () => {{ if (!inFlight.size) pullPicks(); }});
}}
for (const el of [els.q, els.mediaType, els.folder, els.sort]) el.addEventListener("input", render);
for (const el of [els.apiKey, els.platform, els.accountId, els.subId, els.postMode]) el.addEventListener("input", saveSettings);
els.platform.addEventListener("change", () => {{ els.accountId.value = ""; els.accounts.innerHTML = ""; saveSettings(); }});
els.selectVisible.addEventListener("click", async () => {{
  if (syncOn() && !(await ensureReviewer())) return;
  const adding = visibleIds.filter(id => !selected.has(id));
  adding.forEach(id => selected.add(id));
  saveSelected();
  render();
  for (const id of adding) await pushPick(id);
  render();
}});
els.clear.addEventListener("click", async () => {{
  const removing = [...selected];
  if (syncOn() && removing.length && !window.confirm(
      "Clear removes all " + removing.length + " picks from the shared list for everyone. Continue?")) return;
  selected.clear();
  saveSelected();
  render();
  for (const id of removing) await dropPick(id);
  render();
}});
els.selectedOnly.addEventListener("click", () => {{
  selectedOnly = !selectedOnly;
  els.selectedOnly.setAttribute("aria-pressed", String(selectedOnly));
  render();
}});
els.lbClose.addEventListener("click", closePreview);
els.lbPrev.addEventListener("click", () => stepPreview(-1));
els.lbNext.addEventListener("click", () => stepPreview(1));
els.lbSelect.addEventListener("click", () => {{
  if (previewId === null) return;
  toggle(previewId, els.grid.querySelector(`[data-id="${{previewId}}"]`));
  updatePreviewSelect();
}});
els.lbOpen.addEventListener("click", () => {{
  const item = byId.get(previewId);
  if (item) window.open(mediaUrlFor(item), "_blank", "noopener");
}});
els.lightbox.addEventListener("click", event => {{
  if (event.target === els.lightbox) closePreview();
}});
document.addEventListener("keydown", event => {{
  if (!els.lightbox.classList.contains("open")) return;
  if (event.key === "Escape") closePreview();
  if (event.key === "ArrowLeft") stepPreview(-1);
  if (event.key === "ArrowRight") stepPreview(1);
}});
els.loadAccounts.addEventListener("click", loadAccounts);
els.createDrafts.addEventListener("click", createDrafts);
els.createDraftsBottom.addEventListener("click", createDrafts);
els.downloadPayloads.addEventListener("click", () => {{
  try {{ downloadPayloads(); }}
  catch (error) {{ els.status.textContent = error.message || String(error); }}
}});
document.getElementById("downloadFeed").addEventListener("click", () => {{
  downloadFeed().catch(error => {{ els.status.textContent = error.message || String(error); }});
}});
updateActions();
</script>
</body>
</html>
"""
    OUT.write_text(page, encoding="utf-8")


def main():
    scan = import_external_photos()
    records = scan_public_media()
    records += scan_external_videos(len(records))
    payload = build_payload(records, scan)
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    write_if_changed(
        DATA_JS,
        "window.MOKIPOPS_LIBRARY = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
    )
    write_if_changed(
        LIBRARY_DIR / "library-data.json",
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
    )
    render_page(payload)
    counts = payload["counts"]
    print(
        f"wrote {OUT.name}, {DATA_JS.relative_to(ROOT)}, "
        f"{counts['total']} assets ({counts['photo']} photos, {counts['video']} videos)"
    )


if __name__ == "__main__":
    main()
