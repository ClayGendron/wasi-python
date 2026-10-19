#!/usr/bin/env python3
"""Decide whether two builds of one WebAssembly binary are "the same bytes" (spec 037, Decision 17).

They are when they are byte for byte equal, or when the only difference is where the
`try_table` blocks of the functions named in recipes/same_bytes_exceptions.toml open: the pinned
clang (wasi-sdk 33) places them by heap address in a few of ducc0's functions. The rules, as the
decision numbers them:

1. the recipe's toolchain and scipy pin are scripts/line.conf's and downloads/SHA256SUMS';
2. every section but the code section is byte for byte equal;
3. the code sections hold as many bodies, and only bodies of the recipe's functions differ, each
   name matching exactly one function in the name section;
4. each differing body decodes with the decoder below, which fails closed;
5. every `try_table` has the empty block type, and no branch or catch label targets one;
6. the locals are equal, the bodies are as long, and with only the `try_table` instructions
   deleted (every `end` kept) the bytes are identical;
7. with every `try_table` and its `end` deleted and labels made absolute, the instructions are
   equal;
8. every instruction has the same effective handler chain: the `try_table`s around it,
   innermost first, each clause's kind, tag and absolute target, cut after the first catch-all.

Standard library only. Usage: uv run python scripts/same_bytes.py A.wasm B.wasm [--as python.wasm]
(the artifact's name in the set, which the recipe names; A's own name by default).
Exit status 0 when they are the same bytes, 1 (with one line per failure) when not.
"""

from __future__ import annotations

import hashlib
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECIPE = Path("recipes/same_bytes_exceptions.toml")
CODE = 10
CUSTOM = 0
IMPORT = 2


class Refused(Exception):
    """A failed rule: `rule` is its number in the decision, the message says where."""

    def __init__(self, rule: int, message: str) -> None:
        super().__init__(f"rule {rule}: {message}")
        self.rule = rule


# ---------------------------------------------------------------------------------------------
# The recipe (rule 1)


@dataclass(frozen=True)
class Exception_:
    obj: str
    wasi_sdk_version: str
    llvm_commit: str
    source: str
    source_sha256: str
    compile_command_sha256: str
    artifacts: tuple[str, ...]
    functions: tuple[str, ...]


def line_conf(root: Path) -> dict[str, str]:
    out = {}
    for line in (root / "scripts" / "line.conf").read_text().splitlines():
        if line and not line.startswith("#"):
            name, _, value = line.partition("=")
            out[name] = value
    return out


def pins(root: Path) -> dict[str, str]:
    out = {}
    for line in (root / "downloads" / "SHA256SUMS").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            digest, name = line.split(maxsplit=1)
            out[name.lstrip("*")] = digest
    return out


def compile_command_sha256(command: str, root: Path) -> str:
    """The SHA-256 of a compile command as compile_commands.json records it, with the checkout's
    absolute path written `@ROOT@`, so one command hashes alike in any checkout and on any host."""
    return hashlib.sha256(command.replace(str(root), "@ROOT@").encode()).hexdigest()


def load_recipe(root: Path = ROOT, path: Path | None = None) -> list[Exception_]:
    """The recipe's exceptions, each refused (rule 1) unless it holds for this checkout's line:
    the release gate binds the toolchain itself, not only the lane's still-needed check."""
    data = tomllib.loads((path or root / RECIPE).read_text())
    conf, pinned = line_conf(root), pins(root)
    out = []
    for e in data.get("exception", []):
        ex = Exception_(
            obj=e["object"],
            wasi_sdk_version=str(e["wasi_sdk_version"]),
            llvm_commit=e["llvm_commit"],
            source=e["source"],
            source_sha256=e["source_sha256"],
            compile_command_sha256=e["compile_command_sha256"],
            artifacts=tuple(e["artifacts"]),
            functions=tuple(e["functions"]),
        )
        for what, have, want in (
            ("WASI_SDK_VERSION", ex.wasi_sdk_version, conf.get("WASI_SDK_VERSION")),
            ("LLVM_COMMIT", ex.llvm_commit, conf.get("LLVM_COMMIT")),
            (f"the pin of {ex.source}", ex.source_sha256, pinned.get(ex.source)),
        ):
            if have != want:
                raise Refused(1, f"the exception for {ex.obj} names {what} {have}, the line {want}")
        out.append(ex)
    return out


# ---------------------------------------------------------------------------------------------
# Reading bytes, failing closed (rule 4)


class Reader:
    def __init__(self, data: bytes, pos: int = 0, end: int | None = None) -> None:
        self.data, self.pos = data, pos
        self.end = len(data) if end is None else end

    def byte(self) -> int:
        if self.pos >= self.end:
            raise Refused(4, f"truncated at byte {self.pos}")
        b = self.data[self.pos]
        self.pos += 1
        return b

    def take(self, n: int) -> bytes:
        if self.pos + n > self.end:
            raise Refused(4, f"truncated at byte {self.pos}")
        out = self.data[self.pos : self.pos + n]
        self.pos += n
        return out

    def leb(self, bits: int, signed: bool) -> int:
        start, value, shift = self.pos, 0, 0
        for _ in range((bits + 6) // 7):
            b = self.byte()
            value |= (b & 0x7F) << shift
            shift += 7
            if not b & 0x80:
                break
        else:
            raise Refused(4, f"a LEB longer than {(bits + 6) // 7} bytes at byte {start}")
        if signed:
            if value & (1 << (shift - 1)):
                value -= 1 << shift
            if not -(1 << (bits - 1)) <= value < 1 << (bits - 1):
                raise Refused(4, f"a LEB out of range for s{bits} at byte {start}")
        elif value >= 1 << bits:
            raise Refused(4, f"a LEB out of range for u{bits} at byte {start}")
        return value

    def u32(self) -> int:
        return self.leb(32, False)

    def name(self) -> str:
        return self.take(self.u32()).decode("utf-8", errors="surrogateescape")


# ---------------------------------------------------------------------------------------------
# Modules: sections, imports, names, bodies (rules 2 and 3)


@dataclass
class Module:
    data: bytes
    sections: list[tuple[int, int, int, int]]  # (id, header start, payload start, end)
    bodies: list[tuple[int, int]] = field(default_factory=list)  # (content start, end)
    imported_funcs: int = 0
    names: dict[int, str] = field(default_factory=dict)

    def body(self, k: int) -> bytes:
        s, e = self.bodies[k]
        return self.data[s:e]

    def non_code(self) -> list[tuple[int, bytes]]:
        return [(sid, self.data[h:e]) for sid, h, _, e in self.sections if sid != CODE]


def _limits(r: Reader) -> None:
    flags = r.byte()
    r.leb(64, False)
    if flags & 1:
        r.leb(64, False)


def _reftype_or_valtype(r: Reader) -> None:
    if r.byte() in (0x63, 0x64):
        r.leb(33, True)


def parse(data: bytes) -> Module:
    if data[:8] != b"\0asm\x01\0\0\0":
        raise Refused(2, "not a WebAssembly module")
    r = Reader(data, 8)
    mod = Module(data, [])
    while r.pos < r.end:
        header = r.pos
        sid = r.byte()
        size = r.u32()
        start = r.pos
        r.take(size)
        mod.sections.append((sid, header, start, r.pos))
    for sid, _, start, end in mod.sections:
        s = Reader(data, start, end)
        if sid == IMPORT:
            for _ in range(s.u32()):
                s.name()
                s.name()
                kind = s.byte()
                if kind == 0:
                    s.u32()
                    mod.imported_funcs += 1
                elif kind == 1:
                    _reftype_or_valtype(s)
                    _limits(s)
                elif kind == 2:
                    _limits(s)
                elif kind == 3:
                    _reftype_or_valtype(s)
                    s.byte()
                elif kind == 4:
                    s.byte()
                    s.u32()
                else:
                    raise Refused(2, f"an import of kind {kind}")
        elif sid == CODE:
            for _ in range(s.u32()):
                size = s.u32()
                mod.bodies.append((s.pos, s.pos + size))
                s.take(size)
            if s.pos != end:
                raise Refused(3, "the code section has bytes after its bodies")
        elif sid == CUSTOM and s.name() == "name":
            while s.pos < end:
                sub = s.byte()
                sub_end = s.u32() + s.pos
                if sub == 1:
                    for _ in range(s.u32()):
                        index = s.u32()
                        mod.names[index] = s.name()
                s.pos = sub_end
    return mod


# ---------------------------------------------------------------------------------------------
# The decoder (rule 4): every opcode wasi-sdk 33 emits for the line's features, nothing else.

BLOCK, LOOP, IF, ELSE, END, TRY_TABLE = 0x02, 0x03, 0x04, 0x05, 0x0B, 0x1F
BR, BR_IF, BR_TABLE = 0x0C, 0x0D, 0x0E
LEGACY_EH = {0x06: "try", 0x07: "catch", 0x09: "rethrow", 0x18: "delegate", 0x19: "catch_all"}
NO_IMMEDIATE = {0x00, 0x01, 0x05, 0x0A, 0x0B, 0x0F, 0x1A, 0x1B, 0xD1, *range(0x45, 0xC5)}
ONE_INDEX = {0x08, 0x0C, 0x0D, 0x10, 0x12, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0xD2}
VALTYPES = {0x7F, 0x7E, 0x7D, 0x7C, 0x7B, 0x70, 0x6F, 0x69}
EMPTY = 0x40
CATCH_ALL_KINDS = {2, 3}  # catch_all, catch_all_ref
CALLS = {0x08, 0x0A, 0x10, 0x11, 0x12, 0x13}  # throw, throw_ref and the calls


@dataclass(frozen=True)
class Insn:
    start: int  # offset in the body, locals included
    end: int
    op: int | tuple[int, int]
    args: tuple = ()


def _blocktype(r: Reader) -> tuple:
    b = r.data[r.pos] if r.pos < r.end else None
    if b == EMPTY or b in VALTYPES:
        r.pos += 1
        return (b,)
    if b in (0x63, 0x64):
        r.pos += 1
        return (b, r.leb(33, True))
    index = r.leb(33, True)
    if index < 0:
        raise Refused(4, f"a block type {b:#x} at byte {r.pos}")
    return ("type", index)


def _memarg(r: Reader) -> tuple[int, int]:
    align = r.u32()
    if align & 0x40:
        raise Refused(4, f"a multi-memory memarg at byte {r.pos}")
    return align, r.u32()


def _fc(r: Reader, sub: int) -> tuple:
    if sub <= 7:
        return ()
    if sub in (8, 10, 12, 14):
        return (r.u32(), r.u32())
    if sub in (9, 11, 13, 15, 16, 17):
        return (r.u32(),)
    raise Refused(4, f"opcode 0xfc {sub} at byte {r.pos}")


def _fd(r: Reader, sub: int) -> tuple:
    if sub <= 0x0B or sub in (0x5C, 0x5D):
        return _memarg(r)
    if sub in (0x0C, 0x0D):
        return (r.take(16),)
    if 0x15 <= sub <= 0x22:
        return (r.byte(),)
    if 0x54 <= sub <= 0x5B:
        return (*_memarg(r), r.byte())
    if 0x0E <= sub <= 0xFF:
        return ()
    raise Refused(4, f"opcode 0xfd {sub} at byte {r.pos}")


def decode(body: bytes) -> tuple[int, list[Insn]]:
    """The body's locals' end and its instructions. Refuses (rule 4) an unknown opcode, a LEB
    too long or out of range, a read past the body, a stray `else`, and a control stack that is
    not empty exactly at the body's last byte."""
    r = Reader(body)
    for _ in range(r.u32()):
        r.u32()
        _reftype_or_valtype(r)
    locals_end = r.pos
    out: list[Insn] = []
    depth: list[int] = []  # the open block kinds
    while True:
        if r.pos >= r.end:
            raise Refused(4, "the body ends inside a block (an unbalanced end)")
        start = r.pos
        op = r.byte()
        if op in LEGACY_EH:
            raise Refused(4, f"the legacy EH opcode {LEGACY_EH[op]} at byte {start}")
        if op == 0xFE:
            raise Refused(4, f"an atomics opcode at byte {start}")
        if op in NO_IMMEDIATE:
            args: tuple = ()
        elif op in (BLOCK, LOOP, IF):
            args = (_blocktype(r),)
        elif op == TRY_TABLE:
            bt = _blocktype(r)
            clauses = []
            for _ in range(r.u32()):
                kind = r.byte()
                if kind in (0, 1):
                    clauses.append((kind, r.u32(), r.u32()))
                elif kind in CATCH_ALL_KINDS:
                    clauses.append((kind, None, r.u32()))
                else:
                    raise Refused(4, f"a catch clause of kind {kind} at byte {start}")
            args = (bt, tuple(clauses))
        elif op in ONE_INDEX:
            args = (r.u32(),)
        elif op == BR_TABLE:
            args = (tuple(r.u32() for _ in range(r.u32() + 1)),)
        elif op in (0x11, 0x13):
            args = (r.u32(), r.u32())
        elif op == 0x1C:
            args = (tuple(_one_valtype(r) for _ in range(r.u32())),)
        elif 0x28 <= op <= 0x3E:
            args = _memarg(r)
        elif op in (0x3F, 0x40):
            args = (r.u32(),)
        elif op == 0x41:
            args = (r.leb(32, True),)
        elif op == 0x42:
            args = (r.leb(64, True),)
        elif op == 0x43:
            args = (r.take(4),)
        elif op == 0x44:
            args = (r.take(8),)
        elif op == 0xD0:
            args = (_heaptype(r),)
        elif op in (0xFC, 0xFD):
            sub = r.u32()
            args = _fc(r, sub) if op == 0xFC else _fd(r, sub)
            op = (op, sub)
        else:
            raise Refused(4, f"opcode {op:#x} at byte {start}")
        out.append(Insn(start, r.pos, op, args))
        if op in (BLOCK, LOOP, IF, TRY_TABLE):
            depth.append(op)
        elif op == ELSE:
            if not depth or depth[-1] != IF:
                raise Refused(4, f"an else outside an if at byte {start}")
            depth[-1] = ELSE
        elif op == END:
            if not depth:
                if r.pos != r.end:
                    raise Refused(4, f"the function's end at byte {start} is not its last byte")
                return locals_end, out
            depth.pop()


def _one_valtype(r: Reader) -> int | tuple[int, int]:
    b = r.byte()
    if b in (0x63, 0x64):
        return (b, r.leb(33, True))
    if b not in VALTYPES:
        raise Refused(4, f"a value type {b:#x} at byte {r.pos - 1}")
    return b


def _heaptype(r: Reader) -> int:
    return r.leb(33, True)


# ---------------------------------------------------------------------------------------------
# One body's structure (rules 5, 7, 8)


@dataclass
class Shape:
    locals_end: int
    stripped: bytes  # the body without its try_table instructions (rule 6)
    tries: int
    sequence: list[tuple]  # rule 7
    handlers: list[tuple]  # rule 8, one per entry of sequence


def shape(body: bytes) -> Shape:
    locals_end, insns = decode(body)
    stripped = bytearray(body[:locals_end])
    stack: list[tuple[str, object, tuple]] = []  # (kind, absolute id, clauses)
    sequence: list[tuple] = []
    handlers: list[tuple] = []
    next_id = tries = 0

    def target(label: int, frames: list, where: int) -> object:
        if label == len(frames):
            return "function"
        if label > len(frames):
            raise Refused(4, f"label {label} out of range at byte {where}")
        kind, ident, _ = frames[-1 - label]
        if kind == "try":
            raise Refused(5, f"a label targets a try_table at byte {where}")
        return ident

    def chain() -> tuple:
        out = []
        for kind, _, clauses in reversed(stack):
            if kind == "try":
                out.append(clauses)
                if any(k in CATCH_ALL_KINDS for k, _, _ in clauses):
                    break
        return tuple(out)

    for insn in insns:
        op = insn.op
        if op == TRY_TABLE:
            bt, clauses = insn.args
            if bt != (EMPTY,):
                raise Refused(5, f"a try_table with a block type at byte {insn.start}")
            resolved = tuple((k, tag, target(lab, stack, insn.start)) for k, tag, lab in clauses)
            stack.append(("try", None, resolved))
            tries += 1
            continue
        stripped += body[insn.start : insn.end]
        if op == END and stack and stack[-1][0] == "try":
            stack.pop()
            continue
        if op in (BLOCK, LOOP, IF):
            entry: tuple = (op, insn.args, next_id)
        elif op == END:
            entry = (END, stack[-1][1] if stack else "function")
        elif op == ELSE:
            entry = (ELSE, stack[-1][1])
        elif op in (BR, BR_IF):
            entry = (op, target(insn.args[0], stack, insn.start))
        elif op == BR_TABLE:
            entry = (op, tuple(target(lab, stack, insn.start) for lab in insn.args[0]))
        else:
            entry = (op, insn.args)
        sequence.append(entry)
        handlers.append(chain())
        if op in (BLOCK, LOOP, IF):
            stack.append(("block", next_id, ()))
            next_id += 1
        elif op == END and stack:
            stack.pop()
    return Shape(locals_end, bytes(stripped), tries, sequence, handlers)


def compare_bodies(a: bytes, b: bytes) -> None:
    """Refuses unless two differing bodies meet rules 4 to 8."""
    sa, sb = shape(a), shape(b)
    if a[: sa.locals_end] != b[: sb.locals_end]:
        raise Refused(6, "the local declarations differ")
    if len(a) != len(b):
        raise Refused(6, f"the bodies are {len(a)} and {len(b)} bytes long")
    if sa.stripped != sb.stripped:
        at = next(
            (i for i, (x, y) in enumerate(zip(sa.stripped, sb.stripped, strict=False)) if x != y),
            min(len(sa.stripped), len(sb.stripped)),
        )
        raise Refused(6, f"without the try_tables the bytes differ at stripped byte {at}")
    if sa.sequence != sb.sequence:
        at = next(
            i for i, (x, y) in enumerate(zip(sa.sequence, sb.sequence, strict=False)) if x != y
        )
        raise Refused(7, f"instruction {at} differs: {sa.sequence[at]} and {sb.sequence[at]}")
    moved = [i for i, (x, y) in enumerate(zip(sa.handlers, sb.handlers, strict=True)) if x != y]
    if moved:
        calls = sum(1 for i in moved if sa.sequence[i][0] in CALLS)
        i = moved[0]
        raise Refused(
            8,
            f"{len(moved)} instructions ({calls} of them calls or throws) have another effective "
            f"handler chain; the first, instruction {i}, {sa.handlers[i]} and {sb.handlers[i]}",
        )


# ---------------------------------------------------------------------------------------------
# Two binaries (rules 2 and 3, then each differing body)


def compare(a: bytes, b: bytes, functions: tuple[str, ...]) -> list[str]:
    """The names of the recipe functions whose bodies differ when `a` and `b` are the same bytes
    under the rules; refuses otherwise. `functions` is the recipe's list for this artifact."""
    if a == b:
        return []
    ma, mb = parse(a), parse(b)
    if ma.non_code() != mb.non_code():
        differ = sorted(
            {sid for (sid, x), (_, y) in zip(ma.non_code(), mb.non_code(), strict=False) if x != y}
            | ({-1} if len(ma.non_code()) != len(mb.non_code()) else set())
        )
        raise Refused(2, f"a section other than code differs (ids {differ})")
    if len(ma.bodies) != len(mb.bodies):
        raise Refused(3, f"{len(ma.bodies)} and {len(mb.bodies)} function bodies")
    by_name: dict[str, list[int]] = {}
    for index, name in ma.names.items():
        by_name.setdefault(name, []).append(index)
    allowed = {}
    for name in functions:
        found = by_name.get(name, [])
        if len(found) != 1:
            raise Refused(3, f"{len(found)} functions are named {name}")
        allowed[found[0] - ma.imported_funcs] = name
    named = []
    for k in range(len(ma.bodies)):
        x, y = ma.body(k), mb.body(k)
        if x == y:
            continue
        name = allowed.get(k)
        if name is None:
            label = ma.names.get(k + ma.imported_funcs, f"#{k + ma.imported_funcs}")
            raise Refused(3, f"the body of {label}, which the recipe does not name, differs")
        try:
            compare_bodies(x, y)
        except Refused as e:
            raise Refused(e.rule, f"{name}: {e}") from None
        named.append(name)
    return named


def compare_files(a: Path, b: Path, artifact: str, root: Path = ROOT) -> list[str]:
    """`compare` with the recipe's functions for `artifact`, the recipe checked first (rule 1)."""
    if a.read_bytes() == b.read_bytes():
        return []
    functions = tuple(
        name for e in load_recipe(root) if artifact in e.artifacts for name in e.functions
    )
    if not functions:
        raise Refused(3, f"{artifact} differs and no exception names it")
    return compare(a.read_bytes(), b.read_bytes(), functions)


def main(argv: list[str]) -> int:
    artifact = None
    if len(argv) == 4 and argv[2] == "--as":
        artifact, argv = argv[3], argv[:2]
    if len(argv) != 2:
        print("usage: uv run python scripts/same_bytes.py A.wasm B.wasm [--as python.wasm]")
        return 2
    a, b = map(Path, argv)
    try:
        named = compare_files(a, b, artifact or a.name)
    except Refused as e:
        print(f"{a.name}: not the same bytes: {e}")
        return 1
    if named:
        print(f"{a.name}: the same bytes but where {len(named)} named functions open a try_table:")
        for name in named:
            print(f"  {name}")
    else:
        print(f"{a.name}: the same bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
