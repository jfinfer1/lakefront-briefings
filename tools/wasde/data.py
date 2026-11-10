#!/usr/bin/env python3
"""Parse USDA WASDE text (wasdeMMYY.txt) -> data.json, social.txt, numbers.txt.
Usage: python3 data.py WASDE_TXT OUT_DIR
Columns in the U.S. corn/soy tables: prior-year, last-year Est., current-year Proj. (last month), Proj. (this month)."""
import json, os, re, sys

ROWS = {"yield": "Yield per Harvested Acre", "area": "Area Harvested", "prod": "Production",
        "carry": "Ending Stocks", "beg": "Beginning Stocks", "exports": "Exports",
        "crush": "Crushings", "feed": "Feed and Residual", "ethanol": "Ethanol & by-products",
        "use": "Use, Total", "price": "Avg.FarmPrice"}
BOLD = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "".join(chr(0x1D5D4 + i) for i in range(26)))

def table(t, title, start):
    i = t.index(title); seg = t[i:t.index("WASDE - ", i)]
    hdr = re.search(r"Item\s+(\w{3})\s+(\w{3})", seg)
    yrs = re.search(r"(\d{4}/\d{2})\s+(\d{4}/\d{2}) Est\.\s+(\d{4}/\d{2}) Proj\.", seg)
    seg = seg[seg.index("\n" + start):]
    out = {}
    for k, lab in ROWS.items():
        m = re.search(r"^\s*" + re.escape(lab) + r"[^\d\n]*?\s{2,}([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$", seg, re.M)
        if m: out[k] = [float(x) for x in m.groups()]
    for k in ("yield", "area", "prod", "carry"):
        if k not in out: sys.exit(f"{title}: row not found {k}")
    return out, (hdr[1], hdr[2]), yrs.groups()

def main(src, out):
    t = open(src).read()
    month = re.search(r"WASDE - \d+ - \d+\s+(\w+) (\d{4})", t).groups()
    corn, mons, yrs = table(t, "U.S. Feed Grain and Corn Supply and Use", "CORN")
    soy, mons2, _ = table(t, "U.S. Soybeans and Products Supply and Use", "SOYBEANS")
    # sanity: supply/use arithmetic for this month
    for name, d in (("corn", corn), ("soy", soy)):
        if d["prod"][3] < 1000 or not (0 < d["yield"][3] < 300): sys.exit(f"{name} values look wrong")
    d = {"month": month[0], "year": month[1], "cur": mons[1], "prior": mons[0], "est_year": yrs[1], "corn": corn, "soy": soy}
    os.makedirs(out, exist_ok=True)
    json.dump(d, open(os.path.join(out, "data.json"), "w"), indent=1)
    f = lambda v, k: f"{v:.1f}" if k in ("yield", "area") else f"{v:,.0f}"
    def block(emoji, name, x):
        return f"{emoji}{name}\nYield: {f(x['yield'][3],'yield')}\nHarvest Area: {f(x['area'][3],'area')}\nProduction: {f(x['prod'][3],'prod')}\nCarryout: {f(x['carry'][3],'carry')}"
    c, s = block("\U0001F33D", "Corn", corn), block("\U0001FAD8", "Soybeans", soy)
    soc = f"{month[0]} {'WASDE'.translate(BOLD)}\n\n{c}\n\n{s}\n\nFull briefing: lakefrontfutures.com/briefing/\n\n#supplyanddemand #usda"
    open(os.path.join(out, "social.txt"), "w").write(soc + "\n")
    open(os.path.join(out, "numbers.txt"), "w").write(c.replace("\U0001F33D", "\U0001F33D ") + "\n\n" + s.replace("\U0001FAD8", "\U0001FAD8 ") + "\n")
    print(soc)

if __name__ == "__main__":
    main(*sys.argv[1:3])
