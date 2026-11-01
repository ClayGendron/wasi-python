# 179: A display frame is bounded before it is parsed

## Changelog

### Security

- **A display frame no longer costs the host fifty times its size.** With `results=True`, a guest could send a display frame of empty objects, or of text far past `output_bytes`, that the host parsed whole before refusing it. Such a frame is now answered before it is parsed. [Security model](https://claygendron.github.io/wasi-python/explanation/security-model/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "179"
new = ["tests/checks/test_v1_2_hostile_guest.py::test_a_display_frame_costs_the_host_about_its_length*"]
units = 5
```
