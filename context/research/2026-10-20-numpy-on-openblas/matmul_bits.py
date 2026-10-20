# A 64x64 float64 product three ways where available, each printed as hex of its bytes:
#   np      a @ b through numpy (its own loop in today's guest; OpenBLAS's dgemm natively)
#   ob      scipy.linalg.blas.dgemm(1, a, b) on the binary's OpenBLAS
#   dot     a[0] @ b[:, 0], one length-64 dot product, through numpy
import numpy as np

try:
    from scipy.linalg import blas
except ImportError:
    blas = None

rng = np.random.default_rng(11)
a = rng.standard_normal((64, 64))
b = rng.standard_normal((64, 64))
print("np", (a @ b).tobytes().hex())
if blas is not None:
    print("ob", np.ascontiguousarray(blas.dgemm(1.0, a, b)).tobytes().hex())
print("dot", np.float64(a[0] @ b[:, 0]).tobytes().hex())
