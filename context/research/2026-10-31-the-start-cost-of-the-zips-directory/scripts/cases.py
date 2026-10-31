"""Run named cases: python cases.py <artifacts> <zip> <binary> <cases.py-module-with-CASES> [names]"""
import sys, importlib.util
from pathlib import Path
from wasi_python import Artifacts, run
ART, ZIP, BIN, MOD = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
spec = importlib.util.spec_from_file_location("c", MOD); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
names = sys.argv[5].split(",") if len(sys.argv) > 5 else list(m.CASES)
a = Artifacts(snapshot=ART/"python-snapshot.wasm", plain=ART/"python.wasm", stdlib_zip=ZIP, manifest=ART/"MANIFEST")
for n in names:
    r = run(["-c", m.CASES[n]], artifacts=a, snapshot=BIN == "snapshot", fuel=10**13, deadline_s=3600, cache_dir=str(Path(__file__).parent / "cache"))
    out = r.stdout.decode().strip().replace("\n", " | ")[:400]
    if r.exit_code: out += " ERR " + (r.stderr.decode().strip().splitlines() or [""])[-1][:300]
    print(f"{BIN}\t{ZIP.name}\t{n}\t{r.fuel_used}\t{out}", flush=True)
