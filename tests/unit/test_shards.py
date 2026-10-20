"""The shard plan, the selection and every package's suite (acceptances 1, 2 and 7)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from harness import shards

U = shards.UPSTREAM_FILE
FILES = [
    "tests/checks/test_a.py",
    "tests/checks/test_b.py",
    "tests/unit/test_c.py",
    "tests/unit/test_d.py",
    "tests/test_e.py",
    U,
]
GROUPS = ["g1", "g2", "g3"]
PLAN_TEXT = """
[shard.build]
files = ["tests/checks/test_a.py"]
systems = ["build"]

[shard.own-1]
files = ["tests/checks/test_b.py", "tests/unit/test_c.py"]
systems = ["macos", "linux", "windows"]

[shard.own-rest]
rest = true
systems = ["macos", "linux", "windows"]

[shard.up-1]
groups = ["g1", "g2"]
systems = ["linux"]

[shard.up-2]
groups = ["g3"]
systems = ["linux"]

[shard.up-mac]
groups = ["g2"]
systems = ["macos"]
"""


# Spec 101: a shard that takes one function of own-1's file, on own-1's systems.
OWN_2 = """[shard.own-2]
nodes = ["tests/checks/test_b.py::test_x"]
systems = ["macos", "linux", "windows"]

"""


def _plan(text: str = PLAN_TEXT, tmp: Path | None = None) -> dict:
    return {
        name: shards.Shard(
            name,
            tuple(s.get("systems", ())),
            tuple(s.get("files", ())),
            tuple(s.get("groups", ())),
            bool(s.get("rest", False)),
            tuple(s.get("nodes", ())),
        )
        for name, s in tomllib.loads(text)["shard"].items()
    }


def test_the_good_plan_passes() -> None:
    assert shards.plan_errors(_plan(), FILES, GROUPS) == []


BAD_PLANS = [
    (('files = ["tests/checks/test_a.py"]', 'files = ["tests/checks/test_zz.py"]'), "(a) build:"),
    (('groups = ["g3"]', 'groups = ["g3", "g9"]'), "(c) up-2: g9 is not an upstream group"),
    (
        (
            'files = ["tests/checks/test_b.py", "tests/unit/test_c.py"]',
            'files = ["tests/checks/test_a.py"]',
        ),
        "(a) tests/checks/test_a.py is in two shards",
    ),
    (("rest = true\n", 'files = ["tests/unit/test_d.py"]\n'), "(b) 0 shards are rest"),
    (
        (
            "[shard.up-1]",
            '[shard.rest-2]\nrest = true\nsystems = ["macos", "linux", "windows"]\n\n[shard.up-1]',
        ),
        "(b) 2 shards are rest",
    ),
    (
        (
            'files = ["tests/checks/test_b.py", "tests/unit/test_c.py"]',
            'files = ["tests/checks/test_b.py", "tests/unit/test_c.py", "tests/unit/test_d.py", '
            '"tests/test_e.py"]',
        ),
        "(b) every test file is listed",
    ),
    (('groups = ["g3"]', 'groups = ["g2"]'), "(c) upstream group g2 is in 2 Linux shards"),
    (('groups = ["g1", "g2"]', 'groups = ["g1"]'), "(c) upstream group g2 is in 0 Linux shards"),
    (
        (
            'rest = true\nsystems = ["macos", "linux", "windows"]',
            'rest = true\nsystems = ["macos", "windows"]',
        ),
        "(e) own-rest does not run on macos and linux",
    ),
    (
        (
            'test_c.py"]\nsystems = ["macos", "linux", "windows"]',
            'test_c.py"]\nsystems = ["macos", "linux"]',
        ),
        "(e) own-1 does not run on all of",
    ),
    (('systems = ["build"]', 'systems = ["build", "linux"]'), "(d) build: only the shard build"),
    (
        ('groups = ["g3"]\nsystems = ["linux"]', 'groups = ["g3"]\nsystems = ["linux", "beos"]'),
        "(d) up-2: unknown system",
    ),
    (
        (
            '[shard.up-mac]\ngroups = ["g2"]',
            '[shard.up-mac]\ngroups = ["g1"]\nsystems = ["macos"]\n\n'
            '[shard.up-mac2]\ngroups = ["g1"]',
        ),
        "(f) on macos, g1 is in up-mac and up-mac2",
    ),
    (
        ('files = ["tests/checks/test_b.py",', f'files = ["{U}", "tests/checks/test_b.py",'),
        "(a) own-1: the upstream file",
    ),
]


@pytest.mark.parametrize(("change", "error"), BAD_PLANS, ids=[e for _, e in BAD_PLANS])
def test_each_bad_plan_is_named(change, error) -> None:
    old, new = change
    assert PLAN_TEXT.count(old) == 1, old
    # With the upstream file, rest always holds its rules check; without it, rest can be empty.
    files = [f for f in FILES if f != U] if error.startswith("(b) every") else FILES
    errors = shards.plan_errors(_plan(PLAN_TEXT.replace(old, new)), files, GROUPS)
    assert any(e.startswith(error) for e in errors), errors


# The selection (acceptance 2): a synthetic collection.
NODES = [
    "tests/checks/test_a.py::test_x",
    "tests/checks/test_b.py::test_y",
    "tests/unit/test_c.py::test_u1",
    "tests/unit/test_d.py::test_u2",
    "tests/test_e.py::test_top",
    f"{U}::test_upstream_suite[g1]",
    f"{U}::test_upstream_class[g1-k]",
    f"{U}::test_upstream_suite[g2]",
    f"{U}::test_upstream_suite[g3]",
    f"{U}::test_upstream_trap[t1]",
    f"{U}::test_upstream_files_are_well_formed",
    "tests/checks/test_b_more.py::test_new",
]
GROUP_OF = {
    f"{U}::test_upstream_suite[g1]": "g1",
    f"{U}::test_upstream_class[g1-k]": "g1",
    f"{U}::test_upstream_suite[g2]": "g2",
    f"{U}::test_upstream_suite[g3]": "g3",
    f"{U}::test_upstream_trap[t1]": "g3",
}


def test_each_shard_selects_exactly_its_items() -> None:
    got = shards.select(NODES, _plan(), GROUP_OF)
    assert got == {
        "build": ["tests/checks/test_a.py::test_x"],
        "own-1": ["tests/checks/test_b.py::test_y", "tests/unit/test_c.py::test_u1"],
        "own-rest": [
            "tests/unit/test_d.py::test_u2",
            "tests/test_e.py::test_top",
            f"{U}::test_upstream_files_are_well_formed",
            "tests/checks/test_b_more.py::test_new",  # a new file lands in rest, not by prefix
        ],
        "up-1": [
            f"{U}::test_upstream_suite[g1]",
            f"{U}::test_upstream_class[g1-k]",
            f"{U}::test_upstream_suite[g2]",
        ],
        "up-2": [f"{U}::test_upstream_suite[g3]", f"{U}::test_upstream_trap[t1]"],
        "up-mac": [f"{U}::test_upstream_suite[g2]"],
    }


def test_every_item_is_in_one_shard_per_system() -> None:
    plan = _plan()
    got = shards.select(NODES, plan, GROUP_OF)
    for system in shards.SYSTEMS:
        seen = [n for name in shards.on(plan, system) for n in got[name]]
        assert len(seen) == len(set(seen)), system
    union = {n for items in got.values() for n in items}
    assert union == set(NODES)


def test_the_real_plan_takes_every_upstream_check_by_its_group() -> None:
    groups = shards.group_of()
    assert groups, "no upstream group checks"
    plan = shards.load()
    got = shards.select(sorted(groups), plan, groups)
    assert not [n for n in got["own-rest"] if n in groups]
    linux = {n for name in shards.on(plan, "linux") for n in got[name]}
    assert linux == set(groups)


def test_the_units_digest_is_the_sorted_ids() -> None:
    assert shards.units_digest(["b", "a"]) == shards.units_digest(["a", "b"])
    assert shards.units_digest(["a"]) != shards.units_digest(["a", "b"])


# Every package names its own suite (acceptance 7).
PACKAGES_TEXT = """
stdlib_modules = ["zlib"]

[package.numpy]
kind = "suite"

[package.python]
kind = "later"
reason = "not yet"
closes_with = "spec 065"

[package.zlib]
kind = "via"
via = "zlib"

[package.qhull]
kind = "via"
via = "mpl"

[package.mpl]
kind = "later"
reason = "not yet"
closes_with = "spec 001"

[package.wasi-libc]
kind = "via"
via = "python"

[package.pybind11]
kind = "build-only"
reason = "headers"
"""
NAMES = ["mpl", "numpy", "pybind11", "python", "qhull", "wasi-libc", "zlib"]


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "context" / "specifications").mkdir(parents=True)
    (tmp_path / "context" / "specifications" / "001-a.md").write_text("x")
    (tmp_path / "context" / "roadmap.md").write_text("Text.\n\nReserved: 065 (a thing).\n")
    return tmp_path


def _pkg(text: str, repo: Path, names=NAMES) -> list[str]:
    return shards.package_errors(tomllib.loads(text), names, {"numpy": 3}, repo)


def test_the_good_packages_file_passes(repo) -> None:
    assert _pkg(PACKAGES_TEXT, repo) == []


BAD_PACKAGES = [
    (('[package.numpy]\nkind = "suite"\n', ""), "numpy: no entry"),
    (('[package.qhull]\nkind = "via"\nvia = "mpl"\n', ""), "qhull: no entry"),
    (('[package.wasi-libc]\nkind = "via"\nvia = "python"\n', ""), "wasi-libc: no entry"),
    (
        (
            "[package.pybind11]",
            '[package.ghost]\nkind = "build-only"\nreason = "x"\n\n[package.pybind11]',
        ),
        "ghost: an entry for no component",
    ),
    (
        (
            '[package.numpy]\nkind = "suite"',
            '[package.numpy]\nkind = "suite"\n\n[package.zz]\nkind = "suite"',
        ),
        "zz: an entry for no",
    ),
    (('via = "zlib"', 'via = ""'), "zlib: via '' is not"),
    (('via = "zlib"', 'via = "gzip"'), "zlib: via 'gzip' is not"),
    (('via = "python"', 'via = "qhull"'), "wasi-libc: via 'qhull' is not"),
    (('closes_with = "spec 065"', 'closes_with = "context/roadmap.md"'), "python: closes_with"),
    (('closes_with = "spec 065"', 'closes_with = "spec 099"'), "python: closes_with"),
    (('kind = "build-only"', 'kind = "maybe"'), "pybind11: unknown kind"),
]


@pytest.mark.parametrize(("change", "error"), BAD_PACKAGES, ids=[e for _, e in BAD_PACKAGES])
def test_each_bad_packages_file_is_named(change, error, repo) -> None:
    old, new = change
    assert PACKAGES_TEXT.count(old) == 1, old
    names = NAMES + (["zz"] if "zz" in new else [])
    errors = _pkg(PACKAGES_TEXT.replace(old, new), repo, names)
    if error.startswith("zz"):
        errors = shards.package_errors(
            tomllib.loads(PACKAGES_TEXT.replace(old, new)), names, {"numpy": 3}, repo
        )
        assert any(e.startswith("zz: kind suite") for e in errors), errors
        return
    assert any(e.startswith(error) for e in errors), errors


def test_a_suite_without_groups_is_named(repo) -> None:
    errors = shards.package_errors(tomllib.loads(PACKAGES_TEXT), NAMES, {"numpy": 0}, repo)
    assert errors == ["numpy: kind suite, but no tests/upstream/numpy.toml with a group"]


def test_the_components_are_the_packages_the_sources_and_the_runtimes() -> None:
    names = shards.components()
    assert {"qhull", "python", "sqlite-autoconf", "wasi-libc", "llvm-runtimes", "numpy"} <= set(
        names
    )
    assert "cpython" not in names and "sqlite" not in names


@pytest.mark.parametrize(
    "new",
    ["tests/checks/test_v1_9_new.py", "tests/unit/test_runner_new.py", "tests/unit/test_cli.py"],
)
def test_a_product_file_left_to_rest_is_named(new) -> None:
    """Rule (g): a product check file or a runner unit file that no files shard on all three
    systems names would fall to rest, off Windows; the plan names it."""
    assert shards.plan_errors(_plan(), FILES, GROUPS) == []
    errors = shards.plan_errors(_plan(), [*FILES, new], GROUPS)
    assert errors == [f"(g) {new} is a product file in no files shard on all three systems"]


def test_a_product_file_in_a_shard_off_windows_is_named() -> None:
    text = PLAN_TEXT.replace(
        "[shard.up-1]",
        '[shard.mac-lin]\nfiles = ["tests/checks/test_z.py"]\n'
        'systems = ["macos", "linux"]\n\n[shard.up-1]',
    )
    errors = shards.plan_errors(_plan(text), [*FILES, "tests/checks/test_z.py"], GROUPS)
    assert (
        "(g) tests/checks/test_z.py is a product file in no files shard on all three systems"
        in errors
    )


def test_the_rules_the_upstream_file_and_tooling_may_stay_in_rest() -> None:
    files = [*FILES, "tests/checks/test_rules.py", "tests/unit/test_scan.py"]
    assert shards.plan_errors(_plan(), files, GROUPS) == []


def test_a_check_named_by_node_goes_to_the_build_shard_alone() -> None:
    """One check of a product file, named by node id in the build shard,
    runs there only; the rest of its file stays where its file is."""
    text = PLAN_TEXT.replace(
        'systems = ["build"]',
        'systems = ["build"]\nnodes = ["tests/checks/test_b.py::test_cli"]',
        1,
    )
    nodes = ["tests/checks/test_b.py::test_cli", "tests/checks/test_b.py::test_y"]
    got = shards.select(nodes, _plan(text), {})
    assert got["build"] == ["tests/checks/test_b.py::test_cli"]
    assert got["own-1"] == ["tests/checks/test_b.py::test_y"]


@pytest.mark.parametrize(
    ("change", "error"),
    [
        (  # spec 101: a shard may name checks, but runs where their file's shard runs
            (
                "[shard.up-1]",
                OWN_2.replace('"macos", "linux", "windows"', '"linux"') + "[shard.up-1]",
            ),
            "(h) own-2: runs on ['linux'], not on own-1's systems",
        ),
        (  # spec 101: a shard that names checks and nothing else selects by nodes alone
            ("[shard.up-1]", OWN_2.replace("nodes = ", "files = [] \nnodes = ") + "[shard.up-1]"),
            None,
        ),
        (
            ("[shard.up-1]", OWN_2 + OWN_2.replace("own-2", "own-3") + "[shard.up-1]"),
            "(h) tests/checks/test_b.py::test_x is named twice",
        ),
        (
            ('systems = ["build"]', 'systems = ["build"]\nnodes = ["tests/checks/test_zz.py::t"]'),
            "(h) tests/checks/test_zz.py::t: not a check of a tracked test file",
        ),
        (
            ('systems = ["build"]', 'systems = ["build"]\nnodes = ["a::t", "a::t"]'),
            "(h) a::t is named twice",
        ),
    ],
)
def test_each_bad_node_is_named(change, error) -> None:
    old, new = change
    assert PLAN_TEXT.count(old) == 1, old
    errors = shards.plan_errors(_plan(PLAN_TEXT.replace(old, new)), FILES, GROUPS)
    if error is None:
        assert not [e for e in errors if e.startswith(("(a)", "(h)"))], errors
    else:
        assert any(e.startswith(error) for e in errors), errors


def test_a_shard_names_a_function_and_takes_every_case_of_it() -> None:
    """Spec 101, Decision 9: `file::function` takes each parameter case; the file's other checks
    stay with the file's shard; a whole node id still names one check."""
    plan = _plan(PLAN_TEXT.replace("[shard.up-1]", OWN_2 + "[shard.up-1]"))
    b = "tests/checks/test_b.py"
    nodes = [f"{b}::test_x[1]", f"{b}::test_x[2]", f"{b}::test_xy", f"{b}::test_y"]
    got = shards.select(nodes, plan, {})
    assert got["own-2"] == [f"{b}::test_x[1]", f"{b}::test_x[2]"]
    assert got["own-1"] == [f"{b}::test_xy", f"{b}::test_y"]


def test_a_named_entry_matches_its_function_or_its_node() -> None:
    b = "tests/checks/test_b.py"
    assert shards.names(f"{b}::test_x", f"{b}::test_x")
    assert shards.names(f"{b}::test_x", f"{b}::test_x[a-1]")
    assert not shards.names(f"{b}::test_x", f"{b}::test_xy")
    assert shards.names(f"{b}::test_x[a-1]", f"{b}::test_x[a-1]")
    assert not shards.names(f"{b}::test_x[a-1]", f"{b}::test_x[a-2]")


def test_a_node_whose_file_defines_no_such_check_is_named() -> None:
    """Against the repository: the real plan's node exists; a renamed one does not."""
    from harness import paths, upstream

    files = shards.test_files(paths.tracked_files("tests"))
    groups = [g for c in upstream.load_all().values() for g in c.groups]
    plan = shards.load()
    assert shards.plan_errors(plan, files, groups) == []
    build = plan["build"]
    gone = shards.Shard(
        "build",
        build.systems,
        build.files,
        nodes=("tests/checks/test_v1_2_hostile_guest.py::test_gone",),
    )
    errors = shards.plan_errors({**plan, "build": gone}, files, groups)
    file = "tests/checks/test_v1_2_hostile_guest.py"
    assert f"(h) {file}::test_gone: {file} defines no test_gone" in errors


# ---------------------------------------------------------------------------------------------
# CPython's groups in the plan


def _with_stand_in_traps():
    """The judge's configs with stand-in CPython trap entries: since the 8 MiB guest stack closed
    the nine, none is open, and the rules for one still hold."""
    from dataclasses import replace

    from harness import upstream

    configs = upstream.load_all()
    traps = [
        upstream.Trap("t-c", "", "r", "README.md", "cpython-c", "test.test_x.T.test_c", ""),
        upstream.Trap("t-a", "", "r", "README.md", "cpython-a", "", "test_x"),
        upstream.Trap("t-b", "", "r", "README.md", "cpython-b", "test.test_x.T.test_b", ""),
    ]
    return {**configs, "python": replace(configs["python"], traps=traps)}


def test_a_cpython_trap_goes_with_its_named_group() -> None:
    from harness import upstream

    groups = shards.group_of(_with_stand_in_traps())
    assert groups[upstream.trap_node("t-c")] == "cpython-c"
    assert groups[upstream.trap_node("t-a")] == "cpython-a"
    assert groups[upstream.trap_node("t-b")] == "cpython-b"


def test_cpython_fs_runs_on_three_systems_and_the_archives_on_linux_only() -> None:
    plan = shards.load()
    holders = {
        g: sorted(n for n, s in plan.items() if g in s.groups)
        for g in ("cpython-fs", "cpython-archives")
    }
    assert holders["cpython-fs"] == ["upstream-macos", "upstream-numpy-a", "upstream-windows"]
    assert holders["cpython-archives"] == ["upstream-numpy-b"]
    systems = shards.group_systems(plan)
    assert systems["cpython-fs"] == {"darwin", "linux", "win32"}
    assert systems["cpython-archives"] == {"darwin", "linux"}


def test_cpython_entry_checks_go_with_their_group() -> None:
    groups = shards.group_of()
    f = "tests/checks/test_v1_3_upstream_suites.py"
    assert groups[f"{f}::test_upstream_deselected[cpython-b-capi-event-generation]"] == "cpython-b"
    assert groups[f"{f}::test_upstream_environment[cpython-c-sys-path-bdb]"] == "cpython-c"


def test_stand_in_a_cpython_trap_placed_by_the_path_rule_finds_no_group() -> None:
    """Criterion 6's stand-in: the shard plan's path rule alone gives a regrtest trap (no file) no
    group, so it would fall into `rest`."""

    cfg = _with_stand_in_traps()["python"]
    t = next(t for t in cfg.traps if t.id == "t-c")
    assert not any(
        t.file and t.file.startswith(p + "/") for g in cfg.groups.values() for p in g.paths
    )
