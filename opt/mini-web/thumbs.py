#!/usr/bin/env python3
"""mini-thumbs: low-priority thumbnail/view builder for /srv/personal/photos (runs nice 19, idle I/O)."""
import os, sys, time, json, subprocess, tempfile
from PIL import Image, ImageOps, ExifTags
PH = "/srv/personal/photos"; TH = "/srv/personal/.thumbs"
EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif", ".tif", ".tiff", ".bmp")
def exif_date(im):
    try:
        ex = im.getexif(); d = ex.get_ifd(0x8769).get(36867) or ex.get(306)
        return d.replace(":", "-", 2) if d else ""
    except Exception: return ""
def orient(im):
    try: return ImageOps.exif_transpose(im)
    except Exception:   # some cameras write EXIF Pillow cannot re-serialise; rotate by hand
        try: o = im.getexif().get(274)
        except Exception: o = None
        t = {2: Image.Transpose.FLIP_LEFT_RIGHT, 3: Image.Transpose.ROTATE_180, 4: Image.Transpose.FLIP_TOP_BOTTOM, 5: Image.Transpose.TRANSPOSE,
             6: Image.Transpose.ROTATE_270, 7: Image.Transpose.TRANSVERSE, 8: Image.Transpose.ROTATE_90}.get(o)
        return im.transpose(t) if t else im
def build(src, rel):
    out = os.path.join(TH, rel); os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = None
    if src.lower().endswith((".heic", ".heif")):
        tmp = tempfile.mktemp(suffix=".jpg", dir=TH); r = subprocess.run(["heif-convert", "-q", "90", src, tmp], capture_output=True)
        if r.returncode: raise RuntimeError("heif-convert failed")
        src = tmp
    try:
        with Image.open(src) as im:
            date = exif_date(im); im = orient(im).convert("RGB")
            v = im.copy(); v.thumbnail((1600, 1600)); v.save(out + ".v.jpg", quality=82, optimize=True)
            im.thumbnail((360, 360)); im.save(out + ".t.jpg", quality=78)
            json.dump({"date": date, "w": v.width, "h": v.height}, open(out + ".json", "w"))
    finally:
        if tmp and os.path.exists(tmp): os.remove(tmp)
# ---- lossless jpegoptim pass (added 2026-10-29). Covers browser uploads and USB/SD imports: both land in PH.
# Lossless only, metadata kept, mtime kept (--preserve) so thumbnails stay valid. jpegoptim writes atomically.
JO_STATE = TH + "/.jpegoptim.json"; JO_LOG = TH + "/.jpegoptim.log"; JO_MIN_AGE = 120  # skip files still being copied/uploaded
def jo_load():
    try: return json.load(open(JO_STATE))
    except Exception: return {}
def jo_save(st):
    tmp = JO_STATE + ".tmp"; json.dump(st, open(tmp, "w")); os.replace(tmp, JO_STATE)
def jpegoptim(src, rel, st):
    try: s0 = os.stat(src)
    except OSError: return False
    if time.time() - s0.st_mtime < JO_MIN_AGE or os.path.getctime(src) > time.time() - JO_MIN_AGE: return False
    key = [s0.st_size, s0.st_mtime_ns]
    if st.get(rel) == key: return False
    r = subprocess.run(["ionice", "-c3", "jpegoptim", "--preserve", "--all-progressive", "-q", src], capture_output=True, text=True, timeout=600)
    try: s1 = os.stat(src)
    except OSError: return False
    st[rel] = [s1.st_size, s1.st_mtime_ns]
    with open(JO_LOG, "a") as lg:
        lg.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{'ok' if r.returncode == 0 else 'err' + str(r.returncode)}\t{s0.st_size}\t{s1.st_size}\t{rel}\t{(r.stderr or '').strip()[:200]}\n")
    return True
def scan():
    n = 0
    st = jo_load(); jo_n = 0
    for r, ds, fs in os.walk(PH):
        if "/." in r + "/": continue
        for f in fs:
            if f.lower().endswith((".jpg", ".jpeg")):
                try:
                    if jpegoptim(os.path.join(r, f), os.path.relpath(os.path.join(r, f), PH), st): jo_n += 1
                except Exception as e: print("jpegoptim failed", f, e, flush=True)
                if jo_n and jo_n % 20 == 0: jo_save(st)
    if jo_n: jo_save(st); print("jpegoptim", jo_n, flush=True)
    for r, ds, fs in os.walk(PH):
        if "/." in r + "/": continue
        for f in fs:
            if not f.lower().endswith(EXT): continue
            src = os.path.join(r, f); rel = os.path.relpath(src, PH); t = os.path.join(TH, rel) + ".t.jpg"
            if os.path.exists(t) and os.path.getmtime(t) >= os.path.getmtime(src): continue
            try: build(src, rel); n += 1
            except Exception as e: print("skip", rel, e, flush=True); open(t, "w").close()
    return n
if __name__ == "__main__":
    os.nice(19)
    while True:
        try: k = os.path.getmtime(TH + "/.kick")
        except OSError: k = 0
        n = scan()
        try:
            sys.path.insert(0, "/opt/mini-web"); import manage; manage.purge()
        except Exception as e: print("purge failed", e, flush=True)
        if n: print("built", n, flush=True)
        for _ in range(60):
            time.sleep(2)
            try:
                if os.path.getmtime(TH + "/.kick") != k: break
            except OSError: pass
