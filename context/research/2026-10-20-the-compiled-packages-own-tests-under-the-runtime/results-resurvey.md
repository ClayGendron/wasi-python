| group | fuel | cap | passed | failed | skipped | other |
|---|---|---|---|---|---|---|
| `matplotlib-axes` | 699.3 G | 1.10e+12 | 880 | 0 | 45 |  |
| `matplotlib-render-1` | 231.1 G | 3.50e+11 | 248 | 0 | 120 |  |
| `matplotlib-render-2a` | 304.5 G | 4.60e+11 | 290 | 2 | 12 |  |
| `matplotlib-render-2b` | 337.1 G | 5.10e+11 | 392 | 3 | 76 |  |
| `matplotlib-render-3` | 272.9 G | 4.10e+11 | 197 | 0 | 49 |  |
| `matplotlib-rest-a` | 309.5 G | 4.70e+11 | 966 | 9 | 94 | 26 xfailed |
| `matplotlib-rest-b1` | 323.5 G | 4.90e+11 | 3,367 | 14 | 89 |  |
| `matplotlib-rest-b2` | 384.5 G | 5.80e+11 | 1,146 | 1 | 9 | 2 xfailed |
| `mpl-axes_grid1` | 72.0 G | 1.10e+11 | 52 | 0 | 0 |  |
| `mpl-axisartist` | 35.7 G | 5.40e+10 | 50 | 0 | 0 |  |
| `mpl-mplot3d` | 336.8 G | 5.10e+11 | 244 | 0 | 0 |  |
| `contourpy-1` | 217.4 G | 3.30e+11 | 1,213 | 0 | 19 |  |
| `contourpy-lines` | 1,459.5 G | 2.20e+12 | 379 | 0 | 40 |  |
| `contourpy-filled` | 2,387.6 G | 3.60e+12 | 462 | 0 | 56 |  |
| `contourpy-rest` | 90.4 G | 1.40e+11 | 198 | 0 | 80 |  |
| `pillow-ro` | 431.0 G | 6.50e+11 | 4,587 | 78 | 1,054 | 3 xfailed |
| `lxml` | 104.5 G | 1.60e+11 | 2,058 | 2 | 58 | ; 360 deselected |
| `regex` | 16.0 G | 2.50e+10 | 147 | 0 | 0 |  |
| `kiwisolver` | 13.0 G | 2.00e+10 | 50 | 0 | 0 |  |

matplotlib: budget 5.044e+12
contourpy: budget 6.270e+12
pillow: budget 6.500e+11
lxml: budget 1.600e+11
regex: budget 2.500e+10
kiwisolver: budget 2.000e+10
total caps 1.217e+13; total fuel 8.026 T

matplotlib-mathtext was voided twice by host litter on this set; its provisional cap is 1.5 times
wave 05's 296.2 G, 4.5e+11, which brings matplotlib's family to about 5.49e+12 and the total caps to
about 1.262e+13 on about 8.32 T.

## Four further runs (EXECUTED on the same set; the survey's bisection argv, `survey.py <group> <args>`)

| run | argv | fuel | outcome |
|---|---|---|---|
| contourpy's whole suite, `cwd` `/tmp/work` | `survey.py contourpy` (before the split; its group then had `cwd="/tmp/work"`) | 1.5e+12, **out of fuel** (the survey's cap) | 1,247 passed, 201 failed (184 in `test_filled.py`, 17 in `test_config.py`, each `AssertionError` from `compare_images`, which opens `tests/baseline_images/…` relative to the working folder), 61 skipped, before running out in `test_filled_random_big` |
| `test_filled.py` without random_big | `survey.py contourpy-filled tests/test_filled.py "-knot random_big"` | 543,983,988,154 | 422 passed, 54 skipped, 0 failed |
| `test_lines.py` without random_big | `survey.py contourpy-lines tests/test_lines.py "-knot random_big"` | 470,231,479,818 | 345 passed, 38 skipped, 0 failed |
| lxml, `cwd` the read-only tree root | `survey.py lxml` (its group then had `cwd="/upstream-lxml/tree"`) | 104,584,398,212 | 2,056 passed, 58 skipped, 4 failed: `test_include_paths`, `doc/validation.txt`, and two `ETreeC14NTestCase::test_python3_problem_filebased_*` with `PermissionError: [Errno 63] Operation not permitted: 'test.xml'` |

So random_big costs (2,387.6 − 544.0) + (1,459.5 − 470.2) = 2,832.9 G.
