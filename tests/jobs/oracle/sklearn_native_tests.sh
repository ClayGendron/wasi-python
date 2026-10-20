#!/bin/sh
# scikit-learn's own tests, natively, single-threaded, against a native build of the pinned sdist
# with the line's Cython 3.3.0 (spec 044, Decision 2 and stage 1). No scikit-learn release was
# built with 3.3.0, which its pyproject.toml caps out, so the builder runs the subset the pre-build
# review ran and records the counts in the landing notes. Not a build step: the artifact set does
# not depend on it, and build.sh never runs it. It lives beside the oracle, not under scripts/,
# because like the oracle it installs the pinned packages it runs with (scripts/ fetch nothing but
# through scripts/00_download.sh, spec 003, Decision 13).
#
#   sh tests/jobs/oracle/sklearn_native_tests.sh        (after steps 10 and 57; pins and lock files)
#
# It runs the sdist's code on the build host, as the oracle runs native wheels (the confirmation's
# N1), so it is confined the same way: everything under build/sklearn-native/ (the venv, the
# source, the native build, the test site, the outputs); HOME, XDG_CACHE_HOME, the uv cache and
# SCIKIT_LEARN_DATA pointed there; SKLEARN_SKIP_NETWORK_TESTS=1, so no test fetches a dataset; the
# packages from the oracle's and the project's uv.lock with their hashes (numpy, scipy, joblib,
# threadpoolctl, narwhals, pandas; pytest); one thread for OpenMP and BLAS. The source tree gets
# its carried patch, so the patched code is what is tested.
set -eu
# It names what it needs itself, as common.sh does for a step: the repository, the pinned tools
# of step 10, and common.sh's helpers.
HERE=$(CDPATH= cd "$(dirname "$0")/../../.." && pwd -P)
D="$HERE/downloads"
B="$HERE/build"
T="$B/tools"
HOSTPY="$T/python/bin/python3"
. "$HERE/scripts/steps/remove.sh"
export PATH="$T/host-python:$T/pylib/bin:$PATH"
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

N="$B/sklearn-native"
TOP=scikit_learn-1.9.1
TARBALL=$(pinned "$TOP.tar.gz")
[ -x "$T/python/bin/python3" ] && [ -d "$T/pylib/mesonbuild" ] || die "build/tools is missing: run step 10"
remove "$N"
mkdir -p "$N/home" "$N/cache" "$N/data" "$N/run"
export HOME="$N/home" XDG_CACHE_HOME="$N/cache" UV_CACHE_DIR="$N/uv-cache" SCIKIT_LEARN_DATA="$N/data"
export SKLEARN_SKIP_NETWORK_TESTS=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
export PYTHONHASHSEED=0
unset VIRTUAL_ENV

# The venv: the line's Python, the oracle's pins and the project's pytest, each with its hash.
uv export --project "$HERE/tests/jobs/oracle" --frozen --no-emit-project --format requirements-txt \
  > "$N/oracle.txt"
uv export --project "$HERE" --frozen --only-group dev --no-emit-project --format requirements-txt \
  > "$N/pytest.txt"
uv venv -q --python "$T/python/bin/python3" "$N/venv"
VPY="$N/venv/bin/python"
PYTHONPATH= uv pip install -q --python "$VPY" --require-hashes -r "$N/oracle.txt" -r "$N/pytest.txt"

# The native build: the pinned sdist with its patch, meson and Cython from step 10, run by the
# venv's Python so that scikit-learn's native checks find numpy and scipy.
tar -xzf "$TARBALL" -C "$N"
mv "$N/$TOP" "$N/src"
sh "$HERE/scripts/steps/apply_patches.sh" "$N/src" "$HERE/recipes/patches/$TOP"
cd "$N/src"
# Cython runs under step 10's Python and finds numpy's .pxd files in the venv's site-packages.
VSITE=$("$VPY" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
PYTHONPATH="$T/pylib:$VSITE" "$VPY" "$T/pylib/bin/meson" setup "$N/build" --buildtype=release \
  -Db_ndebug=if-release > "$N/setup.log" 2>&1 || { tail -n 20 "$N/setup.log"; die "native meson setup failed"; }
PYTHONPATH="$T/pylib:$VSITE" ninja -C "$N/build" > "$N/build.log" 2>&1 || { tail -n 20 "$N/build.log"; die "native build failed"; }
cd "$HERE"
grep -F "Program cython" "$N/setup.log" | head -n 1
SUFFIX=$("$VPY" -c 'import sysconfig; print(sysconfig.get_config_var("EXT_SUFFIX"))')
"$HOSTPY" "$HERE/scripts/install_from_plan.py" --modules-only "$N/build" "$N/modules.txt" "$SUFFIX"

# The test site: the patched sklearn/ with its tests, and each native module at its install path.
mkdir -p "$N/site"
cp -R "$N/src/sklearn" "$N/site/sklearn"
while IFS="$(printf '\t')" read -r built rel tag; do
  cp "$built" "$N/site/$rel"
done < "$N/modules.txt"

# Cython issue 7846's shape: a cyfunction wrapped with functools.wraps round-trips its
# __annotate__ through pickle; KDTree and BallTree round-trip too.
cd "$N/run"
PYTHONPATH="$N/site" "$VPY" -I -c '
import functools, pickle, sys
sys.path.insert(0, sys.argv[1])
import numpy as np
from sklearn.utils import murmurhash
from sklearn.neighbors import BallTree, KDTree
f = murmurhash._murmurhash3_bytes_array_s32
w = functools.wraps(f)(lambda *a: f(*a))
pickle.loads(pickle.dumps(w.__annotate__))
X = np.arange(20.0).reshape(10, 2)
for T in (KDTree, BallTree):
    t = pickle.loads(pickle.dumps(T(X)))
    assert t.query(X[:1], k=2)[1].tolist() == T(X).query(X[:1], k=2)[1].tolist()
print("7846: __annotate__ pickles; KDTree and BallTree round-trip")
' "$N/site"

# The review's groups, one output file each; the counts are pytest's last line. A group passes only
# when pytest exits 0 and its last line counts passed tests: a group whose interpreter dies (a crash
# in a native module, a kill) prints no summary, and counts as failed (the build review's L4).
FAILED=""
group() { # name modules...
  name=$1
  shift
  status=0
  PYTHONPATH="$N/site" "$VPY" -m pytest -p no:cacheprovider -q --pyargs "$@" > "$N/$name.txt" 2>&1 \
    || status=$?
  echo "$name: $(tail -n 1 "$N/$name.txt") (exit $status)"
  if [ "$status" -ne 0 ] || ! tail -n 1 "$N/$name.txt" | grep -Eq "[0-9]+ passed"; then
    FAILED="$FAILED $name"
  fi
}
group g1 sklearn.svm
group g2 sklearn.tree
group g3 sklearn.neighbors
group g4 sklearn.utils.tests.test_cython_blas sklearn._loss sklearn.cluster.tests.test_hdbscan \
  sklearn.cluster.tests.test_k_means
group g5 sklearn.linear_model.tests.test_sgd sklearn.linear_model.tests.test_coordinate_descent \
  sklearn.metrics.tests.test_pairwise_distances_reduction sklearn.manifold.tests.test_t_sne
group g6 sklearn.ensemble.tests.test_gradient_boosting
group g7 sklearn.ensemble.tests.test_forest
cd "$HERE"
[ -z "$FAILED" ] || die "native test groups failed, or died without pytest's summary:$FAILED (build/sklearn-native/g*.txt)"
echo "native tests: every group passed (build/sklearn-native/g*.txt)"
