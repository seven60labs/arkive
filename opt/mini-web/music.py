"""Music library + in-browser player + Pi-side mpv player + Bluetooth (admin only)."""
import os, json, socket, subprocess, re, time, threading
from common import *
from icons import svg
import manage
MU = P + "/music"; EXT = (".mp3", ".m4a", ".ogg", ".opus", ".flac", ".wav", ".aac")
SOCK = "/run/mini-player/mpv.sock"; LAST = "/var/lib/mini-player/last-speaker"
_IDX = {"sig": None, "tracks": []}
def index():
    sig = []; files = []
    for r, ds, fs in os.walk(MU):
        ds[:] = sorted(d for d in ds if not d.startswith("."))
        for f in sorted(fs):
            if f.lower().endswith(EXT): p = os.path.join(r, f); files.append(p); sig.append((p, os.path.getmtime(p)))
    if sig == _IDX["sig"]: return _IDX["tracks"]
    try: import mutagen
    except ImportError: mutagen = None
    old = {t["path"]: t for t in _IDX["tracks"]}; out = []
    for p in files:
        rel = os.path.relpath(p, MU)
        if rel in old and old[rel]["mt"] == os.path.getmtime(p): out.append(old[rel]); continue
        t = {"path": rel, "mt": os.path.getmtime(p), "title": os.path.splitext(os.path.basename(p))[0], "artist": "Unknown artist", "album": os.path.basename(os.path.dirname(p)) if os.path.dirname(rel) else "Singles", "track": 0, "len": 0}
        try:
            m = mutagen.File(p, easy=True) if mutagen else None
            if m:
                g = lambda k: (m.get(k) or [""])[0]
                t["title"] = g("title") or t["title"]; t["artist"] = g("albumartist") or g("artist") or t["artist"]; t["album"] = g("album") or t["album"]
                t["track"] = int(re.match(r"\d*", g("tracknumber") or "").group() or 0); t["len"] = int(getattr(m.info, "length", 0) or 0)
        except Exception: pass
        out.append(t)
    _IDX.update(sig=sig, tracks=out); return out
def trow(t):
    j = esc(json.dumps({"u": "/admin/music/file?p=" + q(t["path"]), "t": t["title"], "a": t["artist"], "p": t["path"]}))
    ln = f'{t["len"]//60}:{t["len"]%60:02d}' if t["len"] else ""
    return (f'<div class="trk" data-p="{esc(t["path"])}"><span class="nm"><b>{esc(t["title"])}</b> <span class="mut">· {esc(t["artist"])}</span></span><span class="mut">{ln}</span>'
            f'<button data-t="{j}" class="pb">▶</button><button data-t="{j}" class="qb" title="Add to browser queue">+</button><button data-p="{esc(t["path"])}" class="pi" title="Play on Pi speaker">Pi</button><button class="mren" title="Rename">✎</button><button class="mdel" title="Move to Trash">🗑</button></div>')
def page(view="artists", artist="", album="", folder=""):
    ts = index()
    tabs = "".join(f'<a class="btn{" on" if view == v else ""}" href="/admin/music?v={v}">{n}</a>' for v, n in (("artists", "Artists"), ("albums", "Albums"), ("folders", "Folders"), ("all", "All tracks")))
    body = ""
    if view == "artists" and not artist:
        arts = sorted({t["artist"] for t in ts}, key=str.lower)
        body = '<ul class="list">' + "".join(f'<li><a href="/admin/music?v=artists&ar={q(a)}">{svg("chat")}<span class="nm">{esc(a)}</span><span class="meta">{sum(1 for t in ts if t["artist"]==a)} tracks</span></a></li>' for a in arts) + "</ul>"
    elif view in ("artists", "albums") and not album:
        sel = [t for t in ts if not artist or t["artist"] == artist]
        als = sorted({(t["album"], t["artist"]) for t in sel}, key=lambda x: x[0].lower())
        body = (f"<h2>{esc(artist)}</h2>" if artist else "") + '<ul class="list">' + "".join(f'<li><a href="/admin/music?v={view}&ar={q(ar)}&al={q(al)}">{svg("book")}<span class="nm">{esc(al)}</span><span class="meta">{esc(ar)}</span></a></li>' for al, ar in als) + "</ul>"
    elif view in ("artists", "albums"):
        sel = sorted((t for t in ts if t["album"] == album and (not artist or t["artist"] == artist)), key=lambda t: (t["track"], t["title"]))
        body = f'<h2>{esc(album)} · {esc(artist)}</h2><button class="playall pri">Play all in browser</button> <button class="piall">Play all on Pi</button><div class="card" style="padding:0">' + "".join(map(trow, sel)) + "</div>"
    elif view == "folders":
        base = safe(MU, folder) or MU; rel = os.path.relpath(base, MU); rel = "" if rel == "." else rel
        subs = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)) and not d.startswith("."))
        body = (f'<nav class="crumbs"><a href="/admin/music?v=folders">music</a> {esc("/" + rel) if rel else ""}</nav><ul class="list">'
                + "".join(f'<li><a href="/admin/music?v=folders&f={q(os.path.join(rel, d))}">{svg("folder", "t-dir")}<span class="nm">{esc(d)}</span></a></li>' for d in subs) + "</ul>")
        sel = [t for t in ts if os.path.dirname(t["path"]) == rel]
        if sel: body += '<button class="playall pri">Play folder in browser</button> <button class="piall">Play folder on Pi</button><div class="card" style="padding:0">' + "".join(map(trow, sel)) + "</div>"
    else:
        body = '<button class="playall pri">Play all in browser</button> <div class="card" style="padding:0">' + "".join(map(trow, sorted(ts, key=lambda t: (t["artist"].lower(), t["album"], t["track"])))) + "</div>"
    if not ts: body = '<div class="card mut">No music yet. Upload MP3s or import from a USB stick below.</div>'
    folders = sorted({os.path.dirname(t["path"]) for t in ts if os.path.dirname(t["path"])})
    up = (f'<details class="card"><summary><b>Upload music</b></summary><form class="stack" data-up="music" method="post" enctype="multipart/form-data" action="/admin/music/upload">{{CSRF}}'
          f'<input type="file" name="files" multiple accept="audio/*" required><label>Folder (e.g. Artist/Album)<input type="text" name="folder" value="{esc(folder)}" placeholder="Uploads"></label><button class="pri">Upload</button></form></details>'
          f'<details class="card"><summary><b>Import from USB stick / SD card</b></summary>{import_form("/admin/music/import", folders, "folder")}</details>{import_status()}<script src="/static/upload.js"></script>')
    pi = ('<div class="card" id="pi"><div class="row" style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px"><b>' + svg("video") + ' Pi speaker</b>'
          '<a class="btn" href="/admin/bt">Bluetooth speakers</a></div><div id="pinow" class="mut">…</div><div class="bar"><i id="pibar" style="width:0"></i></div>'
          '<div class="row" style="display:flex;gap:6px;flex-wrap:wrap;align-items:center"><button data-c="prev">⏮</button><button data-c="pause">⏯</button><button data-c="next">⏭</button><button data-c="stop">⏹ Clear</button>'
          '<label class="mut">Vol <input type="range" id="pivol" min="0" max="100"></label></div><ol id="piq" class="mut" style="margin:6px 0 0;padding-left:20px;font-size:.9em"></ol></div>')
    player = ('<div class="player"><div class="row"><b id="now" class="nm" style="flex:1">Browser player: nothing playing</b><button id="bprev">⏮</button><button id="bnext">⏭</button>'
              '<button id="bshuf" title="Shuffle">🔀</button><button id="brep" title="Repeat">🔁</button><button id="bclr" title="Clear queue">✕</button></div>'
              '<audio id="au" controls preload="none"></audio><div id="bq" class="mut" style="font-size:.85em"></div></div>')
    up = manage.toolbar("music", folders, folder if view == "folders" and folder and safe(MU, folder) not in (None, MU) else "",
                        manage.count(safe(MU, folder), EXT) if folder and safe(MU, folder) else 0) + up
    if folder:
        up += (f'<details class="card"><summary><b>Rename this folder</b></summary><form class="stack" method="post" action="/admin/music/rename">{{CSRF}}'
               f'<input type="hidden" name="f" value="{esc(folder)}"><label>New name for “{esc(os.path.basename(folder))}”'
               f'<input type="text" name="new" value="{esc(os.path.basename(folder))}" maxlength="150" required></label><button class="pri">Rename</button></form></details>')
    return (f'<h1 style="margin:4px 0">{svg("video")} Music</h1><div class="tabs">{tabs}</div>{body}{pi}{up}{player}'
            '<script src="/static/music.js"></script><script src="/static/manage.js"></script>')
def upload(fields, files):
    folder = "/".join(clean_name(x) for x in (fields.get("folder") or "Uploads").split("/") if clean_name(x)) or "Uploads"
    dest = safe(MU, folder)
    if not dest: return "Bad folder name."
    os.makedirs(dest, exist_ok=True); n = 0
    for fn, data in files:
        name = clean_name(fn)
        if name.lower().endswith(EXT) and data: open(os.path.join(dest, name), "wb").write(data); n += 1
    return f"Uploaded {n} track(s) to {esc(folder)}."
# ---- Pi-side mpv over its JSON IPC socket ----
def mpv(*cmds):
    s = socket.socket(socket.AF_UNIX); s.settimeout(2); s.connect(SOCK); out = []
    for i, c in enumerate(cmds):
        s.sendall((json.dumps({"command": c, "request_id": i}) + "\n").encode())
    buf = b""
    while len(out) < len(cmds):
        try: chunk = s.recv(65536)
        except socket.timeout: break
        if not chunk: break
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1); m = json.loads(line)
            if "request_id" in m: out.append(m)
    s.close(); out.sort(key=lambda m: m["request_id"]); return [m.get("data") for m in out]
def pi_status():
    try:
        pl, pause, vol, pos, dur, title = mpv(["get_property", "playlist"], ["get_property", "pause"], ["get_property", "volume"], ["get_property", "time-pos"], ["get_property", "duration"], ["get_property", "media-title"])
    except Exception as e: return {"ok": False, "err": f"player not running ({e})"}
    return {"ok": True, "queue": [os.path.basename(x.get("filename", "")) for x in (pl or [])], "cur": next((i for i, x in enumerate(pl or []) if x.get("current")), -1),
            "pause": pause, "vol": vol, "pos": pos, "dur": dur, "title": title, "bt": bt_connected()}
def pi_cmd(f):
    c = f.get("c", "")
    if c == "add":
        paths = json.loads(f.get("paths") or "[]"); mode = "append-play"
        if f.get("replace") == "1": mpv(["playlist-clear"]); mpv(["stop"])
        for p in paths[:500]:
            real = safe(MU, p)
            if real and os.path.isfile(real): mpv(["loadfile", real, mode])
    elif c == "pause": mpv(["cycle", "pause"])
    elif c == "next": mpv(["playlist-next", "force"])
    elif c == "prev": mpv(["playlist-prev", "force"])
    elif c == "stop": mpv(["stop"])
    elif c == "rm": mpv(["playlist-remove", int(f.get("i", -1))])
    elif c == "vol": mpv(["set_property", "volume", max(0, min(100, int(float(f.get("v", 70)))))])
    return pi_status()
# ---- Bluetooth via bluetoothctl (minitools is in the bluetooth group; no root needed) ----
MAC = re.compile(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$")
def btctl(*a, timeout=25):
    r = subprocess.run(["bluetoothctl", *a], capture_output=True, text=True, timeout=timeout); return r.stdout + r.stderr
def bt_connected():
    return [l.split(" ", 2)[2] for l in btctl("devices", "Connected").splitlines() if l.startswith("Device ")]
SCAN = {"until": 0}
def bt_page(msg=""):
    devs = []
    for l in btctl("devices").splitlines():
        if not l.startswith("Device "): continue
        _, mac, name = (l.split(" ", 2) + [""])[:3]
        info = btctl("info", mac); g = lambda k: re.search(rf"{k}: (\w+)", info)
        icon = (re.search(r"Icon: (\S+)", info) or [None, ""])[1]
        devs.append((mac, name, (g("Paired") or [0, "no"])[1], (g("Trusted") or [0, "no"])[1], (g("Connected") or [0, "no"])[1], icon))
    devs.sort(key=lambda d: (d[4] != "yes", d[2] != "yes", "audio" not in d[5], d[1] == d[0].replace(":", "-")))
    show = btctl("show"); powered = "Powered: yes" in show
    scanning = time.time() < SCAN["until"]
    rows = ""
    for mac, name, pa, tr, co, icon in devs[:60]:
        btn = lambda a, t, cls="": f'<form method="post" action="/admin/bt" style="display:inline">{{CSRF}}<input type=hidden name=mac value="{mac}"><button name=a value={a} class="{cls}">{t}</button></form>'
        acts = (btn("disconnect", "Disconnect") if co == "yes" else btn("connect", "Connect", "pri")) + (btn("pair", "Pair") if pa != "yes" else "") + (btn("trust", "Trust") if tr != "yes" else "") + btn("remove", "Forget")
        rows += (f'<div class="job"><div class="row"><b>{esc(name)}</b><span class="mut">{mac} · {esc(icon or "device")} · paired {pa} · trusted {tr} · '
                 f'<span style="color:{"var(--acc)" if co=="yes" else "inherit"}">connected {co}</span></span></div>{acts}</div>')
    last = open(LAST).read().strip() if os.path.exists(LAST) else ""
    return (f'{"<meta http-equiv=refresh content=4>" if scanning else ""}<h1 style="margin:4px 0">Bluetooth speakers</h1>'
            + (f'<div class="card">{msg}</div>' if msg else "")
            + f'<div class="card"><b>Adapter:</b> {"powered on" if powered else "<span class=err>off</span> (Bluetooth radio is off: turn it on under <a href=/admin/settings>Settings</a>)"} · {esc((re.search(r"Controller (\S+)", show) or [0, "?"])[1])}'
            f'{" · auto-reconnects " + esc(last) + " at boot" if last else ""}<br><form method="post" action="/admin/bt" style="display:inline">{{CSRF}}<button name=a value=scan class="pri">'
            f'{"Scanning… (page refreshes)" if scanning else "Scan for speakers (20 s)"}</button></form> <a class="btn" href="/admin/music">Back to music</a>'
            '<p class="mut">Put the speaker in pairing mode, scan, then Pair → Trust → Connect. Audio goes to the most recently connected speaker.</p></div>'
            f'<div class="card">{rows or "<p class=mut>No devices known yet. Scan to find speakers.</p>"}</div>')
def bt_action(f):
    a = f.get("a"); mac = f.get("mac", "")
    if a == "scan":
        SCAN["until"] = time.time() + 22
        threading.Thread(target=lambda: btctl("--timeout", "20", "scan", "on", timeout=30), daemon=True).start()
        return "Scanning for 20 seconds…"
    if not MAC.match(mac) or a not in ("pair", "trust", "connect", "disconnect", "remove"): return "Bad request."
    out = btctl(a, mac, timeout=40)
    if a == "connect" and "successful" in out:
        open(LAST, "w").write(mac); btctl("trust", mac)
    ok = re.search(r"(successful|succeeded|removed|trust succeeded|Changing .* succeeded)", out)
    return f'<b>{esc(a.title())} {mac}:</b> {"OK" if ok else "<span class=err>failed</span>"}<pre style="white-space:pre-wrap;font-size:.8em">{esc(out[-800:])}</pre>'

def mpv_drop(real):
    """remove queue entries for a deleted/moved file (or everything under a folder when real ends with /)"""
    try:
        pl = mpv(["get_property", "playlist"])[0] or []
        for i in reversed(range(len(pl))):
            fn = pl[i].get("filename", "")
            if fn == real or (real.endswith("/") and fn.startswith(real)): mpv(["playlist-remove", i])
    except Exception: pass
