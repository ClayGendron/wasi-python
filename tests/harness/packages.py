"""The packages' own tests, each package its own family.

A `driver = "package"` configuration (`tests/upstream/<package>.toml`) has its own grant
(`/upstream-<package>`), its own stage, its own copy of the kit and its own fuel budget, so no
package's tests can move another's fuel. Its groups run through
`tests/upstream/package_drive.py`, which keeps `drive.py`'s stream and adds three lines: `R skipped
<collector>` for a file that skips itself whole, `D <node id>` for an item lxml's own runner would
not run (or that a family's marker expression deselects, where it names a reason), and `K <n>`,
the file's collected count before a split's `-k` deselects.

A family whose tests come from a test source (`test_source = true`: a pure-Python package, whose
pinned wheel or sdist the zip takes, and whose tests come from its sdist or its release tag's
archive) is tied to the bytes that ship at staging: the test source's pin equals the artifact's
MANIFEST, its tree is the pinned archive with exactly its recorded patches, and every file of the
package's pinned wheel is the same file in the test source (`tie_skips` names any it lacks, with a
reason). Such a family may name test-only wheels (`kit_extra`), test-side stand-ins for modules a
test file imports that have no build here (`test_stand_ins`, into its kit), folders copied into the
working folder (`cwd_folders`), environment variables (`env`, from a per-family list), flags set on
`sys` before the package is imported (`sys_flags`), and groups that run items rather than paths: the
docstrings of modules or of whole packages, doctest files, and a module's own `test_*` functions.

numpy's and pandas' configurations, `drive.py` and their guard are untouched: this module reads
only `driver = "package"` configurations.

Four keys serve the packages whose tests live in one `tests` folder per subpackage (scipy,
scikit-learn, statsmodels):

- `package_inits`: the stage also holds each staged folder's ancestor `__init__.py`, so pytest
  names `scipy/linalg/tests/test_basic.py` `scipy.linalg.tests.test_basic` and never confuses two
  `tests.test_basic` modules. `package_paths` is generated from the folders. The staged inits are
  never run: the driver imports every ancestor from the product's zip before pytest starts, and a
  module loaded from a staged `__init__.py` is a finding of the guard.
- `derived`: test data the package's build makes from its own sdist (scipy's `.npz` tables), made
  in the guest from staged members before the stage is sealed, each output checked on the host as
  data before it is staged. Its facts are recorded on the one group `derived_row` names.
- `env`: variables the harness adds to the guest's environment for every run of the family, each
  allowed by name per family (`ENV_ALLOWED`) and with its reason in the TOML.
- `smoke_cover`: for a smoke family, the cover of each compiled subpackage of the package: a smoke
  path, a golden job line that calls it, or `release-only` with the reason.

A release group may carry `clock_step_ns` (with `clock_reason`): its guest's clock advances that
much per read, for a test that repeats a call until a fixed time has passed. Such a group must
run exactly one test, so a changed clock never reaches ordinary tests unnoticed.
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import stat
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from harness import litter, paths, upstream

DRIVER = "package_drive.py"
# numpy's and pandas' keys, with their meaning there: never in a package TOML (Decision 14)
REFUSED = ("path_packages", "support")
WORK = "/tmp/work"  # the writable working folder, in the guest's root
# The variables a family's `env` may set, by family: each joins only by a judge change with its
# reason. scipy's runs its very slow cases in whichever tier their file is in; scikit-learn's runs
# its float32 cases and fixes the global seed its package setup would otherwise draw;
# reportlab's tests write their output where RL_TEST_OUTDIR says (its runAll.py otherwise
# writes beside them), and narwhals' configuration sets three through pytest-env.
ENV_ALLOWED = {
    "scipy": ("SCIPY_XSLOW",),
    "scikit-learn": ("SKLEARN_RUN_FLOAT32_TESTS", "SKLEARN_SEED"),
    "reportlab": ("RL_TEST_OUTDIR",),
    "narwhals": ("MODIN_ENGINE", "PYARROW_IGNORE_TIMEZONE", "TZ"),
}
# Never set by a family: the judge's own environment, the interpreter's (any PYTHON* name),
# scipy's hypothesis profile (its conftest loads its own derandomized one), and scikit-learn's
# seed sweep and network switch (a mode, and the sandbox's network).
ENV_FORBIDDEN = (
    "TMPDIR",
    "HOME",
    "SCIPY_HYPOTHESIS_PROFILE",
    "SKLEARN_TESTS_GLOBAL_RANDOM_SEED",
    "SKLEARN_SKIP_NETWORK_TESTS",
)
CLOCK_STEP_RANGE = (1_000, 1_000_000)  # 1 us to 1 ms per clock read
# A derived output's largest size: twice the largest one measured (scipy's boost.npz, 1,270,643
# bytes), so a run that writes something else entirely is refused before it is staged.
DERIVED_MAX_BYTES = 2_541_286
DERIVED_DIR = "/tmp/derived"  # where a derived script writes, in its own fresh root
# The compiled subpackages (and the patched pure paths) whose smoke cover must be a smoke path,
# never a golden line alone and never release-only: what an edit to the package's build or its
# carried patches most often breaks.
SMOKE_ONLY = {
    "scipy": (
        "scipy.special",
        "scipy.sparse",
        "scipy.spatial",
        "scipy.optimize._highspy",
        "scipy.linalg",
        "scipy._lib._uarray",
        "scipy.io._fast_matrix_market",
        "scipy.stats",
    ),
    "scikit-learn": ("sklearn.tree", "sklearn.utils._repr_html"),
    "statsmodels": (
        "statsmodels.regression",
        "statsmodels.datasets",
        "statsmodels.nonparametric",
        "statsmodels.tsa.stl",
    ),
}
RELEASE_ONLY = "release-only: "
# A golden job line that stands in for a smoke file: the job, the line, and a word on that line
JOB_COVER = re.compile(r"job (tests/jobs/[\w.]+\.py):(\d+) (\S+)")
KIT_EXTRA = paths.REPO / "tests" / "upstream" / "kit-extra.txt"
# A family's test-side stand-ins: the folder that holds them, relative to the repository.
STAND_INS = "tests/upstream/stand-ins"
NONE = "none"  # an empty folder of the stage's judge folder: what an item group collects
# The flags a family may set on `sys` before its package is imported: sympy's conftest sets
# `_running_pytest` as its first statement, so its test helpers turn its decorators into pytest's
# marks; the driver imports sympy earlier (its package paths), so it sets the flag first.
SYS_FLAGS = ("_running_pytest",)
# The steps a family may run once before its first doctest, and the doctest runner and output
# checker it may run its examples with, each upstream's own: sympy's runner prints with ASCII
# pretty forms, no line wrapping and its hash-stable printer as the display hook (which the
# stdlib's runner would reset for each example), compares numbers its own way, and its examples
# are written for that.
DOCTEST_SETUPS = ("sympy.testing.runtests:setup_pprint",)
DOCTEST_RUNNERS = ("sympy.testing.runtests:SymPyDocTestRunner",)
DOCTEST_CHECKERS = ("sympy.testing.runtests:SymPyOutputChecker",)
ITEM_KEYS = ("docstring_modules", "docstring_packages", "doctest_files", "module_functions")
# The wheel tie's places for a wheel's file in a source tree: as is, or under a source folder.
SOURCE_ROOTS = ("", "src/", "lib/", "Lib/")


@dataclass(frozen=True)
class Items:
    """What an item group runs instead of test paths: the docstrings of modules (or of every
    module a package ships, less those named not selected), doctest files with their flags, and
    the `test_*` functions of modules the product ships."""

    docstring_modules: tuple[str, ...] = ()
    docstring_packages: tuple[str, ...] = ()
    docstring_not_selected: tuple[str, ...] = ()
    doctest_files: tuple[tuple[str, int], ...] = ()
    module_functions: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(
            self.docstring_modules
            or self.docstring_packages
            or self.doctest_files
            or self.module_functions
        )


def items_of(g: dict) -> Items:
    return Items(
        docstring_modules=tuple(g.get("docstring_modules", [])),
        docstring_packages=tuple(g.get("docstring_packages", [])),
        docstring_not_selected=tuple(g.get("docstring_not_selected", [])),
        doctest_files=tuple((f, int(flags)) for f, flags in g.get("doctest_files", [])),
        module_functions=tuple(g.get("module_functions", [])),
    )


@dataclass(frozen=True)
class Split:
    """One file too big for one group, split by construction: group i runs
    `-k "(e_i) and not (e_1 or ... or e_{i-1})"`, the last `-k "not (e_1 or ... or e_{n-1})"`."""

    file: str
    groups: tuple[str, ...]
    keywords: tuple[str, ...]

    def keyword(self, group: str) -> str:
        i = self.groups.index(group)
        earlier = " or ".join(f"({k})" for k in self.keywords[:i])
        if i == len(self.groups) - 1:
            return f"not ({earlier})"
        mine = f"({self.keywords[i]})"
        return f"{mine} and not ({earlier})" if earlier else mine


@dataclass(frozen=True)
class Derived:
    """One file the package's build makes for its tests: `script args... -o DERIVED_DIR` writes
    `output`'s name there, from the staged `inputs` folder."""

    script: str
    args: tuple[str, ...]
    inputs: str
    output: str
    measured: int | None
    fuel: int

    @property
    def name(self) -> str:
        return PurePosixPath(self.output).name


@dataclass(frozen=True)
class PackageKeys:
    budget: int
    stage_folders: tuple[str, ...]
    support_files: tuple[str, ...] = ()
    package_paths: dict[str, str] = field(default_factory=dict)
    package_inits: object = False  # a boolean in a well-formed TOML
    init_files: tuple[str, ...] = ()  # the staged ancestors' __init__.py, never run
    listed_paths: bool = False  # the TOML lists package_paths beside package_inits
    derived: tuple[Derived, ...] = ()
    derived_row: str = ""
    env: dict[str, str] = field(default_factory=dict)
    env_reasons: dict[str, str] = field(default_factory=dict)
    group_env: tuple[str, ...] = ()  # groups that carry `env`, which only a family may
    clock_steps: dict[str, tuple[int, str]] = field(default_factory=dict)
    smoke_cover: dict[str, str] = field(default_factory=dict)
    extra_sys_path: tuple[str, ...] = ()
    support_packages: tuple[str, ...] = ()
    cwd: str = WORK
    cwd_files: tuple[str, ...] = ()
    splits: tuple[Split, ...] = ()
    keep_from_test_suite: bool = False  # lxml: run only what each module's test_suite() runs
    doctest_files: tuple[tuple[str, int], ...] = ()
    doctest_preimport: tuple[str, ...] = ()
    docstring_modules: tuple[str, ...] = ()
    docstring_not_selected: tuple[str, ...] = ()  # e.g. lxml.cssselect: cssselect is not shipped
    measured: dict[str, int] = field(default_factory=dict)  # each group's recorded fuel
    refused: tuple[str, ...] = ()  # keys a package TOML may not carry (path_packages, support)
    # A test-source family (see the module's docstring)
    test_source: bool = False
    wheel: str = ""  # the product's pinned wheel, which the tie compares with the test source
    tie_skips: dict[str, str] = field(default_factory=dict)  # a wheel file the source lacks: why
    extra_sources: dict[str, str] = field(default_factory=dict)  # stage folder -> component
    kit_extra: tuple[str, ...] = ()
    test_stand_ins: dict[str, str] = field(default_factory=dict)  # module -> its stand-in file
    cwd_folders: tuple[str, ...] = ()
    sys_flags: tuple[str, ...] = ()
    doctest_setup: tuple[str, ...] = ()  # module:function, run once before the first example
    doctest_runner: str = ""  # module:class, upstream's doctest runner; the stdlib's if empty
    doctest_checker: str = ""  # module:class, upstream's output checker; the stdlib's if empty
    docstring_flags: int = 0  # the doctest option flags upstream's runner gives docstrings
    python_files: tuple[str, ...] = ()  # upstream's test-file patterns, from the family's .ini
    deselect_reason: str = ""  # why the family's marker deselects what it does (D lines)
    opt_in_skips: tuple[str, ...] = ()  # the skip reasons of upstream's opt-ins: never in a smoke
    items: dict[str, Items] = field(default_factory=dict)  # an item group's items

    def split_of(self, group: str) -> Split | None:
        return next((s for s in self.splits if group in s.groups), None)


def ancestors(folders: tuple[str, ...]) -> dict[str, str]:
    """Every proper ancestor folder of each staged folder, by its dotted package name."""
    out: dict[str, str] = {}
    for f in folders:
        parts = PurePosixPath(f).parts
        for i in range(1, len(parts)):
            out[".".join(parts[:i])] = "/".join(parts[:i])
    return dict(sorted(out.items()))


def _derived(raw: dict) -> tuple[Derived, ...]:
    return tuple(
        Derived(
            d["script"],
            tuple(d.get("args", [])),
            d["inputs"],
            d["output"],
            None if d.get("measured") is None else int(d["measured"]),
            int(d["fuel"]),
        )
        for d in raw.get("derived", [])
    )


def _env(raw: dict) -> tuple[dict[str, str], dict[str, str]]:
    """A family's variables and their reasons: `[env.NAME]` with `value` and `reason`."""
    env = raw.get("env", {})
    value = {k: str(v.get("value", "")) if isinstance(v, dict) else str(v) for k, v in env.items()}
    reason = {k: str(v.get("reason", "")) if isinstance(v, dict) else "" for k, v in env.items()}
    return value, reason


def ini_python_files(text: str) -> tuple[str, ...]:
    """The `python_files` patterns of a pytest `.ini`, or none."""
    import configparser

    c = configparser.ConfigParser(interpolation=None)
    c.read_string(text)
    if not c.has_option("pytest", "python_files"):
        return ()
    return tuple(c.get("pytest", "python_files").split())


def load(raw: dict, directory: Path | None = None) -> upstream.Config:
    ini = (directory or upstream.HERE) / f"{raw['package']}.ini"
    inits = raw.get("package_inits", False)
    folders = tuple(raw["stage_folders"])
    generated = ancestors(folders) if inits is True else {}
    env, env_reasons = _env(raw)
    groups = raw.get("groups", {})
    keys = PackageKeys(
        budget=int(raw["budget"]),
        stage_folders=folders,
        support_files=tuple(raw.get("support_files", [])),
        package_paths={**generated, **dict(raw.get("package_paths", {}))},
        package_inits=inits,
        init_files=tuple(f"{folder}/__init__.py" for folder in generated.values()),
        listed_paths=bool(raw.get("package_paths")) and inits is True,
        derived=_derived(raw),
        derived_row=raw.get("derived_row", ""),
        env=env,
        env_reasons=env_reasons,
        group_env=tuple(n for n, g in groups.items() if "env" in g),
        clock_steps={
            n: (int(g["clock_step_ns"]), str(g.get("clock_reason", "")))
            for n, g in groups.items()
            if "clock_step_ns" in g
        },
        smoke_cover=dict(raw.get("smoke_cover", {})),
        extra_sys_path=tuple(raw.get("extra_sys_path", [])),
        support_packages=tuple(raw.get("support_packages", [])),
        cwd=raw.get("cwd", WORK),
        cwd_files=tuple(raw.get("cwd_files", [])),
        splits=tuple(
            Split(s["file"], tuple(s["groups"]), tuple(s["keywords"])) for s in raw.get("split", [])
        ),
        keep_from_test_suite=bool(raw.get("keep_from_test_suite", False)),
        doctest_files=tuple((f, int(flags)) for f, flags in raw.get("doctest_files", [])),
        doctest_preimport=tuple(raw.get("doctest_preimport", [])),
        docstring_modules=tuple(raw.get("docstring_modules", [])),
        docstring_not_selected=tuple(raw.get("docstring_not_selected", [])),
        measured={
            n: int(g["measured"]) for n, g in raw.get("groups", {}).items() if "measured" in g
        },
        refused=tuple(k for k in REFUSED if k in raw),
        test_source=bool(raw.get("test_source", False)),
        wheel=raw.get("wheel", ""),
        tie_skips=dict(raw.get("tie_skips", {})),
        extra_sources=dict(raw.get("extra_sources", {})),
        kit_extra=tuple(raw.get("kit_extra", [])),
        test_stand_ins=dict(raw.get("test_stand_ins", {})),
        cwd_folders=tuple(raw.get("cwd_folders", [])),
        sys_flags=tuple(raw.get("sys_flags", [])),
        doctest_setup=tuple(raw.get("doctest_setup", [])),
        doctest_runner=raw.get("doctest_runner", ""),
        doctest_checker=raw.get("doctest_checker", ""),
        docstring_flags=int(raw.get("docstring_flags", 0)),
        python_files=ini_python_files(ini.read_text()) if ini.is_file() else (),
        deselect_reason=raw.get("deselect_reason", ""),
        opt_in_skips=tuple(raw.get("opt_in_skips", [])),
        items={n: items_of(g) for n, g in raw.get("groups", {}).items() if items_of(g)},
    )
    return upstream.Config(
        package=raw["package"],
        marker=raw.get("marker", ""),
        args=list(raw.get("args", [])),
        path_packages=[],
        markers=list(raw.get("markers", [])),
        support=[],
        groups={name: upstream.group_of(name, g) for name, g in raw.get("groups", {}).items()},
        not_selected=[
            upstream.NotSelected(tuple(n["files"]), n["reason"], n["closes_with"])
            for n in raw.get("not_selected", [])
        ],
        traps=[
            upstream.Trap(t["id"], t["node"], t["reason"], t["closes_with"], t.get("group", ""))
            for t in raw.get("trap", [])
        ],
        expected=[upstream.klass_of(e) for e in raw.get("expected", [])],
        grant=raw["grant"],
        driver="package",
        component=raw.get("component", ""),
        keys=keys,
        **upstream.tier_fields(raw),
    )


def tree_root(cfg: upstream.Config) -> str:
    return f"{cfg.grant}/tree"


def guest_cwd(cfg: upstream.Config) -> str:
    """`/tmp/work`, or the stage's tree root when the TOML says `cwd = "tree"`."""
    return tree_root(cfg) if cfg.keys.cwd == "tree" else cfg.keys.cwd


# ---------------------------------------------------------------------------------------------
# lxml: what each module's test_suite() runs

LOADERS = ("loadTestsFromTestCase", "makeSuite")


def test_suite_classes(source: str) -> list[str] | str | None:
    """The TestCase classes a module's test_suite() adds: their names, "*" when it loads the whole
    module (`loadTestsFromModule`), None when it has no test_suite()."""
    mod = ast.parse(source)
    fn = next(
        (n for n in mod.body if isinstance(n, ast.FunctionDef) and n.name == "test_suite"), None
    )
    if fn is None:
        return None
    names: set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in LOADERS and node.args and isinstance(node.args[0], ast.Name):
                names.add(node.args[0].id)
            elif node.func.attr == "loadTestsFromModule":
                return "*"
    return sorted(names)


def test_suite_doctests(source: str) -> tuple[list[str], int]:
    """The doctest files (basenames) a module's test_suite() names, and how many docstring suites
    (`DocTestSuite`) it adds."""
    mod = ast.parse(source)
    fn = next(
        (n for n in mod.body if isinstance(n, ast.FunctionDef) and n.name == "test_suite"), None
    )
    files: list[str] = []
    docstrings = 0
    for node in ast.walk(fn) if fn else []:
        if not isinstance(node, ast.Call):
            continue
        name = (
            node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
        )
        first = node.args[0] if node.args else None
        if name in ("make_doctest", "DocFileSuite") and isinstance(first, ast.Constant):
            files.append(PurePosixPath(str(first.value)).name)
        elif name == "DocTestSuite":
            docstrings += 1
    return files, docstrings


def keep_classes(cfg: upstream.Config, tree: Path) -> dict[str, list[str] | str]:
    """For each staged test module the groups run, the classes its test_suite() adds."""
    if not cfg.keys.keep_from_test_suite:
        return {}
    out: dict[str, list[str] | str] = {}
    out_files = {f for n in cfg.not_selected for f in n.files}
    for folder in cfg.keys.stage_folders:
        for p in sorted((tree / folder).glob("test_*.py")):
            rel = p.relative_to(tree).as_posix()
            if rel in out_files:
                continue
            got = test_suite_classes(p.read_text(encoding="utf-8"))
            if got is not None:
                out[rel] = got
    return out


# ---------------------------------------------------------------------------------------------
# Staging and the argv


def stage(cfg: upstream.Config, tree: Path, allowed: set[str], dest: Path) -> list[str]:
    """Copy the stage folders and the support files from `tree` to `dest/tree`, members (and
    files a recorded patch creates) only. Returns what was left out."""
    wanted: set[str] = set(cfg.keys.support_files) | {f for f, _ in cfg.keys.doctest_files}
    wanted |= set(cfg.keys.init_files)
    wanted |= {f for it in cfg.keys.items.values() for f, _ in it.doctest_files}
    left_out: list[str] = []
    for folder in cfg.keys.stage_folders:
        for p in sorted((tree / folder).rglob("*")):
            if p.is_dir():
                continue
            rel = p.relative_to(tree).as_posix()
            if rel in allowed:
                wanted.add(rel)
            elif not litter.unrecorded(rel):  # no fact holds litter or bytecode
                left_out.append(rel)
    for rel in sorted(wanted):
        if rel not in allowed or not (tree / rel).is_file():
            continue
        litter.refuse(rel, tree.name)  # the seal's cleanup must never meet it
        target = dest / "tree" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tree / rel, target)
    return sorted(left_out)


def group_args(cfg: upstream.Config, group: upstream.Group) -> list[str]:
    """pytest's selection for one group. The host makes every path absolute under the grant's tree
    and leaves every other argument as it is: a marker or an option's value is never a path.
    `--deselect` takes a node id, relative to the rootdir (the tree)."""
    root = tree_root(cfg) + "/"
    inside = [p if p.endswith(".py") else p + "/" for p in group.paths]
    mine = lambda f: any(f == p or f.startswith(p) for p in inside)  # noqa: E731
    out = [f for n in cfg.not_selected for f in n.files if mine(f.split("::", 1)[0])]
    ignores = [f for f in out if "::" not in f]  # a file
    deselects = [f for f in out if "::" in f]  # one test by node id (regex's test_main)
    deselects += [t.node for t in cfg.traps if "::" in t.node and mine(t.node)]
    from harness import tiers

    ignores += tiers.smoke_ignores(cfg, group)
    deselects += tiers.node_deselects(cfg, group)

    marker = tiers.marker_of(cfg, group)
    args = ["-m", marker] if marker else []
    # an item group collects no path: the stage's empty folder, so no conftest is loaded and
    # pytest collects nothing but the items the driver adds; the family's arguments shape what
    # pytest collects from test files, and an option only a conftest registers (networkx's
    # --runslow) is refused where none loads, so they go to path groups only
    shown = [root + p for p in group.paths] or [f"{cfg.grant}/judge/{NONE}"]
    args += [*(cfg.args if group.paths else []), *shown]
    args += [f"--ignore={root}{f}" for f in dict.fromkeys(ignores)]
    args += [f"--deselect={d}" for d in deselects]
    split = cfg.keys.split_of(group.name)
    k = tiers.keyword_arg(cfg, group, split.keyword(group.name) if split is not None else None)
    if k is not None:
        args.append(f"-k{k}")
    return args


def group_spec(
    cfg: upstream.Config,
    group: upstream.Group,
    keep: dict,
    top_names: list[str],
    modules: list[str] | None = None,
) -> dict:
    k = cfg.keys
    spec = {
        "markers": cfg.markers,
        "args": group_args(cfg, group),
        "package_paths": k.package_paths,
        "extra_sys_path": list(k.extra_sys_path),
        "cwd": guest_cwd(cfg),
        "keep_classes": keep or None,
        "doctest_files": [[f, flags] for f, flags in k.doctest_files],
        "doctest_preimport": list(k.doctest_preimport),
        "docstring_modules": list(k.docstring_modules),
        "top_names": top_names,
        "split": cfg.keys.split_of(group.name) is not None,
    }
    if not k.test_source:
        return spec  # the compiled packages' groups: their JSON byte for byte as before
    items = k.items.get(group.name, Items())
    spec.update(
        doctest_files=[[f, flags] for f, flags in items.doctest_files],
        docstring_modules=docstring_list(items, modules or []),
        docstring_flags=k.docstring_flags,
        module_functions=list(items.module_functions),
        sys_flags=list(k.sys_flags),
        doctest_setup=list(k.doctest_setup),
        doctest_runner=k.doctest_runner,
        doctest_checker=k.doctest_checker,
        reload_profile=True,
        mark_deselected=True,
    )
    return spec


def docstring_list(items: Items, modules: list[str]) -> list[str]:
    """An item group's docstring modules: those it names, then every module the product ships of
    each package it names, in sorted order, less its not-selected entries and any tests folder
    (a package's tests run from the test source, by path)."""
    out = list(items.docstring_modules)
    for pkg in items.docstring_packages:
        for m in modules:
            if (m == pkg or m.startswith(pkg + ".")) and m not in out:
                parts = m.split(".")
                if "tests" in parts or "conftest" in parts:
                    continue
                if any(m == n or m.startswith(n + ".") for n in items.docstring_not_selected):
                    continue
                out.append(m)
    return out


def zip_modules(stdlib: Path) -> list[str]:
    """Every module the zip holds, by its dotted name, sorted."""
    out = set()
    with zipfile.ZipFile(stdlib) as z:
        for n in z.namelist():
            if not n.endswith((".pyc", ".py")):
                continue
            parts = n.rsplit(".", 1)[0].split("/")
            if parts[-1] == "__init__":
                parts = parts[:-1]
            if parts and all(p.isidentifier() for p in parts):
                out.add(".".join(parts))
    return sorted(out)


def zip_top_names(stdlib: Path) -> list[str]:
    with zipfile.ZipFile(stdlib) as z:
        return sorted({n.split("/")[0].removesuffix(".pyc") for n in z.namelist() if n.strip("/")})


# ---------------------------------------------------------------------------------------------
# A test source: the tie to the bytes that ship, the test-only extras, the stage's extras

EXTRA_LINE = re.compile(r"([0-9a-f]{64})  (https://files\.pythonhosted\.org/\S+/([^/\s]+))")
EXTRA_FILE = re.compile(
    r"([A-Za-z0-9_.-]+?)-(\d[\w.!+]*)(?:-(?:py3|py2\.py3)-none-any\.whl|\.tar\.gz)"
)


def extra_name(file: str) -> str:
    """A test-only distribution's name, as a family's `kit_extra` names it (normalized)."""
    m = EXTRA_FILE.fullmatch(file)
    return re.sub(r"[-_.]+", "-", m[1]).lower() if m else ""


def extra_entries(text: str) -> list[tuple[str, str, str]]:
    """(sha256, url, file) per line of kit-extra.txt; a line that does not parse is left out
    (extra_errors names it)."""
    out = []
    for line in text.splitlines():
        m = EXTRA_LINE.fullmatch(line.strip())
        if m:
            out.append((m[1], m[2], m[3]))
    return out


def extra_errors(text: str) -> list[str]:
    """kit-extra.txt's rules, as kit.txt's: each line a SHA-256 and a files.pythonhosted.org URL
    of a pure wheel, or of a pure sdist (a test-only plugin PyPI has no wheel for), one per name."""
    errors, seen = [], set()
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        m = EXTRA_LINE.fullmatch(line.strip())
        if m is None or not extra_name(m[3]):
            errors.append(f"kit-extra.txt:{n}: not a SHA-256 and a pure wheel's or sdist's URL")
            continue
        if extra_name(m[3]) in seen:
            errors.append(f"kit-extra.txt:{n}: {extra_name(m[3])} is listed twice")
        seen.add(extra_name(m[3]))
    return errors


def unpack_extra(path: Path, dest: Path) -> None:
    """A test-only wheel unzipped into the kit, as the kit's own are; a pure sdist's package
    folders copied there (its top folder's subfolders with an __init__.py)."""
    if path.name.endswith(".whl"):
        upstream.safe_unzip(path, dest)
        return
    import tarfile

    with tarfile.open(path) as t:
        tmp = Path(tempfile.mkdtemp(prefix="extra-", dir=paths.HARNESS_TMP))
        try:
            t.extractall(tmp, filter="data")
            for top in tmp.iterdir():
                for p in sorted(top.iterdir()):
                    if p.is_dir() and (p / "__init__.py").is_file():
                        shutil.copytree(p, dest / p.name)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def source_top(tarball: Path) -> str:
    from harness import pins

    return pins.top_dir(tarball)


def source_tie_errors(
    cfg: upstream.Config, manifest: paths.Manifest, tarball: Path, tree: Path
) -> list[str]:
    """Why a test source is not the one the artifact names: its pin is not MANIFEST's, its
    recorded patches are not MANIFEST's, or its tree is not the pinned archive with exactly
    those patches applied."""
    from harness import pins

    errors = []
    sha = paths.sha256_file(tarball)
    if manifest.pins.get(tarball.name) != sha:
        theirs = (manifest.pins.get(tarball.name) or "absent")[:12]
        errors.append(f"tests from {tarball.name} SHA-256 {sha[:12]}, MANIFEST's pin {theirs}")
    top = tree.name
    mine = upstream.repo_patches(top)
    prefix = f"recipes/patches/{top}/"
    recorded = {p: s for p, s in manifest.recipes.items() if p.startswith(prefix)}
    for p in sorted(set(recorded) | set(mine)):
        if recorded.get(p) != mine.get(p):
            errors.append(
                f"tests carry patch {p} {(mine.get(p) or 'absent')[:12]}, MANIFEST records "
                f"{(recorded.get(p) or 'absent')[:12]}"
            )
    twins = case_twins(upstream.tarball_members(tarball))
    errors += [
        f"{tree.name}: {d}"
        for d in pins.tree_drift(tarball, tree)
        if d.split(": ", 1)[0] not in twins
    ]
    return errors


def case_twins(members: set[str]) -> set[str]:
    """Members whose names differ only in case (reportlab's generated chart scripts): a
    case-insensitive file system holds each pair as one file, so the drift of either is the
    file system's, and the stage leaves them out (they are no test)."""
    seen: dict[str, list[str]] = {}
    for m in members:
        seen.setdefault(m.lower(), []).append(m)
    return {m for group in seen.values() if len(group) > 1 for m in group}


def wheel_tie_errors(
    cfg: upstream.Config, manifest: paths.Manifest, wheel: Path, tree: Path
) -> list[str]:
    """Every file the product's pinned wheel holds (less its metadata) is the same file in the
    test source, as is or under a source folder; a file the source lacks is named by `tie_skips`
    with its reason. The wheel's pin is MANIFEST's, and its version the test source's."""
    errors = []
    sha = paths.sha256_file(wheel)
    if manifest.pins.get(wheel.name) != sha:
        errors.append(f"the tie's wheel {wheel.name} is not MANIFEST's pin")
    version = wheel.name.split("-")[1]
    if version not in tree.name:
        errors.append(f"the test source {tree.name} is not version {version} of {wheel.name}")
    import hashlib

    with zipfile.ZipFile(wheel) as z:
        for info in z.infolist():
            name = info.filename
            first = name.split("/", 1)[0]
            if info.is_dir() or first.endswith((".dist-info", ".data")):
                continue
            want = hashlib.sha256(z.read(info)).hexdigest()
            found = [tree / (r + name) for r in SOURCE_ROOTS if (tree / (r + name)).is_file()]
            if not found:
                if name not in cfg.keys.tie_skips:
                    errors.append(f"{name}: the wheel ships it, the test source lacks it")
            elif not any(paths.sha256_file(f) == want for f in found):
                errors.append(f"{name}: the wheel's differs from the test source's")
    errors += [
        f"tie_skips names {n}, which the wheel does not ship"
        for n in cfg.keys.tie_skips
        if n not in z.namelist()
    ]
    return errors


def stage_extras(cfg: upstream.Config, root: Path) -> list[str]:
    """The family's other sources into the stage's tree (each checked as its own), its test-only
    extras into its kit, and the item groups' empty folder. The errors, or none."""
    from harness import pins

    errors = []
    d = paths.artifact_dir()
    manifest = paths.parse_manifest((d / "MANIFEST").read_text())
    for folder, component in cfg.keys.extra_sources.items():
        pair = pins.source_pair(component)
        if pair is None:
            errors.append(f"no source tree for {component}")
            continue
        errors += source_tie_errors(cfg, manifest, *pair)
        shutil.copytree(pair[1], root / "tree" / folder)
    entries = {extra_name(f): f for _, _, f in extra_entries(KIT_EXTRA.read_text())}
    for name in cfg.keys.kit_extra:
        if name not in entries:
            errors.append(f"kit_extra {name} is not in kit-extra.txt")
            continue
        unpack_extra(upstream.WHEELS / entries[name], root / "kit")
    errors += stand_in_errors(cfg, zip_top_names(d / "python-stdlib.zip"))
    if not errors:
        for module, rel in cfg.keys.test_stand_ins.items():
            shutil.copyfile(paths.REPO / rel, root / "kit" / f"{module}.py")
    (root / "judge" / NONE).mkdir(exist_ok=True)
    return errors


def stand_in_errors(cfg: upstream.Config, top_names: list[str]) -> list[str]:
    """A family's test-side stand-ins (`test_stand_ins`, a module a test file imports that has no
    build here) must each be `tests/upstream/stand-ins/<module>.py`, and name no module the
    product's zip carries, so a stand-in can never take the place of what ships."""
    errors = []
    for module, rel in cfg.keys.test_stand_ins.items():
        if rel != f"{STAND_INS}/{module}.py" or not (paths.REPO / rel).is_file():
            errors.append(f"test_stand_ins {module}: no {STAND_INS}/{module}.py")
        elif module in top_names:
            errors.append(f"test_stand_ins {module}: the product's zip carries {module}")
    return errors


def cwd_folder_files(cfg: upstream.Config, tree: Path) -> dict[str, bytes]:
    """The test source's folders the tests read and write by relative paths, copied into the
    working folder before the session."""
    out = {}
    for folder in cfg.keys.cwd_folders:
        for p in sorted((tree / folder).rglob("*")):
            if p.is_file():
                out[f"{WORK}/{p.relative_to(tree).as_posix()}"] = p.read_bytes()
    return out


# ---------------------------------------------------------------------------------------------
# The verdict: the shared judge, then this driver's guard and lines


@dataclass
class Extra:
    deselected: list[str] = field(default_factory=list)  # D lines
    collected: int | None = None  # K line


def parse_extra(text: str) -> Extra:
    e = Extra()
    for line in text.splitlines():
        kind, _, rest = line.partition(" ")
        if kind == "D":
            e.deselected.append(rest)
        elif kind == "K":
            try:
                e.collected = int(rest)
            except ValueError:
                e.collected = -1
    return e


def guard_findings(cfg: upstream.Config, modules: list[tuple[str, str]]) -> list[str]:
    """Path-based: a module loaded from the tree must lie under a staged
    folder; a module of the product's names reported from outside the zip is a finding."""
    root = tree_root(cfg) + "/"
    folders = [root + f.rstrip("/") + "/" for f in cfg.keys.stage_folders]
    files = {
        root + f for f in cfg.keys.support_files
    }  # e.g. Pillow's selftest.py, run by docstring
    findings = []
    for name, f in modules:
        if f.startswith(root):
            if not any(f.startswith(d) for d in folders) and f not in files:
                findings.append(f"a module came from outside the staged folders: {name} {f}")
        else:
            findings.append(f"a product module came from outside the zip: {name} {f}")
    return findings


def _added(listed, node: str) -> bool:
    """Whether a node of a module with a test_suite() is one it adds: a test of a class it names,
    or of any class when it loads the whole module ("*"); never a module-level function."""
    parts = node.split("::")
    if len(parts) < 3:
        return False
    return listed == "*" or parts[1] in listed


def keep_findings(extra: Extra, stream: upstream.Stream, keep: dict) -> list[str]:
    """lxml, exactly test_suite()'s tests: every class
    it names ran at least one test; every test that ran is one it adds; every item deselected is
    one it does not add (its own `test_suite` builder among them)."""
    if not keep:
        return []
    findings = []
    ran = list(stream.started)
    for f, classes in keep.items():
        if classes == "*":
            continue
        for c in classes:
            if not any(n.startswith(f"{f}::{c}::") for n in ran):
                findings.append(f"a class lxml's test_suite() runs ran nothing: {f}::{c}")
    for node in dict.fromkeys(n for _, n, _ in stream.outcomes):  # tests, not collectors
        listed = keep.get(node.split("::", 1)[0])
        if listed is not None and "::" in node and not _added(listed, node):
            findings.append(f"ran a test lxml's test_suite() does not add: {node}")
    for node in extra.deselected:
        listed = keep.get(node.split("::", 1)[0])
        if listed is not None and _added(listed, node):
            findings.append(f"deselected a test lxml's test_suite() runs: {node}")
    return findings


def judge(
    cfg: upstream.Config, group: str, text: str, run: upstream.GuestRun, keep: dict
) -> tuple[upstream.GroupOutcome, Extra]:
    stream = upstream.parse_stream(text)
    extra = parse_extra(text)
    modules, stream.modules = stream.modules, []  # this driver's guard, not drive.py's
    outcome = upstream.judge_group(stream, run, cfg.classes(group))
    outcome.findings += guard_findings(cfg, modules)
    outcome.findings += keep_findings(extra, stream, keep)
    if cfg.keys.split_of(group) is not None and extra.collected is None:
        outcome.findings.append("no K line: the split group's file was not collected")
    outcome.findings += smoke_findings(cfg, group, stream, extra)
    return outcome, extra


def clock_findings(cfg: upstream.Config, group: str, outcome: upstream.GroupOutcome) -> list[str]:
    """A group run with its own clock step runs one test: more outcomes than one mean the changed
    clock reaches other tests."""
    if group not in cfg.keys.clock_steps:
        return []
    n = sum(outcome.counts.values())
    if n == 1:
        return []
    return [f"a changed clock step reaches other tests: {n} outcomes in {group}, not one"]


def smoke_findings(cfg: upstream.Config, group: str, stream: upstream.Stream, extra: Extra) -> list:
    """A smoke group runs no test upstream runs only on request: none of its tests skips for the
    family's opt-in, and its marker deselects nothing unless the family names why (a capability
    the guest lacks, for every group alike)."""
    g = cfg.groups.get(group)
    if g is None or g.smoke is None or not cfg.keys.test_source:
        return []
    out = [
        f"a smoke test skips for an opt-in: {node} ({reason})"
        for outcome, node, reason in stream.outcomes
        if outcome == "skipped" and any(o in reason for o in cfg.keys.opt_in_skips)
    ]
    if not cfg.keys.deselect_reason:
        named = tuple(f for n in cfg.not_selected for f in n.files if "::" in f)  # by its reason
        out += [
            f"a smoke group deselected {node}"
            for node in extra.deselected
            if not node.startswith(named)
        ]
    return out


# ---------------------------------------------------------------------------------------------
# The session: one stage per family, one guest session per group


@dataclass
class PackageRun:
    outcome: upstream.GroupOutcome
    fuel: int
    left_out: list[str]
    collected: int | None
    derived: dict | None = None  # the derived run's facts, on the family's derived_row alone
    deselected: int = 0  # D lines: items the family's marker leaves out, for its named reason


def derived_output_errors(path: Path, name: str) -> list[str]:
    """Why a derived output may not be staged: read with lstat, never through a link, and opened
    as a zip on the host, as data; it holds at least one array (`.npy` member)."""
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return [f"derived {name}: the script wrote no file"]
    if not stat.S_ISREG(st.st_mode):
        return [f"derived {name}: the output is not a regular file (a link is never followed)"]
    if st.st_size > DERIVED_MAX_BYTES:
        return [f"derived {name}: {st.st_size:,} bytes, past the {DERIVED_MAX_BYTES:,} bound"]
    try:
        with zipfile.ZipFile(path) as z:
            arrays = [n for n in z.namelist() if n.endswith(".npy")]
    except (zipfile.BadZipFile, OSError) as e:
        return [f"derived {name}: not a zip archive ({e})"]
    if not arrays:
        return [f"derived {name}: the archive holds no array"]
    return []


def derived_findings(name: str, run) -> list[str]:
    """How a derived script's guest run ended, when it did not end well."""
    if run.trapped == "out of fuel":
        return [f"derived {name}: out of fuel at its cap"]
    if run.trapped:
        return [f"derived {name}: trap: {run.trap_cause or run.trapped}"]
    if run.exit_code != 0:
        return [f"derived {name}: the script exited {run.exit_code}"]
    return []


class Session:
    """Stages each family once per judge run, on first use, and runs each group once."""

    def __init__(self, workdir: Path, configs: dict[str, upstream.Config]) -> None:
        self.workdir = workdir
        self.configs = {p: c for p, c in configs.items() if c.driver == "package"}
        self.roots: dict[str, Path] = {}
        self.prepared: dict[str, str | tuple[list[str], dict]] = {}
        self.groups: dict[str, PackageRun] = {}
        self.derived: dict[str, dict] = {}  # each family's derived facts, by output

    def close(self) -> None:
        for root in self.roots.values():
            litter.remove(root)

    def prepare(self, package: str) -> tuple[list[str], dict]:
        if package not in self.prepared:
            self.prepared[package] = self._prepare(package)
        got = self.prepared[package]
        if isinstance(got, str):
            raise AssertionError(got)
        return got

    def _prepare(self, package: str) -> str | tuple[list[str], dict]:
        from harness import pins

        cfg = self.configs[package]
        pair = pins.source_pair(cfg.component or package)
        if pair is None:
            return f"no source tree for {package}"
        tarball, tree = pair
        d = paths.artifact_dir()
        manifest = paths.parse_manifest((d / "MANIFEST").read_text())
        patches = upstream.repo_patches(tree.name)
        if cfg.keys.test_source:
            errors = source_tie_errors(cfg, manifest, tarball, tree)
            if cfg.keys.wheel:
                wheel = paths.DOWNLOADS / cfg.keys.wheel
                if not wheel.is_file():
                    errors.append(f"no wheel {cfg.keys.wheel} in downloads/ for the tie")
                else:
                    errors += wheel_tie_errors(cfg, manifest, wheel, tree)
        else:
            errors = upstream.tie_errors(package, manifest, tarball, patches)
        if errors:
            return "the tests are not the artifact's: " + "; ".join(errors)
        allowed = upstream.tarball_members(tarball)
        for p in patches:
            allowed |= upstream.patch_created((paths.REPO / p).read_text())
        base = paths.HARNESS_TMP / f"upstream-{package}"
        base.mkdir(parents=True, exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix="run-", dir=base))
        self.roots[package] = root
        for _, _, name in upstream.kit_entries(upstream.KIT.read_text()):
            upstream.safe_unzip(upstream.WHEELS / name, root / "kit")
        judge_dir = root / "judge"
        judge_dir.mkdir()
        shutil.copyfile(upstream.HERE / DRIVER, judge_dir / DRIVER)
        shutil.copyfile(upstream.HERE / f"{package}.ini", judge_dir / f"{package}.ini")
        left_out = stage(cfg, tree, allowed, root)
        if cfg.keys.test_source:
            errors = stage_extras(cfg, root)
            if errors:
                return "the stage is not complete: " + "; ".join(errors)
        keep = keep_classes(cfg, root / "tree")
        top = zip_top_names(d / "python-stdlib.zip")
        modules = zip_modules(d / "python-stdlib.zip") if cfg.keys.test_source else None
        for g in cfg.groups.values():
            spec = group_spec(cfg, g, keep, top, modules)
            (judge_dir / f"{g.name}.json").write_text(json.dumps(spec, indent=1))
        for t in cfg.traps:
            spec = {**group_spec(cfg, cfg.groups[next(iter(cfg.groups))], keep, top)}
            # the node by the path the guest sees, as group_args names every group's paths
            spec["args"], spec["split"] = [*cfg.args, f"{tree_root(cfg)}/{t.node}"], False
            (judge_dir / f"{t.id}.json").write_text(json.dumps(spec, indent=1))
        errors = self._make_derived(package, root)
        if errors:
            return "the derived test data was not made: " + "; ".join(errors)
        litter.seal(root)  # read-only, once staged
        return left_out, keep

    def _make_derived(self, package: str, root: Path) -> list[str]:
        """Each derived output, made in the guest from the staged members (the grant read-only, a
        fresh writable root each), checked on the host as data, then copied into the stage."""
        from harness import guest

        cfg = self.configs[package]
        d = paths.artifact_dir()
        m = paths.parse_manifest((d / "MANIFEST").read_text())
        facts: dict[str, dict] = {}
        for entry in cfg.keys.derived:
            script = f"{tree_root(cfg)}/{entry.script}"
            r = guest.run(
                d / "python-snapshot.wasm",
                ["-u", script, *entry.args, "-o", DERIVED_DIR],
                workdir=self.workdir,
                python_version=m.python,
                stdlib=d / "python-stdlib.zip",
                files={f"{DERIVED_DIR}/.made-here": b""},
                env=upstream.ENV | cfg.keys.env,
                fuel=entry.fuel,
                preopens=[(cfg.grant, root, False)],
            )
            made = r.root / DERIVED_DIR.lstrip("/") / entry.name
            errors = derived_findings(entry.name, r) or derived_output_errors(made, entry.name)
            if not errors:
                target = root / "tree" / entry.output
                shutil.copyfile(made, target)
                facts[entry.output] = {"sha256": paths.sha256_file(target), "fuel": r.fuel}
            litter.remove(r.root.parent)
            if errors:
                return errors
        self.derived[package] = facts
        return []

    def _files(self, package: str) -> dict[str, bytes] | None:
        from harness import pins

        cfg = self.configs[package]
        if not cfg.keys.cwd_files and not cfg.keys.cwd_folders:
            return None
        pair = pins.source_pair(cfg.component or package)
        assert pair is not None
        tree = pair[1]
        files = {f"{WORK}/{rel}": (tree / rel).read_bytes() for rel in cfg.keys.cwd_files}
        return {**files, **cwd_folder_files(cfg, tree)}

    def _run(self, package: str, name: str, fuel: int) -> tuple[str, upstream.GuestRun]:
        from harness import guest

        cfg = self.configs[package]
        d = paths.artifact_dir()
        m = paths.parse_manifest((d / "MANIFEST").read_text())
        r = guest.run(
            d / "python-snapshot.wasm",
            ["-u", f"{cfg.grant}/judge/{DRIVER}", package, name],
            workdir=self.workdir,
            python_version=m.python,
            stdlib=d / "python-stdlib.zip",
            files=self._files(package),
            env=upstream.ENV | cfg.keys.env,
            fuel=fuel,
            preopens=[(cfg.grant, self.roots[package], False)],
            mpl_data=upstream._has_mpl_data(d / "python-stdlib.zip"),
            clock_step_ns=cfg.keys.clock_steps.get(name, (guest.CLOCK_STEP_NS, ""))[0],
        )
        stream_file = r.root / upstream.STREAM
        text = stream_file.read_text(errors="replace") if stream_file.is_file() else ""
        kept = paths.HARNESS_TMP / "streams"  # the whole stream, for reading a failure in full
        kept.mkdir(parents=True, exist_ok=True)
        (kept / f"{package}-{name}.txt").write_text(text)
        tail = r.stderr.decode(errors="replace").strip().splitlines()[-1:] or [""]
        run = upstream.GuestRun(r.exit_code, r.trapped, r.trap_cause, r.fuel, r.text, tail[0][:200])
        about = {"fuel": r.fuel, "exit": r.exit_code, "trapped": r.trapped, "tail": run.stderr_tail}
        (kept / f"{package}-{name}.json").write_text(json.dumps(about))  # beside its stream
        litter.remove(r.root.parent)  # the run's root and its sealed stdlib folder
        return text, run

    def group(self, package: str, group: str) -> PackageRun:
        if group not in self.groups:
            left_out, keep = self.prepare(package)
            cfg = self.configs[package]
            text, run = self._run(package, group, cfg.groups[group].fuel)
            outcome, extra = judge(cfg, group, text, run, keep)
            if cfg.groups[group].selects_nothing:  # a guard: pytest's "no tests ran" is its pass
                outcome.findings = [f for f in outcome.findings if f != "pytest exit code 5"]
            outcome.findings += self._split_findings(cfg, group, extra.collected)
            outcome.findings += clock_findings(cfg, group, outcome)
            derived = self.derived.get(package) if group == cfg.keys.derived_row else None
            self.groups[group] = PackageRun(
                outcome,
                run.fuel,
                left_out,
                extra.collected,
                derived=derived,
                deselected=len(extra.deselected),
            )
        return self.groups[group]

    def _split_findings(self, cfg: upstream.Config, group: str, collected: int | None) -> list[str]:
        """Every group of a split collected the same file: a count unequal to an earlier group's
        of the same split in this judge run is red."""
        split = cfg.keys.split_of(group)
        if split is None or collected is None:
            return []
        for other in split.groups:
            seen = self.groups.get(other)
            if seen is not None and seen.collected is not None and seen.collected != collected:
                return [
                    f"{split.file}: collected {collected} tests here, {seen.collected} in {other}"
                ]
        return []

    def trap(self, package: str, trap_id: str) -> upstream.TrapRun:
        self.prepare(package)
        text, run = self._run(package, trap_id, upstream.TRAP_FUEL)
        node = next(t.node for t in self.configs[package].traps if t.id == trap_id)
        return upstream.TrapRun(
            upstream.trap_findings(upstream.parse_stream(text), run, node), run.fuel
        )


# ---------------------------------------------------------------------------------------------
# The rules


def _keyword_errors(expr: str) -> str | None:
    """Why pytest's own parser refuses a -k expression, or None."""
    try:
        from _pytest.mark.expression import Expression

        Expression.compile(expr)
    except Exception as e:  # noqa: BLE001 (pytest's ParseError, whatever its module)
        return str(e).splitlines()[0]
    return None


# pytest builds a -k expression's `or` and `and` as nested pairs and compiles them as one
# expression; the guest's stack overflows in that compile past some 270 levels (a 275-term `or`
# did), and splits that ran have nested to 108. A split group's nesting is about its longest
# keyword's terms plus the parts before it.
SPLIT_DEPTH = 150


def _terms(keyword: str) -> int:
    return len([w for w in re.findall(r"[\w\[\]-]+", keyword) if w not in ("or", "and", "not")])


def split_errors(pkg: str, cfg: upstream.Config) -> list[str]:
    errors = []
    seen: set[str] = set()
    for s in cfg.keys.splits:
        where = f"{pkg}: split of {s.file}"
        for i, g in enumerate(s.groups):
            nest = i + max((_terms(k) for k in s.keywords[: i + 1]), default=0)
            if nest > SPLIT_DEPTH:
                errors.append(
                    f"{where}: group {g}'s -k expression nests about {nest} deep (its keywords' "
                    f"terms and the parts before it), past {SPLIT_DEPTH}: the guest cannot "
                    "compile it"
                )
        if len(s.groups) < 2:
            errors.append(f"{where}: fewer than two groups")
        if len(s.keywords) != len(s.groups) - 1:
            errors.append(f"{where}: {len(s.keywords)} expressions for {len(s.groups)} groups")
        for k in s.keywords:
            if not k.strip():
                errors.append(f"{where}: an empty expression")
            elif (why := _keyword_errors(k)) is not None:
                errors.append(f"{where}: expression {k!r} does not parse: {why}")
        for g in s.groups:
            if g in seen:
                errors.append(f"{where}: group {g} is in two splits")
            seen.add(g)
            if g not in cfg.groups:
                errors.append(f"{where}: names no group of its package: {g}")
            elif cfg.groups[g].paths != (s.file,):
                errors.append(f"{where}: group {g}'s paths are not exactly its file")
    return errors


def rule_cap(measured: int) -> int:
    """1.5 times a group's recorded fuel, rounded up to two significant figures: the owner's rule
    (decisions.md, "Every test of every package we build", 2026-10-20)."""
    x = 3 * measured // 2 + (3 * measured % 2 > 0)
    step = 10 ** max(len(str(x)) - 2, 0)
    return -(-x // step) * step


def _under(folder: str, path: str) -> bool:
    return path == folder or path.startswith(folder.rstrip("/") + "/")


def product_packages(stdlib: Path) -> set[str]:
    """The packages the product's zip holds, by dotted name (each folder with an `__init__`)."""
    with zipfile.ZipFile(stdlib) as z:
        names = z.namelist()
    return {
        n.rsplit("/", 1)[0].replace("/", ".")
        for n in names
        if n.endswith(("/__init__.pyc", "/__init__.py"))
    }


def inits_errors(
    pkg: str, cfg: upstream.Config, members: set[str] | None, product: set[str] | None
) -> list[str]:
    """`package_inits`: a boolean; its generated entries are tarball packages; every ancestor of
    a staged folder is a package the product has, so the product's own module always wins."""
    k = cfg.keys
    if not isinstance(k.package_inits, bool):
        return [f"{pkg}: package_inits {k.package_inits!r} is not a boolean"]
    if not k.package_inits:
        return []
    errors = []
    if k.listed_paths:
        errors.append(f"{pkg}: package_inits generates package_paths; the TOML lists none")
    if members is not None:
        errors += [
            f"{pkg}: the generated package_paths entry {name} names {folder}, which holds no "
            "__init__.py member"
            for name, folder in k.package_paths.items()
            if f"{folder}/__init__.py" not in members
        ]
    if product is not None:
        for f in k.stage_folders:
            lacking = [n for n in ancestors((f,)) if n not in product]
            if lacking:
                errors.append(
                    f"{pkg}: stage folder {f} lies under {lacking[0]}, a package the product lacks"
                )
    return errors


def derived_errors(pkg: str, cfg: upstream.Config, members: set[str] | None) -> list[str]:
    """Each derived entry: a staged member script, an inputs folder of members, an output inside
    a staged folder that no member is, a cap by the rule; and one derived_row for the family."""
    k = cfg.keys
    errors = []
    if k.derived and not k.derived_row:
        errors.append(f"{pkg}: a family with derived names no derived_row")
    if k.derived_row and k.derived_row not in cfg.groups:
        errors.append(f"{pkg}: derived_row {k.derived_row} names no group of its family")
    if k.derived_row and not k.derived:
        errors.append(f"{pkg}: derived_row without derived")
    staged = lambda f: any(_under(s, f) for s in k.stage_folders)  # noqa: E731
    for e in k.derived:
        where = f"{pkg}: derived {e.output}"
        if e.script not in k.support_files and not staged(e.script):
            errors.append(f"{where}: its script {e.script} is neither staged nor a support file")
        if not staged(e.output):
            errors.append(f"{where}: the output lies outside the staged folders")
        if e.measured is None:
            errors.append(f"{where} records no measured fuel")
        elif e.fuel > rule_cap(e.measured):
            errors.append(
                f"{where}: its cap {e.fuel:,} is above 1.5 times its measured {e.measured:,} "
                f"({rule_cap(e.measured):,})"
            )
        if members is None:
            continue
        if e.script not in members:
            errors.append(f"{where}: its script {e.script} is not a tarball member")
        if not any(_under(e.inputs, m) and m != e.inputs for m in members):
            errors.append(f"{where}: its inputs folder {e.inputs} holds no tarball member")
        if e.output in members:
            errors.append(f"{where}: the output is a tarball member")
    return errors


def env_errors(pkg: str, cfg: upstream.Config) -> list[str]:
    """`env` is a family's key only, names only the family's allowed variables, each with its
    reason, and never one of the forbidden ones."""
    k = cfg.keys
    errors = [f"{pkg}: group {g} carries env; only a family may" for g in k.group_env]
    allowed = ENV_ALLOWED.get(pkg, ())
    for name in k.env:
        if name in ENV_FORBIDDEN or name.startswith("PYTHON"):
            errors.append(f"{pkg}: env sets {name}, which no family may")
        elif name not in allowed:
            errors.append(f"{pkg}: env sets {name}, not one of the family's {allowed}")
        if not k.env_reasons.get(name, "").strip():
            errors.append(f"{pkg}: env {name} gives no reason")
    return errors


def clock_errors(pkg: str, cfg: upstream.Config) -> list[str]:
    """`clock_step_ns`: on a release group only, with its reason, from 1 us to 1 ms."""
    lo, hi = CLOCK_STEP_RANGE
    errors = []
    for g, (ns, reason) in cfg.keys.clock_steps.items():
        group = cfg.groups.get(g)
        if group is None or group.tier != "release":
            errors.append(f"{pkg}: group {g}: clock_step_ns on a group not in the release tier")
        if not reason.strip():
            errors.append(f"{pkg}: group {g}: clock_step_ns without clock_reason")
        if not lo <= ns <= hi:
            errors.append(f"{pkg}: group {g}: clock_step_ns {ns:,} is outside {lo:,} to {hi:,}")
    return errors


def compiled_families(builtins: list[str], top: str) -> set[str]:
    """The subpackages that hold the package's compiled modules: each builtin module's parent."""
    return {n.rsplit(".", 1)[0] for n in builtins if n.startswith(top + ".")}


def top_name(cfg: upstream.Config) -> str:
    return PurePosixPath(cfg.keys.stage_folders[0]).parts[0] if cfg.keys.stage_folders else ""


def cover_errors(
    pkg: str, cfg: upstream.Config, families: set[str] | None, repo: Path = paths.REPO
) -> list[str]:
    """A smoke family's `smoke_cover`: each entry a smoke path of a smoke group, a golden job line
    that holds its word, or `release-only: <reason>`; the families SMOKE_ONLY names by a smoke
    path; and, with the product's builtin names, every compiled family has an entry and every
    entry is a compiled family or one SMOKE_ONLY names."""
    from harness import tiers

    k = cfg.keys
    if not tiers.is_smoke_family(cfg):
        return [f"{pkg}: smoke_cover in a family with no smoke group"] if k.smoke_cover else []
    must = SMOKE_ONLY.get(pkg, ())
    errors = [
        f"{pkg}: smoke_cover names nothing for {fam}, which a smoke path must cover"
        for fam in must
        if fam not in k.smoke_cover
    ]
    smoke = tiers.smoke_paths(cfg)
    for fam, cover in k.smoke_cover.items():
        where = f"{pkg}: smoke_cover {fam}"
        job = JOB_COVER.fullmatch(cover)
        if cover.startswith(RELEASE_ONLY) or cover == RELEASE_ONLY.strip():
            if fam in must:
                errors.append(f"{where} is release-only, but a smoke path must cover it")
            elif not cover[len(RELEASE_ONLY) :].strip():
                errors.append(f"{where} is release-only without its reason")
        elif job is not None:
            if fam in must:
                errors.append(f"{where} is a golden line alone, but a smoke path must cover it")
            f = repo / job[1]
            lines = f.read_text(encoding="utf-8").splitlines() if f.is_file() else []
            n = int(job[2])
            if not 0 < n <= len(lines) or job[3] not in lines[n - 1]:
                errors.append(f"{where}: {job[1]}:{n} does not hold {job[3]}")
        elif not any(tiers._covers(s, cover) for s in smoke):
            errors.append(f"{where}: {cover} is in no smoke group")
    if families is not None:
        errors += [
            f"{pkg}: the compiled family {fam} has no smoke_cover entry"
            for fam in sorted(families - set(k.smoke_cover))
        ]
        errors += [
            f"{pkg}: smoke_cover {fam} is no compiled family of the product"
            for fam in sorted(set(k.smoke_cover) - families - set(must))
        ]
    return errors


def builtin_names(workdir: Path) -> list[str]:
    """The product's builtin module names, as the guest lists them."""
    from harness import guest

    d = paths.artifact_dir()
    m = paths.parse_manifest((d / "MANIFEST").read_text())
    r = guest.run(
        d / "python-snapshot.wasm",
        ["-c", "import sys; print('\\n'.join(sys.builtin_module_names))"],
        workdir=workdir,
        python_version=m.python,
        stdlib=d / "python-stdlib.zip",
        env=upstream.ENV,
        measured=False,
    )
    names = r.stdout.decode().split()
    litter.remove(r.root.parent)
    if r.exit_code != 0 or not names:
        raise AssertionError(f"the guest listed no builtin modules (exit {r.exit_code})")
    return names


def rule_errors(
    pkg: str, cfg: upstream.Config, members: set[str] | None, product: set[str] | None = None
) -> list[str]:
    k = cfg.keys
    errors = [f"{pkg}: a package TOML may not carry {key}" for key in k.refused]
    errors += inits_errors(pkg, cfg, members, product)
    errors += derived_errors(pkg, cfg, members)
    errors += env_errors(pkg, cfg)
    errors += clock_errors(pkg, cfg)
    errors += cover_errors(pkg, cfg, None)
    for g in cfg.groups.values():
        m = k.measured.get(g.name)
        if m is None:
            errors.append(f"{pkg}: group {g.name} records no measured fuel")
        elif g.fuel > rule_cap(m):
            errors.append(
                f"{pkg}: group {g.name}'s cap {g.fuel:,} is above 1.5 times its measured "
                f"{m:,} ({rule_cap(m):,})"
            )
    if cfg.grant != f"/upstream-{pkg}":
        errors.append(f"{pkg}: grant {cfg.grant} is not /upstream-{pkg}")
    if k.cwd not in (WORK, "tree"):
        errors.append(f"{pkg}: cwd {k.cwd!r} is neither {WORK} nor the tree root")
    if k.cwd_files and k.cwd != WORK:
        errors.append(f"{pkg}: cwd_files need cwd = {WORK!r}")
    for folder in k.support_packages:
        if folder not in k.stage_folders:
            errors.append(f"{pkg}: support package {folder} is not a stage folder")
    for g in cfg.groups.values():
        for p in g.paths:
            file = p.split("::", 1)[0]  # a node-id group's path is its file and the test
            if file in k.support_files:
                continue  # a staged support file may be a group's path (a one-file suite)
            if not any(file == f or file.startswith(f.rstrip("/") + "/") for f in k.stage_folders):
                errors.append(f"{pkg}: group {g.name} path {p} is not under a stage folder")
    errors += split_errors(pkg, cfg)
    caps = sum(g.fuel for g in cfg.groups.values()) + upstream.TRAP_FUEL * len(cfg.traps)
    caps += sum(e.fuel for e in k.derived)
    if caps > k.budget:
        errors.append(f"{pkg}: caps {caps:.3g} over the family's budget {k.budget:.3g}")
    if k.test_source:
        errors += source_rule_errors(pkg, cfg, members)
    if members is not None:

        def folder_ok(f: str) -> bool:
            return any(m.startswith(f.rstrip("/") + "/") for m in members)

        for f in [*k.stage_folders, *k.extra_sys_path, *k.package_paths.values()]:
            if f != "." and not folder_ok(f):
                errors.append(f"{pkg}: {f} is not a folder of the tarball")
        files = [*k.support_files, *k.cwd_files, *(f for f, _ in k.doctest_files)]
        files += [
            f.split("::", 1)[0]
            for n in cfg.not_selected
            for f in n.files
            if not folder_ok(f.split("::", 1)[0])  # a not-selected folder is a folder of it
        ]
        files += [f for it in k.items.values() for f, _ in it.doctest_files]
        files += [
            p.split("::", 1)[0]
            for g in cfg.groups.values()
            for p in g.paths
            if p.split("::", 1)[0].endswith(".py")
        ]
        errors += [f"{pkg}: {f} is not a tarball member" for f in files if f not in members]
    return errors


# A test-source family's smoke group is small, and all of them together are: the normal tier runs
# them at every landing, so it cannot grow a second suite unnoticed. Moving either is a judge
# change. They bound the test-source families only. Both rose with the five families of SVG to
# PNG through cairo (tinycss2, cssselect2, cairocffi, CairoSVG, imageio): a group from 100 G to
# 110 G for tinycss2's one test file, 105.9 G whole, which a smoke family cannot split by path;
# the total from 1 T to 1.2 T, their smoke groups measuring 201.3 G together.
SMOKE_GROUP_BOUND = 110 * 10**9
SMOKE_TOTAL_BOUND = 12 * 10**11


def source_rule_errors(pkg: str, cfg: upstream.Config, members: set[str] | None) -> list[str]:
    """A test-source family's own keys: its extras are listed, its folders are the source's, its
    environment and flags are allowed, each group runs paths or items (never both), and it has
    exactly one normal group, its smoke group."""
    k = cfg.keys
    errors = []
    listed = {extra_name(f) for _, _, f in extra_entries(KIT_EXTRA.read_text())}
    errors += [
        f"{pkg}: kit_extra {n} is not in kit-extra.txt" for n in k.kit_extra if n not in listed
    ]
    if k.cwd_folders and k.cwd != WORK:
        errors.append(f"{pkg}: cwd_folders need cwd = {WORK!r}")
    errors += [
        f"{pkg}: sys_flags {n} is not one of {SYS_FLAGS}" for n in k.sys_flags if n not in SYS_FLAGS
    ]
    errors += [
        f"{pkg}: doctest_setup {n} is not one of {DOCTEST_SETUPS}"
        for n in k.doctest_setup
        if n not in DOCTEST_SETUPS
    ]
    if k.doctest_runner and k.doctest_runner not in DOCTEST_RUNNERS:
        errors.append(f"{pkg}: doctest_runner {k.doctest_runner} is not one of {DOCTEST_RUNNERS}")
    if k.doctest_checker and k.doctest_checker not in DOCTEST_CHECKERS:
        errors.append(
            f"{pkg}: doctest_checker {k.doctest_checker} is not one of {DOCTEST_CHECKERS}"
        )
    for g in cfg.groups.values():
        if not g.paths and g.name not in k.items:
            errors.append(f"{pkg}: group {g.name} runs nothing: no paths and no items")
    normal = [g.name for g in cfg.groups.values() if g.tier == "normal"]
    if len(normal) != 1:
        errors.append(
            f"{pkg}: {len(normal)} normal groups; a test-source family has its smoke alone"
        )
    for g in cfg.groups.values():
        if g.smoke is not None and (g.measured or 0) > SMOKE_GROUP_BOUND:
            errors.append(
                f"{pkg}: smoke group {g.name} measures {g.measured / 1e9:.1f} G, "
                f"past {SMOKE_GROUP_BOUND / 1e9:.0f} G"
            )
    if members is not None:
        for f in k.cwd_folders:
            if not any(m.startswith(f.rstrip("/") + "/") for m in members):
                errors.append(f"{pkg}: cwd_folders {f} is not a folder of the test source")
    return errors


def smoke_total_errors(configs: dict[str, upstream.Config]) -> list[str]:
    """The test-source families' smoke groups together stay under their bound."""
    total = sum(
        g.measured or 0
        for c in configs.values()
        if c.driver == "package" and c.keys.test_source
        for g in c.groups.values()
        if g.smoke is not None
    )
    if total > SMOKE_TOTAL_BOUND:
        return [
            f"the test-source smoke groups measure {total / 1e9:.1f} G together, "
            f"past {SMOKE_TOTAL_BOUND / 1e12:.1f} T"
        ]
    return []


def lxml_errors(configs: dict[str, upstream.Config], members: set[str] | None) -> list[str]:
    """lxml's selection is its own runner's, read statically from the
    tarball: the doctest files the selected modules' test_suite() functions name are exactly the
    configuration's, and their docstring suites are as many as it runs or names as left out."""
    from harness import pins

    cfg = configs.get("lxml")
    pair = pins.source_pair("lxml")
    if cfg is None or cfg.driver != "package" or pair is None or members is None:
        return []
    import tarfile

    k = cfg.keys
    out_files = {f for n in cfg.not_selected for f in n.files}
    named: set[str] = set()
    suites = 0
    with tarfile.open(pair[0]) as tar:
        top = tar.getmembers()[0].name.split("/")[0]
        for folder in k.stage_folders:
            for rel in sorted(m for m in members if m.startswith(folder + "/test_")):
                if not rel.endswith(".py") or "/" in rel[len(folder) + 1 :] or rel in out_files:
                    continue
                source = tar.extractfile(f"{top}/{rel}").read().decode("utf-8")
                files, docstrings = test_suite_doctests(source)
                named |= set(files)
                suites += docstrings
    declared = {PurePosixPath(f).name for f, _ in k.doctest_files}
    errors = [
        f"lxml: test_suite() names doctest file {f}, not configured"
        for f in sorted(named - declared)
    ]
    errors += [
        f"lxml: doctest file {f} is named by no selected test_suite()"
        for f in sorted(declared - named)
    ]
    want = len(k.docstring_modules) + len(k.docstring_not_selected)
    if suites != want:
        errors.append(
            f"lxml: the selected test_suite() functions add {suites} docstring suites; the "
            f"configuration runs or leaves out {want}"
        )
    return errors
