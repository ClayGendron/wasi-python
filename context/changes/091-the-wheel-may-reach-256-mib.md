# 091: The wheel may reach 256 MiB

## Changelog

### For contributors

- **The wheel's size check allows 256 MiB.** The check that the wheel fits PyPI now reads 256 MiB, the file limit asked of PyPI, in place of PyPI's default 100 MiB, so packages past the default can land; a release with a larger wheel is not uploaded to PyPI until PyPI grants it. [The release process](https://claygendron.github.io/wasi-python/contributing/release-process/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "091"
```
