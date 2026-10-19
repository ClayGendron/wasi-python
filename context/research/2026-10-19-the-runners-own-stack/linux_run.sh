#!/bin/sh
# Inside a container: the host's thread facts, then probe 5 at W = 8 MiB.
set -e
export SRC=/src CACHE=/tmp/cache WASI_PYTHON_ARTIFACTS=/set
mkdir -p /tmp/cache && chmod 700 /tmp/cache
cd /work
PY="uv run -q --no-project --python 3.14 --with wasmtime==49.0.0 python"
$PY env_facts.py
W=8388608
for shape in list-door list; do
  E=$($PY p5_threadsize.py edge $W 33554432 $shape 20000 60000 | tail -1); echo "$E"
  N=${E##* }
  $PY p5b.py $W $shape:$N 7340032 10485760 4096 | tail -1
done
$PY p5b.py $W free100k 7340032 10485760 4096 | tail -1
for t in main 1048576; do $PY p5_threadsize.py grid $W free100k $t | tail -1; done
