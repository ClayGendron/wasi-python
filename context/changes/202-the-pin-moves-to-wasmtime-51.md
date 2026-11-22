# 202: The pin moves to wasmtime 51

## Changelog

### Security

- **On Windows, a drive letter no longer reaches host files.** wasmtime 51 refuses a `:` in any path. Before, any guest could read a name such as `/usr/local/lib/C:secret` from drive C's current folder, with nothing granted, and write through a writable folder or `root=True` (GHSA-f2pq-268w-886c, High). Your own wasmtime needs 51.0.0, 50.0.3, 49.0.7, 48.0.10 or 36.0.22. [Security model](https://claygendron.github.io/wasi-python/explanation/security-model/)
- **wasmtime's other fixes since 50.0.0 are carried.** None of them reached the runner. A guest's empty writes, for one, never reach the output stream that one of them is about. [Security model](https://claygendron.github.io/wasi-python/explanation/security-model/)
- **The engine refuses WebAssembly GC types.** The runtime uses exceptions but none of the GC proposal's structs and arrays, so the runner now turns that proposal off. A module that declares one is refused. [Security model](https://claygendron.github.io/wasi-python/explanation/security-model/)

### Fixed

- **Removing a folder named with a trailing slash works on a mount.** `os.rmdir("logs/")` now removes an empty `logs` on a mount, as it does on a granted folder under wasmtime 51 and on Linux. It answered EINVAL before. [The guest's files](https://claygendron.github.io/wasi-python/reference/guest-filesystem/)

### Upgrading

- **wasmtime 51 is required.** The wheel requires `wasmtime>=51,<52`. Fuel figures change slightly, since fuel is counted by the new engine. [Support and versioning](https://claygendron.github.io/wasi-python/reference/support-and-versioning/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "202"
new = ["tests/checks/test_v1_2_hostile_guest.py::test_a_drive_prefixed_name_stays_in_its_folder"]
units = 0
```
