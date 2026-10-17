#!/bin/sh
# Step 20: CPython (the line's version) for wasm32-wasip1 with its own Platforms/WASI driver, run under the
# pinned host Python. The driver first builds a native build-Python with the host's C compiler (the
# one unpinned host input: spec 003, Decision 2), then the WASI interpreter in cross-build/.
set -eu
. "$(dirname "$0")/common.sh"

TARBALL=$(pinned "Python-$PYTHON_VERSION.tar.xz")
remove "$CP"
tar -xf "$TARBALL" -C "$B"
patch_tree "$CP"
cd "$CP"
# The build-Python must not see the build tools' path; SOURCE_DATE_EPOCH comes from build.sh.
mkdir -p "$B/logs/cpython"
# --disable-test-modules: CPython's _test* and xx* modules are not part of the product.
env -u PYTHONPATH "$HOSTPY" Platforms/WASI build --quiet --logdir "$B/logs/cpython" -- --disable-test-modules
[ -f "$W/python.wasm" ] || die "no python.wasm in $W"
echo "cpython: $(wc -c < "$W/python.wasm" | tr -d ' ') bytes, $(shasum -a 256 "$W/python.wasm" | cut -c1-16)"
