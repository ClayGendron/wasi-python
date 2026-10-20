#!/bin/sh
# Spec 100's three guest check programs: natively on numpy's OpenBLAS wheel ($WORK/venv-openblas,
# stdout and stderr apart) and in the guest on a set ($SET, compile cache $CACHE), both binaries.
# Usage: WORK=... REPO=<a checkout> SET=... CACHE=... TAG=<name> sh run_checks.sh
set -eu
: "${WORK:?}" "${REPO:?}" "${SET:?}" "${CACHE:?}" "${TAG:?}"
HERE=$(cd "$(dirname "$0")" && pwd)
for c in check1_config check2_rank_deficient check3_errors; do
  PYTHONDONTWRITEBYTECODE=1 "$WORK/venv-openblas/bin/python" -I "$HERE/$c.py" \
    > "$HERE/$c-native-openblas.out" 2> "$HERE/$c-native-openblas.err"
  for which in plain snapshot; do
    flag=""
    [ "$which" = plain ] && flag="--no-snapshot"
    WASI_PYTHON_ARTIFACTS="$SET" WASI_PYTHON_CACHE="$CACHE" uv run --project "$REPO" \
      wasi-python run $flag --stdin "$HERE/$c.py" -- - > "$WORK/out/$c-$TAG-$which.json"
    uv run --project "$REPO" python -c "
import json, sys
d = json.load(open(sys.argv[1]))
head = f'# {sys.argv[3]}, {sys.argv[4]} binary: exit {d[\"exit_code\"]}, trapped {d[\"trapped\"]}, stderr {d[\"stderr\"]!r}\n'
open(sys.argv[2], 'w').write(head + d['stdout'])
" "$WORK/out/$c-$TAG-$which.json" "$HERE/$c-$TAG-$which.out" "$TAG" "$which"
  done
done
