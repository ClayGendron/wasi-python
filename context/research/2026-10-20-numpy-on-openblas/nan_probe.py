# Spec 100's drafting probe: a 3x3 matrix of nan through numpy.linalg (whatever LAPACK numpy has)
# and through the LAPACK routine numpy's umath_linalg calls for it, called by scipy on its OpenBLAS
# with numpy's own job arguments: info > 0 or < 0 means numpy (with spec 099) raises LinAlgError.
import numpy as np

try:
    from scipy.linalg import lapack
except ImportError:
    lapack = None

a = np.full((3, 3), np.nan)
b = np.full((3, 1), np.nan)
print("numpy", np.__version__)


def numpy_case(name, f):
    try:
        r = f()
        rs = r if isinstance(r, tuple) else (r,)
        def kind(x):
            x = np.asarray(x)
            return "all-nan" if np.isnan(x).all() else "finite" if np.isfinite(x).all() else "mixed"
        print(f"np {name:22s} returns", ",".join(kind(x) for x in rs))
    except Exception as e:
        print(f"np {name:22s} raises {type(e).__name__}: {e}")


numpy_case("svd", lambda: np.linalg.svd(a))
numpy_case("svd no uv", lambda: np.linalg.svd(a, compute_uv=False))
numpy_case("pinv", lambda: np.linalg.pinv(a))
numpy_case("matrix_rank", lambda: np.linalg.matrix_rank(a))
numpy_case("norm 2", lambda: np.linalg.norm(a, 2))
numpy_case("cond", lambda: np.linalg.cond(a))
numpy_case("lstsq", lambda: np.linalg.lstsq(a, b, rcond=None)[0])
numpy_case("eigh", lambda: np.linalg.eigh(a))
numpy_case("eigvalsh", lambda: np.linalg.eigvalsh(a))
numpy_case("eig", lambda: np.linalg.eig(a))
numpy_case("inv", lambda: np.linalg.inv(a))
numpy_case("solve", lambda: np.linalg.solve(a, b))
numpy_case("cholesky", lambda: np.linalg.cholesky(a))
numpy_case("qr", lambda: np.linalg.qr(a))
numpy_case("det", lambda: np.linalg.det(a))

if lapack is not None:
    def info_of(name, f):
        out = f()
        print(f"lapack {name:22s} info {int(out[-1])}")

    info_of("dgesdd jobz=A", lambda: lapack.dgesdd(a, compute_uv=1, full_matrices=1))
    info_of("dgesdd jobz=N", lambda: lapack.dgesdd(a, compute_uv=0))
    info_of("dgelsd", lambda: lapack.dgelsd(a, b, lwork=200, size_iwork=200))
    info_of("dsyevd jobz=V", lambda: lapack.dsyevd(a, compute_v=1))
    info_of("dsyevd jobz=N", lambda: lapack.dsyevd(a, compute_v=0))
    info_of("dgesv", lambda: lapack.dgesv(a, b))
    info_of("dpotrf", lambda: lapack.dpotrf(a, lower=1))
    info_of("dgeqrf", lambda: lapack.dgeqrf(a))
    w, iw, inf0 = lapack.dgelsd_lwork(3, 3, 1, -1.0)
    info_of("dgelsd (queried lwork)", lambda: lapack.dgelsd(a, b, lwork=int(w), size_iwork=int(iw), cond=-1.0))
    ar = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 10.0]])
    info_of("dgelsd regular control", lambda: lapack.dgelsd(ar, np.ones((3, 1)), lwork=int(w), size_iwork=int(iw), cond=-1.0))
