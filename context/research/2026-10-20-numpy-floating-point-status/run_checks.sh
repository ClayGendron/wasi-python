#!/bin/sh
# Spec 099's drafting runs of its three guest programs: natively (the oracle venv) and in the guest
# on a private copy of main's set, both binaries. Usage:
#   REPO=<main checkout> SET=<a copy of build/artifacts> CACHE=<scratch dir> sh run_checks.sh <out dir>
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${1:?out dir}
for c in check1_singular check2_numpys_own_signals check3_hardware_signals; do
  PYTHONDONTWRITEBYTECODE=1 "$REPO/build/oracle/venv/bin/python" -I "$HERE/$c.py" > "$OUT/$c-native.out" 2>&1
  for which in plain snapshot; do
    flag=""
    [ "$which" = plain ] && flag="--no-snapshot"
    WASI_PYTHON_ARTIFACTS="$SET" WASI_PYTHON_CACHE="$CACHE" uv run --project "$HERE/../../.." \
      wasi-python run $flag --stdin "$HERE/$c.py" -- - > "$OUT/$c-guest-$which.json"
  done
done
