"""A pytest plugin for spec 060's research: per frame host, the bytes of frames admitted
(read and parsed) and of all frames, written per process at exit."""
import atexit, json, os
from wasi_python import tools as _t

_hosts = []
_orig_admit = _t._ToolHost.admit
_orig_init = _t._ToolHost.__init__

def _init(self, *a, **k):
    _orig_init(self, *a, **k)
    self._t060 = {"all": 0, "admitted": 0, "frames": 0, "max_frame": 0}
    _hosts.append(self)

def _admit(self, length):
    ans = _orig_admit(self, length)
    d = getattr(self, "_t060", None)
    if d is not None:
        d["all"] += length; d["frames"] += 1
        if ans is None:
            d["admitted"] += length
            d["max_frame"] = max(d["max_frame"], length)
    return ans

_t._ToolHost.__init__ = _init
_t._ToolHost.admit = _admit

@atexit.register
def _dump():
    out = os.environ.get("TALLY060_OUT")
    if not out:
        return
    rows = [h._t060 for h in _hosts]
    with open(os.path.join(out, f"tally-{os.getpid()}.json"), "w") as f:
        json.dump(rows, f)
