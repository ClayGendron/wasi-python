"""Spec 099's singular-detection probe (the pre-build review's finding 1): which exactly
rank-deficient matrices make numpy's LAPACK report a failure. 300 integer matrices, n from 3 to 7,
rank below n, a fixed seed, every second one scaled by 0.1; then named cases. One line per case:
`raises` (LinAlgError), `all-nan` (the guest's error fill before spec 099: it raises after), or
`finite`. Then the counts. Natively (the oracle's macosx_14_0_arm64 wheel) numpy runs Apple's
Accelerate (first written here as OpenBLAS; corrected after question 107); in the guest, numpy's
own lapack_lite."""

import numpy as np

rng = np.random.default_rng(99)


def outcome(a):
    try:
        r = np.linalg.inv(a)
    except np.linalg.LinAlgError:
        return "raises"
    return "all-nan" if np.isnan(r).all() else ("some-nan" if np.isnan(r).any() else "finite")


counts = {}
for i in range(300):
    n = int(rng.integers(3, 8))
    k = int(rng.integers(1, n))
    a = (rng.integers(-9, 10, (n, k)) @ rng.integers(-9, 10, (k, n))).astype(np.float64)
    if i % 2:
        a *= 0.1
    got = outcome(a)
    counts[got] = counts.get(got, 0) + 1
    print(f"case {i:3d} n={n} rank<={k} {got}")
print("named arange(1,17).reshape(4,4)", outcome(np.arange(1.0, 17.0).reshape(4, 4)))
print("named [[1,2],[2,4]]", outcome(np.array([[1.0, 2.0], [2.0, 4.0]])))
print("named [[1,2,3],[4,5,6],[7,8,9]]", outcome(np.arange(1.0, 10.0).reshape(3, 3)))
print("counts", dict(sorted(counts.items())))
