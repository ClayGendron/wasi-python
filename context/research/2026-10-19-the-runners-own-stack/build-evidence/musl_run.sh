#!/bin/sh
apk add -q uv >/dev/null 2>&1
export PYTHONPATH=/w/src WASI_PYTHON_ARTIFACTS=/w/build/artifacts
for v in 3.14 3.13 3.14.0; do
  uv run -q --no-project --python $v --with wasmtime==49.0.0 python /w/build/musl/probe.py; echo "exit $?"
done
