"""Shared driver: the 167 set, fuel metered, trap backtraces captured."""
from pathlib import Path
import wasi_python._call as call
from wasi_python import Artifacts, run
ART = Path("/Users/claygendron/Git/Repos/wasi_python-wt/167-pdfplumber-plotly-xarray-and-zstd/build/artifacts")
A = Artifacts(snapshot=ART/"python-snapshot.wasm", plain=ART/"python.wasm", stdlib_zip=ART/"python-stdlib.zip", manifest=ART/"MANIFEST")
C = str(Path(__file__).parent / "cache")
LAST = {}
_orig = call._trap_name
def _cap(e):
    LAST["msg"] = str(e)
    try:
        LAST["frames"] = [f.func_name for f in (e.frames or [])]
    except Exception as x:
        LAST["frames"] = ["ERR" + repr(x)]
    return _orig(e)
call._trap_name = _cap
def go(code, snap=True, fuel=10**13, **kw):
    LAST.clear()
    return run(["-c", code], artifacts=A, snapshot=snap, fuel=fuel, deadline_s=3600, cache_dir=C, **kw)
import os as _os
def variant(path, snap=True):
    """Artifacts with one binary replaced by a spike copy."""
    p = Path(path)
    if snap:
        return Artifacts(snapshot=p, plain=A.plain, stdlib_zip=A.stdlib_zip, manifest=A.manifest)
    return Artifacts(snapshot=A.snapshot, plain=p, stdlib_zip=A.stdlib_zip, manifest=A.manifest)
def go_with(arts, code, snap=True, fuel=10**13, **kw):
    LAST.clear()
    return run(["-c", code], artifacts=arts, snapshot=snap, fuel=fuel, deadline_s=3600, cache_dir=C, **kw)
