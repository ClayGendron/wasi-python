#!/bin/sh
# Spec 080: the own-runner shard's first files, in its order, on Linux; then each guarded test alone.
cd /Users/claygendron/Git/Repos/wasi_python-080
uv run pytest -p no:cacheprovider -q tests/test_api.py tests/unit/test_async_tools.py tests/unit/test_cli.py tests/unit/test_guest_tools.py tests/unit/test_runner_async.py 2>&1 | grep -E "passed|failed|^FAILED" | sed 's/^/ORDER: /'
uv run pytest -p no:cacheprovider -q tests/unit/test_runner_async.py 2>&1 | grep -E "passed|failed|^FAILED" | sed 's/^/ALONE: /'
uv run pytest -p no:cacheprovider -q -p no:faulthandler tests/unit/test_runner_async.py 2>&1 | grep -E "passed|failed|^FAILED" | sed 's/^/ALONE, no faulthandler plugin: /'
uv run python - <<'PY'
import ctypes, signal, sys
sys.path.insert(0, "src")
from wasi_python import runner
print("PROBE: no engine yet:", runner._trap_handlers_ready())
import faulthandler; faulthandler.enable()
print("PROBE: faulthandler on, still no engine:", runner._trap_handlers_ready())
import wasmtime; wasmtime.Engine()
print("PROBE: after the first engine:", runner._trap_handlers_ready())
PY
