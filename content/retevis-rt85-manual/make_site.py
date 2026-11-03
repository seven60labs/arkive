"""Landing page + searchable English text for the RT85 manual ZIM. Usage: make_site.py SITE_DIR ICON_SCRIPT [PDF_DIR with optional Retevis_RT85_User_Manual_EN.txt]"""
import sys, os, subprocess, html
site, icon = sys.argv[1], sys.argv[2]
en = os.path.join(site, "Retevis_RT85_User_Manual_EN.pdf")
tf = os.path.join(sys.argv[3], "Retevis_RT85_User_Manual_EN.txt") if len(sys.argv) > 3 else ""
txt = open(tf).read() if tf and os.path.exists(tf) else subprocess.run(["pdftotext", "-layout", en, "-"], capture_output=True, text=True).stdout if os.path.exists(en) and __import__("shutil").which("pdftotext") else ""
mb = lambda f: f"{os.path.getsize(os.path.join(site, f))/1e6:.1f} MB"
css = "body{font:16px/1.5 system-ui,sans-serif;max-width:48rem;margin:1rem auto;padding:0 1rem}a{color:#0b6e6e}pre{white-space:pre-wrap;font-size:13px}"
links = '<li><a href="Retevis_RT85_User_Manual.pdf">Full manual, 80 pages: EN, FR, DE, IT, ES</a> (PDF, %s)</li>' % mb("Retevis_RT85_User_Manual.pdf")
if txt: links = '<li><a href="Retevis_RT85_User_Manual_EN.pdf">English only, 20 pages</a> (PDF, %s)</li>' % mb("Retevis_RT85_User_Manual_EN.pdf") + links
open(os.path.join(site, "index.html"), "w").write(f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Retevis RT85 User Manual</title><style>{css}</style></head><body>
<h1>Retevis RT85 user manual</h1><p>Dual-band VHF/UHF handheld (136-174 / 400-480 MHz, 5 W, 200 channels, 1400 mAh 7.4 V battery). Manual by Shenzhen Retevis Technology Co., Ltd., supplied by the owner.</p>
<ul>{links}</ul>{'<p><a href="text.html">English text, searchable</a></p>' if txt else ''}
<p><small>Source: owner-supplied copy of the manufacturer's manual (retevis.com, official download restricted). The model is identified from the specifications and the manufacturer's RT85 listing; the PDF itself does not print the model number.</small></p></body></html>""")
if txt:
    open(os.path.join(site, "text.html"), "w").write(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Retevis RT85 manual (English text)</title><style>{css}</style></head><body><p><a href="index.html">RT85 manual</a> · <a href="Retevis_RT85_User_Manual_EN.pdf">PDF</a></p><h1>Retevis RT85 manual: English text</h1><pre>{html.escape(txt)}</pre></body></html>')
subprocess.run([sys.executable, icon, os.path.join(site, "illustration.png")], check=True)
