"""v1.3: matplotlib, the first milestone (spec 023): a line plot saved as a PNG in a granted folder
is native matplotlib's image, pixel for pixel; its errors reach Python as native's do; and what M1
leaves out fails in the named way until M2."""

from __future__ import annotations

import hashlib
import re

import pytest

from harness import jobs, needs, png, scan

pytestmark = pytest.mark.goal("v1.3")

BINARY = pytest.mark.parametrize("which", ["plain", "snapshot"])
# The guest's PNG file, pinned (spec 023, Decision 8): the same bytes on both binaries and every
# host. Native's differ (its Pillow deflates with zlib-ng), so only the guest's are pinned.
PNG_SHA256 = "b8759b7ba05818b6bc3eb95b85387cc592691571ed92e6bf5d9c0e596b68d9a3"
MPL_ENV = {"MPLCONFIGDIR": "/mplconfig"}  # a writable cache folder in the judge's root


def _plot(guest, which: str, code: str, **kw):
    return guest(which, ["-c", code], env=MPL_ENV, mpl_data=True, **kw)


@pytest.mark.slow
@BINARY
def test_plot_line_job_matches_native(guest, which) -> None:
    """The milestone: matplotlib on Agg draws the fixed plot, and its RGBA buffer equals the
    oracle's (full SHA-256 and shape, recorded on the platform tests/jobs/plot_line.platform
    names); the PNG saved in a granted folder decodes, with the stdlib, to those same pixels; and
    the PNG's own bytes are the pinned ones."""
    job = "plot_line"
    files = {f"/jobs/{job}.py": jobs.script(job).read_bytes(), "/out/.keep": b"", "/png/.keep": b""}
    files.update({f"/data/{n}": src.read_bytes() for n, src in jobs.DATA.items()})
    argv = [f"/jobs/{job}.py", "/data", "/out", "/png/plot.png"]
    r = guest(which, argv, files=files, env=MPL_ENV, mpl_data=True)
    assert r.exit_code == 0, f"{job}: {r.describe()}"
    (r.root / "out" / ".keep").unlink()
    expected = jobs.expected_path(job).read_bytes()
    why = jobs.compare(expected, jobs.render(r.stdout, r.root / "out"))
    assert why is None, why
    m = re.search(rb"^rgba (\d+)x(\d+)x(\d+) ([0-9a-f]{64})$", expected, re.M)
    assert m, "plot_line.expected has no rgba line"
    data = (r.root / "png" / "plot.png").read_bytes()
    image = png.decode(data)
    assert image.shape == tuple(int(n) for n in m.groups()[:3]), image.shape
    assert hashlib.sha256(image.pixels).hexdigest() == m[4].decode(), "PNG pixels differ"
    assert hashlib.sha256(data).hexdigest() == PNG_SHA256, hashlib.sha256(data).hexdigest()


DPI = """
import matplotlib
matplotlib.use("agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.plot([1, 2, 3])
try:
    fig.savefig("/out/bad.png", dpi=-1)
except Exception as e:
    print(type(e).__name__, e)
import os
print(os.listdir("/out"))
"""


@pytest.mark.slow
def test_savefig_rejects_a_negative_dpi(guest) -> None:
    """A C++ exception inside matplotlib's Agg backend reaches Python as native's ValueError, and
    no file is left behind."""
    r = _plot(guest, "snapshot", DPI, files={"/out/.keep": b""})
    assert r.exit_code == 0, r.describe()
    assert r.text == "ValueError dpi must be positive\n['.keep']\n", r.text


KIWI = """
import kiwisolver
x = kiwisolver.Variable("x")
s = kiwisolver.Solver()
s.addConstraint(x >= 10)
try:
    s.addConstraint(x <= 5)
except kiwisolver.UnsatisfiableConstraint as e:
    print("UnsatisfiableConstraint", type(e).__module__)
print(kiwisolver.__version__, x.value())
"""


@BINARY
def test_kiwisolver_raises_unsatisfiable_constraint(guest, which) -> None:
    """Contradictory required constraints raise kiwisolver's own exception, thrown in C++ and
    caught in Python, and the solver still holds the first constraint."""
    r = guest(which, ["-c", KIWI])
    assert r.exit_code == 0, r.describe()
    assert r.text == "UnsatisfiableConstraint kiwisolver.exceptions\n1.5.1 0.0\n", r.text


TRIANGULATION = """
import matplotlib.tri as mtri
try:
    t = mtri.Triangulation([0.0, 1.0, 0.0, 1.0], [0.0, 0.0, 1.0, 1.0])
    print(t.triangles.shape)
except Exception as e:
    print(f"Triangulation(x, y) raises {type(e).__name__}: {e}")
"""


@pytest.mark.slow
def test_delaunay_triangulation_runs(guest) -> None:
    """A Delaunay triangulation of four points gives two triangles. M1 leaves matplotlib's
    `_qhull` out of the link (it needs a writable /dev/null, a second carried patch), so this is a
    known gap that M2 closes; triangles given explicitly work through `_tri`."""
    r = _plot(guest, "snapshot", TRIANGULATION)
    assert r.exit_code == 0, r.describe()
    found = [] if r.text == "(2, 3)\n" else [r.text.strip()]
    assert not found, scan.report(found)


CONTOUR = """
import numpy as np
from matplotlib.figure import Figure
fig = Figure()
ax = fig.add_subplot()
z = np.add.outer(np.arange(5.0), np.arange(5.0))
try:
    print(type(ax.contour(z, levels=[2.0, 4.0])).__name__)
except Exception as e:
    print(f"contour raises {type(e).__name__}: {e}")
"""


@pytest.mark.slow
def test_contour_runs(guest) -> None:
    """`contour` draws a QuadContourSet. contourpy is M2's (its own build), so this is a known gap
    that M2 closes."""
    r = _plot(guest, "snapshot", CONTOUR)
    assert r.exit_code == 0, r.describe()
    found = [] if r.text == "QuadContourSet\n" else [r.text.strip()]
    assert not found, scan.report(found)


@pytest.mark.slow
@BINARY
def test_patched_callbacks_run(guest, which) -> None:
    """kiwisolver's 21 and Pillow's two callbacks that spec 051's scan found, each defined with
    fewer parameters than CPython calls it with, now run and print native's output; each trapped
    the guest before its carried patch (spec 023)."""
    job = "plot_callbacks"
    files = {f"/jobs/{job}.py": jobs.script(job).read_bytes(), "/out/.keep": b""}
    files.update({f"/data/{n}": src.read_bytes() for n, src in jobs.DATA.items()})
    r = guest(which, [f"/jobs/{job}.py", "/data", "/out"], files=files)
    assert r.exit_code == 0, f"{job}: {r.describe()}"
    (r.root / "out" / ".keep").unlink()
    why = jobs.compare(jobs.expected_path(job).read_bytes(), jobs.render(r.stdout, r.root / "out"))
    assert why is None, why


THROUGH_THE_RUNNER = """
import os, matplotlib
data = matplotlib.get_data_path()
print(data)
print(len([f for f in os.listdir(os.path.join(data, "fonts", "ttf")) if f.endswith(".ttf")]))
print(matplotlib.rcParams["backend"], matplotlib.matplotlib_fname())
"""


def test_matplotlib_finds_its_data_through_the_runner() -> None:
    """Through `wasi_python.run` itself, not the judge's driver (the build review, F7): matplotlib
    finds its data where the runner extracted and granted it, the 40 bundled fonts and the
    `matplotlibrc` that sets the Agg backend (spec 023, Decision 5)."""
    needs.need("runner", "artifact dir")
    import wasi_python

    done = wasi_python.run(["-c", THROUGH_THE_RUNNER], root=True)
    assert done.exit_code == 0, done
    data = "/usr/local/lib/python315.zip/matplotlib/mpl-data"
    assert done.stdout.decode() == f"{data}\n40\nAgg {data}/matplotlibrc\n", done.stdout
