#!/bin/bash
# usage: measure.sh <tree> <label>
S=/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/5c4a788f-6229-4fb4-8a87-05b4e7e5e695/scratchpad/081
cd "$1" || exit 1
export WASI_PYTHON_ARTIFACTS=/Users/claygendron/Git/Repos/wasi_python/build/sets/s-c50ca51fae5eb55b
uv run pytest -n 3 -p no:cacheprovider --progress-latest "$S/latest-$2.json" $(cat $S/funcs.txt) > "$S/run-$2.log" 2>&1
echo "exit $?" >> "$S/run-$2.log"
