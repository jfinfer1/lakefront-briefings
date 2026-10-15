#!/usr/bin/env python3
"""Rebuild a settlement history CSV (same columns technicals.py reads) from Yahoo Finance.

Usage: python3 settlements.py YAHOO_CHART_JSON OUT_CSV
YAHOO_CHART_JSON = https://query1.finance.yahoo.com/v8/finance/chart/<SYMBOL>?range=2y&interval=1d
fetched through Make (fetch_url). Front month continuous symbols:
  corn ZC=F, soybeans ZS=F, wheat ZW=F, live_cattle LE=F, feeder_cattle GF=F, lean_hogs HE=F,
  crude CL=F, natgas NG=F.
USE A SINGLE CONTRACT for technicals (continuous =F series jump at every roll, e.g. hogs
75.55 -> 66.6 on 10/15/26 when Oct expired): <root><month code><yy>.<exch>, e.g.
  ZCZ26.CBT corn, ZSF27.CBT beans, ZWZ26.CBT wheat, LEZ26.CME live cattle, GFX26.CME feeders,
  HEZ26.CME lean hogs, CLZ26.NYM crude, NGZ26.NYM natgas.
Hightower's daily PDFs name the lead contract per market (CNAZ26, LCZ26, FCX26, LHZ26...):
CNA->ZC, S->ZS, W->ZW, LC->LE, FC->GF, LH->HE, CL->CL, NG->NG.
Yahoo's daily close is the CME settlement (checked: Dec corn 10/9/26 = 479 3/4, matching
Hightower's settlement sheet; the old investing.com file had 480.50). Today's row while the
market is open is a live price; technicals.py excludes it.
"""
import csv, datetime, json, sys
from zoneinfo import ZoneInfo

def main(jp, out):
    d = json.load(open(jp))["chart"]
    if d.get("error") or not d.get("result"): sys.exit(f"VALIDATION FAILED: {d.get('error')}")
    r = d["result"][0]; q = r["indicators"]["quote"][0]
    tz = ZoneInfo(r["meta"].get("exchangeTimezoneName") or "America/Chicago")
    rows = []
    for i, t in enumerate(r["timestamp"]):
        c = q["close"][i]
        if c is None: continue
        day = datetime.datetime.fromtimestamp(t, tz).date()
        rows.append((day, c, q["open"][i], q["high"][i], q["low"][i], q["volume"][i]))
    rows.sort()
    if len(rows) < 205: sys.exit(f"VALIDATION FAILED: only {len(rows)} rows (need 205 for the 200 day SMA)")
    if len(rows) < 252: print(f"NOTE: {len(rows)} rows; 52 week high/low covers the contract life only")
    fmt = lambda x: "" if x is None else f"{x:.4f}".rstrip("0").rstrip(".")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(["Date", "Price", "Open", "High", "Low", "Vol.", "Change %"])
        for i in range(len(rows) - 1, -1, -1):
            day, c, o, h, l, v = rows[i]
            chg = f"{(c / rows[i-1][1] - 1) * 100:.2f}%" if i else ""
            w.writerow([day.strftime("%m/%d/%Y"), fmt(c), fmt(o), fmt(h), fmt(l), "" if v is None else str(v), chg])
    print("OK", out, len(rows), "rows, last", rows[-1][0], rows[-1][1])

if __name__ == "__main__":
    main(*sys.argv[1:3])
