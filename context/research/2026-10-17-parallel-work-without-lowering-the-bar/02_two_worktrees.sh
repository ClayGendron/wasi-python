#!/bin/sh
# Two judges in two git worktrees of one scratch clone, run at the same time against the main
# tree's artifact set, read-only. Nothing here touches the main tree's git state: the clone is
# made from it (a read), and every worktree and branch lives in the clone under $SCRATCH.
#
# Usage: sh 02_two_worktrees.sh <main repo> <scratch dir>
# Output: $SCRATCH/out/ (copied into this memo's folder by hand afterwards).
set -eu
MAIN=$1
SCRATCH=$2
ART="$MAIN/build/artifacts"
OUT="$SCRATCH/out"
mkdir -p "$OUT"

snap_main() {  # what the judges must not change in the main tree
  ( cd "$ART" && find . -type f -exec shasum -a 256 {} + | sort -k2 )
  ls -l "$MAIN/build/cwasm-cache" | sort
  shasum -a 256 "$MAIN/build/progress/latest.json"
  ls "$MAIN/build/harness" | sort
}
snap_main > "$OUT/main-before.txt"

git clone -q --no-hardlinks "$MAIN" "$SCRATCH/clone"
cd "$SCRATCH/clone"
git log -1 --format='clone HEAD %H' > "$OUT/clone.txt"
git worktree add -q -b exp-a "$SCRATCH/wt-a"
git worktree add -q -b exp-b "$SCRATCH/wt-b"
git worktree list >> "$OUT/clone.txt"

for w in wt-a wt-b; do
  ( cd "$SCRATCH/$w" && uv sync -q > "$OUT/$w-sync.txt" 2>&1 )
done

run_judge() {  # $1 worktree name
  cd "$SCRATCH/$1"
  start=$(date +%s)
  WASI_PYTHON_ARTIFACTS="$ART" uv run pytest -m "not slow" -q -p no:cacheprovider \
    > "$OUT/$1-judge.txt" 2>&1 && rc=0 || rc=$?
  echo "$1 exit $rc wall $(( $(date +%s) - start ))s" > "$OUT/$1-exit.txt"
}

start=$(date +%s)
run_judge wt-a &
run_judge wt-b &
wait
echo "both done in $(( $(date +%s) - start ))s" > "$OUT/concurrent.txt"

snap_main > "$OUT/main-after.txt"
for w in wt-a wt-b; do
  ( cd "$SCRATCH/$w" && git status --porcelain > "$OUT/$w-status.txt"
    find build -maxdepth 2 | sort > "$OUT/$w-build-tree.txt"
    du -sh build .venv > "$OUT/$w-du.txt" )
done
