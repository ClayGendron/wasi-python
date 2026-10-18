"""`read`'s EISDIR, returned and raised: whether `os.open` of the path makes a folder descriptor.
With --model the raised one goes through model.py's boundary.

    WASI_PYTHON_ARTIFACTS=<a built artifact set> uv run python -I folder.py [--model]
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from wasi_python import Errno, Mount, Stat, run  # noqa: E402

if "--model" in sys.argv:
    import model  # noqa: F401


class Folder:
    def __init__(self, raises):
        self.raises, self.calls = raises, {"read": 0, "list": 0}

    def stat(self, path):
        return Stat("dir")

    def list(self, path):
        self.calls["list"] += 1
        return []

    def read(self, path):
        self.calls["read"] += 1
        if path != "/" and self.raises:
            raise IsADirectoryError("a folder")
        return Errno.EISDIR


GUEST = r"""
import json, os, stat
out = {}
for base in ("/r", "/o"):
    try:
        fd = os.open(base + "/x", os.O_RDONLY)
        out[base] = ["opened", stat.S_ISDIR(os.fstat(fd).st_mode)]
        os.close(fd)
    except OSError as e:
        out[base] = ["OSError", e.errno]
print(json.dumps(out))
"""

r, o = Folder(False), Folder(True)
done = run(["-c", GUEST], mounts=[Mount(r, "/r"), Mount(o, "/o")])
print(json.dumps({
    "mode": "model" if "--model" in sys.argv else "as built",
    "guest": json.loads(done.stdout) if done.exit_code == 0 else done.stderr.decode()[-500:],
    "returned_calls": r.calls,
    "raised_calls": o.calls,
    "faults": [f.error for f in done.files.faults],
}))
