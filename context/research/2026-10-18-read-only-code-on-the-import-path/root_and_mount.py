"""Is anything of a root or a mount at / on the import path? (memo §1). Run as probe.py is run."""

from wasi_python import Mount, run
from wasi_python.mounts import Errno, Stat


class P:
    def stat(self, p):
        if p == "/":
            return Stat("dir")
        return Stat("file", 10, 1) if p == "/evil.py" else Errno.ENOENT

    def list(self, p):
        return [("evil.py", "file")] if p == "/" else Errno.ENOTDIR

    def read(self, p):
        return b"print(123)" if p == "/evil.py" else Errno.ENOENT


PROG = (
    "import sys, os; print(sys.path, os.getcwd())\n"
    "try:\n    import evil\nexcept ImportError as e: print(e)\n"
)
for snap in (True, False):
    for name, kw in (("root=True", {"root": True}), ("mount at /", {"mounts": [Mount(P(), "/")]})):
        d = run(["-c", PROG], snapshot=snap, **kw)
        print("snapshot" if snap else "plain", name, d.exit_code, d.stdout.decode().strip())
