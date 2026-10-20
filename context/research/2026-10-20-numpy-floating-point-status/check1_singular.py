import numpy as np

S = np.array([[1.0, 2.0], [2.0, 4.0]])  # singular: LU's second pivot is exactly 0
N = np.array([[1.0, 2.0], [2.0, 1.0]])  # symmetric, not positive definite


def case(name, fn):
    try:
        fn()
        print(name, "returned")
    except np.linalg.LinAlgError as e:
        print(name, "LinAlgError", e)


case("inv", lambda: np.linalg.inv(S))
case("inv float32", lambda: np.linalg.inv(S.astype(np.float32)))
case("inv complex128", lambda: np.linalg.inv(S.astype(np.complex128)))
case("inv stacked", lambda: np.linalg.inv(np.stack([np.eye(2), S])))
case("solve", lambda: np.linalg.solve(S, np.array([1.0, 1.0])))
case("solve matrix", lambda: np.linalg.solve(S, np.eye(2)))
case("tensorinv", lambda: np.linalg.tensorinv(S, ind=1))
case("tensorsolve", lambda: np.linalg.tensorsolve(S, np.array([1.0, 1.0])))
case("matrix_power -1", lambda: np.linalg.matrix_power(S, -1))
case("cholesky", lambda: np.linalg.cholesky(N))
case("cholesky upper", lambda: np.linalg.cholesky(N, upper=True))
with np.errstate(all="ignore"):
    case("inv under errstate ignore", lambda: np.linalg.inv(S))
print("det", np.linalg.det(S))
print("slogdet", *np.linalg.slogdet(S))
print("inv regular", np.linalg.inv(np.array([[2.0, 1.0], [1.0, 1.0]])).tolist())
print("errstate after", np.geterr())
