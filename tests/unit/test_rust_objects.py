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
