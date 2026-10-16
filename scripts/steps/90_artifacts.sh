#!/bin/sh
# Step 90: assemble build/artifacts/ from build/out/ (spec 003, Decision 9; scripts/assemble_artifacts.py).
set -eu
. "$(dirname "$0")/common.sh"
"$HOSTPY" "$HERE/scripts/assemble_artifacts.py" "$HERE"
