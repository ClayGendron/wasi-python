# 143: a path_open on a special file is refused

## Changelog

### Security

- **A FIFO or device in a grant no longer stalls a call.** The guest's open of such a file is refused with `ENXIO` before the host opens it, so a deadline, `cancel` and `Session.close()` stop the call as they stop any other. [Grant a folder](https://claygendron.github.io/wasi-python/how-to/grants/#grant-a-folder)

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
units = 34
```
