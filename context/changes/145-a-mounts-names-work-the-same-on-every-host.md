# 145: A mount's names work the same on every host

## Changelog

### Fixed

- **A mount refuses a path component with a backslash or a colon with `EINVAL` on every host, and its `pread` and directory-open answers follow wasmtime's** (spec 145). A provider never sees a name a host could read as a separator or a drive; the mount contract in the how-to and the `FileProvider` docstring now say what a component may hold, and that a provider joins components onto a host folder one at a time. `fd_pread` past one 64 KiB chunk writes the chunk it judged, and an `O_DIRECTORY` open asks `stat` first and answers `ENOTDIR` for a file without asking `list`, so a listing of a folder below the mount costs one `stat` more. A guest cannot name a file with a colon on a mount, such as `12:30.csv`, where it can on a Linux or macOS grant.

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "145"
new = ["tests/checks/test_v1_2_hostile_guest.py::test_a_mount_refuses_a_name_a_host_could_reinterpret"]
units = 4
```
