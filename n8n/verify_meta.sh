#!/bin/bash
# Checks the Meta side before the first automated post: token scopes, page access,
# Instagram account id, and that every media URL in the queue is publicly reachable.
#   ./verify_meta.sh            (reads .env next to this script)
set -u
cd "$(dirname "$0")"
[ -f .env ] && set -a && . ./.env && set +a
: "${META_PAGE_TOKEN:?set META_PAGE_TOKEN in .env}"
V=${GRAPH_VERSION:-v23.0}; PAGE=${FB_PAGE_ID:-1779805528922936}
G="https://graph.facebook.com/$V"

echo "== token =="
curl -s "$G/debug_token?input_token=$META_PAGE_TOKEN&access_token=$META_PAGE_TOKEN" \
 | python3 -c 'import sys,json;d=json.load(sys.stdin).get("data",{});print(" type:",d.get("type")," valid:",d.get("is_valid")," expires:",d.get("expires_at") or "never");print(" scopes:"," ".join(d.get("scopes",[])))'

echo "== page =="
curl -s "$G/$PAGE?fields=name,instagram_business_account{id,username}&access_token=$META_PAGE_TOKEN" | python3 -m json.tool

echo "== can this token act as the page? =="
curl -s "$G/me?fields=id,name&access_token=$META_PAGE_TOKEN" | python3 -m json.tool

echo "== media URLs in social-queue.json =="
python3 - <<'PY'
import json, subprocess
q = json.load(open("../social-queue.json"))["posts"]
seen = {}
for p in q:
    for u in (p["media_url"], p["media_fallback_url"]):
        if u in seen: continue
        code = subprocess.run(["curl","-sI","-o","/dev/null","-w","%{http_code}","-m","20",u],capture_output=True,text=True).stdout
        seen[u] = code
bad = {u:c for u,c in seen.items() if c != "200"}
print(f" {len(seen)} unique URLs, {len(seen)-len(bad)} return 200")
for u,c in bad.items(): print("  NOT LIVE", c, u)
PY
echo
echo "If instagram_business_account is missing: link the IG professional account to the page in Meta Business Suite → Settings → Instagram."
