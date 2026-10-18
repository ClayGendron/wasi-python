#!/bin/sh
# Spec 040, Decision 1: one host's compiler on the one file.
#
#   sh decision1-sweep.sh <clang> <npy_math_complex.i> <out>
#
# Writes <out>/object.txt (the object's SHA-256 with the build's code-generation flags),
# <out>/passes.txt (every pass's output for npy_cpowl, -print-after-all) and its line count, and
# <out>/sched.txt (the object's SHA-256 under each -pre-RA-sched choice).
set -u
CLANG=$1 I=$2 O=$3
mkdir -p "$O"
F="--target=wasm32-wasip1 -std=c11 -O3 -fno-strict-aliasing -ftrapping-math -fvisibility=hidden -Wno-unsupported-floating-point-opt -w"
sha() { if command -v sha256sum > /dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -c1-16; }
"$CLANG" $F -c "$I" -o "$O/a.o" && echo "object $(sha "$O/a.o")" > "$O/object.txt"
"$CLANG" $F -c "$I" -o "$O/p.o" -mllvm -print-after-all -mllvm -filter-print-funcs=npy_cpowl 2> "$O/passes.txt"
wc -l < "$O/passes.txt" | tr -d ' ' > "$O/passes.count"
for s in default source list-burr list-hybrid list-ilp linearize fast; do
  "$CLANG" $F -c "$I" -o "$O/s.o" -mllvm -pre-RA-sched=$s && echo "$s $(sha "$O/s.o")"
done > "$O/sched.txt"
rm -f "$O/a.o" "$O/p.o" "$O/s.o"
cat "$O/object.txt"
echo "passes: $(cat "$O/passes.count") lines"
cat "$O/sched.txt"
