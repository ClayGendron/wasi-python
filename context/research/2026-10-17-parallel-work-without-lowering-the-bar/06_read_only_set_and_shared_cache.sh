#!/bin/sh
# Two sharing questions, in the scratch worktree wt-a only.
# 1. Does the judge need to write to the artifact set? A copy of the set with every write bit
#    removed is judged (fast tier).
# 2. Can worktrees share one compiled-module cache through a symlink? The runner is asked to use
#    a symlink to a private directory as its cache, and reports how it got its module.
#
# Usage: sh 06_read_only_set_and_shared_cache.sh <main repo> <scratch dir>
set -eu
MAIN=$1
SCRATCH=$2
OUT="$SCRATCH/out"
RO="$SCRATCH/ro-set"
rm -rf "$RO"
cp -R "$MAIN/build/artifacts" "$RO"
chmod -R a-w "$RO"
cd "$SCRATCH/wt-a"
WASI_PYTHON_ARTIFACTS="$RO" uv run pytest -m "not slow" -q -p no:cacheprovider \
  > "$OUT/ro-judge.txt" 2>&1 && echo "exit 0" >> "$OUT/ro-judge.txt" || echo "exit $?" >> "$OUT/ro-judge.txt"

mkdir -p "$SCRATCH/shared-cache"
chmod 700 "$SCRATCH/shared-cache"
ln -sfn "$SCRATCH/shared-cache" "$SCRATCH/cache-link"
for cache in "$SCRATCH/shared-cache" "$SCRATCH/cache-link"; do
  WASI_PYTHON_ARTIFACTS="$RO" uv run python -c '
import sys, warnings
from wasi_python import run, runner
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    done = run(["-c", "pass"], cache_dir=sys.argv[1])
print(sys.argv[1].rsplit("/", 1)[-1], done.exit_code, runner.stats(), [str(x.message)[:60] for x in w])
' "$cache" >> "$OUT/cache-link.txt" 2>&1
done
ls "$SCRATCH/shared-cache" >> "$OUT/cache-link.txt"
chmod -R u+w "$RO"
