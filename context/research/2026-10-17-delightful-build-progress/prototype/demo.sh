#!/bin/sh
# Run the prototype over three fake steps (the last fails). Usage: demo.sh <work dir> [steps...]
set -eu
HERE=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
W=$1; shift
mkdir -p "$W/logs" "$W/artifacts"
cd "$W"  # paths print relative, as build/logs/<step>.log does
. "$HERE/progress.sh"
[ -n "${FAKE_CLOCK:-}" ] && progress_now() { c=$(cat "$FAKE_CLOCK"); echo $((c + 7)) > "$FAKE_CLOCK"; echo "$c"; }
STEPS=${*:-a_fetch b_compile c_fails}
set -- $STEPS
progress_init "$#" logs/timings.tsv
for s in $STEPS; do
  progress_step "$s" "$HERE/steps/$s.sh" "logs/$s.log" || exit 1
done
progress_finish artifacts
