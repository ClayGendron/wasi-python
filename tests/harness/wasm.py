"""Read a core wasm module's function types, imports and exports, without an engine.

Enough of the binary format (WebAssembly core spec, chapter 5) to judge the wall: which modules
the guest imports from, with which function types, what it exports, and which sections it has
(a tag section, id 13, is where the exception-handling proposal defines its exception tags).
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
        elif section == 7:
            for _ in range(s.u32()):
                name, kind = s.name(), s.byte()
                s.u32()
                mod.exports[name] = KINDS.get(kind, f"kind{kind}")
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
