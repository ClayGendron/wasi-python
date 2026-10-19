"""v1.3: scipy, built in (spec 037): native scipy's answers in the guest, and what must reach Python
when scipy meets the sandbox's edges.

The three golden jobs run through the judge's driver. Every behaviour check runs through the
runner as an embedder calls it with no root and no grant, so nothing is writable (§4.15), on both
binaries. Three of them fail today, each a `[[gap]]` closed by spec 038 (Decision 9): Matrix
Market's thread pool, Sobol's temporary file, and the `ctypes` values four functions make.
"""

from __future__ import annotations

import json

import pytest

from harness import jobs, needs, scan

pytestmark = pytest.mark.goal("v1.3")

BINARY = pytest.mark.parametrize("which", ["plain", "snapshot"])
FUEL = 60 * 10**9  # a scipy import and one small computation, with room; a hang ends here


def _run(which: str, code: str, metric):
    """One program, as an embedder runs it with nothing writable; its fuel is the check's metric."""
    needs.need("runner", "artifact dir")
    import wasi_python

    done = wasi_python.run(["-c", code], snapshot=which == "snapshot", fuel=FUEL, deadline_s=None)
    if done.fuel_used is not None:
        metric("fuel", done.fuel_used)
    return done


def _describe(done) -> str:
    tail = done.stderr.decode(errors="replace").strip().splitlines()[-1:] or [""]
    return f"exit {done.exit_code}, trapped {done.trapped!r}: {tail[0]}"


def _json(done) -> dict:
    assert (done.exit_code, done.trapped) == (0, None), _describe(done)
    return json.loads(done.stdout.decode().strip().splitlines()[-1])


def _golden(guest, which: str, job: str) -> None:
    files = {f"/jobs/{job}.py": jobs.script(job).read_bytes(), "/out/.keep": b""}
    files.update({f"/data/{n}": src.read_bytes() for n, src in jobs.DATA.items()})
    r = guest(which, [f"/jobs/{job}.py", "/data", "/out"], files=files)
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
def test_a_singular_solve_raises_linalgerror(which, metric) -> None:
    """LAPACK's info code reaches Python as `LinAlgError`."""
    assert _json(_run(which, SINGULAR, metric)) == {"singular": "LinAlgError"}


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
def test_a_flat_convex_hull_raises_qhullerror(which, metric) -> None:
    """qhull's `longjmp` and scipy's message stream (wasi-libc's `open_memstream`, no temporary
    file) reach Python as `QhullError` with qhull's own message code, with nothing writable."""
    assert _json(_run(which, COLLINEAR, metric)) == {"collinear": ["QhullError", True]}


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
def test_a_python_callbacks_exception_comes_back_through_c(which, metric) -> None:
    """A `ValueError` raised in a Python function that `_zeros` and QUADPACK call back is
    re-raised to the caller (their `setjmp` paths, compiled with wasm's exception handling)."""
    want = {"brentq": "from the callback", "quad": "from the callback"}
    assert _json(_run(which, CALLBACK_RAISES, metric)) == want


INFEASIBLE = """
import json
from scipy.optimize import linprog
r = linprog([1.0, 1.0], A_ub=[[1.0, 1.0], [-1.0, -1.0]], b_ub=[1.0, -2.0], method="highs")
print(json.dumps({"status": r.status}))
"""


@BINARY
def test_highs_reports_an_infeasible_problem(which, metric) -> None:
    """HiGHS, asked for one thread and starting none, reports infeasibility (status 2)."""
    assert _json(_run(which, INFEASIBLE, metric)) == {"status": 2}


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
def test_workers_run_serially_or_raise_as_documented(which, metric) -> None:
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
    assert _json(_run(which, WORKERS, metric)) == want


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
def test_scipy_odr_is_left_out_by_name(which, metric) -> None:
    """`scipy.odr` needs ODRPACK, which is Fortran: importing it raises an `ImportError` that
    says so (decision 28)."""
    got = _json(_run(which, ODR, metric))["odr"]
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
def test_matrix_market_round_trips_in_memory(which, metric) -> None:
    """`mmwrite` then `mmread` of a sparse and a dense matrix through `io.BytesIO`, with
    nothing writable, give back the same matrix. A gap until spec 038: fast_matrix_market's
    default parallelism starts a thread pool, and starting a thread throws on WASI."""
    want = {"sparse": True, "dense": True}
    _compare(_run(which, MATRIX_MARKET, metric), want, "Matrix Market in memory")


SOBOL = """
import json
from scipy.stats import qmc
pts = qmc.Sobol(d=2, scramble=False).random(4)
print(json.dumps({"points": pts.tolist()}))
"""


@BINARY
def test_sobol_needs_nothing_writable(which, metric) -> None:
    """The first four points of the unscrambled two-dimensional Sobol sequence, with nothing
    writable. A gap until spec 038: `_sobol.pyx` loads its direction numbers through
    `importlib.resources.as_file`, which copies the zip member to a temporary file; with no
    temporary folder that raises inside a `noexcept` Cython function, which prints "Exception
    ignored" and leaves the direction numbers zero, so every point is 0 (the build's finding; the
    README warns of it)."""
    want = {"points": [[0.0, 0.0], [0.5, 0.5], [0.75, 0.25], [0.25, 0.75]]}
    _compare(_run(which, SOBOL, metric), want, "Sobol with nothing writable")


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
def test_ctypes_values_scipy_makes(which, metric) -> None:
    """Three distributions pass their parameters to C as a `ctypes.c_void_p`, and `loadarff`
    computes `ctypes.c_ulong(-1).value`; each returns a finite number or its records. A gap until
    spec 038: the `ctypes` stand-in raises `OSError` for any instance of a C type."""
    want = {
        "geninvgauss": True,
        "genhyperbolic": True,
        "studentized_range": True,
        "loadarff": [[1.0, 2.0], [3.0, 4.0]],
    }
    _compare(_run(which, CTYPES_VALUES, metric), want, "ctypes values")
