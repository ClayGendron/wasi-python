#!/bin/sh
# Fetch every Linux pin into dl-linux/ (untrusted data: nothing here runs it) and verify its SHA-256.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd -P)
mkdir -p "$HERE/dl-linux"
grep -v '^#' "$HERE/linux-pins.txt" | while read -r sha name url; do
  [ -s "$HERE/dl-linux/$name" ] || curl -fsSL --retry 3 -o "$HERE/dl-linux/$name" "$url"
  echo "$sha  $name"
done > "$HERE/dl-linux/SHA256SUMS"
cd "$HERE/dl-linux" && shasum -a 256 -c SHA256SUMS
