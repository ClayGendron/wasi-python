# 180: A tag stops before it signs a wheel PyPI would refuse

## Changelog

### For contributors

- **A tag no longer signs a wheel PyPI would refuse.** When a tag uploads to PyPI, the release workflow compares the wheel with the limit PyPI has granted (the repository variable `PYPI_FILE_LIMIT_GRANTED`, or 100 MiB) and stops before anything is signed or published. A refusal for size is re-run once PyPI raises the limit. [The release process](https://claygendron.github.io/wasi-python/contributing/release-process/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "180"
new = ["tests/checks/test_rules.py::test_a_tag_refuses_a_wheel_past_pypis_grant[*"]
units = 5
```
