#!/bin/sh
# Experiment: wasi-vfs 0.6.3 with the real reactor, in a scratch clone (nothing in the real repo changes).
# Usage: setup.sh <real repo> <scratch dir>
# The clone gets symbolic links to the real build trees it only reads (objects, archives, tools).
set -eu
REAL=$1
X=$2
R="$X/repo"
rm -rf "$R"
git clone -q "$REAL" "$R"
mkdir -p "$R/build" "$X/out"
for d in Python-3.14.8 link numpy-build pandas-build zlib-wasi tools artifacts out; do
  ln -s "$REAL/build/$d" "$R/build/$d"
done
# The two downloads, each in its own empty directory, checked against the digests GitHub publishes.
mkdir -p "$X/dl-lib" "$X/dl-cli" "$X/lib" "$X/cli"
V=v0.6.3
U=https://github.com/kateinoigakukun/wasi-vfs/releases/download/$V
[ -s "$X/dl-lib/libwasi_vfs-wasm32-unknown-unknown.zip" ] || curl -sfL -o "$X/dl-lib/libwasi_vfs-wasm32-unknown-unknown.zip" "$U/libwasi_vfs-wasm32-unknown-unknown.zip"
[ -s "$X/dl-cli/wasi-vfs-cli-aarch64-apple-darwin.zip" ] || curl -sfL -o "$X/dl-cli/wasi-vfs-cli-aarch64-apple-darwin.zip" "$U/wasi-vfs-cli-aarch64-apple-darwin.zip"
echo "f94dc7fdabdefc0fed78b70f1ab100207db0558cbabb004dd9e5a0bdeec4256f  $X/dl-lib/libwasi_vfs-wasm32-unknown-unknown.zip" | shasum -a 256 -c -
echo "d9ebf1cb77927b39c543dccb3fc35842b0f14ca8f70223de1daf2585896de3c1  $X/dl-cli/wasi-vfs-cli-aarch64-apple-darwin.zip" | shasum -a 256 -c -
unzip -q -o "$X/dl-lib/libwasi_vfs-wasm32-unknown-unknown.zip" -d "$X/lib"
unzip -q -o "$X/dl-cli/wasi-vfs-cli-aarch64-apple-darwin.zip" -d "$X/cli"
echo "a362f13066048638423742573dcc32e812fe3e65eb91983c1a41fda63837bf57  $X/lib/libwasi_vfs.a" | shasum -a 256 -c -
echo "4f6f903d1325851c7505a35a2b86c4f501dc61683def0efd03eb4127012bee9e  $X/cli/wasi-vfs" | shasum -a 256 -c -
echo "clone ready at $R"
