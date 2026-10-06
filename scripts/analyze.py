#!/usr/bin/env python
"""Stage 3: read the audit shards and keep only BIG findings per site (SKILL.md rule 3).

Big = a normal phone visitor would see it broken. Everything else the audit says
(tap targets, small text, zoom caps, invisible console errors) is dropped here.

    python scripts/analyze.py [audit_dir pool.csv out.json]   -> data/big.json (site -> findings), prints a summary
"""
from __future__ import annotations

import csv
import json
import glob
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    import sys
    adir, poolf, outf = (sys.argv[1:4] + ["data/audit", "data/pool.csv", "data/big.json"][len(sys.argv[1:4]):])
    rows = []
    for f in sorted(glob.glob(str(ROOT / adir / "shard-*.json"))):
        try:
            rows += json.load(open(f))
        except json.JSONDecodeError:
            pass  # mid-write
    pool = {r["website"]: r for r in csv.DictReader(open(ROOT / poolf))}
    by = defaultdict(list)
    for r in rows:
        by[r.get("site") or r["url"]].append(r)
    big = {}
    for site, rs in by.items():
        out = []
        for r in rs:
            is_hop = r["url"].rstrip("/") != site.rstrip("/")
            where = "hop" if is_hop else "home"
            dev = r["device"]
            for sev, msg in r.get("findings", []):
                if msg.startswith("sideways overflow (page pans"):
                    out.append({"kind": "overflow", "where": where, "url": r["url"], "dev": dev, "msg": msg, "panX": r.get("panX")})
                elif msg.startswith("page renders blank"):
                    out.append({"kind": "blank", "where": where, "url": r["url"], "dev": dev, "msg": msg})
                elif msg.startswith("document locked"):
                    out.append({"kind": "locked", "where": where, "url": r["url"], "dev": dev, "msg": msg})
                elif msg.startswith("viewport meta: missing"):  # initial-scale=1 alone already lays out at device width
                    out.append({"kind": "no_viewport", "where": where, "url": r["url"], "dev": dev, "msg": msg})
                elif msg.startswith("HTTP ") and is_hop:
                    out.append({"kind": "hop_http", "where": where, "url": r["url"], "dev": dev, "msg": msg})
                elif msg.startswith("did not load"):
                    out.append({"kind": "noload", "where": where, "url": r["url"], "dev": dev, "msg": msg})
                elif "layer" in msg and "covers" in msg:
                    out.append({"kind": "overlay", "where": where, "url": r["url"], "dev": dev, "msg": msg})
                elif msg.startswith("iOS zoom trap") and dev == "iphone":
                    out.append({"kind": "zoom", "where": where, "url": r["url"], "dev": dev, "msg": msg})
                elif msg.startswith("broken image"):
                    out.append({"kind": "broken_img", "where": where, "url": r["url"], "dev": dev, "msg": msg})
            money = {l["href"].split("#")[0]: l["text"] for l in (r.get("moneyLinks") or [])}
            for l in r.get("deadLinks", []):
                if l["verdict"] == "dead":
                    out.append({"kind": "dead_money_link" if l["href"] in money else "dead_link", "where": where, "url": r["url"],
                                "dev": dev, "href": l["href"], "text": money.get(l["href"], ""), "codes": l["codes"]})
        if out:
            p = pool.get(site, {})
            big[site] = {"name": p.get("name"), "reviews": p.get("reviews"), "takes_money": p.get("takes_money"),
                         "prior": p.get("prior_contact"), "findings": out}
    json.dump(big, open(ROOT / outf, "w"), indent=1)
    kinds = defaultdict(int)
    for s in big.values():
        for k in {f["kind"] for f in s["findings"]}:
            kinds[k] += 1
    print(f"{len(by)} sites audited, {len(big)} with a candidate big finding")
    print(dict(kinds))


if __name__ == "__main__":
    main()
