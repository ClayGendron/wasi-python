#!/bin/sh
# Install each candidate alone (no deps) into pkgs/<name>/, binary wheels only, for CPython 3.15 (fallback 3.14).
set -u
PY315=/Users/claygendron/Git/Repos/wasi_python/build/tools/python/bin/python3
P=$(cd "$(dirname "$0")/.." && pwd)
for spec in "$@"; do
  name=$(echo "$spec" | sed 's/[=<>].*//')
  d="$P/pkgs/$name"
  [ -d "$d" ] && continue
  if uv pip install -q --python "$PY315" --target "$d" --no-deps --only-binary :all: "$spec" >"$P/out/install-$name.log" 2>&1; then
    echo "$name 3.15 ok"
  elif rm -rf "$d" && uv pip install -q --python 3.14 --target "$d" --no-deps --only-binary :all: "$spec" >>"$P/out/install-$name.log" 2>&1; then
    echo "$name 3.14 ok"
  else
    echo "$name FAILED"; rm -rf "$d"
  fi
done
