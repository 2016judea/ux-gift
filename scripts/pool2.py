#!/usr/bin/env python
"""Sweep 2 pool: pool.csv past the first 150 (uncontacted only) + places_enriched.csv rows
with a website but no email, whose email is found printed on their own site.

    python scripts/pool2.py 160   -> data/pool2.csv (top N, ranked), data/audit2/urls-*.txt
"""
from __future__ import annotations

import csv
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pool as P  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
JUNK = re.compile(r"\.(png|jpe?g|gif|webp|svg)$|sentry|wixpress|example\.|domain\.com|godaddy|squarespace|@2x|u003e", re.I)


def site_email(home: str, dom: str) -> tuple[str, str]:
    """An address printed on their own site, preferring one on their own domain."""
    found = []
    for path in ("", "/contact", "/contact-us", "/about"):
        u = home.rstrip("/") + path if path else home
        try:
            t = P.requests.get(u, headers=P.UA, timeout=12).text
        except Exception:
            continue
        for e in EMAIL.findall(t.replace("%40", "@")):
            if not JUNK.search(e) and e.lower() not in [f[0].lower() for f in found]:
                found.append((e, path or "homepage"))
        if any(e.split("@")[-1].lower().endswith(dom.split(".", 0)[0]) for e, _ in found):
            break
    own = [f for f in found if f[0].split("@")[-1].lower().replace("www.", "") == dom]
    pick = (own or found or [("", "")])[0]
    return pick


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 160
    prior = P.prior_contacts()
    first = list(csv.DictReader(open(ROOT / "data/pool.csv")))
    done = {r["website"] for r in first[:150]}
    seen_dom = {P.domain(r["website"]) for r in first}
    a = [dict(r, origin="pool") for r in first[150:] if not r["prior_contact"] and r["takes_money"] and int(r["reviews"]) >= 50]

    names = P.Counter(re.sub(r"[^a-z]", "", r["name"].lower()) for r in csv.DictReader(open(P.BRICKS / "places_enriched.csv")))
    cand = []
    for r in csv.DictReader(open(P.BRICKS / "places_enriched.csv")):
        if not r.get("website") or r.get("email"):
            continue
        rev = int(float(r.get("reviews") or 0))
        d = P.domain(r["website"])
        nk = re.sub(r"[^a-z]", "", r["name"].lower())
        if re.search(r"zoo|aquarium|stadium|park\b|casino|museum|tourist_attraction|lodging|amusement|university|church|hospital|airport", r.get("types", "") + " " + r["name"], re.I):
            continue  # institutions, not small businesses
        if rev < 150 or rev > 8000 or d in seen_dom or P.CHAIN_WORDS.search(r["name"]) or names[nk] >= 3:
            continue
        if re.search(r"facebook|instagram|yelp|google|linktr|square\.site|toasttab|vagaro|booksy|glossgenius|business\.site|\.gov|\.edu", d):
            continue
        seen_dom.add(d)
        r["domain"] = d
        cand.append(r)
    cand.sort(key=lambda r: -int(float(r["reviews"] or 0)))
    cand = cand[:500]
    print(f"{len(a)} from pool past 150 (uncontacted, money); {len(cand)} enriched to fetch", file=sys.stderr)
    with ThreadPoolExecutor(32) as ex:
        fetched = list(ex.map(P.fetch, cand))
    live = [(r, f) for r, f in zip(cand, fetched) if f["alive"] and f["takes_money"] and not f["fetch_err"]]
    with ThreadPoolExecutor(24) as ex:
        emails = list(ex.map(lambda rf: site_email(rf[1]["final_url"], rf[0]["domain"]), live))
    b = []
    for (r, f), (e, src) in zip(live, emails):
        if not e or "%" in e or prior.get(e.lower()) or not P.mx_ok(e):
            continue
        rev = int(float(r["reviews"]))
        b.append({"name": r["name"], "city": r["city"], "state": r["state"], "website": f["final_url"], "email": e,
                  "email_source": src, "mx_ok": True, "reviews": rev, "rating": r.get("rating", ""),
                  "types": r.get("types", "").split("|")[0], "takes_money": f["takes_money"], "builder": f.get("builder", ""),
                  "https": f["https"], "prior_contact": "", "score": round(min(rev, 1000) / 10 + 80, 1), "origin": "places_enriched"})
    allr = sorted(a + b, key=lambda x: -float(x["score"]))
    allr = [r for r in allr if r["website"] not in done][:n]
    keys = list(b[0].keys()) if b else list(a[0].keys())
    with open(ROOT / "data/pool2.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader(); w.writerows(allr)
    print(f"{len(b)} enriched with an on-site email + MX; pool2 = {len(allr)} "
          f"({sum(1 for r in allr if r.get('origin') == 'places_enriched')} enriched)", file=sys.stderr)


if __name__ == "__main__":
    main()
