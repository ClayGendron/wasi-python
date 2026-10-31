"""Finder litter never breaks a build: `remove` retries, and the zip, the licences and
the artifact set never carry litter. Each case works on a temporary folder; `remove` runs under a
POSIX `sh` with `rm` replaced by a shell function that counts its calls. Nothing measures time.
The zip's package metadata and the `ctypes` stand-in are checked here on the host too."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import pydoc
import re
import shutil
import subprocess
import sys
import types
import zipfile
from pathlib import Path

import pytest

from harness import paths

sys.path.insert(0, str(paths.REPO / "scripts"))

import assemble_artifacts  # noqa: E402
import freeze_bootstrap  # noqa: E402
import litter  # noqa: E402
import make_stdlib_zip  # noqa: E402
import meson_plan  # noqa: E402

REMOVE = paths.REPO / "scripts" / "steps" / "remove.sh"
SH = shutil.which("sh")


def _remove(target, fails: int, *more, removes: bool = True) -> tuple[int, int, str]:
    """`remove target more...` under `set -eu`, with an `rm` that fails its first `fails` calls (a
    negative number: always) and then removes for real, or, with `removes=False`, answers success
    without removing; returns the exit code, the calls, stderr."""
    then = 'command rm "$@"' if removes else "return 0"
    script = f"""
set -eu
calls=0
rm() {{
  calls=$((calls + 1))
  echo "$calls" > "$COUNT"
  if [ {fails} -lt 0 ] || [ "$calls" -le {fails} ]; then
    echo "rm: {{}}: Directory not empty" >&2
    return 1
  fi
  {then}
}}
. "$REMOVE"
remove "$TARGET" {" ".join(f'"{m}"' for m in more)}
"""
    count = target.parent / "count"
    env = {
        "PATH": os.environ.get("PATH", os.defpath),
        "COUNT": str(count),
        "REMOVE": str(REMOVE),
        "TARGET": str(target),
    }
    out = subprocess.run([SH, "-c", script], env=env, capture_output=True, text=True, timeout=60)
    calls = int(count.read_text()) if count.exists() else 0
    return out.returncode, calls, out.stderr


def _tree(tmp_path):
    target = tmp_path / "out"
    (target / "deep").mkdir(parents=True)
    (target / "deep" / ".DS_Store").write_bytes(b"x")
    return target


@pytest.mark.parametrize(("fails", "calls"), [(0, 1), (1, 2), (2, 3)])
def test_remove_retries_until_the_path_is_gone(tmp_path, fails, calls) -> None:
    if SH is None:
        pytest.skip("needs: a POSIX sh")  # blocked, never passed or failed (B)
    target = _tree(tmp_path)
    assert _remove(target, fails)[:2] == (0, calls)
    assert not target.exists()


def test_remove_stops_after_three_attempts_with_one_line(tmp_path) -> None:
    if SH is None:
        pytest.skip("needs: a POSIX sh")
    target = _tree(tmp_path)
    code, calls, err = _remove(target, -1)
    assert (code, calls) == (1, 3) and target.exists()
    assert err.strip().splitlines()[-1] == f"ERROR: cannot remove {target}"
    assert err.count("Directory not empty") == 1  # only the third attempt's error is shown


def test_remove_removes_a_dangling_link_or_says_so(tmp_path) -> None:
    if SH is None:
        pytest.skip("needs: a POSIX sh")
    if sys.platform == "win32":
        pytest.skip("needs: the privilege to make a link (Windows)")
    link = tmp_path / "link"
    link.symlink_to(tmp_path / "nothing")
    assert _remove(link, 0)[:2] == (0, 1) and not link.is_symlink()
    link.symlink_to(tmp_path / "nothing")  # an rm that reports success but leaves the link
    code, calls, err = _remove(link, 0, removes=False)
    assert (code, calls) == (1, 1) and link.is_symlink() and "cannot remove" in err


def test_remove_removes_every_path_it_is_given(tmp_path) -> None:
    if SH is None:
        pytest.skip("needs: a POSIX sh")
    first, second = tmp_path / "a", tmp_path / "b"
    first.mkdir()
    second.mkdir()
    assert _remove(first, 0, second)[:2] == (0, 2)
    assert not first.exists() and not second.exists()


# Every litter name this host can create (a Windows file name cannot hold `Icon\r`'s CR), an
# AppleDouble file, and a file inside a volume's litter folder.
PLANTABLE = sorted(n for n in litter.OS_LITTER if sys.platform != "win32" or "\r" not in n)


def _plant_litter(folder: Path) -> None:
    (folder / ".TemporaryItems").mkdir(exist_ok=True)  # a volume's folder, with a file in it
    (folder / ".TemporaryItems" / "x.py").write_text("x = 1\n")
    for name in PLANTABLE:
        if not (folder / name).exists():
            (folder / name).write_bytes(b"litter")
    (folder / "._mod.py").write_bytes(b"\0\5\26\7")  # AppleDouble: not Python


def test_the_zip_walk_skips_litter(tmp_path) -> None:
    for tree in ("a", "b"):
        (tmp_path / tree / "pkg").mkdir(parents=True)
        (tmp_path / tree / "pkg" / f"mod_{tree}.py").write_text("x = 1\n")
        _plant_litter(tmp_path / tree)
        _plant_litter(tmp_path / tree / "pkg")
    names = [n for tree in ("a", "b") for _, n in make_stdlib_zip.walk(tmp_path / tree)]
    assert sorted(names) == ["pkg/mod_a.py", "pkg/mod_b.py"]


def test_step_90_drops_litter_and_skips_it_in_licences(tmp_path) -> None:
    (tmp_path / "LICENSES").mkdir(parents=True)
    (tmp_path / "LICENSES" / "A_LICENSE").write_text("a")
    (tmp_path / "LICENSES" / ".DS_Store").write_bytes(b"x")
    (tmp_path / "LICENSES" / "._A_LICENSE").write_bytes(b"x")
    (tmp_path / "Thumbs.db").write_bytes(b"x")
    (tmp_path / "python.wasm").write_bytes(b"\0asm")
    _plant_litter(tmp_path)
    assert [p.name for p in assemble_artifacts.licence_files(tmp_path / "LICENSES")] == [
        "A_LICENSE"
    ]
    assemble_artifacts.drop_litter(tmp_path)
    assert sorted(p.name for p in tmp_path.rglob("*")) == ["A_LICENSE", "LICENSES", "python.wasm"]


def test_step_90_never_lists_litter(tmp_path) -> None:
    (tmp_path / "LICENSES").mkdir()
    for name in ("python.wasm", "LICENSES/zlib.txt", ".DS_Store", "LICENSES/Thumbs.db"):
        (tmp_path / name).write_bytes(b"x")
    _plant_litter(tmp_path)
    _plant_litter(tmp_path / "LICENSES")
    names = [p.relative_to(tmp_path).as_posix() for p in assemble_artifacts.listed_files(tmp_path)]
    assert names == ["LICENSES/zlib.txt", "python.wasm"]


def test_step_90_removes_or_says_why(tmp_path, monkeypatch) -> None:
    assemble_artifacts._remove(tmp_path / "never-made")  # already gone: success
    folder = tmp_path / "set"
    (folder / "x").mkdir(parents=True)
    assemble_artifacts._remove(folder)
    assert not folder.exists()
    folder.mkdir()
    monkeypatch.setattr(shutil, "rmtree", lambda *a, **k: None)  # a folder that will not go
    with pytest.raises(SystemExit, match="ERROR: cannot remove"):
        assemble_artifacts._remove(folder)


def test_the_scripts_litter_is_the_judges() -> None:
    """One definition in two copies, the names and both rules."""
    assert set(litter.OS_LITTER) == set(paths.OS_LITTER)
    assert all(litter.is_litter(n) for n in ("._x.py", "Icon\r", ".TemporaryItems", "ehthumbs.db"))
    names = [*paths.OS_LITTER, "._x", "a.py", "Icon", "DS_Store", ".gitignore", "_x"]
    assert [litter.is_litter(n) for n in names] == [paths.is_litter(n) for n in names]
    rels = ["a/b.py", "a/.DS_Store", ".TemporaryItems/x.py", "a/._b.py", "LICENSES/x.txt"]
    assert [litter.has_litter(r) for r in rels] == [False, True, True, True, False]
    assert [paths.has_litter(r) for r in rels] == [False, True, True, True, False]


def test_the_git_excludes_keep_out_exactly_the_litter(tmp_path) -> None:
    """The pathspecs make_openblas_void_patch.sh adds with leave out of the
    index exactly the paths `has_litter` names, through real git, so git never opens a litter
    file and the unstage (by `has_litter`) has nothing left to do."""
    assert not any(set(n) & set("*?[]\\") for n in litter.OS_LITTER), "a glob character"
    keep = ["keep.c", "sub/keep.c", "DS_Store", "x._y", "Icon", ".DS_Store.bak", ".gitignore"]
    drop = [".DS_Store", "sub/deep/.DS_Store", "sub/._x.c", "._top", ".Trashes/inside", "._d/f"]
    drop += ["Thumbs.db", "sub/desktop.ini", ".Spotlight-V100/a", "sub/ehthumbs.db"]
    if sys.platform != "win32":  # a name with a carriage return
        drop += ["Icon\r", "sub/Icon\r"]
    tree = tmp_path / "tree"
    for rel in keep + drop:
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_text("")
    assert [litter.has_litter(r) for r in keep + drop] == [False] * len(keep) + [True] * len(drop)
    specs = tmp_path / "add.pathspec"
    specs.write_bytes(b"\0".join(s.encode() for s in [".", *litter.git_excludes()]))
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(tmp_path),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CEILING_DIRECTORIES": str(tmp_path),
    }

    def git(*args: str) -> str:
        done = subprocess.run(
            ["git", "-c", "core.quotePath=false", "-C", str(tree), *args],
            capture_output=True,
            env=env,
        )
        assert done.returncode == 0, done.stderr.decode(errors="replace")
        return done.stdout.decode()

    git("init", "-q")
    git("add", "-A", "--force", f"--pathspec-from-file={specs}", "--pathspec-file-nul")
    staged = sorted(p for p in git("ls-files", "--cached", "-z").split("\0") if p)
    assert staged == sorted(keep), staged


@pytest.mark.skipif(sys.platform == "win32", reason="a Windows file name cannot hold Icon\\r's CR")
def test_the_repository_ignores_litter_itself() -> None:
    """Step 90's untracked check and `paths.dirty_path` must not stop on a
    Finder file on a Mac without the owner's global ignore, so the user's excludes are off here."""
    if shutil.which("git") is None:
        pytest.skip("needs: git")

    def ignored(name: str) -> bool:
        r = subprocess.run(
            ["git", "-C", str(paths.REPO), "-c", f"core.excludesFile={os.devnull}",
             "check-ignore", "-q", "--no-index", "--", name],
            capture_output=True,
        )  # fmt: skip
        return r.returncode == 0

    for name in (".DS_Store", "scripts/.DS_Store", "recipes/._x.py", "Icon\r", "recipes/Icon\r"):
        assert ignored(name), name
    for name in ("Icon", "Iconr", "recipes/x.py", "scripts/litter.py"):
        assert not ignored(name), name


# The zip carries package metadata, and the ctypes stand-in names and refuses.

STAND_IN = paths.REPO / "recipes" / "ctypes_stand_in"
REFUSED = "ctypes is unavailable on wasm32-wasi"


def test_the_zip_keeps_a_wheels_metadata_and_entry_points(tmp_path) -> None:
    info = "x-1.0.dist-info"
    kept = {
        "x/__init__.py": b"x = 1\n",
        f"{info}/METADATA": b"Metadata-Version: 2.1\nName: x\nVersion: 1.0\n\nbody\n",
        f"{info}/entry_points.txt": b"[console_scripts]\nx = x:main\n",
    }
    dropped = {
        "x-1.0.data/data/share/x.txt": b"data",
        "x.egg-info/PKG-INFO": b"Name: x\n",
        **{
            f"{info}/{name}": name.encode()
            for name in (
                "RECORD",
                "WHEEL",
                "INSTALLER",
                "REQUESTED",
                "direct_url.json",
                "top_level.txt",
                "zip-safe",
                "licenses/LICENSE",
            )
        },
    }
    wheel = tmp_path / "x-1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as z:
        for name, data in sorted({**kept, **dropped}.items()):
            z.writestr(name, data)
    got = {name: data for data, name in make_stdlib_zip.wheel_members(wheel)}
    assert got == kept


def test_an_sdists_pkg_info_becomes_metadata(tmp_path) -> None:
    good = tmp_path / "good" / "PKG-INFO"
    good.parent.mkdir()
    text = b"Metadata-Version: 2.4\nName: Foo.Bar-baz\nVersion: 1.0\n\nName: not a header\n"
    good.write_bytes(text)
    assert make_stdlib_zip.sdist_metadata(good) == (text, "foo_bar_baz-1.0.dist-info/METADATA")
    for case, body in {
        "no-name": "Metadata-Version: 2.1\nVersion: 1.0\n",
        "no-version": "Metadata-Version: 2.1\nName: foo\n",
        "two-versions": "Name: foo\nVersion: 1.0\nVersion: 2.0\n",
        "after-the-blank": "Name: foo\n\nVersion: 1.0\n",
    }.items():
        bad = tmp_path / case / "PKG-INFO"
        bad.parent.mkdir()
        bad.write_text(body)
        with pytest.raises(SystemExit) as stop:
            make_stdlib_zip.sdist_metadata(bad)
        line = str(stop.value)
        assert str(bad) in line and "\n" not in line, f"{case}: {line!r}"


def test_an_sdists_entry_points_go_beside_its_metadata(tmp_path, monkeypatch) -> None:
    """`--entry-points` packs the file, bytes unchanged, in the folder `--metadata` names for the
    same PKG-INFO; one whose folder has no METADATA member stops in one line naming both files,
    matched by the computed folder, however the PKG-INFO path is spelled.
    The guard gets the members gathered, as main gives it."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "x").mkdir()
    pkg_info = tmp_path / "x" / "PKG-INFO"
    text = b"Metadata-Version: 2.1\nName: Some.Pkg\nVersion: 1.0\n\nbody\n"
    pkg_info.write_bytes(text)
    entry = tmp_path / "x" / "entry_points.txt"
    entry.write_bytes(b"[some.group]\nname = some_pkg.mod:thing\n")
    data, metadata = make_stdlib_zip.sdist_metadata(Path("x/PKG-INFO"))
    assert (data, metadata) == (text, "some_pkg-1.0.dist-info/METADATA")
    for spelled in ("x/PKG-INFO", "./x/PKG-INFO", "x/../x/PKG-INFO", str(pkg_info)):
        got = make_stdlib_zip.sdist_entry_points(Path(spelled), entry)
        assert got == (entry.read_bytes(), "some_pkg-1.0.dist-info/entry_points.txt")
        placed = [(Path(spelled), entry, got[1])]
        make_stdlib_zip.check_entry_points({metadata: b""}, placed)
        with pytest.raises(SystemExit) as stop:
            make_stdlib_zip.check_entry_points({"other-1.0.dist-info/METADATA": b""}, placed)
        line = str(stop.value)
        assert str(Path(spelled)) in line and str(entry) in line and "\n" not in line, line


def test_main_puts_entry_points_beside_metadata_or_stops(tmp_path, monkeypatch) -> None:
    """main() runs the guard after every input is gathered: `--entry-points` with no `--metadata`
    for its PKG-INFO stops naming both files; with the same PKG-INFO spelled another way under
    `--metadata`, the zip holds both members, the entry points' bytes unchanged.
    The line's version check and the host-neutral rewrite are
    set aside, as this zip has no stdlib."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(make_stdlib_zip, "TARGET", sys.version_info[:2])
    monkeypatch.setattr(make_stdlib_zip, "REWRITE", ())
    monkeypatch.setenv("PYTHONHASHSEED", "0")
    (tmp_path / "lib").mkdir()
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "PKG-INFO").write_text("Name: Some.Pkg\nVersion: 1.0\n\n")
    entry = b"[some.group]\nname = some_pkg.mod:thing\n"
    (tmp_path / "x" / "entry_points.txt").write_bytes(entry)
    base = ["make_stdlib_zip.py", "--lib", "lib"]
    tail = ["--entry-points", "x/PKG-INFO", "x/entry_points.txt", "out.zip"]
    monkeypatch.setattr(sys, "argv", base + tail)
    with pytest.raises(SystemExit) as stop:
        make_stdlib_zip.main()
    line = str(stop.value)
    assert "x/PKG-INFO" in line and "x/entry_points.txt" in line and "METADATA" in line, line
    monkeypatch.setattr(sys, "argv", base + ["--metadata", "x/../x/PKG-INFO"] + tail)
    make_stdlib_zip.main()
    with zipfile.ZipFile(tmp_path / "out.zip") as z:
        assert sorted(z.namelist()) == [
            "some_pkg-1.0.dist-info/METADATA",
            "some_pkg-1.0.dist-info/entry_points.txt",
        ]
        assert z.read("some_pkg-1.0.dist-info/entry_points.txt") == entry


def test_a_left_out_folder_is_not_packed(tmp_path, monkeypatch) -> None:
    """A wheel's folder is left out by the `--drop` matplotlib's build added, which applies to
    every input, so no option of its own is added. `Selection.take` drops exactly the members
    under the folder, whether written with a trailing slash or not, keeps a sibling whose name
    only starts the same (`pkg/subway.py`), and records the folder as matched; it is given each
    member's name before `.py` becomes `.pyc`. Through main(), the zip holds the rest with their
    compiled names and nothing under the folder; a folder that matches nothing (a renamed
    upstream folder, a string prefix that is not a folder, a compiled file's name) stops the build
    in one line naming it."""
    wheel = tmp_path / "pkg-1.0-py3-none-any.whl"
    members = {
        "pkg/__init__.py": b"x = 1\n",
        "pkg/subway.py": b"y = 2\n",
        "pkg/sub/__init__.py": b"",
        "pkg/sub/mod.py": b"z = 3\n",
        "pkg/sub/fonts/Vera.ttf": b"font",
        "pkg-1.0.dist-info/METADATA": b"Metadata-Version: 2.1\nName: pkg\nVersion: 1.0\n\n",
    }
    with zipfile.ZipFile(wheel, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
    for written in ("pkg/sub", "pkg/sub/"):
        chosen = make_stdlib_zip.Selection([written], [], [])
        seen = []
        for data, name in make_stdlib_zip.wheel_members(wheel):
            if chosen.take(data, name):
                seen.append(name)
        assert seen == ["pkg-1.0.dist-info/METADATA", "pkg/__init__.py", "pkg/subway.py"]
        assert chosen.matched == {"pkg/sub"}
        chosen.check()
    # Names are matched as the input gives them, before compiling: a file kept by name is named
    # with its .py, which a rule given the compiled name would not find.
    chosen = make_stdlib_zip.Selection([], ["pkg/sub=mod.py"], [])
    kept = [name for data, name in make_stdlib_zip.wheel_members(wheel) if chosen.take(data, name)]
    assert kept == [
        "pkg-1.0.dist-info/METADATA",
        "pkg/__init__.py",
        "pkg/sub/mod.py",
        "pkg/subway.py",
    ]
    chosen.check()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(make_stdlib_zip, "TARGET", sys.version_info[:2])
    monkeypatch.setattr(make_stdlib_zip, "REWRITE", ())
    monkeypatch.setenv("PYTHONHASHSEED", "0")
    (tmp_path / "lib").mkdir()
    base = ["make_stdlib_zip.py", "--lib", "lib", "--wheel", wheel.name]
    monkeypatch.setattr(sys, "argv", [*base, "--drop", "pkg/sub", "out.zip"])
    make_stdlib_zip.main()
    with zipfile.ZipFile(tmp_path / "out.zip") as z:
        assert sorted(z.namelist()) == [
            "pkg-1.0.dist-info/METADATA",
            "pkg/__init__.pyc",
            "pkg/subway.pyc",
        ]
    for wrong in ("pkg/gone", "pkg/su", "pkg/sub/mod.pyc"):
        monkeypatch.setattr(sys, "argv", [*base, "--drop", wrong, "out.zip"])
        with pytest.raises(SystemExit) as stop:
            make_stdlib_zip.main()
        line = str(stop.value)
        assert line == f"--drop, --keep or --inner matched no member: {wrong}", line


def test_a_tree_with_package_metadata_stops_the_zip(tmp_path) -> None:
    for folder in ("x-1.0.dist-info", "x.egg-info"):
        tree = tmp_path / folder.replace(".", "_")
        (tree / "x").mkdir(parents=True)
        (tree / "x" / "__init__.py").write_text("x = 1\n")
        (tree / folder).mkdir()
        (tree / folder / "PKG-INFO").write_text("Name: x\n")
        with pytest.raises(SystemExit) as stop:
            list(make_stdlib_zip.tree_members(tree))
        assert str(stop.value) == (
            f"{tree}: {folder} holds package metadata; pass the package as a wheel, "
            "or its sdist's PKG-INFO with --metadata"
        )
    deep = tmp_path / "deep"
    (deep / "pkg" / "y.egg-info").mkdir(parents=True)
    (deep / "pkg" / "y.egg-info" / "PKG-INFO").write_text("Name: y\n")
    (deep / "pkg" / "mod.py").write_text("y = 1\n")
    assert [name for _, name in make_stdlib_zip.tree_members(deep)] == ["pkg/mod.py"]


def test_a_staged_tree_ignores_litter(tmp_path) -> None:
    """A tree staged as step 70 stages pyyaml's and markupsafe's pure
    folders (a fresh folder holding a copied package) gives the same members, names and bytes,
    with Finder litter at the tree's top and inside the package."""

    def stage(where, litter: bool):
        tree = where / "pure-install"
        (tree / "pkg" / "sub").mkdir(parents=True)
        (tree / "pkg" / "__init__.py").write_text("x = 1\n")
        (tree / "pkg" / "sub" / "mod.py").write_text("y = 2\n")
        (tree / "pkg" / "py.typed").write_text("")
        if litter:
            for folder in (tree, tree / "pkg", tree / "pkg" / "sub"):
                (folder / ".DS_Store").write_bytes(b"\0Bud1")
        return tree

    clean = list(make_stdlib_zip.tree_members(stage(tmp_path / "clean", False)))
    littered = list(make_stdlib_zip.tree_members(stage(tmp_path / "littered", True)))
    assert [name for _, name in clean] == ["pkg/__init__.py", "pkg/py.typed", "pkg/sub/mod.py"]
    assert littered == clean


def _load_stand_in():
    """The recipe folder as a package under a private name, never as `ctypes`, so that its
    relative import of `._types` resolves and nothing on the host can import it as `ctypes`."""
    name = "_ctypes_stand_in_under_test"
    for key in [k for k in sys.modules if k == name or k.startswith(name + ".")]:
        del sys.modules[key]
    spec = importlib.util.spec_from_file_location(
        name, STAND_IN / "__init__.py", submodule_search_locations=[str(STAND_IN)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _refuses(call) -> None:
    with pytest.raises(OSError) as refused:
        call()
    assert str(refused.value) == REFUSED


# Decision 5's names, written here rather than read from the stand-in: sympy's first.
STAND_IN_TYPES = (
    "c_long", "sizeof", "c_bool", "c_char", "c_wchar", "c_byte", "c_ubyte", "c_short", "c_ushort",
    "c_int", "c_uint", "c_ulong", "c_longlong", "c_ulonglong", "c_size_t", "c_ssize_t", "c_float",
    "c_double", "c_longdouble", "c_char_p", "c_wchar_p", "c_void_p", "c_int8", "c_int16",
    "c_int32", "c_int64", "c_uint8", "c_uint16", "c_uint32", "c_uint64", "c_time_t",
    "Structure", "Union", "POINTER", "CFUNCTYPE", "PYFUNCTYPE", "CDLL", "PyDLL", "LibraryLoader",
    "cdll", "pydll", "byref", "pointer", "cast", "addressof", "memmove", "memset", "string_at",
    "wstring_at", "create_string_buffer", "create_unicode_buffer", "resize", "get_errno",
    "set_errno",
)  # fmt: skip
STAND_IN_CONSTANTS = ("DEFAULT_MODE", "RTLD_GLOBAL", "RTLD_LOCAL", "WinError")
# The types whose instances hold a value, written here too.
NUMERIC_TYPES = (
    "c_bool", "c_byte", "c_ubyte", "c_short", "c_ushort", "c_int", "c_uint", "c_long", "c_ulong",
    "c_longlong", "c_ulonglong", "c_int8", "c_int16", "c_int32", "c_int64", "c_uint8", "c_uint16",
    "c_uint32", "c_uint64", "c_size_t", "c_ssize_t", "c_float", "c_double", "c_longdouble",
)  # fmt: skip
VALUE_TYPES = (*NUMERIC_TYPES, "c_void_p")
# wasm32's sizes, which `struct.calcsize` gives in the guest: the host checks size the stand-in's
# types as the guest does, so the wraps they assert are wasm32's.
WASM32_SIZES = {"?": 1, "c": 1, "b": 1, "B": 1, "h": 2, "H": 2, "i": 4, "I": 4, "l": 4, "L": 4,
                "q": 8, "Q": 8, "f": 4, "d": 8, "P": 4}  # fmt: skip


def _load_stand_in_as_wasm32(monkeypatch):
    """The stand-in with `struct.calcsize` answering wasm32's sizes while its types are built (on
    the first lookup, which this makes before returning)."""
    import struct

    real = struct.calcsize
    monkeypatch.setattr(struct, "calcsize", lambda code: WASM32_SIZES.get(code) or real(code))
    ct = _load_stand_in()
    assert f"{ct.__name__}._types" not in sys.modules, "the builder loaded at import"
    assert ct.sizeof(ct.c_long) == 4 and ct.c_int is ct.c_long and ct.sizeof(ct.c_void_p) == 4
    return ct


def test_the_zips_code_carries_the_name_it_is_given() -> None:
    """`pyc` compiles under the name it is given, and every nested code
    object carries it, so the zip's code names the path zipimport gives the module."""
    import marshal

    name = "/usr/local/lib/python3XY.zip/pkg/mod.py"
    src = b"class A:\n    def f(self):\n        return [x for x in (lambda: [1])()]\n"
    names = set()

    def walk(code) -> None:
        names.add(code.co_filename)
        for c in code.co_consts:
            if hasattr(c, "co_filename"):
                walk(c)

    walk(marshal.loads(make_stdlib_zip.pyc(src, name)[16:]))
    assert names == {name}


@pytest.mark.parametrize("prefix", ["usr/local/lib/python315.zip/", "/usr/local/lib/x/", "/a.zip"])
def test_the_zip_refuses_a_code_prefix_that_is_not_an_absolute_zip_path(
    prefix, monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(sys, "argv", ["make_stdlib_zip.py", "--lib", str(tmp_path)])
    sys.argv += ["--code-prefix", prefix, str(tmp_path / "out.zip")]
    with pytest.raises(SystemExit, match="must be absolute and end in .zip/"):
        make_stdlib_zip.main()


def test_the_ctypes_stand_in_names_and_refuses() -> None:
    ct = _load_stand_in()
    assert not [n for n in STAND_IN_TYPES if n in vars(ct)], "built at import"
    assert f"{ct.__name__}._types" not in sys.modules, "the builder loaded at import"
    for name in STAND_IN_TYPES + STAND_IN_CONSTANTS:
        assert getattr(ct, name) is not None, name
    assert all(n in vars(ct) for n in STAND_IN_TYPES), "not stored after the first lookup"
    assert set(ct.__all__) == {*STAND_IN_TYPES, *STAND_IN_CONSTANTS}
    assert set(ct.__all__) <= set(dir(ct))
    names = STAND_IN_TYPES

    for load in (
        lambda: ct.CDLL(None),
        lambda: ct.CDLL("libc.so"),
        lambda: ct.PyDLL(None),
        lambda: ct.cdll.LoadLibrary("x"),
        lambda: ct.cdll.x,
        lambda: ct.cdll["x"],
    ):
        _refuses(load)

    class S(ct.Structure):
        _fields_ = [("name", ct.c_char * 16), ("p", ct.c_void_p)]

    class U(ct.Union):
        _fields_ = [("a", ct.c_int), ("b", ct.c_float)]

    simple = [getattr(ct, n) for n in names if n.startswith("c_")]
    func = ct.CFUNCTYPE(ct.c_int, ct.c_char_p)
    kinds = [*simple, S, U, ct.c_char * 4, func, ct.POINTER(ct.c_int)]
    # The numeric simple types and c_void_p hold values (the checks below);
    # every other kind still refuses an instance.
    holders = {getattr(ct, n) for n in VALUE_TYPES}
    for kind in kinds:
        if kind not in holders:
            _refuses(kind)
        for method in ("from_buffer", "from_buffer_copy", "from_address", "from_param", "in_dll"):
            _refuses(lambda kind=kind, method=method: getattr(kind, method)(b""))
    for name in (
        "byref",
        "pointer",
        "cast",
        "addressof",
        "memmove",
        "memset",
        "string_at",
        "wstring_at",
        "create_string_buffer",
        "create_unicode_buffer",
        "resize",
        "get_errno",
        "set_errno",
    ):
        _refuses(lambda name=name: getattr(ct, name)(None))
    _refuses(ct.WinError)
    _refuses(lambda: S.__numpy_dtype__)  # no layout: numpy must not get dtype('O')

    four, four_again = ct.c_char * 4, 4 * ct.c_char
    assert four is four_again and isinstance(four, type) and four._length_ == 4
    assert four._type_ is ct.c_char
    assert ct.POINTER(ct.c_char) is ct.POINTER(ct.c_char)
    assert isinstance(func, type) and isinstance(ct.PYFUNCTYPE(None), type)
    assert ct.sizeof(ct.c_wchar) == 4 and ct.sizeof(ct.c_longdouble) == 16
    assert ct.sizeof(ct.c_char * 16) == 16
    _refuses(lambda: ct.sizeof(S))
    with pytest.raises(TypeError):
        ct.sizeof(3)
    assert ct.c_int8 is ct.c_byte and ct.c_uint8 is ct.c_ubyte
    for kind in (ct.c_bool, ct.c_byte, ct.c_short, ct.c_long, ct.c_ulonglong, ct.c_double):
        assert kind.__ctype_le__ is kind, kind
        twin = kind.__ctype_be__
        assert twin is kind if ct.sizeof(kind) == 1 else twin.__ctype_le__ is kind, kind
    util = importlib.import_module(f"{ct.__name__}.util")
    assert util.find_library("c") is None
    # The loaded shared libraries, which threadpoolctl lists, are none
    assert util.dllist() == []


def test_the_ctypes_stand_in_documents_itself_with_numpy_loaded(monkeypatch) -> None:
    """help() and np.info read `__numpy_dtype__` on every base class: only the types without a
    layout refuse it, never the module or a simple type (review 033, finding 1). A stand-in
    `numpy` in sys.modules plays numpy's part."""
    numpy = types.ModuleType("numpy")
    numpy.dtype = lambda code: ("dtype", code)
    monkeypatch.setitem(sys.modules, "numpy", numpy)
    ct = _load_stand_in()
    assert ct.c_double.__numpy_dtype__ == ("dtype", "d")
    assert ct.c_long.__ctype_be__.__numpy_dtype__ == ("dtype", ">l")
    assert "c_long" in pydoc.render_doc(ct)
    assert "c_long" in pydoc.render_doc(ct.c_long)
    assert "__numpy_dtype__" in pydoc.allmethods(ct.c_long)

    class S(ct.Structure):
        _fields_ = [("a", ct.c_int)]

    for kind in (S, ct.Union, ct.c_int * 2, ct.POINTER(ct.c_int), ct.CFUNCTYPE(None)):
        _refuses(lambda kind=kind: kind.__numpy_dtype__)


def test_the_ctypes_stand_in_holds_numeric_values_as_wasm32_stores_them(monkeypatch) -> None:
    """A numeric simple type's instance holds a value, zero when given
    none; `.value` reads and writes it as wasm32 C stores it: an integer wraps to the type's width
    and signedness, `c_float` rounds to single precision, `c_bool` stores a bool."""
    import struct

    ct = _load_stand_in_as_wasm32(monkeypatch)
    for name in NUMERIC_TYPES:
        kind = getattr(ct, name)
        zero = kind().value
        assert zero == 0 and type(zero) is type(kind(1).value), name
        assert kind(1).value == 1, name
    assert ct.c_bool().value is False and ct.c_bool(2).value is True
    assert ct.c_bool("").value is False and ct.c_bool([0]).value is True
    assert ct.c_ulong(-1).value == 4294967295  # scipy's loadarff reads this (_arffread.py:485)
    assert ct.c_byte(200).value == -56 and ct.c_ubyte(263).value == 7
    assert ct.c_short(32768).value == -32768 and ct.c_ushort(-1).value == 65535
    assert ct.c_long(2**31).value == -(2**31) and ct.c_uint(2**32 + 3).value == 3
    assert ct.c_longlong(2**63).value == -(2**63) and ct.c_ulonglong(-1).value == 2**64 - 1
    assert ct.c_size_t(-1).value == 2**32 - 1 and ct.c_ssize_t(2**32 - 1).value == -1
    assert ct.c_int(True).value == 1 and type(ct.c_int(True).value) is int
    single = struct.unpack("f", struct.pack("f", 0.1))[0]
    assert ct.c_float(0.1).value == single != 0.1
    assert ct.c_double(0.1).value == 0.1 and ct.c_longdouble(0.1).value == 0.1
    assert ct.c_double(3).value == 3.0 and type(ct.c_double(3).value) is float
    held = ct.c_uint()
    held.value = -2
    assert held.value == 4294967294
    held.value = 5
    assert held.value == 5
    roundtrip = ct.c_float()
    roundtrip.value = 0.1
    assert roundtrip.value == single
    for kind in (ct.c_int, ct.c_ulong, ct.c_byte):
        with pytest.raises(TypeError):
            kind(1.5)  # as CPython's ctypes: an integer type takes an integer
        with pytest.raises(TypeError):
            kind("1")
        with pytest.raises(TypeError):
            kind(None)
    with pytest.raises(TypeError):
        ct.c_double("1.0")
    with pytest.raises(TypeError):
        ct.c_long(1, 2)
    assert repr(ct.c_long(-3)) == "c_long(-3)" and repr(ct.c_double(0.5)) == "c_double(0.5)"
    note = ct.c_int(4)
    note.anything = 1  # instances take attributes, as numpy's data_as needs (ptr._arr = ...)
    assert note.anything == 1
    for kind in (ct.c_long, ct.c_double):  # the byte-order twins are not among Decision 3's types
        if kind.__ctype_be__ is not kind:
            _refuses(kind.__ctype_be__)


def test_the_ctypes_stand_in_values_have_no_memory(monkeypatch) -> None:
    """A value instance has no memory to read, so its buffer refuses
    with the stand-in's OSError (PEP 688's `__buffer__`), as `bytes()`, `memoryview()` and
    `bytearray()` of it would touch memory; CPython's test_memoryview reads `bytes(c_double(0.6))`
    and must meet "ctypes is unavailable", not a TypeError."""
    ct = _load_stand_in_as_wasm32(monkeypatch)
    for make in (lambda: ct.c_double(0.6), lambda: ct.c_int(1), lambda: ct.c_void_p(8)):
        for read in (bytes, memoryview, bytearray):
            _refuses(lambda make=make, read=read: read(make()))


def test_the_ctypes_stand_in_values_are_true_and_typed_as_cpythons(monkeypatch) -> None:
    """An instance is false when its stored C bytes are
    all zero, as CPython's (so -0.0 and NaN are true, and a NULL c_void_p is false); c_void_p takes
    only an int, a floating type only what has `__float__` or `__index__` (never a str or a
    buffer), and instances are unhashable, each as CPython's ctypes."""
    from fractions import Fraction

    ct = _load_stand_in_as_wasm32(monkeypatch)
    false = (ct.c_int(0), ct.c_ulong(2**32), ct.c_bool(False), ct.c_void_p(), ct.c_void_p(0))
    false += (ct.c_double(0.0), ct.c_float(0.0), ct.c_longdouble(0.0))
    true = (ct.c_int(-1), ct.c_byte(1), ct.c_bool(True), ct.c_void_p(8), ct.c_double(-0.0))
    true += (ct.c_float(-0.0), ct.c_double(float("nan")), ct.c_float(1e-45))
    assert [bool(x) for x in false] == [False] * len(false), false
    assert [bool(x) for x in true] == [True] * len(true), true

    class Index:
        def __index__(self):
            return 16

    for bad in (Index(), 1.0, "8"):
        with pytest.raises(TypeError):
            ct.c_void_p(bad)
    assert ct.c_void_p(True).value == 1  # a bool is an int, as CPython reads it
    for bad in (memoryview(b"2.5"), bytearray(b"1"), b"1", "1.0"):
        with pytest.raises(TypeError):
            ct.c_double(bad)
    assert ct.c_double(Fraction(1, 2)).value == 0.5 and ct.c_double(Index()).value == 16.0
    with pytest.raises(TypeError):
        hash(ct.c_int(1))
    with pytest.raises(TypeError):
        hash(ct.c_void_p(8))


def test_the_ctypes_stand_in_types_import_only_what_a_start_has_loaded() -> None:
    """The first type lookup imports nothing new. `ctypes._types` imports
    only `struct` and `sys`, which every start has loaded; `operator` and `math` cost a plain
    start 5.9 M and 1.0 M fuel (measured), so the value rules do without them."""
    import ast

    tree = ast.parse((STAND_IN / "_types.py").read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            imported.add(node.module)
    assert imported == {"struct", "sys"}, sorted(imported)


def test_the_ctypes_stand_in_holds_void_pointers_and_casts_them(monkeypatch) -> None:
    """`c_void_p` holds an int wrapped to wasm32's 32 bits, or None (NULL,
    as CPython's ctypes reads a zero pointer); `cast` of an int, None or a `c_void_p` to `c_void_p`
    is a new `c_void_p` with that value. numpy's `ndarray.ctypes.data_as(c_void_p)` and scipy's
    `LowLevelCallable` user data (`_lib/_ccallback.py`) are exactly these steps."""
    ct = _load_stand_in_as_wasm32(monkeypatch)
    assert ct.c_void_p().value is None and ct.c_void_p(None).value is None
    assert ct.c_void_p(0).value is None
    assert ct.c_void_p(0x1234).value == 0x1234
    assert ct.c_void_p(2**32 + 5).value == 5  # a 64-bit host's address would not fit
    assert ct.c_void_p(-1).value == 2**32 - 1
    held = ct.c_void_p()
    held.value = 2**32 + 8
    assert held.value == 8
    held.value = None
    assert held.value is None
    for bad in (1.5, b"x", "x", ct.c_int(1)):
        with pytest.raises(TypeError):
            ct.c_void_p(bad)
    assert repr(ct.c_void_p(16)) == "c_void_p(16)" and repr(ct.c_void_p()) == "c_void_p(None)"

    assert ct.cast(5, ct.c_void_p).value == 5
    assert ct.cast(None, ct.c_void_p).value is None
    assert ct.cast(2**32 + 9, ct.c_void_p).value == 9
    data = ct.c_void_p(4096)  # numpy's _ctypes.__init__: self._data = ctypes.c_void_p(ptr)
    ptr = ct.cast(data, ct.c_void_p)  # numpy's data_as(c_void_p)
    assert type(ptr) is ct.c_void_p and ptr is not data and ptr.value == 4096
    ptr._arr = [1, 2, 3]  # numpy keeps the array alive on the pointer
    assert ct.cast(ptr, ct.c_void_p).value == 4096  # scipy's _get_ctypes_data
    assert isinstance(ptr, ct.c_void_p)

    # Nothing has an address, no pointer to typed data is made, and nothing is called.
    for refused in (
        lambda: ct.cast(data, ct.POINTER(ct.c_double)),  # numpy's data_as(POINTER(c_double))
        lambda: ct.cast(4096, ct.POINTER(ct.c_int)),
        lambda: ct.cast(4096, ct.c_long),
        lambda: ct.cast(ct.c_int(1), ct.c_void_p),
        lambda: ct.cast(1.5, ct.c_void_p),
        lambda: ct.cast(b"x", ct.c_char_p),
        lambda: ct.byref(ct.c_int(1)),
        lambda: ct.byref(data),
        lambda: ct.pointer(ct.c_int(1)),
        lambda: ct.addressof(ct.c_int(1)),
        lambda: ct.addressof(data),
        lambda: ct.c_void_p.from_param(data),
        lambda: ct.c_int.from_buffer(bytearray(4)),
        lambda: ct.c_void_p.from_address(4096),
        lambda: ct.c_char(b"a"),
        lambda: ct.c_wchar("a"),
        lambda: ct.c_char_p(b"x"),
        lambda: ct.c_wchar_p("x"),
        lambda: (ct.c_int * 2)(1, 2),  # numpy's ndarray.ctypes.shape and strides
        lambda: ct.POINTER(ct.c_int)(),
        lambda: ct.CFUNCTYPE(ct.c_int)(),
        lambda: ct.memmove(4096, 8192, 4),
        lambda: ct.string_at(4096),
    ):
        _refuses(refused)
    function = ct.cast(4096, ct.CFUNCTYPE(ct.c_int))  # scipy's cast, unchanged
    _refuses(function)


# The freezer names each module it freezes; its defaults keep _reactor's
# header as it was.

FROZEN_HEADER = """\
/* Generated by scripts/freeze_bootstrap.py from zip_directory.py: do not edit. */
#define ZIP_DIRECTORY_MAGIC 1234L
static const unsigned char ZIP_DIRECTORY[] = {
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23,
    24, 25,
};
"""


def test_freeze_names_each_module() -> None:
    data = bytes(range(26))
    assert freeze_bootstrap.render(data, 1234, "ZIP_DIRECTORY", "zip_directory.py") == FROZEN_HEADER
    default = freeze_bootstrap.render(bytes([7]), 99, source="reactor_bootstrap.py")
    assert default == (
        "/* Generated by scripts/freeze_bootstrap.py from reactor_bootstrap.py: do not edit. */\n"
        "#define REACTOR_BOOTSTRAP_MAGIC 99L\n"
        "static const unsigned char REACTOR_BOOTSTRAP[] = {\n    7,\n};\n"
    )
    code = freeze_bootstrap.compile_module("def f():\n    return 1\n", "<frozen _x>")
    import marshal

    loaded = marshal.loads(code)
    assert loaded.co_filename == "<frozen _x>"
    assert next(c for c in loaded.co_consts if hasattr(c, "co_filename")).co_filename == (
        "<frozen _x>"
    )


CONSTRUCTORS_SH = paths.REPO / "scripts" / "steps" / "constructors.sh"


@pytest.mark.parametrize("passes", [True, False])
def test_a_binary_that_fails_the_constructor_check_is_removed(tmp_path, passes) -> None:
    """Step 60's last gate: a python.wasm whose static constructors
    or features no review has read is removed before the step stops, so a later step run by name
    cannot snapshot it; one that passes stays. The check itself is a stand-in here."""
    if SH is None:
        pytest.skip("no sh")
    binary, log = tmp_path / "python.wasm", tmp_path / "constructors.log"
    binary.write_bytes(b"\0asm")
    fake = tmp_path / "python3"
    fake.write_text(f"#!/bin/sh\necho checked\nexit {0 if passes else 1}\n")
    fake.chmod(0o755)
    script = f'HERE="{paths.REPO}"; HOSTPY="{fake}"; . "{CONSTRUCTORS_SH}"; '
    script += f'check_constructors "{binary}" "{log}"; echo after'
    r = subprocess.run([SH, "-c", script], capture_output=True, text=True)
    if passes:
        assert (r.returncode, r.stdout, binary.exists()) == (0, "checked\nafter\n", True), r
    else:
        assert r.returncode == 1 and r.stdout == "checked\n" and not binary.exists(), r
        assert "it is removed" in r.stderr, r.stderr


# Every builtin's init function runs inside CPython's package context.


def test_the_inittab_registers_each_module_through_its_package_context(
    tmp_path, monkeypatch
) -> None:
    """The generated inittab registers a wrapper for every entry, each wrapper sets the package
    context to its entry's dotted name around the init function and restores it, and no entry
    registers its init function directly: what `_PyImport_RunModInitFunction` does for a module
    loaded from a shared library, which a builtin otherwise never gets."""
    import re

    import gen_inittab

    built = {
        "regexb": ["regex/_regex"],
        "npb": ["numpy/_core/_multiarray_umath", "numpy/random/_pcg64"],
    }
    for folder, modules in built.items():
        for module in modules:
            so = tmp_path / folder / (module + gen_inittab.SUFFIX)
            so.parent.mkdir(parents=True, exist_ok=True)
            so.write_bytes(b"!<arch>\n")
    out = tmp_path / "inittab.c"
    argv = ["gen_inittab.py", str(out), f"regex={tmp_path / 'regexb'}", f"numpy={tmp_path / 'npb'}"]
    monkeypatch.setattr(sys, "argv", argv)
    gen_inittab.main()
    text = out.read_text()
    want = {
        "regex._regex": "_regex",
        "numpy._core._multiarray_umath": "_multiarray_umath",
        "numpy.random._pcg64": "_pcg64",
    }
    assert "extern const char *_PyImport_SwapPackageContext(const char *);" in text
    wrappers = dict(
        re.findall(
            r"static PyObject \*(\w+)\(void\)\s*\{[^}]*?"
            r'_PyImport_SwapPackageContext\("([\w.]+)"\);[^}]*?'
            r"PyInit_\w+\(\);[^}]*?_PyImport_SwapPackageContext\(\w+\);[^}]*?\}",
            text,
        )
    )
    assert sorted(wrappers.values()) == sorted(want), text
    for wrapper, dotted in wrappers.items():
        body = text[text.index(f"*{wrapper}(void)") :].split("}", 1)[0]
        assert f"PyInit_{want[dotted]}();" in body, body
    registered = dict(re.findall(r'PyImport_AppendInittab\("([\w.]+)", (\w+)\);', text))
    assert registered == {dotted: w for w, dotted in wrappers.items()}, text
    assert not [f for f in registered.values() if f.startswith("PyInit_")], text


RECIPE_ONE = '#ifndef PREIMPORT\n#define PREIMPORT "import encodings, io, os"\n#endif\n'


def test_the_pre_import_list_is_read_from_the_recipe() -> None:
    """MANIFEST's x-preimport line is read from the recipe's one #define:
    a recipe with none, or with two, stops the build naming the file."""
    assert assemble_artifacts.preimport_list(RECIPE_ONE) == "encodings, io, os"
    for text in ("#ifndef PREIMPORT\n#endif\n", RECIPE_ONE + RECIPE_ONE.splitlines()[1] + "\n"):
        with pytest.raises(SystemExit, match="recipes/reactor_main.c"):
            assemble_artifacts.preimport_list(text)


# contourpy's _build_config.py as meson writes it: its host keys are keyword
# arguments of the dict(...) call build_config() returns, not a dict display.
CONTOURPY_CONFIG = """
def build_config() -> dict[str, str]:
    return dict(
        python_path=r"/home/me/repo/scripts/python-wasi-cross",
        build_dir=r"/home/me/repo/build/contourpy-build/lib/contourpy/util",
        host_cpu="wasm32",
        host_cpu_endian="little",
        build_cpu="aarch64",
        build_cpu_family="aarch64",
        build_cpu_endian="little",
        build_cpu_system="darwin",
    )
"""
CONTOURPY_MEMBER = "contourpy/util/_build_config.py"


def test_contourpys_build_host_keys_are_set_to_build() -> None:
    """build_cpu, build_cpu_family and build_cpu_system read back as `build`; the endian and the
    host machine's keys stay as meson wrote them."""
    text = make_stdlib_zip.host_neutral(CONTOURPY_CONFIG, CONTOURPY_MEMBER)
    namespace: dict = {}
    exec(text, namespace)
    got = namespace["build_config"]()
    assert {k: got[k] for k in ("build_cpu", "build_cpu_family", "build_cpu_system")} == {
        "build_cpu": "build",
        "build_cpu_family": "build",
        "build_cpu_system": "build",
    }
    assert (got["build_cpu_endian"], got["host_cpu"]) == ("little", "wasm32")
    assert "aarch64" not in text and "darwin" not in text


@pytest.mark.parametrize("key", ["build_cpu", "build_cpu_family", "build_cpu_system"])
def test_contourpys_config_without_a_build_key_stops(key) -> None:
    lines = [t for t in CONTOURPY_CONFIG.splitlines() if not t.strip().startswith(key + "=")]
    with pytest.raises(SystemExit, match=f"no {key} to make host-neutral"):
        make_stdlib_zip.host_neutral("\n".join(lines) + "\n", CONTOURPY_MEMBER)


def test_contourpys_config_without_its_dict_call_stops() -> None:
    with pytest.raises(SystemExit, match="no dict"):
        make_stdlib_zip.host_neutral("def build_config():\n    return {}\n", CONTOURPY_MEMBER)


def _plan(build, entries: dict) -> None:
    """A meson-info/intro-install_plan.json holding `entries` ({group: {source: (dest, tag)}})."""
    plan = {
        group: {
            str(build / src): {"destination": dest, "tag": tag}
            for src, (dest, tag) in items.items()
        }
        for group, items in entries.items()
    }
    (build / "meson-info").mkdir(parents=True)
    (build / "meson-info" / "intro-install_plan.json").write_text(json.dumps(plan))
    for items in entries.values():
        for src in items:
            (build / src).parent.mkdir(parents=True, exist_ok=True)
            (build / src).write_text(f"# {src}\n")


CONFIG_DEST = "{py_platlib}/contourpy/util/_build_config.py"


def test_untagged_files_go_where_meson_s_plan_says(tmp_path) -> None:
    """Step 55 places contourpy's _build_config.py, which meson installs with no tag, at the
    destination meson's install plan gives it, and stops unless that is exactly the expected
    path."""
    build, site = tmp_path / "build", tmp_path / "site"
    _plan(
        build,
        {
            "configure": {"lib/contourpy/util/_build_config.py": (CONFIG_DEST, None)},
            "targets": {"src/_contourpy.so": ("{py_platlib}/contourpy/_contourpy.so", "runtime")},
            "python": {
                "lib/contourpy/__init__.py": (
                    "{py_purelib}/contourpy/__init__.py",
                    "python-runtime",
                )
            },
        },
    )
    meson_plan.place_untagged(build, site, ["contourpy/util/_build_config.py"])
    assert sorted(p.relative_to(site).as_posix() for p in site.rglob("*") if p.is_file()) == [
        "contourpy/util/_build_config.py"
    ]
    with pytest.raises(SystemExit, match="with no tag, not"):
        meson_plan.place_untagged(build, site, ["contourpy/_build_config.py"])


def test_a_moved_or_stray_untagged_file_stops(tmp_path) -> None:
    moved = tmp_path / "moved"
    _plan(moved, {"configure": {"lib/c.py": ("{py_platlib}/contourpy/_build_config.py", None)}})
    with pytest.raises(SystemExit, match="with no tag, not"):
        meson_plan.place_untagged(moved, tmp_path / "s1", ["contourpy/util/_build_config.py"])
    outside = tmp_path / "outside"
    _plan(outside, {"configure": {"lib/c.py": ("{prefix}/share/c.py", None)}})
    with pytest.raises(SystemExit, match="outside site-packages"):
        meson_plan.place_untagged(outside, tmp_path / "s2", ["contourpy/util/_build_config.py"])


def test_a_wheels_licences_are_read_through_its_pin(tmp_path) -> None:
    """Step 90 reads a wheel's licence files only after the wheel's bytes match its pin, so a
    step run on its own never ships a licence from a download that changed; the failure names
    the file."""
    import hashlib

    d = tmp_path / "downloads"
    d.mkdir()
    wheel = d / "x-1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as z:
        z.writestr("x-1.0.dist-info/licenses/LICENSE", "the licence\n")
        z.writestr("x/__init__.py", "")
    good = hashlib.sha256(wheel.read_bytes()).hexdigest()
    (d / "SHA256SUMS").write_text(f"{good}  {wheel.name}\n")
    assert assemble_artifacts.wheel_licences(wheel) == [
        (f"{wheel.name}: x-1.0.dist-info/licenses/LICENSE", b"the licence\n")
    ]
    (d / "SHA256SUMS").write_text(f"{'0' * 64}  {wheel.name}\n")
    with pytest.raises(SystemExit, match=f"downloads/{wheel.name} does not match its pin"):
        assemble_artifacts.wheel_licences(wheel)


# The download step's choice of URL: a pin's line may name a mirror, a copy of the same bytes the
# project keeps, which is asked first; its origin is asked only when the mirror fails, and a file
# is kept only when its SHA-256 is the pin's. The shell's `get()` runs alone, taken from the
# script's text (the script finds the repository from $0 and runs every pin at load), with a fake
# curl that serves each URL the case's bytes and logs the URL it was asked for.

DOWNLOAD = paths.REPO / "scripts" / "00_download.sh"
DOWNLOAD_FUNCTIONS = ("pin_sum", "fetch_checked", "get")
SHELLS = sorted({s for s in (shutil.which("dash") or SH, shutil.which("bash")) if s})
MIRROR = "https://github.com/o/r/releases/download/test-sources-2026-01-01/x-tag.tar.gz"
ORIGIN = "https://foss.heptapod.net/o/x/-/archive/1/x-1.tar.gz"
PINNED = b"the pinned archive"
CHALLENGE = b"<!doctype html><title>Making sure you&#39;re not a bot!</title>"
FAKE_CURL = """#!/bin/sh
url= out=
while [ "$#" -gt 0 ]; do
  case "$1" in -o) out=$2; shift;; https://*) url=$1;; esac
  shift
done
printf '%s\\n' "$url" >> "$CURL_LOG"
key=$(printf '%s' "$url" | tr -c 'A-Za-z0-9' _)
[ -f "$SERVED/$key" ] || exit 22
cat "$SERVED/$key" > "$out"
"""
# case -> the bytes each URL serves (absent: the fake curl fails as on an HTTP error)
MIRROR_CASES = {
    "the mirror serves": {MIRROR: PINNED, ORIGIN: PINNED},
    "the mirror serves a page": {MIRROR: CHALLENGE, ORIGIN: PINNED},
    "the mirror fails": {ORIGIN: PINNED},
    "neither serves": {MIRROR: CHALLENGE, ORIGIN: b"other bytes"},
}


def _functions(text: str, names: tuple[str, ...]) -> str:
    """The named shell functions as written, each from `name() {` to its closing `}` line."""
    out = []
    for name in names:
        m = re.search(rf"^{name}\(\) \{{[^\n]*\n.*?^\}}\n", text, re.M | re.S)
        assert m, f"00_download.sh defines no {name}()"
        out.append(m[0])
    return "".join(out)


def _shell_get(tmp_path: Path, shell: str, served: dict[str, bytes]) -> tuple[list[str], str, int]:
    """`get ORIGIN x-tag.tar.gz MIRROR` under `set -eu` in `shell`: the URLs asked, in order, the
    output, and the exit status; the file, when kept, is tmp_path/downloads/x-tag.tar.gz."""
    d, bin_, serve = tmp_path / "downloads", tmp_path / "bin", tmp_path / "served"
    for folder in (d, bin_, serve):
        folder.mkdir(parents=True)
    (d / "SHA256SUMS").write_text(f"{hashlib.sha256(PINNED).hexdigest()}  x-tag.tar.gz\n")
    for url, data in served.items():
        (serve / re.sub(r"[^A-Za-z0-9]", "_", url)).write_bytes(data)
    (bin_ / "curl").write_text(FAKE_CURL)
    (bin_ / "curl").chmod(0o755)
    log = tmp_path / "asked.log"
    log.touch()
    body = _functions(DOWNLOAD.read_text(), DOWNLOAD_FUNCTIONS)
    script = (
        f'set -eu\nD="{d}"\nPINS=0 FETCHED=0 NAMES=" "\n{body}get {ORIGIN} x-tag.tar.gz {MIRROR}\n'
    )
    (tmp_path / "get.sh").write_text(script)
    env = {
        "PATH": f"{bin_}{os.pathsep}{os.environ.get('PATH', os.defpath)}",
        "CURL_LOG": str(log),
        "SERVED": str(serve),
    }
    r = subprocess.run([shell, str(tmp_path / "get.sh")], capture_output=True, text=True, env=env)
    return log.read_text().split(), r.stdout + r.stderr, r.returncode


def _python_get(tmp_path: Path, monkeypatch, served: dict[str, bytes]) -> tuple[list[str], str]:
    """The judge's `fetch_first` on the same case: the URLs asked, in order, and its message."""
    spec = importlib.util.spec_from_file_location(
        "upstream_fetch_mirror", paths.REPO / "tests" / "upstream" / "fetch.py"
    )
    fetch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fetch)
    asked: list[str] = []

    def urlopen(url, timeout=0):
        asked.append(url)
        if url not in served:
            raise OSError("HTTP Error 404")
        return io.BytesIO(served[url])

    monkeypatch.setattr(fetch.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(fetch, "PAUSE", 0)
    monkeypatch.setattr(fetch, "ATTEMPTS", 1)
    d = tmp_path / "downloads"
    d.mkdir(parents=True)
    sha = hashlib.sha256(PINNED).hexdigest()
    return asked, fetch.fetch_first(sha, (MIRROR, ORIGIN), d, "x-tag.tar.gz") or ""


def _served_by(served: dict[str, bytes]) -> str | None:
    """The URL whose bytes are kept: the mirror when it serves the pinned bytes, else the origin
    when it does, else none."""
    return next((u for u in (MIRROR, ORIGIN) if served.get(u) == PINNED), None)


@pytest.mark.skipif(not SHELLS, reason="needs a POSIX sh")
@pytest.mark.parametrize("shell", SHELLS, ids=lambda s: Path(s).name)
@pytest.mark.parametrize("case", MIRROR_CASES)
def test_the_download_step_tries_the_mirror_first(tmp_path, shell, case) -> None:
    served = MIRROR_CASES[case]
    asked, out, code = _shell_get(tmp_path, shell, served)
    kept = tmp_path / "downloads" / "x-tag.tar.gz"
    by = _served_by(served)
    assert asked == ([MIRROR] if by == MIRROR else [MIRROR, ORIGIN]), (asked, out)
    assert not list((tmp_path / "downloads").glob("*.part")), out
    if by is None:
        assert code == 1 and not kept.exists(), out
        assert f"ERROR: x-tag.tar.gz: {MIRROR}: " in out and f"; {ORIGIN}: " in out, out
        for body in (CHALLENGE, b"other bytes"):
            assert hashlib.sha256(body).hexdigest() in out, out
        return
    assert code == 0 and kept.read_bytes() == PINNED, out
    assert f"fetched x-tag.tar.gz from {by}" in out, out
    if by == ORIGIN:
        assert "x-tag.tar.gz: the mirror did not serve the pinned bytes" in out, out


@pytest.mark.skipif(not SHELLS, reason="needs a POSIX sh")
@pytest.mark.parametrize("case", MIRROR_CASES)
def test_the_two_fetchers_choose_the_same_url(tmp_path, monkeypatch, case) -> None:
    """The build's shell fetcher and the judge's Python fetcher, on one case each: the same URLs
    asked in the same order, the same file kept or none, and on a failure both URLs named."""
    served = MIRROR_CASES[case]
    sh_asked, sh_out, sh_code = _shell_get(tmp_path / "sh", SHELLS[0], served)
    py_asked, py_error = _python_get(tmp_path / "py", monkeypatch, served)
    assert sh_asked == py_asked, (sh_asked, py_asked)
    sh_kept = (tmp_path / "sh" / "downloads" / "x-tag.tar.gz").exists()
    py_kept = (tmp_path / "py" / "downloads" / "x-tag.tar.gz").exists()
    assert sh_kept == py_kept == (sh_code == 0) == (py_error == ""), (sh_out, py_error)
    if not py_kept:
        for text in (sh_out, py_error):
            assert MIRROR in text and ORIGIN in text, text


def test_the_wasmtime_cli_is_the_lines_by_its_exact_name(tmp_path) -> None:
    """A build tree may still hold an older wasmtime beside the line's own (a step 10 that ran on
    the older pin left it there): the judge's CLI is the folder the line names, never the first
    one sorted, which would be the older."""
    for folder in ("wasmtime-v49.0.3-aarch64-macos", "wasmtime-v50.0.1-aarch64-macos"):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "wasmtime").write_bytes(b"")
    found = paths.wasmtime_cli("wasmtime-v50.0.1-aarch64-macos", tools=tmp_path)
    assert found == tmp_path / "wasmtime-v50.0.1-aarch64-macos" / "wasmtime"
    assert paths.wasmtime_cli("wasmtime-v51.0.0-aarch64-macos", tools=tmp_path) is None
