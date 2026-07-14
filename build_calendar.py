#!/usr/bin/env python3
"""Generate the selectable MOKIPOPS media picker page.

The page is intentionally served at calendar.html to keep the existing link,
but it is no longer date-based. It scans public site media, imports optimized
copies of external photos from the MOKIPOPS folder, and lets selected assets
be sent to Blotato as drafts.
"""

import json
import re
import hashlib
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT.parent
OUT = ROOT / "calendar.html"
LIBRARY_DIR = ROOT / "assets" / "library"
IMPORTED_PHOTOS = LIBRARY_DIR / "imported" / "photos"
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
    <p class="lede">Select photos or videos from the scanned asset library and create Blotato drafts from public GitHub Pages media URLs.</p>
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
      </div>
      <div class="status" id="status">Ready.</div>
      <div class="log" id="log" aria-live="polite"></div>
    </div>
  </section>

  <section class="grid" id="grid" aria-label="Media assets"></section>
</main>

<div class="bar">
  <div class="count"><b id="selectedCount">0</b> selected</div>
  <div class="actions">
    <button class="btn" id="selectedOnly" type="button" aria-pressed="false">Selected Only</button>
    <button class="btn primary" id="createDraftsBottom" type="button" disabled>Create Drafts</button>
  </div>
</div>

<script src="assets/library/library-data.js"></script>
<script>
const API_BASE = "https://backend.blotato.com/v2";
const data = window.MOKIPOPS_LIBRARY;
const items = data.items;
const byId = new Map(items.map(item => [item.id, item]));
const selectedKey = "mokipops-media-selected-v1";
const settingsKey = "mokipops-media-settings-v1";
const selected = new Set(JSON.parse(localStorage.getItem(selectedKey) || "[]").filter(id => byId.has(id)));
let selectedOnly = false;
let visibleIds = [];

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
  log: document.getElementById("log")
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
    card.innerHTML = `
      ${{mediaThumb(item)}}
      <span class="check" aria-hidden="true">✓</span>
      <span class="meta">
        <span class="title">${{escapeHtml(item.title)}}</span>
        <span class="folder">${{escapeHtml(item.folder)}}</span>
        <span class="size">${{escapeHtml(item.extension.toUpperCase())}} · ${{item.sizeMb}} MB</span>
      </span>`;
    card.addEventListener("click", () => toggle(item.id, card));
    fragment.appendChild(card);
  }}
  els.grid.appendChild(fragment);
  updateActions();
}}

function toggle(id, card) {{
  if (selected.has(id)) selected.delete(id);
  else selected.add(id);
  saveSelected();
  if (card) card.setAttribute("aria-pressed", selected.has(id) ? "true" : "false");
  updateActions();
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

fillFolders();
render();
for (const el of [els.q, els.mediaType, els.folder, els.sort]) el.addEventListener("input", render);
for (const el of [els.apiKey, els.platform, els.accountId, els.subId, els.postMode]) el.addEventListener("input", saveSettings);
els.platform.addEventListener("change", () => {{ els.accountId.value = ""; els.accounts.innerHTML = ""; saveSettings(); }});
els.selectVisible.addEventListener("click", () => {{
  visibleIds.forEach(id => selected.add(id));
  saveSelected();
  render();
}});
els.clear.addEventListener("click", () => {{
  selected.clear();
  saveSelected();
  render();
}});
els.selectedOnly.addEventListener("click", () => {{
  selectedOnly = !selectedOnly;
  els.selectedOnly.setAttribute("aria-pressed", String(selectedOnly));
  render();
}});
els.loadAccounts.addEventListener("click", loadAccounts);
els.createDrafts.addEventListener("click", createDrafts);
els.createDraftsBottom.addEventListener("click", createDrafts);
els.downloadPayloads.addEventListener("click", () => {{
  try {{ downloadPayloads(); }}
  catch (error) {{ els.status.textContent = error.message || String(error); }}
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
    payload = build_payload(records, scan)
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    write_if_changed(
        DATA_JS,
        "window.MOKIPOPS_LIBRARY = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
    )
    render_page(payload)
    counts = payload["counts"]
    print(
        f"wrote {OUT.name}, {DATA_JS.relative_to(ROOT)}, "
        f"{counts['total']} assets ({counts['photo']} photos, {counts['video']} videos)"
    )


if __name__ == "__main__":
    main()
