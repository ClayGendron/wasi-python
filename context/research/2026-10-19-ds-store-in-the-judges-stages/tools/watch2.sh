#!/bin/bash
# watch2.sh <out> <stopfile> <dir>...: every 0.5 s, log the first sight of each .DS_Store (path + birth time) under the dirs
out=$1; stop=$2; shift 2
seen="$out.seen"; : > "$seen"
while [ ! -e "$stop" ]; do
  find "$@" -name .DS_Store 2>/dev/null | while IFS= read -r f; do
    k="$f $(stat -f %B "$f" 2>/dev/null)"
    if ! grep -qxF "$k" "$seen"; then echo "$k" >> "$seen"; echo "$(date +%T) birth=$(stat -f %SB -t %T "$f") size=$(stat -f %z "$f") $f" >> "$out"; fi
  done
  sleep 0.5
done
