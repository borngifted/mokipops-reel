#!/usr/bin/env python3
"""Generate picks.html — the client-facing content picker.

A static, self-contained page: the client taps the images they want, then hits
"Email my picks", which opens a pre-filled email to the studio listing every
selection (grouped by section, with the full-res source path). No backend.

Run:  python3 build_picks.py   then commit + push (GitHub Pages serves it).
"""
import html
import json

STUDIO_EMAIL = "digi2uai@gmail.com"

# --- Section definitions ------------------------------------------------------
# label: shown to client · thumb: assets/picks/<file> · source: where the
# full-res original lives (so the studio can grab it for Blotato).

LIFESTYLE = [
    ("01-producthero",  "Product Hero"),
    ("02-pop-outdoors", "Pops Outdoors"),
    ("03-pop-display",  "Pop Display"),
    ("04-smiling-girl", "Smiling Girl"),
    ("05-blackgirlmagic", "Black Girl Magic"),
    ("06-man-two-pops", "Man · Two Pops"),
    ("07-two-women",    "Two Women"),
    ("08-event-tent",   "Event Tent"),
    ("09-brand-sign",   "Brand Sign"),
    ("10-pop-cart",     "Pop Cart"),
]

BRAND = [
    ("instagram-portrait", "Instagram Portrait"),
    ("instagram-square",   "Instagram Square"),
    ("landscape-link",     "Landscape / Link"),
    ("pinterest-pin",      "Pinterest Pin"),
    ("profile-avatar",     "Profile Avatar"),
    ("story-reel",         "Story / Reel"),
    ("youtube-thumbnail",  "YouTube Thumbnail"),
]

PRODUCT = [
    ("basil-lemonade",       "Basil Lemonade"),
    ("blackberry-lemonade",  "Blackberry Lemonade"),
    ("blueberriest-eye",     "Blueberriest Eye"),
    ("cherry-lime",          "Cherry Lime"),
    ("creamy-chocolate",     "Creamy Chocolate"),
    ("lemon-lime",           "Lemon Lime"),
    ("mango-cream",          "Mango Cream"),
    ("mango-ginger",         "Mango Ginger"),
    ("rosy-raspberry",       "Rosy Raspberry"),
    ("watermelon-splasher",  "Watermelon Splasher"),
]


def build_items():
    items = []
    for key, label in LIFESTYLE:
        items.append({
            "id": f"life-{key}", "label": label, "section": "Lifestyle Photos",
            "thumb": f"assets/picks/life-{key}.jpg",
            "source": f"social-graphics-photos/mokipops-{key}-* (square / landscape / story)",
        })
    for key, label in BRAND:
        items.append({
            "id": f"brand-{key}", "label": label, "section": "Brand Graphics",
            "thumb": f"assets/picks/brand-{key}.jpg",
            "source": f"social-graphics/mokipops-{key}.jpg",
        })
    for key, label in PRODUCT:
        items.append({
            "id": f"prod-{key}", "label": label, "section": "Product Shots",
            "thumb": f"assets/picks/prod-{key}.jpg",
            "source": f"assets/products/{key}-clean.jpg",
        })
    return items


def render_section(title, eyebrow, items):
    cards = []
    for it in items:
        cards.append(f'''
        <button class="pcard" data-id="{html.escape(it["id"])}" type="button" aria-pressed="false">
          <span class="pthumb"><img src="{it["thumb"]}" alt="{html.escape(it["label"])}" loading="lazy"></span>
          <span class="check" aria-hidden="true">✓</span>
          <span class="plabel">{html.escape(it["label"])}</span>
        </button>''')
    return f'''
    <section class="psec">
      <div class="sechead">
        <div class="dropeyebrow">{html.escape(eyebrow)}</div>
        <h2>{html.escape(title)}</h2>
      </div>
      <div class="pgrid">{"".join(cards)}</div>
    </section>'''


def main():
    items = build_items()
    data_json = json.dumps({it["id"]: {"label": it["label"], "section": it["section"], "source": it["source"]} for it in items})

    lifestyle = [i for i in items if i["section"] == "Lifestyle Photos"]
    brand = [i for i in items if i["section"] == "Brand Graphics"]
    product = [i for i in items if i["section"] == "Product Shots"]

    page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MOKIPOPS — Content Picker</title>
<meta name="robots" content="noindex">
<style>
@font-face {{ font-family:'Fraunces'; src:url(assets/fraunces.woff2) format('woff2'); font-weight:100 900; font-display:swap; }}
@font-face {{ font-family:'Archivo'; src:url(assets/archivo.woff2) format('woff2'); font-weight:100 900; font-display:swap; }}
:root {{ --bg:#FFF6E9; --panel:#FBEAD0; --ink:#2A1A12; --sub:#5A463B; --hairline:rgba(42,26,18,.12);
  --card:#ffffff; --mango:#F5A623; --orange:#EE6C2B; --chili:#E23A23; --r:20px; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#211714; --panel:#2A1A12; --ink:#FFF6E9; --sub:#cdbba8; --hairline:rgba(255,246,233,.14); --card:#33211a; }}
}}
* {{ box-sizing:border-box; margin:0; padding:0; -webkit-tap-highlight-color:transparent; }}
body {{ font-family:'Archivo',-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif;
  background:var(--bg); color:var(--ink); line-height:1.55; -webkit-font-smoothing:antialiased;
  padding-bottom:96px; }}
h1,h2,h3 {{ font-family:'Fraunces',Georgia,serif; }}
a {{ color:var(--chili); }}
.top {{ position:sticky; top:0; z-index:20; display:flex; align-items:center; justify-content:space-between;
  padding:13px clamp(16px,4vw,40px); backdrop-filter:blur(10px);
  background:color-mix(in srgb, var(--bg) 80%, transparent); border-bottom:1px solid var(--hairline); }}
.wordmark {{ font-family:'Fraunces',Georgia,serif; font-weight:900; font-size:17px; letter-spacing:-.01em; }}
.wordmark em {{ font-style:normal; color:var(--mango); }}
.top a {{ font-size:13px; font-weight:800; color:var(--chili); text-decoration:none; }}
.wrap {{ max-width:1120px; margin:0 auto; padding:0 clamp(16px,4vw,40px); }}
.hero {{ text-align:center; padding:clamp(34px,6vw,64px) 0 12px; }}
.eyebrow {{ display:inline-block; font-size:12.5px; font-weight:800; color:var(--chili); letter-spacing:.09em;
  text-transform:uppercase; background:rgba(245,166,35,.16); border:1px solid rgba(245,166,35,.35);
  border-radius:100px; padding:7px 16px; margin-bottom:20px; }}
.hero h1 {{ font-size:clamp(34px,7vw,60px); line-height:1.02; letter-spacing:-.02em; }}
.hero h1 .soft {{ background:linear-gradient(92deg,var(--mango),var(--orange) 45%,var(--chili));
  -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }}
.lede {{ font-size:clamp(15px,2.3vw,18px); color:var(--sub); max-width:620px; margin:18px auto 0; }}
.meta {{ max-width:620px; margin:26px auto 4px; display:grid; gap:12px; }}
.meta label {{ display:block; font-size:12.5px; font-weight:800; color:var(--sub);
  text-transform:uppercase; letter-spacing:.05em; margin-bottom:6px; text-align:left; }}
.meta input, .meta textarea {{ width:100%; font-family:inherit; font-size:15px; color:var(--ink);
  background:var(--card); border:1.5px solid var(--hairline); border-radius:14px; padding:12px 14px; }}
.meta textarea {{ min-height:64px; resize:vertical; }}
.psec {{ margin-top:clamp(30px,5vw,52px); }}
.sechead {{ text-align:center; margin-bottom:20px; }}
.dropeyebrow {{ font-size:12.5px; font-weight:800; color:var(--chili); letter-spacing:.09em;
  text-transform:uppercase; }}
.sechead h2 {{ font-size:clamp(22px,4vw,32px); letter-spacing:-.01em; margin-top:6px; }}
.pgrid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:14px; }}
.pcard {{ position:relative; display:block; text-align:left; cursor:pointer; padding:0; border:none;
  background:transparent; font-family:inherit; }}
.pthumb {{ display:block; aspect-ratio:4/5; border-radius:16px; overflow:hidden; background:var(--panel);
  border:2.5px solid transparent; transition:border-color .15s ease, transform .12s ease; }}
.pthumb img {{ width:100%; height:100%; object-fit:cover; display:block; }}
.plabel {{ display:block; font-size:13px; font-weight:700; color:var(--ink); margin:9px 4px 2px;
  letter-spacing:-.01em; }}
.check {{ position:absolute; top:10px; right:10px; width:28px; height:28px; border-radius:50%;
  background:rgba(255,255,255,.85); border:1.5px solid var(--hairline); color:transparent;
  display:grid; place-items:center; font-size:15px; font-weight:900; transition:all .15s ease; }}
.pcard[aria-pressed="true"] .pthumb {{ border-color:var(--mango); transform:translateY(-2px); }}
.pcard[aria-pressed="true"] .check {{ background:linear-gradient(135deg,var(--mango),var(--chili));
  border-color:transparent; color:#fff; }}
.pcard:focus-visible .pthumb {{ outline:3px solid var(--orange); outline-offset:2px; }}
.bar {{ position:fixed; left:0; right:0; bottom:0; z-index:30; display:flex; align-items:center; gap:14px;
  justify-content:space-between; padding:12px clamp(16px,4vw,40px);
  background:color-mix(in srgb, var(--bg) 88%, transparent); backdrop-filter:blur(12px);
  border-top:1px solid var(--hairline); }}
.count {{ font-size:15px; font-weight:800; }}
.count b {{ color:var(--chili); font-variant-numeric:tabular-nums; }}
.actions {{ display:flex; gap:10px; }}
.btn {{ font-family:inherit; font-size:14px; font-weight:800; border-radius:100px; padding:11px 20px;
  cursor:pointer; border:1.5px solid var(--hairline); background:var(--card); color:var(--ink); }}
.btn.primary {{ border-color:transparent; color:#fff; background:linear-gradient(90deg,var(--mango),var(--chili)); }}
.btn:disabled {{ opacity:.45; cursor:not-allowed; }}
footer {{ margin-top:56px; background:var(--ink); color:#FBEAD0; text-align:center; padding:34px 20px; }}
footer .fline {{ font-size:14px; color:#e6d6c4; }}
footer .fline b {{ color:#fff; font-family:'Fraunces',Georgia,serif; }}
footer .fsmall {{ margin-top:14px; font-size:12px; color:#cdbba8; opacity:.85; }}
</style>
</head>
<body>
<div class="top">
  <div class="wordmark">MOKI<em>POPS</em></div>
  <a href="index.html">← Back to the reel</a>
</div>

<div class="wrap">
  <div class="hero">
    <span class="eyebrow">Content Picker</span>
    <h1>Pick your <span class="soft">posts.</span></h1>
    <p class="lede">Tap every image you'd like us to schedule. When you're done, hit
      <b>Email my picks</b> at the bottom — it opens a ready-to-send email back to us,
      and we'll load them into the calendar.</p>
    <div class="meta">
      <div>
        <label for="who">Your name</label>
        <input id="who" type="text" placeholder="So we know who sent these" autocomplete="name">
      </div>
      <div>
        <label for="notes">Notes (optional)</label>
        <textarea id="notes" placeholder="Any captions, dates, or priorities you have in mind"></textarea>
      </div>
    </div>
  </div>

  {render_section("Lifestyle Photos", "Real people · real pops", lifestyle)}
  {render_section("Brand Graphics", "Templated · ready to post", brand)}
  {render_section("Product Shots", "Every flavor", product)}
</div>

<footer>
  <div class="fline"><b>Bliss on a Stick</b> · mokipops.com · @mokipops</div>
  <div class="fsmall">Crafted by Work Official LLC</div>
</footer>

<div class="bar">
  <div class="count"><b id="n">0</b> selected</div>
  <div class="actions">
    <button class="btn" id="clear" type="button">Clear</button>
    <button class="btn primary" id="email" type="button" disabled>Email my picks</button>
  </div>
</div>

<script>
const DATA = {data_json};
const STUDIO = {json.dumps(STUDIO_EMAIL)};
const KEY = 'mokipops-picks-v1';
const sel = new Set(JSON.parse(localStorage.getItem(KEY) || '[]'));
const who = document.getElementById('who');
const notes = document.getElementById('notes');
who.value = localStorage.getItem(KEY + '-who') || '';
notes.value = localStorage.getItem(KEY + '-notes') || '';

function save() {{
  localStorage.setItem(KEY, JSON.stringify([...sel]));
  localStorage.setItem(KEY + '-who', who.value);
  localStorage.setItem(KEY + '-notes', notes.value);
}}
function refresh() {{
  document.getElementById('n').textContent = sel.size;
  document.getElementById('email').disabled = sel.size === 0;
}}
document.querySelectorAll('.pcard').forEach(card => {{
  const id = card.dataset.id;
  if (sel.has(id)) card.setAttribute('aria-pressed', 'true');
  card.addEventListener('click', () => {{
    if (sel.has(id)) {{ sel.delete(id); card.setAttribute('aria-pressed','false'); }}
    else {{ sel.add(id); card.setAttribute('aria-pressed','true'); }}
    save(); refresh();
  }});
}});
who.addEventListener('input', save);
notes.addEventListener('input', save);

document.getElementById('clear').addEventListener('click', () => {{
  sel.clear();
  document.querySelectorAll('.pcard').forEach(c => c.setAttribute('aria-pressed','false'));
  save(); refresh();
}});

document.getElementById('email').addEventListener('click', () => {{
  const groups = {{}};
  [...sel].forEach(id => {{
    const it = DATA[id]; if (!it) return;
    (groups[it.section] = groups[it.section] || []).push(it);
  }});
  let body = "MOKIPOPS — Content Picks\\n";
  if (who.value.trim()) body += "From: " + who.value.trim() + "\\n";
  body += "Total selected: " + sel.size + "\\n";
  for (const section of Object.keys(groups)) {{
    body += "\\n" + section + "\\n";
    groups[section].forEach(it => {{ body += "  • " + it.label + "  —  " + it.source + "\\n"; }});
  }}
  if (notes.value.trim()) body += "\\nNotes:\\n" + notes.value.trim() + "\\n";
  const subject = "MOKIPOPS — Client Picks" + (who.value.trim() ? " (" + who.value.trim() + ")" : "");
  window.location.href = "mailto:" + STUDIO +
    "?subject=" + encodeURIComponent(subject) +
    "&body=" + encodeURIComponent(body);
}});

refresh();
</script>
</body>
</html>'''

    with open("picks.html", "w") as f:
        f.write(page)
    print(f"picks.html written · {len(items)} items ({len(lifestyle)} lifestyle, {len(brand)} brand, {len(product)} product)")


if __name__ == "__main__":
    main()
