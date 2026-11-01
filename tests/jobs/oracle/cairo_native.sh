#!/bin/sh
# The native side of the svg_to_png golden: cairo, pixman, libpng, FreeType and zlib built for the
# build host from the same pinned tarballs and options the guest's steps 30, 37 and 39 use, by the
# host's own C compiler, with every SIMD path off and -ffp-contract=off (every wasm compile
# contracts nothing too); cairocffi's bindings written by the same recipes/cairo_build.py and
# compiled against them; and a folder for the oracle's Python holding them with the same Python
# packages the zip carries: cairocffi with its stand-in ffi.py, CairoSVG with its carried patch,
# tinycss2, cssselect2 and imageio. The oracle then runs the job on the same C and Python as the
# guest, and only the C library's maths (the host's libm against wasi-libc's) can differ.
# Not a build step: the artifact set does not depend on it, and build.sh never runs it. It lives
# beside the oracle because, like the oracle, it builds and runs pinned code natively.
#
#   sh tests/jobs/oracle/cairo_native.sh        (after steps 10, 39, 56 and 70)
#
# Everything lands under build/cairo-native/; the folder for the oracle is
# build/cairo-native/site/, which tests/harness/jobs.py puts first on the oracle's PYTHONPATH for
# this job. It prints the host compiler's version first.
set -eu
HERE=$(CDPATH= cd "$(dirname "$0")/../../.." && pwd -P)
D="$HERE/downloads"
B="$HERE/build"
T="$B/tools"
HOSTPY="$T/python/bin/python3"
. "$HERE/scripts/steps/remove.sh"
export PATH="$T/host-python:$T/pylib/bin:$PATH"
export PYTHONPATH="$T/pylib"
export PYTHONDONTWRITEBYTECODE=1
die() {
  echo "ERROR: $*" >&2
  exit 1
}
pinned() {
  [ -s "$D/$1" ] || die "downloads/$1 is missing: run scripts/00_download.sh"
  grep "  $1\$" "$D/SHA256SUMS" > "$B/.pin-check" || die "$1 is not pinned in downloads/SHA256SUMS"
  (cd "$D" && shasum -a 256 -c "$B/.pin-check" > /dev/null 2>&1) || die "downloads/$1 does not match its pin"
  rm -f "$B/.pin-check"
  printf '%s\n' "$D/$1"
}
[ -x "$HOSTPY" ] && [ -d "$T/pylib/mesonbuild" ] || die "build/tools is missing: run step 10"
[ -d "$B/cffi-host/cffi" ] || die "build/cffi-host is missing: run step 56"
[ -d "$B/pure-install/cairocffi" ] && [ -d "$B/pure-install/cairosvg" ] \
  || die "build/pure-install has no cairocffi or cairosvg: run step 70"

N="$B/cairo-native"
P="$N/prefix"
remove "$N"
mkdir -p "$N/src" "$P/lib/pkgconfig" "$P/include" "$N/site"
CC=${CC:-cc}
echo "host compiler: $("$CC" --version 2>&1 | head -n 1)"
FLAGS="-O2 -ffp-contract=off -fPIC"
for t in zlib-1.3.1.tar.gz freetype-2.14.3.tar.xz pixman-0.46.4.tar.xz libpng-1.6.59.tar.xz \
  cairo-1.18.6.tar.xz; do
  tar -xf "$(pinned "$t")" -C "$N/src"
done
for top in zlib-1.3.1 freetype-2.14.3 pixman-0.46.4 libpng-1.6.59 cairo-1.18.6; do
  sh "$HERE/scripts/steps/apply_patches.sh" "$N/src/$top" "$HERE/recipes/patches/$top" > /dev/null
done

# zlib, as step 30 configures it.
mkdir -p "$N/zlib-build"
(cd "$N/zlib-build" && CC="$CC" CFLAGS="$FLAGS" "$N/src/zlib-1.3.1/configure" --static --prefix="$P" \
  > "$N/zlib.log" 2>&1 && make -j8 libz.a >> "$N/zlib.log" 2>&1 && make install >> "$N/zlib.log" 2>&1) \
  || die "zlib did not build (build/cairo-native/zlib.log)"

# The meson builds: one native file, the host compiler with the same flags everywhere, and only the
# prefix's .pc files.
cat > "$N/native.ini" << EOF
[binaries]
c = '$CC'
pkg-config = '$T/pylib/pkgconf/.bin/pkgconf'
cmake = '$B/no-cmake'
ttx = '$B/no-ttx'

[properties]
pkg_config_libdir = ['$P/lib/pkgconfig']

[built-in options]
c_args = ['-ffp-contract=off']
EOF
build() { # name, source tree, then its options
  name=$1 src=$2
  shift 2
  meson setup "$N/$name-build" "$src" --wrap-mode=nofallback --native-file "$N/native.ini" \
    --buildtype=release --prefix="$P" --libdir=lib -Ddefault_library=static -Db_lto=false \
    -Db_staticpic=true "$@" > "$N/$name.log" 2>&1 || die "$name: meson setup failed (build/cairo-native/$name.log)"
}
# FreeType, with step 37's options.
build freetype "$N/src/freetype-2.14.3" -Dzlib=system -Dpng=disabled -Dharfbuzz=disabled \
  -Dbrotli=disabled -Dbzip2=disabled -Dmmap=disabled -Dtests=disabled
ninja -C "$N/freetype-build" >> "$N/freetype.log" 2>&1 && meson install -C "$N/freetype-build" --quiet \
  || die "freetype did not build (build/cairo-native/freetype.log)"
# pixman and cairo, with step 39's options; pixman's constructor lines deleted as there.
build pixman "$N/src/pixman-0.46.4" -Dauto_features=disabled -Dtests=disabled -Ddemos=disabled \
  -Dtimers=false
sed -e '/^#define TOOLCHAIN_SUPPORTS_ATTRIBUTE_CONSTRUCTOR 1$/d' \
  -e '/^#define TOOLCHAIN_SUPPORTS_ATTRIBUTE_DESTRUCTOR 1$/d' \
  "$N/pixman-build/pixman/pixman-config.h" > "$N/pixman-config.h"
mv "$N/pixman-config.h" "$N/pixman-build/pixman/pixman-config.h"
ninja -C "$N/pixman-build" >> "$N/pixman.log" 2>&1 && meson install -C "$N/pixman-build" --quiet \
  || die "pixman did not build (build/cairo-native/pixman.log)"
# libpng, file by file, as step 39 compiles it.
L="$N/src/libpng-1.6.59"
mkdir -p "$N/libpng-build" "$P/include/libpng16"
cp "$L/scripts/pnglibconf.h.prebuilt" "$N/libpng-build/pnglibconf.h"
OFF="-DPNG_ARM_NEON_OPT=0 -DPNG_INTEL_SSE_OPT=0 -DPNG_MIPS_MSA_OPT=0 -DPNG_MIPS_MMI_OPT=0"
OFF="$OFF -DPNG_POWERPC_VSX_OPT=0 -DPNG_LOONGARCH_LSX_OPT=0 -DPNG_RISCV_RVV_OPT=0"
objs=""
for f in png pngerror pngget pngmem pngpread pngread pngrio pngrtran pngrutil pngset pngtrans \
  pngwio pngwrite pngwtran pngwutil; do
  "$CC" $FLAGS -DNDEBUG $OFF -I"$N/libpng-build" -I"$L" -I"$P/include" -c "$L/$f.c" \
    -o "$N/libpng-build/$f.o" || die "libpng's $f.c did not compile"
  objs="$objs $N/libpng-build/$f.o"
done
ar rc "$P/lib/libpng16.a" $objs
ranlib "$P/lib/libpng16.a"
cp "$L/png.h" "$L/pngconf.h" "$N/libpng-build/pnglibconf.h" "$P/include/libpng16/"
cp "$HERE/recipes/libpng16.pc.in" "$P/lib/pkgconfig/libpng16.pc"
cp "$HERE/recipes/libpng16.pc.in" "$P/lib/pkgconfig/libpng.pc"
build cairo "$N/src/cairo-1.18.6" -Dauto_features=disabled -Dfreetype=enabled -Dpng=enabled \
  -Dzlib=enabled -Dfontconfig=disabled -Dtests=disabled -Dgtk_doc=false
ninja -C "$N/cairo-build" src/libcairo.a >> "$N/cairo.log" 2>&1 || die "cairo did not build (build/cairo-native/cairo.log)"
CI="$N/cairo-include"
mkdir -p "$CI"
cp "$N/src/cairo-1.18.6/src/"cairo*.h "$CI/"
cp "$N/cairo-build/src/cairo-features.h" "$CI/"
! grep -q CAIRO_HAS_FC_FONT "$CI/cairo-features.h" || die "the native cairo was configured with fontconfig"

# cairocffi's bindings, from the same generator, compiled as an extension of the host's Python.
PYTHONPATH="$B/cffi-host" "$HOSTPY" -s "$HERE/recipes/cairo_build.py" \
  "$B/cairocffi-1.7.1/cairocffi/constants.py" "$N/_cairocffi_api.c" > /dev/null
SUFFIX=$("$HOSTPY" -c 'import sysconfig; print(sysconfig.get_config_var("EXT_SUFFIX"))')
INCLUDE=$("$HOSTPY" -c 'import sysconfig; print(sysconfig.get_paths()["include"])')
case "$(uname -s)" in
  Darwin) SHARED="-bundle -undefined dynamic_lookup";;
  *) SHARED="-shared";;
esac
"$CC" $FLAGS -DNDEBUG $SHARED -I"$CI" -I"$P/include/freetype2" -I"$INCLUDE" "$N/_cairocffi_api.c" \
  "$N/cairo-build/src/libcairo.a" "$P/lib/libpixman-1.a" "$P/lib/libpng16.a" "$P/lib/libfreetype.a" \
  "$P/lib/libz.a" -lm -o "$N/site/_cairocffi_api$SUFFIX" || die "_cairocffi_api did not compile"

# The Python packages, as the zip carries them; cffi's backend from the host's pinned wheel.
cp "$B/cffi-host/"_cffi_backend*"$SUFFIX" "$N/site/"
cp -R "$B/pure-install/cairocffi" "$B/pure-install/cairosvg" "$N/site/"
for sdist in cairocffi-1.7.1 cairosvg-2.9.1; do
  name=$(sed -n 's/^Name: //p' "$B/$sdist/PKG-INFO" | head -n 1 | tr 'A-Z-' 'a-z_')
  mkdir -p "$N/site/$name-${sdist##*-}.dist-info"
  cp "$B/$sdist/PKG-INFO" "$N/site/$name-${sdist##*-}.dist-info/METADATA"
done
for wheel in tinycss2-1.5.1-py3-none-any.whl cssselect2-0.10.1-py3-none-any.whl \
  imageio-2.38.1-py3-none-any.whl; do
  "$HOSTPY" -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' \
    "$(pinned "$wheel")" "$N/site"
done
echo "native cairo: build/cairo-native/site holds _cairocffi_api$SUFFIX and the packages"
