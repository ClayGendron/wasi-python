# Concurrent runs wait on each other: where, and on what

- **Status:** research, 2026-10-24. The attribution of one finding from `2026-10-23-a-rust-runner-against-wasmtime-py-on-speed.md` (its §3.4): eight hellos on eight threads ran 1.9 times faster than in sequence in the product, 4.2 times in bare wasmtime-py. It changes nothing: no code in `src/`, no pin. Its specification is `../specifications/128-concurrent-runs-do-not-wait-on-each-other.md`, which is small, for the reason in §6. Every number is wall-clock on one shared machine: a benchmark fact, never a check.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Fable 5.1). Box: one evening session, the day after the speed spike.
- **Evidence:** `2026-10-24-concurrent-runs-wait-on-each-other/`: `scripts/driver.py` (the two arms, the speedup curves, the per-thread timeline with lock accounting, the paired fix toggles, the operations count), `scripts/hostonly.py` (the host-side steps alone), `scripts/zip_profile.py` and `scripts/walk_probe.py` (profiles of the two largest steps), `results/*.json` (every run), `results/tables.md` (every table below, generated from them). The scripts ran from `build/concurrency-probe/`, which is git-ignored; they monkeypatch the runner from outside and change nothing under `src/`.
- **Stands on:** `src/wasi_python/_process.py` (the lock order and every lock), `_call.py`, `_engines.py`, `_home.py`, `_zip.py`, `_places.py`, `_private_dirs.py`, `_platform.py`; the specifications 011, 023 (Decision 5: the per-call comparison of matplotlib's data), 078, 113; the design review `2026-10-20-a-design-review-of-the-runner.md`. Read only; nothing copied.
- **Machine:** darwin-arm64, Apple M1 Pro, 10 cores, 32 GiB, macOS 26.5.2; CPython 3.14.2; wasmtime 49.0.0 under wasmtime-py 49.0.0; the 0.1.0 artifact set (`build/artifacts`), the speed spike's warm `.cwasm` caches, main `2cd47507`. **Shared** with two other research agents all evening: the one-minute load average was 7 to 49 during the runs (each result file records it). So every comparison below is a ratio between arms, or between a fix and its own baseline, measured in the same window, and absolute walls are read with that in mind.

Labels: EXECUTED means run here; READ means read from a file, cited; INFERRED means the researcher's reasoning.

## The short version

1. **No lock of the runner's is held across the guest's run, and none is the cause.** Lock accounting over eight concurrent hellos: `cache_lock` is taken 81 times for 0.1 ms of holds and 0.01 ms of waits; `stack_size_lock` 8 times, 0.1 to 0.2 ms per start, never waited for; `held_lock`, `outputs_lock`, `warnings_lock`, `epoch_callback_lock` microseconds. The epoch ticker, the home-thread hand-off and the private folders each measured at nothing when switched off (§5). The spike's candidates are cleared.
2. **One lock shows the waiting, but is not its cause.** `zip_lock` is held for about 2.6 ms per call: under it the runner compares the whole `mpl-data` tree, 213 entries, with its record (spec 023's per-call check), with `os.walk` and pathlib. On eight threads the eight holds queue: 136 to 163 ms of waiting summed over the threads, 40 ms on the longest run's path. Yet moving the comparison **outside** the lock made the batch **slower** by 20 to 35 % in three windows: the eight comparisons then contend for the interpreter's lock at every one of their 226 stats. The lock was, by accident, scheduling them one at a time.
3. **The cause is the interpreter's lock over the runner's own per-call work.** A product call runs about 7.4 ms of host-side Python around a 12 ms guest (in sequence: 19.4 ms per call), and makes about **707 os-level calls** (458 `lstat`, 125 `stat`, 30 `open`, …); the bare arm makes 5. Python's lock serializes that work across threads, and every os call releases and re-takes the lock, which under eight-way contention costs 1.6 to 2.7 times the sequential time (a pure bytecode loop: 1.27). The floor for eight calls is therefore about 8 × 7.4 + 12 ≈ 71 ms against 155 ms in sequence, a ceiling near **2.2 to 2.4** on this machine; measured 1.5 to 1.9. Bare's host-side work is a few hundred microseconds, so its floor is one guest, and it reaches 3.3 to 4.2 under the same load.
4. **Sized by switching each step off** (never a proposal, a measurement): with the data comparison and the grants walk free, the product went from 1.58 to 2.58 against bare's 2.74 in the same window, and from 1.9 to 2.5 against 3.92 in another: those two checks are most of the gap that is the runner's. The rest of the gap is the machine's: bare itself fell from 4.2 to 2.6 as the load rose.
5. **What closes part of it without weakening a promise:** the data comparison by `os.scandir` and plain strings instead of `os.walk` and pathlib. The same comparison, the same one stat per entry, half the interpreter time (2.3 to 2.9 ms → 1.1 ms per call). Measured as a toggle: 1.51 → 2.02 (parallel wall 97.9 → 70.7 ms), 1.77 → 1.96, 1.88 → 1.90. That is the specification. Everything else measured is either nothing (the locks, the ticker, the thread start), a promise (the walk, the private folders, the identity check, judging every call), or the embedder's (the switch interval).

## 1. The question and the method (EXECUTED)

The spike's row (`2026-10-23-…/results/benchmarks.json`, `parallel-8-hello`): eight `print('hello')` guests on the snapshot, the product 140.8 ms in sequence and 73.3 ms on eight threads (1.92), bare wasmtime-py 92.2 and 22.1 ms (4.18). The question: where do the eight product runs wait on each other, how much does each cause account for, and what change closes it without weakening a promise.

Two arms, as the spike's, in `scripts/driver.py`: `product` is `wasi_python.run(["-c", code], fuel=10**12, deadline_s=60, memory_bytes=1 GiB, cache_dir=<the spike's warm cache>)`; `bare` is sixty lines of wasmtime-py (a `Store`, a `WasiConfig` with the stdlib folder preopened, a `Linker` with WASI and one host function, `instantiate`, `run`), the same `Config` (fuel on, epochs on). Both arms warm their module into the process before any timed batch. Four modes:

- `curve`: n hellos in sequence against n on n threads, for n in 1, 2, 4, 8; the arms interleaved so each pair shares a window; three repeats, medians.
- `timeline`: eight on eight, every runner phase stamped on its thread with `perf_counter` and `thread_time` (wall and CPU), by wrapping the runner's functions from outside (`_found_and_checked`, `_walk_grants`, `_zip_folder`, `_preopens`, `_guest_home`, `_Private`, `_start_guest`, `Linker.instantiate`, `Func.__call__`, `Store.close`, the home's `finish` steps and `body`); and every lock on the process object replaced by an accounting stand-in (count, wait, hold, longest hold), through `process()`'s attributes, which production reads at every use.
- `fix`: a fix toggled on and off against its own baseline, alternating, three repeats, with bare in the same window for scale.
- `ops`: every function of the `os` module wrapped and counted per call.

`scripts/hostonly.py` runs the host-side steps alone, no guest, eight in sequence against eight on eight threads, at two switch intervals. `scripts/zip_profile.py` and `scripts/walk_probe.py` profile the two largest steps.

## 2. The speedup curves (EXECUTED)

`results/curve.json` (load 7) and `curve-2.json` (load 17). Walls in ms, medians of three; "per call" is the median wall one call took inside the parallel batch.

| threads | product: in sequence / parallel | speedup | per call in parallel | bare: in sequence / parallel | speedup | per call in parallel |
|---|---|---|---|---|---|---|
| 1 | 20.3 / 20.1 | 1.01 | 20.1 | 12.3 / 13.4 | 0.92 | 12.9 |
| 2 | 38.3 / 26.4 | 1.45 | 26.1 | 24.5 / 13.6 | 1.80 | 12.5 |
| 4 | 75.4 / 47.7 | 1.58 | 42.0 | 51.8 / 15.4 | 3.36 | 13.9 |
| 8 | 159.1 / 104.8 | 1.52 | 78.5 | 108.9 / 31.1 | 3.51 | 24.5 |
| 8 (second window) | 156.9 / 83.4 | 1.88 | 68.5 | 99.2 / 29.9 | 3.32 | 23.7 |

Three things to read off it. The product loses at **two** threads already (1.45 against 1.80), before any machine limit can matter: what it waits on is its own. Bare's call keeps its 12 to 14 ms up to four threads and dilates to 24 ms at eight (the kernel and the other agents' load; the spike's untuned Rust reached 3.0 at eight for the same reason, INFERRED). The product's call dilates from 20 ms alone to 26, 42 and 78 ms: at eight, each call spends three quarters of its time waiting.

## 3. Where the time goes (EXECUTED, `results/timeline-2.json`)

### 3.1 The phases

Eight hellos, in sequence (batch 143 to 163 ms) and on eight threads (76 to 102 ms, speedup 1.86 in this window). Wall and thread CPU summed over the eight calls; the last column is one call's mean.

| phase (where) | n | in sequence: wall (cpu) ms | on 8 threads: wall (cpu) ms | per call, sequence → parallel |
|---|---|---|---|---|
| `run`, the whole call (home thread) | 8 | 155.3 (52.3) | 511.0 (106.1) | 19.4 → 63.9 |
| `guest_body`: the guest thread, instantiate to exit | 8 | 96.2 (95.5) | 112.1 (105.4) | 12.0 → 14.0 |
| `_preopens`: the zip folder, the root, the grants | 8 | 29.1 (23.8) | 185.4 (35.3) | 3.6 → 23.2 |
| of which `_zip_folder` (holds `zip_lock`) | 8 | 27.4 (22.1) | 173.7 (30.5) | 3.4 → 21.7 |
| `_walk_grants`: the runtime folders judged | 8 | 9.7 (9.5) | 156.5 (43.2) | 1.2 → 19.6 |
| `_found_and_checked`: the set's sums | 8 | 2.6 (2.6) | 26.3 (6.7) | 0.3 → 3.3 |
| `_guest_home` | 8 | 2.6 (2.5) | 6.9 (3.9) | 0.3 → 0.9 |
| `_Private.__init__` (two per call) | 16 | 3.0 (3.0) | 5.3 (3.9) | 0.19 → 0.33 |
| `_Private.remove` (two per call) | 16 | 4.7 (4.6) | 11.7 (7.1) | 0.29 → 0.73 |
| the three `finish` release steps | 24 | 8.1 (7.4) | 14.6 (9.8) | 0.34 → 0.61 |
| the identity check (guest thread) | 8 | 4.1 (3.9) | 8.7 (6.3) | 0.5 → 1.1 |
| `_start_guest` (holds `stack_size_lock`) | 8 | 0.9 (0.6) | 1.6 (0.7) | 0.12 → 0.20 |
| `Linker.instantiate` (two per call: the check module and the guest) | 16 | 0.9 (0.9) | 1.4 (1.0) | 0.05 → 0.09 |
| `Store.close` | 24 | 3.2 (2.5) | 2.6 (2.4) | 0.13 → 0.11 |
| `_engine`, `_module`, `_check_module`, `_sweep_once` | 8 each | 0.0 | 0.0 | a dictionary read each |

In sequence a call is 19.4 ms: 12.0 ms of guest and **7.4 ms of host-side Python** on the home thread (the `run` row's CPU, 52.3 / 8 = 6.5 ms, plus the guest thread's host-side 0.9). Of the 7.4, the zip folder's check is 3.4 (of which the `mpl-data` comparison 2.3 to 2.9, §4), the grants walk 1.2, the private folders and releases about 1.6, the set's sums and the HOME 0.6, the thread start 0.1, and about 0.5 unstamped (the `Store`, the `WasiConfig`, the linker lookups, the files table, the result).

On eight threads the guest grows 12.0 → 14.0 ms (the kernel's share and the load: bare's call grows the same way, §2), and **the host-side phases grow five to sixteen times**: the walk 1.2 → 19.6, the zip folder 3.4 → 21.7, the sums 0.3 → 3.3. The home thread's CPU doubles, 52 → 106 ms for the same work.

### 3.2 The locks

Every lock on the process object, over the same eight calls.

| lock | acquisitions per 8 calls | in sequence: held ms | on 8 threads: held ms | on 8 threads: waited ms, summed | longest hold ms |
|---|---|---|---|---|---|
| `zip_lock` | 16 | 27.6 | 47.4 | **135.6** | 7.3 |
| `cache_lock` | 81 | 0.15 | 0.11 | 0.01 | 0.007 |
| `stack_size_lock` | 8 | 0.83 | 1.5 | 0.0 | 0.47 |
| `outputs_lock` | 40 | 0.09 | 0.10 | 0.02 | 0.014 |
| `held_lock` | 32 | 0.04 | 0.06 | 0.01 | 0.006 |
| `warnings_lock` | 8 | 0.01 | 0.03 | 0.0 | 0.021 |
| `epoch_callback_lock` | 8 | 0.01 | 0.01 | 0.0 | 0.001 |
| `live_lock`, `pool_lock`, `tool_threads_lock` | 0 | | | | |

(The first timeline, `results/timeline.json`, load 13: `zip_lock` waited 163 ms, held 60; the rest the same.) Every lock but one is a leaf held for microseconds, as `_process.py`'s docstring says. The compiling guards are never reached with a warm module. **No lock is held while the guest runs:** every hold is inside `_preopens` or the start window, and the guest body's phase begins after both. The ticker's `cache_lock` takes are the 0.007 ms ones.

`zip_lock` is held for about 3.4 ms per call in sequence (two takes per call: `_zip_known` from the walk, microseconds, and `_zip_folder`). What it holds (READ, `_zip.py:39-68`): the entry's lookup, four stats of the folder and the zip, and `_data_intact`, which compares the whole `mpl-data` tree with the record: `os.walk`, one `os.lstat` per entry, a `Path` built per entry, 213 entries (204 files, 9 folders) in this set's zip.

### 3.3 The longest run's path

Of the parallel batch's eight runs, the longest (81.6 ms; the batch 83.3): sums 1 → 5 ms, **walk 5 → 26**, **zip folder 26 → 66**, HOME 67, guest 68 → 82, releases 82 → 83. Forty ms in the zip folder's queue, twenty in a walk that takes 1.2 ms alone. Every run in the batch has the same shape (`results/tables.md` lists all eight for both timelines).

### 3.4 What the lock table does not say (EXECUTED, `results/fix-zip_outside*.json`, `fix2-zip_outside.json`)

The obvious fix: run the comparison outside `zip_lock` (it reads the filesystem only; the lock guards the dictionary entry; the locked path, which checks again, taken only to make or repair). Prototyped as a toggle, three windows:

| window (load) | baseline: in sequence / on 8 threads, speedup | the comparison outside the lock | bare then |
|---|---|---|---|
| 11 | 86.4 ms, 1.75 | **111.5 ms, 1.33** | 3.14 |
| 41 | 130.4 ms, 1.73 | **161.4 ms, 1.61** | 3.28 |
| 17 | 82.1 ms, 1.81 | **103.7 ms, 1.42** | 4.23 |
| 11, with the scandir comparison as well | 95.3 ms, 1.74 | **127.1 ms, 1.17** | 3.56 |

Slower every time, by 20 to 35 %. Removing the queue made the eight comparisons run at once, and at once they contend for the interpreter's lock at every stat (§4). The queue on `zip_lock` is where the waiting *shows*; it is not what the waiting *is*.

## 4. The cause: the interpreter's lock over the runner's per-call work (EXECUTED and INFERRED)

### 4.1 Operations per call (EXECUTED, `results/ops.json`)

Every function of `os` counted, warm, in sequence: the product makes **707 os-level calls per hello**: 458 `lstat`, 125 `stat`, 30 `open`, 30 `fstat`, 30 `close`, 13 `scandir`, 5 `readlink`, 3 `mkdir`, 3 `unlink`, 2 `rmdir`, and a few more. Bare makes **5** (three `stat`, two `mkdir` of the driver's own). Where they come from (`scripts/zip_profile.py`, `walk_probe.py`): the `mpl-data` comparison, 226 `lstat` (one per entry and per `os.walk` step); the grants walk, 169 `lstat` and 117 `stat` (`os.path.realpath` on 21 paths, `identity_of` on 111 paths of which 36 distinct: the seven runtime folders' ancestor chains, judged every call as spec 113 asks); the five preopens' handle walks, about 90 (`open`, `fstat`, `close` per component); the two private folders, their lock files and removals, about 30; the set's three sums, a few.

### 4.2 The host-side steps alone, on eight threads (EXECUTED, `results/hostonly.json`, load 21)

No guest: the step itself, eight in sequence against eight on eight threads. If the parallel wall equalled the sequential, Python's lock would simply serialize the steps; it is longer.

| step | per call ms | 8 in sequence | 8 on 8 threads | parallel / sequence |
|---|---|---|---|---|
| `_data_intact` (os.walk and pathlib) | 2.9 | 23.2 | 41.8 | 1.80 |
| `_data_intact` by scandir (the prototype) | 1.1 | 8.7 | 14.5 | 1.67 |
| `_zip_folder` (the lock and the check) | 2.6 | 20.5 | 33.2 | 1.62 |
| `_walk_grants` | 1.3 | 10.6 | 25.3 | 2.39 |
| `_found_and_checked` | 0.2 | 1.8 | 4.9 | 2.72 |
| `_Private` make and remove | 0.6 | 5.0 | 3.2 | 0.64 |
| a pure bytecode loop of the same length | 1.3 | 10.4 | 13.3 | 1.27 |

Pure bytecode on eight threads costs 1.27 times its sequential time: the lock's serialization and a little switching. The runner's steps cost **1.6 to 2.7 times**: each of their hundreds of os calls releases the interpreter's lock for the system call and takes it back after, and under eight-way contention each take-back is a hand-off through the kernel (the home thread's CPU doubling in §3.1 is system time in those hand-offs, INFERRED; `thread_time` counts user and system). The one step that gains on eight threads is the private folder, whose work is a few system calls and little Python. With the switch interval at 100 µs instead of 5 ms, the same table reads 1.5 to 3.1: no better. The lock behind `_zip_folder` makes it the *least* bad of the three large steps (1.62 against 1.80 for its own body unlocked), which is §3.4 in miniature.

### 4.3 The floor (INFERRED from §3.1)

Eight calls on eight threads cannot finish before their host-side Python has run, one thread at a time: 8 × 7.4 ms = 59 ms, plus the last guest's 12 ms: about **71 ms**, against 155 in sequence. The ceiling for eight hellos with today's runner on this machine is therefore about **2.2**; with the contention tax of §4.2 on top, 1.5 to 1.9 is what one sees. Bare's host-side Python is a few hundred microseconds; its floor is one guest, and its ceiling is the machine's.

The product's two-thread row says the same thing without a model: 1.45 against 1.80, with the machine idle at two threads.

## 5. Each candidate, sized (EXECUTED, `results/fix-*.json`, `fix2-*.json`)

Each is a toggle against its own baseline in the same window, three repeats, medians; "sizing only" means the toggle removes a check and is never a proposal.

| what was switched off or changed | baseline speedup | with the toggle | bare then (load) | reading |
|---|---|---|---|---|
| the stack-size lock (the thread started with the size set once) | 1.88 | 1.81 | 3.81 (11) | nothing: held 0.1 to 0.2 ms per start, never waited for |
| the epoch ticker | 1.74 | 1.81 | 3.45 (11) | nothing |
| both of those | 1.89 | 1.81 | 4.14 (16) | nothing |
| the private folders' lock files (sizing only) | 1.83 | 1.65 | 3.94 (11) | nothing |
| the identity check (sizing only) | 1.83 | 1.66 | 3.85 (11) | nothing |
| the switch interval at 100 µs | 1.58 | 1.75 | 2.74 (44) | noise; the embedder's setting in any case |
| the switch interval at 50 ms | 1.97 | 1.94 | 4.37 (44) | noise |
| the `mpl-data` comparison skipped (sizing only) | 1.91 | 1.83 | 4.13 (11) | the sequence falls 160 → 132 ms; the parallel 84 → 72 |
| the grants walk skipped (sizing only) | 1.90 | 2.30 | 3.93 (10) | the parallel 83 → 62 |
| both skipped (sizing only) | 1.58 | **2.58** | 2.74 (30) | most of the gap that is the runner's |
| both skipped, second window | 1.90 | **2.50** | 3.92 (17) | the same |
| every toggle at once (sizing only) | 1.47 | 2.44 | 2.64 (31) | no further gain past the two checks |
| **the comparison by `os.scandir`** (the proposal) | 1.51 | **2.02** | 3.21 (17) | the parallel 97.9 → 70.7 ms; the sequence 148 → 142 |
| the same, first window | 1.77 | 1.96 | 3.84 (11) | |
| the same, a window at load 37 | 1.88 | 1.90 | 2.86 (37) | the sequence 273 → 186 |
| the comparison outside the lock | 1.75 / 1.73 / 1.81 | 1.33 / 1.61 / 1.42 | | slower, §3.4 |

The home-thread hand-off (spec 078) does not appear: a hello makes no door call and no provider call, so the home thread serves nothing (`serve` runs for the guest's whole 12 ms at 0.1 ms of CPU; §3.1). For a guest that calls the host often, the hand-off is the spike's §3.2 and §3.3, not this memo's question.

## 6. What would close the gap, and what would not

- **The comparison by `os.scandir` and plain strings** (the specification). The same comparison as spec 023 Decision 5 asks for, every call, before granting: every name, each a real folder or regular file as recorded, no link, each file's stamp equal. One `DirEntry.stat(follow_symlinks=False)` per entry is the same one `lstat` the kernel sees today; what goes is the `Path` built and stringified per entry, three quarters of the step's interpreter time (`scripts/zip_profile.py`). 2.3 to 2.9 ms → 1.1 ms per call. The prototype answers as the original on four trees: the live tree (true), a copy with new stamps (false), the copy against its own record (true), a link in place of a file (false). It still runs under `zip_lock`: §3.4 says the lock helps, and the spec leaves it.
- **Not the walk's repeated stats.** A per-call memo of ancestor identities cut 117 `stat` to 42 and saved 0.08 ms per call (`results/walk.json`: 1.18 → 1.10 ms); the walk's cost is its 21 `realpath` calls and their 169 `lstat`, each a component of a real path. A change to the grant judge for 0.08 ms is not worth its review.
- **Not fewer checks per call.** Caching the data comparison or the walk's verdicts across calls would make the parallel runs fast and break spec 023's "per call" and spec 113's "in every call". Not proposed.
- **Not a lock split, a pool of pre-sized threads, or the ticker.** Each measured at nothing (§5). The pool would add a lifecycle (spec 078 Decision 2 says why a thread per entry) for 0.1 ms per call.
- **Not the switch interval.** The embedder owns `sys.setswitchinterval`, and it made no difference.
- **What would close the rest:** the runner's per-call checks run as Python, under the interpreter's lock, and every os call is a hand-off. Closing the remaining gap means running those checks off the interpreter (a native helper, or the free-threaded build, which this project does not target), or fewer of them, which is a promise. The honest ceiling for short runs on eight threads with today's design is about 2.2 to 2.4 on this machine (§4.3), about 2.8 with the scandir comparison (7.4 − 1.5 = 5.9 ms of host Python: 8 × 5.9 + 12 = 59 ms). The product is not slower than bare per guest; it is slower per call by the checks it makes, and those do not parallelize.

## 7. `run_async` and `Session` (READ)

`run_async` reaches `_run_checked` through `_run_checked_flushed` (`runner.py:445`), the same path as `run`, on the default pool's `async_workers` threads: the finding applies as it is, and the pool's size is the number of contending threads. A `Session`'s opening calls `_walk_grants` and `_preopens` once (`_sessions.py:977-985`), so the data comparison and the walk are paid per session, not per call inside it; sessions opened concurrently contend as calls do. The spec's change serves all three callers through the one function.

## 8. Where it stopped

- **The machine was never idle.** Two other agents ran all evening; the load average was 7 to 49. Every conclusion rests on same-window ratios, which held across windows (§5: the scandir toggle three times, the lock-split toggle four times); the absolute walls and the spike's own 1.92 and 4.18 are not reproduced to the millisecond. An idle-machine run is one `uv run --no-sync python scripts/driver.py curve` away.
- **The unstamped 0.5 ms** of host Python per call (the `Store`, the `WasiConfig`, the linker lookups, the files table) was not attributed further; it is 7 % of the host-side time.
- **The kernel's share** of the guest's dilation (12 → 14 ms at eight) was not separated from the load's; bare shows the same dilation, so it is not the runner's.
- **Linux and Windows** were not measured. The mechanism (the interpreter's lock, os calls as hand-offs) is CPython's on every system; the counts are the same; the costs per hand-off differ.
- **No `py-spy` sample** was taken: the phase timeline and the lock accounting answered the question without it.
- **No check was written.** The specification names them: one that counts the comparison's listings and stats, one that pins that the home thread holds no process lock while its guest runs.

## One line

The eight concurrent runs wait on the interpreter's lock over the runner's own per-call checks (7.4 ms and 707 os calls per hello, every os call a hand-off), not on any lock of the runner's; `zip_lock`'s queue only shows it, and removing the queue made things worse; the one change that keeps every promise is the `mpl-data` comparison by `os.scandir`, which halves its interpreter time and lifts eight hellos from about 1.5 to 1.9 to about 1.9 to 2.0 times the sequence on this machine.
