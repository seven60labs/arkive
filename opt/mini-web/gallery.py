"""Photo gallery (admin only): albums = folders under /srv/personal/photos. Thumbs/views built by mini-thumbs."""
import os, json, time, urllib.parse
from common import *
from icons import svg
import manage
PH = P + "/photos"; TH = P + "/.thumbs"
EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif", ".tif", ".tiff", ".bmp")
def albums():
    out = []
    for r, ds, fs in os.walk(PH):
        ds[:] = sorted(d for d in ds if not d.startswith("."))
        rel = os.path.relpath(r, PH)
        if rel != "." : out.append(rel)
    return out
def meta(rel):
    try: return json.load(open(os.path.join(TH, rel) + ".json"))
    except Exception: return {}
def page(rel=""):
    base = safe(PH, rel)
    if not base or not os.path.isdir(base): return '<div class="card">Album not found.</div>'
    parts = [p for p in rel.split("/") if p]
    cr = f'<nav class="crumbs"><a href="/admin/photos">{svg("img")} Photos</a>' + "".join(f'{svg("chev")}<a href="/admin/photos?a={q("/".join(parts[:i+1]))}">{esc(p)}</a>' for i, p in enumerate(parts)) + "</nav>"
    subs = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)) and not d.startswith("."))
    pics = sorted((f for f in os.listdir(base) if f.lower().endswith(EXT)), key=lambda f: (meta(os.path.join(rel, f)).get("date") or "9999", f))
    tiles = ""
    for d in subs:
        cover = manage.cover(os.path.join(base, d), EXT)
        img = f'<img loading="lazy" src="/admin/photos/thumb?p={q(os.path.join(rel, d, cover))}" alt="">' if cover else svg("folder", "t-dir")
        n = sum(1 for f in os.listdir(os.path.join(base, d)) if f.lower().endswith(EXT))
        tiles += f'<a class="ph alb" href="/admin/photos?a={q(os.path.join(rel, d))}">{img}<span>{esc(d)}<small>{n} photos</small></span></a>'
    items = []
    for i, f in enumerate(pics):
        r = os.path.join(rel, f); m = meta(r)
        items.append({"v": f"/admin/photos/view?p={q(r)}", "o": f"/admin/photos/orig?p={q(r)}", "n": f, "d": m.get("date", ""), "p": r})
        tiles += f'<a class="ph" href="/admin/photos/view?p={q(r)}" data-i="{i}" data-p="{esc(r)}"><img loading="lazy" src="/admin/photos/thumb?p={q(r)}" alt="{esc(f)}"></a>'
    up = (f'<details class="card"><summary><b>Upload photos</b></summary><form class="stack" data-up="photos" method="post" enctype="multipart/form-data" action="/admin/photos/upload?a={q(rel)}">{{CSRF}}'
          f'<input type="file" name="files" multiple accept="image/*,.heic,.heif" required><label>Album<input type="text" name="album" value="{esc(rel)}" placeholder="new album name"></label><button class="pri">Upload</button></form></details>'
          f'<details class="card"><summary><b>Import from USB stick / SD card</b></summary>{import_form("/admin/photos/import", albums(), "album")}</details>{import_status()}<script src="/static/upload.js"></script>')
    if rel:
        up += (f'<details class="card"><summary><b>Rename album</b></summary><form class="stack" method="post" action="/admin/photos/rename">{{CSRF}}'
               f'<input type="hidden" name="a" value="{esc(rel)}"><label>New name for “{esc(parts[-1])}” (sub-albums and thumbnails move with it)'
               f'<input type="text" name="new" value="{esc(parts[-1])}" maxlength="150" required></label><button class="pri">Rename</button></form></details>')
    pend = sum(1 for f in pics if not os.path.exists(os.path.join(TH, rel, f) + ".t.jpg"))
    note = f'<p class="mut">{pend} thumbnails still being generated in the background.</p>' if pend else ""
    lb = ('<div id="lb" hidden><img id="lbi" alt=""><div class="lbbar"><span id="lbn"></span><span class="sp"></span><a id="lbo" class="btn" download>Original</a>'
          '<button id="lbp">‹</button><button id="lbx">✕</button><button id="lbnx">›</button></div></div>'
          f'<script>var P={json.dumps(items)};</script><script src="/static/lightbox.js"></script><script src="/static/manage.js"></script>')
    tb = manage.toolbar("photos", albums(), rel, manage.count(base, EXT) if rel else 0)
    lb = lb.replace('<button id="lbp">', '<button id="lbren" title="Rename">✎</button><button id="lbcov" title="Use as album cover">★</button><button id="lbdel" title="Move to Trash">🗑</button><button id="lbp">')
    return f'<h1 style="margin:4px 0">{esc(parts[-1] if parts else "Photos")}</h1>{cr}{note}{tb}<div class="phgrid">{tiles or "<p class=mut>No photos here yet.</p>"}</div>{up}{lb}'
def upload(fields, files, rel):
    album = "/".join(clean_name(x) for x in (fields.get("album") or rel or "Uploads").split("/") if clean_name(x)) or "Uploads"
    if not files: return "No files received.", album
    dest = safe(PH, album)
    if not dest: return "Bad album name."
    os.makedirs(dest, exist_ok=True); n = 0
    for fn, data in files:
        name = clean_name(fn)
        if not name.lower().endswith(EXT) or not data: continue
        t = os.path.join(dest, name)
        if os.path.exists(t): b, e = os.path.splitext(name); t = os.path.join(dest, f"{b}-{int(time.time())}{e}")
        open(t, "wb").write(data); n += 1
    open(TH + "/.kick", "w").close()
    return f"Uploaded {n} photo(s) to {esc(album)}.", album
