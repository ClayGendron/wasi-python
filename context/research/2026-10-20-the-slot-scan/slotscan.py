"""Spec 096's drafting scanner: the type slots spec 051's callback scan leaves out.

Reads a linked python.wasm with the judge's own reader (tests/harness/wasm.py) and checks:
- PyType_Slot arrays, each found through the PyType_Spec that points at it;
- static PyTypeObjects (word 0 is the static immortal refcount, 7 << 28 on wasm32), their tp_*
  function fields, and the PyAsyncMethods, PyNumberMethods, PySequenceMethods, PyMappingMethods
  and PyBufferProcs they point at;
- static PyModuleDefs: m_traverse, m_clear, m_free and their m_slots.
Only referenced records are kept; one that starts like a record but does not read as one is a
finding. Spec 096's Decision 3 states the rules.

Run from the worktree: uv run python context/research/2026-10-20-the-slot-scan/slotscan.py <wasm>
A research script, not the judge's code: the judge's version lives in tests/harness/callbacks.py.
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests"))

from harness import callbacks, wasm  # noqa: E402
from harness.wasm import FuncType  # noqa: E402

I = "i32"  # noqa: E741


def ft(n: int, ret: bool = True) -> FuncType:
    return FuncType((I,) * n, (I,) if ret else ())


DESTRUCTOR = ft(1, False)
UNARY = ft(1)
BINARY = ft(2)
TERNARY = ft(3)
INQUIRY = ft(1)
VECTORCALL = ft(4)
RELEASEBUF = ft(2, False)

# PyTypeObject on wasm32 (Include/cpython/object.h, 3.15.0): offset -> (field, type).
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
    96: ("tp_clear", INQUIRY),
    100: ("tp_richcompare", TERNARY),
    108: ("tp_iter", UNARY),
    112: ("tp_iternext", UNARY),
    136: ("tp_descr_get", TERNARY),
    140: ("tp_descr_set", TERNARY),
    148: ("tp_init", TERNARY),
    152: ("tp_alloc", BINARY),
    156: ("tp_new", TERNARY),
    160: ("tp_free", DESTRUCTOR),
    164: ("tp_is_gc", INQUIRY),
    188: ("tp_del", DESTRUCTOR),
    196: ("tp_finalize", DESTRUCTOR),
    200: ("tp_vectorcall", VECTORCALL),
    208: ("_tp_iteritem", ft(3, False)),  # returns a two-word struct through a pointer
}
TYPE_PTRS = {
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
TYPE_RUNTIME = {132: "tp_dict", 168: "tp_bases", 172: "tp_mro", 176: "tp_cache", 184: "tp_weaklist"}
TYPE_SIZE = 212
STATIC_REFCNT = 7 << 28

NB = [
    "add",
    "subtract",
    "multiply",
    "remainder",
    "divmod",
    "power",
    "negative",
    "positive",
    "absolute",
    "bool",
    "invert",
    "lshift",
    "rshift",
    "and",
    "xor",
    "or",
    "int",
    "reserved",
    "float",
    "inplace_add",
    "inplace_subtract",
    "inplace_multiply",
    "inplace_remainder",
    "inplace_power",
    "inplace_lshift",
    "inplace_rshift",
    "inplace_and",
    "inplace_xor",
    "inplace_or",
    "floor_divide",
    "true_divide",
    "inplace_floor_divide",
    "inplace_true_divide",
    "index",
    "matrix_multiply",
    "inplace_matrix_multiply",
]


def nb_type(name: str) -> FuncType | None:
    if name == "reserved":
        return None
    if name in ("power", "inplace_power"):
        return TERNARY
    if name in ("negative", "positive", "absolute", "invert", "int", "float", "index"):
        return UNARY
    if name == "bool":
        return INQUIRY
    return BINARY


SUITES = {
    "tp_as_async": [
        ("am_await", UNARY),
        ("am_aiter", UNARY),
        ("am_anext", UNARY),
        ("am_send", TERNARY),
    ],
    "tp_as_number": [(f"nb_{n}", nb_type(n)) for n in NB],
    "tp_as_sequence": [
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
    "tp_as_mapping": [
        ("mp_length", UNARY),
        ("mp_subscript", BINARY),
        ("mp_ass_subscript", TERNARY),
    ],
    "tp_as_buffer": [("bf_getbuffer", TERNARY), ("bf_releasebuffer", RELEASEBUF)],
}

# Slot ids (Include/slots_generated.h, 3.15.0) -> (name, type); None for a data slot.
SLOT_IDS: dict[int, tuple[str, FuncType | None]] = {}
for sid, name in [(5, "mp_subscript")]:
    SLOT_IDS[sid] = (name, BINARY)
_nb_ids = {
    6: "absolute",
    7: "add",
    8: "and",
    9: "bool",
    10: "divmod",
    11: "float",
    12: "floor_divide",
    13: "index",
    14: "inplace_add",
    15: "inplace_and",
    16: "inplace_floor_divide",
    17: "inplace_lshift",
    18: "inplace_multiply",
    19: "inplace_or",
    20: "inplace_power",
    21: "inplace_remainder",
    22: "inplace_rshift",
    23: "inplace_subtract",
    24: "inplace_true_divide",
    25: "inplace_xor",
    26: "int",
    27: "invert",
    28: "lshift",
    29: "multiply",
    30: "negative",
    31: "or",
    32: "positive",
    33: "power",
    34: "remainder",
    35: "rshift",
    36: "subtract",
    37: "true_divide",
    38: "xor",
    75: "matrix_multiply",
    76: "inplace_matrix_multiply",
}
for sid, n in _nb_ids.items():
    SLOT_IDS[sid] = (f"nb_{n}", nb_type(n))
SLOT_IDS.update(
    {
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
        51: ("tp_clear", INQUIRY),
        52: ("tp_dealloc", DESTRUCTOR),
        53: ("tp_del", DESTRUCTOR),
        54: ("tp_descr_get", TERNARY),
        55: ("tp_descr_set", TERNARY),
        56: ("tp_doc", None),
        57: ("tp_getattr", BINARY),
        58: ("tp_getattro", BINARY),
        59: ("tp_hash", UNARY),
        60: ("tp_init", TERNARY),
        61: ("tp_is_gc", INQUIRY),
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
        # the four ids 3.15 renumbered; the old ones (1 to 4) stay valid in a PyType_Slot
        88: ("bf_getbuffer", TERNARY),
        89: ("bf_releasebuffer", RELEASEBUF),
        90: ("mp_ass_subscript", TERNARY),
        91: ("mp_length", UNARY),
        1: ("bf_getbuffer", TERNARY),
        2: ("bf_releasebuffer", RELEASEBUF),
        3: ("mp_ass_subscript", TERNARY),
        4: ("mp_length", UNARY),
    }
)


def cstring(image, addr: int, limit: int = 120) -> str | None:
    if not addr or not image.has(addr):
        return None
    off = addr - image.base
    end = image.mem.find(b"\0", off, off + limit)
    if end <= off:
        return None
    raw = image.mem[off:end]
    if not all(0x20 < b < 0x7F for b in raw):
        return None
    return raw.decode()


def main(path: str) -> None:
    mod = wasm.parse_file(path)
    image = callbacks._Image(mod.data)
    refs = callbacks.data_words(image) | callbacks.code_constants(mod.code)
    el = mod.elements
    findings: list[str] = []
    cov = collections.Counter()

    def check(kind, owner, field, index, want):
        if not index or want is None:
            return
        if index not in el:
            findings.append(f"{kind} {owner}.{field}: {index} is not a table index")
            return
        have = mod.func_type(el[index])
        cov[kind + " slots"] += 1
        if have != want:
            nm = mod.names.get(el[index], "?")
            findings.append(
                f"{kind} {owner}.{field}: table index {index} has {have}, called as {want} ({nm})"
            )

    # 1. static type objects. A candidate: the static immortal refcount, then a C string at
    # tp_name. `type` is the one candidate whose ob_type is itself; a metatype is `type`, or a type
    # whose instances are at least a PyTypeObject (tp_basicsize >= 212) or whose tp_base is a
    # metatype. A type is a candidate whose ob_type is 0 (set by PyType_Ready) or a metatype.
    # Every type's fields must read as a type's; one that does not is a finding, never skipped.
    start = image.base
    cands = {}
    for addr in range(start, start + len(image.mem) - TYPE_SIZE, 4):
        w = image.words(addr, TYPE_SIZE // 4)
        if w[0] != STATIC_REFCNT:
            continue
        name = cstring(image, w[3])
        if name:
            cands[addr] = (name, w)
    selfref = [a for a, (_, w) in cands.items() if w[1] == a]
    if len(selfref) != 1:
        findings.append(f"{len(selfref)} candidates for `type` (an object whose type is itself)")
    meta = set(selfref)
    while True:
        new = {
            a
            for a, (_, w) in cands.items()
            if a not in meta
            and (w[1] == 0 or w[1] in meta)
            and (w[4] >= TYPE_SIZE or w[32] in meta)
        }
        if not new:
            break
        meta |= new
    cov["metatypes"] = len(meta)
    types = []
    for addr, (name, w) in cands.items():
        if addr not in refs:
            cov["type look-alikes unreferenced"] += 1
            continue
        if not (w[1] == 0 or w[1] in meta):
            continue
        bad = [f for off, (f, _) in TYPE_FUNCS.items() if w[off // 4] and w[off // 4] not in el]
        # bss (an empty table) lies past the image, so a pointer need only be in static memory
        bad += [
            f
            for off, f in TYPE_PTRS.items()
            if w[off // 4] and not image.base <= w[off // 4] < 1 << 31
        ]
        if w[4] >= 1 << 20 or w[5] >= 1 << 16:
            bad.append("tp_basicsize or tp_itemsize")
        if bad:
            findings.append(f"type {name}: does not read as a type ({', '.join(bad)})")
            continue
        types.append((addr, name, w))
    cov["static types"] = len(types)
    for _addr, name, w in types:
        for off, (field, want) in TYPE_FUNCS.items():
            check("type", name, field, w[off // 4], want)
        for off, suite in (
            (40, "tp_as_async"),
            (48, "tp_as_number"),
            (52, "tp_as_sequence"),
            (56, "tp_as_mapping"),
            (80, "tp_as_buffer"),
        ):
            p = w[off // 4]
            if not p:
                continue
            fields = SUITES[suite]
            sw = image.words(p, len(fields))
            if sw is None:  # past the image: zero-filled at load, no function to check
                cov[suite + " in bss"] += 1
                continue
            cov[suite] += 1
            for (field, want), v in zip(fields, sw, strict=False):
                check("type", name, field, v, want)
        for off, field in TYPE_RUNTIME.items():
            if w[off // 4]:
                cov[f"nonzero {field}"] += 1

    # 2. PyType_Spec -> PyType_Slot arrays
    specs = 0
    for addr in range(start, start + len(image.mem) - 20, 4):
        name_p, basicsize, itemsize, flags, slots_p = image.words(addr, 5)
        if addr not in refs:
            continue
        name = cstring(image, name_p)
        if not name or not slots_p or not image.has(slots_p, 8):
            continue
        if basicsize >= 1 << 20 or itemsize >= 1 << 16:
            continue

        def readable(sw):
            return (
                sw is not None and sw[0] in SLOT_IDS and (SLOT_IDS[sw[0]][1] is None or sw[1] in el)
            )

        # A spec is a record whose slots pointer starts a readable entry; from there the whole
        # run must read to its zero end, or it is a finding.
        if not readable(image.words(slots_p, 2)):
            continue
        entries = []
        p = slots_p
        good = True
        while True:
            sw = image.words(p, 2)
            if sw is not None and sw[0] == 0:
                break
            if not readable(sw) or len(entries) > 120:
                findings.append(f"spec {name}: slot entry {len(entries)} unreadable ({sw})")
                good = False
                break
            fname, want = SLOT_IDS[sw[0]]
            entries.append((fname, sw[1], want))
            p += 8
        if not good:
            continue
        specs += 1
        cov["slot entries"] += len(entries)
        for fname, pf, want in entries:
            check("spec", name, fname, pf, want)
    cov["specs"] = specs

    # 3. static PyModuleDefs: m_traverse, m_clear, m_free and the m_slots array
    mod_slots = {
        1: ("Py_mod_create", BINARY),
        84: ("Py_mod_create", BINARY),
        2: ("Py_mod_exec", INQUIRY),
        85: ("Py_mod_exec", INQUIRY),
        3: ("Py_mod_multiple_interpreters", None),
        86: ("Py_mod_multiple_interpreters", None),
        4: ("Py_mod_gil", None),
        87: ("Py_mod_gil", None),
        109: ("Py_mod_abi", None),
        110: ("Py_mod_token", None),
    }
    mods = 0
    for addr in range(start, start + len(image.mem) - 52, 4):
        w = image.words(addr, 13)
        if w[0] != STATIC_REFCNT or w[1] or w[2] or w[3] or w[4]:
            continue
        name = cstring(image, w[5])
        if not name:
            continue
        if addr not in refs:
            cov["module def look-alikes unreferenced"] += 1
            continue
        bad = [
            f
            for f, v in zip(("m_traverse", "m_clear", "m_free"), w[10:13], strict=True)
            if v and v not in el
        ]
        bad += [
            f
            for f, v in (("m_methods", w[8]), ("m_slots", w[9]))
            if v and not image.base <= v < 1 << 31
        ]
        if bad:
            findings.append(f"module {name}: does not read as a PyModuleDef ({', '.join(bad)})")
            continue
        slots = []
        p = w[9]
        while p:
            sw = image.words(p, 2)
            if sw is None and p == w[9]:  # past the image: zero at load (empty, or filled by code)
                cov["module slot arrays past the image"] += 1
                break
            if sw is None or (sw[0] and sw[0] not in mod_slots):
                findings.append(f"module {name}: slot entry {(p - w[9]) // 8} unreadable ({sw})")
                break
            if sw[0] == 0:
                break
            slots.append((mod_slots[sw[0]], sw[1]))
            p += 8
        mods += 1
        check("module", name, "m_traverse", w[10], TERNARY)
        check("module", name, "m_clear", w[11], INQUIRY)
        check("module", name, "m_free", w[12], DESTRUCTOR)
        for (sname, want), v in slots:
            check("module", name, sname, v, want)
    cov["module defs"] = mods

    for f in sorted(set(findings)):
        print("FINDING", f)
    print("coverage", dict(cov))


if __name__ == "__main__":
    main(sys.argv[1])
