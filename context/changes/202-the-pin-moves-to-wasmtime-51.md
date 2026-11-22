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
new = [
    "tests/checks/test_v1_2_hostile_guest.py::test_a_drive_prefixed_name_stays_in_its_folder",
    "tests/checks/test_v1_4_embedding.py::test_one_large_write_arrives_whole",
]
# The pin's text rows, which now say >=51,<52, and the slash rows of the rename rule, whose
# answers are re-derived on three systems under wasmtime 51 with their safety assertions kept.
changed = [
    "tests/checks/test_v1_4_embedding.py::test_a_plain_install_brings_wasmtime",
    "tests/checks/test_v1_4_embedding.py::test_a_wasmtime_that_cannot_load_is_named",
    "tests/checks/test_v1_2_hostile_guest.py::test_a_trailing_slash_rename_rule",
    "tests/checks/test_v1_2_hostile_guest.py::test_a_trailing_slash_symlink_rename_cannot_escape",
]
grows = ["tests/checks/test_v1_1_artifact_set.py::test_binary_is_a_core_wasm_module[snapshot]"]
growth = "the snapshot is made again by wasmtime wizer 51.0.0, the build's command line on the runner's new line, so its bytes change; python.wasm and the stdlib zip are not made by wasmtime and keep theirs. Every metered check's fuel is counted by wasmtime 51.0.0 and recorded fresh, not compared, as on every move of the engine"
# Unit rows (tallied, not named): test_the_engines_refuse_gc_types, metered and not, is new;
# the two engine-settings rows gain ("wasm_gc", False); the write parity's rmdir 'e/' and 'd/'
# rows pass with the mount following the grant, and the namespace check gains a slash-named
# rmdir above a nested preopen (EBUSY); the read parity's four pread rows past 2**63 are a
# deliberate difference, the mount's EINVAL asserted on every system and the grant's EINTR.
units = 2
```
