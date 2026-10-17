"""Carried patches (spec 020): the one applier the build and the judge share, the patched
zero-diff check, and the rules a patch and its pull request draft must keep. Each case makes a
small tarball and tree in a temporary folder; the applier runs under `sh` with `git`. Nothing
here measures time."""

from __future__ import annotations

import difflib
import io
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

from harness import paths, pins, scan

APPLIER = paths.REPO / "scripts" / "steps" / "apply_patches.sh"
SH, GIT = shutil.which("sh"), shutil.which("git")
TOP = "proj-1.2.3"
FILES = {
    "a.c": b"int a(void) {\n  return 1;\n}\n",
    "win.bat": b"@echo off\r\necho one\r\necho two\r\n",
    "del.txt": b"to be deleted\n",
    "sub/b.c": b"int b;\n",
}


@pytest.fixture
def tools():
    if SH is None or GIT is None:
        pytest.skip("needs: a POSIX sh and git")


def _tarball(base: Path) -> Path:
    path = base / f"{TOP}.tar.gz"
    with tarfile.open(path, "w:gz") as t:
        for i, (name, data) in enumerate(sorted(FILES.items())):
            info = tarfile.TarInfo(f"{TOP}/{name}")
            info.size, info.mtime, info.mode = len(data), 1_700_000_000 + i, 0o644
            t.addfile(info, io.BytesIO(data))
    return path


def _tree(base: Path, tarball: Path) -> Path:
    out = base / "build"
    out.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tarball) as t:
        t.extractall(out, filter="tar")
    return out / TOP


def _edit(name: str, old: bytes, new: bytes) -> str:
    """A git-form patch changing one file; CRLF lines keep their CR."""
    lines = difflib.unified_diff(
        old.decode().splitlines(keepends=True),
        new.decode().splitlines(keepends=True),
        f"a/{name}",
        f"b/{name}",
    )
    return f"diff --git a/{name} b/{name}\n" + "".join(lines)


def _add(name: str, data: bytes) -> str:
    body = "".join("+" + line for line in data.decode().splitlines(keepends=True))
    n = len(data.decode().splitlines())
    return (
        f"diff --git a/{name} b/{name}\nnew file mode 100644\n--- /dev/null\n+++ b/{name}\n"
        f"@@ -0,0 +1,{n} @@\n{body}"
    )


def _delete(name: str, data: bytes) -> str:
    body = "".join("-" + line for line in data.decode().splitlines(keepends=True))
    n = len(data.decode().splitlines())
    return (
        f"diff --git a/{name} b/{name}\ndeleted file mode 100644\n--- a/{name}\n+++ /dev/null\n"
        f"@@ -1,{n} +0,0 @@\n{body}"
    )


def _patches(base: Path, *texts: str) -> Path:
    d = base / "patches" / TOP
    d.mkdir(parents=True, exist_ok=True)
    for i, text in enumerate(texts, 1):
        (d / f"{i:04d}-change.patch").write_bytes(text.encode())
    return d


def _apply(tree: Path, d: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [SH, str(APPLIER), str(tree), str(d)], capture_output=True, text=True, env=env, timeout=60
    )


NEW_A = b"int a(void) {\n  return 2;\n}\n"


def test_a_patch_that_fits_is_applied_byte_for_byte(tools, tmp_path) -> None:
    tree = _tree(tmp_path, _tarball(tmp_path))
    d = _patches(tmp_path, _edit("a.c", FILES["a.c"], NEW_A))
    out = _apply(tree, d)
    assert out.returncode == 0, out.stderr
    assert (tree / "a.c").read_bytes() == NEW_A


def test_patches_apply_in_order_and_may_build_on_each_other(tools, tmp_path) -> None:
    tree = _tree(tmp_path, _tarball(tmp_path))
    third = b"int a(void) {\n  return 3;\n}\n"
    d = _patches(tmp_path, _edit("a.c", FILES["a.c"], NEW_A), _edit("a.c", NEW_A, third))
    assert _apply(tree, d).returncode == 0
    assert (tree / "a.c").read_bytes() == third


@pytest.mark.parametrize("case", ["does not fit", "at an offset", "empty"])
def test_a_patch_that_is_not_exact_stops_the_step_with_one_line(tools, tmp_path, case) -> None:
    tree = _tree(tmp_path, _tarball(tmp_path))
    if case == "does not fit":
        text = _edit("a.c", b"int a(void) {\n  return 9;\n}\n", NEW_A)
    elif case == "at an offset":
        (tree / "a.c").write_bytes(b"// one\n// two\n" + FILES["a.c"])
        text = _edit("a.c", FILES["a.c"], NEW_A)
    else:
        text = ""
    before = (tree / "a.c").read_bytes()
    out = _apply(tree, _patches(tmp_path, text))
    assert out.returncode == 1
    assert out.stderr.strip().count("\n") == 0 and out.stderr.startswith("ERROR: 0001-change.patch")
    if case != "at an offset":
        assert (tree / "a.c").read_bytes() == before


def test_the_callers_git_settings_change_nothing(tools, tmp_path) -> None:
    """Each setting the pre-build review found changing the bytes or skipping a patch (spec 020,
    Decision 3), all at once: the applier clears them."""
    clean_tree = _tree(tmp_path / "clean", _tarball(tmp_path))
    d = _patches(tmp_path, _edit("a.c", FILES["a.c"], NEW_A) + _add("n.c", b"int n;\n"))
    assert _apply(clean_tree, d).returncode == 0
    home = tmp_path / "home"
    (home / ".config" / "git").mkdir(parents=True)
    (home / ".gitconfig").write_text("[core]\n\tautocrlf = true\n[apply]\n\twhitespace = fix\n")
    (home / ".config" / "git" / "attributes").write_text("* text eol=crlf\n")
    other = tmp_path / "other"
    subprocess.run([GIT, "init", "-q", str(other)], check=True)
    env = {
        **os.environ,
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.autocrlf",
        "GIT_CONFIG_VALUE_0": "true",
        "GIT_DIR": str(other / ".git"),
        "GIT_WORK_TREE": str(other),
    }
    tree = _tree(tmp_path / "hostile", _tarball(tmp_path))
    out = _apply(tree, d, env)
    assert out.returncode == 0, out.stderr
    for name in ("a.c", "n.c", "win.bat"):
        assert (tree / name).read_bytes() == (clean_tree / name).read_bytes(), name


def test_a_patch_to_a_crlf_file_survives_a_commit(tools, tmp_path) -> None:
    """`.gitattributes` keeps `recipes/patches/**` byte for byte (spec 020, Decision 4)."""
    repo = tmp_path / "repo"
    subprocess.run([GIT, "init", "-q", str(repo)], check=True)
    shutil.copy(paths.REPO / ".gitattributes", repo / ".gitattributes")
    d = repo / "recipes" / "patches" / TOP
    d.mkdir(parents=True)
    new = b"@echo off\r\necho one\r\necho three\r\n"
    (d / "0001-bat.patch").write_bytes(_edit("win.bat", FILES["win.bat"], new).encode())
    git = [GIT, "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-qm", "x"], check=True)
    (d / "0001-bat.patch").unlink()
    subprocess.run([*git, "checkout", "--", "."], check=True)
    attr = subprocess.run(
        [*git, "check-attr", "text", "recipes/patches/x/0001-y.patch"],
        capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip
    assert attr.strip().endswith("text: unset"), attr
    tree = _tree(tmp_path, _tarball(tmp_path))
    out = _apply(tree, d)
    assert out.returncode == 0, out.stderr
    assert (tree / "win.bat").read_bytes() == new


def test_mtimes_never_make_an_input_newer(tools, tmp_path) -> None:
    tree = _tree(tmp_path, _tarball(tmp_path))
    before = os.stat(tree / "a.c").st_mtime_ns
    newest = max(os.stat(p).st_mtime_ns for p in tree.rglob("*") if p.is_file())
    d = _patches(tmp_path, _edit("a.c", FILES["a.c"], NEW_A) + _add("n.c", b"int n;\n"))
    assert _apply(tree, d).returncode == 0
    assert os.stat(tree / "a.c").st_mtime_ns == before
    assert os.stat(tree / "n.c").st_mtime_ns == newest


def test_the_zero_diff_check_takes_exactly_the_recorded_patches(tools, tmp_path) -> None:
    tarball = _tarball(tmp_path)
    text = (
        _edit("a.c", FILES["a.c"], NEW_A)
        + _delete("del.txt", FILES["del.txt"])
        + _add("sub/n.c", b"int n;\n")
    )
    root = tmp_path / "recipes"
    _patches(root, text)
    patches = root / "patches"
    tree = _tree(tmp_path, tarball)
    assert {d.split(":")[0] for d in pins.tree_drift(tarball, tree, patches)} == {
        "a.c",
        "del.txt",
        "sub/n.c",
    }  # unpatched: the edit, the deletion and the added file are each seen
    assert _apply(tree, patches / TOP).returncode == 0
    assert not (tree / "del.txt").exists()  # deleted, not left as an empty file (review, F1)
    assert pins.tree_drift(tarball, tree, patches) == []
    (tree / "del.txt").write_bytes(b"")  # an empty file left where a patch deleted one
    assert pins.tree_drift(tarball, tree, patches) == ["del.txt: a recorded patch deletes it"]
    (tree / "del.txt").unlink()
    (tree / "sub" / "b.c").write_bytes(b"int b = 1;\n")
    assert pins.tree_drift(tarball, tree, patches) == ["sub/b.c: modified"]


GOOD_DRAFT = """- **Project:** proj (https://example.org/proj)
- **Against:** 1.2.3 (the pinned tarball)
- **Status:** drafted
- **Title:** Return 2
- **Files:** a.c
- **Why we carry it:** a() must return 2 here.

The text for the maintainers.
"""


def _repo(tmp_path: Path, patch: str, draft: str = GOOD_DRAFT, name: str = "0001-two") -> Path:
    root = tmp_path / "root"
    (root / "recipes" / "patches" / TOP).mkdir(parents=True)
    (root / "context" / "upstream" / "patches" / TOP).mkdir(parents=True)
    (root / "recipes" / "patches" / TOP / f"{name}.patch").write_text(patch)
    (root / "context" / "upstream" / "patches" / TOP / f"{name}.md").write_text(draft)
    (root / "CHANGELOG.md").write_text(f"- carries `recipes/patches/{TOP}/{name}.patch`\n")
    (root / "README.md").write_text("| x | upstream patches carried: 1, each … |\n")
    return root


def test_a_correct_patch_folder_breaks_no_rule(tmp_path) -> None:
    root = _repo(tmp_path, _edit("a.c", FILES["a.c"], NEW_A))
    assert scan.patch_errors(root, {TOP}) == []


@pytest.mark.parametrize(
    ("change", "error"),
    [
        (lambda r: None, "no pinned source tarball"),  # the folder's top is not pinned
        (lambda r: _write(r, f"recipes/patches/{TOP}/1-fix.patch", "x"), "never be applied"),
        (lambda r: _rm(r, f"context/upstream/patches/{TOP}/0001-two.md"), "no pull request draft"),
        (lambda r: _write(r, f"context/upstream/patches/{TOP}/0002-x.md", GOOD_DRAFT), "no patch"),
        (lambda r: _write(r, "CHANGELOG.md", "nothing\n"), "not named in CHANGELOG"),
        (lambda r: _write(r, "README.md", "upstream patches carried: 0\n"), "carried: 1"),
        (lambda r: _sub(r, "- **Title:**", "- Title:"), "line 4 must be"),
        (lambda r: _sub(r, "drafted", "thinking about it"), "is not drafted"),
        (lambda r: _sub(r, "drafted", "released 1.2.3"), "delete the patch"),
        (lambda r: _sub(r, "**Files:** a.c", "**Files:** b.c"), "Files lists"),
    ],
)
def test_each_rule_names_what_breaks_it(tmp_path, change, error) -> None:
    root = _repo(tmp_path, _edit("a.c", FILES["a.c"], NEW_A))
    change(root)
    tops = set() if error == "no pinned source tarball" else {TOP}
    errors = scan.patch_errors(root, tops)
    assert any(error in e for e in errors), errors


def test_released_in_a_later_version_is_allowed(tmp_path) -> None:
    root = _repo(tmp_path, _edit("a.c", FILES["a.c"], NEW_A))
    _sub(root, "drafted", "released 1.10.0")
    assert scan.patch_errors(root, {TOP}) == []


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("diff --git a/l b/l\nnew file mode 120000\n--- /dev/null\n+++ b/l\n", "adds a link"),
        ("diff --git a/a.c b/a.c\nold mode 100644\nnew mode 100755\n", "changes a mode"),
        ("diff --git a/x.bin b/x.bin\nGIT binary patch\nliteral 1\n", "binary hunk"),
        ("diff --git a/a.c b/c.c\nrename from a.c\nrename to c.c\n", "renames a file"),
        ("diff --git a/../e b/../e\n--- a/../e\n+++ b/../e\n@@ -1 +1 @@\n-x\n+y\n", "e"),
        (_edit("Makefile.am", b"x\n", b"y\n"), "autotools"),
        (_edit("m4/x.m4", b"x\n", b"y\n"), "autotools"),
        (_add("run.sh", b"echo\n").replace("100644", "100755"), "mode"),
        # git applies by the ---/+++ names, and a plain section after a hunk (review, F2)
        (
            "diff --git a/src/a.c b/src/a.c\n--- a/configure.ac\n+++ b/configure.ac\n"
            "@@ -1 +1 @@\n-x\n+y\n",
            "configure.ac",
        ),
        (
            _edit("a.c", b"x\n", b"y\n") + _edit("Makefile.am", b"x\n", b"y\n").split("\n", 1)[1],
            "autotools",
        ),
    ],
)
def test_a_risky_patch_shape_is_refused(text, error) -> None:
    errors, _ = scan.patch_shape_errors(text, "p")
    assert any(error in e for e in errors), errors


def test_only_a_patchs_own_lines_are_scanned_for_embedder_names(tmp_path) -> None:
    root = tmp_path / "r"
    (root / "recipes").mkdir(parents=True)
    patch = root / "recipes" / "x.patch"
    patch.write_text(
        "diff --git a/s.c b/s.c\n--- a/s.c\n+++ b/s.c\n@@ -1 +1 @@\n acmehost\n-acmehost\n+ok\n"
    )
    assert scan.embedder_hits(root, ["recipes"], ["acmehost"]) == []
    patch.write_text("diff --git a/s.c b/s.c\n--- a/s.c\n+++ b/s.c\n@@ -1 +1 @@\n-x\n+acmehost\n")
    assert scan.embedder_hits(root, ["recipes"], ["acmehost"]) == ["recipes/x.patch:6"]


def _write(root: Path, rel: str, text: str) -> None:
    (root / rel).write_text(text)


def _rm(root: Path, rel: str) -> None:
    (root / rel).unlink()


def _sub(root: Path, old: str, new: str) -> None:
    p = root / "context" / "upstream" / "patches" / TOP / "0001-two.md"
    p.write_text(p.read_text().replace(old, new, 1))


def test_finder_litter_in_the_patch_folders_is_not_ours(tmp_path) -> None:
    root = _repo(tmp_path, _edit("a.c", FILES["a.c"], NEW_A))
    (root / "recipes" / "patches" / ".DS_Store").write_bytes(b"x")
    (root / "recipes" / "patches" / TOP / ".DS_Store").write_bytes(b"x")
    assert scan.patch_errors(root, {TOP}) == []


def test_a_released_version_in_another_form_is_named(tmp_path) -> None:
    root = _repo(tmp_path, _edit("a.c", FILES["a.c"], NEW_A))
    _sub(root, "drafted", "released 1.2")
    errors = scan.patch_errors(root, {TOP})
    assert any("as the pinned file name does (1.2.3)" in e for e in errors), errors


def test_an_added_file_with_any_name_gets_the_newest_time(tools, tmp_path) -> None:
    tree = _tree(tmp_path, _tarball(tmp_path))
    newest = max(os.stat(p).st_mtime_ns for p in tree.rglob("*") if p.is_file())
    assert _apply(tree, _patches(tmp_path, _add("café.c", b"int c;\n"))).returncode == 0
    assert os.stat(tree / "café.c").st_mtime_ns == newest
