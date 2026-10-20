#!/bin/sh
# Checks 2 and 3's programs (the drafting probes) on 099's built set, both binaries.
set -eu
: "${WORK:?a scratch folder}" "${REPO:?a checkout}"
for which in plain snapshot; do
  for p in singular300 nan_probe xerbla_probe; do
    sh "$WORK/bin/guest_on.sh" "$WORK/set099" "$WORK/cache-099" "$WORK/bin/$p.py" "$WORK/out/099-$p-$which.json" "$which"
    echo "done $p $which"
  done
done
