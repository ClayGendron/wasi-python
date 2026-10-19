/* For scipy.optimize._trlib's trlib_tri_factor.c only, through recipes/scipy_file_includes.txt
 * (spec 037, Decision 6; found at build by step 60's clash detector): trlib_private.h passes
 * dlagtm a hidden string length that OpenBLAS's dlagtm_ does not take. It goes to the shim in
 * recipes/scipy_lapack_shims.c; cython_lapack's own dlagtm keeps calling OpenBLAS. */
#define dlagtm_ wasi_scipy_dlagtm_
