"""Probe: pure-Python packages not in the artifact set, imported through import_path.
Every call runs on the released 0.1.0 set with fuel metered. Output is one line per case."""
import io, json, shutil, sys, time
from pathlib import Path
from wasi_python import Grant, run, artifact_dir

S = Path(sys.argv[1])
WHEELS = sorted((S / "wheels").glob("*.whl"))
UNPACKED = S / "lib-unpacked"
COMPILED = S / "lib-compiled"

def call(code, grants=(), import_path=(), snapshot=True, limit=200_000_000_000):
    t = time.perf_counter()
    d = run(["-c", code], grants=list(grants), import_path=list(import_path),
            snapshot=snapshot, fuel=limit)
    ms = (time.perf_counter() - t) * 1000
    out = d.stdout.decode(errors="replace").strip().replace("\n", " | ")[:300]
    err = d.stderr.decode(errors="replace").strip().splitlines()[-1:] if d.exit_code else []
    return d.exit_code, d.fuel_used, out, err, round(ms)

def show(name, r):
    code, fuel, out, err, ms = r
    print(f"{name:52s} exit={code} fuel={fuel:>14,} ms={ms:>5}  {out} {err}")

print("artifacts:", artifact_dir())
RICH = """
import io, rich, importlib.metadata as m
from rich.console import Console
from rich.table import Table
buf = io.StringIO()
c = Console(file=buf, width=40, color_system=None)
t = Table(title="t"); t.add_column("a"); t.add_column("b"); t.add_row("1", "2")
c.print(t)
print(rich.__file__, m.version("rich"), len(buf.getvalue()))
"""
FAKER = """
from faker import Faker
f = Faker(); Faker.seed(7)
print(f.name(), f.address().replace(chr(10), '/'), f.date_of_birth())
"""
SLUG = "from slugify import slugify; print(slugify('Hello, World! Ünïcode'))"
PYTZ = "import pytz; print(pytz.timezone('Europe/Paris'))"

for snap in (True, False):
    tag = "snapshot" if snap else "plain"
    show(f"[{tag}] -c pass, no import_path", call("pass", snapshot=snap))
    g = [Grant(S / "wheels", "/lib")]
    paths = [f"/lib/{w.name}" for w in WHEELS]
    show(f"[{tag}] -c pass, 8 wheel entries", call("pass", g, paths, snapshot=snap))
    show(f"[{tag}] rich from wheel files", call(RICH, g, paths, snapshot=snap))
    show(f"[{tag}] faker from wheel files", call(FAKER, g, paths, snapshot=snap))
    show(f"[{tag}] slugify from wheel files", call(SLUG, g, paths, snapshot=snap))
    g2 = [Grant(UNPACKED, "/lib")]
    show(f"[{tag}] -c pass, 1 folder entry", call("pass", g2, ["/lib"], snapshot=snap))
    show(f"[{tag}] rich from unpacked folder (source)", call(RICH, g2, ["/lib"], snapshot=snap))
    show(f"[{tag}] faker from unpacked folder (source)", call(FAKER, g2, ["/lib"], snapshot=snap))

# Compile the folder's bytecode inside the guest, once, through a writable grant.
if COMPILED.exists():
    shutil.rmtree(COMPILED)
shutil.copytree(UNPACKED, COMPILED)
r = call("import compileall, sys; ok = compileall.compile_dir('/lib', quiet=1, workers=1); "
         "import glob; print(ok, len(glob.glob('/lib/**/__pycache__/*.pyc', recursive=True)))",
         [Grant(COMPILED, "/lib", writable=True)], [], limit=2_000_000_000_000)
show("compileall in the guest (writable grant)", r)
pycs = list(COMPILED.rglob("*.pyc"))
print("pyc files written:", len(pycs), "tag sample:", pycs[0].name if pycs else None,
      "folder size MB:", round(sum(p.stat().st_size for p in COMPILED.rglob('*') if p.is_file())/1e6, 1))
g3 = [Grant(COMPILED, "/lib")]
for snap in (True, False):
    tag = "snapshot" if snap else "plain"
    show(f"[{tag}] rich from compiled folder (read-only)", call(RICH, g3, ["/lib"], snapshot=snap))
    show(f"[{tag}] faker from compiled folder (read-only)", call(FAKER, g3, ["/lib"], snapshot=snap))
show("[snapshot] pytz from compiled folder", call(PYTZ, g3, ["/lib"]))
# Shadowing: a module the set has stays the set's.
show("[snapshot] numpy stays the set's", call("import numpy; print(numpy.__spec__.origin)", g3, ["/lib"]))
# A native wheel cannot work: say so from the guest's own error.
show("[snapshot] a compiled dependency missing", call("import pydantic_core", g3, ["/lib"]))
