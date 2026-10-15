#!/usr/bin/env python3
"""EIA Weekly Petroleum Status: Energy Stocks numbers and post copy.

Usage: python3 data.py PSW01_XLS PSW09_XLS OUT_DIR [WEEK_ENDING]
Files are the WPSR release workbooks (fetch through Make; they update at release time,
the dnav history files lag by hours):
  https://ir.eia.gov/wpsr/psw01.xls  stocks: WCESTUS1 crude excl SPR, WGTSTUS1 gasoline,
                                     WDISTUS1 distillate, WD0ST_NUS_1 ULSD (0-15 ppm)
  https://ir.eia.gov/wpsr/psw09.xls  WPULEUS3 refinery utilization (weekly, not 4-wk avg)
Values match Table 1 of the release (checked against Jack's 9/25 post).
If WEEK_ENDING is given, exits 3 when any file does not yet have that week (release not posted yet).
Writes data.json, social.txt, numbers.txt.
"""
import datetime, json, os, sys
import xlrd

def load(p, key):
    b = xlrd.open_workbook(p)
    for sh in b.sheets()[1:]:
        h = sh.row_values(1)
        if key in h and str(sh.cell_value(2, h.index(key))).startswith("Weekly U.S."):
            c = h.index(key); break
    else: sys.exit(f"VALIDATION FAILED: {key} not in {p}")
    out = {}
    for r in range(3, sh.nrows):
        d, v = sh.cell_value(r, 0), sh.cell_value(r, c)
        if v == "": continue
        out[xlrd.xldate.xldate_as_datetime(d, b.datemode).date()] = float(v)
    return out

def yr_ago(series, d):
    t = d - datetime.timedelta(364)
    if t in series: return t
    near = [x for x in series if abs((x - t).days) <= 3]
    if len(near) != 1: sys.exit(f"VALIDATION FAILED: no unique year-ago week for {d}")
    return near[0]

def main(p01, p09, out, want=None):
    names = [("crude", "Crude Oil", "WCESTUS1"), ("gasoline", "Gasoline", "WGTSTUS1"),
             ("distillate", "Distillate", "WDISTUS1"), ("ulsd", "ULSD", "WD0ST_NUS_1")]
    S = {k: load(p01, key) for k, _, key in names}
    R = load(p09, "WPULEUS3")
    week = max(S["crude"])
    for k in S:
        if max(S[k]) != week: sys.exit(f"VALIDATION FAILED: {k} last week {max(S[k])} != crude {week}")
    if max(R) != week: sys.exit(f"VALIDATION FAILED: refinery last week {max(R)} != {week}")
    if want and str(week) != want:
        print(f"NOT POSTED YET: latest week {week}, want {want}"); sys.exit(3)
    if S["ulsd"][week] > S["distillate"][week]: sys.exit("VALIDATION FAILED: ULSD > distillate")

    dates = sorted(S["crude"])
    prev = dates[dates.index(week) - 1]
    if (week - prev).days != 7: sys.exit("VALIDATION FAILED: gap in weekly data")
    items = {}
    for k, label, _ in names:
        s = S[k]; ya = yr_ago(s, week)
        last4 = dates[-4:]
        items[k] = {"label": label, "level_m": round(s[week] / 1000, 1),
                    "wk_m": round((s[week] - s[prev]) / 1000, 1),
                    "yr_m": round((s[week] - s[ya]) / 1000, 1),
                    "year_ago_week": str(ya),
                    "chart": {"dates": [str(d) for d in last4],
                              "this_year": [round(s[d] / 1000, 1) for d in last4],
                              "last_year": [round(s[yr_ago(s, d)] / 1000, 1) for d in last4]},
                    "recent_8wk_m": [[str(d), round(s[d] / 1000, 1)] for d in dates[-8:]]}
    ref = {"rate": R[week], "prev": R[prev], "year_ago": R[yr_ago(R, week)]}
    d = {"week_ending": str(week), "prev_week": str(prev), "items": items, "refinery": ref}
    os.makedirs(out, exist_ok=True)
    json.dump(d, open(os.path.join(out, "data.json"), "w"), indent=1)

    sg = lambda x: f"+{x:.1f}M" if x >= 0 else f"-{abs(x):.1f}M"
    ud = lambda x: f"up {x:.1f}M" if x >= 0 else f"down {abs(x):.1f}M"
    soc = [f"{v['label']}: {v['level_m']:.1f} ({sg(v['wk_m'])} wk, {sg(v['yr_m'])} yr)" for v in items.values()]
    em = [f"{v['label']}: {v['level_m']:.1f} ({ud(v['wk_m'])} wk, {ud(v['yr_m'])} yr)" for v in items.values()]
    social = ("EIA Energy Stocks\n\n" + f"Refinery Rate: {ref['rate']:.1f}%\n" + "\n".join(soc) +
              "\n\nread more at lakefrontfutures.com/briefing/\n\n#CrudeOil #EIA\n")
    numbers = "\n".join(em) + f"\nRefinery Rate: {ref['rate']:.1f}%\n"
    open(os.path.join(out, "social.txt"), "w").write(social)
    open(os.path.join(out, "numbers.txt"), "w").write(numbers)
    print("OK"); print(social); print(numbers)

if __name__ == "__main__":
    main(*sys.argv[1:5])
