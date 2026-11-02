<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="docs/logo-horizontal-dark.png"><img src="docs/logo-horizontal.png" alt="ARKive — a digital ark for an offline future" width="600"></picture></p>

# ARKive

**ARKive — a digital ark for an offline future.**

ARKive turns a Raspberry Pi into a self-contained offline library: a [Kiwix](https://kiwix.org) server for
ZIM archives (Wikipedia, medical references, how-to guides, maps, books…) plus a small, dependency-free
web panel for files, photos, music and device administration, served over the device's own Wi-Fi hotspot.
No internet connection is needed after setup.

## Features

* **Library** (port 80): `kiwix-serve` with a generated landing page (`build_home.py`): categories, one search box
  across all English full-text-indexed ZIMs, PDF viewer skin.
* **Panel** (port 8080, `mini-web`, Python stdlib only): read-only file browser for manuals/PDFs, offline 3D
  terrain map (MapLibre + PMTiles), photo gallery with thumbnails, music player to a Bluetooth speaker,
  resumable uploads, USB import/export, and a password-protected `/admin` (Wi-Fi, Bluetooth, power, jobs).
* **Hotspot**: an **open** Wi-Fi network (no WPA, by design, so anyone nearby can join without a password).
  Isolation comes from `nftables` (`etc/mini-radio/mini-ap.nft`: hotspot clients are never routed to
  the wired LAN) and a captive-portal DNS (`mini-archive.conf`: every name resolves to the device, plain HTTP
  is redirected to the library). Admin actions require the admin password.
* No third-party scripts, fonts, trackers or cookies on public pages.

## Hardware

* Raspberry Pi 4 (2 GB+; reference build 4 GB) with on-board Wi-Fi + Bluetooth
* microSD card for the OS; a USB SSD/HDD for the library (`/srv/archive`), sized to the ZIMs you want (a few GB to 1 TB+)
* optional: Bluetooth speaker (music), ethernet for administration/updates

## Repository layout

Files mirror their install location:

| path | what |
|---|---|
| `opt/mini-web/` | web panel (`app.py`), landing-page builder, thumbnailer, music, USB UI, static assets, kiwix skin |
| `usr/local/sbin/mini-*` | root helpers called via sudo: `mini-radio` (AP/Bluetooth/SSID), `mini-usb`, `mini-power`, `mini-bt-reconnect`, `mini-admin-passwd` |
| `etc/systemd/system/mini-*` | services: kiwix, web panel, player, thumbnailer, AP firewall, radio boot + watchdog |
| `etc/sudoers.d/02*-mini-*` | the only root commands the panel user (`minitools`) may run |
| `etc/mini-radio/mini-ap.nft`, `etc/NetworkManager/dnsmasq-shared.d/mini-archive.conf` | hotspot isolation + captive DNS |
| `config/arkive.env.example` | device configuration template |

Internal file/unit names keep the historical `mini-*` prefix so existing installs keep working;
user-facing branding is ARKive.

## Install

1. Flash Raspberry Pi OS Lite (64-bit; Bookworm or Trixie, tested on Trixie / Debian 13) and boot with ethernet or a temporary Wi-Fi connection.
2. Install git (`sudo apt install -y git`; Raspberry Pi OS Lite does not ship it), `git clone` this repo onto the Pi, then:
   ```sh
   sudo install -D -m 0644 config/arkive.env.example /etc/arkive/arkive.env && sudoedit /etc/arkive/arkive.env
   sudo ./install.sh        # installs packages, code, units; prompts for the admin password;
                            # starts the library (:80) and panel (:8080) right away
   ```
3. Copy ZIM files into `/srv/archive/zim/` and register them:
   `cd /srv/archive && kiwix-manage library.xml add zim/*.zim` (download ZIMs from https://download.kiwix.org/zim/).
4. Reboot (only needed for the hotspot: it comes up at boot). Join the hotspot and open `http://arkive.lan/` (library) or `http://arkive.lan:8080/admin/`.

Reset the admin password any time with `sudo mini-admin-passwd`.

### Offline terrain map (optional)

The `/terrain` page expects `/srv/archive/files/maps/terrain/mapterhorn-conus-z0-12.pmtiles`. Neither the
tiles nor the `pmtiles` CLI (~54 MB, `bin/pmtiles`) are in this repo. Get the CLI from
https://github.com/protomaps/go-pmtiles/releases and extract a region/zoom range from the Mapterhorn
terrain archive (see https://mapterhorn.com) with `pmtiles extract … --maxzoom=12 --bbox=…`.

## Configuration

| setting | where | default |
|---|---|---|
| hostname clients use | `ARKIVE_HOST` (env or `/etc/arkive/arkive.env`; read by `app.py` and `build_home.py`; must resolve via `mini-archive.conf`) | `arkive.lan` |
| hotspot SSID | `AP_SSID`, or `sudo mini-radio ssid NAME` / admin panel | `ARKive` (re-rolled to a random name at boot by `mini-radio-boot`; disable `reroll.conf` to keep it fixed) |
| hotspot address | `AP_ADDR` | `10.42.0.1/24` |
| admin password | `sudo mini-admin-passwd` → `/etc/mini-web/admin.json` (PBKDF2 hash, never commit) | set at install |
| content | `/srv/archive/{zim,files,manuals}`, `/srv/personal` | — |

## License

MIT — see `LICENSE`. Bundled and relied-on components and content licenses: `THIRD_PARTY.md`.
No ZIM files or other content are included.

## Stay Alive page and Official Manuals

- **Stay Alive** (`:8080/stay-alive`, the big button at the top of the home page): one page organised by need
  (first aid, water, shelter, fire, food, navigation & signalling, hazards, sanitation, plus Rebuild and Maps).
  Each topic lists official manual chapters first (PDF links open at the right page via `#page=`), then the best
  articles from the installed ZIMs. Generated by `opt/mini-web/build_stayalive.py` from `opt/mini-web/stayalive.yaml`
  (`stayalive.json` holds the same data for devices without PyYAML; regenerate it with `build_stayalive.py --export-json`).
  Links to anything not installed, or not answering HTTP 200 from kiwix-serve, are hidden automatically; mini-web
  rebuilds the page shortly after start-up and every 6 hours.
- **Official Manuals** (`:8080/official/`): public-domain US Government manuals (US Army ATP/TC/TB, USGS, NOAA/NWS),
  grouped by subject. The PDFs are **not** in this repo; fetch them on the device with

      sudo -u arkive python3 /usr/local/lib/arkive/tools/fetch_manuals.py --dest /srv/archive/manuals/official

  (install.sh copies the script and `manuals/catalog.json` to `/usr/local/lib/arkive/`, because the arkive user
  usually cannot read a clone in your home directory; re-run install.sh after editing the catalog)

  It reads `manuals/catalog.json` and writes `manifest.json` (title, number, edition, source URL, sha256, licence,
  superseded notes). Only public-release sources are used: APD PDFs behind CAC login and anything marked
  distribution-restricted / FOUO / CUI are refused (with `pdftotext` installed, the first pages are checked).
  Items already in the library's PDF ZIMs are listed but not downloaded again.
