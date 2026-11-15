# 189: The package imports itself by name

## Changelog

### For contributors

- **The package imports its own modules by name.** Every import of a sibling under `src/` reads `from wasi_python.x import y`, and ruff refuses a relative import anywhere it lints, the guest package excepted. Nothing an embedder sees changes. [Principles](https://claygendron.github.io/wasi-python/contributing/principles/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "189"
new = []
retired = []
changed = []
passes = []
grows = []
units = 1
[claim.judge]
"pyproject.toml" = "ruff selects TID252 with every relative import banned, and excepts the guest package's four files, which the guest imports as host and the unit checks load under a private name; a rule added, none loosened"
"tests/unit/test_runner_package.py" = "the shape check reads an import of the package by name as its relative twin, at its own line, so its order, by-name and seam checks judge the same 172 imports and 146 by-name entries as before; a new check refuses import wasi_python and import wasi_python.x at any depth, the one form the walker does not read; ORDER, LATE and the other lists are unchanged"
"tests/checks/test_v1_4_public_api.py" = "the re-export stand-in is planted in the package's new form, from wasi_python.runner; the same one finding is expected"
"tests/unit/test_wasmtime_ffi.py" = "a comment names the import's new form; no assertion changes"
```
