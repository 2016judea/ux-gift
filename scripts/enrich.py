#!/usr/bin/env python
"""Record two columns per audited site, from the pages the sweep already loaded (home + the one hop):

  form        bug-report | contact-form | none, plus the URL of the page carrying it
  dev_credit  the agency/person credited in the footer ("Website by X") and their link

Fields come from the audit JSON (`fields` on each loaded page); the credit and the
bug-report wording come from one GET of those same URLs. No new pages are crawled.

    python scripts/enrich.py   -> data/enrich.json  (build_drafts.py merges it into candidates.csv)
"""
from __future__ import annotations

import glob
import html as H
import json
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"}

CREDIT = re.compile(
    r"(?:web\s*site|site|web\s*design|designed|design|developed|built|made|crafted|created|powered|hosted)"
    r"(?:\s*(?:&amp;|&|and)\s*(?:developed|design(?:ed)?|built|hosted))?\s*(?:with\s*\S+\s*)?by\s*:?\s*"
    r"(?:<[^>]*>\s*)*?<a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", re.I | re.S)
PLATFORM = re.compile(r"squarespace|wordpress|wix|weebly|godaddy|shopify|webflow|duda|elementor|bentobox|popmenu|spothopper|toast|square\b|olo\b|bopple|wpengine|genesis|astra", re.I)
BUGREPORT = re.compile(r"report (?:a|an) (?:problem|bug|issue|broken link)|website feedback|site feedback|accessibility (?:feedback|issue)", re.I)


def get(u: str) -> str:
    try:
        return requests.get(u, headers=UA, timeout=15).text[:800_000]
    except Exception:
        return ""


def main() -> None:
    rows = []
    for f in glob.glob(str(ROOT / "data/audit/shard-*.json")):
        rows += json.load(open(f))
    pages = defaultdict(dict)  # site -> url -> fields
    for r in rows:
        if r.get("device") != "iphone":
            continue
        pages[r.get("site") or r["url"]][r["url"]] = r.get("fields") or []
    urls = sorted({u for s in pages.values() for u in s})
    with ThreadPoolExecutor(24) as ex:
        html = dict(zip(urls, ex.map(get, urls)))
    out = {}
    for site, ps in pages.items():
        form, credit = "none", ""
        for u, fields in ps.items():
            src = html.get(u, "")
            kinds = {f["kind"] for f in fields}
            types = {f["type"] for f in fields}
            if BUGREPORT.search(re.sub(r"<[^>]+>", " ", src)) and "textarea" in types:
                form = f"bug-report {u}"; break
            if form == "none" and "textarea" in types and ("email" in kinds or "tel" in kinds):
                form = f"contact-form {u}"
        for u in ps:
            for m in CREDIT.finditer(html.get(u, "")):
                name = H.unescape(re.sub(r"<[^>]+>|\s+", " ", m.group(2))).strip()
                if name and not PLATFORM.search(name + " " + m.group(1)) and len(name) < 60:
                    credit = f"{name} {m.group(1)}"; break
            if credit:
                break
        out[site] = {"form": form, "dev_credit": credit}
    json.dump(out, open(ROOT / "data/enrich.json", "w"), indent=1)
    forms = defaultdict(int)
    for v in out.values():
        forms[v["form"].split(" ")[0]] += 1
    agencies = defaultdict(list)
    for s, v in out.items():
        if v["dev_credit"]:
            agencies[re.sub(r"https?://(www\.)?|/.*", "", v["dev_credit"].split(" ")[-1]).lower()].append(s)
    print(f"{len(out)} sites; forms {dict(forms)}; dev_credit on {sum(1 for v in out.values() if v['dev_credit'])}")
    for a, ss in sorted(agencies.items(), key=lambda x: -len(x[1])):
        if len(ss) >= 2:
            print(f"  {a}: {len(ss)} sites -> {', '.join(ss)}")


if __name__ == "__main__":
    main()
