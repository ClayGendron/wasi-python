/* Calls seven LAPACK drivers of OpenBLAS's C LAPACK on fixed inputs and prints every result as `key value`.
 * Every prototype is the new convention: all subroutines `void`, no hidden string lengths (OpenBLAS's C
 * translation has none). The same file is built for wasm32-wasip1 and natively; compare.py compares the two.
 * Each routine runs in its own process (argv[1]) so one trap cannot hide the others' results.
 * dgees_ sorts with a C callback through LAPACK's function pointer: the indirect call wasm-ld cannot check. */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { double r, i; } dcomplex;
void dgesv_(int*, int*, double*, int*, int*, double*, int*, int*);
void dgetrf_(int*, int*, double*, int*, int*, int*);
void dpotrf_(char*, int*, double*, int*, int*);
void dgeqrf_(int*, int*, double*, int*, double*, double*, int*, int*);
void dsyev_(char*, char*, int*, double*, int*, double*, double*, int*, int*);
void dsyevr_(char*, char*, char*, int*, double*, int*, double*, double*, int*, int*, double*, int*, double*,
             double*, int*, int*, double*, int*, int*, int*, int*);
void dgesdd_(char*, int*, int*, double*, int*, double*, double*, int*, double*, int*, double*, int*, int*, int*);
void zgesdd_(char*, int*, int*, dcomplex*, int*, double*, dcomplex*, int*, dcomplex*, int*, dcomplex*, int*,
             double*, int*, int*);
void dgees_(char*, char*, int (*)(double*, double*), int*, double*, int*, int*, double*, double*, double*, int*,
            double*, int*, int*, int*);

enum { N = 64, M = 80, K = 48 };
static unsigned long long seed = 12345;
static double rnd(void) { seed = seed * 6364136223846793005ULL + 1442695040888963407ULL; return (double)(seed >> 11) / 9007199254740992.0 - 0.5; }
/* the scipy memo's matrix: 1/(1+i+j) + I, symmetric positive definite */
static void spd(double *a, int n) { for (int j = 0; j < n; j++) for (int i = 0; i < n; i++) a[i + j * n] = 1.0 / (1 + i + j) + (i == j); }
static void gen(double *a, int len) { for (int i = 0; i < len; i++) a[i] = rnd(); }
static void pv(const char *k, const double *v, int len) { for (int i = 0; i < len; i++) printf("%s[%d] %.17g\n", k, i, v[i]); }
static void p1(const char *k, double v) { printf("%s %.17g\n", k, v); }
static int calls = 0;
static int select_pos(double *wr, double *wi) { (void)wi; calls++; return *wr > 0; }

static double a[M * M], a0[M * M], b[M], w[M], z[M * M], u[M * M], vt[M * M], work[8 * M * M], tau[M];
static int ipiv[M], iw[16 * M], bwork[M], isuppz[2 * M];
static dcomplex ca[M * K], ca0[M * K], cu[M * M], cvt[K * K], cwork[8 * M * M];
static double rwork[8 * M * M];

int main(int argc, char **argv) {
  const char *which = argc > 1 ? argv[1] : "";
  int n = N, one = 1, info = -999, lwork = 8 * M * M;
  if (!strcmp(which, "dgesv")) {
    spd(a, n); for (int i = 0; i < n; i++) b[i] = 1;
    dgesv_(&n, &one, a, &n, ipiv, b, &n, &info);
    p1("dgesv.info", info); pv("dgesv.x", b, n);
  } else if (!strcmp(which, "dgetrf")) {
    gen(a, n * n);
    dgetrf_(&n, &n, a, &n, ipiv, &info);
    p1("dgetrf.info", info);
    for (int i = 0; i < n; i++) printf("dgetrf.ipiv[%d] %d\n", i, ipiv[i]);
    for (int i = 0; i < n; i++) printf("dgetrf.U[%d,%d] %.17g\n", i, i, a[i + i * n]);
    for (int i = 0; i < n; i += 7) for (int j = 0; j < n; j += 5) printf("dgetrf.LU[%d,%d] %.17g\n", i, j, a[i + j * n]);
  } else if (!strcmp(which, "dpotrf")) {
    spd(a, n); char up = 'L';
    dpotrf_(&up, &n, a, &n, &info);
    p1("dpotrf.info", info);
    for (int j = 0; j < n; j += 3) for (int i = j; i < n; i += 5) printf("dpotrf.L[%d,%d] %.17g\n", i, j, a[i + j * n]);
  } else if (!strcmp(which, "dgeqrf")) {
    spd(a, n);
    dgeqrf_(&n, &n, a, &n, tau, work, &lwork, &info);
    p1("dgeqrf.info", info); for (int i = 0; i < n; i++) printf("dgeqrf.R[%d,%d] %.17g\n", i, i, a[i + i * n]);
  } else if (!strcmp(which, "dsyev")) {
    spd(a, n); char jv = 'N', up = 'U';
    dsyev_(&jv, &up, &n, a, &n, w, work, &lwork, &info);
    p1("dsyev.info", info); pv("dsyev.w", w, n);
  } else if (!strcmp(which, "dsyevr")) {
    spd(a, n); memcpy(a0, a, sizeof(double) * n * n);
    char jz = 'V', rg = 'A', up = 'U'; double vl = 0, vu = 0, tol = 0; int il = 0, iu = 0, m = 0, liw = 16 * M;
    dsyevr_(&jz, &rg, &up, &n, a, &n, &vl, &vu, &il, &iu, &tol, &m, w, z, &n, isuppz, work, &lwork, iw, &liw, &info);
    p1("dsyevr.info", info); p1("dsyevr.m", m); pv("dsyevr.w", w, m);
    double res = 0, nrm = 0; /* max |A z_k - w_k z_k| */
    for (int k = 0; k < m; k++) for (int i = 0; i < n; i++) {
      double s = 0; for (int j = 0; j < n; j++) s += a0[i + j * n] * z[j + k * n];
      res = fmax(res, fabs(s - w[k] * z[i + k * n]));
    }
    for (int i = 0; i < n * n; i++) nrm = fmax(nrm, fabs(a0[i]));
    p1("dsyevr.residual_ok", res / nrm < 1e-12);
  } else if (!strcmp(which, "dgesdd")) {
    int m = M, k = K; gen(a, m * k); memcpy(a0, a, sizeof(double) * m * k); char jz = 'S';
    dgesdd_(&jz, &m, &k, a, &m, w, u, &m, vt, &k, work, &lwork, iw, &info);
    p1("dgesdd.info", info); pv("dgesdd.s", w, k);
    double res = 0; /* max |A - U S Vt| */
    for (int i = 0; i < m; i++) for (int j = 0; j < k; j++) {
      double s = 0; for (int l = 0; l < k; l++) s += u[i + l * m] * w[l] * vt[l + j * k];
      res = fmax(res, fabs(s - a0[i + j * m]));
    }
    p1("dgesdd.residual_ok", res < 1e-12);
  } else if (!strcmp(which, "dgesdd64")) { /* the memo's trapping call, unchanged */
    spd(a, n); char jz = 'S';
    dgesdd_(&jz, &n, &n, a, &n, w, u, &n, vt, &n, work, &lwork, iw, &info);
    p1("dgesdd64.info", info); p1("dgesdd64.s0", w[0]);
  } else if (!strcmp(which, "zgesdd")) {
    int m = M, k = K; char jz = 'S';
    for (int i = 0; i < m * k; i++) { ca[i].r = rnd(); ca[i].i = rnd(); }
    memcpy(ca0, ca, sizeof(dcomplex) * m * k);
    zgesdd_(&jz, &m, &k, ca, &m, w, cu, &m, cvt, &k, cwork, &lwork, rwork, iw, &info);
    p1("zgesdd.info", info); pv("zgesdd.s", w, k);
    double res = 0;
    for (int i = 0; i < m; i++) for (int j = 0; j < k; j++) {
      double sr = 0, si = 0;
      for (int l = 0; l < k; l++) {
        dcomplex x = cu[i + l * m], y = cvt[l + j * k];
        sr += w[l] * (x.r * y.r - x.i * y.i); si += w[l] * (x.r * y.i + x.i * y.r);
      }
      res = fmax(res, hypot(sr - ca0[i + j * m].r, si - ca0[i + j * m].i));
    }
    p1("zgesdd.residual_ok", res < 1e-12);
  } else if (!strcmp(which, "dgees")) {
    gen(a, n * n); memcpy(a0, a, sizeof(double) * n * n); char jv = 'V', srt = 'S'; int sdim = -1;
    dgees_(&jv, &srt, select_pos, &n, a, &n, &sdim, w, b, z, &n, work, &lwork, bwork, &info);
    p1("dgees.info", info); p1("dgees.sdim", sdim); p1("dgees.select_called", calls > 0);
    pv("dgees.wr", w, n); pv("dgees.wi", b, n);
    double res = 0; /* max |A Z - Z T| */
    for (int i = 0; i < n; i++) for (int j = 0; j < n; j++) {
      double s1 = 0, s2 = 0;
      for (int l = 0; l < n; l++) { s1 += a0[i + l * n] * z[l + j * n]; s2 += z[i + l * n] * a[l + j * n]; }
      res = fmax(res, fabs(s1 - s2));
    }
    p1("dgees.residual_ok", res < 1e-12);
  } else {
    fprintf(stderr, "usage: lapack_void dgesv|dgetrf|dpotrf|dgeqrf|dsyev|dsyevr|dgesdd|dgesdd64|zgesdd|dgees\n");
    return 2;
  }
  return 0;
}
