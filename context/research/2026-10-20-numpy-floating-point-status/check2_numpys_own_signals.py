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


i64 = np.array([1, 2], dtype=np.int64)
case("int floor_divide by 0", lambda: i64 // 0)
case("int remainder by 0", lambda: i64 % 0)
case("int divmod by 0", lambda: np.divmod(i64, 0))
case("int32 min floor_divide -1", lambda: np.array([-(2**31)], dtype=np.int32) // -1)
case("timedelta floor_divide 0", lambda: np.array([10], dtype="m8[s]") // np.timedelta64(0, "s"))
case("float64 to float16 overflow", lambda: np.array([1e6]).astype(np.float16))
case("int scalar floor_divide 0", lambda: np.int64(1) // np.int64(0))
case("int8 scalar add overflow", lambda: np.int8(127) + np.int8(1))
with np.errstate(divide="raise"):
    case("int floor_divide by 0 under raise", lambda: i64 // 0)
with np.errstate(over="raise"):
    case("float16 overflow under raise", lambda: np.array([1e6]).astype(np.float16))
with np.errstate(divide="ignore"):
    case("int floor_divide by 0 under ignore", lambda: i64 // 0)
