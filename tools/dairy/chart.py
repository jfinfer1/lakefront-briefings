#!/usr/bin/env python3
"""Fill Jack's dairy chart template and render at 2x (Chart.js and Inter inlined, no network).
Usage: python3 chart.py DATA_JSON OUT_DIR -> chart.html, chart.png
"""
import base64, datetime, json, math, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))

def sub(s, old, new):
    if s.count(old) != 1: sys.exit(f"TEMPLATE CHANGED: {old[:60]!r} x{s.count(old)}")
    return s.replace(old, new)

def main(dp, out):
    d = json.load(open(dp)); P = d["products"]; t = open(os.path.join(HERE, "template_original.html")).read()
    fonts = "".join(
        f"@font-face{{font-family:'Inter';font-weight:{w};src:url(data:font/woff2;base64,"
        f"{base64.b64encode(open(os.path.join(HERE, f'inter-latin-{w}-normal.woff2'), 'rb').read()).decode()}) format('woff2')}}"
        for w in (400, 500, 600, 700, 800, 900))
    t = sub(t, "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');", fonts)
    t = sub(t, '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>',
            "<script>" + open(os.path.join(HERE, "chart.umd.js")).read() + "</script>")
    rel = datetime.date.fromisoformat(d["release_date"])
    t = sub(t, '<div class="date">July 8, 2026</div>', f'<div class="date">{rel.strftime("%B")} {rel.day}, {rel.year}</div>')
    chg = lambda c: (f"▲ {c:.1f}¢" if c > 0 else f"▼ {abs(c):.1f}¢" if c < 0 else "UNCH")
    for k, v, c in [("butter", "$1.5808", "▲ 1.5¢"), ("cheddar", "$1.5154", "▼ 1.5¢"), ("ndm", "$1.7912", "▼ 5.3¢")]:
        t = sub(t, f'<div class="card-value">{v}</div><div class="card-change">{c}</div>',
                f'<div class="card-value">${P[k]["prices"][-1]:.4f}</div><div class="card-change">{chg(P[k]["chg_c"])}</div>')
    t = sub(t, "labels:['6/6','6/13','6/20','6/27','7/4']", "labels:[" + ",".join(f"'{l}'" for l in d["labels"]) + "]")
    for k, old in [("butter", "1.6053,1.6618,1.6359,1.5655,1.5808"), ("cheddar", "1.6151,1.5804,1.5370,1.5300,1.5154"),
                   ("ndm", "1.9654,1.9697,1.9206,1.8446,1.7912")]:
        t = sub(t, f"data:[{old}]", "data:[" + ",".join(f"{x:.4f}" for x in P[k]["prices"]) + "]")
    vals = P["butter"]["prices"] + P["cheddar"]["prices"] + P["ndm"]["prices"]
    lo, hi = math.floor(min(vals) * 10) / 10, math.ceil(max(vals) * 10) / 10
    if min(vals) - lo < 0.02: lo -= 0.05
    if hi - max(vals) < 0.02: hi += 0.05
    step = 0.10 if hi - lo > 0.45 else 0.05
    lo, hi = math.floor(round(lo / step, 6)) * step, math.ceil(round(hi / step, 6)) * step
    t = sub(t, "y:{min:1.40,max:2.10,ticks:{stepSize:0.10,", f"y:{{min:{lo:.2f},max:{hi:.2f},ticks:{{stepSize:{step:.2f},")
    t = sub(t, "maintainAspectRatio:false,", "maintainAspectRatio:false,animation:false,")
    os.makedirs(out, exist_ok=True); hp = os.path.join(out, "chart.html"); open(hp, "w").write(t)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 840, "height": 700}, device_scale_factor=2)
        pg.goto("file://" + os.path.abspath(hp)); pg.wait_for_timeout(800)
        h = pg.evaluate("document.body.scrollHeight")
        pg.screenshot(path=os.path.join(out, "chart.png"), clip={"x": 0, "y": 0, "width": 840, "height": h}); br.close()
    print("OK", os.path.join(out, "chart.png"))

if __name__ == "__main__":
    main(*sys.argv[1:3])
