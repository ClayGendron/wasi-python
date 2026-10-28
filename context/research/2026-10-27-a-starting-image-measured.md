# A starting image, measured

- **Status:** research, 2026-10-27. A time-boxed spike on the need stated in `2026-10-27-a-snapshot-the-embedder-chooses.md` (in the main tree, not yet committed): can wasi-python give an embedder a starting image, made once from a prelude the embedder names, from which every `run()` or `Session` starts as a fresh instance? It changes nothing: no code under `src/`, `scripts/`, `recipes/` or `tests/`, no pin, no specification. Every time is wall-clock on one loaded machine: a benchmark fact, never a check. Box: three hours of one session; held (about two and a half used).
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), a fresh sub-agent of the orchestrating session
- **Evidence:** the folder of the same name beside this memo. `harness/bare.py` (a bare embedding of the snapshot through wasmtime-py's public API, on the product's own engine and module cache, with `random_get` and `clock_time_get` shadowed by counting Python functions), `harness/image.py` (design (b): every suite), `harness/design_a.py` (design (a) through `wasmtime wizer`), `harness/probe_imports.py` (question 3), `harness/wasm_sections.py` (a reader of the binaries' sections), `harness/preludes.py` (the preludes, the everything list among them), and `results/*.json` with every run's raw output. Large files (images, compiled modules, wizer roots) stayed under the worktree's `build/starting-image/`, never committed.
- **Stands on:**
  - the published 0.1.1 set, `build/release-0.1.1/set/wasi-python-0.1.1` in the main tree, checked against its `SHA256SUMS` (every line OK): `python.wasm` `d41926055c3f…`, `python-snapshot.wasm` `879bdb628a1a…`, `python-stdlib.zip` `a7b8f7cbd479…`, `MANIFEST` `636d2195edc7…`. The first runs (question 3's first pass) used `build/artifacts`, whose three binaries are the same bytes;
  - `recipes/reactor_main.c` (`PREIMPORT`, `pinned`, `wizer.initialize`, `run`, `turn`, `shutdown`, the flags `run_called`, `turned`, `session_set_up`), `recipes/reactor_bootstrap.py` (`run`, `_refresh`, `_MAIN_NAMES`, `_setup`, `turn`), `scripts/steps/80_snapshot.sh`, `docs/explanation/how-it-works.md` ("The snapshot");
  - `src/wasi_python/_call.py` (`_instance`, `_drive`, `_preopens`, `_guest_home`), `src/wasi_python/_sessions.py` (`_open_session`, `_open_wasm`, the turn driver), `src/wasi_python/_engines.py`, `src/wasi_python/_wasmtime_ffi.py`;
  - wasmtime-wasi v49, read only in the prior-art clone: `crates/wasi/src/clocks.rs:120-168` (the monotonic clock counts from its own creation);
  - wasmtime-py 50.0.1 (wasmtime 50.0.0) as `uv sync` installs it; the pinned wasmtime CLI 49.0.3 already under the main tree's `build/tools/` (nothing was downloaded).
- **Machine:** darwin-arm64, Apple M1 Pro, 10 cores, 32 GiB, macOS 26.5.2, CPython 3.14 host. The load average stood near 100 throughout (other agents' builds), so times move by up to five times between windows; fuel and page counts do not.

Labels: EXECUTED means run and seen; READ means read from a file, cited; INFERRED means the researcher's reasoning. Fuel is wasmtime's instruction count, the same on any machine.

## The short version

1. **Design (b), a run-time memory image, works through wasmtime-py's public API and today's exports** (EXECUTED). A prelude runs in a fresh instance of the snapshot module; linear memory is read with `Memory.data_ptr` and `data_len`; a later call instantiates afresh, grows memory with `Memory.grow` and copies the image in with `ctypes.memmove`. A prelude that loaded a CSV from a granted folder, fitted a scikit-learn tree on iris and defined a function gave, in a restored call, output byte-equal to a fresh instance running the same sequence; a second restored call saw nothing the first had done.
2. **Memory alone is the guest's state** (EXECUTED). The snapshot module has one mutable global, the stack pointer, not exported, initialised to 16,777,216; read through an instrumented copy, it was 16,777,216 after every export call, prelude, recursion and restored call alike.
3. **The restore is cheap; the end of the call is not** (EXECUTED). For the everything image (203 MiB, 3,245 pages) the copy took about 21 ms, almost all of it one page fault per 16 KiB page of fresh memory. The reactor's `shutdown` (Python's finalization over the whole heap) took 1.55 billion instructions and 0.65 to 0.73 s; the program itself took 4 million. A call that ends with `atexit` and a flush, without `Py_FinalizeEx`, spent 4.6 million in all.
4. **The image freezes three things the runner gives per call today** (EXECUTED): the guest's preopen table (a call's grants must repeat the image's guest names in the image's order; an extra grant is invisible, and a different folder at the same slot answers under the image's name), any descriptor the prelude left open (a later call's new file takes its number, and the prelude's file object then reads the call's file), and wasmtime's monotonic clock (each instance's starts near zero, so a time the prelude took is in the future).
5. **Randomness** (EXECUTED). With the reactor's per-call refresh, `random` and numpy's legacy global state differ between restored calls; `tempfile`'s name sequence and sympy's two module-level generators do not. Without the refresh, `random` and numpy's legacy state repeat too.
6. **Design (a), a wizer module per prelude, works and instantiates for free, but it needs wizer and a compile per host** (EXECUTED). Every package of the set imports under the build's constants. The everything module is 266 MiB, compiles in 16 s, makes a 443 MiB `.cwasm`, and instantiates from that file in 0.08 ms with no page fault. The wheel carries no wizer, and the snapshot's prelude is a compile-time string.
7. **Recommendation** (INFERRED): design (b), as a `Snapshot` object made by an embedder-side function and passed as `snapshot=` to `run`, `run_async` and `Session`; saved to and loaded from a file bound to the set's digest; with one later reactor export that runs a prelude and ends as `wizer.initialize` ends, so the grants, the descriptors and the run path stay what they are today. §5.

## 1. Design (b): a run-time memory image

### 1.1 What the module offers (EXECUTED, READ)

`harness/wasm_sections.py` over both binaries (`results/sections-0.1.1.json`):

| | `python.wasm` | `python-snapshot.wasm` |
|---|---|---|
| bytes | 99,421,513 | 104,517,748 |
| memory minimum | 640 pages (40 MiB), no maximum | 640 pages, no maximum |
| data | 2 segments, 10.7 MB | 10,002 segments, 15.8 MB, up to 41,942,989 |
| globals | one mutable i32 = 16,777,216; one immutable i32 = 0 | the same |
| exported globals | none | none |
| exports | `memory`, `_initialize`, `wizer.initialize`, `run`, `turn`, `shutdown`, `host_alloc` | `memory`, `run`, `turn`, `shutdown`, `host_alloc` |
| imports | WASI preview1 (42 functions) and `host.call` | the same |

The mutable global is the stack pointer: the stack sits below 16 MiB in linear memory (READ, `reactor_main.c`'s `__stack_high` and the 16 MiB linear stack its comment names). To see it, `with_global_exported` wrote a copy of the snapshot whose export section adds `spike.sp` for global 0, and `image.py sp` read it (`results/sp.json`): 16,777,216 after instantiation, after a pandas prelude turn, after the seal turn, after a 500-deep recursive turn, in a restored instance before and after its call. A wasm function that returns restores the stack pointer; only a trap leaves it moved, and a trapped instance is never imaged (INFERRED). No table is grown or written at run time by a statically linked CPython with no `dlopen` (INFERRED). So the image is linear memory and nothing else of the guest's.

### 1.2 How the spike drives it (EXECUTED)

Today's exports suffice, with one constraint. The snapshot's reactor refuses `run` once `turn` has been called (READ, `reactor_main.c`, `run_called || turned`), and a prelude can only be run through `turn`. So:

- **Make:** a fresh instance; `turn(prelude)`; `turn(seal)`, where the seal is one expression that copies the prelude's own names into `_reactor._MAIN_NAMES` (so each later call's fresh `__main__` starts with them), collects, and freezes the heap as `wizer.initialize` freezes the bootstrap; then `ctypes.string_at(memory.data_ptr, memory.data_len)`.
- **Call:** a fresh store with the same preopens; `memory.grow` to the image's pages; `memmove`; then `turn("raise SystemExit(__import__('_reactor').run(argv, env))")` with the call's argv (`-c program`) and environment as literals: the reactor's own argument handling, environment reset and refresh, and a fresh `__main__`; then `shutdown()`, which unfreezes and finalizes as `run` does.

### 1.3 Correctness (EXECUTED, `results/correctness.json`)

The prelude reads `/data/sales.csv` from a read-only grant, loads iris, fits `DecisionTreeClassifier(random_state=0)`, defines `summarize(frame)` and a list `counter`. The program prints `summarize(df)`, three predictions, a groupby of the CSV, and four leak probes, then mutates: appends to `counter`, adds a column to `df`, sets `numpy.sum = None`, removes `pandas` from `sys.modules`, sets `builtins.LEAK`, writes `/left-by-call.txt`.

- Restored call A, restored call B and the fresh sequence (prelude, seal and program in one instance, no image) printed the same bytes: the class means, `[0, 1, 2]`, `{'north': 17, 'south': 5}`, and `counter 1 False False True False`. B saw none of A's mutations.
- A restored call not granted `/data` printed the same: the frame was already in memory.
- The program's own turn spent 28.06 million instructions restored and 28.07 million in the fresh sequence; the prelude spent 14.73 billion once.

### 1.4 Image sizes and the per-call cost (EXECUTED, `results/sizes.json`)

Five restored calls per prelude, medians; the program is `import sys; print(len(sys.modules))`.

| prelude | prelude fuel, billions | pages | MiB | MiB changed from a fresh instance | zstd-3 MiB | restore ms | finalize fuel, millions | finalize ms | call without finalize, ms |
|---|---|---|---|---|---|---|---|---|---|
| none | 0.00 | 640 | 40.0 | 3.6 | 5.1 | 5.7 | 53 | 15 | 5.4 |
| numpy | 0.73 | 640 | 40.0 | 10.1 | 6.9 | 8.0 | 96 | 39 | 6.7 |
| pandas | 4.38 | 1,013 | 63.3 | 36.1 | 14.8 | 8.0 | 316 | 114 | 10.8 |
| scipy | 8.53 | 1,155 | 72.2 | 45.6 | 16.9 | 8.5 | 356 | 192 | 11.4 |
| scikit-learn | 14.38 | 1,762 | 110.1 | 84.0 | 28.5 | 12.4 | 689 | 259 | 17.7 |
| statsmodels | 16.17 | 1,889 | 118.1 | 92.0 | 30.9 | 13.7 | 729 | 289 | 18.1 |
| matplotlib | 7.60 | 951 | 59.4 | 32.2 | 14.2 | 7.6 | 354 | 106 | 9.3 |
| everything | 34.41 | 3,245 | 202.8 | 177.2 | 58.5 | 22.9 | 1,546 | 734 | 31.0 |

- "Everything" imports every Python package the 0.1.1 MANIFEST names, 91 modules with the submodules a program reaches for (`harness/preludes.py`): 3,717 modules in `sys.modules`. It is broader than the site's everything prelude (28.7 billion), at 34.4 billion here.
- Every restored call's program ran correctly. The program's own turn was 1.7 to 4.0 million instructions on every image.
- Instantiation was 0.09 ms every time; growing was free. `Memory.write` (the public copy) cost a little more than `memmove` (27 against 23 ms for everything). Copying only the pages that differ from a fresh instance saved little, since most of a large image is new heap.

### 1.5 What the copy costs, and copy-on-write (EXECUTED, `results/restorecost.json`, `results/cow.json`)

Twelve rounds on the everything image, alternating sources:

| source | median ms | min | max | minor faults |
|---|---|---|---|---|
| the image held as `bytes` | 21.3 | 19.9 | 57.6 | 12,984 |
| a read-only `mmap` of the image file | 21.6 | 20.3 | 50.8 | 12,984 |
| only the changed pages, from `bytes` | 18.5 | 17.2 | 19.2 | 11,344 |
| the same 203 MiB copied host to host | 5.6 | 5.0 | 16.3 | 0 |

12,984 faults is exactly one per 16 KiB page of 203 MiB: the copy's cost is the fresh memory's first touch, about 1.2 µs a page, not the bytes.

Copy-on-write from Python is possible only outside wasmtime's API: libc's `mmap` through ctypes, `MAP_PRIVATE | MAP_FIXED` from the image file over the instance's own linear memory. It worked (eight rounds, every program correct): 0.76 ms to map, 711 faults for the map and the program together. It replaces pages wasmtime owns behind its back, has no Windows form, and would put a platform branch and raw memory management in the runner; it is a measurement, not a design (INFERRED).

### 1.6 Where the end of a call goes (EXECUTED, `results/finalize.json`)

On the everything image: the program 3.9 million; the program plus `atexit._run_exitfuncs()` 4.6 million; `gc.unfreeze()` and a collection 258 million; `shutdown` after that 1,546 million; `shutdown` alone 1,546 million. So the finalization is Python tearing down 3,717 modules, not the collector. Today's `run()` pays the same for whatever a program imports (INFERRED: the site's fresh scikit-learn example's 15.29 billion includes its own teardown, about 0.69 billion on this table). With an image, a call that imports nothing new still pays the teardown of everything the image holds, unless it ends without finalizing.

### 1.7 On disk (EXECUTED, `results/disk.json`, `results/sizes.json`)

The everything image: 202.8 MiB raw; zstd level 3 (the host's `compression.zstd`) 58.5 MiB, about 0.56 s to compress and 0.2 s to decompress; zlib level 1, 72.9 MiB in 1.9 s; SHA-256 of the raw image 94 ms. Reading the raw file from a warm page cache took 30 ms; copying into the instance from an `mmap` of it cost the same as from `bytes`. Held in a process, an image is its raw size once, however many calls use it; each live instance then holds its whole image privately (every page was written).

The image's bytes depend on the guest module and the stdlib zip, which the set's `SHA256SUMS` names, and on nothing of wasmtime's: linear memory holds no engine pointer, and the one global is at its initial value (INFERRED from §1.1). So unlike the module cache, an image does not need the wasmtime version or the CPU in its key. It is not reproducible: the prelude ran with real entropy and clocks (INFERRED from §3; not run twice).

## 2. Host-side state the image freezes

### 2.1 Descriptors (EXECUTED, `results/probe-imports.json`, `results/fds.json`)

After each prelude of question 3, the guest's open descriptors were 0 to 5 only: stdin, stdout, stderr, the stdlib folder, matplotlib's data, the root. The zip reader opens the zip with a `with` block per read (READ, `recipes/zip_directory.py:41`), so zipimport holds no descriptor. None of the packages leaves a file open at import.

A prelude that does leave one open is wrong in a restored call. `kept = open('/data/sales.csv')` was descriptor 7 in the prelude's instance; in the restored call, descriptor 7 was closed, `kept.readline()` still answered from its in-memory buffer, the program's own `open('/new.txt', 'w+')` was given 7, and `kept.seek(0); kept.read()` then returned `'written by this call'`. The runner can refuse this at make time: its open-file count (the counted linker's `path_open` and `fd_close`) knows how many files the prelude left open (INFERRED from `_call._counted_linker`).

### 2.2 The preopen table (EXECUTED, `results/preopens.json`)

wasi-libc's table of preopens lives in linear memory and is filled on first use (READ, `reactor_main.c`'s `__wasilibc_reset_preopens` comment). The prelude's instance had `/data` as the fourth preopen. In restored calls:

- the same layout: `/data/hello.txt` read from the call's `/data`;
- another folder granted at `/other` in the same slot: `/data/hello.txt` read the `/other` folder's file, and `/other/hello.txt` was not found;
- the image's layout plus one more grant at `/other`: `/other/hello.txt` was not found (it resolved under the root).

So a restored call's grants must repeat the image's guest paths, in order; the host folders behind them may differ. The build-time snapshot does not have this limit because `wizer.initialize` resets the table after its imports (READ). A run-time image made through `turn` cannot reset it; a reactor export could.

### 2.3 The runner's tables, HOME, the environment, the hash key, the clocks

- **The runner's `_fs_*` tables** are host objects made per call and bound to the call's store (READ, `_call._instance`, `_fs_table._Files`). Nothing in them survives into an image, and a restored call makes its own. Mounts are preopens too (READ, `_call._instance`: their numbers come after every other), so §2.2 binds them.
- **HOME.** The runner makes `/tmp/.home-<random>` per call (READ, `_call._guest_home`). matplotlib's import made `$HOME/.matplotlib` and wrote `fontlist-v3.11.0.json` there (EXECUTED); its config folder is read once and kept. An image must be made with a fixed HOME path, and each call must give that path (INFERRED).
- **The environment.** `_reactor.run` clears and refills `os.environ` per call (READ), and the restored calls saw their own `SPIKE_X` (EXECUTED, `results/randomness.json`). But each package reads its settings once, at import (§3: 137 names for everything), and those stay as the image's environment had them: `env=` on a restored call does not reconfigure numpy, pandas, scikit-learn or matplotlib (INFERRED from §3).
- **The hash key** is fixed in the snapshot (READ); `hash("abc")` was 69,611,762 in every call (EXECUTED). An image changes nothing here.
- **Clocks.** wasmtime's monotonic clock counts from the creation of its own context (READ, `clocks.rs:120-168`). The harness's shadow answered the same way, and a time the prelude took with `time.monotonic()` was 0.7 s in the future in every restored call (EXECUTED). The wall clock is unaffected.

### 2.4 What the existing per-call restore covers (READ, EXECUTED)

The build-time snapshot's answer is two parts: the C runtime's clock, entropy and file-metadata reads answer constants while it is made (`pinned`), and `_refresh` reseeds `random` and `numpy.random`, resets `logging._startTime` and the zoneinfo path, on every `run` and on a session's first turn. Under design (b), `pinned` is already 0 when a prelude runs through `turn`, so the image holds real values; `_refresh` runs again in each call through `_reactor.run` and covers what it names. It does not cover the preopen table, a descriptor left open, the monotonic clock, the import-time environment, `tempfile`'s name sequence or sympy's generators.

## 3. Randomness and host work at import

### 3.1 The counts (EXECUTED, `results/probe-imports.json`)

One fresh instance per prelude; the WASI calls counted by the shadow, opens and file events by an audit hook, environment reads by a wrapper on `os.environ`'s lookup (Python-level only: a C `getenv` is not seen).

| prelude | fuel, billions | `random_get` calls (bytes) | `clock_time_get` monotonic | realtime | files written | environment names read |
|---|---|---|---|---|---|---|
| numpy | 0.74 | 0 | 18 | 0 | none | 3 |
| pandas | 4.45 | 11 (2,512) | 99 | 2 | none | 13 |
| scipy | 8.81 | 15 (2,576) | 115 | 2 | none | 12 |
| scikit-learn | 14.75 | 16 (2,608) | 241 | 3 | none | 23 |
| statsmodels | 16.72 | 16 (2,608) | 267 | 3 | none | 23 |
| matplotlib | 7.71 | 10 (2,496) | 107 | 2 | `$HOME/.matplotlib/fontlist-v3.11.0.json` and its lock | 13 |
| everything | 35.17 | 59 (12,632) | 571 | 3 | the same | 137 |

- 2,496 bytes is one Mersenne Twister seeding (624 words): `random`'s module instance. 16 more bytes is numpy's legacy global `RandomState` (pandas, scipy, scikit-learn, statsmodels import `numpy.random`; `import numpy` alone does not). The everything prelude made five such seedings (12,480 of its 12,632 bytes): `random`'s and sympy's two generators are the module-level ones §3.2 found; the other two are held where the scan of module namespaces does not look. The monotonic reads are mostly import timing and warnings; the realtime ones are `logging._startTime` and the like (INFERRED from the modules listed).
- The environment names include `_PYTHON_SYSCONFIGDATA_PATH` and its kin (sysconfig, through pandas, scipy and scikit-learn), `PANDAS_*`, `SKLEARN_*`, `MPLBACKEND`, `MPLCONFIGDIR`, `OPENBLAS_MAIN_FREE`, 67 of reportlab's `RL_*` and 17 of sympy's `SYMPY_*`.
- No package opened anything outside the zip at import, matplotlib's font cache aside.

### 3.2 The module-level generators (EXECUTED)

Found by scanning every module's namespace for an instance of `random.Random` or numpy's generator types after each prelude: numpy's legacy `numpy.random.mtrand._rand`, `random._inst`, `secrets._sysrand` (a `SystemRandom`, stateless), and, for everything, `sympy.core.random.rng` and `sympy.core.random._assumptions_rng`.

Two restored calls of one image (`results/randomness.json`):

| value | equal with the refresh | equal as a bare turn |
|---|---|---|
| `random.random()` | no | **yes** |
| `numpy.random.random()` (legacy) | no | **yes** |
| `numpy.random.default_rng().random()` | no | no |
| sympy's `rng.random()` | **yes** | **yes** |
| `tempfile`'s next candidate name | **yes** | **yes** |
| `uuid4()`, `os.urandom()` | no | no |
| `hash("abc")` | yes (the fixed key) | yes |

Under design (a) the same two are frozen, from zero entropy (EXECUTED, `results/design-a-randomstate.json`): sympy's `rng.random()` was 0.31409123173544795 and the temporary name `6nt4l78r` in every call, and would be on every build of that image (INFERRED from §4's identical bytes).

## 4. Design (a): a wizer module per prelude

The pinned CLI was there (`build/tools/wasmtime-v49.0.3-aarch64-macos/wasmtime`, `wasmtime wizer`). The snapshot's prelude is a compile-time string; for the probe only, a copy of `python.wasm` had `PREIMPORT`'s 55 bytes replaced in place by `exec(open('/prelude.py').read())` padded with spaces, and wizer ran with the build's flags (READ, `80_snapshot.sh`), the zip and matplotlib's data preopened as the runner grants them, `HOME=/tmp/.home`, and a prelude file that imports the bootstrap list, then the prelude, then copies its names into `_MAIN_NAMES` (`harness/design_a.py`). Not a design proposal: a measuring device.

| | scikit-learn | everything |
|---|---|---|
| `wasmtime wizer` | 17.2 s, exit 0 | 21.8 s, exit 0 |
| module | 174.5 MiB, 1,762 pages, 89.9 MiB of data | 265.6 MiB, 3,246 pages, 180.9 MiB of data |
| compile, wasmtime-py `Module` | 19.6 s | 15.7 s |
| `.cwasm` | 350.0 MiB | 442.7 MiB |
| `deserialize_file` | 0.12 s | 0.07 s |
| instantiate, compiled in process | 12 ms, about 6,000 faults | 18 to 39 ms, about 12,000 faults |
| instantiate, from the `.cwasm` file | 0.08 to 0.10 ms, 0 faults | 0.07 to 0.10 ms, 0 faults |
| `run` of the probe program, fuel | 693 million | 1,549 million |

(EXECUTED, `results/design-a-sklearn.json`, `results/design-a-everything.json`.) Every package of the set imports under the snapshot's constants. Instantiation from a file is copy-on-write, as the runner's own comment says it is (READ, `_call._instance`). `run` works unchanged: argv and environment from WASI, the refresh, and a preopen table rebuilt per call, since `wizer.initialize` resets it. Its fuel is almost all finalization, as in §1.6. Two wizer runs of the scikit-learn prelude gave the same bytes (`results/design-a-reproducible.txt`, SHA-256 `4844394c…`).

What it costs: a wizer binary the wheel does not carry, and of another wasmtime than the runtime's (49.0.3 against 50.0.0); a reactor change so the prelude is not a compile-time string; a compile of 16 to 20 s per image per host and per wasmtime version (minutes on a half vCPU, by the need memo's rate), and a 350 to 450 MiB `.cwasm` for each; a prelude that runs under constant clocks and zero entropy, so a prelude that waits on the clock never ends (INFERRED).

## 5. Recommendation (INFERRED unless marked)

### 5.1 Which design

**Design (b).** It needs no new binary, no wizer and no compile: an image is made in the seconds the prelude costs (plus 0.24 billion for the seal on everything), held as bytes, and restored in about 20 ms through public API. Against the 35-billion prelude it replaces (about 6 s here, about 29 s at the need memo's Cloudflare rate), the copy is noise. Design (a)'s free instantiation would save those 20 ms and the private copy of each instance's memory, at a compile and 443 MiB per image per host: worth having later for a container that bakes one image and runs many concurrent instances, and reachable from (b) (an image plus the module is what wizer writes; with one global at its initial value, the runner could write that module itself). Not now.

### 5.2 What the reactor should gain (a set change; its specification is reviewed before it is built, as constitution §5.6 asks for a change to the guest's exports)

One export, say `prepare(ptr, len)`: run the prelude's code from `host_alloc`'d memory in `__main__`, then do what `wizer.initialize` does after `PREIMPORT` (copy `__main__`'s names into `_MAIN_NAMES`, collect, freeze, `__wasilibc_reset_preopens()`, clear the unused stack), without setting `turned` or `run_called`. Then a restored instance takes `run` and `turn` as a fresh snapshot instance does: argv and environment from WASI, the refresh, a session's first-turn setup, and a preopen table rebuilt from the call's own grants, which removes §2.2's limit. Optionally it runs the prelude `pinned`, as wizer does, so the image is reproducible and no monotonic time is in the future; the cost is §3.2's frozen generators seeded from zeros, the same for every image, and a prelude that may not wait on the clock. Until the set carries the export, a first version can ship on today's set with §1.2's turn driver and §2.2's fixed layout.

### 5.3 The public shape

```python
snap = wasi_python.snapshot(
    "import pandas as pd\nsales = pd.read_csv('/data/sales.csv')",
    grants=[Grant("./data", "/data")],      # the layout every call repeats (until 5.2's export)
    env={"MPLBACKEND": "Agg"},               # import-time settings are frozen with the image
    fuel=None, deadline_s=600, memory_bytes=1 << 30,
)
everything = wasi_python.snapshot_of_packages()        # every package the set ships, by import name
sk = wasi_python.snapshot_of_packages(["sklearn", "pandas"])

result = wasi_python.run("print(sales.amount.sum())", snapshot=snap, grants=[Grant("./data", "/data")])
await wasi_python.run_async(code, snapshot=snap)
with wasi_python.Session(snapshot=snap) as s: ...

snap.save("app.wpsnap")                       # zstd, about 59 MiB for everything
snap = wasi_python.Snapshot.load("app.wpsnap")  # checks before any guest runs
snap.origin    # prelude SHA-256, the set's SHA256SUMS digest and version, pages, bytes,
               # guest paths of the grants, HOME, env names, the prelude's fuel, created at
```

- **Made only by the embedder.** `snapshot()` is a host function; nothing a guest can reach (no export, no door frame, no file in a grant) makes, changes or names an image, and a checkpoint of a guest's run is not offered. `tools=` is refused while making one (the host's tool state cannot be frozen). `Snapshot` is immutable; its bytes are copied into each call and never written back.
- **Refused at make time** (`SnapshotFailed`, carrying the prelude's `Completed`): a non-zero exit, a trap, a deadline, a file left open (§2.1), the image past a cap (proposed: the call's `memory_bytes`, default 1 GiB).
- **Refused at load or call time** (`SnapshotMismatch`, a `ValueError`): another set (the image is bound to the snapshot module's and zip's digests, as the set's `SHA256SUMS` lists them; not to the wasmtime version or CPU, §1.7), a format version it does not know, an image whose own SHA-256 does not match, a call whose grants do not repeat the image's guest paths (until §5.2), a `memory_bytes` below the image. A saved image is loaded only as the module cache is: a file this user owns, not group or world writable, never inside a grant (the grant judge already refuses grants over the caches; the snapshot's folder joins them).
- **Per call, the runner** checks the image against the call, makes the store and the preopens in the image's order with a HOME at the image's guest path, instantiates, grows and copies (no fuel), arms the limits, calls the program, and releases the store. It reseeds what `_refresh` reseeds, and should add `tempfile._name_sequence = None` and sympy's two generators.
- **`fuel_used`** is the call's own work from the end of the copy: the program, and the end of the call. The prelude's fuel is spent once and reported on `snap.origin`. The docs say so in one sentence.
- **How a call ends is the one choice left to the owner**, with §1.6's numbers: finalizing as `run` does today costs the teardown of everything the image holds (1.55 billion instructions on everything, about 0.7 s here), on every call; ending with `atexit` and a flush costs nothing, but a file a program left open unflushed loses its buffer, as it would under `os._exit`.

### 5.4 Left to the specification

The export's name and contract (§5.2); whether the prelude is pinned; the file format (a header with the digests, the layout, HOME and the image hash, then zstd); the cap; the end-of-call choice; the list `snapshot_of_packages` uses (the set's MANIFEST names distributions, not import names; the set could carry the list); whether a `Session` from an image may be reused across turns as today (yes: it is a session whose first state is the image).

## Still unknown

- **Linux and Windows** were not run. The copy is portable public API; its fault cost on Linux (4 KiB pages) and on Windows is not measured. The copy-on-write probe is POSIX only.
- **Resident memory** was not measured; §1.7's per-instance figure is inferred from the faults.
- **A pinned prelude through a new export** was not built; §4 shows the packages import under the constants, through wizer.
- **Concurrency**: many restored calls at once (the memory each holds, the copies competing) was not measured.
- **The runner's own path** was not prototyped: the spike's bare embedding has none of the runner's checks, its outputs went to files, and the door was a stub that answers "no host".
- **Times** are from a machine at load average 100; the restore's 20 ms and the finalization's 0.7 s should be re-measured quietly. Fuel and faults stand.
- **Design (b)'s reproducibility** was inferred, not run twice.

In one line: a starting image made at run time from the embedder's prelude, read and restored through wasmtime-py's public API, works today and costs about 20 ms per call for an image of every package (203 MiB) against the 35 billion instructions it replaces, provided the runner repeats the image's grants and HOME, refuses a prelude that leaves a file open, reseeds what the image froze, and the owner decides how a call ends, since finalizing everything the image holds costs 1.55 billion instructions a call.
