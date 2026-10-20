#!/bin/sh
# Inside a research container (spec 086 at its rebase onto 45b917c, criteria 3 and 5, Decision
# 10's trigger): clone the branch (/src, read-only) to /work/wasi_python, stage verified pins from
# /pins (step 00 verifies every one against SHA256SUMS again and fetches this host's SDK), build N
# times from an empty build/, keep each SHA256SUMS, then run criterion 5's checks, spec 065's
# trap entries and the rebase's new checks on the last set. Outputs to /out.
set -eu
N=${1:-1}
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
    cp build/artifacts/MANIFEST /out/MANIFEST-$n
  fi
  [ "$status" = 0 ] || exit "$status"
  n=$((n + 1))
done
T=tests/checks
uv run pytest -p no:cacheprovider -n 3 -q -rA $T/test_v1_2_hostile_guest.py \
  -k "stack_overflow or recursion or deep_list or c_stack_window or deep_data_limits or dup_is_refused or siphash13" \
  > /out/criterion5-hostile.txt 2>&1 || true
uv run pytest -p no:cacheprovider -n 3 -q -rA \
  "$T/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-a]" \
  "$T/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-b]" \
  "$T/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-c]" \
  > /out/criterion5-cpython-suites.txt 2>&1 || true
uv run pytest -p no:cacheprovider -n 3 -q -rA $T/test_v1_3_upstream_suites.py \
  -k "test_upstream_trap or (test_upstream_class and (cpython-a- or cpython-b- or cpython-c-))" \
  > /out/criterion5-cpython-classes-and-traps.txt 2>&1 || true
cp build/progress/latest.json /out/traps-latest.json 2>/dev/null || true
uv run pytest -p no:cacheprovider -q -rA \
  "$T/test_v1_5_rebuild_from_pins.py::test_the_backend_orders_try_tables_alike" \
  "$T/test_v1_5_rebuild_from_pins.py::test_the_guests_configure_results_are_recorded" \
  "$T/test_v1_1_artifact_set.py::test_a_missing_stdlib_module_says_why" \
  > /out/checks-a-c-zip.txt 2>&1 || true
echo done > /out/finished
