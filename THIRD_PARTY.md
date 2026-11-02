# Third-party components

ARKive's own code is MIT-licensed (`LICENSE`). It bundles or relies on:

| component | how | license |
|---|---|---|
| [Kiwix](https://kiwix.org) `kiwix-tools` (kiwix-serve, kiwix-manage) | installed from apt, not bundled | GPL-3.0 |
| ZIM content (Wikipedia, Wikivoyage, Stack Exchange, Project Gutenberg, …) | **not included**; downloaded by the user | per collection — e.g. Wikipedia text is CC BY-SA 4.0 (attribution + share-alike), Gutenberg is public domain in the US |
| MapLibre GL JS (`opt/mini-web/static/vendor/maplibre-gl.*`) | bundled | BSD-3-Clause (`vendor/MAPLIBRE-LICENSE.txt`) |
| PMTiles JS (`vendor/pmtiles.js`, protomaps) | bundled | BSD-3-Clause |
| `pmtiles` CLI (protomaps/go-pmtiles) | **not included** (`bin/pmtiles`, ~54 MB); download from its GitHub releases | BSD-3-Clause |
| OpenStreetMap-derived map tiles / Protomaps basemaps | **not included** | ODbL 1.0 (© OpenStreetMap contributors) |
| Mapterhorn terrain tiles (`/terrain` page) | **not included** | see https://mapterhorn.com/attribution (attribution shown on the page) |
| `3dep-13-footprints.geojson` (USGS 3DEP 1/3 arc-second tile footprints) | bundled | US public domain (USGS) |
| mpv, BlueALSA, NetworkManager, nftables | installed from apt | GPL/LGPL family |

The public pages load no third-party scripts, fonts, analytics or cookies (only /admin sets a first-party, HttpOnly session cookie); everything is served from the device.
