#!/bin/sh
# What if a landing merged two acceptances by keeping both history lines (a union merge) instead
# of accepting again? Builds that history from 03's commits and asks the judge's own history check
# (scoreboard.history_errors) what it sees. Runs in the scratch clone only.
#
# Usage: sh 05_union_merge_of_two_acceptances.sh <scratch dir>
set -eu
SCRATCH=$1
OUT="$SCRATCH/out"
cd "$SCRATCH/clone"
a=$(git rev-parse exp-a)
b=$(git log -g --format='%H %s' exp-b | grep ' change wt-b$' | tail -n 1 | cut -d' ' -f1)
mkdir -p "$SCRATCH/union"
git show "$a:context/progress/history.jsonl" > "$SCRATCH/union/history.jsonl"
git show "$b:context/progress/history.jsonl" | tail -n 1 >> "$SCRATCH/union/history.jsonl"
git show "$b:context/progress/accepted.json" > "$SCRATCH/union/accepted.json"
uv run python -I -c '
import sys; sys.path.insert(0, "tests")
from harness import scoreboard
d = sys.argv[1]
h = open(d + "/history.jsonl").read()
a = open(d + "/accepted.json").read()
for e in scoreboard.history_errors(h, a, None):
    print(e)
' "$SCRATCH/union" > "$OUT/union.txt"
echo "a=$a b=$b lines=$(wc -l < "$SCRATCH/union/history.jsonl")" >> "$OUT/union.txt"
