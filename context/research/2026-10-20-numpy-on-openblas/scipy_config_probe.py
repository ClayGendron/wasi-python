# How scipy's __config__ (made host-neutral by step 70) names OpenBLAS in the guest today.
import scipy

deps = scipy.show_config(mode="dicts")["Build Dependencies"]
for key in ("blas", "lapack"):
    print(key, deps[key])
