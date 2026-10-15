#!/usr/bin/env python3
"""USDA National Dairy Products Sales Report (NDPSR, MMN 2993).

Usage: python3 data.py NDPSR_PDF OUT_DIR [EXPECTED_RELEASE_DATE YYYY-MM-DD]
PDF: https://www.ams.usda.gov/mnreports/dywdairyproductssales.pdf (fetch through Make).
Exit 3 if the PDF's release date is not EXPECTED (not posted yet).
Writes data.json, social.txt, numbers.txt. Changes are vs the (revised) prior week, in cents.
"""
import datetime, json, os, re, subprocess, sys

def main(pdf, out, want=None):
    t = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True).stdout
    rel = datetime.datetime.strptime(re.search(r"NDPSR-\d+\s+(\w+ \d{1,2}, \d{4})", t).group(1), "%B %d, %Y").date()
    if want and str(rel) != want: print(f"NOT POSTED YET: report dated {rel}, want {want}"); sys.exit(3)
    m = re.search(r"Weeks Ending: (\d+/\d+/\d{4}) - (\d+/\d+/\d{4})", t)
    end = datetime.datetime.strptime(m.group(2), "%m/%d/%Y").date()
    prods = {}
    for key, title in [("butter", "Butter Prices and Sales"), ("cheddar", "40-Pound Block Cheddar Cheese Prices and Sales"),
                       ("whey", "Dry Whey Prices and Sales"), ("ndm", "Nonfat Dry Milk Prices and Sales")]:
        blk = t[t.index(title):]
        hdr = re.search(r"United States\s+((?:\d{1,2}-\w{3}\s+){4}\d{1,2}-\w{3})", blk).group(1).split()
        pr = re.search(r"Weighted Price\s+([\s\d.*]+?)\n", blk).group(1).replace("*", "").split()
        if len(pr) != 5: sys.exit(f"VALIDATION FAILED: {key} prices {pr}")
        prods[key] = {"labels": hdr, "prices": [float(x) for x in pr]}
    labels = prods["butter"]["labels"]
    for k in prods:
        if prods[k]["labels"] != labels: sys.exit("VALIDATION FAILED: week headers differ")
    dates = []
    for lab in labels:
        d = datetime.datetime.strptime(f"{lab}-{end.year}", "%d-%b-%Y").date()
        if d > end: d = d.replace(year=end.year - 1)
        dates.append(d)
    if dates[-1] != end: sys.exit("VALIDATION FAILED: last week != weeks ending")
    # cross check against the highlights text
    hl = {"butter": r"Butter prices.*?per pound for the week ending.*?(increased|decreased|unchanged)\s*([\d.]*)",
          "cheddar": r"Cheddar Cheese prices.*?(increased|decreased|unchanged)\s*([\d.]*)",
          "whey": r"Dry Whey prices.*?(increased|decreased|unchanged)\s*([\d.]*)",
          "ndm": r"Nonfat Dry Milk prices.*?(increased|decreased|unchanged)\s*([\d.]*)"}
    flat = re.sub(r"\s+", " ", t)
    for k, p in prods.items():
        chg = round((p["prices"][-1] - p["prices"][-2]) * 100, 1)
        p["chg_c"] = chg
        m2 = re.search(hl[k], flat)
        if m2:
            v = 0.0 if m2.group(1) == "unchanged" else float(m2.group(2)) * (1 if m2.group(1) == "increased" else -1)
            if abs(v - chg) > 0.051: sys.exit(f"VALIDATION FAILED: {k} change {chg} vs highlights {v}")
    d = {"release_date": str(rel), "week_ending": str(end), "dates": [str(x) for x in dates],
         "labels": [f"{x.month}/{x.day}" for x in dates], "products": prods}
    os.makedirs(out, exist_ok=True)
    json.dump(d, open(os.path.join(out, "data.json"), "w"), indent=1)
    arr = lambda c: f"↑{c:.1f}¢" if c > 0 else (f"↓{abs(c):.1f}¢" if c < 0 else "unch")
    P = prods
    line = lambda emo, name, k: f"{emo} {name}: ${P[k]['prices'][-1]:.2f}/lb ({arr(P[k]['chg_c'])})"
    core = [line("🧈", "Butter", "butter"), line("🧀", "Cheddar", "cheddar"), line("🥛", "NDM", "ndm")]
    whey = f"💧 Dry Whey: {P['whey']['prices'][-1]*100:.1f}¢/lb ({arr(P['whey']['chg_c'])})"
    social = "🐄 USDA Dairy Products Sales\n\n" + "\n".join(core + [whey]) + "\n\nread more at lakefrontfutures.com/briefing/\n"
    open(os.path.join(out, "social.txt"), "w").write(social)
    open(os.path.join(out, "numbers.txt"), "w").write("\n".join(core) + "\n")
    print("OK"); print(social); print(json.dumps(d["products"]))

if __name__ == "__main__":
    main(*sys.argv[1:4])
