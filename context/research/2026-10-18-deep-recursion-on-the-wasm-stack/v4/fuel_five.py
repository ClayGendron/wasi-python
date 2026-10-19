"""Spec 080: each fuel-recording 071 check, five times, through wasi_python.run (as 071 ran them)
or through the judge's guest driver (as 080 runs them). Usage: fuel_five.py run|guest"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, "tests")
from checks.test_v1_2_hostile_guest import COUNTED, PICKLE_DEEP, RECURSION_CASES, RECURSIONS  # noqa: E402
import wasi_python  # noqa: E402
from harness import guest, paths  # noqa: E402

mode = sys.argv[1]
d = paths.artifact_dir()
m = paths.parse_manifest((d / "MANIFEST").read_text())
work = Path(tempfile.mkdtemp())
def fuel(code, snapshot):
    if mode == "run":
        return wasi_python.run(["-c", code], snapshot=snapshot, fuel=10**11).fuel_used
    which = "python-snapshot.wasm" if snapshot else "python.wasm"
    return guest.run(d / which, ["-c", code], workdir=work, python_version=m.python,
                     stdlib=d / "python-stdlib.zip").fuel
cases = [(p.values[0], p.values[1]) for p in RECURSION_CASES] + [("pickle-deep", True)]
for name, snap in cases:
    code = PICKLE_DEEP if name == "pickle-deep" else COUNTED.format(body=RECURSIONS[name][0])
    f = [fuel(code, snap) for _ in range(5)]
    print(f"{mode:5} {name:22} {'snapshot' if snap else 'plain':8} spread {max(f) - min(f):>9} {(max(f) - min(f)) / min(f):.4%} {f}", flush=True)
