# 166: the pins move for 0.1.3

## Changelog

### Security

- **tarfile's `tar` filter refuses a link to its own destination.** CPython 3.15.2 makes `tarfile.tar_filter` reject a link member whose path resolves to the destination folder itself, as `data_filter` already did ([gh-160097](https://github.com/python/cpython/issues/160097)). [Security model](https://claygendron.github.io/wasi-python/explanation/security-model/)
- **`http.cookiejar` ignores cookies with a negative version.** CPython 3.15.2's `DefaultCookiePolicy` no longer accepts or returns them without checking their domain against the request's host ([gh-160300](https://github.com/python/cpython/issues/160300)). [Security model](https://claygendron.github.io/wasi-python/explanation/security-model/)
- **The XML parser is libexpat 2.9.0.** CPython 3.15.1 updates the libexpat that `xml.etree`, `xml.dom.minidom` and `pyexpat` parse with ([gh-157953](https://github.com/python/cpython/issues/157953)). [Security model](https://claygendron.github.io/wasi-python/explanation/security-model/)
- **pypdf's limits on hostile PDFs are inside.** pypdf 6.21.4, from 6.21.1, bounds cross-reference tables and copied page attributes, detects a missing end of file and a cloning loop, and uses the validated page count after decryption. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)

### Upgrading

- **CPython 3.15.2 and numpy 2.5.4 inside.** Bug-fix releases, from 3.15.0 and 2.5.2. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)
- **pandas 3.1.0 inside.** A new minor release, from 3.0.6; read pandas' 3.1.0 notes for code that relies on what it changed. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)
- **soupsieve, wrapt and tzdata move to their newest fixes.** soupsieve 3.0.4, wrapt 2.5.2 and tzdata 2026.6, from 3.0.3, 2.5.1 and 2026.5. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)
- **Saved snapshots are made again.** The binary and the zip change, so a `Snapshot` saved with 0.1.2 raises `SnapshotMismatch`. Make it again after you upgrade. [Snapshots](https://claygendron.github.io/wasi-python/how-to/snapshots/)
- **Hashing a deeply nested tuple raises sooner.** CPython 3.15.2 checks the C stack while it hashes a tuple, so a tuple nested more than a few thousand levels deep raises `RecursionError`, as `repr` and `==` already did. 0.1.2 hashed about 40,000 levels, then ended the call with a trap. [Limitations](https://claygendron.github.io/wasi-python/reference/limitations/)

### For contributors

- **The build's wasmtime is the runner's line.** The snapshot is made by wasmtime 50.0.1, not 49.0.3. [Building](https://claygendron.github.io/wasi-python/contributing/building/)
- **The carried patches follow their pins.** `recipes/patches/numpy-2.5.4/0001-npy-files-without-dup.patch`, `recipes/patches/numpy-2.5.4/0002-callback-signatures.patch` and `recipes/patches/pypdf-6.21.4/0001-tests-import-ssl-where-it-is-used.patch` are re-made against their new tarballs, each with the same changed lines. [Carrying a patch](https://claygendron.github.io/wasi-python/contributing/carrying-a-patch/)
- **pandas' carried patch follows its pin.** `recipes/patches/pandas-3.1.0/0001-styler-templates-from-a-zip.patch` is re-made against pandas 3.1.0's tarball, with the same changed lines. [Carrying a patch](https://claygendron.github.io/wasi-python/contributing/carrying-a-patch/)
- **pandas' C++20 builds for the guest by its cross file.** xsimd's emulated architecture declares the SIMD API pandas' scalar path names, and pandas' fast_float takes a namespace of its own beside scipy's older copy. [Adding a package](https://claygendron.github.io/wasi-python/contributing/adding-a-package/)

## Package rows

| numpy | 2.5.4 | Built in. Linear algebra, `dot` and `matmul` run on the set's OpenBLAS 0.3.34, as native numpy's do. The default integer is 32-bit. |
| pandas | 3.1.0 | Built in, including `read_html`, `read_xml` and `to_xml` through lxml, `.xlsx` through openpyxl and xlsxwriter, and the Styler. |
| statsmodels | 0.15.0 | Every public submodule, `statsmodels.api` and `statsmodels.formula.api` included, with formulaic 1.2.2 (with interface-meta 2.0.1 and wrapt 2.5.2) as a second formula engine. Sixteen public-domain datasets ship. |

## Claims

```toml
[[claim]]
spec = "166"
changed = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pandas-io-parser-no-mmap]"]
passes = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pandas-frame]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pandas-groupby]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pandas-internals]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pandas-io-formats]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pandas-io-parser]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pandas-libs]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pandas-reshape]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pandas-tslibs]",
]
grows = ["tests/checks/*"]
growth = "pandas 3.1.0, from 3.0.6, with its C++20 tokenizer (fast_float 8.2.10) and its xsimd moments, changes the guest's code and the zip, so any metered check's fuel and the set's bytes may move. Measured on darwin arm64 against the first pull request's set: python.wasm +1,140,570 bytes (+1.146%), the snapshot +1,141,489 (+1.092%), the zip +333,477 (+0.620%), the wheel +858,967 (+0.874%, 99,186,606 bytes, 813,394 under 100,000,000); the own checks measured, 159 rows, +0.419% in sum (median -0.001%, at most +1.81%, the import of numpy and pandas); pandas' eight normal groups +2.92% in sum (1,217.6 G to 1,253.2 G) with 5,254 more passes. pandas-io-parser grows from 94.4 G to 182.2 G: 3.1.0's new test_parallel_read.py (79.7 G in a session of its own) and 1,311 more passing tests, its cap rising to keep its headroom; pandas-frame +5.1% with 3,031 more passes; every other pandas group falls"
[claim.judge]
"tests/upstream/pandas.toml" = "pandas-io-parser's cap rises from 135 G to 261 G past a measured 182.2 G (darwin, this head's set), keeping its former headroom of 1.431; pandas-slow-b gains two classes, no-mmap (pandas 3.1.0's parallel reader maps its file) and wasm32-int32 (a test that builds its expected categories with numpy's 32-bit default integer), each with its closer"
"tests/upstream/expected/pandas-io-parser/no-mmap.txt" = "sixteen of pandas 3.1.0's new test_parallel_read.py tests and test_memory_map_multichar_sep[python] fail on the missing mmap, the class's cause, and match its pattern: 57 members"
"tests/upstream/expected/pandas-slow-b/no-mmap.txt" = "a new class: nine slow tests of pandas 3.1.0's test_parallel_read.py call the parallel reader, which maps its file"
"tests/upstream/expected/pandas-slow-b/wasm32-int32.txt" = "a new class: test_categorical_dtype_high_cardinality_numeric's three cases build their expected categories with numpy's default integer, 32 bits on wasm32, while read_csv infers int64 categories as natively"
"tests/known_gaps.toml" = "pandas-io-parser-no-mmap counts its 57 findings; pandas-slow-b-no-mmap (9) and pandas-slow-b-wasm32-int32 (3) are new gaps closed by docs/reference/limitations.md"
"context/release-claims.toml" = "166's second pull request appends its release-tier claim block: pandas-slow-a's and pandas-slow-b's pass counts, slow-b's two new classes, and the dependent families' release groups under pandas 3.1.0"
```
