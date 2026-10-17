#!/bin/sh
# Per-call cost of the shadow: each mode, N = 0 and 20000, a real grant's file and a provider's.
# usage: sh micro.sh ART SCRATCH   (from the repository root)
D=context/research/2026-10-17-a-filesystem-provider-for-the-runner
for spec in "plain /data/in.csv" "passthru /data/in.csv" "provider /data/in.csv" "provider /work/seed.txt"; do
  set -- $1 $2 $spec
  for n in 0 20000; do
    sed -e "s|^N, WHERE = .*|N, WHERE = $n, \"$4\"|" $D/micro.py > $2/micro_run.py
    for rep in 1 2 3; do
      echo "== mode=$3 where=$4 N=$n rep=$rep"
      uv run --no-sync python $D/shadow.py $1 $2/run $3 $2/micro_run.py | grep -E "^mode|^shadowed"
    done
  done
done
