"""Render a Futures Education graphic (2400x1350 PNG).

Usage: python3 tools/education/render.py post.json out.png

post.json fields:
  id, series, title, lede, visual, aisource (bool)
  visual = "points"  -> cardTitle, points [2-4 short strings]
           "myth"    -> myth, fact
           "tiles"   -> cardTitle, tiles [4 or 6 short labels], note (optional)
           "basis"   -> (fixed futures vs cash illustration)
Brand rules (Jack, 10/15): Lakefront navy #1E2264 and white only. Lakefront logo on every
graphic; aiSource logo (aisource=true) on every Managed Futures post. No dash characters.
Exit code 2 = layout check failed (text too long / overflowing); shorten and re-run.
"""
import json, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))

def main(post_path, out_png):
    post = json.load(open(post_path, encoding="utf-8"))
    if post.get("series") == "Managed Futures 101":
        post["aisource"] = True
    blob = json.dumps(post, ensure_ascii=False)
    for ch in ("–", "—", " - "):
        if ch in blob:
            print(f"LAYOUT FAILED: dash character {ch!r} in post text (brand rule: no dashes)"); sys.exit(2)
    t = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    t = t.replace("<script>\nconst P = window.POST;", "<script>window.POST = " + blob.replace("</", "<\\/") + ";</script>\n<script>\nconst P = window.POST;", 1)
    hp = os.path.join(HERE, "_render.html")
    open(hp, "w", encoding="utf-8").write(t)
    try:
        with sync_playwright() as p:
            br = p.chromium.launch(args=["--allow-file-access-from-files"])
            pg = br.new_page(viewport={"width": 2400, "height": 1350}, device_scale_factor=1)
            pg.goto("file://" + hp); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(300)
            problems = pg.evaluate("""() => {
              const out = [];
              const h1 = document.getElementById('title');
              if (h1.getBoundingClientRect().height > 125*3) out.push('title more than 3 lines');
              const foot = document.querySelector('.foot').getBoundingClientRect().top;
              for (const sel of ['#lede', '#right > *']) {
                const el = document.querySelector(sel); if (!el) continue;
                const r = el.getBoundingClientRect();
                if (r.bottom > foot - 20) out.push(sel + ' runs into footer');
                if (el.scrollHeight > el.clientHeight + 2) out.push(sel + ' overflows');
              }
              if (document.querySelector('#right').getBoundingClientRect().right > 2262) out.push('right side too wide');
              return out;
            }""")
            pg.screenshot(path=out_png); br.close()
    finally:
        os.remove(hp)
    if problems:
        print("LAYOUT FAILED: " + "; ".join(problems)); sys.exit(2)
    print("OK", out_png)

if __name__ == "__main__":
    main(*sys.argv[1:3])
