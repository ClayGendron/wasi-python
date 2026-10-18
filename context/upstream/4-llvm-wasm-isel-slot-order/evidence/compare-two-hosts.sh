#!/bin/sh
# Compile one C file with two wasi-sdk 33 clangs and say whether the objects differ. Run from the
# folder holding the file: both compilers must see the same relative name (it is in the object).
#   AARCH64_CLANG=<arm64 SDK>/bin/clang X86_64_CLANG="docker exec -w /r <container> /sdk/wasi-sdk-33.0-x86_64-linux/bin/clang" sh compare-two-hosts.sh slot-order.c
# The x86_64 SDK ran in a linux/amd64 Debian trixie-slim container with this folder mounted at /r.
F="--target=wasm32-wasip1 -std=c11 -O3 -fno-strict-aliasing -ftrapping-math -fvisibility=hidden -w"
f=$1; b=${f%.c}
$AARCH64_CLANG $F -c "$f" -o "$b-aarch64.o" || exit 1
$X86_64_CLANG $F -c "$f" -o "$b-x86_64.o" || exit 1
a=$(shasum -a 256 "$b-aarch64.o" | cut -c1-16); x=$(shasum -a 256 "$b-x86_64.o" | cut -c1-16)
if [ "$a" = "$x" ]; then echo "$f: same $a"; else echo "$f: DIFFER aarch64 $a x86_64 $x"; fi
