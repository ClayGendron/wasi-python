/* numpy's side of the LAPACK ABI (spec 100, Decision 4): one shim for each of the 35 LAPACK and
 * BLAS routines numpy's linear algebra calls, and no other.
 *
 *   numpy declares each of them as returning an int (numpy/linalg/umath_linalg.cpp,
 *   lapack_litemodule.c); the set's OpenBLAS defines them void, as LAPACK's subroutines are and as
 *   scipy declares them (spec 037). WebAssembly traps on a call whose type differs from its
 *   target's. recipes/numpy_lapack_abi.h sends numpy's calls to wasi_numpy_<name>_; each shim here
 *   passes numpy's parameters, in numpy's order, unchanged, to OpenBLAS's routine and returns 0,
 *   what an f2c subroutine returns. numpy reads only `info`; lapack_lite returns the 0 as its
 *   '<name>_' entry, which is what native numpy reads on OpenBLAS.
 *
 * The parameter lists are numpy 2.5.2's own, copied by
 * context/research/2026-10-20-numpy-on-openblas/make_numpy_shims.py; every argument is a pointer.
 * Step 40 compiles this file alone, with no numpy flag and no rename header, into
 * build/numpy-shims/libnumpy_lapack_shims.a; step 60 links it. Check 4
 * (test_one_lapack_is_linked) holds the set: the names defined here equal the wasi_numpy_* names
 * numpy's two objects leave undefined, less wasi_numpy_xerbla_. A numpy that calls a routine with
 * no shim fails the link. Remove this file with recipes/numpy_lapack_abi.h. */

typedef int fortran_int; /* numpy's CBLAS_INT with no ILP64: OpenBLAS's LP64 blasint */
typedef struct {
    float r, i;
} f2c_complex;
typedef struct {
    double r, i;
} f2c_doublecomplex;

void ccopy_(fortran_int *n, f2c_complex *sx, fortran_int *incx, f2c_complex *sy,
    fortran_int *incy);
fortran_int wasi_numpy_ccopy_(fortran_int *n, f2c_complex *sx, fortran_int *incx, f2c_complex *sy,
    fortran_int *incy)
{
    ccopy_(n, sx, incx, sy, incy);
    return 0;
}

void cgelsd_(fortran_int *m, fortran_int *n, fortran_int *nrhs, f2c_complex a[], fortran_int *lda,
    f2c_complex b[], fortran_int *ldb, float s[], float *rcond, fortran_int *rank,
    f2c_complex work[], fortran_int *lwork, float rwork[], fortran_int iwork[], fortran_int *info);
fortran_int wasi_numpy_cgelsd_(fortran_int *m, fortran_int *n, fortran_int *nrhs, f2c_complex a[],
    fortran_int *lda, f2c_complex b[], fortran_int *ldb, float s[], float *rcond,
    fortran_int *rank, f2c_complex work[], fortran_int *lwork, float rwork[], fortran_int iwork[],
    fortran_int *info)
{
    cgelsd_(m, n, nrhs, a, lda, b, ldb, s, rcond, rank, work, lwork, rwork, iwork, info);
    return 0;
}

void cgesdd_(char *jobz, fortran_int *m, fortran_int *n, f2c_complex a[], fortran_int *lda,
    float s[], f2c_complex u[], fortran_int *ldu, f2c_complex vt[], fortran_int *ldvt,
    f2c_complex work[], fortran_int *lwork, float rwork[], fortran_int iwork[], fortran_int *info);
fortran_int wasi_numpy_cgesdd_(char *jobz, fortran_int *m, fortran_int *n, f2c_complex a[],
    fortran_int *lda, float s[], f2c_complex u[], fortran_int *ldu, f2c_complex vt[],
    fortran_int *ldvt, f2c_complex work[], fortran_int *lwork, float rwork[], fortran_int iwork[],
    fortran_int *info)
{
    cgesdd_(jobz, m, n, a, lda, s, u, ldu, vt, ldvt, work, lwork, rwork, iwork, info);
    return 0;
}

void cgesv_(fortran_int *n, fortran_int *nrhs, f2c_complex a[], fortran_int *lda,
    fortran_int ipiv[], f2c_complex b[], fortran_int *ldb, fortran_int *info);
fortran_int wasi_numpy_cgesv_(fortran_int *n, fortran_int *nrhs, f2c_complex a[], fortran_int *lda,
    fortran_int ipiv[], f2c_complex b[], fortran_int *ldb, fortran_int *info)
{
    cgesv_(n, nrhs, a, lda, ipiv, b, ldb, info);
    return 0;
}

void cgetrf_(fortran_int *m, fortran_int *n, f2c_complex a[], fortran_int *lda, fortran_int ipiv[],
    fortran_int *info);
fortran_int wasi_numpy_cgetrf_(fortran_int *m, fortran_int *n, f2c_complex a[], fortran_int *lda,
    fortran_int ipiv[], fortran_int *info)
{
    cgetrf_(m, n, a, lda, ipiv, info);
    return 0;
}

void cheevd_(char *jobz, char *uplo, fortran_int *n, f2c_complex a[], fortran_int *lda, float w[],
    f2c_complex work[], fortran_int *lwork, float rwork[], fortran_int *lrwork,
    fortran_int iwork[], fortran_int *liwork, fortran_int *info);
fortran_int wasi_numpy_cheevd_(char *jobz, char *uplo, fortran_int *n, f2c_complex a[],
    fortran_int *lda, float w[], f2c_complex work[], fortran_int *lwork, float rwork[],
    fortran_int *lrwork, fortran_int iwork[], fortran_int *liwork, fortran_int *info)
{
    cheevd_(jobz, uplo, n, a, lda, w, work, lwork, rwork, lrwork, iwork, liwork, info);
    return 0;
}

void cpotrf_(char *uplo, fortran_int *n, f2c_complex a[], fortran_int *lda, fortran_int *info);
fortran_int wasi_numpy_cpotrf_(char *uplo, fortran_int *n, f2c_complex a[], fortran_int *lda,
    fortran_int *info)
{
    cpotrf_(uplo, n, a, lda, info);
    return 0;
}

void dcopy_(fortran_int *n, double *sx, fortran_int *incx, double *sy, fortran_int *incy);
fortran_int wasi_numpy_dcopy_(fortran_int *n, double *sx, fortran_int *incx, double *sy,
    fortran_int *incy)
{
    dcopy_(n, sx, incx, sy, incy);
    return 0;
}

void dgeev_(char *jobvl, char *jobvr, fortran_int *n, double a[], fortran_int *lda, double wr[],
    double wi[], double vl[], fortran_int *ldvl, double vr[], fortran_int *ldvr, double work[],
    fortran_int lwork[], fortran_int *info);
fortran_int wasi_numpy_dgeev_(char *jobvl, char *jobvr, fortran_int *n, double a[],
    fortran_int *lda, double wr[], double wi[], double vl[], fortran_int *ldvl, double vr[],
    fortran_int *ldvr, double work[], fortran_int lwork[], fortran_int *info)
{
    dgeev_(jobvl, jobvr, n, a, lda, wr, wi, vl, ldvl, vr, ldvr, work, lwork, info);
    return 0;
}

void dgelsd_(fortran_int *m, fortran_int *n, fortran_int *nrhs, double a[], fortran_int *lda,
    double b[], fortran_int *ldb, double s[], double *rcond, fortran_int *rank, double work[],
    fortran_int *lwork, fortran_int iwork[], fortran_int *info);
fortran_int wasi_numpy_dgelsd_(fortran_int *m, fortran_int *n, fortran_int *nrhs, double a[],
    fortran_int *lda, double b[], fortran_int *ldb, double s[], double *rcond, fortran_int *rank,
    double work[], fortran_int *lwork, fortran_int iwork[], fortran_int *info)
{
    dgelsd_(m, n, nrhs, a, lda, b, ldb, s, rcond, rank, work, lwork, iwork, info);
    return 0;
}

void dgeqrf_(fortran_int *m, fortran_int *n, double a[], fortran_int *lda, double tau[],
    double work[], fortran_int *lwork, fortran_int *info);
fortran_int wasi_numpy_dgeqrf_(fortran_int *m, fortran_int *n, double a[], fortran_int *lda,
    double tau[], double work[], fortran_int *lwork, fortran_int *info)
{
    dgeqrf_(m, n, a, lda, tau, work, lwork, info);
    return 0;
}

void dgesdd_(char *jobz, fortran_int *m, fortran_int *n, double a[], fortran_int *lda, double s[],
    double u[], fortran_int *ldu, double vt[], fortran_int *ldvt, double work[],
    fortran_int *lwork, fortran_int iwork[], fortran_int *info);
fortran_int wasi_numpy_dgesdd_(char *jobz, fortran_int *m, fortran_int *n, double a[],
    fortran_int *lda, double s[], double u[], fortran_int *ldu, double vt[], fortran_int *ldvt,
    double work[], fortran_int *lwork, fortran_int iwork[], fortran_int *info)
{
    dgesdd_(jobz, m, n, a, lda, s, u, ldu, vt, ldvt, work, lwork, iwork, info);
    return 0;
}

void dgesv_(fortran_int *n, fortran_int *nrhs, double a[], fortran_int *lda, fortran_int ipiv[],
    double b[], fortran_int *ldb, fortran_int *info);
fortran_int wasi_numpy_dgesv_(fortran_int *n, fortran_int *nrhs, double a[], fortran_int *lda,
    fortran_int ipiv[], double b[], fortran_int *ldb, fortran_int *info)
{
    dgesv_(n, nrhs, a, lda, ipiv, b, ldb, info);
    return 0;
}

void dgetrf_(fortran_int *m, fortran_int *n, double a[], fortran_int *lda, fortran_int ipiv[],
    fortran_int *info);
fortran_int wasi_numpy_dgetrf_(fortran_int *m, fortran_int *n, double a[], fortran_int *lda,
    fortran_int ipiv[], fortran_int *info)
{
    dgetrf_(m, n, a, lda, ipiv, info);
    return 0;
}

void dorgqr_(fortran_int *m, fortran_int *n, fortran_int *k, double a[], fortran_int *lda,
    double tau[], double work[], fortran_int *lwork, fortran_int *info);
fortran_int wasi_numpy_dorgqr_(fortran_int *m, fortran_int *n, fortran_int *k, double a[],
    fortran_int *lda, double tau[], double work[], fortran_int *lwork, fortran_int *info)
{
    dorgqr_(m, n, k, a, lda, tau, work, lwork, info);
    return 0;
}

void dpotrf_(char *uplo, fortran_int *n, double a[], fortran_int *lda, fortran_int *info);
fortran_int wasi_numpy_dpotrf_(char *uplo, fortran_int *n, double a[], fortran_int *lda,
    fortran_int *info)
{
    dpotrf_(uplo, n, a, lda, info);
    return 0;
}

void dsyevd_(char *jobz, char *uplo, fortran_int *n, double a[], fortran_int *lda, double w[],
    double work[], fortran_int *lwork, fortran_int iwork[], fortran_int *liwork,
    fortran_int *info);
fortran_int wasi_numpy_dsyevd_(char *jobz, char *uplo, fortran_int *n, double a[],
    fortran_int *lda, double w[], double work[], fortran_int *lwork, fortran_int iwork[],
    fortran_int *liwork, fortran_int *info)
{
    dsyevd_(jobz, uplo, n, a, lda, w, work, lwork, iwork, liwork, info);
    return 0;
}

void scopy_(fortran_int *n, float *sx, fortran_int *incx, float *sy, fortran_int *incy);
fortran_int wasi_numpy_scopy_(fortran_int *n, float *sx, fortran_int *incx, float *sy,
    fortran_int *incy)
{
    scopy_(n, sx, incx, sy, incy);
    return 0;
}

void sgeev_(char *jobvl, char *jobvr, fortran_int *n, float a[], fortran_int *lda, float wr[],
    float wi[], float vl[], fortran_int *ldvl, float vr[], fortran_int *ldvr, float work[],
    fortran_int lwork[], fortran_int *info);
fortran_int wasi_numpy_sgeev_(char *jobvl, char *jobvr, fortran_int *n, float a[],
    fortran_int *lda, float wr[], float wi[], float vl[], fortran_int *ldvl, float vr[],
    fortran_int *ldvr, float work[], fortran_int lwork[], fortran_int *info)
{
    sgeev_(jobvl, jobvr, n, a, lda, wr, wi, vl, ldvl, vr, ldvr, work, lwork, info);
    return 0;
}

void sgelsd_(fortran_int *m, fortran_int *n, fortran_int *nrhs, float a[], fortran_int *lda,
    float b[], fortran_int *ldb, float s[], float *rcond, fortran_int *rank, float work[],
    fortran_int *lwork, fortran_int iwork[], fortran_int *info);
fortran_int wasi_numpy_sgelsd_(fortran_int *m, fortran_int *n, fortran_int *nrhs, float a[],
    fortran_int *lda, float b[], fortran_int *ldb, float s[], float *rcond, fortran_int *rank,
    float work[], fortran_int *lwork, fortran_int iwork[], fortran_int *info)
{
    sgelsd_(m, n, nrhs, a, lda, b, ldb, s, rcond, rank, work, lwork, iwork, info);
    return 0;
}

void sgesdd_(char *jobz, fortran_int *m, fortran_int *n, float a[], fortran_int *lda, float s[],
    float u[], fortran_int *ldu, float vt[], fortran_int *ldvt, float work[], fortran_int *lwork,
    fortran_int iwork[], fortran_int *info);
fortran_int wasi_numpy_sgesdd_(char *jobz, fortran_int *m, fortran_int *n, float a[],
    fortran_int *lda, float s[], float u[], fortran_int *ldu, float vt[], fortran_int *ldvt,
    float work[], fortran_int *lwork, fortran_int iwork[], fortran_int *info)
{
    sgesdd_(jobz, m, n, a, lda, s, u, ldu, vt, ldvt, work, lwork, iwork, info);
    return 0;
}

void sgesv_(fortran_int *n, fortran_int *nrhs, float a[], fortran_int *lda, fortran_int ipiv[],
    float b[], fortran_int *ldb, fortran_int *info);
fortran_int wasi_numpy_sgesv_(fortran_int *n, fortran_int *nrhs, float a[], fortran_int *lda,
    fortran_int ipiv[], float b[], fortran_int *ldb, fortran_int *info)
{
    sgesv_(n, nrhs, a, lda, ipiv, b, ldb, info);
    return 0;
}

void sgetrf_(fortran_int *m, fortran_int *n, float a[], fortran_int *lda, fortran_int ipiv[],
    fortran_int *info);
fortran_int wasi_numpy_sgetrf_(fortran_int *m, fortran_int *n, float a[], fortran_int *lda,
    fortran_int ipiv[], fortran_int *info)
{
    sgetrf_(m, n, a, lda, ipiv, info);
    return 0;
}

void spotrf_(char *uplo, fortran_int *n, float a[], fortran_int *lda, fortran_int *info);
fortran_int wasi_numpy_spotrf_(char *uplo, fortran_int *n, float a[], fortran_int *lda,
    fortran_int *info)
{
    spotrf_(uplo, n, a, lda, info);
    return 0;
}

void ssyevd_(char *jobz, char *uplo, fortran_int *n, float a[], fortran_int *lda, float w[],
    float work[], fortran_int *lwork, fortran_int iwork[], fortran_int *liwork, fortran_int *info);
fortran_int wasi_numpy_ssyevd_(char *jobz, char *uplo, fortran_int *n, float a[], fortran_int *lda,
    float w[], float work[], fortran_int *lwork, fortran_int iwork[], fortran_int *liwork,
    fortran_int *info)
{
    ssyevd_(jobz, uplo, n, a, lda, w, work, lwork, iwork, liwork, info);
    return 0;
}

void zcopy_(fortran_int *n, f2c_doublecomplex *sx, fortran_int *incx, f2c_doublecomplex *sy,
    fortran_int *incy);
fortran_int wasi_numpy_zcopy_(fortran_int *n, f2c_doublecomplex *sx, fortran_int *incx,
    f2c_doublecomplex *sy, fortran_int *incy)
{
    zcopy_(n, sx, incx, sy, incy);
    return 0;
}

void zgeev_(char *jobvl, char *jobvr, fortran_int *n, f2c_doublecomplex a[], fortran_int *lda,
    f2c_doublecomplex w[], f2c_doublecomplex vl[], fortran_int *ldvl, f2c_doublecomplex vr[],
    fortran_int *ldvr, f2c_doublecomplex work[], fortran_int *lwork, double rwork[],
    fortran_int *info);
fortran_int wasi_numpy_zgeev_(char *jobvl, char *jobvr, fortran_int *n, f2c_doublecomplex a[],
    fortran_int *lda, f2c_doublecomplex w[], f2c_doublecomplex vl[], fortran_int *ldvl,
    f2c_doublecomplex vr[], fortran_int *ldvr, f2c_doublecomplex work[], fortran_int *lwork,
    double rwork[], fortran_int *info)
{
    zgeev_(jobvl, jobvr, n, a, lda, w, vl, ldvl, vr, ldvr, work, lwork, rwork, info);
    return 0;
}

void zgelsd_(fortran_int *m, fortran_int *n, fortran_int *nrhs, f2c_doublecomplex a[],
    fortran_int *lda, f2c_doublecomplex b[], fortran_int *ldb, double s[], double *rcond,
    fortran_int *rank, f2c_doublecomplex work[], fortran_int *lwork, double rwork[],
    fortran_int iwork[], fortran_int *info);
fortran_int wasi_numpy_zgelsd_(fortran_int *m, fortran_int *n, fortran_int *nrhs,
    f2c_doublecomplex a[], fortran_int *lda, f2c_doublecomplex b[], fortran_int *ldb, double s[],
    double *rcond, fortran_int *rank, f2c_doublecomplex work[], fortran_int *lwork, double rwork[],
    fortran_int iwork[], fortran_int *info)
{
    zgelsd_(m, n, nrhs, a, lda, b, ldb, s, rcond, rank, work, lwork, rwork, iwork, info);
    return 0;
}

void zgeqrf_(fortran_int *m, fortran_int *n, f2c_doublecomplex a[], fortran_int *lda,
    f2c_doublecomplex tau[], f2c_doublecomplex work[], fortran_int *lwork, fortran_int *info);
fortran_int wasi_numpy_zgeqrf_(fortran_int *m, fortran_int *n, f2c_doublecomplex a[],
    fortran_int *lda, f2c_doublecomplex tau[], f2c_doublecomplex work[], fortran_int *lwork,
    fortran_int *info)
{
    zgeqrf_(m, n, a, lda, tau, work, lwork, info);
    return 0;
}

void zgesdd_(char *jobz, fortran_int *m, fortran_int *n, f2c_doublecomplex a[], fortran_int *lda,
    double s[], f2c_doublecomplex u[], fortran_int *ldu, f2c_doublecomplex vt[], fortran_int *ldvt,
    f2c_doublecomplex work[], fortran_int *lwork, double rwork[], fortran_int iwork[],
    fortran_int *info);
fortran_int wasi_numpy_zgesdd_(char *jobz, fortran_int *m, fortran_int *n, f2c_doublecomplex a[],
    fortran_int *lda, double s[], f2c_doublecomplex u[], fortran_int *ldu, f2c_doublecomplex vt[],
    fortran_int *ldvt, f2c_doublecomplex work[], fortran_int *lwork, double rwork[],
    fortran_int iwork[], fortran_int *info)
{
    zgesdd_(jobz, m, n, a, lda, s, u, ldu, vt, ldvt, work, lwork, rwork, iwork, info);
    return 0;
}

void zgesv_(fortran_int *n, fortran_int *nrhs, f2c_doublecomplex a[], fortran_int *lda,
    fortran_int ipiv[], f2c_doublecomplex b[], fortran_int *ldb, fortran_int *info);
fortran_int wasi_numpy_zgesv_(fortran_int *n, fortran_int *nrhs, f2c_doublecomplex a[],
    fortran_int *lda, fortran_int ipiv[], f2c_doublecomplex b[], fortran_int *ldb,
    fortran_int *info)
{
    zgesv_(n, nrhs, a, lda, ipiv, b, ldb, info);
    return 0;
}

void zgetrf_(fortran_int *m, fortran_int *n, f2c_doublecomplex a[], fortran_int *lda,
    fortran_int ipiv[], fortran_int *info);
fortran_int wasi_numpy_zgetrf_(fortran_int *m, fortran_int *n, f2c_doublecomplex a[],
    fortran_int *lda, fortran_int ipiv[], fortran_int *info)
{
    zgetrf_(m, n, a, lda, ipiv, info);
    return 0;
}

void zheevd_(char *jobz, char *uplo, fortran_int *n, f2c_doublecomplex a[], fortran_int *lda,
    double w[], f2c_doublecomplex work[], fortran_int *lwork, double rwork[], fortran_int *lrwork,
    fortran_int iwork[], fortran_int *liwork, fortran_int *info);
fortran_int wasi_numpy_zheevd_(char *jobz, char *uplo, fortran_int *n, f2c_doublecomplex a[],
    fortran_int *lda, double w[], f2c_doublecomplex work[], fortran_int *lwork, double rwork[],
    fortran_int *lrwork, fortran_int iwork[], fortran_int *liwork, fortran_int *info)
{
    zheevd_(jobz, uplo, n, a, lda, w, work, lwork, rwork, lrwork, iwork, liwork, info);
    return 0;
}

void zpotrf_(char *uplo, fortran_int *n, f2c_doublecomplex a[], fortran_int *lda,
    fortran_int *info);
fortran_int wasi_numpy_zpotrf_(char *uplo, fortran_int *n, f2c_doublecomplex a[], fortran_int *lda,
    fortran_int *info)
{
    zpotrf_(uplo, n, a, lda, info);
    return 0;
}

void zungqr_(fortran_int *m, fortran_int *n, fortran_int *k, f2c_doublecomplex a[],
    fortran_int *lda, f2c_doublecomplex tau[], f2c_doublecomplex work[], fortran_int *lwork,
    fortran_int *info);
fortran_int wasi_numpy_zungqr_(fortran_int *m, fortran_int *n, fortran_int *k,
    f2c_doublecomplex a[], fortran_int *lda, f2c_doublecomplex tau[], f2c_doublecomplex work[],
    fortran_int *lwork, fortran_int *info)
{
    zungqr_(m, n, k, a, lda, tau, work, lwork, info);
    return 0;
}
