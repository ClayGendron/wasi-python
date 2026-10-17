#!/bin/sh
# Step 35 (experiment): the C libraries behind three stdlib modules WASI builds lack, as static
# archives for wasm32-wasip1: bzip2 1.0.8 (_bz2), liblzma from xz 5.8.4 (_lzma) and SQLite 3.54.1
# (_sqlite3). Each is unpacked from its pinned tarball and compiled outside its source tree, so the
# tree stays byte-identical to the tarball (spec 003, Decision 4). Step 60 links them as builtins.
set -eu
. "$(dirname "$0")/common.sh"

CC="$SDK/bin/clang --target=wasm32-wasip1"
AR="$SDK/bin/llvm-ar"
RANLIB="$SDK/bin/llvm-ranlib"
LIBS="$B/stdlib-libs"
rm -rf "$B/bzip2-1.0.8" "$B/xz-5.8.4" "$B/sqlite-autoconf-3540100" "$B/bzip2-build" "$B/xz-build" \
  "$B/sqlite-build" "$LIBS"
mkdir -p "$LIBS/include" "$LIBS/lib"

# bzip2: its Makefile builds in the source tree, so the seven library files of its `libbz2.a`
# target are compiled here with the Makefile's own flags (less -g).
tar -xzf "$(pinned bzip2-1.0.8.tar.gz)" -C "$B"
mkdir -p "$B/bzip2-build"
for f in blocksort huffman crctable randtable compress decompress bzlib; do
  $CC -O2 -D_FILE_OFFSET_BITS=64 -c "$B/bzip2-1.0.8/$f.c" -o "$B/bzip2-build/$f.o"
done
"$AR" rcD "$LIBS/lib/libbz2.a" $(for f in blocksort huffman crctable randtable compress decompress bzlib; do
  printf '%s ' "$B/bzip2-build/$f.o"; done)
cp "$B/bzip2-1.0.8/bzlib.h" "$LIBS/include/"
echo "bzip2: $(wc -c < "$LIBS/lib/libbz2.a" | tr -d ' ') bytes"

# liblzma: xz's own configure, run from a separate build directory (an autotools VPATH build).
# Only the library: no tools, scripts, docs or translations; no threads on wasm32-wasip1.
tar -xzf "$(pinned xz-5.8.4.tar.gz)" -C "$B"
mkdir -p "$B/xz-build"
cd "$B/xz-build"
CC="$CC" AR="$AR" RANLIB="$RANLIB" CFLAGS="-O2" "$B/xz-5.8.4/configure" --host=wasm32-unknown-wasip1 \
  --prefix="$LIBS" --disable-shared --enable-static --disable-threads --disable-xz --disable-xzdec \
  --disable-lzmadec --disable-lzmainfo --disable-lzma-links --disable-scripts --disable-doc \
  --disable-nls --disable-rpath --disable-sandbox > "$B/xz-build/configure.out" 2>&1 \
  || { tail -n 20 "$B/xz-build/config.log"; die "xz configure failed"; }
make -j8 -C src/liblzma > "$B/xz-build/make.out" 2>&1 || { tail -n 20 "$B/xz-build/make.out"; die "liblzma make failed"; }
make -C src/liblzma install > "$B/xz-build/install.out" 2>&1 || die "liblzma install failed"
cd "$HERE"
echo "liblzma: $(wc -c < "$LIBS/lib/liblzma.a" | tr -d ' ') bytes"

# SQLite: the amalgamation (one C file), compiled directly. On __wasi__ sqlite3.c itself sets
# SQLITE_WASI, THREADSAFE=0, OMIT_LOAD_EXTENSION, no mmap or WAL shared memory, and the
# unix-dotfile locking (a lock directory beside the database); they are named again here so the build says what it is. The ENABLE_ options are
# the feature set of the native host Python's SQLite (python-build-standalone), so results compare.
tar -xzf "$(pinned sqlite-autoconf-3540100.tar.gz)" -C "$B"
mkdir -p "$B/sqlite-build"
SQLITE_OPTS="-DSQLITE_THREADSAFE=0 -DSQLITE_OMIT_LOAD_EXTENSION -DSQLITE_MAX_MMAP_SIZE=0 \
  ${SQLITE_EXTRA:-} \
  -DSQLITE_ENABLE_FTS3 -DSQLITE_ENABLE_FTS3_PARENTHESIS -DSQLITE_ENABLE_FTS4 -DSQLITE_ENABLE_FTS5 \
  -DSQLITE_ENABLE_RTREE -DSQLITE_ENABLE_GEOPOLY -DSQLITE_ENABLE_MATH_FUNCTIONS \
  -DSQLITE_ENABLE_DBSTAT_VTAB -DSQLITE_ENABLE_PERCENTILE"
$CC -O2 $SQLITE_OPTS -c "$B/sqlite-autoconf-3540100/sqlite3.c" -o "$B/sqlite-build/sqlite3.o"
"$AR" rcD "$LIBS/lib/libsqlite3.a" "$B/sqlite-build/sqlite3.o"
cp "$B/sqlite-autoconf-3540100/sqlite3.h" "$B/sqlite-autoconf-3540100/sqlite3ext.h" "$LIBS/include/"
echo "sqlite: $(wc -c < "$LIBS/lib/libsqlite3.a" | tr -d ' ') bytes"
echo "stdlib libs: bz2 $(wc -c < "$LIBS/lib/libbz2.a" | tr -d ' '), lzma $(wc -c < "$LIBS/lib/liblzma.a" | tr -d ' '), sqlite3 $(wc -c < "$LIBS/lib/libsqlite3.a" | tr -d ' ') bytes"
