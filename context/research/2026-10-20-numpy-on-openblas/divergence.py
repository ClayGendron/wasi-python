"""Where the guest's OpenBLAS and native numpy on OpenBLAS disagree on the 300 matrices: each index
with n, the rank, whether it was scaled by 0.1, and the smallest |pivot| native's LU leaves.
Usage (native venv with scipy): divergence.py <native.out> <guest.json>"""

import json
import sys

import numpy as np
from scipy.linalg import lapack

native = next(line.split()[1] for line in open(sys.argv[1]) if line.startswith("inv "))
guest = next(
    line.split()[1] for line in json.load(open(sys.argv[2]))["stdout"].splitlines() if line.startswith("gesv ")
)
rng = np.random.default_rng(99)
rows = []
for i in range(300):
    n = int(rng.integers(3, 8))
    k = int(rng.integers(1, n))
    a = (rng.integers(-5, 6, size=(n, k)) @ rng.integers(-5, 6, size=(k, n))).astype(float)
    scaled = rng.random() < 0.5
    if scaled:
        a = a * 0.1
    rows.append((i, n, k, scaled, a))
diff = [r for r in rows if (native[r[0]] == "E") != (guest[r[0]] == "E")]
print("indices where they differ:", len(diff))
print(" ".join(str(r[0]) for r in diff))
print("scaled by 0.1 among them:", sum(r[3] for r in diff), "of", len(diff), "; among all 300:", sum(r[3] for r in rows))
print("native letter / guest letter at those:", sorted({native[r[0]] + guest[r[0]] for r in diff}))
for i, n, k, scaled, a in diff[:5]:
    lu, piv, info = lapack.dgetrf(a)
    print(f"  {i}: n={n} rank={k} scaled={scaled} native min|U_ii|={np.abs(np.diag(lu)).min():.3g}")
