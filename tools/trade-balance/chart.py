#!/usr/bin/env python3
"""Fill Jack's U.S. Trade Balance chart template (1200x675) and render at 2x.
Usage: python3 chart.py DATA_JSON OUT_DIR -> chart.html, chart.png"""
import datetime, json, math, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))

def sub(html, old, new):
    if html.count(old) != 1: sys.exit(f"TEMPLATE CHANGED: {old!r} found {html.count(old)}x")
    return html.replace(old, new)

def js(s): return json.dumps(s, ensure_ascii=True)

def main(dp, out):
    d = json.load(open(dp)); t = open(os.path.join(HERE, "template_original.html")).read()
    rd = datetime.date.fromisoformat(d["release_date"])
    t = sub(t, '<span class="header-date">August 4, 2026</span>', f'<span class="header-date">{rd.strftime("%B")} {rd.day}, {rd.year}</span>')
    t = sub(t, '<div class="panel-title">June 2026 &nbsp;', f'<div class="panel-title">{d["month"]} &nbsp;')
    t = sub(t, '&nbsp;&nbsp;|&nbsp;&nbsp; June 2026</span>', f'&nbsp;&nbsp;|&nbsp;&nbsp; {d["month"]}</span>')
    rows = ",\n".join(f'          {{ label: {js(x["label"])}, val: {x["chg_b"]}, emoji: {js(x["emoji"])} }}' for x in d["items"])
    new = "var items = [\n" + rows + "\n        ];"; t, n = re.subn(r"var items = \[.*?\];", lambda _: new, t, flags=re.S)
    if n != 1: sys.exit("TEMPLATE CHANGED: items")
    v = [x["chg_b"] for x in d["items"]]
    span = max(v) - min(v); step = 1 if span <= 12 else 2 if span <= 24 else 5
    hi = max(step, math.ceil(max(v) / step) * step + (step if max(v) % step > step * .6 or max(v) % step == 0 else 0))
    lo = min(-step, math.floor(min(v) / step) * step - (step if (-min(v)) % step > step * .6 or min(v) % step == 0 else 0))
    hi = max(hi, max(v) + step * .5); lo = min(lo, min(v) - step * .9)
    hi = math.ceil(hi / step) * step; lo = math.floor(lo / step) * step
    t = sub(t, "var maxVal = 4.0;", f"var maxVal = {hi};"); t = sub(t, "var minVal = -7.0;", f"var minVal = {lo};")
    ticks = list(range(int(lo) + step, int(hi), step))
    t = sub(t, "var yTicks = [-6, -5, -4, -3, -2, -1, 0, 1, 2, 3];", f"var yTicks = {ticks};")
    os.makedirs(out, exist_ok=True); hp = os.path.join(out, "chart.html"); open(hp, "w").write(t)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1200, "height": 675}, device_scale_factor=2)
        pg.goto("file://" + os.path.abspath(hp)); pg.wait_for_timeout(500)
        pg.screenshot(path=os.path.join(out, "chart.png"), clip={"x": 0, "y": 0, "width": 1200, "height": 675}); br.close()
    print("OK", os.path.join(out, "chart.png"))

if __name__ == "__main__":
    main(*sys.argv[1:3])
