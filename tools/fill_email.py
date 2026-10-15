#!/usr/bin/env python3
"""fill_email.py TITLE NUMBERS_TXT ANALYSIS_TXT IMAGE_URL OUT_HTML
NUMBERS_TXT: one line per item. ANALYSIS_TXT: paragraphs separated by blank lines.
An empty NUMBERS_TXT drops the numbers block and the "Analysis" heading (COT layout: title, then paragraphs)."""
import html, os, sys
here = os.path.dirname(os.path.abspath(__file__))
title, numbers_p, analysis_p, image_url, out = sys.argv[1:6]
nums = [l.strip() for l in open(numbers_p, encoding="utf-8") if l.strip()]
paras = [p.strip().replace("\n", " ") for p in open(analysis_p, encoding="utf-8").read().split("\n\n") if p.strip()]
numbers_html = '<p style="margin:0;">' + "<br>".join(html.escape(n) for n in nums) + "</p>"
analysis_html = '<p style="margin:0;"><br></p>'.join(f'<p style="margin:0;">{html.escape(p)}</p>' for p in paras)
t = open(os.path.join(here, "email_template.html"), encoding="utf-8").read()
if not nums:
    import re
    t, n = re.subn(r'<div style="padding:10px 0;">\{\{NUMBERS\}\}</div>\s*<p style="margin:0;"><strong><span[^>]*>Analysis</span></strong></p>', '', t)
    assert n == 1, "template changed"
t = t.replace("{{TITLE}}", html.escape(title)).replace("{{NUMBERS}}", numbers_html) \
     .replace("{{ANALYSIS}}", analysis_html).replace("{{IMAGE_URL}}", image_url)
open(out, "w", encoding="utf-8").write(t)
print(out, len(t))
