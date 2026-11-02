"""Shared helpers for personal-space admin modules (photos, music)."""
import os, re, html, hashlib, urllib.parse, email.parser, email.policy, shutil, threading, time, json
P = "/srv/personal"; MEDIA = "/media/usb"
def esc(s): return html.escape(str(s), quote=True)
def q(s): return urllib.parse.quote(s)
def safe(base, rel):
    """resolve rel inside base or return None"""
    real = os.path.realpath(os.path.join(base, (rel or "").lstrip("/")))
    return real if real == base or real.startswith(base + "/") else None
def clean_name(n): return re.sub(r"[^\w .()+,&'-]", "_", os.path.basename(n or "")).strip(" .")[:150]
def parse_multipart(handler, limit=2 << 30):
    """returns (fields dict, files list[(filename, bytes)]) from a multipart POST"""
    n = int(handler.headers.get("Content-Length") or 0)
    if n > limit: raise ValueError("upload too large (max %d MB per batch)" % (limit >> 20))
    body = handler.rfile.read(n)
    if len(body) < n: raise ValueError("upload was interrupted (%d of %d MB received); nothing was saved" % (len(body) >> 20, n >> 20))
    raw = b"Content-Type: " + handler.headers["Content-Type"].encode() + b"\r\n\r\n" + body
    msg = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(raw)
    fields, files = {}, []
    for part in msg.iter_parts():
        name = part.get_param("name", header="content-disposition"); fn = part.get_filename()
        data = part.get_payload(decode=True) or b""
        if fn: files.append((fn, data))
        elif name: fields[name] = data.decode("utf-8", "replace")
    return fields, files
IMPORTS = {}
def start_import(src_rel, dest, exts):
    """copy matching files from a read-only USB mount folder into dest (personal space) in a thread"""
    src = safe(MEDIA, src_rel)
    if not src or not os.path.isdir(src): return "Source folder not found under the USB Tools mounts."
    jid = time.strftime("%H%M%S")
    IMPORTS[jid] = st = {"src": src_rel, "dest": dest, "done": 0, "total": 0, "state": "running"}
    def run():
        files = [os.path.join(r, f) for r, _, fs in os.walk(src) for f in fs if f.lower().endswith(exts)]
        st["total"] = len(files)
        for f in files:
            t = os.path.join(dest, os.path.relpath(f, src)); os.makedirs(os.path.dirname(t), exist_ok=True)
            if not (os.path.exists(t) and os.path.getsize(t) == os.path.getsize(f)): shutil.copy2(f, t)
            st["done"] += 1
        st["state"] = "done"; open(P + "/.thumbs/.kick", "w").close()
    threading.Thread(target=run, daemon=True).start()
    return f"Import started: {esc(src_rel)} → {esc(os.path.relpath(dest, P))}. Progress is shown below and updates by itself."
def import_status():
    return '<div id="imports">' + "".join(f'<div class="job"><div class="row"><b>Import {esc(s["src"])}</b><span class="mut">{s["done"]}/{s["total"]} · {s["state"]}</span></div>'
                   f'<div class="bar"><i style="width:{s["done"]*100/max(1,s["total"]):.0f}%"></i></div></div>' for s in IMPORTS.values()) + "</div>"
def usb_folders():
    out = []
    if os.path.isdir(MEDIA):
        for m in sorted(os.listdir(MEDIA)):
            out.append(m)
            try: out += [f"{m}/{d}" for d in sorted(os.listdir(f"{MEDIA}/{m}")) if os.path.isdir(f"{MEDIA}/{m}/{d}")][:200]
            except OSError: pass
    return out
def import_form(action, albums, label):
    fol = usb_folders()
    if not fol: return '<p class="mut">No USB stick or SD card is mounted. Mount one read-only in <a href="/admin/usb">USB Tools</a> first.</p>'
    o = "".join(f'<option value="{esc(f)}">{esc(f)}</option>' for f in fol)
    a = "".join(f'<option value="{esc(x)}">{esc(x)}</option>' for x in albums)
    return (f'<form class="stack" method="post" action="{action}">{{CSRF}}<label>From USB/SD folder<select name="src">{o}</select></label>'
            f'<label>Into {label}<input type="text" name="dest" list="dl-{action[-6:]}" placeholder="new or existing name" required><datalist id="dl-{action[-6:]}">{a}</datalist></label>'
            f'<button class="pri">Import (copies; stick stays read-only)</button></form>')

def clean_rel(rel): return "/".join(clean_name(x) for x in (rel or "").split("/") if clean_name(x))
def chunk_upload(base, exts, dest_rel, name, off, total, data, kick=None):
    """resumable per-file chunked upload. Chunks go to <base>/.uploads/<key>.part; renamed into place when complete."""
    dest_rel = clean_rel(dest_rel) or "Uploads"; dest = safe(base, dest_rel)
    if not dest: return 400, {"err": "bad folder name"}
    nm = clean_name(name)
    if not nm or not nm.lower().endswith(exts): return 415, {"err": "not a supported file type"}
    if total <= 0 or total > (8 << 30) or off < 0 or off + len(data) > total: return 400, {"err": "bad offset/size"}
    final = os.path.join(dest, nm)
    if off == 0 and os.path.isfile(final) and os.path.getsize(final) == total: return 200, {"ok": True, "done": True, "skipped": True, "name": nm, "dest": dest_rel}
    tmpd = os.path.join(base, ".uploads"); os.makedirs(tmpd, exist_ok=True)
    for old in os.listdir(tmpd):
        try:
            if time.time() - os.path.getmtime(os.path.join(tmpd, old)) > 86400: os.remove(os.path.join(tmpd, old))
        except OSError: pass
    part = os.path.join(tmpd, hashlib.sha1(f"{dest_rel}\0{nm}\0{total}".encode()).hexdigest() + ".part")
    have = os.path.getsize(part) if os.path.exists(part) else 0
    if off == 0: have = 0
    if off != have: return 409, {"have": have}
    with open(part, "r+b" if off else "wb") as fh: fh.seek(off); fh.truncate(); fh.write(data)
    if off + len(data) < total: return 200, {"ok": True, "have": off + len(data)}
    os.makedirs(dest, exist_ok=True)
    b, e = os.path.splitext(final); i = 2
    while os.path.exists(final): final = f"{b} ({i}){e}"; i += 1
    os.replace(part, final)
    if kick: open(kick, "w").close()
    return 200, {"ok": True, "done": True, "name": os.path.basename(final), "dest": dest_rel}
def rename_dir(base, thumbs, rel, new):
    new = (new or "").strip()
    if not new or "/" in new or "\\" in new or ".." in new or new.startswith(".") or clean_name(new) != new:
        return False, "Invalid name: no slashes, no '..', must not start with a dot; letters, digits, spaces and . ( ) + , & ' - _ only."
    src = safe(base, rel)
    if not src or src == base or not os.path.isdir(src): return False, "Folder not found."
    par = os.path.dirname(src); dst = os.path.join(par, new)
    if dst == src: return False, "That is already its name."
    if any(x.lower() == new.lower() and os.path.join(par, x) != src for x in os.listdir(par)): return False, f"Something called '{esc(new)}' already exists there."
    os.rename(src, dst); nrel = os.path.relpath(dst, base)
    if thumbs:
        ts = os.path.join(thumbs, os.path.relpath(src, base)); td = os.path.join(thumbs, nrel)
        if os.path.isdir(ts):
            if os.path.exists(td): shutil.rmtree(td)
            os.makedirs(os.path.dirname(td), exist_ok=True); os.rename(ts, td)
    return True, nrel
def imports_json(): return list(IMPORTS.values())
