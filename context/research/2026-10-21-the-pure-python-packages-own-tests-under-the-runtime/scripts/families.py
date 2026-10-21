"""The survey's 42 families: what each stages, how its tests are found, its transcribed
configuration, and its test-only extras (spec 067, Decisions 2, 5 and 6)."""

from pathlib import Path

TREES = Path(
    "/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/"
    "6c490d24-fe1d-441f-9d11-d529e2f0c242/scratchpad/067/trees"
)


def ini(*lines: str, markers: tuple[str, ...] = (), fw: tuple[str, ...] = ()) -> str:
    out = ["[pytest]", *lines]
    if markers:
        out += ["markers ="] + [f"    {m}" for m in markers]
    if fw:
        # pytest's own warning when the kit's hypothesis is imported before the session (the
        # driver loads the judge profile first), which an "error" filter would make fatal
        fw = (*fw, "ignore:Module already imported so cannot be rewritten"
                   ":pytest.PytestAssertRewriteWarning")
        out += ["filterwarnings ="] + [f"    {w}" for w in fw]
    return "\n".join(out) + "\n"


def tests_folders(fam: str, pkg_dir: str) -> list[str]:
    d = TREES / fam
    root = next(p for p in d.iterdir() if p.is_dir())
    out = []
    for p in sorted((root / pkg_dir).rglob("tests")):
        rel = p.relative_to(root)
        if p.is_dir() and "tests" not in rel.parts[:-1]:
            out.append(rel.as_posix())
    return out


def pp_for(folders: list[str], top: str) -> dict[str, str]:
    """package_paths: the package itself and every ancestor package of each tests folder (the
    staged folder is appended to that package's __path__)."""
    pp = {top.replace("/", "."): top}
    for fo in folders:
        parts = fo.split("/")[:-1]
        for i in range(1, len(parts) + 1):
            pp[".".join(parts[:i])] = "/".join(parts[:i])
    return pp


FAMILIES: dict[str, dict] = {}


def top(fam, stage, *, esp=(".",), **kw):
    FAMILIES[fam] = dict(stage=list(stage), esp=list(esp), **kw)


def inpkg(fam, pkg_dir, *, extra_stage=(), folders=None, **kw):
    folders = folders if folders is not None else tests_folders(fam, pkg_dir)
    FAMILIES[fam] = dict(stage=[*folders, *extra_stage], pp=pp_for(folders, pkg_dir),
                         esp=[], folders=folders, **kw)


# --- matplotlib's and pandas' seven ---------------------------------------------------------
top("fonttools", ["Tests"], ini=ini(
    "python_files = *_test.py", "python_classes = *Test Test*",
    "doctest_optionflags = ALLOW_UNICODE ELLIPSIS",
    markers=("slow: marks tests as slow",),
    fw=("ignore:readPlist:DeprecationWarning:plistlib_test",
        "ignore:writePlist:DeprecationWarning:plistlib_test",
        "ignore:some_function:DeprecationWarning:fontTools.ufoLib.utils",
        "ignore::DeprecationWarning:fontTools.varLib.designspace")))
top("pyparsing", ["tests", "examples"], ini=ini())
top("cycler", ["test_cycler.py"], ini=ini())
top("packaging", ["tests"], ini=ini("xfail_strict = true", "log_level = INFO",
                                    markers=("property: property-based tests (opt-in)",),
                                    fw=("error",)), extras=["pretend"])
top("python-dateutil", ["tests", "docs/exercises/solutions"], ini=ini(
    "python_files = test_*.py *_test.py *_solution.py", "xfail_strict = true",
    markers=("gettz", "import_star", "isoparser", "parserinfo", "rrule", "rruleset", "rrulestr",
             "smoke", "tz_resolve_imaginary", "tzfile", "tzlocal", "tzoffset", "tzstr",
             "no_cover: pytest-cov's marker, which the conftest adds"),
    fw=("error", "error::DeprecationWarning", "error::PendingDeprecationWarning")),
    extras=["freezegun"])
top("six", ["test_six.py"], ini=ini())
top("tzdata", ["tests", "VERSION"], ini=ini())
# --- tier A -----------------------------------------------------------------------------------
inpkg("openpyxl", "openpyxl", extra_stage=["conftest.py"], ini=ini(
    "python_files = test_*.py",
    markers=("pil_required: PIL required to run test",
             "pil_not_installed: Run test only if PIL is not installed",
             "not_py33: Do not run test on Python 3.", "lxml_required: lxml required",
             "defusedxml_required: defusedxml required", "lxml_buffering: lxml >= 3.4.0",
             "no_lxml: do not use lxml", "pandas_required: Pandas required",
             "numpy_required: Numpy required", "defusedxml_not_installed: x",
             "lxml_not_installed: x"),
    fw=("error", "ignore::FutureWarning", "ignore::pytest.PytestUnraisableExceptionWarning",
        "ignore::UserWarning", "ignore::DeprecationWarning")))
inpkg("et-xmlfile", "et_xmlfile", folders=["et_xmlfile/tests"], ini=ini("norecursedirs = et_xmlfile/tests/_vendor"))
inpkg("xlsxwriter", "xlsxwriter", tree="xlsxwriter", folders=["xlsxwriter/test"],
      cwd="/tmp/work", cwd_folders=["xlsxwriter/test/comparison/xlsx_files",
                                    "xlsxwriter/test/comparison/images"], ini=ini())
top("xlrd", ["tests"], ini=ini())
top("pypdf", ["tests", "resources"], stage_from=[("sample-files", "pypdf-samples", ".")],
    ini=ini(markers=("slow: Test which require more than a second",
                     "samples: Tests which use files from sample-files",
                     "enable_socket: Tests which need to download files",
                     "timeout: pytest-timeout's marker (a clock; not run)"), fw=("error",)),
    args=["-m", "not enable_socket"])
inpkg("beautifulsoup4", "bs4", folders=["bs4/tests"], ini=ini())
top("soupsieve", ["tests"], ini=ini(fw=("ignore:The 'strip_cdata':DeprecationWarning",)))
inpkg("html5lib", "html5lib", folders=["html5lib/tests"], extra_stage=[".pytest.expect"],
      ini=ini("xfail_strict = true", markers=(
          "DOM: x", "ElementTree: x", "cElementTree: x", "lxml: x", "genshi: x", "parser: x",
          "namespaced: x", "treewalker: x")),
      extras=["setuptools", "pytest-expect", "u-msgpack-python", "mock"],
      args=["-p", "pytest_expect.expect", "-W", "ignore::pytest.PytestRemovedIn9Warning"])
top("webencodings", ["tests"], ini=ini())
top("defusedxml", ["tests.py", "xmltestdata"], ini=ini("python_files = tests.py"))
top("xmltodict", ["tests"], ini=ini())
top("pyyaml", ["tests/legacy_tests"], esp=["tests/legacy_tests"], ini=ini())
top("tomli-w", ["tests", "benchmark"], ini=ini("xfail_strict = true"), extras=["tomli"])
top("jinja2", ["tests"], ini=ini(fw=("error",)),
    extras=[])
top("markupsafe", ["tests"], ini=ini(markers=("thread_unsafe: x",), fw=("error",)))
top("tabulate", ["test"], esp=["test"], ini=ini())
top("charset-normalizer", ["tests", "data"], ini=ini("log_level = DEBUG", fw=("error",)))
inpkg("networkx", "networkx", extra_stage=["networkx/conftest.py"], ini=ini(
    markers=("slow: slow",), fw=("error",)))
inpkg("patsy", "patsy", folders=[], extra_stage=[
    "patsy/test_build.py", "patsy/test_highlevel.py", "patsy/test_regressions.py",
    "patsy/test_splines_bs_data.py", "patsy/test_splines_crs_data.py", "patsy/test_state.py"],
    ini=ini("python_files = *.py"))
FAMILIES["patsy"]["pp"] = {"patsy": "patsy"}
FAMILIES["patsy"]["judge_files"] = {
    "patsy_inline.py": (Path(__file__).parent / "patsy_inline.py").read_text()}
inpkg("sympy", "sympy", extra_stage=["sympy/conftest.py", "doc/src"], ini=ini(
    "doctest_optionflags = NORMALIZE_WHITESPACE IGNORE_EXCEPTION_DETAIL ELLIPSIS FLOAT_CMP",
    markers=("nocache_fail", "tooslow", "slow"),
    fw=("ignore:More than 20 figures have been opened.*:RuntimeWarning",
        "ignore:FigureCanvasAgg is non-interactive, and thus cannot be shown:UserWarning")),
    extras=["pytest-doctestplus"])
inpkg("mpmath", "mpmath", folders=["mpmath/tests"], ini=ini(
    "doctest_optionflags = IGNORE_EXCEPTION_DETAIL", markers=("slow: x",)))
top("attrs", ["tests"], ini=ini("xfail_strict = true",
                                fw=("once::Warning", "ignore:::pympler[.*]")),
    extras=["pympler"])
top("more-itertools", ["tests"], ini=ini())
inpkg("toolz", "toolz", folders=["toolz/tests", "toolz/sandbox/tests"], ini=ini(
    "xfail_strict = true", "log_cli_level = info",
    fw=("error", "ignore:The toolz.compatibility module is no longer needed:DeprecationWarning:")))
top("tqdm", ["tests"], ini=ini("python_files = tests_*.py", "log_level = INFO",
                               "asyncio_mode = strict",
                               "asyncio_default_fixture_loop_scope = function",
                               markers=("slow",), fw=("error",)),
    extras=["pytest-asyncio"])
top("typing-extensions", ["src/test_typing_extensions.py", "src/_typed_dict_test_helper.py"],
    esp=["src"], ini=ini())
inpkg("joblib", "joblib", folders=["joblib/test"], extra_stage=["doc"], ini=ini(
    "doctest_optionflags = NORMALIZE_WHITESPACE ELLIPSIS", markers=("timeout: pytest-timeout's marker (a clock; not run)",
             "thread_unsafe: pytest-run-parallel's marker")))
top("cloudpickle", ["tests"], esp=[".", "tests/cloudpickle_testpkg"], ini=ini())
top("threadpoolctl", ["tests", "conftest.py"], ini=ini())
top("narwhals", ["tests"], ini=ini(
    "xfail_strict = true", markers=("slow: marks tests as slow",),
    fw=("error",)), env={"MODIN_ENGINE": "python", "PYARROW_IGNORE_TIMEZONE": "1", "TZ": "UTC"},
    args=["--constructors=pandas,pandas[nullable]"])
# --- 042's two, 045's three -------------------------------------------------------------------
top("seaborn", ["tests"], ini=ini(fw=(
    "ignore:The --rsyncdir command line argument:DeprecationWarning",
    "ignore:datetime.datetime.utcfromtimestamp\\(\\) is deprecated:DeprecationWarning")))
top("reportlab", ["tests"], cwd="/tmp/work", ini=ini())
top("formulaic", ["tests"], ini=ini())
top("interface-meta", ["tests"], ini=ini())
top("wrapt", ["tests/conftest.py", "tests/core"], esp=["tests/core"], ini=ini(), env={"WRAPT_DISABLE_EXTENSIONS": "1"})

# Survey-only stage edits and settings found by the first pass (each named in the memo).
FAMILIES["pypdf"]["edits"] = [
    ("tests/__init__.py", "import ssl\n", ""),
    ("tests/__init__.py", "    ssl._create_default_https_context = cast(",
     "    import ssl\n\n    ssl._create_default_https_context = cast("),
]
FAMILIES["reportlab"]["env"] = {"RL_TEST_OUTDIR": "/tmp/work/rl-out"}
FAMILIES["reportlab"]["args"] = ["--ignore=/upstream-reportlab/tree/tests/charts-out"]
