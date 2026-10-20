import warnings

import numpy as np
from numpy.linalg import lapack_lite

warnings.simplefilter("ignore")
a = np.full((3, 3), np.nan)
b = np.full((3, 1), np.nan)


def kind(x):
    if isinstance(x, dict):
        return repr(x)
    x = np.asarray(x)
    return "all-nan" if np.isnan(x).all() else "finite" if np.isfinite(x).all() else "mixed"


def case(name, fn):
    try:
        r = fn()
        rs = r if isinstance(r, tuple) else (r,)
        out = "returns " + ",".join(kind(x) for x in rs)
    except Exception as e:
        out = f"raises {type(e).__name__}: {e}"
    print(f"{name:22s} {out}", flush=True)


case("svd", lambda: np.linalg.svd(a))
case("svd no uv", lambda: np.linalg.svd(a, compute_uv=False))
case("pinv", lambda: np.linalg.pinv(a))
case("matrix_rank", lambda: np.linalg.matrix_rank(a))
case("norm 2", lambda: np.linalg.norm(a, 2))
case("cond", lambda: np.linalg.cond(a))
case("lstsq", lambda: np.linalg.lstsq(a, b, rcond=None)[0])
case("eigh", lambda: np.linalg.eigh(a))
case("eigvalsh", lambda: np.linalg.eigvalsh(a))
case("eig", lambda: np.linalg.eig(a))
case("inv", lambda: np.linalg.inv(a))
case("solve", lambda: np.linalg.solve(a, b))
case("cholesky", lambda: np.linalg.cholesky(a))
case("qr", lambda: np.linalg.qr(a))
case("det", lambda: np.linalg.det(a))
case("xerbla", lambda: lapack_lite.xerbla())
one = np.array([[1.0]])
case("dorgqr lda 0", lambda: lapack_lite.dorgqr(1, 1, 1, one, 0, one, one, 0, 0))
