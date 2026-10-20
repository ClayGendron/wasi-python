"""Golden job: scikit-learn fits, predicts, scores, clusters, decomposes and pipelines on the
datasets it ships (spec 044, Decision 13). Usage: machine_learning.py <data dir> <out dir> (both
unused). Runs natively (the oracle) and in the guest; its output must be byte-identical in both.

The datasets load from the zip through importlib.resources, unchanged. Values print with
significant digits, 037's rules: 9 for direct results, 6 for iterative ones, whose solvers get
tolerances far tighter than the digits printed; no dtype (np.intp is 32 bits in the guest), no
timing and no iteration count; every input fixed or seeded. A forest with n_jobs=2 runs serially in
the guest (joblib has no _multiprocessing there), and must give n_jobs=1's answer, as natively.
"""

import io
from importlib.metadata import version

import joblib
import numpy as np
import pandas as pd
from sklearn import datasets
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, confusion_matrix, r2_score, roc_auc_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC, LinearSVC
from sklearn.tree import DecisionTreeClassifier

D = ".9g"  # direct results
IT = ".6g"  # iterative results


def f(x, k=D):
    return format(float(x) + 0.0, k)


def fs(xs, k=D):
    return "[" + ", ".join(f(x, k) for x in np.ravel(xs)) + "]"


names = ["scikit-learn", "scipy", "numpy", "pandas", "joblib", "threadpoolctl", "narwhals"]
print("versions", " ".join(f"{n}={version(n)}" for n in names))

iris = datasets.load_iris()
digits = datasets.load_digits()
diabetes = datasets.load_diabetes()
cancer = datasets.load_breast_cancer()
wine = datasets.load_wine(as_frame=True)
shapes = (iris.data, digits.data, diabetes.data, cancer.data, wine.frame)
print("shapes", *(s.shape for s in shapes))
print("iris targets", [str(n) for n in iris.target_names], "first row", fs(iris.data[0]))
print("descr starts", iris.DESCR.splitlines()[0])

X_tr, X_te, y_tr, y_te = train_test_split(
    iris.data, iris.target, test_size=0.3, random_state=0, stratify=iris.target
)

tree = DecisionTreeClassifier(random_state=0).fit(X_tr, y_tr)
print(
    "tree nodes",
    tree.tree_.node_count,
    "depth",
    tree.get_depth(),
    "importances",
    fs(tree.feature_importances_),
)
print("tree accuracy", f(accuracy_score(y_te, tree.predict(X_te))))
print("tree confusion", confusion_matrix(y_te, tree.predict(X_te)).tolist())

logreg = make_pipeline(StandardScaler(), LogisticRegression(tol=1e-12, max_iter=10_000))
logreg.fit(X_tr, y_tr)
print("logreg accuracy", f(logreg.score(X_te, y_te)), "coef", fs(logreg[-1].coef_, IT))
print("logreg proba row 0", fs(logreg.predict_proba(X_te[:1]), IT))

forest1 = RandomForestClassifier(n_estimators=25, random_state=0, n_jobs=1).fit(X_tr, y_tr)
forest2 = RandomForestClassifier(n_estimators=25, random_state=0, n_jobs=2).fit(X_tr, y_tr)
print(
    "forest accuracy",
    f(forest1.score(X_te, y_te)),
    "importances",
    fs(forest1.feature_importances_),
)
same = np.array_equal(forest1.predict_proba(X_te), forest2.predict_proba(X_te))
print("forest n_jobs=2 equals n_jobs=1:", bool(same))

km = KMeans(n_clusters=3, n_init=10, random_state=0).fit(iris.data)
print("kmeans inertia", f(km.inertia_, IT), "sizes", sorted(np.bincount(km.labels_).tolist()))

pca = PCA(n_components=2).fit(iris.data)
print(
    "pca explained ratio",
    fs(pca.explained_variance_ratio_),
    "|components|",
    fs(np.abs(pca.components_)),
)

Xd_tr, Xd_te, yd_tr, yd_te = train_test_split(diabetes.data, diabetes.target, random_state=0)
lin = LinearRegression().fit(Xd_tr, yd_tr)
print("linear r2", f(r2_score(yd_te, lin.predict(Xd_te))), "coef", fs(lin.coef_))
ridge = Ridge(alpha=1.0).fit(Xd_tr, yd_tr)
print("ridge coef", fs(ridge.coef_), "intercept", f(ridge.intercept_))

Xc_tr, Xc_te, yc_tr, yc_te = train_test_split(
    cancer.data, cancer.target, random_state=0, stratify=cancer.target
)
svc = make_pipeline(StandardScaler(), SVC(random_state=0)).fit(Xc_tr, yc_tr)
print("svc accuracy", f(svc.score(Xc_te, yc_te)), "support vectors", svc[-1].n_support_.tolist())
print("svc auc", f(roc_auc_score(yc_te, svc.decision_function(Xc_te)), IT))
lsvc = make_pipeline(StandardScaler(), LinearSVC(random_state=0, tol=1e-10, max_iter=100_000))
lsvc.fit(Xc_tr, yc_tr)
print("linear svc accuracy", f(lsvc.score(Xc_te, yc_te)))

knn = KNeighborsClassifier(n_neighbors=3, algorithm="kd_tree")
print("knn digits cv", fs(cross_val_score(knn, digits.data, digits.target, cv=5)))

hgb = HistGradientBoostingClassifier(max_iter=30, random_state=0)
Xw, yw = wine.data, wine.target
Xw_tr, Xw_te, yw_tr, yw_te = train_test_split(Xw, yw, random_state=0, stratify=yw)
hgb.fit(Xw_tr, yw_tr)
print("hist gradient boosting accuracy", f(hgb.score(Xw_te, yw_te)))

frame = pd.DataFrame(
    {
        "city": ["a", "b", "a", "c", "b", "c", "a", "b"],
        "x": [1.0, 2.5, 3.0, 0.5, 2.0, 1.5, 4.0, 3.5],
    }
)
target = [0, 1, 0, 1, 1, 1, 0, 1]
ct = ColumnTransformer([("city", OneHotEncoder(), ["city"]), ("x", StandardScaler(), ["x"])])
model = make_pipeline(ct, LogisticRegression(tol=1e-12)).fit(frame, target)
print(
    "column transformer features",
    list(ct.get_feature_names_out()),
    "predictions",
    model.predict(frame).tolist(),
)

docs = ["the cat sat on the mat", "the dog sat on the log", "cats and dogs", "a mat and a log"]
tfidf = TfidfVectorizer().fit(docs)
m = tfidf.transform(docs)
print("tfidf vocabulary", len(tfidf.vocabulary_), "nnz", m.nnz, "row 0", fs(m[0].data))

buf = io.BytesIO()
joblib.dump(forest1, buf)
buf.seek(0)
again = joblib.load(buf)
same = np.array_equal(again.predict(X_te), forest1.predict(X_te))
print("joblib round trip predicts the same:", bool(same))
