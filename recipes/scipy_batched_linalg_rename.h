/* For scipy.linalg._batched_linalg's _batched_linalg_module.cc only, through
 * recipes/scipy_file_includes.txt (spec 037, Decision 6; found at build by step 60's clash
 * detector): src/_common_array_utils.hh declares ?getrf and ?getri as returning an int, where
 * OpenBLAS's C LAPACK returns void, as LAPACK's subroutines do. They go to the shims in
 * recipes/scipy_lapack_shims.c, which return 0. */
#define sgetrf_ wasi_scipy_int_sgetrf_
#define dgetrf_ wasi_scipy_int_dgetrf_
#define cgetrf_ wasi_scipy_int_cgetrf_
#define zgetrf_ wasi_scipy_int_zgetrf_
#define sgetri_ wasi_scipy_int_sgetri_
#define dgetri_ wasi_scipy_int_dgetri_
#define cgetri_ wasi_scipy_int_cgetri_
#define zgetri_ wasi_scipy_int_zgetri_
