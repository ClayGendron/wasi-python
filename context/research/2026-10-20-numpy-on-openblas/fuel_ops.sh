#!/bin/sh
# Fuel of each operation in fuel_op.py on spec 100's private copy of main's set (plain binary).
set -eu
: "${WORK:?a scratch folder}" "${REPO:?the main checkout}"
S="$WORK"
WT="$REPO"
for op in none np_inv ob_gesv np_svd ob_gesdd np_eigh ob_syevd np_matmul ob_gemm; do
  WASI_PYTHON_ARTIFACTS="$S/set" WASI_PYTHON_CACHE="$S/cache" uv run --project "$WT" \
    wasi-python run --no-snapshot --fuel 100000000000000 --env OP=$op --stdin "$S/bin/fuel_op.py" -- - > "$S/out/fuel-$op.json"
  uv run --project "$WT" python -c "import json,sys; d=json.load(open(sys.argv[1])); print(sys.argv[2], d['exit_code'], d['fuel_used'], d['stdout'].strip(), d['stderr'][-200:])" "$S/out/fuel-$op.json" $op
done
