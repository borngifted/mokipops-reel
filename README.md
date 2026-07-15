# MOKIPOPS — Living Brand Reel

Client-facing content hub, live at **https://borngifted.github.io/mokipops-reel/**

This is a *revolving document*: all content lives in `content.json`, organized as dated
**drops** (newest first, newest gets a NEW badge). `build.py` renders `index.html` from it
in the MOKIPOPS brand kit (Fraunces/Archivo, cream + mango/chili, packaging-color accents).

## Add new content

```bash
cd ~/Documents/MOKIPOPS/mokipops-reel-site

# 1. (once per drop) create a dated section
python3 add.py drop --drop summer-drop --title "Summer Drop" --eyebrow "New flavors" --intro "..."

# 2. add media — videos are auto-encoded for web + poster + downloadable master
python3 add.py video ~/Desktop/new-reel.mp4 --drop summer-drop --title "The Remix" --tag "House · vocal" --blurb "..."
python3 add.py track ~/Desktop/new-song.mp3 --drop summer-drop --title "New Song" --desc "R&B · full length"
python3 add.py image ~/Desktop/new-pack.jpg --drop summer-drop --title "New Packaging"

# 3. rebuild + push live (takes ~1 min to deploy)
./publish.sh
```

Or just ask Claude: *"add this video to the mokipops reel site under a new drop"* — the
repo lives at `~/Documents/MOKIPOPS/mokipops-reel-site`.

## Files

- `content.json` — the single source of truth (site copy + all drops)
- `build.py` — renders `index.html` (never edit `index.html` by hand)
- `build_calendar.py` — scans public/postable media into `calendar.html` as a selectable Blotato asset picker
- `add.py` — encodes & registers new media
- `publish.sh` — build + commit + push
- `assets/` — web-optimized media (+ brand fonts + logo)
- `masters/` — full-resolution downloads linked from each video card

## Media picker + Blotato

`calendar.html` is now a selectable media picker, not a dated calendar. It scans the site media folders, imports optimized copies of external photos from the MOKIPOPS folder into `assets/library/`, labels each asset as photo or video, and sends selected public media URLs to Blotato as drafts.

The picker also curates the Shopify storefront: select assets, pick a Store channel (Gallery / Events / Markets / Waymo / Behind the Scenes), and click "Download Storefront Feed" to export `storefront-feed.json`. Committing that file to this repo root updates the picker-fed sections of the "MOKIPOPS Pop" Shopify theme (see `../mokipops-theme/README.md`) — the theme reads the feed plus `assets/library/library-data.json` from GitHub Pages at page load.

Videos too large for GitHub Pages (the `icloud-photos` clips) are hosted on Blotato media storage instead. `assets/library/imported/external-videos.json` maps each original file to its hosted `mediaUrl` plus a local poster thumbnail in `assets/library/imported/video-thumbs/`; `build_calendar.py` merges those entries into the picker. To add more external videos, upload them via `blotato_create_presigned_upload_url`, append entries to that JSON, generate a poster JPG, and re-run `python3 build_calendar.py`.
