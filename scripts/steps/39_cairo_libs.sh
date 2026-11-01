#!/bin/sh
# Step 39: cairo's C libraries as static archives for wasm32-wasip1, installed under
# build/cairo-libs/: pixman 0.46.4, libpng 1.6.59 and cairo 1.18.6, the renderer cairocffi binds
# (step 56). Each is unpacked from its pinned tarball into build/<top> and built outside its tree,
# so the tree stays its tarball. Meson runs with every automatic feature off, so a library or
# program a build host gains later cannot switch one on; only the features named here are built.
#
# pixman: no SIMD, tests or demos. Its meson finds that the toolchain links static constructors
# and turns on one that picks pixman's implementation and reads PIXMAN_DISABLE before Python
# starts. Both lines are deleted from the generated configuration header in the build folder (not
# the tree), so pixman picks its implementation on first use instead and the binary's list of
# constructors does not change; the step stops if either line is absent before or present after.
# libpng: its fifteen library files compiled one by one with the tarball's prebuilt pnglibconf.h,
# every hardware path off, against step 30's zlib; its .pc from recipes/libpng16.pc.in.
# cairo: FreeType (step 37's), PNG and zlib on, fontconfig and every window system off; only
# src/libcairo.a is built, since cairo's script tools need tmpfile and setjmp the guest lacks.
set -eu
. "$(dirname "$0")/common.sh"

PREFIX="$B/cairo-libs"
[ -s "$B/zlib-wasi/lib/libz.a" ] || die "build/zlib-wasi has no libz.a: run step 30"
[ -s "$B/plot-libs/lib/libfreetype.a" ] || die "build/plot-libs has no libfreetype.a: run step 37"
[ -x "$PKGCONF" ] || die "no pinned pkgconf at $PKGCONF: run step 10"
PX=$(pinned pixman-0.46.4.tar.xz)
PNG=$(pinned libpng-1.6.59.tar.xz)
CR=$(pinned cairo-1.18.6.tar.xz)
remove "$B/pixman-0.46.4" "$B/libpng-1.6.59" "$B/cairo-1.18.6" "$B/pixman-build" "$B/libpng-build" \
  "$B/cairo-build" "$PREFIX"
mkdir -p "$PREFIX/lib/pkgconfig" "$PREFIX/include"
for archive in "$PX" "$PNG" "$CR"; do
  tar -xf "$archive" -C "$B"
done
for top in pixman-0.46.4 libpng-1.6.59 cairo-1.18.6; do
  [ -d "$B/$top" ] || die "a pinned tarball did not unpack to build/$top"
  patch_tree "$B/$top"
done
sed "s#@ROOT@#$HERE#g; s#@SDK@#$WASI_SDK_DIR#g" "$HERE/recipes/wasi-cairo.cross" > "$B/wasi-cairo.cross"

setup() { # source tree, build folder, then its options
  src=$1 dir=$2
  shift 2
  meson setup "$dir" "$src" $MESON_WRAP --cross-file "$B/wasi-cairo.cross" \
    --buildtype=release --prefix="$PREFIX" --libdir=lib -Ddefault_library=static -Db_lto=false \
    -Dauto_features=disabled "$@"
}

# pixman, with its two constructor lines taken out of the generated header.
setup "$B/pixman-0.46.4" "$B/pixman-build" -Dtests=disabled -Ddemos=disabled -Dtimers=false
PXCONF="$B/pixman-build/pixman/pixman-config.h"
for name in TOOLCHAIN_SUPPORTS_ATTRIBUTE_CONSTRUCTOR TOOLCHAIN_SUPPORTS_ATTRIBUTE_DESTRUCTOR; do
  grep -q "^#define $name 1\$" "$PXCONF" || die "pixman's $PXCONF has no '#define $name 1' to delete"
done
sed -e '/^#define TOOLCHAIN_SUPPORTS_ATTRIBUTE_CONSTRUCTOR 1$/d' \
  -e '/^#define TOOLCHAIN_SUPPORTS_ATTRIBUTE_DESTRUCTOR 1$/d' "$PXCONF" > "$PXCONF.new"
mv "$PXCONF.new" "$PXCONF"
! grep -Eq 'TOOLCHAIN_SUPPORTS_ATTRIBUTE_(CON|DE)STRUCTOR' "$PXCONF" \
  || die "pixman's $PXCONF still defines a constructor line"
echo "pixman: its constructor and destructor lines deleted from build/pixman-build/pixman/pixman-config.h"
ninja -C "$B/pixman-build"
meson install -C "$B/pixman-build" --quiet

# libpng: the library's own fifteen files, in sorted order.
P="$B/libpng-1.6.59"
mkdir -p "$B/libpng-build"
cp "$P/scripts/pnglibconf.h.prebuilt" "$B/libpng-build/pnglibconf.h"
PNG_OFF="-DPNG_ARM_NEON_OPT=0 -DPNG_INTEL_SSE_OPT=0 -DPNG_MIPS_MSA_OPT=0 -DPNG_MIPS_MMI_OPT=0"
PNG_OFF="$PNG_OFF -DPNG_POWERPC_VSX_OPT=0 -DPNG_LOONGARCH_LSX_OPT=0 -DPNG_RISCV_RVV_OPT=0"
PNG_OBJS=""
for f in $(printf '%s\n' png.c pngerror.c pngget.c pngmem.c pngpread.c pngread.c pngrio.c pngrtran.c \
  pngrutil.c pngset.c pngtrans.c pngwio.c pngwrite.c pngwtran.c pngwutil.c | sort); do
  "$SDK/bin/clang" --target=wasm32-wasip1 -O2 -DNDEBUG -ffile-prefix-map="$HERE=/wasi-python-build" \
    -fwasm-exceptions -mllvm -wasm-enable-sjlj -mllvm -wasm-use-legacy-eh=false $PNG_OFF \
    -I"$B/libpng-build" -I"$P" -I"$B/zlib-wasi/include" -c "$P/$f" -o "$B/libpng-build/${f%.c}.o"
  PNG_OBJS="$PNG_OBJS $B/libpng-build/${f%.c}.o"
done
"$SDK/bin/llvm-ar" rcD "$PREFIX/lib/libpng16.a" $PNG_OBJS
mkdir -p "$PREFIX/include/libpng16"
cp "$P/png.h" "$P/pngconf.h" "$B/libpng-build/pnglibconf.h" "$PREFIX/include/libpng16/"
cp "$HERE/recipes/libpng16.pc.in" "$PREFIX/lib/pkgconfig/libpng16.pc"
cp "$HERE/recipes/libpng16.pc.in" "$PREFIX/lib/pkgconfig/libpng.pc"

# cairo: the library alone, and its public headers for the features built.
setup "$B/cairo-1.18.6" "$B/cairo-build" -Dfreetype=enabled -Dpng=enabled -Dzlib=enabled \
  -Dfontconfig=disabled -Dtests=disabled -Dgtk_doc=false
ninja -C "$B/cairo-build" src/libcairo.a
cp "$B/cairo-build/src/libcairo.a" "$PREFIX/lib/libcairo.a"
mkdir -p "$PREFIX/include/cairo"
for h in cairo.h cairo-version.h cairo-deprecated.h cairo-pdf.h cairo-ps.h cairo-svg.h cairo-ft.h \
  cairo-script.h; do
  cp "$B/cairo-1.18.6/src/$h" "$PREFIX/include/cairo/"
done
cp "$B/cairo-build/src/cairo-features.h" "$PREFIX/include/cairo/"
# The surfaces and fonts cairocffi's declarations reach, and none of fontconfig's.
for f in FT_FONT PDF_SURFACE PNG_FUNCTIONS PS_SURFACE SVG_SURFACE SCRIPT_SURFACE; do
  grep -q "^#define CAIRO_HAS_$f 1\$" "$PREFIX/include/cairo/cairo-features.h" \
    || die "cairo was configured without CAIRO_HAS_$f"
done
! grep -q 'CAIRO_HAS_FC_FONT' "$PREFIX/include/cairo/cairo-features.h" \
  || die "cairo was configured with fontconfig"

for lib in libpixman-1.a libpng16.a libcairo.a; do
  [ -s "$PREFIX/lib/$lib" ] || die "step 39 made no $lib"
done
size() { wc -c < "$PREFIX/lib/$1" | tr -d ' '; }
echo "cairo libs: pixman $(size libpixman-1.a), libpng $(size libpng16.a), cairo $(size libcairo.a) bytes"
