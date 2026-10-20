# Small-matrix costs, chosen by OP: 2,000 calls on a 3x3 matrix, numpy's own (lapack_lite and
# numpy's BLAS-less matmul in today's guest) beside the same routine on OpenBLAS through scipy's
# wrappers (which add their own f2py overhead, so the OpenBLAS side is an upper bound).
import os

import numpy as np
from scipy.linalg import blas, lapack

a = np.array([[2.0, 1.0, 0.5], [1.0, 3.0, 0.25], [0.5, 0.25, 4.0]])
f = np.asfortranarray(a)
eye = np.eye(3)
op = os.environ["OP"]
for _ in range(2000):
    if op == "none":
        pass
    elif op == "np_matmul3":
        a @ a
    elif op == "ob_gemm3":
        blas.dgemm(1.0, f, f)
    elif op == "np_inv3":
        np.linalg.inv(a)
    elif op == "ob_gesv3":
        lapack.dgesv(a, eye)
print(op, "done")
