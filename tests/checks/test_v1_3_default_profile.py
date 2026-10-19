"""v1.3: the default profile's pure-Python packages, tier A (spec 039). Each family's golden job
prints native Python's output in the guest; pyyaml, markupsafe and charset-normalizer run their
pure-Python paths, as nothing native of theirs is in the zip; threadpoolctl finds no native thread
pools, which is the truth on wasm32-wasi. Two calls that read files by path from the zip are known
gaps until spec 041."""

from __future__ import annotations

import json

import pytest

from harness import jobs, scan

pytestmark = pytest.mark.goal("v1.3")

BINARY = pytest.mark.parametrize("which", ["plain", "snapshot"])
FAMILIES = ("excel", "pdf", "markup", "text_formats", "modelling", "symbolic", "utilities")


def _job(guest, job: str) -> None:
    why = jobs.compare(jobs.expected_path(job).read_bytes(), jobs.run_in_guest(guest, job))
    assert why is None, f"{job}: {why}"


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


def _findings(guest, which: str, program: str) -> list[str]:
    r = guest(which, ["-c", program])
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
print(json.dumps(findings))
"""
)


@pytest.mark.parametrize("which", ["plain"])
def test_pandas_styler_renders_from_the_zip(guest, which) -> None:
    """A known gap until spec 041: pandas' Styler loads its templates with jinja2's
    FileSystemLoader on a folder inside the zip, so `df.style` and `df.to_latex()` raise
    TemplateNotFound (Decision 12; the memo's finding 4d)."""
    findings = _findings(guest, which, STYLER)
    assert not findings, scan.report(findings)


ATLAS = (
    FINDINGS
    + """
import networkx as nx
attempt("nx.graph_atlas(100)", lambda: nx.graph_atlas(100))
print(json.dumps(findings))
"""
)


@pytest.mark.parametrize("which", ["plain"])
def test_networkx_atlas_reads_from_the_zip(guest, which) -> None:
    """A known gap until spec 041: networkx opens its graph atlas with `gzip.open` on an
    `importlib.resources` path, which inside a zip is a Traversable, not a file name (Decision
    9)."""
    findings = _findings(guest, which, ATLAS)
    assert not findings, scan.report(findings)
