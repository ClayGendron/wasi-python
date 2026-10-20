#!/bin/sh
# guest.sh with fuel counted. Usage: guest_fuel.sh <prog.py> <out.json> [plain|snapshot]
set -eu
: "${WORK:?a scratch folder}" "${REPO:?the main checkout}"
S="$WORK"
WT="$REPO"
flag=""
[ "${3:-plain}" = plain ] && flag="--no-snapshot"
WASI_PYTHON_ARTIFACTS="$S/set" WASI_PYTHON_CACHE="$S/cache" uv run --project "$WT" \
  wasi-python run $flag --fuel 100000000000000 --stdin "$1" -- - > "$2"
grep -o '"fuel_used": [0-9]*' "$2"
