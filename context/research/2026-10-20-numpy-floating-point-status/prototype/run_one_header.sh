#!/bin/sh
# Spec 099's drafting prototype, Decision 3's form: the same three translation units as run.sh,
# compiled with the one header (no C file), linked, run under wasmtime 49.0.3; then the flag word
# is counted in the linked module's name section (one definition, however many objects).
# Usage: REPO=<a checkout with build/tools> sh run_one_header.sh  (writes ./out/)
set -eu
P=$(cd "$(dirname "$0")" && pwd)
SDK=${REPO:?set REPO to a checkout whose build/tools holds the toolchain}/build/tools/wasi-sdk-34.0-arm64-macos
WT=$REPO/build/tools/wasmtime-v49.0.3-aarch64-macos/wasmtime
CC="$SDK/bin/clang --target=wasm32-wasip1 --sysroot=$SDK/share/wasi-sysroot -O2"
CXX="$SDK/bin/clang++ --target=wasm32-wasip1 --sysroot=$SDK/share/wasi-sysroot -O2 -std=c++17 -fno-exceptions"
mkdir -p "$P/out"
cd "$P/out"
H=../npy_fenv_flags_one_header.h
$CC -include $H -c ../ieee_like.c -o ieee2.o
$CXX -include $H -c ../half_like.cpp -o half2.o
$CC -c ../main.c -o main2.o
$CXX ieee2.o half2.o main2.o -Wl,--export=wasi_python_fe_flags -o one_header.wasm
"$WT" run one_header.wasm
echo "== the flag word in each object (W = weak definition)"
"$SDK/bin/llvm-nm" ieee2.o half2.o | grep wasi_python_fe_flags
echo "== defined symbols named wasi_python_fe in the linked module"
"$SDK/bin/llvm-nm" one_header.wasm | grep wasi_python_fe || echo "(none by name: inlined; the word is exported below)"
