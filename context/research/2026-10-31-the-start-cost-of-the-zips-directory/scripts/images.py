import sys
from pathlib import Path
from wasi_python import Artifacts, run, make_snapshot
ART = Path(sys.argv[1])
a = Artifacts(snapshot=ART/"python-snapshot.wasm", plain=ART/"python.wasm", stdlib_zip=ART/"python-stdlib.zip", manifest=ART/"MANIFEST")
C = str(Path(__file__).parent / "cache")
P = "'/usr/local/lib/python315.zip'"
IMAGES = {
 "I0 nothing": "pass",
 "I1 copy of the directory (new keys, new tuples)": f"import zipimport as z\nd=z._zip_directory_cache[{P}]\nX={{(k+'\\0')[:-1]: (v and tuple(list(v))) for k,v in d.items()}}",
 "I2 9379 new strings in a list": f"import zipimport as z\nd=z._zip_directory_cache[{P}]\nX=[(k+'\\0')[:-1] for k in d]",
 "I3 dict of 9379 small ints": "X=dict.fromkeys(range(9379))",
 "I4 two copies": f"import zipimport as z\nd=z._zip_directory_cache[{P}]\nX=[{{(k+'\\0')[:-1]: (v and tuple(list(v))) for k,v in d.items()}} for _ in range(2)]",
}
for name, code in IMAGES.items():
    snap = make_snapshot(code, artifacts=a, cache_dir=C)
    for call in ("pass", "pass"):
        r = run(["-c", call], artifacts=a, snapshot=snap, fuel=10**13, cache_dir=C)
        print(f"{name}\t{call}\t{r.fuel_used}\t{r.exit_code}\t{snap.origin.image_bytes}", flush=True)
