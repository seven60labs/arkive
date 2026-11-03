#!/bin/sh
# Fetch-step hook: build the Emergency Radio Guide ZIM from source and register it with kiwix.
# Usage: install.sh [ARKIVE_ROOT]   (default /srv/archive). Replaces older dated builds of the same ZIM.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd); A=${1:-${ARKIVE_ROOT:-/srv/archive}}; LIB="$A/library.xml"
for old in "$A"/zim/arkive_en_emergency-radio_*.zim; do
  [ -e "$old" ] || continue
  id=$(kiwix-manage "$LIB" show 2>/dev/null | awk -v p="$old" '/^id:/{i=$2} /^path:/{if($2==p) print i}')
  [ -n "$id" ] && kiwix-manage "$LIB" remove "$id" >/dev/null || true
  rm -f "$old"
done
Z=$("$HERE/build-zim.sh" "$A/zim")
( cd "$A" && kiwix-manage "$LIB" add "zim/$(basename "$Z")" )
echo "installed $Z"
