#!/usr/bin/env python3
"""Fill Jack's ethanol chart template (1200x675) and render at 2x.
Usage: python3 chart.py DATA_JSON RELEASE_DATE(YYYY-MM-DD) OUT_DIR -> chart.html, chart.png
"""
import datetime, json, math, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))

def sub(html, old, new, count=1):
    if html.count(old) != count: sys.exit(f"TEMPLATE CHANGED: {old!r} found {html.count(old)}x")
    return html.replace(old, new)

def main(dp, rel, out):
    d = json.load(open(dp)); t = open(os.path.join(HERE, "template_original.html")).read()
    fd = lambda x: f"{x.strftime('%B')} {x.day}, {x.year}"
    rd, we = datetime.date.fromisoformat(rel), datetime.date.fromisoformat(d["week_ending"])
    t = sub(t, '<div class="report-date">September 23, 2026</div>', f'<div class="report-date">{fd(rd)}</div>')
    t = sub(t, '<div class="report-week">Week Ending September 18, 2026</div>', f'<div class="report-week">Week Ending {fd(we)}</div>')
    t = sub(t, '1.028<span class="unit">mb/day', f'{d["daily_mbd"]:.3f}<span class="unit">mb/day')
    t = sub(t, '7.196<span class="unit">mil bbl', f'{d["weekly_total_mbbl"]:.3f}<span class="unit">mil bbl')
    t = sub(t, '24.683<span class="unit">mil bbl', f'{d["stocks_mbbl"]:.3f}<span class="unit">mil bbl')
    t = sub(t, 'Most recent: 7.196 mil bbl', f'Most recent: {d["weekly_total_mbbl"]:.3f} mil bbl')
    t = sub(t, 'Most recent: 24.683 mil bbl', f'Most recent: {d["stocks_mbbl"]:.3f} mil bbl')
    t = sub(t, '<span class="pace-val">101.76 <span', f'<span class="pace-val">{d["corn_used_mmbu"]:.2f} <span')
    behind = d["corn_used_mmbu"] < d["corn_needed_mmbu"]
    t = sub(t, '<span class="pace-val behind">107.47 <span', f'<span class="pace-val{" behind" if behind else ""}">{d["corn_needed_mmbu"]:.2f} <span')
    cap = f'Running {abs(d["pace_gap_pct"]):.1f}% {"below" if behind else "above"} needed pace'
    t = sub(t, 'Running 5.3% below needed pace', cap)
    rows = ",\n".join(f'  {{ date: "{r["date"]}", prod: {r["prod"]:.3f}, stocks: {r["stocks"]:.3f} }}' for r in d["chart"])
    t, n = re.subn(r"const weeklyData = \[.*?\];", "const weeklyData = [\n" + rows + ",\n];", t, flags=re.S)
    if n != 1: sys.exit("TEMPLATE CHANGED: weeklyData")
    # keep Jack's fixed axes unless the data falls outside them
    P = [r["prod"] for r in d["chart"]]; S = [r["stocks"] for r in d["chart"]]
    pmin, pmax = min(5.8, math.floor(min(P) * 2) / 2 - 0.5), max(9.0, math.ceil(max(P) * 2) / 2 + 0.5)
    smin, smax = min(23.5, math.floor(min(S) * 2) / 2 - 0.5), max(28.0, math.ceil(max(S) * 2) / 2 + 0.5)
    t = sub(t, "{ minV: 5.8, maxV: 9.0,", f"{{ minV: {pmin}, maxV: {pmax},")
    t = sub(t, "{ minV: 23.5, maxV: 28.0,", f"{{ minV: {smin}, maxV: {smax},")
    os.makedirs(out, exist_ok=True); hp = os.path.join(out, "chart.html"); open(hp, "w").write(t)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1200, "height": 675}, device_scale_factor=2)
        pg.goto("file://" + os.path.abspath(hp)); pg.wait_for_timeout(500)
        pg.screenshot(path=os.path.join(out, "chart.png"), clip={"x": 0, "y": 0, "width": 1200, "height": 675}); br.close()
    print("OK", os.path.join(out, "chart.png"))

if __name__ == "__main__":
    main(*sys.argv[1:4])
