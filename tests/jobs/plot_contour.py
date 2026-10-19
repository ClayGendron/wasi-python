"""Golden job: matplotlib's second milestone (spec 043, Decision 8).

Usage: plot_contour.py <data dir> <out dir> [saves dir].

A Delaunay triangulation of 30 seeded points (matplotlib's `_qhull`), qhull's error on collinear
points, contourpy's `serial`, `mpl2014` and `mpl2005` lines at one level, and a 6 x 3 inch figure
at 100 dpi with `contourf`, `contour`, `clabel`, `tricontourf` and `triplot`, saved to SVG and
PDF. It prints the size and full SHA-256 of each file; the PDF's hash is of the file with each
font subset tag (`/[A-Z]{1,6}+`) replaced by `/XXXXXX+`, with the number of tags replaced, because
matplotlib names a subset from `hash()`, which is 32 bits wide in the guest. Last, the canvas's
RGBA buffer. The output directory stays empty; with a third argument, the SVG and the PDF are
saved there too, by `savefig` on a path, and the judge compares them with these lines and pins
the guest's raw PDF bytes.

Every setting that would make a file differ from run to run is fixed here, not by the oracle's
environment: `svg.hashsalt` (SVG ids), and `Date` and `CreationDate` set to None (the time). The
oracle runs it with MPL_IGNORE_SYSTEM_FONTS=1 and a fresh MPLCONFIGDIR, as the guest's own fonts.
Float sums are `math.fsum`, so no summation order is printed, rounded to nine digits."""

import hashlib
import io
import math
import re
import sys

import matplotlib

matplotlib.use("agg")
import contourpy  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.tri as mtri  # noqa: E402
import numpy as np  # noqa: E402

data_dir, out_dir = sys.argv[1], sys.argv[2]
saves = sys.argv[3] if len(sys.argv) > 3 else None
TAG = re.compile(rb"/[A-Z]{1,6}\+")
SVG_META = {"Date": None}
PDF_META = {"CreationDate": None}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ints(a) -> str:
    """The SHA-256 of an integer array as little-endian int32, whatever its dtype."""
    return sha(np.ascontiguousarray(a, dtype="<i4").tobytes())


def num(x) -> str:
    return format(round(float(x), 9) + 0.0, ".9g")


print(
    f"versions python={sys.version_info[0]}.{sys.version_info[1]} "
    f"matplotlib={matplotlib.__version__} contourpy={contourpy.__version__} "
    f"numpy={np.__version__}"
)

rng = np.random.default_rng(7)
px, py = rng.random(30), rng.random(30)
tri = mtri.Triangulation(px, py)
shape = "x".join(str(n) for n in tri.triangles.shape)
print("delaunay", shape, "triangles", ints(tri.triangles), "neighbors", ints(tri.neighbors))
try:
    mtri.Triangulation([0.0, 1.0, 2.0, 3.0], [0.0, 1.0, 2.0, 3.0])
    print("collinear no error")
except RuntimeError as e:
    print("collinear RuntimeError", e)

x = np.linspace(-3.0, 3.0, 41)
X, Y = np.meshgrid(x, x)
Z = np.exp(-(X**2) - Y**2) - 0.5 * np.exp(-((X - 1.0) ** 2) - (Y - 1.0) ** 2)
for name in ("serial", "mpl2014", "mpl2005"):
    gen = contourpy.contour_generator(X, Y, Z, name=name, line_type="SeparateCode")
    lines, _codes = gen.lines(0.25)
    points = np.concatenate(lines) if lines else np.zeros((0, 2))
    sums = [num(math.fsum(points[:, 0])), num(math.fsum(points[:, 1]))]
    print("contourpy", name, len(lines), len(points), *sums)

fig, (left, right) = plt.subplots(1, 2, figsize=(6, 3), dpi=100)
filled = left.contourf(X, Y, Z, levels=7)
lined = left.contour(X, Y, Z, levels=7, colors="k", linewidths=0.5)
left.clabel(lined, fontsize=6)
pz = np.sin(3.0 * px) * np.cos(3.0 * py)
right.tricontourf(tri, pz, levels=7)
right.triplot(tri, "k-", linewidth=0.3)
print("levels", *[num(v) for v in filled.levels])

plt.rcParams["svg.hashsalt"] = "wasi-python"
buf = io.BytesIO()
fig.savefig(buf, format="svg", metadata=SVG_META)
svg = buf.getvalue()
print("svg", len(svg), sha(svg))
buf = io.BytesIO()
fig.savefig(buf, format="pdf", metadata=PDF_META)
pdf, tags = TAG.subn(b"/XXXXXX+", buf.getvalue())
print("pdf", len(pdf), "tags", tags, sha(pdf))
if saves is not None:
    fig.savefig(f"{saves}/contour.svg", metadata=SVG_META)
    fig.savefig(f"{saves}/contour.pdf", metadata=PDF_META)

fig.canvas.draw()
rgba = np.asarray(fig.canvas.buffer_rgba())
print("rgba", "x".join(str(n) for n in rgba.shape), sha(rgba.tobytes()))
