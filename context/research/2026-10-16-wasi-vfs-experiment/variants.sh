#!/bin/sh
# Build every variant the memo measures, from the relinked reactors (relink.sh control, late).
# Usage: variants.sh <scratch dir> <mpl-data dir>
set -eu
X=$1; MPL=$2
HERE=$(cd "$(dirname "$0")" && pwd -P)
VFS="$X/cli/wasi-vfs"
ZG=/usr/local/lib/python314.zip/matplotlib/mpl-data
PG=/usr/local/share/wasi-python/mpl-data
# The stdlib zip alone in a directory, to pack at /usr/local/lib.
rm -rf "$X/libdir"; mkdir -p "$X/libdir"
cp "$X/repo/build/out/python-stdlib.zip" "$X/libdir/python314.zip"

pack() { # pack <name> <in> <dir args...>
  name=$1; in=$2; shift 2
  mkdir -p "$X/out/$name"
  "$VFS" pack "$in" "$@" -o "$X/out/$name/python.wasm" 2> "$X/out/$name/pack.log"
  echo "$name: $(wc -c < "$X/out/$name/python.wasm" | tr -d ' ') bytes, $(shasum -a 256 "$X/out/$name/python.wasm" | cut -c1-64)"
}
# The vfs library linked in, nothing packed: the per-call overhead.
"$HERE/snapshot.sh" "$X" "$X/out/late/python.wasm" "$X/out/late"
# A: mpl-data at the zip's path; the zip stays in the root (pack, then step 80).
pack packA "$X/out/late/python.wasm" --dir "$MPL::$ZG"
"$HERE/snapshot.sh" "$X" "$X/out/packA/python.wasm" "$X/out/packA"
# A again, from scratch, for byte reproducibility.
pack packA2 "$X/out/late/python.wasm" --dir "$MPL::$ZG"
"$HERE/snapshot.sh" "$X" "$X/out/packA2/python.wasm" "$X/out/packA2"
# P: mpl-data at a plain path.
pack packP "$X/out/late/python.wasm" --dir "$MPL::$PG"
"$HERE/snapshot.sh" "$X" "$X/out/packP/python.wasm" "$X/out/packP"
# Z: the stdlib zip and mpl-data both packed; snapshot taken with no preopen at all (sealed),
# and again with step 80's root (Zr) to see which wins when both claim a path.
pack packZ "$X/out/late/python.wasm" --dir "$X/libdir::/usr/local/lib" --dir "$MPL::$ZG"
"$HERE/snapshot.sh" "$X" "$X/out/packZ/python.wasm" "$X/out/packZ" noroot
mkdir -p "$X/out/packZr"; cp "$X/out/packZ/python.wasm" "$X/out/packZr/python.wasm"
"$HERE/snapshot.sh" "$X" "$X/out/packZr/python.wasm" "$X/out/packZr"
# B: the other order (step 80 first, then pack the snapshot).
pack orderB "$X/out/late/python-snapshot.wasm" --dir "$MPL::$ZG"
