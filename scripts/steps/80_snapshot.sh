#!/bin/sh
# Step 80: the Wizer snapshot (build/out/python-snapshot.wasm): the reactor with the interpreter
# initialized and numpy and pandas imported. One preopen, at /, holding the stdlib zip where the
# guest finds it: wasi-libc's preopen table is snapshotted, and so are zipimport's offsets, so the
# snapshot runs only beside this exact zip (spec 003, Decisions 1 and 9).
set -eu
. "$(dirname "$0")/common.sh"

ROOT="$B/wizer-root"
rm -rf "$ROOT" "$OUT/python-snapshot.wasm"
mkdir -p "$ROOT/usr/local/lib"
cp "$OUT/python-stdlib.zip" "$ROOT/usr/local/lib/python314.zip"
WIZER="$T/wizer-v11.0.3-aarch64-macos/wizer"
FLAGS="--allow-wasi --wasm-bulk-memory true --init-func wizer.initialize"
# The command as run, with the build's paths named generically, for MANIFEST's x-wizer line.
echo "wizer $FLAGS --mapdir /::<root with usr/local/lib/python314.zip> -o python-snapshot.wasm python.wasm" \
  > "$OUT/wizer-command.txt"
"$WIZER" $FLAGS --mapdir "/::$ROOT" -o "$OUT/python-snapshot.wasm" "$OUT/python.wasm"
echo "snapshot: $(wc -c < "$OUT/python-snapshot.wasm" | tr -d ' ') bytes, $(shasum -a 256 "$OUT/python-snapshot.wasm" | cut -c1-16)"
