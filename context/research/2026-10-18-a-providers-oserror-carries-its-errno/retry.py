"""Why EINTR and EAGAIN stay out of the set: what the guest does when an open is answered with
WASI's EINTR (27) or EAGAIN (6). The runner cannot be made to give either today (the closed
set), so this experiment patches `_Files._read` to answer the number after making the provider
call, and caps the run at 50 file calls. Prints, per number, the guest's result and the provider
calls made.

    WASI_PYTHON_ARTIFACTS=<a built artifact set> uv run python -I retry.py
"""

import json

from wasi_python import Errno, Mount, Stat, run
from wasi_python import mounts as M

real_read = M._Files._read


class Files:
    def __init__(self):
        self.reads = 0

    def stat(self, path):
        return Stat("dir") if path == "/" else Stat("file", 1)

    def list(self, path):
        return []

    def read(self, path):
        self.reads += 1
        return Errno.EISDIR if path == "/" else b"x"


GUEST = r"""
import os
try:
    with open('/w/x', 'rb') as f:
        print('read', f.read())
except OSError as e:
    print('OSError', e.errno, type(e).__name__)
"""

out = {}
for name, number in (("EINTR", 27), ("EAGAIN", 6)):

    def patched(self, caller, mount, path, buffer=False, number=number):
        errno, answer = real_read(self, caller, mount, path, buffer)
        return (number, None) if path != "/" else (errno, answer)

    M._Files._read = patched
    files = Files()
    done = run(["-c", GUEST], mounts=[Mount(files, "/w")], max_file_calls=50)
    out[name] = {
        "exit_code": done.exit_code,
        "trapped": done.trapped,
        "stdout": done.stdout.decode().strip(),
        "provider_reads": files.reads,
    }
M._Files._read = real_read
print(json.dumps(out, indent=1))
