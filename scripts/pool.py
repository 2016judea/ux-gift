#!/usr/bin/env python
"""Stage 1: build the candidate pool and rank it by likelihood to pay.

Reads the bricks lead files, drops chains and dead sites, fetches each homepage
once, and scores: reviews, own domain, and whether the site takes money or
bookings (ordering / booking / shop platforms linked or embedded).

    python scripts/pool.py            -> data/pool.csv (every live candidate, ranked)
"""
from __future__ import annotations

import csv
import glob
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

import requests

BRICKS = Path.home() / "Desktop/bricks/data"
OUT = Path(__file__).resolve().parent.parent / "data"

SOURCES = ["leads.csv", "leads_hair_validated.csv", "leads_spa_validated.csv"]

# Platform -> label. Order matters only for the label we print.
MONEY = [
    (r"toasttab\.com", "Toast ordering"), (r"order\.online|doordash\.com/store", "DoorDash storefront"),
    (r"chownow\.com", "ChowNow ordering"), (r"\.olo\.com|olo\.com/", "Olo ordering"),
    (r"square\.site|squareup\.com|squarespace-commerce|order\.square", "Square"),
    (r"clover\.com/online-ordering|clover\.com/order", "Clover ordering"),
    (r"menufy\.com|beyondmenu|popmenu\.com|bentobox|getbento", "online ordering"),
    (r"opentable\.com", "OpenTable reservations"), (r"resy\.com", "Resy reservations"),
    (r"exploretock\.com|tock\.com", "Tock"), (r"sevenrooms\.com", "SevenRooms"), (r"yelp\.com/reservations", "Yelp reservations"),
    (r"vagaro\.com", "Vagaro booking"), (r"booksy\.com", "Booksy booking"), (r"glossgenius\.com", "GlossGenius booking"),
    (r"fresha\.com", "Fresha booking"), (r"mindbodyonline\.com|mindbody\.io|healcode", "Mindbody booking"),
    (r"schedulicity\.com", "Schedulicity booking"), (r"styleseat\.com", "StyleSeat booking"),
    (r"boulevard\.io|joinblvd\.com", "Boulevard booking"), (r"meevo|millenniumsystems|salonbiz|zenoti\.com", "salon booking"),
    (r"acuityscheduling\.com|calendly\.com|setmore\.com|squareup\.com/appointments", "appointment booking"),
    (r"cdn\.shopify\.com|myshopify\.com", "Shopify store"), (r"woocommerce", "WooCommerce store"),
    (r"ecwid\.com", "Ecwid store"), (r"giftup\.app|gift-?cards?|giftcard", "gift cards"),
]
CTA = re.compile(r">\s*(order online|order now|book now|book online|book an appointment|reserve|reservations|shop now|buy gift card|gift cards?)\s*<", re.I)

CHAIN_WORDS = re.compile(
    r"starbucks|mcdonald|chipotle|subway|dunkin|panera|cold stone|taco bell|wendy|burger king|domino|pizza hut|papa john|"
    r"great clips|supercuts|sport clips|fantastic sams|regis|ulta|massage envy|hand ?& ?stone|european wax|drybar|"
    r"buffalo wild|applebee|chili'?s|olive garden|jimmy john|potbelly|noodles & co|qdoba|five guys|shake shack|"
    r"caribou|biggby|scooter'?s|tropical smoothie|smoothie king|jersey mike|firehouse|crumbl|nothing bundt|"
    r"waxing the city|the joint|elements massage|salon lofts|sola salon|phenix salon|my salon suite|hooters|twin peaks|"
    r"apple |kimpton|archer hotel|aveda|hotel|resort|\binn\b|institute|casino|hilton|marriott|hyatt|ihop|denny|cracker barrel|red robin|texas roadhouse|outback|bj'?s|yard house|cheesecake",
    re.I)

UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"}


def domain(u: str) -> str:
    n = urlparse(u if "//" in u else "http://" + u).netloc.lower()
    return n[4:] if n.startswith("www.") else n


def load() -> list[dict]:
    rows, seen = [], set()
    for f in SOURCES:
        for r in csv.DictReader(open(BRICKS / f)):
            if not (r.get("website") and r.get("email")):
                continue
            if r.get("mg_result") and r["mg_result"] not in ("deliverable", "unknown", ""):
                continue
            d = domain(r["website"])
            if not d or d in seen:
                continue
            seen.add(d)
            r["domain"] = d
            r["source_file"] = f
            rows.append(r)
    return rows


def prior_contacts() -> dict[str, str]:
    seen: dict[str, str] = {}
    for r in csv.DictReader(open(BRICKS / "sent_log.csv")):
        seen[r["email"].lower()] = "sent_log " + r["timestamp"][:10]
    for f in glob.glob(str(BRICKS / "outreach/*/tokens.csv")):
        try:
            for r in csv.DictReader(open(f)):
                e = (r.get("email") or "").lower()
                if e:
                    seen.setdefault(e, "outreach " + Path(f).parent.name)
        except Exception:
            pass
    return seen


_MX: dict[str, bool] = {}


def mx_ok(email: str) -> bool:
    """True when the email's domain publishes an MX record (dig). Bounces, not volume, stop a send (SKILL.md rule 8)."""
    import subprocess
    d = email.split("@")[-1].lower().strip()
    if d not in _MX:
        try:
            out = subprocess.run(["dig", "+short", "+time=3", "+tries=2", "MX", d], capture_output=True, text=True, timeout=15).stdout
            _MX[d] = bool(out.strip())
        except Exception:
            _MX[d] = False
    return _MX[d]


def fetch(r: dict) -> dict:
    url = r["website"] if r["website"].startswith("http") else "http://" + r["website"]
    out = {"alive": False, "final_url": "", "takes_money": "", "status": "", "https": False, "fetch_err": ""}
    try:
        resp = requests.get(url, headers=UA, timeout=15, allow_redirects=True)
        out["status"] = resp.status_code
        out["final_url"] = resp.url
        out["https"] = resp.url.startswith("https://")
        html = resp.text[:600_000]
        out["alive"] = resp.ok and len(html) > 1500
        labels = []
        for pat, lab in MONEY:
            if re.search(pat, html, re.I) and lab not in labels:
                labels.append(lab)
        m = CTA.search(html)
        if m and not labels:
            labels.append("'" + m.group(1).strip().lower() + "' link")
        out["takes_money"] = "; ".join(labels)
        out["builder"] = next((b for p, b in [(r"wix\.com|wixstatic", "Wix"), (r"squarespace", "Squarespace"),
                                              (r"wp-content", "WordPress"), (r"godaddy|img1\.wsimg", "GoDaddy"),
                                              (r"weebly", "Weebly"), (r"cdn\.shopify", "Shopify"),
                                              (r"webflow", "Webflow"), (r"duda|dudaone|multiscreensite", "Duda")]
                               if re.search(p, html, re.I)), "custom/other")
        if domain(resp.url).split(".")[-2:] != r["domain"].split(".")[-2:]:
            out["fetch_err"] = "redirects off-domain to " + domain(resp.url)
    except Exception as e:
        out["fetch_err"] = type(e).__name__
        if "SSL" in str(e):
            out["fetch_err"] = "SSL error"
    return out


def main() -> None:
    rows = load()
    names = Counter(re.sub(r"[^a-z]", "", r["name"].lower()) for r in csv.DictReader(open(BRICKS / "leads.csv")))
    emails_dom = Counter(r["email"].split("@")[-1].lower() for r in rows)
    free_mail = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com", "comcast.net", "msn.com", "live.com", "att.net", "me.com"}
    keep = []
    for r in rows:
        nk = re.sub(r"[^a-z]", "", r["name"].lower())
        ed = r["email"].split("@")[-1].lower()
        if CHAIN_WORDS.search(r["name"]) or names[nk] >= 3 or (ed not in free_mail and emails_dom[ed] >= 3):
            continue
        if re.search(r"facebook\.com|instagram\.com|yelp\.com|google\.com|linktr\.ee|square\.site|toasttab|vagaro\.com|booksy\.com|glossgenius|business\.site", r["domain"]):
            continue  # not their own site
        keep.append(r)
    print(f"{len(rows)} with site+email, {len(keep)} after chain/own-domain filter", file=sys.stderr)
    with ThreadPoolExecutor(32) as ex:
        fetched = list(ex.map(fetch, keep))
    with ThreadPoolExecutor(16) as ex:
        mx = list(ex.map(lambda r: mx_ok(r["email"]), keep))
    prior = prior_contacts()
    out = []
    for r, f, m in zip(keep, fetched, mx):
        if not m:
            continue  # no MX: the address cannot receive mail
        if not f["alive"] or f["fetch_err"].startswith("redirects off-domain"):
            continue
        rev = int(float(r.get("reviews") or 0))
        score = min(rev, 1000) / 10  # up to 100
        if f["takes_money"]:
            score += 80
        if rev < 50:
            score -= 40
        pc = prior.get(r["email"].lower(), "")
        if pc:
            score -= 30
        out.append({"name": r["name"], "city": r["city"], "state": r["state"], "website": f["final_url"] or r["website"],
                    "email": r["email"], "email_source": r["email_source"], "mx_ok": True, "reviews": rev, "rating": r.get("rating", ""),
                    "types": r.get("types", "").split("|")[0], "takes_money": f["takes_money"], "builder": f.get("builder", ""),
                    "https": f["https"], "prior_contact": pc, "score": round(score, 1)})
    out.sort(key=lambda x: -x["score"])
    OUT.mkdir(exist_ok=True)
    with open(OUT / "pool.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    print(f"{len(out)} live candidates -> data/pool.csv; {sum(1 for o in out if o['takes_money'])} take money; "
          f"{sum(1 for o in out if not o['prior_contact'])} uncontacted", file=sys.stderr)


if __name__ == "__main__":
    main()
