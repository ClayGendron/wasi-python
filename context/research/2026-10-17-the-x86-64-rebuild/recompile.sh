#!/bin/bash
# Recompile numpy's npy_math_complex.c three times with the build's own command (from meson's
# compile_commands.json), into /tmp, and print each object's hash. Run inside a build container.
cd /work/wasi_python/build/numpy-build
cmd=$(/work/wasi_python/build/tools/python/bin/python3 -I -c '
import json
for e in json.load(open("compile_commands.json")):
    if e["output"].endswith("meson-generated_npy_math_complex.c.o"):
        print(e["command"])')
export PATH="/work/wasi_python/build/tools/pylib/bin:$PATH" WASI_SDK_PATH=$(ls -d /work/wasi_python/build/tools/wasi-sdk-*)
for i in 1 2 3; do
  c=$(echo "$cmd" | sed "s# -o [^ ]*npy_math_complex.c.o# -o /tmp/r$i.o#; s# -MF [^ ]*# -MF /tmp/r$i.d#")
  eval "$c" && sha256sum /tmp/r$i.o | cut -c1-16
done
sha256sum numpy/_core/libnpymath.a.p/meson-generated_npy_math_complex.c.o | cut -c1-16
