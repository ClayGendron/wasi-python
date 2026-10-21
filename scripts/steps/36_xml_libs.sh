#!/bin/sh
# Step 36: lxml's C libraries as static archives for wasm32-wasip1 under build/xml-libs/:
# libxml2 2.15.4 (with its one carried patch: files without dup() on WASI) and
# libxslt 1.1.45 with libexslt. Step 35's pattern: each is unpacked from its pinned tarball,
# patched, and built outside its tree by its own configure (an autotools VPATH build), so the tree
# stays its tarball plus its recorded patches; every tool runs under `clean`, an empty
# environment but for PATH and LC_ALL, with the toolchain's clang over the host-neutral sysroot.
#
# libxml2: no threads (one guest thread), no modules (no dlopen), no zlib (lxml compresses through
# Python's gzip; the decompression branch would call dup a third time), Schematron on (as lxml's
# wheels have it), iconv left at its default, which finds wasi-libc's (musl's; not GNU libiconv).
# -DLIBXML_STATIC compiles out libxml2's one destructor, so __wasm_call_ctors gains nothing. The
# default catalogs are native Linux's paths: configure would build them from --prefix, a folder of
# this checkout, and compile it into the binary. configure requires a pkg-config: it is the pinned
# pkgconf (step 10), with an empty search path, so no .pc file can answer; nothing is asked
# of it with zlib, ICU and libgcrypt off and libxslt given libxml2's flags.
set -eu
. "$(dirname "$0")/common.sh"
clean() { env -i PATH="$PATH" LC_ALL=C "$@"; }  # PATH may hold spaces

CC="$SDK/bin/clang --target=wasm32-wasip1"
AR="$SDK/bin/llvm-ar"
RANLIB="$SDK/bin/llvm-ranlib"
PREFIX="$B/xml-libs"
NOPC="$B/no-pkg-config"
[ -x "$PKGCONF" ] || die "no pinned pkgconf at $PKGCONF: run step 10"
MAP="-ffile-prefix-map=$HERE=/wasi-python-build"
CATALOGS="-DXML_XML_DEFAULT_CATALOG='\"file:///etc/xml/catalog\"' -DXML_SGML_DEFAULT_CATALOG='\"file:///etc/sgml/catalog\"'"
XML2_TGZ=$(pinned libxml2-2.15.4.tar.xz)
XSLT_TGZ=$(pinned libxslt-1.1.45.tar.xz)
remove "$B/libxml2-2.15.4" "$B/libxslt-1.1.45" "$B/libxml2-build" "$B/libxslt-build" "$PREFIX" "$NOPC"
mkdir -p "$PREFIX" "$NOPC" "$B/libxml2-build" "$B/libxslt-build"
for archive in "$XML2_TGZ" "$XSLT_TGZ"; do
  tar -xJf "$archive" -C "$B"
done
for top in libxml2-2.15.4 libxslt-1.1.45; do
  [ -d "$B/$top" ] || die "a pinned tarball did not unpack to build/$top"
  patch_tree "$B/$top"
done

cd "$B/libxml2-build"
clean CC="$CC" AR="$AR" RANLIB="$RANLIB" PKG_CONFIG="$PKGCONF" PKG_CONFIG_LIBDIR="$NOPC" PKG_CONFIG_PATH= \
  CFLAGS="-O2 -DNDEBUG -DLIBXML_STATIC $CATALOGS $MAP" \
  "$B/libxml2-2.15.4/configure" --host=wasm32-unknown-wasip1 --prefix="$PREFIX" \
  --disable-shared --enable-static --without-python --without-threads --without-modules \
  --without-zlib --with-schematron > configure.out 2>&1 \
  || { tail -n 20 config.log; die "libxml2 configure failed (build/libxml2-build/config.log)"; }
clean make -j8 libxml2.la > make.out 2>&1 \
  || { tail -n 20 make.out; die "libxml2 make failed (build/libxml2-build/make.out)"; }
clean make install-libLTLIBRARIES install-data > install.out 2>&1 \
  || { tail -n 20 install.out; die "libxml2 install failed (build/libxml2-build/install.out)"; }
[ -s "$PREFIX/lib/libxml2.a" ] || die "step 36 made no libxml2.a"

cd "$B/libxslt-build"
clean CC="$CC" AR="$AR" RANLIB="$RANLIB" PKG_CONFIG="$PKGCONF" PKG_CONFIG_LIBDIR="$NOPC" PKG_CONFIG_PATH= \
  CFLAGS="-O2 -DNDEBUG -DLIBXSLT_STATIC -DLIBEXSLT_STATIC $MAP" \
  LIBXML_CFLAGS="-I$PREFIX/include/libxml2" LIBXML_LIBS="-L$PREFIX/lib -lxml2" \
  "$B/libxslt-1.1.45/configure" --host=wasm32-unknown-wasip1 --prefix="$PREFIX" \
  --disable-shared --enable-static --without-python --without-crypto > configure.out 2>&1 \
  || { tail -n 20 config.log; die "libxslt configure failed (build/libxslt-build/config.log)"; }
for dir in libxslt libexslt; do
  clean make -j8 -C "$dir" > "make-$dir.out" 2>&1 \
    || { tail -n 20 "make-$dir.out"; die "libxslt make in $dir failed (build/libxslt-build/make-$dir.out)"; }
  clean make -C "$dir" install > "install-$dir.out" 2>&1 \
    || { tail -n 20 "install-$dir.out"; die "libxslt install in $dir failed"; }
done
cd "$HERE"

for lib in libxml2.a libxslt.a libexslt.a; do
  [ -s "$PREFIX/lib/$lib" ] || die "step 36 made no $lib"
  echo "$lib $(wc -c < "$PREFIX/lib/$lib" | tr -d ' ') bytes, sha256 $(shasum -a 256 "$PREFIX/lib/$lib" | cut -d' ' -f1)"
done
size() { wc -c < "$PREFIX/lib/$1" | tr -d ' '; }
echo "xml libs: libxml2 $(size libxml2.a), libxslt $(size libxslt.a), libexslt $(size libexslt.a) bytes"
