/* Force-included in every scipy C and C++ compile (recipes/wasi-scipy.cross; spec 037, Decision 6):
 * the names that would clash in one static link with OpenBLAS, numpy, pandas or matplotlib, each
 * renamed to a name only scipy uses. Each entry is reviewed. */

/* cython_lapack declares these two with scipy's own signatures, which OpenBLAS's C LAPACK does not
 * have; every scipy caller uses scipy's declaration, so the rename is global. The shims are in
 * recipes/scipy_lapack_shims.c. */
#define chla_transtype_ wasi_scipy_chla_transtype_
#define xerbla_array_ wasi_scipy_xerbla_array_

/* Init functions that share a name with another package's module (scripts/gen_inittab.py's
 * RENAMED table names the same three): Cython's shared utility module, which pandas also builds,
 * and spatial's _qhull, whose name matplotlib's _qhull shares (spec 043). */
#define PyInit__cyutility PyInit_scipy__cyutility
#define __pyx_module_is_main__cyutility __pyx_module_is_main_scipy__cyutility
#define PyInit__qhull PyInit_scipy_spatial__qhull

/* scipy.stats vendors numpy.random's distributions.c (stats/libnpyrandom), which numpy's own
 * libnpyrandom also defines; the same code under two owners, so scipy's copy takes scipy's names. */
#define random_standard_uniform scipy_random_standard_uniform
#define random_standard_normal scipy_random_standard_normal
#define random_normal scipy_random_normal
#define random_interval scipy_random_interval

/* SuperLU's own c_abs (double, of its singlecomplex) shares its name with OpenBLAS's f2c c_abs
 * (float); SuperLU's takes a name of scipy's (found at build by step 60's clash detector). */
#define c_abs scipy_superlu_c_abs
