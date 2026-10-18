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
(READ, spec 051's build), never a getter. For the same reason a single definition whose function
sits at one of them is not read as a method (spec 023's build): FreeType's BDF property table
begins `{"ADD_STYLE_NAME", BDF_ATOM = 1, 1, 0}`, sixteen bytes the BDF driver's code points at,
which read as `{name, table index 1, METH_VARARGS, no doc}`.

Out of the scan: the `tp_*` slots of static type objects, `PyType_Slot` arrays, the number,
sequence and mapping method structs, and C callbacks passed to C APIs (`qsort`, LAPACK).
"""

from __future__ import annotations

import re
import struct
from array import array
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
        if meth <= PARSER_RULES:
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
