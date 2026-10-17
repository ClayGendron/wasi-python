#!/bin/sh
# Re-link the scipy memo's own scipy objects (cython_blas/cython_lapack, and the direct-call probes of f2py's
# _fblas/_flapack prototypes) against an archive; count signature-mismatch warnings whose pair names a scipy object.
# usage: scipy_side.sh <archive> <tag>
W=/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/openblas-void
S=$W/../scipy-research/work/abi
SDK=/Users/claygendron/Git/Repos/wasi_python/build/tools/wasi-sdk-33.0-arm64-macos
for set in cython fblas flapack; do
  case $set in cython) objs="$S/cython_blas.o $S/cython_lapack.o";; fblas) objs="$S/direct_fblas.o";; flapack) objs="$S/direct_flapack.o";; esac
  log=$W/outputs/scipy-$set-$2.log
  $SDK/bin/wasm-ld --no-entry --allow-undefined --no-gc-sections --export-all $objs "$1" -o $W/work/scipy-$set-$2.wasm > $log 2>&1
  total=$(grep -c "signature mismatch" $log)
  scipy=$(grep -A2 "signature mismatch" $log | awk '/signature mismatch/{n=$NF; s=0} /(cython_|direct_)/{if(!s){print n; s=1}}' | sort -u)
  echo "$2 $set: warnings=$total involving-scipy=$(printf '%s\n' "$scipy" | grep -c .)"
  printf '%s\n' "$scipy" | grep . > $W/outputs/scipy-$set-$2.names
done
