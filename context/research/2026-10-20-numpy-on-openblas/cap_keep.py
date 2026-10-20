# The README's advice under a tight cap. With FIRST=1, one small level-3 call while memory is free
# maps OpenBLAS's 16 MiB buffer; then memory is filled until MemoryError and 4 MiB handed back (room
# for Python, not for the buffer); then a level-3 call. With FIRST=0 the same without the first call.
import os

import numpy as np
from scipy.linalg import blas

if os.environ.get("FIRST") == "1":
    a = np.ones((4, 4))
    print("first dgemm", float(blas.dgemm(1.0, a, a)[0, 0]), flush=True)
keep = []
try:
    while True:
        keep.append(bytearray(1 << 20))
except MemoryError:
    pass
del keep[-4:]
print("filled", len(keep), "MiB, 4 MiB handed back", flush=True)
b = np.ones((64, 64))
print("dgemm", float(blas.dgemm(1.0, b, b)[0, 0]), flush=True)
