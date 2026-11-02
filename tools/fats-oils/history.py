"""Upsert the three months in data.json into the history CSV (revisions overwrite).
Usage: python3 history.py <data.json> <history.csv>"""
import csv, datetime, json, sys
d = json.load(open(sys.argv[1])); hp = sys.argv[2]
H = {r["month"]: r for r in csv.DictReader(open(hp))}
for k in ("year_ago", "prior", "current"):
    m = datetime.datetime.strptime(d["months"][k], "%B %Y").strftime("%Y-%m")
    H[m] = {"month": m, "crush_mbu": f'{d["crush_mbu"][k]:.3f}', "soyoil_blbs": f'{d["soyoil_stocks_blbs"][k]:.3f}'}
with open(hp, "w", newline="") as f:
    w = csv.DictWriter(f, ["month", "crush_mbu", "soyoil_blbs"]); w.writeheader()
    for m in sorted(H): w.writerow(H[m])
print("history", len(H), "months")
