#!/usr/bin/env python3
"""Parse the Census/BEA trade release (trad<MMYY>.pdf) -> data.json, social.txt, numbers.txt.
Usage: python3 data.py TRAD_PDF OUT_DIR
Commodity values = month-over-month change in EXPORTS (exhibit 7, $ millions), as in Jack's chart."""
import datetime, json, os, re, subprocess, sys

ITEMS = [  # (exhibit 7 row, chart label, emoji, social/email name)
    ("Nonmonetary gold", "Gold", "\U0001F947", "Gold"),
    ("Natural gas", "Natural\nGas", "\U0001F4A8", "Natural Gas"),
    ("Corn", "Corn", "\U0001F33D", "Corn"),
    ("Copper", "Copper", "\U0001FA99", "Copper"),
    ("Natural gas liquids", "Nat Gas\nLiquids", "⛽", "Nat Gas Liquids"),
    ("Soybeans", "Soybeans", "\U0001FAD8", "Soybeans"),
    ("Fuel oil", "Fuel\nOil", "\U0001F525", "Fuel Oil"),
    ("Crude oil", "Crude\nOil", "\U0001F6E2️", "Crude Oil"),
]
SOCIAL = ["Crude Oil", "Soybeans", "Natural Gas"]
EMAIL = ["Gold", "Corn", "Soybeans", "Crude Oil", "Natural Gas"]
num = lambda x: float(x.replace(",", ""))

def sgn(v):  # Jack's style: +$2.0B / ▼$1.1B
    return f"+${v:.1f}B" if round(v, 1) >= 0 else f"▼${abs(v):.1f}B"

def main(pdf, out):
    t = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout
    m = re.search(r"goods and\s+services deficit was \$([\d.]+) billion in (\w+), (up|down) \$([\d.]+) billion from \$([\d.]+) billion in (\w+)", t)
    if not m: sys.exit("headline not found")
    deficit, month, direction, chg, prior = float(m[1]), m[2], m[3], float(m[4]), float(m[5])
    if abs(abs(deficit - prior) - chg) > 0.15: sys.exit("headline check failed")
    rel = re.search(r"RELEASE AT .*?, \w+day, (\w+ \d+, \d{4})", t)[1]
    year = re.search(r"Trade in Goods and Services\s+" + month + r" (\d{4})", t)[1]
    ex = re.search(r"September exports were|" + month + r" exports were \$([\d.]+) billion, \$([\d.]+) billion (more|less)", t)
    exm = re.search(month + r" exports were \$([\d.]+) billion, \$([\d.]+) billion (more|less)", t)
    imm = re.search(month + r" imports were\s+\$([\d.]+) billion, \$([\d.]+) billion (more|less)", t)
    goods = re.search(r"goods deficit of\s+\$([\d.]+) billion to \$([\d.]+) billion", t)
    ytd = re.search(r"Year-to-date, the goods and services deficit (increased|decreased) \$([\d.]+) billion, or ([\d.]+)\s+percent", t)
    # exhibit 7 table (first page of it)
    i = t.index("Exhibit 7. U.S. Exports of Goods by End-Use Category and Commodity", t.index("Exhibit 7.") + 10)
    sec = t[i:t.index("Exhibit 8.", i)]
    items = []
    for row, label, emo, name in ITEMS:
        r = re.search(r"^" + re.escape(row) + r"\s{2,}(-?[\d,]+)\s+(-?[\d,]+)\s+(-?[\d,]+)", sec, re.M)
        if not r: sys.exit(f"row not found: {row}")
        cur, pri, d = map(num, r.groups())
        if abs(cur - pri - d) > 2: sys.exit(f"row check failed: {row}")
        items.append({"row": row, "label": label, "emoji": emo, "name": name, "cur_m": cur, "prior_m": pri, "chg_b": round(d / 1000, 1)})
    items.sort(key=lambda x: -(x["cur_m"] - x["prior_m"]))
    def f(n): return next(x for x in items if x["name"] == n)
    dchg = deficit - prior
    d = {"release_date": datetime.datetime.strptime(rel, "%B %d, %Y").date().isoformat(), "month": f"{month} {year}",
         "deficit_b": deficit, "prior_deficit_b": prior, "deficit_chg_b": round(dchg, 1),
         "exports_b": float(exm[1]), "exports_chg_b": float(exm[2]) * (1 if exm[3] == "more" else -1),
         "imports_b": float(imm[1]), "imports_chg_b": float(imm[2]) * (1 if imm[3] == "more" else -1),
         "goods_deficit_b": float(goods[2]) if goods else None,
         "ytd": {"dir": ytd[1], "chg_b": float(ytd[2]), "pct": float(ytd[3])} if ytd else None,
         "items": items}
    os.makedirs(out, exist_ok=True)
    json.dump(d, open(os.path.join(out, "data.json"), "w"), indent=1, ensure_ascii=False)
    soc = "U.S. Trade Balance:\n\n" + "\n".join(f'{f(n)["emoji"]} {n}: {sgn(f(n)["chg_b"])}' for n in SOCIAL)
    soc += f"\n\nTrade Deficit: ${deficit:.1f}B\n\nread more at lakefrontfutures.com/briefing/"
    open(os.path.join(out, "social.txt"), "w").write(soc + "\n")
    nb = "\n".join(f'{f(n)["emoji"]} {n}: {sgn(f(n)["chg_b"])}' for n in EMAIL)
    nb += f"\nTrade Deficit: ${deficit:.1f}B ({sgn(dchg)})"
    open(os.path.join(out, "numbers.txt"), "w").write(nb + "\n")
    print(soc); print("---"); print(nb)

if __name__ == "__main__":
    main(*sys.argv[1:3])
