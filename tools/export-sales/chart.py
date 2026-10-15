#!/usr/bin/env python3
"""Fill Jack's Grain Export Sales chart template (1200x675) and render at 2x.
Usage: python3 chart.py DATA_JSON OUT_DIR -> chart.html, chart.png
Bars = this week's and last week's "Current" marketing year net sales (MT).
"""
import datetime, json, math, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NAMES = {"Korea": "South Korea"}
PLOT_PX = 266.8   # template: 1,100,000 MT = full plot height

def main(dp, out):
    d = json.load(open(dp)); S, P = d["summary"], d["prev_summary"]
    t = open(os.path.join(HERE, "template_original.html")).read()
    we, pw = datetime.date.fromisoformat(d["week_ending"]), datetime.date.fromisoformat(d["prev_week_ending"])
    def rep(old, new):
        nonlocal t
        if t.count(old) != 1: sys.exit(f"TEMPLATE CHANGED: {old[:70]!r} x{t.count(old)}")
        t = t.replace(old, new)
    rep('<div class="value">September 24, 2026</div>', f'<div class="value">{we.strftime("%B")} {we.day}, {we.year}</div>')
    rep('Week ending 09/24/26</div>', f'Week ending {we.strftime("%m/%d/%y")}</div>')
    rep('Week ending 09/17/26</div>', f'Week ending {pw.strftime("%m/%d/%y")}</div>')
    vals = [S[c]["current"] for c in S] + [P[c]["current"] for c in P]
    step = max(25000, math.ceil(max(vals) * 1.06 / 4 / 25000) * 25000); top = step * 4
    rep('<span>1,100,000</span><span>825,000</span><span>550,000</span><span>275,000</span><span>0</span>',
        "".join(f"<span>{step * k:,}</span>" for k in (4, 3, 2, 1, 0)))
    h = lambda v: f"{max(v, 0) / top * PLOT_PX:.0f}px"
    old_bars = [("535,989", "130px", "838,328", "203px"), ("1,033,545", "250px", "582,432", "141px"), ("289,255", "70px", "267,553", "65px")]
    for c, (a, ah, b, bh) in zip(["corn", "soybeans", "wheat"], old_bars):
        rep(f'<div class="bbar bbar-current" style="height:{ah}"><div class="bval">{a}</div>',
            f'<div class="bbar bbar-current" style="height:{h(S[c]["current"])}"><div class="bval">{S[c]["current"]:,}</div>')
        rep(f'<div class="bbar bbar-previous" style="height:{bh}"><div class="bval">{b}</div>',
            f'<div class="bbar bbar-previous" style="height:{h(P[c]["current"])}"><div class="bval">{P[c]["current"]:,}</div>')
    # destination cards: replace the three drow blocks inside each dcard
    cards = re.findall(r'(<div class="dcard-head">.*?</h3></div>)((?:\s*<div class="drow">.*?</div></div></div>){3})', t, flags=re.S)
    if len(cards) != 3: sys.exit("TEMPLATE CHANGED: destination cards")
    for (head, rows), c in zip(cards, ["corn", "soybeans", "wheat"]):
        tops = d["top3"][c]; mx = max(r[1] for r in tops) or 1
        new = "".join(f'\n      <div class="drow"><div class="drow-top"><span>{NAMES.get(r[0], r[0])}</span><span>{r[1]:,}</span></div>'
                      f'<div class="dbar-track"><div class="dbar-fill" style="width:{max(r[1], 0) / mx * 100:.1f}%"></div></div></div>' for r in tops)
        t = t.replace(head + rows, head + new, 1)
    os.makedirs(out, exist_ok=True); hp = os.path.join(out, "chart.html"); open(hp, "w").write(t)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1200, "height": 675}, device_scale_factor=2)
        pg.goto("file://" + os.path.abspath(hp)); pg.wait_for_timeout(500)
        pg.screenshot(path=os.path.join(out, "chart.png"), clip={"x": 0, "y": 0, "width": 1200, "height": 675}); br.close()
    print("OK", os.path.join(out, "chart.png"))

if __name__ == "__main__":
    main(*sys.argv[1:3])
