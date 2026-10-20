#!/bin/sh
# Run one program in the guest on spec 100's private copy of main's set. Usage: guest.sh <prog.py> <out.json> [plain|snapshot]
set -eu
: "${WORK:?a scratch folder}" "${REPO:?the main checkout}"
S="$WORK"
WT="$REPO"
flag=""
[ "${3:-plain}" = plain ] && flag="--no-snapshot"
WASI_PYTHON_ARTIFACTS="$S/set" WASI_PYTHON_CACHE="$S/cache" uv run --project "$WT" \
  wasi-python run $flag --stdin "$1" -- - > "$2"
