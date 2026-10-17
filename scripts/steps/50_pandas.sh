#!/bin/sh
# Step 50: pandas 3.0.6 cross-compiled for wasm32-wasip1 as static archives, outside its source
# tree. pandas generates no Python file at build time (its sdist ships the one meson-time file,
# _version_meson.py), so its Python package for the zip is the sdist's pandas/ tree plus that file:
# no `meson install`, whose macOS install-name fixer chokes on wasm archives (spec 003, landing notes).
set -eu
. "$(dirname "$0")/common.sh"

TARBALL=$(pinned pandas-3.0.6.tar.gz)
SRC="$B/pandas-3.0.6"
BUILD="$B/pandas-build"
remove "$SRC" "$BUILD" "$B/pandas-install"
[ -d "$B/numpy-host/numpy" ] || die "no host-side numpy stand-in: run step 40 first"
tar -xzf "$TARBALL" -C "$B"
sed "s#@ROOT@#$HERE#g; s#@SDK@#$WASI_SDK_DIR#g" "$HERE/recipes/wasi-pandas.cross" > "$B/wasi-pandas.cross"
# The target Python (scripts/python-wasi-cross) finds the numpy stand-in and the build tools here.
export PYTHONPATH="$B/numpy-host:$PYTHONPATH"
cd "$SRC"
# b_ndebug=if-release: C asserts off, as in pandas' own wheels (meson-python's default).
meson setup "$BUILD" --cross-file "$B/wasi-pandas.cross" --buildtype=release -Db_ndebug=if-release
ninja -C "$BUILD"

# The Python package: the sdist's tree and its meson-time version file, as an install would place it.
SITE="$B/pandas-install/pandas"
mkdir -p "$B/pandas-install"
cp -R "$SRC/pandas" "$SITE"
cp "$SRC/_version_meson.py" "$SITE/_version_meson.py"
[ -f "$SITE/core/frame.py" ] || die "the pandas package lacks core/frame.py"
echo "pandas: $(find "$BUILD" -name '*.so' | wc -l | tr -d ' ') extension archives, package at ${SITE#"$B"/}"
