#!/bin/sh
# Spec 097, criterion 3: the same fuel rows, twice on main's code (5805af0, extracted outside the
# home folder: its guest folders under its own build/harness) and twice on this build (its guest
# folders under GUEST_TMP), on one private set, serially, by node id.
# usage: repeats.sh OUT_DIR NODE_FILE
set -u
WT=/Users/claygendron/Git/Repos/wasi_python/.claude/worktrees/agent-aee0e93a4a535efef
BASE=/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/5c4a788f-6229-4fb4-8a87-05b4e7e5e695/scratchpad/base-097
OUT=$1
NODES=$(cat "$2")
export WASI_PYTHON_ARTIFACTS="$WT/build/097/set"
mkdir -p "$OUT"
for leg in base-1 build-1 base-2 build-2; do
  case $leg in base-*) dir=$BASE ;; *) dir=$WT ;; esac
  echo "$leg start $(date +%H:%M:%S)" >> "$OUT/legs.txt"
  # shellcheck disable=SC2086
  (cd "$dir" && uv run pytest -p no:cacheprovider --progress-latest="$OUT/$leg.json" $NODES) \
    > "$OUT/$leg.log" 2>&1
  echo "$leg exit $? $(date +%H:%M:%S) $(tail -n 1 "$OUT/$leg.log")" >> "$OUT/legs.txt"
done
echo done >> "$OUT/legs.txt"
