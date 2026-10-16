#!/usr/bin/env python3
"""Weekly "Reports Coming Out This Week" graphic + post (social only, no email).
Usage: python3 build.py CALENDAR_JSON MONDAY(YYYY-MM-DD) OUT_DIR -> chart.png, social.txt, week.json
CALENDAR_JSON from parse_calendar.py (Jack's trading calendar PDF).
Adds the weekly reports Lakefront posts that the calendar leaves out: Ethanol Report with EIA Energy
Stocks, and on Friday Weekly Cattle/Hog Slaughter 1:00 and Commitment of Traders 2:30.
"""
import base64, datetime, html, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
WEEKLY = {"Export Inspections", "Crop Progress", "API Energy Stocks", "EIA Energy Stocks", "Ethanol Report",
          "Jobless Claims", "Export Sales", "EIA Gas Storage", "Weekly Cattle Slaughter", "Weekly Hog Slaughter",
          "Commitment of Traders", "Dairy Products Sales"}
COVERED = ["Export Inspections", "Crop Progress", "EIA Energy Stocks", "Ethanol Report", "Dairy Products Sales",
           "Export Sales", "EIA Gas Storage", "Weekly Cattle Slaughter", "Weekly Hog Slaughter", "Commitment of Traders",
           "Cattle On Feed", "Livestock Slaughter", "USDA Supply/Demand", "WASDE", "Crop Production",
           "EIA Short Term Energy Outlook", "Fats & Oils", "Grain Crushings", "Cattle", "Hogs & Pigs", "Hogs and Pigs",
           "Grain Stocks", "Planted Acreage", "Prospective Plantings", "Winter Wheat Seedings", "Small Grains Summary",
           "US Trade Balance"]
US_HOLIDAYS = {"NEW YEAR": "New Year's Day", "MARTIN LUTHER KING": "MLK Day", "PRESIDENTS": "Presidents Day",
               "GOOD FRIDAY": "Good Friday", "MEMORIAL DAY": "Memorial Day", "JUNETEENTH": "Juneteenth",
               "INDEPENDENCE DAY": "Independence Day", "LABOR DAY": "Labor Day", "COLUMBUS DAY": "Columbus Day",
               "VETERANS DAY": "Veterans Day", "THANKSGIVING DAY": "Thanksgiving", "CHRISTMAS": "Christmas"}
CLOSED = {"New Year's Day", "MLK Day", "Presidents Day", "Good Friday", "Memorial Day", "Juneteenth",
          "Independence Day", "Labor Day", "Thanksgiving", "Christmas"}
DAYN = ["Mon", "Tue", "Wed", "Thu", "Fri"]; DAYL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

def minutes(t):
    if not t: return 10**4
    h, m = map(int, t.split(":")); h = h + 12 if h < 7 else h   # 1:00-6:59 are afternoon
    return h * 60 + m

def us_holiday(hs):
    s = " ".join(hs).upper()
    for k, v in US_HOLIDAYS.items():
        if k in s and not (k == "THANKSGIVING DAY" and "CANADA" in s and "THANKSGIVING DAY" not in s): return v
    return None

def main(cp, monday, out):
    cal = json.load(open(cp)); mon = datetime.date.fromisoformat(monday)
    days = []
    for i in range(5):
        d = mon + datetime.timedelta(i); e = cal.get(str(d), {"holidays": [], "reports": []})
        hol = us_holiday(e.get("holidays", []))
        reps = [r for r in e["reports"] if r["time"] or r["name"] in ("EIA Short Term Energy Outlook",)]
        reps = [{"name": "Commitment of Traders" if r["name"].lower().startswith("commitment") else r["name"], "time": r["time"]} for r in reps]
        if any(r["name"] == "EIA Energy Stocks" for r in reps) and not any(r["name"].startswith("Ethanol") for r in reps):
            t = next(r["time"] for r in reps if r["name"] == "EIA Energy Stocks"); reps.append({"name": "Ethanol Report", "time": t})
        if i == 4 and hol not in CLOSED:
            names = {r["name"] for r in reps}
            for n, t in [("Weekly Cattle Slaughter", "1:00"), ("Weekly Hog Slaughter", "1:00"), ("Commitment of Traders", "2:30")]:
                if n not in names: reps.append({"name": n, "time": t})
        reps.sort(key=lambda r: (minutes(r["time"]), r["name"]))
        days.append({"date": str(d), "holiday": hol, "reports": reps})
    counts = [len(x["reports"]) for x in days]; heavy = counts.index(max(counts)) if max(counts) >= 5 else None

    cards = []
    for i, x in enumerate(days):
        d = datetime.date.fromisoformat(x["date"]); body = []
        if x["holiday"]: body.append(f'<div class="holiday-note">🇺🇸 {html.escape(x["holiday"])}</div>')
        for r in x["reports"]:
            cls = "report-item" if r["name"] in WEEKLY else "report-item monthly"
            body.append(f'<div class="{cls}"><span class="report-time">{r["time"] or ""}</span><span class="report-name">{html.escape(r["name"])}</span></div>')
        if not x["reports"]: body.append('<div class="no-reports">No reports scheduled</div>')
        if i == heavy: body.append('<div class="heavy-tag">📅 Heavy day</div>')
        cards.append(f'<div class="day-card"><div class="day-header"><span class="day-name">{DAYN[i]}</span>'
                     f'<span class="day-date">{d.day}</span></div><div class="day-body">{"".join(body)}</div></div>')
    t = open(os.path.join(HERE, "template_original.html"), encoding="utf-8").read()
    a = t.index('<div class="week-grid">') + len('<div class="week-grid">'); b = t.index('</div>\n  </div>\n  <div class="footer">')
    t = t[:a] + "\n" + "\n".join(cards) + "\n    " + t[b:]
    fri = mon + datetime.timedelta(4)
    rng = f"{mon.strftime('%B')} {mon.day}–{fri.day}, {fri.year}" if mon.month == fri.month else f"{mon.strftime('%B')} {mon.day} – {fri.strftime('%B')} {fri.day}, {fri.year}"
    t = re.sub(r'<span class="header-date">[^<]*</span>', f'<span class="header-date">{rng} CST</span>', t, count=1)
    fonts = "".join(f"@font-face{{font-family:'DM Sans';font-weight:{w};src:url(data:font/woff2;base64,"
                    f"{base64.b64encode(open(os.path.join(HERE, f'dm-sans-latin-{w}-normal.woff2'), 'rb').read()).decode()}) format('woff2')}}"
                    for w in (400, 500, 600, 700))
    t = re.sub(r'<link href="https://fonts.googleapis.com[^>]*>', "", t).replace("<style>", "<style>" + fonts, 1)
    os.makedirs(out, exist_ok=True); hp = os.path.join(out, "chart.html"); open(hp, "w", encoding="utf-8").write(t)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1120, "height": 800}, device_scale_factor=2)
        pg.goto("file://" + os.path.abspath(hp)); pg.wait_for_timeout(500)
        pg.locator(".container").screenshot(path=os.path.join(out, "chart.png")); br.close()

    # post text (Jack's 8/31 format)
    short = lambda d: f"{d.strftime('%b')} {d.day}"
    rng2 = f"{short(mon)}–{fri.day}" if mon.month == fri.month else f"{short(mon)}–{short(fri)}"
    hits = []
    for i, x in enumerate(days):
        ns = [r["name"] for r in x["reports"] if r["name"] not in WEEKLY and r["name"] in COVERED]
        if ns: hits.append((" and ".join(ns) if len(ns) < 3 else ", ".join(ns[:-1]) + " and " + ns[-1]) + " " + DAYL[i])
    hol = [f'{x["holiday"]} {DAYL[i]}' for i, x in enumerate(days) if x["holiday"]]
    line = ", ".join(hits) + "." if hits else ""
    if hol: line = (line + " " if line else "") + "Markets observe " + ", ".join(hol) + "."
    social = f"📊 Reports Coming Out This Week ({rng2})\n\n" + (line + "\n\n" if line else "") + "Stay informed by subscribing to lakefrontfutures.com/briefing/\n"
    open(os.path.join(out, "social.txt"), "w").write(social)
    json.dump(days, open(os.path.join(out, "week.json"), "w"), indent=1)
    print("OK"); print(social)

if __name__ == "__main__":
    main(*sys.argv[1:4])
