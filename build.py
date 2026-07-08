#!/usr/bin/env python3
"""Render index.html from content.json — the MOKIPOPS living brand reel.

Usage: python3 build.py
Drops render newest-first; the newest drop gets a NEW badge.
"""
import json, os
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))

def nice_date(iso):
    d = date.fromisoformat(iso)
    return d.strftime("%B %-d, %Y")

def video_card(v):
    dl = ""
    if v.get("master"):
        dl = f'\n        <a class="dl" href="{v["master"]}" download>&#8595;&#xFE0E; Download master (720&times;1280)</a>'
    return f"""
      <div class="card reveal">
        <div class="card-head">
          <span class="num">{v["num"]}</span>
          <div><h3>{v["title"]}</h3><p class="tag">{v["tag"]}</p></div>
        </div>
        <div class="vwrap"><video playsinline preload="none" controls poster="{v["poster"]}" src="{v["src"]}"></video></div>
        <p class="blurb">{v["blurb"]}</p>{dl}
      </div>"""

def track_row(t):
    g1, g2 = t["gradient"].split(",")
    return f"""
      <div class="trow reveal">
        <button class="tplay" aria-label="Play {t["title"]}">
          <svg class="i-play" viewBox="0 0 24 24" width="16" height="16"><path d="M8 5.5v13l11-6.5z" fill="currentColor"/></svg>
          <svg class="i-pause" viewBox="0 0 24 24" width="16" height="16" style="display:none"><path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" fill="currentColor"/></svg>
        </button>
        <div class="tart" style="background:linear-gradient(135deg,{g1},{g2})">&#9834;</div>
        <div class="tmeta">
          <b>{t["title"]}</b><span>{t["desc"]}</span>
          <div class="tbar"><div class="tfill"></div></div>
        </div>
        <span class="tdur">{t["dur"]}</span>
        <audio preload="metadata" src="{t["src"]}"></audio>
      </div>"""

def image_card(im):
    return f"""
      <div class="card reveal">
        <div class="card-head">
          <div><h3>{im["title"]}</h3><p class="tag">{im.get("tag","")}</p></div>
        </div>
        <img class="gimg" src="{im["src"]}" alt="{im["title"]}" loading="lazy">
        <p class="blurb">{im.get("blurb","")}</p>
      </div>"""

def drop_section(drop, is_newest):
    badge = '<span class="newbadge">NEW</span>' if is_newest else ""
    parts = [f"""
<section class="wrap drop" id="{drop["id"]}">
  <div class="drophead reveal">
    <span class="datechip">{nice_date(drop["date"])}</span>{badge}
    <h2>{drop["title"]}<span class="dot">.</span></h2>
    <p class="dropeyebrow">{drop.get("eyebrow","")}</p>
    <p class="dropintro">{drop.get("intro","")}</p>
  </div>"""]
    if drop.get("videos"):
        parts.append(f'  <div class="cuts">{"".join(video_card(v) for v in drop["videos"])}\n  </div>')
    if drop.get("images"):
        parts.append(f'  <div class="cuts">{"".join(image_card(i) for i in drop["images"])}\n  </div>')
    if drop.get("tracks"):
        parts.append(f"""  <div class="panelband" style="margin-top:22px">
    <div class="sechead reveal"><h3 class="tracksh">The Soundtracks<span class="dot">.</span></h3></div>
    <div class="tracks">{"".join(track_row(t) for t in drop["tracks"])}
    </div>
  </div>""")
    parts.append("</section>")
    return "\n".join(parts)

def main():
    with open(os.path.join(HERE, "content.json"), encoding="utf-8") as f:
        data = json.load(f)
    site = data["site"]
    drops = sorted(data["drops"], key=lambda d: d["date"], reverse=True)
    updated = nice_date(max(d["date"] for d in drops))
    sections = "\n".join(drop_section(d, i == 0) for i, d in enumerate(drops))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{site["title"]}</title>
<style>
@font-face {{ font-family:'Fraunces'; src:url(assets/fraunces.woff2) format('woff2'); font-weight:100 900; font-display:swap; }}
@font-face {{ font-family:'Archivo'; src:url(assets/archivo.woff2) format('woff2'); font-weight:100 900; font-display:swap; }}
:root {{
  --bg:#FFF6E9; --panel:#FBEAD0; --ink:#2A1A12; --sub:#5A463B; --hairline:rgba(42,26,18,.12);
  --card:#ffffff; --mango:#F5A623; --orange:#EE6C2B; --chili:#E23A23; --r:22px;
}}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#211714; --panel:#2A1A12; --ink:#FFF6E9; --sub:#cdbba8; --hairline:rgba(255,246,233,.14); --card:#33211a; }}
}}
* {{ box-sizing:border-box; margin:0; padding:0; -webkit-tap-highlight-color:transparent; }}
html {{ scroll-behavior:smooth; }}
body {{
  font-family:'Archivo',-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif;
  background:var(--bg); color:var(--ink); line-height:1.55; -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility;
}}
h1, h2, h3 {{ font-family:'Fraunces',Georgia,serif; }}
.wrap {{ max-width:1040px; margin:0 auto; padding:0 max(22px, env(safe-area-inset-left)); }}

.topbar {{ position:sticky; top:0; z-index:50; backdrop-filter:saturate(180%) blur(20px); -webkit-backdrop-filter:saturate(180%) blur(20px);
  background:color-mix(in srgb, var(--bg) 78%, transparent); border-bottom:1px solid var(--hairline); }}
.topbar .wrap {{ display:flex; align-items:center; justify-content:space-between; height:52px; }}
.wordmark {{ font-family:'Fraunces',Georgia,serif; font-weight:900; font-size:17px; letter-spacing:-.01em; }}
.wordmark em {{ font-style:normal; color:var(--mango); }}
.topmeta {{ font-size:12.5px; color:var(--sub); font-weight:600; }}

.hero {{ position:relative; text-align:center; padding:clamp(56px,10vw,96px) 0 clamp(34px,5vw,54px); overflow:hidden; }}
.hero::before {{ content:""; position:absolute; inset:0; pointer-events:none; background:
  radial-gradient(480px 300px at 18% 8%, rgba(245,166,35,.22), transparent 62%),
  radial-gradient(430px 280px at 84% 16%, rgba(226,58,35,.12), transparent 60%); }}
.hero > * {{ position:relative; }}
.eyebrow {{ display:inline-block; font-size:12.5px; font-weight:800; color:var(--chili); letter-spacing:.09em; text-transform:uppercase;
  background:rgba(245,166,35,.16); border:1px solid rgba(245,166,35,.35); border-radius:100px; padding:7px 16px; margin-bottom:22px; }}
h1 {{ font-size:clamp(38px,7vw,70px); font-weight:900; letter-spacing:-0.02em; line-height:1.02; }}
h1 .soft {{ background:linear-gradient(92deg,var(--mango),var(--orange) 45%,var(--chili)); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }}
.lede {{ font-size:clamp(16px,2.3vw,19px); color:var(--sub); max-width:580px; margin:20px auto 0; }}

.drop {{ padding:clamp(30px,5vw,56px) 0 clamp(20px,3vw,34px); }}
.drop + .drop {{ border-top:1px solid var(--hairline); }}
.drophead {{ text-align:center; margin-bottom:clamp(24px,4vw,40px); }}
.datechip {{ display:inline-block; font-size:12px; font-weight:800; letter-spacing:.06em; text-transform:uppercase;
  color:var(--sub); border:1.5px solid var(--hairline); border-radius:100px; padding:6px 14px; }}
.newbadge {{ display:inline-block; margin-left:8px; font-size:11.5px; font-weight:900; letter-spacing:.1em;
  color:#fff; background:linear-gradient(90deg,var(--mango),var(--chili)); border-radius:100px; padding:6px 12px; vertical-align:1px; }}
h2 {{ font-size:clamp(28px,4.4vw,42px); font-weight:900; letter-spacing:-0.015em; margin-top:14px; }}
h2 .dot, h3 .dot {{ color:var(--mango); }}
.dropeyebrow {{ margin-top:8px; font-size:12.5px; font-weight:800; color:var(--chili); letter-spacing:.09em; text-transform:uppercase; }}
.dropintro {{ color:var(--sub); font-size:15.5px; max-width:640px; margin:10px auto 0; }}
.sechead {{ text-align:center; margin-bottom:clamp(18px,3vw,30px); }}
.tracksh {{ font-size:clamp(22px,3.2vw,30px); font-weight:900; letter-spacing:-0.015em; }}

.cuts {{ display:grid; grid-template-columns:repeat(4,1fr); gap:18px; }}
@media (max-width:960px) {{ .cuts {{ grid-template-columns:repeat(2,1fr); }} }}
@media (max-width:560px) {{
  .cuts {{ display:flex; overflow-x:auto; scroll-snap-type:x mandatory; gap:14px; padding:4px 22px 18px; margin:0 -22px; scrollbar-width:none; }}
  .cuts::-webkit-scrollbar {{ display:none; }}
  .cuts .card {{ flex:0 0 78%; scroll-snap-align:center; }}
}}
.card {{ background:var(--card); border:1px solid var(--hairline); border-radius:var(--r); padding:14px;
  box-shadow:0 18px 38px -24px rgba(120,50,10,.45); }}
.card-head {{ display:flex; gap:10px; align-items:center; margin:2px 4px 12px; }}
.num {{ flex:none; width:30px; height:30px; border-radius:9px; background:linear-gradient(135deg,var(--mango),var(--chili));
  color:#fff; font-size:12.5px; font-weight:800; font-family:'Archivo'; display:grid; place-items:center; }}
.card h3 {{ font-size:17px; font-weight:700; letter-spacing:-0.01em; }}
.tag {{ font-size:12px; color:var(--sub); }}
.vwrap {{ border-radius:14px; overflow:hidden; aspect-ratio:9/16; background:#1a0f0a; }}
.vwrap video {{ width:100%; height:100%; display:block; object-fit:cover; }}
.gimg {{ width:100%; border-radius:14px; display:block; }}
.blurb {{ font-size:13px; color:var(--sub); margin:12px 6px 4px; }}
.dl {{ display:inline-block; margin:10px 6px 2px; font-size:12.5px; font-weight:800; color:var(--chili); text-decoration:none;
  border:1.5px solid rgba(226,58,35,.4); border-radius:100px; padding:7px 14px; transition:background .15s ease; }}
.dl:hover {{ background:rgba(226,58,35,.08); }}

.panelband {{ background:var(--panel); border:1px solid var(--hairline); border-radius:calc(var(--r) + 8px); padding:clamp(22px,3.4vw,40px); }}
.tracks {{ display:flex; flex-direction:column; }}
.trow {{ display:flex; align-items:center; gap:14px; padding:14px 6px; border-bottom:1px solid var(--hairline); }}
.trow:last-child {{ border-bottom:none; }}
.tplay {{ flex:none; width:38px; height:38px; border-radius:50%; border:none; cursor:pointer;
  background:var(--chili); color:#fff; display:grid; place-items:center; transition:transform .15s ease; }}
.tplay:active {{ transform:scale(.92); }}
.tart {{ flex:none; width:46px; height:46px; border-radius:10px; color:rgba(255,255,255,.95); display:grid; place-items:center; font-size:20px; }}
.tmeta {{ flex:1; min-width:0; }}
.tmeta b {{ display:block; font-size:15.5px; font-weight:700; letter-spacing:-0.01em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-family:'Archivo'; }}
.tmeta span {{ display:block; font-size:12.5px; color:var(--sub); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.tbar {{ height:3px; border-radius:99px; background:var(--hairline); margin-top:8px; overflow:hidden; cursor:pointer; }}
.tfill {{ height:100%; width:0%; border-radius:99px; background:linear-gradient(90deg,var(--mango),var(--chili)); }}
.tdur {{ font-size:12.5px; color:var(--sub); font-variant-numeric:tabular-nums; }}

footer {{ margin-top:44px; background:var(--ink); color:#FBEAD0; text-align:center;
  padding:56px 0 calc(44px + env(safe-area-inset-bottom)); }}
@media (prefers-color-scheme: dark) {{ footer {{ background:#170e0a; }} }}
footer img {{ height:64px; width:auto; }}
footer .fline {{ margin-top:16px; font-size:14px; color:#e6d6c4; }}
footer .fline b {{ color:#fff; font-family:'Fraunces',Georgia,serif; }}
footer .fsmall {{ margin-top:22px; font-size:12px; color:#cdbba8; opacity:.85; }}

.reveal {{ opacity:0; transform:translateY(14px); transition:opacity .6s ease, transform .6s ease; }}
.reveal.in {{ opacity:1; transform:none; }}
@media (prefers-reduced-motion: reduce) {{
  html {{ scroll-behavior:auto; }}
  .reveal {{ opacity:1; transform:none; transition:none; }}
}}
</style>
</head>
<body>

<div class="topbar"><div class="wrap">
  <span class="wordmark">{site["wordmark_top"]}<em>{site["wordmark_accent"]}</em></span>
  <span class="topmeta">Updated {updated}</span>
</div></div>

<header class="hero wrap">
  <span class="eyebrow">{site["hero_eyebrow"]}</span>
  <h1>{site["hero_title_1"]}<br><span class="soft">{site["hero_title_2"]}</span></h1>
  <p class="lede">{site["hero_lede"]}</p>
</header>

{sections}

<footer>
  <img src="assets/logo.png" alt="MOKIPOPS — All Natural Handcrafted Frozen Fruit Bars">
  <p class="fline"><b>Bliss on a Stick</b> · mokipops.com · @mokipops</p>
  <p class="fsmall">{site["footer_credit"]}</p>
</footer>

<script>
(function() {{
  var media = Array.prototype.slice.call(document.querySelectorAll('video, audio'));
  function pauseOthers(current) {{
    media.forEach(function(m) {{ if (m !== current && !m.paused) m.pause(); }});
  }}
  media.forEach(function(m) {{ m.addEventListener('play', function() {{ pauseOthers(m); }}); }});

  document.querySelectorAll('.trow').forEach(function(row) {{
    var audio = row.querySelector('audio');
    var btn = row.querySelector('.tplay');
    var iPlay = row.querySelector('.i-play');
    var iPause = row.querySelector('.i-pause');
    var fill = row.querySelector('.tfill');
    var bar = row.querySelector('.tbar');
    btn.addEventListener('click', function() {{
      if (audio.paused) {{ audio.play(); }} else {{ audio.pause(); }}
    }});
    audio.addEventListener('play', function() {{ iPlay.style.display='none'; iPause.style.display='block'; }});
    audio.addEventListener('pause', function() {{ iPlay.style.display='block'; iPause.style.display='none'; }});
    audio.addEventListener('ended', function() {{ fill.style.width='0%'; }});
    audio.addEventListener('timeupdate', function() {{
      if (audio.duration) fill.style.width = (audio.currentTime / audio.duration * 100) + '%';
    }});
    bar.addEventListener('click', function(e) {{
      var r = bar.getBoundingClientRect();
      if (audio.duration) audio.currentTime = ((e.clientX - r.left) / r.width) * audio.duration;
    }});
  }});

  if ('IntersectionObserver' in window) {{
    var io = new IntersectionObserver(function(entries) {{
      entries.forEach(function(en) {{ if (en.isIntersecting) {{ en.target.classList.add('in'); io.unobserve(en.target); }} }});
    }}, {{ threshold: 0.12 }});
    document.querySelectorAll('.reveal').forEach(function(el) {{ io.observe(el); }});
  }} else {{
    document.querySelectorAll('.reveal').forEach(function(el) {{ el.classList.add('in'); }});
  }}
}})();
</script>
</body>
</html>"""
    out = os.path.join(HERE, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"built index.html ({os.path.getsize(out)//1024} KB) — {len(drops)} drop(s), updated {updated}")

if __name__ == "__main__":
    main()
