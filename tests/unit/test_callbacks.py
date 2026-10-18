"""The callback scan (spec 051, Decision 4) on small modules built with wat2wasm: a referenced
mismatch is found, an unreferenced look-alike is not, a code-referenced single definition is
checked, an exclusion that stops matching is a finding, and a passive segment is a finding. Three
rules each have a case that fails without them (the build review, finding 2): setters are
checked, a table referenced only from code is found, and return types are compared."""

from __future__ import annotations

import struct

from harness import callbacks, wasm, wat

NOARGS, VARARGS, KEYWORDS = 0x4, 0x1, 0x3
STRINGS = 1024
NAMES = ("good", "bad", "look", "single", "gs", "coded", "st", "void")


def _strings() -> tuple[bytes, dict[str, int]]:
    blob, at = b"", {}
    for name in NAMES:
        at[name] = STRINGS + len(blob)
        blob += name.encode() + b"\0"
    return blob, at


def _escape(data: bytes) -> str:
    return "".join(f"\\{b:02x}" for b in data)


def _module(*, passive: bool = False) -> str:
    """Functions $one (1 parameter), $two (2), $three (3) and $void (2, no result) at table
    indices 21 to 24 (past the member type codes, 0 to 20, as in a real link, whose first 20 are
    the parser's); then:
    - at 1100, a method array {good: $two NOARGS, bad: $one NOARGS, void: $void NOARGS}, pointed
      at by a data word;
    - at 1200, a look-alike {look: $one NOARGS} that nothing points at;
    - at 1300, a single {single: $two VARARGS|KEYWORDS} that code points at (`i32.const 1300`);
    - at 1400, a getset array {gs: get $one, set $three; st: set $two}, pointed at by a data word;
    - at 1700, a method array {coded: $one NOARGS} that only code points at (`i32.const 1700`),
      as numpy's scalar methods, which C code sets at run time."""
    blob, at = _strings()
    zero16, zero20 = bytes(16), bytes(20)
    methods = struct.pack("<4I", at["good"], 22, NOARGS, 0)
    methods += struct.pack("<4I", at["bad"], 21, NOARGS, 0)
    methods += struct.pack("<4I", at["void"], 24, NOARGS, 0) + zero16
    look = struct.pack("<4I", at["look"], 21, NOARGS, 0) + zero16
    single = struct.pack("<4I", at["single"], 22, KEYWORDS, 0) + b"\xff" * 16
    getsets = struct.pack("<5I", at["gs"], 21, 23, 0, 0)
    getsets += struct.pack("<5I", at["st"], 0, 22, 0, 0) + zero20
    coded = struct.pack("<4I", at["coded"], 21, NOARGS, 0) + zero16
    pointers = struct.pack("<2I", 1100, 1400)  # a type object's tp_methods and tp_getset
    segments = [
        (STRINGS, blob),
        (1100, methods),
        (1200, look),
        (1300, single),
        (1400, getsets),
        (1600, pointers),
        (1700, coded),
    ]
    data = "\n".join(f'  (data (i32.const {a}) "{_escape(b)}")' for a, b in segments)
    extra = '  (data "passive")' if passive else ""
    return f"""
(module
  (func $one (param i32) (result i32) (local.get 0))
  (func $two (param i32 i32) (result i32) (local.get 0))
  (func $three (param i32 i32 i32) (result i32) (local.get 0))
  (func $void (param i32 i32))
  (func (export "make") (result i32) (drop (i32.const 1700)) (i32.const 1300))
  (table 25 funcref)
  (elem (i32.const 21) $one $two $three $void)
  (memory 1)
{data}
{extra}
)
"""


def test_a_referenced_mismatch_is_found_and_a_look_alike_is_not(work) -> None:
    mod = wasm.parse_file(wat.build(work, "cb.wasm", _module()))
    assert mod.elements == {21: 0, 22: 1, 23: 2, 24: 3}  # table index -> function index
    report = callbacks.scan(mod)
    assert callbacks.findings(report) == [
        "getter gs: table index 21 has (i32) -> (i32), called as (i32, i32) -> (i32) (one)",
        "method bad: table index 21 has (i32) -> (i32), called as (i32, i32) -> (i32) (one)",
        "method coded: table index 21 has (i32) -> (i32), called as (i32, i32) -> (i32) (one)",
        "method void: table index 24 has (i32, i32) -> (), called as (i32, i32) -> (i32) (void)",
        "setter st: table index 22 has (i32, i32) -> (i32), "
        "called as (i32, i32, i32) -> (i32) (two)",
        "single method single: table index 22 has (i32, i32) -> (i32), "
        "called as (i32, i32, i32) -> (i32) (two)",
    ]
    assert report.coverage == {"arrays": 4, "singles": 1, "getsets": 2, "members": 0}


def test_a_finding_names_no_function_without_a_name_section(work) -> None:
    mod = wasm.parse_file(wat.build(work, "cb.wasm", _module()))
    mod.names.clear()
    assert "method bad: table index 21 has (i32) -> (i32), called as (i32, i32) -> (i32)" in (
        callbacks.findings(callbacks.scan(mod))
    )


def test_an_exclusion_is_strict_both_ways(work) -> None:
    report = callbacks.scan(wasm.parse_file(wat.build(work, "cb.wasm", _module())))
    kept = callbacks.findings(report, {"method bad": "reviewed", "method gone": "fixed upstream"})
    assert not any(f.startswith("method bad:") for f in kept)
    assert "exclusion 'method gone' matches nothing: remove it" in kept
    assert callbacks.EXCLUDED == {}  # no exclusion today: a mismatch is fixed, never excluded


def test_a_passive_data_segment_is_a_finding(work) -> None:
    mod = wasm.parse_file(wat.build(work, "cb.wasm", _module(passive=True)))
    assert "unread data segment 7: passive" in callbacks.findings(callbacks.scan(mod))


def test_a_module_with_nothing_to_scan_is_a_finding(work) -> None:
    mod = wasm.parse_file(wat.build(work, "plain.wasm", wat.PLAIN_REACTOR))
    assert callbacks.findings(callbacks.scan(mod)) == ["no data image or no function table to scan"]


def test_an_element_segment_of_another_form_is_a_finding(work) -> None:
    text = """
(module
  (func $f (param i32) (result i32) (local.get 0))
  (table 4 funcref)
  (elem (table 0) (i32.const 1) funcref (ref.func $f))
  (memory 1)
  (data (i32.const 16) "x"))
"""
    mod = wasm.parse_file(wat.build(work, "expr.wasm", text))
    assert mod.unread == ["element segment 0: form 6, not an active funcref list"]
    assert "unread element segment 0: form 6, not an active funcref list" in callbacks.findings(
        callbacks.scan(mod)
    )


def test_code_constants_are_read_at_every_position() -> None:
    # A 0x41 byte that ends one operand is read as an opcode too: 0x41 0x41 0x05 gives the
    # constant -63 and the constant 5, where reading on after each match would miss the 5.
    got = callbacks.code_constants(bytes([0x41, 0x41, 0x05]))
    assert got == {-63 & 0xFFFFFFFF, 5}
    assert callbacks.code_constants(bytes([0x41, 0x7F])) == {0xFFFFFFFF}  # -1, as an address


def test_an_extended_constant_offset_is_recorded_not_raised(work) -> None:
    """A data segment placed by an extended constant expression (wasm-ld can emit one) is unread
    by the scan, a finding, while the wall's readers still read the module (the build review,
    finding 4)."""
    text = """
(module
  (import "host" "call" (func (param i32 i32 i32 i32) (result i32)))
  (memory 1)
  (data (offset (i32.add (i32.const 16) (i32.const 16))) "x")
  (data (i32.const 64) "y"))
"""
    mod = wasm.parse_file(wat.build(work, "ext.wasm", text))
    assert mod.unread == ["data segment 0: an offset that is not one i32.const"]
    assert mod.data == [(64, b"y")]
    assert wasm.wall_errors(mod) == []


def test_a_single_at_a_parser_rule_is_not_a_method(work) -> None:
    """A code-referenced record whose second word is a table index of 1 to 20 (the parser's rules
    in a real link) is not read as a single PyMethodDef (spec 023's build: FreeType's BDF property
    table, {"ADD_STYLE_NAME", BDF_ATOM = 1, 1, 0}); the same record at index 21 is."""
    blob, at = _strings()
    rule = struct.pack("<4I", at["look"], 1, VARARGS, 0) + b"\xff" * 16
    method = struct.pack("<4I", at["single"], 21, VARARGS, 0) + b"\xff" * 16
    data = "\n".join(
        f'  (data (i32.const {a}) "{_escape(b)}")'
        for a, b in [(STRINGS, blob), (1300, rule), (1400, method)]
    )
    mod = wasm.parse_file(
        wat.build(
            work,
            "rule.wasm",
            f"""
(module
  (func $rule (param i32) (result i32) (local.get 0))
  (func (export "make") (result i32) (drop (i32.const 1300)) (i32.const 1400))
  (table 25 funcref)
  (elem (i32.const 1) $rule)
  (elem (i32.const 21) $rule)
  (memory 1)
{data}
)
""",
        )
    )
    report = callbacks.scan(mod)
    assert callbacks.findings(report) == [
        "single method single: table index 21 has (i32) -> (i32), "
        "called as (i32, i32) -> (i32) (rule)"
    ]
    assert report.coverage["singles"] == 1
