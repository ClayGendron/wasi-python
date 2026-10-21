"""Compare two Wizer snapshots byte for byte, naming every difference.

    uv run python scripts/compare_snapshots.py <a.wasm> <b.wasm> <build/link/python.map>

Each snapshot is instantiated (nothing in it runs) and its initial linear memory read; differing
bytes are grouped and named by the data symbol that holds them, from the reactor's link map. The
run passes when no byte differs: the reactor pins every clock, entropy and file-metadata read
while it initializes, so two builds give the same snapshot.
The files'
SHA-256 is the stronger test; this tool says where two snapshots differ when that test fails.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import wasmtime as wt

# Data symbols allowed to differ, each with its reason. None is needed today.
ALLOWED: dict[str, str] = {}


def memory(path: Path) -> bytes:
    engine = wt.Engine()
    module = wt.Module.from_file(engine, str(path))
    store = wt.Store(engine)
    store.set_wasi(wt.WasiConfig())
    linker = wt.Linker(engine)
    linker.define_wasi()
    i32 = wt.ValType.i32()
    linker.define_func("host", "call", wt.FuncType([i32] * 4, [i32]), lambda *_: -1)
    mem = linker.instantiate(store, module).exports(store)["memory"]
    return bytes(mem.read(store, 0, mem.data_len(store)))


def symbols(map_file: Path) -> list[tuple[int, int, str]]:
    """(address, size, symbol) for every data symbol in a wasm-ld map."""
    rows = []
    for line in map_file.read_text().splitlines():
        m = re.match(r"\s*([0-9a-f]+)\s+[0-9a-f]+\s+([0-9a-f]+)\s+(\S+)\s*$", line)
        if m and not m[3].startswith(("Objects/", "/", "Modules/", "Python/", "Parser/")):
            rows.append((int(m[1], 16), int(m[2], 16), m[3]))
    return rows


def name_of(addr: int, rows: list[tuple[int, int, str]]) -> str:
    hits = [r for r in rows if r[0] <= addr < r[0] + max(r[1], 1)]
    return min(hits, key=lambda r: r[1])[2] if hits else f"<unnamed {addr:#x}>"


def main() -> int:
    a_path, b_path, map_path = (Path(p) for p in sys.argv[1:4])
    a, b = memory(a_path), memory(b_path)
    if len(a) != len(b):
        print(f"ERROR: memory sizes differ: {len(a)} and {len(b)}")
        return 1
    rows = symbols(map_path)
    regions: dict[str, int] = {}
    i = 0
    while i < len(a):
        if a[i] != b[i]:
            j = i
            while j < len(a) and a[j] != b[j]:
                j += 1
            name = name_of(i, rows)
            regions[name] = regions.get(name, 0) + (j - i)
            i = j
        else:
            i += 1
    total = sum(regions.values())
    unexpected = {n: k for n, k in regions.items() if n not in ALLOWED}
    for name, count in sorted(regions.items()):
        why = ALLOWED.get(name, "NOT ALLOWED")
        print(f"{'ok' if name in ALLOWED else 'ERROR'} {name}: {count} bytes ({why})")
    print(f"{total} differing bytes in {len(regions)} symbols; {len(unexpected)} not allowed")
    return 1 if unexpected else 0


if __name__ == "__main__":
    raise SystemExit(main())
