"""F1 of spec 060's pre-build review: a list answer encoded once and spliced per id, against
encoded per frame. Host CPU per list frame (thread CPU, median of 20), the frame host's encode or
splice plus the door's own copy (bytes(response)); the copy into guest memory is not measured."""
import json
import statistics
import sys
import time

from wasi_python import tools as T
from wasi_python.tools import tool

print(sys.version.split()[0])
for ntools, chars in ((5, 100), (100, 2000), (300, 4000), (1000, 8000)):
    props = {f"p{j}": {"type": "string", "description": "e" * 200} for j in range(10)}
    many = [
        tool(lambda **k: None, name=f"t{i}", description="d" * chars,
             input_schema={"type": "object", "properties": props})
        for i in range(ntools)
    ]
    descriptors = [t.descriptor() for t in many]
    cached = T._encode({"tools": descriptors})[len(b'{"tools":'):-1]  # the array alone, once

    def per_frame(i):
        return bytes(T._encode({"v": 1, "id": i, "ok": True, "tools": descriptors}))

    def spliced(i):
        return bytes(b'{"v":1,"id":' + json.dumps(i).encode() + b',"ok":true,"tools":' + cached + b"}")

    assert per_frame(7) == spliced(7) and per_frame(None) == spliced(None)
    for label, fn in (("encoded per frame", per_frame), ("encoded once, spliced", spliced)):
        cpu = []
        for i in range(20):
            c0 = time.thread_time()
            fn(i)
            cpu.append(time.thread_time() - c0)
        print(f"  {ntools:5d} tools, {len(cached):9d} B: {label:22s} {statistics.median(cpu) * 1000:7.3f} ms")
