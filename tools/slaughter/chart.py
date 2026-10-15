#!/usr/bin/env python3
"""Fill Jack's hog / cattle slaughter canvas templates, laid out like the 8/7 posts
(title and release date in the header, legend under it, source left / url right in footer).
Usage: python3 chart.py SPECIES(hogs|cattle) DATA_JSON OUT_PNG
"""
import base64, datetime, json, math, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))

def rep(t, old, new):
    if t.count(old) != 1: sys.exit(f"TEMPLATE CHANGED: {old[:60]!r} x{t.count(old)}")
    return t.replace(old, new)

def main(sp, dp, out):
    d = json.load(open(dp)); s = d["chart"][sp]
    t = open(os.path.join(HERE, f"template_{sp}.html")).read()
    rel = datetime.date.fromisoformat(d["release_date"])
    title = "Weekly Hog Slaughter" if sp == "hogs" else "Weekly Cattle Slaughter"
    t = re.sub(r'const TITLE = "[^"]*";', f'const TITLE = "{title}";', t)
    t = re.sub(r'const REPORT_DATE = "[^"]*";', f'const REPORT_DATE = "{rel.strftime("%B")} {rel.day}, {rel.year}";', t)
    labels = s["labels"][:]; labels[-1] += " (e)"
    t = re.sub(r"const weeks\s*=\s*\[.*?\];", "const weeks    = " + json.dumps(labels) + ";", t)
    t = re.sub(r"const current\s*=\s*\[.*?\];", "const current  = " + json.dumps(s["this_year"]) + ";", t)
    t = re.sub(r"const lastYear\s*=\s*\[.*?\];", "const lastYear = " + json.dumps(s["last_year"]) + ";", t)
    vals = [v for v in s["this_year"] + s["last_year"] if v is not None]
    step = 150000 if sp == "hogs" else 50000
    lo = math.floor((min(vals) - step * 0.3) / step) * step; hi = math.ceil((max(vals) + step * 0.3) / step) * step
    t = re.sub(r"const Y_MIN\s*=\s*\d+;", f"const Y_MIN  = {lo};", t)
    t = re.sub(r"const Y_MAX\s*=\s*\d+;", f"const Y_MAX  = {hi};", t)
    t = re.sub(r"const Y_STEP\s*=\s*\d+;", f"const Y_STEP = {step};", t)
    # layout like the 8/7 posts
    t = rep(t, """  ctx.fillStyle = NAVY;
  ctx.font = "bold 48px 'Helvetica Neue', Helvetica, Arial, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(TITLE, CW / 2, HEADER_H + 60);""", """  ctx.fillStyle = WHITE;
  ctx.font = "bold 52px 'Helvetica Neue', Helvetica, Arial, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(TITLE, CW / 2, HEADER_H / 2 + 18);""")
    t = rep(t, """  ctx.fillStyle = "#666666";
  ctx.font = "28px 'Helvetica Neue', Helvetica, Arial, sans-serif";
  ctx.fillText(SUBTITLE + " | " + REPORT_DATE, CW / 2, HEADER_H + 100);""", """  ctx.fillStyle = WHITE;
  ctx.font = "bold 28px 'Helvetica Neue', Helvetica, Arial, sans-serif";
  ctx.textAlign = "right";
  ctx.fillText(REPORT_DATE, CW - 40, HEADER_H / 2 + 10);""")
    t = rep(t, "const legY = HEADER_H + 98;", "const legY = HEADER_H + 60;")
    yr = int(d["week_ending"][:4])
    t = rep(t, 'ctx.fillText("2026", legX + 50, legY + 7);', f'ctx.fillText("{yr}", legX + 50, legY + 7);')
    t = rep(t, 'ctx.fillText("2025", leg2X + 50, legY + 7);', f'ctx.fillText("{yr - 1}", leg2X + 50, legY + 7);')
    t = rep(t, """  ctx.textAlign = "center";
  ctx.fillText("Source: USDA  |  lakefrontfutures.com/briefing/", CW / 2, CH - FOOTER_H / 2 + 7);""", """  ctx.textAlign = "left";
  ctx.fillText("Source: USDA", 40, CH - FOOTER_H / 2 + 7);
  ctx.textAlign = "right";
  ctx.fillText("lakefrontfutures.com/briefing/", CW - 40, CH - FOOTER_H / 2 + 7);""")
    hp = out.replace(".png", ".html"); open(hp, "w").write(t)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 2600, "height": 1500})
        pg.goto("file://" + os.path.abspath(hp)); pg.wait_for_timeout(700)
        u = pg.evaluate("document.getElementById('chart').toDataURL('image/png')"); br.close()
    open(out, "wb").write(base64.b64decode(u.split(",")[1])); print("OK", out)

if __name__ == "__main__":
    main(*sys.argv[1:4])
