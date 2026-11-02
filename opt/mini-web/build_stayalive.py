#!/usr/bin/env python3
"""Build the "Stay Alive" start page and the "Official Manuals" index for the :8080 panel.

Reads stayalive.yaml (needs-first link lists) and the Official Manuals manifest
(/srv/archive/manuals/official/manifest.json, written by tools/fetch_manuals.py), resolves every link
against what is actually installed (library.xml ZIM names, PDFs on disk), checks each kiwix link
answers HTTP 200, and writes body fragments that app.py wraps in the normal page chrome:
  /srv/archive/generated/stayalive.html, official.html, stayalive-report.json
Links to content that is not installed (or not answering) are left out, so the same data file works on
a full ARKive and on the small ARKive:zero library. stdlib + PyYAML (falls back to stayalive.json).
"""
import os, re, sys, json, html, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import arkive_host
A = os.environ.get("ARKIVE_ROOT", "/srv/archive")
LIB = f"{A}/library.xml"; OFF = f"{A}/manuals/official"; OUT = f"{A}/generated"
KIWIX = os.environ.get("ARKIVE_KIWIX", "http://127.0.0.1:80")
HOST = arkive_host()
esc = lambda s: html.escape(str(s), quote=True)

def load_data():
    for p in (os.environ.get("ARKIVE_STAYALIVE"), os.path.join(HERE, "stayalive.yaml"), "/etc/arkive/stayalive.yaml"):
        if p and os.path.isfile(p):
            try:
                import yaml
                return yaml.safe_load(open(p))
            except ImportError:
                j = os.path.splitext(p)[0] + ".json"
                if os.path.isfile(j): return json.load(open(j))
                sys.exit("build_stayalive: PyYAML missing and no stayalive.json next to " + p)
    sys.exit("build_stayalive: stayalive.yaml not found")

def books():
    out = {}
    try: root = ET.parse(LIB).getroot()
    except Exception: return out
    for b in root.iter("book"):
        name = os.path.basename(b.get("path", ""))[:-4]
        if not name: continue
        key = re.sub(r"_\d{4}-\d{2}[a-z]?$", "", name)
        out[key] = (name, b.get("title") or key)
    return out
BOOKS = books()
def find_book(pat):
    if pat.startswith("*"): hit = [k for k in BOOKS if k.endswith(pat[1:])]
    else: hit = [k for k in BOOKS if k == pat]
    return BOOKS[sorted(hit)[0]] if hit else None

_ok = {}
def alive(path):
    if path not in _ok:
        try:
            req = urllib.request.Request(KIWIX + path, headers={"Range": "bytes=0-0"})
            with urllib.request.urlopen(req, timeout=60) as r: _ok[path] = r.status in (200, 206)
        except Exception: _ok[path] = False
    return _ok[path]

try: MAN = {m["id"]: m for m in json.load(open(f"{OFF}/manifest.json"))["items"]}
except Exception: MAN = {}
PUB_SHORT = {"Headquarters, Department of the Army": "US Army", "Headquarters, Department of the Army (archive.org copy)": "US Army"}
def man_source(m):
    pub = PUB_SHORT.get(m.get("publisher", ""), m.get("publisher", "")) or "US Government"
    n = m.get("number", "")
    return f"{n} · {pub}" if n and n not in pub else pub

report = []
def resolve(l):
    """-> (href, source, kind) or None"""
    if "pdf" in l:
        m = MAN.get(l["pdf"])
        if not m: return None
        if m.get("status") == "fetched" and os.path.isfile(os.path.join(OFF, m["file"])):
            href = "/official/" + urllib.parse.quote(m["file"]) + (f"#page={int(l['page'])}" if l.get("page") else "")
            return href, l.get("source") or man_source(m) + (f", p. {int(l['page'])}" if l.get("page") else ""), "pdf"
        if m.get("status") == "in_library":
            b = find_book(m["in_library"]["zim"])
            if not b: return None
            p = f"/content/{b[0]}/" + urllib.parse.quote(m["in_library"]["path"])
            return (("K", p), l.get("source") or f'{m.get("number","")} · {b[1]}', "zim") if alive(p) else None
        return None
    if "zim" in l:
        b = find_book(l["zim"])
        if not b: return None
        p = f"/content/{b[0]}/" + urllib.parse.quote(l.get("path", ""), safe="/:")
        return (("K", p), l.get("source") or b[1], "zim") if alive(p) else None
    if "app" in l:
        return "/" + l["app"].lstrip("/"), l.get("source", "ARKive"), "app"
    return None

def link_html(l):
    r = resolve(l)
    report.append({"label": l.get("label"), "ok": bool(r), "href": (r[0][1] if r and isinstance(r[0], tuple) else (r[0] if r else None)), "spec": {k: v for k, v in l.items() if k != "label"}})
    if not r: return ""
    href, src, kind = r
    if isinstance(href, tuple):  # kiwix (:80) - absolute, rewritten to the current hostname by the one-line script
        href = f"http://{HOST}{href[1]}"; cls = ' class="kx"'
    else: cls = ""
    tag = {"pdf": "PDF", "zim": "Library", "app": "Map"}[kind]
    return (f'<li><a{cls} href="{esc(href)}"><span class="sa-l">{esc(l["label"])}</span>'
            f'<span class="sa-s"><i>{tag}</i> {esc(src)}</span></a></li>')

def section(s, cls="sa-sec"):
    items = "".join(link_html(l) for l in s.get("links", []))
    if not items: return "", None
    blurb = f'<p class="mut">{esc(s["blurb"])}</p>' if s.get("blurb") else ""
    return f'<section class="{cls}" id="{esc(s["id"])}"><h2>{esc(s["title"])}</h2>{blurb}<ul class="sa-list">{items}</ul></section>', (s["id"], s["title"])

def build():
    try: urllib.request.urlopen(KIWIX + "/", timeout=30).read(64)
    except Exception as e:
        print(f"stay-alive: kiwix not reachable at {KIWIX} ({e}); try again later", file=sys.stderr); sys.exit(75)
    d = load_data(); os.makedirs(OUT, exist_ok=True)
    secs, nav = "", []
    for s in d.get("sections", []):
        h, n = section(s); secs += h; nav += [n] if n else []
    reb = "".join(section(s, "sa-sec sa-sub")[0] for s in d.get("rebuild", []))
    if reb: secs += f'<section class="sa-sec" id="rebuild"><h2>Rebuild</h2><p class="mut">Power, water systems, construction, agriculture, repair</p>{reb}</section>'; nav.append(("rebuild", "Rebuild"))
    mp = "".join(link_html(l) for l in d.get("maps", []))
    if mp: secs += f'<section class="sa-sec" id="maps"><h2>Maps</h2><ul class="sa-list">{mp}</ul></section>'; nav.append(("maps", "Maps"))
    chips = "".join(f'<a href="#{esc(i)}">{esc(t)}</a>' for i, t in nav)
    body = (f'<div class="sa"><h1>Stay Alive</h1><p class="mut">Pick what you need right now. Official manuals first, then the best articles in this library. Everything here works offline.</p>'
            f'<nav class="sa-nav" aria-label="Topics">{chips}</nav>{secs}'
            f'<p class="mut sa-note">Not medical or professional advice; in an emergency, call for help if you can. PDF links open at the right page.</p></div>'
            "<script>document.querySelectorAll('a.kx').forEach(function(a){var u=new URL(a.href);u.hostname=location.hostname;a.href=u.href})</script>")
    write("stayalive.html", body)
    write("official.html", official())
    ok = sum(r["ok"] for r in report)
    json.dump({"built": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "shown": ok, "hidden": len(report) - ok, "links": report},
              open(f"{OUT}/stayalive-report.json", "w"), indent=1)
    print(f"stay-alive: {ok} links shown, {len(report)-ok} hidden (not installed / not 200)")

def official():
    if not MAN: return '<div class="card">The Official Manuals collection is not installed. Run <code>tools/fetch_manuals.py</code>.</div>'
    subj = {}
    for m in MAN.values():
        if m.get("status") == "fetched" and os.path.isfile(os.path.join(OFF, m["file"])):
            href = "/official/" + urllib.parse.quote(m["file"]); tag = f'PDF · {m.get("bytes",0)/1e6:.1f} MB'
        elif m.get("status") == "in_library" and (b := find_book(m["in_library"]["zim"])):
            href = f'http://{HOST}/content/{b[0]}/{urllib.parse.quote(m["in_library"]["path"])}'; tag = f"in {b[1]}"
        else: continue
        sup = f'<small class="sup">Superseded by {esc(m["superseded_by"])}</small>' if m.get("superseded_by") else ""
        ed = f' · {esc(m["edition"])}' if m.get("edition") else ""
        subj.setdefault(m["subject"], []).append(
            f'<li><a{" class=kx" if href.startswith("http") else ""} href="{esc(href)}"><span class="sa-l">{esc(m["number"])}: {esc(m["title"])}</span>'
            f'<span class="sa-s"><i>{esc(tag)}</i>{ed}</span>{sup}</a></li>')
    order = ["Survival", "First aid & medical", "Water & sanitation", "Food", "Navigation", "Weather & hazards", "Preparedness", "Mountains & cold", "Rebuild: power & engineering"]
    body = "".join(f'<section class="sa-sec"><h2>{esc(s)}</h2><ul class="sa-list">{"".join(subj[s])}</ul></section>'
                   for s in sorted(subj, key=lambda s: order.index(s) if s in order else 99))
    return (f'<div class="sa"><h1>Official Manuals</h1><p class="mut">US Government field manuals and guides (public domain), grouped by subject. '
            f'<a href="/official/manifest.json">Manifest</a> lists source, edition and sha256 for each file.</p>{body}</div>'
            "<script>document.querySelectorAll('a.kx').forEach(function(a){var u=new URL(a.href);u.hostname=location.hostname;a.href=u.href})</script>")

def write(name, s):
    p = f"{OUT}/{name}"; open(p + ".tmp", "w").write(s); os.replace(p + ".tmp", p)

if __name__ == "__main__":
    if "--export-json" in sys.argv:  # for devices without PyYAML (ARKive:zero)
        import yaml; src = os.path.join(HERE, "stayalive.yaml")
        json.dump(yaml.safe_load(open(src)), open(os.path.splitext(src)[0] + ".json", "w"), indent=1); sys.exit()
    build()
