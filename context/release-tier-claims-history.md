# The release-tier claims, by release

Each release acceptance moves the ledger's blocks (`release-tier-claims.toml`) here, under its version, and the ledger starts empty again (`progress/README.md`, "The release tier").

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
