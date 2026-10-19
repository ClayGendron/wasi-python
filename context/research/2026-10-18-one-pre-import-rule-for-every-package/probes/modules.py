import pathlib, sys
HERE = pathlib.Path("/Users/claygendron/Git/Repos/wasi_python"); sys.path.insert(0, str(HERE / "tests/harness"))
import guest
S = pathlib.Path(__file__).resolve().parent.parent
ZIP = HERE / "build/sets/s-4eb5418a2b1bb553/python-stdlib.zip"
for label, wasm in [("A", S/"work/A/python-snapshot.wasm"), ("D", S/"work/D/python-snapshot.wasm"), ("B", S/"work/B/python-snapshot.wasm"), ("C", S/"work/C/python-snapshot.wasm"), ("plain", HERE/"build/sets/s-4eb5418a2b1bb553/python.wasm")]:
    r = guest.run(wasm, ["-c", "import sys; print(len(sys.modules))"], workdir=S/"runs"/"mods", python_version="3.15", stdlib=ZIP)
    print(label, "modules at start", r.text.strip(), r.describe() if r.exit_code else "")
