#!/usr/bin/env python3
"""Parse Jack's trading calendar PDF (one month per page, Mon-Sat grid) into JSON:
{"YYYY-MM-DD": {"holidays": [...], "reports": [{"name":..., "time":"7:30"|None}], "other": [...]}}
Expiration lines (FN:/LT:/LTO: and their continuations) go to "other".
Usage: python3 parse_calendar.py CALENDAR_PDF YEAR OUT_JSON
"""
import json, re, sys
import pdfplumber

MONTHS = ["JANUARY","FEBRUARY","MARCH","APRIL","MAY","JUNE","JULY","AUGUST","SEPTEMBER","OCTOBER","NOVEMBER","DECEMBER"]
DAYS = ["MONDAY","TUESDAY","WEDNESDAY","THURSDAY","FRIDAY","SATURDAY"]
TIME = re.compile(r"^(.*?)\s+(\d{1,2}:\d{2})$")

def lines_of(words, tol=3):
    words = sorted(words, key=lambda w: (round(w["top"]), w["x0"]))
    out = []
    for w in words:
        if out and abs(out[-1]["top"] - w["top"]) <= tol and w["x0"] - out[-1]["x1"] < 12:
            out[-1]["text"] += " " + w["text"]; out[-1]["x1"] = w["x1"]
        else:
            out.append(dict(text=w["text"], top=w["top"], x0=w["x0"], x1=w["x1"]))
    return out

def main(pdf, year, out):
    year = int(year); cal = {}
    with pdfplumber.open(pdf) as P:
        for page in P.pages:
            words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
            title = next(w for w in words if w["text"] in MONTHS)
            month = MONTHS.index(title["text"]) + 1
            heads = {w["text"]: w for w in words if w["text"] in DAYS and w["top"] < title["top"] + 40}
            # column boundaries: midpoints between header starts
            xs = [heads[d]["x0"] for d in DAYS]
            bounds = [0] + [(xs[i] + xs[i+1]) / 2 - 20 for i in range(5)] + [page.width]
            col = lambda x: max(i for i in range(6) if x >= bounds[i])
            hdr_bottom = max(h["bottom"] for h in heads.values())
            # day numbers: digit words that start a cell (left edge of a column)
            nums = [w for w in words if w["top"] > hdr_bottom and re.fullmatch(r"\d{1,2}", w["text"])
                    and abs(w["x0"] - (bounds[col(w["x0"])] + (20 if col(w["x0"]) else 0))) < 60]
            # keep the leftmost digit per (column,row) as the day label
            cells = {}
            for w in sorted(nums, key=lambda w: (w["top"], w["x0"])):
                c = col(w["x0"])
                key = (c, round(w["top"] / 8))
                if key not in cells: cells[key] = w
            labels = sorted(cells.values(), key=lambda w: (w["top"], w["x0"]))
            rows = sorted({round(w["top"]) for w in labels})
            # merge near-equal row tops
            rtops = []
            for r in rows:
                if not rtops or r - rtops[-1] > 25: rtops.append(r)
            def row(y):
                return max([i for i, r in enumerate(rtops) if y >= r - 4] or [0])
            daymap = {}
            for w in labels:
                daymap[(col(w["x0"]), row(w["top"]))] = int(w["text"])
            label_ids = {id(w) for w in labels}
            body = [w for w in words if w["top"] > hdr_bottom and id(w) not in label_ids]
            for ln in lines_of(body):
                c, r = col(ln["x0"]), row(ln["top"])
                d = daymap.get((c, r))
                if d is None: continue
                key = f"{year}-{month:02d}-{d:02d}"
                e = cal.setdefault(key, {"holidays": [], "reports": [], "other": []})
                t = re.sub(r"(ffi|ffl|ff|fi|fl) (?=[a-z])", r"\1", ln["text"].strip())   # PDF ligatures split words ("Confi dence")
                if t.startswith("ALL REPORT TIMES") or t in ("CENTRAL",) or t.startswith(("FN: First", "LT: Last", "LTO: Last")): continue
                e.setdefault("_lines", []).append(t)
    for k, e in cal.items():
        cont = False
        for t in e.pop("_lines", []):
            if re.match(r"^(FN|LT|LTO):", t) or cont:
                e["other"].append(t); cont = t.endswith("/"); continue
            if t.isupper() and not TIME.match(t):
                e["holidays"].append(t); continue
            mm = re.match(r"^(.*?\S)\s+(\d{1,2}:\d{2})\s+(\S.*)$", t)   # two reports run together on one line
            if mm:
                e["reports"].append({"name": mm.group(1), "time": mm.group(2)}); t = mm.group(3)
                if TIME.match(t) is None and not t.isupper():
                    e["reports"].append({"name": t, "time": None}); continue
            m = TIME.match(t)
            e["reports"].append({"name": m.group(1), "time": m.group(2)} if m else {"name": t, "time": None})
        # join wrapped holiday names
        if len(e["holidays"]) > 1: e["holidays"] = [" ".join(e["holidays"])]
    json.dump(dict(sorted(cal.items())), open(out, "w"), indent=1)
    print("OK", len(cal), "days")

if __name__ == "__main__":
    main(*sys.argv[1:4])
