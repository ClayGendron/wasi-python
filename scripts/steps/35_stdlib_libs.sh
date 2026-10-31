#!/bin/sh
# Step 35: the C libraries behind four stdlib modules CPython's WASI build lacks, as static
# archives for wasm32-wasip1 under build/stdlib-libs/: bzip2 1.0.8 (_bz2), liblzma from xz 5.8.4
# (_lzma), SQLite 3.54.1 (_sqlite3) and libzstd from zstd 1.5.7 (_zstd). Each is unpacked from its
# pinned tarball and compiled outside its source tree, so the tree stays byte-identical to the
# tarball.
# Every option is written here, and every tool (clang, llvm-ar, xz's configure and make) runs in an
# empty environment but for PATH and LC_ALL, through `clean`: autoconf reads cache variables
# (`*_cv_*`) and clang reads CCC_OVERRIDE_OPTIONS, CPATH and more from the environment, so none can
# change the archives. The compiler is the toolchain's clang over the host-neutral sysroot step 10
# put in place, so every build host makes the same objects. Step 60 links them in as builtins.
set -eu
. "$(dirname "$0")/common.sh"
clean() { env -i PATH="$PATH" LC_ALL=C "$@"; }  # PATH may hold spaces

CC="$SDK/bin/clang --target=wasm32-wasip1"
AR="$SDK/bin/llvm-ar"
RANLIB="$SDK/bin/llvm-ranlib"
LIBDIR="$B/stdlib-libs"
BZIP2_TGZ=$(pinned bzip2-1.0.8.tar.gz)
XZ_TGZ=$(pinned xz-5.8.4.tar.gz)
SQLITE_TGZ=$(pinned sqlite-autoconf-3540100.tar.gz)
ZSTD_TGZ=$(pinned zstd-1.5.7.tar.gz)
remove "$B/bzip2-1.0.8" "$B/xz-5.8.4" "$B/sqlite-autoconf-3540100" "$B/zstd-1.5.7" \
  "$B/bzip2-build" "$B/xz-build" "$B/sqlite-build" "$B/zstd-build" "$LIBDIR"
mkdir -p "$LIBDIR/include" "$LIBDIR/lib"

# bzip2: its Makefile builds inside the source tree, so the seven files of its `libbz2.a` target
# are compiled here with the Makefile's own flags, less -g.
tar -xzf "$BZIP2_TGZ" -C "$B"
patch_tree "$B/bzip2-1.0.8"
mkdir -p "$B/bzip2-build"
BZ_OBJS=""
for f in blocksort huffman crctable randtable compress decompress bzlib; do
  clean $CC -O2 -D_FILE_OFFSET_BITS=64 -c "$B/bzip2-1.0.8/$f.c" -o "$B/bzip2-build/$f.o"
  BZ_OBJS="$BZ_OBJS $B/bzip2-build/$f.o"
done
clean "$AR" rcD "$LIBDIR/lib/libbz2.a" $BZ_OBJS
cp "$B/bzip2-1.0.8/bzlib.h" "$LIBDIR/include/"
[ -s "$LIBDIR/lib/libbz2.a" ] || die "no libbz2.a"

# liblzma: xz's own configure, run from a separate build directory (an autotools VPATH build).
# Only the library: no tools, scripts, docs or translations, and no threads on wasm32-wasip1.
tar -xzf "$XZ_TGZ" -C "$B"
patch_tree "$B/xz-5.8.4"
mkdir -p "$B/xz-build"
cd "$B/xz-build"
clean CC="$CC" AR="$AR" RANLIB="$RANLIB" CFLAGS="-O2" "$B/xz-5.8.4/configure" \
  --host=wasm32-unknown-wasip1 --prefix="$LIBDIR" --disable-shared --enable-static \
  --disable-threads --disable-xz --disable-xzdec --disable-lzmadec --disable-lzmainfo \
  --disable-lzma-links --disable-scripts --disable-doc --disable-nls --disable-rpath \
  --disable-sandbox > "$B/xz-build/configure.out" 2>&1 \
  || { tail -n 20 "$B/xz-build/config.log"; die "xz configure failed (build/xz-build/config.log)"; }
clean make -j8 -C src/liblzma > "$B/xz-build/make.out" 2>&1 \
  || { tail -n 20 "$B/xz-build/make.out"; die "liblzma make failed (build/xz-build/make.out)"; }
clean make -C src/liblzma install > "$B/xz-build/install.out" 2>&1 \
  || { tail -n 20 "$B/xz-build/install.out"; die "liblzma install failed"; }
cd "$HERE"
[ -s "$LIBDIR/lib/liblzma.a" ] || die "no liblzma.a"

# SQLite: the amalgamation, one C file, compiled directly. On __wasi__ sqlite3.c itself sets
# THREADSAFE=0 and OMIT_LOAD_EXTENSION, leaves out mmap and WAL's shared memory, and locks with a
# directory beside the database; the first three are named again so the command says what the
# build is. The ENABLE_ options are the native host Python's SQLite feature set
# (python-build-standalone 3.15.2's `PRAGMA compile_options`, 3.15.0's the same), so results
# compare with native.
tar -xzf "$SQLITE_TGZ" -C "$B"
patch_tree "$B/sqlite-autoconf-3540100"
mkdir -p "$B/sqlite-build"
SQLITE_OPTS="-DSQLITE_THREADSAFE=0 -DSQLITE_OMIT_LOAD_EXTENSION -DSQLITE_MAX_MMAP_SIZE=0
  -DSQLITE_ENABLE_FTS3 -DSQLITE_ENABLE_FTS3_PARENTHESIS -DSQLITE_ENABLE_FTS4
  -DSQLITE_ENABLE_FTS5 -DSQLITE_ENABLE_RTREE -DSQLITE_ENABLE_GEOPOLY
  -DSQLITE_ENABLE_MATH_FUNCTIONS -DSQLITE_ENABLE_DBSTAT_VTAB -DSQLITE_ENABLE_PERCENTILE"
clean $CC -O2 $SQLITE_OPTS -c "$B/sqlite-autoconf-3540100/sqlite3.c" -o "$B/sqlite-build/sqlite3.o"
clean "$AR" rcD "$LIBDIR/lib/libsqlite3.a" "$B/sqlite-build/sqlite3.o"
cp "$B/sqlite-autoconf-3540100/sqlite3.h" "$B/sqlite-autoconf-3540100/sqlite3ext.h" "$LIBDIR/include/"
[ -s "$LIBDIR/lib/libsqlite3.a" ] || die "no libsqlite3.a"

# libzstd: every C file of the library's four parts, compiled directly in sorted order with the
# include folders zstd's own build gives them, so no Makefile or CMake runs. The parts are the
# common code, the compressor, the decompressor and the dictionary builder, which
# compression.zstd's train_dict and finalize_dict call. The one assembly file, an x86-64 Huffman
# decoder, is not listed, and ZSTD_DISABLE_ASM keeps the C decoder in its place. No
# ZSTD_MULTITHREAD: the guest has no threads, so a compressor asked for workers refuses. No legacy
# decoders: frames from before zstd 0.8 (2016) do not decode. XXH_NAMESPACE, as zstd's Makefile
# sets it, keeps its xxHash's names from meeting another copy in the link. The dictionary builder
# calls clock() for its progress lines; WASI has no process clock, so it is the emulated one, as
# qhull's is. zstd's error macros can name __FILE__, so the build folder is mapped to a fixed name.
# The file count is pinned: a release that adds or drops a file stops here, named.
tar -xzf "$ZSTD_TGZ" -C "$B"
patch_tree "$B/zstd-1.5.7"
mkdir -p "$B/zstd-build"
ZSTD_LIB="$B/zstd-1.5.7/lib"
ZSTD_FILES=$(cd "$ZSTD_LIB" && ls common/*.c compress/*.c decompress/*.c dictBuilder/*.c | sort)
n=$(printf '%s\n' $ZSTD_FILES | wc -l | tr -d ' ')
[ "$n" -eq 30 ] || die "zstd 1.5.7's lib/ has $n C files in its four parts, not 30"
dup=$(printf '%s\n' $ZSTD_FILES | sed 's#.*/##' | sort | uniq -d)
[ -z "$dup" ] || die "two zstd files share an object name: $dup"
ZSTD_OBJS=""
for f in $ZSTD_FILES; do
  o="$B/zstd-build/$(basename "$f" .c).o"
  clean $CC -O2 -ffile-prefix-map="$HERE=/wasi-python-build" -DZSTD_DISABLE_ASM \
    -D_WASI_EMULATED_PROCESS_CLOCKS -DXXH_NAMESPACE=ZSTD_ -DZSTD_LEGACY_SUPPORT=0 \
    -I"$ZSTD_LIB" -I"$ZSTD_LIB/common" -c "$ZSTD_LIB/$f" -o "$o"
  ZSTD_OBJS="$ZSTD_OBJS $o"
done
clean "$AR" rcD "$LIBDIR/lib/libzstd.a" $ZSTD_OBJS
cp "$ZSTD_LIB/zstd.h" "$ZSTD_LIB/zdict.h" "$ZSTD_LIB/zstd_errors.h" "$LIBDIR/include/"
[ -s "$LIBDIR/lib/libzstd.a" ] || die "no libzstd.a"

size() { wc -c < "$LIBDIR/lib/$1" | tr -d ' '; }
echo "stdlib libs: bz2 $(size libbz2.a), lzma $(size liblzma.a), sqlite3 $(size libsqlite3.a), zstd $(size libzstd.a) bytes"
