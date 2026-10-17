#!/bin/sh
# For every commit that changed context/progress/accepted.json: is the accepted "commit" the
# commit's parent (the run was taken on the tree just before the acceptance was committed)?
# Read-only: git log and git show only. Usage: sh 01_accept_baselines.sh <repo>
repo=${1:-.}
git -C "$repo" log --format=%H -- context/progress/accepted.json | while read -r c; do
  p=$(git -C "$repo" rev-parse "$c^" 2>/dev/null)
  a=$(git -C "$repo" show "${c}:context/progress/accepted.json" | sed -n 's/^ "commit": "\([0-9a-f]*\)".*/\1/p' | head -n 1)
  if [ "$a" = "$p" ]; then rel=parent
  elif git -C "$repo" merge-base --is-ancestor "$a" "$c" 2>/dev/null; then rel="ancestor+$(git -C "$repo" rev-list --count "$a..$c")"
  else rel=NOT-AN-ANCESTOR; fi
  printf '%s accepted=%s %s\n' "$(echo "$c" | cut -c1-8)" "$(echo "$a" | cut -c1-8)" "$rel"
done
