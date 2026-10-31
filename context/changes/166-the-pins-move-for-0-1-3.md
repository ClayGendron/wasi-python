# 166: the pins move for 0.1.3

## Changelog

### Security

- **tarfile's `tar` filter refuses a link to its own destination.** CPython 3.15.2 makes `tarfile.tar_filter` reject a link member whose path resolves to the destination folder itself, as `data_filter` already did ([gh-160097](https://github.com/python/cpython/issues/160097)). [Security model](https://claygendron.github.io/wasi-python/explanation/security-model/)
- **`http.cookiejar` ignores cookies with a negative version.** CPython 3.15.2's `DefaultCookiePolicy` no longer accepts or returns them without checking their domain against the request's host ([gh-160300](https://github.com/python/cpython/issues/160300)). [Security model](https://claygendron.github.io/wasi-python/explanation/security-model/)
- **The XML parser is libexpat 2.9.0.** CPython 3.15.1 updates the libexpat that `xml.etree`, `xml.dom.minidom` and `pyexpat` parse with ([gh-157953](https://github.com/python/cpython/issues/157953)). [Security model](https://claygendron.github.io/wasi-python/explanation/security-model/)
- **pypdf's limits on hostile PDFs are inside.** pypdf 6.21.4, from 6.21.1, bounds cross-reference tables and copied page attributes, detects a missing end of file and a cloning loop, and uses the validated page count after decryption. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)

### Upgrading

- **CPython 3.15.2 and numpy 2.5.4 inside.** Bug-fix releases, from 3.15.0 and 2.5.2. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)
- **soupsieve, wrapt and tzdata move to their newest fixes.** soupsieve 3.0.4, wrapt 2.5.2 and tzdata 2026.6, from 3.0.3, 2.5.1 and 2026.5. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)
- **Saved snapshots are made again.** The binary and the zip change, so a `Snapshot` saved with 0.1.2 raises `SnapshotMismatch`. Make it again after you upgrade. [Snapshots](https://claygendron.github.io/wasi-python/how-to/snapshots/)

### For contributors

- **The build's wasmtime is the runner's line.** The snapshot is made by wasmtime 50.0.1, not 49.0.3. [Building](https://claygendron.github.io/wasi-python/contributing/building/)
- **The carried patches follow their pins.** `recipes/patches/numpy-2.5.4/0001-npy-files-without-dup.patch`, `recipes/patches/numpy-2.5.4/0002-callback-signatures.patch` and `recipes/patches/pypdf-6.21.4/0001-tests-import-ssl-where-it-is-used.patch` are re-made against their new tarballs, each with the same changed lines. [Carrying a patch](https://claygendron.github.io/wasi-python/contributing/carrying-a-patch/)

## Package rows

| numpy | 2.5.4 | Built in. Linear algebra, `dot` and `matmul` run on the set's OpenBLAS 0.3.34, as native numpy's do. The default integer is 32-bit. |
| statsmodels | 0.15.0 | Every public submodule, `statsmodels.api` and `statsmodels.formula.api` included, with formulaic 1.2.2 (with interface-meta 2.0.1 and wrapt 2.5.2) as a second formula engine. Sixteen public-domain datasets ship. |

## Claims

```toml
[[claim]]
spec = "166"
new = [
  "tests/checks/test_rules.py::test_the_builds_wasmtime_is_the_runners_line",
  "tests/checks/test_v1_2_hostile_guest.py::test_deep_data_raises[hash-tuple]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_host[cpython-fs-win-logging-emit-reopen-error]",
]
retired = ["tests/checks/test_v1_2_hostile_guest.py::test_deep_data_limits[hash-tuple]"]
changed = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[cpython-a-no-test-modules]",
  "tests/checks/test_v1_3_data_stack.py::test_numpy_linalg_errors_are_native_numpy_on_openblas*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[tqdm-smoke-no-asyncio-loop-error]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[tqdm-smoke-no-threads-error]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[tqdm-smoke-no-threads]",
]
passes = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-a]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-archives]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-b]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-c]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-fs]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[numpy-core]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[numpy-lib]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[numpy-others]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pypdf-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[soupsieve-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[wrapt-smoke]",
]
fewer = "soupsieve-smoke runs tests/test_level1 alone, 35 passes where it ran 88: soupsieve 3.0.4's test_api.py adds two tests that match a selector for each of about 63,000 code points (about 141 G of guest fuel), past the 100 G a smoke group may measure, so test_api.py, whole, runs in the release tier's path group soupsieve-r, which holds every one of its tests (400 passes, from 342)"
grows = ["tests/checks/*"]
growth = "the pins move: CPython 3.15.2 (with mimalloc 2.5, which its tarball vendors), numpy 2.5.4, pypdf 6.21.4, soupsieve 3.0.4, wrapt 2.5.2 and tzdata 2026.6 change every guest's code, so any metered check's fuel and the set's bytes may move. Measured on darwin arm64 against dev's set: python.wasm +65,549 bytes (+0.066%), the snapshot +58,519 (+0.056%), the zip -85,957 (-0.159%), the wheel -44,056 (-0.045%, 98,327,639 bytes); numpy's, pandas' and CPython's 16 normal groups +0.507% in sum (median +0.157%, from -0.525% to +3.197%: cpython-a, which also runs 3.15.2's four new free-threading modules and 33 more passing tests, and numpy-core, +233 passing tests)"
units = 1
[claim.judge]
"tests/upstream/python/cpython-a.txt" = "CPython 3.15.2 adds four test_free_threading modules (test_bytes_object, test_datetime, test_os, test_weakref); regrtest lists every module and the plan places each, so they join their siblings in cpython-a, sorted"
"tests/upstream/python/cpython-b.txt" = "CPython 3.15.2 removes test_cppext, so it leaves its list"
"tests/upstream/expected/cpython-a/no-test-modules.txt" = "three new tests of 3.15.2's test_traceback (CPythonSuggestionFormattingTests.test_name_error_with_bad_getattr, _getattribute, _property) need _testcapi, the class's cause, and match its pattern"
"tests/known_gaps.toml" = "cpython-a-no-test-modules counts its three new members, 143 findings; tqdm-smoke's three classes trade two tests of tests_perf.py, their digests move; the Windows host entry win-logging-emit-reopen-error has its gap"
"tests/upstream/python.toml" = "the host entry win-logging-emit-reopen-error: test_logging's test_emit_reopen_error, new in 3.15.2, errors on a Windows host, which refuses to remove a folder holding a file the guest holds open (CPython itself skips the test on Windows; run 41170628147); passed on Linux and macOS"
"tests/upstream/expected/tqdm-smoke/no-asyncio-loop-error.txt" = "under CPython 3.15.2 the stray event loop of tqdm's asyncio tests is collected during test_iter_overhead_simplebar_hard (an unraisable BaseEventLoop.__del__), no longer during test_iter_basic_overhead, so the two trade places, each with this class's cause and pattern"
"tests/upstream/expected/tqdm-smoke/no-threads-error.txt" = "test_iter_basic_overhead now errors with the monitor thread's cause (instances still in existence) and test_iter_overhead_simplebar_hard leaves, the trade above"
"tests/upstream/expected/tqdm-smoke/no-threads.txt" = "test_iter_basic_overhead now fails with TqdmMonitorWarning (no threads) and test_iter_overhead_simplebar_hard leaves, the trade above"
"context/release-claims.toml" = "166's first pull request appends its release-tier claim block: pypdf-r's and soupsieve-r's passes, and the release groups whose fuel moves under CPython 3.15.2, numpy 2.5.4 and soupsieve 3.0.4"
"tests/upstream/soupsieve.toml" = "soupsieve 3.0.4's wheel; test_api.py leaves the smoke group for the release tier (its two new exhaustive tests measure about 141 G, past a smoke group's 100 G): soupsieve-smoke runs tests/test_level1, 15.1 G measured on darwin, cap 23 G by the 1.5 rule; soupsieve-r runs every other file, test_api.py with it, 185.8 G, cap 280 G; the budget is their sum, 303 G"
"tests/upstream/pypdf.toml" = "pypdf 6.21.4's wheel"
"tests/upstream/wrapt.toml" = "wrapt 2.5.2's wheel"
"tests/upstream/tzdata.toml" = "tzdata 2026.6's wheel"
```
