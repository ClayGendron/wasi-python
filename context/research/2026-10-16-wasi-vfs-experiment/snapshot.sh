#!/bin/sh
# Step 80's Wizer run, same flags, on a variant reactor.
# Usage: snapshot.sh <scratch dir> <in.wasm> <out dir> [noroot]
#   default  one preopen at / holding usr/local/lib/python314.zip, as step 80
#   noroot   no preopen at all (for a reactor that carries the zip inside, packed by wasi-vfs)
# Writes <out dir>/python-snapshot.wasm.
set -eu
X=$1; IN=$2; OUTD=$3; MODE=${4:-}
R="$X/repo"
ROOT="$X/wizer-root"
mkdir -p "$OUTD"
WIZER="$R/build/tools/wizer-v11.0.3-aarch64-macos/wizer"
FLAGS="--allow-wasi --wasm-bulk-memory true --init-func wizer.initialize"
if [ "$MODE" = noroot ]; then
  "$WIZER" $FLAGS -o "$OUTD/python-snapshot.wasm" "$IN"
else
  rm -rf "$ROOT"; mkdir -p "$ROOT/usr/local/lib"
  cp "$R/build/out/python-stdlib.zip" "$ROOT/usr/local/lib/python314.zip"
  "$WIZER" $FLAGS --mapdir "/::$ROOT" -o "$OUTD/python-snapshot.wasm" "$IN"
fi
echo "snapshot: $(wc -c < "$OUTD/python-snapshot.wasm" | tr -d ' ') bytes, $(shasum -a 256 "$OUTD/python-snapshot.wasm" | cut -c1-64)"
