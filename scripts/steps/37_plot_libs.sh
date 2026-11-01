#!/bin/sh
# Step 37: matplotlib's C libraries as static archives for wasm32-wasip1, installed under
# build/plot-libs/: FreeType 2.14.3, HarfBuzz 14.1.0, SheenBidi 3.0.0 and libraqm 0.10.5, at
# matplotlib 3.11.2's own wrap versions (native pixel parity), each with meson and the cross file
# recipes/wasi-plot-libs.cross; qhull 8.0.2's libqhull_r, the one qhull linked, by matplotlib's
# _qhull and scipy's spatial._qhull, with its qhull_r.pc from recipes/qhull_r.pc.in, which scipy's
# configure asks for; and libjpeg-turbo 3.2.0's libjpeg, Pillow's JPEG codec, beside zlib. Each is
# unpacked from its pinned tarball into build/<top>, patched (qhull's format strings) and built
# outside its tree, so the tree stays its tarball plus its recorded patches. libraqm finds the
# other three through the pinned pkgconf; FreeType is built against step 30's zlib, so one zlib is
# linked.
set -eu
. "$(dirname "$0")/common.sh"

PREFIX="$B/plot-libs"
[ -s "$B/zlib-wasi/lib/libz.a" ] || die "build/zlib-wasi has no libz.a: run step 30"
[ -x "$PKGCONF" ] || die "no pinned pkgconf at $PKGCONF: run step 10"
FT=$(pinned freetype-2.14.3.tar.xz)
HB=$(pinned harfbuzz-14.1.0.tar.xz)
SB=$(pinned SheenBidi-3.0.0.tar.gz)
RQ=$(pinned libraqm-0.10.5.tar.gz)
QH=$(pinned qhull-8.0.2.tar.gz)
LJ_TGZ=$(pinned libjpeg-turbo-3.2.0.tar.gz)
remove "$B/freetype-2.14.3" "$B/harfbuzz-14.1.0" "$B/SheenBidi-3.0.0" "$B/libraqm-0.10.5" \
  "$B/qhull-8.0.2" "$B/freetype-build" "$B/harfbuzz-build" "$B/sheenbidi-build" "$B/libraqm-build" \
  "$B/qhull-build" "$B/libjpeg-turbo-3.2.0" "$B/libjpeg-build" "$PREFIX"
mkdir -p "$PREFIX/lib/pkgconfig" "$PREFIX/include"
for archive in "$FT" "$HB" "$SB" "$RQ" "$QH" "$LJ_TGZ"; do
  tar -xf "$archive" -C "$B"
done
for top in freetype-2.14.3 harfbuzz-14.1.0 SheenBidi-3.0.0 libraqm-0.10.5 qhull-8.0.2 \
  libjpeg-turbo-3.2.0; do
  [ -d "$B/$top" ] || die "a pinned tarball did not unpack to build/$top"
  patch_tree "$B/$top"
done
sed "s#@ROOT@#$HERE#g; s#@SDK@#$WASI_SDK_DIR#g" "$HERE/recipes/wasi-plot-libs.cross" > "$B/wasi-plot-libs.cross"

# One meson build: source tree, build folder, then its options. Static, release, no LTO. Meson
# never downloads: $wrap, when a call sets it, names a stricter wrap mode than MESON_WRAP.
build() {
  src=$1 dir=$2
  shift 2
  meson setup "$dir" "$src" ${wrap:-$MESON_WRAP} --cross-file "$B/wasi-plot-libs.cross" \
    --buildtype=release --prefix="$PREFIX" --libdir=lib -Ddefault_library=static -Db_lto=false "$@"
  ninja -C "$dir"
  meson install -C "$dir" --quiet
}
unset wrap  # only the call that needs a stricter mode sets it

# FreeType: its BDF and PCF drivers are built (their notices ship); gzip through step 30's zlib.
build "$B/freetype-2.14.3" "$B/freetype-build" -Dzlib=system -Dpng=disabled -Dharfbuzz=disabled \
  -Dbrotli=disabled -Dbzip2=disabled -Dmmap=disabled -Dtests=disabled
# HarfBuzz: matplotlib's own option list (extern/meson.build), shaping with FreeType only.
# nofallback is HarfBuzz's own project default: it refuses every fallback, a local subproject
# folder too, so it is stricter than nodownload, which would allow one.
wrap=--wrap-mode=nofallback
build "$B/harfbuzz-14.1.0" "$B/harfbuzz-build" -Dbenchmark=disabled -Dcairo=disabled \
  -Dchafa=disabled -Dcoretext=disabled -Ddirectwrite=disabled -Ddocs=disabled -Ddoc_tests=false \
  -Dfontations=disabled -Dfreetype=enabled -Dgdi=disabled -Dglib=disabled -Dgobject=disabled \
  -Dgpu=disabled -Dgpu_demo=disabled -Dharfrust=disabled -Dicu=disabled -Dintrospection=disabled \
  -Dkbts=disabled -Dpng=disabled -Draster=disabled -Dsubset=disabled -Dtests=disabled \
  -Dutilities=disabled -Dvector=disabled -Dwasm=disabled -Dzlib=disabled
unset wrap
build "$B/SheenBidi-3.0.0" "$B/sheenbidi-build"
build "$B/libraqm-0.10.5" "$B/libraqm-build" -Dsheenbidi=true -Dtests=false

# qhull: libqhull_r's 17 files, as matplotlib's own qhull wrap lists them, compiled directly in
# sorted order; qh_errexit longjmps (setjmp through exception handling, as for C in the cross
# file), and WASI has no process clock, so clock() is the emulated one.
mkdir -p "$B/qhull-build" "$PREFIX/include/libqhull_r"
QH_OBJS=""
for f in $(cd "$B/qhull-8.0.2/src/libqhull_r" && ls geom2_r.c geom_r.c global_r.c io_r.c libqhull_r.c \
  mem_r.c merge_r.c poly2_r.c poly_r.c qset_r.c random_r.c rboxlib_r.c stat_r.c usermem_r.c \
  userprintf_rbox_r.c userprintf_r.c user_r.c | sort); do
  "$SDK/bin/clang" --target=wasm32-wasip1 -O2 -ffile-prefix-map="$HERE=/wasi-python-build" \
    -fwasm-exceptions -mllvm -wasm-enable-sjlj -mllvm -wasm-use-legacy-eh=false \
    -D_WASI_EMULATED_PROCESS_CLOCKS -I"$B/qhull-8.0.2/src" -c "$B/qhull-8.0.2/src/libqhull_r/$f" \
    -o "$B/qhull-build/${f%.c}.o"
  QH_OBJS="$QH_OBJS $B/qhull-build/${f%.c}.o"
done
"$SDK/bin/llvm-ar" rcD "$PREFIX/lib/libqhull_r.a" $QH_OBJS
cp "$B/qhull-8.0.2/src/libqhull_r/"*.h "$PREFIX/include/libqhull_r/"
# Its .pc: scipy's dependency('qhull_r') and matplotlib's
# first try both read it; its paths are relative to its own folder.
cp "$HERE/recipes/qhull_r.pc.in" "$PREFIX/lib/pkgconfig/qhull_r.pc"

# libjpeg-turbo: the libjpeg API library alone, without CMake. The list is the one
# set(JPEG_SOURCES ...) statement of its CMakeLists.txt, read by the host Python (never run), and
# the three arithmetic-coding files its default options add; 101 files, the 12- and 16-bit wrapper
# copies among them, or the step stops. No SIMD (none is written for wasm), no TurboJPEG, tools or
# tests. The three headers CMake would configure are recipe files, each held here to every line
# of its template that has no placeholder, so a later pin cannot keep a stale copy. The error
# handler Pillow installs longjmps, so the code is compiled with setjmp through exception handling,
# as for C in the cross file.
LJ="$B/libjpeg-turbo-3.2.0"
LJH="$HERE/recipes/libjpeg-turbo"
mkdir -p "$B/libjpeg-build"
"$HOSTPY" - "$LJ" "$LJH" > "$B/libjpeg-build/sources.txt" << 'EOF_LJ'
import os, re, sys
tree, recipes = sys.argv[1], sys.argv[2]
text = open(os.path.join(tree, "CMakeLists.txt"), encoding="utf-8").read()
found = re.findall(r"^set\(JPEG_SOURCES\s([^)]*)\)", text, re.M)
if len(found) != 1:
    sys.exit(f"ERROR: CMakeLists.txt: {len(found)} set(JPEG_SOURCES ...) statements, not 1")
files = found[0].split() + ["src/jaricom.c", "src/jcarith.c", "src/jdarith.c"]
if len(files) != 101:
    sys.exit(f"ERROR: libjpeg-turbo: {len(files)} source files, not the 101 this recipe was made for")
if len({os.path.basename(f) for f in files}) != len(files):
    sys.exit("ERROR: libjpeg-turbo: two source files share a basename")
for f in files:
    if not os.path.isfile(os.path.join(tree, f)):
        sys.exit(f"ERROR: libjpeg-turbo: {f} is not in the tarball")
placeholder = re.compile(r"@[A-Za-z_]+@")
for name in ("jconfig.h", "jconfigint.h", "jversion.h"):
    template = open(os.path.join(tree, "src", name + ".in"), encoding="utf-8").read().splitlines()
    ours = set(open(os.path.join(recipes, name), encoding="utf-8").read().splitlines())
    for line in template:
        if placeholder.search(line) or line.startswith("#cmakedefine"):
            continue
        if line not in ours:
            sys.exit(f"ERROR: recipes/libjpeg-turbo/{name} lacks a line of its template: {line!r}")
print("\n".join(files))
EOF_LJ
LJ_OBJS=""
while IFS= read -r src; do
  obj="$B/libjpeg-build/$(basename "${src%.c}").o"
  "$SDK/bin/clang" --target=wasm32-wasip1 -O2 -DNDEBUG -ffile-prefix-map="$HERE=/wasi-python-build" \
    -fwasm-exceptions -mllvm -wasm-enable-sjlj -mllvm -wasm-use-legacy-eh=false \
    -I"$LJH" -I"$LJ/src" -c "$LJ/$src" -o "$obj"
  LJ_OBJS="$LJ_OBJS $obj"
done < "$B/libjpeg-build/sources.txt"
"$SDK/bin/llvm-ar" rcD "$PREFIX/lib/libjpeg.a" $LJ_OBJS
cp "$LJ/src/jpeglib.h" "$LJ/src/jerror.h" "$LJ/src/jmorecfg.h" "$LJH/jconfig.h" "$PREFIX/include/"

for lib in libfreetype.a libharfbuzz.a libSheenBidi.a libraqm.a libqhull_r.a libjpeg.a; do
  [ -s "$PREFIX/lib/$lib" ] || die "step 37 made no $lib"
done
size() { wc -c < "$PREFIX/lib/$1" | tr -d ' '; }
echo "plot libs: freetype $(size libfreetype.a), harfbuzz $(size libharfbuzz.a), sheenbidi $(size libSheenBidi.a), raqm $(size libraqm.a), qhull $(size libqhull_r.a), jpeg $(size libjpeg.a) bytes"
