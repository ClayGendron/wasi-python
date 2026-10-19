#!/bin/sh
# $1 = src dir, $2 = artifact dir; each order of spec 071's criterion 11 child in its own process
export PYTHONPATH=$1 WASI_PYTHON_ARTIFACTS=$2 WASI_PYTHON_CACHE=/tmp/wpcache
mkdir -p /tmp/wpcache && chmod 700 /tmp/wpcache
python -c "import wasi_python; print('warm', wasi_python.run(['-c','print(1)']).exit_code)"
for o in none before after before-then-disable after-then-disable signal-after; do
  timeout 120 python $(dirname $0)/child.py $o > /tmp/o.txt 2>&1; rc=$?
  echo "$o | rc $rc | $(tail -1 /tmp/o.txt | cut -c1-160)"
done
