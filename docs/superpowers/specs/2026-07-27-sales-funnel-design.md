# MOKIPOPS Sales Funnel — Design Spec (2026-07-27)

Approved by user 2026-07-27. One funnel, two lanes (B2B wholesale + DTC repeat buyers), powered by HubSpot data (portal 51058060) now syncing two-way with the live Shopify store (mokipops.com / 547ac9-2).

## Segments (HubSpot lists)
| List | Definition | Purpose |
|---|---|---|
| Previous Buyers | Contacts with a purchase (lifecycle = customer, or associated Shopify order) | Track A emails |
| Warm Opportunities | Lifecycle stage = opportunity (33 as of today) | Track B, priority calls |
| B2B Prospects | Company name known AND not customer AND email known | Track B emails |
| Suppression — Do Not Market | Vendor/bot/no-reply addresses: docusign.net, venmo.com, uber.com, adobe*, sba.gov, storebotmail.joonix.net, hubspot samples, inscrlab, ilovemyemail, accaps.top, gibberish-bot signups | Excluded from every send |

Free-tier limit: 5 active lists — this design uses exactly 4 active (suppression may be static).

## Capture: wholesale.html on borngifted.github.io/mokipops-reel
Same design system as calls.html. Sections: hero (wholesale pitch), confirmed pricing ($53.50/case-24 ≈ $2.23/pop; $46/activation case-25 = $1.84/pop; distributor chain $0.68–0.80 → $0.95–1.00 → MSRP $1.49–2.49; pallet = 300 cases), Waymo case study (120 cases / 3,000 pops / $5,520), flavor lineup, event terms (50% deposit, balance +3 business days, staffed cart), embedded HubSpot form (firstname, email, phone, company, interest dropdown: Wholesale / Event / Just pops), Faire link. Form submissions create HubSpot contacts.

## Email sequences (HubSpot marketing email — created as DRAFTS, user approves every send)
Track A — Previous Buyers:
- A1 "New flavors since your last pop" — reorder nudge → mokipops.com
- A2 "Bring MOKIPOPS to your people" — case offer, bridges DTC → wholesale, links landing page

Track B — B2B Prospects + Warm Opportunities:
- B1 Wholesale intro — margin math, pricing table, landing page CTA
- B2 Event/activation offer — Waymo case study, $46 case, staffed cart, deposit terms
- B3 Last touch — short, offers a call, links landing page

Cadence (manual on free tier): B1 day 0 → B2 day 5 → B3 day 12. A1 day 0 → A2 day 7. ~2,000 sends/mo available; full base ≈ 600 net of suppression.

## Phone lane
calls.html remains the outbound arm (no-email contacts + email non-responders). Script close adds the landing page URL. Outcomes logged via mark-as-called + notes; shared via calls-log.json.

## Conversion + tracking
DTC → mokipops.com. Wholesale reorder → Faire (faire.com/apply/r/gf4mdp8kxd). Activations → invoice, 50% deposit. Health = HubSpot email opens/clicks, form submissions, list growth, new opportunities, call-list coverage.

## Out of scope
Automated workflows (paid tier), paid ads, SMS.
