# UX gift — sweep 1 (2026-10-06)

A free UX bug report emailed to a small business about its own website, with Aidan's $100 / $500 upsell.
Drafts only — nothing has been sent. Skill: `~/.claude/skills/ux-gift-sweep/`.

Audited 150 sites on headless WebKit (iPhone 13) and Chromium (Pixel 5); 5 had a big, reproduced bug and got a draft. Ranked best-first:

1. **Cafe Latte (Saint Paul)** (Admin@cafelatte.com; prior: sent_log 2026-05-16) — 5,233 reviews, takes orders, catering and gift cards online; six dead links incl. order online — On your homepage there is a bug where the links at the bottom of the page are broken. "order online", "menu", "catering", "events", "about" and "contact" all go to a "page not found" screen. → `drafts/cafe-latte.txt`
2. **Hell's Kitchen (Minneapolis)** (talktous@hellskitcheninc.com; prior: sent_log 2026-05-16) — 7,188 reviews, sells retail + ships online; the Day Menu PDF button is dead — On your Day Menu page there is a bug where the "DAY MENU PDF" button goes to a "page not found" screen. → `drafts/hells-kitchen.txt`
3. **Peacefood (Upper West Side)** (hello@peacefoodnyc.com; prior: sent_log 2026-05-16) — 1,662 reviews, sells custom cakes; the custom-cake link is dead — On your homepage there is a bug where the "bakery section" link for custom cake ordering goes to a "page not found" screen. → `drafts/peacefood-uws.txt`
4. **Joe's on Weed St. (Chicago)** (reservations@joesbar.com; prior: sent_log 2026-05-16) — 1,533 reviews, sells show tickets + party bookings; a TICKETS button is dead for a 10/23 show — On your homepage there is a bug where the TICKETS button for Austin Snell (Friday 10/23) goes to a "page not found" screen instead of TicketWeb. → `drafts/joes-on-weed-st.txt`
5. **One if by Land, Two if by Sea (New York)** (info@oneifbyland.com; prior: sent_log 2026-05-16) — 1,307 reviews, tasting-menu restaurant on OpenTable/Resy + gift cards; menus page breaks on iPhone — On your Menus page there is a bug on iPhone where the page slides sideways. The menu cards hang off the right edge of the screen and the ones on the left get cut off. → `drafts/one-if-by-land.txt`

## Pipeline

1. `scripts/pool.py` — leads → chain/own-domain/MX filter → homepage fetch → `data/pool.csv` ranked
2. `scripts/sweep.sh 150 10` — `mobile-ui-audit/audit.py --links --hop` in 10 shards → `data/audit/`
3. `scripts/analyze.py` — keep only big findings → `data/big.json`
4. verify each by hand + `scripts/shoot.py` proof PNGs → `data/verified.json`
5. `scripts/build_drafts.py` → `drafts/`, `candidates.csv`, this README
