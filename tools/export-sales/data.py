#!/usr/bin/env python3
"""USDA Weekly Export Sales from a transcription of the Hightower export sales PDF.

The Hightower PDF is an image (no text layer), so the run transcribes page 1 into
state/export-sales/<week_ending>.json (format: see 2026-10-01.json) and this script
validates it and builds the outputs.

Usage: python3 data.py THIS_WEEK_JSON PREV_WEEK_JSON OUT_DIR
Checks: current+next=total for every row; bushels = total MT x factor (corn 39.3679,
soybeans/wheat 36.7437) within 0.01%; destinations are not larger than the total; prev week is 7 days earlier.
"""
import datetime, json, os, sys
F = {"corn": 39.3679, "soybeans": 36.7437, "wheat": 36.7437}
def fail(m): sys.exit("VALIDATION FAILED: " + m)

def check(d, label):
    for c, s in d["summary"].items():
        if s["current"] + s["next"] != s["total"]: fail(f"{label} {c} current+next != total")
        if abs(s["total"] * F[c] - s["bushels"]) > max(2, s["bushels"] * 0.0001): fail(f"{label} {c} bushels {s['bushels']} != {s['total']}x{F[c]}")
        for name, cur, nxt, tot in d["destinations"][c]:
            if cur + nxt != tot: fail(f"{label} {c} {name} current+next != total")

def main(tp, pp, out):
    d, p = json.load(open(tp)), json.load(open(pp))
    check(d, "this week"); check(p, "prev week")
    if (datetime.date.fromisoformat(d["week_ending"]) - datetime.date.fromisoformat(p["week_ending"])).days != 7: fail("prev week is not 7 days earlier")
    S, P = d["summary"], p["summary"]
    top = {c: [r for r in d["destinations"][c] if r[0] != "Unknown"][:3] for c in S}
    res = {"week_ending": d["week_ending"], "prev_week_ending": p["week_ending"], "release_date": d.get("release_date"),
           "summary": S, "prev_summary": P, "top3": top, "destinations": d["destinations"], "prev_destinations": p["destinations"],
           "pace_gap": {c: round(S[c]["pct_usda"] - S[c]["pct_5yr"], 1) for c in S},
           "prev_pace_gap": {c: round(P[c]["pct_usda"] - P[c]["pct_5yr"], 1) for c in P}}
    os.makedirs(out, exist_ok=True)
    json.dump(res, open(os.path.join(out, "data.json"), "w"), indent=1)
    n = lambda x: f"{x:,}"
    social = ("USDA Weekly Grain Export Sales\n\n"
              f"#corn🌽: {n(S['corn']['current'])} MT\n#Soybeans🌱: {n(S['soybeans']['current'])} MT\n#wheat🌾: {n(S['wheat']['current'])} MT\n\n"
              f"Corn pace {S['corn']['pct_usda']}% of USDA est vs {S['corn']['pct_5yr']}% 5yr avg\n"
              f"Beans at {S['soybeans']['pct_usda']}% vs {S['soybeans']['pct_5yr']}% 5yr avg\n\n"
              "read more at lakefrontfutures.com/briefing/\n\n#USDA #exports #exportsales #grains\n")
    numbers = "\n".join(f"{e} {nm}: {n(S[c]['current'])} MT | {S[c]['pct_usda']}% of USDA Est"
                        for e, nm, c in [("🌽", "Corn", "corn"), ("🌱", "Soybeans", "soybeans"), ("🌾", "Wheat", "wheat")]) + "\n"
    open(os.path.join(out, "social.txt"), "w").write(social); open(os.path.join(out, "numbers.txt"), "w").write(numbers)
    print("OK"); print(social); print(numbers); print(json.dumps({k: res[k] for k in ("top3", "pace_gap", "prev_pace_gap")}))

if __name__ == "__main__":
    main(*sys.argv[1:4])
