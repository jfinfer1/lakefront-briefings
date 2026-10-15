#!/usr/bin/env python3
"""Fill Jack's COT card template (1200x675) and render at 2x.
Usage: python3 chart.py DATA_JSON OUT_DIR -> chart.html, chart.png
"""
import datetime, html, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))

def main(dp, out):
    d = json.load(open(dp)); t = open(os.path.join(HERE, "template_original.html")).read()
    a = t.index("<tbody>") + len("<tbody>"); b = t.index("</tbody>")
    body, sector = [], None
    for m in d["markets"]:
        if m["sector"] != sector:
            if sector: body.append("")
            sector = m["sector"]; body.append(f'<tr class="sector-row"><td colspan="5">{sector}</td></tr>')
        net_cls = "pos" if m["net"] >= 0 else "neg"
        chg_cls, arrow = ("pos", "&#9650;") if m["chg"] >= 0 else ("neg", "&#9660;")
        flows = f'<span class="{chg_cls}">{html.escape(m["flows"])}</span>' if m["flows"] else ""
        body.append(f'<tr class="mkt-row"><td class="mkt-name">{html.escape(m["market"])}</td><td class="num {net_cls}">{m["net"]:+,}</td>'
                    f'<td class="num chg {chg_cls}">{arrow} {abs(m["chg"]):,}</td><td class="num oi">{m["oi"]:,}</td><td class="notable">{flows}</td></tr>')
    t = t[:a] + "\n" + "\n".join(body) + "\n" + t[b:]
    asof = datetime.date.fromisoformat(d["as_of"])
    old = '<div class="header-date">Week Ending<br>September 29, 2026</div>'
    if t.count(old) != 1: sys.exit("TEMPLATE CHANGED: header date")
    t = t.replace(old, f'<div class="header-date">Week Ending<br>{asof.strftime("%B")} {asof.day}, {asof.year}</div>')
    os.makedirs(out, exist_ok=True); hp = os.path.join(out, "chart.html"); open(hp, "w").write(t)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1200, "height": 675}, device_scale_factor=2)
        pg.goto("file://" + os.path.abspath(hp)); pg.wait_for_timeout(400)
        pg.screenshot(path=os.path.join(out, "chart.png"), clip={"x": 0, "y": 0, "width": 1200, "height": 675}); br.close()
    print("OK", os.path.join(out, "chart.png"))

if __name__ == "__main__":
    main(*sys.argv[1:3])
