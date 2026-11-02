#!/bin/sh
# ARKive installer: run as root on a fresh Raspberry Pi OS (Bookworm) image, from a checkout of this repo.
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
install -m 0755 usr/local/sbin/mini-* /usr/local/sbin/
cp -r etc/systemd/system/. /etc/systemd/system/
sed -i "s/^User=arkive$/User=$ARKIVE_USER/" /etc/systemd/system/mini-kiwix.service
install -d /etc/mini-radio /etc/NetworkManager/dnsmasq-shared.d
install -m 0644 etc/mini-radio/mini-ap.nft /etc/mini-radio/
sed "s/arkive\.lan/$ARKIVE_HOST/g" etc/NetworkManager/dnsmasq-shared.d/mini-archive.conf > /etc/NetworkManager/dnsmasq-shared.d/mini-archive.conf
install -m 0440 etc/sudoers.d/02*-mini-* /etc/sudoers.d/ && visudo -c >/dev/null
[ -d etc/mini-usb ] && cp -n etc/mini-usb/* /etc/mini-usb/ 2>/dev/null || true
# data layout
install -d -o "$ARKIVE_USER" -g "$ARKIVE_USER" /srv/archive /srv/archive/zim /srv/archive/files /srv/archive/files/maps /srv/archive/manuals /srv/archive/incoming
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
systemctl enable mini-ap-firewall.service mini-kiwix.service mini-web.service mini-player.service mini-thumbs.service mini-bt-reconnect.service
if [ "${ARKIVE_ZERO:-0}" != 1 ]; then systemctl enable mini-radio-boot.service mini-radio-watchdog.timer; fi
echo "ARKive installed. Reboot, then join the '$AP_SSID' Wi-Fi and open http://$ARKIVE_HOST/"
