"""Spec 099's build finding B1: where numpy's lapack_lite error routine (python_xerbla, which sets a
Python ValueError) meets a LAPACK failure that umath_linalg reports by the invalid flag. Natively
numpy runs OpenBLAS, whose xerbla prints and returns. One line per case: what is raised, and the
exception's __context__ (the exception already set when the next one was raised)."""

import numpy as np

NAN = np.full((3, 3), np.nan)
INF = np.array([[np.inf, 1.0], [1.0, 1.0]])

CASES = {
    "lstsq(nan 3x3)": lambda: np.linalg.lstsq(NAN, np.ones(3), rcond=None),
    "lstsq(nan 2x3)": lambda: np.linalg.lstsq(np.full((2, 3), np.nan), np.ones(2), rcond=None),
    "lstsq(inf 2x2)": lambda: np.linalg.lstsq(INF, np.ones(2), rcond=None),
    "svd(nan, no uv)": lambda: np.linalg.svd(NAN, compute_uv=False),
    "svd(nan)": lambda: np.linalg.svd(NAN),
    "svd(inf)": lambda: np.linalg.svd(INF),
    "pinv(nan)": lambda: np.linalg.pinv(NAN),
    "eigh(nan)": lambda: np.linalg.eigh(NAN),
    "eigvalsh(nan)": lambda: np.linalg.eigvalsh(NAN),
    "solve(nan)": lambda: np.linalg.solve(NAN, np.ones(3)),
    "inv(nan)": lambda: np.linalg.inv(NAN),
    "inv(inf)": lambda: np.linalg.inv(INF),
    "cholesky(nan)": lambda: np.linalg.cholesky(NAN),
    "qr(nan)": lambda: np.linalg.qr(NAN),
}

for name, fn in CASES.items():
    try:
        r = fn()
        got = "returned"
    except Exception as e:  # noqa: BLE001
        ctx = e.__context__ or e.__cause__
        got = f"{type(e).__name__}: {e}"
        if ctx:
            got += f" [context {type(ctx).__name__}: {ctx}]"
    print(f"{name:18} {got}")
