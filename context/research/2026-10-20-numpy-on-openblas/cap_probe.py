# Under a memory cap: imports numpy and scipy, then one level-3 call on OpenBLAS (scipy's dgemm,
# which numpy's matmul becomes under spec 100), then numpy's own matmul and a large numpy
# allocation. Each step prints before it runs, flushed, so the output shows where the run ended.
import sys

import numpy as np
from scipy.linalg import blas

a = np.ones((64, 64))
print("imported", flush=True)
try:
    np.empty(64 << 20, dtype=np.uint8)
    print("numpy 64 MiB array allocated", flush=True)
except MemoryError:
    print("numpy 64 MiB array MemoryError", flush=True)
print("numpy matmul", float((a @ a)[0, 0]), flush=True)
print("calling OpenBLAS dgemm", flush=True)
r = blas.dgemm(1.0, a, a)
print("OpenBLAS dgemm returned", float(r[0, 0]), flush=True)
sys.stdout.flush()
