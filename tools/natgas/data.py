#!/usr/bin/env python3
"""EIA Weekly Natural Gas Storage: numbers, history and post copy.

Usage: python3 data.py WNGSR_JSON HISTORY_XLS OUT_DIR
  WNGSR_JSON  = https://ir.eia.gov/ngs/wngsr.json
  HISTORY_XLS = https://www.eia.gov/dnav/ng/hist_xls/NW2_EPG0_SWO_R48_BCFw.xls
Writes data.json (headline numbers, regions, weekly series for the chart),
social.txt and numbers.txt. Exits non-zero if the two EIA files disagree.
"""
import datetime, json, os, sys
import xlrd

def fail(m): print("VALIDATION FAILED: " + m, file=sys.stderr); sys.exit(2)

def main(jp, xp, out):
    j = json.load(open(jp))
    total = next(s for s in j["series"] if s["name"] == "total lower 48 states")
    week = j["current_week"]
    cur = dict(total["data"])[week]
    c = total["calculated"]
    net, avg5, yoy_pct, avg_pct = c["net_change"], c["5yr-avg"], c["pct-change_yrago"], c["pct-chg_5yr-avg"]
    yr_ago = dict(total["data"])[j["year_ago"]]

    b = xlrd.open_workbook(xp); sh = b.sheet_by_name("Data 1")
    hist = []
    for r in range(3, sh.nrows):
        d, v = sh.row_values(r)[:2]
        if v == "": continue
        hist.append((xlrd.xldate.xldate_as_datetime(d, b.datemode).date(), int(v)))
    hist.sort()
    if str(hist[-1][0]) != week or hist[-1][1] != cur:
        fail(f"history last row {hist[-1]} != weekly report {week} {cur}")
    if hist[-1][1] - hist[-2][1] != net:
        fail("net change does not match history")

    # weekly changes and how far back this week's injection/withdrawal is the largest
    changes = [(hist[i][0], hist[i][1] - hist[i-1][1]) for i in range(1, len(hist))]
    largest_since = None
    for d, ch in reversed(changes[:-1]):
        if (net >= 0 and ch >= net) or (net < 0 and ch <= net):
            largest_since = str(d); break

    # chart series by ISO week: this year, last year, 5yr avg/min/max (prior 5 calendar years)
    yr = hist[-1][0].year
    by = {}
    for d, v in hist:
        by.setdefault(d.year, {})[d.isocalendar()[1]] = v
    weeks = range(1, 53)
    five = [yr - k for k in range(1, 6)]
    series = {"weeks": list(weeks),
              "this_year": [by.get(yr, {}).get(w) for w in weeks],
              "last_year": [by.get(yr - 1, {}).get(w) for w in weeks]}
    avg, lo, hi = [], [], []
    for w in weeks:
        vals = [by[y][w] for y in five if w in by.get(y, {})]
        avg.append(round(sum(vals) / len(vals)) if vals else None)
        lo.append(min(vals) if vals else None); hi.append(max(vals) if vals else None)
    series.update(avg5=avg, min5=lo, max5=hi, five_years=f"{five[-1]}-{five[0]}")

    regions = []
    for s in j["series"]:
        if s["name"] == "total lower 48 states": continue
        regions.append({"name": s["name"], "bcf": dict(s["data"])[week],
                        "net_change": s["calculated"]["net_change"],
                        "pct_vs_5yr": s["calculated"]["pct-chg_5yr-avg"],
                        "pct_vs_yr_ago": s["calculated"]["pct-change_yrago"]})

    d = {"release_date": j["release_date"][:11], "week_ending": week, "storage_bcf": cur,
         "net_change": net, "vs_year_ago": cur - yr_ago, "vs_year_ago_pct": yoy_pct,
         "vs_5yr": cur - avg5, "vs_5yr_pct": avg_pct, "five_yr_avg": avg5,
         "largest_change_since": largest_since, "regions": regions,
         "recent_weekly_changes": [[str(a), b] for a, b in changes[-12:]], "series": series}
    os.makedirs(out, exist_ok=True)
    json.dump(d, open(os.path.join(out, "data.json"), "w"), indent=1)

    arr = lambda x: "↑" if x >= 0 else "↓"
    sg = lambda x: f"+{x:,}" if x >= 0 else f"−{abs(x):,}"
    sp = lambda x: f"+{x}%" if x >= 0 else f"−{abs(x)}%"
    lines = [f"{cur:,} Bcf",
             f"{arr(net)} {sg(net)} Bcf on the week",
             f"{arr(cur - yr_ago)} {sg(cur - yr_ago)} vs last year ({sp(yoy_pct)})"]
    social = ("Weekly Natural Gas Storage:\n\n" + "\n".join(lines) +
              f"\n{arr(cur - avg5)} {sg(cur - avg5)} vs 5-yr average ({sp(avg_pct)})" +
              "\n\nread more at lakefrontfutures.com/briefing/\n#NaturalGas #EIA\n")
    numbers = "\n".join(lines) + f"\n{arr(cur - avg5)} {sg(cur - avg5)} vs 5yr average ({sp(avg_pct)})\n"
    open(os.path.join(out, "social.txt"), "w").write(social)
    open(os.path.join(out, "numbers.txt"), "w").write(numbers)
    print("OK"); print(social); print(json.dumps({k: v for k, v in d.items() if k != "series"}, indent=1))

if __name__ == "__main__":
    main(*sys.argv[1:4])
