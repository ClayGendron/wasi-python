"""Verifier v01: the .cwasm checked by lstat versus the file wasmtime maps.

Part A: deterministic schedule. The folder above the cache is swapped for a link to a
planted folder only while wasmtime-py opens the .cwasm by path, then swapped back
before the runner's stamp re-check. The identity (dev, ino) of the file checked and of
the file opened are both recorded.
Part B: blind race. A separate process swaps the cache folder and a link to the planted
folder with renamex_np(RENAME_SWAP) in a loop (no hook in the runner), while the runner
reloads the module from the cache a bounded number of times. Outcomes are counted; the planted file is re-planted whenever the runner's own\nwrite replaced it through the link.
One OS user plays both roles; all paths are under argv[1].
"""
import ctypes, os, shutil, stat, subprocess, sys, warnings
from pathlib import Path

WORK = Path(sys.argv[1]).resolve()
ATTEMPTS = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
if WORK.exists():
    shutil.rmtree(WORK)
WORK.mkdir(parents=True)
parent = WORK / "parent"          # stands for a folder another user owns (~/.cache)
parent.mkdir()
cache = parent / "wasi_python"
planted_root = WORK / "planted"   # the other user's own folder
planted_root.mkdir()

import wasmtime as wt
from wasi_python import _engines, _platform
from wasi_python._process import process

A = WORK / "a.wasm"
A.write_bytes(wt.wat2wasm('(module (func (export "genuine")))'))
engine = _engines._engine(False)
p = process()

def log(*a):
    print(*a, flush=True)

def ident(path):
    st = os.stat(path)
    return (st.st_dev, st.st_ino)

m = _engines._module(engine, False, A, cache)
name = [n for n in os.listdir(cache) if n.endswith(".cwasm")][0]
real = cache / name
log("A1 runner file", name, "mode", oct(stat.S_IMODE(os.lstat(real).st_mode)),
    "private:", _platform.PLATFORM.private(real, is_dir=False), "exports", [e.name for e in m.exports])
fake = planted_root / name
PLANTED = wt.Module(engine, '(module (func (export "planted_image_loaded")))').serialize()
def replant():
    # the other user's own file; the runner's _store may overwrite it while the link is in place
    tmpf = planted_root / ".replant"
    tmpf.write_bytes(PLANTED)
    os.chmod(tmpf, 0o644)
    os.replace(tmpf, fake)
replant()
with warnings.catch_warnings(record=True):
    warnings.simplefilter("always")
    log("A2 planted file mode", oct(stat.S_IMODE(os.lstat(fake).st_mode)),
        "private on it directly:", _platform.PLATFORM.private(fake, is_dir=False))

# Part A
orig = wt.Module.deserialize_file
aside = parent / "wasi_python.aside"
seen = {}
def hooked(engine_, path):
    seen["checked"] = ident(path)
    os.rename(cache, aside)
    os.symlink(planted_root, cache)
    try:
        seen["opened"] = ident(path)
        return orig(engine_, path)
    finally:
        os.unlink(cache)
        os.rename(aside, cache)
        seen["after"] = ident(path)
wt.Module.deserialize_file = staticmethod(hooked)
p.modules.clear()
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    m3 = _engines._module(engine, False, A, cache)
wt.Module.deserialize_file = orig
log("A3 identity checked", seen["checked"], "opened", seen["opened"], "after", seen["after"],
    "planted file", ident(fake))
log("A4 exports", [e.name for e in m3.exports], "warnings", [str(x.message) for x in w],
    "counts", dict(p.counts))
log("A RESULT:", "planted accepted" if "planted_image_loaded" in [e.name for e in m3.exports]
    else "planted refused")

# Part B: blind race with an external swapper process
link = parent / "swaplink"
os.symlink(planted_root, link)
swapper = WORK / "swapper.py"
swapper.write_text(
    "import ctypes, os, sys\n"
    "libc = ctypes.CDLL(None, use_errno=True)\n"
    "a, b, stop = sys.argv[1].encode(), sys.argv[2].encode(), sys.argv[3]\n"
    "n = 0\n"
    "while not os.path.exists(stop):\n"
    "    if libc.renamex_np(a, b, 2) != 0: raise OSError(ctypes.get_errno(), 'renamex_np')\n"
    "    n += 1\n"
    "if n % 2: libc.renamex_np(a, b, 2)\n"
    "print('swaps', n + (n % 2), flush=True)\n")
stop = WORK / "stop"
proc = subprocess.Popen([sys.executable, "-I", str(swapper), str(cache), str(link), str(stop)],
                        stdout=subprocess.PIPE, text=True)
outcomes = {"genuine_loaded": 0, "planted_loaded": 0, "compiled_instead": 0, "error": 0}
warned = 0
first_planted = None
replants = 0
for i in range(ATTEMPTS):
    if fake.read_bytes() != PLANTED:
        replants += 1
        replant()
    p.modules.clear()
    before = dict(p.counts)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            mm = _engines._module(engine, False, A, cache)
        except Exception as e:
            outcomes["error"] += 1
            continue
    if w:
        warned += 1
    names_ = [e.name for e in mm.exports]
    if p.counts["loaded"] > before["loaded"]:
        if "planted_image_loaded" in names_:
            outcomes["planted_loaded"] += 1
            if first_planted is None:
                first_planted = (i, len(w))
        else:
            outcomes["genuine_loaded"] += 1
    else:
        outcomes["compiled_instead"] += 1
stop.write_text("")
out, _ = proc.communicate(timeout=20)
log("B attempts", ATTEMPTS, "outcomes", outcomes, "attempts with a RuntimeWarning", warned,
    "first planted (attempt, warnings in it)", first_planted, "swapper", out.strip(), "replants (runner overwrote the planted file)", replants)
log("B planted loads with no warning in that attempt:",
    "yes" if first_planted is not None and first_planted[1] == 0 else "see counts")
shutil.rmtree(WORK, ignore_errors=True)
