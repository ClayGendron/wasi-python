import warnings

import numpy as np


def case(name, fn):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            fn()
            got = "returned"
        except FloatingPointError as e:
            got = f"FloatingPointError {e}"
    said = [f"{x.category.__name__} {x.message}" for x in w]
    print(name, got, *(["warns", *said] if said else ["silent"]))


one = np.array([1.0])
case("float divide by 0", lambda: one / 0.0)
case("float floor_divide by 0", lambda: one // 0.0)
case("log 0", lambda: np.log(np.array([0.0])))
case("sqrt -1", lambda: np.sqrt(np.array([-1.0])))
case("exp 1000", lambda: np.exp(np.array([1000.0])))
case("nan to int64", lambda: np.array([np.nan]).astype(np.int64))
case("float scalar divide by 0", lambda: np.float64(1.0) / np.float64(0.0))
with np.errstate(all="raise"):
    case("float divide by 0 under raise", lambda: one / 0.0)
