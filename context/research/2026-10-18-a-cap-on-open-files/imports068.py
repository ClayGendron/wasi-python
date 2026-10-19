import sys, wasmtime
e = wasmtime.Engine()
for name in ("python.wasm", "python-snapshot.wasm"):
    m = wasmtime.Module.from_file(e, sys.argv[1] + "/" + name)
    names = sorted(i.name for i in m.imports if i.module == "wasi_snapshot_preview1")
    print(name, len(names), names)
