# The release tier's survey (spec 102, Decision 11)

- **Date:** 2026-10-21, 03:10 to 04:15 (the 90-minute box held: about 65 minutes of guest runs).
- **By:** spec 102's builder, on `spec/102-the-release-tier` rebased onto wave 09's tip
  `a68efbb` (100 and 097; main `58f108f` plus wave 09, which lands by fast-forward).
- **Set:** wave 09's frozen set, `SHA256SUMS` `142bdd38` (built at the wave's code; the lane's
  record `build/wave-09/lane/judge-1.json` is on the same set), copied into the worktree with
  `cp -c -Rp`; the four source tarballs cloned from the main tree's `downloads/` and checked
  against `downloads/SHA256SUMS` (all four OK), their trees and the upstream kit cloned beside.
- **How (EXECUTED):** the judge's own sessions (`upstream.Session`, `packages.Session`,
  `regrtest.Session`), driven one group at a time by a stand-in script in the worktree's
  `build/102/survey/survey.py`, which keeps each group's whole stream and a summary (fuel,
  passes, counts, findings, class members). One guest process at a time; it waited on
  `build/lane.lock` (it never existed during the survey). Darwin arm64, wasmtime 49.0.0.
  Streams and summaries: `build/102/survey/` in the worktree (git-ignored).

## What it measured

### The release tier, group by group

Fuel is darwin's, in G (10^9 instructions). "list" is a CPython release list. The two groups
with findings had them before their classes existed: `pandas-slow-b`'s six (`os.pipe`,
class `no-threads`) and `cpython-release-a`'s one (`test_trace`'s coverage report opens a
stdlib module inside the zip, class `stdlib-zip-error`); re-judged from the kept streams with
the classes, both have none.

| family | group | kind | fuel (G) | passes | outcomes | findings |
|---|---|---|---|---|---|---|
| numpy | `numpy-slow-a` | marker | 143.8 | 9 | passed 9, skipped 12 | 0 |
| numpy | `numpy-slow-linalg` | marker | 251.3 | 27 | passed 27, skipped 1 | 0 |
| numpy | `numpy-slow-b` | marker | 81.9 | 29 | passed 29, skipped 2 | 0 |
| pandas | `pandas-slow-a` | marker | 303.6 | 2259 | passed 2259, xfailed 8 | 0 |
| pandas | `pandas-slow-b` | marker | 86.6 | 28 | failed 6, passed 28, skipped 51 | 6 |
| python | `cpython-release-fs` | list | 7.9 | 72 | passed 72, skipped 24 | 0 |
| python | `cpython-release-archives` | list | 99.7 | 4 | passed 4 | 0 |
| python | `cpython-release-a` | list | 434.1 | 10 | error 1, passed 10, skipped 1 | 3 |
| python | `cpython-release-b` | list | 77.7 | 8 | passed 8, skipped 29 | 0 |
| python | `cpython-release-c` | list | 108.3 | 11 | passed 11, skipped 1 | 0 |
| python | `cpython-release-int` | list | 54.0 | 1 | passed 1, skipped 2 | 0 |
| python | `cpython-release-math-1` | list | 8.7 | 1 | passed 1 | 0 |
| python | `cpython-release-math-2` | list | 621.5 | 1 | passed 1 | 0 |
| python | `cpython-release-unicodedata` | list | 254.9 | 68 | passed 68, skipped 5 | 0 |
| python | `cpython-release-b-inline` | list | 472.0 | 210 | passed 210, skipped 3 | 0 |
| python | `cpython-release-hashlib-1` | list | 222.0 | 1 | passed 1 | 0 |
| python | `cpython-release-hashlib-2` | list | 331.0 | 1 | passed 1 | 0 |
| python | `cpython-release-hashlib-3` | list | 813.4 | 1 | passed 1 | 0 |
| contourpy | `contourpy-filled-1` | keyword | 242.3 | 6 | passed 6 | 0 |
| contourpy | `contourpy-filled-2` | keyword | 263.0 | 6 | passed 6 | 0 |
| contourpy | `contourpy-filled-3` | keyword | 244.7 | 6 | passed 6 | 0 |
| contourpy | `contourpy-filled-4` | keyword | 242.4 | 6 | passed 6 | 0 |
| contourpy | `contourpy-filled-5` | keyword | 263.1 | 6 | passed 6 | 0 |
| contourpy | `contourpy-filled-6` | keyword | 244.8 | 6 | passed 6 | 0 |
| contourpy | `contourpy-filled-7` | keyword | 439.9 | 4 | passed 4, skipped 2 | 0 |
| contourpy | `contourpy-filled-9` | marker | 376.4 | 4 | passed 4 | 0 |
| contourpy | `contourpy-filled-10` | marker | 287.7 | 3 | passed 3 | 0 |
| contourpy | `contourpy-filled-11` | marker | 287.5 | 3 | passed 3 | 0 |
| contourpy | `contourpy-slow-rest` | marker | 18.1 | 0 | skipped 1 | 0 |
| contourpy | `contourpy-lines-1` | keyword | 132.0 | 5 | passed 5 | 0 |
| contourpy | `contourpy-lines-2` | keyword | 145.3 | 5 | passed 5 | 0 |
| contourpy | `contourpy-lines-3` | keyword | 136.8 | 5 | passed 5 | 0 |
| contourpy | `contourpy-lines-4` | keyword | 132.1 | 5 | passed 5 | 0 |
| contourpy | `contourpy-lines-5` | keyword | 145.4 | 5 | passed 5 | 0 |
| contourpy | `contourpy-lines-6` | keyword | 136.9 | 5 | passed 5 | 0 |
| contourpy | `contourpy-lines-7` | keyword | 255.7 | 4 | passed 4, skipped 2 | 0 |
| | **total** | | **8366.5** | | | |

**The release tier costs 8.37 T of darwin fuel**: contourpy 3.99 T, CPython 3.51 T, numpy
0.48 T, pandas 0.39 T. At 0.154 to 0.170 s per G (the parallel-shards research) that is 21 to
24 minutes of guest time serially, about 8 to 9 at `-n 3` with the longest group,
`cpython-release-hashlib-3` (813 G, about 2.2 minutes), last. On Linux CI it is twelve release
shards packed at 725 G.

### The normal tier against the lane's wave 09 record (criterion 4)

Same set, same wasmtime, the lane's `judge-1.json` against this survey's normal groups:

```
contourpy-1               24.32 ->    24.39  +0.002840  passes 1196 -> 1196
contourpy-config-1       377.10 ->   377.07  -0.000082  passes 0 -> 0
contourpy-config-2       204.85 ->   204.78  -0.000307  passes 17 -> 17
contourpy-filled-1       242.33 ->   242.33  -0.000005  passes 6 -> 6
contourpy-filled-10      285.49 ->   287.70  +0.007748  passes 3 -> 3
contourpy-filled-11      285.22 ->   287.48  +0.007943  passes 3 -> 3
contourpy-filled-12      322.10 ->   321.96  -0.000435  passes 268 -> 268
contourpy-filled-2       262.95 ->   262.95  -0.000004  passes 6 -> 6
contourpy-filled-3       244.71 ->   244.71  +0.000031  passes 6 -> 6
contourpy-filled-4       242.36 ->   242.36  -0.000004  passes 6 -> 6
contourpy-filled-5       263.06 ->   263.06  -0.000024  passes 6 -> 6
contourpy-filled-6       244.79 ->   244.79  +0.000008  passes 6 -> 6
contourpy-filled-7       439.89 ->   439.89  -0.000017  passes 4 -> 4
contourpy-filled-8       242.54 ->   242.51  -0.000097  passes 154 -> 154
contourpy-filled-9       376.22 ->   376.37  +0.000412  passes 4 -> 4
contourpy-lines-1        132.00 ->   132.00  -0.000013  passes 5 -> 5
contourpy-lines-2        145.31 ->   145.32  +0.000065  passes 5 -> 5
contourpy-lines-3        136.82 ->   136.82  +0.000013  passes 5 -> 5
contourpy-lines-4        132.07 ->   132.08  +0.000036  passes 5 -> 5
contourpy-lines-5        145.39 ->   145.40  +0.000043  passes 5 -> 5
contourpy-lines-6        136.88 ->   136.89  +0.000089  passes 5 -> 5
contourpy-lines-7        255.70 ->   255.69  -0.000032  passes 4 -> 4
contourpy-lines-8        470.29 ->   470.16  -0.000283  passes 345 -> 345
contourpy-rest           205.75 ->   205.82  +0.000365  passes 277 -> 277
cpython-a                277.03 ->   277.11  +0.000272  passes 5865 -> 5865
cpython-archives         167.44 ->   167.42  -0.000099  passes 1313 -> 1313
cpython-b                296.58 ->   296.62  +0.000122  passes 9536 -> 9536
cpython-c                411.69 ->   411.90  +0.000525  passes 7877 -> 7877
cpython-fs                63.19 ->    63.20  +0.000058  passes 3712 -> 3712
numpy-core               156.60 ->   156.60  +0.000000  passes 9519 -> 9519
numpy-lib                132.51 ->   132.51  +0.000000  passes 4825 -> 4825
numpy-others             177.83 ->   177.83  +0.000000  passes 7277 -> 7277
pandas-frame             354.86 ->   354.86  +0.000000  passes 10926 -> 10926
pandas-groupby           488.00 ->   488.00  +0.000000  passes 22228 -> 22228
pandas-internals          21.69 ->    21.69  +0.000000  passes 258 -> 258
pandas-io-formats         89.59 ->    89.59  +0.000000  passes 1972 -> 1972
pandas-io-parser          94.34 ->    94.34  +0.000000  passes 3474 -> 3474
pandas-libs               27.32 ->    27.32  +0.000000  passes 1063 -> 1063
pandas-reshape           103.28 ->   103.28  +0.000000  passes 2664 -> 2664
pandas-tslibs             38.77 ->    38.77  +0.000000  passes 590 -> 590
```

- numpy's and pandas' normal groups: **equal to the instruction** (`+0.000000`), though the
  `/upstream` stage gained five release JSONs. Their fuel does not depend on the stage's files.
- CPython's normal groups: within 5.3e-4 (`cpython-c` +5.25e-4, `cpython-a` +2.7e-4,
  `cpython-b` +1.2e-4; `-fs` and `-archives` within 1e-4). The stage gained the release groups'
  JSONs and the driver its `Z` line; growth to claim. Passes equal in all five.
- contourpy's normal groups: `contourpy-1` +0.28% (its new `-m "not slow"` filter over 1,196
  items), the rest within 4.4e-4; passes equal in all seven.
- contourpy's release groups: `filled-10` and `-11` +0.78% and +0.79% (their `-k` lost the
  eight earlier expressions of the old single split and gained `-m slow`), the others within
  4.1e-4. Every group's passes equal the lane's.
- The partition held on all five CPython normal groups: each group's `cpu` skips are its lists'
  `gated` entries, each inline module ran (no findings).

## What it found

1. **numpy's slow tests** (the drafter's 33 `slow` lines in selected files): 65 passes and 15
   skips over three groups. The skips are the guest's: numpy's `requires_memory` "could not
   determine available memory" (5), no module building, no `_posixshmem`, no subprocess, no
   cython, 64-bit-only cases, `memmap`, and the 458 MiB sample array that may not fit a
   fragmented 32-bit address space. No failure.
   `numpy-slow-others` measured 656 G as one group, past 480, and was split by path into
   `numpy-slow-linalg` (251 G) and `numpy-slow-b` (82 G); `numpy-slow-a` holds `_core` and
   `lib` (144 G). Three `test_openblas_threading` ids (under `ma`, `matrixlib`, `random`)
   pass in the whole-path group only: linalg's `TestRegression` imported into those modules'
   namespaces when linalg is collected in the same session. The function runs in
   `numpy-slow-linalg` under its own id.
2. **pandas' slow tests**: two groups, 2,287 passes. Six `test_multi_thread` cases fail on the
   missing `os.pipe` (no threads): a class, `no-threads`, closer the README. Three of the eight
   paths select no slow test (exit 5 alone); grouped with the others they need no guard.
3. **contourpy**: the same tests in the same groups as wave 09's acceptance, passes equal in all
   25; no failure, no trap. The guard group `contourpy-slow-rest` (the marker release tier over
   every file but `test_filled.py`) selects nothing, 18 G.
4. **CPython**: the normal groups skip **51 tests** for want of `cpu` (none for `largefile`:
   the review's L4 holds under WASI) and **one module**, `test_peg_generator`, as a whole. The
   **inline readers are modules**, not tests: `test_unicodedata` reads `cpu` at module level
   (`quicktest`, steering several tests), `test_unparse` in a class helper, `test_posixpath` and
   `test_tokenize` in a test. Under the release resources, every listed test started; some then skip
   for reasons of their own, among them (`test_pyexpat`'s 8 GiB minimum, `test_support`'s subprocess,
   `test_peg_generator` whose `Tools/peg_generator` is not staged); one errors
   (`test_trace`, the class above). Two **single tests are past 480 G and cannot be split**:
   `test_sha3_256_update_over_4gb` (813 G: SHA3 over 4 GiB in the guest) and
   `test_sumprod_stress` (621 G). Each is a group of its own; `cpython-release-hashlib-3` fills a shard alone and
   `cpython-release-math-2` packs with `cpython-release-archives` (721.2 G, inside 725 G).
   The other heavy ones were split by id to under 480 G: the three `*_update_over_4gb` hashes
   (222, 331 and 813 G), `test_unicodedata` whole (255 G), the inline `test_tokenize` and
   `test_unparse` (472 G), `test_math`'s two sumprod tests.
5. **Module denials need their reason.** `RESOURCE_DENIED` also ends `test_urllib2net`,
   `test_urllibnet`, `test_socketserver` (network), `test_xpickle` and `test_zipfile64`
   (`extralargefile`, out of scope): none is the tiers'. The driver now writes a `Z <module> --
   <reason>` line before such a module's `D` line, and the partition reads only `cpu` and
   `largefile` denials.

## Its delta (Decision 11's rule)

No trap, and every new class's closer is the README. **Two groups are past 480 G and no split
can bring them under** (single tests, 813 G and 621 G): by Decision 11 that sends the survey's
delta to **a context-only delta review before the build continues**. The delta, for it:

1. CPython's inline entries are modules (the reader is a text search for an inline
   `is_resource_enabled('cpu')` in a planned module's source; the four found are the drafter's
   four); the release group runs the whole module with `cpu` on.
2. The regrtest driver gains a `Z` line (the stage changes; CPython's normal fuel grows by at
   most 5.3e-4).
3. contourpy's guard group (`selects_nothing`, a marker release group allowed pytest's exit 5)
   so the marker release groups cover every normal path, as Decision 3 requires.
4. Budgets per tier: numpy's, pandas' and CPython's budgets bound each tier; CPython's release
   tier has its own, 6 T (its caps sum to 5.39 T); a package family's budget stays the sum of all
   its caps (contourpy's 8.865 T).
5. The release shards: twelve, packed at 725 G from these numbers, one of them a single test
   alone; the normal plot shards re-packed into nine (6.01 T).
6. pandas' and numpy's release groups are by path (two and three), not one each.

In one line: the release tier is 8.37 T on darwin, every test lands in a tier, and two single
CPython tests past 480 G need the delta review's word before the build goes on.
