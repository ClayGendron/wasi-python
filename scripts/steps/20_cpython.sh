#!/bin/sh
# Step 20: CPython (the line's version) for wasm32-wasip1 with its own Platforms/WASI driver, run under the
# pinned host Python. The driver first builds a native build-Python with the host's C compiler (the
# one unpinned host input), then the WASI interpreter in cross-build/.
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
# --with-hash-algorithm=siphash13: CPython's default, which configure leaves for 32-bit FNV when it
# cannot run its aligned-access probe, as in a cross build; wasm loads unaligned words, and FNV
# can be flooded with colliding keys (PEP 456). The
# build-Python gets it too, as its own default.
env -u PYTHONPATH "$HOSTPY" Platforms/WASI build --quiet --logdir "$B/logs/cpython" -- \
  --disable-test-modules --with-hash-algorithm=siphash13
[ -f "$W/python.wasm" ] || die "no python.wasm in $W"
# The driver's two Pythons write bytecode into Lib/ though common.sh says not to: the
# build-Python's own make runs it with -E, which ignores PYTHONDONTWRITEBYTECODE, and `make
# pythoninfo` runs python.wasm under wasmtime, which passes the guest no host variable. Nothing
# reads them later (steps 60 and 70 marshal with the tools' Python), so they go.
find "$CP/Lib" -name __pycache__ -type d -prune | while read -r d; do remove "$d"; done
echo "cpython: $(wc -c < "$W/python.wasm" | tr -d ' ') bytes, $(shasum -a 256 "$W/python.wasm" | cut -c1-16)"
