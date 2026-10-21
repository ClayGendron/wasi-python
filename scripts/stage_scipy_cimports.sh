#!/bin/sh
# scipy's Cython declarations, staged for a package that cimports them
# (scikit-learn and statsmodels):
#
#   scripts/stage_scipy_cimports.sh <scipy source tree> <scipy meson build folder> <out folder>
#
# scikit-learn and statsmodels cimport scipy.linalg.cython_blas, cython_lapack and
# scipy.special.cython_special. Cython finds a cimported module's .pxd on sys.path, and needs every
# folder above it to be a package. Step 57's install of scipy carries none of them: the generated
# cython_blas.pxd and cython_lapack.pxd are tagged devel, and scripts/install_from_plan.py copies
# only python-runtime files. So this writes <out folder> afresh with exactly six files: an empty
# scipy/__init__.py (a package marker; scipy/ has no __init__.pxd), linalg/__init__.pxd and
# special/__init__.pxd and cython_special.pxd from the (patched) source tree, and cython_blas.pxd and
# cython_lapack.pxd from the build folder. None of the five .pxd files cimports anything outside
# them. A missing one stops it, named. The marker means a host process that imported scipy from
# here would get an empty package; nothing in the cross builds imports scipy.
set -eu
[ "$#" -eq 3 ] || { echo "usage: stage_scipy_cimports.sh SCIPY_TREE SCIPY_BUILD OUT" >&2; exit 2; }
SRC=$1 BUILD=$2 OUT=$3
. "$(dirname "$0")/steps/remove.sh"

missing=""
for f in "$SRC/scipy/linalg/__init__.pxd" "$SRC/scipy/special/__init__.pxd" \
  "$SRC/scipy/special/cython_special.pxd" "$BUILD/scipy/linalg/cython_blas.pxd" \
  "$BUILD/scipy/linalg/cython_lapack.pxd"; do
  [ -f "$f" ] || missing="$missing $f"
done
if [ -n "$missing" ]; then
  echo "ERROR: scipy's Cython declarations are missing:$missing" >&2
  exit 1
fi

remove "$OUT"
mkdir -p "$OUT/scipy/linalg" "$OUT/scipy/special"
: > "$OUT/scipy/__init__.py"
cp "$SRC/scipy/linalg/__init__.pxd" "$OUT/scipy/linalg/__init__.pxd"
cp "$BUILD/scipy/linalg/cython_blas.pxd" "$OUT/scipy/linalg/cython_blas.pxd"
cp "$BUILD/scipy/linalg/cython_lapack.pxd" "$OUT/scipy/linalg/cython_lapack.pxd"
cp "$SRC/scipy/special/__init__.pxd" "$OUT/scipy/special/__init__.pxd"
cp "$SRC/scipy/special/cython_special.pxd" "$OUT/scipy/special/cython_special.pxd"
n=$(find "$OUT" -type f | wc -l | tr -d ' ')
[ "$n" = 6 ] || { echo "ERROR: $OUT holds $n files, not 6" >&2; exit 1; }
echo "scipy's Cython declarations: 6 files under $OUT"
