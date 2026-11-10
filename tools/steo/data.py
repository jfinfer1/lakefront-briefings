#!/usr/bin/env python3
"""EIA STEO full PDF (steo_full.pdf) -> annual figures (last 3 columns of Tables 2 and 4a).
Usage: python3 data.py STEO_PDF STATE_DIR OUT_DIR
STATE_DIR (private repo state/steo) keeps <YYYY-MM>.json per edition; the previous edition supplies "prev"."""
import datetime, glob, json, os, re, subprocess, sys
ROWS = {"wti": r"West Texas Intermediate Spot Average", "brent": r"Brent Spot Average",
        "hh": r"Henry Hub Spot \(dollars per million Btu\)", "crude": r"U\.S\. total crude oil production \(a\)"}

def main(pdf, state, out):
    t = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout
    ed = re.search(r"Short-Term Energy Outlook - (\w+ \d{4})", t)[1]
    edk = datetime.datetime.strptime(ed, "%B %Y").strftime("%Y-%m")
    rel = re.search(r"Forecast (?:completion |release )?date:?\s*(\w+ \d+, \d{4})", t)
    yrs = None; vals = {}
    for k, pat in ROWS.items():
        m = re.search(r"^\s*" + pat + r"[ .]*((?:\s+-?[\d.]+){15})\s*$", t, re.M)
        if not m: sys.exit(f"row not found: {k}")
        n = [float(x) for x in m[1].split()]
        vals[k] = {"q": n[:12], "annual": n[12:]}
    hm = re.search(r"^\s+(\d{4})\s+(\d{4})\s+(\d{4})\s+Year\s*$", t, re.M)
    y0 = int(hm[1]) if hm else int(ed.split()[1]) - 1
    ann = {k: dict(zip([y0, y0 + 1, y0 + 2], v["annual"])) for k, v in vals.items()}
    os.makedirs(state, exist_ok=True)
    json.dump({"edition": ed, "annual": {k: {str(y): x for y, x in v.items()} for k, v in ann.items()}}, open(os.path.join(state, edk + ".json"), "w"), indent=1)
    prevs = sorted(p for p in glob.glob(os.path.join(state, "*.json")) if os.path.basename(p) < edk + ".json")
    if not prevs: sys.exit("no previous edition in state")
    pv = json.load(open(prevs[-1]))
    y = int(ed.split()[1])
    s = {k: {"last": ann[k][y - 1], "cur": ann[k][y], "next": ann[k][y + 1], "prev_cur": pv["annual"][k][str(y)]} for k in ROWS}
    res = {"edition": ed, "prev_edition": pv["edition"], "year": y, "series": s}
    os.makedirs(out, exist_ok=True); json.dump(res, open(os.path.join(out, "data.json"), "w"), indent=1)
    f2 = lambda v: f"{v:.2f}"
    lines = [f"\U0001F6E2️ #Brent: ${f2(s['brent']['cur'])}/bbl (prev ${f2(s['brent']['prev_cur'])})",
             f"\U0001F6E2️ #WTI: ${f2(s['wti']['cur'])}/bbl (prev ${f2(s['wti']['prev_cur'])})",
             f"\U0001F525 #NatGas: ${f2(s['hh']['cur'])}/MMBtu (prev ${f2(s['hh']['prev_cur'])})",
             f"⛽ U.S. Crude Production: {f2(s['crude']['cur'])} mb/d"]
    open(os.path.join(out, "lines.txt"), "w").write("\n".join(lines) + "\n")
    open(os.path.join(out, "numbers.txt"), "w").write("\n".join(l.replace("#", "") for l in lines) + "\n")
    print(json.dumps(res)); print("\n".join(lines))

if __name__ == "__main__":
    main(*sys.argv[1:4])
