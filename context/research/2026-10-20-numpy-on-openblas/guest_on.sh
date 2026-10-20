#!/bin/sh
# Run one program in the guest on a named private set. Usage: guest_on.sh <set dir> <cache dir> <prog.py> <out.json> [plain|snapshot]
set -eu
: "${REPO:?a checkout}"
flag=""
[ "${5:-plain}" = plain ] && flag="--no-snapshot"
WASI_PYTHON_ARTIFACTS="$1" WASI_PYTHON_CACHE="$2" uv run --project "$REPO" \
  wasi-python run $flag --stdin "$3" -- - > "$4"
