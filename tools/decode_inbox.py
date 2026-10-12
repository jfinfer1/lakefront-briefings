#!/usr/bin/env python3
"""decode_inbox.py DIR -> writes <fileName> next to each saved attachment, verifying the MD5 checksum."""
import hashlib, json, os, sys
d = sys.argv[1]
for f in sorted(os.listdir(d)):
    p = os.path.join(d, f)
    try: j = json.load(open(p))
    except Exception: continue
    raw = bytes(j["data"]["data"])
    if hashlib.md5(raw).hexdigest() != j["checksum"] or len(raw) != j["fileSize"]:
        sys.exit(f"CHECKSUM MISMATCH: {f}")
    out = os.path.join(d, j["fileName"]); open(out, "wb").write(raw); print(out, len(raw))
