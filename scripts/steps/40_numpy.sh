#!/bin/sh
# Step 40: numpy 2.5.2 cross-compiled for wasm32-wasip1 as static archives, with numpy's vendored
# meson, outside its source tree; installed (its Python package and headers); then the host-side numpy stand-in
# pandas' build imports. numpy's linear algebra, dot and matmul link step 38's OpenBLAS, the one
# scipy links: numpy's meson finds it through step 10's pinned pkgconf, recipes/numpy_lapack_abi.h
# (force-included per file) and recipes/numpy_lapack_shims.c bridge numpy's int declarations to
# OpenBLAS's void subroutines, and lapack_lite's f2c LAPACK is never compiled. Needs step 38.
set -eu
. "$(dirname "$0")/common.sh"

TARBALL=$(pinned numpy-2.5.2.tar.gz)
SRC="$B/numpy-2.5.2"
BUILD="$B/numpy-build"
SHIMS="$B/numpy-shims"
OB="$B/openblas-wasi"
[ -s "$OB/lib/libopenblas.a" ] && [ -f "$OB/lib/pkgconfig/openblas.pc" ] \
  || die "build/openblas-wasi has no libopenblas.a or openblas.pc: run step 38"
remove "$SRC" "$BUILD" "$SHIMS" "$B/numpy-install" "$B/numpy-host"
tar -xzf "$TARBALL" -C "$B"
patch_tree "$SRC"
sed "s#@ROOT@#$HERE#g; s#@SDK@#$WASI_SDK_DIR#g" "$HERE/recipes/wasi-numpy.cross" > "$B/wasi-numpy.cross"
mkdir -p "$BUILD" "$SHIMS"
# pkgconf sees OpenBLAS's own openblas.pc and nothing else: PKG_CONFIG_LIBDIR replaces its default
# search path, so a host's openblas.pc can never be found (step 57's rule).
export PKG_CONFIG_PATH="$OB/lib/pkgconfig" PKG_CONFIG_LIBDIR="$OB/lib/pkgconfig"
# The per-file include map, rendered into build/: numpy's linear-algebra
# files and its three python_xerbla.c compiles get recipes/numpy_lapack_abi.h, nothing else does.
sed "s#@ROOT@#$HERE#g" "$HERE/recipes/numpy_file_includes.txt" > "$BUILD/file-includes.txt"
export WASI_CC_FILE_INCLUDES="$BUILD/file-includes.txt" WASI_CC_FILE_INCLUDES_LOG="$BUILD/file-includes.log"
: > "$WASI_CC_FILE_INCLUDES_LOG"
cd "$SRC"
MESON="$SRC/vendored-meson/meson/meson.py"  # the meson that configures a build directory installs it
# -Dallow-noblas=false: a failed detection stops here, never falls back to lapack_lite.
"$HOSTPY" "$MESON" setup "$BUILD" --cross-file "$B/wasi-numpy.cross" --buildtype=release \
  -Dblas=openblas -Dlapack=openblas -Dallow-noblas=false -Duse-ilp64=false \
  -Ddisable-optimization=true -Ddisable-threading=true \
  -Ddisable-highway=true -Ddisable-intel-sort=true -Ddisable-svml=true -Dtest-simd=BASELINE
ninja -C "$BUILD"
# The per-file include log: each map entry matched exactly as many compiles as it says (one when it
# says nothing).
grep -v '^#' "$BUILD/file-includes.txt" | while read -r suffix header count; do
  [ -n "$suffix" ] || continue
  n=$(cut -f 1 "$WASI_CC_FILE_INCLUDES_LOG" | grep -c -x -F -- "$suffix" || :)
  [ "$n" = "${count:-1}" ] || die "per-file include $suffix matched $n compiles, not ${count:-1} (build/numpy-build/file-includes.log)"
  echo "per-file include: $suffix -> ${header##*/}, $n compile(s)"
done
unset WASI_CC_FILE_INCLUDES WASI_CC_FILE_INCLUDES_LOG
if find "$BUILD" -name '*lapack_lite_f2c*.o' | grep -q .; then
  die "numpy compiled lapack_lite's f2c LAPACK: its meson did not find OpenBLAS's LAPACK"
fi
# python-runtime and devel: the whole Python package and its headers. Not the test modules: meson's
# installer on a macOS host runs install_name_tool on them, and they are archives, not Mach-O.
"$HOSTPY" "$MESON" install -C "$BUILD" --destdir "$B/numpy-install" --tags python-runtime,devel --quiet

# numpy's side of the LAPACK ABI: 35 shims of ours, compiled alone, no numpy
# flag and no rename header.
"$SDK/bin/clang" --target=wasm32-wasip1 -O2 -ffile-prefix-map="$HERE=/wasi-python-build" \
  -c "$HERE/recipes/numpy_lapack_shims.c" -o "$SHIMS/numpy_lapack_shims.o"
"$SDK/bin/llvm-ar" rcD "$SHIMS/libnumpy_lapack_shims.a" "$SHIMS/numpy_lapack_shims.o"

SITE=$(find "$B/numpy-install" -type d -name numpy -path '*site-packages*' | head -n 1)
[ -n "$SITE" ] || die "no installed numpy package under build/numpy-install"
# numpy says what it found: its __config__.py names openblas for BLAS and for LAPACK.
for dep in blas lapack; do
  grep -A 1 -F "\"$dep\": {" "$SITE/__config__.py" | grep -q -F '"name": "openblas",' \
    || die "the installed numpy/__config__.py does not name openblas for $dep"
done
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
