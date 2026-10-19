#!/bin/bash
# One upstream group per pytest process, serially, on the frozen set; wall time per group.
set -u
cd <repos>/wasi_python-063
EV=<repos>/wasi_python/build/reviews-evidence/063-spec/groups
mkdir -p "$EV"
export WASI_PYTHON_ARTIFACTS=<repos>/wasi_python/build/sets/s-4eb5418a2b1bb553
for g in numpy-core numpy-lib numpy-others pandas-frame pandas-groupby pandas-reshape pandas-io-parser pandas-io-formats pandas-tslibs pandas-internals pandas-libs; do
  load0=$(sysctl -n vm.loadavg)
  t0=$(python3 -c 'import time;print(time.time())')
  uv run pytest -p no:cacheprovider -q --progress-dir "$EV/no-baseline" --progress-latest "$EV/$g-latest.json" \
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[$g]" > "$EV/$g.log" 2>&1
  rc=$?
  t1=$(python3 -c 'import time;print(time.time())')
  load1=$(sysctl -n vm.loadavg)
  python3 -c "print(f'$g rc=$rc wall={$t1-$t0:.1f}s load $load0 -> $load1')" | tee -a "$EV/summary.txt"
done
