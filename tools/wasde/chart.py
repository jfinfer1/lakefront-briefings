#!/usr/bin/env python3
"""Fill Jack's WASDE board (1920x1080) from data.json and render chart.png.
Usage: python3 chart.py DATA_JSON OUT_DIR"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))

def main(dp, out):
    d = json.load(open(dp)); t = open(os.path.join(HERE, "template_original.html")).read()
    f = lambda v, k: f"{v:.1f}" if k in ("yield", "area") else f"{v:,.0f}"
    def cells(col, r1):
        cls = " r1" if r1 else ""
        c = "".join(f'<div class="cell{cls} corn-cell">{f(d["corn"][k][col], k)}</div>' for k in ("yield", "area", "prod", "carry"))
        s = "".join(f'<div class="cell{cls} soy-cell">{f(d["soy"][k][col], k)}</div>' for k in ("yield", "area", "prod", "carry"))
        return c + "\n      " + s
    est = d["est_year"][2:]  # 2025/26 -> 25/26
    rows = (f'      <!-- cur row -->\n      <div class="lbl bold">{d["cur"]}</div>\n      {cells(3, True)}\n\n'
            f'      <!-- prior row -->\n      <div class="lbl">{d["prior"]}</div>\n      {cells(2, False)}\n\n'
            f'      <!-- est row -->\n      <div class="lbl small">{est}</div>\n      {cells(1, False)}\n    </div>')
    t, n = re.subn(r"      <!-- Oct row -->.*?</div>\n    </div>\n\n    <div class=\"note\">", lambda _: rows + '\n\n    <div class="note">', t, flags=re.S)
    if n != 1: sys.exit("TEMPLATE CHANGED")
    fonts = open(os.path.join(HERE, "fonts.css")).read()
    t, n2 = re.subn(r'<link rel="preconnect"[^>]*>\s*<link href="https://fonts.googleapis.com[^>]*>', lambda _: "<style>" + fonts + "</style>", t)
    if n2 != 1: sys.exit("TEMPLATE CHANGED: fonts")
    os.makedirs(out, exist_ok=True); hp = os.path.join(out, "chart.html"); open(hp, "w").write(t)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto("file://" + os.path.abspath(hp)); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(800)
        pg.screenshot(path=os.path.join(out, "chart.png"), clip={"x": 0, "y": 0, "width": 1920, "height": 1080}); b.close()
    print("OK", os.path.join(out, "chart.png"))

if __name__ == "__main__":
    main(*sys.argv[1:3])
