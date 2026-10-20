#!/bin/sh
# Spec 099's drafting prototype: numpy's fenv pattern compiled for wasm32-wasip1 with wasi-sdk 34,
# without and with the force-included header, each run under wasmtime 49.0.3.
set -eu
# Usage: REPO=<a checkout with build/tools> sh run.sh  (run in a scratch copy of this folder: it
# writes ./out/; the drafting run was in the session's scratchpad, run.out its output).
P=$(cd "$(dirname "$0")" && pwd)
SDK=${REPO:?set REPO to a checkout whose build/tools holds the toolchain}/build/tools/wasi-sdk-34.0-arm64-macos
WT=$REPO/build/tools/wasmtime-v49.0.3-aarch64-macos/wasmtime
CC="$SDK/bin/clang --target=wasm32-wasip1 --sysroot=$SDK/share/wasi-sysroot -O2"
CXX="$SDK/bin/clang++ --target=wasm32-wasip1 --sysroot=$SDK/share/wasi-sysroot -O2 -std=c++17 -fno-exceptions"
mkdir -p "$P/out"
cd "$P/out"

echo "== without the header (today's numpy build)"
$CC -c ../ieee_like.c -o ieee0.o
$CXX -c ../half_like.cpp -o half0.o
$CC -c ../main.c -o main.o
$CXX ieee0.o half0.o main.o -o without.wasm
"$WT" run without.wasm

echo "== with the header (the recipe)"
$CC -include ../npy_fenv_flags.h -c ../ieee_like.c -o ieee1.o
$CXX -include ../npy_fenv_flags.h -c ../half_like.cpp -o half1.o
$CC -c ../npy_fenv_flags.c -o flags.o
$CXX ieee1.o half1.o flags.o main.o -o with.wasm
"$WT" run with.wasm

echo "== imports of with.wasm (no new import)"
"$SDK/bin/llvm-nm" -u flags.o ieee1.o half1.o | sort -u
