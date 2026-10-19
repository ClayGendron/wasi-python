#!/bin/sh
# Inside a research container (spec 086, criteria 3 and 5): clone the branch's throwaway clone
# (/src, read-only) to /work/wasi_python, stage verified host-neutral pins from /pins (step 00
# verifies every one against SHA256SUMS again), build N times from an empty build/, keep each
# SHA256SUMS, then run criterion 5's checks on the last set. Outputs to /out.
set -eu
N=${1:-2}
R=/work/wasi_python
rm -rf "$R"
git clone -q /src "$R"
cp /pins/* "$R/downloads/" 2>/dev/null || true
cd "$R"
{ echo "uname: $(uname -srm)"; echo "commit: $(git rev-parse HEAD)"; git status --short; } > /out/host-tools.txt
n=1
while [ "$n" -le "$N" ]; do
  rm -rf build
  start=$(date +%s)
  status=0
  sh scripts/build.sh --plain > /out/build-$n.txt 2>&1 || status=$?
  echo "exit: $status, wall: $(( $(date +%s) - start ))s" >> /out/build-$n.txt
  if [ -f build/artifacts/SHA256SUMS ]; then
    cp build/artifacts/SHA256SUMS /out/SHA256SUMS-$n
  fi
  [ "$status" = 0 ] || exit "$status"
  n=$((n + 1))
done
# Criterion 5: the recursion floors, the window, and the CPython groups that carry trap entries.
uv run pytest -p no:cacheprovider -n 3 -q -rA tests/checks/test_v1_2_hostile_guest.py \
  -k "stack_overflow or recursion or deep_list or c_stack_window or deep_data_limits or dup_is_refused" \
  > /out/criterion5-hostile.txt 2>&1 || true
uv run pytest -p no:cacheprovider -n 3 -q -rA \
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-a]" \
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-b]" \
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-c]" \
  > /out/criterion5-cpython-suites.txt 2>&1 || true
uv run pytest -p no:cacheprovider -n 3 -q -rA tests/checks/test_v1_3_upstream_suites.py \
  -k "test_upstream_class and (cpython-a- or cpython-b- or cpython-c-)" \
  > /out/criterion5-cpython-classes.txt 2>&1 || true
uv run pytest -p no:cacheprovider -q -rA \
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_the_backend_orders_try_tables_alike" \
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_the_guests_configure_results_are_recorded" \
  > /out/checks-a-c.txt 2>&1 || true
echo done > /out/finished
