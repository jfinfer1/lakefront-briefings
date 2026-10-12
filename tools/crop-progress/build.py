#!/usr/bin/env python3
"""Lakefront Crop Progress builder (harvest season, corn + soybeans maps).

Usage: python3 build.py DATA_JSON OUT_DIR

DATA_JSON:
{
  "release_date": "2026-10-13",            # report release day (header date)
  "week_ending": "2026-10-11",
  "corn":     {"states": {"Illinois": 36, ...}, "national": 23, "prev": 18, "avg": 27},
  "soybeans": {"states": {...},             "national": 25, "prev": 17, "avg": 33},
  "email_lines": ["Corn Mature: 83% (5yr avg 83%)", ...]   # numbers block, in order
}
State values are % harvested this week. "-" in the report means 0.
Writes chart.html, chart.png, social.txt, numbers.txt. Exits non-zero on bad data.
"""
import datetime, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Path order in the template SVGs: alphabetical by state name, DC last (verified by render).
ORDER = ["Alabama","Arizona","Arkansas","California","Colorado","Connecticut","Delaware","Florida","Georgia",
 "Idaho","Illinois","Indiana","Iowa","Kansas","Kentucky","Louisiana","Maine","Maryland","Massachusetts",
 "Michigan","Minnesota","Mississippi","Missouri","Montana","Nebraska","Nevada","New Hampshire","New Jersey",
 "New Mexico","New York","North Carolina","North Dakota","Ohio","Oklahoma","Oregon","Pennsylvania",
 "Rhode Island","South Carolina","South Dakota","Tennessee","Texas","Utah","Vermont","Virginia","Washington",
 "West Virginia","Wisconsin","Wyoming","District of Columbia"]
# Color ramps reverse engineered from the 10/5 chart: stops at 0/20/40/80%, values above 80 capped.
RAMPS = {
 "corn": [(0,(225,235,215)),(20,(162,205,140)),(40,(100,175,65)),(80,(25,105,30))],
 "soybeans": [(0,(245,230,195)),(20,(222,195,122)),(40,(200,160,50)),(80,(135,90,15))],
}

def fail(m): print("VALIDATION FAILED: " + m, file=sys.stderr); sys.exit(2)

def color(crop, v):
    stops = RAMPS[crop]; v = max(0, min(v, stops[-1][0]))
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if v <= b:
            t = (v - a) / (b - a)
            return "rgb(%d,%d,%d)" % tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))

def fmt_date(d): return d.strftime("%B ") + str(d.day) + d.strftime(", %Y")

def main(data_path, out):
    d = json.load(open(data_path))
    rel = datetime.date.fromisoformat(d["release_date"]); wk = datetime.date.fromisoformat(d["week_ending"])
    if not (0 <= (rel - wk).days <= 3): fail("release date and week ending are not 0-3 days apart")
    for crop in ("corn", "soybeans"):
        c = d[crop]
        for st, v in c["states"].items():
            if st not in ORDER: fail(f"unknown state {st}")
            if not (0 <= v <= 100): fail(f"{crop} {st} out of range: {v}")
        if not (c["prev"] <= c["national"] <= 100): fail(f"{crop} national {c['national']} below last week {c['prev']}")
        if len(c["states"]) < 15: fail(f"{crop}: only {len(c['states'])} states, expected 18")

    t = open(os.path.join(HERE, "template_original.html"), encoding="utf-8").read()
    # header
    t = re.sub(r'<div class="hd-date">.*?</div>', f'<div class="hd-date">{fmt_date(rel)}</div>', t, count=1)
    t = re.sub(r'<div class="hd-week">.*?</div>', f'<div class="hd-week">Week ending {wk.strftime("%B ")}{wk.day}</div>', t, count=1)
    # maps: recolor every state path in each SVG (corn first, soybeans second)
    parts = re.split(r'(<svg viewBox="0 0 959 593"[^>]*>.*?</svg>)', t, flags=re.S)
    svg_idx = [i for i, p in enumerate(parts) if p.startswith("<svg")]
    if len(svg_idx) != 2: fail("template does not have exactly two maps")
    for crop, i in zip(("corn", "soybeans"), svg_idx):
        vals = d[crop]["states"]; n = [0]
        def repl(m):
            st = ORDER[n[0]]; n[0] += 1
            if st in vals:
                return f'<path d="{m.group(1)}" fill="{color(crop, vals[st])}" stroke="#3a3a5c" stroke-width="0.6" stroke-linejoin="round"/>'
            return f'<path d="{m.group(1)}" fill="#eaeaea" stroke="#bbb" stroke-width="0.4" stroke-linejoin="round"/>'
        parts[i] = re.sub(r'<path d="([^"]+)" fill="(?:#eaeaea|rgb\([^)]+\))"[^>]*/>', repl, parts[i])
        if n[0] != len(ORDER): fail(f"{crop} map has {n[0]} state paths, expected {len(ORDER)}")
    t = "".join(parts)
    # harvest bars (corn block first, soybeans second)
    blocks = list(re.finditer(r'<div class="ge">.*?</div>\s*</div>', t, re.S))
    if len(blocks) != 2: fail("expected two harvest bars")
    for crop, m in reversed(list(zip(("corn", "soybeans"), blocks))):
        c = d[crop]; b = m.group(0)
        b = re.sub(r'<div class="ge-val">.*?</div>', f'<div class="ge-val">{c["national"]}% Harvested</div>', b)
        b = re.sub(r'width:\d+%;background:(#[0-9a-f]{6});border-radius', f'width:{c["national"]}%;background:\\1;border-radius', b, count=1)
        b = re.sub(r'width:\d+%;background:#e0ddd6', f'width:{100-c["national"]}%;background:#e0ddd6', b)
        b = re.sub(r'<div class="ge-sub">.*?</div>', f'<div class="ge-sub">5yr avg: {c["avg"]}% · Prev week: {c["prev"]}%</div>', b)
        t = t[:m.start()] + b + t[m.end():]

    os.makedirs(out, exist_ok=True)
    hp = os.path.abspath(os.path.join(out, "chart.html")); open(hp, "w", encoding="utf-8").write(t)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1000, "height": 900}, device_scale_factor=3)
        pg.goto("file://" + hp); pg.wait_for_timeout(1500)
        h = pg.evaluate("document.querySelector('.card').getBoundingClientRect().height")
        pg.set_viewport_size({"width": 1000, "height": int(h) + 40})
        pg.locator(".card").screenshot(path=os.path.join(out, "chart.png")); br.close()

    c, s = d["corn"], d["soybeans"]
    def rel_word(x, a): return "ahead of" if x > a else ("behind" if x < a else "even with")
    social = ("Crop Progress:\n\n"
              f"🌾 Corn harvest {c['national']}%, {rel_word(c['national'], c['avg'])} {c['avg']}% avg\n"
              f"🌱 Soybean harvest {s['national']}%, {rel_word(s['national'], s['avg'])} {s['avg']}% avg\n\n"
              "read more at lakefrontfutures.com/briefing/\n\n#cropprogress #usda #nass\n")
    open(os.path.join(out, "social.txt"), "w", encoding="utf-8").write(social)
    open(os.path.join(out, "numbers.txt"), "w", encoding="utf-8").write("\n".join(d["email_lines"]) + "\n")
    print("OK"); print(social); print("\n".join(d["email_lines"]))

if __name__ == "__main__":
    main(*sys.argv[1:3])
