"""P6: host_alloc for the next turn's code when the session's memory is at its cap: NULL, or a trap?"""
import sys; sys.path.insert(0, sys.argv[1])
import loop
seen = []
def on_turn(n, out, err):
    pass
turns = [
    "l = []\ntry:\n    while True: l.append(bytearray(1 << 16))\nexcept MemoryError:\n    pass\nprint('held', len(l))",
    "print('next turn ran')",
]
import h
orig = h.Guest.__init__
def probe_alloc(caller, sizes):
    alloc = caller["host_alloc"]
    return [alloc(caller, n) for n in sizes]
res = []
queue = list(turns)
state = {}
def door(caller, req):
    g = state["g"]
    if req == b"done":
        out, err = g.swap_streams()
        ptrs = probe_alloc(caller, [1 << 20, 4096, 64])
        res.append((out.data.decode().strip(), ptrs, caller["memory"].data_len(caller) >> 20))
    return queue.pop(0).encode() if queue else b""
g = h.Guest(door=door, argv=("python", "-c", loop.LOOP), memory_bytes=256 << 20)
state["g"] = g
g.store.set_fuel(2**62)
rc = g.ex["run"](g.store)
for r in res:
    print("after turn: stdout %r; host_alloc(1 MiB, 4 KiB, 64) -> %s; memory %d MiB" % r)
print("run returned", rc)
