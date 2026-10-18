"""P4: a session's memory cap (set_limits, 256 MiB) met inside a turn: a Python exception or a trap?"""
import sys; sys.path.insert(0, sys.argv[1])
import loop
turns = [
    "import numpy as np; x = 1",
    "a = np.zeros(300_000_000, np.int8)",
    "print('after a big array', x)",
    "b = [0] * (10**8)",
    "print('after a big list', x)",
    "l = []\nwhile True: l.append(bytearray(1 << 16))",
    "del l; import gc; gc.collect(); print('after 64 KiB blocks', x)",
    "l = []\nwhile True: l.append(str(len(l)))",
    "print('after small objects', x)",
]
res, ended, tail = loop.session(turns, memory_bytes=256 << 20)
for i, (out, err, mem) in enumerate(res, 1):
    last = err.decode(errors="replace").strip().splitlines()[-1:] if err else []
    print(f"turn {i}: memory {mem >> 20} MiB; stdout {out.decode().strip()!r}; last stderr line {last}")
print("ended:", ended, "| stderr after the last turn:", tail[1].decode(errors='replace').strip().splitlines()[-3:])
