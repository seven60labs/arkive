#!/bin/sh
# ARKive installer: run as root on Raspberry Pi OS Lite 64-bit (Bookworm or Trixie), from a checkout of this repo.
set -eu
cd "$(dirname "$0")"
[ "$(id -u)" = 0 ] || { echo "run as root" >&2; exit 1; }
[ -f /etc/arkive/arkive.env ] || install -D -m 0644 config/arkive.env.example /etc/arkive/arkive.env
. /etc/arkive/arkive.env
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get -y install kiwix-tools python3 python3-pil mpv bluez bluez-alsa-utils libasound2-plugin-bluez \
  jpegoptim libheif-examples curl nftables iw rfkill exfatprogs ntfs-3g dosfstools smartmontools avahi-daemon
id "$ARKIVE_USER" >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin "$ARKIVE_USER"
id minitools >/dev/null 2>&1 || useradd --system --create-home --home-dir /var/lib/minitools --shell /usr/sbin/nologin minitools
usermod -aG audio,bluetooth minitools
# code + config (file names keep the internal "mini-*" prefix)
cp -r opt/mini-web /opt/
# fetch tool + catalog in a system path the arkive user can read (the clone may be in a 0700 home)
install -D -m 0755 tools/fetch_manuals.py /usr/local/lib/arkive/tools/fetch_manuals.py
install -D -m 0644 manuals/catalog.json /usr/local/lib/arkive/manuals/catalog.json
install -m 0755 usr/local/sbin/mini-* /usr/local/sbin/
# stale drop-ins from an older install would silently override the units below: move any we do not ship aside
STALE=/var/backups/arkive-stale-dropins-$(date +%Y%m%d-%H%M%S)
for d in /etc/systemd/system/mini-*.service.d /etc/systemd/system/mini-*.timer.d; do
  [ -d "$d" ] || continue
  for f in "$d"/*; do
    [ -e "$f" ] || continue
    [ -e "etc/systemd/system/$(basename "$d")/$(basename "$f")" ] && continue
    install -d "$STALE/$(basename "$d")" && mv "$f" "$STALE/$(basename "$d")/" && echo "WARNING: moved stale override $f to $STALE/" >&2
  done
done
cp -r etc/systemd/system/. /etc/systemd/system/
sed -i "s/^User=arkive$/User=$ARKIVE_USER/" /etc/systemd/system/mini-kiwix.service
install -d /etc/mini-radio /etc/NetworkManager/dnsmasq-shared.d
install -m 0644 etc/mini-radio/mini-ap.nft /etc/mini-radio/
sed "s/arkive\.lan/$ARKIVE_HOST/g" etc/NetworkManager/dnsmasq-shared.d/mini-archive.conf > /etc/NetworkManager/dnsmasq-shared.d/mini-archive.conf
install -m 0440 etc/sudoers.d/02*-mini-* /etc/sudoers.d/ && visudo -c >/dev/null
[ -d etc/mini-usb ] && cp -n etc/mini-usb/* /etc/mini-usb/ 2>/dev/null || true
# data layout
# Library dirs may be symlinks onto exFAT/NTFS/FAT data disks, which cannot hold
# Unix owners: create them, try to chown, and only warn if the filesystem refuses.
for d in /srv/archive /srv/archive/zim /srv/archive/files /srv/archive/files/maps /srv/archive/manuals /srv/archive/incoming; do
  mkdir -p "$d"
  chown "$ARKIVE_USER:$ARKIVE_USER" "$d" 2>/dev/null || echo "WARNING: $d is on a filesystem without Unix ownership ($(stat -f -c %T "$d")); keeping mount-option ownership" >&2
  sudo -u "$ARKIVE_USER" test -w "$d" || echo "WARNING: $ARKIVE_USER cannot write $d (fine for a read-only library; use uid=/gid= mount options to allow fetches/uploads)" >&2
done
install -d -o minitools -g "$ARKIVE_USER" -m 0775 /srv/archive/generated   # Stay Alive / Official Manuals pages (written by mini-web)
install -d -m 0750 -o minitools -g minitools /srv/personal /srv/personal/music /srv/personal/photos /srv/personal/.thumbs
install -d -m 0755 -o minitools -g minitools /srv/personal/.trash /var/lib/mini-player
[ -f /srv/archive/library.xml ] || sudo -u "$ARKIVE_USER" sh -c 'cd /srv/archive && for z in zim/*.zim; do [ -e "$z" ] && kiwix-manage library.xml add "$z"; done; true'
# open hotspot (no WPA by design; isolation = nftables + captive DNS)
nmcli con show mini-ap >/dev/null 2>&1 || nmcli con add type wifi ifname "$AP_IFACE" con-name mini-ap autoconnect no \
  ssid "$AP_SSID" mode ap ipv4.method shared ipv4.addresses "$AP_ADDR" ipv6.method disabled
# protected disks list for the USB tool: the system card is never a write target
install -d /etc/mini-usb
[ -f /etc/mini-usb/protected.json ] || python3 - <<'P'
import json, subprocess
u = [subprocess.run(["findmnt", "-no", "UUID", m], capture_output=True, text=True).stdout.strip() for m in ("/", "/boot/firmware")]
s = subprocess.run(["lsblk", "-dno", "SERIAL", "/dev/mmcblk0"], capture_output=True, text=True).stdout.split()
json.dump({"serials": s, "uuids": [x for x in u if x], "note": "system card; never a write target"}, open("/etc/mini-usb/protected.json", "w"), indent=1)
P
[ -f /etc/mini-web/admin.json ] || { echo "Set the admin-panel password:"; /usr/local/sbin/mini-admin-passwd; }
systemctl daemon-reload
systemctl enable mini-bt-reconnect.service
# start the library, panel and firewall now (no reboot needed to try it); the radio units only switch at boot,
# because mini-radio-boot turns wlan0 into the hotspot and would drop a Wi-Fi uplink used during setup
systemctl enable --now mini-ap-firewall.service mini-kiwix.service mini-web.service mini-player.service mini-thumbs.service
if [ "${ARKIVE_ZERO:-0}" != 1 ]; then systemctl enable mini-radio-boot.service mini-radio-watchdog.timer; fi
echo "ARKive installed: library http://$(hostname -I | cut -d' ' -f1)/ and panel :8080 are running now."
echo "Reboot to bring up the open hotspot, then join the '$AP_SSID' Wi-Fi and open http://$ARKIVE_HOST/"
