# Spec 100's drafting probe: the pre-build review of 099's 300 exactly rank-deficient matrices (seed
# 99), each solved against the identity three ways where the module exists:
#   inv    numpy.linalg.inv: E raises LinAlgError, N returns all-nan, F returns finite, M mixed
#   gesv   scipy.linalg.lapack.dgesv(a, I): E info > 0, F info == 0 (the routine numpy's inv calls)
#   getrf  scipy.linalg.lapack.dgetrf(a): E info > 0, F info == 0
# then one line per matrix where a module is present: index, n, rank, the three letters.
import hashlib

import numpy as np

try:
    from scipy.linalg import lapack
except ImportError:
    lapack = None

rng = np.random.default_rng(99)
mats = []
for i in range(300):
    n = int(rng.integers(3, 8))
    k = int(rng.integers(1, n))
    a = (rng.integers(-5, 6, size=(n, k)) @ rng.integers(-5, 6, size=(k, n))).astype(float)
    if rng.random() < 0.5:
        a = a * 0.1
    mats.append((n, k, a))


def letter(r):
    if np.isnan(r).all():
        return "N"
    if np.isfinite(r).all():
        return "F"
    return "M"


inv, gesv, getrf = [], [], []
xs = hashlib.sha256()
for n, k, a in mats:
    try:
        inv.append(letter(np.linalg.inv(a)))
    except np.linalg.LinAlgError:
        inv.append("E")
    if lapack is not None:
        lu, piv, x, info = lapack.dgesv(a, np.eye(n))
        gesv.append("E" if info > 0 else "F" if info == 0 else f"?{info}")
        if info == 0:
            xs.update(np.ascontiguousarray(x).tobytes())
        lu2, piv2, info2 = lapack.dgetrf(a)
        getrf.append("E" if info2 > 0 else "F" if info2 == 0 else f"?{info2}")
print("inv  ", "".join(inv))
if lapack is not None:
    print("gesv ", "".join(gesv))
    print("getrf", "".join(getrf))
    print("gesv solutions sha256", xs.hexdigest()[:16])
    agree = sum(1 for p, q in zip(inv, gesv) if (p == "E") == (q == "E"))
    print("inv raises iff gesv info>0:", agree, "of 300")
