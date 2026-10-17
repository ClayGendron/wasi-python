#!/bin/sh
# Step 40: numpy 2.5.2 cross-compiled for wasm32-wasip1 as static archives, with numpy's vendored
# meson, outside its source tree; installed (its Python package and headers); then the host-side numpy stand-in
# pandas' build imports (spec 003, Decisions 1 and 6).
set -eu
. "$(dirname "$0")/common.sh"

TARBALL=$(pinned numpy-2.5.2.tar.gz)
SRC="$B/numpy-2.5.2"
BUILD="$B/numpy-build"
remove "$SRC" "$BUILD" "$B/numpy-install" "$B/numpy-host"
tar -xzf "$TARBALL" -C "$B"
sed "s#@ROOT@#$HERE#g; s#@SDK@#$WASI_SDK_DIR#g" "$HERE/recipes/wasi-numpy.cross" > "$B/wasi-numpy.cross"
cd "$SRC"
MESON="$SRC/vendored-meson/meson/meson.py"  # the meson that configures a build directory installs it
"$HOSTPY" "$MESON" setup "$BUILD" --cross-file "$B/wasi-numpy.cross" --buildtype=release \
  -Dallow-noblas=true -Dblas=none -Dlapack=none -Ddisable-optimization=true -Ddisable-threading=true \
  -Ddisable-highway=true -Ddisable-intel-sort=true -Ddisable-svml=true -Dtest-simd=BASELINE
ninja -C "$BUILD"
# python-runtime and devel: the whole Python package and its headers. Not the test modules: meson's
# installer on a macOS host runs install_name_tool on them, and they are archives, not Mach-O.
"$HOSTPY" "$MESON" install -C "$BUILD" --destdir "$B/numpy-install" --tags python-runtime,devel --quiet

SITE=$(find "$B/numpy-install" -type d -name numpy -path '*site-packages*' | head -n 1)
[ -n "$SITE" ] || die "no installed numpy package under build/numpy-install"
HOST="$B/numpy-host/numpy"
mkdir -p "$HOST/_core"
cp "$HERE/recipes/numpy_host_shim.py" "$HOST/__init__.py"
cp "$SRC/numpy/__init__.pxd" "$SRC/numpy/__init__.cython-30.pxd" "$HOST/"
cp -R "$SITE/_core/include" "$HOST/_core/include"  # sdist headers plus the generated WASI ones
for header in _numpyconfig.h __multiarray_api.h __ufunc_api.h; do
  [ -f "$HOST/_core/include/numpy/$header" ] || die "the stand-in lacks the generated $header"
done
grep -q 'NPY_SIZEOF_LONGDOUBLE 16' "$HOST/_core/include/numpy/_numpyconfig.h" ||
  die "the generated _numpyconfig.h does not describe wasm32's 16-byte long double"
echo "numpy: $(find "$BUILD" -name '*.so' | wc -l | tr -d ' ') extension archives, installed at ${SITE#"$B"/}"
