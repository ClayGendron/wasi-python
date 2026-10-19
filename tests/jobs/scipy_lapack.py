"""Golden job: the LAPACK routines that trapped on wasm before OpenBLAS's carried patches (spec
037, Decisions 5 and 15). Usage: scipy_lapack.py <data dir> <out dir> (both unused). Runs natively
(the oracle) and in the guest; its output must be byte-identical in both.

Through `get_lapack_funcs` in all four precisions (f2py's `_flapack`, which calls LAPACK through
function pointers): gesv, getrf, getrs, laswp, lauum, potrf, trtri, trtrs; gees with a sort
callback (schur's `sort="lhp"`: its eigenvalues as a sorted set, and sdim); then eig, svd,
lstsq, pinv and qr_update (through `cython_lapack`). Double precisions print 9 significant digits,
single precisions 5 (float32 carries about 7, and its last bits depend on the order of a sum).
`ilaver()` prints only its shape: the guest's LAPACK is 3.12.0 and the oracle's may be another.
"""

import functools
import sys

import numpy as np
import scipy
from scipy import linalg
from scipy.linalg import lapack


def g(x, k):
    return format(float(x) + 0.0, f".{k}g")


def gs(values, k):
    values = np.ravel(values)
    if np.iscomplexobj(values):
        return " ".join(
            f"{g(v.real, k)}{'+' if v.imag >= 0 else '-'}{g(abs(v.imag), k)}j" for v in values
        )
    return " ".join(g(v, k) for v in values)


def show(label, fn):
    try:
        out = fn()
    except Exception as e:  # the golden records a failure as text, so a difference names it
        out = f"RAISES {type(e).__name__} {str(e)[:120]}"
    print(label, "->", out)


print(f"versions python={sys.version_info[0]}.{sys.version_info[1]} scipy={scipy.__version__}")
rng = np.random.Generator(np.random.PCG64(1664))
A0 = rng.standard_normal((4, 4)) + 4 * np.eye(4)
B0 = rng.standard_normal((4, 2))
C0 = rng.standard_normal((4, 4))
S0 = A0 @ A0.T + np.eye(4)
DIGITS = {"s": 5, "d": 9, "c": 5, "z": 9}
TYPES = {"s": np.float32, "d": np.float64, "c": np.complex64, "z": np.complex128}


def precision(p, dtype):
    k = DIGITS[p]
    cplx = p in "cz"
    A = (A0 + (0.5j * C0 if cplx else 0)).astype(dtype)
    B = B0.astype(dtype)
    S = (A @ A.conj().T + np.eye(4)).astype(dtype)
    U = np.triu(A).astype(dtype)
    gesv, getrf, getrs, laswp, lauum, potrf, trtri, trtrs = linalg.get_lapack_funcs(
        ("gesv", "getrf", "getrs", "laswp", "lauum", "potrf", "trtri", "trtrs"), (A,)
    )
    show(f"{p}gesv", lambda: (lambda r: f"info={r[3]} x={gs(r[2], k)}")(gesv(A, B)))
    lu, piv, info = getrf(A)
    show(f"{p}getrf", lambda: f"info={info} piv={piv.tolist()} diag={gs(np.diag(lu), k)}")
    show(f"{p}getrs", lambda: (lambda r: f"info={r[1]} x={gs(r[0], k)}")(getrs(lu, piv, B)))
    show(f"{p}laswp", lambda: gs(laswp(B.copy(), piv)[:, 0], k))
    show(f"{p}lauum", lambda: (lambda r: f"info={r[1]} diag={gs(np.diag(r[0]), k)}")(lauum(U)))
    show(f"{p}potrf", lambda: (lambda r: f"info={r[1]} diag={gs(np.diag(r[0]), k)}")(potrf(S)))
    show(f"{p}trtri", lambda: (lambda r: f"info={r[1]} diag={gs(np.diag(r[0]), k)}")(trtri(U)))
    show(f"{p}trtrs", lambda: (lambda r: f"info={r[1]} x={gs(r[0], k)}")(trtrs(U, B)))


for p, dtype in TYPES.items():
    precision(p, dtype)


def schur_lhp(dtype, k):
    M = np.array(
        [[0.5, 2.0, 0.5, 0.0], [-3.0, -1.5, 0.0, 1.0], [0.0, 0.5, -2.5, 1.0], [1.0, 0.0, -1.0, 2.5]]
    )
    out = "complex" if np.dtype(dtype).kind == "c" else "real"
    T, Z, sdim = linalg.schur(M.astype(dtype), output=out, sort="lhp")
    lam = np.linalg.eigvals(T.astype(np.complex128))
    # A real eigenvalue of a complex Schur form carries rounding noise in its imaginary part: an
    # imaginary part below 1e-4 of the value's size prints as 0, a stated bound.
    lam = [complex(v.real, 0.0) if abs(v.imag) < 1e-4 * abs(v) else v for v in lam]
    lam = sorted(lam, key=lambda v: (round(v.real, 3), round(v.imag, 3)))
    return f"sdim={sdim} eigenvalues={gs(np.array(lam), k)}"


for p, dtype in TYPES.items():
    show(f"{p}gees lhp", functools.partial(schur_lhp, dtype, DIGITS[p]))

# cython_lapack's callers (eig, svd, lstsq, pinv, qr_update) and the version's shape
show("eig", lambda: gs(sorted(linalg.eigvals(A0), key=lambda v: (v.real, v.imag)), 9))
show("svd", lambda: gs(linalg.svd(A0, compute_uv=False), 9))
show("lstsq", lambda: gs(linalg.lstsq(np.vstack([A0, C0]), np.arange(8.0))[0], 9))
show("pinv residual < 1e-12", lambda: bool(np.abs(linalg.pinv(A0) @ A0 - np.eye(4)).max() < 1e-12))


def qr_update():
    Q, R = linalg.qr(A0)
    u, v = rng.standard_normal(4), rng.standard_normal(4)
    Q1, R1 = linalg.qr_update(Q, R, u, v)
    rebuilt = bool(np.abs(Q1 @ R1 - (A0 + np.outer(u, v))).max() < 1e-12)
    return f"rebuilt<1e-12={rebuilt} |diag(R1)|={gs(np.abs(np.diag(R1)), 9)}"


show("qr_update", qr_update)
show(
    "ilaver",
    lambda: (
        lambda v: (
            f"three integers={len(v) == 3 and all(isinstance(i, int) for i in v)} major={v[0]}"
        )
    )(lapack.ilaver()),
)
