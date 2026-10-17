#!/bin/sh
# Experiment: OpenBLAS 0.3.34 for wasm32-wasip1, static, no Fortran (C LAPACK), no threads.
# Builds in a copy of the pristine tree; the pristine tree under work/src is diffed against the tarball after.
set -eu
S=/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/scipy-research
SDK=/Users/claygendron/Git/Repos/wasi_python/build/tools/wasi-sdk-33.0-arm64-macos
TARGET=${1:-WASM128_GENERIC}
B=$S/work/openblas-$TARGET
rm -rf "$B"; mkdir -p "$B"; tar -xzf $S/dl/openblas/OpenBLAS-0.3.34.tar.gz -C "$B" --strip-components=1
cd "$B"
make -j8 libs netlib \
  CC="$SDK/bin/clang --target=wasm32-wasip1" HOSTCC=/usr/bin/cc \
  AR="$SDK/bin/llvm-ar" RANLIB="$SDK/bin/llvm-ranlib" \
  TARGET=$TARGET ARCH=wasm OSNAME=WASI NOFORTRAN=1 C_LAPACK=1 NO_LAPACKE=1 NO_CBLAS=0 \
  USE_THREAD=0 USE_LOCKING=0 NUM_THREADS=1 NO_SHARED=1 NO_AFFINITY=1 DYNAMIC_ARCH=0 \
  CFLAGS="-O2 -Wno-return-type -D_WASI_EMULATED_SIGNAL -D_WASI_EMULATED_PROCESS_CLOCKS -D_WASI_EMULATED_GETPID -D_WASI_EMULATED_MMAN -DNO_SYSV_IPC -include sched.h -DARCH_WASM -I/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/scipy-research/scripts/stub-include"
