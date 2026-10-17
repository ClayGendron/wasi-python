#!/bin/sh
# Native (macOS arm64, host clang) build of the same OpenBLAS tree, same LAPACK choice (C_LAPACK, no Fortran,
# no threads, static), to give the probe a native reference built from the identical patched source.
# usage: build_native.sh <source tree> <build dir>
set -eu
SRC=$1; B=$2
rm -rf "$B"; mkdir -p "$B"; (cd "$SRC" && tar --exclude .git -cf - .) | (cd "$B" && tar -xf -)
cd "$B"
make -j8 libs netlib CC=/usr/bin/cc HOSTCC=/usr/bin/cc TARGET=ARMV8 NOFORTRAN=1 C_LAPACK=1 NO_LAPACKE=1 \
  USE_THREAD=0 USE_LOCKING=0 NUM_THREADS=1 NO_SHARED=1 NO_AFFINITY=1 DYNAMIC_ARCH=0 CFLAGS="-O2 -Wno-return-type"
