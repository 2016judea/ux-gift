#!/usr/bin/env python
"""Stage 4: render drafts/<slug>.txt from data/verified.json (hand-verified findings only).

The body is Aidan's copy, verbatim. Only the numbered findings change (SKILL.md, "The email").
Also writes candidates.csv (every audited site) and the ranked README.md.

data/verified.json: [{"slug","name","site","email","why_pay","attach":[...],
                      "findings":[{"visitor","cause","fix"}]}, ...]  -- best first
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SUBJECT = "I ran UX testing on your website."  # his subject line, verbatim
BODY_HEAD = ""
BODY_TAIL = """Forward this email to your website/developer to have them fix the above.\x20

This was free of charge. No catch. But if interested we do also offer:
\x20
  - More thorough testing -- $100
  - Brand / website re-designs -- $500
  - Anything else you can think of -- Ask me for a quote

Thank you,
Aidan.
"""


def render(v: dict) -> str:
    hdr = f"To: {v['email']}\nSubject: {SUBJECT}\n"
    if v.get("attach"):
        hdr += "Attach: " + ", ".join(f"drafts/{v['slug']}/{a}" for a in v["attach"]) + "\n"
    items = []
    for i, f in enumerate(v["findings"][:3], 1):
        items.append(f"#{i}) {f['visitor']}\n{f['cause']}\nRecommend to your developer that they {f['fix']}")
    return hdr + "\n" + BODY_HEAD + "\n\n".join(items) + "\n\n" + BODY_TAIL


def main() -> None:
    ver = json.load(open(ROOT / "data/verified.json"))
    for v in ver:
        (ROOT / "drafts" / f"{v['slug']}.txt").write_text(render(v))
    big = json.load(open(ROOT / "data/big.json")) if (ROOT / "data/big.json").exists() else {}
    audited = set()
    for f in (ROOT / "data/audit").glob("urls-*.txt"):
        audited |= set(f.read_text().split())
    vmap = {v["site"]: v for v in ver}
    with open(ROOT / "candidates.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["name", "city", "website", "email", "email_source", "mx_ok", "reviews", "takes_money", "prior_contact",
                    "findings_count", "top_severity", "draft", "form", "dev_credit"])
        enrich = json.load(open(ROOT / "data/enrich.json")) if (ROOT / "data/enrich.json").exists() else {}
        for r in csv.DictReader(open(ROOT / "data/pool.csv")):
            if r["website"] not in audited:
                continue
            v = vmap.get(r["website"])
            n = len(v["findings"]) if v else 0
            sev = "BIG (verified)" if v else ("candidate, not verified big" if r["website"] in big else "none big")
            w.writerow([r["name"], r["city"], r["website"], v["email"] if v else r["email"], r["email_source"], r["mx_ok"],
                        r["reviews"], r["takes_money"], r["prior_contact"], n, sev, f"drafts/{v['slug']}.txt" if v else "",
                        enrich.get(r["website"], {}).get("form", ""), enrich.get(r["website"], {}).get("dev_credit", "")])
    lines = ["# UX gift — sweep 1 (2026-10-06)", "",
             "A free UX bug report emailed to a small business about its own website, with Aidan's $100 / $500 upsell.",
             "Drafts only — nothing has been sent. Skill: `~/.claude/skills/ux-gift-sweep/`.", "",
             f"Audited {len(audited)} sites on headless WebKit (iPhone 13) and Chromium (Pixel 5); "
             f"{len(ver)} had a big, reproduced bug and got a draft. Ranked best-first:", ""]
    prior = {r["website"]: r["prior_contact"] for r in csv.DictReader(open(ROOT / "data/pool.csv"))}
    for i, v in enumerate(ver, 1):
        pc = prior.get(v["site"]) or "uncontacted"
        lines.append(f"{i}. **{v['name']}** ({v['email']}; prior: {pc}) — {v['why_pay']} — {v['findings'][0]['visitor']} → `drafts/{v['slug']}.txt`")
    lines += ["", "## Pipeline", "",
              "1. `scripts/pool.py` — leads → chain/own-domain/MX filter → homepage fetch → `data/pool.csv` ranked",
              "2. `scripts/sweep.sh 150 10` — `mobile-ui-audit/audit.py --links --hop` in 10 shards → `data/audit/`",
              "3. `scripts/analyze.py` — keep only big findings → `data/big.json`",
              "4. verify each by hand + `scripts/shoot.py` proof PNGs → `data/verified.json`",
              "5. `scripts/build_drafts.py` → `drafts/`, `candidates.csv`, this README", ""]
    (ROOT / "README.md").write_text("\n".join(lines))
    print(f"{len(ver)} drafts")


if __name__ == "__main__":
    main()
