"""Find C callbacks whose wasm type is not the type CPython calls them with (spec 051).

CPython calls a C callback through a pointer of a fixed type. Native code tolerates a function
defined with fewer parameters; WebAssembly's `call_indirect` checks the type and traps. This scan
reads the linked `python.wasm` without running it (`harness/wasm.py`) and checks every callback
table something points at:

- **`PyMethodDef` arrays**: 16-byte entries `{name, meth, flags, doc}` ending in a zero entry;
- **single `PyMethodDef`s referenced from code**: Cython's `__pyx_mdef_…` for each module-level
  `def`, and CPython's own single definitions, not inside a found array;
- **`PyGetSetDef` arrays**: 20-byte entries `{name, get, set, doc, closure}`, zero-ended;
- **`PyMemberDef` arrays** (`{name, type <= 20, offset, flags, doc}`) are found first and kept
  out of the others, so a member's type code is never read as a function pointer.

A table is kept only when something points at it: an entry's address appears as an aligned
4-byte word in the data image (a type's `tp_methods`, a `PyModuleDef`, a `PyType_Slot`) or as an
`i32.const` operand in the code section. The operands are read at every `0x41` byte, which
over-approximates: it can add references, never lose one. A run of entries is kept from its first
referenced entry, so bytes that happen to look like an entry just before a table do not hide it.

Members go first because a member array also reads as a getset array (its type code taken for
a getter's table index). The cost: a getset array whose getters all sit at table indices 1 to 20
with no doc would read as members. In the linked binary those twenty are CPython's parser rules
(READ, spec 051's build), never a getter. A single definition whose function sits at one of them is
not read as a method (spec 023's build): FreeType's BDF property table begins `{"ADD_STYLE_NAME",
BDF_ATOM = 1, 1, 0}`, sixteen bytes the BDF driver's code points at, which read as `{name, table
index 1, METH_VARARGS, no doc}`. That rests on link order, so it is checked, not assumed: a single
is skipped only when the name section names the function there as a parser rule (`*_rule` or
`_PyPegen_*`); any other function at index 1 to 20, or a module without names, is checked as a
method like any other (the build review, F3).

The slots of static type objects, `PyType_Slot` arrays and module definitions are read by the
second scan, `scan_slots` (spec 096), whose own docstring says what it leaves out. Out of both: C
callbacks passed to C APIs (`qsort`, LAPACK).
"""

from __future__ import annotations

import re
import struct
from array import array
from collections import Counter
from dataclasses import dataclass, field

from harness.wasm import FuncType, Module

I32 = "i32"
# The flags of a PyMethodDef (Include/methodobject.h), less METH_CLASS, METH_STATIC and
# METH_COEXIST, -> the parameters CPython calls the function with.
METH_CALLS = {
    0x0001: 2,  # METH_VARARGS
    0x0004: 2,  # METH_NOARGS
    0x0008: 2,  # METH_O
    0x0003: 3,  # METH_VARARGS | METH_KEYWORDS
    0x0080: 3,  # METH_FASTCALL
    0x0082: 4,  # METH_FASTCALL | METH_KEYWORDS
    0x0282: 5,  # METH_METHOD | METH_FASTCALL | METH_KEYWORDS
}
IGNORED_FLAGS = 0x10 | 0x20 | 0x40  # METH_CLASS, METH_STATIC, METH_COEXIST
GETTER = FuncType((I32, I32), (I32,))
SETTER = FuncType((I32, I32, I32), (I32,))
IDENT = re.compile(rb"[A-Za-z_][A-Za-z0-9_]{0,80}\0")
METHOD, GETSET, MEMBER = 16, 20, 20  # entry sizes in bytes (wasm32)
# Table indices 1 to 20: CPython's parser rules in the linked binary, never a callback.
PARSER_RULES = 20
I32_CONST = re.compile(rb"(?=\x41([\x80-\xff]{0,4}[\x00-\x7f]))", re.DOTALL)

# Reviewed real cases only, keyed by "<kind> <entry name>", each with its reason. Today none: a
# mismatch is fixed by a carried patch or an upstream release, never by an exclusion. An entry
# that no longer matches a finding is itself a finding.
EXCLUDED: dict[str, str] = {}


@dataclass
class Report:
    findings: list[str] = field(default_factory=list)
    coverage: dict[str, int] = field(
        default_factory=lambda: {"arrays": 0, "singles": 0, "getsets": 0, "members": 0}
    )

    def summary(self) -> str:
        c = self.coverage
        return (
            f"{c['arrays']} method-array entries, {c['singles']} single definitions, "
            f"{c['getsets']} getset entries, {c['members']} member entries"
        )


class _Image:
    """The static memory image: every active data segment laid at its address."""

    def __init__(self, segments: list[tuple[int, bytes]]) -> None:
        self.base = min((off for off, _ in segments), default=0)
        self.base -= self.base % 4
        top = max((off + len(body) for off, body in segments), default=self.base)
        mem = bytearray(top - self.base)
        for off, body in segments:
            mem[off - self.base : off - self.base + len(body)] = body
        self.mem = bytes(mem)

    def has(self, addr: int, n: int = 1) -> bool:
        return self.base <= addr and addr + n <= self.base + len(self.mem)

    def words(self, addr: int, n: int) -> tuple[int, ...] | None:
        if not self.has(addr, 4 * n):
            return None
        return struct.unpack_from(f"<{n}I", self.mem, addr - self.base)

    def ident(self, addr: int) -> str | None:
        if not self.has(addr):
            return None
        m = IDENT.match(self.mem, addr - self.base)
        return m.group()[:-1].decode() if m else None

    def zero(self, addr: int, n: int) -> bool:
        return self.has(addr, n) and not any(self.mem[addr - self.base : addr - self.base + n])


def code_constants(code: bytes) -> set[int]:
    """Every value an `i32.const` could carry in the code: the signed LEB after each 0x41 byte,
    read at every position, so an opcode inside another's operand is never skipped."""
    out = set()
    for m in I32_CONST.finditer(code):
        raw = m.group(1)
        value = shift = 0
        for b in raw:
            value |= (b & 0x7F) << shift
            shift += 7
        if raw[-1] & 0x40:
            value -= 1 << shift
        out.add(value & 0xFFFFFFFF)
    return out


def data_words(image: _Image) -> set[int]:
    """Every aligned 4-byte word of the image."""
    words = array("I")
    usable = len(image.mem) - len(image.mem) % 4
    words.frombytes(image.mem[:usable])
    if words.itemsize != 4:  # pragma: no cover - every platform the judge runs on
        raise RuntimeError("array('I') is not 4 bytes here")
    if struct.pack("=I", 1) != struct.pack("<I", 1):  # pragma: no cover
        words.byteswap()
    return set(words)


def _method_entry(image: _Image, addr: int, elements: dict[int, int]):
    w = image.words(addr, 4)
    if w is None:
        return None
    name_ptr, meth, flags, doc = w
    name = image.ident(name_ptr) if name_ptr else None
    if not name or meth not in elements or (flags & ~IGNORED_FLAGS) not in METH_CALLS:
        return None
    if doc and not image.has(doc):
        return None
    return name, meth, flags


def _getset_entry(image: _Image, addr: int, elements: dict[int, int]):
    w = image.words(addr, 5)
    if w is None:
        return None
    name_ptr, get, set_, doc, _closure = w
    name = image.ident(name_ptr) if name_ptr else None
    if not name or not (get or set_):
        return None
    if (get and get not in elements) or (set_ and set_ not in elements):
        return None
    if doc and not image.has(doc):
        return None
    return name, get, set_


def _member_entry(image: _Image, addr: int, _elements: dict[int, int]):
    w = image.words(addr, 5)
    if w is None:
        return None
    name_ptr, type_code, _offset, flags, doc = w
    if not name_ptr or not image.ident(name_ptr) or type_code > 20 or flags > 0xF:
        return None
    if doc and not image.has(doc):
        return None
    return (image.ident(name_ptr),)


def _tables(image, size, entry, elements, refs, taken):
    """Every zero-ended run of entries not in `taken`, kept from its first referenced entry:
    a list of (address, entry) lists. The bytes of each kept table join `taken`."""
    tables = []
    start = image.base
    end = image.base + len(image.mem)
    seen: set[int] = set()
    for addr in range(start, end - size, 4):
        if addr in seen or addr in taken:
            continue
        run = []
        p = addr
        while p not in taken:
            e = entry(image, p, elements)
            if e is None:
                break
            run.append((p, e))
            p += size
        if not run or not image.zero(p, size):
            continue
        seen.update(q for q, _ in run)
        first = next((k for k, (q, _) in enumerate(run) if q in refs), None)
        if first is None:
            continue
        kept = run[first:]
        tables.append(kept)
        for q, _ in kept:
            taken.update(range(q, q + size))
    return tables


def _parser_rule(mod: Module, index: int) -> bool:
    """Whether the name section names the function at this table index as one of CPython's parser
    rules."""
    name = mod.names.get(mod.elements[index], "")
    return name.endswith("_rule") or name.startswith("_PyPegen_")


def _named(mod: Module, func: int) -> str:
    name = mod.names.get(func)
    return f" ({name})" if name else ""


def _check(mod: Module, kind: str, entry: str, index: int, want: FuncType) -> str | None:
    func = mod.elements[index]
    have = mod.func_type(func)
    if have == want:
        return None
    return f"{kind} {entry}: table index {index} has {have}, called as {want}{_named(mod, func)}"


def _method_type(flags: int) -> FuncType:
    return FuncType((I32,) * METH_CALLS[flags & ~IGNORED_FLAGS], (I32,))


def scan(mod: Module) -> Report:
    """Every referenced callback table's entries checked against the type CPython calls them
    with; segments the reader could not place are findings too."""
    report = Report()
    report.findings += [f"unread {u}" for u in mod.unread]
    if not mod.data or not mod.elements:
        report.findings.append("no data image or no function table to scan")
        return report
    image = _Image(mod.data)
    consts = code_constants(mod.code)
    refs = data_words(image) | consts
    elements = mod.elements
    taken: set[int] = set()

    members = _tables(image, MEMBER, _member_entry, elements, refs, taken)
    report.coverage["members"] = sum(len(t) for t in members)

    methods = _tables(image, METHOD, _method_entry, elements, refs, taken)
    in_arrays = set()
    for table in methods:
        for addr, (name, meth, flags) in table:
            in_arrays.add(addr)
            report.coverage["arrays"] += 1
            found = _check(mod, "method", name, meth, _method_type(flags))
            report.findings += [found] if found else []

    getsets = _tables(image, GETSET, _getset_entry, elements, refs, taken)
    for table in getsets:
        for _addr, (name, get, set_) in table:
            report.coverage["getsets"] += 1
            for kind, index, want in (("getter", get, GETTER), ("setter", set_, SETTER)):
                found = _check(mod, kind, name, index, want) if index else None
                report.findings += [found] if found else []

    for addr in sorted(consts):
        if addr % 4 or addr in taken or not image.has(addr, METHOD):
            continue
        e = _method_entry(image, addr, elements)
        if e is None:
            continue
        name, meth, flags = e
        if meth <= PARSER_RULES and _parser_rule(mod, meth):
            continue  # a record that only looks like a PyMethodDef (the module docstring says why)
        report.coverage["singles"] += 1
        found = _check(mod, "single method", name, meth, _method_type(flags))
        report.findings += [found] if found else []
    return report


def findings(report: Report, excluded: dict[str, str] | None = None) -> list[str]:
    """The report's findings less the reviewed exclusions, plus every exclusion that no longer
    matches a finding (strict both ways)."""
    excluded = EXCLUDED if excluded is None else excluded
    out, used = [], set()
    for f in report.findings:
        key = f.split(":", 1)[0]
        if key in excluded:
            used.add(key)
            continue
        out.append(f)
    out += [f"exclusion {k!r} matches nothing: remove it" for k in excluded if k not in used]
    return sorted(set(out))


# ---------------------------------------------------------------------------------------------
# Spec 096: the type slots, slot arrays and module definitions CPython calls through.

UNARY = FuncType((I32,), (I32,))
BINARY = FuncType((I32, I32), (I32,))
TERNARY = FuncType((I32, I32, I32), (I32,))
DESTRUCTOR = FuncType((I32,), ())
RELEASEBUFFER = FuncType((I32, I32), ())
VECTORCALL = FuncType((I32, I32, I32, I32), (I32,))
ITERITEM = FuncType((I32, I32, I32), ())  # returns a two-word struct through a hidden pointer

# _Py_STATIC_IMMORTAL_INITIAL_REFCNT on 32-bit (Include/refcount.h), which PyObject_HEAD_INIT
# writes into every static object.
STATIC_REFCNT = 7 << 28
TYPE_SIZE = 212  # sizeof(PyTypeObject) on wasm32, CPython 3.15
MODULE_SIZE = 52  # sizeof(PyModuleDef)
SPEC_SIZE = 20  # sizeof(PyType_Spec)
STRING = re.compile(rb"[\x20-\x7e]{1,256}\0")

# PyTypeObject's function fields: byte offset -> (field, the type CPython calls it with).
TYPE_FUNCS = {
    24: ("tp_dealloc", DESTRUCTOR),
    32: ("tp_getattr", BINARY),
    36: ("tp_setattr", TERNARY),
    44: ("tp_repr", UNARY),
    60: ("tp_hash", UNARY),
    64: ("tp_call", TERNARY),
    68: ("tp_str", UNARY),
    72: ("tp_getattro", BINARY),
    76: ("tp_setattro", TERNARY),
    92: ("tp_traverse", TERNARY),
    96: ("tp_clear", UNARY),
    100: ("tp_richcompare", TERNARY),
    108: ("tp_iter", UNARY),
    112: ("tp_iternext", UNARY),
    136: ("tp_descr_get", TERNARY),
    140: ("tp_descr_set", TERNARY),
    148: ("tp_init", TERNARY),
    152: ("tp_alloc", BINARY),
    156: ("tp_new", TERNARY),
    160: ("tp_free", DESTRUCTOR),
    164: ("tp_is_gc", UNARY),
    188: ("tp_del", DESTRUCTOR),
    196: ("tp_finalize", DESTRUCTOR),
    200: ("tp_vectorcall", VECTORCALL),
    208: ("_tp_iteritem", ITERITEM),
}
# Its pointer fields: each 0 or in static memory (.bss lies past the image).
TYPE_POINTERS = {
    40: "tp_as_async",
    48: "tp_as_number",
    52: "tp_as_sequence",
    56: "tp_as_mapping",
    80: "tp_as_buffer",
    88: "tp_doc",
    116: "tp_methods",
    120: "tp_members",
    124: "tp_getset",
    128: "tp_base",
}
_NB_UNARY = {"negative", "positive", "absolute", "invert", "int", "float", "index"}
_NB = (
    "add subtract multiply remainder divmod power negative positive absolute bool invert lshift "
    "rshift and xor or int reserved float inplace_add inplace_subtract inplace_multiply "
    "inplace_remainder inplace_power inplace_lshift inplace_rshift inplace_and inplace_xor "
    "inplace_or floor_divide true_divide inplace_floor_divide inplace_true_divide index "
    "matrix_multiply inplace_matrix_multiply"
).split()


def _nb(name: str) -> FuncType | None:
    if name == "reserved":
        return None
    if name in ("power", "inplace_power"):
        return TERNARY
    return UNARY if name in _NB_UNARY or name == "bool" else BINARY


# The method suites a type points at: its field offset -> (suite, [(field, type or None)]).
SUITES = {
    40: (
        "tp_as_async",
        [("am_await", UNARY), ("am_aiter", UNARY), ("am_anext", UNARY), ("am_send", TERNARY)],
    ),
    48: ("tp_as_number", [(f"nb_{n}", _nb(n)) for n in _NB]),
    52: (
        "tp_as_sequence",
        [
            ("sq_length", UNARY),
            ("sq_concat", BINARY),
            ("sq_repeat", BINARY),
            ("sq_item", BINARY),
            ("was_sq_slice", None),
            ("sq_ass_item", TERNARY),
            ("was_sq_ass_slice", None),
            ("sq_contains", BINARY),
            ("sq_inplace_concat", BINARY),
            ("sq_inplace_repeat", BINARY),
        ],
    ),
    56: (
        "tp_as_mapping",
        [("mp_length", UNARY), ("mp_subscript", BINARY), ("mp_ass_subscript", TERNARY)],
    ),
    80: ("tp_as_buffer", [("bf_getbuffer", TERNARY), ("bf_releasebuffer", RELEASEBUFFER)]),
}

# PyType_Slot ids (Include/slots_generated.h, 3.15.0) -> (slot, type, or None for a data slot).
_NB_IDS = (
    "6 absolute 7 add 8 and 9 bool 10 divmod 11 float 12 floor_divide 13 index 14 inplace_add "
    "15 inplace_and 16 inplace_floor_divide 17 inplace_lshift 18 inplace_multiply 19 inplace_or "
    "20 inplace_power 21 inplace_remainder 22 inplace_rshift 23 inplace_subtract "
    "24 inplace_true_divide 25 inplace_xor 26 int 27 invert 28 lshift 29 multiply 30 negative "
    "31 or 32 positive 33 power 34 remainder 35 rshift 36 subtract 37 true_divide 38 xor "
    "75 matrix_multiply 76 inplace_matrix_multiply"
).split()
SLOT_IDS: dict[int, tuple[str, FuncType | None]] = {
    int(i): (f"nb_{n}", _nb(n)) for i, n in zip(_NB_IDS[::2], _NB_IDS[1::2], strict=True)
}
SLOT_IDS.update(
    {
        5: ("mp_subscript", BINARY),
        39: ("sq_ass_item", TERNARY),
        40: ("sq_concat", BINARY),
        41: ("sq_contains", BINARY),
        42: ("sq_inplace_concat", BINARY),
        43: ("sq_inplace_repeat", BINARY),
        44: ("sq_item", BINARY),
        45: ("sq_length", UNARY),
        46: ("sq_repeat", BINARY),
        47: ("tp_alloc", BINARY),
        48: ("tp_base", None),
        49: ("tp_bases", None),
        50: ("tp_call", TERNARY),
        51: ("tp_clear", UNARY),
        52: ("tp_dealloc", DESTRUCTOR),
        53: ("tp_del", DESTRUCTOR),
        54: ("tp_descr_get", TERNARY),
        55: ("tp_descr_set", TERNARY),
        56: ("tp_doc", None),
        57: ("tp_getattr", BINARY),
        58: ("tp_getattro", BINARY),
        59: ("tp_hash", UNARY),
        60: ("tp_init", TERNARY),
        61: ("tp_is_gc", UNARY),
        62: ("tp_iter", UNARY),
        63: ("tp_iternext", UNARY),
        64: ("tp_methods", None),
        65: ("tp_new", TERNARY),
        66: ("tp_repr", UNARY),
        67: ("tp_richcompare", TERNARY),
        68: ("tp_setattr", TERNARY),
        69: ("tp_setattro", TERNARY),
        70: ("tp_str", UNARY),
        71: ("tp_traverse", TERNARY),
        72: ("tp_members", None),
        73: ("tp_getset", None),
        74: ("tp_free", DESTRUCTOR),
        77: ("am_await", UNARY),
        78: ("am_aiter", UNARY),
        79: ("am_anext", UNARY),
        80: ("tp_finalize", DESTRUCTOR),
        81: ("am_send", TERNARY),
        82: ("tp_vectorcall", VECTORCALL),
        83: ("tp_token", None),
        # The four ids 3.15 renumbered: the old ones (a limited API before 3.15) and the new.
        1: ("bf_getbuffer", TERNARY),
        2: ("bf_releasebuffer", RELEASEBUFFER),
        3: ("mp_ass_subscript", TERNARY),
        4: ("mp_length", UNARY),
        88: ("bf_getbuffer", TERNARY),
        89: ("bf_releasebuffer", RELEASEBUFFER),
        90: ("mp_ass_subscript", TERNARY),
        91: ("mp_length", UNARY),
    }
)
# PyModuleDef_Slot ids, old and new.
MODULE_SLOT_IDS: dict[int, tuple[str, FuncType | None]] = {
    1: ("Py_mod_create", BINARY),
    84: ("Py_mod_create", BINARY),
    2: ("Py_mod_exec", UNARY),
    85: ("Py_mod_exec", UNARY),
    3: ("Py_mod_multiple_interpreters", None),
    86: ("Py_mod_multiple_interpreters", None),
    4: ("Py_mod_gil", None),
    87: ("Py_mod_gil", None),
    109: ("Py_mod_abi", None),
    110: ("Py_mod_token", None),
}
SLOT_COVERAGE = (
    "types",
    "specs",
    "modules",
    "functions",
    "metatypes",
    "types named at run time",
    "unreferenced type candidates",
    "static instances",
    "names not pointers",
    "module-shaped records",
    "specs with slots past the image",
    "suites past the image",
    "module slots past the image",
    "NULL function slots",
)


@dataclass
class SlotReport:
    findings: list[str] = field(default_factory=list)
    coverage: Counter = field(default_factory=lambda: Counter(dict.fromkeys(SLOT_COVERAGE, 0)))
    seen: dict[str, set[str]] = field(
        default_factory=lambda: {"type": set(), "spec": set(), "spec slot": set(), "module": set()}
    )

    def summary(self) -> str:
        return ", ".join(f"{self.coverage[k]} {k}" for k in SLOT_COVERAGE)


def _string(image: _Image, addr: int) -> str | None:
    """A C string: 1 to 256 bytes in 0x20-0x7E, ending in NUL (spec 096, the review's F1)."""
    if not addr or not image.has(addr):
        return None
    m = STRING.match(image.mem, addr - image.base)
    return m.group()[:-1].decode() if m else None


def _static(image: _Image, addr: int) -> bool:
    """Whether an address lies in static memory: the image or the zero-filled .bss past it."""
    return image.base <= addr < 1 << 31


def scan_slots(mod: Module) -> SlotReport:
    """The functions CPython calls through the slots of static type objects (and the method
    suites they point at), through `PyType_Slot` arrays (found by their `PyType_Spec`) and through
    static module definitions, each checked against the type CPython calls it with (spec 096,
    Decision 3). Only records something points at are read. Every static record is classified,
    each one dropped is counted by its reason, and one that starts like a record but does not read
    as one is a finding.

    Out of this scan: slots code fills at run time (pybind11's heap types, `PyType_Ready`'s
    inherited slots, a type made from a spec built in code); records C++ dynamic initialization
    fills (they lie in .bss, past the image); a spec whose first entry is neither a known id nor a
    NULL function slot (irreducible by shape: a `PyMethodDef` reads as a spec); the `PySlot`
    arrays of 3.15 (`PyModExport`), which no linked module uses. Their ids 92 to 110
    (`Py_slot_subslots`, `Py_tp_slots`, `Py_mod_slots`, `Py_tp_name`, `Py_tp_basicsize`,
    `Py_tp_extra_basicsize`, `Py_tp_itemsize`, `Py_tp_flags`, `Py_mod_name`, `Py_mod_doc`,
    `Py_mod_state_size`, `Py_mod_methods`, `Py_mod_state_traverse`, `Py_mod_state_clear`,
    `Py_mod_state_free`, `Py_tp_metaclass`, `Py_tp_module`) are findings inside a `PyType_Slot`
    run, where they do not belong."""
    report = SlotReport()
    report.findings += [f"unread {u}" for u in mod.unread]
    if not mod.data or not mod.elements:
        report.findings.append("no data image or no function table to scan")
        return report
    image = _Image(mod.data)
    refs = data_words(image) | code_constants(mod.code)
    cov = report.coverage

    def check(kind: str, owner: str, slot: str, index: int, want: FuncType | None) -> None:
        if not index or want is None:
            return
        cov["functions"] += 1
        if index not in mod.elements:
            report.findings.append(f"{kind} {owner}.{slot}: {index} is not a table index")
            return
        found = _check(mod, kind, f"{owner}.{slot}", index, want)
        report.findings += [found] if found else []

    end = image.base + len(image.mem)
    records = {}
    for addr in range(image.base, end - 8, 4):
        if image.words(addr, 1) == (STATIC_REFCNT,):
            w = image.words(addr, TYPE_SIZE // 4)
            if w is None:  # a record cut by the image's end: pad with the zeros of .bss
                have = (end - addr) // 4
                w = image.words(addr, have) + (0,) * (TYPE_SIZE // 4 - have)
            records[addr] = w
    _types(mod, image, refs, records, report, check)
    _specs(mod, image, refs, report, check)
    _modules(mod, image, refs, records, report, check)
    return report


def _types(mod, image, refs, records, report, check) -> None:
    cov, seen = report.coverage, report.seen
    names = {a: _string(image, w[3]) for a, w in records.items()}
    selfref = [a for a, w in records.items() if w[1] == a]
    if len(selfref) != 1:
        report.findings.append(f"{len(selfref)} records whose type is itself (one is `type`)")
    meta = set(selfref)
    while True:
        new = {
            a
            for a, w in records.items()
            if a not in meta
            and names[a]
            and (w[1] == 0 or w[1] in meta)
            and (w[4] >= TYPE_SIZE or w[32] in meta)
        }
        if not new:
            break
        meta |= new
    cov["metatypes"] = len(meta)
    nameless, instances = set(), []
    for addr, w in records.items():
        if not any(w[1:5]) and _string(image, w[5]):
            cov["module-shaped records"] += 1
            continue
        if not (w[1] == 0 or w[1] in meta):
            cov["static instances"] += 1
            instances.append((addr, w[1]))
            continue
        if w[3] and not image.has(w[3]):
            cov["names not pointers"] += 1
            continue
        if addr not in refs:
            cov["unreferenced type candidates"] += 1
            continue
        if w[3] and not names[addr]:
            report.findings.append(f"type at {addr:#x}: does not read as a type (tp_name)")
            continue
        name = names[addr] or f"<tp_name NULL at {addr:#x}>"
        bad = [
            f
            for off, (f, _) in TYPE_FUNCS.items()
            if w[off // 4] and w[off // 4] not in mod.elements
        ]
        bad += [
            f for off, f in TYPE_POINTERS.items() if w[off // 4] and not _static(image, w[off // 4])
        ]
        if w[4] >= 1 << 20 or w[5] >= 1 << 16:
            bad.append("tp_basicsize or tp_itemsize")
        if bad:
            report.findings.append(f"type {name}: does not read as a type ({', '.join(bad)})")
            continue
        cov["types"] += 1
        seen["type"].add(name)
        if not names[addr]:
            cov["types named at run time"] += 1
            nameless.add(addr)
        for off, (slot, want) in TYPE_FUNCS.items():
            check("type", name, slot, w[off // 4], want)
        for off, (_suite, fields) in SUITES.items():
            if not w[off // 4]:
                continue
            values = image.words(w[off // 4], len(fields))
            if values is None:  # past the image: an empty static struct, zero at load
                cov["suites past the image"] += 1
                continue
            for (slot, want), value in zip(fields, values, strict=True):
                check("type", name, slot, value, want)
    for addr, typ in instances:
        if typ in nameless:
            report.findings.append(
                f"static record at {addr:#x}: its type, a type named at run time at {typ:#x}, "
                "is no metatype the scan knows, so its slots go unread"
            )


def _specs(mod, image, refs, report, check) -> None:
    """`PyType_Spec`s {name, basicsize, itemsize, flags, slots} and their `PyType_Slot` runs."""
    cov, seen = report.coverage, report.seen

    def readable(entry) -> bool:
        # A function slot holding 0 is readable (CPython's legacy iterator only logs it): it is
        # skipped and counted, never checked (spec 096, the review's L3).
        if entry is None or entry[0] not in SLOT_IDS:
            return False
        return SLOT_IDS[entry[0]][1] is None or entry[1] == 0 or entry[1] in mod.elements

    for addr in range(image.base, image.base + len(image.mem) - SPEC_SIZE + 1, 4):
        if addr not in refs:
            continue
        name_ptr, basicsize, itemsize, _flags, slots = image.words(addr, 5)
        if not slots or basicsize >= 1 << 20 or itemsize >= 1 << 16:
            continue
        name = _string(image, name_ptr)
        if not name:
            continue
        if not image.has(slots, 8):
            if _static(image, slots):
                cov["specs with slots past the image"] += 1
            continue
        if not readable(image.words(slots, 2)):
            continue  # not a spec: its first entry is no slot (out of the scan, by shape)
        entries, p = [], slots
        while True:
            entry = image.words(p, 2)
            if entry is not None and entry[0] == 0:
                break
            if not readable(entry) or len(entries) > 120:
                report.findings.append(f"spec {name}: slot entry {len(entries)} unreadable {entry}")
                entries = None
                break
            entries.append(entry)
            p += 8
        if entries is None:
            continue
        cov["specs"] += 1
        seen["spec"].add(name)
        for sid, value in entries:
            slot, want = SLOT_IDS[sid]
            if want is None:
                continue
            if value == 0:
                cov["NULL function slots"] += 1
                continue
            check("spec", name, slot, value, want)
            seen["spec slot"].add(f"{name}.{slot}")


def _modules(mod, image, refs, records, report, check) -> None:
    """Static `PyModuleDef`s: m_traverse, m_clear, m_free and their m_slots' functions."""
    cov, seen = report.coverage, report.seen
    for addr, w in records.items():
        if any(w[1:5]):
            continue
        name = _string(image, w[5])
        if not name or addr not in refs:
            continue
        bad = [
            f
            for f, v in zip(("m_traverse", "m_clear", "m_free"), w[10:13], strict=True)
            if v and v not in mod.elements
        ]
        bad += [
            f for f, v in (("m_methods", w[8]), ("m_slots", w[9])) if v and not _static(image, v)
        ]
        if bad:
            report.findings.append(
                f"module {name}: does not read as a PyModuleDef ({', '.join(bad)})"
            )
            continue
        cov["modules"] += 1
        seen["module"].add(name)
        check("module", name, "m_traverse", w[10], TERNARY)
        check("module", name, "m_clear", w[11], UNARY)
        check("module", name, "m_free", w[12], DESTRUCTOR)
        p = w[9]
        while p:
            entry = image.words(p, 2)
            if entry is None and p == w[9]:  # zero at load: empty, or filled by code (pybind11)
                cov["module slots past the image"] += 1
                break
            if entry is None or (entry[0] and entry[0] not in MODULE_SLOT_IDS):
                report.findings.append(
                    f"module {name}: slot entry {(p - w[9]) // 8} unreadable {entry}"
                )
                break
            if entry[0] == 0:
                break
            slot, want = MODULE_SLOT_IDS[entry[0]]
            check("module", name, slot, entry[1], want)
            p += 8


def unread_named(report: SlotReport, named: dict[str, set[str]]) -> list[str]:
    """Each named record the report did not read (spec 096, check 3; the review's F2)."""
    return [
        f"named record not read: {kind} {n}"
        for kind, names in named.items()
        for n in sorted(names - report.seen.get(kind, set()))
    ]


def slot_verdict(
    report: SlotReport,
    minimums: dict[str, int],
    maximums: dict[str, int],
    named: dict[str, set[str]],
) -> list[str]:
    """Check 3's problems with a slot report (spec 096): its findings less the reviewed
    exclusions, any coverage below its minimum or above its bound, and each named record unread."""
    c = report.coverage
    return (
        findings(report)
        + [f"{k} {c[k]} < {floor}" for k, floor in minimums.items() if c[k] < floor]
        + [f"{k} {c[k]} > {cap}" for k, cap in maximums.items() if c[k] > cap]
        + unread_named(report, named)
    )
