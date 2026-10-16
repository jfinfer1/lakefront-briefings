#!/usr/bin/env python3
"""USDA NASS Cattle on Feed (monthly). Source: ESMIS cofdMMYY.txt
(https://esmis.nal.usda.gov/publication/cattle-feed -> release-files/<n>/cofdMMYY.txt, fetch through Make).
Usage: python3 data.py COFD_TXT OUT_DIR [ESTIMATES_JSON]
ESTIMATES_JSON (optional): {"on_feed": 102.0, "placements": 93.0, "marketings": 93.0} (average trade
estimates, % of last year) shown as "(est. 102%)" in the email.
Percents are computed from the 1,000 head numbers to one decimal (NASS rounds to whole %).
"""
import datetime, json, os, re, sys

MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"]

def table(t, first):
    """the national table whose first line is 'On feed <Month> 1'"""
    m = re.search(r"On feed " + first + r" 1 \.+:\s+([\d,]+)\s+([\d,]+)\s+(\d+)\s*\n"
                  r"Placed on feed during (\w+) \.+:\s+([\d,]+)\s+([\d,]+)\s+(\d+)\s*\n"
                  r"Fed cattle marketed during \w+ \.+:\s+([\d,]+)\s+([\d,]+)\s+(\d+)\s*\n"
                  r"Other disappearance during \w+ \.+:\s+([\d,]+)\s+([\d,]+)\s+(\d+)\s*\n"
                  r"On feed (\w+) 1 \.+:\s+([\d,]+)\s+([\d,]+)\s+(\d+)", t)
    if not m: return None
    g = [x.replace(",", "") for x in m.groups()]
    n = lambda i: int(g[i])
    return {"start_month": first, "on_feed_start": (n(0), n(1), n(2)), "month": g[3],
            "placed": (n(4), n(5), n(6)), "marketed": (n(7), n(8), n(9)), "other": (n(10), n(11), n(12)),
            "end_month": g[13], "on_feed_end": (n(14), n(15), n(16))}

def main(tp, out, ep=None):
    t = open(tp).read()
    rel = datetime.datetime.strptime(re.search(r"Released (\w+ \d{1,2}, \d{4})", t).group(1), "%B %d, %Y").date()
    cur = MONTHS[rel.month - 1]; prev = MONTHS[rel.month - 2]   # inventory on <cur> 1; flows during <prev>
    flows = table(t, prev)
    if not flows or flows["end_month"] != cur: sys.exit("VALIDATION FAILED: could not find the national table")
    pct = lambda a: round(a[1] / a[0] * 100, 1)
    for k in ("on_feed_start", "placed", "marketed", "on_feed_end"):
        if abs(pct(flows[k]) - flows[k][2]) > 0.51: sys.exit(f"VALIDATION FAILED: {k} computed {pct(flows[k])} vs NASS {flows[k][2]}")
    # identity: start + placed - marketed - other = end (this year), within rounding
    s, p, mk, o, e = (flows[k][1] for k in ("on_feed_start", "placed", "marketed", "other", "on_feed_end"))
    if abs(s + p - mk - o - e) > 3: sys.exit("VALIDATION FAILED: inventory does not balance")
    yr = rel.year; pyr = yr if rel.month > 1 else yr - 1
    d = {"release_date": str(rel), "cur_month": cur, "prev_month": prev,
         "cur": {"label": f"{cur[:3]} '{str(yr)[2:]}", "on_feed_pct": pct(flows["on_feed_end"]), "head_m": e / 1000},
         "prev": {"label": f"{prev[:3]} '{str(pyr)[2:]}", "on_feed_pct": pct(flows["on_feed_start"]), "head_m": s / 1000,
                  "placements_pct": pct(flows["placed"]), "marketings_pct": pct(flows["marketed"]),
                  "placed_k": p, "marketed_k": mk},
         "raw": flows, "estimates": json.load(open(ep)) if ep else None}
    hl = re.search(r"\n\n(United States Cattle on Feed[^\n]*)\n", t); d["headline"] = hl.group(1) if hl else None
    os.makedirs(out, exist_ok=True); json.dump(d, open(os.path.join(out, "data.json"), "w"), indent=1)
    C, P, E = d["cur"], d["prev"], d["estimates"] or {}
    est = lambda k: f" (est. {E[k]:g}%)" if k in E else ""
    social = (f"🐄 USDA Cattle on Feed\n\n{cur}\nOn Feed: {C['on_feed_pct']:.1f}%\nOn Feed Million Head: {C['head_m']:.3f} million\n\n"
              f"{prev}\nOn Feed: {P['on_feed_pct']:.1f}%\nOn Feed Million Head: {P['head_m']:.3f}\n"
              f"Placements: {P['placements_pct']:.1f}%\nMarketings: {P['marketings_pct']:.1f}%\n\n"
              "read more at lakefrontfutures.com/briefing/\n\n#CattleOnFeed #USDA\n")
    # Jack's 8/21 email: the three numbers the trade estimates (inventory now, last month's flows)
    numbers = (f"On Feed: {C['on_feed_pct']:.1f}%{est('on_feed')}\nPlacements: {P['placements_pct']:.1f}%{est('placements')}\n"
               f"Marketings: {P['marketings_pct']:.1f}%{est('marketings')}\n")
    open(os.path.join(out, "social.txt"), "w").write(social); open(os.path.join(out, "numbers.txt"), "w").write(numbers)
    print("OK"); print(social); print(numbers)

if __name__ == "__main__":
    main(*sys.argv[1:4])
