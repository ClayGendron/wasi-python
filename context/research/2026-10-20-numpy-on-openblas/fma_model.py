"""Does fused multiply-add explain the 46? A pure-Python LU with partial pivoting, right-looking as
reference dgetf2, in two arithmetics: a - l*u rounded twice (wasm has no FMA), and math.fma(-l, u, a)
rounded once (arm64's fmla). E when a pivot is exactly 0. Compared, per matrix, with native numpy on
OpenBLAS and with the guest's OpenBLAS. Usage: fma_model.py <native.out> <guest.json>"""

import json
import math
import sys

import numpy as np

native = next(line.split()[1] for line in open(sys.argv[1]) if line.startswith("inv "))
guest = next(
    line.split()[1] for line in json.load(open(sys.argv[2]))["stdout"].splitlines() if line.startswith("gesv ")
)


def lu_singular(a, fused):
    a = [list(map(float, row)) for row in a]
    n = len(a)
    for j in range(n):
        p = max(range(j, n), key=lambda i: abs(a[i][j]))
        if a[p][j] == 0.0:
            return True
        a[j], a[p] = a[p], a[j]
        for i in range(j + 1, n):
            l = a[i][j] / a[j][j]
            a[i][j] = l
            for c in range(j + 1, n):
                a[i][c] = math.fma(-l, a[j][c], a[i][c]) if fused else a[i][c] - l * a[j][c]
    return False


rng = np.random.default_rng(99)
plain, fused = [], []
for i in range(300):
    n = int(rng.integers(3, 8))
    k = int(rng.integers(1, n))
    a = (rng.integers(-5, 6, size=(n, k)) @ rng.integers(-5, 6, size=(k, n))).astype(float)
    if rng.random() < 0.5:
        a = a * 0.1
    plain.append("E" if lu_singular(a, False) else "F")
    fused.append("E" if lu_singular(a, True) else "F")


def agree(x, y):
    return sum(1 for p, q in zip(x, y) if (p == "E") == (q == "E"))


print("model without FMA vs guest OpenBLAS:", agree(plain, guest), "/300")
print("model with FMA    vs native OpenBLAS:", agree(fused, native), "/300")
print("model without FMA vs native OpenBLAS:", agree(plain, native), "/300")
print("model with FMA    vs guest OpenBLAS:", agree(fused, guest), "/300")
print("E counts: no-FMA", plain.count("E"), "FMA", fused.count("E"), "guest", guest.count("E"), "native", native.count("E"))
