"""Write the probe jobs: scipy's remaining candidate files one per session; scikit-learn's and
statsmodels' likely-heavy files alone, the rest as draft groups.

    uv run python build/095b/survey/mkjobs.py
"""

from pathlib import Path

S = Path.cwd() / "build/095b/survey"
M = "-mnot slow and not xslow"


def label(prefix: str, path: str) -> str:
    rest = path.split("/", 1)[1].replace("/tests", "").removesuffix(".py").replace("/", ".")
    return f"{prefix}-{rest}"


lines = []
for path in (S / "files-scipy.txt").read_text().split():
    lines.append("\t".join(["scipy", label("sc", path), "150e9", M, path]))
SK_ALONE = [
    "sklearn/ensemble/tests/test_gradient_boosting.py",
    "sklearn/cluster/tests/test_k_means.py",
    "sklearn/manifold/tests/test_t_sne.py",
    "sklearn/metrics/tests/test_pairwise.py",
    "sklearn/_loss/tests/test_loss.py",
]
SK_A = [
    "sklearn/tree/tests/test_monotonic_tree.py", "sklearn/tree/tests/test_split.py",
    "sklearn/ensemble/_hist_gradient_boosting/tests/test_splitting.py",
    "sklearn/ensemble/_hist_gradient_boosting/tests/test_histogram.py",
    "sklearn/ensemble/_hist_gradient_boosting/tests/test_binning.py",
    "sklearn/ensemble/_hist_gradient_boosting/tests/test_predictor.py",
    "sklearn/cluster/tests/test_dbscan.py", "sklearn/cluster/_hdbscan/tests",
    "sklearn/svm/tests", "sklearn/linear_model/tests/test_base.py",
    "sklearn/linear_model/tests/test_sag.py",
    "sklearn/linear_model/tests/test_sparse_coordinate_descent.py",
    "sklearn/linear_model/tests/test_perceptron.py",
]
SK_B = [
    "sklearn/feature_extraction/tests/test_feature_hasher.py",
    "sklearn/datasets/tests/test_svmlight_format.py",
    "sklearn/metrics/tests/test_pairwise_distances_reduction.py", "sklearn/metrics/cluster/tests",
    "sklearn/neighbors/tests/test_kd_tree.py", "sklearn/neighbors/tests/test_ball_tree.py",
    "sklearn/neighbors/tests/test_quad_tree.py",
    "sklearn/preprocessing/tests/test_polynomial.py",
    "sklearn/preprocessing/tests/test_target_encoder.py",
    "sklearn/utils/tests/test_sparsefuncs.py", "sklearn/utils/tests/test_cython_blas.py",
    "sklearn/utils/tests/test_murmurhash.py", "sklearn/utils/tests/test_fast_dict.py",
    "sklearn/utils/tests/test_seq_dataset.py", "sklearn/utils/tests/test_arrayfuncs.py",
    "sklearn/utils/tests/test_random.py", "sklearn/utils/tests/test_typedefs.py",
    "sklearn/utils/tests/test_weight_vector.py", "sklearn/utils/_repr_html/tests",
    "sklearn/decomposition/tests/test_online_lda.py", "sklearn/decomposition/tests/test_nmf.py",
    "sklearn/tests/test_isotonic.py",
]
for path in SK_ALONE:
    lines.append("\t".join(["scikit-learn", label("sk", path), "150e9", path]))
lines.append("\t".join(["scikit-learn", "sk-group-a", "400e9", *SK_A]))
lines.append("\t".join(["scikit-learn", "sk-group-b", "400e9", *SK_B]))
SM_ALONE = [
    "statsmodels/regression/tests/test_regression.py",
    "statsmodels/tsa/holtwinters/tests/test_holtwinters.py",
    "statsmodels/tsa/tests/test_exponential_smoothing.py",
    "statsmodels/tsa/regime_switching/tests/test_markov_regression.py",
    "statsmodels/tsa/stl/tests/test_stl.py",
    "statsmodels/nonparametric/tests/test_kde.py",
    "statsmodels/tsa/statespace/tests/test_simulation_smoothing.py",
    "statsmodels/tsa/statespace/tests/test_kalman.py",
]
SM_G = [
    "statsmodels/nonparametric/tests/test_lowess.py", "statsmodels/robust/tests/test_scale.py",
    "statsmodels/tsa/innovations/tests", "statsmodels/tsa/arima/tests",
    "statsmodels/tsa/statespace/tests/test_tools.py", "statsmodels/genmod/families/tests",
    "statsmodels/formula/tests", "statsmodels/iolib/tests", "statsmodels/tsa/filters/tests",
]
for path in SM_ALONE:
    lines.append("\t".join(["statsmodels", label("sm", path), "150e9", path]))
lines.append("\t".join(["statsmodels", "sm-group", "400e9", *SM_G]))
(S / "jobs-2.tsv").write_text("\n".join(lines) + "\n")
print(len(lines), "jobs")
