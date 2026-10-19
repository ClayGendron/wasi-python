"""Golden job: scipy's direct computations (spec 037, Decision 15). Usage: scipy_numeric.py <data
dir> <out dir> (both unused). Runs natively (the oracle, scipy-openblas, one thread) and in the
guest (OpenBLAS 0.3.34's C LAPACK); its output must be byte-identical in both.

Every float is printed with 9 significant digits, never after an absolute round, so a small
p-value keeps its digits. Residuals print as a comparison with a stated bound. No eigenvector or
singular-vector sign, no iteration count, no timing. Every input is fixed here or drawn from a
seeded PCG64 generator.
"""

import sys

import numpy as np
import scipy
from scipy import (
    cluster,
    fft,
    interpolate,
    linalg,
    ndimage,
    signal,
    sparse,
    spatial,
    special,
    stats,
)
from scipy.sparse import csgraph
from scipy.sparse import linalg as splinalg


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


print(f"versions python={sys.version_info[0]}.{sys.version_info[1]} scipy={scipy.__version__}")
rng = np.random.Generator(np.random.PCG64(20261019))
A = rng.standard_normal((5, 5)) + 5 * np.eye(5)
b = rng.standard_normal(5)
S = A @ A.T + np.eye(5)  # symmetric positive definite

# linalg
show("solve", lambda: gs(linalg.solve(A, b)))
show("lu_factor piv", lambda: linalg.lu_factor(A)[1].tolist())
show("lu_factor diag(U)", lambda: gs(np.diag(linalg.lu_factor(A)[0])))
show("qr |diag(R)|", lambda: gs(np.abs(np.diag(linalg.qr(A)[1]))))
show("cholesky diag", lambda: gs(np.diag(linalg.cholesky(S))))
show("det", lambda: g(linalg.det(A)))
show("inv residual < 1e-12", lambda: bool(np.abs(linalg.inv(A) @ A - np.eye(5)).max() < 1e-12))
show("eigh values", lambda: gs(linalg.eigh(S)[0]))
show("eigvalsh", lambda: gs(linalg.eigvalsh(S)))
show("svdvals", lambda: gs(linalg.svdvals(A)))
show("expm", lambda: gs(linalg.expm(np.array([[0.0, 1.0], [-2.0, -3.0]]))))
show("solve_triangular", lambda: gs(linalg.solve_triangular(np.triu(A), b)))

# sparse: CSR, a product, SuperLU, ARPACK, csgraph
n = 30
main = 4.0 + np.arange(n) / n
T = sparse.diags([-np.ones(n - 1), main, -np.ones(n - 1)], [-1, 0, 1], format="csr")
x0 = np.linspace(1.0, 2.0, n)
show("csr nnz", lambda: (T.nnz, T.shape))
show("csr product", lambda: gs((T @ T @ x0)[:5]))
show("spsolve", lambda: gs(splinalg.spsolve(T.tocsc(), x0)[:5]))
show("eigsh largest", lambda: gs(np.sort(splinalg.eigsh(T, k=3, v0=x0, tol=1e-12)[0])))
G = sparse.csr_matrix(
    np.array(
        [
            [0, 2, 0, 0, 0, 0],
            [2, 0, 3, 0, 0, 0],
            [0, 3, 0, 1, 0, 0],
            [0, 0, 1, 0, 0, 0],
            [0, 0, 0, 0, 0, 5],
            [0, 0, 0, 0, 5, 0],
        ],
        dtype=float,
    )
)
show("shortest_path", lambda: csgraph.shortest_path(G, directed=False)[0].tolist())
show(
    "connected_components",
    lambda: (lambda c: (c[0], c[1].tolist()))(csgraph.connected_components(G)),
)

# fft (ducc0, threads compiled out: workers runs serially and gives the same answer)
sig = np.cos(2 * np.pi * 3 * np.arange(16) / 16) + 0.5 * np.arange(16) / 16
show("fft |X|", lambda: gs(np.abs(fft.fft(sig))[:9]))
show("rfft |X|", lambda: gs(np.abs(fft.rfft(sig))))
show("dct", lambda: gs(fft.dct(np.arange(1.0, 9.0) ** 1.5)))
show("fftfreq", lambda: gs(fft.fftfreq(8, d=0.5)))
show(
    "fft workers=4 equals workers=1",
    lambda: bool(np.array_equal(fft.fft(sig, workers=4), fft.fft(sig, workers=1))),
)

# special (xsf, Boost.Math)
show("gamma", lambda: gs(special.gamma([0.5, 4.5, 10.25])))
show("erf", lambda: gs(special.erf([0.1, 0.9, 2.5])))
show("jv", lambda: gs(special.jv([0, 1, 2.5], 3.7)))
show("beta", lambda: g(special.beta(2.5, 3.25)))
show("betaincc", lambda: g(special.betaincc(2.5, 3.5, 0.3)))
show("hyp2f1", lambda: g(special.hyp2f1(0.5, 1.5, 2.25, 0.4)))
show("ellipk", lambda: g(special.ellipk(0.7)))
show("zeta", lambda: gs(special.zeta([2.0, 3.5, 7.0])))

# stats
data1 = rng.normal(10.0, 2.0, 40)
data2 = rng.normal(11.0, 2.5, 35)
show("norm.cdf", lambda: gs(stats.norm.cdf([-5.0, -1.0, 0.3])))
show("norm.ppf", lambda: gs(stats.norm.ppf([0.001, 0.25, 0.975])))
show("t.sf", lambda: gs(stats.t.sf([2.0, 8.0], df=7)))
show("beta.ppf", lambda: gs(stats.beta.ppf([0.1, 0.5, 0.9], 2.0, 5.0)))
show("binom.pmf", lambda: gs(stats.binom.pmf([0, 3, 17], 20, 0.3)))
show(
    "describe",
    lambda: (
        lambda d: (
            f"{d.nobs} {gs(d.minmax)} {g(d.mean)} {g(d.variance)} {g(d.skewness)} {g(d.kurtosis)}"
        )
    )(stats.describe(data1)),
)
show(
    "ttest_ind",
    lambda: (lambda r: f"{g(r.statistic)} {g(r.pvalue)}")(stats.ttest_ind(data1, data2)),
)
show(
    "pearsonr",
    lambda: (lambda r: f"{g(r.statistic)} {g(r.pvalue)}")(stats.pearsonr(data1[:35], data2)),
)
show(
    "linregress",
    lambda: (lambda r: gs([r.slope, r.intercept, r.rvalue, r.pvalue, r.stderr]))(
        stats.linregress(np.arange(35.0), data2)
    ),
)
show("gaussian_kde", lambda: gs(stats.gaussian_kde(data1)([8.0, 10.0, 12.0])))

# interpolate (griddata runs qhull)
xs = np.linspace(0.0, 3.0, 7)
ys = np.sin(xs) + xs / 4
show("CubicSpline", lambda: gs(interpolate.CubicSpline(xs, ys)([0.25, 1.1, 2.9])))
show(
    "make_interp_spline", lambda: gs(interpolate.make_interp_spline(xs, ys, k=3)([0.25, 1.1, 2.9]))
)
pts = rng.uniform(0.0, 1.0, (30, 2))
vals = pts[:, 0] ** 2 + pts[:, 1]
show(
    "griddata linear",
    lambda: gs(interpolate.griddata(pts, vals, [[0.5, 0.5], [0.3, 0.6]], method="linear")),
)
show(
    "RBFInterpolator", lambda: gs(interpolate.RBFInterpolator(pts, vals)([[0.5, 0.5], [0.3, 0.6]]))
)

# signal
bb, aa = signal.butter(4, 0.2)
noisy = np.sin(np.arange(64) / 4.0) + 0.3 * rng.standard_normal(64)
show("butter b", lambda: gs(bb))
show("butter a", lambda: gs(aa))
show("lfilter", lambda: gs(signal.lfilter(bb, aa, noisy)[-4:]))
show("filtfilt", lambda: gs(signal.filtfilt(bb, aa, noisy)[:4]))
show("convolve", lambda: gs(signal.convolve([1.0, 2.0, 3.0], [0.0, 1.0, 0.5])))
show("find_peaks", lambda: signal.find_peaks(np.sin(np.arange(40) / 2.0), height=0.5)[0].tolist())
show(
    "welch",
    lambda: (lambda fp: f"{gs(fp[0][:4])} | {gs(fp[1][:4])}")(
        signal.welch(noisy, fs=8.0, nperseg=32)
    ),
)

# ndimage
img = np.zeros((8, 8))
img[1:3, 1:3] = 1.0
img[5:7, 4:7] = 2.0
show("gaussian_filter", lambda: gs(ndimage.gaussian_filter(img, sigma=1.0)[2, :5]))
show("label", lambda: (lambda lab: (lab[1], lab[0].sum().item()))(ndimage.label(img > 0)))

# spatial (qhull, cKDTree)
P = rng.uniform(0.0, 1.0, (20, 3))
show("cdist", lambda: gs(spatial.distance.cdist(P[:3], P[3:6])))
show(
    "cKDTree.query",
    lambda: (lambda dq: f"{gs(dq[0])} {dq[1].tolist()}")(
        spatial.cKDTree(P).query([[0.5, 0.5, 0.5]], k=3)
    ),
)
show("ConvexHull.volume", lambda: g(spatial.ConvexHull(P).volume))
show("Delaunay simplices", lambda: spatial.Delaunay(P[:, :2]).simplices.shape[0])

# cluster
show("linkage", lambda: gs(cluster.hierarchy.linkage(P[:8], method="average")[:, 2]))
