/* numpy's side of the LAPACK ABI (spec 100, Decision 4). Force-included, by the per-file map
 * recipes/numpy_file_includes.txt, into numpy/linalg/umath_linalg.cpp, numpy/linalg/lapack_litemodule.c
 * and numpy's three compiles of python_xerbla.c, and into nothing else.
 *
 * numpy declares every LAPACK subroutine it calls, and BLAS's four ?copy routines, as returning an
 * int. The set's OpenBLAS defines them void, as LAPACK's Fortran subroutines are and as scipy's f2py
 * declares them (spec 037), and WebAssembly traps on a call whose type differs from its target's.
 * numpy's own hook, BLAS_SYMBOL_PREFIX (npy_cblas.h defines it only #ifndef), sends these files'
 * every BLAS_FUNC name to wasi_numpy_<name>_: the shims in recipes/numpy_lapack_shims.c, which call
 * OpenBLAS's routine and return 0. It also renames numpy's python_xerbla, which raises ValueError,
 * to wasi_numpy_xerbla_, so OpenBLAS keeps its own xerbla_, which prints and returns, as natively;
 * only numpy.linalg.lapack_lite.xerbla() calls numpy's.
 *
 * numpy's core calls OpenBLAS's CBLAS directly: its cblas_* declarations already match, and this
 * header never reaches those files. Remove this file, the shims and the map when a numpy release
 * declares LAPACK's subroutines void
 * (context/upstream/31-numpy-lapack-subroutines-declared-int/facts.md). */
#define BLAS_SYMBOL_PREFIX wasi_numpy_
