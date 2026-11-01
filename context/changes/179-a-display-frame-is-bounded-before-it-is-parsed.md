# 179: A display frame is bounded before it is parsed

## Changelog

### Security

- **A display frame costs the host a few times its length.** With `results=True`, a guest could send a display frame of empty objects that made the host hold about fifty times the frame before refusing it. A frame that holds more values than a display needs is now refused before it is parsed. [Security model](https://claygendron.github.io/wasi-python/explanation/security-model/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "179"
new = ["tests/checks/test_v1_2_hostile_guest.py::test_a_display_frame_costs_the_host_about_its_length*"]
units = 3
```
