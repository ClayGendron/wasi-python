"""The compiled packages' families (harness.packages): the split by construction, the rules,
the guard, lxml's selection both ways and the extra stream lines, on fixed inputs, with no guest."""

from __future__ import annotations

import tomllib

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
        ("upstream-plot-l", ["matplotlib"]),
        ("upstream-plot-g", ["contourpy", "pillow"]),
        ("upstream-plot-a", ["contourpy"]),
        ("upstream-numpy-a", ["cpython", "numpy", "pandas"]),
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
