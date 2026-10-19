"""Probe 4 (benchmark, memo only): the host-side wall time of one provider call and one door call
today, so the handoff's 7 us can be put beside it."""
import os, sys, time
from wasi_python import run, Mount
from wasi_python.mounts import Stat

class P:
    def stat(self, path):
        return Stat("dir") if path == "/" else Stat("file", size=3)
    def list(self, path):
        return [("a", "file")]
    def read(self, path):
        return b"abc"

N = 5000
stat_code = f"import os\nfor _ in range({N}): os.stat('/m/a')"
door_code = f"import _host\nfor _ in range({N}): _host.call(b'x')"
base = "pass"
kw = dict(cache_dir=os.environ["CACHE"])
def t(code, **k):
    t0 = time.perf_counter(); d = run(["-c", code], **kw, **k); el = time.perf_counter() - t0
    assert d.exit_code == 0, d
    return el, d
run(["-c", "pass"], **kw)
for rep in range(2):
    b, _ = t(base, mounts=[Mount(P(), "/m")])
    s, d = t(stat_code, mounts=[Mount(P(), "/m")])
    print(f"provider: {(s - b) / N * 1e6:6.1f} us per guest os.stat (calls {sum(d.files.calls.values())})")
    b, _ = t(base, host=lambda r: r)
    s, _ = t(door_code, host=lambda r: r)
    print(f"door:     {(s - b) / N * 1e6:6.1f} us per door call")
