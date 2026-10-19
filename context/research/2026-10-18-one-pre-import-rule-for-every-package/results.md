# Results: one snapshot per pre-import rule (EXECUTED, darwin-arm64, 2026-10-18)

Fuel is wasmtime's guest instruction count through tests/harness/guest.py; the stdlib zip is the frozen set's
(16ee747c…). Resident memory is ps RSS growth per live instance after `-c pass`, 8 instances (instances.py).

| variant | pre-imported modules at start | snapshot bytes | deflated (level 6, as the wheel) | data section (heap+static) | memory min (pages / MiB) | resident per live instance (MiB) |
|---|---|---|---|---|---|---|
| plain python.wasm | 36 | 36,916,497 | 8,806,081 | 5,581,810 | 640 / 40.0 | 7.9 |
| A stdlib only | 70 | 40,509,812 | 10,375,343 | 9,175,158 | 640 / 40.0 | 9.6 |
| D + numpy | 186 | 45,738,350 | 12,393,182 | 14,403,696 | 640 / 40.0 | 24.0 |
| B today (numpy, pandas) | 588 | 70,901,724 | 21,435,051 | 39,567,070 | 916 / 57.25 | 41.3 |
| C every package | 772 | 88,513,509 | 27,982,574 | 57,178,855 | 1186 / 74.12 | 58.1 |

| job (fuel) | plain python.wasm | A stdlib only | D + numpy | B today (numpy, pandas) | C every package |
|---|---|---|---|---|---|
| pass | 166,511,583 | 15,593,597 | 26,924,082 | 83,372,077 | 106,917,575 |
| hard_exit | 138,231,359 | 966,826 | 382,149 | 2,652,687 | 2,654,948 |
| pure | 552,698,409 | 278,458,424 | 278,242,642 | 327,658,205 | 350,741,494 |
| numpy | 1,069,458,472 | 788,454,481 | 38,596,311 | 87,608,631 | 110,939,574 |
| pandas | 4,946,583,451 | 4,627,538,215 | 3,871,212,236 | 110,249,985 | 133,808,388 |
| plot_fresh_cache | 9,104,844,554 | 8,782,824,216 | 8,030,175,815 | 7,559,044,109 | 1,021,030,619 |
| plot_kept_cache | 7,116,225,420 | 6,791,331,735 | 6,037,809,244 | 5,569,651,749 | 1,021,001,321 |

| job (wall s, benchmark fact, one run) | plain python.wasm | A stdlib only | D + numpy | B today (numpy, pandas) | C every package |
|---|---|---|---|---|---|
| pass | 0.03 | 0.014 | 0.013 | 0.034 | 0.043 |
| hard_exit | 0.021 | 0.012 | 0.007 | 0.009 | 0.011 |
| pure | 0.074 | 0.06 | 0.037 | 0.05 | 0.065 |
| numpy | 0.199 | 0.143 | 0.014 | 0.027 | 0.042 |
| pandas | 1.08 | 0.809 | 0.665 | 0.034 | 0.057 |
| plot_fresh_cache | 1.686 | 1.281 | 1.414 | 1.066 | 0.303 |
| plot_kept_cache | 1.296 | 1.004 | 1.065 | 0.804 | 0.265 |

## Per pre-imported module (EXECUTED differences)

| step | modules | heap bytes / module | `pass` fuel / module | resident KiB / module | snapshot bytes / module |
|---|---|---|---|---|---|
| numpy (D - A) | 116 | 45,074 | 97,677 | 127 | 45,074 |
| numpy + pandas (B - A) | 518 | 58,672 | 130,846 | 63 | 58,672 |
| pandas alone (B - D) | 402 | 62,595 | 140,418 | 44 | 62,595 |
| plot stack and the rest (C - B) | 184 | 95,716 | 127,965 | 93 | 95,716 |

## What a run pays or saves (EXECUTED differences)

- Pre-importing numpy and pandas (B over A) costs every run 67,778,480 fuel and 31.7 MiB resident; it saves a pandas run 4,517,288,230 and a numpy run 700,845,850. Fuel break-even: pandas in more than 1.5% of runs.
- Pre-importing the plot stack (C over B) costs every run 23,545,498 fuel and 16.8 MiB resident; it saves a plot run 6,538,013,490 (fresh font cache) or 4,548,650,428 (kept). Fuel break-even: a plot in more than 0.36% of runs.
- A stdlib only: `-c pass` 15,593,597; the same with `os._exit(0)` 966,826: finalization is 93.8% of a bare run.
- B today (numpy, pandas): `-c pass` 83,372,077; the same with `os._exit(0)` 2,652,687: finalization is 96.8% of a bare run.
- C every package: `-c pass` 106,917,575; the same with `os._exit(0)` 2,654,948: finalization is 97.5% of a bare run.
- D + numpy: `-c pass` 26,924,082; the same with `os._exit(0)` 382,149: finalization is 98.6% of a bare run.
- A over plain: `pass` 10.7x cheaper, pure script 1.98x, pandas 1.07x, numpy 1.36x.
- A against B on a pandas run: 42x the fuel; on a numpy run 9x; on the pure script 1.18x (B pays more).
