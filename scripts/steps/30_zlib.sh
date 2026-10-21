#!/bin/sh
# Step 30: zlib 1.3.1 as a static archive for wasm32-wasip1, configured and built outside its source
# tree (build/zlib-build/), so the tree stays byte-identical to its tarball.
set -eu
. "$(dirname "$0")/common.sh"

TARBALL=$(pinned zlib-1.3.1.tar.gz)
remove "$B/zlib-1.3.1" "$B/zlib-build" "$B/zlib-wasi"
tar -xzf "$TARBALL" -C "$B"
patch_tree "$B/zlib-1.3.1"
mkdir -p "$B/zlib-build"
cd "$B/zlib-build"
CC="$SDK/bin/clang --target=wasm32-wasip1" AR="$SDK/bin/llvm-ar" RANLIB="$SDK/bin/llvm-ranlib" \
  CFLAGS="-O2" "$B/zlib-1.3.1/configure" --static --prefix="$B/zlib-wasi"
# zlib's configure picks `libtool -o` as the archiver on Darwin, which rejects wasm objects.
make -j8 AR="$SDK/bin/llvm-ar" ARFLAGS=rc libz.a
make AR="$SDK/bin/llvm-ar" ARFLAGS=rc install
[ -s "$B/zlib-wasi/lib/libz.a" ] || die "no libz.a"
echo "zlib: $(wc -c < "$B/zlib-wasi/lib/libz.a" | tr -d ' ') bytes"
