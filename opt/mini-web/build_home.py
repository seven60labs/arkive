#!/usr/bin/env python3
"""Regenerate the kiwix front page (/srv/archive/home.html) from library.xml. Runs before mini-kiwix starts."""
import os, re, sys, html, base64, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from icons import svg, THEME_JS
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = "/srv/archive/home.html"
# Fallback host for links to the :8080 panel (JS rewrites them to the current hostname anyway).
from common import arkive_host
HOST = arkive_host()
CSS = open(os.path.join(HERE, "static/style.css")).read()  # same shared stylesheet, inlined (kiwix serves a single file)
books = []; search_ids = []; search_skipped = []
# search_exclude.txt: ZIM names (no date) whose full-text index has entries that crash kiwix-serve 3.7/3.8 multi-ZIM
# search ("basic_string::substr: __pos (which is 2) > this->size() (which is 0)"). They stay browsable and searchable
# from their own page; they are just left out of the home page's all-collections search.
try: EXCL = {l.split("#")[0].strip() for l in open(os.path.join(HERE, "search_exclude.txt"))} - {""}
except OSError: EXCL = set()
for b in ET.parse("/srv/archive/library.xml").getroot().iter("book"):
    p = b.get("path", ""); books.append((os.path.basename(p)[:-4], b.get("title") or p, b.get("tags", ""), int(b.get("size") or 0)))
    # kiwix-serve 3.7 refuses a search spanning books in different languages (HTTP 400), and a bare /search
    # selects the whole library, which includes a few multilingual ("eng,spa,...") ZIMs. So the search form
    # names every English, full-text-indexed book explicitly.
    if b.get("language") == "eng" and "_ftindex:yes" in (b.get("tags") or "") and b.get("id"):
        if b.get("name") in EXCL: search_skipped.append(b.get("title") or b.get("name"))
        else: search_ids.append(b.get("id"))
def datauri(name, mime):
    return f"data:{mime};base64," + base64.b64encode(open(os.path.join(HERE, "static", name), "rb").read()).decode()
FAV = datauri("favicon-32.png", "image/png"); TOUCH = datauri("apple-touch-icon.png", "image/png"); LOGO = datauri("logo-800.webp", "image/webp"); LOGO_D = datauri("logo-800-dark.webp", "image/webp")
HIDDEN = "".join(f'<input type="hidden" name="books.id" value="{i}">' for i in search_ids)
CATS = [("Encyclopedia", "globe", r"^wikipedia_en_all|^wik(tionary|iquote|isource|iversity|ispecies)"),
        ("Medical", "med", r"medicine|mdwiki|medline|nhs|wikem|cdc|military-medicine|zimgit-medicine|libretexts.org_en_med"),
        ("How-to & repair", "tool", r"ifixit|wikihow|appropedia|diy|mechanics|woodworking|lifehacks|restarters|post-disaster|zimgit|ready\.gov|armypubs|prepper|survivor|trueprepper|lrnselfreliance|energypedia|lowtech|cd3wd"),
        ("Maps & travel", "map", r"^maps_|wikivoyage|openstreetmap|nps-maps"),
        ("Books & learning", "book", r"gutenberg|wikibooks|libretexts|khan|phet|milne|crashcourse|philosophy"),
        ("Videos", "video", r"^ted_|canadian-prepper|urban-prepper|crashcourse"),
        ("Q&A forums", "chat", r"stackexchange|stackoverflow|superuser|serverfault|askubuntu|mathoverflow")]
def esc(s): return html.escape(s, quote=True)
tiles = ""; lists = ""
def hs(n): n *= 1024; return f"{n/1e9:.1f} GB" if n >= 1e9 else f"{n/1e6:.0f} MB"
for name, ic, rx in CATS:
    m = [b for b in books if re.search(rx, b[0])]
    if not m: continue
    m.sort(key=lambda b: -b[3]); top = m[0]
    if len(m) == 1:
        tiles += (f'<a class="tile" href="/content/{esc(top[0])}">{svg(ic)}<span><b>{esc(name)}</b>'
                  f'<small>{esc(top[1])}</small></span></a>')
        continue
    cid = "cat-" + re.sub(r"[^a-z]+", "-", name.lower()).strip("-")
    tiles += (f'<a class="tile cat" href="#{cid}" data-cat="{cid}">{svg(ic)}<span><b>{esc(name)}</b>'
              f'<small>{esc(top[1])} + {len(m)-1} more</small></span></a>')
    items = "".join(f'<li><a href="/content/{esc(b[0])}">{esc(b[1])}</a> <small>{hs(b[3])}</small></li>' for b in m)
    lists += f'<details class="catlist card" id="{cid}"><summary><b>{esc(name)}</b> <small>{len(m)} collections</small></summary><ul>{items}</ul></details>'
# Featured Internet Archive tile: the five IA ZIMs match no CATS rule; reuse the catlist mechanism.
# Book count = PDFs counted in the ZIMs with python-libzim on 2026-10-30 (589+520+587+545+644).
IA_BOOKS = 2885
ia = sorted([b for b in books if re.search(r"_en_internet-archive-part", b[0])], key=lambda b: b[0])
if ia:
    cid = "cat-internet-archive"
    items = "".join(f'<li><a href="/content/{esc(b[0])}">{esc(b[1])}</a> <small>{hs(b[3])}</small></li>' for b in ia)
    lists += f'<details class="catlist card" id="{cid}"><summary><b>Internet Archive</b> <small>{len(ia)} parts · {IA_BOOKS:,} books</small></summary><ul>{items}</ul></details>'
    tiles = (f'<a class="tile cat" href="#{cid}" data-cat="{cid}">{svg("lib")}<span><b>Internet Archive</b>'
             f'<small>{esc(f"{IA_BOOKS:,} public-domain books in {len(ia)} parts")}</small></span></a>') + tiles
for b in books:
    if re.search(r"_en_survivorlibrary", b[0]):
        tiles = (f'<a class="tile" href="/content/{esc(b[0])}">{svg("book")}<span><b>Survivor Library</b>'
                 f'<small>{esc("11,802 old-tech books, by category")}</small></span></a>') + tiles
        break
tiles += f'<a class="tile" href="/nojs">{svg("lib")}<span><b>Whole library</b><small>All {len(books)} collections</small></span></a>'
tiles += f'<a class="tile port" data-port="8080" data-path="terrain" href="http://{HOST}:8080/terrain">{svg("map")}<span><b>Terrain</b><small>Offline 3D relief map + USGS elevation downloads</small></span></a>'
if os.path.isfile("/srv/archive/manuals/official/manifest.json"):
    tiles += f'<a class="tile port" data-port="8080" data-path="official/" href="http://{HOST}:8080/official/">{svg("book")}<span><b>Official Manuals</b><small>US Army, FEMA, USDA, NOAA field manuals by subject</small></span></a>'
tiles += f'<a class="tile port" data-port="8080" href="http://{HOST}:8080/">{svg("pdf")}<span><b>Manuals & PDFs</b><small>Offline manuals, maps and documents</small></span></a>'
page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ARKive</title><link rel="icon" type="image/png" sizes="32x32" href="{FAV}"><link rel="apple-touch-icon" href="{TOUCH}">
<meta name="theme-color" content="#0F4C4C"><meta name="apple-mobile-web-app-title" content="ARKive"><style>{CSS}</style>{THEME_JS}</head><body><div class="wrap">
<div class="top"><span class="sp"></span><button class="iconbtn" onclick="tt()" title="Light/dark">{svg("sun")}</button></div>
<div class="hero"><img class="poster only-l" src="{LOGO}" alt="ARKive: a digital ark for an offline future" width="800" height="192"><img class="poster only-d" src="{LOGO_D}" alt="ARKive: a digital ark for an offline future" width="800" height="192"><a class="sa-cta sa-stopcta port" data-port="8080" data-path="stay-alive" href="http://{HOST}:8080/stay-alive" aria-label="Stop to Stay Alive"><svg class="stop-sign" viewBox="0 0 48 48" width="60" height="60" aria-hidden="true"><polygon class="so" points="14.1,1.5 33.9,1.5 46.5,14.1 46.5,33.9 33.9,46.5 14.1,46.5 1.5,33.9 1.5,14.1"/><polygon class="si" points="15.1,4 32.9,4 44,15.1 44,32.9 32.9,44 15.1,44 4,32.9 4,15.1"/><text x="24" y="28.6" text-anchor="middle">STOP</text></svg><span class="sa-ct">Stop to Stay Alive<small>Stop · Think · Observe · Plan</small></span><span aria-hidden="true">&rsaquo;</span></a><a class="sa-cta mz-cta port" data-port="8080" data-path="maslow" href="http://{HOST}:8080/maslow"><span>Maslow index<small>The whole archive by need, from survival to meaning</small></span><span aria-hidden="true">&rsaquo;</span></a>
<h1 style="font-size:1.25em;margin-top:14px">Offline library</h1><p><span class="dot">●</span> {len(books)} collections · works without internet</p>
<form class="search" id="sf" action="/search" method="get"><input name="pattern" placeholder="Search everything…" aria-label="Search" autofocus required>{HIDDEN}<button class="pri">{svg("search")}<span>Search</span></button></form>
<p class="searching" id="sw" hidden>Searching {len(search_ids)} English collections<span class="dots"></span> the first search after a restart can take a minute while indexes load.</p>{f'<p class="mut" style="font-size:.85em">{len(search_skipped)} collections ({html.escape(", ".join(sorted(search_skipped)))}) are left out of this search because of a kiwix search bug; open one and use its own search box.</p>' if search_skipped else ''}</div>
<h2>Browse</h2><div class="grid">{tiles}</div>
<div class="cats">{lists}</div>
<div class="foot"><a class="port" data-port="8080" data-path="admin/" href="http://{HOST}:8080/admin/">Admin</a></div>
<script>document.getElementById('sf').addEventListener('submit',function(){{document.getElementById('sw').hidden=false}});
try{{var m={{name:"ARKive",short_name:"ARKive",start_url:location.origin+"/",display:"standalone",background_color:"#FFFFFF",theme_color:"#0F4C4C",icons:[{{src:location.protocol+"//"+location.hostname+":8080/static/icon-192.png",sizes:"192x192",type:"image/png"}},{{src:location.protocol+"//"+location.hostname+":8080/static/icon-512.png",sizes:"512x512",type:"image/png"}}]}};var l=document.createElement("link");l.rel="manifest";l.href="data:application/manifest+json,"+encodeURIComponent(JSON.stringify(m));document.head.appendChild(l)}}catch(e){{}}</script>
<script>document.querySelectorAll('a.port').forEach(function(a){{a.href=location.protocol+'//'+location.hostname+':'+a.dataset.port+'/'+(a.dataset.path||'')}})</script>
<script>function oc(id){{var d=document.getElementById(id);if(!d)return;document.querySelectorAll('details.catlist').forEach(function(x){{if(x!==d)x.open=false}});d.open=true;d.scrollIntoView({{behavior:'smooth',block:'start'}})}}
document.querySelectorAll('a.tile.cat').forEach(function(a){{a.addEventListener('click',function(e){{e.preventDefault();oc(a.dataset.cat);history.replaceState(null,'','#'+a.dataset.cat)}})}});if(location.hash)oc(location.hash.slice(1));</script>
<style>.cats{{margin-top:14px}}details.catlist{{margin:10px 0;padding:10px 14px}}details.catlist summary{{cursor:pointer}}details.catlist ul{{margin:8px 0 2px;padding-left:20px;columns:2 280px}}details.catlist li{{margin:4px 0;break-inside:avoid}}details.catlist small{{opacity:.7}}</style>
</div></body></html>'''
tmp = OUT + ".tmp"; open(tmp, "w").write(page); os.replace(tmp, OUT)
print(f"home.html: {len(books)} books, {len(search_ids)} searchable, {len(page)} bytes")
