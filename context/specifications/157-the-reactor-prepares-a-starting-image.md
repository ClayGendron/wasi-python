# 157: The reactor prepares a starting image

- **Status:** drafted 2026-10-27 with specification 150, which stands on it; built 2026-10-28 on its branch, before its pull request and review (Landing notes). It changes the guest's exports, the artifact set's bytes and the build recipe, so it is reviewed before it is built (constitution §5.6), as `../reviews/157-the-reactor-prepares-a-starting-image-spec-YYYY-MM-DD.md`. Decision 5 (how a call from a prepared instance ends) is decided A by the orchestrating session on 2026-10-27; B is kept as the owner's alternative, and the decision says what changes if the owner chooses it. Revised 2026-10-28 against its pre-build review, `../reviews/157-the-reactor-prepares-a-starting-image-spec-2026-10-27.md` ("Not yet": Findings 1 to 3), every finding taken as its fix text says; the review's Disposition says where.
- **Date:** 2026-10-27
- **Owner:** Clay Gendron
- **Kind:** **build-class** (constitution §5.6 and §5.7), **not structural**: it changes no file under `src/`. Recipe: `recipes/reactor_main.c` (the export `prepare`, the flags `preparing` and `prepared` and the reference `end_function`, `pinned` split into two bits, and a prepared instance's ending in `run` and `shutdown`), `recipes/reactor_bootstrap.py` (`prepare`, `_end`, a prepared instance's `run` in the image's own `__main__`, and three more reseeds in `_refresh`), a new recipe file `recipes/snapshot-packages.txt`, and `scripts/assemble_artifacts.py` (it reads that file, writes MANIFEST's `x-snapshot-package` lines, and stops the build on a package with no line there). The artifact bytes that change: `python.wasm` and `python-snapshot.wasm` (new code, and the snapshot's heap holds the larger `_reactor`), `MANIFEST` (the recipe lines' hashes and the new line) and `SHA256SUMS`. `python-stdlib.zip` does not change (the bootstrap is frozen into the binaries, not the zip), so `x-snapshot-zip` keeps its value. No pin, no patch, no change to `downloads/SHA256SUMS`. The judge: `tests/harness/artifacts.py` (`PLAIN_EXPORTS`, `SNAPSHOT_EXPORTS` and `EXPORT_TYPES` gain `prepare`), `tests/checks/test_v1_1_artifact_set.py` (one row for the new MANIFEST line), `tests/harness/guest.py` (the judge's driver learns to prepare, capture and restore), a new `tests/checks/test_v1_4_prepare.py`, rows in `tests/unit/test_artifact_rules.py` for the list's reader, and a cap for the new family in `tests/lint/budget.toml`. Every guest fuel row and the two binaries' byte rows move; the news file claims them with the reason of Decision 9, and the release-tier ledger gets the upstream suites' block. `tests/public_api.txt` does not change.
- **Depends on:** landed and unchanged: 003 (the reactor and `wizer.initialize`), 006 (the preopen table rebuilt by name), 055 (`turn`, `shutdown`, the strong references the C side calls through), 069 (the snapshot pre-imports no package; `PREIMPORT` and its one source), 073 (a fresh `__main__` per program; `run` unfreezes before it finalizes). Stands under: 150, which builds the runner's API on this export and is built on this specification's reviewed tip or after it lands. In flight beside it: 142, 144 to 146 touch `src/` and the judge's rules only, not the recipe; whichever lands second rebases.
- **Research it stands on:** `../research/2026-10-27-a-starting-image-measured.md` ("the spike"; its evidence folder `../research/2026-10-27-a-starting-image-measured/`), §1.2 (how a prelude is driven through today's exports), §1.6 (where the end of a call goes), §2.1 and §2.2 (a descriptor left open and the preopen table), §2.4 (what the per-call refresh covers), §3.2 (the module-level generators) and §5.2 (the export it recommends). `../research/2026-10-27-a-snapshot-the-embedder-chooses.md` ("the need"). The owner's words on 0.1.2's scope (`../decisions.md`, "The scope of 0.1.2", lines 494 to 501). CPython 3.15.0's `Python/gc.c` from the pinned tarball, read in the main tree's `build/Python-3.15.0` (READ: `_PyGC_GetObjects`, lines 1705 to 1733, walks the three generations and not the permanent one; `_PyGC_Freeze`, lines 1735 to 1743, merges all three into it).

Labels: EXECUTED means run and seen; READ means read from a file, cited; INFERRED means reasoned.

## The problem

Specification 150 gives an embedder a starting image: the guest's linear memory after the embedder's own code ran, copied into each fresh instance before its program runs. The spike made such images from today's exports, through `turn`, and they work (the spike, §1.3, EXECUTED). But a prelude run through `turn` leaves three things wrong in the image, and only the reactor can set them right.

- **The preopen table is frozen.** wasi-libc fills its table of preopens on first use, in linear memory (READ, `recipes/reactor_main.c:307-309`). An image made through `turn` keeps the making call's table, so a restored call's grants must repeat the image's guest paths in the image's order; a grant in another slot answers under the image's name, and an extra grant is not found (the spike, §2.2, EXECUTED). The build-time snapshot has no such limit because `wizer.initialize` calls `__wasilibc_reset_preopens()` after its imports (`reactor_main.c:309`). A turn cannot.
- **The clocks and entropy are real while the prelude runs.** `pinned` is 0 once `wizer.initialize` returns (`reactor_main.c:306`), so a prelude's monotonic times are real. wasmtime's monotonic clock counts from each store's creation (the spike, §2.3, READ from wasmtime-wasi's `clocks.rs:120-168`), so in a restored call every time the prelude took lies in the future: 0.7 s in the spike (EXECUTED).
- **`run` and `turn` exclude each other.** A turn sets `turned`, and `run` then refuses (`reactor_main.c:383-387`). The spike had to drive each restored call through a second turn that called `_reactor.run` by hand, then `shutdown` (§1.2), which is not the path any call takes today.

Two more gaps are the reactor's to close. The per-call refresh (`recipes/reactor_bootstrap.py:63-95`) reseeds `random` and numpy's legacy generator, but not `tempfile`'s name sequence or sympy's two module-level generators, which then repeat in every call from one image (the spike, §3.2, EXECUTED). And a call from an image that ends as `run` ends today pays Python's teardown of every module the image holds: 1,546 million instructions on the image of every package, against 3.9 million for the program (the spike, §1.6, EXECUTED).

The runner also needs to know, for 150's helper that imports every package, which names to import. MANIFEST names distributions (`package scikit-learn 1.9.1`), not import names (`sklearn`, `sklearn.linear_model`).

## Research

What the spike measured is cited above and in each decision. What it did not, and how this specification's build covers it:

- **A pinned prelude through a new export** was not built; the spike's §4 showed every package of the set imports under the build's constants, through wizer. Criterion 3 runs the everything prelude through `prepare` on Linux, macOS and Windows.
- **Linux and Windows** were not run. The export's rows (Decision 8) run on the pull request's Linux and Windows legs, and on macOS under the label `ci:full`.
- **The ending's own cost** (Decision 5's collection and its walk of the collector's objects) was not measured. Criterion 5 records both on the everything image.
- **Reproducibility** of an image was inferred, not run twice. Decision 8's row makes one image twice in one process and compares the bytes.

## Decisions

### 1. One export, `prepare`

The reactor gains one export:

```c
__attribute__((export_name("prepare")))
int reactor_prepare(int32_t ptr, int32_t len);
```

It does for a prelude the host passes what `wizer.initialize` does for `PREIMPORT`. The code is `len` bytes of UTF-8 at `ptr`, a buffer from `host_alloc` that `prepare` frees on every path, exactly as `turn` takes its code (`reactor_main.c:474-508`). It returns the prelude's exit status, 0 to 255, or -1 for a refusal, which runs no Python (Decision 4). It is exported by both binaries, as every export is, and survives Wizer, which removes `wizer.initialize` and `_initialize` and keeps every other export (READ, `scripts/steps/80_snapshot.sh:18`: `--init-func wizer.initialize`; the snapshot's forbidden pair, `tests/harness/artifacts.py:25`).

Reason: the spike's recommendation (§5.2), and the smallest change that closes all three gaps of the problem at once: the preopen reset needs C (`__wasilibc_reset_preopens` is wasi-libc's), the pinned clocks need C, and a function that is not `turn` leaves `turned` unset so `run` still works in the restored instance. A host-side workaround for each would leave the layout limit in place and keep the spike's hand-driven `run` (§1.2).

### 2. The prelude runs with pinned clocks and entropy, and real file metadata

`pinned` (`reactor_main.c:60-132`) becomes two bits. `PIN_CLOCKS` covers `clock_time_get` and `random_get`; `PIN_FILES` covers `path_filestat_get` and `fd_filestat_get`. It starts at both bits, so the build-time snapshot is made exactly as today; `wizer.initialize`, `run`, `turn` and `shutdown` set it to 0 as today. `prepare` sets it to `PIN_CLOCKS` before any Python runs and to 0 before it returns, on every path.

So while a prelude runs, `time.time()` reads the build's constant, 2026-01-01T00:00:00Z (`PINNED_REALTIME_NS`, `reactor_main.c:69`), `time.monotonic()` reads 0 throughout, and entropy is zeros. File metadata is the host's own.

Reasons:

- **No time in the image lies in the future.** Every monotonic value the prelude stored is 0, which no restored call's clock is below. This closes the problem's second gap without a host-side offset on the clock, which would put a shadow on `clock_time_get` into every call.
- **The image is the same bytes when it is made again** from the same code, in one process, with the same environment and grants of the same folders. A folder made fresh for each making, such as a private root, can differ in its times and inode, so an image whose code reads them differs too. The row through the judge's driver holds the C side's determinism (Decision 8); the pin itself is held by `test_the_prelude_sees_pinned_clocks`, and 150's `test_one_prelude_makes_one_image` holds it with real entropy. A prelude made under real entropy is never reproducible (the spike, §1.7, INFERRED).
- **File metadata stays real** because pinning it breaks ordinary code. Under `PIN_FILES` every file has inode 0 on device 0, so `os.path.samefile` says any two files are one, and `shutil.copyfile` raises `SameFileError` for every copy onto an existing file (INFERRED from `pin_filestat`, `reactor_main.c:99-111`, and CPython's `shutil._samefile`, which compares `st_dev` and `st_ino` through `os.path.samefile`; READ by the pre-build review, `shutil.py:267-271`, `genericpath.py:133-136`). Real metadata costs only reproducibility across machines, which no one needs from an image: an image binds to one artifact set and is made where it is used.

The costs, which 150's documentation states: a prelude that waits for time to pass (`asyncio.sleep`, a loop on `time.monotonic()`) never sees it pass and runs to its deadline; `time.sleep` returns, though not always after the time it was asked for (INFERRED: the host's `poll_oneoff` waits against its real clock while the prelude reckons against the pinned one); and a value the prelude draws from entropy is the same in every image (`uuid.uuid4()`, `secrets.token_hex()`, a generator seeded without an argument), so a prelude must not make a secret. The module-level generators are reseeded per call (Decision 6).

### 3. What `prepare` does

In order, after its refusals (Decision 4):

1. `preparing = 1`, then `pinned = PIN_CLOCKS`. The code is copied into a `bytes` object and the buffer freed, before any Python runs, as `turn` does. `preparing` is a new static, set before any Python runs and cleared just before `prepare` returns, as `turn` sets `in_turn` (`reactor_main.c:485-490`): while it is set, `run` returns 70 and `turn`, `shutdown` and `prepare` return -1, each running no Python. A prelude that traps or calls `proc_exit` unwinds without running C, so `preparing` stays set and the instance refuses every export ever after; and a host that re-enters the instance from its door during a prelude finds every export refused.
2. It takes a strong reference to `_reactor._end` into a new static, `end_function`, as `wizer.initialize` takes `unfreeze_function` (`reactor_main.c:298-304`), so code the prelude or a later program runs cannot replace what the C side calls at the end of a call (spec 055's reason for its own references, `reactor_main.c:143-148`).
3. It reads argv and the environment from WASI, as `turn`'s first call does (`reactor_main.c:513-524`), and calls `_reactor.prepare(source, (argv, env))`. That function, new in `reactor_bootstrap.py`:
   - saves `list(sys.path)`, sets `os.environ` from `env`, and puts each argv entry after the first that begins with `/` on `sys.path`, as `_setup` does (`reactor_bootstrap.py:237-244`), so the making call's `import_path` works in the prelude;
   - sets `sys.argv` to `[""]`;
   - compiles the source as `<snapshot>`, registers it with `linecache` as `_run_turn` does, so a traceback shows its lines, and runs it in `sys.modules["__main__"]`;
   - returns 0, or the status of a `SystemExit` by `_exit_code`, or 1 after `_report` printed any other exception;
   - on 0, copies every name the prelude bound in `__main__` that does not begin with two underscores into `_MAIN_NAMES` (`reactor_bootstrap.py:24-27`), which the ending reads to tell the code's names from a call's (Decision 5), and sets `_reactor._prepared = True`;
   - on every path, restores `sys.path` to the saved list and drops each `sys.path_importer_cache` key not on it, so the making's import path never reaches a call from the image: modules the prelude imported from it stay imported, and a call that imports more from it passes its own `import_path`, which the runner judges as every call's (spec 006's rule that no guest plants code for a later call; the pre-build review's Finding 2);
   - flushes `sys.stdout` and `sys.stderr` on every path, so no byte the prelude printed stays in a buffer of the image and reappears in every call.
4. On status 0, the C side then does what `wizer.initialize` does after `PREIMPORT` (`reactor_main.c:305-310`): `gc.collect()` and `gc.freeze()` through `run_private`; `pinned = 0`; `__wasilibc_reset_preopens()`; `clear_unused_stack()`; and sets `prepared = 1`. On any other status it sets `pinned = 0` and returns; the host never images such an instance.
5. `fflush(NULL)`, `preparing = 0`, and the status is returned.

`prepare` never sets `turned` or `run_called`. So a restored instance is, to the C side, a snapshot instance whose interpreter has more in it: `run` reads argv and the environment from WASI, refreshes (Decision 6) and runs the program; `turn`'s first call runs the session's setup; and wasi-libc rebuilds the preopen table from the call's own grants, by name and in any order, on first use (spec 006, Decision 5). The layout limit of the spike's §2.2 is gone.

**A program runs in the image's own `__main__`.** In a prepared instance (`_reactor._prepared`), `_reactor.run` runs the program, a script and `-m` in `sys.modules["__main__"]`, the module the code ran in, instead of making a fresh one (`_fresh_main`, `reactor_bootstrap.py:30-36`, which a call without an image keeps). Each call has a private copy of that module, so nothing it binds reaches another call. Reason: a call then means what one `-c` program of the code and the program means, and what a session's second turn means: `x = 1; def f(): return x` as the code and `x = 2; print(f())` as the program print 2 in all three, where a copy of the names into a fresh module would print 1 from an image (the 150 review's Finding 6, decided by the orchestrating session on 2026-10-28). Spec 073's reason for a fresh `__main__`, a frozen one that was never freed at finalization, does not hold here: a prepared instance's ending drops the call's own names and collects them (Decision 5).

### 4. When `prepare` refuses

It frees the buffer and returns -1, running no Python, when any of these holds: `initialized` is 0 (the plain reactor before a call: an image is made only from the snapshot, whose interpreter `wizer.initialize` started with the fixed hash key every snapshot instance shares); `preparing`, `prepared`, `run_called`, `turned` or `shut` is set (once per instance, and before anything else); or `len < 0`. A NULL pointer with a length above 0 is the host's out-of-memory, as for `turn`: the prelude raises `MemoryError` and returns 1.

Reason: an image is a snapshot instance's memory, restored into a snapshot instance; a prelude run after a program or a turn would freeze that program's state too, which is a checkpoint of a guest's run, outside this release (the owner, `../decisions.md:498`). Since a running program or turn has set `run_called` or `turned`, and a running prelude has set `preparing`, nothing a guest does, and no host that re-enters from the door, can reach `prepare` and have it run.

### 5. How a call from a prepared instance ends (A, decided; B the owner's alternative)

The orchestrating session chose A on 2026-10-27; the owner may choose B before the build, and what changes under B is stated.

**The choice.** In an instance where `prepared` is 1, `run` and `shutdown` end the call one of two ways.

| | A. Run `atexit` and flush (recommended) | B. Python's full teardown, as `run` does today |
|---|---|---|
| what runs | `_reactor.run`'s own flush of `sys.stdout` and `sys.stderr`; then every `atexit` handler; then the call's own names dropped and a collection of what the call made; then a flush of every writable file object still open; then every C stream | the same handlers, then `gc.unfreeze()` and `Py_FinalizeEx()`: every module the image holds is torn down |
| instructions at the end of a call, on the image of every package | the program and its `atexit` handlers: 4.6 million in all for a program of 3.9 million (the spike, §1.6, EXECUTED), plus the collection and the flush's walk, each over the call's own objects only (unmeasured; criterion 5 records both) | 1,546 million, on every call, whatever the program did (§1.6, EXECUTED); 0.65 to 0.73 s on an M1 Pro, about 1.3 s on Cloudflare `standard-1` at the need's 1.2 billion a second (INFERRED) |
| on smaller images (§1.4, EXECUTED) | the same few million | numpy 96 M, pandas 316 M, scikit-learn 689 M, statsmodels 729 M |
| what a program loses | the finalizers of objects still reachable from the image's modules: a file, a `zipfile.ZipFile` or a `gzip.GzipFile` a program hung on `numpy` or on a module it imported is flushed, not finalized, so what its buffers hold is written and what a compressor holds is not, and a `gzip` or `zipfile` stream left that way is cut short | nothing: CPython's own semantics |

**The recommendation, A.** The image exists to make a call cost its own work. Under B a call from the image of every package pays 1,546 million instructions to tear down modules it never used, 400 times its program, and the instance is discarded right after; that would undo most of what the image saves for the short programs it is for. A keeps spec 073's promise for what the program's own names held: its bytes, and a `ZipFile`'s directory (`tests/checks/test_v1_4_embedding.py:117` and `:167`, whose second row promises that a `ZipFile` left open is finalized, its directory written), because the ending drops those names and collects what they held before it flushes. What it gives up is the finalizer of an object the program hung on the image's own modules, which the documentation says in one sentence ("when a call from a snapshot ends, what your program's own names held is finalized as in CPython; an object it hung on an imported module is flushed, not finalized; close what you open, or use `with`"). A call without an image, `run` and a `Session` alike, keeps its full teardown: nothing changes for them.

**The mechanism of A.** `_reactor._end()`, new in `reactor_bootstrap.py`:

1. `atexit._run_exitfuncs()`, which runs every handler, the image's and the call's, and reports a handler's exception itself, as CPython does at exit.
2. The call's own names are dropped: every name of `__main__` (the image's own, in a call and in a session alike) that is not bound to the same object in `_MAIN_NAMES`; and `sys.last_exc`, `sys.last_type`, `sys.last_value` and `sys.last_traceback`. Then `gc.collect()`, which walks only the generations made since the image was frozen, so `__del__`, `weakref.finalize` and a `ZipFile`'s directory run for what the program alone held, by reference count or by the collection (the pre-build review's probe, EXECUTED there on CPython 3.14.10: a `ZipFile` in a cleared dict, then `gc.collect()`, is a readable zip, the freeze intact).
3. A walk of `gc.get_objects()` for instances of `io.TextIOWrapper`, `io.BufferedWriter` and `io.BufferedRandom` that are not closed: each text wrapper is flushed (which flushes its buffer), then each buffered writer, and the writers' pass is repeated while a pass flushed any byte, at most three passes, since a writer stacked on another (`gzip.GzipFile` holds its own `io.BufferedWriter`) pushes bytes into the lower one when it flushes (the pre-build review, EXECUTED there: one pass left a file at 12 bytes, a second at 16,404). An exception from one flush is printed to `sys.stderr` as CPython prints an exception ignored in a finalizer, and the walk goes on. The walk sees the call's own objects only: `gc.freeze()` in `prepare` moved every object of the image to the permanent generation, which `gc.get_objects()` does not visit (READ, `Python/gc.c:1715-1721` and `:1735-1743`); and a prelude that left a file open is refused when the image is made (150, Decision 4), so the image holds none.
4. `sys.stdout.flush()` and `sys.stderr.flush()`; it returns `False` when either raises, else `True`.

In C, `run` and `shutdown` in a prepared instance call `end_function` in place of the unfreeze and `Py_FinalizeEx()`, and return 120 when it returned `False` (or raised), as they return 120 when `Py_FinalizeEx()` reports an error (`reactor_main.c:426-428`, `:570`); then `fflush(NULL)`, which flushes every C stream, a C library's own `FILE *` included, for the cost of two. `shutdown` still sets `shut` and refuses a second call. The other options for the flush were weighed and refused: CPython keeps no list of open files (a file is flushed by its own deallocation), and wrapping `open` to track files at their opening misses `io.FileIO`, `os.fdopen` and C-level opens, and changes the `open` a program sees.

**If the owner chooses B.** `run` and `shutdown` take today's path in every instance; `_end`, its collection and its walk are not built; Decision 8's ending rows assert today's teardown instead (each still passes: B is CPython's own ending); criterion 5 records the teardown's fuel; 150's documentation drops the finalizer sentence and states the teardown's cost on the limits page.

### 6. Three more reseeds in `_refresh`

`_refresh` (`reactor_bootstrap.py:63-95`), which runs at the start of every `run` and in a session's first turn, gains, each only when its module is in `sys.modules`:

- `tempfile._name_sequence = None`, so `tempfile` makes a fresh name sequence seeded from the call's entropy on its next use, as a fresh interpreter does;
- `sympy.core.random.seed()`, sympy's own public call that reseeds both its module-level generators, `rng` and `_assumptions_rng` (the spike, §3.2, EXECUTED: both repeated across restored calls);
- for each other generator a package makes at import and seeds from entropy, its package's own public reseeding call, or `.seed()` on the instance where the package has none. The spike counted five Mersenne Twister seedings in the everything prelude and named three (`random`'s and sympy's two); the other two "are held where the scan of module namespaces does not look" (§3.1, line 150). The builder finds them by a walk of `gc.get_objects()` run as the last lines of the everything prelude, before `prepare` freezes it (after the freeze `gc.get_objects()` lists none of them), for instances of `random.Random` that are not `random.SystemRandom` (stateless, `secrets._sysrand` among them, needing no reseed), and of `numpy.random.Generator`, `numpy.random.RandomState` and `numpy.random.BitGenerator` other than numpy's global one, with `gc.get_referrers` naming each one's owner; adds a reseed for each that a fresh import seeds from entropy; and lists each in the landing notes with its owner. A generator its package seeds from a constant is left as it is, since a fresh import seeds it the same way.

On a call from the artifact set's own snapshot none of these modules is imported when `_refresh` runs (`PREIMPORT` holds none of them, `reactor_main.c:57`), so each is one failed dictionary lookup. Reason: the reactor already owns the per-call refresh of what a snapshot froze, and putting the rest there keeps one list and one place; a host-side reseed would need a turn of its own before every call.

### 7. The package list: a recipe file and a MANIFEST line per distribution

A new recipe file, `recipes/snapshot-packages.txt`, holds what a program imports to use each distribution the set ships, one line per MANIFEST `package` line:

```
# <distribution>: the import names a program reaches for, in import order.
numpy: numpy
pandas: pandas
scikit-learn: sklearn sklearn.linear_model sklearn.tree sklearn.ensemble ...
pybind11:
```

- Each distribution named in `scripts/assemble_artifacts.py`'s `PACKAGES` has exactly one line. A C library linked into a Python package, or a build-time tool (pybind11, cppy, qhull, freetype and the like), has an empty right side: its package's line imports it. A C library the stdlib exposes is named by its module (`zlib: zlib`, `bzip2: bz2`, `xz: lzma`, `sqlite-autoconf: sqlite3`).
- The names include the submodules a program reaches for, since many packages load them lazily (`import sklearn` loads no estimator). The first version is the spike's everything list (`../research/2026-10-27-a-starting-image-measured/harness/preludes.py`, `EVERYTHING_MODULES`, 91 names, which imported cleanly and gave 3,717 modules; §1.4) with `matplotlib.use("Agg")` left out (the file names imports only, and pyplot resolves its own backend), plus `zlib`, `bz2` and `lzma`.
- `scripts/assemble_artifacts.py` gains one reader, `snapshot_packages(text, packages) -> list[tuple[str, list[str]]]`, beside `preimport_list` (`scripts/assemble_artifacts.py:444-450`): it parses the file, stops the build naming the distribution when a `PACKAGES` key has no line, when a line names a distribution `PACKAGES` lacks, or when a name is not a dotted Python identifier, and returns each distribution with its names, in file order, a name already on an earlier line dropped. MANIFEST gains one `x-snapshot-package <distribution> <name> <name> …` line per distribution that has names, in the recipe file's order, after `x-preimport` (`:885`); a distribution whose right side is empty has no line.

Reasons: the list is a fact of the set, so the set carries it; a runner given another set (`artifacts=`) then imports that set's list, never its own idea of it. One line per distribution keeps the names a developer installs and types (`scikit-learn`, `pillow`, `pyyaml`, `beautifulsoup4`, the names of `pip` and of `docs/reference/packages.md`) beside the names a program imports, so 150's helper takes either and needs no guess from dots (the pre-build review's Finding 8); a MANIFEST line is an artifact byte, cheaper to shape now than later. The build's refusal makes the rule self-enforcing: a specification that adds a package cannot build its set until it says what to import, or that nothing is. The recipe file, not a constant in the script, because 069 moved `PREIMPORT`'s list out of the script for the same reason (spec 069, Decision 3) and the recipe lines hash it into MANIFEST.

### 8. The rows first

Each is written before the code and seen failing on `dev`'s set (criterion 1). The guest rows drive the export through the judge's own driver, `tests/harness/guest.py`, which stays apart from the runner it judges (`guest.py:1-13`): `Turns` gains `prepare(code)` (the export, through `host_alloc`), `image()` (the memory read whole) and a `run(..., image=…)` path that grows a fresh instance's memory and copies an image in before its `run`. The driver answers entropy and the clocks itself, seeded alike in every run (`guest.py:9-12`), so a row here can show that a generator was reseeded, not that two calls differ; 150's rows show that, through the runner and real entropy.

- `tests/harness/artifacts.py`: `PLAIN_EXPORTS` and `SNAPSHOT_EXPORTS` gain `prepare`; `EXPORT_TYPES` gains `"prepare": "(i32, i32) -> (i32)"`. `test_plain_reactor_exports` and `test_snapshot_exports` (`tests/checks/test_v1_1_artifact_set.py:85-96`) fail on `dev`'s set.
- `tests/checks/test_v1_1_artifact_set.py::test_manifest_names_the_snapshot_packages`: MANIFEST's `x-snapshot-package` lines follow `x-preimport`; each names a distribution of a `package` line, at most once, with at least one name; each name is a dotted identifier, and none repeats across the lines. That every entry imports is the slow row's to show (`test_the_everything_prelude_prepares`, below), since a compiled package such as kiwisolver is a builtin module with no file in the zip.
- `tests/checks/test_v1_4_prepare.py`, on the snapshot, each row recording its fuel:
  - `test_prepare_refuses`: -1 on the plain reactor, after `run`, after `turn`, and a second time; no output in each case.
  - `test_a_trapped_prepare_leaves_nothing_callable`: a prelude that loops under a small fuel cap traps; then `run` returns 70, and `prepare`, `turn` and `shutdown` return -1, each with no output (the pre-build review's Finding 1).
  - `test_the_makings_import_path_is_gone`: an image made with a read-only folder at `/a` on the import path, whose module the prelude imports; a restored `run` of `-c import sys, amod; print('/a' in sys.path, amod.__name__)` prints `False amod` (the pre-build review's Finding 2).
  - `test_a_prepared_image_runs_a_program`: a prelude defines `def f(): return 42` and `x = [1, 2]`; the image restored into a fresh instance, `run` of `-c print(f(), x)` prints `42 [1, 2]`.
  - `test_the_preopens_are_the_calls`: the image made with read-only folders granted at `/a` then `/b`; a restored instance granted `/b` then `/a`, and `/c` besides, reads each folder's own file at its own path.
  - `test_the_prelude_sees_pinned_clocks`: the prelude records `time.time()`, `time.monotonic()` and `os.urandom(4)`; they are 1767225600.0, 0.0 and four zero bytes; a restored program's `time.monotonic()` is at or above the prelude's.
  - `test_a_prelude_does_not_pin_files`: in a prelude, two different files of a grant have different `(st_dev, st_ino)` and `shutil.copyfile` between them succeeds.
  - `test_the_refresh_reseeds_what_the_image_froze`: a prelude imports `random`, `numpy.random`, `tempfile` and `sympy` and prints each generator's next draw (`random.random()`, `numpy.random.random()`, `sympy.core.random.rng.random()`) and `next(tempfile._get_candidate_names())`, then repeats nothing; a restored `run` prints the same four draws, and each differs from the prelude's.
  - `test_a_program_shares_the_codes_namespace`: the code `x = 1` and `def f(): return x`; a restored `run` of `-c x = 2; print(f())` prints 2, as one `-c` program of both does.
  - `test_a_prepared_call_keeps_an_unclosed_files_bytes`: a restored program opens a file in a writable grant, writes 100 bytes and ends without closing it; the file holds the 100 bytes (Decision 5, choice A; under B the same row holds through the teardown).
  - `test_a_prepared_call_finalizes_a_zipfile_left_open`: a restored program opens a `zipfile.ZipFile` for writing in a writable grant, writes one member and ends without closing it, as `tests/checks/test_v1_4_embedding.py:167` does without an image; the file is a readable zip holding that member (the pre-build review's Finding 3).
  - `test_a_hung_writer_is_flushed`: a restored program opens a file, writes 100 bytes and hangs the file object on the `json` module; the file holds the 100 bytes, flushed, not finalized.
  - `test_a_prepared_call_runs_atexit`: a handler registered in the prelude and one registered by the program both run, in reverse order of registration, before the call ends.
  - `test_a_prepared_session_ends_light`: a restored instance's `turn` then `shutdown` returns 0 and keeps an unclosed file's bytes; its fuel is recorded.
  - `test_a_prepared_image_is_reproducible`: one prelude prepared twice in one process gives byte-equal images; this holds the C side's determinism, since the driver answers entropy and the clocks alike in every run.
  - `test_the_everything_prelude_prepares` (marked slow): the prelude imports every name of the `x-snapshot-package` lines; it returns 0; a restored `run` of `-c pass` ends with exit code 0; the prelude's fuel, the image's pages, and the restored call's fuel are recorded (criterion 5).
- `tests/unit/test_artifact_rules.py`: `snapshot_packages` refuses a missing distribution, an unknown one and a name that is not a dotted identifier, each naming it; it keeps file order, drops a name already on an earlier line, and gives a distribution with an empty right side no MANIFEST line.
- `tests/lint/budget.toml`: the family `test_v1_4_prepare` gets its cap, twice the largest fuel its first acceptance records, as the file's header rule says.

### 9. The fuel and bytes that move, and how they are claimed

Every guest row's fuel moves, because both binaries carry new code and the snapshot's heap holds a larger `_reactor`. The sources, INFERRED: the plain reactor unmarshals the larger `_reactor` at each start; every run's `_refresh` makes three more lookups; `run` takes one more branch; and the snapshot's heap layout shifts, which can move a run's fuel either way. The binaries' `bytes` rows (`test_binary_is_a_core_wasm_module[plain]` and `[snapshot]`) grow by the new code.

The news file, `../changes/157-the-reactor-prepares-a-starting-image.md`, claims them: `grows` names `tests/checks/test_v1_*`, which covers the product's rows and the upstream suites' alike; `growth` gives this reason ("the reactor gains the export `prepare`, a prepared instance's ending and three reseeds in `_refresh`, so both binaries are larger and every run unmarshals and refreshes a little more"). Since the upstream suites' rows are release-tier rows, a block is appended to `../release-tier-claims.toml` naming `tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[*`, as 127's did. The landing notes give the bare `-c pass` fuel on both binaries before (`dev`'s accepted rows) and after (the pull request's), and name every row whose fuel moves by more than the bare `-c pass` row's move plus 1% of that row's own fuel, with its cause. A fall needs no claim.

Its `## Changelog` entry, under `### New` in 152's shape, or the same words under `### Added` in the old shape if 152 has not landed:

```
- **Other engines can start every call from a starting image.** The snapshot binary exports `prepare`, which runs your setup code once and leaves memory ready to copy into each new instance. [Embed from other languages](https://claygendron.github.io/wasi-python/how-to/embed-from-other-languages/)
```

### 10. The documentation of the export

- `docs/explanation/how-it-works.md`, "The reactor and its exports": `prepare` joins the list, in one sentence: it runs code the host passes in a snapshot instance that has run nothing, then leaves the instance ready to be imaged, with its preopen table cleared and its heap frozen.
- `docs/how-to/embed-from-other-languages.md`, "Load the artifacts in your own engine": a short subsection for an embedder in another language: call `prepare` with code from `host_alloc`, read linear memory whole, and start each later instance by growing its memory to the image's size and copying the image in before calling `run` or `turn`; the image binds to the exact snapshot binary and stdlib zip; a call from it ends without Python's teardown (Decision 5).
- 150 writes the Python embedder's page.

## Intent

After this specification, the artifact set lets any embedder make a starting image from its own code with one export call, and start any number of fresh instances from it: each instance gets its grants from its own call in any order, never sees a time in its future, gets fresh randomness, and ends a call at the cost of its own work. The set says which names import every package it ships.

## Design

```
recipes/reactor_main.c          PIN_CLOCKS, PIN_FILES; preparing; prepared; end_function;
                                reactor_prepare (export "prepare"); every export refuses while preparing;
                                run and reactor_shutdown: a prepared instance ends through end_function
recipes/reactor_bootstrap.py    prepare(source, environ) with sys.path restored; _prepared; run in the
                                image's own __main__ when prepared; _end(); _refresh's three reseeds
recipes/snapshot-packages.txt   new: one line per distribution
scripts/assemble_artifacts.py   snapshot_packages(text, packages); the x-snapshot-package lines
tests/harness/artifacts.py      the export sets and types
tests/harness/guest.py          Turns.prepare, Turns.image, run(image=...)
tests/checks/test_v1_1_artifact_set.py   test_manifest_names_the_snapshot_packages
tests/checks/test_v1_4_prepare.py        Decision 8's rows
tests/unit/test_artifact_rules.py        the reader's rows
tests/lint/budget.toml          the new family's cap
docs/explanation/how-it-works.md, docs/how-to/embed-from-other-languages.md   Decision 10
context/changes/157-the-reactor-prepares-a-starting-image.md                 Decision 9's claim
context/release-tier-claims.toml                                            the upstream rows' block
```

The commits, in order: the rows seen failing; the recipe and the reader; the docs; the news file and the ledger block.

## Scope

In: the above. Out, each with its reason:

- **The runner's API** (`make_snapshot`, `Snapshot`, `snapshot=` taking one): specification 150, so the export is reviewed and landed on its own.
- **Design (a), a Wizer module per prelude**: the spike, §4 and §5.1: it needs a wizer binary the wheel does not carry and a compile per image per host. Not built.
- **A checkpoint of a guest's run**: `prepare` refuses after `run` or `turn` (Decision 4); the owner kept it out of 0.1.2 (`../decisions.md:498`).
- **Copy-on-write restores**: a measurement, POSIX only (the spike, §1.5); a later optimisation, in the runner, not here.
- **Any change to `PREIMPORT`** or to the build-time snapshot's making: the rule of spec 069 stands; `wizer.initialize` is unchanged but for `pinned`'s new name for its value.

## Acceptance criteria

1. **Seen failing first on `dev`'s set.** The export rows, the MANIFEST row and every row of `test_v1_4_prepare.py` fail on `dev`'s set (no `prepare` export, no MANIFEST line), and the reader's unit rows fail before the reader exists; the pull request names each with its one failing line.
2. **The set builds.** The pull request's run builds the set from the pins; step 80 prints the snapshot's size and hash; MANIFEST holds one `x-snapshot-package` line per distribution with names and the same `x-snapshot-zip` value as `dev`'s set; `python-stdlib.zip`'s SHA-256 equals `dev`'s. The landing notes give both binaries' sizes and SHA-256 prefixes before and after.
3. **The rows pass** on the pull request's Linux and Windows legs, and on macOS under the label `ci:full`, which the pull request carries: the export rows, the MANIFEST row, every row of `test_v1_4_prepare.py` including the slow one, and the reader's unit rows.
4. **No pass is lost**, and every growth is claimed. The gather's `GROWTH` lists only rows the news file's claim names; the landing notes give the bare `-c pass` before and after on both binaries, as Decision 9 says.
5. **The facts, recorded.** From the slow row, in the landing notes: the everything prelude's fuel through `prepare`, the image's pages, the restored `-c pass` call's fuel, and, for the owner's comparison, the shares of that fuel spent in `_end`'s collection and in its walk of `gc.get_objects()`, each measured by a probe that runs it alone in a restored instance (EXECUTED by the builder, with the command).
6. **The generators.** The landing notes list every generator the builder's walk found at the end of the everything prelude, before the freeze (Decision 6), with its owner and whether `_refresh` reseeds it and why.
7. **The docs** of Decision 10 are in the pull request, and the documentation site builds.
8. **The rules.** `uv run ruff check`, `uv run ruff format --check`, `uv run pytest tests/lint` and the fast tier are green; `tests/public_api.txt` is unchanged; `ci-status` is green; the pre-build review and the pull request's review are cited in the landing notes.

## Landing notes

Built 2026-10-28 by an agent (Claude Opus 5.5), the builder of this specification, a sub-agent of the orchestrating session, in the worktree `../wasi_python-wt/spec-157`, on `spec/157-the-reactor-prepares-a-starting-image` rebased onto `658a6213` (`dev`'s tip). The set was built locally from the pins, `scripts/build.sh --from 60`, in a copy-on-write clone of the main tree's build tree with its paths rewritten to the worktree's; unchanged, that clone rebuilt the published 0.1.1 set byte for byte (all four hashes and MANIFEST, `build/157/build-baseline.log`), so dev's set is 0.1.1's. Pull request, CI run and review: not yet. Labels: EXECUTED means I ran it, READ means I read the file cited, INFERRED means my reasoning.

**The baseline, rebuilt byte for byte** (EXECUTED, `build/157/build-baseline.log`): before any change, `scripts/build.sh --from 60` in the worktree, on the cloned build tree with the main tree's paths rewritten to the worktree's, gave `python.wasm` `d41926055c3f`, `python-snapshot.wasm` `879bdb628a1a`, `python-stdlib.zip` `a7b8f7cbd479` and `MANIFEST` `636d2195edc7`: the published 0.1.1 set's four files exactly. So the local build's steps 60 to 90, over the main tree's objects from the steps before 60, reproduce dev's set, and every difference in the set after is this specification's; the pull request's rebuild from the pins is the whole build's evidence. The log prints the three binaries' hashes; MANIFEST's equality is held by the saved set, `build/157/set-before/`, whose four files equal 0.1.1's by `cmp` (EXECUTED by the pull request's reviewer, 2026-10-28).

The commits, in the Design's order: `f147cde5` the rows, seen failing; `09731d94` the recipe and the reader; `532d58f3` the docs; `c948b4d5` the pinned-clocks row reworded for the clock rule; then the news file, the ledger block and these notes.

**Seen failing first** on the published 0.1.1 set (EXECUTED, `build/157/rows-failing-on-0.1.1.log`, not committed): `test_plain_reactor_exports` and `test_snapshot_exports`, "no export prepare; no function export prepare"; `test_manifest_names_the_snapshot_packages`, "MANIFEST has no x-snapshot-package line"; the fifteen fast rows of `test_v1_4_prepare.py`, `KeyError: 'prepare'` (the driver finds no export); `test_the_everything_prelude_prepares`, "MANIFEST has no x-snapshot-package line"; the five reader rows, "module 'assemble_artifacts' has no attribute 'snapshot_packages'". The MANIFEST rule's own unit row and the budget row were written with their functions.

**The set** (EXECUTED; before is 0.1.1's, which dev's set equals):

| file | before | after |
|---|---|---|
| `python.wasm` | 99,421,513 bytes, `d41926055c3f` | 99,431,714 bytes (+10,201), `915306e6c191` |
| `python-snapshot.wasm` | 104,517,748 bytes, `879bdb628a1a` | 104,546,308 bytes (+28,560), `67889390b57d` |
| `python-stdlib.zip` | 53,915,154 bytes, `a7b8f7cbd479` | the same bytes |
| `MANIFEST` | `636d2195edc7` | `fcd0008bea6e`: 57 `x-snapshot-package` lines (94 names) after `x-preimport`; `x-snapshot-zip` unchanged |

**The bare `-c pass`** through the judge's driver (EXECUTED, `build/157/probes/bare.py`, `build/157/probes/bare.out`): the plain reactor 271,947,108 before, 272,199,837 after (+252,729, +0.093%); the snapshot 53,388,410 before, 53,506,765 after (+118,355, +0.22%), on the set with the review's fix (`build/157/probes/bare-after-fix.out`; before the fix they were 272,199,833 and 53,506,761).

**The fast tier** (EXECUTED, `uv run pytest -m "not slow" -n 3` on the local set, `build/157/fast-tier-2.log`): 3,886 passed, 6 skipped; the ratchet against `1921c381` lost 0, gained 17, grew 113 (every one claimed by the news file's `tests/checks/test_v1_*`; the gather printed no unclaimed row); one accepted pass blocked locally, `test_wheel_carries_the_artifact_set`, which needs a built wheel. Against `dev`'s accepted darwin fuel, 124 rows grew and 93 fell; none moved by more than the bare `-c pass` row's move (252,725, the plain reactor's) plus 1% of its own fuel. The largest moves: `test_unbuffered_output_survives_a_hard_exit[snapshot]` +16,703 (+1.29%), `test_recursion_through_python_raises[map-snapshot]` +165,471 (+0.29%), `test_no_cpython_test_module_is_built_in` +137,031 (+0.25%); the largest fall `test_formula_engines_run_pure[plain]` −13,367,384 (−0.16%). The first full run found two rows red, both fixed: `test_no_test_reads_a_clock` read the pinned-clocks row's guest code (it now names the clocks through `getattr`), and `test_every_build_python_is_pinned` read meson logs in the cloned build tree that still named the main tree's path (rewritten to the worktree's; a local artifact of the clone).

**Criterion 5, the facts** (EXECUTED on the local set, the slow row and `build/157/probes/ending.py`): the everything prelude (94 names) through `prepare` ran 34,656,378,777 instructions; the image is 3,245 pages (202.8 MiB); a restored `-c pass` ran 3,440,768, against the spike's 1,546 million for an ending by teardown. Of that call, the ending (`_end`, measured as `shutdown` after a session's first turn on the same image) is 447,538: switching off the walk of `gc.get_objects()` takes it to 338,421 (the walk's share 109,117, 24%), switching off the collection to 420,405 (27,133, 6%), both to 311,702; the rest is the `atexit` handlers the packages register and the flushes. Most of the call is the per-call refresh (a session's first turn on the image: 3,375,169), which reseeds the generators below.

**Criterion 6, the generators** found by a walk of `gc.get_objects()` as the everything prelude's last lines, before the freeze (EXECUTED, `build/157/probes/generators.py`), with each one's owner:

- `numpy.random.mtrand._rand`, numpy's global `RandomState`, and its `MT19937`: reseeded already (`numpy.random.seed()`).
- `random._inst` (also reached as `jinja2.utils.choice`, `more_itertools.more.random` and other bound methods): reseeded already (`random.seed()`).
- `sympy.core.random.rng` and `sympy.core.random._assumptions_rng`: reseeded, by sympy's own `sympy.core.random.seed()`.
- `more_itertools.recipes._private_randrange`'s `random.Random`: reseeded, `.seed()` on the instance (the package has no call); `test_the_refresh_reseeds_what_the_image_froze` holds it.
- scikit-learn's `TreeGrower.__init__` default `rng=np.random.default_rng()` (`sklearn/ensemble/_hist_gradient_boosting/grower.py:262`), a `Generator` with its `PCG64`: reseeded, its bit generator's state set from a fresh one, since a `Generator` has no `seed()`.
- scikit-learn's `Splitter.__init__` default `rng=np.random.RandomState()` (`splitting.pyx:200`), with its `MT19937`: not reseeded (see below).
- `sympy.core.symbol.Dummy._prng`: not reseeded (see below).
- `tempfile._name_sequence` is made on first use, not at import: set to `None` per call.

**Found by the review** (`../reviews/157-the-reactor-prepares-a-starting-image-pr-2026-10-28.md`, Finding 1, Medium): after a `prepare` that returned anything but 0, `prepare` ran again and returned 0, and `run` and `turn` ran too, since the refusal tested `preparing` and `prepared` and a failed prelude clears the one without setting the other; an embedder retrying a failed setup on the same instance got an image holding the failed attempt's state. Fixed as the review's text says: a `prepare_called` bit, set with `preparing` and never cleared, makes `prepare` refuse a second call whatever the first returned (and keeps `end_function` from being taken twice), and `run` (70) and `turn` (-1) refuse, running no Python, in an instance whose `prepare` failed; the embedder's page says to discard such an instance. `test_prepare_refuses` gained the three cases, seen failing first on the earlier head's set (EXECUTED, `build/157/refuses-before-fix.log`): "after a failed prepare: returned 0; stdout b'ran\n'; a run after a failed prepare: returned 0; stdout b'ran\n'; a turn after a failed prepare: returned 0; stdout b'ran\n'", green after the rebuild. Its Low 3 is taken too: the page says the making call's argv folders are on `sys.path` for the setup alone. The set moved again by the few bytes of the new flag; the figures above are the fixed set's.

**Different from the specification, each for a reason:**

- **Two generators are listed and not reseeded.** scikit-learn's `Splitter` default is a Cython default argument, held where Python cannot reach it once the heap is frozen (its only referrer the walk sees is the list it returned); its one caller, `TreeGrower`, always passes its own generator. sympy's `Dummy._prng` draws once, at class creation, for `Dummy._base_dummy_index`; reseeding it changes nothing a call sees, and redrawing the index would copy sympy's constants into the reactor.
- **Two more reseeds than "three".** Decision 6's third bullet asks for one per generator found; the walk found `more_itertools`' and scikit-learn's `TreeGrower`'s, so `_refresh` has five reseeds where the Kind line says three.
- **A new check file's cap waits for its first acceptance** (`tests/harness/budget.py`'s `stale_caps` and `new_families`, the lint row and a unit row). The gather and the acceptance refuse fuel from a family with no cap, and the lint refused a cap no accepted check uses, so a new family could not carry the cap Decision 8 asks for. A cap is now pending, not stale, while its check file has no accepted check. `test_v1_4_prepare` is capped at 98,359,580, twice the largest fuel of its first local run (`test_a_prelude_does_not_pin_files`, 49,179,790); the first acceptance may set it again.
- **`tests/harness/wat.py`** gains a refusing `prepare` in the synthetic sets' session exports, and `test_the_session_exports_have_their_types` names `prepare` among a set from before sessions' missing exports, since `EXPORT_TYPES` now holds it.
- **`tests/release_shards.toml`**: the new file joins `own-guest`, as every product check file is in a files shard; claimed under `[claim.judge]`.
- **`_MAIN_NAMES` keeps the double-underscore names too.** Decision 3 says the names the code bound that do not begin with two underscores; `prepare` copies the whole of `__main__`'s dictionary, so `_end` drops exactly what a call bound or rebound (a script's `__loader__`, `-m`'s `__spec__`) and keeps the module's own `__name__` and `__builtins__`, which the Decision's rule would have left out of `_MAIN_NAMES` and so dropped at the end of every call (recorded by the pull request's reviewer).
- **The import-path row** prints one value more than the specification's: `'/a' in sys.path_importer_cache`, `False False amod`, so the importer cache's half of Decision 3 is held too.
- **The news file's entry is under `### Added`**: 152 has not landed, and this tree's rule refuses its headings. The orchestrating session decided on 2026-10-28 that when 152 lands the entry moves to `### For contributors`: the export serves embedders in other languages and 150, and the reader-facing value is 150's entry.
