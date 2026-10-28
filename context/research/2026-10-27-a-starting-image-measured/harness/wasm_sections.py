"""A minimal reader of a wasm binary's sections: imports, exports, memories, globals, data.

Run: uv run --no-sync python harness/wasm_sections.py <module.wasm> [...]
It parses only what the memo needs and decodes only i32.const/i64.const global initialisers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

KINDS = {0: "func", 1: "table", 2: "memory", 3: "global", 4: "tag"}
VALTYPES = {0x7F: "i32", 0x7E: "i64", 0x7D: "f32", 0x7C: "f64", 0x7B: "v128", 0x70: "funcref", 0x6F: "externref"}


class Reader:
    def __init__(self, data: bytes, pos: int = 0, end: int | None = None) -> None:
        self.d, self.p, self.end = data, pos, len(data) if end is None else end

    def byte(self) -> int:
        b = self.d[self.p]
        self.p += 1
        return b

    def uleb(self) -> int:
        result = shift = 0
        while True:
            b = self.byte()
            result |= (b & 0x7F) << shift
            shift += 7
            if not b & 0x80:
                return result

    def sleb(self) -> int:
        result = shift = 0
        while True:
            b = self.byte()
            result |= (b & 0x7F) << shift
            shift += 7
            if not b & 0x80:
                if b & 0x40:
                    result -= 1 << shift
                return result

    def name(self) -> str:
        n = self.uleb()
        s = self.d[self.p : self.p + n].decode()
        self.p += n
        return s

    def limits(self) -> dict:
        flags = self.byte()
        lo = self.uleb()
        hi = self.uleb() if flags & 1 else None
        return {"min": lo, "max": hi, "flags": flags}

    def const_expr(self) -> object:
        op = self.byte()
        if op == 0x41:
            v: object = self.sleb()
        elif op == 0x42:
            v = self.sleb()
        elif op == 0x23:
            v = f"global.get {self.uleb()}"
        else:
            v = f"op 0x{op:02x}"
            while self.byte() != 0x0B:
                pass
            return v
        assert self.byte() == 0x0B
        return v


def sections(data: bytes) -> dict:
    assert data[:4] == b"\0asm"
    r = Reader(data, 8)
    out: dict = {"imports": [], "exports": [], "memories": [], "globals": [], "data": [], "sizes": {}, "customs": []}
    imported_globals = 0
    while r.p < len(data):
        sid = r.byte()
        size = r.uleb()
        start, end = r.p, r.p + size
        out["sizes"][sid] = out["sizes"].get(sid, 0) + size
        s = Reader(data, start, end)
        if sid == 0:
            out["customs"].append((s.name(), size))
        elif sid == 2:
            for _ in range(s.uleb()):
                mod, nm, kind = s.name(), s.name(), s.byte()
                if kind == 0:
                    s.uleb()
                elif kind == 1:
                    s.byte()
                    s.limits()
                elif kind == 2:
                    s.limits()
                elif kind == 3:
                    s.byte()
                    s.byte()
                    imported_globals += 1
                elif kind == 4:
                    s.byte()
                    s.uleb()
                out["imports"].append(f"{mod}.{nm} ({KINDS[kind]})")
        elif sid == 5:
            for _ in range(s.uleb()):
                out["memories"].append(s.limits())
        elif sid == 6:
            for i in range(s.uleb()):
                t, mut = s.byte(), s.byte()
                out["globals"].append(
                    {"index": imported_globals + i, "type": VALTYPES.get(t, hex(t)), "mutable": bool(mut), "init": s.const_expr()}
                )
        elif sid == 7:
            for _ in range(s.uleb()):
                nm, kind, idx = s.name(), s.byte(), s.uleb()
                out["exports"].append({"name": nm, "kind": KINDS[kind], "index": idx})
        elif sid == 11:
            for _ in range(s.uleb()):
                flags = s.uleb()
                offset = None
                if flags in (0, 2):
                    if flags == 2:
                        s.uleb()
                    offset = s.const_expr()
                n = s.uleb()
                out["data"].append({"offset": offset, "bytes": n})
                s.p += n
        r.p = end
    return out


def summary(path: Path) -> dict:
    data = path.read_bytes()
    s = sections(data)
    exported_globals = {e["index"]: e["name"] for e in s["exports"] if e["kind"] == "global"}
    return {
        "file": path.name,
        "bytes": len(data),
        "imports": s["imports"],
        "exports": [f'{e["name"]} ({e["kind"]})' for e in s["exports"]],
        "memories": s["memories"],
        "globals": [dict(g, exported_as=exported_globals.get(g["index"])) for g in s["globals"]],
        "data_segments": len(s["data"]),
        "data_bytes": sum(d["bytes"] for d in s["data"]),
        "data_extent": max((d["offset"] + d["bytes"]) for d in s["data"] if isinstance(d["offset"], int)) if s["data"] else 0,
        "section_bytes": {str(k): v for k, v in sorted(s["sizes"].items())},
        "custom_sections": s["customs"],
    }


if __name__ == "__main__":
    print(json.dumps([summary(Path(p)) for p in sys.argv[1:]], indent=1))


def with_global_exported(data: bytes, index: int, name: str) -> bytes:
    """The same module with one more export: global `index` as `name` (to read the stack pointer)."""

    def uleb(n: int) -> bytes:
        out = bytearray()
        while True:
            b = n & 0x7F
            n >>= 7
            if n:
                out.append(b | 0x80)
            else:
                out.append(b)
                return bytes(out)

    r = Reader(data, 8)
    out = bytearray(data[:8])
    while r.p < len(data):
        head = r.p
        sid = r.byte()
        size = r.uleb()
        start, end = r.p, r.p + size
        if sid != 7:
            out += data[head:end]
        else:
            s = Reader(data, start, end)
            count = s.uleb()
            body = uleb(count + 1) + data[s.p : end] + uleb(len(name)) + name.encode() + bytes([3]) + uleb(index)
            out += bytes([7]) + uleb(len(body)) + body
        r.p = end
    return bytes(out)
