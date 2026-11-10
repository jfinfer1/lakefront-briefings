#!/usr/bin/env python3
"""Fill Jack's STEO card (1200x675) from data.json; render chart.png at 2x.
Usage: python3 chart.py DATA_JSON RELEASE_DATE(YYYY-MM-DD) OUT_DIR"""
import datetime, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))

def main(dp, rel, out):
    d = json.load(open(dp)); s = d["series"]; y = d["year"]
    t = open(os.path.join(HERE, "template_original.html")).read()
    t = t.replace(re.search(r"@import url\('https://fonts.googleapis.com[^)]*\);", t)[0], open(os.path.join(HERE, "fonts.css")).read())
    rd = datetime.date.fromisoformat(rel)
    t = re.sub(r'<div class="header-date">[^<]*</div>', f'<div class="header-date">{rd.strftime("%B")} {rd.day}, {rd.year}</div>', t)
    money = lambda v: f"${v:.2f}"; plain = lambda v: f"{v:.2f}"
    for i, k in enumerate(("brent", "wti", "hh", "crude"), 1):
        fm = plain if k == "crude" else money
        t, n = re.subn(rf'(<div class="box box{i}"><div class="val">)[^<]*', lambda m: m[1] + fm(s[k]["cur"]), t)
        ch = s[k]["cur"] - s[k]["last"]; cls = "up" if ch >= 0 else "dn"
        cells = (f'<div class="cell c{y-1}">{fm(s[k]["last"])}</div>\n    <div class="cell c{y}">{fm(s[k]["cur"])}</div>\n'
                 f'    <div class="cell cyoy {cls}">{fm(abs(ch))}</div>\n    <div class="cell c{y+1}">{fm(s[k]["next"])}</div>')
        t, n2 = re.subn(rf'(<div class="row row{i}">\s*<div class="cell c-name">[^<]*</div>\s*)<div class="cell c2025">.*?<div class="cell c2027">[^<]*</div>', lambda m: m[1] + cells, t, flags=re.S)
        if n != 1 or n2 != 1: sys.exit(f"TEMPLATE CHANGED at {k}")
    t = t.replace('>2025</div>', f'>{y-1}</div>').replace('>2026 Forecast<', f'>{y} Forecast<').replace('>2027 Forecast<', f'>{y+1} Forecast<')
    t = t.replace(f'class="cell c{y-1}"', 'class="cell c2025"').replace(f'class="cell c{y}"', 'class="cell c2026"').replace(f'class="cell c{y+1}"', 'class="cell c2027"')
    os.makedirs(out, exist_ok=True); hp = os.path.join(out, "chart.html"); open(hp, "w").write(t)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 675}, device_scale_factor=2)
        pg.goto("file://" + os.path.abspath(hp)); pg.wait_for_timeout(600)
        pg.screenshot(path=os.path.join(out, "chart.png"), clip={"x": 0, "y": 0, "width": 1200, "height": 675}); b.close()
    print("OK", os.path.join(out, "chart.png"))

if __name__ == "__main__":
    main(*sys.argv[1:4])
