/* scipy's side of the LAPACK ABI (spec 037, Decision 6): six functions of ours, each with the
 * signature scipy declares, each calling OpenBLAS's real one, whose C LAPACK follows f2c.
 *
 *   wasi_scipy_{s,d,c,z}gees_   f2py's _flapack passes two hidden string lengths (17 arguments);
 *                               OpenBLAS's ?gees_ takes 15. The lengths are dropped.
 *   wasi_scipy_chla_transtype_  cython_lapack declares `char chla_transtype(int *trans)`;
 *                               OpenBLAS's returns the character through its first argument.
 *   wasi_scipy_xerbla_array_    cython_lapack passes no hidden length; OpenBLAS's takes one.
 *   wasi_scipy_int_?getrf_, wasi_scipy_int_?getri_
 *                               linalg._batched_linalg declares these SUBROUTINEs as returning
 *                               an int (src/_common_array_utils.hh); OpenBLAS's return void.
 *                               They return 0, what an f2c subroutine returns.
 *   wasi_scipy_dlagtm_          optimize._trlib passes dlagtm a hidden length; OpenBLAS's
 *                               dlagtm_ takes none (found by step 60's clash detector at build).
 *
 * recipes/scipy_flapack_rename.h sends _flapackmodule.c's ?gees_ here, recipes/scipy_rename.h
 * every scipy caller of chla_transtype and xerbla_array, recipes/scipy_batched_linalg_rename.h the
 * one caller of the int ?getrf_ and ?getri_, and recipes/scipy_trlib_dlagtm.h the one caller of
 * dlagtm with a length; cython_lapack's own calls keep calling OpenBLAS.
 * Step 57 compiles this file alone, with no rename header, into libscipy_lapack_shims.a. */

typedef int f_int; /* f2c's integer, logical and ftnlen on wasm32: OpenBLAS's blasint */

typedef f_int (*select_real)(float *, float *);
typedef f_int (*select_double)(double *, double *);
typedef f_int (*select_complex)(void *);

void sgees_(char *, char *, select_real, f_int *, float *, f_int *, f_int *, float *, float *,
            float *, f_int *, float *, f_int *, f_int *, f_int *);
void dgees_(char *, char *, select_double, f_int *, double *, f_int *, f_int *, double *,
            double *, double *, f_int *, double *, f_int *, f_int *, f_int *);
void cgees_(char *, char *, select_complex, f_int *, void *, f_int *, f_int *, void *, void *,
            f_int *, void *, f_int *, float *, f_int *, f_int *);
void zgees_(char *, char *, select_complex, f_int *, void *, f_int *, f_int *, void *, void *,
            f_int *, void *, f_int *, double *, f_int *, f_int *);
void chla_transtype_(char *ret_val, f_int ret_val_len, f_int *trans);
void sgetrf_(f_int *, f_int *, float *, f_int *, f_int *, f_int *);
void dgetrf_(f_int *, f_int *, double *, f_int *, f_int *, f_int *);
void cgetrf_(f_int *, f_int *, void *, f_int *, f_int *, f_int *);
void zgetrf_(f_int *, f_int *, void *, f_int *, f_int *, f_int *);
void sgetri_(f_int *, float *, f_int *, f_int *, float *, f_int *, f_int *);
void dgetri_(f_int *, double *, f_int *, f_int *, double *, f_int *, f_int *);
void cgetri_(f_int *, void *, f_int *, f_int *, void *, f_int *, f_int *);
void zgetri_(f_int *, void *, f_int *, f_int *, void *, f_int *, f_int *);
void dlagtm_(char *, f_int *, f_int *, double *, double *, double *, double *, double *, f_int *,
             double *, double *, f_int *);
void xerbla_array_(char *srname_array, f_int *srname_len, f_int *info, f_int srname_array_len);

void wasi_scipy_sgees_(char *jobvs, char *sort, select_real select, f_int *n, float *a, f_int *lda,
                       f_int *sdim, float *wr, float *wi, float *vs, f_int *ldvs, float *work,
                       f_int *lwork, f_int *bwork, f_int *info, f_int len_jobvs, f_int len_sort)
{
    (void)len_jobvs;
    (void)len_sort;
    sgees_(jobvs, sort, select, n, a, lda, sdim, wr, wi, vs, ldvs, work, lwork, bwork, info);
}

void wasi_scipy_dgees_(char *jobvs, char *sort, select_double select, f_int *n, double *a,
                       f_int *lda, f_int *sdim, double *wr, double *wi, double *vs, f_int *ldvs,
                       double *work, f_int *lwork, f_int *bwork, f_int *info, f_int len_jobvs,
                       f_int len_sort)
{
    (void)len_jobvs;
    (void)len_sort;
    dgees_(jobvs, sort, select, n, a, lda, sdim, wr, wi, vs, ldvs, work, lwork, bwork, info);
}

void wasi_scipy_cgees_(char *jobvs, char *sort, select_complex select, f_int *n, void *a,
                       f_int *lda, f_int *sdim, void *w, void *vs, f_int *ldvs, void *work,
                       f_int *lwork, float *rwork, f_int *bwork, f_int *info, f_int len_jobvs,
                       f_int len_sort)
{
    (void)len_jobvs;
    (void)len_sort;
    cgees_(jobvs, sort, select, n, a, lda, sdim, w, vs, ldvs, work, lwork, rwork, bwork, info);
}

void wasi_scipy_zgees_(char *jobvs, char *sort, select_complex select, f_int *n, void *a,
                       f_int *lda, f_int *sdim, void *w, void *vs, f_int *ldvs, void *work,
                       f_int *lwork, double *rwork, f_int *bwork, f_int *info, f_int len_jobvs,
                       f_int len_sort)
{
    (void)len_jobvs;
    (void)len_sort;
    zgees_(jobvs, sort, select, n, a, lda, sdim, w, vs, ldvs, work, lwork, rwork, bwork, info);
}

char wasi_scipy_chla_transtype_(f_int *trans)
{
    char r;
    chla_transtype_(&r, 1, trans);
    return r;
}

void wasi_scipy_xerbla_array_(char *srname_array, f_int *srname_len, f_int *info)
{
    xerbla_array_(srname_array, srname_len, info, *srname_len);
}

#define GETRF(p, T)                                                                              \
    f_int wasi_scipy_int_##p##getrf_(f_int *m, f_int *n, T *a, f_int *lda, f_int *ipiv,          \
                                     f_int *info)                                                \
    {                                                                                            \
        p##getrf_(m, n, a, lda, ipiv, info);                                                     \
        return 0;                                                                                \
    }
#define GETRI(p, T)                                                                              \
    f_int wasi_scipy_int_##p##getri_(f_int *n, T *a, f_int *lda, f_int *ipiv, T *work,           \
                                     f_int *lwork, f_int *info)                                  \
    {                                                                                            \
        p##getri_(n, a, lda, ipiv, work, lwork, info);                                           \
        return 0;                                                                                \
    }
GETRF(s, float)
GETRF(d, double)
GETRF(c, void)
GETRF(z, void)
GETRI(s, float)
GETRI(d, double)
GETRI(c, void)
GETRI(z, void)

void wasi_scipy_dlagtm_(char *trans, f_int *n, f_int *nrhs, double *alpha, double *dl, double *d,
                        double *du, double *x, f_int *ldx, double *beta, double *b, f_int *ldb,
                        f_int len_trans)
{
    (void)len_trans;
    dlagtm_(trans, n, nrhs, alpha, dl, d, du, x, ldx, beta, b, ldb);
}
