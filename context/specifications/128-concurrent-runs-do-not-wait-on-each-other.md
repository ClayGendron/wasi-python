# 128: Concurrent runs wait less on each other: the data comparison by scandir

- **Status:** Reviewed before build 2026-10-24 (`../reviews/128-concurrent-runs-do-not-wait-on-each-other-spec-2026-10-24.md`, "not fit to build yet: H1"): H1 fixed in Decision 2 (`os.lstat` per entry, on every system, as the record's stamp) and in Decision 1's first check and Decision 5, the Lows answered in the Disposition. Before: **drafted 2026-10-24**, from the speed spike's parallel row (eight hellos: the product 1.9 times its sequence, bare wasmtime-py 4.2) and the attribution memo written for it. Its checks are named in Decision 1 and not yet written: the builder writes them first, records the first failing on main's code and the second green on main and red under a deliberate fault (AGENTS.md rule 3), then builds. It is runner code, so a **pre-build review is required** (AGENTS.md rule 8); a different agent reviews the build. Its file name is the question it was drafted for; its title is what the research supports, and the memo's §6 says why the specification is this small.
- **Date:** 2026-10-24
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, **not structural**: `src/` (`_zip.py` only, one function body), two unit-check files already in the `own-runner` shard (`tests/unit/test_runner_data.py`, `tests/unit/test_runner_calls.py`), and `CHANGELOG.md`. It touches nothing under `scripts/`, `recipes/`, `downloads/SHA256SUMS` or the release workflow, no artifact byte, no `docs/` page and not the README. Decision 5 says why it is not structural by AGENTS.md's definition. It changes no default an embedder can see (constitution §4.15): no limit, no channel, no path, no lock.
- **Depends on:** landed and unchanged: 023 (matplotlib's data beside the zip; its Decision 5, the per-call comparison of the whole tree, which this specification keeps to the letter), 078 (the guest's own thread; the home thread, whose holds Decision 1's second check pins), 105 (the process object, the one seam the checks use). On nothing in flight. It shares `CHANGELOG.md` with whatever lands beside it, nothing else.
- **Research it stands on:** `../research/2026-10-24-concurrent-runs-wait-on-each-other.md` (the attribution: §3 the phases and the locks, §4 the cause, §5 every candidate sized, §6 what is and is not proposed) and `../research/2026-10-23-a-rust-runner-against-wasmtime-py-on-speed.md` §3.4 (where it was found). Every number below is one of theirs (EXECUTED there, on a shared machine, as same-window ratios) unless marked.

## The problem

Eight `print('hello')` guests on eight threads run **1.5 to 1.9** times faster than the same eight in sequence in the product, against **3.3 to 4.2** in a sixty-line wasmtime-py embedding of the same module on the same machine. The product loses at two threads already (1.45 against 1.80), before any machine limit can matter.

The memo looked for the lock. There is none. Every lock on the process object is a leaf held for microseconds, none is held while a guest runs, and the stack-size window, the epoch ticker, the private folders and the identity check each measured at nothing when switched off. One lock shows the waiting: `zip_lock` is held for about 3 ms per call, because under it the runner compares the whole `mpl-data` tree with its record (spec 023 Decision 5, every call, before granting), 213 entries by `os.walk`, one `os.lstat` per entry and a `Path` built and stringified per entry. On eight threads the eight holds queue, and the longest run spends 40 of its 82 ms in that queue. But the comparison moved **outside** the lock made the batch **slower**, by 20 to 35 % in three windows.

That is because the cause is the interpreter's lock, not the runner's. A product call runs about **7.4 ms of host-side Python** around a 12 ms guest and makes about **707 os-level calls** (458 `lstat`, 125 `stat`, 30 `open`, …; bare makes 5). Python's lock runs that work one thread at a time, and every os call releases and re-takes the lock, which under eight-way contention costs 1.6 to 2.7 times the sequential time. The floor for eight calls is 8 × 7.4 + 12 ≈ 71 ms against 155 in sequence: a ceiling near 2.2 with today's runner. The queue on `zip_lock` was, by accident, scheduling the eight comparisons one at a time, which is the least bad way to run them.

Of the 7.4 ms, the `mpl-data` comparison is 2.3 to 2.9 ms, the largest single step, and three quarters of it is pathlib building a path per entry, not the stats. The grants walk is 1.2 ms (every runtime folder judged each call, spec 113), the private folders and releases 1.6, the rest small. Only the comparison has a cheaper form that makes the **same comparison with the same stats**: `os.scandir` for the listings, one `os.lstat` of each entry's path for its stamp (the record's own source, so the stamp is the same on every system), and plain strings for the keys. Prototyped from outside the runner it takes **1.1 ms** per call (0.9 in the reviewer's probe and in the author's confirmation at load 5, the same whether the stamp comes from `os.lstat` of the entry's path or from the `DirEntry`'s own stat: the saving is pathlib's, not the stat's), answers as the original on four trees (the live tree, a copy with new stamps, the copy against its own record, a link in place of a file), and as a toggle lifted eight hellos from 1.51 to **2.02** (the eight-thread wall 97.9 → 70.7 ms) and from 1.88 to 1.90 (144.9 → 97.7 ms) in the two windows the evidence folder holds, and from 1.81 to 1.88 (86.9 → 74.6 ms) in the reviewer's re-run, with the sequence 2 to 6 ms shorter. A third window the memo quotes (1.77 → 1.96) has no result file, its run having been overwritten by a later one under the same label; it is not counted here.

## Decisions

### 1. The checks first

Written before the code, each in a file the `own-runner` shard already runs on all three systems. No check measures time (AGENTS.md: tests count operations, never wall-clock). Neither patches a private name of `wasi_python`: the first wraps the standard library's `os` functions, the second replaces attributes of `process()` itself, the sanctioned seam.

- `tests/unit/test_runner_data.py::test_the_data_comparison_lists_each_folder_once_and_stats_each_entry_once`: the file's fixture tree (`FILES`: three files in three folders, six entries) is extracted by `_extract_data` as the existing checks do, then compared with its record while `os.scandir`, `os.lstat` and `os.stat` are wrapped by the test to count their calls and the paths they were given. The comparison answers true; `os.scandir` was called once per folder of the tree plus once for its root; `os.lstat` exactly once per entry plus once for the root's link test (seven on the fixture), each with an entry's path or the root; `os.stat` once (the root's folder test). **On main: fails on the lstat count**, ten on the fixture: one per entry, one more per folder for `os.walk`'s own link test, one for the root (`os.walk` reaches `os.scandir` through the module's name, so the listing count is the same on both bodies; the lstat count alone tells them apart). This is the operations count that holds the change: the per-entry work is one `os.lstat` of a plain path string, nothing built by pathlib and no second stat.
- `tests/unit/test_runner_calls.py::test_the_home_thread_holds_no_process_lock_while_its_guest_runs`: every `threading.Lock` and `RLock` attribute of `process()` (the names `_process.py` lists; the check finds them by type through the `RENEW` table's keys) is replaced through `monkeypatch.setattr(process(), name, …)` by a stand-in that records the owning thread's ident while held and forwards `acquire`, `release`, `__enter__`, `__exit__` and `locked`; the stand-in for `outputs_lock` is re-entrant, as the lock it replaces is. The check needs the artifact set and `wasi_python.run`, which this file does not use today (it drives synthetic wat guests through `_call._drive`): the fault it exists for is in `_zip_folder`, above `_drive`, so it must go through `run`, and it begins with the harness gate `needs.need("runner", "artifact dir")`, as `tests/unit/test_runner_module_caches.py`'s `compiled` fixture does, which skips it on a machine without the set and nowhere else. It stays in this file because its subject is the call's threads and locks, which is this file's; the files that already use the set (`test_runner_module_caches.py`, `test_runner_sets.py`, `test_runner_sessions.py`, `test_runner_mounts.py`) are about the cache, the set, sessions and mounts. A `run` with `host=` whose guest calls the door once: the host function, which the runner runs on the home thread (spec 078), records which stand-ins the calling thread owns at that moment. Asserted: the door was called, and the set is empty. **On main: green** (the memo's finding), and the builder records it red once under a deliberate fault in a scratch copy of `_zip.py` whose `_zip_folder` takes `p.zip_lock.acquire()` in place of its `with p.zip_lock:` and releases it only in `_remove_zips`, so the lock stays held through `_preopens` and the guest's run (the fault the check exists for; a `return` inside a `with` block releases the lock, so that is no fault), so the check is shown to bite. Why a check that is green on main is still written: this specification keeps the comparison under `zip_lock` on the memo's evidence, and the lock is released before the guest starts; the check pins that, and that no later change holds any process lock across a guest.
- The five existing checks of `test_runner_data.py` are kept unchanged; `test_every_change_on_the_host_is_seen_and_undone` (an added file, a changed one, a removed folder, a folder swapped for a link, the root swapped for a link: each fails the comparison and is undone) is the one that holds the comparison's meaning, and it must stay green on the new body without any change.

### 2. The comparison by `os.scandir`

`_zip._data_intact` keeps its signature, its docstring's promise and its answers, and walks the tree with `os.scandir` instead of `os.walk` and pathlib:

- the two root tests first, as today (`os.path.islink(data)`, `os.path.isdir(data)`: false on either);
- an iterative walk over a to-do list of relative folder keys (plain strings, `/`-joined, as `Path.as_posix()` gave: the record's keys do not change); for every `DirEntry`, one `os.lstat(entry.path)`, whose mode says what the entry is and whose result is the stamp; a folder is recorded as `None` and queued; a regular file as `_artifacts._stamp(st)`; anything else (a link, a device, a socket) answers false at once;
- **why `os.lstat` of the entry's path and not the `DirEntry`'s own `stat(follow_symlinks=False)`** (the review's H1, READ there against CPython 3.14's `posixmodule.c`): the record is written by `os.lstat` (`_record`), and `_stamp` is `(st_dev, st_ino, st_size, st_mtime_ns, st_ctime_ns)`; on Windows a `DirEntry`'s stat is filled from the directory listing with `st_dev` and `st_ino` zero and `st_ctime` the creation time, three of the five fields, so the record would never match there, and every call would remove and extract the 204 files again. `os.lstat` is the record's own source on every system, the one `lstat` per entry the kernel sees today on POSIX, and it costs the same as the `DirEntry`'s stat on macOS (0.89 against 0.92 ms in the review's probe, 0.94 against 0.95 in the author's): the saving is pathlib's.
- any `OSError` answers false, as today;
- the answer is `seen == record`, as today.

About twenty-five lines; under 80 (AGENTS.md's function ceiling). `_zip.py` stays at about 290 lines. A comment gives the reason in words: the comparison runs on every call and the per-entry work is one `os.lstat` of a plain path, so no path object is built per entry; and the stamp is taken with `os.lstat`, as the record's is, because a `DirEntry`'s own stat does not carry the same fields on every system.

- **Why not a cheaper comparison** (a folder's own stamp instead of each file's): a file replaced in place changes its own stamp and not its folder's; spec 023 Decision 5 asks for each file's stamp, every call. Not proposed.
- **Why not cache the verdict across calls:** the same decision says per call, before granting. Not proposed.

### 3. The comparison stays under `zip_lock`

The lock order (`_process.py`'s docstring, pair 1) and the hold are unchanged: `_zip_folder` still takes `zip_lock`, still compares under it, and releases before the guest's HOME, scratch folder and thread exist. The memo measured the alternative (the comparison outside the lock, the locked path taken only to make or repair) slower every time, 20 to 35 % on the batch, because eight comparisons at once contend for the interpreter's lock at every stat, and the queue on `zip_lock` was running them one at a time. A faster comparison under the lock shortens the queue; Decision 1's second check pins that the queue never reaches the guest.

### 4. What is not done, with the reason

- **No lock split, no new lock.** None is waited on (the memo's §3.2: `cache_lock` 0.01 ms of waits over 81 takes).
- **No pool of pre-sized threads.** The stack-size window is held 0.1 to 0.2 ms per start and never waited for; a pool adds a lifecycle spec 078 Decision 2 rejected.
- **No change to the epoch ticker, the private folders, the identity check, the grants walk** (a per-call memo of ancestor identities saved 0.08 ms; a change to the grant judge is not worth that), **or the switch interval** (the embedder's; no effect measured).
- **No per-process cache of per-call checks:** a promise (023, 113).
- **No measurement in the judge.** The before-and-after speedup is a benchmark fact for the landing notes (acceptance criterion 6); no check compares walls.

### 5. The shape of the change (not structural)

One function body in `_zip.py`; two checks. No module-level mutable or lock, no private wasmtime-py name, no platform branch (`os.scandir` lists and `os.lstat` stamps, the same two standard-library calls on every system; the stamp comes from `os.lstat` everywhere, as the record's does, so no system needs a branch of its own), no test seam that is not on the process object or the standard library. `_zip.py` stays under 300 lines; `_data_intact` under 80. The build shows the rules checks green.

### 6. Fuel does not move

The change is host-side only: nothing the guest sees changes (the same folder is granted, read-only, at the same path). The builder's release run on the branch confirms it across every check and system; **any growth line is red for this specification**, since it claims none.

## Intent

Every call still compares the whole `mpl-data` tree with its record before granting it, with the same one `lstat` per entry from the same source as the record, in half the interpreter's time, so eight concurrent runs spend less of their time waiting for one another's checks and a run in sequence is a millisecond or two shorter. Nothing the guest or an embedder can observe changes: not fuel, not the grant, not the public API, not a default. The runner's remaining ceiling for short concurrent runs is named in the memo, not hidden.

## Design

- `src/wasi_python/_zip.py`: `_data_intact`, the body of Decision 2, its docstring kept, the one comment giving the reason in words. `_zip_folder`, `_extract_data` and `_record` unchanged (the record is still written by `_record`'s `os.walk`, called from `_extract_data`; its keys are `as_posix()` strings, which the new walk reproduces with `/`).
- `tests/unit/test_runner_data.py`: the counting check (Decision 1, first); the five existing checks unchanged.
- `tests/unit/test_runner_calls.py`: the lock-ownership check (Decision 1, second), beside the file's other checks on the call's threads; it is the file's first check to run a real guest, behind the harness gate `needs.need("runner", "artifact dir")` (Decision 1 says why it is here and not in a file that already uses the set).
- `CHANGELOG.md`, under the one unreleased section (`release/version.py bump` makes it): one line (below).
- `README.md`, `docs/`: unchanged (neither names the comparison or a speedup).

### The CHANGELOG line

- **The per-call comparison of matplotlib's data takes half the interpreter's time** (spec 128). Every call compares the whole `mpl-data` tree, 213 entries, with its record before granting it; the comparison walked the tree with `os.walk` and built a path object per entry, 2.3 to 2.9 ms of interpreter time per call under the zip folder's lock. It now lists with `os.scandir`, stamps each entry with one `os.lstat` as the record does, and keeps plain strings: the same comparison, the same one stat per entry on every system, about 1 ms. On the research machine the eight-thread wall of eight hellos shortened by 14 to 33 % in three windows with a result file (their ratio to the sequence 1.5 to 1.9 before, 1.9 to 2.0 after; on a shared machine the wall is the steadier number), and a hello in sequence is one to two milliseconds shorter (benchmark facts, not checks). The memo behind it found no lock of the runner's held across a guest and none waited on: concurrent runs wait on the interpreter's lock over the runner's per-call checks, and that ceiling is named, not hidden. A check now pins that the home thread holds no process lock while its guest runs.

## Scope

In: `_data_intact`'s body, two unit checks, the CHANGELOG line. Out: `zip_lock` and the lock order (kept, Decision 3); the grants walk, the private folders, the identity check, the ticker, the thread start (Decision 4); any cache of per-call verdicts; `docs/` and the README; Linux and Windows measurements (the change is uniform; the checks run on all three); the bare arm and the Rust spike (research only).

## Acceptance criteria

1. `test_the_data_comparison_lists_each_folder_once_and_stats_each_entry_once` green on three systems, seen failing on main's code first, with the counts it saw recorded in the landing notes (on the fixture: seven `os.lstat` against main's ten).
2. `test_the_home_thread_holds_no_process_lock_while_its_guest_runs` green on main and on the branch, and seen red once under the deliberate fault of Decision 1 in a scratch copy, recorded in the landing notes.
3. The five existing checks of `test_runner_data.py` green without any change to them.
4. The fast tier green on the branch; the release run on the branch green on three systems with **no growth line** (Decision 6).
5. `ruff check`, `ruff format --check` and the rules checks green; no function or module crosses a ceiling.
6. The builder records, as benchmark facts in the landing notes and not as checks: the memo's driver (`../research/2026-10-24-concurrent-runs-wait-on-each-other/scripts/driver.py`, `fix` mode with `FIXES=data_scandir`, which toggles the research prototype against whatever `_data_intact` is at import) run once on main's code and once on the branch, each with eight hellos in sequence and on eight threads, the speedups, and the one-minute load average. On main the toggle is prototype against today's body; on the branch its baseline is the new body and the toggle the prototype, which cost the same, so the comparison that matters is the branch run's baseline against main's baseline. The landing notes then show the saving the specification claims and the machine it was measured on.

## For the lane

- **Wave kind:** parallel-safe, runner code; the pre-build review is required.
- **The claim list:** none. No existing check changes, no gap entry, no golden output, no growth. Two checks are added, which is a judge change by hash.
- **Flags:** `--accept "128: the per-call comparison of matplotlib's data by os.scandir, the same comparison in half the interpreter's time"`, `--accept-judge "128: two checks added: the comparison lists each folder once and stats each entry once; the home thread holds no process lock while its guest runs"`. No `--accept-growth`: a growth line ejects the entry.

## Disposition of the pre-build review

`../reviews/128-concurrent-runs-do-not-wait-on-each-other-spec-2026-10-24.md`, in the review's order.

1. H1 (on Windows the `DirEntry`'s stat is not the record's `os.lstat`: `st_dev`, `st_ino` and `st_ctime` differ, the tree is judged changed every call) — fixed in the specification: Decision 2's second bullet and its new bullet (`os.lstat(entry.path)` per entry, on every system, with the reason), the comment's wording there, Decision 1's first check (renamed; it asserts one `os.lstat` per entry plus the root, seven on the fixture against main's ten), Decision 5 (the wrong Windows sentence deleted; the stamp's source named), the Problem's fourth paragraph, the Intent and the CHANGELOG line ("the same stats", "one `os.lstat` as the record does"), acceptance criterion 1 and the `--accept-judge` flag. The reviewer's cost figure (0.89 against 0.92 ms) was confirmed by the author at load 5 (0.94 against 0.95, main 2.28) with a scratch run of the memo's probe; no evidence file was added.
2. L1 (the fault meant to show the second check red released the lock) — written in by the reviewer, confirmed: `p.zip_lock.acquire()` in place of the `with`, released only in `_remove_zips`.
3. L3 (the second check needs the set and `run`, which `tests/unit/test_runner_calls.py` does not use) — fixed in the specification: Decision 1's second bullet and the Design's third bullet keep the check in that file behind the harness gate `needs.need("runner", "artifact dir")`, as `test_runner_module_caches.py`'s `compiled` fixture does, and say why it is not moved to one of the four files that already use the set.
4. L4 (the window "1.77 → 1.96" has no result file) — fixed in the specification: the Problem's fourth paragraph counts only the two windows the evidence folder holds and the reviewer's re-run, and says the third was overwritten and is not counted. Not fixed in the memo: the run is gone and the author has no file to add, so the memo's §5 row keeps its number with this specification's note standing beside it; the memo is the research record, this file the one that is built from.
5. L2 (the CHANGELOG line and the Problem claimed "about 2.0" from the best window) — written in by the reviewer, confirmed: the eight-thread wall's change is the steadier fact; the Problem keeps 2.02 with its window and now carries the reviewer's 1.88 beside it.
6. L6 (`_extract_data`'s `os.walk` is `_record`'s) — written in by the reviewer, confirmed.

## Landing notes

Not yet built. The builder fills this section: the commits, the first check seen failing on main's code and the second seen red under the fault, the fast tier, the branch's release run (its id, every line green, no growth line), the benchmark facts of acceptance criterion 6, the self-check list (`../reviews/README.md`), and the rebase onto the wave's tip with every conflict named.

## One line

`_data_intact` lists `mpl-data` with `os.scandir`, stamps each entry with one `os.lstat` as the record does on every system, and keeps plain strings instead of a path per entry, the same comparison with the same stats in half the interpreter's time, because the memo found that eight concurrent runs wait on the interpreter's lock over the runner's own per-call checks and on no lock of the runner's, and this is the one check with a cheaper equal form.
