"""The compiled packages' families (harness.packages): the split by construction, the rules,
the guard, lxml's selection both ways and the extra stream lines, on fixed inputs, with no guest."""

from __future__ import annotations

import json
import tomllib
import zipfile

import pytest

from harness import packages, upstream

BASE = """
package = "demo"
driver = "package"
grant = "/upstream-demo"
budget = 30
stage_folders = ["tests"]
cwd = "/tmp/work"

[groups.demo-1]
paths = ["tests/test_big.py"]
fuel = 10
measured = 7

[groups.demo-2]
paths = ["tests/test_big.py"]
fuel = 10
measured = 7

[groups.demo-3]
paths = ["tests/test_big.py"]
fuel = 10
measured = 7

[[split]]
file = "tests/test_big.py"
groups = ["demo-1", "demo-2", "demo-3"]
keywords = ["random_big and serial", "random_big"]
"""


def _cfg(text: str = BASE) -> upstream.Config:
    return packages.load(tomllib.loads(text))


def test_a_split_partitions_by_construction() -> None:
    split = _cfg().keys.splits[0]
    assert split.keyword("demo-1") == "(random_big and serial)"
    assert split.keyword("demo-2") == "(random_big) and not ((random_big and serial))"
    assert split.keyword("demo-3") == "not ((random_big and serial) or (random_big))"


def test_a_split_groups_argv_carries_its_keyword() -> None:
    cfg = _cfg()
    args = packages.group_args(cfg, cfg.groups["demo-2"])
    assert args[-1] == "-k(random_big) and not ((random_big and serial))"
    assert "/upstream-demo/tree/tests/test_big.py" in args  # absolute, made by the host


def test_the_well_formed_split_has_no_error() -> None:
    assert packages.rule_errors("demo", _cfg(), None) == []


BAD_SPLITS = [
    (
        'keywords = ["random_big and serial", "random_big"]',
        'keywords = ["random_big and serial", "random_big", "x"]',
        "3 expressions for 3 groups",
    ),
    (
        'keywords = ["random_big and serial", "random_big"]',
        'keywords = ["", "random_big"]',
        "empty",
    ),
    (
        'keywords = ["random_big and serial", "random_big"]',
        'keywords = ["random_big and (", "random_big"]',
        "does not parse",
    ),
    (
        '[groups.demo-3]\npaths = ["tests/test_big.py"]',
        '[groups.demo-3]\npaths = ["tests/test_big.py", "tests/test_other.py"]',
        "not exactly its file",
    ),
    ('grant = "/upstream-demo"', 'grant = "/upstream"', "is not /upstream-demo"),
    ('cwd = "/tmp/work"', 'cwd = "/tmp"', "neither /tmp/work nor the tree root"),
    ("budget = 30", "budget = 29", "over the family's budget"),
]


@pytest.mark.parametrize(("old", "new", "error"), BAD_SPLITS, ids=[e for _, _, e in BAD_SPLITS])
def test_a_malformed_configuration_fails_with_its_own_line(old, new, error) -> None:
    assert BASE.count(old) == 1, old
    errors = packages.rule_errors("demo", _cfg(BASE.replace(old, new)), None)
    assert any(error in e for e in errors), errors


def test_cwd_files_need_the_writable_folder() -> None:
    text = BASE.replace('cwd = "/tmp/work"', 'cwd = "tree"\ncwd_files = ["doc/test.xml"]')
    assert any("cwd_files need" in e for e in packages.rule_errors("demo", _cfg(text), None))


def _run(code=0, trapped=None) -> upstream.GuestRun:
    return upstream.GuestRun(code, trapped, None, 1, "", "")


STREAM = """C tests/test_big.py
K 5
P derandomize=True database=None max_examples=100
S tests/test_big.py::test_a
R passed tests/test_big.py::test_a --
R skipped tests/test_skipping.py -- skips itself
E {code}
"""


def test_a_split_group_records_its_collected_count() -> None:
    outcome, extra = packages.judge(_cfg(), "demo-1", STREAM.format(code=0), _run(), {})
    assert outcome.findings == []
    assert extra.collected == 5
    assert outcome.counts == {"passed": 1, "skipped": 1}  # the whole-file skip is counted


def test_a_split_group_that_selects_nothing_fails() -> None:
    outcome, _ = packages.judge(_cfg(), "demo-1", STREAM.format(code=5), _run(), {})
    assert "pytest exit code 5" in outcome.findings


def test_a_split_group_without_its_k_line_fails() -> None:
    text = STREAM.format(code=0).replace("K 5\n", "")
    outcome, _ = packages.judge(_cfg(), "demo-1", text, _run(), {})
    assert any("no K line" in f for f in outcome.findings)


def test_the_guard_is_path_based() -> None:
    cfg = _cfg()
    root = "/upstream-demo/tree/"
    ok = [("tests.test_big", root + "tests/test_big.py")]
    assert packages.guard_findings(cfg, ok) == []
    support = packages.load(
        tomllib.loads(
            BASE.replace('cwd = "/tmp/work"', 'cwd = "/tmp/work"\nsupport_files = ["selftest.py"]')
        )
    )
    assert packages.guard_findings(support, [("selftest", root + "selftest.py")]) == []
    from_tree = [("demo.core", root + "demo/core.py")]
    assert "outside the staged folders" in packages.guard_findings(cfg, from_tree)[0]
    from_kit = [("packaging", "/upstream-demo/kit/packaging/__init__.py")]
    assert "outside the zip" in packages.guard_findings(cfg, from_kit)[0]


SUITE = """
import unittest
class _Base(unittest.TestCase):
    etree = None
class Kept(_Base):
    pass
def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(Kept)])
    suite.addTests([doctest.DocFileSuite("test_basic.txt")])
    suite.addTests([make_doctest("api.txt")])
    suite.addTests(doctest.DocTestSuite(etree))
    return suite
"""


def test_lxml_test_suite_is_read_statically() -> None:
    assert packages.test_suite_classes(SUITE) == ["Kept"]
    assert packages.test_suite_doctests(SUITE) == (["test_basic.txt", "api.txt"], 1)
    whole = "def test_suite():\n    return loader.loadTestsFromModule(sys.modules[__name__])\n"
    assert packages.test_suite_classes(whole) == "*"
    assert packages.test_suite_classes("x = 1\n") is None


def test_lxml_selection_is_checked_both_ways() -> None:
    keep = {"tests/test_e.py": ["Kept"]}
    stream = upstream.parse_stream("S tests/test_e.py::Kept::test_x\n")
    extra = packages.parse_extra("D tests/test_e.py::_Base::test_x\n")
    assert packages.keep_findings(extra, stream, keep) == []
    lost = upstream.parse_stream("S tests/test_e.py::Other::test_x\n")
    assert any("ran nothing" in f for f in packages.keep_findings(extra, lost, keep))
    wrong = packages.parse_extra("D tests/test_e.py::Kept::test_x\n")
    assert any("deselected a test" in f for f in packages.keep_findings(wrong, stream, keep))
    # the third direction: every test that ran is one test_suite() adds
    builder = upstream.parse_stream(
        "R passed tests/test_e.py::Kept::test_x --\nR passed tests/test_e.py::test_suite --\n"
    )
    assert any("does not add" in f for f in packages.keep_findings(extra, builder, keep))
    other = upstream.parse_stream(
        "R passed tests/test_e.py::Kept::test_x --\nR passed tests/test_e.py::_Base::t --\n"
    )
    assert any("does not add" in f for f in packages.keep_findings(extra, other, keep))
    dropped = packages.parse_extra("D tests/test_e.py::test_suite\n")
    assert packages.keep_findings(dropped, stream, keep) == []
    whole = {"tests/test_w.py": "*"}
    ok = upstream.parse_stream("R passed tests/test_w.py::Any::test_x --\n")
    assert packages.keep_findings(packages.Extra(), ok, whole) == []
    fn = upstream.parse_stream(
        "R passed tests/test_w.py::Any::test_x --\nR passed tests/test_w.py::test_suite --\n"
    )
    assert any("does not add" in f for f in packages.keep_findings(packages.Extra(), fn, whole))


def test_the_rule_cap_is_one_and_a_half_times_rounded_up() -> None:
    assert packages.rule_cap(439_781_534_980) == 660_000_000_000
    assert packages.rule_cap(12_975_521_084) == 20_000_000_000
    assert packages.rule_cap(100) == 150


def test_a_cap_above_the_rule_or_without_a_measurement_is_refused() -> None:
    high = BASE.replace("fuel = 10\nmeasured = 7", "fuel = 10\nmeasured = 6", 1)
    assert any("above 1.5 times" in e for e in packages.rule_errors("demo", _cfg(high), None))
    bare = BASE.replace("fuel = 10\nmeasured = 7", "fuel = 10", 1)
    assert any("no measured fuel" in e for e in packages.rule_errors("demo", _cfg(bare), None))


@pytest.mark.parametrize("key", ["path_packages = []", "support = []"])
def test_numpys_keys_are_refused_in_a_package_toml(key) -> None:
    text = BASE.replace('cwd = "/tmp/work"', f'cwd = "/tmp/work"\n{key}')
    assert any("may not carry" in e for e in packages.rule_errors("demo", _cfg(text), None))


def test_unequal_collected_counts_across_a_split_are_red(tmp_path) -> None:
    cfg = _cfg()
    s = packages.Session(tmp_path, {"demo": cfg})
    s.groups["demo-1"] = packages.PackageRun(None, 1, [], 5)
    assert s._split_findings(cfg, "demo-2", 5) == []
    assert "collected 6 tests here, 5 in demo-1" in s._split_findings(cfg, "demo-2", 6)[0]


def test_numpy_and_pandas_are_read_as_today() -> None:
    configs = upstream.load_all()
    for name in ("numpy", "pandas"):
        assert configs[name].driver == "upstream"
        assert isinstance(configs[name].path_packages, list)
    families = upstream.families(configs)
    assert set(families[upstream.GRANT]) == {"numpy", "pandas"}
    for name in upstream.PACKAGE_SUITES:
        assert configs[name].grant == f"/upstream-{name}"


def test_the_upstream_stage_never_takes_a_package_family(monkeypatch, tmp_path) -> None:
    """Criterion 6's mechanism: numpy's and pandas' stage prepares only its own families' trees,
    even when every package family's tree is on disk, so its file list is the base's."""
    from harness import pins

    configs = upstream.load_all()
    asked: list[str] = []
    monkeypatch.setattr(pins, "source_pair", lambda pkg, *a, **k: ("tarball", "tree"))
    monkeypatch.setattr(upstream.Session, "_prepare", lambda self, p: asked.append(p) or [])
    s = upstream.Session(tmp_path, configs)
    s.prepare("numpy")
    assert sorted(asked) == ["numpy", "pandas"]


@pytest.mark.parametrize(
    ("shard", "families"),
    [
        ("upstream-plot-b", ["matplotlib", "pillow", "regex"]),
        ("upstream-plot-a", ["contourpy", "matplotlib"]),
        ("upstream-plot-i", ["contourpy"]),
        ("upstream-release-004", ["scipy", "statsmodels"]),
        ("upstream-numpy-a", ["cpython", "numpy", "pandas"]),
        ("upstream-sci-smoke-a", ["scipy"]),
        ("upstream-sci-smoke-b", ["scikit_learn", "statsmodels"]),
    ],
)
def test_a_shard_fetches_only_its_families_trees(shard, families) -> None:
    """Criterion 8's mechanism: `fetch.py --shard` fetches the trees of the families whose groups
    the shard runs, and no other package family's (the plan as it stands)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("fetch", upstream.HERE / "fetch.py")
    fetch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fetch)
    assert sorted(fetch.shard_packages(shard)) == families


# ---------------------------------------------------------------------------------------------
# The packages whose tests live in a tests folder per subpackage: the ancestors' inits, the
# derived test data, the family's environment, the clock step and the smoke cover

INITS = """
package = "scipy"
driver = "package"
grant = "/upstream-scipy"
budget = 100
stage_folders = ["pkg/a/tests", "pkg/b/c/tests"]
package_inits = true
support_files = ["pkg/utils/make.py"]
derived_row = "demo-b"
cwd = "/tmp/work"

[env.SCIPY_XSLOW]
value = "1"
reason = "the very slow cases run in whichever tier their file is in"

[[derived]]
script = "pkg/utils/make.py"
args = ["boost"]
inputs = "pkg/a/tests/data/boost"
output = "pkg/a/tests/data/boost.npz"
measured = 6
fuel = 9

[groups.demo-a]
paths = ["pkg/a/tests"]
fuel = 30
measured = 20

[groups.demo-b]
paths = ["pkg/b/c/tests"]
tier = "release"
fuel = 30
measured = 20
clock_step_ns = 1_000_000
clock_reason = "the test repeats a call until the clock has advanced 0.5 ms"
"""
MEMBERS = {
    "pkg/__init__.py",
    "pkg/a/__init__.py",
    "pkg/b/__init__.py",
    "pkg/b/c/__init__.py",
    "pkg/a/tests/test_x.py",
    "pkg/a/tests/data/boost/t.txt",
    "pkg/b/c/tests/test_z.py",
    "pkg/utils/make.py",
}
PRODUCT = {"pkg", "pkg.a", "pkg.b", "pkg.b.c"}


def _errors(text=INITS, members=MEMBERS, product=PRODUCT, pkg="scipy") -> list[str]:
    return packages.rule_errors(pkg, _cfg(text), members, product)


def test_package_inits_generates_the_ancestors_paths_and_inits() -> None:
    k = _cfg(INITS).keys
    want = {"pkg": "pkg", "pkg.a": "pkg/a", "pkg.b": "pkg/b", "pkg.b.c": "pkg/b/c"}
    assert k.package_paths == want
    assert set(k.init_files) == {f"{f}/__init__.py" for f in want.values()}
    assert k.env == {"SCIPY_XSLOW": "1"}
    assert _errors() == []


REASON = 'clock_reason = "the test repeats a call until the clock has advanced 0.5 ms"'
BAD_KEYS = [
    # (what, the TOML's edit, members, product, the line)
    ("no init", "", MEMBERS - {"pkg/b/__init__.py"}, PRODUCT, "holds no __init__.py member"),
    ("product lacks", "", MEMBERS, PRODUCT - {"pkg.b"}, "a package the product lacks"),
    ("script", "", MEMBERS - {"pkg/utils/make.py"}, PRODUCT, "is not a tarball member"),
    ("inputs", "", MEMBERS - {"pkg/a/tests/data/boost/t.txt"}, PRODUCT, "holds no tarball member"),
    (
        "output member",
        "",
        MEMBERS | {"pkg/a/tests/data/boost.npz"},
        PRODUCT,
        "the output is a tarball member",
    ),
    ("output outside", "output-outside", MEMBERS, PRODUCT, "outside the staged folders"),
    ("derived cap", "derived-cap", MEMBERS, PRODUCT, "above 1.5 times its measured 6"),
    ("no derived_row", "no-row", MEMBERS, PRODUCT, "names no derived_row"),
    ("group env", "group-env", MEMBERS, PRODUCT, "carries env"),
    ("env name", "[env.SCIPY_ARRAY_API]", MEMBERS, PRODUCT, "not one of the family's"),
    ("env HOME", "[env.HOME]", MEMBERS, PRODUCT, "HOME, which no family may"),
    ("env PYTHONPATH", "[env.PYTHONPATH]", MEMBERS, PRODUCT, "PYTHONPATH, which no family may"),
    (
        "env profile",
        "[env.SCIPY_HYPOTHESIS_PROFILE]",
        MEMBERS,
        PRODUCT,
        "PROFILE, which no family may",
    ),
    (
        "env network",
        "[env.SKLEARN_SKIP_NETWORK_TESTS]",
        MEMBERS,
        PRODUCT,
        "NETWORK_TESTS, which no family may",
    ),
    ("clock normal", "clock-normal", MEMBERS, PRODUCT, "not in the release tier"),
    ("clock reason", "clock-reason", MEMBERS, PRODUCT, "without clock_reason"),
    ("clock 2 ms", "clock-2ms", MEMBERS, PRODUCT, "outside 1,000 to 1,000,000"),
    ("inits not boolean", "inits-yes", MEMBERS, PRODUCT, "is not a boolean"),
    ("paths listed", "paths-listed", MEMBERS, PRODUCT, "the TOML lists none"),
]
EDITS = {
    "": (INITS, INITS),
    "no-row": ('derived_row = "demo-b"\n', ""),
    "clock-normal": ('tier = "release"\n', ""),
    "output-outside": ('output = "pkg/a/tests/data/boost.npz"', 'output = "pkg/utils/boost.npz"'),
    "derived-cap": ("measured = 6\nfuel = 9\n", "measured = 6\nfuel = 10\n"),
    "group-env": (
        'paths = ["pkg/a/tests"]',
        'paths = ["pkg/a/tests"]\nenv = { SCIPY_XSLOW = "1" }',
    ),
    "clock-reason": (REASON, 'clock_reason = ""'),
    "clock-2ms": ("clock_step_ns = 1_000_000", "clock_step_ns = 2_000_000"),
    "inits-yes": ("package_inits = true", 'package_inits = "yes"'),
    "paths-listed": ('cwd = "/tmp/work"', 'cwd = "/tmp/work"\n[package_paths]\n"pkg" = "pkg"'),
}


def _variant(edit: str) -> str:
    if edit.startswith("[env."):
        return INITS + f'\n{edit}\nvalue = "1"\nreason = "a reason"\n'
    old, new = EDITS[edit]
    assert INITS.count(old) == 1, old
    return INITS.replace(old, new)


@pytest.mark.parametrize(
    ("what", "edit", "members", "product", "error"), BAD_KEYS, ids=[b[0] for b in BAD_KEYS]
)
def test_a_malformed_key_fails_with_its_own_line(what, edit, members, product, error) -> None:
    errors = _errors(_variant(edit), members, product)
    assert any(error in e for e in errors), errors


def test_a_clock_stepped_group_with_two_outcomes_is_red() -> None:
    cfg = _cfg(INITS)
    one_text = STREAM.format(code=0).replace("K 5\n", "")
    one_text = one_text.replace("R skipped tests/test_skipping.py -- skips itself\n", "")
    two_text = one_text + "R passed tests/test_big.py::test_b --\n"
    two, _ = packages.judge(cfg, "demo-b", two_text, _run(), {})
    found = packages.clock_findings(cfg, "demo-b", two)
    assert found == ["a changed clock step reaches other tests: 2 outcomes in demo-b, not one"]
    one, _ = packages.judge(cfg, "demo-b", one_text, _run(), {})
    assert packages.clock_findings(cfg, "demo-b", one) == []
    assert packages.clock_findings(cfg, "demo-a", two) == []  # no key, no rule


def test_a_staged_init_imported_during_a_run_is_a_finding() -> None:
    cfg = _cfg(INITS)
    root = "/upstream-scipy/tree/"
    test = [("pkg.a.tests.test_x", root + "pkg/a/tests/test_x.py")]
    assert packages.guard_findings(cfg, test) == []
    found = packages.guard_findings(cfg, [("pkg.b", root + "pkg/b/__init__.py")])
    assert found and "outside the staged folders" in found[0]


def test_staging_takes_the_ancestors_inits_and_the_support_files(tmp_path) -> None:
    tree = tmp_path / "tree"
    for m in MEMBERS:
        (tree / m).parent.mkdir(parents=True, exist_ok=True)
        (tree / m).write_text("x")
    packages.stage(_cfg(INITS), tree, set(MEMBERS), tmp_path / "dest")
    dest = tmp_path / "dest" / "tree"
    assert {p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()} == MEMBERS


# The derived run, on a synthetic tarball: the guest is replaced by a stand-in that acts as the
# script would, so each way it can fail is seen without any real package.

PASS_STREAM = (
    "P derandomize=True database=None max_examples=100\n"
    "S pkg/a/tests/test_x.py::t\nR passed pkg/a/tests/test_x.py::t --\nE 0\n"
)


class _Guest:
    """`guest.run`'s stand-in: a derived run writes its output as `how` says; a group run writes
    one pass."""

    def __init__(self, how: str) -> None:
        self.how = how
        self.n = 0

    def __call__(self, wasm, argv, *, workdir, **kw):
        import types

        self.n += 1
        root = workdir / f"run-{self.n}" / "root"
        root.mkdir(parents=True)
        for path, content in (kw.get("files") or {}).items():
            (root / path.lstrip("/")).parent.mkdir(parents=True, exist_ok=True)
            (root / path.lstrip("/")).write_bytes(content)
        r = types.SimpleNamespace(
            exit_code=0, trapped=None, trap_cause=None, fuel=7, text="", stderr=b"", root=root
        )
        if not argv[1].endswith("make.py"):
            stream = root / upstream.STREAM
            stream.parent.mkdir(parents=True, exist_ok=True)
            stream.write_text(PASS_STREAM)
            return r
        out = root / "tmp/derived/boost.npz"
        if self.how in ("valid", "empty"):
            with zipfile.ZipFile(out, "w") as z:
                if self.how == "valid":
                    z.writestr("a.npy", b"\x93NUMPY")
        elif self.how == "exit1":
            r.exit_code = 1
        elif self.how == "link":
            (root / "elsewhere").write_bytes(b"x")
            out.symlink_to(root / "elsewhere")
        elif self.how == "big":
            out.write_bytes(b"\0" * (packages.DERIVED_MAX_BYTES + 1))
        elif self.how == "cap":
            r.trapped = "out of fuel"
        return r


def _family(
    tmp_path, monkeypatch, how: str, pin: str | None = None, text: str = INITS
) -> packages.Session:
    import io
    import tarfile

    from harness import guest, pins

    tree = tmp_path / "src" / "scipy-1.0"
    for m in MEMBERS:
        (tree / m).parent.mkdir(parents=True, exist_ok=True)
        (tree / m).write_text("x")
    tarball = tmp_path / "scipy-1.0.tar.gz"
    with tarfile.open(tarball, "w:gz") as t:
        for m in sorted(MEMBERS):
            info = tarfile.TarInfo(f"scipy-1.0/{m}")
            info.size = 1
            t.addfile(info, io.BytesIO(b"x"))
    art = tmp_path / "art"
    art.mkdir()
    sha = pin or packages.paths.sha256_file(tarball)
    (art / "MANIFEST").write_text(f"python 3.15.0\npin {sha} scipy-1.0.tar.gz\n")
    with zipfile.ZipFile(art / "python-stdlib.zip", "w") as z:
        z.writestr("pkg/__init__.pyc", b"")
    here = tmp_path / "here"
    here.mkdir()
    (here / packages.DRIVER).write_text("")
    (here / "scipy.ini").write_text("[pytest]\n")
    (here / "kit.txt").write_text("")
    monkeypatch.setattr(pins, "source_pair", lambda *a, **k: (tarball, tree))
    monkeypatch.setattr(packages.paths, "artifact_dir", lambda: art)
    monkeypatch.setattr(packages.paths, "HARNESS_TMP", tmp_path / "harness")
    monkeypatch.setattr(upstream, "KIT", here / "kit.txt")
    monkeypatch.setattr(upstream, "HERE", here)
    monkeypatch.setattr(guest, "run", _Guest(how))
    work = tmp_path / "work"
    work.mkdir()
    return packages.Session(work, {"scipy": _cfg(text)})


@pytest.mark.parametrize("first", ["demo-a", "demo-b"])
def test_a_valid_derived_output_is_staged_and_recorded_on_its_row_alone(
    tmp_path, monkeypatch, first
) -> None:
    s = _family(tmp_path, monkeypatch, "valid")
    try:
        order = [first, "demo-b" if first == "demo-a" else "demo-a"]
        runs = {g: s.group("scipy", g) for g in order}
        assert runs["demo-a"].derived is None
        facts = runs["demo-b"].derived
        assert set(facts) == {"pkg/a/tests/data/boost.npz"}
        assert facts["pkg/a/tests/data/boost.npz"]["fuel"] == 7
        assert len(facts["pkg/a/tests/data/boost.npz"]["sha256"]) == 64
        assert (s.roots["scipy"] / "tree/pkg/a/tests/data/boost.npz").is_file()
    finally:
        s.close()


@pytest.mark.parametrize(
    ("how", "named"),
    [
        ("exit1", "the script exited 1"),
        ("nothing", "the script wrote no file"),
        ("empty", "the archive holds no array"),
        ("link", "not a regular file"),
        ("big", "past the 2,541,286 bound"),
        ("cap", "out of fuel at its cap"),
    ],
)
def test_a_failed_derived_run_fails_every_group_of_the_family(
    tmp_path, monkeypatch, how, named
) -> None:
    s = _family(tmp_path, monkeypatch, how)
    try:
        for g in ("demo-a", "demo-b"):
            with pytest.raises(AssertionError, match=f"derived boost.npz: .*{named}"):
                s.group("scipy", g)
    finally:
        s.close()


def test_a_differing_pin_fails_the_group_and_never_blocks_it(tmp_path, monkeypatch) -> None:
    s = _family(tmp_path, monkeypatch, "valid", pin="0" * 64)
    try:
        with pytest.raises(AssertionError, match="the tests are not the artifact's: tests from"):
            s.group("scipy", "demo-a")
    finally:
        s.close()


TRAP = """
[[trap]]
id = "demo-trap"
node = "pkg/a/tests/test_x.py::t"
group = "demo-a"
reason = "the case does not finish"
closes_with = "README.md"
"""


def test_a_trap_runs_its_node_under_the_tree_and_leaves_its_group(tmp_path, monkeypatch) -> None:
    """A trap's session names its test by the path the guest sees, as every group's paths are
    named, and the group that holds the test deselects it."""
    import json

    s = _family(tmp_path, monkeypatch, "valid", text=INITS + TRAP)
    try:
        s.prepare("scipy")
        judge = s.roots["scipy"] / "judge"
        trap = json.loads((judge / "demo-trap.json").read_text())
        group = json.loads((judge / "demo-a.json").read_text())
        assert trap["args"][-1] == "/upstream-scipy/tree/pkg/a/tests/test_x.py::t"
        assert not trap["split"]
        assert "--deselect=pkg/a/tests/test_x.py::t" in group["args"]
    finally:
        s.close()


SMOKE_TOML = """
package = "demo"
driver = "package"
grant = "/upstream-demo"
budget = 100
stage_folders = ["pkg/a/tests", "pkg/b/tests"]
cwd = "/tmp/work"

[smoke_cover]
"pkg.a" = "pkg/a/tests/test_x.py"
"pkg.b" = "job tests/jobs/scipy_numeric.py:1 Golden"
"pkg.c" = "release-only: every file of it costs past the bound and no golden line calls it"

[groups.demo-smoke]
paths = ["pkg/a/tests/test_x.py"]
smoke = "pkg.a's compiled module"
fuel = 30
measured = 20

[groups.demo-b]
paths = ["pkg/b/tests"]
tier = "release"
fuel = 30
measured = 20
"""


def test_the_smoke_cover_holds_every_compiled_family() -> None:
    cfg = _cfg(SMOKE_TOML)
    assert packages.cover_errors("demo", cfg, {"pkg.a", "pkg.b", "pkg.c"}) == []
    names = ["pkg.a._m", "pkg.b.c._n", "other._x"]
    assert packages.compiled_families(names, "pkg") == {"pkg.a", "pkg.b.c"}
    missing = packages.cover_errors("demo", cfg, {"pkg.a", "pkg.b", "pkg.c", "pkg.d"})
    assert any("pkg.d has no smoke_cover entry" in e for e in missing), missing
    stale = packages.cover_errors("demo", cfg, {"pkg.a", "pkg.b"})
    assert any("pkg.c is no compiled family" in e for e in stale), stale


@pytest.mark.parametrize(
    ("old", "new", "error"),
    [
        ('"pkg.a" = "pkg/a/tests/test_x.py"', '"pkg.a" = "pkg/a/tests/test_y.py"', "in no smoke"),
        ("scipy_numeric.py:1 Golden", "scipy_numeric.py:1 nowhere", "does not hold nowhere"),
        (
            "release-only: every file of it costs past the bound and no golden line calls it",
            "release-only: ",
            "without its reason",
        ),
    ],
)
def test_a_cover_that_names_nothing_real_is_refused(old, new, error) -> None:
    assert SMOKE_TOML.count(old) == 1
    errors = packages.cover_errors("demo", _cfg(SMOKE_TOML.replace(old, new)), None)
    assert any(error in e for e in errors), errors


@pytest.mark.parametrize(
    "kind", ["release-only: a reason", "job tests/jobs/scipy_numeric.py:1 Golden"]
)
def test_a_family_a_smoke_file_must_cover_is_refused_otherwise(kind) -> None:
    text = SMOKE_TOML.replace('"pkg.c" =', f'"scipy.special" = "{kind}"\n"pkg.c" =')
    errors = packages.cover_errors("scipy", _cfg(text), None)
    assert any("scipy.special is" in e and "a smoke path must cover it" in e for e in errors)
    assert any("names nothing for scipy.sparse" in e for e in errors), errors


# ---------------------------------------------------------------------------------------------
# What every other family stages is untouched by these keys: its group JSON and its staged file
# list, byte for byte, against the digests recorded before the keys existed

STAGES = packages.paths.REPO / "tests" / "fixtures" / "upstream-stages.json"
OTHER_FAMILIES = (
    "numpy",
    "pandas",
    "python",
    "matplotlib",
    "contourpy",
    "pillow",
    "kiwisolver",
    "lxml",
    "regex",
)


def _digest(data) -> str:
    return packages.paths.sha256_bytes(json.dumps(data, sort_keys=True, indent=1).encode())


def _staged_list(root) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def stage_digests(work) -> dict[str, dict[str, str]]:
    """Each family's group JSON digest, and its staged file list's when its tree is here."""
    from harness import pins, regrtest

    configs = upstream.load_all()
    out: dict[str, dict[str, str]] = {}
    for name in OTHER_FAMILIES:
        cfg = configs[name]
        pair = pins.source_pair(cfg.component or name)
        dest = work / name
        staged = None
        if cfg.runner == "regrtest":
            specs = {g: regrtest.group_spec(cfg, g) for g in cfg.groups}
            specs |= {t.id: regrtest.trap_spec(cfg, t) for t in cfg.traps}
            if pair is not None:
                regrtest.stage(pair[0], pair[1], dest)
                staged = _staged_list(dest)
        elif cfg.driver == "package":
            keep = {}
            if pair is not None:
                allowed = upstream.tarball_members(pair[0])
                for p in upstream.repo_patches(pair[1].name):
                    allowed |= upstream.patch_created((packages.paths.REPO / p).read_text())
                packages.stage(cfg, pair[1], allowed, dest)
                staged = _staged_list(dest)
                keep = packages.keep_classes(cfg, dest / "tree")
            specs = {g.name: packages.group_spec(cfg, g, keep, []) for g in cfg.groups.values()}
        else:
            specs = upstream.judge_specs(cfg)
            if pair is not None:
                upstream.stage(cfg, pair[1], upstream.tarball_members(pair[0]), dest)
                staged = _staged_list(dest)
        out[name] = {"json": _digest(specs)}
        if staged is not None:
            out[name]["staged"] = _digest(staged)
    return out


def test_every_other_family_stages_what_it_staged_before(tmp_path) -> None:
    """numpy's, pandas', CPython's and the six plot and XML families' group JSON, and their staged
    file lists when their trees are here, equal the digests recorded before the keys of the
    subpackage-folder families existed. A family whose group JSON names classes read from its
    tree (lxml's) has a second digest, the JSON a host without the tree writes."""
    want = json.loads(STAGES.read_text())
    got = stage_digests(tmp_path)
    for name in OTHER_FAMILIES:
        bare = "staged" not in got[name] and "json_without_tree" in want[name]
        key = "json_without_tree" if bare else "json"
        assert got[name]["json"] == want[name][key], f"{name}'s group JSON changed"
        if "staged" in got[name]:
            assert got[name]["staged"] == want[name]["staged"], f"{name}'s staged files changed"
