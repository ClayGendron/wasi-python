/* Spec 100's drafting prototype of recipes/numpy_lapack_abi.h. Force-included, by the per-file
 * map, into numpy/linalg/umath_linalg.cpp, numpy/linalg/lapack_litemodule.c and the three
 * compiles of python_xerbla.c. numpy declares each LAPACK subroutine and each BLAS copy as
 * returning an int; the set's OpenBLAS defines them void, as scipy's f2py declares them, and wasm
 * traps on the difference. numpy's own hook, BLAS_SYMBOL_PREFIX (npy_cblas.h, #ifndef), sends
 * these files' every BLAS_FUNC name to wasi_numpy_<name>_, the shims in
 * recipes/numpy_lapack_shims.c, which call OpenBLAS's real routine and return 0; and it keeps
 * numpy's python_xerbla, which raises ValueError, off OpenBLAS's own xerbla_, as natively. */
#define BLAS_SYMBOL_PREFIX wasi_numpy_
