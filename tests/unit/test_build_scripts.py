"""Finder litter never breaks a build (spec 018): `remove` retries, and the zip, the licences and
the artifact set never carry litter. Each case works on a temporary folder; `remove` runs under a
POSIX `sh` with `rm` replaced by a shell function that counts its calls. Nothing measures time.
The zip's package metadata and the `ctypes` stand-in (spec 033) are checked here on the host too."""

from __future__ import annotations

import importlib.util
import json
import os
import pydoc
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
        pytest.skip("needs: a POSIX sh")  # blocked, never passed or failed (spec 018, B)
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
# AppleDouble file, and a file inside a volume's litter folder (spec 090, Decisions 1 and 2).
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
    """Spec 090, Decision 1: one definition in two copies, the names and both rules."""
    assert set(litter.OS_LITTER) == set(paths.OS_LITTER)
    assert all(litter.is_litter(n) for n in ("._x.py", "Icon\r", ".TemporaryItems", "ehthumbs.db"))
    names = [*paths.OS_LITTER, "._x", "a.py", "Icon", "DS_Store", ".gitignore", "_x"]
    assert [litter.is_litter(n) for n in names] == [paths.is_litter(n) for n in names]
    rels = ["a/b.py", "a/.DS_Store", ".TemporaryItems/x.py", "a/._b.py", "LICENSES/x.txt"]
    assert [litter.has_litter(r) for r in rels] == [False, True, True, True, False]
    assert [paths.has_litter(r) for r in rels] == [False, True, True, True, False]


@pytest.mark.skipif(sys.platform == "win32", reason="a Windows file name cannot hold Icon\\r's CR")
def test_the_repository_ignores_litter_itself() -> None:
    """Spec 090, Decision 7: step 90's untracked check and `paths.dirty_path` must not stop on a
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


# Spec 033: the zip carries package metadata, and the ctypes stand-in names and refuses.

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
    matched by the computed folder, however the PKG-INFO path is spelled (spec 041, Decision 5).
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
    `--metadata`, the zip holds both members, the entry points' bytes unchanged (spec 041,
    Decision 5; the build review's F2). The line's version check and the host-neutral rewrite are
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
    """Spec 039, Decision 12: a tree staged as step 70 stages pyyaml's and markupsafe's pure
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


def test_the_zips_code_carries_the_name_it_is_given() -> None:
    """Spec 051, Decision 7: `pyc` compiles under the name it is given, and every nested code
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
    for kind in kinds:
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
    # Spec 039, Decision 5: the loaded shared libraries, which threadpoolctl lists, are none
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


# Spec 035, Decision 5: the freezer names each module it freezes; its defaults keep _reactor's
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
    """Step 60's last gate (spec 023's build review, F6): a python.wasm whose static constructors
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


# Spec 047, Decision 4: every builtin's init function runs inside CPython's package context.


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
    """MANIFEST's x-preimport line is read from the recipe's one #define (spec 069, Decision 3):
    a recipe with none, or with two, stops the build naming the file."""
    assert assemble_artifacts.preimport_list(RECIPE_ONE) == "encodings, io, os"
    for text in ("#ifndef PREIMPORT\n#endif\n", RECIPE_ONE + RECIPE_ONE.splitlines()[1] + "\n"):
        with pytest.raises(SystemExit, match="recipes/reactor_main.c"):
            assemble_artifacts.preimport_list(text)


# contourpy's _build_config.py as meson writes it (spec 043, Decision 4): its host keys are keyword
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
    path (spec 043's build review, F5)."""
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
