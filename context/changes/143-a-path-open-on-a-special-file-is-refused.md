# 143: a path_open on a special file is refused

## Changelog

### Security

- A guest's open of a FIFO, socket or device file in a granted folder is refused with `ENXIO` before wasmtime opens it, so it can no longer hold a call past its deadline and `cancel`, or `Session.close()`; with `O_DIRECTORY` it answers `ENOTDIR`, and a write-open of one on a read-only grant answers `ENXIO`, or `ENOTDIR` with `O_DIRECTORY`, where wasmtime answered `EPERM`.

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "143"
new = [
    "tests/checks/test_v1_2_hostile_guest.py::test_an_open_of_a_fifo_in_a_grant_returns_refused[read-only]",
    "tests/checks/test_v1_2_hostile_guest.py::test_an_open_of_a_fifo_in_a_grant_returns_refused[writable]",
    "tests/checks/test_v1_2_hostile_guest.py::test_a_link_a_guest_makes_to_a_fifo_is_refused",
    "tests/checks/test_v1_2_hostile_guest.py::test_a_session_whose_turn_opens_a_fifo_closes[read-only]",
    "tests/checks/test_v1_2_hostile_guest.py::test_a_session_whose_turn_opens_a_fifo_closes[writable]",
]
units = 30
```
