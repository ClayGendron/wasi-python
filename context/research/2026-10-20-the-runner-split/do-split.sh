#!/bin/sh
# The whole mechanical move, reproducible: restore 103's runner.py, split, keep the pre-format
# copies (the residue script's middle term), move the one comment, sort imports, format.
set -e
cp build/104/runner-base.py src/wasi_python/runner.py
uv run python build/104/split.py
mkdir -p build/104/preformat
for f in _limits _platform _artifacts _engines _private_dirs _zip _places _home _call _sessions runner; do
  cp src/wasi_python/$f.py build/104/preformat/$f.py
done
uv run python build/104/wrap_comment.py
cd src/wasi_python
uv run ruff check --fix --select I _limits.py _platform.py _artifacts.py _engines.py _private_dirs.py _zip.py _places.py _home.py _call.py _sessions.py runner.py
uv run ruff format _limits.py _platform.py _artifacts.py _engines.py _private_dirs.py _zip.py _places.py _home.py _call.py _sessions.py runner.py
