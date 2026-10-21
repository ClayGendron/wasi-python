#!/bin/sh
# Step 59: statsmodels 0.15.0 for wasm32-wasip1 (Decision 4): meson through
# recipes/wasi-statsmodels.cross against step 40's numpy and step 57's scipy, whose Cython
# declarations scripts/stage_scipy_cimports.sh stages under build/scipy-cimport, as
# scikit-learn's step does. Each extension module becomes a static archive beside a .deps file, as scripts/wasi-cc makes
# them; the four init names that would clash in one static link are renamed per file through
# recipes/statsmodels_file_includes.txt and recipes/statsmodels-renames/ (Decision 5). statsmodels'
# version script imports setuptools_scm and packaging at configure time: the recipe's stand-in
# (recipes/setuptools_scm_stand_in, which reads the sdist's PKG-INFO) and the pinned packaging wheel
# are on PYTHONPATH for meson setup alone (Decision 3). Three gates: the configured version is the
# sdist's, scipy's blas_int found, and the per-file include log (each entry matched exactly one
# compile). The Python package is the patched sdist's statsmodels/ folder as an install places it
# (meson installs its subfolders with install_subdir and generates no Python file from an sdist):
# without _build/, with the project's pyproject.toml, under build/statsmodels-install; the
# extension modules' list, from meson's install plan, goes to
# build/statsmodels-build/extension-modules.txt, and each archive to its import path under
# build/statsmodels-modules for step 60.
# Needs steps 10, 20, 40 and 57.
set -eu
. "$(dirname "$0")/common.sh"

TOP=statsmodels-0.15.0
VERSION=0.15.0
SRC="$B/$TOP"
BUILD="$B/statsmodels-build"
INST="$B/statsmodels-install"
MODS="$B/statsmodels-modules"
CIMPORT="$B/scipy-cimport"
TARBALL=$(pinned "$TOP.tar.gz")
PACKAGING=$(pinned packaging-26.3-py3-none-any.whl)
SUFFIX=".cpython-$PYTHON_TAG-wasm32-wasi.so"
MODULES=26  # the native build's count (EXECUTED while drafting), none tagged tests
[ -d "$B/numpy-host/numpy" ] || die "no host-side numpy stand-in: run step 40 first"
[ -d "$B/scipy-1.18.1/scipy" ] && [ -d "$B/scipy-build/scipy" ] \
  || die "build/scipy-1.18.1 or build/scipy-build is missing: run step 57"
remove "$SRC" "$BUILD" "$INST" "$MODS" "$CIMPORT"
tar -xzf "$TARBALL" -C "$B"
[ -d "$SRC" ] || die "the pinned tarball did not unpack to build/$TOP"
patch_tree "$SRC"
mkdir -p "$BUILD"

# scipy's cython_blas, cython_lapack and cython_special declarations, as scikit-learn's step stages them.
sh "$HERE/scripts/stage_scipy_cimports.sh" "$B/scipy-1.18.1" "$B/scipy-build" "$CIMPORT"

sed "s#@ROOT@#$HERE#g; s#@SDK@#$WASI_SDK_DIR#g" "$HERE/recipes/wasi-statsmodels.cross" > "$B/wasi-statsmodels.cross"
# The per-file include map, rendered into build/: nothing is ever written under recipes/.
sed "s#@ROOT@#$HERE#g; s#@SO@#$SUFFIX#g" "$HERE/recipes/statsmodels_file_includes.txt" > "$BUILD/file-includes.txt"
export WASI_CC_FILE_INCLUDES="$BUILD/file-includes.txt" WASI_CC_FILE_INCLUDES_LOG="$BUILD/file-includes.log"
: > "$WASI_CC_FILE_INCLUDES_LOG"
# The target Python (scripts/python-wasi-cross) finds step 40's numpy stand-in here, whose
# get_include() names the wasm build's headers and which holds numpy's __init__.pxd, and Cython
# finds scipy's declarations beside it.
export PYTHONPATH="$CIMPORT:$B/numpy-host:$PYTHONPATH"

cd "$SRC"
# The release build type and asserts off are meson-python's defaults, as statsmodels' wheels are
# built. project() runs statsmodels/_build/git_version.py under meson's own Python, the pinned host
# Python, which imports setuptools_scm (the stand-in) and packaging.version (the pinned wheel, a
# zip on the path; nothing is installed).
PYTHONPATH="$HERE/recipes/setuptools_scm_stand_in:$PACKAGING:$PYTHONPATH" \
  meson setup "$BUILD" --cross-file "$B/wasi-statsmodels.cross" --buildtype=release -Db_ndebug=if-release
SETUP="$BUILD/meson-logs/meson-log.txt"
# The version gate (Decision 3): the stand-in's answer is the sdist's own, and the sdist's
# _version.py, which meson installs as it is, says the same.
grep -q -x -F "Project version: $VERSION" "$SETUP" || die "meson configured another version than $VERSION ($SETUP)"
grep -q -x -F "Version: $VERSION" "$SRC/PKG-INFO" || die "build/$TOP/PKG-INFO is not version $VERSION"
grep -q -x -F "__version__ = version = '$VERSION'" "$SRC/statsmodels/_version.py" \
  || die "build/$TOP/statsmodels/_version.py does not say $VERSION"
# scipy's LP64 cython_blas declares blas_int; without the staged declarations statsmodels would
# fall back to its own typedef silently (meson.build).
grep -q -F 'Checking if "scipy cython_blas blas_int" compiles: YES' "$SETUP" \
  || die "scipy's cython_blas blas_int was not found ($SETUP): check build/scipy-cimport"
ninja -C "$BUILD" > "$BUILD.log" 2>&1 || { tail -n 30 "$BUILD.log"; die "statsmodels' ninja failed (build/statsmodels-build.log)"; }
cd "$HERE"
echo "warnings: $(grep -c 'warning:' "$BUILD.log" || :)"

# The per-file include log: each map entry matched exactly one compile.
grep -v '^#' "$BUILD/file-includes.txt" | while read -r suffix header count; do
  [ -n "$suffix" ] || continue
  n=$(cut -f 1 "$WASI_CC_FILE_INCLUDES_LOG" | grep -c -x -F -- "$suffix" || :)
  [ "$n" = "${count:-1}" ] || die "per-file include $suffix matched $n compiles, not ${count:-1} (build/statsmodels-build/file-includes.log)"
  echo "per-file include: $suffix -> ${header##*/}, $n compile(s)"
done

# The Python package, as an install places it: the patched sdist's statsmodels/ folder without
# _build/ (never installed), with the project's pyproject.toml, which meson.build installs into the
# package. Step 70 sets aside its tests, sources and meson.build files by its own rules.
mkdir -p "$INST"
cp -R "$SRC/statsmodels" "$INST/statsmodels"
remove "$INST/statsmodels/_build"
cp "$SRC/pyproject.toml" "$INST/statsmodels/pyproject.toml"
[ -f "$INST/statsmodels/__init__.py" ] && [ -f "$INST/statsmodels/datasets/longley/longley.csv" ] \
  || die "the statsmodels package lacks __init__.py or datasets/longley/longley.csv"

# The extension modules' list from meson's install plan, nothing copied, as scikit-learn's step reads it.
out=$("$HOSTPY" "$HERE/scripts/install_from_plan.py" --modules-only "$BUILD" "$BUILD/extension-modules.txt" "$SUFFIX")
echo "$out"
[ "$out" = "$MODULES extension modules listed; 0 tagged tests left out" ] \
  || die "meson's install plan lists other modules than statsmodels' $MODULES, none tagged tests"
# Each extension archive at its import path under build/statsmodels-modules, as step 58 lays
# scikit-learn's, its .deps paths made absolute (a -l or -L line stays as it is).
while IFS="$(printf '\t')" read -r built rel tag; do
  mkdir -p "$(dirname "$MODS/$rel")"
  cp "$built" "$MODS/$rel"
  while IFS= read -r dep; do
    case "$dep" in /*|-*) printf '%s\n' "$dep";; ?*) printf '%s\n' "$BUILD/$dep";; esac
  done < "$built.deps" > "$MODS/$rel.deps"
done < "$BUILD/extension-modules.txt"
n=$(find "$MODS" -name "*$SUFFIX" | wc -l | tr -d ' ')
[ "$n" = "$MODULES" ] || die "build/statsmodels-modules holds $n extension archives, not $MODULES"
echo "statsmodels: $n extension archives under build/statsmodels-modules, package at ${INST#"$B"/}/statsmodels"
