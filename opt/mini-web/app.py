#!/usr/bin/env python3
"""mini-web (:8080): public read-only file browser + password-protected admin panel at /admin. stdlib only."""
import os, sys, json, time, html, hmac, hashlib, secrets, mimetypes, subprocess, urllib.parse, glob, threading, shutil
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from icons import svg, THEME_JS
import icons
icons.P.setdefault("wifi", '<path d="M2 8.5a15 15 0 0 1 20 0M5 12a10 10 0 0 1 14 0M8.5 15.5a5 5 0 0 1 7 0"/><circle cx="12" cy="19" r="1"/>')
icons.P.setdefault("gear", '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1"/>')
import usbui, gallery, music, common, manage
HOST = common.arkive_host()  # ARKIVE_HOST (env or /etc/arkive/arkive.env)
ROOT = "/srv/archive/manuals"; ALLOWED = ("/srv/archive/manuals", "/srv/archive/files")
A = "/srv/archive"; GEN = f"{A}/generated"; CONF = "/etc/mini-web/admin.json"; HERE = os.path.dirname(os.path.abspath(__file__))
DRY = os.environ.get("MINI_POWER_DRY_RUN") == "1"
CSS_V = str(int(os.path.getmtime(os.path.join(HERE, "static/style.css"))))
SESS = {}; FAILS = {}; LOCK = threading.Lock(); TTL = 8 * 3600
mimetypes.add_type("application/pdf", ".pdf")

def esc(s): return html.escape(str(s), quote=True)
def human(n):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB": return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024
BRAND_HEAD = ('<link rel="icon" href="/favicon.ico" sizes="48x48"><link rel="icon" type="image/png" sizes="32x32" href="/static/favicon-32.png">'
              '<link rel="apple-touch-icon" href="/static/apple-touch-icon.png"><link rel="manifest" href="/static/manifest.webmanifest">'
              '<meta name="theme-color" content="#0F4C4C"><meta name="apple-mobile-web-app-title" content="ARKive">')
def page(title, body, admin=False, head=""):
    nav = (f'<a class="btn" href="/admin/">{svg("act")}Status</a><a class="btn" href="/admin/usb">{svg("tool")}USB</a><a class="btn" href="/admin/photos">{svg("img")}Photos</a><a class="btn" href="/admin/music">{svg("video")}Music</a><a class="btn" href="/admin/settings">{svg("gear")}Settings</a>' if admin else "")
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)} · ARKive</title><link rel="stylesheet" href="/static/style.css?v={CSS_V}">{BRAND_HEAD}{head}{THEME_JS}</head><body><div class="wrap">'
            f'<div class="top"><a class="brand" href="{"/admin/" if admin else "/"}"><img class="gear" src="/static/gear-96.webp" alt="" width="34" height="34"><img class="wm only-l" src="/static/wordmark-360.webp" alt="ARKive" width="99" height="34"><img class="wm only-d" src="/static/wordmark-360-dark.webp" alt="ARKive" width="99" height="34">{'<span class="adm">Admin</span>' if admin else ""}</a><span class="sp"></span>{nav}'
            f'<button class="iconbtn" onclick="tt()" title="Light/dark">{svg("sun")}</button></div>{body}'
            f'<div class="foot"><a id="home" href="/">Archive home</a></div>'
            "<script>document.getElementById('home').href=location.protocol+'//'+location.hostname+'/'</script></div></body></html>")
ICON = {".pdf": ("pdf", "t-pdf"), ".jpg": ("img", "t-img"), ".jpeg": ("img", "t-img"), ".png": ("img", "t-img"), ".gif": ("img", "t-img"), ".svg": ("img", "t-img"),
        ".htm": ("htm", "t-htm"), ".html": ("htm", "t-htm"), ".zip": ("zip", "t-zip"), ".7z": ("zip", "t-zip"), ".gz": ("zip", "t-zip"),
        ".txt": ("file", "t-doc"), ".epub": ("book", "t-doc"), ".json": ("file", "t-zip")}

# ---------- auth ----------
def conf():
    try: return json.load(open(CONF))
    except Exception: return {}
def cgen():
    try: return os.stat(CONF).st_mtime_ns
    except OSError: return 0
def radio(*a):
    r = subprocess.run(["sudo", "-n", "/usr/local/sbin/mini-radio", *a], capture_output=True, text=True, timeout=90)
    return r.returncode, (r.stdout + r.stderr).strip()
def radio_status():
    c, o = radio("status")
    try: return json.loads(o)
    except Exception: return {"err": o}
def check_pw(user, pw):
    c = conf()
    if not c or user != c.get("user", "admin"): return False
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(c["salt"]), c["iter"]).hex()
    return hmac.compare_digest(h, c["hash"])

class H(BaseHTTPRequestHandler):
    server_version = "mini-web"; protocol_version = "HTTP/1.1"; timeout = 120
    def log_message(self, *a): pass
    def ip(self): return self.client_address[0]
    def out(self, code, body, ctype="text/html; charset=utf-8", headers=()):
        if isinstance(body, str): body = body.encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff"); self.send_header("Referrer-Policy", "same-origin")
        for k, v in headers: self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD": self.wfile.write(body)
    def redirect(self, loc, headers=()): self.out(303, "", headers=[("Location", loc), *headers])
    def session(self):
        ck = self.headers.get("Cookie", "")
        for part in ck.split(";"):
            k, _, v = part.strip().partition("=")
            if k == "mini_admin":
                with LOCK:
                    s = SESS.get(v)
                    if s and s["exp"] > time.time() and s.get("gen") == cgen(): s["exp"] = time.time() + TTL; return v, s
                    SESS.pop(v, None)
        return None, None
    def form(self):
        n = min(int(self.headers.get("Content-Length") or 0), 2 << 20)
        return {k: v[0] for k, v in urllib.parse.parse_qs(self.rfile.read(n).decode("utf-8", "replace")).items()}
    def admin_page(self, title, body, s, head=""):
        tok = f'<input type="hidden" name="csrf" value="{s["csrf"]}">'
        self.out(200, page(title, body.replace("{CSRF}", tok), admin=True, head=head or "").replace("{CSRF}", tok), headers=[("Cache-Control", "no-store")])

    # ---------- routing ----------
    def do_HEAD(self): self.do_GET()
    def do_GET(self):
        u = urllib.parse.urlsplit(self.path); path = urllib.parse.unquote(u.path)
        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            f = os.path.join(HERE, "static", "vendor", os.path.basename(rel)) if rel.startswith("vendor/") else os.path.join(HERE, "static", os.path.basename(rel))
            if os.path.isfile(f):
                ct = {".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".geojson": "application/geo+json", ".txt": "text/plain; charset=utf-8", ".webp": "image/webp", ".png": "image/png", ".ico": "image/x-icon", ".webmanifest": "application/manifest+json"}.get(os.path.splitext(f)[1], "application/octet-stream")
                return self.out(200, open(f, "rb").read(), ct, [("Cache-Control", "max-age=3600")])
            return self.out(404, "not found", "text/plain")
        if path in ("/favicon.ico", "/apple-touch-icon.png"): return self.out(200, open(os.path.join(HERE, "static", path[1:]), "rb").read(), "image/x-icon" if path.endswith(".ico") else "image/png", [("Cache-Control", "max-age=86400")])
        if path in ("/terrain", "/terrain/"):  # public offline terrain viewer (MapLibre + PMTiles, self-hosted)
            return self.out(200, page("Terrain map", open(os.path.join(HERE, "static", "terrain_body.html")).read(), head='<link rel="stylesheet" href="/static/vendor/maplibre-gl.css">'))
        if path == "/admin": return self.redirect("/admin/")
        if path.startswith("/admin/"):
            sid, s = self.session()
            if path == "/admin/login": return self.login_form()
            if not s: return self.redirect("/admin/login")
            if path == "/admin/": return self.status(s)
            if path == "/admin/usb":
                body, head = usbui.tools_page(); return self.admin_page("USB Tools", body, s, head)
            if path in ("/admin/usb/browse", "/admin/usb/file"):
                q = urllib.parse.parse_qs(u.query); root = q.get("root", [""])[0]; rp = q.get("path", [""])[0]
                real, title = usbui.browse(root, rp)
                if not real or not os.path.exists(real): return self.admin_page("Not found", '<div class="card">Not found.</div>', s)
                if os.path.isdir(real): return self.admin_page(title, usbui.listing(root, rp, real, title), s)
                return self.sendfile(real)
            qs = urllib.parse.parse_qs(u.query); g = lambda k: qs.get(k, [""])[0]
            if path == "/admin/photos": return self.admin_page("Photos", gallery.page(g("a")), s)
            if path in ("/admin/photos/thumb", "/admin/photos/view", "/admin/photos/orig"):
                src = common.safe(gallery.PH, g("p"))
                if not src or not os.path.isfile(src): return self.out(404, "not found", "text/plain")
                if path == "/admin/photos/orig": return self.sendfile(src, attach=True)
                t = os.path.join(gallery.TH, os.path.relpath(src, gallery.PH)) + (".t.jpg" if path.endswith("thumb") else ".v.jpg")
                if os.path.isfile(t) and os.path.getsize(t): return self.sendfile(t)
                if path.endswith("view") and not src.lower().endswith((".heic", ".heif")): return self.sendfile(src)
                return self.out(200, f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="96" height="96" fill="none" stroke="#888" stroke-width="1.5">{icons.P["img"]}</svg>', "image/svg+xml")
            if path == "/admin/music": return self.admin_page("Music", music.page(g("v") or "artists", g("ar"), g("al"), g("f")), s)
            if path == "/admin/music/file":
                src = common.safe(music.MU, g("p"))
                return self.sendfile(src) if src and os.path.isfile(src) else self.out(404, "not found", "text/plain")
            if path == "/admin/music/pi": return self.out(200, json.dumps(music.pi_status()), "application/json", [("Cache-Control", "no-store")])
            if path == "/admin/bt": return self.admin_page("Bluetooth", music.bt_page(), s)
            if path == "/admin/import/status": return self.out(200, json.dumps(common.imports_json()), "application/json", [("Cache-Control", "no-store")])
            if path == "/admin/settings": return self.settings(s)
            if path == "/admin/trash": return self.admin_page("Trash", manage.trash_page(), s)
            if path == "/admin/media/zip":
                kind = g("kind"); ps = qs.get("p", [])
                if kind not in manage.KINDS or not ps: return self.out(400, "bad request", "text/plain")
                try: [manage.check(kind, p) for p in ps]
                except ValueError as e: return self.out(400, str(e), "text/plain")
                self.send_response(200); self.send_header("Content-Type", "application/zip"); self.send_header("Connection", "close")
                self.send_header("Content-Disposition", f'attachment; filename="arkive-{kind}-{time.strftime("%Y%m%d-%H%M")}.zip"'); self.end_headers()
                self.close_connection = True
                class W:
                    def __init__(s2, w): s2.w = w; s2.n = 0
                    def write(s2, b): s2.w.write(b); s2.n += len(b); return len(b)
                    def tell(s2): return s2.n
                    def flush(s2): pass
                try: manage.zip_stream(kind, ps, W(self.wfile))
                except Exception: pass
                return
            if path == "/admin/radios": return self.redirect("/admin/settings")
            if path == "/admin/radios/status": return self.out(200, json.dumps(radio_status()), "application/json", [("Cache-Control", "no-store")])
            if path == "/admin/power": return self.power_confirm(s, urllib.parse.parse_qs(u.query).get("action", [""])[0])
            return self.out(404, page("Not found", "<p>Not found.</p>"))
        if path in ("/stay-alive", "/stay-alive/"): return self.generated("stayalive.html", "Stay Alive")
        if path == "/official/": return self.generated("official.html", "Official Manuals")
        return self.browse(path)
    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == "/admin/login": return self.login()
        sid, s = self.session()
        if not s: return self.out(403, page("Forbidden", '<div class="card err">Please <a href="/admin/login">log in</a>.</div>'))
        if path == "/admin/upload": return self.chunk(s)
        files = []
        if (self.headers.get("Content-Type") or "").startswith("multipart/form-data"):
            try: f, files = common.parse_multipart(self)
            except Exception as e: return self.out(400, page("Upload failed", f'<div class="card err">{esc(e)}</div>'))
        else: f = self.form()
        if not hmac.compare_digest(f.get("csrf", ""), s["csrf"]): return self.out(403, page("Forbidden", '<div class="card err">Form expired. Go back, reload and try again.</div>'))
        if path == "/admin/logout":
            with LOCK: SESS.pop(sid, None)
            return self.redirect("/admin/login", [("Set-Cookie", "mini_admin=; Path=/admin; Max-Age=0; HttpOnly; SameSite=Strict")])
        if path == "/admin/power": return self.power_do(s, f)
        if path == "/admin/settings": return self.settings_do(sid, s, f)
        if path == "/admin/media":
            try: r = {"ok": True, "msg": manage.op(f, music.mpv_drop if f.get("kind") == "music" else None)}
            except (ValueError, OSError, json.JSONDecodeError) as e: r = {"ok": False, "msg": str(e)}
            return self.out(200 if r["ok"] else 400, json.dumps(r), "application/json", [("Cache-Control", "no-store")])
        if path == "/admin/trash":
            try: msg = manage.op(f); cls = "card"
            except (ValueError, OSError) as e: msg = esc(e); cls = "card err"
            return self.admin_page("Trash", f'<div class="{cls}">{msg}</div>' + manage.trash_page(), s)
        if path == "/admin/radios": return self.radios_do(s, f)
        if path == "/admin/photos/rename":
            ok, r = common.rename_dir(gallery.PH, gallery.TH, f.get("a", ""), f.get("new", ""))
            return self.admin_page("Photos", f'<div class="card{"" if ok else " err"}">{"Renamed to <b>" + esc(r) + "</b>." if ok else r}</div>' + gallery.page(r if ok else f.get("a", "")), s)
        if path == "/admin/music/rename":
            ok, r = common.rename_dir(music.MU, None, f.get("f", ""), f.get("new", ""))
            return self.admin_page("Music", f'<div class="card{"" if ok else " err"}">{"Renamed to <b>" + esc(r) + "</b>." if ok else r}</div>' + music.page("folders", folder=r if ok else f.get("f", "")), s)
        qs = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        if path == "/admin/photos/upload":
            r = gallery.upload(f, files, qs.get("a", [""])[0]); msg, alb = (r if isinstance(r, tuple) else (r, ""))
            return self.admin_page("Photos", f'<div class="card">{msg}</div>' + gallery.page(alb), s)
        if path == "/admin/photos/import":
            dest = common.safe(gallery.PH, "/".join(common.clean_name(x) for x in f.get("dest", "").split("/") if common.clean_name(x)) or "Imported")
            return self.admin_page("Photos", f'<div class="card">{common.start_import(f.get("src", ""), dest, gallery.EXT)}</div>' + gallery.page(), s)
        if path == "/admin/music/upload": return self.admin_page("Music", f'<div class="card">{music.upload(f, files)}</div>' + music.page(), s)
        if path == "/admin/music/import":
            dest = common.safe(music.MU, "/".join(common.clean_name(x) for x in f.get("dest", "").split("/") if common.clean_name(x)) or "Imported")
            return self.admin_page("Music", f'<div class="card">{common.start_import(f.get("src", ""), dest, music.EXT)}</div>' + music.page(), s)
        if path == "/admin/music/pi":
            try: r = music.pi_cmd(f)
            except Exception as e: r = {"ok": False, "err": str(e)}
            return self.out(200, json.dumps(r), "application/json", [("Cache-Control", "no-store")])
        if path == "/admin/bt": return self.admin_page("Bluetooth", music.bt_page(music.bt_action(f)), s)
        if path == "/admin/usb/act":
            msg = usbui.do_action(f); body, head = usbui.tools_page(msg); return self.admin_page("USB Tools", body, s, head)
        return self.out(404, "not found", "text/plain")

    # ---------- chunked uploads ----------
    def chunk(self, s):
        J = lambda c, d: self.out(c, json.dumps(d), "application/json", [("Cache-Control", "no-store")])
        if not hmac.compare_digest(self.headers.get("X-CSRF", ""), s["csrf"]): return J(403, {"err": "session expired: reload the page"})
        n = int(self.headers.get("Content-Length") or 0)
        if n > (16 << 20): return J(413, {"err": "chunk too large"})
        data = self.rfile.read(n)
        if len(data) < n: self.close_connection = True; return J(400, {"err": "interrupted"})
        qs = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query); g = lambda k: qs.get(k, [""])[0]
        kind = g("kind")
        if kind == "photos": base, ext, kick = gallery.PH, gallery.EXT, gallery.TH + "/.kick"
        elif kind == "music": base, ext, kick = music.MU, music.EXT, None
        else: return J(400, {"err": "bad kind"})
        try: code, d = common.chunk_upload(base, ext, g("dest"), g("name"), int(g("off") or 0), int(g("total") or 0), data, kick)
        except Exception as e: code, d = 500, {"err": str(e)[:200]}
        return J(code, d)

    # ---------- settings: password ----------
    def settings(self, s, msg="", ok=False):
        m = f'<div class="card{"" if ok else " err"}">{msg}</div>' if msg else ""
        body = (f'<h1 style="margin:4px 0">{svg("gear")} Settings</h1>{m}'
                f'<h2>{svg("wifi")} Wi-Fi &amp; Bluetooth</h2>' + self.radios_html()
                + f'<h2>{svg("lock")} Password</h2><div class="card" style="max-width:520px">'
                '<form class="stack" method="post" action="/admin/settings">{CSRF}'
                '<input type="hidden" name="user" value="admin" autocomplete="username">'
                '<label>Current password<input type="password" name="cur" autocomplete="current-password" required></label>'
                '<label>New password<input type="password" name="new" autocomplete="new-password" required></label>'
                '<label>New password again<input type="password" name="rep" autocomplete="new-password" required></label>'
                '<button class="pri">Change password</button></form><p class="mut">All other logged-in browsers are signed out. If you forget it, run <code>sudo mini-admin-passwd</code> on the Pi.</p></div>'
                f'<h2>{svg("power")} Power</h2><div class="card"><p class="mut" style="margin-top:0">Shut down before unplugging so the SSD is never cut mid-write.</p>'
                f'<a class="btn bad" href="/admin/power?action=poweroff">{svg("power")}Shut down…</a> <a class="btn" href="/admin/power?action=reboot">{svg("reboot")}Reboot…</a>'
                f'{"<p class=mut><i>Dry-run mode is on: power actions only report what they would do.</i></p>" if DRY else ""}</div>'
                f'<h2>Log out</h2><div class="card"><form method="post" action="/admin/logout">{{CSRF}}<button>{svg("lock")}Log out</button></form></div>')
        self.admin_page("Settings", body, s)
    def settings_do(self, sid, s, f):
        ip = self.ip(); now = time.time()
        with LOCK: fl = [t for t in FAILS.get(ip, []) if now - t < 900]; FAILS[ip] = fl
        if len(fl) >= 5: return self.settings(s, "Too many wrong passwords. Try again in 15 minutes.")
        if not check_pw(conf().get("user", "admin"), f.get("cur", "")):
            with LOCK: FAILS.setdefault(ip, []).append(now)
            time.sleep(1.0); return self.settings(s, "Current password is wrong. Nothing changed.")
        new = f.get("new", "")
        if not new: return self.settings(s, "New password must not be empty.")
        if new != f.get("rep", ""): return self.settings(s, "The two new passwords do not match.")
        r = subprocess.run(["sudo", "-n", "/usr/local/sbin/mini-admin-passwd", "--stdin"], input=new, capture_output=True, text=True, timeout=60)
        if r.returncode: return self.settings(s, "Could not save: " + esc((r.stdout + r.stderr).strip()[-200:]))
        with LOCK:
            n = 0
            for k in list(SESS):
                if k != sid: SESS.pop(k); n += 1
            s["gen"] = cgen()
        self.settings(s, f"Password changed. {n} other session(s) signed out; this one stays logged in.", ok=True)

    # ---------- radios ----------
    def radios_html(self):
        st = radio_status()
        if "err" in st: return f'<div class="card err">Radio helper failed: {esc(st["err"])}</div>'
        e, w, b = st["eth"], st["wifi"], st["bt"]
        on = lambda x: f'<span style="color:var(--acc)">{x}</span>'
        btn = lambda a, t, cls="", dis="": (f'<form method="post" action="/admin/radios" style="display:inline">{{CSRF}}<button name="a" value="{a}" class="{cls}"'
                                             f'{" disabled title=" + chr(34) + esc(dis) + chr(34) if dis else ""}>{t}</button></form>')
        wifi_up = w["ap"] and not w["blocked"]
        why = "" if e["ok"] else "Ethernet is not connected (no link or no IP), so Wi-Fi must stay on or the Pi would be unreachable."
        cl = "".join(f'<li><code>{esc(c["mac"])}</code> {esc(c["ip"])} {esc(c["name"])}</li>' for c in w["clients"]) or '<li class="mut">none</li>'
        return (                f'<div class="card"><div class="row" style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px"><b>Wi-Fi access point</b>'
                f'<span>{btn("wifi_off", "Turn Wi-Fi off", "bad", why) if wifi_up else btn("wifi_on", "Turn Wi-Fi on", "pri")}</span></div>'
                f'<div style="margin:10px 0;padding:10px 14px;border:1px solid var(--line);border-radius:10px;background:var(--card2)"><span class="mut">Current network name (SSID)</span><br>'
                f'<code style="font-size:1.9em;font-weight:700;letter-spacing:.06em;user-select:all">{esc(w["ssid"])}</code></div>'
                f'<p style="margin:6px 0">State: {on("broadcasting") if wifi_up else "<span class=err>off</span>"} · open network, no password · '
                f'Pi address <b>{esc(w["ip"])}</b> · country {esc(w["reg"])}</p>'
                + (f'<p class="warn" style="margin:6px 0">{esc(why)}</p>' if wifi_up and why else "")
                + f'<p class="mut" style="margin:6px 0">On a phone: join <b>{esc(w["ssid"])}</b>, then open <b>http://{HOST}</b> (archive) or <b>http://{HOST}:8080/admin/</b> (this panel). '
                'Wi-Fi always comes back on at boot, and turns itself back on within about 20 seconds if ethernet drops while it is off. Hotspot clients can reach this Pi only, never your home network.</p>'
                f'<b>Connected clients ({len(w["clients"])})</b><ul style="margin:4px 0 10px;padding-left:20px">{cl}</ul>'
                '<form method="post" action="/admin/radios">{CSRF}<button name="a" value="ssid_random">Reroll now</button> '
                '<span class="mut">A new random name is generated at every boot. Rerolling disconnects current Wi-Fi clients.</span></form></div>'
                f'<div class="card"><div class="row" style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px"><b>Bluetooth</b>'
                f'<span>{btn("bt_off", "Turn Bluetooth off", "bad") if not b["blocked"] else btn("bt_on", "Turn Bluetooth on", "pri")}</span></div>'
                f'<p style="margin:6px 0">State: {on("on") if not b["blocked"] and b["powered"] else ("on (adapter not powered yet)" if not b["blocked"] else "<span class=err>off</span>")} · '
                'Off at every boot. Turning it on reconnects the last speaker. <a href="/admin/bt">Speakers…</a></p></div>'
                '')
    def radios_do(self, s, f):
        a = f.get("a", "")
        if a == "wifi_off":
            st = radio_status()
            if not st.get("eth", {}).get("ok"): return self.settings(s, "Refused: ethernet is not connected, so Wi-Fi stays on.")
            c, o = radio("wifi", "off")
        elif a == "wifi_on": c, o = radio("wifi", "on")
        elif a == "bt_on": c, o = radio("bt", "on")
        elif a == "bt_off": c, o = radio("bt", "off")
        elif a == "ssid_random": c, o = radio("ssid", "--random")
        else: return self.settings(s, "Unknown action.")
        self.settings(s, esc(o), ok=(c == 0))

    # ---------- login ----------
    def login_form(self, msg=""):
        body = (f'<div class="card login-card" style="max-width:420px;margin:30px auto"><img class="gear" src="/static/gear-96.webp" alt="" width="84" height="84"><h1 style="margin-top:0">Admin sign-in</h1>'
                f'<p class="mut">Admin panel · password required</p>{f"<p class=err>{esc(msg)}</p>" if msg else ""}<form class="stack" method="post" action="/admin/login">'
                '<label>Password<input type="password" name="pw" autocomplete="current-password" autofocus required></label>'
                '<button class="pri">Log in</button></form></div>')
        self.out(200 if not msg else 401, page("Admin login", body), headers=[("Cache-Control", "no-store")])
    def login(self):
        ip = self.ip(); now = time.time()
        with LOCK:
            fl = [t for t in FAILS.get(ip, []) if now - t < 900]; FAILS[ip] = fl
        if len(fl) >= 5: return self.login_form("Too many failed attempts. Try again in 15 minutes.")
        f = self.form()
        if check_pw(conf().get("user", "admin"), f.get("pw", "")):  # password-only login; the stored config still carries the fixed user name
            sid = secrets.token_urlsafe(32)
            with LOCK: SESS[sid] = {"exp": now + TTL, "csrf": secrets.token_urlsafe(24), "gen": cgen()}; FAILS.pop(ip, None)
            return self.redirect("/admin/", [("Set-Cookie", f"mini_admin={sid}; Path=/admin; HttpOnly; SameSite=Strict; Max-Age={TTL}")])
        with LOCK: FAILS.setdefault(ip, []).append(now)
        time.sleep(1.0)
        self.login_form("Wrong password.")

    # ---------- status ----------
    def queue(self, label, plans, donefile, name_col, size_col):
        done = set(open(donefile).read().split()) if os.path.exists(donefile) else set()
        tot = got = 0; cur = None; left = 0
        for p in plans:
            if not os.path.exists(p): continue
            for l in open(p):
                c = l.rstrip("\n").split("\t")
                if len(c) <= max(name_col, size_col): continue
                name = os.path.basename(c[name_col]); size = int(c[size_col]); tot += size
                if name in done: got += size; continue
                part = f"{A}/incoming/{name}.part"
                if os.path.exists(part):
                    ps = os.path.getsize(part); got += ps
                    if time.time() - os.path.getmtime(part) < 120: cur = (name, ps, size)
                left += 1
        return label, tot, got, cur, left
    def jobs(self):
        out = []
        for label, pat in [("Copy from build host", r"cat >> .?/srv/archive/incoming"), ("Web download queue", r"fillweb\.sh"), ("NPS map crawl", r"python3 npscrawl"),
                           ("rsync", r"^rsync "), ("git clone/fetch", r"^git .*(clone|fetch)"), ("Disk image / flash", r"^(dd |bmaptool|rpi-imager)"), ("Checksum verify", r"^sha256sum ")]:
            r = subprocess.run(["pgrep", "-af", pat], capture_output=True, text=True)
            out += [(label, l.split(" ", 1)[1][:140]) for l in r.stdout.splitlines() if "pgrep" not in l]
        return out
    def status(self, s):
        du = shutil.disk_usage("/srv"); pct = du.used * 100 / du.total
        qs = [self.queue("Build host → device copy (pass 1 + 2)", [f"{A}/plan.tsv", f"{A}/plan2.tsv"], f"{A}/fill.done", 1, 2),
              self.queue("Internet downloads", [f"{A}/plan-web.tsv"], f"{A}/fill-web.done", 1, 2)]
        rows = ""
        for label, tot, got, cur, left in qs:
            if left == 0 and not cur: continue
            p = got * 100 / tot if tot else 100
            curtxt = (f'<div class="mut">Now: <code>{esc(cur[0])}</code> {human(cur[1])} / {human(cur[2])}</div><div class="bar"><i style="width:{cur[1]*100/cur[2]:.1f}%"></i></div>' if cur else "")
            rows += (f'<div class="job"><div class="row"><b>{esc(label)}</b><span class="mut">{human(got)} / {human(tot)} · {left} files left</span></div>'
                     f'<div class="bar"><i style="width:{p:.1f}%"></i></div>{curtxt}</div>')
        try:
            idx = json.load(open(f"{A}/nps-crawl/index.json")); have = len(glob.glob("/srv/archive/files/maps/nps/*/*.pdf"))
            if have < len(idx): rows += (f'<div class="job"><div class="row"><b>NPS park maps</b><span class="mut">{have} / {len(idx)} PDFs</span></div>'
                     f'<div class="bar"><i style="width:{have*100/max(1,len(idx)):.1f}%"></i></div></div>')
        except Exception: pass
        js = self.jobs()
        jl = "".join(f"<li><b>{esc(a)}</b> <code>{esc(b)}</code></li>" for a, b in js) or "<li class=mut>None</li>"
        def tail(f, n=6):
            try: return esc("".join(open(f).readlines()[-n:]))
            except Exception: return ""
        e = radio_status().get("eth", {})
        eth = (f'<div class="card"><b>Ethernet (eth0):</b> ' + ('<span style="color:var(--acc)">connected</span>' if e.get("ok") else "<span class=err>not connected</span>")
               + (f' · {esc(e["ip"])}' if e.get("ip") else "") + ("" if e.get("carrier") else " · no cable link") + '</div>')
        body = (eth + f'<div class="card"><div class="row" style="display:flex;justify-content:space-between"><b>Storage</b><span class="mut">{human(du.used)} used · {human(du.free)} free of {human(du.total)}</span></div>'
                f'<div class="bar"><i style="width:{pct:.1f}%"></i></div></div>'
                f'<h2>Jobs</h2><div class="card">{rows or "<span class=mut>No active jobs</span>"}</div>'
                f'<h2>Running processes</h2><div class="card"><ul style="margin:0;padding-left:18px">{jl}</ul></div>'
                f'<h2>Recent log lines</h2><div class="card"><pre style="white-space:pre-wrap;margin:0;font-size:.8em">{tail(A+"/fill.log")}{tail(A+"/fill-web.log")}{tail(A+"/nps-crawl.log",3)}</pre></div>')
        self.admin_page("Status", body, s)
    def power_confirm(self, s, act):
        if act not in ("poweroff", "reboot"): return self.redirect("/admin/")
        word = "SHUTDOWN" if act == "poweroff" else "REBOOT"; js = self.jobs()
        warn = ("<div class='warn'><b>These jobs are running and will be interrupted:</b><ul>" + "".join(f"<li><b>{esc(a)}</b> <code>{esc(b)}</code></li>" for a, b in js)
                + "</ul>Copies and downloads resume afterwards; an interrupted flash or clone does not.</div>") if js else "<p class=mut>No copy, download, clone or flash jobs are running.</p>"
        body = (f'<div class="card"><h1 style="margin-top:0">Confirm {word.lower()}</h1>{warn}<form class="stack" method="post" action="/admin/power">{{CSRF}}'
                f'<input type="hidden" name="action" value="{act}"><label>Type <b>{word}</b> to confirm<input type="text" name="confirm" autocomplete="off" required></label>'
                f'<button class="{"bad" if act=="poweroff" else "pri"}">{svg("power" if act=="poweroff" else "reboot")}{word.title()} now</button></form></div>')
        self.admin_page(word.title(), body, s)
    def power_do(self, s, f):
        act = f.get("action", ""); need = {"poweroff": "SHUTDOWN", "reboot": "REBOOT"}.get(act)
        if not need or f.get("confirm", "").strip() != need: return self.admin_page("Not confirmed", '<div class="card">Not confirmed. Nothing was done.</div>', s)
        verb = ["dry-run", act] if DRY else [act]
        r = subprocess.run(["sudo", "-n", "/usr/local/sbin/mini-power", *verb], capture_output=True, text=True, timeout=30)
        msg = (r.stdout + r.stderr).strip() or ("Shutting down. Wait for the green light to stop before unplugging." if act == "poweroff" else "Rebooting; back in about a minute.")
        self.admin_page("Power", f'<div class="card">{esc(msg)}</div>', s)

    # ---------- generated pages (build_stayalive.py) ----------
    def generated(self, name, title):
        try: body = open(os.path.join(GEN, name)).read()
        except OSError: body = f'<div class="card"><h1 style="margin-top:0">{esc(title)}</h1><p class="mut">This page is being built; reload in a minute.</p></div>'
        self.out(200, page(title, body))

    # ---------- public file browser ----------
    def browse(self, path):
        real = os.path.realpath(os.path.join(ROOT, path.lstrip("/")))
        if not any(real == a or real.startswith(a + "/") for a in ALLOWED) or not os.path.exists(real):
            return self.out(404, page("Not found", '<div class="card">Not found.</div>'))
        if os.path.isdir(real):
            if not path.endswith("/"): return self.redirect(urllib.parse.quote(path + "/"))
            return self.listing(path, real)
        return self.sendfile(real)
    def sendfile(self, real, attach=False):
        if not os.access(real, os.R_OK): return self.out(403, page("Forbidden", '<div class="card">Permission denied.</div>'))
        ctype = mimetypes.guess_type(real)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/json", "application/javascript"): ctype += "; charset=utf-8"
        size = os.path.getsize(real); start, end = 0, size - 1; code = 200
        rng = self.headers.get("Range", "")
        if rng.startswith("bytes="):
            a, _, b = rng[6:].split(",")[0].partition("-")
            try:
                if a: start = int(a); end = int(b) if b else end
                else: start = size - int(b)
                end = min(end, size - 1); code = 206
            except ValueError: pass
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes"); self.send_header("Cache-Control", "max-age=3600")
        if code == 206: self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        if attach: self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{urllib.parse.quote(os.path.basename(real))}")
        elif ctype == "application/pdf": self.send_header("Content-Disposition", f"inline; filename*=UTF-8''{urllib.parse.quote(os.path.basename(real))}")
        self.end_headers()
        if self.command == "HEAD": return
        with open(real, "rb") as fh:
            fh.seek(start); left = end - start + 1
            while left > 0:
                b = fh.read(min(1 << 20, left))
                if not b: break
                self.wfile.write(b); left -= len(b)
    def listing(self, path, real):
        parts = [p for p in path.strip("/").split("/") if p]
        cr = f'<nav class="crumbs"><a href="/">{svg("home")}</a>'
        for i, p in enumerate(parts): cr += f'{svg("chev")}<a href="/{urllib.parse.quote("/".join(parts[:i+1]))}/">{esc(p)}</a>'
        cr += "</nav>"
        items = []
        for n in os.listdir(real):
            if n.startswith(".") or n.endswith(".part"): continue
            fp = os.path.join(real, n)
            try: isd = os.path.isdir(fp); st = os.stat(fp)
            except OSError: continue
            items.append((not isd, n.lower(), n, isd, st.st_size))
        items.sort()
        li = ""
        for _, _, n, isd, sz in items:
            ic, cl = ("folder", "t-dir") if isd else ICON.get(os.path.splitext(n)[1].lower(), ("file", "t-doc"))
            li += f'<li><a href="{urllib.parse.quote(n)}{"/" if isd else ""}">{svg(ic, cl)}<span class="nm">{esc(n)}</span><span class="meta">{"" if isd else human(sz)}</span></a></li>'
        title = parts[-1] if parts else "Files & manuals"
        intro = "" if parts else '<p class="mut">Manuals, PDFs and maps. PDFs open right in the browser.</p>'
        self.out(200, page(title, f'<h1 style="margin:4px 0 6px">{esc(title)}</h1>{intro}{cr}<ul class="list">{li or "<li><a>Empty folder</a></li>"}</ul>'))

class Captive(BaseHTTPRequestHandler):
    """:8081 - hotspot clients' unknown-host HTTP lands here (nft redirect) and is sent to the archive front page"""
    timeout = 20
    def log_message(self, *a): pass
    def do_GET(self):
        self.send_response(302); self.send_header("Location", f"http://{HOST}/"); self.send_header("Content-Length", "0"); self.send_header("Cache-Control", "no-store"); self.end_headers()
    do_HEAD = do_POST = do_GET
def stayalive_loop():
    """(Re)build the Stay Alive + Official Manuals pages: as soon as kiwix answers after start-up, then every 6 h."""
    time.sleep(15)
    while True:
        try: rc = subprocess.run([sys.executable, os.path.join(HERE, "build_stayalive.py")], capture_output=True, timeout=1800).returncode
        except Exception: rc = 1
        time.sleep(60 if rc == 75 else 6 * 3600)
if __name__ == "__main__":
    threading.Thread(target=stayalive_loop, daemon=True).start()
    c = ThreadingHTTPServer(("", 8081), Captive); c.daemon_threads = True; threading.Thread(target=c.serve_forever, daemon=True).start()
    s = ThreadingHTTPServer(("", int(os.environ.get("PORT", "8080"))), H); s.daemon_threads = True; s.serve_forever()
