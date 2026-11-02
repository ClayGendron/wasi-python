# The start cost of the zip's directory

- **Status:** research, 2026-10-31. Nothing in `recipes/`, `scripts/`, `src/`, `tests/` or the judge changed. It answers the owner's choice of 2026-10-31 on plotly, "lets research how to cut the cost first"; plotly waits on it.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), briefed by the session's lead agent.
- **Stands on:** `2026-10-17-the-zips-directory-is-read-once.md` and spec 035, which built the reader (`recipes/zip_directory.py`, `recipes/zip_resources.py`); spec 165's 24.5 k fuel a member; spec 167's plotly numbers (1,528 members, plain start +14.7%, snapshot start +7.0%).
- **Evidence:** `2026-10-31-the-start-cost-of-the-zips-directory/`: `scripts/` holds every script run, `outputs/` every number quoted (its `README.txt` names the zips). The zips stayed in the session's scratchpad.
- **Repository state:** worktree `research/zip-start-cost` at `dev` `a750e8fe`. The guest ran spec/167-plotly's set (`43005960`, its `build/artifacts`: CPython 3.15.2, 8,191 members) through `wasi_python.run` with fuel metered. "Without plotly" is that zip less `plotly/`, `_plotly_utils/` and plotly's `.dist-info`: 6,663 members, 57,058,947 bytes, the size of `dev`'s zip today.

Labels: EXECUTED means run here; READ means read in source; INFERRED means arithmetic or reasoning from those.

Terms. A **member** is one file in the zip. The **directory** is the zip's central directory, the table at its end listing every member. A **plain start** is `-c pass` on `python.wasm`; a **snapshot start** is `-c pass` on `python-snapshot.wasm`, which Wizer captured after the interpreter started. **Teardown** is `Py_FinalizeEx` at a call's end, which frees what the interpreter holds. **Fuel** is wasmtime's count of executed instructions. The snapshot's hash seed is fixed, so its numbers are exact; the plain binary's is random, so its numbers move by a few M.

## The short version

1. **A plain start pays about 27 k fuel per member, in two places.** About 25 k builds zipimport's dict. About 2 k frees it at teardown.
2. **A snapshot start pays only the teardown, about 2.4 k per member.** The snapshot never reads the zip: beside the plotly-less zip it costs exactly what it costs beside the plotly zip, 58,545,351 fuel. Nothing rebuilds the directory after restore, and nothing is copied on write. The +7% is teardown freeing 9,379 more dict entries.
3. **Two changes take the per-member cost to almost nothing.** Keep the directory alive past teardown. Then let a plain start read each package folder's members only on first use, from a table the build writes into the zip's comment. Projected: a plain start falls from 323.6 M to about 115 M, a snapshot start from 58.5 M to about 39 M. plotly's members would add about 1 M to a plain start, and nothing to a snapshot start.

## 1. Where the cost goes (EXECUTED)

| | without plotly (6,663) | with plotly (8,191) | per member |
|---|---|---|---|
| plain start | 282.2 M | 323.6 M | 27.1 k |
| snapshot start, one image, either zip | 58,545,351 | 58,545,351 | 0 |
| snapshot start, image built beside each zip (spec 167) | 54.6 M | 58.5 M | 2.5 k |

**The parse.** Each stage of the reader, re-run on the snapshot binary against both zips, so the difference is exact (`scripts/parts.py`, `outputs/c2-*.tsv`). Each row adds one step:

| stage of `_zip_directory._fast` | fuel per member |
|---|---|
| read the directory's bytes (one `read`) | 6 |
| the loop and one `_struct` unpack per entry | 6,622 |
| slice and decode the name | 4,237 |
| build the path string | 2,203 |
| build the 8-tuple | 1,835 |
| insert into the dict | 2,668 |
| the implied-directory pass (1,188 folders the zip does not list) | 6,596 |
| the recipe's safety checks (Zip64, bounds, cp437) | 2,681 |
| **total** | **26,849** |

Neither the host (6 fuel a member) nor the collector (`gc.disable()` moves it −26) is the cost. It is bytecode and objects: two strings, a tuple, up to four integers and a dict slot per member. A smarter implied-directory pass, walking up only when the folder changes, costs 5,788 instead of 6,596. No tweak fixes this.

**The teardown.** Freeing the cache and then leaving by `os._exit` costs 17.6 M more than `os._exit` alone on the snapshot. A call that only frees the cache, then finalizes, costs 1.7 M less than `pass`. So teardown spends about 19.3 M on the directory, 2.36 k a member; spec 167's two images differ by 2.52 k a member. On the plain binary freeing it costs 14.4 M and 17.3 M on the two zips, about 1.9 k a member (`outputs/c2-*`, `c5-plain-*`).

**Why the snapshot pays it.** `wizer_initialize` freezes the heap, and `run` unfreezes it before `Py_FinalizeEx`, so a program's objects are finalized as CPython finalizes them (READ: `recipes/reactor_main.c`; spec 073). Finalization clears `zipimport`'s module dict, and the cache goes with it. Its tuples are untracked by the collector (EXECUTED: 0 of 8,191), so they cost nothing to collect, only to free. A call from a `make_snapshot` image ends through `_reactor._end` and never finalizes: images holding an extra copy of the directory cost 0.66 M a call, within 2,300 fuel of an empty image (`outputs/images.tsv`).

**A finding beside the question.** Teardown is most of a snapshot start: `os._exit(0)` in place of finalizing saves 57.5 M of 58.5 M. On the plain binary teardown is about 23 M. Spec 073 chose to finalize; that is the owner's, outside this memo, and the largest lever on a snapshot start.

## 2. The options

### a. Keep the directory in the snapshot, and past teardown

The snapshot already holds the built directory; its only per-member cost is teardown. `recipes/reactor_main.c` takes one extra reference to the stdlib zip's dict after the start and never drops it, so finalization leaves it alive. The instance is discarded, so nothing outlives the call. The dict holds only strings, integers and tuples, so no finalizer waits on it. After `invalidate_caches()` the new dict is freed as today.

- Snapshot start: 58.5 M → about 39.2 M at 8,191 members (38.9 M at 6,663), and no growth with the zip (INFERRED from the 19.3 M share; a C reference cannot be prototyped from Python).
- Plain start: saves 14 to 17 M, and still pays the parse. Bytes: none. Embedders: nothing changes.

### b. A precomputed index, or a sorted table searched by bisection

- **A marshalled dict in the zip.** `marshal.loads` costs 9,283 fuel a member against 26,849; it is 1,176,163 bytes at 8,191 members (`outputs/c2-*`). It still builds every object, needs a way to be found without the directory, and a check that it matches its zip. It saves about 143 M plain after plotly: less than (c), at more cost.
- **Bisection.** Almost free at start, but every lookup becomes Python. A dict subclass whose `in` and `[]` merely forward to `dict` adds 22.4 M to `import pandas`, which makes 3,590 lookups: 6.2 k each (`outputs/c3-*`). On the snapshot that tax replaces zero. Rejected.

### c. Lazy folders (prototyped: `scripts/lazy2.py`, `scripts/segment_zip.py`)

- **The table.** step 70 writes the zip sorted (READ: `scripts/make_stdlib_zip.py:13`), so each top-level folder is one contiguous run of the directory (EXECUTED: 312 runs, 312 names). The build writes one line per package folder into the zip's archive comment: the run's offset, size and count, and its `__init__.pyc` entry's place. 62 folders take 2,024 bytes. zipimport and `zipfile` ignore the comment; no member, offset or directory byte changes.
- **The start.** One read of the directory, as today. Entries outside the folders (top-level modules, every `.dist-info`) are parsed. For each folder only `folder/` and its `__init__.pyc` entry go in; the rest is pending. The result is zipimport's own plain `dict`, so every lookup stays in C.
- **The triggers.** A pending folder is parsed (one seek, one read) on the first of: a `zipimporter` made with a prefix in it, which every submodule import makes, since zipimport finds `pkg.mod` only through `pkg/`'s importer (READ: `_get_module_path`); `zipimporter.get_data` on a path in it (`pkgutil.get_data`, plotly's patch); our resource reader made for it. A first prototype without the last failed `importlib.resources.files('plotly')` with `FileNotFoundError` (`outputs/c3-*`).
- **Invalidation.** A re-read after `invalidate_caches()` loads again every folder loaded before, so cached importers still find their members.

| read (EXECUTED, `outputs/c4-*`, `c5-*`) | full | lazy, package folders | lazy, every folder |
|---|---|---|---|
| 6,663 members, snapshot binary | 168.7 M | 17.8 M (909 names) | 10.8 M |
| 8,191 members, snapshot binary | 209.7 M | 18.0 M (915 names) | 11.0 M (471 names) |
| per added plotly member | 26.8 k | **119** | 79 |
| 8,191 members, plain binary | 210.3 M | 18.9 M | |

**Checked in the guest** (EXECUTED, cache rebuilt lazily inside a call): once every folder is loaded the dict equals the full read; each folder's children keep the full read's order, and only the top level's own listing differs; `import pandas` loads three folders and a plotly figure's `to_json` four; `pkgutil.get_data('plotly', 'package_data/plotly.min.js')` as first touch returns 4,815,814 bytes; the namespace package `mpl_toolkits` resolves; `invalidate_caches()` between `import plotly.io` and `import plotly.colors` works; `pkgutil.iter_modules()` gives 252 names and 25 under `plotly.__path__` either way; `importlib.metadata` finds 59 distributions and plotly 7.1.0 either way.

**Projected plain start** (INFERRED: today's, less the full read, plus the lazy read, less teardown's share under (a)): 282.2 M → about 117 M without plotly; 323.6 M → about 115 M with it, the gap within the plain binary's noise. The cost moves to the call that uses a folder, about 27 k a member once per call: about 14 M for pandas, numpy and dateutil, against about 190 M today for every package's members.

**The snapshot stays whole.** `wizer.initialize` puts one full `_fast` read in the cache before the freeze, so the image's dict equals today's, order included. A lazy snapshot would charge a call that imports pandas about 14 M it pays nothing for today. `make_snapshot` images start from it and inherit the whole dict.

### d. Parse to the first match, or by a hash of names

The first is a linear walk, and the start's first lookup, `encodings`, sorts after most packages; the unpack loop alone is 6.6 k a member. The second makes a lookup Python, priced in (b) at 6.2 k or more. Both lose to (c).

### e. Every folder lazy, the stdlib's too

471 names at start, a read of 11.0 M against 18.0 M; the start then loads `encodings` (123 members) and the little else it imports, about 4 M better in all (INFERRED). Package folders take nearly all the gain.

## 3. The zip's other readers

- **`importlib.metadata`.** Its zip search (`_zip_resources.zip_children`) uses top-level names only, and every `.dist-info` is parsed at start, so `distributions()`, `version()` and spec 171's `top_level.txt` route see what they see today (EXECUTED: 59 distributions). Top-level order holds, since each `folder/` entry sits at its folder's sorted place (INFERRED).
- **`pkgutil`.** `get_data` works through its trigger (EXECUTED). `iter_modules` reads `zipimport._zip_directory_cache` directly (READ: `Lib/pkgutil.py:180`): the top level sees each package through its `__init__.pyc`, and a package's listing goes through its importer, which loads it (EXECUTED).
- **`importlib.resources`.** `ZipDirectoryReader` calls the loader for its folder: one line in `recipes/zip_resources.py`.
- **zipimport.** Unchanged: its dict is a `dict`, its lookups and errors its own. An embedder's zip on `sys.path` has no table and gets today's full read. The one visible difference, on the plain binary only: code reading `zipimport._zip_directory_cache[...]` directly, outside pkgutil, sees the folders loaded so far. CPython already warns against that use (issue #121342).
- **Safety.** A table that does not fit the directory (a run's first or last entry naming another folder, overlapping runs, counts that do not add up) sends the reader to the full read. A wrong table never yields a wrong dict.
- **Reproducibility.** step 70 derives the table from the sorted members it writes, so the same inputs give the same bytes on every host; spec 012's rebuild check covers it.

## 4. Who carries the members, and what each option saves (EXECUTED counts)

Today's zip has 6,663 members: the stdlib about 610, 67 `.dist-info` members in 58 folders, and 5,986 in package folders. The largest: sympy 879, tzdata 627, scipy 607, statsmodels 501, scikit-learn 410, fontTools 344, pandas 315, networkx 289, openpyxl 190, numpy 181, narwhals 164, reportlab 143, xarray 126. plotly adds 1,507, `_plotly_utils` 20 and one METADATA, the largest folder of all.

| option | plain start saves, today / with plotly | snapshot start saves | bytes |
|---|---|---|---|
| (a) keep past teardown | 14 M / 17 M | 15.7 M / 19.3 M | 0 |
| (b) marshalled index | about 117 M / 143 M | 0 | +0.9 MB / +1.2 MB |
| (c) lazy package folders | 151 M / 191 M | 0, by design | +2 KB |
| (a) + (c) | about 165 M / 208 M | 15.7 M / 19.3 M | +2 KB |
| plotly's own start cost after (a) + (c) | about +1 M (now +41.5 M) | 0 (now +3.85 M) | |

## 5. Recommendation

**One specification, "the zip's directory is read by folder": (a) and (c) together.** The reference held past teardown in `recipes/reactor_main.c`. The folder table written by step 70 (`scripts/make_stdlib_zip.py`). The lazy read, its two zipimporter triggers, the reload after invalidation and the fallback in `recipes/zip_directory.py`. The loader call in `recipes/zip_resources.py`. One full read put in the cache by `wizer.initialize`. It is medium-sized: about 150 lines of recipe and a dozen checks.

The checks count fuel (§4.9):

- A plain start grows at most 2,000 fuel per member added inside a package folder (27,100 today), on a padded zip whose padding is new folders. This replaces spec 035's bound of 30,000: a judge change, with this memo as its reason.
- A snapshot start's teardown does not grow with the directory: `pass` less a free-the-cache-and-`os._exit` call stays under a fixed bound.
- With every folder loaded, the plain dict equals the stock reader's as a dict, each folder's children in stock order. Spec 035's list-equality check on a re-read changes to match; its snapshot check holds as it is.
- One check per trigger (a submodule import, `get_data` first, a resource first, a namespace package, a re-read after `invalidate_caches`), a mismatched or missing table falling back to the full read, and the snapshot reproducible.

**It is reviewed before it is built.** It changes the artifact set (the zip's bytes by its comment, the snapshot's image) and the build recipe (step 70, the reactor): constitution §5.6. It touches nothing in `src/`, so it is not structural by AGENTS.md's definition. It is a recipe, not a patch (§4.1). It can land before plotly, whose pull request then claims about 1 M of start fuel instead of 41.5 M.

**Questions for the owner:**

1. **Lazy folders: package folders only (recommended), or every folder, the stdlib's too?** The second saves about 4 M more on a plain start and makes the start's own imports lazy.
2. **Teardown is 57.5 M of a 58.5 M snapshot start.** Should a later memo weigh ending a snapshot call without full teardown, against spec 073's choice? It is three times the snapshot saving here.

## Not run, and unsettled

- No binary was built. The plain-start projections are arithmetic over prototypes run inside a call (INFERRED). The reference past teardown was priced by subtraction, not built.
- The lazy reader ran inside a call on the snapshot binary, after the cache was cleared. Its first use at a real start, during `_Py_InitializeMain`, is the specification's first check.
- Top-level order in `zip_children` was reasoned, not compared name for name.
- The plain binary's random hash seed moves its numbers: two runs of `pass` differed by up to 0.24 M here.

## One line

The zip's directory costs a plain start about 25 k fuel a member to build and 2 k to free, and a snapshot start only the 2.4 k to free; keeping it alive past teardown, and reading each package folder on first use from a 2 KB table in the zip's comment, would take plotly's start cost from 41.5 M to about 1 M plain and to nothing on the snapshot.
