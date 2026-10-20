# Is scipy.linalg.lapack.dgesv(a, I) an exact proxy for numpy.linalg.inv(a) on one OpenBLAS?
# Natively both run the wheel's OpenBLAS 0.3.34 (numpy's ILP64 copy, scipy's LP64 copy).
import numpy as np
from scipy.linalg import lapack

rng = np.random.default_rng(99)
same = differ = 0
for i in range(300):
    n = int(rng.integers(3, 8))
    k = int(rng.integers(1, n))
    a = (rng.integers(-5, 6, size=(n, k)) @ rng.integers(-5, 6, size=(k, n))).astype(float)
    if rng.random() < 0.5:
        a = a * 0.1
    lu, piv, x, info = lapack.dgesv(a, np.eye(n))
    if info != 0:
        continue
    r = np.linalg.inv(a)
    if np.array_equal(r, x):
        same += 1
    else:
        differ += 1
print("finite inverses bit-identical:", same, "differ:", differ)
