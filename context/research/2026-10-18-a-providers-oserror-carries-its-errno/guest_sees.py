"""What the guest sees, and what the record holds, when a provider raises an OSError.

Run from the worktree:
    WASI_PYTHON_ARTIFACTS=<a built artifact set> uv run python -I guest_sees.py [--model]

Without --model it measures the runner as it is. With --model it first replaces the runner's
provider boundary (`_Files._invoke`) with model.py's, the mapping this memo proposes, so the
same cases show what the guest would see. Each case is one mount; the guest prints, per case,
the errno and the text of the OSError it caught. Prints one JSON object."""

import errno
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from wasi_python import Errno, Mount, Stat, run  # noqa: E402

if "--model" in sys.argv:
    import model  # noqa: F401  (installs the model boundary)


class Hostile(OSError):
    """errno looked up through the class gives a different answer from the slot."""

    @property
    def errno(self):  # type: ignore[override]
        raise RuntimeError("a property that raises")


CASES = {
    # name: (method that raises, the exception)
    "FileNotFoundError(ENOENT)": ("read", FileNotFoundError(errno.ENOENT, "secret /host/path")),
    "PermissionError(EACCES)": ("read", PermissionError(errno.EACCES, "denied by policy")),
    "OSError(EDQUOT)": ("read", OSError(errno.EDQUOT, "quota")),
    "OSError(ENAMETOOLONG)": ("read", OSError(errno.ENAMETOOLONG, "long")),
    "IsADirectoryError(EISDIR) at read": ("read", IsADirectoryError(errno.EISDIR, "a folder")),
    "FileNotFoundError('msg') errno None": ("read", FileNotFoundError("only a message")),
    "PermissionError('msg') errno None": ("read", PermissionError("only a message")),
    "OSError('msg') errno None": ("read", OSError("only a message")),
    "InterruptedError(EINTR)": ("read", InterruptedError(errno.EINTR, "retry me")),
    "BlockingIOError(EAGAIN)": ("read", BlockingIOError(errno.EAGAIN, "retry me")),
    "OSError(EBADF)": ("read", OSError(errno.EBADF, "bad fd")),
    "OSError(ELOOP) not in Errno": ("read", OSError(errno.ELOOP, "loop")),
    "OSError(99999) unknown": ("read", OSError(99999, "unknown")),
    "OSError errno True": ("read", OSError(True, "a bool")),
    "Hostile errno property": ("read", Hostile(errno.ENOENT, "property")),
    "stat FileNotFoundError": ("stat", FileNotFoundError(errno.ENOENT, "x")),
    "list NotADirectoryError": ("list", NotADirectoryError(errno.ENOTDIR, "x")),
    "write PermissionError(EROFS) at close": ("write", OSError(errno.EROFS, "read-only store")),
    "mkdir FileExistsError": ("mkdir", FileExistsError(errno.EEXIST, "x")),
    "ValueError": ("read", ValueError("not an OSError")),
}


class Raising:
    def __init__(self, method, exc):
        self.method, self.exc = method, exc

    def _maybe(self, method):
        if method == self.method:
            raise self.exc

    def stat(self, path):
        self._maybe("stat")
        return Stat("dir") if path == "/" else Stat("file", 1)

    def list(self, path):
        self._maybe("list")
        return [("x", "file")]

    def read(self, path):
        self._maybe("read")
        return Errno.EISDIR if path == "/" else b"x"

    def write(self, path, data):
        if data:  # the create at open succeeds; the close's write-back raises
            self._maybe("write")
        return None

    def mkdir(self, path):
        self._maybe("mkdir")
        return None

    remove = rmdir = mkdir

    def rename(self, src, dst):
        return None


GUEST = r"""
import json, os, sys
out = {}
for i, (name, method) in enumerate(json.loads(sys.argv[1])):
    base = f"/c{i}"
    try:
        if method == "stat":
            os.stat(base + "/x")
        elif method == "list":
            os.listdir(base)
        elif method == "write":
            with open(base + "/x", "wb") as f:
                f.write(b"data")
        elif method == "mkdir":
            os.mkdir(base + "/d")
        else:
            with open(base + "/x", "rb") as f:
                f.read()
        out[name] = ["answered", None, None]
    except OSError as e:
        out[name] = [e.errno, type(e).__name__, e.strerror]
print(json.dumps(out))
"""


def main():
    names = list(CASES)
    mounts = [
        Mount(Raising(*CASES[n]), f"/c{i}", writable=CASES[n][0] in ("write", "mkdir"))
        for i, n in enumerate(names)
    ]
    done = run(["-c", GUEST, json.dumps([[n, CASES[n][0]] for n in names])], mounts=mounts)
    guest = json.loads(done.stdout) if done.exit_code == 0 else done.stderr.decode()[-2000:]
    print(json.dumps({
        "mode": "model" if "--model" in sys.argv else "as built",
        "exit_code": done.exit_code,
        "guest": guest,
        "faults": [[f.method, f.error] for f in done.files.faults],
        "refused": [[r.method, int(r.errno), r.at, r.cause] for r in done.files.refused],
        "calls": {k: v for k, v in done.files.calls.items() if v},
    }, indent=1))


main()
