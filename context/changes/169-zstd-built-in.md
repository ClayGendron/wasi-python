# 169: zstd, built in

## Changelog

### New

- **Zstandard compression works.** `compression.zstd` is built in over libzstd 1.5.7, so `tarfile`'s `zst` modes, `zipfile`'s `ZIP_ZSTANDARD` and `shutil`'s `zstdtar` format work, and write native Python's bytes. It runs on one thread, and frames from before zstd 0.8 do not decode. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)
- **pandas reads and writes `.zst` files.** `compression="zstd"` and a `.zst` suffix now use the standard library's `compression.zstd`, since the set has no python-zstandard. `level` is honoured when writing; any other option raises `TypeError`. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)

### For contributors

- **A carried patch gives pandas the standard library's zstd.** `recipes/patches/pandas-3.1.0/0002-zstd-from-the-standard-library.patch` opens a `compression.zstd.ZstdFile` in `get_handle` when python-zstandard does not import, and refuses any option but `level` on write. [Carrying a patch](https://claygendron.github.io/wasi-python/contributing/carrying-a-patch/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "169"
new = [
  "tests/checks/test_v1_3_data_stack.py::test_zstd_files_job_matches_native",
  "tests/checks/test_v1_3_data_stack.py::test_pandas_zstd_reads_and_writes_through_the_standard_library",
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_source_tree_matches_its_tarball[zstd]",
]
passes = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-b]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-archives]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-fs]",
]
grows = ["tests/checks/*"]
growth = "libzstd 1.5.7 is linked into _zstd, and shutil, tempfile (through shutil) and zipfile now import compression.zstd at module top, as CPython's own build does. Measured on darwin arm64 against 165's set (dev at 28a1e7cf): python.wasm 99,492,553 to 99,977,838 bytes (+485,285), python-snapshot.wasm 104,660,252 to 105,151,156 (+490,904), the zip +377 (the patch); import shutil 409,965,881 to 420,398,638 fuel on python.wasm (+2.54%) and 85,165,046 to 95,553,453 on the snapshot (+12.2%), import pandas +0.08% and +0.16%, a bare start unchanged; the wheel, built by hand from each set, 99,478,846 to 99,729,163 bytes (+250,317), 5,128,437 under 104,857,600. CPython's test_zstd now runs: cpython-b 9,573 to 9,687 passes, 296.7 G to 302.8 G; cpython-archives 1,336 to 1,505 passes (zstd cases of test_tarfile, test_zipfile and test_zipimport), 167.8 G to 172.1 G; cpython-fs 3,738 to 3,739 passes (test_shutil's), 64.1 G to 64.3 G"
units = 1
[claim.judge]
"tests/upstream/packages.toml" = "zstd is a component of the set, reached through compression.zstd, which joins stdlib_modules"
"tests/upstream/python/cpython-release-archives.txt" = "test_zipimport's two Zstandard ZIP64 tests skip for want of the largefile resource in cpython-archives, as their Deflate and stored kin do, so the release group runs them"
"tests/upstream/python.toml" = "cpython-release-archives runs the two Zstandard ZIP64 tests too: measured 248.9 G on darwin arm64 (99.7 G before), its cap 150 G to 380 G, 1.5 times the measure"
"context/release-claims/169-zstd-built-in.toml" = "169's block: cpython-release-archives' new passes and its fuel"
```
