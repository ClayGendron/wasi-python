"""Spec 099's drafting probe: a package that relies on numpy's LinAlgError (matplotlib's own
test_mlab case, spec 066's survey) and a scipy.special call that reads numpy's status."""

import numpy as np
from matplotlib import mlab

x1 = np.array([[1, 2, 3], [1, 2, 3], [1, 2, 3]])
try:
    mlab.GaussianKDE(x1, "silverman")
    print("mlab.GaussianKDE(rank-1 data): returned")
except np.linalg.LinAlgError as e:
    print(f"mlab.GaussianKDE(rank-1 data): raises LinAlgError: {e}")
