#!/usr/bin/env python3
"""Fill Jack's EIA Energy Stocks chart template and render PNG.
Usage: python3 chart.py DATA_JSON RELEASE_DATE(YYYY-MM-DD) OUT_DIR  -> chart.html, chart.png
"""
import datetime, json, os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))

def card(it):
    def chg(v, unit):
        cls, arr = ("pos", "▲") if v >= 0 else ("neg", "▼")
        return f'<span class="{cls}">{arr} {abs(v):.1f}M {unit}</span>'
    return (f'<div class="mc"><div class="mc-label">{it["label"]}</div><div class="mc-val">{it["level_m"]:.1f}M</div>'
            f'<div class="mc-chg">{chg(it["wk_m"], "wk")}, {chg(it["yr_m"], "yr")}</div></div>')

def svg(it):
    c = it["chart"]; vals = c["this_year"] + c["last_year"]
    lo, hi = min(vals), max(vals); pad = max((hi - lo) * 0.12, 1.0)
    lo, hi = lo - pad, hi + pad
    X = [32, 122, 212, 302]; Y0, Y1 = 112.0, 10.0
    y = lambda v: round(Y0 - (v - lo) / (hi - lo) * (Y0 - Y1), 1)
    o = ['<svg width="310" height="130" xmlns="http://www.w3.org/2000/svg"><rect width="310" height="130" fill="#FAFAFA"/>']
    for k in range(4):
        gy = Y0 - k * (Y0 - Y1) / 3; v = lo + k * (hi - lo) / 3
        o.append(f'<line x1="32" y1="{gy:.1f}" x2="302" y2="{gy:.1f}" stroke="#EEE" stroke-width="0.5"/>'
                 f'<text x="29" y="{gy+2:.1f}" text-anchor="end" font-family="Arial" font-size="7" fill="#888">{v:.0f}</text>')
    for x, d in zip(X, c["dates"]):
        dd = datetime.date.fromisoformat(d)
        o.append(f'<text x="{x}" y="128" text-anchor="middle" font-family="Arial" font-size="7" fill="#888">{dd.month}/{dd.day}</text>')
    o.append('<rect x="0" y="0" width="310" height="130" fill="none" stroke="#E5E7F4" stroke-width="0.5"/>')
    for series, col, w, r in [(c["last_year"], "#8B9DC3", 1.5, 2.5), (c["this_year"], "#2B2D6E", 2.5, 3.5)]:
        pts = " ".join(f"{x},{y(v)}" for x, v in zip(X, series))
        o.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round"/>')
        o += [f'<circle cx="{x}" cy="{y(v)}" r="{r}" fill="{col}"/>' for x, v in zip(X, series)]
    o.append('</svg>')
    return f'<div><div class="chart-title">{it["label"]}</div><div class="chart-wrap">{"".join(o)}</div></div>'

def main(dp, rel, out):
    d = json.load(open(dp)); it = d["items"]
    t = open(os.path.join(HERE, "template_original.html")).read()
    a = t.index('<div class="metrics">'); b = t.index('<div class="legend">')
    mid = ('<div class="metrics">' + "".join(card(it[k]) for k in ["crude", "gasoline", "distillate", "ulsd"]) + '</div>'
           '<div class="charts">' + "".join(svg(it[k]) for k in ["crude", "distillate", "gasoline", "ulsd"]) + '</div>')
    html = t[:a] + mid + t[b:]
    rd = datetime.date.fromisoformat(rel)
    old = 'September 30, 2026</span>'; assert old in html
    html = html.replace(old, f'{rd.strftime("%B")} {rd.day}, {rd.year}</span>')
    yr = int(d["week_ending"][:4])
    html = html.replace("2026 (current)", f"{yr} (current)").replace("2025 (prior year)", f"{yr-1} (prior year)")
    os.makedirs(out, exist_ok=True)
    hp = os.path.join(out, "chart.html"); open(hp, "w").write(html)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 680, "height": 600}, device_scale_factor=2)
        pg.goto("file://" + os.path.abspath(hp)); pg.wait_for_timeout(300)
        pg.locator(".card").screenshot(path=os.path.join(out, "chart.png")); br.close()
    print("OK", os.path.join(out, "chart.png"))

if __name__ == "__main__":
    main(*sys.argv[1:4])
