#!/usr/bin/env python3
"""fill_email.py TITLE NUMBERS_TXT ANALYSIS_TXT IMAGE_URL OUT_HTML

email_template.html is Jack's real Brevo email (campaign 209), so spacing matches what he sends.
NUMBERS_TXT: one line per item; a blank line starts a new block, and a line followed by more lines
  in its block that has no ':' is treated as a bold sub-heading (e.g. "Cattle Slaughter").
  Empty file = no numbers block and no "Analysis" heading (COT layout).
ANALYSIS_TXT: paragraphs separated by blank lines.
  If the file starts with "<" it is used as raw HTML (Morning Briefing sections).
IMAGE_URL: one URL, or several separated by commas (each gets its own chart block and divider),
  or "none" for no chart (Morning Briefing)."""
import html, os, re, sys
here = os.path.dirname(os.path.abspath(__file__))
title, numbers_p, analysis_p, image_url, out = sys.argv[1:6]
raw = open(numbers_p, encoding="utf-8").read().strip("\n")
paras = [p.strip().replace("\n", " ") for p in open(analysis_p, encoding="utf-8").read().split("\n\n") if p.strip()]
t = open(os.path.join(here, "email_template.html"), encoding="utf-8").read()

def row(cls_marker, s):
    """the <tr>...</tr> that contains marker"""
    i = s.index(cls_marker); a = s.rfind("<tr>", 0, i); b = s.index("</tr>", i) + len("</tr>")
    return a, b

if raw.strip():
    blocks = [b.split("\n") for b in raw.split("\n\n")]
    parts = []
    for b in blocks:
        lines = [html.escape(l.strip()) for l in b if l.strip()]
        if len(lines) > 1 and ":" not in lines[0]:
            lines[0] = f"<strong>{lines[0]}</strong>"
        parts.append("<br>".join(lines))
    t = t.replace("{{NUMBERS}}", "<br><br>".join(parts))
else:
    a, b = row("{{NUMBERS}}", t); t = t[:a] + t[b:]
    a, b = row(">Analysis", t); t = t[:a] + t[b:]

span = '<p style="margin: 0;"><span style="color: rgb(27, 27, 27);">{}</span></p>'
araw = open(analysis_p, encoding="utf-8").read().strip()
if araw.startswith("<"):
    t = t.replace("{{ANALYSIS}}", araw)
else:
    t = t.replace("{{ANALYSIS}}", '<p style="margin: 0;"><br></p>'.join(span.format(html.escape(p)) for p in paras))

urls = [u.strip() for u in image_url.split(",") if u.strip() and u.strip().lower() != "none"]
a, b = row("{{IMAGE_URL}}", t); img_row = t[a:b]
d0 = t.rfind('<tr><td class="r14-c"', 0, a); divider = t[d0:t.index("</tr>", d0) + len("</tr>")]
if urls:
    t = t[:a] + divider.join(img_row.replace("{{IMAGE_URL}}", html.escape(u, quote=True)) for u in urls) + t[b:]
else:  # drop the chart row and the divider after it, keeping one divider above the buttons
    after = t[b:]; assert after.startswith(divider), "template changed (divider)"
    t = t[:a] + after[len(divider):]
t = t.replace("{{TITLE}}", html.escape(title))
assert "{{" not in re.sub(r"\{\{ contact\.EMAIL[^}]*\}\}", "", t), "unfilled placeholder"
open(out, "w", encoding="utf-8").write(t)
print(out, len(t))
