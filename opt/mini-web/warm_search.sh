#!/bin/sh
# Pre-load kiwix full-text indexes after mini-kiwix starts so the first real search from the landing page is fast.
sleep 15
Q=$(grep -o 'name="books.id" value="[^"]*"' /srv/archive/home.html | sed 's/.*value="\([^"]*\)"/books.id=\1/' | paste -sd '&')
[ -n "$Q" ] && nice -n 10 curl -s -o /dev/null --max-time 600 "http://127.0.0.1/search?pattern=water&$Q"
exit 0
