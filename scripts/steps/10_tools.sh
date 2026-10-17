#!/bin/sh
# Step 10: unpack the toolchain and the host Python under build/tools/, replace the toolchain's wasm
# runtime with the host-neutral one (spec 012), and install the build tools (Cython, meson, ninja,
# versioneer) from their pinned wheels: offline, with their hashes (spec 003).
set -eu
. "$(dirname "$0")/common.sh"

SDK_TGZ=$(pinned "$WASI_SDK_DIR.tar.gz")
WASMTIME_TXZ=$(pinned "$WASMTIME_DIR.tar.xz")
PYTHON_TGZ=$(pinned "$HOST_PYTHON_ARCHIVE")
SYSROOT_TGZ=$(pinned "wasi-sysroot-$WASI_SDK_VERSION.0+m.tar.gz")
RT_TGZ=$(pinned "libclang_rt-$WASI_SDK_VERSION.0+m.tar.gz")
WHEELS="$CYTHON_WHEEL meson-1.12.1-py3-none-any.whl
$NINJA_WHEEL versioneer-0.29-py3-none-any.whl"

remove "$T" "$B/wheelhouse"
mkdir -p "$T" "$B/wheelhouse"
for archive in "$SDK_TGZ" "$WASMTIME_TXZ" "$PYTHON_TGZ"; do
  tar -xf "$archive" -C "$T"
done
[ -x "$HOSTPY" ] || die "the host Python did not unpack to $HOSTPY"

# The wasm runtime every host links (spec 012, Decision 2): the host tarball keeps only its compiler.
# Its own sysroot and its wasm32-wasip1 builtins are removed and replaced by wasi-sdk's host-neutral
# ones, the same bytes on every host. The SDK is a downloaded binary toolchain, not a source tree.
set -- "$SDK"/lib/clang/*
[ "$#" -eq 1 ] && [ -d "$1" ] || die "the SDK has $# lib/clang/* directories, not exactly one"
BUILTINS="$1/lib/wasm32-unknown-wasip1"
[ -d "$BUILTINS" ] || die "the SDK has no $BUILTINS"
remove "$SDK/share/wasi-sysroot" "$BUILTINS" "$B/neutral-rt"
mkdir -p "$SDK/share/wasi-sysroot" "$BUILTINS" "$B/neutral-rt"
tar -xzf "$SYSROOT_TGZ" -C "$SDK/share/wasi-sysroot" --strip-components=1
tar -xzf "$RT_TGZ" -C "$B/neutral-rt" --strip-components=1
cp "$B/neutral-rt/wasm32-unknown-wasip1/"* "$BUILTINS/"
remove "$B/neutral-rt"

# Only the pinned wheels, and a requirements file carrying their pinned hashes.
REQS="$B/tools-requirements.txt"
: > "$REQS"
for wheel in $WHEELS; do
  cp "$(pinned "$wheel")" "$B/wheelhouse/"
  sha=$(grep "  $wheel\$" "$D/SHA256SUMS" | cut -c1-64)
  dist=${wheel%%-*}
  rest=${wheel#*-}
  printf '%s==%s --hash=sha256:%s\n' "$dist" "${rest%%-*}" "$sha" >> "$REQS"
done
uv pip install --python "$HOSTPY" --target "$T/pylib" --offline --no-index --find-links "$B/wheelhouse" --require-hashes -r "$REQS"

"$HOSTPY" -c "import platform, sys; assert platform.python_version() == sys.argv[1], sys.version" "$PYTHON_VERSION"
for tool in meson ninja cython; do
  command -v "$tool" > /dev/null || die "$tool is not on PATH from build/tools/pylib/bin"
done
echo "tools: python $("$HOSTPY" -c 'import platform; print(platform.python_version())'), meson $(meson --version), ninja $(ninja --version), cython $(cython --version 2>&1 | cut -d' ' -f3)"
