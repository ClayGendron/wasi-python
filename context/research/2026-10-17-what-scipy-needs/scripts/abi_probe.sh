#!/bin/sh
# Experiment: compile scipy 1.18.1's f2py BLAS/LAPACK modules (and its cython_blas/cython_lapack) for
# wasm32-wasip1 and link them against the OpenBLAS 0.3.34 C-LAPACK archive, to list every ABI clash
# wasm-ld reports. Nothing is run; the link is only a detector.
set -u
S=/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/scipy-research
R=/Users/claygendron/Git/Repos/wasi_python
SDK=$R/build/tools/wasi-sdk-33.0-arm64-macos
SCI=$S/work/src/scipy-1.18.1
OB=$S/work/openblas-WASM128_GENERIC
F2PY=$S/work/hostvenv/lib/python3.15/site-packages/numpy/f2py/src
O=$S/work/abi; rm -rf $O; mkdir -p $O
CC="$SDK/bin/clang --target=wasm32-wasip1 -O2 -w -D_WASI_EMULATED_SIGNAL -D_WASI_EMULATED_PROCESS_CLOCKS -D_WASI_EMULATED_GETPID -DNPY_NO_SIGNAL -fwasm-exceptions -mllvm -wasm-enable-sjlj -mllvm -wasm-use-legacy-eh=false"
INC="-I$R/build/Python-3.15.0/Include -I$R/build/Python-3.15.0/cross-build/wasm32-wasip1 -I$R/build/numpy-host/numpy/_core/include -I$F2PY -I$SCI/scipy/_build_utils/src -I$OB"
DEF="-DF2PY_THREAD_LOCAL_DECL=_Thread_local -DNPY_NO_DEPRECATED_API=NPY_1_9_API_VERSION"
for f in $S/work/f2pygen/_fblasmodule.c $S/work/f2pygen/_flapackmodule.c $F2PY/fortranobject.c $SCI/scipy/_build_utils/src/wrap_dummy_g77_abi.c; do
  b=$(basename $f .c)
  $CC $INC $DEF -c $f -o $O/$b.o 2> $O/$b.err || { echo "COMPILE FAIL $b"; head -5 $O/$b.err; }
done
# cython_blas / cython_lapack: generated on the host, cythonized with the line's pinned Cython 3.3.0.
mkdir -p $O/cy && $S/work/hostvenv/bin/python -I $SCI/scipy/linalg/_generate_pyx.py -o $O/cy > $O/cy/gen.log 2>&1 || echo "GENERATE FAIL"
cp $SCI/scipy/linalg/__init__.pxd $O/cy/ 2>/dev/null
for m in cython_blas cython_lapack; do
  PYTHONPATH=$R/build/tools/pylib $R/build/tools/python/bin/python3 -m cython -3 --fast-fail -I $R/build/numpy-host -I $O/cy -I $SCI/scipy -o $O/cy/$m.c $O/cy/$m.pyx > $O/cy/$m.cy.log 2>&1 || { echo "CYTHON FAIL $m"; tail -5 $O/cy/$m.cy.log; }
  $CC $INC -I$O/cy -I$SCI/scipy/linalg -c $O/cy/$m.c -o $O/$m.o 2> $O/$m.err || { echo "COMPILE FAIL $m"; head -5 $O/$m.err; }
done
ls $O/*.o
# The detector: a link with every object kept, Python's C API left undefined.
$SDK/bin/wasm-ld --no-entry --allow-undefined --no-gc-sections --export-all \
  $O/*.o $OB/libopenblas_wasm128-r0.3.34.a -o $O/probe.wasm > $O/link.log 2>&1
echo "link exit=$?"
grep -c "signature mismatch" $O/link.log
