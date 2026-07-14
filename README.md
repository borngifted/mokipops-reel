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
- `build_calendar.py` — extracts the full content calendar into `calendar.html` and public media for Blotato drafts
- `add.py` — encodes & registers new media
- `publish.sh` — build + commit + push
- `assets/` — web-optimized media (+ brand fonts + logo)
- `masters/` — full-resolution downloads linked from each video card

## Content calendar + Blotato

`calendar.html` is generated from `../MOKIPOPS-Content-Calendar.html`. It extracts the embedded calendar images into `assets/calendar/` so each selected post has a public GitHub Pages media URL that Blotato can pull into a scheduled draft.
