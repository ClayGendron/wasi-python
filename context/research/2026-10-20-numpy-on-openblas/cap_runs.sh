#!/bin/sh
# cap_probe.py under several memory caps (MiB), on main's set; one summary line per run.
set -u
: "${WORK:?a scratch folder}" "${REPO:?a checkout}"
which=${WHICH:-plain}
flag=""
[ "$which" = plain ] && flag="--no-snapshot"
for mib in "$@"; do
  WASI_PYTHON_ARTIFACTS="$WORK/set" WASI_PYTHON_CACHE="$WORK/cache" uv run --project "$REPO" \
    wasi-python run $flag --memory-bytes $((mib << 20)) --stdin "$WORK/bin/cap_probe.py" -- - \
    > "$WORK/out/cap-$which-$mib.json"
  uv run --project "$REPO" python -c "import json,sys; d=json.load(open(sys.argv[1])); print(sys.argv[2], 'MiB', '$which', 'exit', d['exit_code'], 'trapped', d['trapped'], '|', ' / '.join(d['stdout'].splitlines()), '| stderr:', d['stderr'].strip().splitlines()[-1:] )" "$WORK/out/cap-$which-$mib.json" "$mib"
done
