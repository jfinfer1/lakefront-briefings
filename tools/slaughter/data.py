#!/usr/bin/env python3
"""USDA Estimated Weekly Livestock Slaughter (SJ_LS712, MMN 3209): cattle and hogs.

Usage: python3 data.py LS712_TXT HISTORY_CSV OUT_DIR [EXPECTED_WEEK_ENDING]
LS712: https://www.ams.usda.gov/mnreports/sj_ls712.txt (fetch through Make).
HISTORY_CSV (private repo state/slaughter/history.csv): week_ending,cattle,hogs,kind
  kind = est | actual. Each run upserts this week (est), last week (est, may be revised)
  and the year-ago week (actual). The caller commits the file.
Exit 3 if the week ending is not EXPECTED (not posted yet).
Writes data.json (numbers, YTD, chart series of the last 10 weeks vs year ago), social_hogs.txt,
social_cattle.txt, numbers.txt.
"""
import csv, datetime, json, os, re, sys

def num(x): return int(x.replace(",", ""))

def main(tp, hp, out, want=None):
    t = open(tp).read()
    rel = datetime.datetime.strptime(re.search(r"\w{3} (\w{3} \d{2}, \d{4})\s+USDA", t).group(1), "%b %d, %Y").date()
    sec = t[t.index("Livestock Slaughter (head)"):]
    rows = re.findall(r"^\s*(\d{2}-\w{3}-\d{2})\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)", sec, flags=re.M)[:3]
    chg = re.findall(r"Change:\s+(-?[\d.]+)%\s+(-?[\d.]+)%\s+(-?[\d.]+)%", sec)[:3]
    ytd = re.findall(r"^\s*(\d{4}) YTD\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)", sec, flags=re.M)[:2]
    if len(rows) != 3 or len(chg) < 3 or len(ytd) != 2: sys.exit("VALIDATION FAILED: could not parse head table")
    D = lambda s: datetime.datetime.strptime(s, "%d-%b-%y").date()
    (w0, c0, _, h0, _), (w1, c1, _, h1, _), (wy, cy, _, hy, _) = rows
    w0, w1, wy = D(w0), D(w1), D(wy)
    if want and str(w0) != want: print(f"NOT POSTED YET: week ending {w0}, want {want}"); sys.exit(3)
    c0, c1, cy, h0, h1, hy = map(num, (c0, c1, cy, h0, h1, hy))
    pct = lambda a, b: round((a - b) / b * 100, 1)
    if abs(pct(c0, c1) - float(chg[0][0])) > 0.11 or abs(pct(h0, h1) - float(chg[0][2])) > 0.11: fail = True
    else: fail = False
    if fail or abs(pct(c0, cy) - float(chg[1][0])) > 0.11 or abs(pct(h0, hy) - float(chg[1][2])) > 0.11:
        sys.exit("VALIDATION FAILED: computed % changes disagree with the report")
    # history upsert
    hist = {}
    if os.path.exists(hp):
        for r in csv.DictReader(open(hp)): hist[r["week_ending"]] = r
    for w, c, h, k in [(wy, cy, hy, "actual"), (w1, c1, h1, "est"), (w0, c0, h0, "est")]:
        if hist.get(str(w), {}).get("kind") == "actual" and k == "est": continue
        hist[str(w)] = {"week_ending": str(w), "cattle": c, "hogs": h, "kind": k}
    with open(hp, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["week_ending", "cattle", "hogs", "kind"]); wr.writeheader()
        for k in sorted(hist): wr.writerow(hist[k])
    H = {datetime.date.fromisoformat(k): v for k, v in hist.items()}
    def near(d):
        c = [x for x in H if abs((x - d).days) <= 3]
        return H[min(c, key=lambda x: abs((x - d).days))] if c else None
    weeks = [w0 - datetime.timedelta(7 * i) for i in range(9, -1, -1)]
    chart = {}
    for sp in ("cattle", "hogs"):
        ty = [int(H[w][sp]) if w in H else None for w in weeks]
        ly = [int(near(w - datetime.timedelta(364))[sp]) if near(w - datetime.timedelta(364)) else None for w in weeks]
        keep = [i for i in range(10) if ty[i] is not None and ly[i] is not None]
        chart[sp] = {"labels": [f"{weeks[i].month}/{weeks[i].day}" for i in keep],
                     "this_year": [ty[i] for i in keep], "last_year": [ly[i] for i in keep]}
    d = {"release_date": str(rel), "week_ending": str(w0),
         "cattle": {"head": c0, "prev": c1, "year_ago": cy, "wk_pct": float(chg[0][0]), "yr_pct": float(chg[1][0]),
                    "ytd": num(ytd[0][1]), "ytd_prev_year": num(ytd[1][1])},
         "hogs": {"head": h0, "prev": h1, "year_ago": hy, "wk_pct": float(chg[0][2]), "yr_pct": float(chg[1][2]),
                  "ytd": num(ytd[0][3]), "ytd_prev_year": num(ytd[1][3])},
         "chart": chart}
    os.makedirs(out, exist_ok=True); json.dump(d, open(os.path.join(out, "data.json"), "w"), indent=1)
    sg = lambda x: f"+{x:.1f}%" if x > 0 else (f"−{abs(x):.1f}%" if x < 0 else "0.0%")
    block = lambda sp: f"Head: {d[sp]['head']:,}\nvs Last Week: {sg(d[sp]['wk_pct'])}\nvs Year Ago: {sg(d[sp]['yr_pct'])}"
    open(os.path.join(out, "social_hogs.txt"), "w").write(
        "🐖 USDA Hog Slaughter\n\n" + block("hogs") + "\n\nread more at lakefrontfutures.com/briefing/\n\n#Hogs #LeanHogs #USDA\n")
    open(os.path.join(out, "social_cattle.txt"), "w").write(
        "🐂 USDA Cattle Slaughter\n\n" + block("cattle") + "\n\nread more at lakefrontfutures.com/briefing/\n\n#Cattle #LiveCattle #USDA\n")
    open(os.path.join(out, "numbers.txt"), "w").write("Cattle Slaughter\n" + block("cattle") + "\n\nHog Slaughter\n" + block("hogs") + "\n")
    print("OK"); print(open(os.path.join(out, "social_hogs.txt")).read()); print(open(os.path.join(out, "social_cattle.txt")).read())
    print("chart points:", {k: len(v["labels"]) for k, v in chart.items()})

if __name__ == "__main__":
    main(*sys.argv[1:5])
