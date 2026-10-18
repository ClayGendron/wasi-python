"""Read a core wasm module's function types, imports and exports, without an engine.

Enough of the binary format (WebAssembly core spec, chapter 5) to judge the wall: which modules
the guest imports from, with which function types, what it exports, and which sections it has
(a tag section, id 13, is where the exception-handling proposal defines its exception tags).

For the callback scan (spec 051, `harness/callbacks.py`) it also reads the function section
(each defined function's type), the element section (the table index a C function pointer
holds), the data section (the static memory image), the code section's bytes, and the function
names of the name section when present. An element segment in any form but an active `funcref`
list for table 0, or a data segment that is passive or not placed by one `i32.const` (an
extended constant expression included), is recorded in `Module.unread` rather than skipped in
silence, so a reader of the image can never pass by reading less, and the other readers still
read the module. Only a constant-expression opcode outside the extended-constant proposal stops
every reader, since its segment's end cannot be found.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MAGIC = b"\0asm"
CORE_VERSION = b"\x01\0\0\0"

KINDS = {0: "func", 1: "table", 2: "memory", 3: "global", 4: "tag"}
TAG_SECTION = 13
START_SECTION = 8  # a start function runs guest code at instantiation
VALTYPES = {0x7F: "i32", 0x7E: "i64", 0x7D: "f32", 0x7C: "f64", 0x7B: "v128"}


class WasmError(ValueError):
    """The bytes are not a core wasm module this reader understands."""


@dataclass(frozen=True)
class FuncType:
    params: tuple[str, ...]
    results: tuple[str, ...]

    def __str__(self) -> str:
        return f"({', '.join(self.params)}) -> ({', '.join(self.results)})"


@dataclass(frozen=True)
class Import:
    module: str
    name: str
    kind: str
    type: FuncType | None  # for functions


@dataclass
class Module:
    types: list[FuncType] = field(default_factory=list)
    imports: list[Import] = field(default_factory=list)
    exports: dict[str, str] = field(default_factory=dict)  # name -> kind
    sections: set[int] = field(default_factory=set)  # the ids of the sections present
    funcs: list[int] = field(default_factory=list)  # each defined function's type index
    elements: dict[int, int] = field(default_factory=dict)  # table index -> function index
    data: list[tuple[int, bytes]] = field(default_factory=list)  # active segments: (address, bytes)
    code: bytes = b""  # the code section's bytes, as they are
    names: dict[int, str] = field(default_factory=dict)  # function index -> name (name section)
    unread: list[str] = field(default_factory=list)  # element or data segments not read, and why

    def func_type(self, index: int) -> FuncType | None:
        """The type of a function by its index: imported functions first, then defined ones."""
        imported = [i.type for i in self.imports if i.kind == "func"]
        if index < len(imported):
            return imported[index]
        k = index - len(imported)
        return self.types[self.funcs[k]] if 0 <= k < len(self.funcs) else None


class _Reader:
    def __init__(self, data: bytes, pos: int = 0, end: int | None = None) -> None:
        self.data, self.pos, self.end = data, pos, len(data) if end is None else end

    def byte(self) -> int:
        if self.pos >= self.end:
            raise WasmError("unexpected end of module")
        b = self.data[self.pos]
        self.pos += 1
        return b

    def u32(self) -> int:
        result = shift = 0
        while True:
            b = self.byte()
            result |= (b & 0x7F) << shift
            if not b & 0x80:
                return result
            shift += 7
            if shift > 35:
                raise WasmError("LEB128 integer too long")

    def name(self) -> str:
        n = self.u32()
        if self.pos + n > self.end:
            raise WasmError("name runs past its section")
        raw = self.data[self.pos : self.pos + n]
        self.pos += n
        try:
            return raw.decode()
        except UnicodeDecodeError as e:
            raise WasmError("name is not UTF-8") from e

    def valtype(self) -> str:
        b = self.byte()
        if b in VALTYPES:
            return VALTYPES[b]
        if b in (0x70, 0x6F):  # funcref, externref
            return "ref"
        if b == 0x69:  # exnref: the exception-handling proposal's standard form
            return "exnref"
        raise WasmError(f"unsupported value type 0x{b:02x}")

    def limits(self) -> None:
        flags = self.byte()
        self.u32()
        if flags & 1:
            self.u32()

    def s32(self) -> int:
        result = shift = 0
        while True:
            b = self.byte()
            result |= (b & 0x7F) << shift
            shift += 7
            if not b & 0x80:
                return result - (1 << shift) if b & 0x40 else result
            if shift > 35:
                raise WasmError("LEB128 integer too long")

    def const_i32(self) -> int | None:
        """A constant expression, read to its `end`: n for `i32.const n` alone; None for any
        other expression of the extended-constant proposal (`global.get`, `i32.add` …), whose
        value the image does not hold, so its segment is recorded as unread. An opcode outside
        those is an error: its operands, and so its `end`, cannot be found."""
        ops, value = [], None
        while True:
            op = self.byte()
            if op == 0x0B:
                break
            ops.append(op)
            if op == 0x41:
                value = self.s32()
            elif op == 0x42:  # i64.const: a LEB of up to ten bytes
                for _ in range(10):
                    if not self.byte() & 0x80:
                        break
                else:
                    raise WasmError("LEB128 integer too long")
            elif op == 0x23:
                self.u32()
            elif op not in (0x6A, 0x6B, 0x6C, 0x7C, 0x7D, 0x7E):  # i32/i64 add, sub, mul
                raise WasmError(f"unsupported constant expression (opcode 0x{op:02x})")
        return value if ops == [0x41] else None


def _elements(s: _Reader, mod: Module) -> None:
    """The element section: active funcref lists for table 0 fill `mod.elements`."""
    for n in range(s.u32()):
        flags = s.u32()
        if flags not in (0, 2):
            mod.unread.append(f"element segment {n}: form {flags}, not an active funcref list")
            return  # its layout differs; the rest of the section cannot be found without it
        table = s.u32() if flags == 2 else 0
        offset = s.const_i32()
        if flags == 2 and s.byte() != 0x00:
            mod.unread.append(f"element segment {n}: not a funcref list")
            return
        indices = [s.u32() for _ in range(s.u32())]
        if table != 0 or offset is None:
            why = f"table {table}" if table else "an offset that is not one i32.const"
            mod.unread.append(f"element segment {n}: {why}")
            continue
        for i, f in enumerate(indices):
            mod.elements[offset + i] = f


def _data(s: _Reader, mod: Module) -> None:
    """The data section: active segments placed by a constant fill `mod.data`."""
    for n in range(s.u32()):
        flags = s.u32()
        if flags not in (0, 1, 2):
            mod.unread.append(f"data segment {n}: form {flags}")
            return
        memory = s.u32() if flags == 2 else 0
        offset = s.const_i32() if flags != 1 else None
        size = s.u32()
        if s.pos + size > s.end:
            raise WasmError("data segment runs past its section")
        body = s.data[s.pos : s.pos + size]
        s.pos += size
        if flags == 1:
            mod.unread.append(f"data segment {n}: passive")
        elif memory != 0 or offset is None:
            why = f"memory {memory}" if memory else "an offset that is not one i32.const"
            mod.unread.append(f"data segment {n}: {why}")
        else:
            mod.data.append((offset, body))


def _names(s: _Reader, mod: Module) -> None:
    """The name section's function names (subsection 1); the other subsections are skipped."""
    while s.pos < s.end:
        sub = s.byte()
        size = s.u32()
        end = s.pos + size
        if sub == 1:
            for _ in range(s.u32()):
                index = s.u32()
                mod.names[index] = s.name()
        s.pos = end


def parse(data: bytes) -> Module:
    if data[:4] != MAGIC:
        raise WasmError("not a wasm binary (bad magic)")
    if data[4:8] != CORE_VERSION:
        raise WasmError(f"not a core module (version bytes {data[4:8].hex()})")
    mod = Module()
    r = _Reader(data, 8)
    while r.pos < r.end:
        section = r.byte()
        size = r.u32()
        start = r.pos
        if start + size > len(data):
            raise WasmError(f"section {section} runs past the end")
        s = _Reader(data, start, start + size)
        mod.sections.add(section)
        if section == 1:
            for _ in range(s.u32()):
                if s.byte() != 0x60:
                    raise WasmError("type section entry is not a function type")
                params = tuple(s.valtype() for _ in range(s.u32()))
                results = tuple(s.valtype() for _ in range(s.u32()))
                mod.types.append(FuncType(params, results))
        elif section == 2:
            for _ in range(s.u32()):
                module, name, kind = s.name(), s.name(), s.byte()
                ftype = None
                if kind == 0:
                    idx = s.u32()
                    if idx >= len(mod.types):
                        raise WasmError(f"import {module}::{name} names type {idx}, out of range")
                    ftype = mod.types[idx]
                elif kind == 1:
                    s.valtype()
                    s.limits()
                elif kind == 2:
                    s.limits()
                elif kind == 3:
                    s.valtype()
                    s.byte()
                elif kind == 4:
                    s.byte()
                    s.u32()
                else:
                    raise WasmError(f"import {module}::{name} has unknown kind {kind}")
                mod.imports.append(Import(module, name, KINDS[kind], ftype))
        elif section == 3:
            mod.funcs = [s.u32() for _ in range(s.u32())]
        elif section == 7:
            for _ in range(s.u32()):
                name, kind = s.name(), s.byte()
                s.u32()
                mod.exports[name] = KINDS.get(kind, f"kind{kind}")
        elif section == 9:
            _elements(s, mod)
        elif section == 10:
            mod.code = data[start : start + size]
        elif section == 11:
            _data(s, mod)
        elif section == 0 and s.name() == "name":
            _names(s, mod)
        r.pos = start + size
    return mod


def parse_file(path) -> Module:
    with open(path, "rb") as f:
        return parse(f.read())


DOOR_TYPE = FuncType(("i32", "i32", "i32", "i32"), ("i32",))
WASI = "wasi_snapshot_preview1"


def wall_errors(mod: Module) -> list[str]:
    """Constitution §4.4: imports only from WASI preview1 and `host::call` with the door's type."""
    errors = []
    for imp in mod.imports:
        if imp.module == WASI:
            continue
        if imp.module == "host" and imp.name == "call":
            if imp.kind != "func" or imp.type != DOOR_TYPE:
                errors.append(f"host::call has type {imp.type}, not {DOOR_TYPE}")
            continue
        errors.append(f"third import {imp.module}::{imp.name} ({imp.kind})")
    if not any(i.module == "host" and i.name == "call" for i in mod.imports):
        errors.append("no host::call import (the door)")
    return errors
