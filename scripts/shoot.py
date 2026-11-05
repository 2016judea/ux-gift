#!/usr/bin/env python
"""Proof screenshot for one finding: phone-sized PNG, red box round the broken thing, < ~150KB.

Headless WebKit, iPhone 13 profile (the same engine and profile mobile-ui-audit judges on).

    shoot.py URL OUT.png                      the first screen as a visitor lands on it
    shoot.py URL OUT.png --pan                pan the page sideways first (sideways overflow proof)
    shoot.py URL OUT.png --box "CSS"          red box round the first visible match
    shoot.py URL OUT.png --box-widest         red box round the widest element that leaks past the right edge
    shoot.py URL OUT.png --scroll-to "CSS"    scroll that element into view first

Prints the boxed rect and the final file size, so the draft can quote what the picture shows.
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "Desktop/workspace/bricks/.venv/lib/python3.11/site-packages"))
from PIL import Image, ImageDraw  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

WIDEST = r"""() => { const vw = innerWidth; let best = null;
  for (const el of document.querySelectorAll('body *')) { const r = el.getBoundingClientRect();
    if (r.width > 0 && r.height > 8 && r.right > vw + 1) { const clipped = (() => { for (let a = el.parentElement; a && a !== document.body; a = a.parentElement) { const s = getComputedStyle(a); if (s.overflowX !== 'visible') return true; } return false; })();
      if (!clipped && (!best || r.right > best.right || (r.right === best.right && r.height > best.h))) best = { x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height, right: r.right, el: el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/)[0] : '') }; } }
  return best; }"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("url"); ap.add_argument("out", type=Path)
    ap.add_argument("--pan", action="store_true")
    ap.add_argument("--box"); ap.add_argument("--box-widest", action="store_true")
    ap.add_argument("--scroll-to")
    ap.add_argument("--wait", type=int, default=2500)
    a = ap.parse_args()
    with sync_playwright() as p:
        b = p.webkit.launch()
        ctx = b.new_context(**p.devices["iPhone 13"])
        pg = ctx.new_page()
        try:
            pg.goto(a.url, wait_until="networkidle", timeout=45000)
        except Exception:
            pg.goto(a.url, wait_until="load", timeout=45000)
        pg.wait_for_timeout(a.wait)
        if a.scroll_to:
            pg.locator(a.scroll_to).first.scroll_into_view_if_needed()
            pg.wait_for_timeout(400)
        rect = None
        if a.box_widest:
            rect = pg.evaluate(WIDEST)
        elif a.box:
            rect = pg.evaluate("""s => { const el = [...document.querySelectorAll(s)].find(e => e.getBoundingClientRect().width > 0); if (!el) return null;
              const r = el.getBoundingClientRect(); return { x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height, el: s }; }""", a.box)
        pan = 0
        if a.pan:
            pg.evaluate("() => window.scrollTo(1e5, scrollY)")
            pg.wait_for_timeout(400)
            pan = pg.evaluate("() => Math.round(scrollX)")
        sx, sy = pg.evaluate("() => [scrollX, scrollY]")
        png = pg.screenshot()
        dpr = pg.evaluate("() => devicePixelRatio")
        b.close()
    img = Image.open(io.BytesIO(png)).convert("RGB")
    if rect:
        d = ImageDraw.Draw(img)
        x0 = (rect["x"] - sx) * dpr; y0 = (rect["y"] - sy) * dpr
        x1 = x0 + rect["w"] * dpr; y1 = y0 + rect["h"] * dpr
        W, H = img.size
        x0, y0, x1, y1 = max(4, x0), max(4, y0), min(W - 4, x1), min(H - 4, y1)
        if x1 > x0 and y1 > y0:
            for k in range(int(3 * dpr)):
                d.rectangle([x0 - k, y0 - k, x1 + k, y1 + k], outline=(230, 20, 20))
    # Phone-sized: 390pt wide at 2x is plenty; shrink, then palette-quantize until under 150KB.
    img = img.resize((img.width // 2 * 2 // 2, img.height // 2 * 2 // 2)) if img.width > 600 else img
    for colors in (256, 128, 64):
        buf = io.BytesIO()
        img.quantize(colors=colors, method=Image.Quantize.MEDIANCUT).save(buf, "PNG", optimize=True)
        if buf.tell() < 150_000:
            break
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_bytes(buf.getvalue())
    print({"out": str(a.out), "bytes": buf.tell(), "pan": pan, "box": rect, "size": img.size})


if __name__ == "__main__":
    main()
