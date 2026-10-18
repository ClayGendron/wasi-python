#!/bin/sh
S=/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/5c4a788f-6229-4fb4-8a87-05b4e7e5e695/scratchpad/prior-art-repro
MAC=$S/dl/mac/wasi-sdk-33.0-arm64-macos/bin/clang
IMG=debian:trixie-slim@sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f
C=$(docker run -d --rm --platform linux/amd64 -v $S/dl/x86:/sdk:ro -v $S/exp:/r -w /r $IMG sleep 3600)
X="docker exec -w /r $C /sdk/wasi-sdk-33.0-x86_64-linux/bin/clang"
F="--target=wasm32-wasip1 -std=c11 -O3 -fno-strict-aliasing -ftrapping-math -fvisibility=hidden -Wno-unsupported-floating-point-opt -w"
cd $S/exp
run() { n=$1; shift
  $MAC $F "$@" -c npy_math_complex.i -o na-$n.o || { echo "$n: mac failed"; return; }
  $X $F "$@" -c npy_math_complex.i -o nx-$n.o || { echo "$n: x86 failed"; return; }
  a=$(shasum -a 256 na-$n.o | cut -c1-16); x=$(shasum -a 256 nx-$n.o | cut -c1-16)
  [ "$a" = "$x" ] && echo "numpy $n [$*]: SAME $a" || echo "numpy $n [$*]: DIFFER aarch64 $a x86_64 $x"
}
run base
run fpoff -ffp-contract=off
run fpfast -ffp-contract=fast
run fpoff_O2 -O2 -ffp-contract=off
docker rm -f $C >/dev/null
