"""Section 7b's probe: a preopen's `ino`, as the guest's fd_filestat_get reports it, against
SipHash-1-3 (zero keys) over the host's (st_dev, st_ino). Run: uv run python identity_probe.py DIR"""

import os
import struct
import sys

import wasmtime as wt

M = (1 << 64) - 1


def rotl(x: int, b: int) -> int:
    return ((x << b) | (x >> (64 - b))) & M


def siphash13(data: bytes) -> int:
    v0, v1, v2, v3 = 0x736F6D6570736575, 0x646F72616E646F6D, 0x6C7967656E657261, 0x7465646279746573

    def rnd() -> None:
        nonlocal v0, v1, v2, v3
        v0 = (v0 + v1) & M
        v1 = rotl(v1, 13) ^ v0
        v0 = rotl(v0, 32)
        v2 = (v2 + v3) & M
        v3 = rotl(v3, 16) ^ v2
        v0 = (v0 + v3) & M
        v3 = rotl(v3, 21) ^ v0
        v2 = (v2 + v1) & M
        v1 = rotl(v1, 17) ^ v2
        v2 = rotl(v2, 32)

    end = len(data) - len(data) % 8
    for i in range(0, end, 8):
        m = struct.unpack_from("<Q", data, i)[0]
        v3 ^= m
        rnd()
        v0 ^= m
    b = (len(data) & 0xFF) << 56
    for i, c in enumerate(data[end:]):
        b |= c << (8 * i)
    v3 ^= b
    rnd()
    v0 ^= b
    v2 ^= 0xFF
    for _ in range(3):
        rnd()
    return v0 ^ v1 ^ v2 ^ v3


WAT = """(module
  (import "wasi_snapshot_preview1" "fd_filestat_get" (func $st (param i32 i32) (result i32)))
  (memory (export "memory") 1)
  (func (export "stat") (param $fd i32) (result i32) (call $st (local.get $fd) (i32.const 64))))"""

folder = sys.argv[1]
engine = wt.Engine()
store = wt.Store(engine)
config = wt.WasiConfig()
config.preopen_dir(folder, "/x", False)
store.set_wasi(config)
linker = wt.Linker(engine)
linker.define_wasi()
exports = linker.instantiate(store, wt.Module(engine, WAT)).exports(store)
assert exports["stat"](store, 3) == 0
reported = struct.unpack_from("<Q", bytes(exports["memory"].read(store, 72, 80)))[0]
st = os.stat(folder)
computed = siphash13(struct.pack("=QQ", st.st_dev & M, st.st_ino))
print(f"reported {reported} computed {computed} equal {reported == computed}")
