"""/find: home-page search across every English, full-text-indexed ZIM, working around a kiwix-serve bug.

kiwix-serve (3.7.0 and 3.8.2) fails a multi-ZIM search page with "basic_string::substr: __pos (which is 2) >
this->size() (which is 0)" (a 500, or with 3.8 the text inside a 200 page) when one particular hit lands on it. The
broken hit depends on the whole book set (ranking statistics change with the set), so dropping books is unreliable.
Instead the wrapper keeps all books and works per result: it asks kiwix for the page; if it is broken it splits the
result range in halves (in parallel) down to single results, skips the single broken ones, and stitches the good hits
back into kiwix's own page. Broken result ranks are cached per query (memory + /var/cache/mini-web), so repeat and
neighbouring pages fetch only the good spans. If the hunt runs past a deadline, the remaining broken spans are skipped
and the page is shown with what was found. Pagination links point back through /find."""
import os, re, json, time, html, threading, urllib.parse, urllib.request, xml.etree.ElementTree as ET

KIWIX = "http://127.0.0.1:80"; LIB = "/srv/archive/library.xml"; CACHE = "/var/cache/mini-web/search-bad.json"
DEADLINE = 90; REQ_TIMEOUT = 150; BAD_RX = re.compile(rb"basic_string::substr|Internal Server Error")
_lock = threading.Lock(); _ids = {"mt": 0, "ids": []}
_mem = {"mt": 0, "q": {}}

def all_ids():
    mt = os.path.getmtime(LIB)
    if mt != _ids["mt"]:
        _ids.update(mt=mt, ids=[b.get("id") for b in ET.parse(LIB).getroot().iter("book")
                                if b.get("language") == "eng" and "_ftindex:yes" in (b.get("tags") or "") and b.get("id")])
    return list(_ids["ids"])

def _bad_ranks(key):
    with _lock:
        if not _mem["q"]:
            try: _mem.update(json.load(open(CACHE)))
            except Exception: pass
        if _mem["mt"] != _ids["mt"]: _mem.update(mt=_ids["mt"], q={})   # library changed: ranks are stale
        return set(_mem["q"].get(key, []))
def _add_bad(key, ranks):
    with _lock:
        _mem["q"][key] = sorted(set(_mem["q"].get(key, [])) | set(ranks))
        if len(_mem["q"]) > 3000: _mem["q"] = dict(list(_mem["q"].items())[-2000:])
        try:
            os.makedirs(os.path.dirname(CACHE), exist_ok=True); tmp = CACHE + ".tmp"
            json.dump(_mem, open(tmp, "w")); os.replace(tmp, CACHE)
        except OSError: pass

def fetch(ids, pattern, start, n):
    qs = urllib.parse.urlencode([("pattern", pattern), ("start", start), ("pageLength", n)] + [("books.id", i) for i in ids])
    try:
        with urllib.request.urlopen(KIWIX + "/search?" + qs, timeout=REQ_TIMEOUT) as r: code, body = r.status, r.read()
    except urllib.error.HTTPError as e: code, body = e.code, e.read()
    except Exception as e: return False, 0, str(e)
    body = body.decode("utf-8", "replace")
    return (code < 500 and not BAD_RX.search(body.encode())), code, body

_ITEMS = re.compile(r'<div class="results">\s*<ul>(.*?)</ul>\s*</div>', re.S)
_LI = re.compile(r"<li>.*?</li>", re.S)
_TOTAL = re.compile(r"of <b>([\d,]+)</b>")
def get_span(ids, pattern, start, n, deadline, out):
    """Collect good hits for ranks start..start+n-1 into out['items'][rank]; record broken ranks in out['bad']."""
    ok, code, body = fetch(ids, pattern, start, n)
    if ok:
        out.setdefault("page", body)
        m = _TOTAL.search(body)
        if m: out["total"] = int(m.group(1).replace(",", ""))
        lis = _LI.findall((_ITEMS.search(body) or [None, ""])[1] if _ITEMS.search(body) else "")
        for k, li in enumerate(lis): out["items"][start + k] = li
        return
    if code == 0: out["err"] = body; return
    if n == 1: out["bad"].add(start); return
    if time.time() > deadline: out["bad"].update(range(start, start + n)); out["timed_out"] = True; return
    h = n // 2   # probe both halves at once: one in a helper thread, one here
    t = threading.Thread(target=get_span, args=(ids, pattern, start, h, deadline, out)); t.start()
    get_span(ids, pattern, start + h, n - h, deadline, out); t.join()

def search(pattern, start, plen):
    ids = all_ids(); key = pattern.strip().lower(); t0 = time.time(); deadline = t0 + DEADLINE
    known = {r for r in _bad_ranks(key) if start <= r < start + plen}
    out = {"items": {}, "bad": set(known), "timed_out": False}
    # contiguous spans of the requested range that are not known to be broken
    spans, s = [], None
    for r in range(start, start + plen + 1):
        if r < start + plen and r not in known: s = r if s is None else s
        elif s is not None: spans.append((s, r - s)); s = None
    for sp in spans: get_span(ids, pattern, sp[0], sp[1], deadline, out)
    new_bad = out["bad"] - known
    if new_bad and not out["timed_out"]: _add_bad(key, new_bad)
    out["secs"] = round(time.time() - t0, 1); return out

def _footer(pattern, start, plen, total):
    if not total: return ""
    pages = (total + plen - 1) // plen; cur = (start - 1) // plen
    def link(p, label, sel=False):
        q = urllib.parse.urlencode({"pattern": pattern, "start": p * plen + 1, "pageLength": plen})
        return f'<li><a{" class=selected" if sel else ""} href="/find?{html.escape(q)}">{label}</a></li>'
    lis = []
    if cur > 0: lis.append(link(0, "&#9664;"))
    for p in range(max(0, cur - 4), min(pages, cur + 5)): lis.append(link(p, p + 1, p == cur))
    if cur < pages - 1: lis.append(link(pages - 1, "&#9654;"))
    return '<div class="footer"><ul>' + "".join(lis) + "</ul></div>"

_HREF = re.compile(r'(href|src)="(/[^"]*)"')
def render(pattern, start, plen, host):
    start = max(1, start); out = search(pattern, start, plen); kx = f"http://{host}"
    items = [out["items"][r] for r in sorted(out["items"])]; total = out.get("total", 0); nbad = len(out["bad"])
    page = out.get("page") or ('<!DOCTYPE html><html><head><meta charset="utf-8"><title>Search</title></head><body>'
                               '<div class="header"></div><div class="results"><ul></ul></div><div class="footer"></div></body></html>')
    hdr = (f'Results <b>{start}-{start + plen - 1 if total >= start + plen - 1 else total}</b> of <b>{total:,}</b> for <b>"{html.escape(pattern)}"</b>'
           if total else f'No results were found for <b>"{html.escape(pattern)}"</b>')
    page = re.sub(r'<div class="header">.*?</div>', lambda m: f'<div class="header">{hdr}</div>', page, count=1, flags=re.S)
    page = _ITEMS.sub(lambda m: '<div class="results"><ul>' + "\n".join(items) + "</ul></div>", page, count=1) if _ITEMS.search(page) else page
    page = re.sub(r'<div class="footer">.*</div>\s*(?=</body>)', lambda m: _footer(pattern, start, plen, total), page, count=1, flags=re.S)
    page = _HREF.sub(lambda m: f'{m.group(1)}="{kx}{m.group(2)}"' if not m.group(2).startswith("/find?") else m.group(0), page)
    bar = (f'<div style="font:14px system-ui,sans-serif;margin:0 0 .6em"><a href="{kx}/">&larr; ARKive home</a>'
           f'<form action="/find" method="get" style="display:inline;margin-left:1em"><input name="pattern" value="{html.escape(pattern)}" aria-label="Search">'
           f' <button>Search</button></form>')
    if nbad: bar += f' <span style="color:#666;font-size:.9em">&middot; {nbad} result{"s" if nbad != 1 else ""} on this page could not be shown (kiwix error)</span>'
    if out.get("err"): bar += f' <p style="color:#B3392F">Search is not responding right now ({html.escape(str(out["err"])[:120])}). Try again in a minute.</p>'
    bar += "</div>"
    page = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + bar, page, count=1)
    return (502 if out.get("err") and not items else 200), page, out, nbad
