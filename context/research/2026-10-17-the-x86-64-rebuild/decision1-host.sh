#!/bin/sh
# Spec 040, Decision 1, on the arm64 macOS host (Decision 10 moves it into this folder). After a
# build (build/numpy-build exists), in a clone of the repository:
#
#   sh context/research/2026-10-17-the-x86-64-rebuild/decision1-host.sh <out>
#
# 1. Preprocesses numpy's npy_math_complex.c with the build's own command from meson's
#    compile_commands.json (-E -P): <out>/npy_math_complex.i. It is numpy's and wasi-libc's text,
#    so it is regenerated, never committed.
# 2. Compiles that one file with the build's code-generation flags on this host's SDK, prints the
#    pass list for npy_cpowl, and compiles it once per -pre-RA-sched choice (decision1-sweep.sh).
set -eu
HERE=$(CDPATH= cd "$(dirname "$0")/../../.." && pwd -P)
OUT=$1
mkdir -p "$OUT"
OUT=$(CDPATH= cd "$OUT" && pwd -P)
NB="$HERE/build/numpy-build"
PY="$HERE/build/tools/python/bin/python3"
[ -f "$NB/compile_commands.json" ] || { echo "no $NB/compile_commands.json: build first" >&2; exit 1; }
cmd=$("$PY" -I - "$NB/compile_commands.json" <<'EOF'
import json, sys
for e in json.load(open(sys.argv[1])):
    if e["output"].endswith("meson-generated_npy_math_complex.c.o"):
        print(e["command"])
EOF
)
# The build's own command, preprocessing only: no object, no depfile.
pre=$(printf '%s' "$cmd" | sed 's# -MD -MQ [^ ]* -MF [^ ]*##; s# -o [^ ]*npy_math_complex\.c\.o# -E -P -o '"$OUT"'/npy_math_complex.i#')
export WASI_SDK_PATH="$HERE/build/tools/wasi-sdk-33.0-arm64-macos"
(cd "$NB" && eval "$pre")
echo "preprocessed: $(wc -c < "$OUT/npy_math_complex.i" | tr -d ' ') bytes, $(shasum -a 256 "$OUT/npy_math_complex.i" | cut -c1-16)"
echo "the build's object: $(shasum -a 256 "$NB/numpy/_core/libnpymath.a.p/meson-generated_npy_math_complex.c.o" | cut -c1-16)"
sh "$(dirname "$0")/decision1-sweep.sh" "$WASI_SDK_PATH/bin/clang" "$OUT/npy_math_complex.i" "$OUT/macos-arm64"
