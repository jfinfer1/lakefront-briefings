#!/usr/bin/env python3
"""USDA Fats & Oils chart (1200x675 @2x): KPI cards + 12 month crush bars and soyoil stock lines vs a year ago.
Usage: python3 chart.py DATA_JSON HISTORY_CSV OUT_DIR -> chart.html, chart.png
HISTORY_CSV: month (YYYY-MM), crush_mbu, soyoil_blbs (private repo state/fats-oils/history.csv; history.py updates it)."""
import base64, csv, datetime, html, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
NAVY, LIGHT, UP, DOWN = "#242a68", "#b9bfd9", "#1a7a4a", "#c0392b"

def fonts():
    return "".join(f"@font-face{{font-family:'Inter';font-weight:{w};src:url(data:font/woff2;base64,"
                   f"{base64.b64encode(open(os.path.join(HERE, f'inter-latin-{w}-normal.woff2'), 'rb').read()).decode()}) format('woff2')}}"
                   for w in (400, 600, 700, 800))

def chg(v, label):
    c, a = (UP, "▲") if v >= 0 else (DOWN, "▼")
    return f'<span style="color:{c}">{a} {abs(v):.1f}% {label}</span>'

def svg(series_cur, series_ly, labels, kind, fmt, w=540, h=350):
    L, R, T, B = 52, 12, 14, 34; cw, ch = w - L - R, h - T - B
    vals = [v for v in series_cur + series_ly if v is not None]
    lo, hi = min(vals), max(vals); pad = (hi - lo) * 0.15 or 1
    lo, hi = (0 if kind == "bar" else lo - pad), hi + pad
    if kind == "bar": lo = max(0, min(vals) - (hi - min(vals)) * 0.6)
    import math
    raw = (hi - lo) / 4; mag = 10 ** math.floor(math.log10(raw)); stp = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw))
    lo = math.floor(lo / stp) * stp; hi = lo + stp * 4
    while hi < max(vals) * 1.04: hi += stp
    nt = round((hi - lo) / stp)
    y = lambda v: T + ch - (v - lo) / (hi - lo) * ch
    n = len(labels); step = cw / n
    o = [f'<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">']
    for k in range(nt + 1):
        v = lo + stp * k; yy = y(v)
        o.append(f'<line x1="{L}" x2="{w-R}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="#e6e7ee"/>'
                 f'<text x="{L-6}" y="{yy+4:.1f}" font-size="11" text-anchor="end" fill="#555">{fmt(v)}</text>')
    for i, lab in enumerate(labels):
        cx = L + step * (i + .5)
        o.append(f'<text x="{cx:.1f}" y="{h-12}" font-size="11" text-anchor="middle" fill="#333" font-weight="600">{lab}</text>')
        if kind == "bar":
            bw = step * .36
            for j, (s, col) in enumerate([(series_ly, LIGHT), (series_cur, NAVY)]):
                v = s[i]
                if v is None: continue
                x = cx - bw + j * bw; o.append(f'<rect x="{x:.1f}" y="{y(v):.1f}" width="{bw-1:.1f}" height="{T+ch-y(v):.1f}" rx="2" fill="{col}"/>')
    if kind == "line":
        for s, col, wd, r in [(series_ly, LIGHT, 2.5, 3), (series_cur, NAVY, 3.5, 4)]:
            pts = [(L + step * (i + .5), y(v)) for i, v in enumerate(s) if v is not None]
            o.append('<polyline fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round" points="%s"/>' % (col, wd, " ".join(f"{a:.1f},{b:.1f}" for a, b in pts)))
            o += [f'<circle cx="{a:.1f}" cy="{b:.1f}" r="{r}" fill="{col}"/>' for a, b in pts]
    cur = series_cur[-1]; top = min(y(v) for v in (series_cur[-1], series_ly[-1]) if v is not None)
    if kind == "line" and series_cur[-2] is not None: top = min(top, y(series_cur[-2]))
    cx = L + step * (n - .5) + (step * .18 if kind == "bar" else 0)
    if kind == "bar": top = y(series_cur[-1])
    cx = min(cx, w - 29); by = max(T - 10, top - 24)
    o.append(f'<rect x="{cx-26:.1f}" y="{by:.1f}" width="52" height="18" rx="3" fill="{NAVY}"/>')
    o.append(f'<text x="{cx:.1f}" y="{by+13:.1f}" font-size="11" fill="#fff" font-weight="700" text-anchor="middle">{fmt(cur, True)}</text>')
    return "".join(o) + "</svg>"

def main(dp, hp, out):
    d = json.load(open(dp)); H = {r["month"]: r for r in csv.DictReader(open(hp))}
    cur = datetime.datetime.strptime(d["months"]["current"], "%B %Y").date()
    months = []
    y_, m_ = cur.year, cur.month
    for _ in range(12):
        months.insert(0, (y_, m_)); m_ -= 1
        if m_ == 0: y_, m_ = y_ - 1, 12
    key = lambda yy, mm: f"{yy:04d}-{mm:02d}"
    get = lambda k, f: float(H[k][f]) if k in H and H[k][f] else None
    labels = [datetime.date(yy, mm, 1).strftime("%b") for yy, mm in months]
    cr = [get(key(yy, mm), "crush_mbu") for yy, mm in months]; cr_ly = [get(key(yy - 1, mm), "crush_mbu") for yy, mm in months]
    so = [get(key(yy, mm), "soyoil_blbs") for yy, mm in months]; so_ly = [get(key(yy - 1, mm), "soyoil_blbs") for yy, mm in months]
    rel = datetime.date.fromisoformat(d["release_date"]); pri = d["months"]["prior"].split()[0][:3]
    pace = d["crush_per_day_mbu"]
    pace_m = (pace["current"] / pace["prior"] - 1) * 100 if "prior" in pace else None
    pace_y = (pace["current"] / pace["year_ago"] - 1) * 100 if "year_ago" in pace else None
    card = lambda title, val, unit, a, b: (f'<div class="card"><div class="ct">{title}</div><div class="cv">{val}<span class="cu">{unit}</span></div>'
                                           f'<div class="cc">{a}{"&nbsp;&nbsp;" + b if b else ""}</div></div>')
    cards = (card(f"Soybean Crush · {cur.strftime('%b %Y')}", f"{d['crush_mbu']['current']:.1f}", "M bu",
                  chg(d["crush_vs_prior_pct"], f"vs {pri}"), chg(d["crush_vs_year_pct"], "vs yr")) +
             card("Daily Crush Pace", f"{pace['current']:.2f}", "M bu/day",
                  chg(pace_m, f"vs {pri}") if pace_m is not None else "", chg(pace_y, "vs yr") if pace_y is not None else "") +
             card("Soyoil Stocks · Crude + Refined", f"{d['soyoil_stocks_blbs']['current']:.3f}", "B lbs",
                  chg(d["stocks_vs_prior_pct"], f"vs {pri}"), chg(d["stocks_vs_year_pct"], "vs yr")))
    yr = cur.year
    page = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{fonts()}
*{{margin:0;padding:0;box-sizing:border-box}}body{{background:#fff;font-family:'Inter',Arial,sans-serif}}
#w{{width:1200px;height:675px;display:flex;flex-direction:column;background:#fff}}
.hd{{height:86px;background:{NAVY};display:flex;align-items:center;justify-content:space-between;padding:0 28px;color:#fff;position:relative}}
.hd .t{{position:absolute;left:50%;transform:translateX(-50%);font-size:38px;font-weight:800;letter-spacing:1px}}
.hd .dt{{font-size:12px;font-weight:600;opacity:.85}}.hd .dt b{{display:block;font-size:16px;opacity:1}}.hd img{{height:52px}}
.cards{{display:flex;gap:14px;padding:16px 28px 6px}}
.card{{flex:1;background:#eef0f7;border-radius:8px;padding:12px 16px;text-align:center}}
.ct{{font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:#222}}
.cv{{font-size:38px;font-weight:800;color:{NAVY};margin-top:2px}}.cu{{font-size:15px;font-weight:600;margin-left:6px;color:#555}}
.cc{{font-size:13px;font-weight:600;margin-top:2px}}
.charts{{display:flex;gap:24px;padding:4px 28px 0;flex:1}}.ch{{flex:1}}
.cht{{font-size:14px;font-weight:700;text-align:center;color:#111;margin:4px 0 2px}}
.lg{{display:flex;gap:22px;justify-content:center;font-size:12px;font-weight:600;color:#444;padding:2px 0 8px}}
.lg i{{display:inline-block;width:14px;height:10px;border-radius:2px;margin-right:6px;vertical-align:middle}}
.ft{{height:40px;background:{NAVY};display:flex;justify-content:space-between;align-items:center;padding:0 28px;color:#fff;font-size:13px;font-weight:700}}
</style></head><body><div id="w">
<div class="hd"><div class="dt">USDA NASS Monthly Report<b>{rel.strftime('%B')} {rel.day}, {rel.year}</b></div><div class="t">USDA FATS &amp; OILS</div><img src="{open(os.path.join(HERE,'logo.txt')).read()}"></div>
<div class="cards">{cards}</div>
<div class="charts"><div class="ch"><div class="cht">Monthly Soybean Crush (million bushels)</div>{svg(cr, cr_ly, labels, "bar", lambda v, tag=False: f"{v:.1f}" if tag else f"{v:.0f}")}</div>
<div class="ch"><div class="cht">Soyoil Stocks, Crude + Once Refined (billion pounds)</div>{svg(so, so_ly, labels, "line", lambda v, tag=False: f"{v:.3f}" if tag else f"{v:.2f}")}</div></div>
<div class="lg"><span><i style="background:{NAVY}"></i>Last 12 months</span><span><i style="background:{LIGHT}"></i>Same month a year earlier</span></div>
<div class="ft"><span>Source: USDA NASS Fats &amp; Oils</span><span>lakefrontfutures.com/briefing</span></div></div></body></html>"""
    os.makedirs(out, exist_ok=True); hp_ = os.path.join(out, "chart.html"); open(hp_, "w", encoding="utf-8").write(page)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1200, "height": 675}, device_scale_factor=2)
        pg.goto("file://" + os.path.abspath(hp_)); pg.wait_for_timeout(500)
        pg.locator("#w").screenshot(path=os.path.join(out, "chart.png")); br.close()
    print("OK", os.path.join(out, "chart.png"))

if __name__ == "__main__":
    main(*sys.argv[1:4])
