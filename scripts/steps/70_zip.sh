#!/bin/sh
# Step 70: the stdlib zip (build/out/python-stdlib.zip): bytecode-only, deflated, deterministic,
# compiled by the pinned host Python (spec 003, Decision 7).
set -eu
. "$(dirname "$0")/common.sh"

NUMPY_SITE=$(dirname "$(find "$B/numpy-install" -type d -name numpy -path '*site-packages*' | head -n 1)")
SYSCONFIG="$W/build/lib.wasi-wasm32-$PYTHON_MM/_sysconfigdata__wasi_wasm32-wasi.py"
[ -f "$SYSCONFIG" ] || die "no WASI _sysconfigdata at $SYSCONFIG"
mkdir -p "$OUT"
host_from_source
PYTHONHASHSEED=0 "$HOSTPY" "$HERE/scripts/make_stdlib_zip.py" \
  --lib "$CP/Lib" --skip ctypes \
  --tree "$NUMPY_SITE" \
  --tree "$B/pandas-install" \
  --wheel "$(pinned python_dateutil-2.9.0.post0-py2.py3-none-any.whl)" \
  --wheel "$(pinned tzdata-2026.5-py2.py3-none-any.whl)" \
  --wheel "$(pinned six-1.17.0-py2.py3-none-any.whl)" \
  --file "$SYSCONFIG=_sysconfigdata__wasi_wasm32-wasi.py" \
  --file "$HERE/recipes/ctypes_stub.py=ctypes.py" \
  --file "$HERE/recipes/mmap_stub.py=mmap.py" \
  --replace "$HERE=/wasi-python-build" \
  "$OUT/python-stdlib.zip"
