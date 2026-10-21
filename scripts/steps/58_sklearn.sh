#!/bin/sh
# Step 58: scikit-learn 1.9.1 for wasm32-wasip1: meson through
# recipes/wasi-sklearn.cross against step 40's numpy and step 57's scipy, whose Cython
# declarations scripts/stage_scipy_cimports.sh stages under build/scipy-cimport (Decision 4). Each
# extension module becomes a static archive beside a .deps file, as scripts/wasi-cc makes them; the
# names that would clash in one static link are renamed per file through
# recipes/sklearn_file_includes.txt and recipes/sklearn-renames/ (Decision 6). Three gates: no
# OpenMP (meson found none, and no compile has -fopenmp; Decision 3), scipy's blas_int found, and
# the per-file include log (each entry matched exactly one compile). The Python package is the
# patched sdist's sklearn/ folder, as an install places it (scikit-learn installs it with
# install_subdir and generates no Python file), under build/sklearn-install; the extension
# modules' list, from meson's install plan, goes to build/sklearn-build/extension-modules.txt, and
# each archive to its import path under build/sklearn-modules for step 60.
# Needs steps 10, 20, 40 and 57.
set -eu
. "$(dirname "$0")/common.sh"

TOP=scikit_learn-1.9.1
SRC="$B/$TOP"
BUILD="$B/sklearn-build"
INST="$B/sklearn-install"
MODS="$B/sklearn-modules"
CIMPORT="$B/scipy-cimport"
TARBALL=$(pinned "$TOP.tar.gz")
SUFFIX=".cpython-$PYTHON_TAG-wasm32-wasi.so"
MODULES=69  # the native build's count (EXECUTED while drafting), none tagged tests
[ -d "$B/numpy-host/numpy" ] || die "no host-side numpy stand-in: run step 40 first"
NUMPY_SITE=$(find "$B/numpy-install" -type d -name numpy -path '*site-packages*' | head -n 1)
[ -n "$NUMPY_SITE" ] || die "no installed numpy package under build/numpy-install: run step 40"
NUMPY_INCLUDE="$NUMPY_SITE/_core/include"
[ -d "$B/scipy-1.18.1/scipy" ] && [ -d "$B/scipy-build/scipy" ] \
  || die "build/scipy-1.18.1 or build/scipy-build is missing: run step 57"
remove "$SRC" "$BUILD" "$INST" "$MODS" "$CIMPORT"
tar -xzf "$TARBALL" -C "$B"
[ -d "$SRC" ] || die "the pinned tarball did not unpack to build/$TOP"
patch_tree "$SRC"
mkdir -p "$BUILD"

# scipy's cython_blas, cython_lapack and cython_special declarations (Decision 4).
sh "$HERE/scripts/stage_scipy_cimports.sh" "$B/scipy-1.18.1" "$B/scipy-build" "$CIMPORT"

sed "s#@ROOT@#$HERE#g; s#@SDK@#$WASI_SDK_DIR#g; s#@NUMPY_INCLUDE@#$NUMPY_INCLUDE#g" \
  "$HERE/recipes/wasi-sklearn.cross" > "$B/wasi-sklearn.cross"
# The per-file include map, rendered into build/: nothing is ever written under recipes/.
sed "s#@ROOT@#$HERE#g; s#@SO@#$SUFFIX#g" "$HERE/recipes/sklearn_file_includes.txt" > "$BUILD/file-includes.txt"
export WASI_CC_FILE_INCLUDES="$BUILD/file-includes.txt" WASI_CC_FILE_INCLUDES_LOG="$BUILD/file-includes.log"
: > "$WASI_CC_FILE_INCLUDES_LOG"
# The target Python (scripts/python-wasi-cross) finds step 40's numpy stand-in here, which holds
# numpy's __init__.pxd, and Cython finds scipy's declarations beside it.
export PYTHONPATH="$CIMPORT:$B/numpy-host:$PYTHONPATH"

cd "$SRC"
# The release build type and asserts off are meson-python's defaults, as scikit-learn's wheels are
# built. The version script (sklearn/_build_utils/version.py) runs under meson's own Python.
meson setup "$BUILD" --cross-file "$B/wasi-sklearn.cross" --buildtype=release -Db_ndebug=if-release
SETUP="$BUILD/meson-logs/meson-log.txt"
grep -q -x -F "Project version: 1.9.1" "$SETUP" || die "meson configured another version than 1.9.1 ($SETUP)"
# No OpenMP (Decision 3): wasi-sdk ships no omp.h and no runtime, and the cross file lets meson find
# no host library. A future SDK with one would also need threads, which the guest lacks.
grep -q -F "Run-time dependency OpenMP for c found: NO" "$SETUP" \
  || die "meson found OpenMP for wasm32-wasip1 ($SETUP); the guest has no threads"
# scipy's LP64 cython_blas declares blas_int; without the staged declarations scikit-learn would
# fall back to its own typedef silently (sklearn/utils/meson.build).
grep -q -F 'Checking if "scipy cython_blas blas_int" compiles: YES' "$SETUP" \
  || die "scipy's cython_blas blas_int was not found ($SETUP): check build/scipy-cimport"
ninja -C "$BUILD" > "$BUILD.log" 2>&1 || { tail -n 30 "$BUILD.log"; die "scikit-learn's ninja failed (build/sklearn-build.log)"; }
cd "$HERE"
echo "warnings: $(grep -c 'warning:' "$BUILD.log" || :)"
n=$(grep -c -e '-fopenmp' "$BUILD/compile_commands.json" || :)
[ "$n" = 0 ] || die "$n lines of build/sklearn-build/compile_commands.json hold -fopenmp"
echo "OpenMP: not found by meson, and no compile holds -fopenmp"

# The per-file include log: each map entry matched exactly one compile.
grep -v '^#' "$BUILD/file-includes.txt" | while read -r suffix header count; do
  [ -n "$suffix" ] || continue
  n=$(cut -f 1 "$WASI_CC_FILE_INCLUDES_LOG" | grep -c -x -F -- "$suffix" || :)
  [ "$n" = "${count:-1}" ] || die "per-file include $suffix matched $n compiles, not ${count:-1} (build/sklearn-build/file-includes.log)"
  echo "per-file include: $suffix -> ${header##*/}, $n compile(s)"
done

# The Python package, as an install places it: the patched sdist's sklearn/ folder. Step 70 sets
# aside its tests, sources and meson.build files by its own rules.
mkdir -p "$INST"
cp -R "$SRC/sklearn" "$INST/sklearn"
[ -f "$INST/sklearn/__init__.py" ] && [ -f "$INST/sklearn/utils/_repr_html/estimator.css" ] \
  || die "the scikit-learn package lacks __init__.py or utils/_repr_html/estimator.css"

# The extension modules' list from meson's install plan, nothing copied (Decision 5).
out=$("$HOSTPY" "$HERE/scripts/install_from_plan.py" --modules-only "$BUILD" "$BUILD/extension-modules.txt" "$SUFFIX")
echo "$out"
[ "$out" = "$MODULES extension modules listed; 0 tagged tests left out" ] \
  || die "meson's install plan lists other modules than scikit-learn's $MODULES, none tagged tests"
# Each extension archive at its import path under build/sklearn-modules, as step 57 lays scipy's,
# its .deps paths made absolute (a -l or -L line stays as it is).
while IFS="$(printf '\t')" read -r built rel tag; do
  mkdir -p "$(dirname "$MODS/$rel")"
  cp "$built" "$MODS/$rel"
  while IFS= read -r dep; do
    case "$dep" in /*|-*) printf '%s\n' "$dep";; ?*) printf '%s\n' "$BUILD/$dep";; esac
  done < "$built.deps" > "$MODS/$rel.deps"
done < "$BUILD/extension-modules.txt"
n=$(find "$MODS" -name "*$SUFFIX" | wc -l | tr -d ' ')
[ "$n" = "$MODULES" ] || die "build/sklearn-modules holds $n extension archives, not $MODULES"
echo "scikit-learn: $n extension archives under build/sklearn-modules, package at ${INST#"$B"/}/sklearn"
