#!/bin/sh
# Relink the reactor exactly as step 60 did (build/link/reactor-commands.txt, line 2), into
# <scratch>/out/<name>/python.wasm (wasm-ld writes the output's file name into the name section, so
# every variant is called python.wasm). Usage: relink.sh <scratch dir> <name> [vfs|vfs-late]
#   (none)    the control: must reproduce build/out/python.wasm byte for byte
#   vfs       libwasi_vfs.a appended as wasi-vfs's README shows; it then supplies libm, memcpy and
#             the soft float to the whole link, ahead of wasi-libc and compiler-rt
#   vfs-late  libc, libm and compiler-rt named first, so wasi-vfs supplies only what nothing else does
set -eu
X=$1; NAME=$2; WITH=${3:-}
R="$X/repo"
mkdir -p "$X/out/$NAME"
W="$R/build/Python-3.14.8/cross-build/wasm32-wasip1"
SDK="$R/build/tools/wasi-sdk-24.0-arm64-macos"
RT=$(echo "$SDK"/lib/clang/*/lib/wasi/libclang_rt.builtins-wasm32.a)
link=$(sed -n 2p "$R/build/link/reactor-commands.txt")
link=$(printf '%s' "$link" | sed "s#-Wl,--Map=[^ ]*#-Wl,--Map=$X/out/$NAME/python.map#; s#-o [^ ]*/build/out/python\.wasm#-o $X/out/$NAME/python.wasm#")
case "$WITH" in
  vfs) link="$link $X/lib/libwasi_vfs.a" ;;
  vfs-late) link="$link -lc -lm $RT $X/lib/libwasi_vfs.a" ;;
  '') ;;
  *) echo "unknown variant $WITH" >&2; exit 2 ;;
esac
cd "$W"
eval "$link" > "$X/out/$NAME/link.log" 2>&1 || { tail -n 30 "$X/out/$NAME/link.log"; exit 1; }
if grep -E 'signature mismatch|duplicate symbol' "$X/out/$NAME/link.log"; then exit 1; fi
"$SDK/bin/llvm-strip" --strip-debug "$X/out/$NAME/python.wasm"
# The C-namespace symbols the link took from libwasi_vfs.a (Rust-mangled and local ones left out).
awk '/libwasi_vfs.a\(/{f=1;next} f&&/^ +- +[0-9a-f]+ +[0-9a-f]+ +[A-Za-z_][A-Za-z0-9_.]*$/{print $NF} {f=0}' \
  "$X/out/$NAME/python.map" | grep -v '^_ZN\|^\.L\|^_R' | sort -u > "$X/out/$NAME/from-wasi-vfs.txt" || true
echo "$NAME: $(wc -c < "$X/out/$NAME/python.wasm" | tr -d ' ') bytes, $(shasum -a 256 "$X/out/$NAME/python.wasm" | cut -c1-64), $(wc -l < "$X/out/$NAME/from-wasi-vfs.txt" | tr -d ' ') C symbols from libwasi_vfs.a"
