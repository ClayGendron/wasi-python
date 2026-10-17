#!/bin/sh
# Build the artifact set from pinned inputs (spec 003): one line per step, the full log under
# build/logs/<step>.log.
#
#   scripts/build.sh               every step, in order
#   scripts/build.sh 60 70 80 90   only the named steps (by number or full name)
#
# Downloads come first: scripts/00_download.sh fetches and verifies every pin.
set -eu
HERE=$(CDPATH= cd "$(dirname "$0")/.." && pwd -P)
export SOURCE_DATE_EPOCH=1767225600  # 2026-01-01T00:00:00Z: a constant, so rebuilds are equal
export UV_CACHE_DIR="$HERE/build/uv-cache"
export PYTHONHASHSEED=0
export LC_ALL=C  # one collation on every host: each step's `sort` orders bytes alike (spec 012)
mkdir -p "$HERE/build/logs"
. "$HERE/scripts/steps/remove.sh"

ALL="00_download 10_tools 20_cpython 30_zlib 35_stdlib_libs 40_numpy 50_pandas 60_link 70_zip 80_snapshot 90_artifacts"
if [ "$#" -eq 0 ]; then
  STEPS=$ALL
else
  STEPS=""
  for want in "$@"; do
    found=""
    for step in $ALL; do
      case "$step" in "$want"|"$want"_*) found=$step;; esac
    done
    [ -n "$found" ] || { echo "ERROR build: no step $want (steps: $ALL)"; exit 2; }
    STEPS="$STEPS $found"
  done
fi

for step in $STEPS; do
  case "$step" in
    00_*) script="$HERE/scripts/00_download.sh";;
    *) script="$HERE/scripts/steps/$step.sh"
       # A rebuild never leaves an older set that looks current.
       remove "$HERE/build/artifacts" "$HERE/build/artifacts.new";;
  esac
  log="$HERE/build/logs/$step.log"
  if sh "$script" > "$log" 2>&1; then
    echo "ok $step: $(tail -n 1 "$log" | cut -c1-120)"
  else
    echo "ERROR $step: $(grep -E 'ERROR|[Ee]rror' "$log" | tail -n 1 | cut -c1-160) (log: build/logs/$step.log)"
    exit 1
  fi
done
