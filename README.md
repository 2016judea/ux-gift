# UX gift — sweeps 1 and 2 (2026-10-06)

A free UX bug report emailed to a small business about its own website, with Aidan's $100 / $500 upsell.
Sent drafts are logged in `ledger.csv`; everything else is a draft. Skill: `~/.claude/skills/ux-gift-sweep/`.

Audited 310 sites on headless WebKit (iPhone 13) and Chromium (Pixel 5); 10 had a big, reproduced bug and got a draft. Ranked best-first:

1. **Cafe Latte (Saint Paul)** (Admin@cafelatte.com; prior: sent_log 2026-05-16; SENT (ledger.csv)) — 5,233 reviews, takes orders, catering and gift cards online; six dead links incl. order online — On your homepage there is a bug where the links at the bottom of the page are broken. "order online", "menu", "catering", "events", "about" and "contact" all go to a "page not found" screen. → `drafts/cafe-latte.txt`
2. **Pompei (Chicago, Little Italy)** (info@pompeiusa.com; prior: sent_log 2026-05-16; SENT (ledger.csv)) — 2,923 reviews, two locations, online ordering + catering + banquets; whole site renders as a shrunk desktop page on phones — On a phone your whole site shows up as the desktop version shrunk down to fit the screen. The hours bar, the menu and the Order Online button are all tiny, so people have to pinch-zoom to read anything or to order. → `drafts/pompei.txt`
3. **Hell's Kitchen (Minneapolis)** (talktous@hellskitcheninc.com; prior: sent_log 2026-05-16; SENT (ledger.csv)) — 7,188 reviews, sells retail + ships online; the Day Menu PDF button is dead — On your Day Menu page there is a bug where the "DAY MENU PDF" button goes to a "page not found" screen. → `drafts/hells-kitchen.txt`
4. **Peacefood (Upper West Side)** (hello@peacefoodnyc.com; prior: sent_log 2026-05-16; SENT (ledger.csv)) — 1,662 reviews, sells custom cakes; the custom-cake link is dead — On your homepage there is a bug where the "bakery section" link for custom cake ordering goes to a "page not found" screen. → `drafts/peacefood-uws.txt`
5. **Joe's on Weed St. (Chicago)** (reservations@joesbar.com; prior: sent_log 2026-05-16; SENT (ledger.csv)) — 1,533 reviews, sells show tickets + party bookings; a TICKETS button is dead for a 10/23 show — On your homepage there is a bug where the TICKETS button for Austin Snell (Friday 10/23) goes to a "page not found" screen instead of TicketWeb. → `drafts/joes-on-weed-st.txt`
6. **One if by Land, Two if by Sea (New York)** (info@oneifbyland.com; prior: sent_log 2026-05-16; SENT (ledger.csv)) — 1,307 reviews, tasting-menu restaurant on OpenTable/Resy + gift cards; menus page breaks on iPhone — On your Menus page there is a bug on iPhone where the page slides sideways. The menu cards hang off the right edge of the screen and the ones on the left get cut off. → `drafts/one-if-by-land.txt`
7. **Filomena Ristorante (Washington DC)** (info@filomena.com; prior: uncontacted) — 5,782 reviews, sells gift cards online; gift card + all four menu buttons go to a dead staging site — On your homepage there is a bug where the "Gift Cards" link at the bottom of the page goes to an error screen that says "Site is not available". Same on your Menu page: the Dinner, Lunch, Desserts and Wine buttons all go to that error screen. → `drafts/filomena.txt`
8. **Reggies (Chicago)** (Info@reggieslive.com; prior: uncontacted) — 4,863 reviews, live-music venue selling show tickets; on a phone the whole site is cut off on the right — On a phone your site is cut off on the right. The logo, the menu and the show listings run off the edge of the screen, and people have to drag the page sideways to read what's playing. → `drafts/reggies-chicago.txt`
9. **Rasika (Penn Quarter, Washington DC)** (rasika@rasikarestaurant.com; prior: uncontacted) — 3,946 reviews, takes reservations and sells gift cards; Wine List and Bar Menu buttons are dead — On your Penn Quarter menu page there is a bug where the "Wine List" and "Bar Menu" buttons at the bottom both go to a "page not found" screen. → `drafts/rasika.txt`
10. **Andina (Portland)** (info@andinarestaurant.com; prior: uncontacted) — 3,537 reviews, books tables, weddings and private dining and sells gift cards; the footer's Sunday Brunch link is dead — On your site there is a bug where the "sunday brunch" link at the bottom of every page goes to a "page not found" screen. → `drafts/andina.txt`

## Pipeline

1. `scripts/pool.py` — leads → chain/own-domain/MX filter → homepage fetch → `data/pool.csv` ranked
2. `scripts/sweep.sh 150 10` — `mobile-ui-audit/audit.py --links --hop` in 10 shards → `data/audit/`
3. `scripts/analyze.py` — keep only big findings → `data/big.json`
4. verify each by hand + `scripts/shoot.py` proof PNGs → `data/verified.json`
5. `scripts/build_drafts.py` → `drafts/`, `candidates.csv`, this README
