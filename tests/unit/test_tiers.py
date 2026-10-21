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
    """A normal group of a family with no keyword selection runs what it ran before there were
    tiers: no tier filter, and the family's marker."""
    for cfg in upstream.load_all().values():
        for g in cfg.groups.values():
            if g.tier != "normal" or cfg.runner == "regrtest" or cfg.release_select:
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
INLINE = regrtest.ReleaseEntry("test_b", "inline", "g", "r")
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
    + "D test_a PASSED kept\n"
    + "C test_b\nS test.test_b.U.test_all\nR passed test.test_b.U.test_all -- \n"
    + "D test_b PASSED kept\nE 0\n"
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
    text = NORMAL.replace(
        "D test_b PASSED kept",
        "Z test_b -- Use of the 'cpu' resource not enabled\nD test_b RESOURCE_DENIED kept",
    )
    assert any("test_b: skipped for" in f for f in _judge(text, "g"))
    module = regrtest.ReleaseEntry("test_b", "gated", "g", "r")
    assert _judge(text, "g", _py([GATED, module])) == []
    network = NORMAL.replace(
        "D test_b PASSED kept",
        "Z test_b -- Use of the 'network' resource not enabled\nD test_b RESOURCE_DENIED kept",
    )
    assert _judge(network, "g", _py([GATED])) == []  # another resource: not the tiers' business


def test_an_inline_module_missing_from_its_normal_group_is_a_finding() -> None:
    text = NORMAL.replace("C test_b\nD test_b PASSED kept\n", "")
    assert any("test_b: an inline module that did not run" in f for f in _judge(text, "g"))


def test_a_release_stream_must_run_every_listed_test_with_its_resource() -> None:
    assert _judge(RELEASE, "r") == []
    skipped = RELEASE.replace(
        "R passed test.test_a.T.test_long -- ",
        "R skipped test.test_a.T.test_long -- resource 'cpu' is not enabled",
    )
    assert any("test.test_a.T.test_long: skipped for" in f for f in _judge(skipped, "r"))
    missing = RELEASE.replace(
        "C test_b\nS test.test_b.U.test_all\nR passed test.test_b.U.test_all -- \n"
        "D test_b PASSED kept\n",
        "",
    )
    assert any("test_b: listed, did not run" in f for f in _judge(missing, "r"))
    gone = RELEASE.replace("S test.test_a.T.test_long\nR passed test.test_a.T.test_long -- \n", "")
    assert any("test.test_a.T.test_long: listed, did not run" in f for f in _judge(gone, "r"))
    # a listed test that then skips for a reason of its own ran in the release tier
    own = RELEASE.replace(
        "R passed test.test_a.T.test_long -- ",
        "R skipped test.test_a.T.test_long -- not enough memory: 8.0G minimum needed",
    )
    assert _judge(own, "r") == []


def test_without_release_lists_there_is_no_partition() -> None:
    """Before a family has release lists, its normal groups' resource skips are what they were."""
    assert _judge(NORMAL, "g", _py([], groups={"g": _py().groups["g"]})) == []


def test_the_release_groups_json_matches_its_ids_with_the_release_resources() -> None:
    cfg = _py([GATED, INLINE])
    spec = regrtest.group_spec(cfg, "r")
    assert spec["resources"] == "all,-gui" and spec["ignore"] == []
    assert spec["match"] == ["test.test_a.T.test_long", "test.test_b.*"]
    assert spec["modules"] == ["test_a", "test_b"]
    normal = regrtest.group_spec(cfg, "g")
    assert normal["resources"] == "all,-cpu,-gui,-largefile" and "match" not in normal


def test_a_release_plan_line_is_parsed_and_checked(tmp_path) -> None:
    (tmp_path / "python").mkdir()
    (tmp_path / "python" / "r.txt").write_text("test.test_a.T.test_long gated g\ntest_b inline g\n")
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


SOURCE_A = "from test import support\nN = 1000 if support.is_resource_enabled('cpu') else 10\n"
SOURCE_B = 'quick = not is_resource_enabled("cpu")\n'


def test_the_inline_cpu_modules_are_read_from_the_source() -> None:
    sources = {"Lib/test/test_a.py": SOURCE_A, "Lib/test/test_b.py": SOURCE_B}
    assert regrtest.inline_cpu_modules(sources, ["test_a", "test_b"]) == {"test_a", "test_b"}
    errors = regrtest.inline_errors(_py([GATED, INLINE]), sources)
    assert errors == [
        "python: test_a reads the cpu resource inline, but no release list names it inline"
    ]
    a = regrtest.ReleaseEntry("test_a", "inline", "g", "r")
    assert regrtest.inline_errors(_py([GATED, INLINE, a]), sources) == []
    gone = regrtest.inline_errors(_py([GATED, INLINE, a]), {"Lib/test/test_a.py": SOURCE_A})
    assert gone == [
        "python: test_b is listed inline, but its source does not read the cpu resource"
    ]
    test_id = regrtest.ReleaseEntry("test.test_a.T.test_x", "inline", "g", "r")
    assert any("an inline entry is a module" in e for e in regrtest.release_errors(_py([test_id])))


def test_only_a_marker_release_group_may_select_nothing() -> None:
    guard = CONTOUR.replace(
        "[groups.demo-slow]\n", '[groups.demo-slow]\nselects_nothing = "a guard"\n'
    )
    assert _errors(_contour(guard)) == []
    normal = CONTOUR.replace(
        '[groups.demo-rest]\npaths = ["tests/test_misc.py"]',
        '[groups.demo-rest]\nselects_nothing = "no"\npaths = ["tests/test_misc.py"]',
    )
    assert any(
        "only a marker release group may select nothing" in e for e in _errors(_contour(normal))
    )


# ---------------------------------------------------------------------------------------------
# The smoke kind: a package's own suite in the release tier whole, a small smoke group normal

SMOKE = """
package = "demo"
driver = "package"
grant = "/upstream-demo"
budget = 10_000
stage_folders = ["pkg"]
cwd = "/tmp/work"

[groups.demo-smoke]
paths = ["pkg/a/tests/test_x.py"]
fuel = 15
measured = 10
smoke = "imports the package and runs its core path"

[groups.demo-a]
paths = ["pkg/a/tests"]
fuel = 15
measured = 10
tier = "release"

[groups.demo-b]
paths = ["pkg/b/tests"]
fuel = 15
measured = 10
tier = "release"
"""
SMOKE_MEMBERS = {
    "pkg/a/__init__.py",
    "pkg/a/tests/test_x.py",
    "pkg/a/tests/test_y.py",
    "pkg/b/tests/test_z.py",
}


def _smoke_errors(text: str = SMOKE) -> list[str]:
    cfg = _contour(text)
    return tiers.rule_errors("demo", cfg, SMOKE_MEMBERS) + packages.split_errors("demo", cfg)


def test_a_smoke_family_is_clean_and_its_path_groups_run_whole() -> None:
    assert _smoke_errors() == []
    for text in (
        SMOKE,
        SMOKE.replace('cwd = "/tmp/work"', 'cwd = "/tmp/work"\nmarker = "not slow"'),
    ):
        cfg = _contour(text)
        args = packages.group_args(cfg, cfg.groups["demo-a"])
        assert "--ignore=/upstream-demo/tree/pkg/a/tests/test_x.py" in args
        assert "-m" not in args and not any(a.startswith("-k") for a in args)
        assert tiers.kind_of(cfg, cfg.groups["demo-a"]) == "path"


BAD_SMOKE = [
    # a staged test file in neither a smoke path nor a path release group
    (
        ('[groups.demo-b]\npaths = ["pkg/b/tests"]', '[groups.demo-b]\npaths = ["pkg/b/other"]'),
        "pkg/b/tests/test_z.py is in no tier",
    ),
    # a path release group inside a smoke path
    (
        (
            '[groups.demo-b]\npaths = ["pkg/b/tests"]',
            '[groups.demo-b]\npaths = ["pkg/b/tests", "pkg/a/tests/test_x.py"]',
        ),
        "lies in a smoke path",
    ),
    # an empty smoke reason
    (('smoke = "imports the package and runs its core path"', 'smoke = " "'), "smoke is empty"),
    # a normal group without smoke in a smoke family
    (
        (
            "[groups.demo-a]\n",
            '[groups.demo-n]\npaths = ["pkg/c"]\nfuel = 1\nmeasured = 1\n\n[groups.demo-a]\n',
        ),
        "demo-n carries no smoke",
    ),
    # a keyword selection in a smoke family
    (
        (
            'cwd = "/tmp/work"',
            'cwd = "/tmp/work"\n[[release_select]]\nfiles = ["pkg/a/tests/test_y.py"]'
            '\nkeyword = "big"\nreason = "r"',
        ),
        "a smoke family has no [[release_select]]",
    ),
    # smoke past its budget
    (("measured = 10\nsmoke", "measured = 600_000_000_000\nsmoke"), "past the 500 G smoke budget"),
    # a test file under two path release groups
    (
        (
            "[groups.demo-b]\n",
            '[groups.demo-a2]\npaths = ["pkg/a/tests/test_y.py"]\nfuel = 15\n'
            'measured = 10\ntier = "release"\n\n[groups.demo-b]\n',
        ),
        "under two path release groups",
    ),
]


@pytest.mark.parametrize(("change", "error"), BAD_SMOKE)
def test_each_bad_smoke_family_is_named(change, error) -> None:
    old, new = change
    assert SMOKE.count(old) == 1, old
    errors = _smoke_errors(SMOKE.replace(old, new))
    assert any(error in e for e in errors), errors


def test_a_path_group_outside_a_smoke_family_is_of_no_named_kind() -> None:
    text = NUMPY.replace('tier = "release"', 'tier = "release"\nrelease_by = "path"').replace(
        'release_marker = "slow"\n', ""
    )
    assert any("of no named kind" in e for e in _errors(_numpy(text)))


def test_a_smoke_family_with_a_release_marker_needs_it_over_the_smoke_paths() -> None:
    marked = SMOKE.replace(
        'cwd = "/tmp/work"', 'cwd = "/tmp/work"\nmarker = "not slow"\nrelease_marker = "slow"'
    ).replace('tier = "release"\n', 'tier = "release"\nrelease_by = "path"\n')
    assert any("marker release groups' paths" in e for e in _smoke_errors(marked))
    guarded = marked + (
        '\n[groups.demo-smoke-slow]\npaths = ["pkg/a/tests/test_x.py"]\nfuel = 15\nmeasured = 10\n'
        'tier = "release"\nrelease_by = "marker"\n'
    )
    assert _smoke_errors(guarded) == []
    cfg = _contour(guarded)
    assert packages.group_args(cfg, cfg.groups["demo-smoke-slow"])[:2] == ["-m", "slow"]


# ---------------------------------------------------------------------------------------------
# A smoke family's tiers, collected by pytest itself: every test in exactly one tier

PARTITION = """
package = "demo"
driver = "package"
grant = "/upstream-demo"
budget = 1000
stage_folders = ["pkg/a/tests", "pkg/b/tests"]
marker = "not slow"
release_marker = "slow"
cwd = "/tmp/work"

[groups.demo-smoke]
paths = ["pkg/a/tests/test_x.py", "pkg/a/tests/test_y.py"]
smoke = "two files that call the package's compiled code"
fuel = 30
measured = 20

[groups.demo-smoke-slow]
paths = ["pkg/a/tests/test_x.py", "pkg/a/tests/test_y.py"]
tier = "release"
release_by = "marker"
fuel = 30
measured = 20

[groups.demo-a]
paths = ["pkg/a/tests"]
tier = "release"
release_by = "path"
fuel = 30
measured = 20

[groups.demo-b]
paths = ["pkg/b/tests"]
tier = "release"
release_by = "path"
fuel = 30
measured = 20
"""
TESTS = {
    "pkg/a/tests/test_x.py": "import pytest\n\ndef test_x1(): pass\n\n"
    "@pytest.mark.slow\ndef test_x2(): pass\n",
    "pkg/a/tests/test_y.py": "def test_y1(): pass\n",
    "pkg/a/tests/test_w.py": "import pytest\n\ndef test_w1(): pass\n\n"
    "@pytest.mark.slow\ndef test_w2(): pass\n",
    "pkg/b/tests/test_z.py": "def test_z1(): pass\n",
}


def _collected(tree: Path, args: list[str]) -> list[str]:
    """The node ids pytest selects for one group's argv, collected in this process."""

    class Seen:
        def __init__(self) -> None:
            self.ids: list[str] = []

        def pytest_collection_finish(self, session) -> None:
            self.ids = [item.nodeid for item in session.items]

    seen = Seen()
    ini = tree / "demo.ini"
    ini.write_text("[pytest]\nmarkers =\n    slow: a slow test\n")
    argv = [
        "--collect-only",
        "-q",
        "-p",
        "no:faulthandler",
        "-p",
        "no:cacheprovider",
        "--import-mode=importlib",
        f"--rootdir={tree}",
        "-c",
        str(ini),
        *[a.replace("/upstream-demo/tree", str(tree)) for a in args],
    ]
    assert pytest.main(argv, plugins=[seen]) in (0, 5)
    return seen.ids


def test_every_collected_test_of_a_smoke_family_is_in_exactly_one_tier(tmp_path) -> None:
    """The owner's rule, by collection: the smoke group over two files and the release groups
    over all of them select each test once, none in both tiers and none in neither."""
    tree = tmp_path / "tree"
    for rel, text in TESTS.items():
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_text(text)
    cfg = packages.load(tomllib.loads(PARTITION))
    assert tiers.rule_errors("demo", cfg, set(TESTS)) == []
    every = _collected(tree, [str(tree / "pkg")])
    by_tier: dict[str, list[str]] = {"normal": [], "release": []}
    for g in cfg.groups.values():
        by_tier[g.tier] += _collected(tree, packages.group_args(cfg, g))
    normal, release = by_tier["normal"], by_tier["release"]
    assert sorted(normal) == ["pkg/a/tests/test_x.py::test_x1", "pkg/a/tests/test_y.py::test_y1"]
    assert len(release) == len(set(release))  # no test in two release groups
    assert not set(normal) & set(release)  # none in both tiers
    assert sorted(normal + release) == sorted(every)  # none in neither
