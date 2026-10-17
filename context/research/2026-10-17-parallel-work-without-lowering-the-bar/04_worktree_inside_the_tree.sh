#!/bin/sh
# Does a worktree placed inside the repository (Claude Code's default, .claude/worktrees/<name>/)
# change the judge of the tree that holds it? paths.judge_files() walks the whole tree for a
# stray conftest.py. Runs in the scratch clone only.
#
# Usage: sh 04_worktree_inside_the_tree.sh <scratch dir>
set -eu
SCRATCH=$1
OUT="$SCRATCH/out"
cd "$SCRATCH/clone"
probe() {
  uv run python -I -c '
import sys; sys.path.insert(0, "tests")
from harness import paths
fs = paths.judge_files()
inside = [f for f in fs if f.startswith(".claude/")]
print(len(fs), paths.judge_hash(fs)[:12], inside)
'
}
echo "before: $(probe)" > "$OUT/inside.txt"
git worktree add -q -b exp-inside .claude/worktrees/inside
echo "after:  $(probe)" >> "$OUT/inside.txt"
git status --porcelain --untracked-files=normal | head -n 3 >> "$OUT/inside.txt"
git worktree remove .claude/worktrees/inside
git branch -q -D exp-inside
echo "removed: $(probe)" >> "$OUT/inside.txt"
