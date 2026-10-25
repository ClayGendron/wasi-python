"""A set passed as artifacts= is hashed by _digest and then compiled by wasmtime from the path,
so the digest that names the in-process module and the .cwasm is not bound to the bytes compiled.
Deterministic schedule: the file changes between the hash and wasmtime's open. A later call that
holds its binary to the same checked digest (as a set found and checked against SHA256SUMS does)
then gets the other image from the .cwasm cache. One OS user; scratch only."""
import shutil, sys
from pathlib import Path
import wasmtime as wt
from wasi_python import _engines, _artifacts
from wasi_python._process import process

work = Path(sys.argv[1]).resolve()
shutil.rmtree(work, ignore_errors=True)
(work / "given").mkdir(parents=True)
(work / "checked").mkdir()
cache = work / "cache"
good = wt.wat2wasm('(module (func (export "genuine")))')
other = wt.wat2wasm('(module (func (export "other_image")))')
given = work / "given" / "python.wasm"
given.write_bytes(good)
checked = work / "checked" / "python.wasm"
checked.write_bytes(good)
digest = _artifacts._digest(checked)
engine = _engines._engine(False)
orig = wt.Module.from_file
def changed(engine_, path):
    Path(path).write_bytes(other)   # the writer, between the hash and the compile
    return orig(engine_, path)
wt.Module.from_file = staticmethod(changed)
m = _engines._module(engine, False, given, cache)  # artifacts= path: want is None
wt.Module.from_file = orig
print("artifacts= call compiled:", [e.name for e in m.exports], "keyed under", digest[:32])
process().modules.clear()
m2 = _engines._module(engine, False, checked, cache, digest)  # a checked set's call
print("checked call (binary on disk is genuine, digest", digest[:16], ") got:",
      [e.name for e in m2.exports], dict(process().counts))
shutil.rmtree(work)
