#!/bin/sh
# Step 55: the plot packages for wasm32-wasip1 (spec 023): Pillow 13.0.0's _imaging, _imagingmath
# and _imagingmorph (zlib only) and kiwisolver 1.5.1's _cext, compiled directly from their source
# lists, and matplotlib 3.11.2 (with its carried patch) through meson and
# recipes/wasi-matplotlib.cross against step 37's libraries. Each extension module becomes a static
# archive beside a .deps file, as scripts/wasi-cc makes them, laid out at its import path under
# build/plot-modules/<package>/ for step 60; each package's Python files go under
# build/plot-install/ for step 70. Needs steps 10 (pkgconf), 20 (the cross Python), 30 (zlib) and
# 37. The sources are unpacked from their pinned tarballs into build/<top> and never written to.
set -eu
. "$(dirname "$0")/common.sh"

MODS="$B/plot-modules"
INST="$B/plot-install"
TOOLS="$B/plot-tools"
SUFFIX=".cpython-$PYTHON_TAG-wasm32-wasi.so"
for lib in libfreetype.a libharfbuzz.a libSheenBidi.a libraqm.a libqhull_r.a; do
  [ -s "$B/plot-libs/lib/$lib" ] || die "build/plot-libs/lib/$lib is missing: run step 37"
done
[ -s "$B/zlib-wasi/lib/libz.a" ] || die "build/zlib-wasi has no libz.a: run step 30"
[ -f "$W/pyconfig.h" ] || die "no WASI pyconfig.h at $W: run step 20"
PIL_TGZ=$(pinned pillow-13.0.0.tar.gz)
KIWI_TGZ=$(pinned kiwisolver-1.5.1.tar.gz)
MPL_TGZ=$(pinned matplotlib-3.11.2.tar.gz)
PYBIND11_WHL=$(pinned pybind11-3.1.0-py3-none-any.whl)
CPPY_WHL=$(pinned cppy-1.3.1-py3-none-any.whl)
remove "$B/pillow-13.0.0" "$B/kiwisolver-1.5.1" "$B/matplotlib-3.11.2" "$B/pillow-build" \
  "$B/kiwisolver-build" "$B/matplotlib-build" "$B/matplotlib-install" "$MODS" "$INST" "$TOOLS"
mkdir -p "$MODS" "$INST" "$TOOLS"
for archive in "$PIL_TGZ" "$KIWI_TGZ" "$MPL_TGZ"; do
  tar -xzf "$archive" -C "$B"
done
for top in pillow-13.0.0 kiwisolver-1.5.1 matplotlib-3.11.2; do
  [ -d "$B/$top" ] || die "a pinned tarball did not unpack to build/$top"
  patch_tree "$B/$top"
done
# Header-only C++ from the pinned wheels (build inputs, never run): pybind11 for matplotlib, cppy for
# kiwisolver. A wheel is a zip; the host Python reads it.
"$HOSTPY" -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' "$PYBIND11_WHL" "$TOOLS/pybind11"
"$HOSTPY" -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' "$CPPY_WHL" "$TOOLS/cppy"

CC="$SDK/bin/clang --target=wasm32-wasip1"
CXX="$SDK/bin/clang++ --target=wasm32-wasip1"
AR="$SDK/bin/llvm-ar"
PYINC="-I$CP/Include -I$W"
MAP="-ffile-prefix-map=$HERE=/wasi-python-build"
CXX_EH="-fwasm-exceptions -mllvm -wasm-use-legacy-eh=false -fexceptions"

# Pillow: setup.py's own source lists (its _IMAGING and _LIB_IMAGING tuples, read with ast, never
# run), sorted so the archive's member order is fixed. Its pil_imaging_mode library (Mode.c), which
# setup.py links into every extension, is one archive here that the three modules' .deps name.
P="$B/pillow-13.0.0"
mkdir -p "$B/pillow-build" "$MODS/pillow/PIL"
"$HOSTPY" - "$P/setup.py" > "$B/pillow-build/sources.txt" << 'EOF_PIL'
import ast, sys
tree = ast.parse(open(sys.argv[1], encoding="utf-8").read())
lists = {}
for node in tree.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        name = getattr(node.targets[0], "id", None)
        if name in ("_IMAGING", "_LIB_IMAGING"):
            lists[name] = [e.value for e in node.value.elts]
if set(lists) != {"_IMAGING", "_LIB_IMAGING"}:
    sys.exit("setup.py: no _IMAGING or _LIB_IMAGING tuple")
files = ["src/_imaging.c"] + [f"src/{s}.c" for s in lists["_IMAGING"]]
files += [f"src/libImaging/{s}.c" for s in lists["_LIB_IMAGING"]]
print("\n".join(sorted(files)))
EOF_PIL
PIL_VERSION=$(sed -n 's/^Version: //p' "$P/PKG-INFO" | head -n 1)
[ "$PIL_VERSION" = 13.0.0 ] || die "pillow's PKG-INFO says version $PIL_VERSION"
pil_cc() { # source, object
  $CC -O2 -DNDEBUG $MAP $PYINC -I"$P/src/libImaging" -I"$B/zlib-wasi/include" -DHAVE_LIBZ \
    "-DPILLOW_VERSION=\"$PIL_VERSION\"" -c "$P/$1" -o "$2"
}
objs=""
while IFS= read -r src; do
  obj="$B/pillow-build/$(printf '%s' "$src" | tr / _).o"
  pil_cc "$src" "$obj"
  objs="$objs $obj"
done < "$B/pillow-build/sources.txt"
pil_cc src/libImaging/Mode.c "$B/pillow-build/mode.o"
"$AR" rcD "$B/pillow-build/libpil_imaging_mode.a" "$B/pillow-build/mode.o"
"$AR" rcD "$MODS/pillow/PIL/_imaging$SUFFIX" $objs
printf '%s\n' "$B/pillow-build/libpil_imaging_mode.a" "$B/zlib-wasi/lib/libz.a" > "$MODS/pillow/PIL/_imaging$SUFFIX.deps"
for m in _imagingmath _imagingmorph; do
  pil_cc "src/$m.c" "$B/pillow-build/$m.o"
  "$AR" rcD "$MODS/pillow/PIL/$m$SUFFIX" "$B/pillow-build/$m.o"
  printf '%s\n' "$B/pillow-build/libpil_imaging_mode.a" > "$MODS/pillow/PIL/$m$SUFFIX.deps"
done
mkdir -p "$INST/pillow"
cp -R "$P/src/PIL" "$INST/pillow/PIL"

# kiwisolver: setup.py's seven C++ files, with cppy's headers and cppy's C++11, sorted.
K="$B/kiwisolver-1.5.1"
mkdir -p "$B/kiwisolver-build" "$MODS/kiwisolver/kiwisolver"
objs=""
for src in $(cd "$K/py/src" && ls ./*.cpp | sed 's#^\./##' | sort); do
  obj="$B/kiwisolver-build/${src%.cpp}.o"
  $CXX -O2 -DNDEBUG -std=c++11 $MAP $CXX_EH $PYINC -I"$K" -I"$TOOLS/cppy/cppy/include" \
    -c "$K/py/src/$src" -o "$obj"
  objs="$objs $obj"
done
[ "$(printf '%s\n' $objs | wc -l | tr -d ' ')" = 7 ] || die "kiwisolver: not the seven C++ files setup.py lists"
"$AR" rcD "$MODS/kiwisolver/kiwisolver/_cext$SUFFIX" $objs
: > "$MODS/kiwisolver/kiwisolver/_cext$SUFFIX.deps"
mkdir -p "$INST/kiwisolver"
cp -R "$K/py/kiwisolver" "$INST/kiwisolver/kiwisolver"

# matplotlib: meson with the system libraries of step 37 and no LTO; the install takes exactly the
# package and mpl-data (on a macOS host the runtime tag would run install_name_tool on archives).
M="$B/matplotlib-3.11.2"
sed "s#@ROOT@#$HERE#g; s#@SDK@#$WASI_SDK_DIR#g" "$HERE/recipes/wasi-matplotlib.cross" > "$B/wasi-matplotlib.cross"
export PYTHONPATH="$HERE/recipes/setuptools_scm_stand_in:$PYTHONPATH"
cd "$M"
meson setup "$B/matplotlib-build" --cross-file "$B/wasi-matplotlib.cross" --buildtype=release \
  -Db_lto=false -Dsystem-freetype=true -Dsystem-libraqm=true -Dsystem-qhull=true \
  -DrcParams-backend=Agg -Dmacosx=false -Dpython.bytecompile=-1
ninja -C "$B/matplotlib-build"
meson install -C "$B/matplotlib-build" --destdir "$B/matplotlib-install" --tags python-runtime,data --quiet
cd "$HERE"
SITE=$(find "$B/matplotlib-install" -type d -name matplotlib -path '*site-packages*' | head -n 1)
[ -n "$SITE" ] && [ -f "$SITE/__init__.py" ] || die "no installed matplotlib package under build/matplotlib-install"
SITE=$(dirname "$SITE")
mkdir -p "$INST/matplotlib"
for top in matplotlib mpl_toolkits pylab.py; do
  cp -R "$SITE/$top" "$INST/matplotlib/$top"
done
# Each extension archive at its import path, read from meson's install plan (the extension modules
# carry the runtime tag, so the install above leaves them out), with its .deps from the build
# folder, the paths there made absolute (a -l or -L line stays as it is).
"$HOSTPY" - "$B/matplotlib-build" "$MODS/matplotlib" "$SUFFIX" << 'EOF_MPL' || die "matplotlib's extension archives could not be placed"
import json, os, shutil, sys
build, mods, suffix = sys.argv[1:]
plan = json.load(open(os.path.join(build, "meson-info", "intro-installed.json"), encoding="utf-8"))
placed = 0
for built, target in sorted(plan.items()):
    if not built.endswith(suffix):
        continue
    rel = target.split("/site-packages/", 1)[1]
    dest = os.path.join(mods, rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copyfile(built, dest)
    with open(built + ".deps", encoding="utf-8") as f, open(dest + ".deps", "w", encoding="utf-8") as out:
        for line in f.read().split():
            out.write((line if line.startswith(("/", "-")) else os.path.join(build, line)) + "\n")
    placed += 1
if placed == 0:
    sys.exit("meson's install plan names no extension module")
EOF_MPL
n=$(find "$MODS" -name "*$SUFFIX" | wc -l | tr -d ' ')
echo "plot packages: $n extension archives under build/plot-modules; Python packages under build/plot-install"
