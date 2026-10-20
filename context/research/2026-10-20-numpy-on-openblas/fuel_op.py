# One linear-algebra operation, chosen by the OP environment variable, on a fixed 200x200 matrix:
# numpy's own (lapack_lite in today's guest) beside the same LAPACK routine on the set's OpenBLAS
# through scipy. "none" is the baseline: imports and the matrix only.
import os

import numpy as np
from scipy.linalg import blas, lapack

n = 200
rng = np.random.default_rng(7)
a = rng.standard_normal((n, n))
s = a + a.T
f = np.asfortranarray(a)
op = os.environ["OP"]
reps = 5
for _ in range(reps):
    if op == "none":
        pass
    elif op == "np_inv":
        np.linalg.inv(a)
    elif op == "ob_gesv":
        lapack.dgesv(a, np.eye(n))
    elif op == "np_svd":
        np.linalg.svd(a, compute_uv=False)
    elif op == "ob_gesdd":
        lapack.dgesdd(a, compute_uv=0)
    elif op == "np_eigh":
        np.linalg.eigh(s)
    elif op == "ob_syevd":
        lapack.dsyevd(s, compute_v=1)
    elif op == "np_matmul":
        a @ a
    elif op == "ob_gemm":
        blas.dgemm(1.0, f, f)
    elif op == "np_dot_vec":
        a[0] @ a[1]
    else:
        raise SystemExit("unknown OP " + op)
print(op, "done")
