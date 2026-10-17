#!/bin/sh
# Build OpenBLAS for wasm32-wasip1 from a source tree, in a fresh copy (the source tree stays clean).
# Flags and toolchain are the scipy memo's scripts/build_openblas.sh, unchanged; only the paths differ.
# usage: build_wasm.sh <source tree> <build dir>
set -eu
W=/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/openblas-void
SDK=/Users/claygendron/Git/Repos/wasi_python/build/tools/wasi-sdk-33.0-arm64-macos
SRC=$1; B=$2; TARGET=WASM128_GENERIC
rm -rf "$B"; mkdir -p "$B"; (cd "$SRC" && tar --exclude .git -cf - .) | (cd "$B" && tar -xf -)
cd "$B"
make -j8 libs netlib \
  CC="$SDK/bin/clang --target=wasm32-wasip1" HOSTCC=/usr/bin/cc \
  AR="$SDK/bin/llvm-ar" RANLIB="$SDK/bin/llvm-ranlib" \
  TARGET=$TARGET ARCH=wasm OSNAME=WASI NOFORTRAN=1 C_LAPACK=1 NO_LAPACKE=1 NO_CBLAS=0 \
  USE_THREAD=0 USE_LOCKING=0 NUM_THREADS=1 NO_SHARED=1 NO_AFFINITY=1 DYNAMIC_ARCH=0 \
  CFLAGS="-O2 -Wno-return-type -D_WASI_EMULATED_SIGNAL -D_WASI_EMULATED_PROCESS_CLOCKS -D_WASI_EMULATED_GETPID -D_WASI_EMULATED_MMAN -DNO_SYSV_IPC -include sched.h -DARCH_WASM -I$W/scripts/stub-include"
