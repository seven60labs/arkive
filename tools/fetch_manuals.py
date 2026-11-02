#!/usr/bin/env python3
"""Fetch the ARKive "Official Manuals" collection (public-domain US Government PDFs).

    python3 tools/fetch_manuals.py [--catalog manuals/catalog.json] [--dest /srv/archive/manuals/official] [--only ID ...]

Reads the catalog, resolves each 'fetch' item to a PDF URL, downloads into <dest>/<subject>/<file>.pdf,
and writes <dest>/manifest.json (title, number, edition date, source URL, sha256, size, license, superseded notes).
Sources: Army Publishing Directorate (armypubs.army.mil, public 'DR_pubs' PDFs only), other official .gov sites,
and archive.org copies of public-domain military manuals. Items already present elsewhere in the library
('in_library') are recorded in the manifest but not downloaded. Re-runs skip files whose sha256 is unchanged.
Restriction check: if `pdftotext` is installed, the first pages are scanned and anything marked
distribution-restricted / FOUO / CUI (and not "approved for public release") is deleted and reported as skipped.
stdlib only.
"""
import argparse, hashlib, html, json, os, re, shutil, subprocess, sys, time, urllib.parse, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (ARKive manual fetcher)"}
APD = "https://armypubs.army.mil/ProductMaps/PubForm/"
HERE = os.path.dirname(os.path.abspath(__file__))

def get(url, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()

def slug(s): return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")

_lists = {}
def apd_id(number, lst):
    if lst not in _lists: _lists[lst] = get(APD + lst + ".aspx").decode("utf-8", "replace")
    for c in _lists[lst].split("Details.aspx?PUB_ID=")[1:]:
        m = re.match(r'(\d+)[^>]*>([^<]+)</a>', c)
        if m and html.unescape(m.group(2)).strip().upper() == number.upper(): return int(m.group(1))
    raise LookupError(f"{number} not found in APD {lst} list")

def apd_resolve(pid):
    page = get(f"{APD}Details.aspx?PUB_ID={pid}").decode("utf-8", "replace")
    txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))
    m = re.search(r"href=['\"]([^'\"]*epubs/DR_pubs/[^'\"]+\.pdf)['\"]", page, re.I)
    if not m: raise LookupError("no public PDF on APD details page (CAC/restricted or not digitised)")
    url = urllib.parse.urljoin(APD, m.group(1)).replace(" ", "%20")
    if "/DR_a/" not in url:  # DR_a = public release; DR_b/c/d sit behind CAC login (distribution-restricted)
        raise PermissionError("distribution-restricted on APD (CAC-only PDF: %s)" % url.rsplit("/", 1)[-1])
    date = (re.search(r"Pub/Form Date (\d\d/\d\d/\d{4})", txt) or [None, ""])[1]
    status = (re.search(r"Pub/Form Status (\w+)", txt) or [None, ""])[1]
    chg = (re.search(r"Changes ([0-9]{3} - \d\d/\d\d/\d{4})", txt) or [None, ""])[1]
    if re.search(r"\bFOUO\b|FOR OFFICIAL USE ONLY|\bCUI\b", txt) and "PUBLIC RELEASE" not in txt.upper():
        raise PermissionError("APD details page marks it restricted")
    return url, {"edition": date + (f" (change {chg})" if chg else ""), "apd_status": status,
                 "apd_page": f"{APD}Details.aspx?PUB_ID={pid}"}

def archive_resolve(ident, search=None):
    try: meta = json.loads(get(f"https://archive.org/metadata/{ident}"))
    except Exception: meta = {}
    if not meta.get("files") and search:
        q = urllib.parse.urlencode({"q": f"({search}) AND mediatype:texts", "fl[]": "identifier", "sort[]": "downloads desc", "rows": 1, "output": "json"})
        docs = json.loads(get("https://archive.org/advancedsearch.php?" + q))["response"]["docs"]
        if not docs: raise LookupError("archive.org: no match")
        ident = docs[0]["identifier"]; meta = json.loads(get(f"https://archive.org/metadata/{ident}"))
    pdfs = [f for f in meta.get("files", []) if f["name"].lower().endswith(".pdf")]
    if not pdfs: raise LookupError(f"archive.org {ident}: no PDF")
    pdfs.sort(key=lambda f: (f.get("source") != "original", "_text" in f["name"], -int(f.get("size", 0) or 0)))
    f = pdfs[0]; md = meta.get("metadata", {})
    return (f"https://archive.org/download/{ident}/{urllib.parse.quote(f['name'])}",
            {"edition": str(md.get("date", "") or ""), "archive_item": f"https://archive.org/details/{ident}"})

RESTRICT = re.compile(r"DISTRIBUTION RESTRICTION[^.]{0,200}?(authorized to|limited to|U\.S\. Government agencies only|DoD components only)"
                      r"|FOR OFFICIAL USE ONLY|\bFOUO\b|CONTROLLED UNCLASSIFIED|\bCUI\b|DISTRIBUTION (STATEMENT )?[B-F]\b", re.I)
def restriction(path):
    if not shutil.which("pdftotext"): return None
    try: t = subprocess.run(["pdftotext", "-l", "6", path, "-"], capture_output=True, text=True, timeout=120).stdout
    except Exception: return None
    t = re.sub(r"\s+", " ", t)
    if re.search(r"approved for public release", t, re.I): return "public"
    m = RESTRICT.search(t)
    return ("RESTRICTED: " + m.group(0)[:120]) if m else "no marking"

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default=os.path.join(HERE, "..", "manuals", "catalog.json"))
    ap.add_argument("--dest", default="/srv/archive/manuals/official")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    cat = json.load(open(a.catalog)); os.makedirs(a.dest, exist_ok=True)
    mpath = os.path.join(a.dest, "manifest.json")
    old = {m["id"]: m for m in json.load(open(mpath))["items"]} if os.path.exists(mpath) else {}
    out, skipped = [], []
    for it in cat["items"]:
        if a.only and it["id"] not in a.only:
            if it["id"] in old: out.append(old[it["id"]])
            continue
        rec = {k: it[k] for k in ("id", "subject", "number", "title", "supersedes", "superseded_by", "publisher", "note") if k in it}
        rec["license"] = cat["license"]
        if "skip" in it:
            rec.update(status="skipped", reason=it["skip"]); skipped.append(rec); out.append(rec); continue
        if "in_library" in it:
            rec.update(status="in_library", in_library=it["in_library"], source_url=it.get("source", ""))
            out.append(rec); continue
        try:
            if "apd" in it or "apd_number" in it:
                pid = it.get("apd") or apd_id(it["apd_number"], it.get("apd_list", "TB"))
                url, extra = apd_resolve(pid); rec["publisher"] = "Headquarters, Department of the Army"
            elif "archive" in it:
                url, extra = archive_resolve(it["archive"], it.get("archive_search")); rec.setdefault("publisher", "Headquarters, Department of the Army (archive.org copy)")
            else:
                url, extra = it["url"], {}
            rec.update(extra); rec["source_url"] = url
            sub = os.path.join(a.dest, slug(it["subject"])); os.makedirs(sub, exist_ok=True)
            fn = slug(f'{it["number"]} {it["title"]}')[:90] + ".pdf"
            dst = os.path.join(sub, fn); tmp = dst + ".part"
            o = old.get(it["id"], {})
            if os.path.isfile(dst) and o.get("status") == "fetched" and o.get("sha256") == sha256(dst):
                o.update({k: v for k, v in rec.items() if k not in ("source_url",)}); o["source_url"] = url
                print(f"[{it['id']}] unchanged", flush=True); out.append(o); continue
            if it.get("manual_only"):  # site blocks scripts: record a copy saved by hand, never download
                if not os.path.isfile(dst): raise FileNotFoundError(f"manual_only: save {url} by hand to {dst}")
                rec.update(status="fetched", file=os.path.relpath(dst, a.dest), sha256=sha256(dst), bytes=os.path.getsize(dst),
                           edition=it.get("edition", ""), saved_by_hand=True, restriction_check="no restriction marking (civil-agency publication)")
                print(f"[{it['id']}] hand-saved copy recorded", flush=True); out.append(rec); continue
            print(f"[{it['id']}] {url}", flush=True)
            data = get(url, timeout=600)
            if not data.startswith(b"%PDF"): raise ValueError("not a PDF (got %r)" % data[:40])
            open(tmp, "wb").write(data)
            r = restriction(tmp); rec["restriction_check"] = r or "pdftotext unavailable"
            if r and r.startswith("RESTRICTED"):
                os.remove(tmp); raise PermissionError(r)
            os.replace(tmp, dst)
            rec.update(status="fetched", file=os.path.relpath(dst, a.dest), sha256=sha256(dst), bytes=os.path.getsize(dst),
                       fetched=time.strftime("%Y-%m-%d"))
            out.append(rec)
        except Exception as e:
            print(f"  SKIP {it['id']}: {e}", file=sys.stderr, flush=True)
            rec.update(status="skipped", reason=str(e)[:200]); skipped.append(rec); out.append(rec)
    json.dump({"collection": "ARKive Official Manuals", "license": cat["license"], "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "items": out}, open(mpath + ".tmp", "w"), indent=1)
    os.replace(mpath + ".tmp", mpath)
    f = [r for r in out if r.get("status") == "fetched"]
    print(f"fetched {len(f)} ({sum(r['bytes'] for r in f)/1e6:.1f} MB), in library {sum(r.get('status')=='in_library' for r in out)}, skipped {len(skipped)} -> {mpath}")

if __name__ == "__main__": main()
