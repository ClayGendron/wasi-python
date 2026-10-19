/* For _flapackmodule.c only, through recipes/scipy_file_includes.txt (spec 037, Decision 6):
 * f2py's ?gees calls pass two hidden string lengths that OpenBLAS's ?gees_ does not take, so they
 * go to the shims in recipes/scipy_lapack_shims.c. cython_lapack calls the same names with
 * OpenBLAS's 15 arguments and keeps calling OpenBLAS. */
#include "scipy_f2py_weak_api.h"
#define sgees_ wasi_scipy_sgees_
#define dgees_ wasi_scipy_dgees_
#define cgees_ wasi_scipy_cgees_
#define zgees_ wasi_scipy_zgees_
