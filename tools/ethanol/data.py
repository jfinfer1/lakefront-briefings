#!/usr/bin/env python3
"""Ethanol Production: Hightower ethanol PDF table, cross-checked against EIA WPSR.

Usage: python3 data.py HIGHTOWER_ETHANOL_PDF PSW01_XLS OUT_DIR WEEK_ENDING
Hightower PDF ("ETHANOL PRODUCTION REPORT") supplies corn used / needed / cumulative and the
narrative (5yr averages, % changes). EIA psw01.xls (W_EPOOXE_YOP_NUS_MBBLD production kb/d,
W_EPOOXE_SAE_NUS_MBBL stocks) must agree with it. Writes data.json, social.txt, numbers.txt.
"""
import datetime, json, os, re, subprocess, sys
import xlrd

def fail(m): sys.exit("VALIDATION FAILED: " + m)

def eia(p, key):
    b = xlrd.open_workbook(p)
    for sh in b.sheets()[1:]:
        h = sh.row_values(1)
        if key in h and str(sh.cell_value(2, h.index(key))).startswith("Weekly U.S."):
            c = h.index(key); break
    else: fail(f"{key} not in {p}")
    return {xlrd.xldate.xldate_as_datetime(sh.cell_value(r, 0), 0).date(): sh.cell_value(r, c)
            for r in range(3, sh.nrows) if sh.cell_value(r, c) != ""}

def main(pdf, p01, out, want):
    txt = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True).stdout
    flat = re.sub(r"\s+", " ", txt)
    rows = {}
    for m in re.finditer(r"(\d{1,2}/\d{1,2}/\d{2}) (\d+\.\d{3}) (-?\d+\.\d{3}) (\d+\.\d{3}) (-?\d+\.\d{3}) (\d+\.\d{3}) (\d+\.\d{2}) (\d+\.\d{2}|-) (\d+\.\d{2})", flat):
        d = datetime.datetime.strptime(m.group(1), "%m/%d/%y").date()
        rows[d] = dict(prod=float(m.group(2)), stocks=float(m.group(4)), stocks_chg=float(m.group(5)),
                       demand=float(m.group(6)), corn=float(m.group(7)),
                       needed=None if m.group(8) == "-" else float(m.group(8)), cum=float(m.group(9)))
    week = max(rows)
    if str(week) != want: print(f"NOT POSTED YET: Hightower latest {week}, want {want}"); sys.exit(3)
    r = rows[week]
    P, S = eia(p01, "W_EPOOXE_YOP_NUS_MBBLD"), eia(p01, "W_EPOOXE_SAE_NUS_MBBL")
    if week not in P: fail("EIA file does not have this week")
    daily = P[week] / 1000
    for d, x in rows.items():
        if d in P and abs(P[d] * 7 / 1000 - x["prod"]) > 0.002: fail(f"weekly prod mismatch {d}")
        if d in S and abs(S[d] / 1000 - x["stocks"]) > 0.0015: fail(f"stocks mismatch {d}")
    # narrative sits in the left column of the layout text
    left = re.sub(r"\s+", " ", " ".join(l[:45] for l in txt.splitlines()[:60]))
    left = left.replace("5- year", "5-year")
    m = re.search(r"averaged ([\d.]+) million barrels\.(?: (?:[^.]|\.\d)+?\.){0,2}? This was (up|down) ([\d.]+)% from last week and (up|down) ([\d.]+)% from last year\. The 5-year average for this week is ([\d.]+)", left)
    m2 = re.search(r"Ethanol stocks were ([\d.]+) million barrels\.(?: (?:[^.]|\.\d)+?\.){0,2}? This was (up|down) ([\d.]+)% from last week and (up|down) ([\d.]+)% from last year\. The 5-year average stocks for this week is ([\d.]+)", left)
    if not (m and m2): fail("could not parse Hightower narrative")
    if abs(float(m.group(1)) - daily) > 0.0005 or abs(float(m2.group(1)) - r["stocks"]) > 0.0005: fail("narrative vs table")
    sgn = lambda dirn, v: float(v) if dirn == "up" else -float(v)
    dates = sorted(d for d in P if d <= week)
    last14 = dates[-14:]
    gap = (r["needed"] - r["corn"]) / r["needed"] * 100
    d = {"week_ending": str(week), "daily_mbd": round(daily, 3), "weekly_total_mbbl": r["prod"], "stocks_mbbl": r["stocks"],
         "stocks_change_mbbl": r["stocks_chg"], "implied_demand_mbbl": r["demand"], "corn_used_mmbu": r["corn"],
         "corn_needed_mmbu": r["needed"], "corn_cum_mmbu": r["cum"], "pace_gap_pct": round(gap, 1),
         "prod_wk_pct": sgn(m.group(2), m.group(3)), "prod_yr_pct": sgn(m.group(4), m.group(5)), "prod_5yr_avg_mbd": float(m.group(6)),
         "stocks_wk_pct": sgn(m2.group(2), m2.group(3)), "stocks_yr_pct": sgn(m2.group(4), m2.group(5)), "stocks_5yr_avg_mbbl": float(m2.group(6)),
         "hightower_table": {str(k): v for k, v in sorted(rows.items())},
         "chart": [{"date": f"{x.month}/{x.day}", "prod": round(P[x] * 7 / 1000, 3), "stocks": round(S[x] / 1000, 3)} for x in last14]}
    os.makedirs(out, exist_ok=True)
    json.dump(d, open(os.path.join(out, "data.json"), "w"), indent=1)
    lines = [f"Production: {daily:.3f} mb/day", f"Weekly Total: {r['prod']:.3f} mil bbl",
             f"Stocks: {r['stocks']:.3f} mil bbl", f"Corn Used: {r['corn']:.2f} vs {r['needed']:.2f} needed"]
    open(os.path.join(out, "numbers.txt"), "w").write("\n".join(lines) + "\n")
    open(os.path.join(out, "social.txt"), "w").write("Ethanol Production\n\n" + "\n".join(lines) +
        "\n\nread more at lakefrontfutures.com/briefing/\n\n#Ethanol #EIA\n")
    print("OK"); print(open(os.path.join(out, "social.txt")).read()); print(json.dumps({k: v for k, v in d.items() if k not in ("hightower_table", "chart")}, indent=1))

if __name__ == "__main__":
    main(*sys.argv[1:5])
