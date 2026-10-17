"""The wasm reader and the wall rule, on small modules with known shapes."""

from __future__ import annotations

import pytest

from harness import wasm, wat


def test_reads_imports_types_and_exports(work) -> None:
    mod = wasm.parse_file(wat.build(work, "plain.wasm", wat.PLAIN_REACTOR))
    door = [i for i in mod.imports if i.module == "host"]
    assert [(i.name, i.kind, i.type) for i in door] == [("call", "func", wasm.DOOR_TYPE)]
    assert {"memory", "_initialize", "wizer.initialize", "run", "host_alloc"} <= set(mod.exports)
    assert mod.exports["memory"] == "memory"


def test_wall_holds_for_wasi_and_the_door(work) -> None:
    mod = wasm.parse_file(wat.build(work, "plain.wasm", wat.PLAIN_REACTOR))
    assert wasm.wall_errors(mod) == []


def test_wall_names_a_third_import(work) -> None:
    mod = wasm.parse_file(wat.build(work, "third.wasm", wat.THIRD_IMPORT))
    assert wasm.wall_errors(mod) == ["third import env::sneak (func)"]


def test_wall_names_a_door_of_the_wrong_type(work) -> None:
    mod = wasm.parse_file(wat.build(work, "bad.wasm", wat.WRONG_DOOR_TYPE))
    assert wasm.wall_errors(mod) == [
        "host::call has type (i32) -> (i32), not " + str(wasm.DOOR_TYPE)
    ]


def test_wall_requires_the_door(work) -> None:
    mod = wasm.parse_file(wat.build(work, "cmd.wasm", wat.COMMAND_EXIT_7))
    assert wasm.wall_errors(mod) == ["no host::call import (the door)"]


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"\x7fELF\x02\x01\x01\x00", "bad magic"),
        (b"\0asm\x0d\x00\x01\x00", "not a core module"),
        (b"\0asm\x01\0\0\0\x02\x05\x01", "runs past the end"),
    ],
)
def test_rejects_what_is_not_a_core_module(data, message) -> None:
    with pytest.raises(wasm.WasmError, match=message):
        wasm.parse(data)


def test_reads_a_real_cpython_build_when_present() -> None:
    from harness import paths

    binary = paths.REFERENCE_BUILD / "python.wasm"
    if not binary.is_file():
        pytest.skip("Brett's reference build is not unpacked under build/")
    mod = wasm.parse_file(binary)
    assert {i.module for i in mod.imports} == {"wasi_snapshot_preview1"}
    assert set(mod.exports) == {"memory", "_start"}
    assert wasm.wall_errors(mod) == ["no host::call import (the door)"]


def test_reads_exnref_and_the_tag_section(work) -> None:
    mod = wasm.parse_file(wat.build(work, "eh.wasm", wat.EXCEPTIONS))
    assert mod.types[0].params == ("exnref",)
    assert wasm.TAG_SECTION in mod.sections


def test_a_module_without_exceptions_has_no_tag_section(work) -> None:
    mod = wasm.parse_file(wat.build(work, "plain.wasm", wat.PLAIN_REACTOR))
    assert wasm.TAG_SECTION not in mod.sections
