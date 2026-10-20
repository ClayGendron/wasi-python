#!/bin/sh
# Spec 097's probe: does macOS's folder-size cache write .DS_Store under the home folder (control)
# and under the per-user temporary folder (candidate)? Two identical trees, changed every 5 s.
# usage: probe.sh HOME_TREE TMP_TREE LOG ROUNDS
set -u
H=$1 T=$2 LOG=$3 N=$4
for d in "$H" "$T"; do
  mkdir -p "$d/root/tmp/work" "$d/lib/test"
  echo seed > "$d/root/tmp/work/a.txt"
done
: > "$LOG"
i=0
while [ "$i" -lt "$N" ]; do
  for d in "$H" "$T"; do
    echo "$i" > "$d/root/tmp/work/f$((i % 7)).txt"
    echo "$i" > "$d/root/x$((i % 3)).txt"
  done
  for d in "$H" "$T"; do
    find "$d" -name '.DS_Store' -o -name '._*' | while IFS= read -r f; do
      echo "round $i $(date +%H:%M:%S) $f" >> "$LOG"
    done
  done
  i=$((i + 1))
  sleep 5
done
echo "done $(date +%H:%M:%S)" >> "$LOG"
echo "home tree litter: $(find "$H" -name '.DS_Store' | wc -l | tr -d ' ')" >> "$LOG"
echo "temp tree litter: $(find "$T" -name '.DS_Store' | wc -l | tr -d ' ')" >> "$LOG"
find "$H" "$T" -name '.DS_Store' >> "$LOG"
