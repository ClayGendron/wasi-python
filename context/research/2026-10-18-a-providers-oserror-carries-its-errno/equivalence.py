"""Raising versus returning, for every member of the closed set: a provider whose `stat` raises
`OSError(errno.<NAME>, ...)` (the host's number) against one whose `stat` returns
`Errno.<NAME>`. Also a generator `list` that raises FileNotFoundError while it is iterated.
Prints the guest's errno per name for both providers and both records.

    WASI_PYTHON_ARTIFACTS=<a built artifact set> uv run python -I equivalence.py [--model]
"""

import errno as host_errno
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from wasi_python import Errno, Mount  # noqa: E402

if "--model" in sys.argv:
    import model  # noqa: F401

from wasi_python import run  # noqa: E402


class Returns:
    def stat(self, path):
        return Errno[path.strip("/")]

    def list(self, path):
        return Errno.ENOTDIR

    def read(self, path):
        return Errno.ENOENT


class Raises(Returns):
    def stat(self, path):
        name = path.strip("/")
        raise OSError(getattr(host_errno, name), f"{name} from the host")

    def list(self, path):  # a generator: its body runs only when the runner iterates it
        yield ("a", "file")
        raise FileNotFoundError(host_errno.ENOENT, "gone while listing")


GUEST = r"""
import json, os, sys
out = {}
for name in json.loads(sys.argv[1]):
    try:
        os.stat("/m/" + name)
        out[name] = None
    except OSError as e:
        out[name] = e.errno
try:
    os.listdir("/m")
    out["listdir"] = None
except OSError as e:
    out["listdir"] = e.errno
print(json.dumps(out))
"""

names = [e.name for e in Errno]
result = {"mode": "model" if "--model" in sys.argv else "as built"}
for label, provider in (("returns", Returns()), ("raises", Raises())):
    done = run(["-c", GUEST, json.dumps(names)], mounts=[Mount(provider, "/m")])
    result[label] = {
        "guest": json.loads(done.stdout) if done.exit_code == 0 else done.stderr.decode()[-800:],
        "faults": len(done.files.faults),
        "fault_kinds": sorted({f.error.split(":")[0] for f in done.files.faults}),
        "calls": {k: v for k, v in done.files.calls.items() if v},
    }
same = {n: result["returns"]["guest"][n] == result["raises"]["guest"][n] for n in names}
result["stat_same_for_all_21"] = all(same.values())
result["differs"] = [n for n, s in same.items() if not s]
print(json.dumps(result, indent=1))
