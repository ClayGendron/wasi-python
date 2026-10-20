# Criterion 6's memory-cap probe on the built set (spec 100, Decision 13): cap_probe.py with
# numpy's own a @ a, which now runs on OpenBLAS, in place of scipy's dgemm. The imports are the
# same, so the memory before the call is the same.
import numpy as np
from scipy.linalg import blas  # noqa: F401  (imported as cap_probe.py imports it)

a = np.ones((64, 64))
print("imported", flush=True)
try:
    np.empty(64 << 20, dtype=np.uint8)
    print("numpy 64 MiB array allocated", flush=True)
except MemoryError:
    print("numpy 64 MiB array MemoryError", flush=True)
print("calling numpy matmul", flush=True)
r = a @ a
print("numpy matmul returned", float(r[0, 0]), flush=True)
