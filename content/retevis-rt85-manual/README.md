# Retevis RT85 manual ZIM

The RT85 manual's official download on retevis.com is restricted, so the PDF is **owner-supplied** and is **not in git**.
Put the files in `/srv/archive/manuals/radio/retevis/`:

- `Retevis_RT85_User_Manual.pdf` (full EN/FR/DE/IT/ES manual, ghostscript `/ebook`)
- `Retevis_RT85_User_Manual_EN.pdf` (pages 1-18 and 79-80, optional)
- `Retevis_RT85_User_Manual_EN.txt` (optional; `pdftotext -layout` of the EN PDF, used for the searchable text page)

Then run `build-zim.sh [ARKIVE_ROOT]` to build `zim/arkive_en_retevis-rt85-manual_YYYY-MM.zim` and register it with kiwix.
The scripts are MIT licensed; the manual is © Shenzhen Retevis Technology Co., Ltd.
