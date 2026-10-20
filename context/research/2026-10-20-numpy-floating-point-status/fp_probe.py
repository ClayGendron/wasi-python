"""Spec 099's drafting probe: what numpy reports, by explicit floating-point status, natively and
in the guest. One line per case: the case's name, then what happened."""

import warnings

import numpy as np

S = np.array([[1.0, 2.0], [2.0, 4.0]])  # singular, rank 1
NPD = np.array([[1.0, 2.0], [2.0, 1.0]])  # symmetric, not positive definite
NAN = np.full((3, 3), np.nan)


def outcome(fn):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            r = fn()
        except Exception as e:  # noqa: BLE001
            return f"raises {type(e).__name__}: {e}"
    shown = ""
    if isinstance(r, np.ndarray):
        shown = "all-nan" if np.isnan(r).all() else ("some-nan" if np.isnan(r).any() else "finite")
    elif isinstance(r, tuple):
        parts = [np.asarray(x) for x in r]
        shown = "tuple " + ",".join(
            "all-nan" if np.isnan(p).all() else ("some-nan" if np.isnan(p).any() else "finite")
            for p in parts
            if p.dtype.kind in "fc"
        )
    else:
        shown = repr(r)
    warned = "; ".join(f"{x.category.__name__}: {x.message}" for x in w)
    return f"returns {shown}" + (f" + warns {warned}" if warned else "")


CASES = {
    # numpy.linalg, through umath_linalg's invalid flag
    "linalg.inv(singular)": lambda: np.linalg.inv(S),
    "linalg.solve(singular)": lambda: np.linalg.solve(S, np.array([1.0, 1.0])),
    "linalg.tensorinv(singular)": lambda: np.linalg.tensorinv(S.reshape(2, 2), ind=1),
    "linalg.tensorsolve(singular)": lambda: np.linalg.tensorsolve(S, np.array([1.0, 1.0])),
    "linalg.matrix_power(singular,-1)": lambda: np.linalg.matrix_power(S, -1),
    "linalg.inv(stacked, one singular)": lambda: np.linalg.inv(np.stack([np.eye(2), S])),
    "linalg.inv(singular, float32)": lambda: np.linalg.inv(S.astype(np.float32)),
    "linalg.inv(singular, complex)": lambda: np.linalg.inv(S.astype(np.complex128)),
    "linalg.cholesky(not posdef)": lambda: np.linalg.cholesky(NPD),
    "linalg.cholesky(not posdef, upper)": lambda: np.linalg.cholesky(NPD, upper=True),
    "linalg.svd(nan)": lambda: np.linalg.svd(NAN),
    "linalg.svd(nan, no uv)": lambda: np.linalg.svd(NAN, compute_uv=False),
    "linalg.svdvals(nan)": lambda: np.linalg.svdvals(NAN),
    "linalg.pinv(nan)": lambda: np.linalg.pinv(NAN),
    "linalg.matrix_rank(nan)": lambda: np.linalg.matrix_rank(NAN),
    "linalg.norm(nan, 2)": lambda: np.linalg.norm(NAN, 2),
    "linalg.cond(nan)": lambda: np.linalg.cond(NAN),
    "linalg.lstsq(nan)": lambda: np.linalg.lstsq(NAN, np.ones(3), rcond=None),
    "linalg.eigh(nan)": lambda: np.linalg.eigh(NAN),
    "linalg.eigvalsh(nan)": lambda: np.linalg.eigvalsh(NAN),
    "linalg.eig(nan)": lambda: np.linalg.eig(NAN),
    "linalg.det(singular)": lambda: np.linalg.det(S),
    "linalg.slogdet(singular)": lambda: np.linalg.slogdet(S),
    "linalg.inv(regular)": lambda: np.linalg.inv(np.array([[2.0, 1.0], [1.0, 3.0]])),
    # errstate with linalg
    "errstate(invalid=ignore) does not hide inv": lambda: _ignored_inv(),
    # integer arithmetic: explicit npy_set_floatstatus_* in numpy's loops
    "int array // 0": lambda: np.array([1, 2], dtype=np.int64) // 0,
    "int array % 0": lambda: np.array([1, 2], dtype=np.int64) % 0,
    "divmod(int array, 0)": lambda: np.divmod(np.array([1, 2], dtype=np.int64), 0),
    "int32 min // -1": lambda: np.array([np.iinfo(np.int32).min], dtype=np.int32) // -1,
    "errstate(divide=raise) int // 0": lambda: _raise_int_div(),
    "int scalar // 0": lambda: np.int64(1) // np.int64(0),
    "int8 scalar overflow": lambda: np.int8(127) + np.int8(1),
    "timedelta // 0": lambda: np.array([10], dtype="m8[s]") // np.timedelta64(0, "s"),
    # floating point: hardware flags natively, explicit in some loops
    "float array // 0.0": lambda: np.array([1.0, -1.0]) // 0.0,
    "float array % 0.0": lambda: np.array([1.0]) % 0.0,
    "float array / 0.0": lambda: np.array([1.0]) / 0.0,
    "log(0.0)": lambda: np.log(np.array([0.0])),
    "sqrt(-1.0)": lambda: np.sqrt(np.array([-1.0])),
    "exp(1000.0)": lambda: np.exp(np.array([1000.0])),
    "float64 -> float16 overflow": lambda: np.array([1e6]).astype(np.float16),
    "float -> int nan cast": lambda: np.array([np.nan]).astype(np.int64),
    "float scalar / 0.0": lambda: np.float64(1.0) / np.float64(0.0),
}


def _ignored_inv():
    with np.errstate(invalid="ignore"):
        return np.linalg.inv(S)


def _raise_int_div():
    with np.errstate(divide="raise"):
        return np.array([1], dtype=np.int64) // 0


for name, fn in CASES.items():
    print(f"{name:45} {outcome(fn)}")
print("status after:", np.geterr())
