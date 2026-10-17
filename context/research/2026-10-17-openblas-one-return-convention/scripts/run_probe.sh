#!/bin/sh
# Build the probe for wasm32-wasip1 against an archive and run each routine under the pinned wasmtime;
# build it natively against the native archive and run the same. One process per routine.
# usage: run_probe.sh <wasm archive> <native archive or -> <tag>
set -u
W=/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/openblas-void
R=/Users/claygendron/Git/Repos/wasi_python
SDK=$R/build/tools/wasi-sdk-33.0-arm64-macos
WT=$R/build/tools/wasmtime-v49.0.3-aarch64-macos/wasmtime
O=$W/work/probe-$3; mkdir -p $O
ROUTINES="dgesv dgetrf dpotrf dgeqrf dsyev dsyevr dgesdd64 dgesdd zgesdd dgees"
$SDK/bin/clang --target=wasm32-wasip1 -O2 -D_WASI_EMULATED_MMAN $W/probes/lapack_void.c "$1" -lwasi-emulated-mman -lm \
  -o $O/lapack_void.wasm > $W/outputs/probe-link-$3.log 2>&1
echo "wasm link exit=$? mismatch warnings=$(grep -c 'signature mismatch' $W/outputs/probe-link-$3.log)"
: > $W/outputs/probe-wasm-$3.txt
for r in $ROUTINES; do
  $WT run $O/lapack_void.wasm $r >> $W/outputs/probe-wasm-$3.txt 2> $O/$r.err
  rc=$?; echo "$r.exit $rc" >> $W/outputs/probe-wasm-$3.txt
  [ $rc = 0 ] || grep -m2 "signature_mismatch\|wasm trap" $O/$r.err | sed "s/^/$r.trap /" >> $W/outputs/probe-wasm-$3.txt
done
if [ "$2" != "-" ]; then
  /usr/bin/cc -O2 $W/probes/lapack_void.c "$2" -lm -o $O/lapack_void.native
  : > $W/outputs/probe-native-$3.txt
  for r in $ROUTINES; do $O/lapack_void.native $r >> $W/outputs/probe-native-$3.txt; echo "$r.exit $?" >> $W/outputs/probe-native-$3.txt; done
fi
grep "\.exit\|\.trap\|info\|_ok\|sdim\|select" $W/outputs/probe-wasm-$3.txt
