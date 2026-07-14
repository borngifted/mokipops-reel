#!/bin/bash
# Rebuild the page from content.json, commit, and push live to GitHub Pages.
set -e
cd "$(dirname "$0")"
python3 build.py
python3 build_picks.py
python3 build_calendar.py
git add -A
if git diff --cached --quiet; then
  echo "nothing new to publish"
  exit 0
fi
git commit -m "Content update — $(date '+%B %d, %Y')"
git push
echo "live in ~1 minute: https://borngifted.github.io/mokipops-reel/"
