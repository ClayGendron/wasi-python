"""The F3 check's program, as the spec proposes it, through the driver at 2 ms per clock read."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests"))  # the repository's tests/
from harness import guest as g, paths
setdir = Path(sys.argv[1]); work = Path(tempfile.mkdtemp(dir=sys.argv[2]))
m = paths.parse_manifest((setdir / "MANIFEST").read_text())
g.CLOCK_STEP_NS = 2_000_000
PROG = r'''
import json, time, regex
p = regex.compile(r"(a|aa)+$")
s = "a" * 20 + "!"
out = {}
for t in (0, 2.0, 3, 1e9, 1e13, float("inf"), None):
    t0 = time.monotonic_ns()
    try:
        out[repr(t)] = ["completed", repr(p.search(s, timeout=t))]
    except TimeoutError:
        out[repr(t)] = ["TimeoutError"]
    out[repr(t)].append(time.monotonic_ns() - t0)
print(json.dumps(out))
'''
for wasm in sys.argv[3:]:
    r = g.run(Path(wasm), ["-c", PROG], workdir=work, python_version=m.python, stdlib=setdir / "python-stdlib.zip", fuel=5 * 10**9)
    print(Path(wasm).parent.name, r.exit_code, r.trapped, r.fuel, r.stdout.decode().strip(), flush=True)
