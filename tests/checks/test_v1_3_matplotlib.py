"""v1.3: matplotlib, the first milestone: a line plot saved as a PNG in a granted folder
is native matplotlib's image, pixel for pixel; its errors reach Python as native's do. The second
milestone: Delaunay triangulations through `_qhull`, contours through contourpy, and
SVG and PDF saves whose bytes are native matplotlib's (the PDF up to its font subset tags)."""

from __future__ import annotations

import hashlib
import re

import pytest

from harness import jobs, needs, png, scan

pytestmark = pytest.mark.goal("v1.3")

BINARY = pytest.mark.parametrize("which", ["plain", "snapshot"])
# The guest's PNG file, pinned: the same bytes on both binaries and every
# host. Native's differ (its Pillow deflates with zlib-ng), so only the guest's are pinned.
PNG_SHA256 = "b8759b7ba05818b6bc3eb95b85387cc592691571ed92e6bf5d9c0e596b68d9a3"
# The guest's PDF file from the plot_contour job, pinned: the same bytes on
# both binaries and every host. Native's differ in their font subset tags (matplotlib derives each
# from hash(), 32 bits wide in the guest), so the golden holds the PDF with its tags normalized.
# The pin moves with the guest's zlib (step 30): the PDF's streams are deflated at level 6, so a
# zlib release needs a judge change, with its reason, and the normalized golden must still hold.
PDF_SHA256 = "9f21cc48b8e37f0052745d7c66c3de245ac36db91f42c93f1e219c554f32b990"
PDF_TAG = re.compile(rb"/[A-Z]{1,6}\+")
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


@pytest.mark.slow
@BINARY
def test_plot_contour_job_matches_native(guest, which) -> None:
    """The second milestone: a Delaunay triangulation, qhull's error, contourpy's three algorithms,
    `contourf`, `contour`, `clabel`, `tricontourf` and `triplot`, and the figure saved to SVG and
    PDF, each printed line equal to the oracle's (recorded on the platform
    tests/jobs/plot_contour.platform names). The SVG and PDF files `savefig` wrote in a granted
    folder are the files the golden describes, the PDF with its subset tags normalized; and the
    PDF's own bytes are the pinned ones."""
    job = "plot_contour"
    files = {
        f"/jobs/{job}.py": jobs.script(job).read_bytes(),
        "/out/.keep": b"",
        "/saves/.keep": b"",
    }
    files.update({f"/data/{n}": src.read_bytes() for n, src in jobs.DATA.items()})
    argv = [f"/jobs/{job}.py", "/data", "/out", "/saves"]
    r = guest(which, argv, files=files, env=MPL_ENV, mpl_data=True)
    assert r.exit_code == 0, f"{job}: {r.describe()}"
    (r.root / "out" / ".keep").unlink()
    expected = jobs.expected_path(job).read_bytes()
    why = jobs.compare(expected, jobs.render(r.stdout, r.root / "out"))
    assert why is None, why
    svg_line = re.search(rb"^svg (\d+) ([0-9a-f]{64})$", expected, re.M)
    pdf_line = re.search(rb"^pdf (\d+) tags (\d+) ([0-9a-f]{64})$", expected, re.M)
    assert svg_line and pdf_line, "plot_contour.expected has no svg or pdf line"
    svg = (r.root / "saves" / "contour.svg").read_bytes()
    assert (len(svg), hashlib.sha256(svg).hexdigest()) == (
        int(svg_line[1]),
        svg_line[2].decode(),
    ), "the SVG file differs from the golden's"
    pdf = (r.root / "saves" / "contour.pdf").read_bytes()
    normalized, tags = PDF_TAG.subn(b"/XXXXXX+", pdf)
    assert (len(normalized), tags, hashlib.sha256(normalized).hexdigest()) == (
        int(pdf_line[1]),
        int(pdf_line[2]),
        pdf_line[3].decode(),
    ), "the PDF file, its tags normalized, differs from the golden's"
    assert hashlib.sha256(pdf).hexdigest() == PDF_SHA256, hashlib.sha256(pdf).hexdigest()


THREADS = """
import numpy as np, contourpy
x = np.linspace(-2.0, 2.0, 201)
X, Y = np.meshgrid(x, x)
Z = np.sin(3.0 * X) * np.cos(2.0 * Y) + 0.1 * X
serial = contourpy.contour_generator(X, Y, Z, name="serial", line_type="Separate", chunk_count=16)
threaded = contourpy.contour_generator(
    X, Y, Z, name="threaded", line_type="Separate", chunk_count=16, thread_count=4
)
a, b = serial.lines(0.3), threaded.lines(0.3)
same = len(a) == len(b) and all(np.array_equal(p, q) for p, q in zip(a, b))
print(contourpy.max_threads(), threaded.thread_count, len(a), sum(map(len, a)), same)
"""


@pytest.mark.slow
def test_contourpy_runs_one_thread(guest) -> None:
    """The guest has no threads: `contourpy.max_threads()` is 1, and the `threaded` algorithm asked
    for four threads runs one, with lines whose points equal `serial`'s at the same chunk count
    (the points depend on the chunk count, so both use 16)."""
    r = guest("snapshot", ["-c", THREADS])
    assert r.exit_code == 0, r.describe()
    fields = r.text.split()
    assert len(fields) == 5, r.text
    max_threads, used, _lines, _points, same = fields
    assert (max_threads, used, same) == ("1", "1", "True"), r.text


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
    """A Delaunay triangulation of four points gives two triangles, through matplotlib's `_qhull`
    with carried patch 0002, which opens no /dev/null on WASI (a known gap of M1's,
    closed by M2)."""
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
    """`contour` draws a QuadContourSet, through contourpy, built in by M2 (a known gap of
    M1's, closed by M2)."""
    r = _plot(guest, "snapshot", CONTOUR)
    assert r.exit_code == 0, r.describe()
    found = [] if r.text == "QuadContourSet\n" else [r.text.strip()]
    assert not found, scan.report(found)


@pytest.mark.slow
@BINARY
def test_patched_callbacks_run(guest, which) -> None:
    """kiwisolver's 21 and Pillow's two callbacks that the callback-signature scan found, each
    defined with fewer parameters than CPython calls it with, now run and print native's output;
    each trapped the guest before its carried patch."""
    job = "plot_callbacks"
    files = {f"/jobs/{job}.py": jobs.script(job).read_bytes(), "/out/.keep": b""}
    files.update({f"/data/{n}": src.read_bytes() for n, src in jobs.DATA.items()})
    r = guest(which, [f"/jobs/{job}.py", "/data", "/out"], files=files)
    assert r.exit_code == 0, f"{job}: {r.describe()}"
    (r.root / "out" / ".keep").unlink()
    why = jobs.compare(jobs.expected_path(job).read_bytes(), jobs.render(r.stdout, r.root / "out"))
    assert why is None, why


# One garbage cycle through all four kiwisolver types. The collector calls
# tp_clear on the collectable objects in their order of allocation (Python/gc.c, delete_garbage):
# the variable, the term, the expression, the constraint, then the list, which holds them all and
# itself, so each type's tp_clear is called through its pointer in turn.
KIWI_CYCLE = """
import gc
import kiwisolver as kiwi
gc.disable()
v = kiwi.Variable("x")
t = v * 2.0
e = t + 1.0
c = e >= 0.0
hold = [v, t, e, c]
hold.append(hold)
v.setContext(hold)
print(type(t).__name__, type(e).__name__, type(c).__name__, flush=True)
del v, t, e, c, hold
print("collected", gc.collect() >= 5)
print("ok")
"""


@BINARY
def test_a_cycle_through_kiwisolver_objects_is_collected(guest, which) -> None:
    """A garbage cycle holding a Variable, a Term, an Expression and a Constraint is collected, as
    natively: kiwisolver's four tp_clear returned `void` where CPython calls `int (*)(PyObject *)`,
    so the collection ended the guest in an indirect-call type mismatch before carried patch
    0002."""
    r = guest(which, ["-c", KIWI_CYCLE])
    assert r.exit_code == 0, r.describe()
    assert r.text == "Term Expression Constraint\ncollected True\nok\n", r.text


THROUGH_THE_RUNNER = """
import os, matplotlib
data = matplotlib.get_data_path()
print(data)
print(len([f for f in os.listdir(os.path.join(data, "fonts", "ttf")) if f.endswith(".ttf")]))
print(matplotlib.rcParams["backend"], matplotlib.matplotlib_fname())
"""


def test_matplotlib_finds_its_data_through_the_runner() -> None:
    """Through `wasi_python.run` itself, not the judge's driver: matplotlib
    finds its data where the runner extracted and granted it, the 40 bundled fonts and the
    `matplotlibrc` that sets the Agg backend."""
    needs.need("runner", "artifact dir")
    import wasi_python

    done = wasi_python.run(["-c", THROUGH_THE_RUNNER], root=True)
    assert done.exit_code == 0, done
    data = "/usr/local/lib/python315.zip/matplotlib/mpl-data"
    assert done.stdout.decode() == f"{data}\n40\nAgg {data}/matplotlibrc\n", done.stdout


@pytest.mark.slow
def test_jpeg_images_job_matches_native(guest) -> None:
    """Pillow writes JPEG through libjpeg-turbo, with the defaults, at quality 95, without chroma
    subsampling, progressive with optimized tables, and as L and CMYK; each file's bytes and the
    pixels it decodes to equal native Pillow's. The golden is the oracle's wheel, whose SIMD code
    gives the same output as its plain C code for the integer DCT, the guest's only code."""
    job = "jpeg_images"
    why = jobs.compare(jobs.expected_path(job).read_bytes(), jobs.run_in_guest(guest, job))
    assert why is None, f"{job}: {why}"


# The byte of the first DHT segment that counts its one-bit codes: the segment's marker (2 bytes),
# its length (2) and its class and table id (1) come before it. 255 one-bit codes are more than a
# table may hold, so libjpeg's error handler runs, and Pillow's longjmps back out of the codec.
DHT_ONE_BIT_COUNT = 5
BROKEN_JPEG = f"""
import importlib.util, io
spec = importlib.util.spec_from_file_location("jpeg_images", "/jobs/jpeg_images.py")
job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)
from PIL import Image, features
good = job.encode(job.image())
bad = bytearray(good)
bad[good.index(b"\\xff\\xc4") + {DHT_ONE_BIT_COUNT}] = 0xFF
errors = {{}}
for _ in range(300):
    try:
        with Image.open(io.BytesIO(bytes(bad))) as im:
            im.load()
        errors["none"] = errors.get("none", 0) + 1
    except OSError as e:
        errors[str(e)] = errors.get(str(e), 0) + 1
print("broken", errors)
print("default decodes to", job.decoded(good))
print("jpg", features.check("jpg"))
import matplotlib
matplotlib.use("agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(4, 3), dpi=50)
ax.plot([1, 3, 2])
buf = io.BytesIO()
fig.savefig(buf, format="jpg")
with Image.open(io.BytesIO(buf.getvalue())) as im:
    im.load()
    print("savefig", im.format, im.mode, im.size)
"""


@pytest.mark.slow
@BINARY
def test_a_broken_jpeg_raises_and_the_next_decodes(guest, which) -> None:
    """A JPEG whose first Huffman table counts 255 one-bit codes raises Pillow's `OSError: broken
    data stream when reading image file` 300 times in a row: libjpeg's error handler longjmps out
    of the codec through the guest's setjmp support, each time. The next good decode in the same
    guest gives the jpeg_images job's pixels; `features.check("jpg")` is true; and matplotlib's
    `savefig(format="jpg")` writes a file that opens as a JPEG."""
    job = "jpeg_images"
    files = {f"/jobs/{job}.py": jobs.script(job).read_bytes()}
    r = _plot(guest, which, BROKEN_JPEG, files=files)
    assert r.exit_code == 0, r.describe()
    golden = re.search(rb"^default decodes to .*$", jobs.expected_path(job).read_bytes(), re.M)
    assert golden, f"{job}.expected has no 'default decodes to' line"
    expected = (
        "broken {'broken data stream when reading image file': 300}\n"
        f"{golden[0].decode()}\n"
        "jpg True\n"
        "savefig JPEG RGB (200, 150)\n"
    )
    assert r.text == expected, r.text
