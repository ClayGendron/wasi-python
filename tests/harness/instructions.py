"""Read a core wasm module's function bodies instruction by instruction, without an engine.

Enough of the binary format's instructions (WebAssembly core spec, chapter 5.4, with the SIMD,
exception-handling, reference-types, bulk-memory and tail-call proposals the build's features
allow) to say what each function calls directly, which functions it names by `ref.func`, and
whether it grows the memory. Every immediate is decoded, so a byte inside an immediate is never
read as an opcode; an opcode outside these is a `WasmError`, never skipped."""

from __future__ import annotations

from dataclasses import dataclass, field

from harness.wasm import Module, WasmError, _Reader, bodies

# Opcodes with no immediate: control and parametric ones, then every numeric opcode.
_PLAIN = {0x00, 0x01, 0x05, 0x0A, 0x0B, 0x0F, 0x19, 0x1A, 0x1B, 0xD1, 0xD3, 0xD5}
_PLAIN |= set(range(0x45, 0xC5))
_BLOCKS = {0x02, 0x03, 0x04, 0x06}  # block, loop, if, try: a block type
_INDEX = {0x07, 0x08, 0x09, 0x0C, 0x0D, 0x18, 0x14, 0x15, 0xD4, 0xD6}  # one index
_INDEX |= {0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26}  # locals, globals, tables
_MEMARG = set(range(0x28, 0x3F))  # loads and stores
_SIMD_MEMARG = set(range(0, 12)) | {92, 93}
_SIMD_LANE = set(range(21, 35))
_SIMD_MEMARG_LANE = set(range(84, 92))


@dataclass
class Body:
    calls: set[int] = field(default_factory=set)  # call and return_call targets
    refs: set[int] = field(default_factory=set)  # ref.func targets
    grows: bool = False  # memory.grow


def _signed(s: _Reader) -> None:
    """Skip a signed LEB128 of any length (a block type's s33, an i32 or i64 constant)."""
    while s.byte() & 0x80:
        pass


def _memarg(s: _Reader) -> None:
    align = s.u32()
    if align & 0x40:  # multi-memory: a memory index follows
        s.u32()
    s.u32()  # the offset


def _locals(s: _Reader) -> None:
    for _ in range(s.u32()):
        s.u32()
        t = s.byte()
        if t in (0x63, 0x64):  # (ref null ht), (ref ht): a heap type follows
            _signed(s)


def _prefixed(s: _Reader, op: int, out: Body) -> None:
    sub = s.u32()
    if op == 0xFC:
        if sub <= 7 or sub in (13, 9):  # saturating truncations; elem.drop, data.drop: below
            if sub in (13, 9):
                s.u32()
        elif sub in (8, 12, 14):  # memory.init, table.init, table.copy: two indices
            s.u32()
            s.u32()
        elif sub in (10,):  # memory.copy: two memory indices
            s.u32()
            s.u32()
        elif sub in (11, 15, 16, 17):  # memory.fill, table.grow, table.size, table.fill
            s.u32()
        else:
            raise WasmError(f"unknown 0xFC instruction {sub}")
    elif op == 0xFD:
        if sub in _SIMD_MEMARG:
            _memarg(s)
        elif sub in (12, 13):  # v128.const, i8x16.shuffle: sixteen bytes
            for _ in range(16):
                s.byte()
        elif sub in _SIMD_LANE:
            s.byte()
        elif sub in _SIMD_MEMARG_LANE:
            _memarg(s)
            s.byte()
        elif sub > 0x113:
            raise WasmError(f"unknown SIMD instruction {sub}")
    elif op == 0xFE:
        if sub == 0x03:  # atomic.fence
            s.byte()
        else:
            _memarg(s)
    else:
        raise WasmError(f"unknown prefix 0x{op:02x}")


def read_body(body: bytes) -> Body:
    """What one function body calls, names and does to the memory."""
    out = Body()
    s = _Reader(body)
    _locals(s)
    while s.pos < s.end:
        op = s.byte()
        if op in _PLAIN:
            continue
        if op in _BLOCKS:
            _signed(s)
        elif op in (0x10, 0x12):  # call, return_call
            out.calls.add(s.u32())
        elif op in (0x11, 0x13):  # call_indirect, return_call_indirect: type, table
            s.u32()
            s.u32()
        elif op in _INDEX:
            s.u32()
        elif op == 0x0E:  # br_table
            for _ in range(s.u32() + 1):
                s.u32()
        elif op == 0x1C:  # select with types
            for _ in range(s.u32()):
                s.byte()
        elif op == 0x1F:  # try_table: a block type and its catches
            _signed(s)
            for _ in range(s.u32()):
                kind = s.byte()
                if kind in (0x00, 0x01):
                    s.u32()
                s.u32()
        elif op in _MEMARG:
            _memarg(s)
        elif op == 0x3F:  # memory.size
            s.u32()
        elif op == 0x40:  # memory.grow
            s.u32()
            out.grows = True
        elif op in (0x41, 0x42):
            _signed(s)
        elif op == 0x43:
            s.pos += 4
        elif op == 0x44:
            s.pos += 8
        elif op == 0xD0:  # ref.null
            _signed(s)
        elif op == 0xD2:  # ref.func
            out.refs.add(s.u32())
        elif op in (0xFC, 0xFD, 0xFE):
            _prefixed(s, op, out)
        else:
            raise WasmError(f"unknown opcode 0x{op:02x} at byte {s.pos - 1}")
    if s.pos != s.end:
        raise WasmError("a body's last instruction runs past its end")
    return out


def read_all(mod: Module) -> dict[int, Body]:
    """Every defined function's body, read."""
    return {index: read_body(body) for index, body in bodies(mod).items()}
