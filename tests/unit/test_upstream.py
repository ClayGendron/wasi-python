"""numpy's and pandas' own tests in the guest, on fixed inputs: the kit, the unzip, the
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
    (tree / "numpy/tests/.DS_Store").write_bytes(b"Bud1")
    (tree / "numpy/tests/data/._d.txt").write_bytes(b"")
    dest = work / "stage"
    members = upstream.tarball_members(tb) | {"numpy/tests/patched_in.py"}
    (tree / "numpy/tests/patched_in.py").write_text("")
    left_out = upstream.stage(_cfg(), tree, members, dest)
    # Bytecode and litter are no fact; the conftest a build left is.
    assert left_out == ["numpy/tests/conftest.py"]
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
    entry = "numpy/_core/tests/test_arraymethod.py"
    assert upstream.trap_findings(s, run, entry) == [
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
    assert upstream.trap_findings(s, clean, "n::t") == []  # passes; its gap says remove it
    open_s = upstream.parse_stream(_stream("S n::t", end=None))
    one = upstream.GuestRun(None, "e", "wasm trap: indirect call type mismatch", 1, "", "")
    other = upstream.GuestRun(None, "e", "wasm trap: out of bounds memory access", 1, "", "")
    a, b = (
        upstream.trap_findings(open_s, one, "n::t"),
        upstream.trap_findings(open_s, other, "n::t"),
    )
    assert a != b and scan.digest(a) != scan.digest(b)


def test_a_trap_entry_whose_test_passes_makes_its_gap_say_remove_it(pytester) -> None:
    """The plugin's own rule, through a trap check's assertion: a gap whose check passes fails
    with "remove the gap"."""
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
    findings = upstream.trap_findings(s, upstream.GuestRun(0, None, None, 1, "", ""), "n::t")
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
    partly normalised inside a gap's digest; the +/- comparison with the list is exact."""
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
    # python: CPython's own tests; the six compiled packages: their own tests
    assert set(CONFIGS) == {"numpy", "pandas", "python", *upstream.PACKAGE_SUITES}
    tiers = [g.tier for n in ("numpy", "pandas") for g in CONFIGS[n].groups.values()]
    assert tiers.count("normal") == 11 and tiers.count("release") == 5


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


@pytest.mark.parametrize(
    "text",
    [
        "C \nC numpy/tests\nP derandomize=True database=None max_examples=100\nE 5\n",
        "C \nE 4\n",
        "C \nC numpy/tests/test_b.py\nS numpy/tests/test_b.py::t\n"
        "R passed numpy/tests/test_b.py::t -- \nE 0\n",
        "C \nC numpy/tests/test_a.py\n",
    ],
    ids=["no-tests-collected", "usage-error", "another-test", "no-E-line"],
)
def test_a_trap_check_whose_session_runs_nothing_of_its_entry_fails(text) -> None:
    """An entry renamed away, or a session that never got to it, is a
    finding, not a pass."""
    clean = upstream.GuestRun(0, None, None, 1, "", "")
    findings = upstream.trap_findings(
        upstream.parse_stream(text), clean, "numpy/tests/test_a.py::t"
    )
    assert findings and ("ran nothing" in findings[0] or "no E line" in findings[0]), findings


def test_a_trap_check_whose_entry_ran_and_finished_has_no_finding() -> None:
    clean = upstream.GuestRun(0, None, None, 1, "", "")
    by_test = "C \nS numpy/tests/test_a.py::t[0]\nR failed numpy/tests/test_a.py::t[0] -- x\nE 1\n"
    by_file = "C \nC numpy/tests/test_a.py\nE 0\n"
    assert (
        upstream.trap_findings(upstream.parse_stream(by_test), clean, "numpy/tests/test_a.py::t")
        == []
    )
    assert (
        upstream.trap_findings(upstream.parse_stream(by_file), clean, "numpy/tests/test_a.py") == []
    )


def _scaffold(work, monkeypatch, *, pandas_sha: str | None = None):
    """Two scratch packages with tarballs, trees, a kit and an artifact MANIFEST, wired into the
    harness the way a judge run finds them."""
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
    shas = {pkg: paths.sha256_file(tb) for pkg, (tb, _) in trees.items()}
    if pandas_sha is not None:
        shas["pandas"] = pandas_sha
    pins_lines = "".join(f"pin {shas[pkg]} {tb.name}\n" for pkg, (tb, _) in trees.items())
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
    return {p: _cfg(p) for p in ("numpy", "pandas")}


def test_a_manifest_mismatch_fails_the_checks_through_prepare_not_blocks(work, monkeypatch) -> None:
    """The tie's errors reach the checks as a failure (an AssertionError),
    never dropped and never a skip, which the plugin would file as blocked."""
    configs = _scaffold(work, monkeypatch, pandas_sha="0" * 64)
    s = upstream.Session(work, configs)
    try:
        for _ in range(2):  # and again from the cache
            try:
                s.prepare("pandas")
            except BaseException as e:  # a pytest.skip is a BaseException
                assert type(e) is AssertionError, f"{type(e).__name__}: {e}"
                message = str(e)
            else:
                raise AssertionError("prepare accepted tests that are not the artifact's")
            assert message.startswith(
                "the tests are not the artifact's: tests from pandas-9.tar.gz"
            )
            assert "000000000000" in message and "artifact built from pandas-9.tar.gz" in message
        assert s.prepare("numpy") == []  # the other package is the artifact's and stages
    finally:
        s.close()


def test_a_trap_check_whose_entry_started_but_whose_session_did_not_finish_fails() -> None:
    """The entry's test started, then the session
    ended without its E line and without a trap (the driver died, say). That is a finding."""
    text = "C \nC numpy/tests/test_a.py\nS numpy/tests/test_a.py::t[0]\n"
    run = upstream.GuestRun(1, None, None, 1, "", "Traceback: boom")
    findings = upstream.trap_findings(upstream.parse_stream(text), run, "numpy/tests/test_a.py::t")
    assert len(findings) == 1 and findings[0].startswith("no E line"), findings


# ---------------------------------------------------------------------------------------------
# Fuel facts: a test whose fuel measures a type object's address, run alone

EVIDENCE = ("context/reviews/047-regex-build-2026-10-18.md",)


def _fact(**change):
    """Built inside each row, so on a judge without fuel facts only these rows fail."""
    base = {
        "id": "f",
        "group": "g",
        "node": "numpy/tests/test_a.py::test_x",
        "fuel": 10**9,
        "reason": "why",
        "evidence": EVIDENCE,
    }
    return upstream.FuelFact(**{**base, **change})


def test_a_fuel_facts_cases_leave_its_group_and_run_alone_under_the_marker() -> None:
    cfg = _cfg(fuel_facts=[_fact()])
    assert upstream.group_spec(cfg, cfg.groups["g"])["args"][-1] == (
        "--deselect=numpy/tests/test_a.py::test_x["
    )
    assert upstream.fact_spec(cfg, _fact())["args"] == [
        "-m",
        "not slow",
        "/upstream/tests/numpy/tests/test_a.py::test_x",
    ]
    assert _fact().owns("numpy/tests/test_a.py::test_x[S2-True]")
    assert not _fact().owns("numpy/tests/test_a.py::test_x_empty[S2]")
    assert not _fact().owns("numpy/tests/test_a.py::test_x")


def test_the_judges_one_fuel_fact_is_string_comparisons_in_numpy_core() -> None:
    """The list is pinned here as well as in numpy.toml: a second entry is a judge change in two
    places, with its reason and its evidence."""
    facts = [(p, f.id, f.group, f.node) for p, c in CONFIGS.items() for f in c.fuel_facts]
    assert facts == [
        (
            "numpy",
            "string-comparisons",
            "numpy-core",
            "numpy/_core/tests/test_strings.py::test_string_comparisons",
        )
    ]
    cfg = CONFIGS["numpy"]
    args = upstream.group_spec(cfg, cfg.groups["numpy-core"])["args"]
    assert "--deselect=numpy/_core/tests/test_strings.py::test_string_comparisons[" in args
    assert cfg.fuel_facts[0].fuel >= 2 * 65_730_000_000  # twice the measured 65.73 G at least


def _r(*nodes: str, outcome: str = "passed") -> str:
    return "".join(f"S {n}\nR {outcome} {n} -- \n" for n in nodes)


@pytest.mark.parametrize(
    ("group", "alone", "finding"),
    [
        ("numpy/tests/test_a.py::test_y", "numpy/tests/test_a.py::test_x[0]", None),
        ("numpy/tests/test_a.py::test_x[0]", "numpy/tests/test_a.py::test_x[1]", "also ran in"),
        ("numpy/tests/test_a.py::test_y", None, "ran nothing of"),
        ("numpy/tests/test_a.py::test_y", "numpy/tests/test_a.py::test_x_empty[0]", "ran nothing"),
    ],
    ids=["once", "in-the-group-too", "nothing", "only-a-neighbour"],
)
def test_a_fuel_facts_cases_run_exactly_once(group, alone, finding) -> None:
    g = upstream.parse_stream(_stream(_r(group).strip()))
    a = upstream.parse_stream(_stream(*([_r(alone).strip()] if alone else [])))
    found = upstream.fact_findings(g, a, _fact())
    if finding is None:
        assert found == []
    else:
        assert found and finding in found[0], found


def test_a_neighbour_in_the_facts_session_is_a_finding() -> None:
    g = upstream.parse_stream(_stream())
    a = upstream.parse_stream(
        _stream(_r("numpy/tests/test_a.py::test_x[0]", "numpy/tests/test_a.py::test_x_e[0]"))
    )
    assert upstream.fact_findings(g, a, _fact()) == [
        "fuel fact f: its session ran numpy/tests/test_a.py::test_x_e[0], outside the entry"
    ]


def test_two_sessions_are_judged_as_one_group() -> None:
    """Passes, counts and members add up, and the digest is the one session's digest would be:
    the passed set does not depend on how the group is split."""
    one, two = "numpy/tests/test_a.py::test_y", "numpy/tests/test_a.py::test_x[0]"
    fail = f"S {two.replace('[0]', '[1]')}\nR failed {two.replace('[0]', '[1]')} -- [Errno 58] x"
    whole = upstream.parse_stream(_stream(_r(one).strip(), _r(two).strip(), fail))
    g = upstream.parse_stream(_stream(_r(one).strip()))
    a = upstream.parse_stream(_stream(_r(two).strip(), fail))
    clean = upstream.GuestRun(0, None, None, 1, "", "")
    combined = upstream.combine(
        [
            (g, upstream.judge_group(g, clean, [K_DUP, K_ANY]), ""),
            (a, upstream.judge_group(a, clean, [K_DUP, K_ANY]), "fuel fact f: "),
        ],
        [],
    )
    single = upstream.judge_group(whole, clean, [K_DUP, K_ANY])
    assert combined.passes == single.passes == 2
    assert combined.passed_digest == single.passed_digest
    assert combined.counts == single.counts == {"failed": 1, "passed": 2}
    assert combined.members == single.members
    assert combined.findings == [] and combined.finished


def test_a_finding_in_the_facts_session_names_it() -> None:
    g = upstream.parse_stream(_stream())
    a = upstream.parse_stream(_stream(end=None))  # no E line: the session did not finish
    clean = upstream.GuestRun(0, None, None, 1, "", "")
    out = upstream.combine(
        [
            (g, upstream.judge_group(g, clean, []), ""),
            (a, upstream.judge_group(a, clean, []), "fuel fact f: "),
        ],
        ["extra"],
    )
    assert out.findings[0].startswith("fuel fact f: no E line") and out.findings[-1] == "extra"
    assert not out.finished


def test_a_session_runs_the_group_then_its_fact_and_records_each_fuel(work, monkeypatch) -> None:
    """`Session.group` wires the parts together. The fact's spec file is
    staged, each session runs on its own cap, the group's fuel is its own session's and the fact's
    is the fact's, the passes add up, the fact's findings carry its prefix, and a case that ran in
    both sessions is the exactly-once finding. `_run` returns canned sessions; no guest runs."""
    configs = _scaffold(work, monkeypatch)
    configs["numpy"] = _cfg(fuel_facts=[_fact(fuel=7 * 10**8)])
    y, x0, x1 = (f"numpy/tests/test_a.py::{n}" for n in ("test_y", "test_x[0]", "test_x[1]"))
    canned = {
        "g": (_stream(_r(y, x0).strip()), 111_000),
        "f": (_stream(_r(x0).strip(), f"S {x1}\nR failed {x1} -- boom"), 222_000),
    }
    calls = []

    def run(self, package, name, fuel):
        calls.append((package, name, fuel))
        text, used = canned[name]
        return upstream.parse_stream(text), upstream.GuestRun(0, None, None, used, "", "")

    monkeypatch.setattr(upstream.Session, "_run", run)
    s = upstream.Session(work, configs)
    try:
        got = s.group("numpy", "g")
        staged = json.loads((s.root / "judge" / "f.json").read_text())
    finally:
        s.close()
    assert calls == [("numpy", "g", 10**9), ("numpy", "f", 7 * 10**8)]
    assert staged == upstream.fact_spec(configs["numpy"], _fact())
    assert got.fuel == 111_000 and got.fuel_facts == {"f": 222_000}
    assert got.outcome.passes == 3 and got.outcome.counts == {"failed": 1, "passed": 3}
    assert got.outcome.findings == [
        f"fuel fact f: unexpected failed {x1} — boom",
        f"fuel fact f: {x0} also ran in the group",
    ]
    assert got.outcome.finished and s.group("numpy", "g") is got  # cached: no third session
    assert len(calls) == 2


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ({"reason": "  "}, "has no reason"),
        ({"evidence": ()}, "names no evidence"),
        ({"evidence": ("README.md",)}, "evidence README.md is not a file under"),
        ({"evidence": ("context/reviews/nowhere.md",)}, "is not a file under"),
        ({"group": "h"}, "names no group of its package: h"),
        ({"node": "numpy/other/test_a.py::test_x"}, "is not under its group's paths"),
        ({"node": "numpy/tests/test_a.py::test_x[0]"}, "is not file::function"),
        ({"fuel": 0}, "is not positive"),
    ],
)
def test_a_fuel_fact_needs_its_group_a_plain_node_a_reason_and_evidence(work, change, error):
    good = _cfg(fuel_facts=[_fact()])
    assert upstream.rule_errors({"numpy": good}, set(), expected_dir=work / "expected") == []
    bad = _cfg(fuel_facts=[_fact(**change)])
    errors = upstream.rule_errors({"numpy": bad}, set(), expected_dir=work / "expected")
    assert any(error in e for e in errors), errors


def test_a_fuel_fact_that_overlaps_another_entry_or_a_name_fails_the_rules(work) -> None:
    cfg = _cfg(
        fuel_facts=[_fact(), _fact(node="numpy/tests/test_a.py::test_x_e")],
        not_selected=[upstream.NotSelected(("numpy/tests/test_a.py",), "r", "README.md")],
    )
    errors = upstream.rule_errors({"numpy": cfg}, set(), expected_dir=work / "expected")
    assert any("also left out by" in e for e in errors), errors
    assert any("the name f is used twice" in e for e in errors), errors
    trap = upstream.Trap("t", "numpy/tests/test_a.py::test_x", "r", "README.md")
    cfg = _cfg(fuel_facts=[_fact()], traps=[trap])
    errors = upstream.rule_errors(
        {"numpy": cfg}, {upstream.trap_node("t")}, expected_dir=work / "expected"
    )
    assert any("also left out by" in e for e in errors), errors
    for folder, overlaps in (("numpy/tests", True), ("numpy/tests/", True), ("numpy/test", False)):
        cfg = _cfg(
            fuel_facts=[_fact()], not_selected=[upstream.NotSelected((folder,), "r", "README.md")]
        )
        errors = upstream.rule_errors({"numpy": cfg}, set(), expected_dir=work / "expected")
        assert any("also left out by" in e for e in errors) == overlaps, (folder, errors)
    sibling = upstream.Trap("t", "numpy/tests/test_a.py::test_x_empty", "r", "README.md")
    cfg = _cfg(fuel_facts=[_fact()], traps=[sibling])
    errors = upstream.rule_errors(
        {"numpy": cfg}, {upstream.trap_node("t")}, expected_dir=work / "expected"
    )
    assert not any("also left out by" in e for e in errors), errors


def test_a_regrtest_suite_has_no_fuel_facts_and_caps_count_them(work) -> None:
    py = upstream.Config(
        **{**_cfg("python").__dict__, "runner": "regrtest", "fuel_facts": [_fact()]}
    )
    assert any(
        "only a pytest suite" in e for e in upstream.fact_errors("python", py, upstream.paths.REPO)
    )
    big = _fact(fuel=3 * 10**12)
    errors = upstream.rule_errors(
        {"numpy": _cfg(fuel_facts=[big])}, set(), expected_dir=work / "expected"
    )
    assert any("caps" in e for e in errors), errors
