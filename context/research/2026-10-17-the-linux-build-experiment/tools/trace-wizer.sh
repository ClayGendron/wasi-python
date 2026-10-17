#!/bin/sh
# Run step 80's exact wizer command with wasmtime's WASI trace log; argv: wasmtime reactor zip out-dir
set -eu
WT=$1; REACTOR=$2; ZIP=$3; OUTD=$4
ROOT=$(mktemp -d)
mkdir -p "$ROOT/usr/local/lib" "$OUTD"
cp "$ZIP" "$ROOT/usr/local/lib/python315.zip"
FLAGS="-W exceptions=y,unknown-imports-trap=y -S cli=y,inherit-stdin=n,inherit-stdout=n,inherit-stderr=n -C cache=n --init-func wizer.initialize"
WASMTIME_LOG=wasmtime_wasi=trace "$WT" wizer $FLAGS --dir "$ROOT::/" -o "$OUTD/snap.wasm" "$REACTOR" 2> "$OUTD/trace.log"
shasum -a 256 "$OUTD/snap.wasm" | cut -c1-16
wc -l < "$OUTD/trace.log"
rm -rf "$ROOT"
