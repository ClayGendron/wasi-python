#!/bin/bash
# usage: measure.sh <tree> <label> <count>: every fuel-recording check function, <count> times, against
# the tree's private copy of the set (build/set-083), each run's record kept beside this script
H=/Users/claygendron/Git/Repos/wasi_python-083/build/083
cd "$1" || exit 1
export WASI_PYTHON_ARTIFACTS=/Users/claygendron/Git/Repos/wasi_python-083/build/set-083
for i in $(seq 1 "$3"); do
  uv run pytest -n 3 -p no:cacheprovider --progress-latest "$H/latest-$2-$i.json" $(cat $H/funcs.txt) > "$H/run-$2-$i.log" 2>&1
  echo "exit $?" >> "$H/run-$2-$i.log"
done
