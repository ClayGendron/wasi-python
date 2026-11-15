# 186: The signature check reads the file the read-back judged

## Changelog

### For contributors

- **A release's signature check no longer waits on PyPI's index page.** The read-back hands the verifier the wheel's address on PyPI's file host, so a lagging index page cannot fail a published release, and a version holding any file but the release's wheel is red. [The release process](https://claygendron.github.io/wasi-python/contributing/release-process/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "186"
units = 14
[claim.judge]
"tests/harness/scan.py" = "rule 21: the read-back writes the wheel's address with --url-out and the signature check verifies that address in pypi-verify and pypi-rehearsal, in place of a pypi: name that sends the verifier to the lagging Simple API (0.1.4's tag run 42110186903)"
"tests/unit/test_pypi_readback.py" = "the read-back keeps the wheel's address, refuses any other file for the version (the 0.1.4 security review's L1) and an address not in PyPI's own shape on its file host, and reads no Simple API"
```
