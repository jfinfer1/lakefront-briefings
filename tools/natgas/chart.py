#!/usr/bin/env python3
"""Render Jack's nat gas storage chart from data.json (tools/natgas/data.py output).
Usage: python3 chart.py DATA_JSON OUT_DIR  -> chart.html, chart.png"""
import datetime, json, math, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))

def m_of(d):  # month position 0..12 used by the template's x axis
    start = datetime.date(d.year, 1, 1)
    days = (datetime.date(d.year + 1, 1, 1) - start).days
    return round((d - start).days / days * 12, 3)

def main(dp, out):
    d = json.load(open(dp)); s = d["series"]
    wk = datetime.date.fromisoformat(d["week_ending"]); yr = wk.year
    rel = datetime.datetime.strptime(d["release_date"], "%Y-%b-%d").date()
    dts = [datetime.date.fromisoformat(x) for x in s["dates"]]
    pts = lambda arr: [{"m": m_of(dt), "v": v} for dt, v in zip(dts, arr) if v is not None]
    cur, prev, avg = pts(s["this_year"]), pts(s["last_year"]), pts(s["avg5"])
    top, bot = pts(s["max5"]), pts(s["min5"])
    allv = [p["v"] for p in cur + prev + avg + top + bot]
    ymin = math.floor((min(allv) - 150) / 500) * 500; ymax = math.ceil((max(allv) + 100) / 250) * 250
    ticks = list(range(ymin + 500 if ymin % 500 else ymin, ymax + 1, 500))
    js = lambda a: json.dumps(a, separators=(",", ":")).replace('"m"', "m").replace('"v"', "v")

    t = open(os.path.join(HERE, "template_original.html"), encoding="utf-8").read()
    t = re.sub(r"const seasonal = \{.*?\n\};", f"const seasonal = {{\n  curr2026: {js(cur)},\n  prev2025: {js(prev)},\n  avg5yr: {js(avg)}\n}};", t, count=1, flags=re.S)
    t = re.sub(r"const bandT = \[.*?\];", f"const bandT = {js(top)};", t, count=1, flags=re.S)
    t = re.sub(r"const bandB = \[.*?\];", f"const bandB = {js(bot)};", t, count=1, flags=re.S)
    t = re.sub(r"const yMin\s*=\s*\d+, yMax = \d+;", f"const yMin  = {ymin}, yMax = {ymax};", t, count=1)
    t = re.sub(r"\[1500, 2000, 2500, 3000, 3500\]\.forEach", f"{ticks}.forEach", t, count=1)
    t = re.sub(r"lt\.textContent = '[\d,]+ Bcf';", f"lt.textContent = '{d['storage_bcf']:,} Bcf';", t, count=1)
    t = re.sub(r'(<div class="rd-value">).*?(</div>)', rf"\g<1>{rel.strftime('%B')} {rel.day}, {rel.year}\g<2>", t, count=1)
    t = t.replace(">2026</div>", f">{yr}</div>", 1).replace(">2025</div>", f">{yr-1}</div>", 1)

    sg = lambda x: f"+{x:,}" if x >= 0 else f"−{abs(x):,}"
    cls = lambda x: "pos" if x >= 0 else "neg"
    i = s["dates"].index(d["week_ending"])
    cells = [
        ("Current Storage", "", f"{d['storage_bcf']:,}", f"Bcf, week of {wk.month}/{wk.day}/{str(yr)[2:]}"),
        ("Weekly Injection" if d["net_change"] >= 0 else "Weekly Withdrawal", cls(d["net_change"]), sg(d["net_change"]), "Bcf vs prior week"),
        ("Year-Over-Year", cls(d["vs_year_ago"]), sg(d["vs_year_ago"]),
         f"Bcf, {sg(d['vs_year_ago_pct'])}% {'above' if d['vs_year_ago'] >= 0 else 'below'} LY"),
        ("vs 5-Yr Average", cls(d["vs_5yr"]), sg(d["vs_5yr"]),
         f"Bcf, {sg(d['vs_5yr_pct'])}% {'above' if d['vs_5yr'] >= 0 else 'below'} avg"),
        ("5-Yr Week Range", "", f"{s['min5'][i]:,}", f"min, {s['max5'][i]:,} max"),
    ]
    strip = "".join(f'\n    <div class="stat-cell">\n      <div class="sc-label">{a}</div>\n      <div class="sc-value{(" " + c) if c else ""}">{v}</div>\n      <div class="sc-unit">{u}</div>\n    </div>' for a, c, v, u in cells)
    t = re.sub(r'(<div class="stats-strip">).*?(\n  </div>\n\n  <!-- FOOTER -->)', lambda m: m.group(1) + strip + m.group(2), t, count=1, flags=re.S)

    os.makedirs(out, exist_ok=True)
    hp = os.path.abspath(os.path.join(out, "chart.html")); open(hp, "w", encoding="utf-8").write(t)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 675}, device_scale_factor=2)
        pg.goto("file://" + hp); pg.wait_for_timeout(800)
        pg.locator("#chart-wrapper").screenshot(path=os.path.join(out, "chart.png")); b.close()
    print("OK chart", ymin, ymax)

if __name__ == "__main__":
    main(*sys.argv[1:3])
