#!/bin/sh
# The 300-matrix probe natively on numpy's OpenBLAS wheel under each OpenBLAS kernel set the arm64
# DYNAMIC_ARCH build carries (OPENBLAS_CORETYPE), to see whether "native" is one answer.
set -u
: "${WORK:?a scratch folder}" "${REPO:?the main checkout}"
S="$WORK"
cd "$S"
for ct in ARMV8 CORTEXA57 NEOVERSEN1 NEOVERSEV1 VORTEX; do
  OPENBLAS_CORETYPE=$ct OPENBLAS_VERBOSE=2 PYTHONDONTWRITEBYTECODE=1 venv-openblas/bin/python -I bin/singular300.py > "out/singular300-native-openblas-$ct.out" 2>&1
  echo "== $ct"; grep -v "^inv \|^gesv \|^getrf" "out/singular300-native-openblas-$ct.out"
done
