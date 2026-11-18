# 198: Bound raw host requests

## Changelog

### Security

- **Raw host requests are bounded.** The runner checks the length before copying a request out of the guest or calling your function. [Defaults and limits](https://claygendron.github.io/wasi-python/reference/defaults-and-limits/)

### Upgrading

- **Raw requests default to 1 MiB each.** If your host function accepts larger requests, set `max_host_request_bytes=` when you open a session or run a program. [Defaults and limits](https://claygendron.github.io/wasi-python/reference/defaults-and-limits/)

## Claims

```toml
[[claim]]
spec = "198"
new = ["tests/checks/test_v1_4_embedding.py::test_each_entry_limits_raw_host_requests"]
units = 2
[claim.judge]
"tests/public_api.txt" = "run, run_async and Session take max_host_request_bytes; Defaults appends host_request_bytes"
"tests/checks/test_rules.py" = "the existing run, run_async and Session opening each add five lines for the parameter, documentation and forwarding; the instance adds eleven to pass the checked bound to its call"
```
