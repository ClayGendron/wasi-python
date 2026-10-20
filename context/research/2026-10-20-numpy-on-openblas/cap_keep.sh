#!/bin/sh
# cap_keep.py under a 256 MiB cap on main's set, both binaries, with and without the early call.
set -eu
: "${WORK:?a scratch folder}" "${REPO:?a checkout}"
for first in 1 0; do
  for which in plain snapshot; do
    flag=""
    [ "$which" = plain ] && flag="--no-snapshot"
    WASI_PYTHON_ARTIFACTS="$WORK/set" WASI_PYTHON_CACHE="$WORK/cache" uv run --project "$REPO" \
      wasi-python run $flag --memory-bytes $((256 << 20)) --env FIRST=$first --stdin "$WORK/bin/cap_keep.py" -- - \
      > "$WORK/out/cap-keep-$which-$first.json"
    uv run --project "$REPO" python -c "import json,sys; d=json.load(open(sys.argv[1])); print('FIRST=' + sys.argv[3], sys.argv[2], 'exit', d['exit_code'], 'trapped', d['trapped'], '|', ' / '.join(d['stdout'].splitlines()), '| stderr:', d['stderr'].strip().splitlines()[-1:])" "$WORK/out/cap-keep-$which-$first.json" "$which" "$first"
  done
done
