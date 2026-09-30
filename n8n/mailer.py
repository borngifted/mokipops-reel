#!/usr/bin/env python3
"""Manual funnel mailer — send MOKIPOPS emails by hand, no n8n needed.

  python3 n8n/mailer.py --campaign V  --to you@example.com --name You        # one-off / test
  python3 n8n/mailer.py --campaign A2 --segment buyers --limit 40             # batch by hand
  python3 n8n/mailer.py --campaign B2 --segment b2b --limit 40 --dry-run      # writes previews only
  python3 n8n/mailer.py --list                                                # campaigns + counts

Campaigns: V (video opener) · A1 A2 (buyers) · B1 B2 B3 (b2b). Templates in docs/.
Video: every email can carry the film — `--video` adds the block to any campaign
(V has it built in): real <video> that autoplays muted in Apple Mail / iOS Mail, an
animated GIF everywhere else, a still poster in old Outlook, all linking to video.html.

SMTP login comes from n8n/.env: SMTP_HOST SMTP_PORT SMTP_USER SMTP_PASS (FUNNEL_FROM).
Every send is appended to contacts/send-log.jsonl and anyone already logged for that
campaign is skipped, so this script and the n8n batch share one memory.
"""
import argparse, csv, json, os, re, smtplib, ssl, sys, time, datetime as dt
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / "n8n" / ".env"
CONTACTS = ROOT / "contacts" / "contacts.csv"
LOG = ROOT / "contacts" / "send-log.jsonl"
OUTBOX = ROOT / "contacts" / "outbox"
SITE = "https://borngifted.github.io/mokipops-reel/"

CAMPAIGNS = {
    "V":  dict(segment="b2b",    file="docs/funnel-video-email.html", subject="12 years in 38 seconds 🍉", preview="Kid-founded, Atlanta-made, now on Faire. Press play."),
    "A1": dict(segment="buyers", file="docs/funnel-a1-template.html", subject="The pops got better since you left 🍉", preview="New flavors, same real fruit — and a way to never run out."),
    "A2": dict(segment="buyers", file="docs/funnel-a2-template.html", subject="One case = your whole event, sorted", preview="$53.50 for 24 pops. Offices, parties, teams, schools."),
    "B1": dict(segment="b2b",    file="docs/funnel-b1-template.html", subject="A $2 pop your customers will pay $4 for", preview="All-natural, Atlanta-made, margin at every level."),
    "B2": dict(segment="b2b",    file="docs/funnel-b2-template.html", subject="120 cases, 3,000 pops, one Atlanta afternoon", preview="The activation playbook — staffed cart included."),
    "B3": dict(segment="b2b",    file="docs/funnel-b3-template.html", subject="Should I close your file?", preview="One reply gets you the price sheet — or a call."),
}

VIDEO_TAG = f"""<video width="520" autoplay muted loop playsinline poster="{SITE}assets/funnel/funnel-poster.jpg" style="display:block;width:100%;max-width:520px;height:auto;border-radius:14px;">
      <source src="{SITE}assets/funnel/mokipops-wholesale-funnel.mp4" type="video/mp4">
      <img src="{SITE}assets/funnel/funnel-loop.gif" width="520" alt="MOKIPOPS — real fruit pops, made in Atlanta (tap to watch)" style="display:block;width:100%;max-width:520px;height:auto;border-radius:14px;border:0;">
    </video>"""

VIDEO_BLOCK = f"""
<!-- VIDEO BLOCK: <video> plays in Apple Mail / iOS Mail; everyone else sees the animated GIF; all click through -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center" style="padding:8px 24px 18px;">
  <a href="{SITE}video.html?utm_source=email&utm_medium=email&utm_campaign=wholesale_funnel&utm_content=video" target="_blank" style="text-decoration:none;display:block;">
    {VIDEO_TAG}
  </a>
  <p style="margin:10px 0 0;font-family:Helvetica,Arial,sans-serif;font-size:13px;color:#5A463B;">&#9654;&nbsp; <a href="{SITE}video.html?utm_source=email&utm_medium=email&utm_campaign=wholesale_funnel&utm_content=video_caption" target="_blank" style="color:#E23A23;text-decoration:underline;font-weight:700;">Watch the full 38 seconds</a> &nbsp;&middot;&nbsp; sound on</p>
</td></tr></table>
"""

def load_env():
    env = {}
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.split("#", 1)[0].strip().strip('"').strip("'")
    return {**env, **{k: v for k, v in os.environ.items() if k.startswith(("SMTP_", "FUNNEL_"))}}

def render(campaign, contact, with_video):
    c = CAMPAIGNS[campaign]
    html = (ROOT / c["file"]).read_text()
    first = (contact.get("firstname") or "there").strip() or "there"
    unsub = f"mailto:{FROM}?subject=" + "Unsubscribe%20" + contact["email"]
    html = re.sub(r"<!--[\s\S]*?-->", "", html)
    html = re.sub(r'\{%\s*text[^%]*value="([^"]*)"[^%]*%\}', lambda m: c["preview"] or m.group(1), html)
    html = re.sub(r"\{%[\s\S]*?%\}", "", html)
    reps = {"content.name": c["subject"], "contact.firstname": first, "unsubscribe_link": unsub, "unsubscribe_link_all": unsub,
            "site_settings.company_name": "MOKIPOPS", "site_settings.company_street_address_1": "", "site_settings.company_street_address_2": "",
            "site_settings.company_city": "Atlanta", "site_settings.company_state": "GA", "site_settings.company_zip": "", "site_settings.company_country": "USA"}
    for k, v in reps.items():
        html = re.sub(r"\{\{\s*" + re.escape(k) + r"\s*\}\}", v, html)
    html = re.sub(r"\{\{[^}]*\}\}", "", html)
    html = html.replace("utm_source=hubspot", "utm_source=email")
    if campaign == "V":
        # upgrade the GIF-only opener: swap the preview GIF <img> for the <video> element (GIF stays as its fallback)
        html = re.sub(r'<img src="[^"]*funnel-preview\.gif"[\s\S]*?>', VIDEO_TAG, html, count=1)
    elif with_video:
        # drop the video block right after the logo (first closing </tr> that follows logo.png), else at top of body
        m = re.search(r"logo\.png[\s\S]*?</tr>", html)
        html = html[:m.end()] + "<tr><td>" + VIDEO_BLOCK + "</td></tr>" + html[m.end():] if m else re.sub(r"(<body[^>]*>)", r"\1" + VIDEO_BLOCK, html, count=1)
    text = re.sub(r"<style[\s\S]*?</style>", "", html)
    text = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>', lambda m: re.sub(r"<[^>]+>", "", m.group(2)).strip() + f" ({m.group(1)})", text)
    text = re.sub(r"<video[\s\S]*?</video>", f"Watch the film: {SITE}video.html", text)
    text = re.sub(r"</(p|div|tr|h\d|li)>", "\n", text); text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"').replace("&middot;", "·").replace("&#9654;", "▶")
    text = re.sub(r"[ \t]+\n", "\n", text); text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return c["subject"], html, text

def already_sent():
    sent = {}
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            try:
                r = json.loads(line)
                if r.get("ok"): sent.setdefault(r["campaign"], set()).add(r["email"].lower())
            except Exception: pass
    return sent

def log(rec):
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "a") as f: f.write(json.dumps(rec) + "\n")

def recipients(args):
    if args.to:
        return [dict(email=args.to.lower(), firstname=(args.name or "").split(" ")[0], name=args.name or "", segment="manual", status="active")]
    if not CONTACTS.exists(): sys.exit("contacts/contacts.csv missing — run python3 n8n/build_contacts.py")
    seg = args.segment or CAMPAIGNS[args.campaign]["segment"]
    sent = already_sent().get(args.campaign, set())
    rows = [r for r in csv.DictReader(open(CONTACTS)) if r["segment"] == seg and r.get("status", "active") == "active" and r["email"].lower() not in sent]
    print(f"{args.campaign} → segment {seg}: {len(rows)} eligible & unsent, sending {min(len(rows), args.limit)}")
    return rows[: args.limit]

def main():
    global FROM
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--campaign", choices=CAMPAIGNS.keys())
    ap.add_argument("--to"); ap.add_argument("--name", default="")
    ap.add_argument("--segment", choices=["buyers", "b2b", "lead"]); ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--video", action="store_true", help="add the video block to a non-video campaign")
    ap.add_argument("--dry-run", action="store_true", help="render to contacts/outbox/ instead of sending")
    ap.add_argument("--pause", type=float, default=30); ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    env = load_env(); FROM = env.get("FUNNEL_FROM", "moreflavor@mokipops.com")
    if args.list:
        sent = already_sent()
        for k, c in CAMPAIGNS.items(): print(f"{k:3s} {c['segment']:7s} sent so far: {len(sent.get(k, [])):4d}  — {c['subject']}")
        return
    if not args.campaign: ap.error("--campaign is required")
    rows = recipients(args)
    if not rows: print("nothing to send"); return
    smtp = None
    if not args.dry_run:
        host, port, user, pw = env.get("SMTP_HOST", "smtp.office365.com"), int(env.get("SMTP_PORT", 587)), env.get("SMTP_USER", FROM), env.get("SMTP_PASS", "")
        smtp = smtplib.SMTP(host, port, timeout=60); smtp.ehlo()
        if port != 25 and smtp.has_extn("starttls"): smtp.starttls(context=ssl.create_default_context()); smtp.ehlo()
        if pw: smtp.login(user, pw)
        print(f"connected to {host}:{port} as {user}")
    OUTBOX.mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(rows):
        subject, html, text = render(args.campaign, r, args.video)
        msg = EmailMessage()
        msg["From"] = formataddr(("MOKIPOPS", FROM)); msg["To"] = formataddr((r.get("name") or "", r["email"])); msg["Subject"] = subject
        msg["Reply-To"] = FROM; msg["Message-ID"] = make_msgid(domain=FROM.split("@")[1]); msg["List-Unsubscribe"] = f"<mailto:{FROM}?subject=Unsubscribe>"
        msg.set_content(text); msg.add_alternative(html, subtype="html")
        rec = dict(at=dt.datetime.utcnow().isoformat(timespec="seconds") + "Z", campaign=args.campaign, email=r["email"], segment=r.get("segment", ""), via="mailer.py", ok=True, error=None)
        if args.dry_run:
            p = OUTBOX / f"{args.campaign}-{r['email'].replace('@', '_at_')}.html"; p.write_text(html); print(f"  preview → {p.relative_to(ROOT)}")
            continue
        try:
            smtp.send_message(msg); print(f"  sent {args.campaign} → {r['email']}")
        except Exception as e:
            rec.update(ok=False, error=str(e)[:300]); print(f"  FAILED {r['email']}: {e}")
        log(rec)
        if i < len(rows) - 1 and not args.to: time.sleep(args.pause)
    if smtp: smtp.quit()

if __name__ == "__main__":
    main()
