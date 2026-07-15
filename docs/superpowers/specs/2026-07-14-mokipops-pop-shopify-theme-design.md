# MOKIPOPS Pop — Shopify Theme Design

Date: 2026-07-14
Status: Approved (homepage-first scope)

## Goal

A new Shopify draft theme for the MOKIPOPS store (`547ac9-2.myshopify.com`) that
replicates the layout, section order, and interactive functions of
nokaorganics.com's homepage, restyled entirely with MOKIPOPS branding, and whose
lifestyle/gallery sections are fed by the media picker library shipped at
https://borngifted.github.io/mokipops-reel/calendar.html.

Explicitly NOT copying from Noka: images, copy, logos, color palette, fonts.
What we replicate: section anatomy, layout patterns, motion (marquee ticker,
parallax hero fruit, tabbed media carousel, curved dividers), and functions.

## Decisions (user-confirmed)

1. Picker integration: theme sections pull media from the picker library
   manifest on GitHub Pages; curation via a storefront feed JSON.
2. Branding: MOKIPOPS identity (cream #FFF6E9 / mango #F5A623 / orange #EE6C2B /
   chili #E23A23 / teal #4FB6A1 / pink #EE5A8A; Fraunces + Archivo) on Noka's
   layout.
3. Scope: homepage + header/footer now; product/collection/story pages remain
   Dawn defaults inheriting the brand tokens. Subscriptions app, store-locator
   map, and product-page rebuild are out of scope for round 1.

## Architecture

- Base: latest public release of Shopify Dawn (15.x), downloaded from
  github.com/Shopify/dawn. Keeps cart drawer, predictive search, product forms,
  localization, and accessibility.
- Local working copy: `/Users/borngifted/Documents/MOKIPOPS/mokipops-theme/`
  (its own git repo).
- Custom code is additive: new sections prefixed `mp-` (e.g.
  `sections/mp-ticker.liquid`), shared CSS in `assets/mp-pop.css`, shared JS in
  `assets/mp-pop.js`, brand tokens via `config/settings_data.json` +
  `mp-pop.css` custom properties. Dawn core files are modified as little as
  possible (only `layout/theme.liquid` to include the assets, and template
  JSON files).
- Deploy: zip the theme, import via Shopify admin Themes > Import as a DRAFT
  named "MOKIPOPS Pop". Never publish without explicit user approval.

## Homepage sections (templates/index.json order)

1. `mp-ticker` — infinite marquee announcement bar. Settings: repeated phrases,
   link, speed, colors. CSS keyframe marquee, duplicated content for seamless
   loop, `prefers-reduced-motion` pauses it.
2. `mp-header` (section group `header-group.json`) — sticky floating pill nav:
   left links (shop +, our story), centered logo, right (contact, cart pill
   with live count). Mobile: hamburger opens Dawn's drawer. Reuses Dawn cart
   drawer + menus; only presentation is custom.
3. `mp-hero` — split hero: left big lowercase Fraunces headline, review-stars
   microcopy line, pill CTA; right layered product cutout images with 4-8
   absolutely-positioned floating fruit sprites, translated on scroll via
   IntersectionObserver + rAF parallax (disabled under reduced motion).
   Settings: heading, sub, CTA, product images, fruit images, bg color.
4. `mp-product-cards` — horizontal snap-scroll carousel of products from a
   chosen collection; each card gets a solid color from a rotating brand
   palette; stars line, flavor title, hover lift; arrow buttons + dots.
5. `mp-icon-row` — 4-6 value-prop icons (All Natural, Vegan, Clean Label,
   FDA-Registered Facility, No Dairy/Gluten).
6. `mp-benefits` — image/copy split with curved SVG divider flowing into a
   full-bleed orange band (Noka's signature curve), badge sticker rotator
   optional.
7. `mp-media-tabs` — PICKER-FED tabbed lifestyle carousel. Tabs (e.g. Events /
   Markets / Waymo / Behind the Scenes) map to feed channels. Photos render as
   rounded cards; videos autoplay muted loop inline (playsinline, lazy).
8. `mp-logo-bar` — horizontally scrolling press/partner logos (editor uploads).
9. `mp-ugc-reviews` — quote carousel, editor-managed blocks (name, stars, text,
   optional image).
10. `mp-find-us` — CTA band ("find us around Atlanta") with button; simple
    text/link version of Noka's store finder.
11. `mp-image-banner` — full-width rounded image banner with overlay text.
12. `mp-two-col-grid` — two promo cards (e.g. wholesale inquiry / event
    booking), pill CTAs.
13. `mp-gallery` — PICKER-FED Instagram-style grid (channel `gallery`),
    lightbox-free (links to the picker's Content Hub), video tiles muted loop.
14. `footer` — restyled Dawn footer: email capture headline ("Get 15% off your
    first order"), socials, link columns.

## Picker feed contract

- `mokipops-reel-site/storefront-feed.json` (served on GitHub Pages, CORS `*`):

```json
{
  "updated": "2026-07-14T00:00:00Z",
  "channels": {
    "lifestyle-events": ["asset-1067", "asset-1102"],
    "lifestyle-markets": [],
    "lifestyle-waymo": [],
    "lifestyle-bts": [],
    "gallery": ["asset-0009"]
  }
}
```

- Asset IDs reference `assets/library/library-data.js` entries (the 1350-asset
  manifest). Theme JS (`mp-pop.js`) fetches `library-data.json` — a JSON twin
  of the manifest that `build_calendar.py` will additionally emit — plus the
  feed, resolves IDs to mediaUrl/thumbnail, and renders.
- Relative photo URLs resolve against `https://borngifted.github.io/mokipops-reel/`;
  icloud video URLs are already absolute (Blotato storage).
- Picker page gains a "Download Storefront Feed" button exporting the current
  selection into this JSON shape (channel chosen via prompt/dropdown), merged
  client-side with the previously published feed when reachable.
- Fallback: every picker-fed section supports editor-uploaded fallback images;
  if fetch fails or a channel is empty, fallbacks render. No blank sections.

## Data flow

Shopify storefront (theme JS)
  -> GET borngifted.github.io/mokipops-reel/storefront-feed.json
  -> GET borngifted.github.io/mokipops-reel/assets/library/library-data.json
  -> resolve channel IDs -> render cards (img / muted video)
  -> on any failure -> render section fallback blocks

Curation loop: client selects in picker -> downloads storefront-feed.json ->
sends to studio (or Claude commits directly) -> git push -> Pages deploy ->
storefront updates on next load. Shopify untouched.

## Error handling

- Feed/manifest fetch: 3s timeout, single retry, then fallbacks. Errors logged
  to console with `[mp-pop]` prefix.
- Missing asset ID in manifest: skipped silently.
- Video element error: card swaps to poster thumbnail image.
- Reduced motion: marquee pauses, parallax disabled, videos show posters with
  play affordance.

## Testing

- `shopify theme check` (if CLI available) or Liquid syntax review pass.
- Local render test of mp-pop.js feed resolution with node against the real
  manifest + a sample feed.
- After import as draft: preview via theme preview URL; verify all 14 sections
  render, cart drawer opens, mobile layout at 390px, picker-fed sections load
  real assets, fallbacks appear when feed URL is blocked.
- Lighthouse quick pass on preview (target: no regression vs Dawn defaults on
  LCP; lazy-load all picker media).

## Risks

- Theme zip import cap (50MB) — fine, no videos ship in the theme.
- Shopify CSP does not block cross-origin fetch/media from GitHub Pages or
  Blotato storage (both plain public CDNs). Verified pattern: Blotato media
  already renders on Pages picker.
- Subscribe & save: links to /pages/contact or hidden until a subscription app
  exists.
