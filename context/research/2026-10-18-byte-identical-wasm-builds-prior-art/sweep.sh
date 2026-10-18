#!/bin/sh
# Flag sweep: compile slot-order.c with the arm64 macOS SDK (native) and the x86_64 Linux SDK
# (linux/amd64 container, under Rosetta), hash the objects, say same or differ.
S=/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/5c4a788f-6229-4fb4-8a87-05b4e7e5e695/scratchpad/prior-art-repro
MAC=$S/dl/mac/wasi-sdk-33.0-arm64-macos/bin/clang
IMG=debian:trixie-slim@sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f
C=$(docker run -d --rm --platform linux/amd64 -v $S/dl/x86:/sdk:ro -v $S/exp:/r -w /r $IMG sleep 3600)
X="docker exec -w /r $C /sdk/wasi-sdk-33.0-x86_64-linux/bin/clang"
BASE="--target=wasm32-wasip1 -std=c11 -fno-strict-aliasing -ftrapping-math -fvisibility=hidden -w"
run() { # name flags...
  n=$1; shift
  $MAC $BASE "$@" -c slot-order.c -o a-$n.o || { echo "$n: mac failed"; return; }
  $X $BASE "$@" -c slot-order.c -o x-$n.o || { echo "$n: x86 failed"; return; }
  a=$(shasum -a 256 a-$n.o | cut -c1-16); x=$(shasum -a 256 x-$n.o | cut -c1-16)
  [ "$a" = "$x" ] && echo "$n [$*]: SAME $a" || echo "$n [$*]: DIFFER aarch64 $a x86_64 $x"
}
run base -O3
run O2 -O2
run O1 -O1
run Os -Os
run Oz -Oz
run misched0 -O3 -mllvm -enable-misched=0
run fastisel -O3 -mllvm -fast-isel
run nounroll -O3 -fno-unroll-loops
run novec -O3 -fno-vectorize -fno-slp-vectorize
run fpoff -O3 -ffp-contract=off
run nolegalcheck -O3 -mllvm -combiner-alias-analysis=0
run dag_sched_source -O3 -mllvm -pre-RA-sched=source
run nocsr -O3 -fno-omit-frame-pointer
run lto -O3 -flto
echo "--- environment-size probe (x86_64 clang, -O3): same binary, different process addresses"
docker exec -w /r $C env -i /sdk/wasi-sdk-33.0-x86_64-linux/bin/clang $BASE -O3 -c slot-order.c -o x-envi.o
docker exec -w /r $C sh -c 'BIG=$(head -c 300000 /dev/zero | tr "\0" x) /sdk/wasi-sdk-33.0-x86_64-linux/bin/clang '"$BASE"' -O3 -c slot-order.c -o x-envbig.o'
docker exec -w /r $C sh -c 'setarch x86_64 -R /sdk/wasi-sdk-33.0-x86_64-linux/bin/clang '"$BASE"' -O3 -c slot-order.c -o x-noaslr.o' 2>&1 | head -2
shasum -a 256 x-base.o x-envi.o x-envbig.o x-noaslr.o 2>/dev/null | cut -c1-16,65-
echo "--- the same probe on the aarch64 macOS clang"
env -i $MAC $BASE -O3 -c slot-order.c -o a-envi.o
BIG=$(head -c 300000 /dev/zero | tr "\0" x) $MAC $BASE -O3 -c slot-order.c -o a-envbig.o
shasum -a 256 a-base.o a-envi.o a-envbig.o | cut -c1-16,65-
echo "--- clang versions"
$MAC --version | head -1; $X --version | head -1
docker rm -f $C >/dev/null
