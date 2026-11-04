#!/usr/bin/env python3
"""mini-videos.service: convert uploads in /srv/personal/videos/.incoming to phone/Wi-Fi friendly MP4, one job at a time.
Target: H.264 High (level 4.0) yuv420p + AAC-LC stereo, MP4 with +faststart (moov first, so playback/seek starts before the
whole file is read), longest side <= 1280 and shortest side <= 720 (720p, aspect kept, never upscaled), <= 30 fps.
Rate control: CRF 24 (quality-targeted, so simple scenes stay small) capped by VBV maxrate 1.8 Mbit/s / bufsize 3.6 Mbit,
so peaks never exceed what a busy 2.4 GHz hotspot can stream to several phones. x264 preset veryfast: the Pi 4 has no
usable hardware encoder (h264_v4l2m2m is fast but low quality / CBR-only), so this is the speed/size sweet spot for software.
Runs under Nice=19 / idle I/O (see unit) so the web server and kiwix stay responsive."""
import os, sys, json, time, subprocess, shutil, secrets, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from videos import VD, INC, EXT, QUEUE, settings
from common import clean_name
WORK = VD + "/.work"; FAILED = VD + "/.failed"; ORIG = VD + "/.originals"
VF = ("scale=w='if(gte(iw,ih),min(1280,iw),min(720,iw))':h='if(gte(iw,ih),min(720,ih),min(1280,ih))'"
      ":force_original_aspect_ratio=decrease:force_divisible_by=2,format=yuv420p")
def ffargs(src, dst):
    return ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i", src,
            "-map", "0:v:0", "-map", "0:a:0?", "-sn", "-dn", "-map_metadata", "-1", "-map_chapters", "-1",
            "-vf", VF, "-fpsmax", "30",
            "-c:v", "libx264", "-preset", "veryfast", "-profile:v", "high", "-level:v", "4.0",
            "-crf", "24", "-maxrate", "1800k", "-bufsize", "3600k", "-g", "120", "-keyint_min", "24",
            "-c:a", "aac", "-b:a", "112k", "-ac", "2", "-ar", "48000",
            "-movflags", "+faststart", "-progress", "pipe:1", "-nostats", dst]
def probe(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json", p], capture_output=True, text=True, timeout=120)
    j = json.loads(r.stdout or "{}"); v = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), {})
    return float(j.get("format", {}).get("duration") or 0), v.get("width"), v.get("height")
def state(**kw):
    try: q = json.load(open(QUEUE))
    except Exception: q = {}
    q.update(kw); q["ts"] = time.time(); t = QUEUE + ".tmp"; json.dump(q, open(t, "w")); os.replace(t, QUEUE)
def pending():
    out = []
    for r, ds, fs in os.walk(INC):
        ds[:] = [d for d in ds if not d.startswith(".")]
        out += [os.path.join(r, f) for f in fs if f.lower().endswith(EXT)]
    return sorted(out, key=os.path.getmtime)
def one(src):
    name = os.path.basename(src); title = os.path.splitext(name)[0]
    vid = time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
    tmp = f"{WORK}/{vid}.mp4"; log = []
    try: d, w0, h0 = probe(src)
    except Exception as e: d, w0, h0 = 0, None, None
    state(current={"name": name, "duration": d, "pos": 0, "speed": 0, "started": time.time()})
    t0 = time.time(); p = subprocess.Popen(ffargs(src, tmp), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    pos = 0; last = 0
    for line in p.stdout:
        k, _, v = line.strip().partition("=")
        if k == "out_time_us" and v.isdigit(): pos = int(v) / 1e6
        if k == "progress" and time.time() - last > 1.5:
            last = time.time(); el = time.time() - t0
            state(current={"name": name, "duration": d, "pos": pos, "speed": pos / el if el > 0 else 0, "started": t0})
    err = p.stderr.read(); rc = p.wait(); el = time.time() - t0
    if rc != 0 or not os.path.isfile(tmp) or os.path.getsize(tmp) < 1024:
        os.makedirs(FAILED, exist_ok=True)
        try: os.remove(tmp)
        except OSError: pass
        shutil.move(src, os.path.join(FAILED, name)); open(os.path.join(FAILED, name + ".log"), "w").write(err[-8000:])
        state(current=None, last={"name": name, "ok": False, "at": time.time()}); return
    od, w, h = probe(tmp)
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", str(min(10, od * 0.1)), "-i", tmp, "-frames:v", "1",
                    "-vf", "scale=480:-2", "-q:v", "4", f"{WORK}/{vid}.jpg"], timeout=120)
    if os.path.isfile(f"{WORK}/{vid}.jpg"): os.replace(f"{WORK}/{vid}.jpg", f"{VD}/{vid}.jpg")
    os.replace(tmp, f"{VD}/{vid}.mp4")
    m = {"title": title, "source": name, "duration": od, "width": w, "height": h, "size": os.path.getsize(f"{VD}/{vid}.mp4"),
         "src_size": os.path.getsize(src), "src_width": w0, "src_height": h0, "encode_secs": round(el, 1), "speed": round(od / el, 3) if el else 0, "added": time.time()}
    json.dump(m, open(f"{VD}/{vid}.json", "w"))
    if settings()["keep_original"]:
        os.makedirs(ORIG, exist_ok=True); shutil.move(src, os.path.join(ORIG, f"{vid}-{clean_name(name)}"))
    else: os.remove(src)
    state(current=None, last={"name": name, "ok": True, "speed": m["speed"], "at": time.time(), "id": vid})
    print(f"done {name} -> {vid}.mp4 {m['size']} B in {el:.0f}s ({m['speed']}x realtime)", flush=True)
def main():
    for d in (VD, INC, WORK): os.makedirs(d, exist_ok=True)
    for f in os.listdir(WORK):  # leftovers from a crash/restart: the source is still in .incoming, so just redo it
        try: os.remove(os.path.join(WORK, f))
        except OSError: pass
    state(current=None)
    while True:
        fs = [f for f in pending() if time.time() - os.path.getmtime(f) > 5]
        if fs:
            try: one(fs[0])
            except Exception as e:
                print("error:", e, flush=True); state(current=None); time.sleep(30)
        else:
            state(); time.sleep(5)
if __name__ == "__main__": main()
