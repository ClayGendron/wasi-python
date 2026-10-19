#!/bin/sh
# Strip a relinked reactor as step 60 does and snapshot it as step 80 does. Usage: snapshot.sh <variant dir> [mpl]
# With "mpl", matplotlib's data is granted at its nested path and /tmp is writable, as spec 023's builder did.
set -eu
HERE=/Users/claygendron/Git/Repos/wasi_python
SET=$HERE/build/sets/s-4eb5418a2b1bb553
SDK=$HERE/build/tools/wasi-sdk-33.0-arm64-macos
WT=$HERE/build/tools/wasmtime-v49.0.3-aarch64-macos/wasmtime
V=$1
S=$(dirname "$V")
"$SDK/bin/llvm-strip" --strip-debug "$V/python.wasm"
ROOT="$V/wizer-root"; rm -rf "$ROOT"; mkdir -p "$ROOT/usr/local/lib" "$V/tmp"
cp "$SET/python-stdlib.zip" "$ROOT/usr/local/lib/python315.zip"
DIRS="--dir $ROOT::/"
if [ "${2:-}" = mpl ]; then
  [ -d "$S/mpl-data" ] || "$HERE/.venv/bin/python" -c "
import zipfile, io, sys
with zipfile.ZipFile('$SET/python-stdlib.zip') as outer: inner = io.BytesIO(outer.read('matplotlib/mpl-data.zip'))
with zipfile.ZipFile(inner) as z: z.extractall('$S/mpl-data')"
  DIRS="$DIRS --dir $S/mpl-data::/usr/local/lib/python315.zip/matplotlib/mpl-data --dir $V/tmp::/tmp"
fi
FLAGS="-W exceptions=y,unknown-imports-trap=y -S cli=y,inherit-stdin=n,inherit-stdout=n,inherit-stderr=n -C cache=n --init-func wizer.initialize"
echo "wasmtime wizer $FLAGS $DIRS -o python-snapshot.wasm python.wasm" > "$V/wizer-command.txt"
"$WT" wizer $FLAGS $DIRS -o "$V/python-snapshot.wasm" "$V/python.wasm"
rm -rf "$ROOT"
echo "$V: python.wasm $(wc -c < "$V/python.wasm" | tr -d ' ') snapshot $(wc -c < "$V/python-snapshot.wasm" | tr -d ' ') $(shasum -a 256 "$V/python-snapshot.wasm" | cut -c1-16)"
