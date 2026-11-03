#!/usr/bin/env python3
"""Fetch official radio manuals listed in radio-catalog.json into <root>/manuals/radio/<maker>/ and write manifest.json.
Usage: fetch_radio.py [catalog.json] [ARKIVE_ROOT]. Only official manufacturer / authorised-distributor URLs belong in the catalog."""
import json, os, sys, hashlib, time, urllib.request
cat = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "radio-catalog.json")
root = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("ARKIVE_ROOT", "/srv/archive")
base = os.path.join(root, "manuals", "radio"); out = []
for it in json.load(open(cat))["items"]:
    d = os.path.join(base, it["maker"]); os.makedirs(d, exist_ok=True); p = os.path.join(d, it["file"]); rec = dict(it)
    try:
        if not os.path.isfile(p):
            req = urllib.request.Request(it["url"], headers={"User-Agent": "Mozilla/5.0 (ARKive manual fetch)"})
            data = urllib.request.urlopen(req, timeout=120).read()
            if not data.startswith(b"%PDF"): raise ValueError("not a PDF")
            open(p + ".part", "wb").write(data); os.replace(p + ".part", p)
        b = open(p, "rb").read(); rec.update(status="fetched", bytes=len(b), sha256=hashlib.sha256(b).hexdigest(),
                                            fetched=time.strftime("%Y-%m-%d", time.gmtime(os.path.getmtime(p))))
        if it.get("sha256") and it["sha256"] != rec["sha256"]: rec["status"] = "sha256-changed"
    except Exception as e:
        rec.update(status="failed", error=str(e)[:200])
    out.append(rec); print(rec["status"], it["maker"], it["model"])
json.dump({"generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "items": out}, open(os.path.join(base, "manifest.json"), "w"), indent=1)
