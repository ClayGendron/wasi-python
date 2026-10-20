"""Golden job: seaborn's statistical plots (spec 042, Decision 10).

Usage: statistical_plots.py <data dir> <out dir> (both unused).

A fixed frame of 120 rows from numpy's PCG64 at seed 42 (three dose groups, ten days, `x` normal
and `y` linear in `x` with a group offset and noise), seaborn's theme and palettes, then a run of
plots, each on the Agg backend at 4 x 3 inches and 80 dpi unless a grid sets its own size. What is
printed is only what native Python prints the same way:
- a figure's RGBA buffer (its shape and full SHA-256), as matplotlib's plot job prints it;
- a figure's SVG (its length and SHA-256), with `svg.hashsalt` fixed and no date, only when the
  figure holds no raster: a heatmap's colour bar is an image, which the SVG embeds as a deflated
  PNG whose bytes depend on the zlib that wrote it, so the heatmap prints its RGBA only;
- fitted and estimated values as text at nine significant digits (a regression's band at six),
  never as pixels: a least-squares line is numpy's own `lapack_lite` in the guest and the host's
  LAPACK natively, which differ in the last bits and so move a few pixels. Each array is printed
  as the first 16 hex digits of the SHA-256 of its text and its first three values.

The oracle runs it with MPL_IGNORE_SYSTEM_FONTS=1 and a fresh MPLCONFIGDIR, as the guest's own
fonts, and with one BLAS thread (spec 037's oracle_env). seaborn uses scipy for its kernel
densities and its clustering once scipy imports; both paths print the same digits, and a check
of its own shows which one ran in the guest.
"""

import hashlib
import io
import math
import sys
from importlib.metadata import version

import matplotlib

matplotlib.use("agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402
import seaborn.objects as so  # noqa: E402

data_dir, out_dir = sys.argv[1], sys.argv[2]
print(
    "versions",
    *(f"{name}={version(name)}" for name in ("numpy", "pandas", "matplotlib", "seaborn")),
)
matplotlib.rcParams["svg.hashsalt"] = "wasi_python"
matplotlib.rcParams["figure.dpi"] = 80
SIZE = (4, 3)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def num(x, digits: int = 9) -> str:
    return format(float(x) + 0.0, f".{digits}g")


def values(a, digits: int = 9) -> str:
    """An array as text: the SHA-256 prefix of all its values, its size and its first three."""
    flat = [num(v, digits) for v in np.ravel(np.asarray(a, dtype=float))]
    return f"{sha(' '.join(flat).encode())[:16]} n={len(flat)} [{' '.join(flat[:3])}]"


def rgba(fig) -> str:
    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())
    return f"rgba {'x'.join(str(n) for n in buf.shape)} {sha(buf.tobytes())}"


def svg(fig) -> str:
    out = io.BytesIO()
    fig.savefig(out, format="svg", metadata={"Date": None})
    return f"svg {len(out.getvalue())} {sha(out.getvalue())}"


def show(name: str, fig, with_svg: bool = True) -> None:
    print(name, rgba(fig), *([svg(fig)] if with_svg else []))
    plt.close(fig)


def axes():
    return plt.subplots(figsize=SIZE)


rng = np.random.Generator(np.random.PCG64(42))
dose = np.repeat(["low", "mid", "high"], 40)
day = np.tile(np.repeat(np.arange(1, 11), 4), 3)
x = rng.normal(0.0, 1.0, 120)
offset = np.select([dose == "low", dose == "mid"], [0.0, 1.0], 2.0)
y = 1.5 * x + offset + rng.normal(0.0, 0.5, 120)
df = pd.DataFrame({"dose": dose, "day": day, "x": x, "y": y})
print("frame", "x".join(str(n) for n in df.shape), num(math.fsum(y)), num(np.std(y, ddof=1)))

sns.set_theme(style="whitegrid", palette="deep")
deep = sns.color_palette().as_hex()[:3]
husl = sns.color_palette("husl", 3).as_hex()
print("palette deep", *deep, "husl", *husl)

fig, ax = axes()
sns.scatterplot(data=df, x="x", y="y", hue="dose", style="dose", ax=ax)
show("scatterplot", fig)

fig, ax = axes()
sns.lineplot(data=df, x="day", y="y", hue="dose", errorbar="sd", ax=ax)
show("lineplot", fig)

fig, ax = axes()
sns.barplot(data=df, x="dose", y="y", errorbar=("ci", 95), n_boot=500, seed=0, ax=ax)
show("barplot", fig)

fig, ax = axes()
sns.histplot(data=df, x="y", hue="dose", multiple="stack", bins=12, ax=ax)
show("histplot", fig)

fig, ax = axes()
sns.boxplot(data=df, x="dose", y="y", ax=ax)
show("boxplot", fig)

fig, ax = axes()
sns.stripplot(data=df, x="dose", y="y", jitter=False, ax=ax)
show("stripplot", fig)

fig, ax = axes()
sns.ecdfplot(data=df, x="y", hue="dose", ax=ax)
show("ecdfplot", fig)

grid = sns.relplot(data=df, x="x", y="y", col="dose", height=2.0, aspect=1.0)
show("relplot", grid.figure)

grid = sns.pairplot(df[["x", "y", "day", "dose"]], hue="dose", diag_kind="hist", height=1.5)
show("pairplot", grid.figure)

means = df.pivot_table(index="dose", columns="day", values="y", aggfunc="mean")
fig, ax = axes()
sns.heatmap(means, annot=True, fmt=".1f", annot_kws={"size": 6}, ax=ax)
show("heatmap", fig, with_svg=False)

fig = plt.figure(figsize=SIZE)
so.Plot(df, x="x", y="y", color="dose").add(so.Dot()).add(so.Line(), so.Agg()).on(fig).plot()
show("objects", fig)

fig, ax = axes()
sns.regplot(data=df, x="x", y="y", n_boot=200, seed=0, ax=ax)
line = ax.lines[0].get_xydata()
band = ax.collections[1].get_paths()[0].vertices
print("regplot line", values(line), "band", values(band, 6))
plt.close(fig)

fig, ax = axes()
sns.kdeplot(data=df, x="y", ax=ax)
print("kdeplot", values(ax.lines[0].get_xydata()))
plt.close(fig)

fig, ax = axes()
sns.violinplot(data=df, x="dose", y="y", ax=ax)
outlines = [p.vertices for c in ax.collections for p in c.get_paths()]
print("violinplot", len(outlines), values(np.concatenate(outlines)))
plt.close(fig)

by_day = df.pivot_table(index="day", columns="dose", values="y", aggfunc="mean")
grid = sns.clustermap(by_day, figsize=(4, 4))
rows = grid.dendrogram_row.reordered_ind
cols = grid.dendrogram_col.reordered_ind
print("clustermap rows", rows, "cols", cols, "linkage", values(grid.dendrogram_row.linkage))
plt.close(grid.figure)
