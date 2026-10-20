#!/bin/sh
# Spec 100's criterion 6 probes on the built set ($SET) and, for fuel, against the base ($BASE, 099's
# built set). One summary line per run on stdout; each run's JSON under $WORK/out/p2-*.json.
# Usage: WORK=... REPO=<a checkout> SET=... BASE=... sh phase2_probes.sh
set -eu
: "${WORK:?}" "${REPO:?}" "${SET:?}" "${BASE:?}"
HERE=$(cd "$(dirname "$0")" && pwd)
run() { # tag set which extra-args... -- prog
  tag=$1 set=$2 which=$3; shift 3
  flag=""
  [ "$which" = plain ] && flag="--no-snapshot"
  out="$WORK/out/p2-$tag-$which.json"
  WASI_PYTHON_ARTIFACTS="$set" WASI_PYTHON_CACHE="$WORK/cache-$(basename "$set")" uv run --project "$REPO" \
    wasi-python run $flag --fuel 100000000000000 "$@" > "$out"
  uv run --project "$REPO" python -c "
import json, sys
d = json.load(open(sys.argv[1]))
out = ' / '.join(d['stdout'].splitlines())
print(sys.argv[2], sys.argv[3], 'exit', d['exit_code'], 'trapped', d['trapped'], 'fuel', d['fuel_used'],
      '|', out[:200], '| stderr:', repr(d['stderr'].strip().splitlines()[-1:]))
" "$out" "$tag" "$which"
}
for which in plain snapshot; do
  for mib in 64 68 72; do
    run "cap-np-$mib" "$SET" "$which" --memory-bytes $((mib << 20)) --stdin "$HERE/cap_probe_np.py" -- -
  done
  for first in 0 1; do
    run "keep-np-$first" "$SET" "$which" --memory-bytes $((256 << 20)) --env FIRST=$first \
      --stdin "$HERE/cap_keep_np.py" -- -
  done
  run "singular300" "$SET" "$which" --stdin "$HERE/singular300.py" -- -
  run "nan" "$SET" "$which" --stdin "$HERE/nan_probe.py" -- -
done
for set in "$SET" "$BASE"; do
  name=$(basename "$set")
  for op in none np_matmul3 np_inv3; do
    run "small-$name-$op" "$set" plain --env OP=$op --stdin "$HERE/fuel_small.py" -- -
  done
  for op in none np_inv np_svd np_eigh np_matmul; do
    run "ops-$name-$op" "$set" plain --env OP=$op --stdin "$HERE/fuel_op.py" -- -
  done
done
