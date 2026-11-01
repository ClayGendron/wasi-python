"""v1.3: the default profile's pure-Python packages, tier A. Each family's golden job
prints native Python's output in the guest; pyyaml, markupsafe and charset-normalizer run their
pure-Python paths, as nothing native of theirs is in the zip; threadpoolctl finds no native thread
pools, which is the truth on wasm32-wasi. pandas' Styler and networkx's graph atlas read their own
files from the zip through two carried patches, with native Python's output.
scikit-learn gives native scikit-learn's answers serially: no OpenMP, joblib in the
calling thread, its datasets and style sheets read from the zip (one carried patch), and what the
sandbox lacks raised by name. statsmodels gives native statsmodels' answers, its
public-domain datasets read from the zip (one carried patch), the thirteen left out raising
FileNotFoundError, both formula engines in pure Python, and what the sandbox lacks raised.
python-docx and python-pptx start from their default templates, read from the zip through one
carried patch each, and write Word and PowerPoint files with native Python's output.
pdfplumber reads text and tables with native Python's output, pdfminer.six without cryptography
until a file needs AES (one carried patch), and page images name pypdfium2; xarray aligns, groups,
interpolates and writes netCDF3 with native Python's output. drawsvg draws SVG, HTML and
animations with native Python's output, and its parts the set lacks fail by name."""

from __future__ import annotations

import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from harness import jobs, needs, scan

pytestmark = pytest.mark.goal("v1.3")

BINARY = pytest.mark.parametrize("which", ["plain", "snapshot"])
FAMILIES = ("excel", "pdf", "markup", "text_formats", "modelling", "symbolic", "utilities")
MPL_ENV = {"MPLCONFIGDIR": "/mplconfig"}  # a writable cache folder in the judge's root


def _job(guest, job: str, **kw) -> None:
    why = jobs.compare(jobs.expected_path(job).read_bytes(), jobs.run_in_guest(guest, job, **kw))
    assert why is None, f"{job}: {why}"


@pytest.mark.slow
def test_files_from_the_zip_job_matches_native(guest) -> None:
    """pandas' Styler renders HTML, LaTeX, text, Typst and a custom template, and networkx reads
    its graph atlas, from the zip, as native Python does with the files on disk.
    Equal output shows the patches change no result on these calls; the Styler check
    below shows the patched branch served them."""
    _job(guest, "files_from_the_zip")


@pytest.mark.slow
def test_documents_job_matches_native(guest) -> None:
    """python-docx writes a Word document (a heading, bold and italic runs, a table, a picture, a
    section's own header and footer, and a comment) and python-pptx a deck (a title slide, a
    bullet slide, a table, a column chart, a picture and a notes slide), each from its default
    template; each file is saved, reopened and read back as native Python reads it. Equal output
    shows the patches change no result on these calls."""
    _job(guest, "documents")


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
    default flavor (lxml), webencodings, xmltodict and defusedxml."""
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


# seaborn imports matplotlib.pyplot, which needs a writable cache folder; both jobs read
# matplotlib's data (its fonts, DejaVu Sans for reportlab) from its grant.
MPL = {"env": {"MPLCONFIGDIR": "/mplconfig"}, "mpl_data": True}


@pytest.mark.slow
def test_statistical_plots_job_matches_native(guest) -> None:
    """seaborn's relational, distribution, categorical, grid, matrix and objects plots, each
    figure's RGBA buffer (and its SVG when it holds no raster) equal to the oracle's, and its
    regression, kernel densities, violins and clustering as text at nine digits (recorded on the
    platform tests/jobs/statistical_plots.platform names)."""
    _job(guest, "statistical_plots", **MPL)


@pytest.mark.slow
def test_pdf_reports_job_matches_native(guest) -> None:
    """reportlab's canvas, platypus, charts through renderPDF and renderSVG, renderPM's error,
    Unicode text in DejaVu Sans and a matplotlib image, each PDF's bytes (built invariant and
    uncompressed) or pypdf's read-back equal to the oracle's."""
    _job(guest, "pdf_reports", **MPL)


@pytest.mark.slow
def test_pdf_tables_job_matches_native(guest) -> None:
    """reportlab draws a two-page ruled table; pdfplumber reads each page's text, its words'
    boxes, its ruling lines and its tables, and opens a copy pypdf encrypted with RC4 by its
    password, all as native pdfplumber does."""
    _job(guest, "pdf_tables")


@pytest.mark.slow
def test_vector_drawings_job_matches_native(guest) -> None:
    """drawsvg draws its README drawing, a native SVG animation with playback controls, frame
    callbacks, 1,000 circles, an embedded PNG and a clip path and mask, as SVG and HTML with
    native drawsvg's bytes. drawsvg ships no tests, so this holds the guest's interpreter to
    native's on drawsvg's code: the two agree, which is not to say the SVG is right."""
    _job(guest, "vector_drawings")


@pytest.mark.slow
def test_plotly_figures_job_matches_native(guest) -> None:
    """plotly builds a graph-objects figure and an express scatter of its iris dataset, reads its
    tips, gapminder and election datasets, and writes JSON, an HTML fragment, an offline page with
    plotly.js inside and a page that loads it from the CDN, as native plotly does; `to_image`
    fails as natively without kaleido."""
    _job(guest, "plotly_figures")


@pytest.mark.slow
def test_labelled_arrays_job_matches_native(guest) -> None:
    """xarray aligns two arrays on their labels, groups, rolls, resamples and interpolates through
    scipy, round-trips a DataFrame and netCDF3 bytes, and draws its HTML view from the package's
    files, as native xarray does; an absent engine and the tutorial data fail by name."""
    _job(guest, "labelled_arrays")


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
    the zip or loaded after it runs (Decision 3)."""
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
    jinja2's PackageLoader, the carried patch's branch for templates that are not a folder.
    Without the patch, importing the Styler raises TemplateNotFound."""
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


REPORTLAB = """
import io, json, zipfile
out = {}
try:
    import _rl_accel
    out["_rl_accel"] = "imported"
except ModuleNotFoundError:
    out["_rl_accel"] = "ModuleNotFoundError"
from reportlab.lib import rl_accel
out["c funcs"] = sorted(rl_accel._c_funcs)
out["py funcs"] = sorted(rl_accel._py_funcs)
from reportlab.graphics import renderPM
from reportlab.graphics.shapes import Drawing
try:
    renderPM.drawToString(Drawing(10, 10), fmt="PNG")
    out["renderPM"] = "drew"
except Exception as e:
    out["renderPM"] = [type(e).__name__, "rlPyCairo" in str(e)]
with zipfile.ZipFile("/usr/local/lib/python315.zip") as z:
    out["font members"] = [n for n in z.namelist() if n.startswith("reportlab/fonts/")]
from reportlab.pdfbase.ttfonts import TTFError, TTFont
try:
    TTFont("Vera", "Vera.ttf")
    out["Vera"] = "registered"
except TTFError:
    out["Vera"] = "TTFError"
try:
    from reportlab.graphics.barcode import qr
    out["qr"] = "imported"
except ModuleNotFoundError:
    out["qr"] = "ModuleNotFoundError"
from reportlab.pdfgen import canvas
buf = io.BytesIO()
c = canvas.Canvas(buf, invariant=1)
c.drawString(72, 72, "pure")
c.save()
out["pdf"] = buf.getvalue()[:5].decode()
print(json.dumps(out))
"""
RL_ACCEL = [
    "add32",
    "asciiBase85Decode",
    "asciiBase85Encode",
    "calcChecksum",
    "escapePDF",
    "fp_str",
    "hex32",
    "instanceStringWidthT1",
    "instanceStringWidthTTF",
    "sameFrag",
    "unicode2T1",
]


@BINARY
def test_reportlab_runs_its_pure_paths(guest, which) -> None:
    """reportlab runs without `_rl_accel` (all eleven of its functions are the Python ones), has
    no bitmap renderer (renderPM needs rlPyCairo), has no fonts of its own in the zip (bundled
    `Vera.ttf` raises TTFError), has no barcode modules while the leave-out stands, and writes a
    PDF in memory."""
    r = guest(which, ["-c", REPORTLAB])
    assert r.exit_code == 0, r.describe()
    want = {
        "_rl_accel": "ModuleNotFoundError",
        "c funcs": [],
        "py funcs": RL_ACCEL,
        "renderPM": ["RenderPMError", True],
        "font members": [],
        "Vera": "TTFError",
        "qr": "ModuleNotFoundError",
        "pdf": "%PDF-",
    }
    assert json.loads(r.text) == want


SCIPY_PATHS = """
import json
import seaborn, seaborn.matrix, seaborn._statistics
print(json.dumps({
    "matrix._no_scipy": seaborn.matrix._no_scipy,
    "_statistics._no_scipy": seaborn._statistics._no_scipy,
    "gaussian_kde": seaborn._statistics.gaussian_kde.__module__,
}))
"""
LOAD_DATASET = """
import seaborn
try:
    seaborn.load_dataset("tips")
    print("loaded")
except Exception as e:
    print(type(e).__name__, repr(getattr(e, "filename", None)))
"""


@BINARY
def test_seaborn_takes_its_scipy_paths(guest, guest_workdir, which) -> None:
    """seaborn takes scipy's paths, not its own copies: `_no_scipy` is False in `matrix` and
    `_statistics`, and its kernel density is scipy's `gaussian_kde`; it catches only ImportError,
    so a scipy that failed to import would leave it on its copies silently.
    And `load_dataset` through the runner, with only a writable cache grant
    (the README's set-up), raises PermissionError naming its cache folder under the HOME before
    any fetch, and makes no `~` folder in the grant: with no writable /tmp the guest's HOME is
    the runner's empty, read-only folder, so seaborn cannot make its cache folder there."""
    needs.need("runner")
    import wasi_python

    r = guest(which, ["-c", SCIPY_PATHS], **MPL)
    assert r.exit_code == 0, r.describe()
    got = json.loads(r.text)
    assert got["matrix._no_scipy"] is False and got["_statistics._no_scipy"] is False, got
    assert got["gaussian_kde"].startswith("scipy."), got

    cfg = Path(tempfile.mkdtemp(prefix="seaborn-cfg-", dir=guest_workdir))
    done = wasi_python.run(
        ["-c", LOAD_DATASET],
        grants=[wasi_python.Grant(cfg, "/cfg", writable=True)],
        env={"MPLCONFIGDIR": "/cfg"},
        snapshot=which == "snapshot",
    )
    # The folder first: litter in the caller's grant is the worse failure.
    assert not (cfg / "~").exists(), sorted(p.name for p in cfg.iterdir())
    assert done.exit_code == 0, done
    assert done.stdout.startswith(b"PermissionError '/tmp/.home-"), done
    assert done.stdout.endswith(b"/.cache'\n"), done


@BINARY
def test_networkx_atlas_reads_from_the_zip(guest, which) -> None:
    """networkx opens its graph atlas resource and decompresses the stream, the carried patch, so
    `graph_atlas` and `graph_atlas_g` read it from the zip. Without
    the patch, `gzip.open` refuses the zip's Traversable with TypeError."""
    findings = _findings(guest, which, ATLAS)
    assert not findings, scan.report(findings)


# python-docx's six template sites and python-pptx's three, each called as the package calls it.
# A site that returns a path (as an install from files does) is opened, so the check reads what the
# package would read; each result is hashed. parse_from_template's result is compared with the
# zip's member parsed by parse_xml, both serialised; the icon by the blob of the image part an OLE
# object adds. Then a document and a deck are made from the defaults and saved in memory.
OFFICE = """
import hashlib, io, json, zipfile
from lxml import etree
import docx, pptx
from docx import api as docx_api
from docx.parts.comments import CommentsPart
from docx.parts.hdrftr import FooterPart, HeaderPart
from docx.parts.settings import SettingsPart
from docx.parts.styles import StylesPart
from pptx import api as pptx_api
from pptx.enum.shapes import PROG_ID
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml import parse_from_template, parse_xml
from pptx.util import Inches

def digest(call):
    try:
        got = call()
        if isinstance(got, str):
            with open(got, "rb") as f:
                got = f.read()
        elif not isinstance(got, bytes):
            got = got.read()
        return hashlib.sha256(got).hexdigest()
    except Exception as e:
        return type(e).__name__

def icon(prog_id):
    prs = pptx.Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.shapes.add_ole_object(io.BytesIO(b"object"), prog_id, Inches(1), Inches(1))
    (blob,) = [r.target_part.blob for r in slide.part.rels.values() if r.reltype == RT.IMAGE]
    return blob

def saved(make):
    try:
        out = io.BytesIO()
        make().save(out)
        return out.getvalue()[:2].decode()
    except Exception as e:
        return type(e).__name__

def document():
    d = docx.Document()
    d.add_paragraph("body")
    d.sections[0].header.paragraphs[0].text = "header"
    d.sections[0].footer.paragraphs[0].text = "footer"
    d.add_comment(d.paragraphs[0].runs, text="a comment", author="judge")
    return d

def deck():
    prs = pptx.Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.notes_slide.notes_text_frame.text = "notes"
    return prs

sites = {
    "docx/templates/default.docx": lambda: docx_api._default_docx_path(),
    "docx/templates/default-settings.xml": SettingsPart._default_settings_xml,
    "docx/templates/default-styles.xml": StylesPart._default_styles_xml,
    "docx/templates/default-comments.xml": CommentsPart._default_comments_xml,
    "docx/templates/default-footer.xml": FooterPart._default_footer_xml,
    "docx/templates/default-header.xml": HeaderPart._default_header_xml,
    "pptx/templates/default.pptx": lambda: pptx_api._default_pptx_path(),
    "pptx/templates/generic-icon.emf": lambda: icon("Foo.Bar.18"),
    "pptx/templates/docx-icon.emf": lambda: icon(PROG_ID.DOCX),
    "pptx/templates/pptx-icon.emf": lambda: icon(PROG_ID.PPTX),
    "pptx/templates/xlsx-icon.emf": lambda: icon(PROG_ID.XLSX),
}
out = {"files": [docx.__file__, pptx.__file__]}
out["sites"] = {member: digest(call) for member, call in sites.items()}
out["parsed"] = {}
with zipfile.ZipFile("/usr/local/lib/python315.zip") as z:
    for name in ("theme", "notesMaster", "notes"):
        member = parse_xml(z.read(f"pptx/templates/{name}.xml"))
        out["parsed"][name] = [
            digest(lambda: etree.tostring(parse_from_template(name))),
            digest(lambda: etree.tostring(member)),
        ]
out["saved"] = {"docx": saved(document), "pptx": saved(deck)}
print(json.dumps(out))
"""
OFFICE_MEMBERS = (
    "docx/templates/default.docx",
    "docx/templates/default-settings.xml",
    "docx/templates/default-styles.xml",
    "docx/templates/default-comments.xml",
    "docx/templates/default-footer.xml",
    "docx/templates/default-header.xml",
    "pptx/templates/default.pptx",
    "pptx/templates/generic-icon.emf",
    "pptx/templates/docx-icon.emf",
    "pptx/templates/pptx-icon.emf",
    "pptx/templates/xlsx-icon.emf",
)


@BINARY
def test_office_templates_read_from_the_zip(guest, artifacts, which) -> None:
    """python-docx's and python-pptx's nine template sites each read their template from the zip,
    the bytes the zip holds (parse_from_template's three XML templates parse to the zip member's
    tree, and each OLE object's default icon is the zip's), and a document and a deck made from
    the defaults save in memory, with nothing granted. Both packages are imported from the zip.
    Without the carried patches each site opens a path inside the zip, and `Document()` and
    `Presentation()` raise PackageNotFoundError."""
    r = guest(which, ["-c", OFFICE], root_writable=False)
    assert r.exit_code == 0, r.describe()
    got = json.loads(r.text)
    zip_path = "/usr/local/lib/python315.zip/"
    assert all(f.startswith(zip_path) for f in got["files"]), got["files"]
    with zipfile.ZipFile(artifacts.path("python-stdlib.zip")) as z:
        want = {m: hashlib.sha256(z.read(m)).hexdigest() for m in OFFICE_MEMBERS}
    assert got["sites"] == want
    assert sorted(got["parsed"]) == ["notes", "notesMaster", "theme"]
    for name, (template, member) in got["parsed"].items():
        assert len(template) == 64 and template == member, (name, template, member)
    assert got["saved"] == {"docx": "PK", "pptx": "PK"}


# scikit-learn. Each behaviour check runs as an embedder calls it, nothing
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
    the runner's empty, read-only HOME where /tmp is not writable, so fetch_california_housing()
    raises PermissionError on that folder before any network call (Decision 9). With a root the
    folder is made and the download fails instead, as the README says."""
    needs.need("runner", "artifact dir")
    import wasi_python

    done = wasi_python.run(["-c", SKLEARN_LACKS], snapshot=False, fuel=SKLEARN_FUEL)
    assert done.exit_code == 0, done
    got = json.loads(done.stdout.decode().strip().splitlines()[-1])
    fetch = got.pop("fetch")
    assert got == {"images": ["ModuleNotFoundError", "sklearn.datasets.images"]}, got
    assert fetch[0] == "PermissionError", fetch
    assert fetch[1].startswith("/tmp/.home-") and fetch[1].endswith("/scikit_learn_data"), fetch


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
    """Each of scikit-learn's 69 extension modules is a builtin that imports under its dotted name,
    the form matplotlib's and scipy's checks use; the four whose init functions are renamed are
    among them (Decisions 6 and 8). They run apart from the other packages' dotted builtins
    (test_v1_1_artifact_set), as scipy's do."""
    got = _sklearn(guest, which, SKLEARN_BUILTINS)
    assert len(got["names"]) == SKLEARN_MODULES, got["names"]
    assert set(SKLEARN_RENAMED) <= set(got["names"]), got["names"]
    assert got["wrong"] == [], got["wrong"]


# statsmodels (Decision 12), as scikit-learn's: each behaviour check runs as an embedder
# calls it, nothing writable, with a fuel limit a hang ends at; the golden runs through the judge's
# driver.
SM_FUEL = 80 * 10**9  # an import of statsmodels.api and a few loads or fits, with room
SM_MODULES = 26  # step 59's module count
SM_RENAMED = (  # recipes/statsmodels-renames/, scripts/gen_inittab.py's RENAMED
    "statsmodels.tsa.statespace._tools",
    "statsmodels.tsa.statespace._smoothers._conventional",
    "statsmodels.tsa.statespace._smoothers._univariate",
    "statsmodels.tsa.statespace._smoothers._univariate_diffuse",
)
SM_SHAPES = {  # natively, the pinned oracle (EXECUTED at the build)
    "anes96": [944, 11],
    "co2": [2284, 1],
    "danish_data": [55, 5],
    "elec_equip": [257, 1],
    "elnino": [61, 13],
    "engel": [235, 2],
    "grunfeld": [220, 5],
    "longley": [16, 7],
    "macrodata": [203, 14],
    "modechoice": [840, 9],
    "nile": [100, 2],
    "randhie": [20190, 10],
    "stackloss": [21, 4],
    "statecrime": [51, 7],
    "strikes": [62, 2],
    "sunspots": [309, 2],
}
SM_LEFT_OUT = (
    "cancer ccard china_smoking committee copper cpunish fair fertility heart interest_inflation "
    "scotland spector star98"
).split()


@pytest.mark.slow
@BINARY
def test_statistical_models_job_matches_native(guest, which) -> None:
    """OLS on longley with its summary's coefficient table and robust errors, one formula fitted
    with patsy and with formulaic, a type-2 ANOVA, a Logit by Newton, a Poisson GLM by IRLS, a
    t-test, Benjamini-Hochberg, ARIMA fitted and filtered, ADF, ACF and PACF, STL, simple
    exponential smoothing, LOWESS and a KDE print native statsmodels' values (Decision 12)."""
    _golden(guest, which, "statistical_models")


SM_DATASETS = """
import importlib, json
names = (
    "anes96 co2 danish_data elec_equip elnino engel grunfeld longley macrodata modechoice nile "
    "randhie stackloss statecrime strikes sunspots"
).split()
shapes = {}
for n in names:
    shapes[n] = list(importlib.import_module(f"statsmodels.datasets.{n}").load_pandas().data.shape)
print(json.dumps({"shapes": shapes}))
"""


@BINARY
def test_statsmodels_reads_its_datasets_from_the_zip(guest, which) -> None:
    """Each of the sixteen public-domain datasets loads from the zip with native's shape, through
    the carried patch's package-resource fallback (without it, every loader raises
    NotADirectoryError; Decisions 7 and 9)."""
    assert _sklearn(guest, which, SM_DATASETS) == {"shapes": SM_SHAPES}


SM_LEFT = """
import importlib, json
import statsmodels.api as sm
names = (
    "cancer ccard china_smoking committee copper cpunish fair fertility heart interest_inflation "
    "scotland spector star98"
).split()
raised = {}
for n in names:
    try:
        importlib.import_module(f"statsmodels.datasets.{n}").load_pandas()
        raised[n] = None
    except Exception as e:
        raised[n] = type(e).__name__
print(json.dumps({"api": sm.OLS.__name__, "raised": raised}))
"""


def test_left_out_datasets_say_so(guest) -> None:
    """`import statsmodels.api` works, and each of the thirteen datasets whose files are left out
    raises FileNotFoundError: the type only, since the message is the zip's resource reader's,
    which promises none (Decision 9)."""
    got = _sklearn(guest, "plain", SM_LEFT)
    assert got == {"api": "OLS", "raised": dict.fromkeys(SM_LEFT_OUT, "FileNotFoundError")}


SM_FORMULAS = """
import json
import numpy as np
import pandas as pd
import formulaic, patsy, wrapt.__wrapt__
frame = pd.DataFrame({
    "y": [1.0, 2.5, 2.0, 4.5, 5.0, 6.5],
    "x": [0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
    "g": ["a", "b", "c", "a", "b", "c"],
})
mm = formulaic.model_matrix("y ~ x + C(g)", frame)
_, px = patsy.dmatrices("y ~ x + C(g)", frame, return_type="dataframe")
fx = mm.rhs
same = sorted(fx.columns) == sorted(px.columns) and all(
    np.array_equal(np.asarray(fx[c], dtype=float), np.asarray(px[c], dtype=float))
    for c in px.columns
)
print(json.dumps({
    "c_extension": wrapt.__wrapt__._using_c_extension,
    "columns": sorted(px.columns),
    "same": same,
}))
"""


@BINARY
def test_formula_engines_run_pure(guest, which) -> None:
    """wrapt runs its pure-Python classes (its wheel carries no compiled module), and formulaic's
    model matrix for `y ~ x + C(g)` has patsy's columns with the same values, column by column
    (their orders differ; Decisions 1 and 6), as natively."""
    got = _sklearn(guest, which, SM_FORMULAS)
    want = {
        "c_extension": False,
        "columns": ["C(g)[T.b]", "C(g)[T.c]", "Intercept", "x"],
        "same": True,
    }
    assert got == want


SM_LACKS = """
import json
import statsmodels.api as sm
from statsmodels.tsa.x13 import x13_arima_analysis
out = {}
try:
    x13_arima_analysis(sm.datasets.co2.load_pandas().data["co2"].resample("MS").mean().ffill())
except Exception as e:
    out["x13"] = type(e).__name__
try:
    sm.datasets.get_rdataset("iris")
except Exception as e:
    out["rdataset"] = [type(e).__name__, str(getattr(e, "reason", e))]
print(json.dumps(out))
"""


def test_statsmodels_says_what_it_lacks() -> None:
    """Through `wasi_python.run` itself, with no root and no grant (the runner's defaults), on the
    plain binary: X-13ARIMA-SEATS is a program statsmodels runs in a subprocess, which the guest
    neither carries nor can start, so x13_arima_analysis raises X13NotFoundError; get_rdataset
    downloads, and with its default cache=False goes straight to urlopen, whose https scheme the
    guest has no handler for (Decision 11). With cache=True and a root, its cache folder is made
    first and the download fails the same way, as the README says."""
    needs.need("runner", "artifact dir")
    import wasi_python

    done = wasi_python.run(["-c", SM_LACKS], snapshot=False, fuel=SM_FUEL)
    assert done.exit_code == 0, done
    got = json.loads(done.stdout.decode().strip().splitlines()[-1])
    want = {"x13": "X13NotFoundError", "rdataset": ["URLError", "unknown url type: https"]}
    assert got == want


SM_HDR = """
import json
import matplotlib
matplotlib.use("Agg")
import statsmodels.api as sm
data = sm.datasets.elnino.load_pandas().data
try:
    sm.graphics.hdrboxplot(data.iloc[:, 1:].to_numpy(), rng=0, kernel_rng=0)
    out = None
except Exception as e:
    out = [type(e).__name__, str(e)]
print(json.dumps({"hdrboxplot": out}))
"""


def test_hdrboxplot_needs_processes(guest) -> None:
    """hdrboxplot maps its band search over multiprocessing.Pool(), which needs os.pipe, so in the
    guest it raises where natively it draws (Decision 11); a plot needs matplotlib's data, granted
    as the runner grants it, and a writable config folder."""
    r = guest("plain", ["-c", SM_HDR], env=MPL_ENV, mpl_data=True, fuel=SM_FUEL)
    assert (r.exit_code, r.trapped) == (0, None), r.describe()
    got = json.loads(r.text.strip().splitlines()[-1])
    assert got == {"hdrboxplot": ["AttributeError", "module 'os' has no attribute 'pipe'"]}


SM_BUILTINS = """
import importlib, json, sys
names = sorted(n for n in sys.builtin_module_names if n.split(".")[0] == "statsmodels")
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
def test_statsmodels_modules_are_builtin(guest, which) -> None:
    """Each of statsmodels' 26 extension modules is a builtin that imports under its dotted name;
    the four whose init functions are renamed are among them (Decisions 5 and 8). They run apart
    from the other packages' dotted builtins (test_v1_1_artifact_set), as scikit-learn's do."""
    got = _sklearn(guest, which, SM_BUILTINS)
    assert len(got["names"]) == SM_MODULES, got["names"]
    assert set(SM_RENAMED) <= set(got["names"]), got["names"]
    assert got["wrong"] == [], got["wrong"]


# pdfplumber and pdfminer.six. A one-page PDF, and the same page encrypted with AES-256 (revision
# 6), whose password check itself runs AES, are written in the program; no file is granted.
PDF_PAGES = """
import io, json, sys
import pdfplumber
from pdfminer.high_level import extract_text
out = {"files": [pdfplumber.__file__, sys.modules["pdfminer"].__file__],
       "cryptography": "cryptography" in sys.modules}

def pdf(objs, trailer=b""):
    data = bytearray(b"%PDF-1.7\\n")
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(data))
        data += b"%d 0 obj\\n" % i + o + b"\\nendobj\\n"
    xref = len(data)
    data += b"xref\\n0 %d\\n0000000000 65535 f \\n" % (len(objs) + 1)
    for o in offsets:
        data += b"%010d 00000 n \\n" % o
    tail = b"trailer\\n<< /Size %d /Root 1 0 R%s >>\\nstartxref\\n%d\\n%%%%EOF\\n"
    return bytes(data + tail % (len(objs) + 1, trailer, xref))

def zeros(n):
    return b"<" + b"00" * n + b">"

PAGE = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 100] >>"]
AES = (b"<< /Filter /Standard /V 5 /R 6 /Length 256 /P -4 /O " + zeros(48) + b" /U " + zeros(48)
       + b" /OE " + zeros(32) + b" /UE " + zeros(32) + b" /Perms " + zeros(16)
       + b" /CF << /StdCF << /CFM /AESV3 /AuthEvent /DocOpen /Length 32 >> >>"
       + b" /StmF /StdCF /StrF /StdCF >>")
locked = pdf(PAGE + [AES], b" /Encrypt 4 0 R /ID [" + zeros(16) + b" " + zeros(16) + b"]")
with pdfplumber.open(io.BytesIO(pdf(PAGE))) as p:
    page = p.pages[0]
    out["plain"] = [len(p.pages), page.width, page.height]
    try:
        page.to_image()
    except Exception as e:
        out["to_image"] = [type(e).__name__, getattr(e, "name", None)]
out["cryptography after a plain file"] = "cryptography" in sys.modules
try:
    pdfplumber.open(io.BytesIO(locked))
except Exception as e:
    cause = e.args[0] if e.args else None
    out["aes"] = [type(e).__name__, type(cause).__name__, getattr(cause, "name", None)]
try:
    extract_text(io.BytesIO(locked))
except Exception as e:
    out["aes, pdfminer"] = [type(e).__name__, getattr(e, "name", None)]
print(json.dumps(out))
"""


@BINARY
def test_pdfplumber_needs_cryptography_only_for_aes(guest, artifacts, which) -> None:
    """pdfplumber and pdfminer.six import from the zip without cryptography, which the profile
    does not carry, and read a plain file; a file encrypted with AES raises ModuleNotFoundError
    naming it (pdfplumber wraps it in its PdfminerException), and a page image names pypdfium2,
    which is not carried either. The zip holds none of pdfminer's predefined CJK character maps.
    Without the carried patch `import pdfplumber` itself raises ModuleNotFoundError."""
    r = guest(which, ["-c", PDF_PAGES], root_writable=False)
    assert r.exit_code == 0, r.describe()
    got = json.loads(r.text)
    zip_path = "/usr/local/lib/python315.zip/"
    assert all(f.startswith(zip_path) for f in got.pop("files")), r.text
    assert got == {
        "cryptography": False,
        "plain": [1, 200, 100],
        "to_image": ["ModuleNotFoundError", "pypdfium2"],
        "cryptography after a plain file": False,
        "aes": ["PdfminerException", "ModuleNotFoundError", "cryptography"],
        "aes, pdfminer": ["ModuleNotFoundError", "cryptography"],
    }, got
    with zipfile.ZipFile(artifacts.path("python-stdlib.zip")) as z:
        assert not [n for n in z.namelist() if n.startswith("pdfminer/cmap/")]


# xarray reads a netCDF3 file on disk through scipy, which maps a file it is given by path; the
# guest has no mmap, so the limitations page names the two routes that read it.
NETCDF_FILE = """
import json, os
import numpy as np
import xarray as xr
os.makedirs("/work", exist_ok=True)
ds = xr.Dataset({"a": ("x", np.arange(3.0))}, coords={"x": [10.0, 20.0, 30.0]}, attrs={"t": "u"})
ds.to_netcdf("/work/a.nc")
out = {}
try:
    xr.open_dataset("/work/a.nc").load()
    out["by path"] = "read"
except OSError as e:
    out["by path"] = str(e)
with xr.open_dataset("/work/a.nc", mmap=False) as read:
    out["mmap=False"] = read.load().identical(ds)
with open("/work/a.nc", "rb") as f, xr.open_dataset(f) as read:
    out["an open file"] = read.load().identical(ds)
print(json.dumps(out))
"""


@BINARY
def test_xarray_reads_netcdf3_files_without_mmap(guest, which) -> None:
    """A netCDF3 file written to a folder reads back identical with `mmap=False`, and through an
    open file; opened by path alone it raises OSError naming mmap, which the guest lacks."""
    r = guest(which, ["-c", NETCDF_FILE])
    assert r.exit_code == 0, r.describe()
    assert json.loads(r.text) == {
        "by path": "mmap is unavailable on wasm32-wasi",
        "mmap=False": True,
        "an open file": True,
    }, r.text


# drawsvg's optional parts: rasterizing works through CairoSVG; the parts the set does not carry
# fail by name, as natively without them.
DRAWSVG_LACKS = """
import json, sys
import drawsvg as draw
out = {"files": sorted({m.__file__ for n, m in sys.modules.items() if n.startswith("drawsvg")})}
d = draw.Drawing(20, 20)
d.append(draw.Circle(10, 10, 5))
out["rasterize"] = d.rasterize().png_data[:8].hex()
try:
    import drawsvg.color
except ImportError as e:
    cause = e.__cause__
    out["color"] = [type(e).__name__, type(cause).__name__, getattr(cause, "name", None)]
try:
    d.embed_google_font("Permanent Marker", text="x")
except Exception as e:
    out["google font"] = [type(e).__name__, str(getattr(e, "reason", e))]
try:
    import drawsvg.widgets
except ImportError as e:
    out["widgets"] = [type(e).__name__, e.name]
print(json.dumps(out))
"""


@BINARY
def test_drawsvg_names_what_the_set_lacks(guest, which) -> None:
    """drawsvg imports from the zip and draws, and rasterizes to PNG through CairoSVG; what it
    cannot do here raises a named exception. The colour helpers need pwkit, not carried, so
    drawsvg raises its ImportError from the missing module's; a Google font raises URLError,
    since the guest has no ssl module, so no HTTPS handler, and no network; the widgets need
    ipywidgets."""
    r = guest(which, ["-c", DRAWSVG_LACKS])
    assert r.exit_code == 0, r.describe()
    got = json.loads(r.text)
    zip_path = "/usr/local/lib/python315.zip/"
    files = got.pop("files")
    assert files and all(f.startswith(zip_path) for f in files), r.text
    assert got == {
        "rasterize": "89504e470d0a1a0a",
        "color": ["ImportError", "ModuleNotFoundError", "pwkit"],
        "google font": ["URLError", "unknown url type: https"],
        "widgets": ["ModuleNotFoundError", "ipywidgets"],
    }, got


# plotly reads its validators' table, its datasets and plotly.js from the zip through one carried
# patch (the golden job shows the results equal native's); its JupyterLab extension and the
# widget's script stay out, so FigureWidget, which needs anywidget, fails as natively without it.
PLOTLY_ZIP = """
import json, sys, zipfile
import plotly, plotly.graph_objects as go
out = {"file": plotly.__file__}
try:
    go.FigureWidget()
except ImportError as e:
    out["FigureWidget"] = ["ImportError", "anywidget" in str(e)]
with zipfile.ZipFile("/usr/local/lib/python315.zip") as z:
    names = z.namelist()
out["left out"] = sorted(
    n for n in names if n.startswith("plotly/labextension/") or n.endswith("widgetbundle.js")
)
out["kept"] = sorted(
    n for n in ("plotly/validators/_validators.json", "plotly/package_data/plotly.min.js")
    if n in names
)
print(json.dumps(out))
"""


@BINARY
def test_plotly_reads_its_data_from_the_zip(guest, which) -> None:
    """plotly imports from the zip with its validators' table and plotly.js beside it, and without
    its notebook widget's parts, so FigureWidget raises ImportError naming anywidget."""
    r = guest(which, ["-c", PLOTLY_ZIP], root_writable=False)
    assert r.exit_code == 0, r.describe()
    got = json.loads(r.text)
    assert got.pop("file").startswith("/usr/local/lib/python315.zip/"), r.text
    assert got == {
        "FigureWidget": ["ImportError", True],
        "left out": [],
        "kept": ["plotly/package_data/plotly.min.js", "plotly/validators/_validators.json"],
    }, got
