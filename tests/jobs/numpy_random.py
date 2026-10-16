"""Golden job: numpy.random, both APIs, seeded. The spike's `Generator.poisson` trapped on a
symbol clash that only a static link creates; this job pins that down against native.
Usage: numpy_random.py <data dir> <out dir> (both unused). Integer draws name int64, because the
platform's default integer is 32-bit (a documented difference, checked on its own)."""

import sys

import dateutil
import numpy as np
import pandas
import six
import tzdata


def fl(xs):
    return [format(round(float(x), 9) + 0.0, ".9g") for x in xs]


print(
    f"versions python={sys.version_info[0]}.{sys.version_info[1]} numpy={np.__version__}"
    f" pandas={pandas.__version__} python-dateutil={dateutil.__version__}"
    f" tzdata={tzdata.__version__} six={six.__version__}"
)
g = np.random.Generator(np.random.PCG64(12345))
print("g.random", fl(g.random(4)))
print("g.normal", fl(g.normal(size=4)))
print("g.integers", g.integers(0, 1000, 5, dtype=np.int64).tolist())
print("g.poisson", g.poisson(3.0, 5).tolist())
print("g.choice", g.choice(10, 4, replace=False).tolist())
print("g.multinomial", g.multinomial(20, [0.2, 0.3, 0.5]).tolist())
np.random.seed(12345)
print("l.rand", fl(np.random.rand(4)))
print("l.normal", fl(np.random.normal(size=4)))
print("l.binomial", [int(x) for x in np.random.binomial(10, 0.5, 5)])
print("l.randint", np.random.randint(0, 1000, 5, dtype=np.int64).tolist())
print("l.poisson", [int(x) for x in np.random.poisson(2.0, 5)])
print("l.multinomial", [int(x) for x in np.random.multinomial(20, [0.2, 0.3, 0.5])])
