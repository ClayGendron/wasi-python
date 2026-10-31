import sys
from pathlib import Path
from wasi_python import Artifacts, run
ART = Path("/Users/claygendron/Git/Repos/wasi_python-wt/167-pdfplumber-plotly-xarray-and-zstd/build/artifacts")
a = Artifacts(snapshot=ART/"python-snapshot.wasm", plain=ART/"python.wasm", stdlib_zip=ART/"python-stdlib.zip", manifest=ART/"MANIFEST")
C = "/Users/claygendron/Git/Repos/wasi_python-wt/research-lighter-exit/build/lx/cache"
r = run(["-c", "pass"], artifacts=a, snapshot=True, fuel=10**13, deadline_s=600, cache_dir=C)
print(r.fuel_used, r.exit_code)
r = run(["-c", "pass"], artifacts=a, snapshot=True, fuel=30_000_000, deadline_s=600, cache_dir=C)
print(r)
