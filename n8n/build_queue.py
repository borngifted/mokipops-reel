#!/usr/bin/env python3
"""Build social-queue.json — the MOKIPOPS daily posting calendar that the n8n
workflow (n8n/mokipops-daily-post.json) reads from GitHub Pages every day.

  python3 n8n/build_queue.py                       # regenerate the default window
  python3 n8n/build_queue.py 2026-12-01 2027-01-31 # extend into a new window (appends)

Rules baked in (from the Jul 13 - Aug 20 Blotato run, 150 posts / 27.9K views):
  * 1 post/day at 12:00 ET, cross-posted to Facebook + Instagram. Four-a-day
    tripped Facebook's 35-posts/24h cap and burned the library in two weeks.
  * Video of real people (facility, kitchen, pop-ups, kids) did ~1.6-2.8K views;
    designed stills and award clips ~300. Tier A assets get 4 slots per window,
    tier B 3, tier C 1.
  * Every slot uses a *different* caption per round so repeats don't read as
    copy-paste. Date-specific overrides layer in seasonal hooks.

Output rows are what the workflow consumes:
  {id, date, time, tz, key, media_type, media_url, media_fallback_url, caption}
"""
import json, sys, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "social-queue.json"
LIBRARY = ROOT / "social-library.json"
LEGACY = ROOT / "docs" / "post-library.json"   # Blotato file names -> fallback URLs

PAGES = "https://borngifted.github.io/mokipops-reel/assets/social-library/"
TZ = "America/New_York"
SLOT = "12:00"

# ---------------------------------------------------------------- library --
# key: (tier, media_type, theme)
ASSETS = {
    "facility":     ("A", "video", "new manufacturing facility walk-in"),
    "kitchen":      ("A", "video", "kitchen BTS, pops packed by hand"),
    "popup":        ("A", "video", "pop-up day with the crew"),
    "kids":         ("A", "video", "kids' reactions"),
    "firstbite":    ("A", "video", "first-bite smile"),
    "beltline":     ("A", "video", "cart on the Atlanta BeltLine"),
    "community":    ("A", "video", "community love / crowd"),
    "sunshine":     ("A", "video", "customer enjoying a pop in the sun"),
    "grabgo":       ("A", "video", "wrapped pops, grab-and-go"),
    "freezer":      ("A", "video", "stocked freezer / order online"),
    "hawks_screen": ("B", "video", "on the big screen at State Farm Arena"),
    "hawks_thanks": ("B", "video", "thank-you to Hawks + Chase"),
    "bigscreen":    ("B", "video", "big-screen feature, kid-founded"),
    "founders":     ("B", "video", "founders telling the story"),
    "blueberries":  ("B", "video", "'this is real blueberries' reaction"),
    "basil":        ("B", "video", "Basil Lemonade made from scratch"),
    "dessertwars":  ("B", "video", "People's Choice #1, Dessert Wars Atlanta"),
    "hotday":       ("C", "image", "designed still: good for a hot day"),
    "nodairy":      ("C", "image", "designed still: no dairy / no dyes / no refined sugar"),
}

# ---------------------------------------------------------------- captions --
# One list per asset; index = round (0..3). Round 0 = early October, 3 = late Nov.
CAPTIONS = {
    "facility": [
        "New month, new kitchen. 🧡 Our manufacturing facility is up and running — bigger batches, same rule: real whole fruit in every pop. #mokipops #atlanta #realfruit #newchapter",
        "Behind these doors: fruit, freezers, and a family that's been at this since 2016. 🏭🧡 Retailers, this is where your cases come from. #mokipops #madeinatlanta #wholesale #realfruit",
        "From a home freezer to this. 🥹 Every square foot of our new facility was earned one pop at a time. Thank you, Atlanta. #mokipops #atlanta #familybusiness #kidfounded",
        "Holiday orders are made right here. 🎁🧡 Stocking up for the season? mokipops.com — or DM us for wholesale. #mokipops #shopsmall #atlanta #realfruit",
    ],
    "kitchen": [
        "Inside the MOKIPOPS kitchen 🧤🍓 Real fruit in, bliss out. Every single pop is packed by hand in Atlanta. #mokipops #behindthescenes #realfruit #atlanta",
        "No shortcuts in here. Whole strawberries, whole mango, whole hands. 🍓🥭 This is what clean-label actually looks like. #mokipops #cleanlabel #behindthescenes #atlanta",
        "Fall in the kitchen still means fruit — just more of it. 🍁🧡 Stocking freezers across Atlanta before the holidays. #mokipops #madeinatlanta #realfruit #bts",
        "Hand-packed, small-batch, Atlanta-made. 🧡 That's the whole recipe. #mokipops #handmade #cleanlabel #atlanta",
    ],
    "popup": [
        "Pop-up day with the crew ☀️ Nothing beats handing someone their first MOKIPOPS. Find us around Atlanta + at mokipops.com 🍧 #mokipops #atlanta #popup #fruitpops",
        "Atlanta 'fall' is still pop weather. 😅🧡 Catch the cart at events all October — follow along for the next stop. #mokipops #atlanta #popup #realfruit",
        "Want MOKIPOPS at your event, school, or game day? 🎉 We bring the cart, the crew, and the fruit. DM us. #mokipops #atlantaevents #popup #kidfounded",
        "Every pop-up starts with a kid asking 'what flavor is THAT?' 🥭🍓 Real fruit, no dyes — and the answer is usually mango. #mokipops #atlanta #popup #realfruit",
    ],
    "kids": [
        "Little pop lovers, big smiles 🥹🧡 This is exactly why we make them. #mokipops #realfruit #kidsapproved #atlanta",
        "Parents: a treat with no dyes, no dairy, no refined sugar — and they still ask for seconds. 🧡 #mokipops #kidsapproved #cleanlabel #nodyes",
        "The taste-test panel has spoken. 😄🍓 Real fruit wins every time. #mokipops #kidsapproved #realfruit #atlanta",
        "After-school snack, sorted. 🎒🧡 Fruit on a stick, made in Atlanta. Stock the freezer at mokipops.com #mokipops #kidsapproved #snacktime #realfruit",
    ],
    "firstbite": [
        "That first-bite smile gets us every time 😄🧡 Thanks for the love! #mokipops #fruitpops #atlanta #realfruit",
        "Wait for it… 😏🍓 The moment someone realizes it's actually real fruit. #mokipops #realfruit #firstbite #atlanta",
        "First bites never get old. 🧡 Bring a friend who hasn't tried one yet — you know who. #mokipops #atlanta #fruitpops #shareable",
        "Holiday hack: a MOKIPOPS after the big meal. Light, cold, real fruit. 🍁🧡 #mokipops #realfruit #dessert #atlanta",
    ],
    "beltline": [
        "Spotted on the BeltLine! 🛴🧡 Thanks for stopping by the cart — see you out there, Atlanta. #mokipops #atlbeltline #atlanta #fruitpops",
        "BeltLine walks hit different with a pop in hand. 🍓🚶 Look for the orange cart. #mokipops #atlbeltline #atlanta #realfruit",
        "Cool mornings, warm afternoons, cart's out. 🍁🧡 Atlanta fall is our favorite pop-up season. #mokipops #atlbeltline #atlanta #popup",
        "Some of our best regulars found us on the BeltLine. 🧡 Now they order by the box at mokipops.com #mokipops #atlbeltline #atlanta #shoplocal",
    ],
    "community": [
        "Community love like this keeps us going 🧡 Thank you, Atlanta, for cheering on our kid-founded crew! #mokipops #community #atlanta #kidfounded",
        "This city shows up. 🧡 Every event, every line, every 'we saw you on the Hawks screen!' — thank you. #mokipops #atlanta #community #blackowned",
        "Built by a family, carried by a community. 🧡 #mokipops #atlanta #community #familybusiness",
        "Grateful for every single one of you this season. 🍁🧡 Atlanta made MOKIPOPS what it is. #mokipops #thankful #atlanta #community",
    ],
    "sunshine": [
        "Sunshine + a MOKIPOPS = the whole vibe ☀️🍓 Thanks for sharing the love! #mokipops #realfruit #fruitpops #atlanta",
        "Golden-hour pop. ☀️🧡 Tag us in yours — we repost our favorites. #mokipops #fruitpops #atlanta #realfruit",
        "Still 75° in Atlanta? Still pop season. 😎🍓 #mokipops #atlanta #realfruit #fallinatlanta",
        "Real fruit, real sunshine, real smiles. 🧡 That's the brand. #mokipops #realfruit #atlanta #fruitpops",
    ],
    "grabgo": [
        "Grab-and-go bliss 🍓🌿 Real whole fruit, wrapped and ready — zero artificial anything. mokipops.com #mokipops #cleanlabel #realfruit #fruitpops",
        "Read the label. That's it. That's the post. 🍓🥭🫐 #mokipops #cleanlabel #realfruit #nodyes",
        "Store owners: these fly out of a grab-and-go freezer. 🧊🧡 Case of 24, find us on Faire or DM for wholesale. #mokipops #wholesale #retail #realfruit",
        "Lunchbox, gym bag, dessert table — wrapped and ready for all of it. 🧡 #mokipops #realfruit #snack #atlanta",
    ],
    "freezer": [
        "Freezer's stocked and ready 🧊 Real-fruit pops, made in Atlanta — order yours at mokipops.com 🧡 #mokipops #shopsmall #atlanta #fruitpops",
        "The most popular thing in this freezer is the mango. Every time. 🥭🧡 mokipops.com #mokipops #mango #realfruit #atlanta",
        "Your freezer, but make it real fruit. 🧊🍓 Boxes ship from Atlanta — mokipops.com #mokipops #cleanlabel #shopsmall #fruitpops",
        "Holiday hosting? A stocked MOKIPOPS freezer ends every argument about dessert. 🎁🧡 mokipops.com #mokipops #holidays #realfruit #atlanta",
    ],
    "hawks_screen": [
        "Up on the big screen at State Farm Arena! 🏀 Grateful to the Atlanta Hawks and Chase for supporting Black-owned businesses 🧡 #mokipops #atlanta #atlhawks #blackowned",
        "Hawks season is BACK. 🏀🧡 Still can't believe we were up on that screen. Let's go, Atlanta! #mokipops #atlhawks #atlanta #kidfounded",
        "From a kid's idea to the State Farm Arena jumbotron. 🏀 Thank you @atlhawks + @chase. 🧡 #mokipops #atlhawks #blackowned #atlanta",
    ],
    "hawks_thanks": [
        "Thank you @atlhawks and @chase for the support and recognition 🏀🧡 Proud to be an Atlanta-grown, family-run business. #mokipops #atlhawks #atlanta #blackowned",
        "Recognition like this means the most when it comes from home. 🏀🧡 Thank you, Atlanta Hawks + Chase. #mokipops #atlhawks #atlanta #familybusiness",
        "A small family business, backed by the home team. 🧡🏀 Forever grateful. #mokipops #atlhawks #blackowned #atlanta",
    ],
    "bigscreen": [
        "Catch us on the big screen! 🤩 Kid-founded, Atlanta-grown — and just getting started 🧡 #mokipops #atlanta #familyowned #fruitpops",
        "Big screen, small business, real fruit. 🎬🧡 #mokipops #kidfounded #atlanta #fruitpops",
        "Play it back one more time. 😭🧡 Kid-founded in 2016, on the big screen in 2026. #mokipops #kidfounded #atlanta #familyowned",
    ],
    "founders": [
        "Our founders, telling the MOKIPOPS story 🎤 Kid-founded, family-run, Atlanta-grown since 2016. #mokipops #kidfounded #familyowned #atlanta",
        "It started with a kid, a blender, and a freezer. 🧡 Ten years later we're still a family — just with a bigger kitchen. #mokipops #founders #kidfounded #atlanta",
        "Why real fruit? Because that's what we wanted for our own kids. 🍓🧡 That's the whole origin story. #mokipops #founders #cleanlabel #familybusiness",
    ],
    "blueberries": [
        "\"Oh THIS is real blueberries!\" 🫐 Yes it is — real whole fruit, nothing artificial, every time. #mokipops #realfruit #blueberry #cleanlabel",
        "The reaction when you can actually see the fruit. 🫐😂 No purple dye needed. #mokipops #realfruit #blueberry #nodyes",
        "Blueberries so real you can count them. 🫐🧡 #mokipops #realfruit #blueberry #atlanta",
    ],
    "basil": [
        "Basil Lemonade, from scratch 🌿🍋 Fresh basil, real lemon, and nothing you can't pronounce. #mokipops #basillemonade #cleanlabel #realfruit",
        "Yes, that's real basil. 🌿 Grown-up flavor, kid-approved ingredients. #mokipops #basillemonade #cleanlabel #atlanta",
        "The flavor people don't expect — then order again. 🌿🍋 Basil Lemonade, made in Atlanta. #mokipops #basillemonade #realfruit #atlanta",
    ],
    "dessertwars": [
        "People's Choice, baby! 🏆 MOKIPOPS voted #1 at Dessert Wars Atlanta. Thank you for every single vote — this one's yours, Atlanta 🧡 #mokipops #dessertwars #atlanta #peopleschoice",
        "Still the People's Choice. 🏆🧡 Atlanta picked real fruit over everything else at Dessert Wars — we'll never forget it. #mokipops #dessertwars #atlanta #realfruit",
        "Award-winning, kid-founded, Atlanta-made. 🏆 Looking for a dessert that wins the table this holiday? mokipops.com #mokipops #dessertwars #holidays #atlanta",
    ],
    "hotday": [
        "Good for a hot day, good all around ☀️ mokipops.com #mokipops #cleanlabel #fruitpops #atlanta",
    ],
    "nodairy": [
        "No dairy. No dyes. No refined sugar. Just fruit, done right 🧡 #mokipops #cleanlabel #fruitpops #atlanta",
    ],
}

# ---------------------------------------------------------------- rotation --
# Hand-ordered rounds so themes alternate and no asset repeats within ~10 days.
ROUNDS = [
    ["facility", "kids", "dessertwars", "kitchen", "sunshine", "hawks_screen", "popup",
     "nodairy", "firstbite", "beltline", "founders", "grabgo", "blueberries", "community",
     "basil", "freezer", "hawks_thanks", "hotday", "bigscreen"],
    ["kitchen", "hawks_screen", "popup", "blueberries", "hawks_thanks", "founders", "facility",
     "grabgo", "dessertwars", "sunshine", "freezer", "kids", "community", "basil", "firstbite",
     "bigscreen", "beltline"],
    ["popup", "freezer", "kids", "facility", "basil", "firstbite", "hawks_screen", "kitchen",
     "community", "dessertwars", "grabgo", "founders", "sunshine", "blueberries", "beltline",
     "hawks_thanks", "bigscreen"],
    ["kitchen", "firstbite", "popup", "community", "freezer", "founders", "grabgo", "kids",
     "beltline", "sunshine"],
]

# Date-specific hooks. key=None keeps whatever the rotation put there.
OVERRIDES = {
    "2026-10-21": ("hawks_screen", CAPTIONS["hawks_screen"][1]),           # NBA tip-off week
    "2026-10-31": ("kids", "Happy Halloween from the MOKIPOPS crew 🎃🧡 Real fruit, no dyes — the treat parents don't have to think twice about. #mokipops #halloween #nodyes #kidsapproved"),
    "2026-11-26": ("community", "Happy Thanksgiving, Atlanta 🍁🧡 From our family to yours — thank you for a year we'll never forget. #mokipops #thanksgiving #atlanta #grateful"),
    "2026-11-27": ("freezer", "Skip the mall. Stock the freezer. 🧊🧡 Real-fruit pops ship from Atlanta all weekend — mokipops.com #mokipops #blackfriday #shopsmall #realfruit"),
    "2026-11-28": ("founders", "Small Business Saturday 🧡 Kid-founded in 2016, family-run ever since, Atlanta-made every day. Shop small with us: mokipops.com #mokipops #smallbusinesssaturday #shopsmall #atlanta"),
}


def daterange(start, end):
    d = start
    while d <= end:
        yield d
        d += dt.timedelta(days=1)


def build(start, end):
    legacy = json.load(open(LEGACY))
    fallback = {k: legacy["base"] + fb for k, fb, ig, v in legacy["library"]}
    order = [k for r in ROUNDS for k in r]
    round_of = []
    for i, r in enumerate(ROUNDS):
        round_of += [i] * len(r)

    rows, used = [], {}
    for n, day in enumerate(daterange(start, end)):
        if n >= len(order):
            raise SystemExit(f"window longer than rotation ({len(order)} days) — add a round")
        key, rnd = order[n], round_of[n]
        ds = day.isoformat()
        caption = CAPTIONS[key][min(rnd, len(CAPTIONS[key]) - 1)]
        if ds in OVERRIDES:
            okey, ocap = OVERRIDES[ds]
            key, caption = (okey or key), ocap
        used[key] = used.get(key, 0) + 1
        tier, mtype, _ = ASSETS[key]
        ext = "mp4" if mtype == "video" else "jpg"
        rows.append({
            "id": f"{ds}-{key}",
            "date": ds,
            "time": SLOT,
            "tz": TZ,
            "key": key,
            "tier": tier,
            "media_type": mtype,
            "media_url": f"{PAGES}{key}.{ext}",
            "media_fallback_url": fallback[key],
            "caption": caption,
            "platforms": ["facebook", "instagram"],
        })
    return rows, used


def main():
    if len(sys.argv) == 3:
        start, end = (dt.date.fromisoformat(a) for a in sys.argv[1:3])
    else:
        start, end = dt.date(2026, 10, 1), dt.date(2026, 11, 30)
    rows, used = build(start, end)

    existing = []
    if QUEUE.exists():
        existing = [r for r in json.load(open(QUEUE))["posts"] if r["date"] < start.isoformat()]
    posts = existing + rows
    json.dump({
        "_about": "Daily MOKIPOPS cross-post queue read by n8n/mokipops-daily-post.json. Regenerate with n8n/build_queue.py; edit captions freely, keep ids unique.",
        "generated": dt.date.today().isoformat(),
        "timezone": TZ,
        "posts": posts,
    }, open(QUEUE, "w"), indent=1, ensure_ascii=False)

    legacy = json.load(open(LEGACY))
    lib = []
    for k, fb, ig, v in legacy["library"]:
        tier, mtype, theme = ASSETS[k]
        ext = "mp4" if mtype == "video" else "jpg"
        lib.append({"key": k, "tier": tier, "media_type": mtype, "theme": theme,
                    "file": f"assets/social-library/{k}.{ext}",
                    "url": f"{PAGES}{k}.{ext}", "fallback_url": legacy["base"] + fb,
                    "captions": CAPTIONS[k]})
    json.dump({"_about": "The 19 proven MOKIPOPS social assets (from the Jul-Aug 2026 run) with tiers and caption variants.",
               "assets": lib}, open(LIBRARY, "w"), indent=1, ensure_ascii=False)

    print(f"{len(rows)} slots {start} → {end}; total in queue: {len(posts)}")
    for k, n in sorted(used.items(), key=lambda kv: -kv[1]):
        print(f"  {k:13s} x{n} ({ASSETS[k][0]})")


if __name__ == "__main__":
    main()
