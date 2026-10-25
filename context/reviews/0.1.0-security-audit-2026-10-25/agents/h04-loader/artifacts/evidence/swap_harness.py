"""Deterministic schedule for the .cwasm cache check-to-load gap.

Simulates a lower-trust owner of the cache folder's parent (e.g. the user whose $HOME a
sudo'd process keeps) swapping the cache folder for a link while wasmtime opens the .cwasm
by path, and swapping it back before the runner's post-load stamp check. Everything lives
under scratch/work; one OS user plays both roles (the cross-user part is not observed here).
"""
import os, shutil, stat, sys, warnings
from pathlib import Path

WORK = Path(sys.argv[1]).resolve()
if WORK.exists():
    shutil.rmtree(WORK)
WORK.mkdir(parents=True)
parent = WORK / "parent"            # stands for the lower-trust user's folder (~/.cache)
parent.mkdir()
cache = parent / "wasi_python"      # the runner's cache, as private() makes it
planted = WORK / "planted"          # the lower-trust user's folder holding its own image
planted.mkdir()

import wasmtime as wt
from wasi_python import _engines, _platform
from wasi_python._process import process

A = WORK / "a.wasm"
A.write_bytes(wt.wat2wasm('(module (func (export "genuine")))'))
B_WAT = '(module (func (export "planted_image_loaded")))'

engine = _engines._engine(False)
p = process()

def log(*a):
    print(*a, flush=True)

# 1. The runner compiles a.wasm and writes its own .cwasm into the cache.
m1 = _engines._module(engine, False, A, cache)
log("step1 exports:", [e.name for e in m1.exports], "counts:", dict(p.counts))
names = [n for n in os.listdir(cache) if n.endswith(".cwasm")]
assert len(names) == 1, names
name = names[0]
real = cache / name
st = os.lstat(real)
log("runner file:", name, "mode", oct(stat.S_IMODE(st.st_mode)), "nlink", st.st_nlink,
    "private():", _platform.PLATFORM.private(real, is_dir=False))

# 2. The planted image: another module's .cwasm, mode 0644 (not as the runner makes it).
fake = planted / name
fake.write_bytes(wt.Module(engine, B_WAT).serialize())
os.chmod(fake, 0o644)
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    log("planted file mode", oct(stat.S_IMODE(os.lstat(fake).st_mode)),
        "private() on it directly:", _platform.PLATFORM.private(fake, is_dir=False))

# 3. Control: forget the in-process module; reload with no swap -> the runner's own file.
p.modules.clear()
m2 = _engines._module(engine, False, A, cache)
log("control exports:", [e.name for e in m2.exports], "counts:", dict(p.counts))

# 4. The schedule: between private(cwasm) and wasmtime's own open, the parent's owner
#    renames the cache folder aside and puts a link to its folder in its place; it puts
#    the real folder back once wasmtime has read the file.
orig = wt.Module.deserialize_file
aside = parent / "wasi_python.aside"
def swapped(engine_, path):
    os.rename(cache, aside)
    os.symlink(planted, cache)
    try:
        log("  during open: wasmtime opens", path, "->", os.path.realpath(path))
        return orig(engine_, path)
    finally:
        os.unlink(cache)
        os.rename(aside, cache)
wt.Module.deserialize_file = staticmethod(swapped)
p.modules.clear()
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    m3 = _engines._module(engine, False, A, cache)
    log("warnings during swapped load:", [str(x.message) for x in w])
wt.Module.deserialize_file = orig
exports = [e.name for e in m3.exports]
log("swapped exports:", exports, "counts:", dict(p.counts))
log("RESULT:", "planted image accepted as the cached module for a.wasm"
    if "planted_image_loaded" in exports else "planted image refused")
shutil.rmtree(WORK)
