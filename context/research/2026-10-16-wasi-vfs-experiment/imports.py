"""Print a module's import namespaces (with counts) and its exports.  Usage: imports.py <wasm>..."""

import collections
import sys

import wasmtime

engine = wasmtime.Engine()
for path in sys.argv[1:]:
    module = wasmtime.Module.from_file(engine, path)
    spaces = collections.Counter(i.module for i in module.imports)
    print(path.rsplit("/", 2)[-2] + "/" + path.rsplit("/", 1)[-1])
    print("  imports:", dict(spaces))
    print("  wasi:", sorted(i.name for i in module.imports if i.module == "wasi_snapshot_preview1"))
    print("  exports:", sorted(e.name for e in module.exports))
