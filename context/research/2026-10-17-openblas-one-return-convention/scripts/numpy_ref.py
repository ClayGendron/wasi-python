"""Independent reference: the probe's inputs regenerated in numpy and solved by numpy's own LAPACK
(the numpy wheel's bundled OpenBLAS, Fortran Reference-LAPACK compiled by gfortran). Eigenvalues are compared
as sorted sets, since dgees orders them by its SELECT and numpy does not.
usage: uv run --no-project --python <venv with numpy> python -I numpy_ref.py <probe-wasm.txt>"""
import sys
import numpy as np

M64 = (1 << 64) - 1


class LCG:
    def __init__(self): self.s = 12345
    def __call__(self):
        self.s = (self.s * 6364136223846793005 + 1442695040888963407) & M64
        return (self.s >> 11) / 9007199254740992.0 - 0.5


def gen(m, k):
    r = LCG(); return np.array([r() for _ in range(m * k)]).reshape((k, m)).T


def spd(n):
    i = np.arange(n); return 1.0 / (1 + i[:, None] + i[None, :]) + np.eye(n)


w = {}
for line in open(sys.argv[1]):
    k, v = line.split(None, 1); w[k] = float(v)
vec = lambda p, n: np.array([w[f"{p}[{i}]"] for i in range(n)])
ref = {}
ref["dgesv.x"] = (np.linalg.solve(spd(64), np.ones(64)), vec("dgesv.x", 64))
ref["dsyev.w"] = (np.linalg.eigvalsh(spd(64)), vec("dsyev.w", 64))
ref["dsyevr.w"] = (np.linalg.eigvalsh(spd(64)), vec("dsyevr.w", 64))
ref["dgesdd64.s0"] = (np.linalg.svd(spd(64), compute_uv=False)[:1], np.array([w["dgesdd64.s0"]]))
ref["dgesdd.s"] = (np.linalg.svd(gen(80, 48), compute_uv=False), vec("dgesdd.s", 48))
r = LCG(); flat = [complex(r(), r()) for _ in range(80 * 48)]
ref["zgesdd.s"] = (np.linalg.svd(np.array(flat).reshape((48, 80)).T, compute_uv=False), vec("zgesdd.s", 48))
ev = np.linalg.eigvals(gen(64, 64))
key = lambda z: (round(z.real, 9), round(z.imag, 9))
ref["dgees.eig(sorted)"] = (np.array(sorted(ev, key=key)), np.array(sorted(vec("dgees.wr", 64) + 1j * vec("dgees.wi", 64), key=key)))
ref["dgees.sdim(=#Re>0)"] = (np.array([float((ev.real > 0).sum())]), np.array([w["dgees.sdim"]]))
ok = True
print(f"numpy {np.__version__}")
for k, (a, b) in ref.items():
    rel = np.max(np.abs(a - b)) / np.max(np.abs(a))
    ok &= rel <= 1e-10
    print(f"{k:22s} {'pass' if rel <= 1e-10 else 'FAIL'}  n={a.size:3d}  max|d|/max|x| = {rel:.2e}")
print(f"ALL {'PASS' if ok else 'FAIL'} against numpy (tolerance 1e-10 relative)")
