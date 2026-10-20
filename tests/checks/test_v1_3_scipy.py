"""v1.3: scipy, built in (spec 037): native scipy's answers in the guest, and what must reach Python
when scipy meets the sandbox's edges.

The golden jobs run through the judge's driver. Every behaviour check runs as an embedder calls
the runner with no root and no grant, so nothing is writable (§4.15), on both binaries. Three of
them were `[[gap]]`s until spec 038 closed them (037's Decision 9; 038's Decisions 1 to 4): Matrix
Market's thread pool, Sobol's temporary file, and the `ctypes` values four functions make. Spec
038 adds the edges golden, run with nothing writable, and the address check.
"""

from __future__ import annotations

import json

import pytest

from harness import jobs, scan

pytestmark = pytest.mark.goal("v1.3")

BINARY = pytest.mark.parametrize("which", ["plain", "snapshot"])
FUEL = 60 * 10**9  # a scipy import and one small computation, with room; a hang ends here


def _run(guest, which: str, code: str):
    """One program, as an embedder runs it with nothing writable (the root `/` read-only), through
    the judge's own driver, whose seeded random and stepped clock make its fuel repeat (spec 080;
    037's build review, F1). The fuel is the check's metric."""
    return guest(which, ["-c", code], fuel=FUEL, root_writable=False)


def _describe(done) -> str:
    tail = done.stderr.decode(errors="replace").strip().splitlines()[-1:] or [""]
    return f"exit {done.exit_code}, trapped {done.trapped!r}: {tail[0]}"


def _json(done) -> dict:
    assert (done.exit_code, done.trapped) == (0, None), _describe(done)
    return json.loads(done.stdout.decode().strip().splitlines()[-1])


def _golden(guest, which: str, job: str, *, root_writable: bool = True) -> None:
    files = {f"/jobs/{job}.py": jobs.script(job).read_bytes(), "/out/.keep": b""}
    files.update({f"/data/{n}": src.read_bytes() for n, src in jobs.DATA.items()})
    r = guest(which, [f"/jobs/{job}.py", "/data", "/out"], files=files, root_writable=root_writable)
    assert r.exit_code == 0, f"{job}: {r.describe()}"
    (r.root / "out" / ".keep").unlink()
    why = jobs.compare(jobs.expected_path(job).read_bytes(), jobs.render(r.stdout, r.root / "out"))
    assert why is None, why


@pytest.mark.slow
@BINARY
def test_scipy_numeric_job_matches_native(guest, which) -> None:
    """linalg, sparse (SuperLU, ARPACK, csgraph), fft, special, stats, interpolate (qhull),
    signal, ndimage, spatial and cluster print native scipy's values to 9 significant digits."""
    _golden(guest, which, "scipy_numeric")


@pytest.mark.slow
@BINARY
def test_scipy_solvers_job_matches_native(guest, which) -> None:
    """optimize (BFGS, Nelder-Mead, L-BFGS-B, SLSQP, hybr, least_squares, curve_fit, brentq,
    HiGHS's linprog and milp, linear_sum_assignment) and integrate (QUADPACK, solve_ivp, odeint,
    simpson), each bounded by a tolerance 1,000 times tighter than its 6 printed digits."""
    _golden(guest, which, "scipy_solvers")


@pytest.mark.slow
@BINARY
def test_scipy_lapack_job_matches_native(guest, which) -> None:
    """Every LAPACK routine that trapped before OpenBLAS's carried patches, in four precisions
    through f2py's function pointers, gees with a sort callback, and cython_lapack's callers."""
    _golden(guest, which, "scipy_lapack")


@pytest.mark.slow
@BINARY
def test_scipy_edges_job_matches_native(guest, which) -> None:
    """Matrix Market through `io.BytesIO` (the bytes' SHA-256 and the values read back), Sobol's
    unscrambled and seeded scrambled points, the four functions that make `ctypes` values and
    `loadarff`, as native scipy prints them, with nothing writable (spec 038, Decision 5)."""
    _golden(guest, which, "scipy_edges", root_writable=False)


SINGULAR = """
import json
import numpy as np
from scipy import linalg
try:
    linalg.solve(np.array([[1.0, 2.0], [2.0, 4.0]]), np.array([1.0, 1.0]))
    got = "returned"
except linalg.LinAlgError as e:
    got = type(e).__name__
print(json.dumps({"singular": got}))
"""


@BINARY
def test_a_singular_solve_raises_linalgerror(guest, which) -> None:
    """LAPACK's info code reaches Python as `LinAlgError`."""
    assert _json(_run(guest, which, SINGULAR)) == {"singular": "LinAlgError"}


COLLINEAR = """
import json
import numpy as np
from scipy.spatial import ConvexHull, QhullError
try:
    ConvexHull(np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 2.0], [3.0, 3.0]]))
    got = "returned"
except QhullError as e:
    got = [type(e).__name__, "QH6154" in str(e)]
print(json.dumps({"collinear": got}))
"""


@BINARY
def test_a_flat_convex_hull_raises_qhullerror(guest, which) -> None:
    """qhull's `longjmp` and scipy's message stream (wasi-libc's `open_memstream`, no temporary
    file) reach Python as `QhullError` with qhull's own message code, with nothing writable."""
    assert _json(_run(guest, which, COLLINEAR)) == {"collinear": ["QhullError", True]}


CALLBACK_RAISES = """
import json
from scipy import integrate, optimize
def bad(x):
    raise ValueError("from the callback")
out = {}
for name, call in (("brentq", lambda: optimize.brentq(bad, 0.0, 1.0)),
                   ("quad", lambda: integrate.quad(bad, 0.0, 1.0))):
    try:
        call()
        out[name] = "returned"
    except ValueError as e:
        out[name] = str(e)
print(json.dumps(out))
"""


@BINARY
def test_a_python_callbacks_exception_comes_back_through_c(guest, which) -> None:
    """A `ValueError` raised in a Python function that `_zeros` and QUADPACK call back is
    re-raised to the caller (their `setjmp` paths, compiled with wasm's exception handling)."""
    want = {"brentq": "from the callback", "quad": "from the callback"}
    assert _json(_run(guest, which, CALLBACK_RAISES)) == want


INFEASIBLE = """
import json
from scipy.optimize import linprog
r = linprog([1.0, 1.0], A_ub=[[1.0, 1.0], [-1.0, -1.0]], b_ub=[1.0, -2.0], method="highs")
print(json.dumps({"status": r.status}))
"""


@BINARY
def test_highs_reports_an_infeasible_problem(guest, which) -> None:
    """HiGHS, asked for one thread and starting none, reports infeasibility (status 2)."""
    assert _json(_run(guest, which, INFEASIBLE)) == {"status": 2}


WORKERS = """
import json
import numpy as np
from scipy import fft, optimize, spatial
out = {}
x = np.arange(64.0) % 7
out["fft"] = bool(np.array_equal(fft.fft(x, workers=4), fft.fft(x, workers=1)))
def raised(call):
    try:
        call()
        return "returned"
    except Exception as e:
        return type(e).__name__
out["differential_evolution"] = raised(
    lambda: optimize.differential_evolution(optimize.rosen, [(-1, 1)] * 2,
                                            workers=2, maxiter=2, seed=1, updating="deferred"))
tree = spatial.cKDTree(np.arange(30.0).reshape(10, 3))
out["cKDTree.query"] = raised(lambda: tree.query(np.zeros((4, 3)), workers=2))
print(json.dumps(out))
"""


@BINARY
def test_workers_run_serially_or_raise_as_documented(guest, which) -> None:
    """`scipy.fft`'s `workers` runs serially and gives the same answer (ducc0's threads are
    compiled out); `differential_evolution(workers=2)` builds a process pool and
    `cKDTree.query(workers=2)` starts threads, and each raises at once, as the README says,
    within the fuel cap (Decision 9): the pool's queue needs `os.pipe`, which WASI lacks
    (AttributeError), and a thread cannot start (RuntimeError, "can't start new thread"), both
    recorded by the build."""
    want = {
        "fft": True,
        "differential_evolution": "AttributeError",
        "cKDTree.query": "RuntimeError",
    }
    assert _json(_run(guest, which, WORKERS)) == want


ODR = """
import json
try:
    import scipy.odr
    got = "imported"
except ImportError as e:
    got = str(e)
print(json.dumps({"odr": got}))
"""


@BINARY
def test_scipy_odr_is_left_out_by_name(guest, which) -> None:
    """`scipy.odr` needs ODRPACK, which is Fortran: importing it raises an `ImportError` that
    says so (decision 28)."""
    got = _json(_run(guest, which, ODR))["odr"]
    assert "Fortran" in got and "scipy.odr" in got, got


def test_the_version_names_scipy_odr_among_the_missing(guest) -> None:
    """`-V` names `scipy.odr` among what this build lacks (Decision 9)."""
    r = guest("plain", ["-V"], record=False)
    assert r.exit_code == 0, r.describe()
    assert "scipy.odr" in r.text, r.text


def _compare(done, want: dict, what: str) -> None:
    """Each item the program printed against its wanted value, reported as findings with their
    digest, so a gap names exactly the items that fail."""
    if (done.exit_code, done.trapped) != (0, None):
        findings = [_describe(done)]
    else:
        got = json.loads(done.stdout.decode().strip().splitlines()[-1])
        findings = [f"{k}: {got.get(k)!r}" for k, v in want.items() if got.get(k) != v]
    assert not findings, scan.report(findings, what)


MATRIX_MARKET = """
import io, json
import numpy as np
from scipy import io as sio, sparse
out = {}
for name, m in (("sparse", sparse.coo_array(np.array([[1.0, 0.0], [0.0, 2.5]]))),
                ("dense", np.array([[1.0, 2.0], [3.0, 4.5]]))):
    try:
        buf = io.BytesIO()
        sio.mmwrite(buf, m)
        back = sio.mmread(io.BytesIO(buf.getvalue()))
        back = back.toarray() if hasattr(back, "toarray") else back
        want = m.toarray() if hasattr(m, "toarray") else m
        out[name] = bool(np.array_equal(back, want))
    except Exception as e:
        out[name] = f"RAISES {type(e).__name__}: {e}"
print(json.dumps(out))
"""


@BINARY
def test_matrix_market_round_trips_in_memory(guest, which) -> None:
    """`mmwrite` then `mmread` of a sparse and a dense matrix through `io.BytesIO`, with
    nothing writable, give back the same matrix. A gap until spec 038, whose carried patch makes
    the default parallelism 1 on WASI: fast_matrix_market's default started a thread pool, and
    starting a thread throws on WASI."""
    want = {"sparse": True, "dense": True}
    _compare(_run(guest, which, MATRIX_MARKET), want, "Matrix Market in memory")


SOBOL = """
import json
from scipy.stats import qmc
pts = qmc.Sobol(d=2, scramble=False).random(4)
print(json.dumps({"points": pts.tolist()}))
"""


@BINARY
def test_sobol_needs_nothing_writable(guest, which) -> None:
    """The first four points of the unscrambled two-dimensional Sobol sequence, with nothing
    writable. A gap until spec 038, whose carried patch reads the direction numbers' bytes
    without a file: `_sobol.pyx` loaded them through `importlib.resources.as_file`, which copies
    the zip member to a temporary file; with no temporary folder that raised inside a `noexcept`
    Cython function, which printed "Exception ignored" and left the direction numbers zero, so
    every point was 0 (spec 037's build's finding)."""
    want = {"points": [[0.0, 0.0], [0.5, 0.5], [0.75, 0.25], [0.25, 0.75]]}
    _compare(_run(guest, which, SOBOL), want, "Sobol with nothing writable")


CTYPES_VALUES = """
import io, json, math
from scipy import stats
from scipy.io import arff
text = "@relation r\\n@attribute a numeric\\n@attribute b numeric\\n@data\\n1,2\\n3,4\\n"
calls = {
    "geninvgauss": lambda: math.isfinite(stats.geninvgauss.cdf(1.0, 2.0, 1.5)),
    "genhyperbolic": lambda: math.isfinite(stats.genhyperbolic.cdf(0.5, 1.0, 1.5, 0.5)),
    "studentized_range": lambda: math.isfinite(stats.studentized_range.cdf(3.0, 3, 10)),
    "loadarff": lambda: [list(r) for r in arff.loadarff(io.StringIO(text))[0].tolist()],
}
out = {}
for name, call in calls.items():
    try:
        out[name] = call()
    except Exception as e:
        out[name] = f"RAISES {type(e).__name__}: {e}"
print(json.dumps(out))
"""


@BINARY
def test_ctypes_values_scipy_makes(guest, which) -> None:
    """Three distributions pass their parameters to C as a `ctypes.c_void_p`, and `loadarff`
    computes `ctypes.c_ulong(-1).value`; each returns a finite number or its records. A gap until
    spec 038, whose stand-in holds numeric and `c_void_p` values: the stand-in raised `OSError` for
    any instance of a C type."""
    want = {
        "geninvgauss": True,
        "genhyperbolic": True,
        "studentized_range": True,
        "loadarff": [[1.0, 2.0], [3.0, 4.0]],
    }
    _compare(_run(guest, which, CTYPES_VALUES), want, "ctypes values")


ADDRESS = """
import ctypes, json
import numpy as np
a = np.arange(5.0)
p = a.ctypes.data_as(ctypes.c_void_p)
address = a.__array_interface__["data"][0]
print(json.dumps({"equal": p.value == address, "data": a.ctypes.data == address,
                  "kept": p._arr is a, "fits": 0 < p.value < 2**32}))
"""


@BINARY
def test_ndarray_ctypes_gives_the_arrays_address(guest, which) -> None:
    """numpy's `ndarray.ctypes.data_as(ctypes.c_void_p).value` and `.ctypes.data` are the array's
    `__array_interface__` address, a 32-bit one, and the pointer keeps the array alive, with the
    real numpy in the guest (spec 038, Decision 5: a guest check, since a 64-bit host's address
    does not fit the stand-in's 32 bits and numpy is not a development dependency)."""
    want = {"equal": True, "data": True, "kept": True, "fits": True}
    _compare(_run(guest, which, ADDRESS), want, "ndarray.ctypes's address")


SOBOL_OPTIONS = """
import json
from scipy import optimize
def sphere(x):
    return float((x**2).sum())
out = {}
for name, call in (
    ("differential_evolution", lambda: optimize.differential_evolution(
        sphere, [(-1, 1)] * 2, init="sobol", rng=1, maxiter=1000, popsize=16)),
    ("shgo", lambda: optimize.shgo(sphere, [(-1, 1)] * 2, sampling_method="sobol", n=32)),
):
    try:
        r = call()
        out[name] = [bool(r.success), bool(float(r.fun) < 1e-8)]
    except Exception as e:
        out[name] = f"RAISES {type(e).__name__}: {e}"
print(json.dumps(out))
"""


@BINARY
def test_the_sobol_options_need_nothing_writable(guest, which) -> None:
    """`differential_evolution(init='sobol')` and `shgo(sampling_method='sobol')` find the
    minimum of a two-dimensional sphere with nothing writable (spec 038; its build review's Low 7:
    the README says they work). Before 038, the first started from Sobol's zero population and the
    second raised QhullError (QH6421)."""
    want = {"differential_evolution": [True, True], "shgo": [True, True]}
    _compare(_run(guest, which, SOBOL_OPTIONS), want, "Sobol's options with nothing writable")
