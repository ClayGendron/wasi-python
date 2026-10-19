"""PB (spec 068): what the guest sees today when the host runs out of descriptors. A lower soft
limit makes the host run out quickly. Runs on main's code."""

import resource
import sys
import tempfile
from pathlib import Path

from common068 import A

from wasi_python import Grant, run

soft = int(sys.argv[1]) if len(sys.argv) > 1 else 256
resource.setrlimit(resource.RLIMIT_NOFILE, (soft, resource.getrlimit(resource.RLIMIT_NOFILE)[1]))
tmp = Path(tempfile.mkdtemp())
(tmp / "f.txt").write_bytes(b"x")
code = r'''
import errno, os
held = []
try:
    while True:
        held.append(os.open("/data/f.txt", os.O_RDONLY))
except OSError as e:
    print("opened", len(held), "then errno", e.errno, errno.errorcode.get(e.errno), "-", e.strerror)
print("EMFILE is", errno.EMFILE, "EIO is", errno.EIO, "in the guest")
'''
r = run(["-c", code], artifacts=A, grants=[Grant(tmp, "/data")], cache_dir=False)
print("soft limit", soft, "->", r.exit_code, r.trapped, r.stdout.decode(), r.stderr.decode()[-300:])
