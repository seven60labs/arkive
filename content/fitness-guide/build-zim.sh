#!/bin/sh
# Build the ARKive Fitness Guide ZIM from src/ (original content, MIT licensed).
# Usage: build-zim.sh [OUTDIR]   (default /srv/archive/zim). Needs zimwriterfs (Debian: apt install zim-tools).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd); OUT=${1:-/srv/archive/zim}
STAMP=${ZIM_DATE:-$(date +%Y-%m)}; NAME=arkive_en_fitness-guide
command -v zimwriterfs >/dev/null || { echo "zimwriterfs missing: apt install zim-tools" >&2; exit 1; }
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
mkdir "$TMP/site"; cp -r "$HERE/src/." "$TMP/site/"; python3 "$HERE/make_icon.py" "$TMP/site/illustration.png"
zimwriterfs --welcome=index.html --illustration=illustration.png --language=eng \
  --title="Fitness Guide" --description="No-equipment exercise, stretching, yoga, breathing and weekly plans" \
  --longDescription="Plain-language, no-equipment fitness guide: safety, calisthenics progressions, stretching and mobility, beginner yoga, breathing and meditation, weekly plans, recovery and a printable cheat sheet. Original ARKive content, MIT licensed." \
  --creator="ARKive" --publisher="ARKive" --name="$NAME" --tags="_category:arkive;health;fitness;_ftindex:yes" \
  "$TMP/site" "$TMP/$NAME.zim" >/dev/null
mkdir -p "$OUT"; install -m 664 "$TMP/$NAME.zim" "$OUT/${NAME}_$STAMP.zim"
echo "$OUT/${NAME}_$STAMP.zim"
