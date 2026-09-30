#!/usr/bin/env python3
"""Build contacts/contacts.csv — the local replacement for the HubSpot segments.

Sources already in this repo (all git-ignored, never published):
  calls-customers.json  Shopify customers with ≥1 order          → segment "buyers"   (was: Previous Buyers)
  calls-hubspot.json    HubSpot CRM export, email + company + lifecycle
                        lifecycle=opportunity OR company known    → segment "b2b"      (was: B2B Prospects + Warm Opportunities)
                        everything else with an email             → segment "lead"     (never mailed by default)
Suppression: contacts/suppress-domains.txt (junk/bot domains) and contacts/unsubscribed.txt
(one email per line; anyone who replies "unsubscribe" goes here).

  python3 n8n/build_contacts.py
"""
import csv, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "contacts" / "contacts.csv"
SUPPRESS = ROOT / "contacts" / "suppress-domains.txt"
UNSUB = ROOT / "contacts" / "unsubscribed.txt"

DEFAULT_SUPPRESS = """# one pattern per line; matched against the part after @ (substring match)
docusign.net
venmo.com
uber.com
adobe
echosign.com
sba.gov
storebotmail.joonix.net
hubspot.com
mokipops.com
inscrlab
ilovemyemail
accaps.top
noreply
no-reply
"""

def load_lines(p, default=""):
    if not p.exists():
        p.write_text(default)
    return [l.strip().lower() for l in p.read_text().splitlines() if l.strip() and not l.startswith("#")]

def first_name(full):
    full = (full or "").strip()
    if not full or "@" in full:
        return ""
    return re.split(r"[\s,]+", full)[0].title()

def main():
    suppress = load_lines(SUPPRESS, DEFAULT_SUPPRESS)
    unsub = set(load_lines(UNSUB, "# one email per line\n"))
    hub = json.load(open(ROOT / "calls-hubspot.json"))["contacts"]
    buyers = {e.lower() for e in json.load(open(ROOT / "calls-customers.json"))["emails"]}

    rows, seen = [], set()
    def add(email, name, company, city, phone, segment, lifecycle, source):
        email = (email or "").strip().lower()
        if not email or "@" not in email or email in seen:
            return
        seen.add(email)
        dom = email.split("@", 1)[1]
        status = "active"
        if email in unsub:
            status = "unsubscribed"
        elif any(s in dom for s in suppress):
            status = "suppressed"
        rows.append(dict(email=email, firstname=first_name(name), name=name or "", company=company or "",
                         city=city or "", phone=phone or "", segment=segment, lifecycle=lifecycle or "",
                         source=source, status=status))

    byemail = {r[2].lower(): r for r in hub if r[2]}
    for e in sorted(buyers):
        r = byemail.get(e)
        add(e, r[1] if r else "", r[4] if r else "", r[5] if r else "", r[3] if r else "", "buyers", r[6] if r else "customer", "shopify")
    for _id, name, email, phone, company, city, lifecycle in hub:
        if not email or email.lower() in seen:
            continue
        seg = "b2b" if (lifecycle == "opportunity" or (company or "").strip()) else "lead"
        add(email, name, company, city, phone, seg, lifecycle, "hubspot")

    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    from collections import Counter
    c = Counter((r["segment"], r["status"]) for r in rows)
    print(f"{len(rows)} contacts → {OUT.relative_to(ROOT)}")
    for (seg, st), n in sorted(c.items()):
        print(f"  {seg:7s} {st:12s} {n}")

if __name__ == "__main__":
    main()
