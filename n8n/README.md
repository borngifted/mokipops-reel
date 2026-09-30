# MOKIPOPS local automation on n8n (replaces Blotato **and** HubSpot)

The client-facing version of this guide, with a live queue widget, is
**https://borngifted.github.io/mokipops-reel/runbook.html** — start there. This file is the
engineer's copy.

Three workflows, all running in one n8n container on this Mac:

| Workflow | File | Replaces |
|---|---|---|
| Daily FB + IG cross-post, 12:00 ET | `mokipops-daily-post.json` | Blotato |
| Funnel email batch (A1/A2 buyers · B1/B2/B3 b2b), manual, capped | `mokipops-funnel-send.json` | HubSpot Marketing Email |
| Wholesale & events lead form receiver (webhook via ngrok) | `mokipops-lead-webhook.json` | HubSpot Forms |

Private data lives in `../contacts/` (git-ignored): `contacts.csv` from `build_contacts.py`,
`send-log.jsonl`, `leads.jsonl`, `suppress-domains.txt`, `unsubscribed.txt`.

---

## Part 1 — Social posting

One n8n workflow posts the day's slot from `social-queue.json` to the **MokiPops
Facebook page** and **@mokipops on Instagram** at **12:00 pm ET**, straight through
Meta's Graph API. No third-party scheduler, no per-post fee, no MCP.

```
GitHub Pages (queue + media)  ──▶  n8n (daily 12:00 ET)  ──▶  Facebook Page  (video / photo)
 social-queue.json                  Config → Fetch → Pick        Instagram      (reel / image)
 assets/social-library/*            → FB post → IG container → poll → publish → mark done
```

## What is in this folder

| File | Purpose |
|---|---|
| `mokipops-daily-post.json` | The n8n workflow. Import it as-is. |
| `build_queue.py` | Generates / extends `../social-queue.json` (rotation + caption bank + seasonal overrides). |
| `docker-compose.yml` | Runs n8n locally or on any VPS. |
| `.env.example` | The five values n8n needs. Copy to `.env`. |
| `verify_meta.sh` | Pre-flight: token scopes, page, IG id, every media URL live. |

Media lives in `../assets/social-library/` (19 proven assets, 83 MB) and is served
from `https://borngifted.github.io/mokipops-reel/assets/social-library/<key>.<mp4|jpg>`.
Each queue row also carries the old Blotato URL as `media_fallback_url`; those still
resolve today but should not be relied on.

## One-time setup (about 30 minutes, all in the MOKIPOPS Meta accounts)

### 1. Publish the queue and media
```bash
cd ~/Documents/MOKIPOPS/mokipops-reel-site
./publish.sh          # commits social-queue.json + assets/social-library/ and pushes to GitHub Pages
```
Wait a minute, then confirm `https://borngifted.github.io/mokipops-reel/social-queue.json` loads.

### 2. Create the Meta app and a permanent token
Do this logged in as an admin of the MokiPops page and its Business portfolio.

1. **developers.facebook.com → My Apps → Create App.** Use case *Other*, type **Business**,
   connect it to the MOKIPOPS business portfolio. Name it e.g. `MOKIPOPS Poster`.
2. In the app dashboard add the products **Facebook Login for Business** and
   **Instagram** (Instagram API with Facebook Login). Nothing needs configuring inside them.
3. **App settings → Basic:** add a Privacy Policy URL (the Shopify policy page works,
   e.g. `https://mokipops.com/policies/privacy-policy`), an app icon and a category, then
   flip the top toggle from **Development to Live**.
   Posts made while the app is in Development mode are only visible to people with a role
   on the app, so this step is not optional.
4. **business.facebook.com → Settings → Users → System users → Add.** Name `n8n-poster`,
   role *Admin*. Then **Add assets**: the MokiPops Page (full control) and the
   @mokipops Instagram account (full control).
5. On that system user click **Generate new token**, choose the app from step 1,
   token expiration **Never**, and tick:
   `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `publish_video`,
   `instagram_basic`, `instagram_content_publish`, `business_management`.
   Copy the token once; Meta will not show it again.

Alternative if you cannot use system users: Graph API Explorer → your app → User token
with the same permissions → `GET /me/accounts` → copy the MokiPops **page** access token.
That token expires in ~60 days unless you first exchange the user token for a long-lived
one, so the system-user route is the one to use for a hands-off schedule.

### 3. Fill in `.env` and verify
```bash
cd ~/Documents/MOKIPOPS/mokipops-reel-site/n8n
cp .env.example .env         # paste META_PAGE_TOKEN, set a random N8N_ENCRYPTION_KEY
./verify_meta.sh             # prints scopes, the page, and instagram_business_account.id
```
Put the printed Instagram id into `IG_USER_ID` in `.env`. Every media URL should show 200.
If `instagram_business_account` is missing, link the Instagram professional account to the
page in Meta Business Suite → Settings → Instagram, then re-run.

### 4. Run n8n and import the workflow
```bash
docker compose up -d
open http://localhost:5678
```
Create the owner account, then **Workflows → ⋯ → Import from file → `mokipops-daily-post.json`**.

### 5. Test, then activate
1. In `.env` set `DRY_RUN=true`, `docker compose up -d` again, open the workflow and click
   **Execute workflow**. It should fetch the queue, pick nothing (no slot today) or stop at
   the "Dry run" node.
2. Set `DRY_RUN=false` and `FORCE_POST_ID=<an id from social-queue.json>` to push one real
   post now. Check it on facebook.com/mokipops and instagram.com/mokipops, then clear
   `FORCE_POST_ID`.
3. Toggle the workflow **Active**. It fires every day at 12:00 pm ET from then on.

## Where to run it

Decision (Sep 30 2026): **fully local on this Mac.** It is already set to never sleep
(`pmset -g` → `sleep 0`); enable *Start Docker Desktop when you sign in* and the containers
restart on their own. The other options remain if that ever changes:

| Option | Cost | Notes |
|---|---|---|
| **n8n Cloud** (Starter) | ~$24/mo | Import the same JSON. No `$env` there: paste the values into the **Config** node instead of `.env`. |
| **Small VPS** (Hetzner / DigitalOcean / Railway) with this compose file | $5–8/mo | Set `N8N_SECURE_COOKIE=true` and put it behind HTTPS (`WEBHOOK_URL`, `N8N_HOST`). |
| This Mac, kept awake | $0 | `docker compose up -d` plus System Settings → prevent sleep. Fine for a trial week. |

## Day-to-day

* **Extend the calendar** (do this before the queue runs out on **Nov 30, 2026**):
  ```bash
  python3 n8n/build_queue.py 2026-12-01 2027-01-31   # appends the next window
  ./publish.sh
  ```
  Add a round to `ROUNDS` if the window is longer than 63 days, and put holiday hooks in
  `OVERRIDES`. Edit captions in `social-queue.json` directly any time; ids must stay unique.
* **Add a new asset**: drop a ≤90 s H.264 MP4 (9:16, ≥720 px wide) or JPG into
  `assets/social-library/`, add it to `ASSETS` and `CAPTIONS` in `build_queue.py`, rebuild.
  New video of real people (kitchen, pop-ups, kids) is the highest-performing content by 5–8×.
* **Skip a day**: delete that row from `social-queue.json` and publish.
* **Re-post one slot**: set `FORCE_POST_ID` in `.env`, execute once, clear it.
* **Check what happened**: n8n → Executions. Each run ends in *Mark posted* with the
  Facebook and Instagram ids, or in *Dry run*, or with zero items ("Nothing to post").

## How the workflow protects itself

* Idempotent: posted ids are kept in the workflow's static data, so a re-run never
  double-posts a day. The Facebook id is recorded the moment Facebook accepts the upload,
  before Instagram starts.
* Facebook failures do not block Instagram (the FB nodes continue on error; the error text
  ends up in *Mark posted*).
* Instagram reels are polled every 20 s for up to ~13 minutes; `ERROR`/`EXPIRED` containers
  fail the run loudly instead of publishing nothing.
* One post per day keeps well under Meta's limits (Instagram allows 100 API posts / 24 h;
  the old 4-a-day bulk queue is what tripped Facebook's spam filter in July).

## Fallbacks if you would rather not touch the Meta developer console

* **Metricool** is already connected to this Claude setup as an MCP server (authentication
  pending) and has a scheduling API on its Advanced plan; n8n can call it from the same
  queue with an HTTP node.
* **Postiz** (open-source, self-hosted) and **Late** / **Ayrshare** (paid APIs) also accept
  the same `{media_url, caption, date}` rows.
Direct Graph API is still the recommendation: it is free and has no middleman that can
disappear the way Blotato did.

---

## Part 2 — Funnel email without HubSpot

```bash
python3 n8n/build_contacts.py        # → contacts/contacts.csv  (buyers 50 · b2b 411 active / 28 suppressed · lead 140 held)
```
Segments: `buyers` = Shopify customers with an order (was Previous Buyers); `b2b` = HubSpot
contacts with lifecycle *opportunity* or a company (was B2B Prospects + Warm Opportunities);
`lead` = everything else, never mailed. Status column: `active | suppressed | unsubscribed`.

Mailbox: an **SMTP credential in n8n named `MOKIPOPS mail (SMTP)`** — moreflavor@mokipops.com,
`smtp.office365.com:587`, STARTTLS, app password. Turn on *Authenticated SMTP* for the mailbox
in the Microsoft 365 admin center first, and enable DKIM for mokipops.com in the Defender
portal (add the two selector CNAMEs at GoDaddy) so mail is aligned SPF+DKIM from the real domain.

Run: set `FUNNEL_CAMPAIGN` and `FUNNEL_DAILY_CAP` in `.env`, `docker compose up -d`, open the
workflow, **Execute workflow**. The workflow remembers who received each campaign (static
data) and appends every attempt to `contacts/send-log.jsonl`. Templates come from
`docs/funnel-<a1|a2|b1|b2|b3>-template.html`; HubSpot's HubL tags are stripped at send time and
the unsubscribe link becomes a `mailto:` to moreflavor@. Put unsubscribes in
`contacts/unsubscribed.txt` and rebuild.

Status: A1 + B1 went out Aug 26 2026 via HubSpot. **Next: A2 + B2 the same day, B3 a week later.**
Warm-up: ≤40/day for the first week from this mailbox.

### Manual path (no n8n): `mailer.py`
`python3 n8n/mailer.py --campaign V --to you@x.com --name You` · `--campaign V --segment b2b --limit 40` ·
`--video` on any campaign · `--dry-run` (previews in `contacts/outbox/`) · `--list`. Reads `SMTP_*` from
`.env`, writes the same `contacts/send-log.jsonl`, skips anyone already logged for that campaign.
Video block = `<video autoplay muted loop>` (Apple/iOS Mail) with `assets/funnel/funnel-loop.gif` as the
fallback image and `funnel-poster.jpg` as poster; all wrapped in a link to `video.html`. The runbook page
(`#manual`) also has rich-copy buttons for pasting a finished email into any mail app.

## Part 3 — Wholesale & events form

`wholesale.html` now has a native form. It POSTs JSON to
`https://<NGROK_DOMAIN>/webhook/mokipops-lead`; the ngrok service in `docker-compose.yml`
(`--profile public`) tunnels only `/webhook/*` to n8n (`ngrok-policy.yml`). The workflow
validates (honeypot + email regex), appends to `contacts/leads.jsonl`, emails
`LEAD_NOTIFY_TO` with Reply-To set to the lead, and answers `{ok:true}` with CORS headers.
Set `const LEAD_ENDPOINT` in `wholesale.html` once the domain exists; while it is empty the
form falls back to a pre-filled `mailto:`.

## Test evidence (Sep 30 2026, n8n 2.41.4, mock Graph API + mock SMTP)
- Daily post: video path (FB /videos → IG REELS container → 3 polls → publish), image path,
  and no-slot day all end in *Mark posted* / clean exit.
- Funnel batch: cap 2 → 2 emails with HTML + text parts and Reply-To; re-run continues with
  the next 2; send-log appended.
- Lead hook: valid POST → 200 + CORS header + leads.jsonl + alert email; honeypot → 400.

Note: n8n 2.x hides the *Execute Command* node by default; the compose file sets
`NODES_EXCLUDE=[]` so the two append-to-file steps work.
