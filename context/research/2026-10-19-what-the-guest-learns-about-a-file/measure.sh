#!/bin/bash
# usage: measure.sh <tree> <label> <count>: run every fuel-recording check function <count> times
S=/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/5c4a788f-6229-4fb4-8a87-05b4e7e5e695/scratchpad/083
cd "$1" || exit 1
export WASI_PYTHON_ARTIFACTS=/Users/claygendron/Git/Repos/wasi_python/build/sets/s-c50ca51fae5eb55b-c9dcb5b8
for i in $(seq 1 "$3"); do
  uv run pytest -n 3 -p no:cacheprovider --progress-latest "$S/latest-$2-$i.json" $(cat $S/funcs.txt) > "$S/run-$2-$i.log" 2>&1
  echo "exit $?" >> "$S/run-$2-$i.log"
done
