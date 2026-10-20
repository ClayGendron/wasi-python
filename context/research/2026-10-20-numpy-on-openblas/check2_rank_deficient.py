import numpy as np
from scipy.linalg import lapack

rng = np.random.default_rng(99)
num, sci = [], []
for _ in range(300):
    n = int(rng.integers(3, 8))
    k = int(rng.integers(1, n))
    a = (rng.integers(-5, 6, size=(n, k)) @ rng.integers(-5, 6, size=(k, n))).astype(float)
    if rng.random() < 0.5:
        a = a * 0.1
    try:
        r = np.linalg.inv(a)
        num.append("N" if np.isnan(r).all() else "F" if np.isfinite(r).all() else "M")
    except np.linalg.LinAlgError:
        num.append("E")
    info = lapack.dgesv(a, np.eye(n))[-1]
    sci.append("E" if info > 0 else "F" if info == 0 else "?")
print("numpy", "".join(num))
print("scipy", "".join(sci))
print("agree", sum(p == q for p, q in zip(num, sci)))
