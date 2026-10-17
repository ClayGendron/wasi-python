/* Each call uses the definition's own signature, so this file adds no clash; only OpenBLAS's internal ones remain. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int  dgesv_(int*, int*, double*, int*, int*, double*, int*, int*);          /* interface/lapack: int */
void dgeqrf_(int*, int*, double*, int*, double*, double*, int*, int*);      /* C LAPACK: void */
void dsyev_(char*, char*, int*, double*, int*, double*, double*, int*, int*);
void dgesdd_(char*, int*, int*, double*, int*, double*, double*, int*, double*, int*, double*, int*, int*, int*);
static void fill(double *a, int n) { for (int i = 0; i < n * n; i++) a[i] = 1.0 / (1 + (i % n) + (i / n)) + (i % (n + 1) == 0); }
int main(int argc, char **argv) {
  int n = 64, one = 1, info = 0, lwork = 64 * 64 * 4, ipiv[64], iw[8 * 64];
  static double a[64 * 64], b[64], tau[64], w[64], s[64], u[64 * 64], vt[64 * 64], work[64 * 64 * 4];
  const char *which = argc > 1 ? argv[1] : "gesv";
  fill(a, n); for (int i = 0; i < n; i++) b[i] = 1;
  if (!strcmp(which, "gesv")) { dgesv_(&n, &one, a, &n, ipiv, b, &n, &info); printf("dgesv info=%d x0=%.12f\n", info, b[0]); }
  if (!strcmp(which, "geqrf")) { dgeqrf_(&n, &n, a, &n, tau, work, &lwork, &info); printf("dgeqrf info=%d r00=%.12f\n", info, a[0]); }
  if (!strcmp(which, "syev")) { char v = 'N', u_ = 'U'; dsyev_(&v, &u_, &n, a, &n, w, work, &lwork, &info); printf("dsyev info=%d wmax=%.12f\n", info, w[n - 1]); }
  if (!strcmp(which, "gesdd")) { char j = 'S'; dgesdd_(&j, &n, &n, a, &n, s, u, &n, vt, &n, work, &lwork, iw, &info); printf("dgesdd info=%d s0=%.12f\n", info, s[0]); }
  return 0;
}
