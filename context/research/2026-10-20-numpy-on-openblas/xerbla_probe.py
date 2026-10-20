# numpy.linalg.lapack_lite's xerbla and dorgqr error path (numpy's test_xerbla_override, without fork).
import numpy as np
from numpy.linalg import lapack_lite

try:
    lapack_lite.xerbla()
    print("xerbla returned")
except ValueError as e:
    print("xerbla ValueError", e)
a = np.array([[1.0]])
try:
    r = lapack_lite.dorgqr(1, 1, 1, a, 0, a, a, 0, 0)
    print("dorgqr returned", r)
except ValueError as e:
    print("dorgqr ValueError", e)
