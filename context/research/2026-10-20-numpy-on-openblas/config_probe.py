# What numpy says it was built with (check 1's program, drafted).
import numpy as np
from numpy.linalg import lapack_lite

deps = np.show_config(mode="dicts")["Build Dependencies"]
for key in ("blas", "lapack"):
    d = deps.get(key, {})
    print(key, d.get("name"), d.get("found"), d.get("version"), d.get("openblas configuration"))
print("ilp64", lapack_lite._ilp64)
