#!/usr/bin/env python3
"""Generate the selectable MOKIPOPS content calendar page.

The source calendar is a standalone HTML file with embedded data URI images.
This builder extracts those images into public assets so Blotato can fetch
them from GitHub Pages, then renders an interactive calendar page.
"""
import base64
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "MOKIPOPS-Content-Calendar.html"
ASSET_DIR = ROOT / "assets" / "calendar"
DATA_JS = ASSET_DIR / "calendar-data.js"
INTERSTITIAL_DATA = ASSET_DIR / "interstitial" / "interstitial-data.json"
OUT = ROOT / "calendar.html"
TZ = ZoneInfo("America/New_York")


def text(node, selector):
    found = node.select_one(selector)
    return found.get_text(" ", strip=True) if found else ""


def parse_day(day_label):
    raw = day_label.split("·")[-1].strip()
    return datetime.strptime(raw, "%B %d, %Y").date()


def scheduled_iso(date_value, slot):
    when = datetime.strptime(f"{date_value.isoformat()} {slot}", "%Y-%m-%d %I:%M %p")
    return when.replace(tzinfo=TZ).isoformat()


def format_day_label(value):
    return f"{value.strftime('%a')} · {value.strftime('%B')} {value.day}, {value.year}"


def format_slot(value):
    return value.strftime("%I:%M %p").lstrip("0")


def write_if_changed(path, data):
    if path.exists() and path.read_bytes() == data:
        return
    path.write_bytes(data)


def media_counts(posts):
    photo_count = sum(1 for post in posts if post.get("mediaType") == "photo")
    video_count = sum(1 for post in posts if post.get("mediaType") == "video")
    return {"photo": photo_count, "video": video_count}


def add_interstitial_posts(posts):
    if not INTERSTITIAL_DATA.exists():
        return posts

    items = json.loads(INTERSTITIAL_DATA.read_text(encoding="utf-8")).get("items", [])
    if not items:
        return posts

    interval = max(1, len(posts) // (len(items) + 1))
    inserts = {}
    for index, item in enumerate(items, start=1):
        anchor_index = min(len(posts) - 1, index * interval - 1)
        anchor = posts[anchor_index]
        anchor_time = datetime.fromisoformat(anchor["scheduledTime"])
        scheduled_time = anchor_time + timedelta(minutes=45)
        media_type = item.get("mediaType", "photo")
        thumbnail = item.get("thumbnail") or item.get("mediaUrl")
        label_icon = "🎥" if media_type == "video" else "📷"
        post = {
            "id": item.get("id", f"interstitial-{index:03d}"),
            "number": 0,
            "weekLabel": anchor["weekLabel"],
            "theme": anchor["theme"],
            "themeDescription": anchor["themeDescription"],
            "themeColor": "#EE6C2B" if media_type == "video" else "#F5A623",
            "dayLabel": format_day_label(scheduled_time.date()),
            "date": scheduled_time.date().isoformat(),
            "slot": format_slot(scheduled_time),
            "scheduledTime": scheduled_time.isoformat(),
            "caption": item.get("caption") or item.get("title", "MOKIPOPS interstitial"),
            "cta": item.get("cta", "Add this between scheduled posts."),
            "tags": item.get("tags", "#mokipops #blissonastick"),
            "text": "\n\n".join(part for part in [
                item.get("caption") or item.get("title", "MOKIPOPS interstitial"),
                item.get("cta", "Add this between scheduled posts."),
                item.get("tags", "#mokipops #blissonastick"),
            ] if part),
            "file": f"{label_icon} {item.get('sourceFile', item.get('mediaUrl', 'media asset'))} · {item.get('suggestedSlot', 'between scheduled posts')}",
            "image": thumbnail,
            "thumbnail": thumbnail,
            "mediaUrl": item.get("mediaUrl", thumbnail),
            "mediaType": media_type,
            "assetTitle": item.get("title", ""),
            "source": "interstitial",
        }
        inserts.setdefault(anchor_index, []).append(post)

    merged = []
    for index, post in enumerate(posts):
        merged.append(post)
        merged.extend(inserts.get(index, []))

    for number, post in enumerate(merged, start=1):
        post["number"] = number
    return merged


def extract_posts():
    soup = BeautifulSoup(SOURCE.read_text(encoding="utf-8"), "html.parser")
    main = next(
        div for div in soup.find_all("div", class_="wrap")
        if div.find("div", class_="weekhdr")
    )

    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    weeks = []
    posts = []
    current_week = None
    current_day = ""
    current_date = None

    for child in main.find_all(recursive=False):
        classes = child.get("class", [])

        if "weekhdr" in classes:
            style = child.get("style", "")
            color_match = re.search(r"#[0-9a-fA-F]{6}", style)
            current_week = {
                "label": text(child, ".wk"),
                "theme": text(child, "h2"),
                "description": text(child, "p"),
                "color": color_match.group(0) if color_match else "#E23A23",
            }
            weeks.append(current_week)
            continue

        if "day" in classes:
            current_day = child.get_text(" ", strip=True)
            current_date = parse_day(current_day)
            continue

        if "posts" not in classes:
            continue

        for card in child.find_all("div", class_="post", recursive=False):
            idx = len(posts) + 1
            img = card.find("img")
            src = img.get("src", "") if img else ""
            match = re.match(r"data:(image/[^;]+);base64,(.*)", src, re.DOTALL)
            if not match:
                raise ValueError(f"Post {idx} is missing an embedded image")

            mime, payload = match.groups()
            ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(mime, "jpg")
            image_name = f"post-{idx:03d}.{ext}"
            image_path = ASSET_DIR / image_name
            image_bytes = base64.b64decode(payload)
            write_if_changed(image_path, image_bytes)

            caption = text(card, ".cap")
            cta = text(card, ".cta")
            tags = text(card, ".tags")
            slot = text(card, ".slot")
            full_text = "\n\n".join(part for part in [caption, cta, tags] if part)

            posts.append({
                "id": f"cal-{idx:03d}",
                "number": idx,
                "weekLabel": current_week["label"] if current_week else "",
                "theme": current_week["theme"] if current_week else "",
                "themeDescription": current_week["description"] if current_week else "",
                "themeColor": current_week["color"] if current_week else "#E23A23",
                "dayLabel": current_day,
                "date": current_date.isoformat(),
                "slot": slot,
                "scheduledTime": scheduled_iso(current_date, slot),
                "caption": caption,
                "cta": cta,
                "tags": tags,
                "text": full_text,
                "file": text(card, ".fn"),
                "image": f"assets/calendar/{image_name}",
                "thumbnail": f"assets/calendar/{image_name}",
                "mediaUrl": f"assets/calendar/{image_name}",
                "mediaType": "photo",
                "source": "calendar",
            })

    posts = add_interstitial_posts(posts)
    payload = {
        "source": SOURCE.name,
        "count": len(posts),
        "timezone": "America/New_York",
        "mediaCounts": media_counts(posts),
        "weeks": weeks,
        "posts": posts,
    }
    DATA_JS.write_text(
        "window.MOKIPOPS_CALENDAR = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    return payload


def render_page(count):
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>MOKIPOPS - Content Calendar</title>
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
body {{ font-family:'Archivo',-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif; background:var(--bg); color:var(--ink); line-height:1.48; -webkit-font-smoothing:antialiased; padding-bottom:94px; }}
h1,h2,h3 {{ font-family:'Fraunces',Georgia,serif; }}
button,input,select,textarea {{ font:inherit; }}
.top {{ position:sticky; top:0; z-index:40; display:flex; align-items:center; justify-content:space-between; gap:18px; padding:13px clamp(16px,4vw,40px); backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px); background:color-mix(in srgb,var(--bg) 84%,transparent); border-bottom:1px solid var(--line); }}
.wordmark {{ font-family:'Fraunces',Georgia,serif; font-weight:900; font-size:17px; letter-spacing:0; white-space:nowrap; }}
.wordmark em {{ font-style:normal; color:var(--mango); }}
.nav {{ display:flex; flex-wrap:wrap; align-items:center; justify-content:flex-end; gap:14px; }}
.nav a {{ color:var(--chili); text-decoration:none; font-size:13px; font-weight:850; }}
.wrap {{ max-width:1180px; margin:0 auto; padding:0 clamp(16px,4vw,40px); }}
.hero {{ padding:clamp(34px,6vw,64px) 0 22px; text-align:center; }}
.eyebrow {{ display:inline-block; color:var(--chili); background:rgba(245,166,35,.16); border:1px solid rgba(245,166,35,.36); border-radius:999px; padding:7px 15px; font-size:12px; font-weight:850; letter-spacing:.09em; text-transform:uppercase; margin-bottom:18px; }}
h1 {{ font-size:clamp(34px,7vw,62px); line-height:1.02; letter-spacing:0; font-weight:900; }}
.soft {{ background:linear-gradient(92deg,var(--mango),var(--orange) 48%,var(--chili)); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }}
.lede {{ max-width:680px; margin:18px auto 0; color:var(--sub); font-size:clamp(15px,2.2vw,18px); }}
.stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; max-width:760px; margin:24px auto 0; }}
.stat {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:11px 13px; text-align:left; box-shadow:var(--shadow); }}
.stat span {{ display:block; font-size:11px; color:var(--sub); font-weight:850; text-transform:uppercase; letter-spacing:.07em; }}
.stat b {{ display:block; font-size:17px; margin-top:2px; }}
.tools {{ display:grid; grid-template-columns:1fr; gap:14px; margin:20px 0 24px; }}
.panel {{ background:var(--card); border:1px solid var(--line); border-radius:16px; padding:16px; box-shadow:var(--shadow); }}
.filters {{ display:grid; grid-template-columns:minmax(180px,1fr) 180px 150px 150px auto auto; gap:10px; align-items:end; }}
.field label {{ display:block; color:var(--sub); font-size:11px; font-weight:850; letter-spacing:.07em; text-transform:uppercase; margin:0 0 6px 2px; }}
.field input,.field select,.field textarea {{ width:100%; border:1.5px solid var(--line); background:var(--bg); color:var(--ink); border-radius:12px; padding:10px 12px; min-height:42px; }}
.field textarea {{ min-height:66px; resize:vertical; }}
.draft-grid {{ display:grid; grid-template-columns:1.2fr .8fr .8fr .8fr .8fr; gap:10px; align-items:end; }}
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
.calendar {{ display:grid; gap:12px; }}
.weekhead {{ margin-top:22px; padding:14px 16px; border-radius:14px; color:#fff; box-shadow:var(--shadow); }}
.weekhead .wk {{ font-size:11px; font-weight:900; letter-spacing:.13em; text-transform:uppercase; opacity:.92; }}
.weekhead h2 {{ font-size:22px; letter-spacing:0; margin-top:2px; }}
.weekhead p {{ margin-top:3px; font-size:12.5px; opacity:.94; max-width:800px; }}
.dayhead {{ margin-top:12px; color:var(--chili); font-weight:900; font-size:14px; border-bottom:2px solid var(--line); padding-bottom:6px; }}
.postgrid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }}
.post {{ position:relative; display:grid; grid-template-columns:104px 1fr; gap:12px; width:100%; text-align:left; border:1px solid var(--line); background:var(--card); color:var(--ink); border-radius:14px; padding:10px; cursor:pointer; box-shadow:var(--shadow); }}
.post[aria-pressed="true"] {{ border-color:var(--mango); outline:2px solid rgba(245,166,35,.24); }}
.thumb {{ position:relative; width:104px; height:132px; border-radius:10px; overflow:hidden; background:var(--panel); }}
.thumb img {{ width:100%; height:100%; object-fit:cover; display:block; }}
.media-badge {{ position:absolute; left:7px; top:7px; z-index:2; display:inline-flex; align-items:center; gap:4px; color:#fff; border-radius:999px; padding:4px 7px; font-size:9px; line-height:1; font-weight:900; letter-spacing:.06em; background:rgba(42,26,18,.82); }}
.post[data-media="video"] .media-badge {{ background:linear-gradient(90deg,var(--orange),var(--chili)); }}
.play {{ position:absolute; inset:0; display:grid; place-items:center; color:#fff; font-size:28px; text-shadow:0 2px 14px rgba(0,0,0,.6); background:radial-gradient(circle,rgba(0,0,0,.18),rgba(0,0,0,0) 45%); }}
.check {{ position:absolute; top:16px; right:16px; width:28px; height:28px; border-radius:50%; display:grid; place-items:center; font-weight:900; color:transparent; background:rgba(255,255,255,.88); border:1px solid var(--line); }}
.post[aria-pressed="true"] .check {{ color:#fff; border-color:transparent; background:linear-gradient(135deg,var(--mango),var(--chili)); }}
.body {{ min-width:0; padding-right:26px; }}
.slot {{ display:inline-block; color:#fff; background:var(--ink); border-radius:999px; padding:3px 9px; font-size:11px; font-weight:900; }}
.cap {{ margin-top:8px; font-size:13.5px; font-weight:720; }}
.cta {{ margin-top:5px; color:var(--sub); font-size:12px; font-weight:760; }}
.tags {{ margin-top:6px; color:#a57942; font-size:11px; overflow-wrap:anywhere; }}
.fn {{ margin-top:7px; color:color-mix(in srgb,var(--sub) 70%,transparent); font-size:10px; overflow-wrap:anywhere; }}
.empty {{ text-align:center; color:var(--sub); padding:32px; border:1px dashed var(--line); border-radius:16px; }}
.bar {{ position:fixed; left:0; right:0; bottom:0; z-index:50; display:flex; align-items:center; justify-content:space-between; gap:12px; padding:12px clamp(16px,4vw,40px) calc(12px + env(safe-area-inset-bottom)); background:color-mix(in srgb,var(--bg) 88%,transparent); backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px); border-top:1px solid var(--line); }}
.count {{ font-weight:900; }}
.count b {{ color:var(--chili); font-variant-numeric:tabular-nums; }}
@media (max-width:940px) {{
  .stats {{ grid-template-columns:repeat(2,1fr); }}
  .filters,.draft-grid {{ grid-template-columns:1fr 1fr; }}
  .postgrid {{ grid-template-columns:1fr; }}
}}
@media (max-width:620px) {{
  .top {{ align-items:flex-start; flex-direction:column; gap:8px; }}
  .nav {{ justify-content:flex-start; }}
  .stats,.filters,.draft-grid {{ grid-template-columns:1fr; }}
  .post {{ grid-template-columns:92px 1fr; }}
  .thumb {{ width:92px; height:118px; }}
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
    <span class="eyebrow">Content Calendar</span>
    <h1>{count} posts, ready for <span class="soft">Blotato.</span></h1>
    <p class="lede">Select photo or video posts, connect a Blotato account, and create scheduled drafts from the live GitHub Pages media URLs.</p>
    <div class="stats" aria-label="Calendar stats">
      <div class="stat"><span>Total posts</span><b id="statPosts">{count}</b></div>
      <div class="stat"><span>Photos</span><b id="statPhotos">0</b></div>
      <div class="stat"><span>Videos</span><b id="statVideos">0</b></div>
      <div class="stat"><span>Timezone</span><b>ET</b></div>
    </div>
  </header>

  <section class="tools" aria-label="Calendar controls">
    <div class="panel">
      <div class="filters">
        <div class="field"><label for="q">Search</label><input id="q" type="search" placeholder="Caption, tag, filename"></div>
        <div class="field"><label for="theme">Theme</label><select id="theme"></select></div>
        <div class="field"><label for="mediaType">Media</label><select id="mediaType"><option value="">Photos + videos</option><option value="photo">Photos only</option><option value="video">Videos only</option></select></div>
        <div class="field"><label for="month">Month</label><select id="month"></select></div>
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
        <div class="field"><label for="scheduleMode">Schedule</label><select id="scheduleMode"><option value="calendar">Calendar dates</option><option value="next">Next free slots</option></select></div>
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

  <section class="calendar" id="calendar" aria-label="Calendar posts"></section>
</main>

<div class="bar">
  <div class="count"><b id="selectedCount">0</b> selected</div>
  <div class="actions">
    <button class="btn" id="selectedOnly" type="button" aria-pressed="false">Selected Only</button>
    <button class="btn primary" id="createDraftsBottom" type="button" disabled>Create Drafts</button>
  </div>
</div>

<script src="assets/calendar/calendar-data.js"></script>
<script>
const API_BASE = "https://backend.blotato.com/v2";
const data = window.MOKIPOPS_CALENDAR;
const posts = data.posts;
const byId = new Map(posts.map(post => [post.id, post]));
const selectedKey = "mokipops-calendar-selected-v1";
const settingsKey = "mokipops-calendar-settings-v1";
const selected = new Set(JSON.parse(localStorage.getItem(selectedKey) || "[]").filter(id => byId.has(id)));
let selectedOnly = false;
let visibleIds = [];

const els = {{
  q: document.getElementById("q"),
  theme: document.getElementById("theme"),
  mediaType: document.getElementById("mediaType"),
  month: document.getElementById("month"),
  calendar: document.getElementById("calendar"),
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
  scheduleMode: document.getElementById("scheduleMode"),
  loadAccounts: document.getElementById("loadAccounts"),
  createDrafts: document.getElementById("createDrafts"),
  createDraftsBottom: document.getElementById("createDraftsBottom"),
  downloadPayloads: document.getElementById("downloadPayloads"),
  status: document.getElementById("status"),
  log: document.getElementById("log")
}};

els.statPosts = document.getElementById("statPosts");
els.statPhotos = document.getElementById("statPhotos");
els.statVideos = document.getElementById("statVideos");

const settings = JSON.parse(localStorage.getItem(settingsKey) || "{{}}");
for (const key of ["apiKey", "platform", "accountId", "subId", "scheduleMode"]) {{
  if (settings[key]) els[key].value = settings[key];
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
    scheduleMode: els.scheduleMode.value
  }};
  localStorage.setItem(settingsKey, JSON.stringify(next));
  updateActions();
}}

function escapeHtml(value) {{
  return String(value || "").replace(/[&<>"']/g, char => ({{"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}}[char]));
}}

function unique(values) {{
  return [...new Set(values.filter(Boolean))];
}}

function fillFilters() {{
  const themes = unique(posts.map(post => post.theme));
  els.theme.innerHTML = '<option value="">All themes</option>' + themes.map(value => `<option>${{escapeHtml(value)}}</option>`).join("");

  const monthNames = new Intl.DateTimeFormat("en", {{ month:"long", year:"numeric", timeZone:"UTC" }});
  const months = unique(posts.map(post => post.date.slice(0, 7)));
  els.month.innerHTML = '<option value="">All months</option>' + months.map(value => {{
    const label = monthNames.format(new Date(value + "-01T00:00:00Z"));
    return `<option value="${{value}}">${{escapeHtml(label)}}</option>`;
  }}).join("");
}}

function updateStats() {{
  const counts = data.mediaCounts || {{}};
  els.statPosts.textContent = posts.length;
  els.statPhotos.textContent = counts.photo ?? posts.filter(post => post.mediaType !== "video").length;
  els.statVideos.textContent = counts.video ?? posts.filter(post => post.mediaType === "video").length;
}}

function matches(post) {{
  if (selectedOnly && !selected.has(post.id)) return false;
  if (els.theme.value && post.theme !== els.theme.value) return false;
  if (els.mediaType.value && (post.mediaType || "photo") !== els.mediaType.value) return false;
  if (els.month.value && !post.date.startsWith(els.month.value)) return false;
  const query = els.q.value.trim().toLowerCase();
  if (!query) return true;
  return [post.caption, post.cta, post.tags, post.file, post.theme, post.dayLabel, post.mediaType, post.assetTitle].join(" ").toLowerCase().includes(query);
}}

function mediaUrlFor(post) {{
  return post.mediaUrl || post.image;
}}

function render() {{
  const filtered = posts.filter(matches);
  visibleIds = filtered.map(post => post.id);
  els.calendar.innerHTML = "";

  if (!filtered.length) {{
    els.calendar.innerHTML = '<div class="empty">No posts match the current filters.</div>';
    updateActions();
    return;
  }}

  let lastWeek = "";
  let lastDay = "";
  let grid = null;
  for (const post of filtered) {{
    if (post.weekLabel !== lastWeek) {{
      lastWeek = post.weekLabel;
      const week = document.createElement("div");
      week.className = "weekhead";
      week.style.background = `linear-gradient(120deg, ${{post.themeColor}}, ${{post.themeColor}}cc)`;
      week.innerHTML = `<div class="wk">${{escapeHtml(post.weekLabel)}}</div><h2>${{escapeHtml(post.theme)}}</h2><p>${{escapeHtml(post.themeDescription)}}</p>`;
      els.calendar.appendChild(week);
      lastDay = "";
    }}
    if (post.dayLabel !== lastDay) {{
      lastDay = post.dayLabel;
      const day = document.createElement("div");
      day.className = "dayhead";
      day.textContent = post.dayLabel;
      els.calendar.appendChild(day);
      grid = document.createElement("div");
      grid.className = "postgrid";
      els.calendar.appendChild(grid);
    }}
    const card = document.createElement("button");
    card.type = "button";
    card.className = "post";
    card.dataset.id = post.id;
    card.dataset.media = post.mediaType || "photo";
    card.setAttribute("aria-pressed", selected.has(post.id) ? "true" : "false");
    const mediaType = post.mediaType || "photo";
    const mediaLabel = mediaType === "video" ? "VIDEO" : "PHOTO";
    const mediaIcon = mediaType === "video" ? "▶" : "●";
    card.innerHTML = `
      <span class="thumb">
        <img src="${{escapeHtml(post.thumbnail || post.image)}}" alt="" loading="lazy">
        <span class="media-badge">${{mediaIcon}} ${{mediaLabel}}</span>
        ${{mediaType === "video" ? '<span class="play" aria-hidden="true">▶</span>' : ''}}
      </span>
      <span class="check" aria-hidden="true">✓</span>
      <span class="body">
        <span class="slot">${{escapeHtml(post.slot)}} · ${{mediaLabel}}</span>
        <span class="cap">${{escapeHtml(post.caption)}}</span>
        <span class="cta">${{escapeHtml(post.cta)}}</span>
        <span class="tags">${{escapeHtml(post.tags)}}</span>
        <span class="fn">${{escapeHtml(post.file)}}</span>
      </span>`;
    card.addEventListener("click", () => toggle(post.id, card));
    grid.appendChild(card);
  }}
  updateActions();
}}

function toggle(id, card) {{
  if (selected.has(id)) selected.delete(id);
  else selected.add(id);
  saveSelected();
  if (card) card.setAttribute("aria-pressed", selected.has(id) ? "true" : "false");
  updateActions();
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

function selectedPosts() {{
  return posts.filter(post => selected.has(post.id));
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

function payloadFor(post) {{
  const platform = els.platform.value;
  const payload = {{
    post: {{
      accountId: els.accountId.value.trim(),
      content: {{
        text: post.text,
        mediaUrls: [new URL(mediaUrlFor(post), window.location.href).href],
        platform
      }},
      target: targetFor(platform)
    }}
  }};

  const scheduledTime = Date.parse(post.scheduledTime);
  if (els.scheduleMode.value === "calendar" && scheduledTime > Date.now() + 10 * 60 * 1000) {{
    payload.scheduledTime = post.scheduledTime;
  }} else {{
    payload.useNextFreeSlot = true;
  }}
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
    const items = result.items || [];
    els.accounts.innerHTML = items.map(item => `<option value="${{escapeHtml(item.id)}}">${{escapeHtml([item.fullname, item.username, item.platform].filter(Boolean).join(" - "))}}</option>`).join("");
    if (items.length && !els.accountId.value.trim()) {{
      els.accountId.value = items[0].id;
      saveSettings();
    }}
    els.status.textContent = `${{items.length}} account${{items.length === 1 ? "" : "s"}} loaded.`;
  }} catch (error) {{
    els.status.textContent = "Could not load accounts.";
    logLine(error.message || String(error), "bad");
  }} finally {{
    setBusy(false);
  }}
}}

async function createDrafts() {{
  const chosen = selectedPosts();
  if (!chosen.length) return;
  saveSettings();
  els.log.innerHTML = "";
  setBusy(true);
  let ok = 0;
  let failed = 0;
  els.status.textContent = `Creating ${{chosen.length}} Blotato draft${{chosen.length === 1 ? "" : "s"}}...`;
  for (const [index, post] of chosen.entries()) {{
    try {{
      const result = await blotato("/posts", {{
        method: "POST",
        body: JSON.stringify(payloadFor(post))
      }});
      ok += 1;
      logLine(`#${{post.number}} ${{post.slot}} - draft queued${{result.postSubmissionId ? " (" + result.postSubmissionId + ")" : ""}}`, "ok");
    }} catch (error) {{
      failed += 1;
      logLine(`#${{post.number}} failed - ${{error.message || error}}`, "bad");
      if (/401|403/.test(String(error.message))) break;
    }}
    if (index < chosen.length - 1) await sleep(2200);
  }}
  els.status.textContent = `${{ok}} draft${{ok === 1 ? "" : "s"}} created${{failed ? ", " + failed + " failed" : ""}}.`;
  setBusy(false);
}}

function downloadPayloads() {{
  const payloads = selectedPosts().map(post => ({{ calendarPost: post, blotatoPayload: payloadFor(post) }}));
  const blob = new Blob([JSON.stringify(payloads, null, 2)], {{ type:"application/json" }});
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "mokipops-blotato-draft-payloads.json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}}

fillFilters();
updateStats();
render();
for (const el of [els.q, els.theme, els.mediaType, els.month]) el.addEventListener("input", render);
for (const el of [els.apiKey, els.platform, els.accountId, els.subId, els.scheduleMode]) el.addEventListener("input", saveSettings);
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
    payload = extract_posts()
    render_page(payload["count"])
    counts = payload.get("mediaCounts", {})
    print(
        f"wrote {OUT.name}, {DATA_JS.relative_to(ROOT)}, "
        f"{payload['count']} posts ({counts.get('photo', 0)} photos, {counts.get('video', 0)} videos)"
    )


if __name__ == "__main__":
    main()
