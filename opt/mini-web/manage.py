"""Media management for /srv/personal: trash (30-day auto purge), move, rename, delete album/folder, cover, zip."""
import os, re, json, time, shutil, secrets, zipfile
from common import *
TR = P + "/.trash"; KEEP = 30 * 86400; SUF = (".t.jpg", ".v.jpg", ".json")
PEXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif", ".tif", ".tiff", ".bmp")
MEXT = (".mp3", ".m4a", ".ogg", ".opus", ".flac", ".wav", ".aac")
KINDS = {"photos": (P + "/photos", P + "/.thumbs", PEXT), "music": (P + "/music", None, MEXT)}
def kick(): open(P + "/.thumbs/.kick", "w").close()
def thumbs_move(th, base, src, dst):
    if not th: return
    a = os.path.join(th, os.path.relpath(src, base)); b = os.path.join(th, os.path.relpath(dst, base)) if dst else None
    if os.path.isdir(a):
        if b: shutil.rmtree(b, ignore_errors=True); os.makedirs(os.path.dirname(b), exist_ok=True); os.rename(a, b)
        else: shutil.rmtree(a, ignore_errors=True)
    for s in SUF:
        if os.path.exists(a + s):
            if b: os.makedirs(os.path.dirname(b), exist_ok=True); os.replace(a + s, b + s)
            else: os.remove(a + s)
def count(real, exts):
    if os.path.isfile(real): return 1
    return sum(1 for r, ds, fs in os.walk(real) for f in fs if f.lower().endswith(exts))
def uniq(path):
    b, e = os.path.splitext(path); i = 2
    while os.path.exists(path): path = f"{b} ({i}){e}"; i += 1
    return path
def check(kind, rel, isdir=None):
    """server-side path safety: inside the kind's base, not the base itself, no hidden components, right type"""
    base, th, exts = KINDS[kind]; real = safe(base, rel)
    if not real or real == base or any(p.startswith(".") for p in os.path.relpath(real, base).split("/")): raise ValueError("bad path")
    if os.path.islink(real) or not os.path.exists(real): raise ValueError("not found: " + rel)
    if isdir is True and not os.path.isdir(real): raise ValueError("not a folder")
    if isdir is False and not (os.path.isfile(real) and real.lower().endswith(exts)): raise ValueError("not a media file")
    return real
def to_trash(kind, real):
    base, th, exts = KINDS[kind]; n = count(real, exts)
    tid = time.strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(3); d = os.path.join(TR, tid); os.makedirs(d)
    json.dump({"kind": kind, "rel": os.path.relpath(real, base), "t": time.time(), "n": n, "dir": os.path.isdir(real)}, open(d + "/meta.json", "w"))
    os.rename(real, d + "/item"); thumbs_move(th, base, real, None); return n
def entries():
    out = []
    if os.path.isdir(TR):
        for t in sorted(os.listdir(TR), reverse=True):
            try: m = json.load(open(os.path.join(TR, t, "meta.json"))); m["id"] = t; out.append(m)
            except Exception: pass
    return out
def purge():
    for m in entries():
        if time.time() - m["t"] > KEEP: shutil.rmtree(os.path.join(TR, m["id"]), ignore_errors=True)
def tid_ok(t): return bool(re.fullmatch(r"\d{8}-\d{6}-[0-9a-f]{6}", t or "")) and os.path.isdir(os.path.join(TR, t))
def newname(old, new, exts, isdir):
    new = (new or "").strip()
    if not new or "/" in new or "\\" in new or ".." in new or new.startswith(".") or clean_name(new) != new: raise ValueError("invalid name: no slashes, no '..', no leading dot")
    if not isdir:
        e = os.path.splitext(old)[1]
        if not new.lower().endswith(exts): new += e
    return new
def op(f, mpv_drop=None):
    """returns message; raises ValueError on bad input"""
    o = f.get("op", ""); kind = f.get("kind", "")
    purge()
    if o in ("restore", "forget"):
        t = f.get("id", "")
        if not tid_ok(t): raise ValueError("unknown trash item")
        d = os.path.join(TR, t); m = json.load(open(d + "/meta.json"))
        if o == "forget": shutil.rmtree(d); return f"Permanently deleted {esc(m['rel'])}."
        base = KINDS[m["kind"]][0]; dst = safe(base, m["rel"])
        if not dst or dst == base: raise ValueError("bad trash entry")
        dst = uniq(dst); os.makedirs(os.path.dirname(dst), exist_ok=True); os.rename(d + "/item", dst); shutil.rmtree(d)
        if m["kind"] == "photos": kick()
        return f"Restored {esc(os.path.relpath(dst, base))}."
    if o == "empty":
        n = len(entries()); shutil.rmtree(TR, ignore_errors=True); return f"Trash emptied ({n} item(s) permanently deleted)."
    if kind not in KINDS: raise ValueError("bad kind")
    base, th, exts = KINDS[kind]
    paths = json.loads(f.get("paths") or "[]")
    if not isinstance(paths, list) or not paths or len(paths) > 5000: raise ValueError("nothing selected")
    if o == "delete":
        reals = [check(kind, p, False) for p in paths]; n = 0
        for r in reals:
            n += to_trash(kind, r)
            if mpv_drop: mpv_drop(r)
        return f"Moved {n} item(s) to Trash."
    if o == "rmdir":
        r = check(kind, paths[0], True); n = to_trash(kind, r)
        if mpv_drop: mpv_drop(r + "/")
        return f"Moved folder {esc(paths[0])} ({n} file(s)) to Trash."
    if o == "move":
        if ".." in f.get("dest", "") or f.get("dest", "").strip().startswith("/"): raise ValueError("bad destination")
        dest = clean_rel(f.get("dest", ""))
        if not dest: raise ValueError("choose a destination")
        dr = safe(base, dest)
        if not dr or any(p.startswith(".") for p in dest.split("/")): raise ValueError("bad destination")
        reals = [check(kind, p, False) for p in paths]; os.makedirs(dr, exist_ok=True); n = 0
        for r in reals:
            if os.path.dirname(r) == dr: continue
            t = uniq(os.path.join(dr, os.path.basename(r))); os.rename(r, t); thumbs_move(th, base, r, t); n += 1
            if mpv_drop: mpv_drop(r)
        return f"Moved {n} item(s) to {esc(dest)}."
    if o == "rename":
        r = check(kind, paths[0]); isd = os.path.isdir(r)
        nm = newname(os.path.basename(r), f.get("new"), exts, isd); t = os.path.join(os.path.dirname(r), nm)
        if t == r: raise ValueError("that is already its name")
        if any(x.lower() == nm.lower() for x in os.listdir(os.path.dirname(r)) if os.path.join(os.path.dirname(r), x) != r): raise ValueError(f"'{nm}' already exists there")
        os.rename(r, t); thumbs_move(th, base, r, t)
        if mpv_drop: mpv_drop(r)
        return f"Renamed to {esc(nm)}."
    if o == "cover" and kind == "photos":
        r = check(kind, paths[0], False); d = os.path.dirname(r)
        if d == base: raise ValueError("photos in the top level have no album")
        open(d + "/.cover", "w").write(os.path.basename(r)); return f"Album cover set to {esc(os.path.basename(r))}."
    raise ValueError("unknown action")
def cover(d, exts):
    try:
        c = open(os.path.join(d, ".cover")).read().strip()
        if c and "/" not in c and os.path.isfile(os.path.join(d, c)): return c
    except OSError: pass
    return next((f for f in sorted(os.listdir(d)) if f.lower().endswith(exts)), None)
def zip_stream(kind, paths, w):
    base, th, exts = KINDS[kind]
    with zipfile.ZipFile(w, "w", zipfile.ZIP_STORED, allowZip64=True) as z:
        for p in paths[:5000]:
            r = check(kind, p)
            files = [r] if os.path.isfile(r) else [os.path.join(a, x) for a, ds, fs in os.walk(r) for x in fs if x.lower().endswith(exts)]
            for fp in files: z.write(fp, os.path.relpath(fp, os.path.dirname(r)))
def trash_page():
    purge(); es = entries(); now = time.time()
    rows = "".join(
        f'<div class="job"><div class="row"><b>{"📁 " if m["dir"] else ""}{esc(m["rel"])}</b><span class="mut">{m["kind"]} · {m["n"]} file(s) · deleted {time.strftime("%b %d %H:%M", time.localtime(m["t"]))} · '
        f'purged in {max(0, int((m["t"] + KEEP - now) // 86400))} days</span></div>'
        f'<form method="post" action="/admin/trash" style="display:inline">{{CSRF}}<input type="hidden" name="id" value="{m["id"]}"><button name="op" value="restore" class="pri">Restore</button> '
        f'<button name="op" value="forget" class="bad" onclick="return confirm(\'Delete permanently?\')">Delete forever</button></form></div>' for m in es)
    return (f'<h1 style="margin:4px 0">🗑 Trash</h1><p class="mut">Deleted photos, tracks, albums and folders wait here for 30 days, then are removed automatically.</p>'
            f'<div class="card">{rows or "<p class=mut>Trash is empty.</p>"}</div>'
            + (f'<form method="post" action="/admin/trash">{{CSRF}}<button name="op" value="empty" class="bad" onclick="return confirm(\'Permanently delete all {len(es)} item(s) in the Trash?\')">Empty trash</button></form>' if es else "")
            + '<p><a class="btn" href="/admin/photos">Photos</a> <a class="btn" href="/admin/music">Music</a></p>')
def toolbar(kind, folders, here="", here_n=0):
    """selection toolbar (photos/music) + delete-folder button"""
    dl = "".join(f'<option value="{esc(x)}">' for x in folders)
    del_dir = (f'<button class="bad" data-rmdir="{esc(here)}" data-n="{here_n}">Delete this {"album" if kind == "photos" else "folder"}…</button>' if here else "")
    return (f'<div id="mg" class="mgbar" data-kind="{kind}"><button id="mgsel">☑ Select</button>'
            f'<span id="mgtools" hidden><button id="mgall">Select all</button><b id="mgn">0 selected</b>'
            f'<button id="mgdel" class="bad">Delete</button><input id="mgdest" list="mgdl" placeholder="{"album" if kind == "photos" else "folder"} name"><datalist id="mgdl">{dl}</datalist>'
            f'<button id="mgmv">Move</button><button id="mgzip">Download zip</button></span>'
            f'<span class="sp"></span>{del_dir}<a class="btn" href="/admin/trash">🗑 Trash</a></div>')
