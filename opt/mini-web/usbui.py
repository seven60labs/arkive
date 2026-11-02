"""USB Tools pages for mini-web admin. Imported by app.py; every action goes through sudo mini-usb."""
import json, os, subprocess, urllib.parse, html, mimetypes, time
from icons import svg
HELPER = "/usr/local/sbin/mini-usb"
ROOTS = {"media": ("USB drives", "/media/usb"), "repo": ("Repository drive (read-only)", "/")}
def esc(s): return html.escape(str(s), quote=True)
def gb(n): n = int(n or 0); return f"{n/1e12:.2f} TB" if n >= 1e12 else f"{n/1e9:.1f} GB" if n >= 1e9 else f"{n/1e6:.0f} MB"
def helper(*a, timeout=120):
    r = subprocess.run(["sudo", "-n", HELPER, *a], capture_output=True, text=True, timeout=timeout)
    try: return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception: return {"ok": False, "error": (r.stderr or r.stdout or "helper failed").strip()[:300]}
def flat(ch):
    for c in ch or []:
        yield c; yield from flat(c.get("children"))
def opt(vals, sel=None): return "".join(f'<option value="{esc(v)}"{" selected" if v == sel else ""}>{esc(t)}</option>' for v, t in vals)
def tools_page(msg=""):
    L = helper("list"); J = helper("jobs").get("jobs", [])
    if not L.get("ok"): return f'<div class="card err">{esc(L.get("error"))}</div>', False
    disks = L["disks"]; running = any(j["state"] == "running" for j in J)
    targets = [d for d in disks if not d["protected"] and d["removable"]]
    out = f'<h1 style="margin:4px 0">{svg("tool")} USB Tools</h1>'
    if msg: out += f'<div class="card">{msg}</div>'
    if not targets: out += '<div class="warn">No removable USB drive or microSD card is attached. Plug one in and reload this page.</div>'
    # jobs
    if J:
        rows = ""
        for j in sorted(J, key=lambda j: -j["start"])[:8]:
            col = {"running": "", "done": "", "failed": " err"}[j["state"]]
            cancel = (f'<form method="post" action="/admin/usb/act" style="display:inline">{{CSRF}}<input type=hidden name=action value=cancel><input type=hidden name=job value="{esc(j["id"])}"><button>Stop</button></form>'
                      if j["state"] == "running" and j["kind"] == "badblocks" else "")
            rows += (f'<div class="job"><div class="row"><b>{esc(j["kind"].title())} → {esc(j["target"])}</b><span class="mut{col}">{esc(j["state"])} · {time.strftime("%H:%M", time.localtime(j["start"]))}</span></div>'
                     f'<div class="bar"><i style="width:{float(j.get("pct") or 0):.1f}%"></i></div><div class="mut{col}">{esc(j.get("msg",""))} {cancel}</div></div>')
        out += f'<h2>Jobs{" (page refreshes every 3 s)" if running else ""}</h2><div class="card">{rows}</div>'
    # drives
    out += "<h2>Drives</h2>"
    for d in disks:
        if d.get("empty"):
            out += f'<div class="card"><b>{svg("tool")} microSD slot (/dev/mmcblk0)</b><div class="mut">Empty: no card inserted. Insert a card and reload.</div></div>'; continue
        prot = d["protected"]
        badge = (f'<span class="err">{svg("lock")} PROTECTED: {esc("; ".join(prot))}</span>' if prot else '<span style="color:var(--acc)">Removable: tools enabled</span>')
        parts = ""
        for c in flat(d.get("children")):
            mps = [m for m in (c.get("mountpoints") or []) if m]
            act = ""
            if not prot:
                if mps and mps[0].startswith("/media/usb/"):
                    act = (f'<a class="btn" href="/admin/usb/browse?root=media&path={urllib.parse.quote(c["name"])}">{svg("folder")}Browse</a> '
                           f'<form method="post" action="/admin/usb/act" style="display:inline">{{CSRF}}<input type=hidden name=action value=umount><input type=hidden name=dev value="{esc(c["name"])}"><button>Unmount</button></form>')
                elif not mps and c.get("fstype"):
                    act = f'<form method="post" action="/admin/usb/act" style="display:inline">{{CSRF}}<input type=hidden name=action value=mount><input type=hidden name=dev value="{esc(c["name"])}"><button>{svg("folder")}Mount read-only</button></form>'
                if c.get("fstype"):
                    act += f' <form method="post" action="/admin/usb/act" style="display:inline">{{CSRF}}<input type=hidden name=action value=fsck><input type=hidden name=dev value="{esc(c["name"])}"><button>Check filesystem</button></form>'
            parts += (f'<div class="job"><div class="row"><span><b>{esc(c["name"])}</b> {gb(c["size"])} · {esc(c.get("fstype") or "no filesystem")}'
                      f'{" · " + esc(c["label"]) if c.get("label") else ""}</span><span class="mut">{esc(", ".join(mps) or "not mounted")}</span></div>{act}</div>')
        tools = ""
        if prot:
            tools = f'<a class="btn" href="/admin/usb/browse?root=repo&path=srv/archive">{svg("folder")}Browse read-only</a> '
        tools += f'<form method="post" action="/admin/usb/act" style="display:inline">{{CSRF}}<input type=hidden name=action value=smart><input type=hidden name=dev value="{esc(d["name"])}"><button>SMART health</button></form> '
        if not prot:
            dn = esc(d["name"])
            tools += f'<form method="post" action="/admin/usb/act" style="display:inline">{{CSRF}}<input type=hidden name=action value=badblocks><input type=hidden name=dev value="{dn}"><button>Read-only surface scan</button></form>'
            tools += (f'<details style="margin-top:10px"><summary><b>Format</b></summary><form class="stack" method="post" action="/admin/usb/act">{{CSRF}}<input type=hidden name=action value=format><input type=hidden name=dev value="{dn}">'
                      f'<label>Filesystem <select name=fs>{opt([(f, {"exfat":"exFAT (Windows/Mac/Linux, big files)","fat32":"FAT32 (most compatible, 4 GB file limit)","ext4":"ext4 (Linux)","ntfs":"NTFS (Windows)"}[f]) for f in L["fs"]])}</select></label>'
                      f'<label>Label <input type=text name=label value="USB" maxlength=15></label><label>Type <b>{dn}</b> to erase it<input type=text name=confirm autocomplete=off required></label><button class="bad">Erase and format</button></form></details>')
            imgs = L.get("images") or []
            tools += (f'<details style="margin-top:6px"><summary><b>Flash an installer image</b></summary><form class="stack" method="post" action="/admin/usb/act">{{CSRF}}<input type=hidden name=action value=flash><input type=hidden name=dev value="{dn}">'
                      + (f'<label>Image <select name=image>{opt([(i, i) for i in imgs])}</select></label><label>Type <b>{dn}</b> to overwrite it<input type=text name=confirm autocomplete=off required></label><button class="bad">Write and verify</button>' if imgs else '<p class="mut">No images downloaded yet.</p>')
                      + '</form></details>')
            tools += (f'<details style="margin-top:6px"><summary><b>Clone this archive drive onto it</b></summary><p class="mut">Makes a bootable copy of this Pi: same partition layout (root grows to fill the target), '
                      f'boot and root copied file-by-file with rsync (including all of /srv/archive, minus unfinished downloads), new disk ID with fstab and cmdline.txt fixed. '
                      f'The target must hold the used data ({gb(L.get("used",0)) if L.get("used") else "see size check"}) plus 5%.</p><form class="stack" method="post" action="/admin/usb/act">{{CSRF}}<input type=hidden name=action value=clone><input type=hidden name=dev value="{dn}">'
                      f'<label><input type=checkbox name=personal value=with-personal> Also copy personal photos &amp; music (/srv/personal)</label><label>Type <b>{dn}</b> to overwrite it<input type=text name=confirm autocomplete=off required></label><button class="bad">Clone</button></form></details>')
        out += (f'<div class="card"><div class="row" style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px"><b>{svg("tool")} /dev/{esc(d["name"])} · {"microSD slot" if d.get("sdslot") else esc(d.get("model") or d["type"])} · {gb(d["size"])}</b>'
                f'<span class="mut">serial {esc(d.get("serial") or "n/a")} · {esc(d.get("tran") or d["type"])}</span></div><div>{badge}</div>{parts}<div style="margin-top:10px">{tools}</div></div>')
    head = '<meta http-equiv="refresh" content="3">' if running else ""
    return out, head
def do_action(f):
    a = f.get("action"); dev = f.get("dev", ""); c = f.get("confirm", "").strip()
    args = {"mount": [dev], "umount": [dev], "fsck": [dev], "smart": [dev], "badblocks": [dev], "cancel": [f.get("job", "")],
            "format": [dev, f.get("fs", ""), f.get("label", ""), c], "flash": [f.get("image", ""), dev, c], "clone": [dev, c] + (["with-personal"] if f.get("personal") == "with-personal" else [])}.get(a)
    if args is None: return "<span class=err>Unknown action.</span>"
    r = helper(a, *args, timeout=3700)
    if not r.get("ok"): return f'<span class="err"><b>Refused / failed:</b> {esc(r.get("error"))}</span>'
    if "output" in r:
        title = {"fsck": f"Filesystem check of {dev}: " + ("clean" if r.get("clean") else f"problems reported (exit {r.get('rc')})"),
                 "smart": f"SMART health of {dev}: {r.get('health')}"}[a]
        return f'<b>{esc(title)}</b><pre style="white-space:pre-wrap;font-size:.8em;max-height:420px;overflow:auto">{esc(r["output"])}</pre>'
    if "job" in r: return f"Started {esc(a)} on {esc(dev)} (job {esc(r['job'])})."
    if "mountpoint" in r: return f'Mounted read-only at {esc(r["mountpoint"])}. <a href="/admin/usb/browse?root=media&path={urllib.parse.quote(dev)}">Browse</a>'
    return f"{esc(a.title())} done."
def browse(root, path):
    if root not in ROOTS: return None, "bad root"
    title, base = ROOTS[root]
    real = os.path.realpath(os.path.join(base, path.lstrip("/")))
    if not (real == base or real.startswith(base.rstrip("/") + "/")): return None, "outside root"
    if root == "repo" and (real.startswith("/proc") or real.startswith("/sys") or real.startswith("/dev")): return None, "not browsable"
    return real, title
def listing(root, path, real, title):
    parts = [p for p in path.strip("/").split("/") if p]
    cr = f'<nav class="crumbs"><a href="/admin/usb">{svg("tool")}</a>{svg("chev")}<a href="/admin/usb/browse?root={root}&path=">{esc(title)}</a>'
    for i, p in enumerate(parts): cr += f'{svg("chev")}<a href="/admin/usb/browse?root={root}&path={urllib.parse.quote("/".join(parts[:i+1]))}">{esc(p)}</a>'
    cr += "</nav>"
    try: names = os.listdir(real)
    except PermissionError: return cr + '<div class="card err">Permission denied.</div>'
    items = []
    for n in names:
        fp = os.path.join(real, n)
        try: isd = os.path.isdir(fp) and not os.path.islink(fp); sz = os.path.getsize(fp) if not isd else 0
        except OSError: continue
        items.append((not isd, n.lower(), n, isd, sz))
    li = ""
    for _, _, n, isd, sz in sorted(items)[:2000]:
        q = urllib.parse.quote("/".join(parts + [n]))
        li += (f'<li><a href="/admin/usb/{"browse" if isd else "file"}?root={root}&path={q}">{svg("folder" if isd else "file", "t-dir" if isd else "t-doc")}'
               f'<span class="nm">{esc(n)}</span><span class="meta">{"" if isd else gb(sz)}</span></a></li>')
    return f'<h1 style="margin:4px 0 6px">{esc(parts[-1] if parts else title)}</h1>{cr}<ul class="list">{li or "<li><a>Empty</a></li>"}</ul>'
