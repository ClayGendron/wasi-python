#!/bin/sh
# cap_probe_np.py under lower caps on the built set ($SET), both binaries: where numpy's matmul
# starts to exit 1 (the built binary is smaller and starts with less memory than 099's).
set -eu
: "${WORK:?}" "${REPO:?}" "${SET:?}"
HERE=$(cd "$(dirname "$0")" && pwd)
for which in plain snapshot; do
  flag=""
  [ "$which" = plain ] && flag="--no-snapshot"
  for mib in 62 60 58 56 54; do
    out="$WORK/out/p2-thr-$mib-$which.json"
    WASI_PYTHON_ARTIFACTS="$SET" WASI_PYTHON_CACHE="$WORK/cache-set100" uv run --project "$REPO" \
      wasi-python run $flag --memory-bytes $((mib << 20)) --stdin "$HERE/cap_probe_np.py" -- - > "$out"
    uv run --project "$REPO" python -c "
import json, sys
d = json.load(open(sys.argv[1]))
print(sys.argv[2], 'MiB', sys.argv[3], 'exit', d['exit_code'], 'trapped', d['trapped'], '|',
      ' / '.join(d['stdout'].splitlines()), '| stderr:', repr(d['stderr'].strip().splitlines()[-1:]))
" "$out" "$mib" "$which"
  done
done
