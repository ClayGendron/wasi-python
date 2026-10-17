#!/bin/sh
# Step 80's Wizer command on this host, given macOS's reactor and zip, with and without NaN
# canonicalization; prints each snapshot's hash. Outputs under /tmp only.
set -eu
WT=$(ls -d /work/wasi_python/build/tools/wasmtime-v49.0.3-*)/wasmtime
for nan in "" ",nan-canonicalization=y"; do
  R=/tmp/root; rm -rf $R; mkdir -p $R/usr/local/lib
  cp /in/python-stdlib.zip $R/usr/local/lib/python315.zip
  "$WT" wizer -W exceptions=y,unknown-imports-trap=y$nan -S cli=y,inherit-stdin=n,inherit-stdout=n,inherit-stderr=n -C cache=n --init-func wizer.initialize --dir "$R::/" -o /tmp/snap.wasm /in/macos-python.wasm
  echo "flags '${nan}': $(sha256sum /tmp/snap.wasm | cut -c1-64) $(wc -c < /tmp/snap.wasm)"
done
