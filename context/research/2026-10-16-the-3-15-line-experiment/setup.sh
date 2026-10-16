#!/bin/sh
# Experiment: the CPython 3.15.0 + wasi-sdk 33 line, in a scratch clone (nothing in the real repo changes).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd -P)
REAL=<repo>
R="$HERE/repo"
rm -rf "$R"
git clone -q "$REAL" "$R"
mkdir -p "$R/downloads"
for f in "$REAL"/downloads/*; do
  [ "$(basename "$f")" = SHA256SUMS ] || cp -c "$f" "$R/downloads/"
done
cp -c "$HERE/../dl-315/Python-3.15.0.tar.xz" "$R/downloads/"
cd "$R/downloads"
fetch() { [ -s "$2" ] || curl -sfL -o "$2" "$1"; }
fetch "https://github.com/astral-sh/python-build-standalone/releases/download/20261009/cpython-3.15.0%2B20261009-aarch64-apple-darwin-install_only.tar.gz" cpython-3.15.0+20261009-aarch64-apple-darwin-install_only.tar.gz
fetch "https://files.pythonhosted.org/packages/ea/45/7f6988070013e16918e39b1b3dab9c5f2c8e404253a7fd10ee685bbd6902/cython-3.3.0-cp315-cp315-macosx_11_0_arm64.whl" cython-3.3.0-cp315-cp315-macosx_11_0_arm64.whl
fetch "https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-33/wasi-sdk-33.0-arm64-macos.tar.gz" wasi-sdk-33.0-arm64-macos.tar.gz
grep "  wasi-sdk-33.0-arm64-macos.tar.gz$" SHA256SUMS | shasum -a 256 -c -
echo "596e8df019372a2cd417805015022d42cb8ee4e1803ccdc11ed00e451625fb66  cython-3.3.0-cp315-cp315-macosx_11_0_arm64.whl" | shasum -a 256 -c -
for f in Python-3.15.0.tar.xz cpython-3.15.0+20261009-aarch64-apple-darwin-install_only.tar.gz cython-3.3.0-cp315-cp315-macosx_11_0_arm64.whl; do
  shasum -a 256 "$f" >> SHA256SUMS
done
cd "$R"
"$REAL/build/tools/python/bin/python3" -I "$HERE/edit.py" "$R"
git -C "$R" add -A && git -C "$R" -c user.name=exp -c user.email=exp@localhost commit -q -m "experiment: the 3.15 + SDK 33 line"
echo "clone ready at $R"
