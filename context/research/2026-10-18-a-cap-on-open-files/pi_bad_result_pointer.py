"""PI (spec 068): on plain wasmtime 49.0.0 (no runner), does a path_open whose result pointer is out
of bounds open the file before it traps? The next open's number shows whether one was left held."""

import struct
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests"))
from harness import files  # noqa: E402

tmp = Path(tempfile.mkdtemp())
for i in range(3):
    (tmp / f"f{i}").write_bytes(b"x")
raw = files.grant_raw([(tmp, "/w", False)])
size = raw.memory.data_len(raw.store)


def opener(name, out):
    raw.put(files.PATH, name.encode())
    return raw("path_open", 3, 0, files.PATH, len(name), 0, files.READ_RIGHTS, 0, 0, out)


print("f0:", opener("f0", files.RESULT), struct.unpack("<I", raw.get(files.RESULT, 4))[0])
try:
    print("f1 with out past memory:", opener("f1", size))
except files.Ends as e:
    print("f1 with out past memory: trap:", e.message)
print("f2:", opener("f2", files.RESULT), struct.unpack("<I", raw.get(files.RESULT, 4))[0])
