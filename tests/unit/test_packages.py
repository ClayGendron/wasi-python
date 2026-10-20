"""Spec 066's families (harness.packages): the split by construction, the rules, the guard, lxml's
selection both ways and the extra stream lines, on fixed inputs, with no guest."""

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

[groups.demo-2]
paths = ["tests/test_big.py"]
fuel = 10

[groups.demo-3]
paths = ["tests/test_big.py"]
fuel = 10

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
    assert "tests/test_big.py" in args


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


def test_numpy_and_pandas_are_read_as_today() -> None:
    configs = upstream.load_all()
    for name in ("numpy", "pandas"):
        assert configs[name].driver == "upstream"
        assert isinstance(configs[name].path_packages, list)
    families = upstream.families(configs)
    assert set(families[upstream.GRANT]) == {"numpy", "pandas"}
    for name in upstream.PACKAGE_SUITES:
        assert configs[name].grant == f"/upstream-{name}"
