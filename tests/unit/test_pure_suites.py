"""The test-source families (harness.packages, harness.tiers, the fetch and the pin rules): the
tie to the bytes that ship, the extras, the item and node-id groups, the smoke rules and the
partition by path, on fixed inputs, with no guest."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import tarfile
import tomllib
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from harness import packages, paths, scan, tiers, upstream

BASE = """
package = "demo"
driver = "package"
grant = "/upstream-demo"
test_source = true
budget = 1_000_000_000_000
stage_folders = ["tests"]
cwd = "tree"

[groups.demo-smoke]
paths = ["tests/test_a.py"]
smoke = "a few files"
fuel = 30
measured = 20

[groups.demo-r]
paths = ["tests"]
tier = "release"
release_by = "path"
fuel = 30
measured = 20
"""
RELEASE = '\ntier = "release"\nrelease_by = "path"\nfuel = 3\nmeasured = 2\n'
MEMBERS = {"tests/test_a.py", "tests/test_b.py", "tests/helper.py", "tests/data/x.txt"}


def _cfg(text: str = BASE, directory: Path | None = None) -> upstream.Config:
    return packages.load(tomllib.loads(text), directory)


def _errors(cfg, members=MEMBERS) -> list[str]:
    return packages.rule_errors("demo", cfg, members) + tiers.rule_errors("demo", cfg, members)


def test_the_well_formed_family_has_no_error() -> None:
    assert _errors(_cfg()) == []


@pytest.mark.parametrize(
    ("extra", "want"),
    [
        ('kit_extra = ["no-such-wheel"]', "kit_extra no-such-wheel is not in kit-extra.txt"),
        ('cwd_folders = ["tests/data"]', "cwd_folders need cwd = '/tmp/work'"),
        ('sys_flags = ["_not_a_flag"]', "sys_flags _not_a_flag is not one of"),
        ('env = {PATH = "/x"}', "env sets PATH, not one of the family's"),
        ('doctest_setup = ["os:system"]', "doctest_setup os:system is not one of"),
        ('doctest_runner = "pdb:Pdb"', "doctest_runner pdb:Pdb is not one of"),
        ('doctest_checker = "pdb:Pdb"', "doctest_checker pdb:Pdb is not one of"),
    ],
    ids=[
        "an extra not listed",
        "cwd_folders in the tree",
        "a flag not allowed",
        "an env name",
        "a doctest setup not allowed",
        "a doctest runner not allowed",
        "a doctest checker not allowed",
    ],
)
def test_each_source_key_has_its_rule(extra, want) -> None:
    cfg = _cfg(BASE.replace('cwd = "tree"', 'cwd = "tree"\n' + extra, 1))
    assert any(want in e for e in _errors(cfg)), _errors(cfg)


def test_a_cwd_folder_must_be_a_folder_of_the_source() -> None:
    text = BASE.replace('cwd = "tree"', 'cwd = "/tmp/work"\ncwd_folders = ["tests/nowhere"]')
    assert "demo: cwd_folders tests/nowhere is not a folder of the test source" in _errors(
        _cfg(text)
    )


def test_a_second_normal_group_and_a_group_running_nothing_are_refused() -> None:
    text = (
        BASE
        + '\n[groups.demo-other]\npaths = ["tests/test_b.py"]\nsmoke = "more"'
        + "\nfuel = 3\nmeasured = 2\n"
    )
    text += '\n[groups.demo-empty]\ntier = "release"\nrelease_by = "path"\nfuel = 3\nmeasured = 2\n'
    errors = _errors(_cfg(text))
    assert "demo: 2 normal groups; a test-source family has its smoke alone" in errors
    assert "demo: group demo-empty runs nothing: no paths and no items" in errors


def test_a_smoke_group_and_the_smoke_groups_together_are_bounded() -> None:
    big = BASE.replace("measured = 20\n", "measured = 120_000_000_000\n", 1).replace(
        "fuel = 30\n", "fuel = 180_000_000_000\n", 1
    )
    assert any("past 100 G" in e for e in _errors(_cfg(big)))
    many = {f"p{i}": _cfg(big) for i in range(9)}
    assert packages.smoke_total_errors(many) == [
        "the test-source smoke groups measure 1080.0 G together, past 1 T"
    ]


def test_a_staged_support_file_may_be_a_group_path() -> None:
    text = BASE.replace(
        'stage_folders = ["tests"]', 'stage_folders = []\nsupport_files = ["test_one.py"]'
    )
    text = text.replace('paths = ["tests/test_a.py"]', 'paths = ["test_one.py"]')
    text = text.replace('paths = ["tests"]\ntier', 'paths = ["test_one.py::test_x"]\ntier')
    errors = packages.rule_errors("demo", _cfg(text), {"test_one.py"})
    assert not [e for e in errors if "stage folder" in e], errors


def test_upstreams_python_files_name_the_staged_tests(tmp_path) -> None:
    """The widening's (i): a family whose .ini says `python_files = tests_*.py` stages tests_x.py
    as a test file, which then must be in a tier."""
    (tmp_path / "demo.ini").write_text("[pytest]\npython_files = tests_*.py\n")
    text = BASE.replace('paths = ["tests"]\ntier', 'paths = ["tests/test_b.py"]\ntier')
    cfg = _cfg(text, tmp_path)
    assert cfg.keys.python_files == ("tests_*.py",)
    errors = tiers.smoke_errors("demo", cfg, {"tests/tests_x.py", "tests/test_a.py"})
    assert (
        "demo: tests/tests_x.py is in no tier: under no smoke path or path release group" in errors
    )
    assert not tiers.is_test_file(cfg, "tests/conftest.py")


def test_a_docstring_module_is_in_one_group_only() -> None:
    """The widening's (ii): two item groups that both cover one module are refused; a module
    entry covers only itself, a package entry its submodules."""
    text = BASE + (
        '\n[groups.demo-doc-1]\ndocstring_packages = ["demo"]\ntier = "release"\n'
        'release_by = "path"\nfuel = 3\nmeasured = 2\n'
        '\n[groups.demo-doc-2]\ndocstring_modules = ["demo.sub"]\ntier = "release"\n'
        'release_by = "path"\nfuel = 3\nmeasured = 2\n'
    )
    errors = tiers.item_errors("demo", _cfg(text))
    assert errors == [
        "demo: the docstrings of demo.sub and demo are in two groups: demo-doc-2, demo-doc-1"
    ]
    fine = text.replace('docstring_packages = ["demo"]', 'docstring_modules = ["demo"]')
    assert tiers.item_errors("demo", _cfg(fine)) == []


def test_a_module_functions_group_is_a_named_kind() -> None:
    text = BASE + (
        '\n[groups.demo-inline]\nmodule_functions = ["demo.core"]\ntier = "release"\n'
        'release_by = "path"\nfuel = 3\nmeasured = 2\n'
    )
    assert not [e for e in _errors(_cfg(text)) if "named kind" in e], _errors(_cfg(text))


def test_a_node_id_group_is_deselected_by_its_path_group() -> None:
    """The widening's (iii): the node id lies in one path group's paths, whose argv deselects it;
    one in no path group's paths is refused."""
    node = "tests/test_b.py::test_huge"
    text = BASE + f'\n[groups.demo-huge]\npaths = ["{node}"]' + RELEASE
    cfg = _cfg(text)
    assert tiers.node_errors("demo", cfg) == []
    assert f"--deselect={node}" in packages.group_args(cfg, cfg.groups["demo-r"])
    assert f"--deselect={node}" not in packages.group_args(cfg, cfg.groups["demo-huge"])
    lost = _cfg(text.replace("tests/test_b.py::", "other/test_c.py::"))
    assert tiers.node_errors("demo", lost) == [
        "demo: node id other/test_c.py::test_huge lies in 0 path release groups' paths, not one"
    ]


def test_an_item_group_collects_the_empty_folder() -> None:
    text = BASE + '\n[groups.demo-doc]\ndocstring_modules = ["demo"]' + RELEASE
    cfg = _cfg(text)
    args = packages.group_args(cfg, cfg.groups["demo-doc"])
    assert args[-1] == f"/upstream-demo/judge/{packages.NONE}"


def test_docstring_packages_walk_the_shipped_modules_in_order() -> None:
    items = packages.Items(
        docstring_modules=("demo",),
        docstring_packages=("demo.sub",),
        docstring_not_selected=("demo.sub.skipped",),
    )
    mods = [
        "demo",
        "demo.sub",
        "demo.sub.a",
        "demo.sub.b",
        "demo.sub.skipped",
        "demo.sub.skipped.c",
        "demo.sub.tests",
        "demo.sub.tests.test_a",
        "other",
    ]
    assert packages.docstring_list(items, mods) == ["demo", "demo.sub", "demo.sub.a", "demo.sub.b"]


def test_a_test_source_groups_spec_names_its_items_and_flags() -> None:
    text = BASE.replace(
        'cwd = "tree"', 'cwd = "tree"\nsys_flags = ["_running_pytest"]\ndocstring_flags = 8'
    )
    text += '\n[groups.demo-inline]\nmodule_functions = ["demo.core"]' + RELEASE
    cfg = _cfg(text)
    spec = packages.group_spec(cfg, cfg.groups["demo-inline"], {}, ["demo"], ["demo", "demo.core"])
    assert spec["sys_flags"] == ["_running_pytest"]
    assert spec["module_functions"] == ["demo.core"]
    assert spec["docstring_flags"] == 8 and spec["reload_profile"] and spec["mark_deselected"]
    compiled = _cfg(BASE.replace("test_source = true\n", ""))
    spec = packages.group_spec(compiled, compiled.groups["demo-r"], {}, ["demo"])
    assert not {"sys_flags", "module_functions", "reload_profile", "mark_deselected"} & set(spec)


def test_a_doctest_group_carries_upstreams_doctest_setup() -> None:
    """A package whose own doctest runner prepares the printer first, and keeps the display hook
    that printer installs, names that step, its runner and its output checker; the group's spec
    carries them to the driver, which runs the step once before the first example and runs each
    example with that runner and checker."""
    setup = "sympy.testing.runtests:setup_pprint"
    runner = "sympy.testing.runtests:SymPyDocTestRunner"
    checker = "sympy.testing.runtests:SymPyOutputChecker"
    text = BASE.replace(
        'cwd = "tree"',
        f'cwd = "tree"\ndoctest_setup = ["{setup}"]\ndoctest_runner = "{runner}"\n'
        f'doctest_checker = "{checker}"',
    )
    text += '\n[groups.demo-doc]\ndocstring_modules = ["demo.core"]' + RELEASE
    cfg = _cfg(text)
    assert not any("doctest_" in e for e in _errors(cfg))
    spec = packages.group_spec(cfg, cfg.groups["demo-doc"], {}, ["demo"], ["demo", "demo.core"])
    assert spec["doctest_setup"] == [setup]
    assert (spec["doctest_runner"], spec["doctest_checker"]) == (runner, checker)
    plain = _cfg()
    spec = packages.group_spec(plain, plain.groups["demo-r"], {}, ["demo"], ["demo"])
    assert (spec["doctest_setup"], spec["doctest_runner"], spec["doctest_checker"]) == ([], "", "")


def _stream(*lines: str) -> upstream.Stream:
    return upstream.parse_stream("\n".join(lines) + "\n")


def test_a_smoke_group_runs_no_opt_in_test() -> None:
    """A smoke test skipped for the family's opt-in, or deselected by its marker, is red; a
    family whose marker leaves tests out for a named reason may deselect them in every group."""
    cfg = _cfg(
        BASE.replace(
            'cwd = "tree"', 'cwd = "tree"\nopt_in_skips = ["need --runslow option to run"]'
        )
    )
    s = _stream("R skipped tests/test_a.py::test_slow -- need --runslow option to run")
    assert packages.smoke_findings(cfg, "demo-smoke", s, packages.Extra()) == [
        "a smoke test skips for an opt-in: tests/test_a.py::test_slow"
        " (need --runslow option to run)"
    ]
    assert packages.smoke_findings(cfg, "demo-r", s, packages.Extra()) == []
    extra = packages.Extra(deselected=["tests/test_a.py::test_net"])
    assert packages.smoke_findings(cfg, "demo-smoke", _stream(), extra) == [
        "a smoke group deselected tests/test_a.py::test_net"
    ]
    named = _cfg(BASE.replace('cwd = "tree"', 'cwd = "tree"\ndeselect_reason = "no network"'))
    assert packages.smoke_findings(named, "demo-smoke", _stream(), extra) == []


# ---------------------------------------------------------------------------------------------
# The tie


def _tar(path: Path, top: str, files: dict[str, bytes]) -> Path:
    with tarfile.open(path, "w:gz") as t:
        for name, data in files.items():
            info = tarfile.TarInfo(f"{top}/{name}")
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    return path


def _wheel(path: Path, files: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return path


def _manifest(**pins: str) -> paths.Manifest:
    text = "python 3.15.0\n" + "".join(f"pin {sha} {name}\n" for name, sha in pins.items())
    return paths.parse_manifest(text)


@pytest.fixture
def source(tmp_path):
    files = {
        "src/demo/__init__.py": b"x = 1\n",
        "src/demo/zone.bin": b"\x00\x01",
        "tests/test_a.py": b"",
    }
    tarball = _tar(tmp_path / "demo-1.0.tar.gz", "demo-1.0", files)
    tree = tmp_path / "demo-1.0"
    for name, data in files.items():
        (tree / name).parent.mkdir(parents=True, exist_ok=True)
        (tree / name).write_bytes(data)
    wheel = _wheel(
        tmp_path / "demo-1.0-py3-none-any.whl",
        {
            "demo/__init__.py": b"x = 1\n",
            "demo/zone.bin": b"\x00\x01",
            "demo-1.0.dist-info/RECORD": b"",
        },
    )
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
    m = _manifest(**{tarball.name: sha(tarball), wheel.name: sha(wheel)})
    cfg = SimpleNamespace(keys=SimpleNamespace(tie_skips={}))
    return SimpleNamespace(tarball=tarball, tree=tree, wheel=wheel, m=m, cfg=cfg, tmp=tmp_path)


def test_the_tie_holds_for_the_same_bytes(source) -> None:
    s = source
    assert packages.wheel_tie_errors(s.cfg, s.m, s.wheel, s.tree) == []
    assert packages.source_tie_errors(s.cfg, s.m, s.tarball, s.tree) == []


def test_a_differing_file_of_the_wheel_fails_the_tie_naming_it(source) -> None:
    s = source
    (s.tree / "src/demo/__init__.py").write_bytes(b"x = 2\n")
    assert (
        "demo/__init__.py: the wheel's differs from the test source's"
        in packages.wheel_tie_errors(s.cfg, s.m, s.wheel, s.tree)
    )
    (s.tree / "src/demo/zone.bin").write_bytes(b"\x00\x02")  # a data file too, not only .py
    assert "demo/zone.bin: the wheel's differs from the test source's" in packages.wheel_tie_errors(
        s.cfg, s.m, s.wheel, s.tree
    )


def test_a_file_the_source_lacks_fails_unless_named(source) -> None:
    s = source
    (s.tree / "src/demo/zone.bin").unlink()
    want = "demo/zone.bin: the wheel ships it, the test source lacks it"
    assert want in packages.wheel_tie_errors(s.cfg, s.m, s.wheel, s.tree)
    s.cfg.keys.tie_skips = {"demo/zone.bin": "the wheel's build writes it"}
    assert want not in packages.wheel_tie_errors(s.cfg, s.m, s.wheel, s.tree)


def test_another_version_or_another_pin_fails_the_tie(source) -> None:
    s = source
    other = s.tree.rename(s.tmp / "demo-2.0")
    assert any(
        "is not version 1.0" in e for e in packages.wheel_tie_errors(s.cfg, s.m, s.wheel, other)
    )
    other.rename(s.tree)
    m = _manifest(**{s.tarball.name: "0" * 64})
    assert any(
        "MANIFEST's pin" in e for e in packages.source_tie_errors(s.cfg, m, s.tarball, s.tree)
    )


def test_a_test_source_with_its_patch_unapplied_fails_the_tie(source, monkeypatch) -> None:
    """A recorded patch the tree does not carry: the tree is not the pinned archive with exactly
    its patches applied, and the file is named."""
    from harness import pins

    s = source
    patches = s.tmp / "patches"
    (patches / "demo-1.0").mkdir(parents=True)
    (patches / "demo-1.0" / "0001-a.patch").write_text(
        "diff --git a/tests/test_a.py b/tests/test_a.py\n"
        "--- a/tests/test_a.py\n+++ b/tests/test_a.py\n"
        "@@ -0,0 +1 @@\n+import os\n"
    )
    monkeypatch.setattr(pins, "PATCHES", patches)
    monkeypatch.setattr(upstream, "repo_patches", lambda top: {})
    drift = packages.source_tie_errors(s.cfg, s.m, s.tarball, s.tree)
    assert "demo-1.0: tests/test_a.py: modified" in drift, drift


def test_case_twins_are_the_file_systems() -> None:
    assert packages.case_twins({"a/X.py", "a/x.py", "a/y.py"}) == {"a/X.py", "a/x.py"}


# ---------------------------------------------------------------------------------------------
# The extras, the fetch and the pins


def test_kit_extra_takes_pure_wheels_and_one_pure_sdist() -> None:
    ok = "a" * 64 + "  https://files.pythonhosted.org/packages/x/freezegun-1.5.5-py3-none-any.whl\n"
    ok += "b" * 64 + "  https://files.pythonhosted.org/packages/x/pytest-expect-1.1.0.tar.gz\n"
    assert packages.extra_errors(ok) == []
    assert [packages.extra_name(f) for _, _, f in packages.extra_entries(ok)] == [
        "freezegun",
        "pytest-expect",
    ]
    bad = "c" * 64 + "  https://example.org/thing-1.0-cp315-cp315-linux.whl\n"
    assert packages.extra_errors(bad) == [
        "kit-extra.txt:1: not a SHA-256 and a pure wheel's or sdist's URL"
    ]
    assert packages.extra_errors(ok + ok.splitlines()[0] + "\n") == [
        "kit-extra.txt:3: freezegun is listed twice"
    ]


_fspec = importlib.util.spec_from_file_location(
    "upstream_fetch_pure", paths.REPO / "tests" / "upstream" / "fetch.py"
)
fetch = importlib.util.module_from_spec(_fspec)
_fspec.loader.exec_module(fetch)


def test_a_fetch_that_fails_twice_then_succeeds_passes(tmp_path, monkeypatch) -> None:
    data = b"wheel bytes"
    tries = []

    def urlopen(url, timeout=0):
        tries.append(url)
        if len(tries) < 3:
            raise OSError("connection reset")
        return io.BytesIO(data)

    monkeypatch.setattr(fetch.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(fetch, "PAUSE", 0)
    sha = hashlib.sha256(data).hexdigest()
    assert fetch.fetch(sha, "https://github.com/o/r/archive/x-tag.tar.gz", tmp_path) is None
    assert len(tries) == 3


def test_a_fetch_that_fails_three_times_names_the_forge_and_the_file(tmp_path, monkeypatch) -> None:
    def urlopen(url, timeout=0):
        raise OSError("connection reset")

    monkeypatch.setattr(fetch.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(fetch, "PAUSE", 0)
    e = fetch.fetch("0" * 64, "https://foss.heptapod.net/o/r/-/archive/1/x-tag.tar.gz", tmp_path)
    assert e == "x-tag.tar.gz: foss.heptapod.net failed 3 times: connection reset"
    assert not list(tmp_path.glob("*.part"))


MIRROR = "https://github.com/o/r/releases/download/test-sources-2026-01-01/x-tag.tar.gz"
ORIGIN = "https://foss.heptapod.net/o/x/-/archive/1/x-1.tar.gz"
PINNED = b"the pinned archive"
CHALLENGE = b"<!doctype html><title>Making sure you&#39;re not a bot!</title>"


def _network(monkeypatch, served: dict[str, bytes | Exception]) -> list[str]:
    """A fake network answering each URL with its bytes or its error; the URLs asked, in order."""
    asked: list[str] = []

    def urlopen(url, timeout=0):
        asked.append(url)
        answer = served[url]
        if isinstance(answer, Exception):
            raise answer
        return io.BytesIO(answer)

    monkeypatch.setattr(fetch.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(fetch, "PAUSE", 0)
    return asked


def test_a_mirrored_file_is_fetched_from_the_mirror_first(tmp_path, monkeypatch, capsys) -> None:
    asked = _network(monkeypatch, {MIRROR: PINNED, ORIGIN: PINNED})
    sha = hashlib.sha256(PINNED).hexdigest()
    assert fetch.fetch_first(sha, (MIRROR, ORIGIN), tmp_path, "x-tag.tar.gz") is None
    assert asked == [MIRROR]
    assert (tmp_path / "x-tag.tar.gz").read_bytes() == PINNED
    assert f"fetched x-tag.tar.gz from {MIRROR}" in capsys.readouterr().out


def test_a_mirror_that_serves_other_bytes_falls_back_to_the_origin(
    tmp_path, monkeypatch, capsys
) -> None:
    asked = _network(monkeypatch, {MIRROR: CHALLENGE, ORIGIN: PINNED})
    sha = hashlib.sha256(PINNED).hexdigest()
    assert fetch.fetch_first(sha, (MIRROR, ORIGIN), tmp_path, "x-tag.tar.gz") is None
    assert asked == [MIRROR, ORIGIN]
    assert (tmp_path / "x-tag.tar.gz").read_bytes() == PINNED
    out, err = capsys.readouterr()
    assert f"fetched x-tag.tar.gz from {ORIGIN}" in out
    assert "x-tag.tar.gz: the mirror did not serve the pinned bytes" in err
    assert hashlib.sha256(CHALLENGE).hexdigest() in err


def test_a_mirror_that_fails_three_times_falls_back_to_the_origin(tmp_path, monkeypatch) -> None:
    asked = _network(monkeypatch, {MIRROR: OSError("connection reset"), ORIGIN: PINNED})
    sha = hashlib.sha256(PINNED).hexdigest()
    assert fetch.fetch_first(sha, (MIRROR, ORIGIN), tmp_path, "x-tag.tar.gz") is None
    assert asked == [MIRROR] * fetch.ATTEMPTS + [ORIGIN]
    assert (tmp_path / "x-tag.tar.gz").read_bytes() == PINNED


def test_a_file_neither_url_serves_names_both(tmp_path, monkeypatch) -> None:
    asked = _network(monkeypatch, {MIRROR: CHALLENGE, ORIGIN: b"other bytes"})
    sha = hashlib.sha256(PINNED).hexdigest()
    e = fetch.fetch_first(sha, (MIRROR, ORIGIN), tmp_path, "x-tag.tar.gz")
    assert asked == [MIRROR, ORIGIN]
    assert e is not None and e.startswith(f"x-tag.tar.gz: {MIRROR}: SHA-256 "), e
    assert f"; {ORIGIN}: SHA-256 " in e, e
    for body in (CHALLENGE, b"other bytes"):
        assert hashlib.sha256(body).hexdigest() in e, e
    assert not list(tmp_path.iterdir())


def test_a_challenge_page_for_a_test_source_is_refused(tmp_path, monkeypatch) -> None:
    """A host that answers an archive's URL with a page is refused by the hash: nothing lands in
    downloads/, no tree is unpacked, and the error names the file."""
    downloads, build = tmp_path / "downloads", tmp_path / "build"
    downloads.mkdir()
    name = "openpyxl-3.1.5-tag.tar.gz"
    (downloads / "SHA256SUMS").write_text(f"{hashlib.sha256(PINNED).hexdigest()}  {name}\n")
    script = tmp_path / "00_download.sh"
    script.write_text(f"tests {ORIGIN} {name}\n")
    _network(monkeypatch, {ORIGIN: CHALLENGE})
    errors = fetch.fetch_trees(
        ["openpyxl"],
        downloads=downloads,
        build=build,
        script=script,
        applier=Path("apply.sh"),
        patches=tmp_path / "patches",
        run=lambda argv, check=False: pytest.fail(f"nothing may be patched: {argv}"),
    )
    assert len(errors) == 1 and errors[0].startswith(f"{name}: SHA-256"), errors
    assert sorted(p.name for p in downloads.iterdir()) == ["SHA256SUMS"]
    assert not build.exists()


def test_a_tests_line_needs_its_pin_and_a_forges_archive_its_tag_name(tmp_path) -> None:
    script = tmp_path / "00_download.sh"
    script.write_text(
        "tests https://files.pythonhosted.org/p/six-1.17.0.tar.gz six-1.17.0.tar.gz\n"
        "tests https://github.com/o/cycler/archive/refs/tags/v0.12.1.tar.gz cycler-0.12.1.tar.gz\n"
    )
    errors = scan.test_source_errors(script, {"cycler-0.12.1.tar.gz"})
    assert "six-1.17.0.tar.gz: a tests line, but not pinned in downloads/SHA256SUMS" in errors
    assert "cycler-0.12.1.tar.gz: a forge's archive, not named -tag.tar.gz" in errors
    assert "cycler-0.12.1.tar.gz: matches 0 source patterns, not one" in errors


def test_the_pure_packages_are_suites_and_none_waits() -> None:
    entries = tomllib.loads((paths.REPO / "tests" / "upstream" / "packages.toml").read_text())
    entries = entries["package"]
    assert {p: entries[p]["kind"] for p in upstream.PURE_SUITES} == dict.fromkeys(
        upstream.PURE_SUITES, "suite"
    )
    assert not [p for p, e in entries.items() if "067" in str(e.get("closes_with", ""))]


@pytest.mark.parametrize(
    ("group", "wheel", "extras"),
    [
        ("six-smoke", "six-1.17.0-py2.py3-none-any.whl", []),
        (
            "python-dateutil-smoke",
            "python_dateutil-2.9.0.post0-py2.py3-none-any.whl",
            ["freezegun"],
        ),
    ],
)
def test_a_shard_fetches_its_familys_source_wheel_and_extras(
    group, wheel, extras, monkeypatch
) -> None:
    from harness import shards

    monkeypatch.setattr(shards, "load", lambda: {"s": SimpleNamespace(groups=[group])})
    package = group.removesuffix("-smoke")
    assert fetch.shard_packages("s") == [package]
    assert fetch.shard_files("s") == ([wheel], extras)


def test_an_item_group_gets_no_option_of_upstreams_conftest() -> None:
    """An item group collects the stage's empty folder, so no conftest loads, and pytest refuses
    an option only a conftest registers (networkx's --runslow): the family's arguments, which
    shape what pytest collects from the test files, go to its path groups only."""
    text = BASE.replace('cwd = "tree"', 'cwd = "tree"\nargs = ["--runslow"]')
    text += '\n[groups.demo-doc]\ndocstring_modules = ["demo.core"]' + RELEASE
    cfg = _cfg(text)
    assert "--runslow" in packages.group_args(cfg, cfg.groups["demo-r"])
    assert "--runslow" not in packages.group_args(cfg, cfg.groups["demo-doc"])


def test_a_split_expression_too_long_for_the_guest_is_refused() -> None:
    """pytest builds a -k expression's `or` and `and` as nested pairs, and the guest's stack holds
    only so deep a one when it compiles it: a split whose expression would nest past the bound
    (one keyword's terms and the parts before it) is refused before any run, naming the group."""
    names = " or ".join(f"test_{i}" for i in range(packages.SPLIT_DEPTH + 1))
    text = BASE.replace(
        '[groups.demo-r]\npaths = ["tests"]', '[groups.demo-r]\npaths = ["tests/test_b.py"]'
    )
    text += '\n[groups.demo-r2]\npaths = ["tests/test_b.py"]' + RELEASE
    text += '\n[[split]]\nfile = "tests/test_b.py"\ngroups = ["demo-r", "demo-r2"]\n'
    text += f'keywords = ["{names}"]\n'
    errors = packages.split_errors("demo", _cfg(text))
    assert any("demo-r" in e and "terms" in e for e in errors), errors
