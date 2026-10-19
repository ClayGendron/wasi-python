#!/bin/sh
# Step 57: scipy 1.18.1 for wasm32-wasip1 (spec 037, Decisions 6 and 7), with no Fortran compiler:
# meson through recipes/wasi-scipy.cross against step 38's OpenBLAS, step 40's numpy and pybind11,
# with f2py run on the build host (scripts/f2py-host) and pythran off. Each extension module becomes
# a static archive beside a .deps file, as scripts/wasi-cc makes them; scipy's own side of the
# LAPACK ABI is recipes/scipy_lapack_shims.c and its rename headers, three of them per file through
# recipes/scipy_file_includes.txt. Then two gates: the per-file include log (each entry matched one
# compile) and the direct-call gate (every routine f2py calls through a pointer, called directly
# and linked, so a signature clash shows at link time). The Python package comes from meson's
# install plan (scripts/install_from_plan.py), never `meson install`, under build/scipy-install;
# the extension modules' list goes to build/scipy-build/extension-modules.txt for step 60.
# Needs steps 10, 20, 38 and 40.
set -eu
. "$(dirname "$0")/common.sh"

TOP=scipy-1.18.1
SRC="$B/$TOP"
BUILD="$B/scipy-build"
INST="$B/scipy-install"
TOOLS="$B/scipy-tools"
SHIMS="$B/scipy-shims"
OB="$B/openblas-wasi"
TARBALL=$(pinned "$TOP.tar.gz")
PYBIND11_WHL=$(pinned pybind11-3.1.0-py3-none-any.whl)
[ -s "$OB/lib/libopenblas.a" ] || die "build/openblas-wasi has no libopenblas.a: run step 38"
[ -d "$B/numpy-host/numpy" ] || die "no host-side numpy stand-in: run step 40 first"
[ -d "$T/f2py-numpy/numpy" ] || die "build/tools/f2py-numpy is missing: run step 10"
NUMPY_SITE=$(find "$B/numpy-install" -type d -name numpy -path '*site-packages*' | head -n 1)
[ -n "$NUMPY_SITE" ] || die "no installed numpy package under build/numpy-install: run step 40"
NUMPY_INCLUDE="$NUMPY_SITE/_core/include"
[ -f "$NUMPY_SITE/f2py/src/fortranobject.c" ] || die "step 40's numpy has no f2py/src/fortranobject.c"
remove "$SRC" "$BUILD" "$INST" "$TOOLS" "$SHIMS"
tar -xzf "$TARBALL" -C "$B"
[ -d "$SRC" ] || die "the pinned tarball did not unpack to build/$TOP"
patch_tree "$SRC"
mkdir -p "$BUILD" "$TOOLS/bin" "$SHIMS"

# pybind11's headers and .pc from its pinned wheel (a build input, never run).
"$HOSTPY" -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' "$PYBIND11_WHL" "$TOOLS/pybind11"
# f2py on the build host: scipy's generator runs `f2py` from PATH (tools/generate_f2pymod.py).
printf '#!/bin/sh\nexec "%s/scripts/f2py-host" "$@"\n' "$HERE" > "$TOOLS/bin/f2py"
chmod 755 "$TOOLS/bin/f2py"
export PATH="$TOOLS/bin:$PATH"

sed "s#@ROOT@#$HERE#g; s#@SDK@#$WASI_SDK_DIR#g; s#@NUMPY_INCLUDE@#$NUMPY_INCLUDE#g" \
  "$HERE/recipes/wasi-scipy.cross" > "$B/wasi-scipy.cross"
# pkgconf sees exactly three folders, and none of the host's: PKG_CONFIG_LIBDIR replaces its default
# search path, so a host's own openblas.pc can never be found if one of ours is missing.
PCDIRS="$OB/lib/pkgconfig:$NUMPY_SITE/_core/lib/pkgconfig:$TOOLS/pybind11/pybind11/share/pkgconfig"
export PKG_CONFIG_PATH="$PCDIRS" PKG_CONFIG_LIBDIR="$PCDIRS"
# The per-file include map, rendered into build/: nothing is ever written under recipes/.
sed "s#@ROOT@#$HERE#g" "$HERE/recipes/scipy_file_includes.txt" > "$BUILD/file-includes.txt"
export WASI_CC_FILE_INCLUDES="$BUILD/file-includes.txt" WASI_CC_FILE_INCLUDES_LOG="$BUILD/file-includes.log"
: > "$WASI_CC_FILE_INCLUDES_LOG"
# The target Python (scripts/python-wasi-cross) and Cython find the numpy stand-in here: step 40's,
# copied, with numpy.random's .pxd files from step 40's install beside it, because scipy's
# stats._unuran cimports numpy.random (pandas cimports numpy alone, so step 40's
# own stand-in stays as it is).
cp -R "$B/numpy-host" "$TOOLS/numpy-host"
mkdir -p "$TOOLS/numpy-host/numpy/random"
cp "$NUMPY_SITE"/random/*.pxd "$TOOLS/numpy-host/numpy/random/"
export PYTHONPATH="$TOOLS/numpy-host:$PYTHONPATH"

cd "$SRC"
# The release build type and asserts off are meson-python's defaults, as scipy's wheels are built.
meson setup "$BUILD" --cross-file "$B/wasi-scipy.cross" --buildtype=release -Db_ndebug=if-release \
  -D_without-fortran=true -Duse-pythran=false -Dblas=openblas -Dlapack=openblas \
  -Duse-system-libraries=none
# Every installed target but the seven test modules (one, special._test_internal, sets the FPU's
# rounding modes, which WASI lacks; none is linked).
"$HOSTPY" "$HERE/scripts/install_from_plan.py" --targets "$BUILD" > "$BUILD/targets.txt"
ninja -C "$BUILD" $(cat "$BUILD/targets.txt") > "$BUILD.log" 2>&1 || { tail -n 30 "$BUILD.log"; die "scipy's ninja failed (build/scipy-build.log)"; }
cd "$HERE"
echo "warnings: $(grep -c 'warning:' "$BUILD.log" || :)"

# The per-file include log: each map entry matched exactly as many compiles as it says (one when
# it says nothing).
grep -v '^#' "$BUILD/file-includes.txt" | while read -r suffix header count; do
  [ -n "$suffix" ] || continue
  n=$(cut -f 1 "$WASI_CC_FILE_INCLUDES_LOG" | grep -c -x -F -- "$suffix" || :)
  [ "$n" = "${count:-1}" ] || die "per-file include $suffix matched $n compiles, not ${count:-1} (build/scipy-build/file-includes.log)"
  echo "per-file include: $suffix -> $(basename "$header"), $n compile(s)"
done

# scipy's side of the LAPACK ABI (Decision 6): six shims of ours, compiled alone, no rename header.
"$SDK/bin/clang" --target=wasm32-wasip1 -O2 -ffile-prefix-map="$HERE=/wasi-python-build" \
  -c "$HERE/recipes/scipy_lapack_shims.c" -o "$SHIMS/scipy_lapack_shims.o"
"$SDK/bin/llvm-ar" rcD "$SHIMS/libscipy_lapack_shims.a" "$SHIMS/scipy_lapack_shims.o"

# The Python package from meson's install plan, and the extension modules' list for step 60.
SUFFIX=".cpython-$PYTHON_TAG-wasm32-wasi.so"
"$HOSTPY" "$HERE/scripts/install_from_plan.py" "$BUILD" "$INST" "$BUILD/extension-modules.txt" "$SUFFIX"
[ -f "$INST/scipy/__init__.py" ] && [ -f "$INST/scipy/__config__.py" ] && [ -f "$INST/scipy/version.py" ] \
  || die "the install from meson's plan lacks scipy/__init__.py, __config__.py or version.py"
# Each extension archive at its import path under build/scipy-modules, as step 55 lays matplotlib's,
# its .deps paths made absolute (a -l or -L line stays as it is).
MODS="$B/scipy-modules"
remove "$MODS"
while IFS="$(printf '\t')" read -r built rel tag; do
  mkdir -p "$(dirname "$MODS/$rel")"
  cp "$built" "$MODS/$rel"
  while IFS= read -r dep; do
    case "$dep" in /*|-*) printf '%s\n' "$dep";; ?*) printf '%s\n' "$BUILD/$dep";; esac
  done < "$built.deps" > "$MODS/$rel.deps"
done < "$BUILD/extension-modules.txt"
n=$(find "$MODS" -name "*$SUFFIX" | wc -l | tr -d ' ')
echo "scipy: $n extension archives under build/scipy-modules"

# The direct-call gate (Decision 6): f2py calls LAPACK through pointers, so a clash there links
# silently and traps at run time. Every routine of _fblas and _flapack is called directly in one
# file, compiled with _flapackmodule.c's own command and its per-file include, and linked with what
# the two modules link, OpenBLAS and the shims; a signature mismatch or undefined symbol stops here.
G="$BUILD/direct-calls"
mkdir -p "$G"
"$HOSTPY" "$HERE/scripts/f2py_direct_calls.py" "$G/direct-calls.c" \
  "$BUILD/scipy/linalg/_flapackmodule.c" "$BUILD/scipy/linalg/_fblasmodule.c"
"$HOSTPY" - "$BUILD/compile_commands.json" "$G/direct-calls.c" "$G/direct-calls.o" \
  "$HERE/recipes/scipy_flapack_rename.h" > "$G/compile.sh" << 'EOF_CC'
import json, shlex, sys
db, src, obj, header = sys.argv[1:]
hits = [e for e in json.load(open(db)) if e["file"].endswith("_flapackmodule.c")]
if len(hits) != 1:
    sys.exit(f"compile_commands.json has {len(hits)} entries for _flapackmodule.c, not 1")
args = shlex.split(hits[0]["command"])
args[args.index("-o") + 1] = obj
args[args.index("-c") + 1] = src
args[1:1] = ["-include", header]  # _flapackmodule.c's per-file include, given by name here
print("cd " + shlex.quote(hits[0]["directory"]) + " && " + shlex.join(args))
EOF_CC
# The map is not consulted for this compile: its include is on the command, and the log stays the
# record of scipy's own compiles.
(unset WASI_CC_FILE_INCLUDES; sh "$G/compile.sh") > "$G/compile.log" 2>&1 \
  || { tail -n 20 "$G/compile.log"; die "the direct-call gate's compile failed (build/scipy-build/direct-calls/compile.log)"; }
deps=$(cat "$MODS/scipy/linalg/_fblas$SUFFIX.deps" "$MODS/scipy/linalg/_flapack$SUFFIX.deps" | sort -u | tr '\n' ' ')
"$SDK/bin/clang" --target=wasm32-wasip1 -fwasm-exceptions -nostartfiles -Wl,--no-entry \
  -Wl,--export=wasi_scipy_direct_calls -o "$G/direct-calls.wasm" "$G/direct-calls.o" $deps \
  "$SHIMS/libscipy_lapack_shims.a" "$OB/lib/libopenblas.a" -lwasi-emulated-mman -lsetjmp \
  > "$G/link.log" 2>&1 || { tail -n 20 "$G/link.log"; die "direct-call gate: the link failed, an undefined symbol or another error (build/scipy-build/direct-calls/link.log)"; }
n=$(grep -c 'signature mismatch' "$G/link.log" || :)
[ "$n" = 0 ] || die "direct-call gate: $n signature mismatches, the first: $(grep -m 1 'signature mismatch' "$G/link.log")"
remove "$G/direct-calls.wasm"
echo "direct-call gate: $(grep -c '^    (void)F_FUNC' "$G/direct-calls.c") routines, 0 signature mismatches, no undefined symbol"
