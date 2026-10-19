# One pre-import rule for every package

- **Status:** research (measured on the frozen set), 2026-10-18. Advice for question 34 as the
  owner reframed it: one rule for all packages, pre-imported or not.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Fable 5.1). About two hours.
- **Feeds:** question 34 (`context/questions-for-the-owner.md`), question 64 (the wheel),
  constitution §2 (a profile is its own artifact set), spec 023's landing notes, and the roadmap's
  default-profile table.
- **Evidence:** everything ran in the session scratchpad; the probes and results are filed in
  the folder of the same name beside this memo (the scratch snapshots and run folders were not
  kept). The probes are in `probes/` (`relink.py`, `snapshot.sh`, `measure.py`, `instances.py`, `modules.py`,
  `table.py`, `jobs/`), the raw numbers in `results-*.json`, the full table in `results.md`. The
  main tree was used read-only: the frozen set `build/sets/s-4eb5418a2b1bb553`, step 60's
  recorded link commands (`build/link/reactor-commands.txt`), the CPython cross-build objects,
  wasi-sdk 33's `clang` and `llvm-strip`, wasmtime 49.0.3's `wizer`, and the judge's guest
  driver (`tests/harness/guest.py`). Nothing was downloaded. Nothing in a git tree changed.

Terms. **Snapshot:** `python-snapshot.wasm`, the reactor after Wizer ran `wizer.initialize`,
which starts the interpreter and imports a fixed list (`PREIMPORT`, `recipes/reactor_main.c`).
**Pre-import:** a module in that list; its import is paid once, at build time, and lives in the
snapshot's memory. **Fuel:** wasmtime's count of guest instructions, the judge's measure.
**Resident memory:** the host memory an instance really occupies, apart from the memory it reserves.

## The question

The owner's instinct: one rule for all packages. None pre-imported if that works; if some must
be, then all. Does "none" work? Does "all" scale as scipy, scikit-learn, statsmodels, lxml, regex
and about thirty pure-Python packages land? Is there a uniform middle?

## Method

Four snapshots were built from the frozen set's own objects, differing only in `PREIMPORT`:

| variant | `PREIMPORT` |
|---|---|
| A, stdlib only | `encodings, io, os, sys, json, csv, re, _colorize` |
| D, numpy only | A plus `numpy` |
| B, today's | A plus `numpy, pandas` |
| C, every package in the set | B plus `matplotlib, matplotlib.pyplot, PIL.Image, kiwisolver, fontTools, dateutil, tzdata, six, cycler, pyparsing, packaging, sqlite3, bz2, lzma, zlib`, with `MPLCONFIGDIR=/tmp/matplotlib` during the import, as spec 023's builder did |

- **The method reproduces the set (EXECUTED).** Variant B's relinked, stripped `python.wasm` is
  byte for byte the frozen set's (`1655014314805b58…`), and its snapshot is the frozen snapshot
  (`4eb5418a2b1bb553…`). So the other variants differ from the set in nothing but the list.
  `relink.py` reruns step 60's compile with `-DPREIMPORT=…` and its link; `snapshot.sh` strips
  as step 60 does and runs `wasmtime wizer` with step 80's flags (for C, also matplotlib's data
  at its nested path and a writable `/tmp`).
- **Fuel (EXECUTED)** through the judge's driver, which fixes the clock and entropy, so a figure
  repeats to parts in ten million. Jobs: `-c pass`; `-c "import os; os._exit(0)"` (a run with no
  finalization); a pure-Python script (2,000 records through `json`, `csv` and `re`,
  `probes/jobs/pure.py`); `import numpy` plus a small array job; `import pandas`, `read_csv` of
  240 rows and a `groupby`; and the judge's own plot job `tests/jobs/plot_line.py` with its PNG
  save, with a fresh font cache and with a kept one. The plain `python.wasm` is the reference.
- **Bytes (EXECUTED):** the snapshot's size; its deflated size at zlib level 6, which is what the
  wheel holds (the frozen snapshot deflates to 21,435,051 this way; spec 023 measured the wheel's
  member at 21,434,463 for a snapshot 4.5 KB smaller); the wasm data section (the memory the
  snapshot fills at start).
- **Memory (EXECUTED):** the module's memory minimum (the pages an instance reserves; the judge's
  figure), and the resident growth of the host process per live instance that has run `-c pass`,
  eight instances kept alive (`instances.py`, `ps` RSS). Resident bytes are a fact about this
  machine's wasmtime; the ratios between variants are what matter.
- **The projection (INFERRED)** scales the measured per-module costs by the module counts the
  coming packages would add.

## Findings

### 1. The four snapshots

| variant | modules at start | snapshot bytes | deflated (the wheel) | reserved memory | resident per live instance |
|---|---|---|---|---|---|
| plain `python.wasm` | 36 | 36,916,497 | 8,806,081 | 640 pages, 40.0 MiB | 7.9 MiB |
| A, stdlib only | 70 | 40,509,812 | 10,375,343 | 640 pages, 40.0 MiB | 9.6 MiB |
| D, numpy only | 186 | 45,738,350 | 12,393,182 | 640 pages, 40.0 MiB | 24.0 MiB |
| B, today's | 588 | 70,901,724 | 21,435,051 | 916 pages, 57.3 MiB | 41.3 MiB |
| C, every package | 772 | 88,513,509 | 27,982,574 | 1,186 pages, 74.1 MiB | 58.1 MiB |

- 640 pages is the link's `--initial-memory=41943040` (40 MiB): a floor, not a use. The resident
  column is the honest memory figure. B's snapshot holds 34.0 MB of heap; C's 51.6 MB; A's 3.6 MB.
- The wheel (spec 028's shape: `python.wasm` 8.8 MB deflated, the zip 21.6 MB, the snapshot as
  above): A about 41.0 MB, B 52.1 MB (measured by spec 023: 52,091,103), C about 58.6 MB.

### 2. What each run costs

Fuel, EXECUTED. Wall clock is a benchmark fact from one run on an M-series Mac, in parentheses.

| job | plain | A, stdlib only | D, numpy only | B, today's | C, every package |
|---|---|---|---|---|---|
| `-c pass` | 166,511,583 (30 ms) | 15,593,597 (14 ms) | 26,924,082 (13 ms) | 83,372,077 (34 ms) | 106,917,575 (43 ms) |
| `-c pass`, `os._exit(0)` | 138,231,359 | 966,826 | 382,149 | 2,652,687 | 2,654,948 |
| pure script (json, csv, re) | 552,698,409 (74 ms) | 278,458,424 (60 ms) | 278,242,642 | 327,658,205 (50 ms) | 350,741,494 (65 ms) |
| numpy, small array job | 1,069,458,472 (199 ms) | 788,454,481 (143 ms) | 38,596,311 (14 ms) | 87,608,631 (27 ms) | 110,939,574 (42 ms) |
| pandas, read_csv + groupby | 4,946,583,451 (1.08 s) | 4,627,538,215 (0.81 s) | 3,871,212,236 (0.67 s) | 110,249,985 (34 ms) | 133,808,388 (57 ms) |
| plot + PNG, fresh font cache | 9,104,844,554 (1.69 s) | 8,782,824,216 (1.28 s) | 8,030,175,815 | 7,559,044,109 (1.07 s) | 1,021,030,619 (0.30 s) |
| plot + PNG, kept font cache | 7,116,225,420 | 6,791,331,735 | 6,037,809,244 | 5,569,651,749 (0.80 s) | 1,021,001,321 |

B's `pass`, plot and memory figures equal spec 023's landing notes to the instruction and the page.

### 3. The pre-import tax is finalization, not start

- In every snapshot, 94% to 99% of a bare run's fuel is `Py_FinalizeEx` tearing down the
  pre-imported modules (EXECUTED: row 2 against row 1). C's `pass` is 106.9 M; the same run that
  ends with `os._exit(0)` is 2.65 M. A's is 15.6 M against 0.97 M.
- So the per-run fuel of pre-importing is about 130,000 fuel per module torn down (B − A:
  67.8 M over 518 modules; C − B: 23.5 M over 184), and it would nearly vanish if `run` flushed
  and skipped module teardown for an instance that is discarded anyway. The README already
  records the wall-clock half of this (20 ms against 6 ms). That is a separate specification;
  it is named here because it changes the fuel side of this decision but not the memory side.
- The start itself, instantiating the snapshot's memory, is unmetered (spec 008) and is the same
  few instructions in every variant.

### 4. What a run saves, and when pre-importing pays in fuel

- numpy and pandas (B over A) cost every run 67.8 M fuel and 31.7 MiB of resident memory. They
  save a pandas run 4.52 G and a numpy run 0.70 G. In fuel alone, pre-importing pays as soon as
  more than **1.5%** of runs use pandas.
- The plot stack (C over B) costs every run 23.5 M fuel and 16.8 MiB resident. It saves a plot
  run 6.54 G (fresh font cache) or 4.55 G (kept). In fuel alone, pre-importing pays as soon as
  more than **0.36%** of runs plot.
- The asymmetry in words: pre-importing costs a pure script +18% fuel (B against A) and
  +32 MiB; not pre-importing costs a pandas script **42 times** the fuel (4.63 G against
  0.11 G; 0.81 s against 0.03 s here) and a numpy script 9 times.
- Fuel amortizes; memory does not. Each live instance holds its pre-imported heap for its whole
  life, used or not. On a host with 100 live instances, A holds about 1.0 GB, B 4.1 GB, C 5.8 GB
  (EXECUTED per instance, multiplied). Sessions (spec 055, turns in one instance) make this
  worse for pre-import and better for none: an import paid in turn one serves every later turn,
  while pre-imported memory is held for the session.

### 5. Is "none" (A) still worth a snapshot at all?

Yes. Against the plain binary, A's `pass` is 10.7 times cheaper (15.6 M against 166.5 M), the
pure script 1.98 times, numpy 1.36 times, a plot 1.04 times. But a pandas run is only 1.07 times
cheaper (4.63 G against 4.95 G): for pandas users, A's snapshot is nearly the plain binary. A's
snapshot is 40.5 MB and the wheel about 41 MB.

### 6. Per-module costs, the basis of the projection (EXECUTED differences)

| step | modules added | heap bytes per module | `pass` fuel per module | resident KiB per module | snapshot bytes per module |
|---|---|---|---|---|---|
| numpy (D − A) | 116 | 45,074 | 97,677 | 127 | 45,074 |
| pandas alone (B − D) | 402 | 62,595 | 140,418 | 44 | 62,595 |
| the plot stack and the rest (C − B) | 184 | 95,716 | 127,965 | 93 | 95,716 |

A pre-imported module costs about 45 to 96 KB of snapshot and heap, 44 to 127 KiB resident, and
about 100,000 to 140,000 fuel of teardown on every run. matplotlib's modules are the heaviest
(its `fontManager` and `rcParams` are large objects).

## The projection (INFERRED)

The coming packages, from their specifications and memos: scipy (639 Python files; `python.wasm`
+25 MB, spec 037), scikit-learn (415 zip members; +5.5 MB), statsmodels (588 members; +3.9 MB),
lxml (+4.3 MB), regex (+0.7 MB), tier A's about thirty pure packages (2,014 members; spec 039).
The ratio of modules imported to members was 0.64 for numpy, about 1 for pandas (it pulls in
stdlib modules too), and 0.3 for the plot stack (pyplot imports a third of fontTools). A
pre-import that means anything for scipy imports its submodules (`import scipy` alone is lazy).

| what "all" would add | modules imported (range) | heap and snapshot | `pass` fuel per run | resident per instance |
|---|---|---|---|---|
| scipy's tree, scikit-learn, statsmodels, lxml, regex (the compiled-in packages) | 770 to 1,480 | +46 to +141 MB | +100 to +190 M | +45 to +130 MiB |
| the same plus tier A's thirty pure packages | 1,470 to 3,280 | +88 to +312 MB | +190 to +430 M | +86 to +290 MiB |

Per module: 60 to 95 KB heap, 130,000 fuel, 60 to 90 KiB resident (finding 6). `python.wasm`
itself grows about +39 MB raw (the specifications' estimates summed), and that growth lands in
every snapshot, pre-import or not; so do about 366 bytes per new zip member (spec 039).

What the rules then look like once the whole roadmap has landed:

| rule, at the end of the roadmap | snapshot raw | snapshot deflated | the wheel | resident per live instance | snapshot `-c pass` |
|---|---|---|---|---|---|
| none (A) | about 82 MB | about 21 MB | about 89 MB | about 10 MiB | about 31 M |
| today's list (B, numpy and pandas) | about 112 MB | about 32 MB | about 100 MB | about 42 MiB | about 100 M |
| all compiled-in packages | 174 to 269 MB | 55 to 85 MB | 123 to 153 MB | 103 to 188 MiB | 207 to 299 M |
| all packages, tier A too | 216 to 440 MB | 68 to 139 MB | 136 to 207 MB | 144 to 346 MiB | 298 to 533 M |

Arithmetic: the wheel is `python.wasm` deflated (8.8 MB today, about 18 MB at 76 MB raw), the
zip (21.6 MB today; +3.8 scipy, +3.3 scikit-learn, +4.1 statsmodels, about +1 lxml and regex,
+16.5 tier A, the specifications' figures: about 50 MB) and the snapshot deflated at C's ratio
(0.316). The plain binary's `pass` grows too, about 26,700 fuel per new zip member (spec 039):
about 325 M at the end of the roadmap. PyPI's default limit is 100 MiB, 104.9 MB (question 64).

So: **"all" fails the wheel limit as soon as scipy and tier B land, and holds 100 to 350 MiB per
live instance.** Even today's list reaches the limit (question 64 already projects 95 to 110 MB).
Only "none" leaves headroom.

## The options weighed

1. **None pre-imported (A).** Uniform. Light: 9.6 MiB per instance, 40.5 MB snapshot, 41 MB
   wheel, `pass` 15.6 M. The snapshot is still worth shipping (finding 5). Its cost: every
   pandas run pays 4.6 G and about 0.8 s here (42 times today's), every numpy run 0.79 G (9
   times), every plot about 16% more than today. The README's "about 20 ms with the stack"
   becomes "14 ms, stack not counted". Sessions (055) and a finalization-skipping `run` recover
   part of it; nothing recovers the first import of a session.
2. **All pre-imported (C, then everything).** Uniform. Today it is fine: +28% on `pass`
   (+23.5 M), +16.8 MiB per instance, 88.5 MB snapshot, 58.6 MB wheel, plots 7.4 times cheaper,
   pandas 134 M. It does not survive the roadmap: the wheel passes 100 MiB at scipy plus tier B
   (123 to 153 MB), and 100 to 350 MiB per instance is a multi-tenant host's whole budget. The
   rule would have to be broken within three specifications.
3. **"Pre-import what is compiled into `python.wasm`, never what sits in the zip."** Uniform
   with a natural line, and it is C today. The line does not track cost (a pure-Python import
   is the expensive kind; C init is cheap), and it still fails the wheel limit at tier B.
4. **Two snapshots in one set, none and all.** The owner's framing taken literally. Today
   +28 MB of wheel on top of A's; at the end of the roadmap 144 to 174 MB, over the limit again.
   It also changes §4.6's artifact shape and spec 049's frozen `snapshot: bool`.
5. **Profiles (constitution §2).** The default set keeps rule 1; a `full` profile, its own
   artifact set and wheel, pre-imports everything for embedders who plot and compute in every
   run and have the memory. Profiles stay few: two. The release matrix doubles only when
   someone asks for it.
6. **An embedder-chosen list at build time.** The list is already one `-D` flag; a relink and a
   Wizer run took ten seconds here. A documented `PREIMPORT` knob for people who run the build
   costs nothing and promises nothing. It is not a product rule; it is a note in the build's
   README. The constitution forbids assembling on a user's machine, not building one's own set.

## Recommendation

**Adopt "none" as the rule: the default snapshot pre-imports the stdlib's bootstrap modules
only (variant A), for every package now and later.** Keep shipping the snapshot (10.7 times
cheaper than plain on a bare run, twice on pure scripts). Record in the roadmap that a `full`
profile (option 5) is the answer for embedders who want the stack resident, built only if asked.
Add two follow-ups that make "none" cheaper without touching the rule: a finalization-skipping
`run` (finding 3: 15.6 M to about 1 M on a bare run) and spec 055's sessions, which pay an import
once per session.

Why this and not "all": "all" is the better deal in fuel today (finding 4) but the only costs it
has are the ones that never amortize, memory per live instance and wheel bytes, and both cross
hard lines at scipy plus tier B (the projection). "None" is the only uniform rule that holds to
the end of the roadmap, and it is the owner's stated preference.

**What the owner is agreeing to (EXECUTED numbers, today's set):**

| | today (B) | with "none" (A) |
|---|---|---|
| a pandas script | 110 M fuel, 34 ms | 4.63 G fuel, 0.81 s (42 times) |
| a numpy script | 88 M, 27 ms | 788 M, 143 ms (9 times) |
| a plot with PNG, fresh font cache | 7.56 G, 1.07 s | 8.78 G, 1.28 s (+16%) |
| a pure-Python script | 328 M, 50 ms | 278 M, 60 ms (−15% fuel) |
| `-c pass` | 83.4 M | 15.6 M (5.3 times less) |
| resident memory per live instance | 41.3 MiB | 9.6 MiB |
| snapshot / wheel | 70.9 MB / 52.1 MB | 40.5 MB / about 41 MB |
| at the end of the roadmap: wheel, resident | about 100 MB, about 42 MiB | about 89 MB, about 10 MiB |

If the owner says no (the pandas latency is the product), the fallback with numbers is option 2
today and a forced re-decision at scipy, not option 3.

## Where it stopped

- The projection's module counts are ranges from member counts, not imports traced in a native
  environment (no scipy or scikit-learn was installed; nothing was downloaded). The first scipy
  build should count `len(sys.modules)` after its imports and replace the range.
- Resident memory is one machine's wasmtime; copy-on-write of the data segments may lower the
  per-instance figure on Linux. The ratios between variants are the finding.
- Not measured: a snapshot with matplotlib but not pandas, or a "middle" list; the owner asked
  for all or none.

One line: pre-import nothing; the snapshot still pays, a pandas run then costs 4.6 G instead of
0.11 G, and every other rule runs out of memory and wheel before the roadmap ends.
