"""numpy's and pandas' own tests in the guest, on fixed inputs (spec 050): the kit, the unzip, the
MANIFEST tie, the member filter, the argv, the stream, the sorting into classes, the class lists'
+/- findings, the trap's node, and the rules. No guest runs here."""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
import zipfile
from pathlib import Path

import pytest

from harness import paths, scan, upstream

CONFIGS = upstream.load_all()


def _cfg(package="numpy", **kw) -> upstream.Config:
    base = {
        "package": package,
        "marker": "not slow",
        "args": [],
        "path_packages": [package],
        "markers": [],
        "support": [],
        "groups": {"g": upstream.Group("g", (f"{package}/tests",), 10**9)},
        "not_selected": [],
        "traps": [],
        "expected": [],
    }
    base.update(kw)
    return upstream.Config(**base)


# ---------------------------------------------------------------------------------------------
# The kit (criterion 1)


def _wheel(path: Path, members: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
    return path


def test_a_wheel_with_one_byte_changed_leaves_the_kit_unmet(work) -> None:
    wheels = work / "wheels"
    wheels.mkdir()
    w = _wheel(wheels / "pytest-9.0.3-py3-none-any.whl", {"pytest/__init__.py": b"x = 1\n"})
    sha = paths.sha256_file(w)
    kit = work / "kit.txt"
    kit.write_text(f"{sha}  https://files.pythonhosted.org/packages/aa/{w.name}\n")
    assert upstream.kit_met(kit, wheels)
    data = bytearray(w.read_bytes())
    data[-1] ^= 1
    w.write_bytes(bytes(data))
    assert not upstream.kit_met(kit, wheels)
    w.unlink()
    assert not upstream.kit_met(kit, wheels)


@pytest.mark.parametrize("bad", ["../x", "/x", "a/../../x", "a/..\\x"])
def test_the_unzip_refuses_a_member_outside_its_folder(work, bad) -> None:
    w = _wheel(work / "evil-1-py3-none-any.whl", {"ok.py": b"", bad: b"boom"})
    dest = work / "out"
    with pytest.raises(ValueError, match="refused"):
        upstream.safe_unzip(w, dest)
    assert not (work / "x").exists()


def test_the_unzip_unpacks_a_plain_wheel(work) -> None:
    w = _wheel(work / "ok-1-py3-none-any.whl", {"ok/__init__.py": b"y = 2\n"})
    upstream.safe_unzip(w, work / "out")
    assert (work / "out" / "ok" / "__init__.py").read_bytes() == b"y = 2\n"


@pytest.mark.parametrize(
    ("line", "why"),
    [
        ("abc  https://files.pythonhosted.org/p/x-1-py3-none-any.whl", "64 hex"),
        ("a" * 64 + " https://files.pythonhosted.org/p/x-1-py3-none-any.whl", "64 hex"),
        ("a" * 64 + "  https://example.org/p/x-1-py3-none-any.whl", "files.pythonhosted.org"),
        ("a" * 64 + "  https://files.pythonhosted.org/p/x-1-cp315-cp315-any.whl", "py3-none-any"),
        ("a" * 64 + "  https://files.pythonhosted.org/p/x-1.tar.gz", "py3-none-any"),
    ],
)
def test_a_malformed_kit_line_is_a_rule_error(line, why) -> None:
    errors = upstream.kit_errors(line + "\n")
    assert errors and why in errors[0], errors


def test_the_pinned_kit_is_well_formed() -> None:
    assert upstream.kit_errors(upstream.KIT.read_text()) == []
    assert len(upstream.kit_entries(upstream.KIT.read_text())) == 7


# ---------------------------------------------------------------------------------------------
# The MANIFEST tie and the member filter (criterion 9)


def _tarball(path: Path, top: str, files: dict[str, bytes]) -> Path:
    with tarfile.open(path, "w:gz") as t:
        for rel, data in files.items():
            info = tarfile.TarInfo(f"{top}/{rel}")
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    return path


def _manifest(pins: dict[str, str], recipes: dict[str, str]) -> paths.Manifest:
    return paths.Manifest(python="3.15.0", pins=dict(pins), recipes=dict(recipes))


def test_the_tie_holds_for_the_artifacts_own_tarball_and_patches(work) -> None:
    tb = _tarball(work / "numpy-2.5.2.tar.gz", "numpy-2.5.2", {"numpy/tests/test_a.py": b""})
    patch_dir = work / "patches" / "numpy-2.5.2"
    patch_dir.mkdir(parents=True)
    p = patch_dir / "0001-x.patch"
    p.write_text("--- a/x\n+++ b/x\n")
    rel = "recipes/patches/numpy-2.5.2/0001-x.patch"
    m = _manifest({tb.name: paths.sha256_file(tb)}, {rel: paths.sha256_file(p)})
    assert upstream.tie_errors("numpy", m, tb, {rel: paths.sha256_file(p)}) == []


def test_a_manifest_from_another_tarball_fails_naming_both(work) -> None:
    tb = _tarball(work / "numpy-2.6.0.tar.gz", "numpy-2.6.0", {"numpy/tests/test_a.py": b""})
    m = _manifest({"numpy-2.5.2.tar.gz": "0" * 64}, {})
    errors = upstream.tie_errors("numpy", m, tb, {})
    assert errors == ["tests from numpy-2.6.0.tar.gz, artifact built from numpy-2.5.2.tar.gz"]
    same_name = _manifest({"numpy-2.6.0.tar.gz": "0" * 64}, {})
    [error] = upstream.tie_errors("numpy", same_name, tb, {})
    assert "numpy-2.6.0.tar.gz" in error and "0" * 12 in error and "SHA-256" in error


def test_a_manifest_with_other_patches_fails_naming_both() -> None:
    m = _manifest({}, {"recipes/patches/numpy-2.5.2/0001-x.patch": "a" * 64})
    tb_name_only = Path("numpy-2.5.2.tar.gz")
    errors = upstream.tie_errors(
        "numpy",
        m,
        tb_name_only,
        {"recipes/patches/numpy-2.5.2/0001-x.patch": "b" * 64},
        tarball_sha="c" * 64,
    )
    assert any("patch" in e and "aaaaaaaaaaaa" in e and "bbbbbbbbbbbb" in e for e in errors), errors
    missing = upstream.tie_errors(
        "numpy",
        _manifest({}, {}),
        tb_name_only,
        {"recipes/patches/numpy-2.5.2/0001-x.patch": "b" * 64},
        tarball_sha="c" * 64,
    )
    assert any("0001-x.patch" in e for e in missing), missing


def test_a_patch_that_creates_a_file_names_it() -> None:
    text = (
        "diff --git a/numpy/x.py b/numpy/x.py\n--- a/numpy/x.py\n+++ b/numpy/x.py\n@@ -1 +1 @@\n"
        "diff --git a/numpy/tests/test_new.py b/numpy/tests/test_new.py\nnew file mode 100644\n"
        "--- /dev/null\n+++ b/numpy/tests/test_new.py\n@@ -0,0 +1 @@\n+x = 1\n"
    )
    assert upstream.patch_created(text) == {"numpy/tests/test_new.py"}


def test_a_stray_file_is_not_staged_and_is_listed(work) -> None:
    files = {
        "numpy/tests/__init__.py": b"",
        "numpy/tests/test_a.py": b"def test_a(): pass\n",
        "numpy/tests/data/d.txt": b"1\n",
    }
    tb = _tarball(work / "numpy-9.tar.gz", "numpy-9", files)
    tree = work / "tree" / "numpy-9"
    for rel, data in files.items():
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_bytes(data)
    (tree / "numpy/tests/conftest.py").write_text("raise SystemExit\n")  # a build left it here
    (tree / "numpy/tests/__pycache__").mkdir()
    (tree / "numpy/tests/__pycache__/test_a.pyc").write_bytes(b"x")
    dest = work / "stage"
    members = upstream.tarball_members(tb) | {"numpy/tests/patched_in.py"}
    (tree / "numpy/tests/patched_in.py").write_text("")
    left_out = upstream.stage(_cfg(), tree, members, dest)
    assert left_out == [
        "numpy/tests/__pycache__/test_a.pyc",
        "numpy/tests/conftest.py",
    ]
    staged = sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file())
    assert staged == [
        "numpy/tests/__init__.py",
        "numpy/tests/data/d.txt",
        "numpy/tests/patched_in.py",
        "numpy/tests/test_a.py",
    ]


def test_a_groups_ancestors_init_and_conftest_and_the_support_files_are_staged(work) -> None:
    files = {
        "pandas/conftest.py": b"",
        "pandas/core/frame.py": b"",
        "pandas/tests/__init__.py": b"",
        "pandas/tests/io/__init__.py": b"",
        "pandas/tests/io/conftest.py": b"",
        "pandas/tests/io/test_other.py": b"",
        "pandas/tests/io/parser/__init__.py": b"",
        "pandas/tests/io/parser/test_p.py": b"",
        "pandas/tests/extension/decimal/array.py": b"",
    }
    tree = work / "pandas-1"
    for rel, data in files.items():
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_bytes(data)
    cfg = _cfg(
        "pandas",
        groups={"p": upstream.Group("p", ("pandas/tests/io/parser",), 10**9)},
        support=["pandas/conftest.py", "pandas/tests/extension/decimal/array.py"],
    )
    upstream.stage(cfg, tree, set(files), work / "stage")
    staged = sorted(
        p.relative_to(work / "stage").as_posix() for p in (work / "stage").rglob("*") if p.is_file()
    )
    assert staged == [
        "pandas/conftest.py",
        "pandas/tests/__init__.py",
        "pandas/tests/extension/decimal/array.py",
        "pandas/tests/io/__init__.py",
        "pandas/tests/io/conftest.py",
        "pandas/tests/io/parser/__init__.py",
        "pandas/tests/io/parser/test_p.py",
    ]


def test_the_grant_is_read_only_at_upstream(work) -> None:
    assert upstream.preopens(work) == [("/upstream", work, False)]


# ---------------------------------------------------------------------------------------------
# The argv (Decisions 5, 7, 8, 9)


def test_a_groups_argv_carries_its_marker_paths_ignores_and_deselects() -> None:
    cfg = _cfg(
        args=["--x"],
        groups={"g": upstream.Group("g", ("numpy/a/tests", "numpy/tests"), 10**9)},
        not_selected=[upstream.NotSelected(("numpy/a/tests/test_c.py",), "r", "README.md")],
        traps=[
            upstream.Trap("t1", "numpy/a/tests/test_b.py::T::test_x", "r", "README.md"),
            upstream.Trap("t2", "numpy/a/tests/test_w.py", "r", "README.md"),
            upstream.Trap("t3", "numpy/other/tests/test_z.py::t", "r", "README.md"),
        ],
    )
    spec = upstream.group_spec(cfg, cfg.groups["g"])
    assert spec["args"] == [
        "-m",
        "not slow",
        "--x",
        "/upstream/tests/numpy/a/tests",
        "/upstream/tests/numpy/tests",
        "--ignore=/upstream/tests/numpy/a/tests/test_c.py",
        "--ignore=/upstream/tests/numpy/a/tests/test_w.py",
        "--deselect=numpy/a/tests/test_b.py::T::test_x",
    ]
    assert spec["path_packages"] == ["numpy"]
    trap = upstream.trap_spec(cfg, cfg.traps[0])
    assert trap["args"] == ["--x", "/upstream/tests/numpy/a/tests/test_b.py::T::test_x"]


def test_the_guest_argv_runs_the_driver_unbuffered() -> None:
    assert upstream.guest_argv("numpy", "numpy-core") == [
        "-u",
        "/upstream/judge/drive.py",
        "numpy",
        "numpy-core",
    ]


# ---------------------------------------------------------------------------------------------
# The stream and the group's findings (criterion 5)

GOOD_P = "P derandomize=True database=None max_examples=15"
K_DUP = upstream.Klass("no-dup", "g", "failed", r"Errno 58", "r", "README.md")
K_ANY = upstream.Klass("bare", "g", "failed", r"^AssertionError: ?$", "r", "README.md")


def _stream(*body: str, end: str | None = "E 1", p: str | None = GOOD_P) -> str:
    lines = ["C ", "C numpy/tests/test_a.py", *([p] if p else [])]
    lines += list(body)
    if end:
        lines.append(end)
    return "".join(line + "\n" for line in lines)


def _group(text: str, trapped=None, cause=None, classes=(K_DUP, K_ANY), exit_code=0, out=""):
    run = upstream.GuestRun(
        exit_code=None if trapped else exit_code,
        trapped=trapped,
        cause=cause,
        fuel=1,
        stdout=out,
        stderr_tail="",
    )
    return upstream.judge_group(upstream.parse_stream(text), run, list(classes))


def test_a_clean_stream_passes_and_counts_passes() -> None:
    text = _stream(
        "S numpy/tests/test_a.py::test_1",
        "R passed numpy/tests/test_a.py::test_1 -- ",
        "S numpy/tests/test_a.py::test_2",
        "R skipped numpy/tests/test_a.py::test_2 -- not on wasm",
        "S numpy/tests/test_a.py::test_3",
        "R xfailed numpy/tests/test_a.py::test_3 -- known",
        "S numpy/tests/test_a.py::test_4",
        "R xpassed numpy/tests/test_a.py::test_4 -- ",
        "M numpy.tests.test_a /upstream/tests/numpy/tests/test_a.py",
    )
    g = _group(text)
    assert g.findings == [] and g.passes == 1
    assert g.passed_digest == paths.sha256_bytes(b"numpy/tests/test_a.py::test_1")[:12]
    assert g.counts == {"passed": 1, "skipped": 1, "xfailed": 1, "xpassed": 1}


def test_failures_sort_into_the_first_class_that_fits_and_the_rest_are_findings() -> None:
    text = _stream(
        "S numpy/tests/test_a.py::test_1",
        "R failed numpy/tests/test_a.py::test_1 -- OSError: [Errno 58] Not supported",
        "R error numpy/tests/test_a.py::test_1 -- OSError: [Errno 58] Not supported",
        "S numpy/tests/test_a.py::test_2",
        "R failed numpy/tests/test_a.py::test_2 -- AssertionError: ",
        "S numpy/tests/test_a.py::test_3",
        "R failed numpy/tests/test_a.py::test_3 -- AssertionError: values differ",
    )
    g = _group(text)
    assert g.members == {
        "no-dup": ["numpy/tests/test_a.py::test_1"],
        "bare": ["numpy/tests/test_a.py::test_2"],
    }
    assert g.findings == [
        "unexpected error numpy/tests/test_a.py::test_1 — OSError: [Errno 58] Not supported",
        "unexpected failed numpy/tests/test_a.py::test_3 — AssertionError: values differ",
    ]


def test_a_node_id_with_the_separator_inside_is_read_whole() -> None:
    node = "numpy/tests/test_a.py::test_1[a -- b]"
    text = _stream(f"S {node}", f"R failed {node} -- x -- OSError: [Errno 58] y")
    g = _group(text)
    assert g.members["no-dup"] == [node]


@pytest.mark.parametrize(
    ("text", "kw", "finding"),
    [
        (_stream("X numpy/tests/test_b.py -- ImportError: no"), {}, "collection error"),
        (_stream(end="E 2"), {}, "pytest exit code 2"),
        (_stream(end="E 3"), {}, "INTERNALERROR"),
        (_stream(end="E 4"), {}, "pytest exit code 4"),
        (_stream(end="E 5"), {}, "pytest exit code 5"),
        (_stream(), {"out": "INTERNALERROR> boom"}, "INTERNALERROR"),
        (_stream(end=None), {"exit_code": 1}, "no E line"),
        (
            _stream("S numpy/tests/test_a.py::test_1", end=None),
            {"trapped": "error while executing", "cause": "wasm trap: indirect call"},
            "trap: wasm trap: indirect call at numpy/tests/test_a.py::test_1",
        ),
        (
            _stream("S numpy/tests/test_a.py::test_1", end=None),
            {"trapped": "out of fuel"},
            "out of fuel at numpy/tests/test_a.py::test_1",
        ),
        (
            _stream(p="P derandomize=False database=None max_examples=15"),
            {},
            "hypothesis profile",
        ),
        (
            _stream(p="P derandomize=True database=DirectoryBasedExampleDatabase() x=1"),
            {},
            "hypothesis profile",
        ),
        (_stream(p=None), {}, "no P line"),
        (
            _stream("M numpy.lib._format_impl /upstream/tests/numpy/lib/_format_impl.py"),
            {},
            "a product module came from the grant",
        ),
    ],
)
def test_protocol_faults_are_group_findings(text, kw, finding) -> None:
    g = _group(text, **kw)
    assert any(finding in f for f in g.findings), g.findings


def test_conftest_and_tests_modules_pass_the_guard() -> None:
    text = _stream(
        "M pandas.conftest /upstream/tests/pandas/conftest.py",
        "M pandas.tests.extension.decimal.array /upstream/tests/pandas/tests/extension/x.py",
        "M numpy._core.tests._locales /upstream/tests/numpy/_core/tests/_locales.py",
    )
    assert _group(text).findings == []


# ---------------------------------------------------------------------------------------------
# A trap's node and cause (criterion 4)


def test_a_stream_that_ends_after_a_c_line_names_that_collector() -> None:
    text = "C \nC numpy/_core/tests\nC numpy/_core/tests/test_arraymethod.py\n"
    s = upstream.parse_stream(text)
    assert s.open_node == "numpy/_core/tests/test_arraymethod.py"
    run = upstream.GuestRun(None, "error while executing", "wasm trap: indirect call", 1, "", "")
    assert upstream.trap_findings(s, run) == [
        "trap: wasm trap: indirect call at numpy/_core/tests/test_arraymethod.py"
    ]


def test_a_stream_that_ends_inside_a_test_names_that_test() -> None:
    text = _stream(
        "S numpy/tests/test_a.py::test_1",
        "R passed numpy/tests/test_a.py::test_1 -- ",
        "S numpy/tests/test_a.py::test_2",
        end=None,
    )
    assert upstream.parse_stream(text).open_node == "numpy/tests/test_a.py::test_2"


def test_an_entry_that_no_longer_traps_has_no_finding_and_another_cause_differs() -> None:
    s = upstream.parse_stream(_stream("S n::t", "R failed n::t -- ValueError: x"))
    clean = upstream.GuestRun(0, None, None, 1, "", "")
    assert upstream.trap_findings(s, clean) == []  # the check passes; its gap says remove it
    open_s = upstream.parse_stream(_stream("S n::t", end=None))
    one = upstream.GuestRun(None, "e", "wasm trap: indirect call type mismatch", 1, "", "")
    other = upstream.GuestRun(None, "e", "wasm trap: out of bounds memory access", 1, "", "")
    a, b = upstream.trap_findings(open_s, one), upstream.trap_findings(open_s, other)
    assert a != b and scan.digest(a) != scan.digest(b)


def test_a_trap_entry_whose_test_passes_makes_its_gap_say_remove_it(pytester) -> None:
    """The plugin's own rule, through a trap check's assertion: a gap whose check passes fails
    with "remove the gap" (spec 002, Decision 4)."""
    node = "test_inner.py::test_upstream_trap[t]"
    gaps = pytester.path / "gaps.toml"
    gaps.write_text(
        f'[[gap]]\ncheck = "{node}"\nmatch = "1 finding(s)"\nreason = "r"\n'
        'closes_with = "README.md"\n'
    )
    pytester.makepyfile(
        test_inner="""
import pytest
from harness import scan, upstream

pytestmark = pytest.mark.goal("v1.3")

@pytest.mark.parametrize("trap", ["t"])
def test_upstream_trap(trap):
    s = upstream.parse_stream("S n::t\\nR passed n::t -- \\nE 0\\n")
    findings = upstream.trap_findings(s, upstream.GuestRun(0, None, None, 1, "", ""))
    assert not findings, scan.report(findings, "trap t")
"""
    )
    result = pytester.runpytest(
        "-p",
        "harness.plugin",
        "--progress-dir",
        str(pytester.path / "progress"),
        "--progress-latest",
        str(pytester.path / "latest.json"),
        "--known-gaps",
        str(gaps),
    )
    record = json.loads((pytester.path / "latest.json").read_text())["checks"][node]
    assert result.ret == 1 and record["status"] == "fail"
    assert "remove the gap" in record["reason"]


# ---------------------------------------------------------------------------------------------
# The class lists (criteria 4, 5)

ODD = "pandas/tests/tslibs/test_x.py::test_y[2020-01-01 00:00:00]"


def test_an_exact_list_gives_one_finding_per_member() -> None:
    assert upstream.class_findings(["b", "a"], ["a", "b"]) == ["a", "b"]


def test_one_more_member_shows_plus_and_one_fewer_shows_minus() -> None:
    listed = ["a", "b"]
    more = upstream.class_findings(["a", "b", "c"], listed)
    fewer = upstream.class_findings(["a"], listed)
    assert "+c" in more and "-b" in fewer
    exact = scan.digest(upstream.class_findings(["a", "b"], listed))
    assert scan.digest(more) != exact and scan.digest(fewer) != exact


def test_ids_that_the_digest_normalises_are_still_compared_exactly() -> None:
    """scan.digest strips `:<digits>` before a space or the end, so `…00:00:00]`-style ids are
    partly normalised inside a gap's digest; the +/- comparison with the list is exact (the
    review's builder note on F3)."""
    other = ODD.replace("00:00:00", "00:00:01")
    assert upstream.class_findings([other], [ODD]) == [other, f"+{other}", f"-{ODD}"]


def test_an_emptied_class_passes_and_a_returning_failure_shows_as_plus() -> None:
    assert upstream.class_findings([], []) == []
    assert upstream.class_findings([], ["a"]) == []  # the check passes; its gap says remove it
    assert upstream.class_findings(["a"], []) == ["a", "+a"]


def test_a_list_file_reads_sorted_lines(work) -> None:
    f = work / "x.txt"
    f.write_text("a\nb\n")
    assert upstream.read_list(f) == ["a", "b"]
    assert upstream.read_list(work / "missing.txt") == []


# ---------------------------------------------------------------------------------------------
# The rules (criterion 8)


def _rule_cfg(listed: list[str], tmp: Path):
    k = upstream.Klass("c", "g", "failed", "x", "r", "README.md")
    cfg = _cfg(expected=[k])
    exp = tmp / "expected" / "g"
    exp.mkdir(parents=True, exist_ok=True)
    (exp / "c.txt").write_text("".join(n + "\n" for n in listed))
    return {"numpy": cfg}, upstream.class_node("g", "c")


def test_an_empty_list_with_no_gap_passes_the_rules(work) -> None:
    configs, _ = _rule_cfg([], work)
    assert upstream.rule_errors(configs, set(), expected_dir=work / "expected") == []


def test_an_empty_list_with_a_gap_fails_the_rules(work) -> None:
    configs, node = _rule_cfg([], work)
    errors = upstream.rule_errors(configs, {node}, expected_dir=work / "expected")
    assert any("empty" in e and "gap" in e for e in errors), errors


def test_a_listed_class_without_a_gap_fails_the_rules(work) -> None:
    configs, node = _rule_cfg(["a"], work)
    assert upstream.rule_errors(configs, {node}, expected_dir=work / "expected") == []
    errors = upstream.rule_errors(configs, set(), expected_dir=work / "expected")
    assert any("no gap" in e for e in errors), errors


def test_an_unsorted_or_repeated_list_and_a_stray_list_fail_the_rules(work) -> None:
    configs, node = _rule_cfg(["b", "a", "a"], work)
    (work / "expected" / "g" / "orphan.txt").write_text("")
    errors = upstream.rule_errors(configs, {node}, expected_dir=work / "expected")
    assert any("sorted" in e for e in errors) and any("orphan" in e for e in errors), errors


def test_a_trap_without_its_gap_and_caps_over_the_budget_fail_the_rules(work) -> None:
    cfg = _cfg(
        groups={"g": upstream.Group("g", ("numpy/tests",), 3 * 10**12)},
        traps=[upstream.Trap("t", "numpy/tests/test_a.py", "r", "README.md")],
    )
    errors = upstream.rule_errors({"numpy": cfg}, set(), expected_dir=work / "expected")
    assert any("trap t" in e and "gap" in e for e in errors), errors
    assert any("caps" in e for e in errors), errors


def test_a_missing_closer_and_a_repeated_id_fail_the_rules(work) -> None:
    k = upstream.Klass("c", "g", "failed", "x", "r", "context/nowhere.md")
    cfg = _cfg(expected=[k, k])
    errors = upstream.rule_errors({"numpy": cfg}, set(), expected_dir=work / "expected")
    assert any("context/nowhere.md" in e for e in errors), errors
    assert any("twice" in e for e in errors), errors


def test_paths_that_are_not_tarball_members_fail_the_rules(work) -> None:
    cfg = _cfg(not_selected=[upstream.NotSelected(("numpy/tests/test_gone.py",), "r", "README.md")])
    members = {"numpy/tests/test_a.py"}
    errors = upstream.rule_errors(
        {"numpy": cfg}, set(), expected_dir=work / "expected", members={"numpy": members}
    )
    assert any("test_gone.py" in e for e in errors), errors


def test_the_judges_own_upstream_files_load() -> None:
    assert set(CONFIGS) == {"numpy", "pandas"}
    assert sum(len(c.groups) for c in CONFIGS.values()) == 11


def test_digests_of_passing_ids_are_twelve_hex() -> None:
    d = upstream.passed_digest(["b", "a"])
    assert d == hashlib.sha256(b"a\nb").hexdigest()[:12]


def test_the_stage_holds_every_package_whichever_check_asks_first(work, monkeypatch) -> None:
    """The guest's fuel depends on the grant's whole tree (pytest lists the root folder, and the
    allocations shift the collector's timing): a pandas group's fuel moved by up to 320 parts in
    a million when numpy's tests were or were not staged beside it (EXECUTED, the build's first
    runs). So one run's stage is always both packages, whichever check prepares it first."""
    from harness import pins

    trees = {}
    for pkg in ("numpy", "pandas"):
        files = {f"{pkg}/tests/__init__.py": b"", f"{pkg}/tests/test_a.py": b""}
        tb = _tarball(work / f"{pkg}-9.tar.gz", f"{pkg}-9", files)
        tree = work / "build" / f"{pkg}-9"
        for rel, data in files.items():
            (tree / rel).parent.mkdir(parents=True, exist_ok=True)
            (tree / rel).write_bytes(data)
        trees[pkg] = (tb, tree)
    art = work / "art"
    art.mkdir()
    pins_lines = "".join(f"pin {paths.sha256_file(tb)} {tb.name}\n" for tb, _ in trees.values())
    (art / "MANIFEST").write_text("python 3.15.0\npackage numpy 9\npackage pandas 9\n" + pins_lines)
    wheels = work / "wheels"
    wheels.mkdir()
    w = _wheel(wheels / "k-1-py3-none-any.whl", {"k.py": b""})
    kit = work / "kit.txt"
    kit.write_text(f"{paths.sha256_file(w)}  https://files.pythonhosted.org/p/{w.name}\n")
    monkeypatch.setattr(upstream, "KIT", kit)
    monkeypatch.setattr(upstream, "WHEELS", wheels)
    monkeypatch.setattr(upstream.paths, "HARNESS_TMP", work / "harness")
    monkeypatch.setattr(pins, "source_pair", lambda pkg, *a, **k: trees.get(pkg))
    monkeypatch.setattr(upstream.paths, "artifact_dir", lambda: art)
    monkeypatch.setattr(upstream, "repo_patches", lambda top, repo=None: {})
    configs = {p: _cfg(p) for p in ("numpy", "pandas")}
    for first in ("pandas", "numpy"):
        s = upstream.Session(work, configs)
        try:
            s.prepare(first)
            staged = sorted(
                p.relative_to(s.root).as_posix() for p in s.root.rglob("*") if p.is_file()
            )
        finally:
            s.close()
        assert "tests/numpy/tests/test_a.py" in staged and "tests/pandas/tests/test_a.py" in staged
        assert "judge/g.json" in staged and "kit/k.py" in staged
