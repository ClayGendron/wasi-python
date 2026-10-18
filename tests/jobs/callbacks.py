"""Golden job: numpy's C callbacks that CPython calls through a pointer of a fixed type. Each one
here was defined with fewer parameters than CPython passes, which native code tolerates and
WebAssembly traps on (spec 051, Decision 5). The last three are private: they are the callback
scan's findings, proved fixed in the guest.
Usage: callbacks.py <data dir> <out dir> (both unused)."""

import copy
import pickle
import sys
import warnings

import numpy as np
import pandas


def step(label, run):
    try:
        print(label, *run())
    except Exception as e:
        print(label, type(e).__name__, e)


print(
    f"versions python={sys.version_info[0]}.{sys.version_info[1]} numpy={np.__version__}"
    f" pandas={pandas.__version__}"
)
for value in (
    np.float64(1.5),
    np.int32(3),
    np.bool_(True),
    np.str_("a"),
    np.datetime64("2017-08-25"),
    np.void(b"a"),
):
    step("copy", lambda v=value: (repr(copy.copy(v)), type(copy.copy(v)).__name__))


def dtype_set():
    a = np.zeros(4, np.int32)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        a.dtype = np.float32
    return a, [x.category.__name__ for x in w]


step("dtype", dtype_set)
m = np._core._multiarray_umath


def sfloat():
    SF = m._get_sfloat_dtype()
    np._ScaledFloatTestDType = SF  # pickle finds the type by its repr, as numpy's own test does
    d = pickle.loads(pickle.dumps(SF(2.0)))
    return type(d).__name__, d.get_scaling()


def castingimpl():
    c = m._get_castingimpl(np.dtypes.Float64DType, np.dtypes.Int64DType)
    return type(c).__name__, c._supports_unaligned


step("sfloat", sfloat)
step("castingimpl", castingimpl)
step("scalar_input", lambda: (m._array_converter(1, [2]).scalar_input,))
