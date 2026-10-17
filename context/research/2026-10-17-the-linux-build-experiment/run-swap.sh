#!/bin/sh
# Hypothesis test: the reactor differs only through the wasi-sdk tarballs' runtime archives, and the
# snapshot only through its two inputs. Swap the macOS SDK's three wasip1 runtime archives into the
# Linux SDK tree (wasm objects, not host code), relink, then snapshot with the macOS zip.
set -eu
cd /work/wasi_python
SDK=build/tools/wasi-sdk-33.0-arm64-linux
cp /maclibs/libc++.a /maclibs/libc++abi.a "$SDK/share/wasi-sysroot/lib/wasm32-wasip1/eh/"
cp /maclibs/libclang_rt.builtins.a "$SDK/lib/clang/22/lib/wasm32-unknown-wasip1/"
export SOURCE_DATE_EPOCH=1767225600
sh scripts/build.sh 60 70 > /out/swap-output.txt 2>&1 || true
sha256sum build/out/python.wasm build/out/python-stdlib.zip >> /out/swap-output.txt
cp /maclibs/macos-python-stdlib.zip build/out/python-stdlib.zip
sh scripts/build.sh 80 >> /out/swap-output.txt 2>&1 || true
sha256sum build/out/python-snapshot.wasm >> /out/swap-output.txt
cat /out/swap-output.txt
