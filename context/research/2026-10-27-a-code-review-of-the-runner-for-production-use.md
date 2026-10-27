# A code review of the runner for production use

- **Status:** research, 2026-10-27. An outside read of `src/`, `tests/`, `scripts/` and `release/` at `dev` `898bc09` (0.1.1 accepted), asked by the owner with one question: is this built for production use? It changes nothing: no code in `src/`, no pin. Its findings become specifications 144, 145 and 146; what it leaves as notes is listed in §6.
- **Date:** 2026-10-27
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Fable 5.1), with three fresh sub-agents of the same session, one per slice (§2, §3, §4). Box: one session.
- **Evidence:** the commands and their last lines in §1, run in a Linux container as root with no artifact set. No file beside this memo.
- **Stands on:** `src/wasi_python/` whole; `tests/unit/`, `tests/checks/`, `tests/harness/`, `tests/known_gaps.toml`; `scripts/`, `release/`; `AGENTS.md`, `constitution.md`, the 0.1.1 security and structural reviews.
- **Machine:** linux-x86_64, a cloud container, running as root (which changes two checks, §1); CPython 3.12, wasmtime-py 50.0.1; no `build/artifacts`, so no guest ran.

Labels: EXECUTED means run here; READ means read from a file, cited; INFERRED means the researcher's reasoning.

## The short version

1. **The sandbox boundary and the build are production-grade.** Every guest pointer, length, path, flag and frame is checked at one chokepoint each, provider answers are judged by type before any of their code runs, and no guest-driven escape was traced (READ, §3). Pins are verified at every use and patches are applied with a cleared git (READ, §4).
2. **The lifecycle code around `Session.run_async` is not there yet.** Two paths deadlock or strand a session: a `close()` from a tool during a `run_async` turn, and a queued turn cancelled after a concurrent `close()` (READ, §2, re-read by the researcher; specification 144).
3. **Three bounds are per call where a process needs them**: abandoned tool threads, host memory held for a guest's mount staging, and the text a `ToolError` hands the guest (READ, §3; specification 146).
4. **A mount provider's contract leaves a hole the first Windows provider will fall into**: a path component may carry a backslash or a drive letter, and three small answers differ from wasmtime's (READ, §3; specification 145).
5. **The tooling is clean**: ruff and ruff format on `src/` and `tests/`, mypy strict on `src/`, and 2,953 of 3,028 unit rows pass; the one failure and the fast tier's one lost pass are this container's root user, not the code (EXECUTED, §1).
6. **Two facts a production embedder should weigh**: the engine seam reads 31 private names of wasmtime-py through ctypes, in one module with a debt sheet (READ, `_wasmtime_ffi.py:14-50`), and the project has one owner and is eleven days past its first non-alpha release (READ, `CHANGELOG.md`).

## 1. What was run (EXECUTED)

```
$ uv run ruff check src tests            -> All checks passed!
$ uv run ruff format --check src tests   -> 188 files already formatted
$ uv run mypy src/wasi_python            -> Success: no issues found in 27 source files
$ uv run ruff check src tests scripts release
  -> Found 46 errors (E501 25, E702 12, I001 3, F402 2, E401 2, E701 1, B023 1), all under scripts/ and release/
$ uv run pytest tests/unit -q
  -> 1 failed, 2953 passed, 74 skipped in 306.15s
  FAILED tests/unit/test_runner_grants.py::test_the_walk_judges_links
    ValueError: 'g: ... passes through the link 'link' in a folder this user can write'
$ uv run pytest -m "not slow" -x -q
  -> 1 failed, 123 passed, 488 skipped; blocked by: artifact dir 483
  LOST tests/checks/test_v1_4_embedding.py::test_the_removal_never_deletes_what_the_guest_may_not[home]
    skipped without a known need: modes refuse nothing to root
```

The two failures are the container: it runs as root, so a folder "this user can write" is every folder, and mode bits refuse root nothing. Neither is a defect (INFERRED from the two messages). The 46 ruff findings are outside the set the judge lints (READ, `pyproject.toml`, `[tool.ruff] src`); §4 says what they are.

## 2. The runner's call lifecycle (READ)

A fresh sub-agent read `runner.py`, `_call.py`, `_sessions.py`, `_limits.py`, `_outputs.py` and `_process.py`. The researcher re-read the two High findings against the code and confirms the paths; the Medium and Low findings are the sub-agent's reads, cited, not re-traced.

The lock order written at `_process.py:10-28` holds in everything traced: no nested take outside the named pairs, and no leaf lock held across an embedder's code. The session state machine (`_sessions.py:115-128`, invariants at `:196-216`) is well designed. The defects are in the seams between `Session.run_async` and that machine, where the thread that claimed the turn is not the thread that runs it.

### High 1. `Session.close()` from a tool or host function during a `run_async` turn deadlocks

`_claim` records the claiming thread as `holder` (`runner.py:1029`). `run_async` claims on the event-loop thread (`runner.py:1145`) and runs the turn on a worker (`_session_turn`, `_sessions.py:858`), which never rebinds `holder`: the only writer is `_move`, and the only `CLAIM` is the one in `_claim` (READ, grep of both files). A `host=` function or a tool runs on that worker, as the turn's home thread. A `close()` from there finds `holder != me` (`runner.py:1205`), falls through to `state.done.wait()` (`runner.py:1213`), and the turn cannot return until the tool does. Nothing breaks the cycle. The docstring at `runner.py:1189-1191` promises the synchronous behaviour, which does hold for `Session.run`. The inverse also holds: a `close()` from the loop thread returns at once without waiting for the ending, against invariant 2 at `_sessions.py:203`.

### High 2. A queued `run_async` turn cancelled after a concurrent `close()` leaves the session MARKED with no one to end it

Scenario: the pool is busy and the turn is claimed (TURN). Another thread calls `close()`: TURN to STOPPING, `here` is false, and it waits on `done`. The awaiting task is cancelled; `future.cancel()` succeeds (`runner.py:1166-1167`) and `_release_claim` moves STOPPING to MARKED (`_sessions.py:123`, which names this very case). The reaper acts only on OPEN (`_sessions.py:347`), and so does `_end_dropped` (`_sessions.py:395`); a later `_claim` sees `ended` set and raises `SessionEnded` without ending anything (`runner.py:1024-1038`). The `close()` caller blocks until interpreter exit, and the store, up to `memory_bytes`, and the pipe reader thread are held meanwhile. The path through `_submit` raising (`runner.py:1157-1160`) is the same hole.

### Medium 1. A closer thread that fails to start strands the session in ENDING

`_reap` marks and claims the ending with `_CLOSER` under the lock, then `_start_closer` calls `thread.start()` outside it (`_sessions.py:350-355`, `:319`). If `start()` raises, as it does under thread pressure when many idle sessions expire at once, the exception is swallowed into `wait = TICK_S` (`_sessions.py:388`), the phase stays ENDING, nothing retries, `close()` hangs at `runner.py:1213` and exit hangs at `_sessions.py:434`. The same holds for `_claim(here=False)` (`runner.py:1037`) and `_end_dropped`.

### Medium 2. Interpreter exit hangs with a turn still queued in the pool

`_stop_async_calls` cancels queued futures (`runner.py:541`) before `atexit` runs; the coroutine never resumes to `_release_claim`, so the phase stays TURN; `_sessions_at_exit` marks it STOPPING and waits on `done` (`_sessions.py:428-434`) for a turn that never runs.

### Medium 3. An abandoned turn's session leaks until exit

`_abandon_turn` (`_sessions.py:914-922`) moves the session to MARKED at the guest thread's end; a user who then drops the `Session` gets no ending, since `_end_dropped` handles OPEN alone, and the store stays resident.

### Low

`_write_output` returns `size` on any failure without setting `dropped` (`_outputs.py:300-306`): a silent truncation. `process().pools` grows by one pool at every `set_defaults` resize (`runner.py:507`). `_end_quietly` swallows every `BaseException` from a closer (`_sessions.py:323-326`), so an embedder's `atexit` tool error is visible only as the outcome.

### Design and load

`_instance` (`_call.py:395-551`) and `_open_session` (`_sessions.py:935-1072`) are near-duplicates past the 80-line rule, and have already diverged. `_call.py` mixes the run path, the home folders, the driver, the epoch callback, the linkers, `poll_oneoff`, the door and the tool host. `runner.py` carries three copies of the same argument documentation. The lock essay and the state invariants are exemplary; long justifications inside `except` blocks (`_call.py:709-760`) hide control flow. Under load, every call or turn starts a guest thread under the process-wide `stack_size_lock` (`_home.py:333-342`), a serialisation point; every session holds one pipe reader thread for its life (`_outputs.py:125-128`); every expiry at the same instant starts one closer thread, which is Medium 1's trigger; and `_wake_reaper` after every turn makes `_reap` scan every session. These are facts for a benchmark memo, not findings (INFERRED).

## 3. The sandbox boundary: mounts and tools (READ)

A fresh sub-agent read `mounts.py`, the four `_fs_*.py` modules, `_tool_host.py`, `tools.py` and `_tool_schema.py`. It traced no guest-driven escape. Every guest pointer and length passes `_Memory.fits` (`_fs_memory.py:214-215`, `:231-238`, `:249-265`); every path passes `_resolve` (`_fs_paths.py:61-89`: no leading `/`, no NUL, `..` refused the moment it would climb above the descriptor's folder, a nested preopen `EPERM`); provider descriptors start at 2**30 and `fd_renumber` refuses them (`_fs_descriptors.py:397-411`); links are `ENOTSUP` or `EINVAL` by construction (`_fs_paths.py:274-302`, `:429-438`); every provider call runs inside one fault boundary (`_fs_table.py:307-320`) that maps `OSError` by errno name (`mounts.py:280-299`) and keeps exception text host-side. Tool frames are decoded once (`_tool_host.py:104-153`), validated under a step budget (`_tool_schema.py:449-626`), and a tool's exception other than `ToolError` crosses as "(internal error)" (`_tool_host.py:269-272`). Guest-supplied values are trusted nowhere found: cookies are bounds-checked indices (`_fs_descriptors.py:391`), flags and enums end the run as wasmtime does (`_fs_memory.py:160-190`), frame ids are range-checked (`_tool_host.py:939-941`), and arguments reach `fn(**args)` only after the schema (`_tool_host.py:1000-1009`).

### Medium 4. A normalised path may carry backslashes and drive letters to the provider

`_resolve` splits on `/` alone (`_fs_paths.py:69`), so `a\..\..\x` or `C:x` is one component. The provider contract (`mounts.py:82`; `docs/how-to/mounts.md:39`) promises normalised paths and says nothing else. A provider on Windows that writes the obvious `Path(root) / path` lets the guest read outside the mount. No provider ships in the package, so this is a contract gap, and it is the first provider anyone writes.

### Medium 5. Host memory for one guest can reach about three times `memory_bytes`

Mount staging is bounded by `memory_bytes` (`_call.py:483`; 1 GiB by default, 4 GiB when `None`), and that bound is host memory outside the guest's linear memory. A guest that seeks to the bound and writes one byte makes `_grow` allocate the gap (`_fs_descriptors.py:303-317`); at close or exit `bytes(entry.data)` copies it (`_fs_table.py:541`) and the provider gets its own copy. N untrusted guests then cost about 3 GiB each at peak, not the 1 GiB budgeted (INFERRED from the three allocations; not measured).

### Medium 6. Abandoned tool threads are uncancellable and unbounded across runs

A tool past its deadline is marked abandoned and runs on with the embedder's full authority (`_tool_host.py:723-736`). `_MAX_ABANDONED = 4` (`_tool_host.py:38`) bounds one call or one session, not the process. With `timeout_s=None` and a run with no deadline, `_wait` loops without bound (`_tool_host.py:749-769`). Thousands of runs, one slow tool each, accumulate threads and whatever they hold.

### Low

`path_filestat_set_times` on a writable mount succeeds on a missing path (`_fs_paths.py:424-426`: no `stat`). The `fd_pread` guard and slice disagree (`_fs_descriptors.py:254-257`: `count` feeds the `EINVAL` check, `size` the slice). `ToolError` text crosses whole, 4,096 characters, so `raise ToolError(os_error)` hands the guest host paths (`_tool_host.py:190-193`, `:263-266`). Nested-preopen `EPERM` against `ENOENT` (`_fs_paths.py:86-88`) lets a guest enumerate other preopens' names. `writable` is checked in each handler rather than at one chokepoint (`_fs_paths.py:137`, `:368`, `:417`, `:436`, `:465`; `_fs_descriptors.py:190`, `:218`). An `O_DIRECTORY` open never stats first (`_fs_paths.py:150-155`), so a lenient provider hands back a listing for a file.

## 4. The tests, the build scripts and the release (READ)

A fresh sub-agent sampled `tests/` and read `scripts/` and `release/`.

Three layers, all real. Unit rows drive the boundary with hand-written WebAssembly text modules under real wasmtime (`tests/unit/test_runner_calls.py:21-45`, `tests/unit/test_runner_mounts.py:51-63`, `tests/unit/test_tools.py:22-38`). The goal checks run the real guest through `tests/harness/guest.py`, which seeds entropy, the clock and inode numbers itself so fuel repeats exactly; golden outputs are regenerated natively under a pinned oracle with two hash seeds (`tests/jobs/regen.py:8-10`). The upstream suites of every package run in the guest with a pass count that may not fall. The wall-clock rule is largely honoured: every `time.sleep` found is a trigger or a fail-safe, not a measurement; a 0.5 s assumption at `tests/checks/test_v1_4_embedding.py:993` and two bounded polling loops (`:977-982`, `:1541-1551`) are the residue, and a slow host can turn them red (Low). The judge harness is about 23,000 lines plus about 12,000 of its own tests, with digest-pinned gaps and a hash-chained history: a second product to maintain and a steep ramp (Medium, a fact, not a defect). The 297 gaps are all upstream-suite cases: 266 close with the limitations page and 31 name pending work. No bare `assert True`, three strict `xfail`s, and skips go through a fixed vocabulary of needs (`tests/harness/needs.py:3-7`), so nothing suggests a test written to pass.

The 21 shell entry points are `#!/bin/sh` with `set -eu`, with checksum output routed through a file rather than a pipe (`scripts/00_download.sh:269-270`); `apply_patches.sh:21-25,61-66` refuses a tree with `.git`, runs git with a cleared environment and fails on any offset hunk; every step re-verifies its tarball at use (`scripts/common.sh:41-67`). Low: a fixed `.pin-check` path (`scripts/common.sh:63-66`) that collides if two builds share a tree; three short wrappers without `set -eu`; `release/ci_plan.py` (980 lines) and `scripts/assemble_artifacts.py` (901) are dense single files. The 46 ruff findings are cosmetic: 37 in one-off bench and OpenBLAS tools, `B023` a false positive, and two `F402` at `scripts/assemble_artifacts.py:587,601`, a loop variable that shadows an import in the script that builds the artifact set, worth a rename.

## 5. What follows

- **Specification 144, a session is always ended**: High 1, High 2, Medium 1, Medium 2 and Medium 3 of §2, and the two Low rows of `_outputs.py` and `runner.py`.
- **Specification 145, a mount's names work the same on every host**: Medium 4 and the four mount Lows of §3.
- **Specification 146, the tool host's bounds are the process's**: Medium 5, Medium 6 and the `ToolError` Low of §3.

## 6. Left as notes

- The duplication of `_instance` and `_open_session`, and `_call.py`'s mixed concerns: a structural change, reviewed before it is built; it waits for its own specification. The reserved 142 (the 80-line allowance judged by length) is the judge's half of it.
- The `writable` checks moved to one chokepoint, and the nested-preopen `EPERM`: each a design choice that a change to the boundary should carry, not a fix on its own.
- The load facts of §2: a benchmark memo on many sessions at once, with the reader threads, the stack-size lock and the reaper's scan counted, before any change is proposed.
- `tool.ruff.src` extended to `scripts` and `release`, and the two `F402` renamed: a one-hour change the next pull request that touches those files may carry.
- The engine seam's 31 private names: already a debt sheet with the public name wanted for each; nothing to add.

One line: the wall holds and the build is honest; the async session paths and three per-call bounds need the three specifications above before an embedder runs many untrusted sessions at once.
