"""wasmtime 49.0.0's own fd_readdir (wasmtime-py 49.0.0), on a read-only preopen: tally each
entry's three padding bytes after d_type. The guest buffer is zeroed before every call, so a
non-zero byte is written by wasmtime. Usage: uv run python padding.py STORES (from the repo)."""

import collections
import struct
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tests"))
from harness import files as F  # noqa: E402

seen: collections.Counter = collections.Counter()
tree = F.write_tree(Path(tempfile.mkdtemp()))
for _ in range(int(sys.argv[1])):
    r = F.grant_raw([(tree, "/m", False)])
    d = r.open(3, "d", F.O_DIRECTORY)[1]
    for _ in range(5):
        r.clear()
        r("fd_readdir", d, F.DIRBUF, 4096, 0, F.RESULT)
        data, pos = r.get(F.DIRBUF, r.u32(F.RESULT)), 0
        while pos + 24 <= len(data):
            namlen = struct.unpack_from("<I", data, pos + 16)[0]
            seen[(data[pos + 24 : pos + 24 + namlen], data[pos + 20 : pos + 24])] += 1
            pos += 24 + namlen
import wasmtime  # noqa: E402
from importlib.metadata import version  # noqa: E402

print("wasmtime-py", version("wasmtime"), "| (name, d_type and padding): count")
for key, count in sorted(seen.items()):
    print(key, count)
