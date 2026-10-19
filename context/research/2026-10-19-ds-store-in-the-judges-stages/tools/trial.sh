#!/bin/bash
# trial.sh <clone> <label> <P_LITTER mode> <writer: yes|no>: one cpython-archives run by its node id,
# against the private set, with the simulated writer on the clone's CPython stages if asked.
D="${D:?set D to this folder}"
W=$D/w; clone=$1; label=$2; mode=$3; writer=$4
out=$W/trial-$label; rm -f $out.stop $out.writer
mkdir -p $clone/build/harness/cpython
if [ "$writer" = yes ]; then
  uv run --no-project python -I $D/tools/writer.py $clone/build/harness/cpython $out.stop $out.writer 0.3 &
fi
cd $clone
echo "start $(date +%T) mode=$mode writer=$writer" > $out.log
P_LITTER=$mode WASI_PYTHON_ARTIFACTS=$W/set uv run pytest -p no:cacheprovider --progress-latest $out.json \
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-archives]" >> $out.log 2>&1
echo "end $(date +%T) exit=$?" >> $out.log
touch $out.stop; wait
