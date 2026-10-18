#!/bin/sh
# Step 70: the stdlib zip (build/out/python-stdlib.zip): bytecode-only, deflated, deterministic,
# compiled by the pinned host Python (spec 003, Decision 7). _sysconfigdata and numpy's __config__
# say nothing about the build host (spec 012, Decision 5): make_stdlib_zip.py sets their host keys
# to fixed values, and the text rewrites below, computed from what the build knows and applied in
# this order (the triple appears only inside the build-Python's path, which goes first), replace
# the rest. Each Python distribution's METADATA rides along (spec 033): a wheel's from the wheel,
# numpy's and pandas' from their pinned sdists' PKG-INFO. CPython's own ctypes stays out (no libffi
# in wasi-sdk); the recipe's stand-in package takes its place.
set -eu
. "$(dirname "$0")/common.sh"

NUMPY_SITE=$(dirname "$(find "$B/numpy-install" -type d -name numpy -path '*site-packages*' | head -n 1)")
SYSCONFIG="$W/build/lib.wasi-wasm32-$PYTHON_MM/_sysconfigdata__wasi_wasm32-wasi.py"
[ -f "$SYSCONFIG" ] || die "no WASI _sysconfigdata at $SYSCONFIG"
# The build-Python CPython's driver built, found as scripts/python-wasi-cross finds it: its
# directory under cross-build/ is the build triple. Both are host facts the zip must not carry.
BUILD_PYTHON=""
for dir in "$CP"/cross-build/*; do
  [ "$dir" = "$W" ] && continue
  for exe in "$dir/python.exe" "$dir/python"; do
    if [ -f "$exe" ] && [ -x "$exe" ]; then BUILD_PYTHON=$exe; break 2; fi
  done
done
[ -n "$BUILD_PYTHON" ] || die "no build-Python under $CP/cross-build"
TRIPLE=$(basename "$(dirname "$BUILD_PYTHON")")
mkdir -p "$OUT"
host_from_source
PYTHONHASHSEED=0 "$HOSTPY" "$HERE/scripts/make_stdlib_zip.py" \
  --lib "$CP/Lib" --skip ctypes \
  --tree "$NUMPY_SITE" \
  --tree "$B/pandas-install" \
  --wheel "$(pinned python_dateutil-2.9.0.post0-py2.py3-none-any.whl)" \
  --wheel "$(pinned tzdata-2026.5-py2.py3-none-any.whl)" \
  --wheel "$(pinned six-1.17.0-py2.py3-none-any.whl)" \
  --metadata "$B/numpy-2.5.2/PKG-INFO" \
  --metadata "$B/pandas-3.0.6/PKG-INFO" \
  --file "$SYSCONFIG=_sysconfigdata__wasi_wasm32-wasi.py" \
  --file "$HERE/recipes/ctypes_stand_in/__init__.py=ctypes/__init__.py" \
  --file "$HERE/recipes/ctypes_stand_in/_types.py=ctypes/_types.py" \
  --file "$HERE/recipes/ctypes_stand_in/util.py=ctypes/util.py" \
  --file "$HERE/recipes/mmap_stub.py=mmap.py" \
  --replace "cross-build/$TRIPLE/$(basename "$BUILD_PYTHON")=cross-build/build/python" \
  --replace "$WASI_SDK_DIR=wasi-sdk" \
  --replace "$WASMTIME_DIR=wasmtime" \
  --replace "$TRIPLE=build" \
  --replace "$HERE=/wasi-python-build" \
  "$OUT/python-stdlib.zip"
