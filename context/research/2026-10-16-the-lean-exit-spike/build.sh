#!/bin/sh
# SPIKE: link the lean-exit variant of the reactor against the landed build (steps 20 to 60 must
# have run), then snapshot it. Outputs go to build/spike-lean-exit/; nothing in build/artifacts/ or
# recipes/ changes. Run from the repository root: sh context/research/2026-10-16-the-lean-exit-spike/build.sh
set -eu
HERE=$(pwd -P)
E="$HERE/context/research/2026-10-16-the-lean-exit-spike"
O="$HERE/build/spike-lean-exit"
T="$HERE/build/tools"
W="$HERE/build/Python-3.14.8/cross-build/wasm32-wasip1"
export WASI_SDK_PATH="$T/wasi-sdk-24.0-arm64-macos" PATH="$T/pylib/bin:$PATH" PYTHONHASHSEED=0 SOURCE_DATE_EPOCH=1767225600
rm -rf "$O" && mkdir -p "$O/root/usr/local/lib"
env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 "$T/python/bin/python3" "$HERE/scripts/freeze_bootstrap.py" \
  "$E/reactor_bootstrap.py" "$O/reactor_bootstrap.h" > "$O/freeze.log"
compile=$(sed -n 1p "$HERE/build/link/reactor-commands.txt" | sed "s#$HERE/build/link#$O#; s#$HERE/recipes/reactor_main.c#$E/reactor_main.c#; s#-o Modules/reactor_main.o#-o $O/reactor_main.o#")
link=$(sed -n 2p "$HERE/build/link/reactor-commands.txt" | sed "s#-Wl,--Map=[^ ]*##; s#-o $HERE/build/out/python.wasm Modules/reactor_main.o#-o $O/python.wasm $O/reactor_main.o#")
cd "$W"
eval "$compile" > "$O/compile.log" 2>&1
eval "$link" > "$O/link.log" 2>&1
"$T/wasi-sdk-24.0-arm64-macos/bin/llvm-strip" --strip-debug "$O/python.wasm"
cp "$HERE/build/artifacts/python-stdlib.zip" "$O/root/usr/local/lib/python314.zip"
"$T/wizer-v11.0.3-aarch64-macos/wizer" --allow-wasi --wasm-bulk-memory true --init-func wizer.initialize \
  --mapdir "/::$O/root" -o "$O/python-snapshot.wasm" "$O/python.wasm"
cp "$HERE/build/artifacts/python-stdlib.zip" "$HERE/build/artifacts/MANIFEST" "$O/"
echo "spike: $(shasum -a 256 "$O/python.wasm" | cut -c1-16) $(shasum -a 256 "$O/python-snapshot.wasm" | cut -c1-16)"
