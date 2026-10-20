#!/bin/sh
# A private native reference: the oracle's CPython 3.15.0 with numpy 2.5.2's macosx_11_0_arm64 wheel
# (OpenBLAS) and scipy 1.18.1's macosx_12_0_arm64 wheel, each checked against tests/jobs/oracle/uv.lock.
set -eu
: "${WORK:?a scratch folder}" "${REPO:?the main checkout}"
S="$WORK"
DL="$S/dl"
mkdir -p "$DL"
NP=numpy-2.5.2-cp315-cp315-macosx_11_0_arm64.whl
SP=scipy-1.18.1-cp315-cp315-macosx_12_0_arm64.whl
curl -sSfL -o "$DL/$NP" https://files.pythonhosted.org/packages/dd/d1/973ca116000d244897e468ea1aff30b589e5022e3c8744b71706fe33bd57/$NP
curl -sSfL -o "$DL/$SP" https://files.pythonhosted.org/packages/8c/c5/ba929d7feb9b2332f96827c12e0e924b61973b59b4dea383b603372c65ce/$SP
echo "50a68f4bacd8a2b33d8da3d2269d0d78500f86ea582e4786dc10f5ef2c2c6842  $DL/$NP" | shasum -a 256 -c
echo "30f464bee641fa8e282577c7dce027308403213c6ca8270bba73285c91024bc5  $DL/$SP" | shasum -a 256 -c
PY=$REPO/build/oracle/venv/bin/python
UV_CACHE_DIR="$S/uvcache" uv venv --python "$PY" "$S/venv-openblas"
UV_CACHE_DIR="$S/uvcache" uv pip install --python "$S/venv-openblas/bin/python" --no-index --no-deps "$DL/$NP" "$DL/$SP"
