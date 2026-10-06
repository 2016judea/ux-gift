#!/usr/bin/env python
"""Verify a finding the way a visitor would: tap a link (or try to scroll / close a popup) on a phone.

    click.py URL --href 991408          tap the first visible <a> whose href contains this; report where it lands
    click.py URL --text "Order"         same, by visible text
    click.py URL --scroll               try to scroll down (finger-style wheel) and report how far the page moved
    click.py URL --overlay              list fixed layers covering >=40% and any visible close control inside them
    add --shot OUT.png to keep what the visitor ends up looking at

Headless WebKit, iPhone 13. A finding ships only if this reproduces it (SKILL.md rule 1).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "Desktop/bricks/.venv/lib/python3.11/site-packages"))
from playwright.sync_api import sync_playwright  # noqa: E402

OVER = r"""() => { const vw = innerWidth, vh = innerHeight; const out = [];
  for (const el of document.querySelectorAll('*')) { const s = getComputedStyle(el); if (s.position !== 'fixed' || s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0' || s.pointerEvents === 'none') continue;
    const r = el.getBoundingClientRect(); const w = Math.max(0, Math.min(r.right, vw) - Math.max(r.left, 0)), h = Math.max(0, Math.min(r.bottom, vh) - Math.max(r.top, 0));
    const cover = Math.round(100 * w * h / (vw * vh)); if (cover < 40) continue;
    const closers = [...el.querySelectorAll('button,a,[role=button],[aria-label],.close,[class*=close]')].filter(c => { const cr = c.getBoundingClientRect(); return cr.width > 0 && cr.height > 0 && cr.top >= 0 && cr.bottom <= vh && cr.left >= 0 && cr.right <= vw; })
      .map(c => (c.getAttribute('aria-label') || c.textContent || c.className || '').toString().trim().slice(0, 30));
    out.push({ el: el.tagName.toLowerCase() + '#' + el.id + '.' + (typeof el.className === 'string' ? el.className.split(' ')[0] : ''), cover, text: (el.innerText || '').trim().slice(0, 120), closers: closers.slice(0, 6) }); }
  return out; }"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("url"); ap.add_argument("--href"); ap.add_argument("--text")
    ap.add_argument("--scroll", action="store_true"); ap.add_argument("--overlay", action="store_true")
    ap.add_argument("--close", help="tap the popup's close control (CSS selector) first")
    ap.add_argument("--shot", type=Path); ap.add_argument("--device", default="iPhone 13")
    a = ap.parse_args()
    with sync_playwright() as p:
        eng = p.chromium if "Pixel" in a.device else p.webkit
        b = eng.launch(); ctx = b.new_context(**p.devices[a.device]); pg = ctx.new_page()
        statuses = {}
        pg.on("response", lambda r: statuses.__setitem__(r.url, r.status) if r.request.is_navigation_request() else None)
        try:
            pg.goto(a.url, wait_until="networkidle", timeout=45000)
        except Exception:
            pg.goto(a.url, wait_until="load", timeout=45000)
        pg.wait_for_timeout(3000)
        if a.overlay:
            print("overlays:", pg.evaluate(OVER))
        if a.close:
            try:
                pg.locator(a.close).filter(visible=True).first.click(timeout=6000); pg.wait_for_timeout(1200)
                print("closed popup via", a.close, "; overlays now:", pg.evaluate(OVER))
            except Exception as e:
                print("close failed:", str(e)[:160])
        if a.scroll:
            # A finger scroll. Mobile WebKit has no wheel, so swipe with CDP-less touch is unavailable there:
            # use --device "Pixel 5" (Chromium) for the scroll proof; WebKit reports computed overflow only.
            y0 = pg.evaluate("scrollY")
            if "Pixel" in a.device:
                pg.mouse.move(200, 400)
                for _ in range(6):
                    pg.mouse.wheel(0, 600); pg.wait_for_timeout(250)
            print("scrolled from", y0, "to", pg.evaluate("scrollY"), "of", pg.evaluate("document.documentElement.scrollHeight"),
                  "html/body overflow:", pg.evaluate("[getComputedStyle(document.documentElement).overflowY, getComputedStyle(document.body).overflowY]"))
        if a.href or a.text:
            loc = pg.locator(f'a[href*="{a.href}"]') if a.href else pg.get_by_text(a.text, exact=False)
            n = loc.count(); vis = [i for i in range(n) if loc.nth(i).is_visible()]
            print("matches", n, "visible", len(vis))
            target = loc.nth(vis[0]) if vis else (loc.first if n else None)
            if target is not None:
                before = pg.url
                try:
                    target.scroll_into_view_if_needed(timeout=5000)
                    target.click(timeout=8000, force=not vis)
                except Exception as e:
                    print("click failed:", str(e)[:200])
                pg.wait_for_timeout(3500)
                print("before", before, "\nafter ", pg.url, "status", statuses.get(pg.url), "\ntitle", pg.title()[:100],
                      "\ntext", (pg.evaluate("document.body.innerText") or "")[:300].replace("\n", " | "))
        if a.shot:
            pg.screenshot(path=str(a.shot))
        b.close()


if __name__ == "__main__":
    main()
