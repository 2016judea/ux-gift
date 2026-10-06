#!/usr/bin/env python
"""Where a link sits and what it says, on a phone: linkctx.py URL HREF_SUBSTRING [...]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "Desktop/bricks/.venv/lib/python3.11/site-packages"))
from playwright.sync_api import sync_playwright
url, subs = sys.argv[1], sys.argv[2:]
with sync_playwright() as p:
    b = p.webkit.launch(); ctx = b.new_context(**p.devices["iPhone 13"]); pg = ctx.new_page()
    try: pg.goto(url, wait_until="networkidle", timeout=45000)
    except Exception: pg.goto(url, wait_until="load", timeout=45000)
    pg.wait_for_timeout(2000)
    for s in subs:
        print(s, pg.evaluate("""s => [...document.querySelectorAll('a')].filter(a => (a.getAttribute('href')||'').includes(s)).map(a => { const r = a.getBoundingClientRect();
          const sec = a.closest('section,footer,header,nav,[class*=footer],[class*=section]');
          return { text: a.innerText.trim().slice(0,60), y: Math.round(r.top + scrollY), w: Math.round(r.width), h: Math.round(r.height),
                   ctx: (a.parentElement.innerText||'').trim().replace(/\\s+/g,' ').slice(0,160), in: sec ? sec.tagName + '.' + (sec.className||'').toString().split(' ')[0] : '' }; })""", s))
    print("docH", pg.evaluate("document.documentElement.scrollHeight"))
    b.close()
