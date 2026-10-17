#!/bin/sh
# Two accepted changes made in parallel, then landed one after the other on the scratch clone's
# main: what conflicts, and what a serial landing lane does about it. Runs after
# 02_two_worktrees.sh, in the same scratch directory; never touches the main tree's git state.
#
# Usage: sh 03_two_acceptances.sh <main repo> <scratch dir>
set -eu
MAIN=$1
SCRATCH=$2
ART="$MAIN/build/artifacts"
OUT="$SCRATCH/out"
export GIT_AUTHOR_NAME=experiment GIT_AUTHOR_EMAIL=experiment@invalid
export GIT_COMMITTER_NAME=experiment GIT_COMMITTER_EMAIL=experiment@invalid

judge() {  # $1 worktree, $2 log name, rest: extra pytest arguments
  w=$1; log=$2; shift 2
  ( cd "$SCRATCH/$w" && WASI_PYTHON_ARTIFACTS="$ART" uv run pytest -m "not slow" -q \
      -p no:cacheprovider "$@" > "$OUT/$log.txt" 2>&1; echo "exit $?" >> "$OUT/$log.txt" )
}

# Two independent changes, each touching the hot file CHANGELOG.md, each accepted in its own tree.
for w in wt-a wt-b; do
  printf '\n- experiment: a line from %s\n' "$w" >> "$SCRATCH/$w/CHANGELOG.md"
done
judge wt-a accept-a --accept "experiment: change a" &
judge wt-b accept-b --accept "experiment: change b" &
wait
for w in wt-a wt-b; do
  ( cd "$SCRATCH/$w" && git add -A CHANGELOG.md context/progress && git commit -q -m "change $w" )
done

# Land A: a fast-forward of the clone's main.
cd "$SCRATCH/clone"
git merge -q --ff-only exp-a && echo "main fast-forwarded to exp-a" > "$OUT/land.txt"

# Land B on top of A by rebase, as a lane would: record what conflicts.
cd "$SCRATCH/wt-b"
if git rebase -q main > "$OUT/rebase-b.txt" 2>&1; then
  echo "rebase: clean" >> "$OUT/land.txt"
else
  git diff --name-only --diff-filter=U > "$OUT/rebase-b-conflicts.txt"
  echo "rebase: conflicts in $(tr '\n' ' ' < "$OUT/rebase-b-conflicts.txt")" >> "$OUT/land.txt"
  # The lane's resolution: the hot file is merged by hand (both lines kept); the progress files
  # are never merged: they are taken from main and the acceptance is made again on the result.
  git show main:CHANGELOG.md > CHANGELOG.md
  printf '\n- experiment: a line from wt-b\n' >> CHANGELOG.md
  git show main:context/progress/accepted.json > context/progress/accepted.json
  git show main:context/progress/history.jsonl > context/progress/history.jsonl
  git add CHANGELOG.md context/progress
  GIT_EDITOR=true git rebase --continue > /dev/null 2>&1 || true
  echo "after rebase: HEAD $(git rev-parse --short HEAD), parent $(git rev-parse --short HEAD^), main $(git rev-parse --short main)" >> "$OUT/land.txt"
fi
judge wt-b reaccept-b --accept "experiment: change b, re-accepted on main"
git add -A context/progress && git commit -q -m "change b: accepted on main"
cd "$SCRATCH/clone"
git merge -q --ff-only exp-b && echo "main fast-forwarded to exp-b" >> "$OUT/land.txt"
# The history is one chain: n, prev and commit of the last three lines.
tail -n 3 context/progress/history.jsonl | uv run --no-project python -I -c '
import json, sys
for l in sys.stdin:
    d = json.loads(l)
    print(d["n"], d["prev"][:12], d["commit"][:10], d["reason"])
' >> "$OUT/land.txt"
git log --format='%h %s' -5 >> "$OUT/land.txt"
judge wt-b final-b
