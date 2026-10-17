#!/bin/bash
# Compare the two Linux builds' numpy trees: generated sources and the objects that differ.
cd /a/wasi_python/build/numpy-build
f=$(find . -name "npy_math_complex.c" | head -1); echo "generated: $f"
cmp "$f" "/x/wasi_python/build/numpy-build/$f" && echo "  source equal"
for o in $(find . -name "*npy_math_complex.c.o"); do cmp "$o" "/x/wasi_python/build/numpy-build/$o" >/dev/null && echo "$o equal" || echo "$o DIFFERS"; done
echo "== generated .c/.h that differ"
diff <(find . \( -name "*.c" -o -name "*.h" \) | sort | xargs sha256sum) <(cd /x/wasi_python/build/numpy-build && find . \( -name "*.c" -o -name "*.h" \) | sort | xargs sha256sum)
echo "== objects that differ (count)"
n=0; for o in $(find . -name "*.o"); do cmp -s "$o" "/x/wasi_python/build/numpy-build/$o" || { n=$((n+1)); echo "$o"; }; done | head -20
grep -rn "LONG_DOUBLE\|longdouble" /a/wasi_python/build/numpy-build/meson-logs/meson-log.txt | grep -i "result\|format" | head -5
echo "== x86"; grep -rn "LONG_DOUBLE\|longdouble" /x/wasi_python/build/numpy-build/meson-logs/meson-log.txt | grep -i "result\|format" | head -5
