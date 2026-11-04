"""Admin "Update" tab: version display + check/apply/rollback via the root helper /usr/local/sbin/mini-update (sudoers: those 3 verbs only)."""
import os, json, subprocess, glob
from common import esc
from icons import svg
HERE = os.path.dirname(os.path.abspath(__file__)); STATE = "/var/lib/arkive-update"
def version():
    for f in (os.path.join(HERE, "VERSION"), os.path.join(HERE, "..", "..", "VERSION")):
        try: return open(f).read().strip()
        except OSError: pass
    return "0.0.0"
def rj(n):
    try: return json.load(open(f"{STATE}/{n}"))
    except Exception: return None
def status():
    try: lg = open(f"{STATE}/update.log").read()[-12000:]
    except OSError: lg = ""
    running = subprocess.run(["systemctl", "is-active", "--quiet", "arkive-update"]).returncode == 0
    return {"version": version(), "check": rj("check.json"), "apply": rj("apply.json"), "log": lg, "running": running,
            "rollbacks": len(glob.glob(f"{STATE}/rollback/*.tgz")) if os.access(f"{STATE}/rollback", os.R_OK) else None}
def action(a):
    if a not in ("check", "apply", "rollback"): return {"ok": False, "msg": "unknown action"}
    try: r = subprocess.run(["sudo", "-n", "/usr/local/sbin/mini-update", a], capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired: return {"ok": False, "msg": "timed out", **status()}
    return {"ok": r.returncode in (0, 2), "msg": (r.stdout + r.stderr).strip()[-400:], **status()}
def page():
    return (f'<h1 style="margin:4px 0">{svg("reboot")} Software update</h1>'
            f'<div class="card"><div class="row" style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;align-items:center">'
            f'<span>Installed version <b style="font-size:1.3em">v{esc(version())}</b></span>'
            '<span><button id="uchk" class="pri">Check for updates</button> <button id="uapp" disabled>Update</button></span></div>'
            '<div id="ures" style="margin-top:10px"></div></div>'
            '<h2>Progress / log</h2><div class="card"><div id="ust" class="mut">Idle.</div><pre class="ulog" id="ulog"></pre></div>'
            '<details class="card"><summary><b>Roll back</b></summary><p class="mut">Each update first saves the previous version on the Pi (newest 3 kept). '
            'If an update fails it is restored automatically; use this to go back by hand.</p><button id="urb" class="bad">Restore previous version</button></details>'
            '<p class="mut">Needs internet (ethernet with a router). Updates come from the public ARKive GitHub releases; the library, photos, music and videos are not touched. '
            'The panel restarts during an update; this page reconnects by itself.</p>'
            '{CSRF}<script src="/static/update.js"></script>')
