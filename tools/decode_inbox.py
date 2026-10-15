#!/usr/bin/env python3
"""decode_inbox.py DIR -> writes <fileName> next to each saved attachment (duplicates get -2, -3 in email id order), verifying the MD5 checksum."""
import hashlib, json, os, sys
d = sys.argv[1]
seen = set()
for f in sorted(os.listdir(d), key=lambda x: (len(x), x)):
    p = os.path.join(d, f)
    try: j = json.load(open(p))
    except Exception: continue
    raw = bytes(j["data"]["data"])
    if hashlib.md5(raw).hexdigest() != j["checksum"] or len(raw) != j["fileSize"]:
        sys.exit(f"CHECKSUM MISMATCH: {f}")
    name = j["fileName"]
    if name in seen:  # two emails with the same attachment name: keep both (name-2.pdf, name-3.pdf ...)
        stem, ext = os.path.splitext(name); n = 2
        while f"{stem}-{n}{ext}" in seen: n += 1
        name = f"{stem}-{n}{ext}"
    seen.add(name)
    out = os.path.join(d, name); open(out, "wb").write(raw); print(out, len(raw), "from", f)
