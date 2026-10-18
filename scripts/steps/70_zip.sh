#!/bin/sh
# Step 70: the stdlib zip (build/out/python-stdlib.zip): bytecode-only, deflated, deterministic,
# compiled by the pinned host Python (spec 003, Decision 7). _sysconfigdata and numpy's __config__
# say nothing about the build host (spec 012, Decision 5): make_stdlib_zip.py sets their host keys
# to fixed values, and the text rewrites below, computed from what the build knows and applied in
# this order (the triple appears only inside the build-Python's path, which goes first), replace
# the rest. Each Python distribution's METADATA rides along (spec 033): a wheel's from the wheel,
# numpy's and pandas' from their pinned sdists' PKG-INFO. CPython's own ctypes stays out (no libffi
# in wasi-sdk); the recipe's stand-in package takes its place. The tool protocol's guest package,
# `host` (spec 031), rides along as the project's own code; the snapshot does not pre-import it.
# Each module's code is compiled under the name zipimport gives a source in the same zip, the
# archive's guest path plus the member (spec 051): that path is recipes/reactor_main.c's
# STDLIB_ZIP, written there once more, and step 80's ZIP. The plot packages (spec 023, Decision 4):
# Pillow's, kiwisolver's and matplotlib's Python files from step 55, the four pure wheels, and their
# METADATA; matplotlib's backends but the ten a plot and its saves can use, its testing and
# sphinxext folders, and every tests/ folder stay out; its mpl-data goes in as one member, an inner
# archive the runner extracts and grants at the path matplotlib computes (Decision 5).
set -eu
. "$(dirname "$0")/common.sh"

NUMPY_SITE=$(dirname "$(find "$B/numpy-install" -type d -name numpy -path '*site-packages*' | head -n 1)")
SYSCONFIG="$W/build/lib.wasi-wasm32-$PYTHON_MM/_sysconfigdata__wasi_wasm32-wasi.py"
[ -f "$SYSCONFIG" ] || die "no WASI _sysconfigdata at $SYSCONFIG"
for pkg in pillow kiwisolver matplotlib; do
  [ -d "$B/plot-install/$pkg" ] || die "build/plot-install/$pkg is missing: run step 55"
done
BACKENDS="__init__.py,registry.py,_backend_pdf_ps.py,backend_mixed.py,backend_agg.py,backend_pdf.py"
BACKENDS="$BACKENDS,backend_ps.py,backend_svg.py,backend_pgf.py,backend_template.py"
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
  --code-prefix "/usr/local/lib/python$PYTHON_TAG.zip/" \
  --tree "$NUMPY_SITE" \
  --tree "$B/pandas-install" \
  --tree "$B/plot-install/pillow" \
  --tree "$B/plot-install/kiwisolver" \
  --tree "$B/plot-install/matplotlib" \
  --wheel "$(pinned python_dateutil-2.9.0.post0-py2.py3-none-any.whl)" \
  --wheel "$(pinned tzdata-2026.5-py2.py3-none-any.whl)" \
  --wheel "$(pinned six-1.17.0-py2.py3-none-any.whl)" \
  --wheel "$(pinned cycler-0.12.1-py3-none-any.whl)" \
  --wheel "$(pinned pyparsing-3.3.3-py3-none-any.whl)" \
  --wheel "$(pinned packaging-26.3-py3-none-any.whl)" \
  --wheel "$(pinned fonttools-4.67.0-py3-none-any.whl)" \
  --metadata "$B/numpy-2.5.2/PKG-INFO" \
  --metadata "$B/pandas-3.0.6/PKG-INFO" \
  --metadata "$B/pillow-13.0.0/PKG-INFO" \
  --metadata "$B/kiwisolver-1.5.1/PKG-INFO" \
  --metadata "$B/matplotlib-3.11.2/PKG-INFO" \
  --keep "matplotlib/backends=$BACKENDS" \
  --drop matplotlib/testing \
  --drop matplotlib/sphinxext \
  --inner matplotlib/mpl-data \
  --file "$SYSCONFIG=_sysconfigdata__wasi_wasm32-wasi.py" \
  --file "$HERE/recipes/ctypes_stand_in/__init__.py=ctypes/__init__.py" \
  --file "$HERE/recipes/ctypes_stand_in/_types.py=ctypes/_types.py" \
  --file "$HERE/recipes/ctypes_stand_in/util.py=ctypes/util.py" \
  --file "$HERE/recipes/mmap_stub.py=mmap.py" \
  --file "$HERE/recipes/guest/host/__init__.py=host/__init__.py" \
  --file "$HERE/recipes/guest/host/tools.py=host/tools.py" \
  --replace "cross-build/$TRIPLE/$(basename "$BUILD_PYTHON")=cross-build/build/python" \
  --replace "$WASI_SDK_DIR=wasi-sdk" \
  --replace "$WASMTIME_DIR=wasmtime" \
  --replace "$TRIPLE=build" \
  --replace "$HERE=/wasi-python-build" \
  "$OUT/python-stdlib.zip"
