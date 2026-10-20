import numpy as np
import scipy
from numpy.linalg import lapack_lite

nd = np.show_config(mode="dicts")["Build Dependencies"]
sd = scipy.show_config(mode="dicts")["Build Dependencies"]
keys = ("name", "found", "version", "detection method", "openblas configuration")
for k in ("blas", "lapack"):
    print(k, *(nd[k].get(x) for x in keys))
both = (*keys, "include directory", "lib directory")
print("same as scipy", all(nd[k].get(x) == sd[k].get(x) for k in ("blas", "lapack") for x in both))
print("ilp64", lapack_lite._ilp64)
