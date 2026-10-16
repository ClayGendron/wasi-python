"""Golden job: read a CSV with numpy's own loader, group by region, write a summary, and touch
linalg and fft. Usage: numpy_csv.py <data dir> <out dir>. Runs natively (the oracle) and in the
guest; its output must be byte-identical in both."""

import os
import sys

import dateutil
import numpy as np
import pandas
import six
import tzdata


def f(x):
    return format(round(float(x), 9) + 0.0, ".9g")


data_dir, out_dir = sys.argv[1], sys.argv[2]
print(
    f"versions python={sys.version_info[0]}.{sys.version_info[1]} numpy={np.__version__}"
    f" pandas={pandas.__version__} python-dateutil={dateutil.__version__}"
    f" tzdata={tzdata.__version__} six={six.__version__}"
)
path = os.path.join(data_dir, "sales.csv")
values = np.loadtxt(path, delimiter=",", skiprows=1, usecols=(1, 2))
regions = np.loadtxt(path, delimiter=",", skiprows=1, usecols=(0,), dtype=str)
names = sorted(set(regions.tolist()))
print("rows", values.shape[0], "regions", names)
rows = []
for r in names:
    s = values[regions == r, 1]
    rows.append((s.sum(), s.mean(), s.max(), np.median(s), s.std()))
    print(r, *(f(x) for x in rows[-1]))
np.savetxt(
    os.path.join(out_dir, "summary.csv"),
    np.array(rows),
    delimiter=",",
    header="sum,mean,max,median,std",
    comments="",
    fmt="%.9g",
)
a = np.array([[4.0, 1.0], [2.0, 3.0]])
print("det", f(np.linalg.det(a)), "inv", [f(x) for x in np.linalg.inv(a).ravel()])
print("fft", [f(abs(x)) for x in np.fft.fft(np.arange(8.0))])
print("cumsum", np.cumsum(np.arange(10, dtype=np.int64)).tolist())
