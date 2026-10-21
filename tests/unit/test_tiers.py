"""The two tiers in the upstream files, on fixed inputs with no guest: which tests each tier runs,
the rules that keep every test in a tier, the argv each group gets, and CPython's resource lists
and the partition its normal groups prove."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from harness import packages, regrtest, tiers, upstream

# A numpy-like family: three normal groups, one marker release group over all their paths.
NUMPY = """
package = "numpy"
marker = "not slow"
release_marker = "slow"
path_packages = ["numpy"]
args = ["-p", "no:cacheprovider"]

[groups.np-core]
paths = ["numpy/_core/tests"]
fuel = 100

[groups.np-lib]
paths = ["numpy/lib/tests"]
fuel = 100

[groups.np-slow]
paths = ["numpy/_core/tests", "numpy/lib/tests"]
fuel = 150
measured = 100
tier = "release"
"""

# A contourpy-like family: a slow marker and a keyword selection, a split per tier and kind.
CONTOUR = """
package = "demo"
driver = "package"
grant = "/upstream-demo"
budget = 10_000
stage_folders = ["tests"]
cwd = "/tmp/work"
marker = "not slow"
release_marker = "slow"
args = ["--runslow"]

[[release_select]]
files = ["tests/test_filled.py", "tests/test_lines.py"]
keyword = "random_big"
reason = "the package's own selection for slow hosts"

[groups.demo-rest]
paths = ["tests/test_misc.py"]
fuel = 10
measured = 7

[groups.demo-filled-8]
paths = ["tests/test_filled.py"]
fuel = 10
measured = 7

[groups.demo-filled-12]
paths = ["tests/test_filled.py"]
fuel = 10
measured = 7

[[split]]
file = "tests/test_filled.py"
groups = ["demo-filled-8", "demo-filled-12"]
keywords = ["serial"]

[groups.demo-lines-8]
paths = ["tests/test_lines.py"]
fuel = 10
measured = 7

[groups.demo-filled-1]
paths = ["tests/test_filled.py"]
fuel = 10
measured = 7
tier = "release"
release_by = "keyword"

[groups.demo-filled-7]
paths = ["tests/test_filled.py"]
fuel = 10
measured = 7
tier = "release"
release_by = "keyword"

[[split]]
file = "tests/test_filled.py"
groups = ["demo-filled-1", "demo-filled-7"]
keywords = ["corner_mask"]

[groups.demo-lines-1]
paths = ["tests/test_lines.py"]
fuel = 10
measured = 7
tier = "release"
release_by = "keyword"

[groups.demo-slow]
paths = ["tests/test_misc.py", "tests/test_filled.py", "tests/test_lines.py"]
fuel = 10
measured = 7
tier = "release"
release_by = "marker"
"""


def _numpy(text: str = NUMPY, tmp: Path | None = None) -> upstream.Config:
    return upstream.from_raw(tomllib.loads(text), Path("."))


def _contour(text: str = CONTOUR) -> upstream.Config:
    return packages.load(tomllib.loads(text))


def _errors(cfg: upstream.Config) -> list[str]:
    return tiers.rule_errors(cfg.package, cfg)


# ---------------------------------------------------------------------------------------------
# The rules


def test_the_well_formed_families_have_no_tier_error() -> None:
    assert _errors(_numpy()) == []
    assert _errors(_contour()) == []
    assert packages.split_errors("demo", _contour()) == []


def test_the_judges_own_files_have_no_tier_error() -> None:
    for pkg, cfg in upstream.load_all().items():
        assert tiers.rule_errors(pkg, cfg) == [], pkg


BAD_NUMPY = [
    # the two markers overlap
    (('release_marker = "slow"', 'release_marker = "slow or leaks_references"'), "overlap"),
    # their union is not the whole suite, and nothing says what is excluded
    (('marker = "not slow"', 'marker = "not slow and not network"'), "is not every test"),
    # a marker with keyword arguments cannot be evaluated
    (('release_marker = "slow"', 'release_marker = "slow(reason=1)"'), "keyword arguments"),
    # what may be excluded is a closed list
    (
        ('release_marker = "slow"', 'release_marker = ""\nexcluded_marker = "slow"'),
        "excluded_marker names slow",
    ),
    # a release marker may not select an excluded test
    (
        (
            'marker = "not slow"',
            'marker = "not slow and not network"\nexcluded_marker = "network"\n'
            'excluded_reason = "r"\nexcluded_closes_with = "README.md"',
        ),
        "selects an excluded test",
    ),
    # a tier is one of two
    (('tier = "release"', 'tier = "fast"'), "tier 'fast'"),
    # a release group carries its measured fuel, and a cap by the rule
    (("measured = 100\n", ""), "np-slow records no measured fuel"),
    (("fuel = 150\n", "fuel = 160\n"), "np-slow's cap 160 is above"),
    # the marker release groups cover exactly the normal groups' paths
    (
        ('paths = ["numpy/_core/tests", "numpy/lib/tests"]', 'paths = ["numpy/_core/tests"]'),
        "marker release groups' paths",
    ),
    # a trap in a family with release groups names its group
    (
        (
            'args = ["-p", "no:cacheprovider"]',
            'args = []\n[[trap]]\nid = "t1"\n'
            'node = "numpy/lib/tests/test_x.py::test_y"\nreason = "r"\ncloses_with = "README.md"',
        ),
        "trap t1 names no group",
    ),
]


@pytest.mark.parametrize(("change", "error"), BAD_NUMPY)
def test_each_bad_numpy_tier_is_named(change, error) -> None:
    old, new = change
    assert NUMPY.count(old) == 1, old
    errors = _errors(_numpy(NUMPY.replace(old, new)))
    assert any(error in e for e in errors), errors


def test_excluded_marker_needs_a_reason_and_makes_the_union_whole() -> None:
    text = NUMPY.replace(
        'marker = "not slow"',
        'marker = "not slow and not network"\nexcluded_marker = "network"\n'
        'excluded_reason = "no network in the guest"\nexcluded_closes_with = "README.md"',
    ).replace('release_marker = "slow"', 'release_marker = "slow and not network"')
    assert _errors(_numpy(text)) == []
    assert any(
        "excluded_reason" in e for e in _errors(_numpy(text.replace("no network in the guest", "")))
    )


def test_a_plain_release_group_in_a_family_with_no_selection_is_refused() -> None:
    text = NUMPY.replace('release_marker = "slow"\n', "")
    assert any("of no named kind" in e for e in _errors(_numpy(text)))


BAD_CONTOUR = [
    # a keyword entry without a reason
    (('reason = "the package\'s own selection for slow hosts"', 'reason = ""'), "no reason"),
    # a keyword that does not parse
    (('keyword = "random_big"', 'keyword = "random_big and"'), "does not parse"),
    # an entry naming a file no group covers
    (
        (
            'files = ["tests/test_filled.py", "tests/test_lines.py"]',
            'files = ["tests/test_filled.py", "tests/test_lines.py", "tests/test_gone.py"]',
        ),
        "tests/test_gone.py, a file no group covers",
    ),
    # keyword release groups whose paths are not exactly the entries' files
    (
        (
            '[groups.demo-lines-1]\npaths = ["tests/test_lines.py"]',
            '[groups.demo-lines-1]\npaths = ["tests/test_filled.py"]',
        ),
        "keyword release groups' paths",
    ),
    # a split that mixes tiers
    (
        (
            'groups = ["demo-filled-1", "demo-filled-7"]',
            'groups = ["demo-filled-1", "demo-filled-8"]',
        ),
        "mixes tiers",
    ),
    # a release group with no release_by where the family has both kinds
    (('tier = "release"\nrelease_by = "marker"', 'tier = "release"'), "names no release_by"),
    # a normal group over an entry's file and another file
    (
        (
            '[groups.demo-lines-8]\npaths = ["tests/test_lines.py"]',
            '[groups.demo-lines-8]\npaths = ["tests/test_lines.py", "tests/test_other.py"]',
        ),
        "an entry's file beside others",
    ),
]


@pytest.mark.parametrize(("change", "error"), BAD_CONTOUR)
def test_each_bad_contour_tier_is_named(change, error) -> None:
    old, new = change
    assert CONTOUR.count(old) == 1, old
    cfg = _contour(CONTOUR.replace(old, new))
    errors = _errors(cfg) + packages.split_errors("demo", cfg)
    assert any(error in e for e in errors), errors


# ---------------------------------------------------------------------------------------------
# The argv: a normal group's is today's unless an entry names its file


def test_a_normal_numpy_group_keeps_its_argv_and_the_release_group_takes_its_marker() -> None:
    cfg = _numpy()
    plain = _numpy(
        NUMPY.replace('release_marker = "slow"\n', "").replace("[groups.np-slow]", "[x]")
    )
    for name in ("np-core", "np-lib"):
        assert upstream.group_spec(cfg, cfg.groups[name]) == upstream.group_spec(
            plain, plain.groups[name]
        )
    args = upstream.group_spec(cfg, cfg.groups["np-slow"])["args"]
    assert args[:2] == ["-m", "slow"] and not any(a.startswith("-k") for a in args)


def test_the_judges_own_normal_groups_keep_their_argv() -> None:
    """With no release fields, a group's JSON is what it was before there were tiers: the tier
    filter is empty and the marker is the family's."""
    for cfg in upstream.load_all().values():
        for g in cfg.groups.values():
            if g.tier != "normal" or cfg.runner == "regrtest":
                continue
            assert tiers.tier_filter(cfg, g) is None
            assert tiers.marker_of(cfg, g) == cfg.marker


def test_contour_argv_by_tier_and_kind() -> None:
    cfg = _contour()
    a = packages.group_args
    g = cfg.groups
    assert a(cfg, g["demo-rest"])[:2] == ["-m", "not slow"]
    assert not any(x.startswith("-k") for x in a(cfg, g["demo-rest"]))
    assert a(cfg, g["demo-lines-8"])[-1] == "-knot (random_big)"
    assert a(cfg, g["demo-filled-12"])[-1] == "-k(not (random_big)) and (not ((serial)))"
    assert a(cfg, g["demo-filled-8"])[-1] == "-k(not (random_big)) and ((serial))"
    assert a(cfg, g["demo-filled-1"])[:2] == ["-m", "not slow"]
    assert a(cfg, g["demo-filled-1"])[-1] == "-k(random_big) and ((corner_mask))"
    assert a(cfg, g["demo-filled-7"])[-1] == "-k(random_big) and (not ((corner_mask)))"
    assert a(cfg, g["demo-lines-1"])[-1] == "-krandom_big"
    assert a(cfg, g["demo-slow"])[:2] == ["-m", "slow"]
    assert not any(x.startswith("-k") for x in a(cfg, g["demo-slow"]))


def test_the_stage_never_depends_on_the_tier() -> None:
    """Every group's JSON, both tiers', is staged: the tier picks the checks that run, never
    what the guest sees."""
    cfg = _numpy()
    assert set(upstream.judge_specs(cfg)) == {"np-core", "np-lib", "np-slow"}


# ---------------------------------------------------------------------------------------------
# CPython: the release lists and the partition


def _py(entries=(), **kw) -> upstream.Config:
    groups = {
        "g": upstream.Group("g", (), 10**9, ("test_a", "test_b"), "python/g.txt"),
        "r": upstream.Group(
            "r",
            (),
            10**9,
            ("test_a",),
            "python/r.txt",
            tier="release",
            measured=10**9,
        ),
    }
    base = dict(
        package="python",
        marker="",
        args=[],
        path_packages=[],
        markers=[],
        support=[],
        groups=groups,
        not_selected=[],
        traps=[],
        expected=[],
        runner="regrtest",
        component="cpython",
        grant=regrtest.GRANT,
        resources="all,-cpu,-gui,-largefile",
        release_resources="all,-gui",
        options=(),
        warnings="error",
        release_entries=list(entries),
    )
    base.update(kw)
    return upstream.Config(**base)


GATED = regrtest.ReleaseEntry("test.test_a.T.test_long", "gated", "g", "r")
INLINE = regrtest.ReleaseEntry("test.test_a.T.test_more", "inline", "g", "r")
LISTED = "L test_a\nL test_b\n"
NORMAL = (
    LISTED
    + "C test_a\nS test.test_a.T.test_long\n"
    + "R skipped test.test_a.T.test_long -- resource 'cpu' is not enabled\n"
    + "S test.test_a.T.test_more\nR passed test.test_a.T.test_more -- \n"
    + "D test_a PASSED kept\nC test_b\nD test_b PASSED kept\nE 0\n"
)
RELEASE = (
    LISTED
    + "C test_a\nS test.test_a.T.test_long\nR passed test.test_a.T.test_long -- \n"
    + "S test.test_a.T.test_more\nR passed test.test_a.T.test_more -- \n"
    + "D test_a PASSED kept\nE 0\n"
)


def _judge(text: str, group: str, cfg=None) -> list[str]:
    cfg = cfg or _py([GATED, INLINE])
    run = regrtest.GuestRun(0, None, None, 10**9, "")
    return regrtest.judge_group(regrtest.parse_stream(text), run, cfg, group, "darwin").findings


def test_a_normal_stream_whose_resource_skips_equal_the_list_passes() -> None:
    assert _judge(NORMAL, "g") == []


def test_an_unlisted_resource_skip_is_a_finding() -> None:
    text = NORMAL.replace(
        "D test_a",
        "S test.test_a.T.test_x\nR skipped test.test_a.T.test_x -- Use of the "
        "'largefile' resource not enabled\nD test_a",
    )
    assert any("test.test_a.T.test_x: skipped for" in f for f in _judge(text, "g"))


def test_a_listed_gated_test_that_was_not_gated_is_a_finding() -> None:
    text = NORMAL.replace(
        "R skipped test.test_a.T.test_long -- resource 'cpu' is not enabled",
        "R passed test.test_a.T.test_long -- ",
    )
    assert any("test.test_a.T.test_long: listed gated" in f for f in _judge(text, "g"))


def test_a_module_denied_its_resource_but_unlisted_is_a_finding() -> None:
    text = NORMAL.replace("D test_b PASSED kept", "D test_b RESOURCE_DENIED kept")
    assert any("test_b: skipped for" in f for f in _judge(text, "g"))
    module = regrtest.ReleaseEntry("test_b", "gated", "g", "r")
    assert _judge(text, "g", _py([GATED, INLINE, module])) == []


def test_an_inline_test_missing_from_its_normal_group_is_a_finding() -> None:
    text = NORMAL.replace("S test.test_a.T.test_more\nR passed test.test_a.T.test_more -- \n", "")
    assert any("test.test_a.T.test_more: an inline test" in f for f in _judge(text, "g"))


def test_a_release_stream_must_run_every_listed_test_with_its_resource() -> None:
    assert _judge(RELEASE, "r") == []
    skipped = RELEASE.replace(
        "R passed test.test_a.T.test_long -- ",
        "R skipped test.test_a.T.test_long -- resource 'cpu' is not enabled",
    )
    assert any("test.test_a.T.test_long: skipped for" in f for f in _judge(skipped, "r"))
    missing = RELEASE.replace(
        "S test.test_a.T.test_more\nR passed test.test_a.T.test_more -- \n", ""
    )
    assert any("test.test_a.T.test_more: listed, did not run" in f for f in _judge(missing, "r"))


def test_without_release_lists_there_is_no_partition() -> None:
    """Before a family has release lists, its normal groups' resource skips are what they were."""
    assert _judge(NORMAL, "g", _py([], groups={"g": _py().groups["g"]})) == []


def test_the_release_groups_json_matches_its_ids_with_the_release_resources() -> None:
    cfg = _py([GATED, INLINE, regrtest.ReleaseEntry("test_b", "gated", "g", "r")])
    spec = regrtest.group_spec(cfg, "r")
    assert spec["resources"] == "all,-gui" and spec["ignore"] == []
    assert spec["match"] == ["test.test_a.T.test_long", "test.test_a.T.test_more", "test.test_b.*"]
    assert spec["modules"] == ["test_a", "test_b"]
    normal = regrtest.group_spec(cfg, "g")
    assert normal["resources"] == "all,-cpu,-gui,-largefile" and "match" not in normal


def test_a_release_plan_line_is_parsed_and_checked(tmp_path) -> None:
    (tmp_path / "python").mkdir()
    (tmp_path / "python" / "r.txt").write_text(
        "test.test_a.T.test_long gated g\ntest.test_a.T.test_more inline g\n"
    )
    entries = regrtest.read_release_plan(tmp_path, "python/r.txt", "r")
    assert entries == [GATED, INLINE]
    (tmp_path / "python" / "r.txt").write_text("test.test_a.T.test_long sometimes\n")
    with pytest.raises(ValueError, match="not <id> <gated|inline> <group>"):
        regrtest.read_release_plan(tmp_path, "python/r.txt", "r")


def test_the_release_list_rules() -> None:
    assert regrtest.release_errors(_py([GATED, INLINE])) == []
    stray = regrtest.ReleaseEntry("test.test_z.T.test_q", "gated", "g", "r")
    assert any("in no module of g" in e for e in regrtest.release_errors(_py([GATED, stray])))
    twice = regrtest.release_errors(_py([GATED, GATED]))
    assert any("listed twice" in e for e in twice)
    no_res = regrtest.release_errors(_py([GATED], release_resources=""))
    assert any("release_resources" in e for e in no_res)
    to_release = regrtest.ReleaseEntry("test.test_a.T.test_q", "gated", "r", "r")
    assert any("names no normal group" in e for e in regrtest.release_errors(_py([to_release])))


SOURCE = """
from test import support
import unittest

class T(unittest.TestCase):
    def test_more(self):
        n = 1000 if support.is_resource_enabled("cpu") else 10

    def test_other(self):
        pass

class U(unittest.TestCase):
    def test_fifth(self):
        if is_resource_enabled('cpu'):
            pass
"""


def test_the_inline_cpu_tests_are_read_from_the_source() -> None:
    sources = {"Lib/test/test_a.py": SOURCE}
    found = regrtest.inline_cpu_tests(sources, ["test_a", "test_b"])
    assert found == {"test.test_a.T.test_more", "test.test_a.U.test_fifth"}
    errors = regrtest.inline_errors(_py([GATED, INLINE]), sources)
    assert errors == [
        "python: test.test_a.U.test_fifth reads the cpu resource inline, but no "
        "release list names it inline"
    ]
    fifth = regrtest.ReleaseEntry("test.test_a.U.test_fifth", "inline", "g", "r")
    assert regrtest.inline_errors(_py([GATED, INLINE, fifth]), sources) == []
    missing = regrtest.inline_errors(_py([GATED, fifth]), sources)
    assert any("test.test_a.T.test_more reads the cpu resource" in e for e in missing)
