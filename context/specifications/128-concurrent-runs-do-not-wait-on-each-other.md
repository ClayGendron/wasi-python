# 128: Concurrent runs wait less on each other: the data comparison by scandir

- **Status:** **drafted 2026-10-24**, from the speed spike's parallel row (eight hellos: the product 1.9 times its sequence, bare wasmtime-py 4.2) and the attribution memo written for it. Its checks are named in Decision 1 and not yet written: the builder writes them first, records the first failing on main's code and the second green on main and red under a deliberate fault (AGENTS.md rule 3), then builds. It is runner code, so a **pre-build review is required** (AGENTS.md rule 8); a different agent reviews the build. Its file name is the question it was drafted for; its title is what the research supports, and the memo's §6 says why the specification is this small.
- **Date:** 2026-10-24
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, **not structural**: `src/` (`_zip.py` only, one function body), two unit-check files already in the `own-runner` shard (`tests/unit/test_runner_data.py`, `tests/unit/test_runner_calls.py`), and `CHANGELOG.md`. It touches nothing under `scripts/`, `recipes/`, `downloads/SHA256SUMS` or the release workflow, no artifact byte, no `docs/` page and not the README. Decision 5 says why it is not structural by AGENTS.md's definition. It changes no default an embedder can see (constitution §4.15): no limit, no channel, no path, no lock.
- **Depends on:** landed and unchanged: 023 (matplotlib's data beside the zip; its Decision 5, the per-call comparison of the whole tree, which this specification keeps to the letter), 078 (the guest's own thread; the home thread, whose holds Decision 1's second check pins), 105 (the process object, the one seam the checks use). On nothing in flight. It shares `CHANGELOG.md` with whatever lands beside it, nothing else.
- **Research it stands on:** `../research/2026-10-24-concurrent-runs-wait-on-each-other.md` (the attribution: §3 the phases and the locks, §4 the cause, §5 every candidate sized, §6 what is and is not proposed) and `../research/2026-10-23-a-rust-runner-against-wasmtime-py-on-speed.md` §3.4 (where it was found). Every number below is one of theirs (EXECUTED there, on a shared machine, as same-window ratios) unless marked.

## The problem

Eight `print('hello')` guests on eight threads run **1.5 to 1.9** times faster than the same eight in sequence in the product, against **3.3 to 4.2** in a sixty-line wasmtime-py embedding of the same module on the same machine. The product loses at two threads already (1.45 against 1.80), before any machine limit can matter.

The memo looked for the lock. There is none. Every lock on the process object is a leaf held for microseconds, none is held while a guest runs, and the stack-size window, the epoch ticker, the private folders and the identity check each measured at nothing when switched off. One lock shows the waiting: `zip_lock` is held for about 3 ms per call, because under it the runner compares the whole `mpl-data` tree with its record (spec 023 Decision 5, every call, before granting), 213 entries by `os.walk`, one `os.lstat` per entry and a `Path` built and stringified per entry. On eight threads the eight holds queue, and the longest run spends 40 of its 82 ms in that queue. But the comparison moved **outside** the lock made the batch **slower**, by 20 to 35 % in three windows.

That is because the cause is the interpreter's lock, not the runner's. A product call runs about **7.4 ms of host-side Python** around a 12 ms guest and makes about **707 os-level calls** (458 `lstat`, 125 `stat`, 30 `open`, …; bare makes 5). Python's lock runs that work one thread at a time, and every os call releases and re-takes the lock, which under eight-way contention costs 1.6 to 2.7 times the sequential time. The floor for eight calls is 8 × 7.4 + 12 ≈ 71 ms against 155 in sequence: a ceiling near 2.2 with today's runner. The queue on `zip_lock` was, by accident, scheduling the eight comparisons one at a time, which is the least bad way to run them.

Of the 7.4 ms, the `mpl-data` comparison is 2.3 to 2.9 ms, the largest single step, and three quarters of it is pathlib building a path per entry, not the stats. The grants walk is 1.2 ms (every runtime folder judged each call, spec 113), the private folders and releases 1.6, the rest small. Only the comparison has a cheaper form that makes the **same comparison with the same system calls**: `os.scandir`, whose `DirEntry.stat(follow_symlinks=False)` is the one `lstat` per entry the kernel sees today, with plain strings for the keys. Prototyped from outside the runner it takes **1.1 ms** per call, answers as the original on four trees (the live tree, a copy with new stamps, the copy against its own record, a link in place of a file), and as a toggle lifted eight hellos from 1.51 to **2.02** (the parallel wall 97.9 → 70.7 ms), from 1.77 to 1.96, and from 1.88 to 1.90 in three windows, with the sequence 4 to 6 ms shorter.

## Decisions

### 1. The checks first

Written before the code, each in a file the `own-runner` shard already runs on all three systems. No check measures time (AGENTS.md: tests count operations, never wall-clock). Neither patches a private name of `wasi_python`: the first wraps the standard library's `os` functions, the second replaces attributes of `process()` itself, the sanctioned seam.

- `tests/unit/test_runner_data.py::test_the_data_comparison_lists_each_folder_once_and_stats_no_path`: the file's fixture tree (`FILES`, extracted by `_extract_data` as the existing checks do) is compared with its record while `os.scandir`, `os.lstat` and `os.stat` are wrapped by the test to count calls. The comparison answers true; `os.scandir` was called once per folder of the tree plus one for its root; `os.lstat` and `os.stat` together at most twice (the root's link and folder tests), and never for an entry. **On main: fails**, with one `os.lstat` per entry (the fixture's files and folders) and `os.walk`'s listings. This is the operations count that holds the change: the per-entry work is one `DirEntry.stat`, nothing built by path.
- `tests/unit/test_runner_calls.py::test_the_home_thread_holds_no_process_lock_while_its_guest_runs`: every `threading.Lock` and `RLock` attribute of `process()` (the names `_process.py` lists; the check finds them by type through the `RENEW` table's keys) is replaced through `monkeypatch.setattr(process(), name, …)` by a stand-in that records the owning thread's ident while held and forwards `acquire`, `release`, `__enter__`, `__exit__` and `locked`. A `run` with `host=` whose guest calls the door once: the host function, which the runner runs on the home thread (spec 078), records which stand-ins the calling thread owns at that moment. Asserted: the door was called, and the set is empty. **On main: green** (the memo's finding), and the builder records it red once under a deliberate fault in a scratch copy of `_zip.py` whose `_zip_folder` takes `p.zip_lock.acquire()` in place of its `with p.zip_lock:` and releases it only in `_remove_zips`, so the lock stays held through `_preopens` and the guest's run (the fault the check exists for; a `return` inside a `with` block releases the lock, so that is no fault), so the check is shown to bite. Why a check that is green on main is still written: this specification keeps the comparison under `zip_lock` on the memo's evidence, and the lock is released before the guest starts; the check pins that, and that no later change holds any process lock across a guest.
- The five existing checks of `test_runner_data.py` are kept unchanged; `test_every_change_on_the_host_is_seen_and_undone` (an added file, a changed one, a removed folder, a folder swapped for a link, the root swapped for a link: each fails the comparison and is undone) is the one that holds the comparison's meaning, and it must stay green on the new body without any change.

### 2. The comparison by `os.scandir`

`_zip._data_intact` keeps its signature, its docstring's promise and its answers, and walks the tree with `os.scandir` instead of `os.walk` and pathlib:

- the two root tests first, as today (`os.path.islink(data)`, `os.path.isdir(data)`: false on either);
- an iterative walk over a to-do list of relative folder keys (plain strings, `/`-joined, as `Path.as_posix()` gave: the record's keys do not change); for every `DirEntry`, one `stat(follow_symlinks=False)`; a folder is recorded as `None` and queued; a regular file as `_artifacts._stamp(st)`; anything else (a link, a device, a socket) answers false at once;
- any `OSError` answers false, as today;
- the answer is `seen == record`, as today.

About twenty-five lines; under 80 (AGENTS.md's function ceiling). `_zip.py` stays at about 290 lines. A comment gives the reason in words: the comparison runs on every call and the per-entry work is one stat, so no path object is built per entry.

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

One function body in `_zip.py`; two checks. No module-level mutable or lock, no private wasmtime-py name, no platform branch (`os.scandir` and `DirEntry.stat` are the standard library's on every system; on Windows `follow_symlinks=False` reads the reparse point as today's `os.lstat` does), no test seam that is not on the process object or the standard library. `_zip.py` stays under 300 lines; `_data_intact` under 80. The build shows the rules checks green.

### 6. Fuel does not move

The change is host-side only: nothing the guest sees changes (the same folder is granted, read-only, at the same path). The builder's release run on the branch confirms it across every check and system; **any growth line is red for this specification**, since it claims none.

## Intent

Every call still compares the whole `mpl-data` tree with its record before granting it, with the same system calls, in half the interpreter's time, so eight concurrent runs spend less of their time waiting for one another's checks and a run in sequence is a millisecond or two shorter. Nothing the guest or an embedder can observe changes: not fuel, not the grant, not the public API, not a default. The runner's remaining ceiling for short concurrent runs is named in the memo, not hidden.

## Design

- `src/wasi_python/_zip.py`: `_data_intact`, the body of Decision 2, its docstring kept, the one comment giving the reason in words. `_zip_folder`, `_extract_data` and `_record` unchanged (the record is still written by `_record`'s `os.walk`, called from `_extract_data`; its keys are `as_posix()` strings, which the new walk reproduces with `/`).
- `tests/unit/test_runner_data.py`: the counting check (Decision 1, first); the five existing checks unchanged.
- `tests/unit/test_runner_calls.py`: the lock-ownership check (Decision 1, second), beside the file's other checks on the call's threads.
- `CHANGELOG.md`, under the one unreleased section (`release/version.py bump` makes it): one line (below).
- `README.md`, `docs/`: unchanged (neither names the comparison or a speedup).

### The CHANGELOG line

- **The per-call comparison of matplotlib's data takes half the interpreter's time** (spec 128). Every call compares the whole `mpl-data` tree, 213 entries, with its record before granting it; the comparison walked the tree with `os.walk` and built a path object per entry, 2.3 to 2.9 ms of interpreter time per call under the zip folder's lock. It now walks with `os.scandir` and plain strings: the same comparison, the same one stat per entry, about 1.1 ms. On the research machine the eight-thread wall of eight hellos shortened by 14 to 33 % in three windows with a result file (their ratio to the sequence 1.5 to 1.9 before, 1.9 to 2.0 after; on a shared machine the wall is the steadier number), and a hello in sequence is one to two milliseconds shorter (benchmark facts, not checks). The memo behind it found no lock of the runner's held across a guest and none waited on: concurrent runs wait on the interpreter's lock over the runner's per-call checks, and that ceiling is named, not hidden. A check now pins that the home thread holds no process lock while its guest runs.

## Scope

In: `_data_intact`'s body, two unit checks, the CHANGELOG line. Out: `zip_lock` and the lock order (kept, Decision 3); the grants walk, the private folders, the identity check, the ticker, the thread start (Decision 4); any cache of per-call verdicts; `docs/` and the README; Linux and Windows measurements (the change is uniform; the checks run on all three); the bare arm and the Rust spike (research only).

## Acceptance criteria

1. `test_the_data_comparison_lists_each_folder_once_and_stats_no_path` green, seen failing on main's code first, with the counts it saw recorded in the landing notes.
2. `test_the_home_thread_holds_no_process_lock_while_its_guest_runs` green on main and on the branch, and seen red once under the deliberate fault of Decision 1 in a scratch copy, recorded in the landing notes.
3. The five existing checks of `test_runner_data.py` green without any change to them.
4. The fast tier green on the branch; the release run on the branch green on three systems with **no growth line** (Decision 6).
5. `ruff check`, `ruff format --check` and the rules checks green; no function or module crosses a ceiling.
6. The builder records, as benchmark facts in the landing notes and not as checks: the memo's driver (`../research/2026-10-24-concurrent-runs-wait-on-each-other/scripts/driver.py`, `fix` mode with `FIXES=data_scandir`, which toggles the prototype against main's body) run once on main's code and once on the branch, each with eight hellos in sequence and on eight threads, the speedups, and the one-minute load average, so the landing notes show the saving the specification claims and the machine it was measured on.

## For the lane

- **Wave kind:** parallel-safe, runner code; the pre-build review is required.
- **The claim list:** none. No existing check changes, no gap entry, no golden output, no growth. Two checks are added, which is a judge change by hash.
- **Flags:** `--accept "128: the per-call comparison of matplotlib's data by os.scandir, the same comparison in half the interpreter's time"`, `--accept-judge "128: two checks added: the comparison lists each folder once and stats no path; the home thread holds no process lock while its guest runs"`. No `--accept-growth`: a growth line ejects the entry.

## Landing notes

Not yet built. The builder fills this section: the commits, the first check seen failing on main's code and the second seen red under the fault, the fast tier, the branch's release run (its id, every line green, no growth line), the benchmark facts of acceptance criterion 6, the self-check list (`../reviews/README.md`), and the rebase onto the wave's tip with every conflict named.

## One line

`_data_intact` walks `mpl-data` with `os.scandir` and plain strings instead of `os.walk` and a path per entry, the same comparison with the same stats in half the interpreter's time, because the memo found that eight concurrent runs wait on the interpreter's lock over the runner's own per-call checks and on no lock of the runner's, and this is the one check with a cheaper equal form.
