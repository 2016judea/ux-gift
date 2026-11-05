#!/usr/bin/env python3
"""Pre-send gate for one draft: the three checks that must pass before send.py runs.

  1. the bug is still live  -- every `verify` entry for the slug in data/verified.json
     ({"url", "expect": 404} | {"url", "expect_present": "<regex>"} | {"url", "expect_missing": "<regex>"}) re-checked by curl now
  2. the recipient's domain has an MX record
  3. the address is not on Mailgun's bounces / complaints / unsubscribes lists for the domain

    set -a; source ~/Desktop/workspace/bricks/.env; set +a
    python3 scripts/presend.py drafts/<slug>.txt [...]     -> PASS/FAIL per draft, exit 1 on any FAIL

Writes nothing and sends nothing.
"""
import json
import os
import re
import subprocess
import sys

UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"


BODY = "/tmp/presend.body"


def curl(url):
    # Remove the last check's body first: a curl that times out writes nothing, and the
    # previous page's HTML would otherwise be read as this one's (a dead bug "still there").
    if os.path.exists(BODY):
        os.remove(BODY)
    out = subprocess.run(["curl", "-sL", "-A", UA, "-o", BODY, "-w", "%{http_code}", "--max-time", "20", url],
                         capture_output=True, text=True).stdout
    body = open(BODY, errors="ignore").read() if os.path.exists(BODY) else ""
    return out, body


def main():
    ver = {v["slug"]: v for v in json.load(open("data/verified.json"))}
    key, dom = os.environ.get("MAILGUN_API_KEY"), os.environ.get("MAILGUN_DOMAIN")
    bad = 0
    for f in sys.argv[1:]:
        slug = os.path.basename(f)[:-4]
        to = re.search(r"^To: (.+)$", open(f).read(), re.M).group(1).strip()
        res = []
        for chk in ver[slug].get("verify", []):
            code, body = curl(chk["url"])
            if "expect_present" in chk:
                ok = bool(re.search(chk["expect_present"], body, re.I))
                res.append((ok, f"{chk['url']} -> {code}, /{chk['expect_present']}/ {'still there' if ok else 'GONE (fixed?)'}"))
            elif "expect" in chk:
                res.append((code == str(chk["expect"]), f"{chk['url']} -> {code} (want {chk['expect']})"))
            else:
                ok = not re.search(chk["expect_missing"], body, re.I)
                res.append((ok, f"{chk['url']} -> {code}, /{chk['expect_missing']}/ {'absent' if ok else 'PRESENT (fixed?)'}"))
        mx = subprocess.run(["dig", "+short", "MX", to.split("@")[1]], capture_output=True, text=True).stdout.strip()
        res.append((bool(mx), f"MX {to.split('@')[1]}: {mx.splitlines()[0] if mx else 'none'}"))
        if key and dom:
            for lst in ("bounces", "complaints", "unsubscribes"):
                code = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-u", f"api:{key}",
                                       f"https://api.mailgun.net/v3/{dom}/{lst}/{to}"], capture_output=True, text=True).stdout
                res.append((code == "404", f"mailgun {lst}: {'not listed' if code == '404' else 'HTTP ' + code}"))
        else:
            res.append((False, "MAILGUN_API_KEY/DOMAIN not in env: suppression lists unchecked"))
        ok = all(r[0] for r in res)
        bad += not ok
        print(("PASS " if ok else "FAIL ") + f"{slug} <{to}>")
        for r in res:
            print(("   ok  " if r[0] else "   NO  ") + r[1])
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
