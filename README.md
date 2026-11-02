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

1. Flash Raspberry Pi OS Lite (64-bit, Bookworm) and boot with ethernet or a temporary Wi-Fi connection.
2. `git clone` this repo onto the Pi, then:
   ```sh
   sudo install -D -m 0644 config/arkive.env.example /etc/arkive/arkive.env && sudoedit /etc/arkive/arkive.env
   sudo ./install.sh        # installs packages, code, units; prompts for the admin password
   ```
3. Copy ZIM files into `/srv/archive/zim/` and register them:
   `cd /srv/archive && kiwix-manage library.xml add zim/*.zim` (download ZIMs from https://download.kiwix.org/zim/).
4. Reboot. Join the hotspot and open `http://arkive.lan/` (library) or `http://arkive.lan:8080/admin/`.

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
