#!/bin/sh
# Spec 099's drafting runs of its three guest programs and its singular-detection probe: natively
# (the oracle venv) and in the guest on a private copy of main's set, both binaries. Usage:
#   REPO=<main checkout> SET=<a copy of build/artifacts> CACHE=<scratch dir> sh run_checks.sh <out dir>
# Each guest run writes <name>-guest-<which>.json; the committed <name>-guest-<which>.out is made
# from it by to_out.py (a `# main set …: exit, trapped, stderr` line, then the JSON's stdout field),
# and the singular probe's table by `to_out.py --crosstab <native.out> <guest.out>` (the pre-build
# review's L4). The singular probe was run on the plain binary only.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${1:?out dir}
for c in check1_singular check2_numpys_own_signals check3_hardware_signals singular_probe; do
  PYTHONDONTWRITEBYTECODE=1 "$REPO/build/oracle/venv/bin/python" -I "$HERE/$c.py" > "$OUT/$c-native.out" 2>&1
  for which in plain snapshot; do
    flag=""
    [ "$which" = plain ] && flag="--no-snapshot"
    WASI_PYTHON_ARTIFACTS="$SET" WASI_PYTHON_CACHE="$CACHE" uv run --project "$HERE/../../.." \
      wasi-python run $flag --stdin "$HERE/$c.py" -- - > "$OUT/$c-guest-$which.json"
    uv run --project "$HERE/../../.." python "$HERE/to_out.py" \
      "$OUT/$c-guest-$which.json" "$OUT/$c-guest-$which.out" "$which"
  done
done
