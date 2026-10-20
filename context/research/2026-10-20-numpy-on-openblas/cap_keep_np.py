# cap_keep.py with numpy's matmul in place of scipy's dgemm (spec 100, criterion 6). With FIRST=1,
# one small matmul while memory is free maps OpenBLAS's buffer; then memory is filled until
# MemoryError and 4 MiB handed back; then a matmul. With FIRST=0 the same without the first call.
import os

import numpy as np

if os.environ.get("FIRST") == "1":
    a = np.ones((4, 4))
    print("first matmul", float((a @ a)[0, 0]), flush=True)
keep = []
try:
    while True:
        keep.append(bytearray(1 << 20))
except MemoryError:
    pass
del keep[-4:]
print("filled", len(keep), "MiB, 4 MiB handed back", flush=True)
b = np.ones((64, 64))
print("matmul", float((b @ b)[0, 0]), flush=True)
