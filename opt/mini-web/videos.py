"""Video library: chunked upload -> background transcode (mini-videos.service) -> library grid + HTML5 player.
Layout under VD (on the data disk, next to music/photos):
  .incoming/   uploads land here (chunked, resumable); the transcoder picks them up oldest-first, one at a time
  .work/       transcoder scratch (partial MP4)
  .failed/     sources that ffmpeg could not convert (+ .log)
  .originals/  sources kept when "keep originals" is on
  <id>.mp4 / <id>.jpg / <id>.json   finished library (H.264/AAC, +faststart)
  .queue.json  transcoder state (current job, progress, speed); .settings.json  admin settings"""
import os, json, time, re, shutil
from common import *
from icons import svg
VD = P + "/videos"; INC = VD + "/.incoming"
EXT = (".mp4", ".m4v", ".mov", ".mkv", ".webm", ".avi", ".wmv", ".mpg", ".mpeg", ".ts", ".mts", ".m2ts", ".3gp", ".flv", ".ogv", ".vob")
SET = VD + "/.settings.json"; QUEUE = VD + "/.queue.json"
DEFAULTS = {"keep_original": False, "public": False}
ID_RE = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")
def settings():
    s = dict(DEFAULTS)
    try: s.update({k: bool(v) for k, v in json.load(open(SET)).items() if k in DEFAULTS})
    except Exception: pass
    return s
def save_settings(f):
    s = {"keep_original": f.get("keep_original") == "1", "public": f.get("public") == "1"}
    os.makedirs(VD, exist_ok=True); t = SET + ".tmp"; json.dump(s, open(t, "w")); os.replace(t, SET); return s
def library():
    out = []
    try: names = os.listdir(VD)
    except OSError: return out
    for n in names:
        if not n.endswith(".json") or n.startswith("."): continue
        vid = n[:-5]
        if not ID_RE.match(vid) or not os.path.isfile(f"{VD}/{vid}.mp4"): continue
        try: m = json.load(open(f"{VD}/{n}"))
        except Exception: continue
        m["id"] = vid; out.append(m)
    out.sort(key=lambda m: m.get("title", "").lower()); return out
def meta(vid):
    if not ID_RE.match(vid or "") or not os.path.isfile(f"{VD}/{vid}.mp4"): return None
    try: m = json.load(open(f"{VD}/{vid}.json"))
    except Exception: m = {"title": vid}
    m["id"] = vid; return m
def path(vid, kind):
    if not ID_RE.match(vid or ""): return None
    p = f"{VD}/{vid}.{'mp4' if kind == 'mp4' else 'jpg'}"
    return p if os.path.isfile(p) else None
def queue_state():
    try: q = json.load(open(QUEUE))
    except Exception: q = {}
    pend = []
    for r, ds, fs in os.walk(INC):
        ds[:] = [d for d in ds if not d.startswith(".")]
        for f in fs:
            if f.lower().endswith(EXT): pend.append(os.path.join(r, f))
    pend.sort(key=lambda p: os.path.getmtime(p))
    cur = q.get("current") if q.get("current") and time.time() - q.get("ts", 0) < 120 else None
    names = [os.path.basename(p) for p in pend if not cur or os.path.basename(p) != cur.get("name")]
    fails = sorted(n for n in os.listdir(VD + "/.failed") if not n.endswith(".log")) if os.path.isdir(VD + "/.failed") else []
    upd = INC + "/.uploads"
    uploading = os.path.isdir(upd) and any(time.time() - os.path.getmtime(os.path.join(upd, f)) < 90 for f in os.listdir(upd))
    return {"current": cur, "waiting": names, "failed": fails, "last": q.get("last"), "alive": time.time() - q.get("ts", 0) < 120, "uploading": uploading}
def busy():
    """one video at a time: a reason string while an upload or conversion is in progress, else ''"""
    q = queue_state()
    if q["current"]: return f"“{q['current']['name']}” is being converted."
    if q["waiting"]: return f"“{q['waiting'][0]}” is about to be converted."
    if q["uploading"]: return "Another video is being uploaded."
    return ""
def last_speed():
    sp = [m.get("speed") for m in library() if m.get("speed")]
    return sorted(sp)[len(sp) // 2] if sp else 0
def delete(vid):
    if not ID_RE.match(vid or ""): raise ValueError("bad id")
    n = 0
    for e in ("mp4", "jpg", "json"):
        try: os.remove(f"{VD}/{vid}.{e}"); n += 1
        except FileNotFoundError: pass
    return n
def dur(s):
    s = int(s or 0); return f"{s//3600}:{s%3600//60:02d}:{s%60:02d}" if s >= 3600 else f"{s//60}:{s%60:02d}"
def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB": return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024
def grid(vids, base):
    t = ""
    for m in vids:
        t += (f'<a class="vt" href="{base}/watch?id={m["id"]}"><span class="vth"><img loading="lazy" src="{base}/thumb?id={m["id"]}" alt="">'
              f'<span class="vdur">{dur(m.get("duration"))}</span></span><b>{esc(m.get("title", m["id"]))}</b>'
              f'<small class="mut">{m.get("width", "?")}×{m.get("height", "?")} · {human(m.get("size", 0))}</small></a>')
    return f'<div class="vgrid">{t}</div>' if t else '<p class="mut">No videos yet.</p>'
def page(msg=""):
    st = settings(); vids = library()
    b = busy(); sp = last_speed()
    up = (f'<h2>{svg("video")} Add a video clip</h2><div class="card">'
          '<div class="warn" style="margin-bottom:10px"><b>Designed for short clips, not as a media server for full movies.</b> '
          'After upload the Pi converts the video to a phone-friendly MP4. That keeps the device busy for a while: the Pi 4 has no fast video encoder, '
          'so long videos take much longer (roughly as long as the video itself, or more) and use noticeably more power when running on battery. '
          'Only one video can be uploaded or converted at a time.</div>'
          f'<form class="stack" data-up="videos" id="vform" style="max-width:520px" data-speed="{sp or 1.0:.2f}"{" data-busy=1" if b else ""}>'
          f'<input type="file" name="f" accept="video/*,.mkv,.avi,.mov,.m4v,.mts,.m2ts,.wmv,.mpg,.ts,.vob" required{" disabled" if b else ""}>'
          f'<input type="hidden" name="folder" value="in"><div id="vinfo" class="mut"></div><button class="pri"{" disabled" if b else ""}>Upload</button></form>'
          f'<p id="vbusy" class="err"{"" if b else " hidden"}>Upload is disabled until the current video is finished: {esc(b)}</p>'
          '<p class="mut">Output: H.264/AAC MP4, at most 720p, about 1–2 Mbit/s (roughly 0.5–0.9 GB per hour of video). You can close this page once the upload finishes.</p></div>')
    q = ('<h2>Current job</h2><div class="card" id="vq"><span class="mut">Loading…</span></div>')
    sets = (f'<details class="card"><summary><b>Video settings</b></summary><form class="stack" method="post" action="/admin/videos/settings" style="max-width:640px">{{CSRF}}'
            f'<label><input type="checkbox" name="keep_original" value="1"{" checked" if st["keep_original"] else ""}> Keep the original upload after conversion (in <code>videos/.originals</code>; uses much more space)</label>'
            f'<label><input type="checkbox" name="public" value="1"{" checked" if st["public"] else ""}> Also let hotspot users watch (read-only library at <code>/videos</code> on this port, no upload/delete)</label>'
            '<button class="pri">Save</button></form></details>')
    m = f'<div class="card">{msg}</div>' if msg else ""
    return (f'<h1 style="margin:4px 0">{svg("video")} Videos</h1>{m}{grid(vids, "/admin/videos")}{q}{up}{sets}'
            '<script src="/static/upload.js"></script><script src="/static/videos.js"></script>')
def watch(m, base, admin):
    d = (f'<form method="post" action="/admin/videos/delete" onsubmit="return confirm(\'Delete this video for good?\')">{{CSRF}}'
         f'<input type="hidden" name="id" value="{m["id"]}"><button class="bad">Delete</button></form>') if admin else ""
    return (f'<p><a href="{base}">‹ All videos</a></p><h1 style="margin:4px 0 10px">{esc(m.get("title", m["id"]))}</h1>'
            f'<video class="vplay" controls playsinline preload="metadata" poster="{base}/thumb?id={m["id"]}" src="{base}/file?id={m["id"]}"></video>'
            f'<div class="row" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:8px"><span class="mut">{dur(m.get("duration"))} · {m.get("width", "?")}×{m.get("height", "?")} · '
            f'{human(m.get("size", 0))} · from <code>{esc(m.get("source", ""))}</code></span><span class="sp"></span>'
            f'<a class="btn" href="{base}/file?id={m["id"]}" download="{esc(clean_name(m.get("title", m["id"])))}.mp4">Download</a>{d}</div>')
