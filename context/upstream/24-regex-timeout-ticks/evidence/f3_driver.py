"""F3: regex timeout= through the judge's driver, whose clock steps a fixed amount per read."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests"))  # the repository's tests/
from harness import guest as g, paths

import tempfile
wasm = Path(sys.argv[1]); setdir = Path(sys.argv[2]); work = Path(tempfile.mkdtemp(dir=sys.argv[3]))
step = int(sys.argv[4]); timeouts = sys.argv[5].split(",")
m = paths.parse_manifest((setdir / "MANIFEST").read_text())
g.CLOCK_STEP_NS = step
PROG = """import regex, time
PAT, SUBJ = {pat!r}, {subj}
p = regex.compile(PAT)
t0 = time.monotonic_ns()
try:
    r = p.search(SUBJ, timeout={t})
    print('result', r)
except TimeoutError as e:
    print('TimeoutError', e)
print('guest-ns', time.monotonic_ns() - t0)
"""
PAT = sys.argv[7]; SUBJ = sys.argv[8]
for t in timeouts:
    r = g.run(wasm, ["-c", PROG.format(t=t, pat=PAT, subj=SUBJ)], workdir=work, python_version=m.python,
              stdlib=setdir / "python-stdlib.zip", fuel=int(float(sys.argv[6])))
    print(f"step={step} timeout={t}: exit={r.exit_code} trapped={r.trapped} fuel={r.fuel} out={r.stdout.decode().strip()!r}", flush=True)
