"""Golden job: the scipy functions that meet the sandbox's edges (spec 038, Decision 5). Usage:
scipy_edges.py <data dir> <out dir> (both unused). Runs natively (the oracle, scipy-openblas, one
thread) and in the guest with nothing writable; its output must be byte-identical in both.

Matrix Market (a thread pool natively, serial in the guest), Sobol's direction numbers (a
temporary file natively from a zip), and the distributions and the ARFF reader that make
`ctypes` values. Direct results print with 9 significant digits. Results computed by quadrature
(geninvgauss's and genhyperbolic's `cdf`, studentized_range and tukey_hsd) print with 6: scipy
integrates them at its own tolerances (epsabs 1e-11 or tighter, epsrel 1e-10 to 1e-12), each
far tighter than 6 digits, so what prints is bounded by the tolerance, not by the path a step
took. The Matrix Market bytes print with their SHA-256: fast_matrix_market writes its chunks in
order, threaded or not. Every input is fixed here or drawn from a seeded PCG64 generator.
"""

import hashlib
import io
import sys

import numpy as np
import scipy
from scipy import io as sio
from scipy import sparse, stats
from scipy.io import arff
from scipy.stats import qmc


def g(x, k=9):
    return format(float(x) + 0.0, f".{k}g")


def gs(values, k=9):
    return " ".join(g(v, k) for v in np.ravel(values))


def show(label, fn):
    try:
        out = fn()
    except Exception as e:  # the golden records a failure as text, so a difference names it
        out = f"RAISES {type(e).__name__} {str(e)[:120]}"
    print(label, "->", out)


def round_trip(m):
    buf = io.BytesIO()
    sio.mmwrite(buf, m)
    data = buf.getvalue()
    back = sio.mmread(io.BytesIO(data))
    dense = back.toarray() if sparse.issparse(back) else back
    want = m.toarray() if sparse.issparse(m) else m
    equal = bool(np.array_equal(dense, want))
    text = data.decode().replace("\n", "|")
    return f"sha256={hashlib.sha256(data).hexdigest()} equal={equal} values={gs(dense)} text={text}"


print(f"versions python={sys.version_info[0]}.{sys.version_info[1]} scipy={scipy.__version__}")

# Matrix Market, in memory
show(
    "mmwrite/mmread sparse",
    lambda: round_trip(sparse.coo_array(np.array([[1.0, 0.0, -2.5], [0.0, 3.25, 0.0]]))),
)
show("mmwrite/mmread dense", lambda: round_trip(np.array([[1.0, 2.0], [3.0, 4.5], [-6.0, 0.125]])))
HEADER = b"%%MatrixMarket matrix array real general\n1 1\n2\n"
show("mminfo", lambda: sio.mminfo(io.BytesIO(HEADER)))

# Sobol's direction numbers
show("Sobol unscrambled", lambda: gs(qmc.Sobol(d=3, scramble=False).random(8)))
show(
    "Sobol scrambled",
    lambda: gs(qmc.Sobol(d=3, rng=np.random.Generator(np.random.PCG64(20261020))).random(8)),
)

# ctypes values: c_void_p user data to C, and c_ulong(-1)
show("geninvgauss.cdf", lambda: g(stats.geninvgauss(2.3, 1.5).cdf(1.0), 6))
show("genhyperbolic.cdf", lambda: g(stats.genhyperbolic(0.5, 1.5, -0.5).cdf(0.3), 6))
show("studentized_range.cdf", lambda: g(stats.studentized_range.cdf(3.0, 3, 10), 6))
groups = (
    [24.5, 23.5, 26.4, 27.1, 29.9],
    [28.4, 34.2, 29.5, 32.2, 30.1],
    [26.1, 28.3, 24.3, 26.2, 27.8],
)
show("tukey_hsd pvalue", lambda: gs(stats.tukey_hsd(*groups).pvalue, 6))
ARFF = """@relation edges
@attribute a numeric
@attribute b numeric
@attribute c {red,green}
@data
1,2.5,red
3,-4.25,green
"""


def loaded():
    data, meta = arff.loadarff(io.StringIO(ARFF))
    rows = "; ".join(f"{g(a)} {g(b)} {c.decode()}" for a, b, c in data.tolist())
    return f"{rows} names={','.join(meta.names())}"


show("loadarff", loaded)
