#!/usr/bin/env python3
"""USDA NASS Fats & Oils: Oilseed Crushings (monthly), soybean crush and soyoil stocks.
Source: ESMIS https://esmis.nal.usda.gov/publication/fats-and-oils-oilseed-crushings-production-consumption-and-stocks
-> release-files/<n>/cafoMMYY.txt (fetch through Make).
Usage: python3 data.py CAFO_TXT OUT_DIR [EXPECTED_RELEASE YYYY-MM-DD]
Crush in bushels = tons x 2000/60. Soyoil stocks = crude + once refined on hand end of month
(Hightower's "crude & once refined"). Checked against Hightower 10/1/26: 209.644 M bu, 1.696 B lbs.
"""
import datetime, json, os, re, sys

def main(tp, out, want=None):
    t = open(tp).read()
    rel = datetime.datetime.strptime(re.search(r"Released (\w+ \d{1,2}, \d{4})", t).group(1), "%B %d, %Y").date()
    if want and str(rel) != want: print(f"NOT POSTED YET: released {rel}, want {want}"); sys.exit(3)
    a = t.index("Soybean Crushing, Production, Consumption and Stocks - United States")
    blk = t[a:t.index("(D) Withheld", a)]
    hdr = re.search(r"Item\s*:\s*(\w+ \d{4})\s*:\s*(\w+ \d{4})\s*:\s*(\w+ \d{4})", blk).groups()   # year ago, prior, current
    def row(label):
        m = re.search(r"^" + re.escape(label) + r"\.*[^:]*:\s+([\d,()D]+)\s+([\d,()D]+)\s+([\d,()D]+)", blk, flags=re.M)
        if not m: sys.exit(f"VALIDATION FAILED: row {label}")
        v = [None if "D" in x else int(x.replace(",", "")) for x in m.groups()]
        return v
    crush = row("Soybeans crushed"); crude = row("Crude oil on hand end of month"); refd = row("Once refined oil on hand end of month")
    if None in crush + crude + refd: sys.exit("VALIDATION FAILED: withheld value")
    bu = [c * 2000 / 60 / 1e6 for c in crush]                     # million bushels
    stocks = [(c + r) / 1e6 for c, r in zip(crude, refd)]          # billion pounds
    # cross check vs the highlights sentence ("6.29 million tons (210 million bushels)")
    m = re.search(r"Soybeans crushed for crude oil was ([\d.]+) million tons \((\d+) million bushels\)", t)
    if not m or abs(float(m.group(1)) - crush[2] / 1e6) > 0.006 or abs(int(m.group(2)) - bu[2]) > 0.6:
        sys.exit("VALIDATION FAILED: highlights disagree with the table")
    import calendar
    days = {h: calendar.monthrange(int(h.split()[1]), datetime.datetime.strptime(h.split()[0], "%B").month)[1] for h in hdr}
    labels = ["year_ago", "prior", "current"]
    d = {"release_date": str(rel), "months": dict(zip(labels, hdr)),
         "crush_tons": dict(zip(labels, crush)), "crush_mbu": {k: round(v, 3) for k, v in zip(labels, bu)},
         "crush_per_day_mbu": {k: round(v / days[h], 3) for k, v, h in zip(labels, bu, hdr) if h in days},
         "soyoil_stocks_blbs": {k: round(v, 3) for k, v in zip(labels, stocks)},
         "crude_stocks_mlbs": dict(zip(labels, [c / 1000 for c in crude])), "refined_stocks_mlbs": dict(zip(labels, [r / 1000 for r in refd]))}
    pct = lambda a, b: (a / b - 1) * 100
    d["crush_vs_prior_pct"] = round(pct(bu[2], bu[1]), 1); d["crush_vs_year_pct"] = round(pct(bu[2], bu[0]), 1)
    d["stocks_vs_prior_pct"] = round(pct(stocks[2], stocks[1]), 1); d["stocks_vs_year_pct"] = round(pct(stocks[2], stocks[0]), 1)
    os.makedirs(out, exist_ok=True); json.dump(d, open(os.path.join(out, "data.json"), "w"), indent=1)
    arr = lambda x: f"↑ {x:.1f}%" if x >= 0 else f"↓ {abs(x):.1f}%"
    cur, pri = hdr[2].split()[0], hdr[1].split()[0][:3]
    lines = [f"Soybean Crush ({cur}): {bu[2]:.1f}M bu ({crush[2]/1e6:.2f}M tons)",
             f"{arr(d['crush_vs_prior_pct'])} vs {pri}, {arr(d['crush_vs_year_pct'])} vs last year",
             f"Soyoil Stocks: {stocks[2]:.3f}B lbs",
             f"{arr(d['stocks_vs_prior_pct'])} vs {pri}, {arr(d['stocks_vs_year_pct'])} vs last year"]
    social = "🌱 USDA Fats & Oils\n\n" + "\n".join(lines) + "\n\nread more at lakefrontfutures.com/briefing/\n\n#Soybeans #SoybeanOil #USDA\n"
    open(os.path.join(out, "social.txt"), "w").write(social); open(os.path.join(out, "numbers.txt"), "w").write("\n".join(lines) + "\n")
    print("OK"); print(social); print(json.dumps({k: d[k] for k in d if k.startswith(("crush", "soyoil"))}))

if __name__ == "__main__":
    main(*sys.argv[1:4])
