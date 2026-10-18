"""Finder litter never breaks a build (spec 018): `remove` retries, and the zip, the licences and
the artifact set never carry litter. Each case works on a temporary folder; `remove` runs under a
POSIX `sh` with `rm` replaced by a shell function that counts its calls. Nothing measures time.
The zip's package metadata and the `ctypes` stand-in (spec 033) are checked here on the host too."""

from __future__ import annotations

import importlib.util
import os
import pydoc
import shutil
import subprocess
import sys
import types
import zipfile

import pytest

from harness import paths

sys.path.insert(0, str(paths.REPO / "scripts"))

import assemble_artifacts  # noqa: E402
import litter  # noqa: E402
import make_stdlib_zip  # noqa: E402

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


def test_the_zip_walk_skips_litter(tmp_path) -> None:
    for tree in ("a", "b"):
        (tmp_path / tree / "pkg").mkdir(parents=True)
        (tmp_path / tree / "pkg" / f"mod_{tree}.py").write_text("x = 1\n")
        for name in litter.OS_LITTER:
            (tmp_path / tree / name).write_bytes(b"litter")
            (tmp_path / tree / "pkg" / name).write_bytes(b"litter")
    names = [n for tree in ("a", "b") for _, n in make_stdlib_zip.walk(tmp_path / tree)]
    assert sorted(names) == ["pkg/mod_a.py", "pkg/mod_b.py"]


def test_step_90_drops_litter_and_skips_it_in_licences(tmp_path) -> None:
    (tmp_path / "LICENSES").mkdir(parents=True)
    (tmp_path / "LICENSES" / "A_LICENSE").write_text("a")
    (tmp_path / "LICENSES" / ".DS_Store").write_bytes(b"x")
    (tmp_path / "Thumbs.db").write_bytes(b"x")
    (tmp_path / "python.wasm").write_bytes(b"\0asm")
    assert [p.name for p in assemble_artifacts.licence_files(tmp_path / "LICENSES")] == [
        "A_LICENSE"
    ]
    assemble_artifacts.drop_litter(tmp_path)
    assert sorted(p.name for p in tmp_path.rglob("*")) == ["A_LICENSE", "LICENSES", "python.wasm"]


def test_step_90_never_lists_litter(tmp_path) -> None:
    (tmp_path / "LICENSES").mkdir()
    for name in ("python.wasm", "LICENSES/zlib.txt", ".DS_Store", "LICENSES/Thumbs.db"):
        (tmp_path / name).write_bytes(b"x")
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
    assert set(litter.OS_LITTER) == set(paths.OS_LITTER)


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
    assert importlib.import_module(f"{ct.__name__}.util").find_library("c") is None


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
