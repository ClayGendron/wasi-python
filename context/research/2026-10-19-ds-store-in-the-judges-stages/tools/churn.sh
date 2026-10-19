#!/bin/bash
# churn.sh <seconds> <dir>...: every second, create and remove files under each dir's cpython/run-abc/tmp and a guest-* sibling
end=$(( $(date +%s) + $1 )); shift
while [ $(date +%s) -lt $end ]; do
  for d in "$@"; do
    echo $RANDOM > "$d/cpython/run-abc/tmp/w$RANDOM.txt"; rm -f $(ls "$d"/cpython/run-abc/tmp/w*.txt | head -1)
    mkdir -p "$d/guest-$RANDOM/x"; rm -rf $(ls -d "$d"/guest-* | head -1)
  done
  sleep 1
done
