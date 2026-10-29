# The release-tier claims, by release

`release/version.py date` moves the ledger's blocks (`release-tier-claims.toml`) here, under the version it dates, before the release pull request, and the ledger starts empty again; the release pull request's gather and acceptance read the version's blocks, with any appended since, as their claims (`progress/README.md`, "The release tier"). Until 0.1.0 the release acceptance moved them.

## 0.1.2

Moved by `release/version.py date` on 2026-10-29, before the release pull request.

```toml
[[claim]]
spec = "157"
grows = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[*"]
growth = "the reactor gains the export `prepare`, a prepared instance's ending and five reseeds in `_refresh`, so both binaries are larger and every run unmarshals and refreshes a little more"
[claim.judge]
"context/release-tier-claims.toml" = "this block: the reason the upstream suites' fuel grows with 157's new reactor code, for the release pull request's acceptance"
```

## 0.1.1

Moved by `release/version.py date` on 2026-10-27, before the release pull request.

No block was in the ledger at the date.

One block was appended after the date, by 127's landing documents (`607b2d79`, pull request #25): it named every upstream suite's dropped fuel as a growth, since the move to wasmtime 50.0.1 left the release-tier groups, which run on Linux alone in CI, no fuel of the new engine. The release pull request's acceptance (`898bc091`) read it as its one growth reason. 154 removed it from the ledger before 0.1.2's date, since the acceptance from CI's record now records Linux's fuel, labelled, for a check only Linux ran when no fuel darwin measured under the current engine is accepted, so an engine move drops no such row's fuel; left in the ledger, the date would have moved it under 0.1.2, where its prefix would clear a real fuel growth. It is quoted here in a `text` fence, which the release's claims do not read:

```text
[[claim]]
spec = "127"
grows = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[*"]
growth = "the upstream suites' fuel was last measured on darwin under wasmtime 49.0.0, and 127 moved the engine to 50.0.1; in CI the upstream groups run on Linux alone, whose fuel is not ratcheted, so the acceptance keeps no fuel of the other engine for these rows until a darwin run of the release tier measures them again"
[claim.judge]
"context/release-tier-claims.toml" = "this block: the reason the upstream suites' fuel measured under wasmtime 49 is dropped at the first release-tier acceptance since 127 moved the engine"
```

## 0.1.0

Moved at the release acceptance on `eac93d0f` (history line 94, accepted in `1aa0eff7`), the first release acceptance: 102, 114, 095 and 067.

```toml
[[claim]]
spec = "102"
new = [
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[numpy-slow-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pandas-slow-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-release-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-slow-rest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pandas-slow-b-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[cpython-release-a-stdlib-zip-error]",
]
changed = [
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-filled-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-lines-*",
]
passes = []
grows = [
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-fs]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-a]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-b]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-c]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-1]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-rest]",
]
growth = "102: the regrtest driver's Z line (it names a module's denied resource) moves every CPython group's fuel on this set, EXECUTED on d0d91cef: cpython-fs +43.8 M (+6.9e-4), cpython-a +43.3 M (+1.56e-4), cpython-b +53.0 M (+1.79e-4), cpython-c +73.8 M (+1.77e-4); the thirteen staged release JSONs cost nothing (cpython-fs and cpython-b equal to the instruction with them staged and the base's driver); contourpy's normal groups run -m 'not slow' (contourpy-1 +0.28%, contourpy-rest +3.7e-4; the survey, on 142bdd38)"
retired = []
units = 113  # 112 before wave 11's integration review, L1, counted 113 per file

[[claim]]
spec = "114"
growth = "114: the zip's two members move every release-tier group's fuel both ways; passes unchanged"

[[claim]]
spec = "095"
# 261 release groups, their classes and three traps, all new: scipy 172 groups (63.66 T),
# scikit-learn 38 (9.72 T), statsmodels 51 (12.84 T), 86.22 T measured on darwin-arm64 by node id
# with --tier release (the build's passes 1 to 4, sets d0d91cef and 1556bbd5); the four smoke
# groups are normal-tier rows, not claimed here
new = [
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[scipy-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[scikit-learn-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[statsmodels-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[scipy-hypothesis-*",
]
changed = []
passes = []
grows = []
retired = []
units = 46  # tests/unit: 2,290 collected against main's 2,244

[[claim]]
spec = "067"
# 419 release groups of 23 families, their classes and seven traps, all new: 95.32 T measured
# on darwin-arm64 by node id with --tier release (sympy 80.92 T in 342 groups, the other 22
# families 14.40 T; sets d0d91cef and 1556bbd5, the judging set's MANIFEST with this
# specification's pins and patches), and the seven traps at 50 G each; the 42 smoke groups are
# normal-tier rows, not claimed here
new = [
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[fonttools-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pyparsing-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[packaging-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[python-dateutil-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[openpyxl-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[xlsxwriter-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pypdf-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[beautifulsoup4-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[soupsieve-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[jinja2-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[charset-normalizer-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[networkx-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[patsy-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[sympy-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[mpmath-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[attrs-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[more-itertools-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[joblib-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cloudpickle-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[narwhals-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[seaborn-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[reportlab-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[formulaic-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[sympy-slow-17141]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[fonttools-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pyparsing-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[python-dateutil-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[openpyxl-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pypdf-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[soupsieve-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[jinja2-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[charset-normalizer-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[networkx-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[mpmath-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[more-itertools-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[joblib-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[cloudpickle-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[narwhals-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[seaborn-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[reportlab-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[sympy-slow-*",
]
changed = []
passes = []
grows = [
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-filled-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-lines-*",
]
growth = "067: the package driver moves every package-driver group's fuel both ways; passes unchanged (the wave 12 integration review's M1 and L3)"
retired = []
units = 37  # tests/unit/test_pure_suites.py, a new file: 36 collected; tests/unit/test_fetch_trees.py: 1 more
```

Moved at the second release acceptance of 0.1.0, on `d33f0383` (history line 97; the record's SHA-256 `bed3e5f204f4a8dc0fe3aef361621bfa607c3665ba1f9575d5ee9f7bc64fd9ec`), compared with the record of the first (`8a26e68c`, SHA-256 `ecb68db9acfc5ca5c298cf461c65779ac4e00e8f6041a34f17459ac8692850b3`): 067 and 122. 122's 162 closer changes explained every difference; 067's two entries were already in the first record.

```toml
[[claim]]
spec = "067"
# After 0.1.0's release acceptance: networkx's test_asadpour_integral_held_karp leaves
# networkx-r-approximation-1 for a trap of its own: on Linux x86_64 it did not end within its
# group's 710 G cap (dry run 39741960669), against about 442 to 470 G on darwin-arm64, on the
# same artifact set and wasmtime, so the guest takes a different path on Linux, which may be the
# product's. The group runs its other 44 tests in 100,156,534,716 fuel (EXECUTED): one accepted
# pass fewer, by this reason, and less fuel.
new = [
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[networkx-r-trap-asadpour-integral-held-karp]",
]
changed = []
passes = [
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[networkx-r-approximation-1]",
]
grows = []
retired = []
units = 0

[[claim]]
spec = "122"
# The short README: the limitations it listed moved to docs/reference/limitations.md, and every
# known gap that named README.md as its closer names that page instead. A release-tier row changes
# its closer only; its status, need, area, facts and metrics are the same. Written by the lane at
# the release acceptance on d33f0383, where the comparison found these 162 rows and no other
# difference; 122 landed without its block.
new = []
changed = [
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[charset-normalizer-r-cli-writes-beside-input]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[charset-normalizer-r-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[cloudpickle-r-captured-stdout]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[cloudpickle-r-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[cpython-release-a-stdlib-zip-error]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[fonttools-r-doc-doctest-output]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[fonttools-r-rest-counted-clock]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[fonttools-r-rest-importlib-module-names]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[fonttools-r-rest-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[fonttools-r-rest-read-only-source]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[fonttools-r-rest-sdist-lacks-data]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[fonttools-r-rest-zip-no-source]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[fonttools-r-ttlib-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[jinja2-r-importlib-module-names]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[jinja2-r-no-asyncio-loop-error]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[jinja2-r-no-asyncio-loop]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[jinja2-r-read-only-source]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[jinja2-r-zip-package-loader]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[joblib-r-doc-doctest-output]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[joblib-r-joblib-cache-clock]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[joblib-r-no-asyncio-loop-error]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[joblib-r-no-asyncio-loop]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[joblib-r-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[joblib-r-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[more-itertools-r-counted-clock]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[more-itertools-r-doc-doctest-output]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[more-itertools-r-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[mpmath-r-doc-functions-2-doctest-output]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[mpmath-r-doc-libmp-doctest-output]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[mpmath-r-doc-matrices-doctest-output]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[narwhals-r-no-ctypes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[narwhals-r-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[narwhals-r-no-terminal-size]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[narwhals-r-wasm32-int32]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[networkx-r-doc-doctest-output]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[networkx-r-other-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[networkx-r-root-1-counted-clock]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[openpyxl-r-openpyxl-lxml-only]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[openpyxl-r-read-only-source]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pandas-slow-b-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pyparsing-r-pyparsing-no-railroad]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pyparsing-r-unit-6-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pypdf-r-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[python-dateutil-r-no-tzset]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[python-dateutil-r-tz-cache]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[reportlab-r-importlib-module-names]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[reportlab-r-pytest-collects-helper-error]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[reportlab-r-reportlab-data-folder]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[reportlab-r-reportlab-no-accel]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[reportlab-r-reportlab-reference-attributes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[reportlab-r-reportlab-tools-not-shipped]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-datasets-pillow-zlib-only-at-setup]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-decomposition-1-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-linear_model-1-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-linear_model-3-no-dev-null]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-linear_model-3-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-loss-to-cross_decomposition-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-metrics-no-mmap-at-setup]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-model_selection-3-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-neighbors-to-neural_network-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-preprocessing-to-semi_supervised-wasm32-int128]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-tests-1-1-no-openmp]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-tests-1-1-package-in-zip]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-tests-common-1-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-tests-common-2-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-tests-common-3-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-tests-common-4-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-tree-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-utils-no-mmap-estimator-checks]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-utils-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-integrate-1-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-interpolate-1-no-native-id-test-names]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-interpolate-1-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-interpolate-2-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-interpolate-fitpack2-1-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-io-harwell_boeing-to-io-enotsup-io-file-left-open-at-setup]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-io-harwell_boeing-to-io-enotsup-io-no-warning]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-io-harwell_boeing-to-io-enotsup-io]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-io-harwell_boeing-to-io-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-io-harwell_boeing-to-io-no-native-id-test-names]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-io-harwell_boeing-to-io-wasm32-memory]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-lib-to-fft-no-native-id-uarray]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-lib-to-fft-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-ndimage-to-optimize-trustregion_constr-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-optimize-1-1-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-optimize-1-2-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-optimize-2-no-fp-exceptions]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-optimize-3-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-optimize-3-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-signal-float32-rounding]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-signal-signaltools-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-smoke-slow-9-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-smoke-slow-9-wasm32-memory]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-sparse-1-no-fp-exceptions]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-sparse-csgraph-to-sparse-linalg-eigen-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-spatial-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-special-2-no-fp-exceptions]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-special-mpmath-10-mpmath-tolerance]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-special-mpmath-2-mpmath-tolerance]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-special-mpmath-37-mpmath-tolerance]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-special-mpmath-6-mpmath-tolerance]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-stats-1-mgc-3-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-stats-1-stats-5-no-fp-exceptions]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-stats-fit-1-fit-flat-likelihood]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-stats-fit-2-no-fp-exceptions]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[seaborn-r-1-newer-dependencies]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[seaborn-r-1-no-pyarrow-interchange]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[seaborn-r-3-no-pyarrow-interchange]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[seaborn-r-5-newer-dependencies]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[seaborn-r-5c-newer-dependencies]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[seaborn-r-6-newer-dependencies]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[seaborn-r-8-newer-dependencies]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[soupsieve-r-no-alarm]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-base-to-datasets-left-out-datasets]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-base-to-datasets-wasm-is-not-emscripten]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-discrete-discrete-1-left-out-datasets-at-setup]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-discrete-discrete-1-left-out-datasets]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-discrete-discrete-2-left-out-datasets]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-emplike-left-out-datasets-at-setup]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-emplike-left-out-datasets]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-genmod-left-out-datasets-at-setup]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-genmod-left-out-datasets]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-graphics-to-multivariate-factor_rotation-left-out-datasets]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-graphics-to-multivariate-factor_rotation-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-stats-4-upstream-xfail-platform]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-tests-to-treatment-left-out-datasets-at-setup]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-doc-1-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-doc-10-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-doc-11-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-doc-15-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-doc-2-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-doc-3-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-doc-6-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-doc-7-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-doc-8-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-docfiles-1-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-docfiles-2-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-docfiles-3-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-docfiles-4-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-docfiles-5-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-docfiles-6-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-docfiles-7-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-docfiles-8-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-docfiles-8b-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-docfiles-9-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-polys-2-s11-1-sympy-tooslow-fails]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-polys-4-s1-1-sympy-tooslow-fails]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-solvers-7-5a-sympy-solution-form]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-solvers-7-5b-sympy-solution-form]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-testing-1-sympy-source-tree]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-utilities-4-no-path-variable]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[networkx-r-trap-asadpour-integral-held-karp]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[scipy-hypothesis-hyp1f1]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[scipy-hypothesis-lpmv]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[scipy-hypothesis-yn]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[sympy-slow-W25]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[sympy-slow-function-range1]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[sympy-slow-issue-15227]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[sympy-slow-issue-3880]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[sympy-slow-linear-new-order1-type2-de-lorentz-slow-check]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[sympy-slow-nonlinear-3eq-order1-type1]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[sympy-slow-nonlinear-3eq-order1-type3]",
]
passes = []
grows = []
retired = []
units = 0
```
