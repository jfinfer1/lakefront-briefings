#!/usr/bin/env python3
"""CFTC Commitments of Traders card: managed money (disaggregated F&O combined) and
leveraged funds (TFF F&O combined).

Usage: python3 data.py C_DISAGG_TXT FINCOMWK_TXT OUT_DIR [EXPECTED_AS_OF YYYY-MM-DD]
Files (fetch through Make): https://www.cftc.gov/dea/newcot/c_disagg.txt
                            https://www.cftc.gov/dea/newcot/FinComWk.txt
Exit 3 if the report date is not EXPECTED_AS_OF (new report not posted yet).
Notable flows: long/short legs of at least 3,500 contracts that moved the net position the
same direction as its weekly change, largest first, max 2 (checked against Jack's 10/9 card).
"""
import csv, json, os, sys
MARKETS = [  # (sector, label, file, CFTC code)
    ("GRAINS", "Corn", "d", "002602"), ("GRAINS", "Soybeans", "d", "005602"), ("GRAINS", "Wheat SRW", "d", "001602"),
    ("ENERGIES", "Crude Oil WTI", "d", "067651"), ("ENERGIES", "Natural Gas", "d", "023651"), ("ENERGIES", "RBOB Gasoline", "d", "111659"),
    ("FINANCIALS", "E-Mini S&P 500", "t", "13874A"), ("FINANCIALS", "Nasdaq 100", "t", "209742"), ("FINANCIALS", "10Y T-Note", "t", "043602"),
    ("LIVESTOCK", "Live Cattle", "d", "057642"), ("LIVESTOCK", "Feeder Cattle", "d", "061641"), ("LIVESTOCK", "Lean Hogs", "d", "054642"),
    ("METALS", "Gold", "d", "088691"), ("METALS", "Silver", "d", "084691"), ("METALS", "Copper", "d", "085692"),
    ("SOFTS", "Coffee", "d", "083731"), ("SOFTS", "Sugar", "d", "080732"), ("SOFTS", "Cocoa", "d", "073732")]
# column indexes: disaggregated combined: OI 7, MM long 13, MM short 14, chg MM long 61, chg MM short 62
#                 TFF combined: OI 7, Lev long 14, Lev short 15, chg Lev long 31, chg Lev short 32
COLS = {"d": (7, 13, 14, 61, 62), "t": (7, 14, 15, 31, 32)}
THRESH = 3500

def main(dp, tp, out, want=None):
    rows = {"d": {r[3].strip(): r for r in csv.reader(open(dp))}, "t": {r[3].strip(): r for r in csv.reader(open(tp))}}
    dates = {r[2].strip() for f in rows.values() for r in f.values()}
    if len(dates) != 1: sys.exit(f"VALIDATION FAILED: mixed report dates {dates}")
    asof = dates.pop()
    if want and asof != want: print(f"NOT POSTED YET: report as of {asof}, want {want}"); sys.exit(3)
    res = []
    for sector, label, f, code in MARKETS:
        r = rows[f].get(code)
        if not r: sys.exit(f"VALIDATION FAILED: {label} ({code}) missing")
        oi, L, S, dL, dS = (int(r[i]) for i in COLS[f])
        legs = [(dL, "New Longs" if dL > 0 else "Longs Liquidated"), (dS, "New Shorts" if dS > 0 else "Shorts Covered")]
        # only legs that pushed the net position the same way it moved this week
        legs = [(v, n) for v, n in zip((dL, -dS), [legs[0][1], legs[1][1]]) if abs(v) >= THRESH and (v > 0) == (dL - dS > 0)]
        flows = [f"{round(abs(v) / 1000)}K {name}" for v, name in sorted(legs, key=lambda x: -abs(x[0]))][:2]
        res.append({"sector": sector, "market": label, "name": r[0].strip(), "net": L - S, "chg": dL - dS, "oi": oi,
                    "long": L, "short": S, "chg_long": dL, "chg_short": dS, "flows": ", ".join(flows)})
    d = {"as_of": asof, "markets": res}
    os.makedirs(out, exist_ok=True)
    json.dump(d, open(os.path.join(out, "data.json"), "w"), indent=1)
    open(os.path.join(out, "social.txt"), "w").write(
        "Commitments Of Traders\nDisaggregated Futures & Options Combined\n\nRead more at lakefrontfutures.com/briefing/\n")
    open(os.path.join(out, "numbers.txt"), "w").write("")
    print("OK as of", asof)
    for m in res: print(f'{m["market"]:15} {m["net"]:>+11,} {m["chg"]:>+9,} {m["oi"]:>11,}  {m["flows"]}')

if __name__ == "__main__":
    main(*sys.argv[1:5])
