#!/usr/bin/env python3
"""Fill Jack's Cattle on Feed card (1920x1080) and render.
Usage: python3 chart.py DATA_JSON OUT_DIR -> chart.html, chart.png"""
import datetime, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
def main(dp, out):
    d = json.load(open(dp)); t = open(os.path.join(HERE, "template_original.html"), encoding="utf-8").read()
    rel = datetime.date.fromisoformat(d["release_date"])
    t = re.sub(r'<div class="date">[^<]*</div>', f'<div class="date">{rel.strftime("%B")} {rel.day}, {rel.year}</div>', t, count=1)
    C, P = d["cur"], d["prev"]
    na = '<div class="cell"><span class="na">N/A</span></div>'
    cell = lambda v: f'<div class="cell"><span>{v}</span></div>'
    rows = (f'<div class="row-label">{C["label"]}</div>' + cell(f'{C["on_feed_pct"]:.1f}%') + cell(f'{C["head_m"]:.3f}') + na + na +
            f'<div class="row-label">{P["label"]}</div>' + cell(f'{P["on_feed_pct"]:.1f}%') + cell(f'{P["head_m"]:.3f}') +
            cell(f'{P["placements_pct"]:.1f}%') + cell(f'{P["marketings_pct"]:.1f}%'))
    a = t.index('<div class="row-label">'); b = t.index('</div>\n\n  <!-- Note -->')
    t = t[:a] + rows + "\n  " + t[b:]
    os.makedirs(out, exist_ok=True); hp = os.path.join(out, "chart.html"); open(hp, "w", encoding="utf-8").write(t)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto("file://" + os.path.abspath(hp)); pg.wait_for_timeout(400)
        pg.locator(".card").screenshot(path=os.path.join(out, "chart.png")); br.close()
    print("OK", os.path.join(out, "chart.png"))
if __name__ == "__main__":
    main(*sys.argv[1:3])
