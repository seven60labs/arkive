#!/usr/bin/env python3
"""Build the "Maslow index" page for the :8080 panel: the whole archive sorted into Maslow's five levels.

Reads maslow.yaml (falls back to maslow.json on devices without PyYAML, e.g. ARKive:zero), resolves every item
against what is installed (library.xml ZIMs, Official Manuals manifest, files on disk), checks each kiwix link
answers 200, and writes a body fragment that app.py wraps in the normal page chrome:
  /srv/archive/generated/maslow.html, maslow-report.json
Items that are not installed are left out; a group, level or pyramid tier with nothing left is hidden.
Level 1 and half of level 2 link to the Stay Alive sections (only those Stay Alive actually rendered).
The report also lists installed ZIMs that no item covers ("unsorted"), so new collections get noticed.
Reuses the resolvers in build_stayalive.py. stdlib + PyYAML.
"""
import os, re, sys, json, html, time, urllib.parse, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import build_stayalive as sa
from build_stayalive import esc, BOOKS, MAN, OFF, OUT, HOST, KIWIX, alive, find_book, man_source, write
MANUALS = os.path.join(sa.A, "manuals")  # root of the :8080 file browser
TIERS = {1: "Body", 2: "Safety", 3: "People", 4: "Skills", 5: "Meaning"}

def load_data():
    for p in (os.environ.get("ARKIVE_MASLOW"), os.path.join(HERE, "maslow.yaml"), "/etc/arkive/maslow.yaml"):
        if p and os.path.isfile(p):
            try:
                import yaml
                return yaml.safe_load(open(p))
            except ImportError:
                j = os.path.splitext(p)[0] + ".json"
                if os.path.isfile(j): return json.load(open(j))
                sys.exit("build_maslow: PyYAML missing and no maslow.json next to " + p)
    sys.exit("build_maslow: maslow.yaml not found")

used = set(); report = []
def hs(kb):
    n = kb * 1024
    return f"{n/1e9:.1f} GB" if n >= 1e9 else f"{n/1e6:.0f} MB"
SIZES = {}
def _sizes():
    import xml.etree.ElementTree as ET
    try:
        for b in ET.parse(sa.LIB).getroot().iter("book"):
            SIZES[os.path.basename(b.get("path", ""))[:-4]] = int(b.get("size") or 0)
    except Exception: pass
_sizes()

def zim_entry(key, label=None, path="", note=None):
    """-> (kind, href, label, note) for an installed, answering ZIM; key is the undated name"""
    name, title = BOOKS[key]
    p = f"/content/{name}" + ("/" + urllib.parse.quote(path, safe="/:()',") if path else "")
    if not alive(p): return None
    if not path: used.add(key)
    sz = SIZES.get(name)
    return ("zim", ("K", p), label or title, note or (f"{title} · {hs(sz)}" if label and sz else (hs(sz) if sz else "")))

def resolve(it):
    """-> list of (kind, href, label, note)"""
    if "zim" in it:
        b = find_book(it["zim"])
        if not b: return []
        key = [k for k, v in BOOKS.items() if v[0] == b[0]][0]
        r = zim_entry(key, it.get("label"), it.get("path", ""), it.get("note"))
        return [r] if r else []
    if "match" in it:
        rx = re.compile(it["match"]); out = []
        for k in sorted(BOOKS):
            if rx.search(k):
                r = zim_entry(k)
                if r: out.append(r)
        return out
    if "pdf" in it:
        m = MAN.get(it["pdf"])
        if not m: return []
        lab = it.get("label") or f'{m.get("number","")}: {m.get("title","")}'.strip(": ")
        if m.get("status") == "fetched" and os.path.isfile(os.path.join(OFF, m["file"])):
            return [("pdf", "/official/" + urllib.parse.quote(m["file"]), lab, it.get("note") or man_source(m))]
        if m.get("status") == "in_library":
            b = find_book(m["in_library"]["zim"])
            if not b: return []
            p = f"/content/{b[0]}/" + urllib.parse.quote(m["in_library"]["path"])
            return [("pdf", ("K", p), lab, it.get("note") or f"{man_source(m)} · in {b[1]}")] if alive(p) else []
        return []
    if "file" in it:
        rel = it["file"].lstrip("/"); real = os.path.realpath(os.path.join(MANUALS, rel))
        if not os.path.exists(real): return []
        return [("file", "/" + urllib.parse.quote(rel), it.get("label") or os.path.basename(rel.rstrip("/")), it.get("note") or "ARKive files")]
    if "app" in it:
        return [("app", "/" + it["app"].lstrip("/"), it.get("label") or it["app"], it.get("note") or "ARKive")]
    return []

TAG = {"zim": "Library", "pdf": "Manual", "file": "File", "app": "Map"}
def li(e):
    kind, href, label, note = e
    cls = ""
    if isinstance(href, tuple): href = f"http://{HOST}{href[1]}"; cls = ' class="kx"'
    n = f' {esc(note)}' if note else ""
    return f'<li><a{cls} href="{esc(href)}"><span class="sa-l">{esc(label)}</span><span class="sa-s"><i>{TAG[kind]}</i>{n}</span></a></li>'

def item_html(it):
    es = resolve(it)
    report.append({"item": {k: v for k, v in it.items()}, "shown": len(es),
                   "hrefs": [e[1][1] if isinstance(e[1], tuple) else e[1] for e in es]})
    if not es: return "", []
    if "match" in it and len(es) > 4:  # fold long families (DevDocs, Q&A sets) into one entry
        inner = "".join(li(e) for e in es)
        return (f'<li class="mz-fold"><details><summary><span class="sa-l">{esc(it.get("label","More"))}</span>'
                f'<span class="sa-s"><i>Library</i> {len(es)} collections</span></summary><ul class="sa-list">{inner}</ul></details></li>'), es
    return "".join(li(e) for e in es), es

def stayalive_ids():
    try: s = open(os.path.join(OUT, "stayalive.html")).read()
    except OSError: return {}
    out = {}
    for m in re.finditer(r'<section class="sa-sec[^"]*" id="([^"]+)"><h2>(?:<svg[^>]*>.*?</svg>)?([^<]+)</h2>', s): out[m.group(1)] = html.unescape(m.group(2))
    for m in re.finditer(r'<span id="([^"]+)" class="sa-anchor"></span>', s): out.setdefault(m.group(1), m.group(1).replace("-", " ").title())
    return out

def build():
    try: urllib.request.urlopen(KIWIX + "/", timeout=30).read(64)
    except Exception as e:
        print(f"maslow: kiwix not reachable at {KIWIX} ({e}); try again later", file=sys.stderr); sys.exit(75)
    d = load_data(); os.makedirs(OUT, exist_ok=True)
    sav = stayalive_ids(); levels = []; summary = []
    for L in d.get("levels", []):
        groups = ""; n_items = 0; n_coll = 0; gsum = []
        for g in L.get("groups", []):
            parts = [item_html(it) for it in g.get("items", [])]
            body = "".join(p[0] for p in parts); es = [e for p in parts for e in p[1]]
            if not es: continue
            n_items += len(es); n_coll += sum(1 for e in es if e[0] == "zim")
            gsum.append({"group": g["title"], "entries": len(es)})
            groups += f'<section class="mz-grp"><h3>{esc(g["title"])}</h3><ul class="sa-list">{body}</ul></section>'
        chips = [(i, sav[i]) for i in L.get("stayalive", []) if i in sav]
        sa_box = ""
        if chips:
            sa_box = ('<div class="mz-sa"><p><b>Start with Stay Alive.</b> Step-by-step pages for this level are already there:</p><nav class="sa-nav">'
                      + "".join(f'<a href="/stay-alive#{esc(i)}">{esc(t)}</a>' for i, t in chips) + "</nav></div>")
        if not groups and not sa_box: continue  # nothing installed for this level
        lid = f'lvl-{L["n"]}'
        levels.append((L, lid, n_items,
            f'<section class="mz-lvl mz-l{int(L["n"])}" id="{esc(lid)}"><h2><span class="mz-n">{int(L["n"])}</span>{esc(L["title"])}</h2>'
            f'<p class="mut">{esc(L.get("blurb",""))}</p>{sa_box}{groups}</section>'))
        summary.append({"level": L["n"], "title": L["title"], "entries": n_items, "zim_entries": n_coll,
                        "stayalive_links": [c[0] for c in chips], "groups": gsum})
    # stepped pyramid: level 5 on top (narrowest) down to level 1 (widest); only levels that have content
    tiers = "".join(f'<a class="mz-t mz-t{int(L["n"])}" href="#{lid}"><b>{esc(L["title"])}</b><small>{int(L["n"])} · {esc(TIERS.get(L["n"], ""))} · {n} entries</small></a>'
                    for L, lid, n, _ in sorted(levels, key=lambda x: -x[0]["n"]))
    body = ('<div class="sa mz"><h1>Maslow index</h1><p class="mut">The whole archive sorted by need, from staying alive up to meaning. '
            'Start at the bottom of the pyramid; each step links down to its collections. Everything here works offline.</p>'
            f'<nav class="mz-pyr" aria-label="Levels, top to bottom">{tiers}</nav>'
            + "".join(x[3] for x in levels) +
            '<p class="mut sa-note">Collections not installed on this ARKive are left out automatically. Stay Alive has the first-response articles; this page is the full shelf.</p></div>'
            "<script>document.querySelectorAll('a.kx').forEach(function(a){var u=new URL(a.href);u.hostname=location.hostname;a.href=u.href})</script>")
    write("maslow.html", body)
    unsorted = sorted(BOOKS[k][0] for k in BOOKS if k not in used)
    shown = sum(r["shown"] > 0 for r in report)
    json.dump({"built": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "items_shown": shown, "items_hidden": len(report) - shown,
               "levels": summary, "unsorted_zims": unsorted, "items": report}, open(f"{OUT}/maslow-report.json", "w"), indent=1)
    print(f"maslow: {shown} items shown, {len(report)-shown} hidden; {len(unsorted)} installed ZIMs unsorted")

if __name__ == "__main__":
    if "--export-json" in sys.argv:  # for devices without PyYAML (ARKive:zero)
        import yaml; src = os.path.join(HERE, "maslow.yaml")
        json.dump(yaml.safe_load(open(src)), open(os.path.splitext(src)[0] + ".json", "w"), indent=1); sys.exit()
    build()
