#!/bin/sh
# Step 10: unpack the toolchain and the host Python under build/tools/, and install the build tools
# (Cython, meson, ninja, versioneer) from their pinned wheels: offline, with their hashes (spec 003).
set -eu
. "$(dirname "$0")/common.sh"

SDK_TGZ=$(pinned "$WASI_SDK_DIR.tar.gz")
WASMTIME_TXZ=$(pinned "$WASMTIME_DIR.tar.xz")
PYTHON_TGZ=$(pinned "$HOST_PYTHON_ARCHIVE")
WHEELS="$CYTHON_WHEEL meson-1.12.1-py3-none-any.whl
ninja-1.13.2-py3-none-macosx_10_9_universal2.whl versioneer-0.29-py3-none-any.whl"

rm -rf "$T" "$B/wheelhouse"
mkdir -p "$T" "$B/wheelhouse"
for archive in "$SDK_TGZ" "$WASMTIME_TXZ" "$PYTHON_TGZ"; do
  tar -xf "$archive" -C "$T"
done
[ -x "$HOSTPY" ] || die "the host Python did not unpack to $HOSTPY"

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
