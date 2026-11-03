# Fetch lists (radio additions)

- `radio-catalog.json` official radio manual URLs (manufacturer or authorised distributor) with sha256; `fetch_radio.py` downloads them into /srv/archive/manuals/radio/<maker>/ and writes manifest.json.
- `zim-downloads.tsv` ZIMs to fetch or build; `build` rows run the named script.

Third-party PDFs are never committed. Merge these into the main repo's manuals catalog.json / ZIM download queue.
