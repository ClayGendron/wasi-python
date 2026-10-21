"""extra.json for gen095.py: not_selected, smoke_cover and derived per family; and pass 1's
signal split (the clock-stepped conv-method group) written into groups.json and splits.json."""

import json
from pathlib import Path

SP = Path(__file__).parent
INV = json.loads((SP / "inventory.json").read_text())

TEST_ONLY = (
    "imports one of scipy's test-only C modules (_test_ccallback, _test_multivariate, _ctest, "
    "_cytest, _test_internal), which the product leaves out on purpose; the judge-only binary "
    "the roadmap reserves (088) links them"
)
extra = {
    "scipy": {
        "derived_row": "scipy-special",
        "derived": [
            {
                "script": "scipy/special/utils/makenpz.py",
                "args": [name],
                "inputs": f"scipy/special/tests/data/{name}",
                "output": f"scipy/special/tests/data/{name}.npz",
                "measured": fuel,
            }
            for name, fuel in (
                ("boost", 5_780_000_000),
                ("gsl", 1_240_000_000),
                ("local", 1_570_000_000),
            )
        ],
        "not_selected": [
            {
                "files": [
                    "scipy/_lib/tests/test_ccallback.py",
                    "scipy/integrate/tests/test_quadpack.py",
                    "scipy/ndimage/tests/test_c_api.py",
                    "scipy/special/tests/test_dd.py",
                    "scipy/special/tests/test_round.py",
                ],
                "reason": "each " + TEST_ONLY + "; it fails to load without them",
                "closes_with": "context/roadmap.md",
            },
            {
                "files": [
                    "scipy/linalg/tests/test_cython_abi.py",
                    "scipy/optimize/tests/test_cython_abi.py",
                    "scipy/special/tests/test_cython_abi.py",
                ],
                "reason": (
                    "each reads capsule names through ctypes.pythonapi at import, which the ctypes "
                    "stand-in lacks; the stand-ins' names at import (reserved in the roadmap as "
                    "074) would let them load, their tests then a no-ctypes class"
                ),
                "closes_with": "context/roadmap.md",
            },
            {
                "files": [
                    "scipy/linalg/tests/_cython_examples/ilp64_test_package/tests/test_direct.py",
                    "scipy/linalg/tests/_cython_examples/ilp64_test_package/tests/test_wrappers.py",
                ],
                "reason": (
                    "an example package test_extending.py would build with meson in a "
                    "subprocess; scipy installs only its extending.pyx and meson.build, so it is "
                    "not part of the installed suite"
                ),
                "closes_with": "README.md",
            },
        ],
    },
    "scikit-learn": {
        "not_selected": [
            {
                "files": [
                    "sklearn/cluster/tests/test_hierarchical.py",
                    "sklearn/metrics/tests/test_dist_metrics.py",
                ],
                "reason": (
                    "each builds memory-mapped arrays at import (create_memmap_backed_data), and "
                    "the mmap stand-in raises, so the file cannot load"
                ),
                "closes_with": "README.md",
            },
            {
                "files": ["sklearn/neighbors/tests/test_neighbors.py"],
                "reason": (
                    "it imports a constant from metrics/tests/test_dist_metrics.py, which cannot "
                    "load without mmap"
                ),
                "closes_with": "README.md",
            },
        ],
    },
    "statsmodels": {
        "not_selected": [
            {
                "files": [
                    "statsmodels/discrete/tests/test_constrained.py",
                    "statsmodels/discrete/tests/test_margins.py",
                    "statsmodels/emplike/tests/test_anova.py",
                    "statsmodels/genmod/tests/test_glm_weights.py",
                    "statsmodels/stats/tests/test_oaxaca.py",
                    "statsmodels/tsa/vector_ar/tests/test_vecm.py",
                ],
                "reason": (
                    "each loads, at import, one of the thirteen datasets the product leaves out "
                    "for their terms, so the file cannot load and every test in it is lost"
                ),
                "closes_with": "README.md",
            },
        ],
    },
}

SCIPY_COVER = {
    "scipy": "scipy/special/tests/test_cython_special.py",
    "scipy._lib": (
        "release-only: imported by every session; the files that test its compiled paths "
        "(test_ccallback.py, the deprecation calls) need scipy's test-only C modules"
    ),
    "scipy._lib._uarray": "scipy/fft/tests/test_basic.py",
    "scipy.cluster.hierarchy": "scipy/cluster/hierarchy/tests",
    "scipy.cluster.vq": "scipy/cluster/vq/tests",
    "scipy.fft._duccfft": "scipy/fft/tests/test_basic.py",
    "scipy.fftpack": "scipy/fftpack/tests/test_pseudo_diffs.py",
    "scipy.integrate": "scipy/integrate/tests/test_integrate.py",
    "scipy.interpolate": "scipy/interpolate/tests/test_fitpack.py",
    "scipy.io._fast_matrix_market": "scipy/io/tests/test_mmio.py",
    "scipy.io.matlab": "scipy/io/matlab/tests",
    "scipy.linalg": "scipy/linalg/tests/test_decomp_cholesky.py",
    "scipy.ndimage": "scipy/ndimage/tests/test_measurements.py",
    "scipy.optimize": "scipy/optimize/tests/test_minpack.py",
    "scipy.optimize._highspy": "scipy/optimize/tests/test_milp.py",
    "scipy.optimize._lsq": "scipy/optimize/tests/test_lsq_linear.py",
    "scipy.optimize._trlib": "scipy/optimize/tests/test_trustregion_krylov.py",
    "scipy.optimize.cython_optimize": "scipy/optimize/tests/test_cython_optimize.py",
    "scipy.signal": "scipy/signal/tests/test_upfirdn.py",
    "scipy.sparse": "scipy/sparse/tests/test_sparsetools.py",
    "scipy.sparse.csgraph": "job tests/jobs/scipy_numeric.py:89 shortest_path",
    "scipy.sparse.linalg": "scipy/sparse/linalg/tests/test_propack.py",
    "scipy.sparse.linalg._dsolve": "scipy/sparse/linalg/_dsolve/tests",
    "scipy.sparse.linalg._eigen.arpack": "job tests/jobs/scipy_numeric.py:75 eigsh",
    "scipy.spatial": "scipy/spatial/tests/test_qhull.py",
    "scipy.spatial.transform": "scipy/spatial/transform/tests",
    "scipy.special": "scipy/special/tests/test_cython_special.py",
    "scipy.stats": "scipy/stats/tests/test_qmc.py",
    "scipy.stats._levy_stable": (
        "release-only: its tests live in test_distributions.py, 680 test functions, past a "
        "smoke file's reach, and no golden line calls it"
    ),
    "scipy.stats._rcont": "scipy/stats/tests/test_contingency.py",
    "scipy.stats._unuran": "scipy/stats/tests/test_sampling.py",
}
SKLEARN_COVER = {
    "sklearn": "sklearn/tests/test_isotonic.py",
    "sklearn.__check_build": "sklearn/tests/test_isotonic.py",
    "sklearn._loss": "job tests/jobs/machine_learning.py:0 LogisticRegression",
    "sklearn.cluster": "sklearn/cluster/tests/test_dbscan.py",
    "sklearn.cluster._hdbscan": "sklearn/cluster/_hdbscan/tests",
    "sklearn.datasets": "sklearn/datasets/tests/test_svmlight_format.py",
    "sklearn.decomposition": "sklearn/decomposition/tests/test_online_lda.py",
    "sklearn.ensemble": (
        "release-only: its one compiled module serves the classic gradient boosting, whose "
        "test file costs past a smoke file's reach, and no golden line calls it"
    ),
    "sklearn.ensemble._hist_gradient_boosting": (
        "sklearn/ensemble/_hist_gradient_boosting/tests/test_splitting.py"
    ),
    "sklearn.feature_extraction": "sklearn/feature_extraction/tests/test_feature_hasher.py",
    "sklearn.linear_model": "sklearn/linear_model/tests/test_sag.py",
    "sklearn.manifold": (
        "release-only: its compiled modules serve t-SNE, whose test file costs past a smoke "
        "file's reach, and no golden line calls it"
    ),
    "sklearn.metrics": "job tests/jobs/machine_learning.py:0 KNeighborsClassifier",
    "sklearn.metrics._pairwise_distances_reduction": (
        "sklearn/metrics/tests/test_pairwise_distances_reduction.py"
    ),
    "sklearn.metrics.cluster": "sklearn/metrics/cluster/tests",
    "sklearn.neighbors": "sklearn/neighbors/tests/test_kd_tree.py",
    "sklearn.preprocessing": "sklearn/preprocessing/tests/test_target_encoder.py",
    "sklearn.svm": "sklearn/svm/tests",
    "sklearn.tree": "sklearn/tree/tests/test_split.py",
    "sklearn.utils": "sklearn/utils/tests/test_sparsefuncs.py",
    "sklearn.utils._repr_html": "sklearn/utils/_repr_html/tests",
}
SM_COVER = {
    "statsmodels.datasets": "statsmodels/regression/tests/test_regression.py",
    "statsmodels.regression": "statsmodels/regression/tests/test_regression.py",
    "statsmodels.nonparametric": "statsmodels/nonparametric/tests/test_lowess.py",
    "statsmodels.robust": "statsmodels/robust/tests/test_scale.py",
    "statsmodels.tsa": "statsmodels/tsa/innovations/tests",
    "statsmodels.tsa.exponential_smoothing": (
        "release-only: its one test file, test_exponential_smoothing.py, costs past a smoke "
        "file's reach, and no golden line calls it"
    ),
    "statsmodels.tsa.holtwinters": "job tests/jobs/statistical_models.py:0 SimpleExpSmoothing",
    "statsmodels.tsa.innovations": "statsmodels/tsa/innovations/tests",
    "statsmodels.tsa.regime_switching": (
        "statsmodels/tsa/regime_switching/tests/test_markov_regression.py"
    ),
    "statsmodels.tsa.statespace": "statsmodels/tsa/statespace/tests/test_simulation_smoothing.py",
    "statsmodels.tsa.statespace._filters": "statsmodels/tsa/arima/tests",
    "statsmodels.tsa.statespace._smoothers": "statsmodels/tsa/arima/tests",
    "statsmodels.tsa.stl": "statsmodels/tsa/stl/tests/test_stl.py",
}
extra["scipy"]["smoke_cover"] = SCIPY_COVER
extra["scikit-learn"]["smoke_cover"] = SKLEARN_COVER
extra["statsmodels"]["smoke_cover"] = SM_COVER

# A job line's number, read from the job file: the line that calls the word.
W = Path("/Users/claygendron/Git/Repos/wasi_python/.claude/worktrees/agent-aab0b516adb4e5c06")
for fam in extra.values():
    for k, v in list(fam.get("smoke_cover", {}).items()):
        if v.startswith("job ") and ":0 " in v:
            path, word = v[4:].split(":0 ")
            lines = (W / path).read_text().splitlines()
            hits = [
                i
                for i, line in enumerate(lines, 1)
                if word + "(" in line and not line.lstrip().startswith(("from ", "import "))
            ]
            fam["smoke_cover"][k] = f"job {path}:{hits[0]} {word}"
(SP / "extra.json").write_text(json.dumps(extra, indent=1))

# pass 1: signal's folder without test_signaltools.py, which is split so its clock-timed test
# runs alone with its own clock step
groups = json.loads((SP / "groups.json").read_text())
plan_smoke = {
    "scipy/signal/tests/test_max_len_seq.py",
    "scipy/signal/tests/test_upfirdn.py",
    "scipy/signal/tests/test_splines.py",
    "scipy/signal/tests/test_bsplines.py",
}
sig = [g for g in groups["scipy"] if g["paths"] == ["scipy/signal/tests"]]
if sig:
    g = sig[0]
    files = [
        f
        for f in INV["scipy"]["files"]
        if f.startswith("scipy/signal/tests/") and f not in plan_smoke
        and f != "scipy/signal/tests/test_signaltools.py"
    ]
    g["paths"] = files
    i = groups["scipy"].index(g)
    groups["scipy"][i + 1 : i + 1] = [
        {"name": "scipy-signal-conv-method", "paths": ["scipy/signal/tests/test_signaltools.py"],
         "cap": 60_000_000_000, "clock": 1_000_000, "est": 37.9},
        {"name": "scipy-signal-signaltools", "paths": ["scipy/signal/tests/test_signaltools.py"],
         "cap": 1_500_000_000_000, "est": 400},
    ]
(SP / "groups.json").write_text(json.dumps(groups, indent=1))
(SP / "splits.json").write_text(
    json.dumps(
        {
            "scipy": [
                {
                    "file": "scipy/signal/tests/test_signaltools.py",
                    "groups": ["scipy-signal-conv-method", "scipy-signal-signaltools"],
                    "keywords": ["test_choose_conv_method and not _2"],
                }
            ]
        },
        indent=1,
    )
)
print("ok")
