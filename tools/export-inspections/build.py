#!/usr/bin/env python3
"""Lakefront USDA Export Inspections builder.

Usage: python3 build.py RAW_REPORT.txt OUT_DIR

Parses the USDA AMS WA_GR101 text report, validates the numbers against the
report's own totals, then writes:
  chart.png      branded chart (Lakefront template)
  social.txt     X/Buffer post
  numbers.txt    Brevo "numbers" block (headline + date + numbers)
  data.json      every figure the commentary is allowed to use
Exits non-zero if any validation check fails, so a bad pull never gets posted.
"""
import json, math, os, re, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BU_PER_MT = {"SOYBEANS": 36.7437, "WHEAT": 36.7437, "CORN": 39.3679}
GRAINS = ["SOYBEANS", "CORN", "WHEAT"]

def num(s): return int(s.replace(",", ""))

def fail(msg):
    print("VALIDATION FAILED: " + msg, file=sys.stderr); sys.exit(2)

def parse(raw):
    m = re.search(r"WEEK ENDING\s+([A-Z]{3}\s+\d{2},\s+\d{4})", raw)
    if not m: fail("week-ending date not found in header")
    week_end = datetime.datetime.strptime(m.group(1).title(), "%b %d, %Y").date()
    rel = re.search(r"(Mon|Tue|Wed|Thu|Fri)\s+([A-Z][a-z]{2})\s+(\d{1,2}),\s+(\d{4})", raw)
    release = datetime.datetime.strptime(" ".join(rel.groups()[1:]), "%b %d %Y").date() if rel else None

    hdr = re.search(r"GRAIN\s+(\d\d/\d\d/\d{4})\s+(\d\d/\d\d/\d{4})\s+(\d\d/\d\d/\d{4})", raw)
    if not hdr: fail("summary table header not found")
    cols = hdr.groups()

    summary = {}
    for g in GRAINS:
        r = re.search(rf"^{g}\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)", raw, re.M)
        if not r: fail(f"{g} summary row not found")
        cur, prev, yago, myd, pmyd = map(num, r.groups())
        summary[g] = dict(week=cur, prev_week=prev, year_ago=yago, my_to_date=myd, prior_my_to_date=pmyd)

    # Country-of-destination table (by region)
    sec = raw.split("BY REGION AND COUNTRY OF DESTINATION", 1)
    if len(sec) < 2: fail("country-of-destination table not found")
    body = sec[1]
    # Column set varies week to week (USDA drops all-zero columns such as BARLEY),
    # so read the column names from the table header instead of assuming positions.
    hm = re.search(r"^\s*REGION\s+COUNTRY\s+(.+?)\s*$", body, re.M)
    if not hm: fail("country table header not found")
    names = hm.group(1).split()
    if not names or names[-1] != "TOTALS": fail(f"unexpected country table header: {names}")
    ncol = len(names)
    for need in ("WHEAT", "YELLOW", "WHITE", "SOYBEANS"):
        if need not in names: fail(f"country table missing column {need}: {names}")
    row_re = re.compile(r"^\s*(?:(ATLANTIC|GULF|PACIFIC|INTERIOR|ST LAWR SWY|LAKES)\s+)?([A-Z][A-Z .'&-]*?)\s{2,}" + r"\s+".join([r"([\d,]+)"]*ncol) + r"\s*$", re.M)
    dest = {g: {} for g in GRAINS}
    region_sum = [0]*ncol
    subtotal_sum = [0]*ncol
    grand = None
    for mm in row_re.finditer(body):
        name = mm.group(2).strip()
        vals = [num(v) for v in mm.groups()[2:]]
        if name == "SUBTOTAL":
            if vals != region_sum: fail(f"region subtotal mismatch: rows {region_sum} vs subtotal {vals}")
            subtotal_sum = [a+b for a, b in zip(subtotal_sum, vals)]
            region_sum = [0]*ncol
            continue
        if name == "TOTAL":
            grand = vals; break
        region_sum = [a+b for a, b in zip(region_sum, vals)]
        col = dict(zip(names, vals))
        if sum(vals[:-1]) != vals[-1]: fail(f"row total mismatch for {name}")
        for g, v in (("WHEAT", col["WHEAT"]), ("CORN", col["YELLOW"]+col["WHITE"]), ("SOYBEANS", col["SOYBEANS"])):
            if v: dest[g][name] = dest[g].get(name, 0) + v
    if grand is None: fail("country table TOTAL row not found")
    if grand != subtotal_sum: fail("grand total does not equal sum of region subtotals")
    gcol = dict(zip(names, grand))
    checks = {"WHEAT": gcol["WHEAT"], "CORN": gcol["YELLOW"]+gcol["WHITE"], "SOYBEANS": gcol["SOYBEANS"]}
    for g in GRAINS:
        if checks[g] != summary[g]["week"]:
            fail(f"{g}: destination table total {checks[g]:,} != summary {summary[g]['week']:,}")
    top = {g: sorted(dest[g].items(), key=lambda kv: -kv[1])[:3] for g in GRAINS}
    return week_end, release, cols, summary, top

def pct(a, b): return None if not b else round((a-b)/b*100, 1)

def mbu(g, mt): return mt * BU_PER_MT[g] / 1e6

def nice_country(c):
    special = {"KOREA REP": "South Korea", "HONG KONG": "Hong Kong", "COSTA RICA": "Costa Rica"}
    return special.get(c, c.title())

def build_html(week_end, cols, summary, top):
    tmpl = open(os.path.join(HERE, "template_original.html")).read()
    style = re.search(r"<style>.*?</style>", tmpl, re.S).group(0)
    logo = open(os.path.join(HERE, "logo.b64")).read().strip()
    cur_lbl = datetime.datetime.strptime(cols[0], "%m/%d/%Y").strftime("%m/%d/%y")
    prev_lbl = datetime.datetime.strptime(cols[1], "%m/%d/%Y").strftime("%m/%d/%y")
    peak = max(max(summary[g]["week"], summary[g]["prev_week"]) for g in GRAINS)
    ymax = max(2_000_000, math.ceil(peak/500_000)*500_000)
    ticks = "".join(f"<span>{int(ymax*k/4):,}</span>" for k in (4, 3, 2, 1, 0))
    plot_h = 396
    h = lambda v: round(v/ymax*plot_h)
    pos = {"SOYBEANS": "14%", "CORN": "46%", "WHEAT": "80%"}
    bars = ""
    for g in GRAINS:
        s = summary[g]
        bars += f'''<div class="bgroup" style="left: calc({pos[g]} - 150px);">
        <div class="bbar bbar-current" style="height:{h(s["week"])}px"><div class="bval">{s["week"]:,}</div></div>
        <div class="bbar bbar-previous" style="height:{h(s["prev_week"])}px"><div class="bval">{s["prev_week"]:,}</div></div>
        <div class="bcat">{g.title()}</div></div>'''
    emoji = {"SOYBEANS": "🫘", "CORN": "🌽", "WHEAT": "🌾"}
    cards = ""
    for g in GRAINS:
        lead = top[g][0][1] if top[g] else 1
        rows = "".join(f'''<div class="drow"><div class="drow-top"><span>{nice_country(c)}</span><span>{v:,}</span></div>
          <div class="dbar-track"><div class="dbar-fill" style="width:{v/lead*100:.1f}%"></div></div></div>''' for c, v in top[g])
        cards += f'<div class="dcard"><div class="dcard-head"><span class="emoji">{emoji[g]}</span><h3>{g.title()}</h3></div>{rows}</div>'
    date_txt = week_end.strftime("%B ") + str(week_end.day) + week_end.strftime(", %Y")
    return f'''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>USDA Weekly Grain Export Inspections</title>{style}</head>
<body><div class="wrapper" id="chart-wrapper">
<div class="header"><span class="date-line">Week Ending {date_txt}</span><h1>Export Inspections</h1>
<img class="logo" src="{logo}" alt="Lakefront Futures"></div>
<div class="legend"><div class="legend-item"><span class="dot dot-current"></span>Week ending {cur_lbl}</div>
<div class="legend-item"><span class="dot dot-previous"></span>Week ending {prev_lbl}</div></div>
<div class="chart-section"><div class="y-label-col"><span class="y-label-text">tons of exports weighted</span></div>
<div class="y-ticks-col">{ticks}</div>
<div class="chart-plot"><div class="hline" style="bottom:25%"></div><div class="hline" style="bottom:50%"></div>
<div class="hline" style="bottom:75%"></div><div class="hline" style="bottom:100%"></div>{bars}</div></div>
<div class="chart-note">Note: Figures are weighed in Metric Tons. Source USDA</div>
<div class="divider"><h2>TOP GRAIN EXPORT DESTINATIONS (Metric Tons)</h2></div>
<div class="dest-section">{cards}</div></div></body></html>''', date_txt

def render_png(html_path, png_path):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1456, "height": 1200}, device_scale_factor=2)
        pg.goto("file://" + html_path); pg.wait_for_timeout(300)
        pg.locator("#chart-wrapper").screenshot(path=png_path)
        b.close()

def main(raw_path, out):
    os.makedirs(out, exist_ok=True)
    week_end, release, cols, summary, top = parse(open(raw_path).read())
    html, date_txt = build_html(week_end, cols, summary, top)
    hp = os.path.abspath(os.path.join(out, "chart.html")); open(hp, "w").write(html)
    render_png(hp, os.path.join(out, "chart.png"))

    m = {g: f"{mbu(g, summary[g]['week']):.3f}" for g in GRAINS}
    social = (f"USDA Weekly Grain Export Inspections\n\n#Soybeans🫘: {m['SOYBEANS']} mbu\n\n"
              f"#corn🌽: {m['CORN']} mbu\n\n#wheat🌾: {m['WHEAT']} mbu\n\n"
              f"https://www.lakefrontfutures.com/briefing/\n\n#USDA #exports #exportinspections #grains\n")
    numbers = (f"USDA Weekly Export Inspections\nWeek Ending {date_txt}\n\n"
               f"Soybeans🫘: {m['SOYBEANS']} mbu\nCorn🌽: {m['CORN']} mbu\nWheat🌾: {m['WHEAT']} mbu\n")
    open(os.path.join(out, "social.txt"), "w").write(social)
    open(os.path.join(out, "numbers.txt"), "w").write(numbers)

    data = {"release_date": str(release), "week_ending": str(week_end), "columns": cols,
            "marketing_years": {"CORN": "begins Sep 1", "SOYBEANS": "begins Sep 1", "WHEAT": "begins Jun 1"}, "grains": {}}
    for g in GRAINS:
        s = summary[g]
        data["grains"][g] = dict(s, mbu=float(m[g]),
            wow_pct=pct(s["week"], s["prev_week"]), yoy_pct=pct(s["week"], s["year_ago"]),
            my_pace_vs_prior_pct=pct(s["my_to_date"], s["prior_my_to_date"]),
            top_destinations=[{"country": nice_country(c), "mt": v} for c, v in top[g]])
    json.dump(data, open(os.path.join(out, "data.json"), "w"), indent=2, ensure_ascii=False)
    print("OK: all totals reconcile")
    print(social); print(numbers); print(json.dumps(data["grains"], indent=1, ensure_ascii=False))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
