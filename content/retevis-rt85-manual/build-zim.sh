#!/bin/sh
# Build a small ZIM around the owner-supplied Retevis RT85 manual PDFs (the PDFs are NOT in git).
# Usage: build-zim.sh [ARKIVE_ROOT]  -> builds zim/arkive_en_retevis-rt85-manual_YYYY-MM.zim and registers it.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd); A=${1:-${ARKIVE_ROOT:-/srv/archive}}; LIB="$A/library.xml"
D="$A/manuals/radio/retevis"; NAME=arkive_en_retevis-rt85-manual; STAMP=${ZIM_DATE:-$(date +%Y-%m)}
[ -f "$D/Retevis_RT85_User_Manual.pdf" ] || { echo "missing $D/Retevis_RT85_User_Manual.pdf (owner-supplied)" >&2; exit 1; }
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT; mkdir "$TMP/site"
cp "$D"/Retevis_RT85_User_Manual*.pdf "$TMP/site/"
python3 "$HERE/make_site.py" "$TMP/site" "$HERE/../emergency-radio/make_icon.py" "$D"
zimwriterfs --welcome=index.html --illustration=illustration.png --language=eng \
  --title="Retevis RT85 User Manual" --description="Retevis RT85 dual-band handheld: user manual PDFs" \
  --longDescription="Owner-supplied Retevis RT85 user's manual (EN/FR/DE/IT/ES) plus an English-only extract and searchable English text." \
  --creator="Shenzhen Retevis Technology" --publisher="ARKive" --name="$NAME" --tags="_category:arkive;radio;manual;_ftindex:yes" \
  "$TMP/site" "$TMP/$NAME.zim" >/dev/null
for old in "$A"/zim/${NAME}_*.zim; do
  [ -e "$old" ] || continue
  id=$(kiwix-manage "$LIB" show 2>/dev/null | awk -v p="zim/$(basename "$old")" '/^id:/{i=$2} /^path:/{if($2==p||index($2,p)) print i}')
  [ -n "$id" ] && kiwix-manage "$LIB" remove $id >/dev/null || true; rm -f "$old"
done
install -m 664 "$TMP/$NAME.zim" "$A/zim/${NAME}_$STAMP.zim"
( cd "$A" && kiwix-manage "$LIB" add "zim/${NAME}_$STAMP.zim" )
echo "$A/zim/${NAME}_$STAMP.zim"
