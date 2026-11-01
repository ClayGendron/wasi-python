#!/bin/sh
# Step 56: the two C extension modules cairocffi needs, for wasm32-wasip1, as static archives at
# the top of build/cffi-modules/ for step 60, each beside its .deps file.
#
# _cffi_backend: cffi 2.1.1's C backend from its sdist, compiled against a stand-in for libffi
# (recipes/libffi_stand_in/), since libffi has no wasm32-wasip1 port: a call description is
# accepted, so API mode and its static callbacks work; a call through a function pointer aborts and
# a run-time callback is refused. Emulated mmap, which cffi's closure allocator includes, is
# wasi-libc's (malloc underneath; no new import). cffi's Python package is not shipped.
#
# _cairocffi_api: cairocffi 1.7.1's declarations written as C in cffi's API mode by
# recipes/cairo_build.py, run on the build host with the pinned cffi and pycparser (unpacked here
# from their pinned wheels into build/cffi-host/), with a pool of static callbacks and a font
# helper; compiled against step 39's cairo and step 37's FreeType, with the tmpfile refusal
# (recipes/tmpfile_refusal.c) in the same archive, since only cairo calls tmpfile and step 60's
# guards reach the reactor only. Its .deps names cairo, pixman, libpng and FreeType.
#
# Both sdists are unpacked under build/, as every source tree is; step 70 stages cairocffi's
# package from this tree. Step 70 replaces cairocffi's ffi.py with recipes/cairocffi_ffi_stand_in.py. That stand-in follows
# the pinned ffi.py, so this step stops if the pinned ffi.py binds a module-level name the stand-in
# does not, or if cairocffi makes a callback of a type the stand-in's pools do not hold.
set -eu
. "$(dirname "$0")/common.sh"

[ -f "$W/pyconfig.h" ] || die "no WASI pyconfig.h at $W: run step 20"
for lib in libcairo.a libpixman-1.a libpng16.a; do
  [ -s "$B/cairo-libs/lib/$lib" ] || die "build/cairo-libs/lib/$lib is missing: run step 39"
done
[ -s "$B/plot-libs/lib/libfreetype.a" ] || die "build/plot-libs/lib/libfreetype.a is missing: run step 37"
CFFI_TGZ=$(pinned cffi-2.1.1.tar.gz)
CAIROCFFI_TGZ=$(pinned cairocffi-1.7.1.tar.gz)
OBJ="$B/cffi-build"
MODS="$B/cffi-modules"
HOSTCFFI="$B/cffi-host"
SUFFIX=".cpython-$PYTHON_TAG-wasm32-wasi.so"
remove "$B/cffi-2.1.1" "$B/cairocffi-1.7.1" "$OBJ" "$MODS" "$HOSTCFFI"
mkdir -p "$OBJ" "$MODS" "$HOSTCFFI"
for archive in "$CFFI_TGZ" "$CAIROCFFI_TGZ"; do
  tar -xzf "$archive" -C "$B"
done
for top in cffi-2.1.1 cairocffi-1.7.1; do
  [ -d "$B/$top" ] || die "a pinned tarball did not unpack to build/$top"
  patch_tree "$B/$top"
done
CFFI_VERSION=$(sed -n 's/^Version: //p' "$B/cffi-2.1.1/PKG-INFO" | head -n 1)
[ "$CFFI_VERSION" = 2.1.1 ] || die "cffi's PKG-INFO says version $CFFI_VERSION"
CC_VERSION=$(sed -n 's/^Version: //p' "$B/cairocffi-1.7.1/PKG-INFO" | head -n 1)
[ "$CC_VERSION" = 1.7.1 ] || die "cairocffi's PKG-INFO says version $CC_VERSION"

# The stand-in ffi.py follows the pinned one: the same module-level names, and pools for every
# callback type cairocffi makes.
"$HOSTPY" - "$B/cairocffi-1.7.1/cairocffi" "$HERE/recipes/cairocffi_ffi_stand_in.py" \
  > "$OBJ/stand-in-check.log" 2>&1 <<'EOF_CHECK' || { cat "$OBJ/stand-in-check.log"; die "cairocffi's ffi.py stand-in no longer follows the pinned cairocffi (build/cffi-build/stand-in-check.log)"; }
import ast, re, sys
from pathlib import Path

package, stand_in = Path(sys.argv[1]), Path(sys.argv[2])

def bound(path):
    """Names a module binds by assignment at its top level, inside a top-level try or if too."""
    names, todo = set(), list(ast.parse(path.read_text()).body)
    while todo:
        node = todo.pop()
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            for target in node.targets if isinstance(node, ast.Assign) else [node.target]:
                names |= {n.id for n in ast.walk(target) if isinstance(n, ast.Name)}
        elif isinstance(node, ast.Try):
            todo += node.body + node.orelse + node.finalbody
            for handler in node.handlers:
                todo += handler.body
        elif isinstance(node, ast.If):
            todo += node.body + node.orelse
    return names

missing = sorted(bound(package / "ffi.py") - bound(stand_in))
if missing:
    sys.exit(f"ERROR: the pinned ffi.py binds {missing}, which the stand-in does not")
stand_in_text = stand_in.read_text()
pools = set(re.findall(r'"(cairo_\w+_func_t)": "\w+"', stand_in_text))
types = set()
for path in sorted(package.glob("*.py")):
    if path.name.startswith("test_") or path.name == "ffi.py":
        continue
    types |= set(re.findall(r"ffi\.callback\(\s*['\"]([^'\"]+)['\"]", path.read_text()))
if not types or types - pools:
    sys.exit(f"ERROR: cairocffi makes callbacks of types {sorted(types)}; the pools hold {sorted(pools)}")
print(f"stand-in: binds {sorted(bound(stand_in) & bound(package / 'ffi.py'))}; callback types {sorted(types)}")
EOF_CHECK
tail -n 1 "$OBJ/stand-in-check.log"

# The build host's cffi and pycparser, from their pinned wheels (each hash checked by `pinned`),
# unpacked into build/cffi-host/: a wheel is a zip of its installed files, and nothing is fetched.
for wheel in "$CFFI_WHEEL" pycparser-3.12-py3-none-any.whl; do
  "$HOSTPY" -I -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' \
    "$(pinned "$wheel")" "$HOSTCFFI" || die "$wheel did not unpack into build/cffi-host"
done
PYTHONPATH="$HOSTCFFI" "$HOSTPY" -s "$HERE/recipes/cairo_build.py" \
  "$B/cairocffi-1.7.1/cairocffi/constants.py" "$OBJ/_cairocffi_api.c" \
  || die "recipes/cairo_build.py did not write cairocffi's bindings"

# -DNDEBUG, as CPython's release build and cffi's wheels compile, and the prefix map: no build path
# in the binary.
CFLAGS="-O2 -DNDEBUG -ffile-prefix-map=$HERE=/wasi-python-build -I$CP/Include -I$W"
compile() { # source, object, then its own flags
  src=$1 obj=$2
  shift 2
  "$HERE/scripts/wasi-cc" $CFLAGS "$@" -c "$src" -o "$OBJ/$obj.o" > "$OBJ/$obj.log" 2>&1 \
    || { tail -n 20 "$OBJ/$obj.log"; die "$src did not compile (build/cffi-build/$obj.log)"; }
  echo "$obj: $(grep -c 'warning:' "$OBJ/$obj.log" || :) warnings (build/cffi-build/$obj.log)"
}
compile "$B/cffi-2.1.1/src/c/_cffi_backend.c" _cffi_backend -I"$HERE/recipes/libffi_stand_in" -D_WASI_EMULATED_MMAN
compile "$HERE/recipes/libffi_stand_in/ffi_stand_in.c" ffi_stand_in -I"$HERE/recipes/libffi_stand_in"
# FreeType's headers include setjmp.h, which asks for the exception-handling form, as step 37 builds.
compile "$OBJ/_cairocffi_api.c" _cairocffi_api -I"$B/cairo-libs/include/cairo" \
  -I"$B/plot-libs/include/freetype2" -fwasm-exceptions -mllvm -wasm-enable-sjlj \
  -mllvm -wasm-use-legacy-eh=false
compile "$HERE/recipes/tmpfile_refusal.c" tmpfile_refusal
"$HERE/scripts/wasi-cc" -shared -o "$MODS/_cffi_backend$SUFFIX" "$OBJ/_cffi_backend.o" "$OBJ/ffi_stand_in.o"
"$HERE/scripts/wasi-cc" -shared -o "$MODS/_cairocffi_api$SUFFIX" "$OBJ/_cairocffi_api.o" \
  "$OBJ/tmpfile_refusal.o" "$B/cairo-libs/lib/libcairo.a" "$B/cairo-libs/lib/libpixman-1.a" \
  "$B/cairo-libs/lib/libpng16.a" "$B/plot-libs/lib/libfreetype.a"
for m in _cffi_backend _cairocffi_api; do
  [ -s "$MODS/$m$SUFFIX" ] || die "step 56 made no $m$SUFFIX"
done
echo "cairocffi: 2 extension archives under build/cffi-modules ($(wc -c < "$MODS/_cffi_backend$SUFFIX" | tr -d ' ') and $(wc -c < "$MODS/_cairocffi_api$SUFFIX" | tr -d ' ') bytes)"
