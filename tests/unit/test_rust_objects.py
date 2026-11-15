"""The gates on the Rust static library, on the host: which archive members are kept, which direct
imports the entropy shim routes, the shim's C, and where the link map says the runtime names came
from. No artifact: the archives and objects are made here, the map lines are wasm-ld's own form."""

from __future__ import annotations

import hashlib
import sys

import pytest

from harness import paths

sys.path.insert(0, str(paths.REPO / "scripts"))

import rust_objects  # noqa: E402


def _ar(members: list[tuple[str, bytes]]) -> bytes:
    """A GNU `ar` archive, with a `//` table for names over 15 characters, as llvm-ar writes."""
    longnames = b""
    offsets = {}
    for name, _ in members:
        if len(name) > 15:
            offsets[name] = len(longnames)
            longnames += name.encode() + b"/\n"
    out = b"!<arch>\n"

    def member(field: str, body: bytes) -> bytes:
        head = f"{field:<16}{0:<12}{0:<6}{0:<6}{644:<8}{len(body):<10}`\n".encode()
        return head + body + (b"\n" if len(body) & 1 else b"")

    out += member("/", b"\0\0\0\0")
    if longnames:
        out += member("//", longnames)
    for name, body in members:
        out += member(f"/{offsets[name]}" if name in offsets else f"{name}/", body)
    return out


def test_an_archive_is_read_with_its_long_names() -> None:
    members = [("wasi_python_rust-0123.rcgu.o", b"abc"), ("x.o", b"de")]
    assert rust_objects.ar_members(_ar(members)) == members


UMBRELLA = "wasi_python_rust"
YYJSON = b"yyjson's object"


def _keep(members):
    ours = {hashlib.sha256(YYJSON).hexdigest(): "orjson"}
    return rust_objects.keep(members, UMBRELLA, ours, set())


def test_the_umbrella_and_a_module_crates_c_are_kept_and_compiler_builtins_dropped() -> None:
    kept, dropped, errors = _keep(
        [
            ("wasi_python_rust-a1.wasi_python_rust.b2-cgu.0.rcgu.o", b"rust"),
            ("c8ee16200fd4ed00-yyjson.o", YYJSON),
            ("compiler_builtins-c3.compiler_builtins.d4-cgu.0.rcgu.o", b"builtins"),
        ]
    )
    assert [n for n, _ in kept] == [
        "wasi_python_rust-a1.wasi_python_rust.b2-cgu.0.rcgu.o",
        "c8ee16200fd4ed00-yyjson.o",
    ]
    assert dropped == ["compiler_builtins-c3.compiler_builtins.d4-cgu.0.rcgu.o"]
    assert errors == []


def test_a_member_that_is_neither_a_modules_nor_compiler_builtins_stops_the_step() -> None:
    _, _, errors = _keep([("wasi_python_rust-a1.rcgu.o", b"rust"), ("round.o", b"a planted round")])
    assert errors == ["a member that is neither a module's nor compiler_builtins': round.o"]


def test_an_archive_without_the_umbrellas_object_stops_the_step() -> None:
    _, _, errors = _keep([("c8ee16200fd4ed00-yyjson.o", YYJSON)])
    assert errors == [f"no object of the umbrella crate {UMBRELLA}"]


@pytest.mark.parametrize(
    ("path", "crate"),
    [
        ("orjson/0123456789abcdef/out/yyjson.o", "orjson"),
        ("orjson-0123456789abcdef/out/yyjson.o", "orjson"),
        ("compiler_builtins-0123456789abcdef/out/x.o", "compiler_builtins"),
        ("pyo3-ffi-0123456789abcdef/out/x.o", "pyo3-ffi"),
    ],
)
def test_a_build_script_folder_names_its_crate(tmp_path, path, crate) -> None:
    assert rust_objects._crate_of(tmp_path, tmp_path / path) == crate


def _leb(n: int) -> bytes:
    out = b""
    while True:
        byte, n = n & 0x7F, n >> 7
        out += bytes([byte | (0x80 if n else 0)])
        if not n:
            return out


def _section(sid: int, body: bytes) -> bytes:
    return bytes([sid]) + _leb(len(body)) + body


def _name(s: str) -> bytes:
    return _leb(len(s)) + s.encode()


def _object(*imports: tuple[str, str, tuple[int, ...], tuple[int, ...]]) -> bytes:
    """A wasm object whose only content is the function imports given, each (module, field,
    params, results) in value-type bytes."""
    types = b"".join(
        b"\x60" + _leb(len(p)) + bytes(p) + _leb(len(r)) + bytes(r) for _, _, p, r in imports
    )
    entries = b"".join(
        _name(m) + _name(f) + b"\x00" + _leb(i) for i, (m, f, _, _) in enumerate(imports)
    )
    return (
        b"\0asm\x01\0\0\0"
        + _section(1, _leb(len(imports)) + types)
        + _section(2, _leb(len(imports)) + entries)
    )


I32 = 0x7F
I64 = 0x7E
RANDOM_GET = ("wasi_snapshot_preview1", "random_get", (I32, I32), (I32,))


def test_random_get_and_env_imports_pass_and_are_counted() -> None:
    obj = _object(RANDOM_GET, ("env", "PyLong_FromLong", (I32,), (I32,)))
    assert rust_objects.entropy_imports([("a.o", obj), ("b.o", _object(RANDOM_GET))]) == (2, [])


def test_a_direct_clock_import_stops_the_step() -> None:
    clock = ("wasi_snapshot_preview1", "clock_time_get", (I32, I64, I32), (I32,))
    count, errors = rust_objects.entropy_imports([("a.o", _object(clock))])
    assert (count, errors) == (
        0,
        ["a.o: a direct import the shim does not route: wasi_snapshot_preview1.clock_time_get"],
    )


def test_a_random_get_of_another_type_stops_the_step() -> None:
    odd = ("wasi_snapshot_preview1", "random_get", (I32,), (I32,))
    count, errors = rust_objects.entropy_imports([("a.o", _object(odd))])
    assert count == 0 and len(errors) == 1 and "not (i32, i32) -> (i32)" in errors[0]


def test_the_shim_defines_each_mangled_name_to_call_the_wrapped_call() -> None:
    mangled = "_RNvNtNtCs0_6wasip113lib_generated22wasi_snapshot_preview110random_get"
    text = rust_objects.shim_source(
        [(mangled, "wasip1::lib_generated::wasi_snapshot_preview1::random_get")]
    )
    assert f'__asm__("{mangled}");' in text
    assert "return __wasi_random_get(buf, len);" in text
    assert text.count("__asm__") == 1


LIBC = "/sdk/share/wasi-sysroot/lib/wasm32-wasip1/libc.a"
BUILTINS = "/sdk/lib/clang/23/lib/wasm32-unknown-wasip1/libclang_rt.builtins.a"
RUST = "/b/rust/lib/librust_modules.a"


def _map(*chunks: tuple[str, str]) -> str:
    """wasm-ld's map: its header, the CODE section, and a chunk with its symbol per (file, name)."""
    lines = ["    Addr      Off     Size Out     In      Symbol", "       -       fc     284a CODE"]
    for file, name in chunks:
        lines.append(f"       -      2c0        6         {file}:({name})")
        lines.append(f"       -      2c0        6                 {name}")
    return "\n".join(lines) + "\n"


GOOD = (
    (f"{LIBC}(round.c.obj)", "round"),
    (f"{LIBC}(math-builtins.c.obj)", "sqrt"),
    (f"{LIBC}(fma.c.obj)", "fma"),
    (f"{BUILTINS}(multf3.c.o)", "__multf3"),
    (f"{BUILTINS}(multi3.c.o)", "__multi3"),
    ("/tmp/reactor_main.o", "main"),
)


def test_the_runtime_names_from_libc_and_compiler_rt_pass() -> None:
    assert rust_objects.map_findings(_map(*GOOD)) == []


def test_a_round_from_the_rust_archive_is_named() -> None:
    planted = (f"{RUST}(compiler_builtins-c3.o)", "round")
    found = rust_objects.map_findings(_map(*GOOD[1:], planted))
    assert found == ["round comes from librust_modules.a, not libc.a"]


def test_an_empty_map_does_not_pass() -> None:
    found = rust_objects.map_findings(_map())
    assert found == [f"the link map does not name {n}" for n in rust_objects.MUST_BE_NAMED]


def test_a_modules_list_line_must_name_an_init_function(tmp_path) -> None:
    good = tmp_path / "modules.txt"
    good.write_text("# comment\norjson.orjson PyInit_orjson\n", encoding="utf-8")
    assert rust_objects.read_modules(good) == [("orjson.orjson", "PyInit_orjson")]
    bad = tmp_path / "bad.txt"
    bad.write_text("orjson.orjson init_orjson\n", encoding="utf-8")
    with pytest.raises(ValueError, match="bad.txt:1"):
        rust_objects.read_modules(bad)


NM, CXXFILT = "/sdk/bin/llvm-nm", "/sdk/bin/llvm-cxxfilt"


def _tools(monkeypatch, names: dict[tuple[str, str], list[str]], demangled=None) -> None:
    """llvm-nm and llvm-cxxfilt stood in: `names` maps (path, flags) to the names llvm-nm would
    print for that path, and `demangled` maps a mangled name to its demangled form."""
    demangled = demangled or {}

    def run(cmd, input=None, **_):
        if cmd[0] == CXXFILT:
            out = "\n".join(demangled.get(n, n) for n in input.splitlines())
        else:
            assert cmd[:2] == [NM, "-j"], cmd
            out = "\n".join(names.get((cmd[-1], " ".join(cmd[2:-1])), []))
        return rust_objects.subprocess.CompletedProcess(cmd, 0, out + "\n", "")

    monkeypatch.setattr(rust_objects.subprocess, "run", run)


def _modules(tmp_path):
    path = tmp_path / "modules.txt"
    path.write_text("orjson PyInit_orjson\n_rust_probe PyInit__rust_probe\n", encoding="utf-8")
    return str(path)


def test_inits_pass_when_the_archive_defines_exactly_the_listed_ones(
    monkeypatch, tmp_path, capsys
) -> None:
    defined = ["PyInit_orjson", "PyInit__rust_probe", "orjson_dumps"]
    _tools(monkeypatch, {(RUST, "-g --defined-only"): defined})
    assert rust_objects.inits_main([NM, RUST, _modules(tmp_path)]) == 0
    assert "defines exactly PyInit__rust_probe, PyInit_orjson" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("defined", "error"),
    [
        (
            ["PyInit_orjson", "PyInit__rust_probe", "PyInit_stray"],
            "defines PyInit_stray, which modules.txt does not list",
        ),
        (["PyInit_orjson"], "does not define PyInit__rust_probe, which modules.txt lists"),
    ],
    ids=["an init not listed", "a listed init missing"],
)
def test_inits_stop_the_step_on_an_init_the_list_does_not_match(
    monkeypatch, tmp_path, capsys, defined, error
) -> None:
    _tools(monkeypatch, {(RUST, "-g --defined-only"): defined})
    assert rust_objects.inits_main([NM, RUST, _modules(tmp_path)]) == 1
    assert capsys.readouterr().out == f"ERROR: the Rust archive {error}\n"


def test_foreign_passes_when_no_runtime_library_defines_a_rust_name(monkeypatch, capsys) -> None:
    _tools(
        monkeypatch,
        {(RUST, "-g --defined-only"): ["PyInit_orjson"], (LIBC, "-g --defined-only"): ["round"]},
    )
    assert rust_objects.foreign_main([NM, RUST, LIBC, BUILTINS]) == 0
    assert "none of the 2 runtime libraries' names" in capsys.readouterr().out


def test_foreign_names_a_rust_definition_a_runtime_library_also_makes(monkeypatch, capsys) -> None:
    _tools(
        monkeypatch,
        {
            (RUST, "-g --defined-only"): ["PyInit_orjson", "round", "__multi3"],
            (LIBC, "-g --defined-only"): ["round", "sqrt"],
            (BUILTINS, "-g --defined-only"): ["__multi3"],
        },
    )
    assert rust_objects.foreign_main([NM, RUST, LIBC, BUILTINS]) == 1
    assert capsys.readouterr().out.splitlines() == [
        "ERROR: the Rust archive defines round, which libc.a defines too",
        "ERROR: the Rust archive defines __multi3, which libclang_rt.builtins.a defines too",
    ]


MANGLED = "_RNvNtNtCs0_6wasip113lib_generated22wasi_snapshot_preview110random_get"
DEMANGLED = "wasip1::lib_generated::wasi_snapshot_preview1::random_get"


def _imports(monkeypatch, tmp_path, undefined: list[str]) -> tuple[int, str]:
    """imports_main over an archive whose one object imports random_get, with llvm-nm naming
    `undefined` as the archive's undefined names; (its exit, the shim written or "")."""
    archive = tmp_path / "librust_modules.a"
    archive.write_bytes(_ar([("rust_modules-1.o", _object(RANDOM_GET))]))
    shim = tmp_path / "shim.c"
    _tools(monkeypatch, {(str(archive), "-u"): undefined}, {MANGLED: DEMANGLED})
    code = rust_objects.imports_main([NM, CXXFILT, str(archive), str(shim), LIBC])
    return code, shim.read_text(encoding="utf-8") if shim.exists() else ""


def test_each_random_get_import_is_shimmed(monkeypatch, tmp_path, capsys) -> None:
    code, shim = _imports(monkeypatch, tmp_path, [MANGLED])
    assert code == 0 and f'__asm__("{MANGLED}");' in shim
    assert capsys.readouterr().out.endswith(
        "imports: 1 entropy imports shimmed, nothing else imported\n"
    )


def test_a_random_get_import_the_shim_would_miss_stops_the_step(
    monkeypatch, tmp_path, capsys
) -> None:
    """An import entry with no undefined name to define: the shim would leave that draw reading the
    host's entropy directly, so the step stops and writes no shim."""
    assert _imports(monkeypatch, tmp_path, []) == (1, "")
    assert capsys.readouterr().out == (
        "ERROR: 0 random_get names to shim, but 1 random_get import entries\n"
    )


def test_an_undefined_name_that_is_not_random_get_stops_the_step(
    monkeypatch, tmp_path, capsys
) -> None:
    assert _imports(monkeypatch, tmp_path, [MANGLED, "clock_time_get"]) == (1, "")
    assert capsys.readouterr().out == (
        "ERROR: a direct WASI import the shim does not route: clock_time_get (clock_time_get)\n"
    )
