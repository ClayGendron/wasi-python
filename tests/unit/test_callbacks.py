"""The callback scan (spec 051, Decision 4) on small modules built with wat2wasm: a referenced
mismatch is found, an unreferenced look-alike is not, a code-referenced single definition is
checked, an exclusion that stops matching is a finding, and a passive segment is a finding. Three
rules each have a case that fails without them (the build review, finding 2): setters are
checked, a table referenced only from code is found, and return types are compared."""

from __future__ import annotations

import struct

import pytest

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


def _low_index_module(work, at_one: str):
    """A code-referenced record pointing at table index 1, where the function `at_one` sits, and
    the same record at index 21, where a function named `method` sits."""
    blob, at = _strings()
    rule = struct.pack("<4I", at["look"], 1, VARARGS, 0) + b"\xff" * 16
    method = struct.pack("<4I", at["single"], 21, VARARGS, 0) + b"\xff" * 16
    data = "\n".join(
        f'  (data (i32.const {a}) "{_escape(b)}")'
        for a, b in [(STRINGS, blob), (1300, rule), (1400, method)]
    )
    return wasm.parse_file(
        wat.build(
            work,
            f"{at_one}.wasm",
            f"""
(module
  (func ${at_one} (param i32) (result i32) (local.get 0))
  (func $method (param i32) (result i32) (local.get 0))
  (func (export "make") (result i32) (drop (i32.const 1300)) (i32.const 1400))
  (table 25 funcref)
  (elem (i32.const 1) ${at_one})
  (elem (i32.const 21) $method)
  (memory 1)
{{data}}
)
""".replace("{data}", data),
        )
    )


METHOD_FINDING = (
    "single method single: table index 21 has (i32) -> (i32), "
    "called as (i32, i32) -> (i32) (method)"
)


def test_a_single_at_a_parser_rule_is_not_a_method(work) -> None:
    """A code-referenced record whose function, at table index 1 to 20, the name section names as
    a parser rule is not read as a single PyMethodDef (spec 023's build: FreeType's BDF property
    table, {"ADD_STYLE_NAME", BDF_ATOM = 1, 1, 0}); the same record at index 21 is."""
    report = callbacks.scan(_low_index_module(work, "_tmp_6_rule"))
    assert callbacks.findings(report) == [METHOD_FINDING]
    assert report.coverage["singles"] == 1


@pytest.mark.parametrize("at_one", ["handler", "_rule_handler"])
def test_a_low_index_that_is_no_parser_rule_is_checked(work, at_one) -> None:
    """The exemption is checked against the name section, never assumed from link order (the
    build review, F3): another function at index 1 is a method like any other, and so is any
    function there in a module whose names are gone."""
    mod = _low_index_module(work, at_one)
    report = callbacks.scan(mod)
    low = "single method look: table index 1 has (i32) -> (i32), called as (i32, i32) -> (i32)"
    assert callbacks.findings(report) == [f"{low} ({at_one})", METHOD_FINDING]
    mod.names.clear()
    found = callbacks.findings(callbacks.scan(mod))
    assert low in found and len(found) == 2, found


# ---------------------------------------------------------------------------------------------
# Spec 096: the slot scan (`callbacks.scan_slots`) on small modules. Functions $u (i32) -> (i32),
# $d (i32) -> (), $b (i32, i32) -> (i32) and $t (i32, i32, i32) -> (i32) sit at table indices 21
# to 24. Records are laid at fixed addresses; one data segment of pointers references the ones
# meant to be referenced, as a real type's module or a PyType_FromSpec call would.

U, D, B, T = 21, 22, 23, 24
REFCNT = callbacks.STATIC_REFCNT
PAST = 60_000  # inside the memory, past every segment: .bss, zero at load


def _type(name_at: int, ob_type: int = 0, basicsize: int = 32, **fields: int) -> bytes:
    """A static PyTypeObject (212 bytes): fields by byte offset, as `o96=D` for tp_clear."""
    words = [0] * (callbacks.TYPE_SIZE // 4)
    words[0], words[1], words[3], words[4] = REFCNT, ob_type, name_at, basicsize
    for key, value in fields.items():
        words[int(key[1:]) // 4] = value
    return struct.pack(f"<{len(words)}I", *words)


def _module_def(name_at: int, slots: int = 0, clear: int = 0) -> bytes:
    return struct.pack("<13I", REFCNT, 0, 0, 0, 0, name_at, 0, 0, 0, slots, 0, clear, 0)


def _slots(*entries: tuple[int, int]) -> bytes:
    return b"".join(struct.pack("<2I", *e) for e in (*entries, (0, 0)))


class _Layout:
    """Strings at 1024, records from 2048 every 256 bytes; `ref` marks a record referenced."""

    def __init__(self) -> None:
        self.strings, self.segments, self.refs = b"", [], []
        self.next = 2048

    def string(self, raw: bytes) -> int:
        at = 1024 + len(self.strings)
        self.strings += raw + b"\0"
        return at

    def put(self, body: bytes, ref: bool = True) -> int:
        at, self.next = self.next, self.next + 256 * (1 + len(body) // 256)
        self.segments.append((at, body))
        if ref:
            self.refs.append(at)
        return at

    def module(self, work, name: str):
        segs = [(1024, self.strings), *self.segments]
        segs.append((self.next, struct.pack(f"<{len(self.refs)}I", *self.refs)))
        data = "\n".join(f'  (data (i32.const {a}) "{_escape(b)}")' for a, b in segs)
        text = f"""
(module
  (func $u (param i32) (result i32) (local.get 0))
  (func $d (param i32))
  (func $b (param i32 i32) (result i32) (local.get 0))
  (func $t (param i32 i32 i32) (result i32) (local.get 0))
  (table 25 funcref)
  (elem (i32.const 21) $u $d $b $t)
  (memory 1)
{data}
)
"""
        return wasm.parse_file(wat.build(work, f"{name}.wasm", text))


def _with_type(lay: _Layout) -> int:
    """`type` itself: the one static record whose type is itself."""
    at = lay.next
    return lay.put(_type(lay.string(b"type"), ob_type=at, basicsize=900))


def test_slots_a_static_types_void_clear_is_found_and_its_destructor_is_not(work) -> None:
    lay = _Layout()
    _with_type(lay)
    lay.put(_type(lay.string(b"m.T"), o96=D, o24=D))
    report = callbacks.scan_slots(lay.module(work, "t1"))
    assert callbacks.findings(report) == [
        "type m.T.tp_clear: table index 22 has (i32) -> (), called as (i32) -> (i32) (d)"
    ]
    assert report.coverage["types"] == 2 and "m.T" in report.seen["type"]


def test_slots_a_type_named_with_a_space_is_read(work) -> None:
    """F1: a C string is 1 to 256 bytes in 0x20-0x7E; CPython names `<dummy key> type` so."""
    lay = _Layout()
    _with_type(lay)
    lay.put(_type(lay.string(b"<a b> type"), o44=B))
    found = callbacks.findings(callbacks.scan_slots(lay.module(work, "t2")))
    assert found == [
        "type <a b> type.tp_repr: table index 23 has (i32, i32) -> (i32), "
        "called as (i32) -> (i32) (b)"
    ]


def test_slots_a_metatypes_static_instance_is_read(work) -> None:
    lay = _Layout()
    typ = _with_type(lay)
    meta = lay.put(_type(lay.string(b"m.Meta"), ob_type=typ, basicsize=300))
    lay.put(_type(lay.string(b"m.I"), ob_type=meta, o44=D))
    report = callbacks.scan_slots(lay.module(work, "t3"))
    assert callbacks.findings(report) == [
        "type m.I.tp_repr: table index 22 has (i32) -> (), called as (i32) -> (i32) (d)"
    ]
    assert report.coverage["metatypes"] == 2


def test_slots_a_suite_is_read_and_one_past_the_image_is_counted(work) -> None:
    lay = _Layout()
    _with_type(lay)
    number = lay.put(struct.pack("<36I", *([0] * 9 + [B] + [0] * 26)), ref=False)  # nb_bool
    lay.put(_type(lay.string(b"m.N"), o48=number, o56=PAST))
    report = callbacks.scan_slots(lay.module(work, "t4"))
    assert callbacks.findings(report) == [
        "type m.N.nb_bool: table index 23 has (i32, i32) -> (i32), called as (i32) -> (i32) (b)"
    ]
    assert report.coverage["suites past the image"] == 1


def test_slots_a_type_that_does_not_read_as_one_is_a_finding(work) -> None:
    lay = _Layout()
    _with_type(lay)
    lay.put(_type(lay.string(b"m.X"), o92=999))
    found = callbacks.findings(callbacks.scan_slots(lay.module(work, "t5")))
    assert found == ["type m.X: does not read as a type (tp_traverse)"]


def test_slots_no_record_for_type_is_a_finding(work) -> None:
    lay = _Layout()
    lay.put(_type(lay.string(b"m.T")))
    found = callbacks.findings(callbacks.scan_slots(lay.module(work, "t6")))
    assert found == ["0 records whose type is itself (one is `type`)"]


def test_slots_names_unreadable_null_and_typed_by_a_nameless_type(work) -> None:
    """F1 and the confirmation's Low: a referenced candidate whose tp_name points at no C string
    is a finding; tp_name 0 is a type named at run time, read and counted; a static record whose
    type is such a type is a finding, since no metatype rule classifies it."""
    lay = _Layout()
    _with_type(lay)
    bad = lay.put(_type(lay.string(b"\x01bad")))
    nameless = lay.put(_type(0, o44=D))
    inst = lay.put(_type(lay.string(b"m.Inst"), ob_type=nameless))
    report = callbacks.scan_slots(lay.module(work, "t7"))
    assert callbacks.findings(report) == sorted(
        [
            f"type at {bad:#x}: does not read as a type (tp_name)",
            f"type <tp_name NULL at {nameless:#x}>.tp_repr: table index 22 has (i32) -> (), "
            "called as (i32) -> (i32) (d)",
            f"static record at {inst:#x}: its type, a type named at run time at "
            f"{nameless:#x}, is no metatype the scan knows, so its slots go unread",
        ]
    )
    assert report.coverage["types named at run time"] == 1


def test_slots_drops_are_counted_by_reason(work) -> None:
    lay = _Layout()
    _with_type(lay)
    plain = lay.put(_type(lay.string(b"m.Plain"), basicsize=16))
    lay.put(_type(lay.string(b"m.Lost")), ref=False)  # an unreferenced candidate
    lay.put(struct.pack("<4I", REFCNT, plain, 0, 0))  # a static instance of m.Plain
    lay.put(_type(0x7372))  # its tp_name is no pointer: string-table bytes
    report = callbacks.scan_slots(lay.module(work, "t8"))
    assert callbacks.findings(report) == []
    c = report.coverage
    assert (c["unreferenced type candidates"], c["static instances"], c["names not pointers"]) == (
        1,
        1,
        1,
    )


def _spec(lay: _Layout, name: bytes, slots: bytes, ref: bool = True) -> int:
    at = lay.put(slots, ref=False)
    return lay.put(struct.pack("<5I", lay.string(name), 16, 0, 0, at), ref=ref)


def test_slots_a_specs_void_clear_is_found_and_an_unreferenced_copy_is_not(work) -> None:
    lay = _Layout()
    _with_type(lay)
    _spec(lay, b"m.S", _slots((51, D), (52, D)))
    _spec(lay, b"m.Copy", _slots((51, D)), ref=False)
    report = callbacks.scan_slots(lay.module(work, "s1"))
    assert callbacks.findings(report) == [
        "spec m.S.tp_clear: table index 22 has (i32) -> (), called as (i32) -> (i32) (d)"
    ]
    assert report.seen["spec"] == {"m.S"} and "m.S.tp_clear" in report.seen["spec slot"]


def test_slots_a_run_that_breaks_before_its_end_is_a_finding(work) -> None:
    lay = _Layout()
    _with_type(lay)
    _spec(lay, b"m.S", _slots((52, D), (200, 0)))
    found = callbacks.findings(callbacks.scan_slots(lay.module(work, "s2")))
    assert found == ["spec m.S: slot entry 1 unreadable (200, 0)"]


def test_slots_old_and_new_ids_are_both_read(work) -> None:
    lay = _Layout()
    _with_type(lay)
    _spec(lay, b"m.Old", _slots((4, B)))
    _spec(lay, b"m.New", _slots((91, B)))
    found = callbacks.findings(callbacks.scan_slots(lay.module(work, "s3")))
    want = "table index 23 has (i32, i32) -> (i32), called as (i32) -> (i32) (b)"
    assert found == [f"spec m.New.mp_length: {want}", f"spec m.Old.mp_length: {want}"]


def test_slots_a_null_function_slot_is_read_and_counted(work) -> None:
    """L3: CPython's legacy iterator only logs a NULL function slot, so the spec is read."""
    lay = _Layout()
    _with_type(lay)
    _spec(lay, b"m.First", _slots((51, 0), (52, D)))
    _spec(lay, b"m.Later", _slots((52, D), (51, 0)))
    report = callbacks.scan_slots(lay.module(work, "s4"))
    assert callbacks.findings(report) == []
    assert report.seen["spec"] == {"m.First", "m.Later"}
    assert report.coverage["NULL function slots"] == 2


def test_slots_a_module_definitions_functions_are_read(work) -> None:
    lay = _Layout()
    _with_type(lay)
    slots = lay.put(_slots((85, B)), ref=False)
    lay.put(_module_def(lay.string(b"m_one"), slots=slots, clear=D))
    lay.put(_module_def(lay.string(b"m_two"), slots=PAST))
    report = callbacks.scan_slots(lay.module(work, "m1"))
    assert callbacks.findings(report) == [
        "module m_one.Py_mod_exec: table index 23 has (i32, i32) -> (i32), "
        "called as (i32) -> (i32) (b)",
        "module m_one.m_clear: table index 22 has (i32) -> (), called as (i32) -> (i32) (d)",
    ]
    assert report.seen["module"] == {"m_one", "m_two"}
    assert report.coverage["module slots past the image"] == 1


def test_slots_check_3s_verdict_bounds_and_named_records(work) -> None:
    """F2 and the bounds: a named spec whose slots word is zeroed goes unread, and that alone is
    the problem while every minimum holds; a second type named at run time, or an unreferenced
    candidate, passes its bound."""
    named = {"spec": {"m.S"}, "spec slot": {"m.S.tp_clear"}, "type": {"type"}}
    caps = {"unreferenced type candidates": 0, "types named at run time": 1}
    floors = {"specs": 1}

    def verdict(zero_slots: bool, extra_nameless: bool = False, lost: bool = False):
        lay = _Layout()
        _with_type(lay)
        slots = lay.put(_slots((51, U)), ref=False)
        lay.put(struct.pack("<5I", lay.string(b"m.S"), 16, 0, 0, 0 if zero_slots else slots))
        lay.put(struct.pack("<5I", lay.string(b"m.Other"), 16, 0, 0, slots))
        lay.put(_type(0))
        if extra_nameless:
            lay.put(_type(0))
        if lost:
            lay.put(_type(lay.string(b"m.Lost")), ref=False)
        report = callbacks.scan_slots(lay.module(work, f"v{zero_slots}{extra_nameless}{lost}"))
        return callbacks.slot_verdict(report, floors, caps, named)

    assert verdict(False) == []
    assert verdict(True) == [
        "named record not read: spec m.S",
        "named record not read: spec slot m.S.tp_clear",
    ]
    assert verdict(False, extra_nameless=True) == ["types named at run time 2 > 1"]
    assert verdict(False, lost=True) == ["unreferenced type candidates 1 > 0"]


def test_slots_an_exclusion_is_strict_both_ways(work) -> None:
    lay = _Layout()
    _with_type(lay)
    _spec(lay, b"m.S", _slots((51, D)))
    report = callbacks.scan_slots(lay.module(work, "x1"))
    kept = callbacks.findings(report, {"spec m.S.tp_clear": "reviewed", "spec m.Gone.x": "fixed"})
    assert kept == ["exclusion 'spec m.Gone.x' matches nothing: remove it"]


def test_slots_a_types_pointer_fields_must_be_in_static_memory(work) -> None:
    """The build review's L1: a pointer field below the image's base is no type's."""
    lay = _Layout()
    _with_type(lay)
    lay.put(_type(lay.string(b"m.P"), o116=16))
    found = callbacks.findings(callbacks.scan_slots(lay.module(work, "l1a")))
    assert found == ["type m.P: does not read as a type (tp_methods)"]


def test_slots_a_types_sizes_are_bounded(work) -> None:
    lay = _Layout()
    _with_type(lay)
    lay.put(_type(lay.string(b"m.Big"), basicsize=1 << 20))
    found = callbacks.findings(callbacks.scan_slots(lay.module(work, "l1b")))
    assert found == ["type m.Big: does not read as a type (tp_basicsize or tp_itemsize)"]


def test_slots_a_module_definition_that_does_not_read_as_one_is_a_finding(work) -> None:
    lay = _Layout()
    _with_type(lay)
    lay.put(_module_def(lay.string(b"m_bad"), clear=999))
    found = callbacks.findings(callbacks.scan_slots(lay.module(work, "l1c")))
    assert found == ["module m_bad: does not read as a PyModuleDef (m_clear)"]


def test_slots_an_unknown_module_slot_id_is_a_finding(work) -> None:
    lay = _Layout()
    _with_type(lay)
    slots = lay.put(_slots((200, 0)), ref=False)
    lay.put(_module_def(lay.string(b"m_odd"), slots=slots))
    found = callbacks.findings(callbacks.scan_slots(lay.module(work, "l1d")))
    assert found == ["module m_odd: slot entry 0 unreadable (200, 0)"]


def test_slots_a_c_string_is_at_most_256_bytes(work) -> None:
    lay = _Layout()
    _with_type(lay)
    at = lay.put(_type(lay.string(b"n" * 257)))
    found = callbacks.findings(callbacks.scan_slots(lay.module(work, "l1e")))
    assert found == [f"type at {at:#x}: does not read as a type (tp_name)"]
