"""v1.3: the default profile's pure-Python packages, tier A (spec 039). Each family's golden job
prints native Python's output in the guest; pyyaml, markupsafe and charset-normalizer run their
pure-Python paths, as nothing native of theirs is in the zip; threadpoolctl finds no native thread
pools, which is the truth on wasm32-wasi. pandas' Styler and networkx's graph atlas read their own
files from the zip through spec 041's two carried patches, with native Python's output.
scikit-learn (spec 044) gives native scikit-learn's answers serially: no OpenMP, joblib in the
calling thread, its datasets and style sheets read from the zip (one carried patch), and what the
sandbox lacks raised by name."""

from __future__ import annotations

import json

import pytest

from harness import jobs, needs, scan

pytestmark = pytest.mark.goal("v1.3")

BINARY = pytest.mark.parametrize("which", ["plain", "snapshot"])
FAMILIES = ("excel", "pdf", "markup", "text_formats", "modelling", "symbolic", "utilities")


def _job(guest, job: str) -> None:
    why = jobs.compare(jobs.expected_path(job).read_bytes(), jobs.run_in_guest(guest, job))
    assert why is None, f"{job}: {why}"


@pytest.mark.slow
def test_files_from_the_zip_job_matches_native(guest) -> None:
    """pandas' Styler renders HTML, LaTeX, text, Typst and a custom template, and networkx reads
    its graph atlas, from the zip, as native Python does with the files on disk (spec 041,
    Decision 7). Equal output shows the patches change no result on these calls; the Styler check
    below shows the patched branch served them."""
    _job(guest, "files_from_the_zip")


@pytest.mark.slow
def test_excel_job_matches_native(guest) -> None:
    """xlsxwriter writes in memory, openpyxl reads, pandas round-trips through both, openpyxl writes
    with a writable folder for its temporary files, and xlrd refuses an .xlsx (Decision 11)."""
    _job(guest, "excel")


@pytest.mark.slow
def test_pdf_job_matches_native(guest) -> None:
    """pypdf reads, merges, writes, and encrypts with RC4; AES raises DependencyError."""
    _job(guest, "pdf")


@pytest.mark.slow
def test_markup_job_matches_native(guest) -> None:
    """beautifulsoup4 with html.parser and html5lib, soupsieve, `pd.read_html` with bs4 and its
    default flavor (lxml, spec 046), webencodings, xmltodict and defusedxml."""
    _job(guest, "markup")


@pytest.mark.slow
def test_text_formats_job_matches_native(guest) -> None:
    """pyyaml's safe loader and dumper, tomli-w, jinja2, markupsafe, `df.to_markdown()` through
    tabulate's metadata, and charset-normalizer's guesses."""
    _job(guest, "text_formats")


@pytest.mark.slow
def test_modelling_job_matches_native(guest) -> None:
    """networkx's algorithms and patsy's design matrices, with nothing that needs scipy."""
    _job(guest, "modelling")


@pytest.mark.slow
def test_symbolic_job_matches_native(guest) -> None:
    """sympy's algebra, calculus, matrices, ODEs and `lambdify(..., modules="numpy")`, and mpmath
    at 30 digits."""
    _job(guest, "symbolic")


@pytest.mark.slow
def test_utilities_job_matches_native(guest) -> None:
    """attrs, more-itertools, toolz, tqdm, typing_extensions, joblib (serial), cloudpickle and
    narwhals over pandas."""
    _job(guest, "utilities")


PURE = """
import json, sys, zipfile
import yaml
out = {"libyaml": yaml.__with_libyaml__,
       "C names": sorted(n for n in ("CLoader", "CSafeLoader", "CDumper") if hasattr(yaml, n))}
try:
    import _yaml
    out["_yaml"] = "imported"
except ModuleNotFoundError:
    out["_yaml"] = "ModuleNotFoundError"
import markupsafe
out["markupsafe"] = markupsafe._escape_inner.__module__
import charset_normalizer, charset_normalizer.md
out["md"] = charset_normalizer.md.__file__.endswith(".pyc")
best = charset_normalizer.from_bytes("Grüße aus Köln, Straße und Öl.".encode("utf_16")).best()
out["guess"] = best.encoding
out["mypyc modules"] = sorted(m for m in sys.modules if "__mypyc" in m)
with zipfile.ZipFile("/usr/local/lib/python315.zip") as z:
    out["mypyc members"] = sorted(n for n in z.namelist() if "__mypyc" in n)
print(json.dumps(out))
"""


@BINARY
def test_the_default_profile_runs_its_pure_python_paths(guest, which) -> None:
    """pyyaml has no libyaml (`__with_libyaml__` is False, no C loaders, no `_yaml`); markupsafe
    escapes through `_native`; charset-normalizer's modules are bytecode and no mypyc module is in
    the zip or loaded after it runs (Decision 3; the review's finding 8)."""
    r = guest(which, ["-c", PURE])
    assert r.exit_code == 0, r.describe()
    want = {
        "libyaml": False,
        "C names": [],
        "_yaml": "ModuleNotFoundError",
        "markupsafe": "markupsafe._native",
        "md": True,
        "guess": "utf_16",
        "mypyc modules": [],
        "mypyc members": [],
    }
    assert json.loads(r.text) == want


THREADPOOLS = """
import json, warnings
warnings.simplefilter("error")
import ctypes.util
from threadpoolctl import ThreadpoolController, threadpool_info, threadpool_limits
out = {"info": threadpool_info()}
limits = threadpool_limits(limits=1, user_api="blas")
with limits:
    out["inside"] = threadpool_info()
out["left"] = True
out["openmp"] = ThreadpoolController().select(user_api="openmp").info()
out["dllist"] = ctypes.util.dllist()
print(json.dumps(out))
"""


@BINARY
def test_threadpoolctl_finds_no_native_pools(guest, which) -> None:
    """The ctypes stand-in's `util.dllist()` answers `[]`, the truth for one statically linked
    module, so threadpoolctl lists no library, enters and leaves a limit, and selects nothing,
    with every warning an error (Decision 5). Without `dllist` it would call `CDLL(None)`, which
    the stand-in refuses with OSError."""
    r = guest(which, ["-c", THREADPOOLS])
    assert r.exit_code == 0, r.describe()
    want = {"dllist": [], "info": [], "inside": [], "left": True, "openmp": []}
    assert json.loads(r.text) == want


def _findings(guest, which: str, program: str, **kw) -> list[str]:
    r = guest(which, ["-c", program], **kw)
    assert r.exit_code == 0, r.describe()
    return json.loads(r.text)


FINDINGS = """
import json
findings = []

def attempt(label, call):
    try:
        call()
    except Exception as e:
        # jinja2's TemplateNotFound quotes the zip's path in its message: its name says what failed
        detail = e.name if type(e).__name__ == "TemplateNotFound" else str(e)
        findings.append(f"{label}: {type(e).__name__}: {detail}")
"""

STYLER = (
    FINDINGS
    + """
import pandas as pd
df = pd.DataFrame({"a": [1, 2], "b": [0.5, 1.5]})
attempt("df.style.to_html()", lambda: df.style.to_html())
attempt("df.to_latex()", lambda: df.to_latex())
attempt("df.style.to_string()", lambda: df.style.to_string())
attempt("df.style.to_typst()", lambda: df.style.to_typst())

def custom():
    from pandas.io.formats.style import Styler
    Mine = Styler.from_custom_template("/data", html_table="mine.tpl")
    if "<p>mine</p>" not in Mine(df).to_html():
        raise AssertionError("the custom template did not render")

attempt("from_custom_template", custom)

def loader():
    from pandas.io.formats.style_render import StylerRenderer
    name = type(StylerRenderer.loader).__name__
    if name != "PackageLoader":
        raise AssertionError(f"the loader is {name}")

attempt("StylerRenderer", loader)
print(json.dumps(findings))
"""
)
MINE = b'{% extends "html_table.tpl" %}{% block table %}<p>mine</p>{{ super() }}{% endblock %}'


@BINARY
def test_pandas_styler_renders_from_the_zip(guest, which) -> None:
    """pandas' Styler loads its templates from the zip: `df.style` to HTML, text and Typst,
    `df.to_latex()`, and a custom template in a granted folder that extends a built-in one, with
    jinja2's PackageLoader, the carried patch's branch for templates that are not a folder (spec
    041, Decisions 2 and 7). Without the patch, importing the Styler raises TemplateNotFound."""
    findings = _findings(guest, which, STYLER, files={"/data/mine.tpl": MINE})
    assert not findings, scan.report(findings)


ATLAS = (
    FINDINGS
    + """
import networkx as nx
attempt("nx.graph_atlas(100)", lambda: nx.graph_atlas(100))
attempt("nx.graph_atlas_g()", lambda: nx.graph_atlas_g())
print(json.dumps(findings))
"""
)


@BINARY
def test_networkx_atlas_reads_from_the_zip(guest, which) -> None:
    """networkx opens its graph atlas resource and decompresses the stream, the carried patch, so
    `graph_atlas` and `graph_atlas_g` read it from the zip (spec 041, Decisions 3 and 7). Without
    the patch, `gzip.open` refuses the zip's Traversable with TypeError (spec 039, Decision 9)."""
    findings = _findings(guest, which, ATLAS)
    assert not findings, scan.report(findings)


# scikit-learn (spec 044, Decision 13). Each behaviour check runs as an embedder calls it, nothing
# writable, on both binaries, with a fuel limit a hang ends at; the golden runs through the judge's
# driver, as scipy's do.
SKLEARN_FUEL = 80 * 10**9  # an import of scikit-learn and a small fit, with room
SKLEARN_MODULES = 69  # step 58's module count
SKLEARN_RENAMED = (  # recipes/sklearn-renames/, scripts/gen_inittab.py's RENAMED
    "sklearn._cyutility",
    "sklearn.ensemble._hist_gradient_boosting._gradient_boosting",
    "sklearn.cluster._hdbscan._tree",
    "sklearn.manifold._utils",
    "sklearn.utils._random",
)


def _sklearn(guest, which: str, code: str) -> dict:
    r = guest(which, ["-c", code], fuel=SKLEARN_FUEL, root_writable=False)
    assert (r.exit_code, r.trapped) == (0, None), r.describe()
    return json.loads(r.text.strip().splitlines()[-1])


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
def test_machine_learning_job_matches_native(guest, which) -> None:
    """scikit-learn's bundled datasets, a tree, a scaled logistic regression, a forest with
    n_jobs=1 and 2, KMeans, PCA, linear and ridge regression, an RBF SVC and a LinearSVC, a k-d
    tree k-NN's cross-validation, histogram gradient boosting, a ColumnTransformer over a pandas
    frame, TF-IDF and a joblib round trip print native scikit-learn's values (Decision 13)."""
    _golden(guest, which, "machine_learning")


SKLEARN_THREADS = """
import json, warnings
warnings.simplefilter("error")
import joblib
import numpy as np
from threadpoolctl import threadpool_info
from sklearn.cluster import KMeans
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.utils._openmp_helpers import _openmp_effective_n_threads, _openmp_parallelism_enabled
X, y = load_iris(return_X_y=True)
every = RandomForestClassifier(n_estimators=10, random_state=0, n_jobs=-1).fit(X, y)
one = RandomForestClassifier(n_estimators=10, random_state=0, n_jobs=1).fit(X, y)
km = KMeans(n_clusters=3, n_init=1, random_state=0).fit(X)
print(json.dumps({
    "openmp": _openmp_parallelism_enabled(),
    "n_threads": _openmp_effective_n_threads(-1),
    "n_jobs": joblib.effective_n_jobs(-1),
    "same": np.array_equal(every.predict_proba(X), one.predict_proba(X)),
    "pools": threadpool_info(),
    "clusters": len(set(km.labels_.tolist())),
}))
"""


@BINARY
def test_scikit_learn_runs_without_threads(guest, which) -> None:
    """With every warning an error, scikit-learn says OpenMP is off and resolves every n_threads to
    1; joblib's n_jobs=-1 is 1, so a forest fitted with it predicts what n_jobs=1 predicts;
    threadpoolctl finds no pool; a KMeans fit returns (Decisions 3 and 9)."""
    got = _sklearn(guest, which, SKLEARN_THREADS)
    want = {"openmp": False, "n_threads": 1, "n_jobs": 1, "same": True, "pools": [], "clusters": 3}
    assert got == want


SKLEARN_FILES = """
import json
from sklearn import datasets
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils import all_estimators, estimator_html_repr
names = ("iris", "digits", "diabetes", "breast_cancer", "wine", "linnerud")
loaded = {n: getattr(datasets, f"load_{n}")() for n in names}
html = estimator_html_repr(make_pipeline(StandardScaler(), LogisticRegression()))
print(json.dumps({
    "shapes": {n: list(b.data.shape) for n, b in loaded.items()},
    "descr": sorted(n for n, b in loaded.items() if b.DESCR.startswith(".. _")),
    "css": "--sklearn-color-unfitted-level-0: #fff5e6;" in html,
    "estimators": len(all_estimators()),
}))
"""


@BINARY
def test_scikit_learn_reads_its_files_from_the_zip(guest, which) -> None:
    """The six bundled loaders give native's shapes and descriptions through importlib.resources;
    the HTML representation holds a line of estimator.css, which the carried patch reads as a
    package resource (without it, `import sklearn` raises NotADirectoryError); all_estimators()
    finds native's 208 (Decisions 7 and 9)."""
    got = _sklearn(guest, which, SKLEARN_FILES)
    shapes = {
        "iris": [150, 4],
        "digits": [1797, 64],
        "diabetes": [442, 10],
        "breast_cancer": [569, 30],
        "wine": [178, 13],
        "linnerud": [20, 3],
    }
    want = {"shapes": shapes, "descr": sorted(shapes), "css": True, "estimators": 208}
    assert got == want


SKLEARN_LACKS = """
import json
from sklearn.datasets import fetch_california_housing, load_sample_images
out = {}
try:
    load_sample_images()
except Exception as e:
    out["images"] = [type(e).__name__, getattr(e, "name", None)]
try:
    fetch_california_housing()
except Exception as e:
    out["fetch"] = [type(e).__name__, getattr(e, "filename", None)]
print(json.dumps(out))
"""


def test_scikit_learn_says_what_it_lacks() -> None:
    """Through `wasi_python.run` itself, with no root and no grant (the runner's defaults), on the
    plain binary: the sample photographs are left out, so load_sample_images() raises
    ModuleNotFoundError naming sklearn.datasets.images; a fetcher's cache folder is under `~`,
    which no HOME expands, so fetch_california_housing() raises FileNotFoundError on `~` before
    any network call (Decision 9). With a root the folder is made and the download fails instead,
    as the README says."""
    needs.need("runner", "artifact dir")
    import wasi_python

    done = wasi_python.run(["-c", SKLEARN_LACKS], snapshot=False, fuel=SKLEARN_FUEL)
    assert done.exit_code == 0, done
    got = json.loads(done.stdout.decode().strip().splitlines()[-1])
    want = {
        "images": ["ModuleNotFoundError", "sklearn.datasets.images"],
        "fetch": ["FileNotFoundError", "~"],
    }
    assert got == want


SKLEARN_BUILTINS = """
import importlib, json, sys
names = sorted(n for n in sys.builtin_module_names if n.split(".")[0] == "sklearn")
wrong = []
for n in names:
    try:
        got = importlib.import_module(n).__name__
    except Exception as e:
        got = f"import {type(e).__name__}"
    if got != n:
        wrong.append([n, got])
print(json.dumps({"names": names, "wrong": wrong}))
"""


@BINARY
def test_scikit_learn_modules_are_builtin(guest, which) -> None:
    """Each of scikit-learn's 69 extension modules is a builtin that imports under its dotted
    name, the form 023's and 037's checks use; the four whose init functions are renamed are
    among them (Decisions 6 and 8). They run apart from the other packages' dotted builtins
    (test_v1_1_artifact_set), as scipy's do."""
    got = _sklearn(guest, which, SKLEARN_BUILTINS)
    assert len(got["names"]) == SKLEARN_MODULES, got["names"]
    assert set(SKLEARN_RENAMED) <= set(got["names"]), got["names"]
    assert got["wrong"] == [], got["wrong"]
