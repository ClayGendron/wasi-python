# 145: A mount's names work the same on every host

## Changelog

### Fixed

- **A mount answers times, reads and folder opens as a grant does.** Setting the times of a missing file answers `ENOENT`, a positioned read of more than 64 KiB returns exactly the bytes asked for, and opening a file as a folder answers `ENOTDIR` without listing it. [Know how a mount differs from a grant](https://claygendron.github.io/wasi-python/how-to/mounts/#know-how-a-mount-differs-from-a-grant)

### Upgrading

- **A mount refuses file names with `:` or `\`.** On Linux and macOS a mount accepted them before; now every host answers `EINVAL`, as Windows always did. A guest that writes timestamped names such as `12:30.csv` into a mount should use another separator. [Treat a path as a name, not a host path](https://claygendron.github.io/wasi-python/how-to/mounts/#treat-a-path-as-a-name-not-a-host-path)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "145"
new = ["tests/checks/test_v1_2_hostile_guest.py::test_a_mount_refuses_a_name_a_host_could_reinterpret"]
units = 7
```
