# 157: The reactor prepares a starting image

- **Status:** drafted 2026-10-27 with specification 150, which stands on it; not yet built. It changes the guest's exports, the artifact set's bytes and the build recipe, so it is reviewed before it is built (constitution §5.6), as `../reviews/157-the-reactor-prepares-a-starting-image-spec-YYYY-MM-DD.md`. Decision 5 is the one choice the owner has not yet been asked; it is written so the owner may reverse it before the build, and says what changes if so.
- **Date:** 2026-10-27
- **Owner:** Clay Gendron
- **Kind:** **build-class** (constitution §5.6 and §5.7), **not structural**: it changes no file under `src/`. Recipe: `recipes/reactor_main.c` (the export `prepare`, the flag `prepared` and the reference `end_function`, `pinned` split into two bits, and a prepared instance's ending in `run` and `shutdown`), `recipes/reactor_bootstrap.py` (`prepare`, `_end`, and three more reseeds in `_refresh`), a new recipe file `recipes/snapshot-packages.txt`, and `scripts/assemble_artifacts.py` (it reads that file, writes MANIFEST's `x-snapshot-packages` line, and stops the build on a package with no line there). The artifact bytes that change: `python.wasm` and `python-snapshot.wasm` (new code, and the snapshot's heap holds the larger `_reactor`), `MANIFEST` (the recipe lines' hashes and the new line) and `SHA256SUMS`. `python-stdlib.zip` does not change (the bootstrap is frozen into the binaries, not the zip), so `x-snapshot-zip` keeps its value. No pin, no patch, no change to `downloads/SHA256SUMS`. The judge: `tests/harness/artifacts.py` (`PLAIN_EXPORTS`, `SNAPSHOT_EXPORTS` and `EXPORT_TYPES` gain `prepare`), `tests/checks/test_v1_1_artifact_set.py` (one row for the new MANIFEST line), `tests/harness/guest.py` (the judge's driver learns to prepare, capture and restore), a new `tests/checks/test_v1_4_prepare.py`, rows in `tests/unit/test_artifact_rules.py` for the list's reader, and a cap for the new family in `tests/lint/budget.toml`. Every guest fuel row and the two binaries' byte rows move; the news file claims them with the reason of Decision 9, and the release-tier ledger gets the upstream suites' block. `tests/public_api.txt` does not change.
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
- **The ending's own cost** (Decision 5's walk of the collector's objects) was not measured. Criterion 5 records it on the everything image.
- **Reproducibility** of an image was inferred, not run twice. Decision 8's row makes one image twice in one process and compares the bytes.

## Decisions

### 1. One export, `prepare`

The reactor gains one export:

```c
__attribute__((export_name("prepare")))
int reactor_prepare(int32_t ptr, int32_t len);
```

It does for a prelude the host passes what `wizer.initialize` does for `PREIMPORT`. The code is `len` bytes of UTF-8 at `ptr`, a buffer from `host_alloc` that `prepare` frees on every path, exactly as `turn` takes its code (`reactor_main.c:474-508`). It returns the prelude's exit status, 0 to 255, or -1 for a refusal, which runs no Python (Decision 4). It is exported by both binaries, as every export is, and survives Wizer, which removes only its init function's export (READ, `scripts/steps/80_snapshot.sh:18`: `--init-func wizer.initialize`).

Reason: the spike's recommendation (§5.2), and the smallest change that closes all three gaps of the problem at once: the preopen reset needs C (`__wasilibc_reset_preopens` is wasi-libc's), the pinned clocks need C, and a function that is not `turn` leaves `turned` unset so `run` still works in the restored instance. A host-side workaround for each would leave the layout limit in place and keep the spike's hand-driven `run` (§1.2).

### 2. The prelude runs with pinned clocks and entropy, and real file metadata

`pinned` (`reactor_main.c:60-132`) becomes two bits. `PIN_CLOCKS` covers `clock_time_get` and `random_get`; `PIN_FILES` covers `path_filestat_get` and `fd_filestat_get`. It starts at both bits, so the build-time snapshot is made exactly as today; `wizer.initialize`, `run`, `turn` and `shutdown` set it to 0 as today. `prepare` sets it to `PIN_CLOCKS` before any Python runs and to 0 before it returns, on every path.

So while a prelude runs, `time.time()` reads the build's constant, 2026-01-01T00:00:00Z (`PINNED_REALTIME_NS`, `reactor_main.c:69`), `time.monotonic()` reads 0 throughout, and entropy is zeros. File metadata is the host's own.

Reasons:

- **No time in the image lies in the future.** Every monotonic value the prelude stored is 0, which no restored call's clock is below. This closes the problem's second gap without a host-side offset on the clock, which would put a shadow on `clock_time_get` into every call.
- **The image is the same bytes when it is made again** from the same prelude, the same grants' files and the same environment in one process (Decision 8 checks it). A prelude made under real entropy is never reproducible (the spike, §1.7, INFERRED).
- **File metadata stays real** because pinning it breaks ordinary code. Under `PIN_FILES` every file has inode 0 on device 0, so `os.path.samefile` says any two files are one, and `shutil.copyfile` raises `SameFileError` for every copy (INFERRED from `pin_filestat`, `reactor_main.c:99-111`, and CPython's `shutil._samefile`, which compares `st_dev` and `st_ino`). Real metadata costs only reproducibility across machines, which no one needs from an image: an image binds to one artifact set and is made where it is used.

The costs, which 150's documentation states: a prelude that waits for time to pass (`asyncio.sleep`, a loop on `time.monotonic()`) never sees it pass and runs to its deadline; `time.sleep` returns, though not always after the time it was asked for (INFERRED: the host's `poll_oneoff` waits against its real clock while the prelude reckons against the pinned one); and a value the prelude draws from entropy is the same in every image (`uuid.uuid4()`, `secrets.token_hex()`, a generator seeded without an argument), so a prelude must not make a secret. The module-level generators are reseeded per call (Decision 6).

### 3. What `prepare` does

In order, after its refusals (Decision 4):

1. `pinned = PIN_CLOCKS`. The code is copied into a `bytes` object and the buffer freed, before any Python runs, as `turn` does.
2. It takes a strong reference to `_reactor._end` into a new static, `end_function`, as `wizer.initialize` takes `unfreeze_function` (`reactor_main.c:298-304`), so code the prelude or a later program runs cannot replace what the C side calls at the end of a call (spec 055's reason for its own references, `reactor_main.c:143-148`).
3. It reads argv and the environment from WASI, as `turn`'s first call does (`reactor_main.c:513-524`), and calls `_reactor.prepare(source, (argv, env))`. That function, new in `reactor_bootstrap.py`:
   - sets `os.environ` from `env`, and puts each argv entry after the first that begins with `/` on `sys.path`, as `_setup` does (`reactor_bootstrap.py:237-244`), so the making call's `import_path` works in the prelude;
   - sets `sys.argv` to `[""]`;
   - compiles the source as `<snapshot>`, registers it with `linecache` as `_run_turn` does, so a traceback shows its lines, and runs it in `sys.modules["__main__"]`;
   - returns 0, or the status of a `SystemExit` by `_exit_code`, or 1 after `_report` printed any other exception;
   - on 0, copies every name the prelude bound in `__main__` that does not begin with two underscores into `_MAIN_NAMES` (`reactor_bootstrap.py:24-27`), so every later call's fresh `__main__` starts with them (`_fresh_main`, `reactor_bootstrap.py:30-36`), and a session's turns, which run in this same `__main__`, have them already;
   - flushes `sys.stdout` and `sys.stderr` on every path, so no byte the prelude printed stays in a buffer of the image and reappears in every call.
4. On status 0, the C side then does what `wizer.initialize` does after `PREIMPORT` (`reactor_main.c:305-310`): `gc.collect()` and `gc.freeze()` through `run_private`; `pinned = 0`; `__wasilibc_reset_preopens()`; `clear_unused_stack()`; and sets `prepared = 1`. On any other status it sets `pinned = 0` and returns; the host never images such an instance.
5. `fflush(stdout)`, `fflush(stderr)`, and the status is returned.

`prepare` never sets `turned` or `run_called`. So a restored instance is, to the C side, a snapshot instance whose interpreter has more in it: `run` reads argv and the environment from WASI, refreshes (Decision 6), makes a fresh `__main__` and runs the program; `turn`'s first call runs the session's setup; and wasi-libc rebuilds the preopen table from the call's own grants, by name and in any order, on first use (spec 006, Decision 5). The layout limit of the spike's §2.2 is gone.

### 4. When `prepare` refuses

It frees the buffer and returns -1, running no Python, when any of these holds: `initialized` is 0 (the plain reactor before a call: an image is made only from the snapshot, whose interpreter `wizer.initialize` started with the fixed hash key every snapshot instance shares); `prepared`, `run_called`, `turned` or `shut` is set (once per instance, and before anything else); or `len < 0`. A NULL pointer with a length above 0 is the host's out-of-memory, as for `turn`: the prelude raises `MemoryError` and returns 1.

Reason: an image is a snapshot instance's memory, restored into a snapshot instance; a prelude run after a program or a turn would freeze that program's state too, which is a checkpoint of a guest's run, outside this release (the owner, `../decisions.md:498`). Since a running program or turn has set `run_called` or `turned`, nothing a guest does can reach `prepare` and have it run.

### 5. How a call from a prepared instance ends (the owner's to confirm)

This is the one choice in 157 and 150 the owner has not yet been asked. The orchestrator puts it to the owner before the build; the recommendation is written in, and what changes under the other choice is stated.

**The choice.** In an instance where `prepared` is 1, `run` and `shutdown` end the call one of two ways.

| | A. Run `atexit` and flush (recommended) | B. Python's full teardown, as `run` does today |
|---|---|---|
| what runs | `_reactor.run`'s own flush of `sys.stdout` and `sys.stderr`; then every `atexit` handler; then a flush of every writable file object the call left open; then the C streams | the same handlers, then `gc.unfreeze()` and `Py_FinalizeEx()`: every module the image holds is torn down |
| instructions at the end of a call, on the image of every package | the program and its `atexit` handlers: 4.6 million in all for a program of 3.9 million (the spike, §1.6, EXECUTED), plus the flush's walk (unmeasured; criterion 5 records it) | 1,546 million, on every call, whatever the program did (§1.6, EXECUTED); 0.65 to 0.73 s on an M1 Pro, about 1.3 s on Cloudflare `standard-1` at the need's 1.2 billion a second (INFERRED) |
| on smaller images (§1.4, EXECUTED) | the same few million | numpy 96 M, pandas 316 M, scikit-learn 689 M, statsmodels 729 M |
| what a program loses | object finalizers at the end: a `__del__` method, a `weakref.finalize` registered without `atexit`, and so a `zipfile.ZipFile`, `gzip.GzipFile`, `tarfile.TarFile` or `pandas.ExcelWriter` left open is never finished (its bytes so far are flushed; its closing directory or trailer is not written), and a `NamedTemporaryFile` left open stays on disk in a writable grant | nothing: CPython's own semantics |

**The recommendation, A.** The image exists to make a call cost its own work. Under B a call from the image of every package pays 1,546 million instructions to tear down modules it never used, 400 times its program, and the instance is discarded right after; that would undo most of what the image saves for the short programs it is for. A keeps what spec 073 promised `run`: a file a program wrote and left open keeps its bytes (spec 073, `tests/checks/test_v1_4_embedding.py:117` and `:167`), because the flush covers every writable file object. What it gives up is a finalizer's work at exit, which the documentation says in one sentence ("object finalizers do not run when a call from a snapshot ends; close what you open, or use `with`"). A call without an image, `run` and a `Session` alike, keeps its full teardown: nothing changes for them.

**The mechanism of A.** `_reactor._end()`, new in `reactor_bootstrap.py`:

1. `atexit._run_exitfuncs()`, which runs every handler, the image's and the call's, and reports a handler's exception itself, as CPython does at exit.
2. A walk of `gc.get_objects()` for instances of `io.TextIOWrapper`, `io.BufferedWriter` and `io.BufferedRandom` that are not closed: each text wrapper is flushed first (which flushes its buffer), then each buffered writer. An exception from one flush is printed to `sys.stderr` as CPython prints an exception ignored in a finalizer, and the walk goes on. The walk sees the call's own objects only: `gc.freeze()` in `prepare` moved every object of the image to the permanent generation, which `gc.get_objects()` does not visit (READ, `Python/gc.c:1715-1721` and `:1735-1743`); and a prelude that left a file open is refused when the image is made (150, Decision 7), so the image holds none.
3. `sys.stdout.flush()` and `sys.stderr.flush()`; it returns `False` when either raises, else `True`.

In C, `run` and `shutdown` in a prepared instance call `end_function` in place of the unfreeze and `Py_FinalizeEx()`, and return 120 when it returned `False` (or raised), as they return 120 when `Py_FinalizeEx()` reports an error (`reactor_main.c:426-428`, `:570`); then `fflush(stdout)`, `fflush(stderr)`. `shutdown` still sets `shut` and refuses a second call. The other options for the flush were weighed and refused: CPython keeps no list of open files (a file is flushed by its own deallocation), and wrapping `open` to track files at their opening misses `io.FileIO`, `os.fdopen` and C-level opens, and changes the `open` a program sees.

**If the owner chooses B.** `run` and `shutdown` take today's path in every instance; `_end` and its walk are not built; Decision 8's ending rows assert today's teardown instead; criterion 5 records the teardown's fuel; 150's documentation drops the finalizer sentence and states the teardown's cost on the limits page.

### 6. Three more reseeds in `_refresh`

`_refresh` (`reactor_bootstrap.py:63-95`), which runs at the start of every `run` and in a session's first turn, gains, each only when its module is in `sys.modules`:

- `tempfile._name_sequence = None`, so `tempfile` makes a fresh name sequence seeded from the call's entropy on its next use, as a fresh interpreter does;
- `sympy.core.random.seed()`, sympy's own public call that reseeds both its module-level generators, `rng` and `_assumptions_rng` (the spike, §3.2, EXECUTED: both repeated across restored calls);
- for each other generator a package makes at import and seeds from entropy, its package's own public reseeding call, or `.seed()` on the instance where the package has none. The spike counted five Mersenne Twister seedings in the everything prelude and named three (`random`'s and sympy's two); the other two "are held where the scan of module namespaces does not look" (§3.1, line 150). The builder finds them by a walk of `gc.get_objects()` for `random.Random` instances after the everything prelude, with `gc.get_referrers` naming each one's owner, adds a reseed for each that a fresh import seeds from entropy, and lists each in the landing notes with its owner; a generator its package seeds from a constant is left as it is, since a fresh import seeds it the same way.

On a call from the artifact set's own snapshot none of these modules is imported when `_refresh` runs (`PREIMPORT` holds none of them, `reactor_main.c:57`), so each is one failed dictionary lookup. Reason: the reactor already owns the per-call refresh of what a snapshot froze, and putting the rest there keeps one list and one place; a host-side reseed would need a turn of its own before every call.

### 7. The package list: a recipe file and a MANIFEST line

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
- `scripts/assemble_artifacts.py` gains one reader, `snapshot_packages(text, packages) -> str`, beside `preimport_list` (`scripts/assemble_artifacts.py:444-450`): it parses the file, stops the build naming the distribution when a `PACKAGES` key has no line, when a line names a distribution `PACKAGES` lacks, or when a name is not a dotted Python identifier, and returns the names in file order, a repeat dropped. MANIFEST gains `x-snapshot-packages <name>, <name>, …` after `x-preimport` (`:885`).

Reasons: the list is a fact of the set, so the set carries it; a runner given another set (`artifacts=`) then imports that set's list, never its own idea of it. The build's refusal makes the rule self-enforcing: a specification that adds a package cannot build its set until it says what to import, or that nothing is. The recipe file, not a constant in the script, because 069 moved `PREIMPORT`'s list out of the script for the same reason (spec 069, Decision 3) and the recipe lines hash it into MANIFEST.

### 8. The rows first

Each is written before the code and seen failing on `dev`'s set (criterion 1). The guest rows drive the export through the judge's own driver, `tests/harness/guest.py`, which stays apart from the runner it judges (`guest.py:1-13`): `Turns` gains `prepare(code)` (the export, through `host_alloc`), `image()` (the memory read whole) and a `run(..., image=…)` path that grows a fresh instance's memory and copies an image in before its `run`. The driver answers entropy and the clocks itself, seeded alike in every run (`guest.py:9-12`), so a row here can show that a generator was reseeded, not that two calls differ; 150's rows show that, through the runner and real entropy.

- `tests/harness/artifacts.py`: `PLAIN_EXPORTS` and `SNAPSHOT_EXPORTS` gain `prepare`; `EXPORT_TYPES` gains `"prepare": "(i32, i32) -> (i32)"`. `test_plain_reactor_exports` and `test_snapshot_exports` (`tests/checks/test_v1_1_artifact_set.py:85-96`) fail on `dev`'s set.
- `tests/checks/test_v1_1_artifact_set.py::test_manifest_names_the_snapshot_packages`: MANIFEST has one `x-snapshot-packages` line, after `x-preimport`; each entry is a dotted identifier, and none repeats. That every entry imports is the slow row's to show (`test_the_everything_prelude_prepares`, below), since a compiled package such as kiwisolver is a builtin module with no file in the zip.
- `tests/checks/test_v1_4_prepare.py`, on the snapshot, each row recording its fuel:
  - `test_prepare_refuses`: -1 on the plain reactor, after `run`, after `turn`, and a second time; no output in each case.
  - `test_a_prepared_image_runs_a_program`: a prelude defines `def f(): return 42` and `x = [1, 2]`; the image restored into a fresh instance, `run` of `-c print(f(), x)` prints `42 [1, 2]`.
  - `test_the_preopens_are_the_calls`: the image made with read-only folders granted at `/a` then `/b`; a restored instance granted `/b` then `/a`, and `/c` besides, reads each folder's own file at its own path.
  - `test_the_prelude_sees_pinned_clocks`: the prelude records `time.time()`, `time.monotonic()` and `os.urandom(4)`; they are 1767225600.0, 0.0 and four zero bytes; a restored program's `time.monotonic()` is at or above the prelude's.
  - `test_a_prelude_does_not_pin_files`: in a prelude, two different files of a grant have different `(st_dev, st_ino)` and `shutil.copyfile` between them succeeds.
  - `test_the_refresh_reseeds_what_the_image_froze`: a prelude imports `random`, `numpy.random`, `tempfile` and `sympy` and prints each generator's state digest (`hash` of `getstate()`, `next(tempfile._get_candidate_names())`); a restored `run` prints different ones for each.
  - `test_a_prepared_call_keeps_an_unclosed_files_bytes`: a restored program opens a file in a writable grant, writes 100 bytes and ends without closing it; the file holds the 100 bytes (Decision 5, choice A; under B the same row holds through the teardown).
  - `test_a_prepared_call_runs_atexit`: a handler registered in the prelude and one registered by the program both run, in reverse order of registration, before the call ends.
  - `test_a_prepared_session_ends_light`: a restored instance's `turn` then `shutdown` returns 0 and keeps an unclosed file's bytes; its fuel is recorded.
  - `test_a_prepared_image_is_reproducible`: one prelude prepared twice in one process gives byte-equal images.
  - `test_the_everything_prelude_prepares` (marked slow): the prelude imports every name of the `x-snapshot-packages` line; it returns 0; a restored `run` of `-c pass` ends with exit code 0; the prelude's fuel, the image's pages, and the restored call's fuel are recorded (criterion 5).
- `tests/unit/test_artifact_rules.py`: `snapshot_packages` refuses a missing distribution, an unknown one and a name that is not a dotted identifier, each naming it; it keeps file order and drops a repeat.
- `tests/lint/budget.toml`: the family `test_v1_4_prepare` gets its cap, twice the largest fuel its first acceptance records, as the file's header rule says.

### 9. The fuel and bytes that move, and how they are claimed

Every guest row's fuel moves, because both binaries carry new code and the snapshot's heap holds a larger `_reactor`. The sources, INFERRED: the plain reactor unmarshals the larger `_reactor` at each start; every run's `_refresh` makes three more lookups; `run` takes one more branch; and the snapshot's heap layout shifts, which can move a run's fuel either way. The binaries' `bytes` rows (`test_binary_is_a_core_wasm_module[plain]` and `[snapshot]`) grow by the new code.

The news file, `../changes/157-the-reactor-prepares-a-starting-image.md`, claims them: `grows` names `tests/checks/test_v1_*` (a prefix, which stands for every product check whose fuel or bytes grow) and `tests/upstream` rows by the same prefix rule; `growth` gives this reason ("the reactor gains the export `prepare`, a prepared instance's ending and three reseeds in `_refresh`, so both binaries are larger and every run unmarshals and refreshes a little more"). Since the upstream suites' rows are release-tier rows, the same block is appended to `../release-tier-claims.toml`, as 127 did. The landing notes give the bare `-c pass` fuel on both binaries before (`dev`'s accepted rows) and after (the pull request's), and any row whose fuel moves by more than 1% more than the bare row's move is named with its cause. A fall needs no claim.

### 10. The documentation of the export

- `docs/explanation/how-it-works.md`, "The reactor and its exports": `prepare` joins the list, in one sentence: it runs code the host passes in a snapshot instance that has run nothing, then leaves the instance ready to be imaged, with its preopen table cleared and its heap frozen.
- `docs/how-to/embed-from-other-languages.md`, "Load the artifacts in your own engine": a short subsection for an embedder in another language: call `prepare` with code from `host_alloc`, read linear memory whole, and start each later instance by growing its memory to the image's size and copying the image in before calling `run` or `turn`; the image binds to the exact snapshot binary and stdlib zip; a call from it ends without Python's teardown (Decision 5).
- 150 writes the Python embedder's page.

## Intent

After this specification, the artifact set lets any embedder make a starting image from its own code with one export call, and start any number of fresh instances from it: each instance gets its grants from its own call in any order, never sees a time in its future, gets fresh randomness, and ends a call at the cost of its own work. The set says which names import every package it ships.

## Design

```
recipes/reactor_main.c          PIN_CLOCKS, PIN_FILES; prepared; end_function; reactor_prepare (export "prepare");
                                run and reactor_shutdown: a prepared instance ends through end_function
recipes/reactor_bootstrap.py    prepare(source, environ); _end(); _refresh's three reseeds
recipes/snapshot-packages.txt   new: one line per distribution
scripts/assemble_artifacts.py   snapshot_packages(text, packages); the x-snapshot-packages line
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
2. **The set builds.** The pull request's run builds the set from the pins; step 80 prints the snapshot's size and hash; MANIFEST holds one `x-snapshot-packages` line and the same `x-snapshot-zip` value as `dev`'s set; `python-stdlib.zip`'s SHA-256 equals `dev`'s. The landing notes give both binaries' sizes and SHA-256 prefixes before and after.
3. **The rows pass** on the pull request's Linux and Windows legs, and on macOS under the label `ci:full`, which the pull request carries: the export rows, the MANIFEST row, every row of `test_v1_4_prepare.py` including the slow one, and the reader's unit rows.
4. **No pass is lost**, and every growth is claimed. The gather's `GROWTH` lists only rows the news file's claim names; the landing notes give the bare `-c pass` before and after on both binaries, as Decision 9 says.
5. **The facts, recorded.** From the slow row, in the landing notes: the everything prelude's fuel through `prepare`, the image's pages, the restored `-c pass` call's fuel, and, for the owner's comparison, the share of that fuel spent in `_end`'s walk of `gc.get_objects()`, measured by a probe that runs the walk alone in a restored instance (EXECUTED by the builder, with the command).
6. **The generators.** The landing notes list every module-level generator the builder's walk found after the everything prelude (Decision 6), with its owner and whether `_refresh` reseeds it and why.
7. **The docs** of Decision 10 are in the pull request, and the documentation site builds.
8. **The rules.** `uv run ruff check`, `uv run ruff format --check`, `uv run pytest tests/lint` and the fast tier are green; `tests/public_api.txt` is unchanged; `ci-status` is green; the pre-build review and the pull request's review are cited in the landing notes.

## Landing notes

Not yet built.
