#!/bin/sh
# Build the ARKive Emergency Radio Guide ZIM from src/ (original content, MIT licensed).
# Usage: build-zim.sh [OUTDIR]   (default /srv/archive/zim). Needs zimwriterfs (Debian: apt install zim-tools).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd); OUT=${1:-/srv/archive/zim}
STAMP=${ZIM_DATE:-$(date +%Y-%m)}; NAME=arkive_en_emergency-radio
command -v zimwriterfs >/dev/null || { echo "zimwriterfs missing: apt install zim-tools" >&2; exit 1; }
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
mkdir "$TMP/site"; cp -r "$HERE/src/." "$TMP/site/"; python3 "$HERE/make_icon.py" "$TMP/site/illustration.png"
zimwriterfs --welcome=index.html --illustration=illustration.png --language=eng \
  --title="Emergency Radio Guide" --description="Emergency radio channels, 3-3-3 plan and cheat sheet" \
  --longDescription="Plain-language guide to FRS, GMRS, MURS, marine VHF, NOAA weather radio, ham and CB channels for emergencies, with a printable cheat sheet. Original ARKive content, MIT licensed." \
  --creator="ARKive" --publisher="ARKive" --name="$NAME" --tags="_category:arkive;radio;emergency;_ftindex:yes" \
  "$TMP/site" "$TMP/$NAME.zim" >/dev/null
mkdir -p "$OUT"; install -m 664 "$TMP/$NAME.zim" "$OUT/${NAME}_$STAMP.zim"
echo "$OUT/${NAME}_$STAMP.zim"
