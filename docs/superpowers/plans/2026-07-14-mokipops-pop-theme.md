# MOKIPOPS Pop Shopify Theme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the "MOKIPOPS Pop" draft Shopify theme replicating nokaorganics.com's homepage anatomy with MOKIPOPS branding, with lifestyle/gallery sections fed by the GitHub Pages media picker library.

**Architecture:** Dawn 15.x base + additive `mp-` prefixed sections, one shared CSS file (`assets/mp-pop.css`) holding brand tokens and section styles, one shared JS file (`assets/mp-pop.js`) with the feed client. Feed data lives in the mokipops-reel-site repo (GitHub Pages): `storefront-feed.json` + `assets/library/library-data.json`.

**Tech Stack:** Shopify Liquid (Dawn 15.x), vanilla JS/CSS, Python 3 (build_calendar.py changes), git + Shopify admin theme Import.

## Global Constraints

- Never publish the theme; import as DRAFT "MOKIPOPS Pop" only.
- No Noka images, copy, fonts, or palette. MOKIPOPS tokens: bg #FFF6E9, panel #FBEAD0, ink #2A1A12, mango #F5A623, orange #EE6C2B, chili #E23A23, green #5DA869, teal #4FB6A1, pink #EE5A8A. Fonts: Fraunces (display), Archivo (body).
- All custom files prefixed `mp-`; Dawn core edits limited to `layout/theme.liquid` include lines and template JSON.
- Picker-fed sections must render editor fallbacks when fetch fails/empty.
- Media base URL: https://borngifted.github.io/mokipops-reel/
- Theme repo: /Users/borngifted/Documents/MOKIPOPS/mokipops-theme (new git repo).

---

### Task 1: Scaffold theme from Dawn release

**Files:** Create `/Users/borngifted/Documents/MOKIPOPS/mokipops-theme/` (entire Dawn tree)

- [ ] Download latest Dawn release zip from https://github.com/Shopify/dawn/releases/latest, unzip into `mokipops-theme/`
- [ ] `git init`, commit baseline as `chore: Dawn <version> baseline`
- [ ] Verify: `ls sections/ | wc -l` > 30, `git log --oneline` shows baseline

### Task 2: Brand tokens + asset wiring

**Files:** Create `assets/mp-pop.css`, `assets/mp-pop.js` (empty shell); Modify `layout/theme.liquid` (add stylesheet+script tags before `</head>`), `config/settings_data.json` (colors/typography to MOKIPOPS values)

**Produces:** CSS custom properties `--mp-bg --mp-panel --mp-ink --mp-mango --mp-orange --mp-chili --mp-green --mp-teal --mp-pink --mp-radius:18px --mp-pill:999px`; utility classes `.mp-pill-btn .mp-card .mp-curve-top .mp-curve-bottom .mp-stars`; font stacks (Fraunces/Archivo via Google Fonts preconnect or Dawn font settings fallback).

- [ ] Write mp-pop.css tokens + utilities; add include lines to theme.liquid:
  `{{ 'mp-pop.css' | asset_url | stylesheet_tag }}` and `<script src="{{ 'mp-pop.js' | asset_url }}" defer></script>`
- [ ] Set settings_data.json scheme colors to brand values
- [ ] Verify: grep include lines; `python3 -c "import json;json.load(open('config/settings_data.json'))"`
- [ ] Commit `feat: MOKIPOPS brand tokens and asset shells`

### Task 3: Feed data on GitHub Pages (mokipops-reel-site repo)

**Files:** Modify `build_calendar.py` (emit `assets/library/library-data.json` alongside .js); Create `storefront-feed.json` (seeded channels using real asset IDs); Modify picker template (add "Download Storefront Feed" button + channel dropdown + JS exporter)

**Produces (contract for Task 5):**
- `GET <base>/assets/library/library-data.json` → same payload as window.MOKIPOPS_LIBRARY
- `GET <base>/storefront-feed.json` → `{updated, channels:{"lifestyle-events":[ids],"lifestyle-markets":[],"lifestyle-waymo":[],"lifestyle-bts":[],"gallery":[ids]}}`
- Exporter downloads `storefront-feed.json` built from current selection + chosen channel.

- [ ] build_calendar.py: after write_if_changed(DATA_JS,...) also `write_if_changed(LIBRARY_DIR / "library-data.json", json.dumps(payload,...))`
- [ ] Seed storefront-feed.json: pick 8 real video IDs (icloud-photos) for lifestyle-events, 12 mixed IDs for gallery
- [ ] Picker UI: add feed channel `<select id="feedChannel">` + `<button id="downloadFeed">` in draft panel; JS merges current selection into channel and downloads JSON
- [ ] Rebuild, verify `python3 - <<'EOF' json.load(open('assets/library/library-data.json'))` and feed JSON valid; commit + push; curl both URLs live (HTTP 200, JSON parses)

### Task 4: Ticker, header, footer restyle

**Files:** Create `sections/mp-ticker.liquid`, `sections/mp-header.liquid`; Modify `sections/header-group.json` (ticker + mp-header order), `sections/footer.liquid` only via CSS classes in mp-pop.css (no core edit); templates untouched yet

**mp-ticker core:** duplicated `<div class="mp-ticker__track">` spans, CSS `@keyframes mp-marquee {to{transform:translateX(-50%)}}`, `animation: mp-marquee var(--mp-ticker-speed,18s) linear infinite`, `@media (prefers-reduced-motion: reduce){animation:none}`. Schema: text, link, bg scheme, speed range 8-40s.

**mp-header:** sticky wrapper `.mp-header` (floating pill: max-width, border-radius pill, blur bg, shadow), left nav links from menu setting, centered `{{ section.settings.logo | image_url }}`, right: contact link + `{% render 'mp-cart-pill' %}` linking cart drawer (reuse Dawn `cart-icon-bubble`). Mobile ≤749px: hamburger button toggling Dawn menu-drawer.

- [ ] Write sections + schemas; wire header-group.json `["mp-ticker","mp-header"]`
- [ ] Verify: `python3 -c "import json;json.load(open('sections/header-group.json'))"`; Liquid tags balanced (grep `{% schema %}` + endschema in each new file)
- [ ] Commit `feat: ticker marquee and floating pill header`

### Task 5: Feed client (mp-pop.js)

**Files:** Modify `assets/mp-pop.js`

**Produces (used by Tasks 6-7):**
```js
window.MPFeed = {
  load(): Promise<{feed, manifest}|null>   // cached; 3s timeout + 1 retry each
  resolve(channel): Promise<Item[]>        // [] on any failure
  mediaCard(item, {video:'loop'}): HTMLElement  // .mp-media-card (img or muted looping video)
}
```

```js
(function () {
  const BASE = "https://borngifted.github.io/mokipops-reel/";
  let cache = null;
  async function fetchJson(url) {
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        const ctl = new AbortController();
        const t = setTimeout(() => ctl.abort(), 3000);
        const res = await fetch(url, { signal: ctl.signal });
        clearTimeout(t);
        if (res.ok) return await res.json();
      } catch (e) { console.warn("[mp-pop]", url, e.message); }
    }
    return null;
  }
  async function load() {
    if (cache) return cache;
    const [feed, manifest] = await Promise.all([
      fetchJson(BASE + "storefront-feed.json"),
      fetchJson(BASE + "assets/library/library-data.json"),
    ]);
    if (!feed || !manifest) return null;
    const byId = new Map(manifest.items.map(i => [i.id, i]));
    cache = { feed, manifest, byId };
    return cache;
  }
  function absUrl(u) { return /^https?:/.test(u) ? u : BASE + u; }
  async function resolve(channel) {
    const data = await load();
    if (!data) return [];
    return (data.feed.channels[channel] || [])
      .map(id => data.byId.get(id)).filter(Boolean);
  }
  function mediaCard(item) {
    const card = document.createElement("div");
    card.className = "mp-media-card";
    if (item.mediaType === "video") {
      const v = document.createElement("video");
      Object.assign(v, { muted: true, loop: true, playsInline: true, autoplay: true, preload: "metadata" });
      v.poster = item.thumbnail ? absUrl(item.thumbnail) : "";
      v.src = absUrl(item.mediaUrl);
      v.addEventListener("error", () => { card.innerHTML = `<img loading="lazy" src="${v.poster}" alt="">`; });
      card.appendChild(v);
    } else {
      const img = document.createElement("img");
      img.loading = "lazy"; img.alt = item.title || "";
      img.src = absUrl(item.thumbnail || item.mediaUrl);
      card.appendChild(img);
    }
    return card;
  }
  window.MPFeed = { load, resolve, mediaCard };
})();
```

- [ ] Write file; test against LIVE data with node (fetch available in node 18+):
  `node -e "global.window={};require('./assets/mp-pop.js');window.MPFeed.resolve('gallery').then(x=>console.log(x.length,'items'))"` → prints seeded count
- [ ] Commit `feat: picker feed client`

### Task 6: Hero + product cards + icon row + benefits

**Files:** Create `sections/mp-hero.liquid`, `sections/mp-product-cards.liquid`, `sections/mp-icon-row.liquid`, `sections/mp-benefits.liquid`; styles in mp-pop.css

- mp-hero: 2-col grid; blocks: `fruit` (image + top/left/depth settings) absolutely positioned, parallax via rAF scroll translate (data-depth), stars line text, h1 lowercase Fraunces clamp(34px,7vw,74px), pill CTA; reduced-motion disables transforms.
- mp-product-cards: collection setting; snap-x scroll list; card bg cycles `--mp-mango --mp-chili --mp-teal --mp-pink --mp-green` via `assign palette = 'mango,chili,teal,pink,green' | split`; stars, title, price, whole-card link; prev/next buttons scrollBy(±card width).
- mp-icon-row: up to 6 blocks (icon image + label), flex wrap center.
- mp-benefits: image+text split, `.mp-curve-top` SVG divider into `--mp-orange` band, optional rotating badge (`@keyframes mp-spin 24s linear`).
- [ ] Write all four + schemas with presets; JSON-validate schemas (`python3` extract between schema tags); commit `feat: hero, product cards, icons, benefits sections`

### Task 7: Picker-fed sections — media tabs + gallery

**Files:** Create `sections/mp-media-tabs.liquid`, `sections/mp-gallery.liquid`

- mp-media-tabs: blocks = tabs (label + channel key from fixed select: lifestyle-events/markets/waymo/bts + fallback image list setting). On load: `MPFeed.resolve(channel)` → horizontal snap carousel of `mediaCard`s (aspect 4/5, radius 18px); empty/failure → render fallback block images. Tab click swaps rendered set; lazy: only active tab loads media.
- mp-gallery: channel `gallery`, responsive grid `repeat(auto-fill,minmax(220px,1fr))`, first 12 items, "see more" link → picker Content Hub URL setting; same fallback pattern.
- [ ] Write sections; verify schemas parse; commit `feat: picker-fed media tabs and gallery`

### Task 8: Logo bar, UGC reviews, find-us, image banner, two-col grid

**Files:** Create `sections/mp-logo-bar.liquid`, `sections/mp-ugc-reviews.liquid`, `sections/mp-find-us.liquid`, `sections/mp-image-banner.liquid`, `sections/mp-two-col.liquid`

- mp-logo-bar: block images, slow marquee reusing mp-ticker keyframes (32s).
- mp-ugc-reviews: blocks (stars 1-5, quote, name, optional image); snap carousel + dots.
- mp-find-us: heading, sub, pill CTA on `--mp-teal` band with curve dividers.
- mp-image-banner: image, overlay heading/CTA, rounded 24px, full-bleed option.
- mp-two-col: 2 blocks (image, heading, text, CTA) side-by-side cards.
- [ ] Write all five + presets; JSON-validate; commit `feat: remaining homepage sections`

### Task 9: Homepage template + zip build

**Files:** Modify `templates/index.json` (compose sections in Noka order 1-13 with real settings/copy: "bliss on a stick, made simple", value props, Atlanta find-us copy); Create `build_zip.sh` (`cd theme dir && zip -r ../mokipops-pop-theme.zip . -x '*.git*'`)

- [ ] Compose index.json with all sections + seeded copy; JSON-validate
- [ ] Run `./build_zip.sh`; verify zip < 50MB and contains layout/theme.liquid at root level
- [ ] Commit `feat: homepage template and zip build`

### Task 10: Import + browser verification

- [ ] Shopify admin → Themes → Import (Add theme > Upload zip file) → upload mokipops-pop-theme.zip; DO NOT publish
- [ ] Rename to "MOKIPOPS Pop" if import name differs; open preview
- [ ] Verify in preview: ticker animates; pill header sticky + cart opens; hero renders with fruit; product cards show real products with rotating colors; media tabs load real picker videos (network shows blotato/github requests); gallery grid loads; footer email form renders; 390px mobile layout sane
- [ ] Screenshot key sections for the user; report issues found + fix + re-import cycle (theme Import creates new draft each time — delete superseded drafts we created)

### Task 11: Docs + handoff

- [ ] mokipops-theme/README.md: what it is, section inventory, feed contract, how to update storefront feed via picker, how to re-zip/import
- [ ] Update mokipops-reel-site README picker section: document Download Storefront Feed button
- [ ] Commit both repos; push mokipops-reel-site

## Self-Review Notes

- Spec coverage: all 14 spec sections map to Tasks 4/6/7/8 + footer restyle (Task 4). Feed contract → Task 3/5. Fallbacks → Tasks 5/7. Draft-only deploy → Task 10. Docs → Task 11. ✓
- No unresolved placeholders; section behaviors specified inline. ✓
- Type consistency: MPFeed API used by Tasks 6-7 matches Task 5 signature. ✓
