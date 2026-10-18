# Review of 030 — A cancel during a door call is named "cancelled" (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change, the specification,
  or its pre-build review and confirmation. I read `AGENTS.md`, the constitution (§4.9, §4.10,
  §4.13, §4.14, §4.15, §5.6, §5.7), specification 030 with its landing notes, its pre-build
  review with the confirmation and the three builder notes, and the diff (`git show 52674ed`).
  I read the runner around it: `_instance`, `_fuel_used`, `_drive`, `_Call`, `_shared`,
  `_epoch_now`, `_epoch_answer`, `_stop_error`, `_door`, `_ctrl_c_watched`, `_deferred_ctrl_c`,
  `_stop_at` and `_epoch_ticker`. I read `.github/workflows/release.yml`'s verify job. Each
  claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** commit `52674ed` on `spec/030-a-cancel-in-the-door-is-named`, in the worktree
  `../wasi_python-030`: `src/wasi_python/runner.py`, `tests/checks/test_v1_4_embedding.py`,
  `tests/unit/test_runner_cancel.py` (new), `tests/unit/test_runner_async.py`, `CHANGELOG.md`
  and the specification's landing notes.
- **Ran (EXECUTED, darwin-arm64, 10 cores, host CPython 3.14 from `uv run`, wasmtime-py 49, main's
  frozen set `build/sets/4befe9de64edc783` read only; `scripts/build.sh` not run).** Work is under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/030-buildreview/`.
  - `uv sync`, then `WASI_PYTHON_ARTIFACTS=… uv run pytest` in the worktree, no flags
    (`judge.log`). `uv run ruff check src tests`, `uv run ruff format --check src tests`.
  - Mutants. I did not edit the worktree. `make_mutants.py` extracts `src/wasi_python` from
    `52674ed` with `git archive` into `mutants/base/` (`diff` against `git show
    52674ed:src/wasi_python/runner.py`: identical), and makes five copies, each with one change
    asserted to apply exactly once. Each copy is put first on `PYTHONPATH` (checked:
    `wasi_python.runner.__file__` is the copy's; the check children inherit it). `before/` is the
    implementer's pre-fix copy (`diff` against `52674ed^`'s runner: identical).
    - `mutants_unit.txt`: `tests/unit/test_runner_cancel.py`, `test_runner_async.py` and
      `test_runner_calls.py` against each copy.
    - `repeat.txt`: `tests/checks/test_v1_4_embedding.py -k "door_call or ctrl_c_before or
      cancel"`, six times on `base`, twice on `before` and on each mutant. `--progress-dir` was a
      scratch folder, so nothing under the worktree's or main's progress folders was written by
      these runs.
  - `load.txt`: the new `CANCEL_RUN` child (extracted from the check file by `extract.py`, byte for
    byte), its four new cases 16 at a time on 10 cores, three rounds: 48 runs.
  - `extra_cases.txt`: the pre-build reviewer's `030-review/cases.py`, run unchanged against
    `mutants/base/src` (the built runner): seven cases, three times each, the four-thread case
    among them.
  - `ign.py`: the `door-ctrl-c` child run with SIGINT inherited as ignored, on the check's text
    (`cancel_run.py`) and on two fixed variants (`cancel_run_raise.py`, `cancel_run_fixed.py`).
  - `margin.py`: how far into the deadline case's 50 ms the guest reaches the door, snapshot and
    plain binary, five calls each. A benchmark fact, not a check.
  - `gh run view 39088978405`: main's last release dry run, for what the Windows verify job runs.
  - I wrote only this file in the main tree. The worktree is clean after all of it (`git status
    --short` empty; `git diff --stat` empty). The full judge rewrote the worktree's
    `build/progress/latest.json`, as every run does. I never passed `--accept`,
    `--accept-judge` or anything that writes `context/progress/`. No commit, stage, checkout,
    restore or stash.

## The judge

- **Full judge (EXECUTED, `judge.log`).** Exit 0. `770 passed, 19 skipped`. `wasi_python v1:
  186/197 pass · 0 gap · 11 blocked · 0 fail (unit suite 584/592, 8 skipped)`; v1.4 `74/74`.
  `ratchet vs 567d64204b: lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 4 · grew 0 ·
  judge changed: tests/checks/test_v1_4_embedding.py, tests/unit/test_runner_async.py,
  tests/unit/test_runner_cancel.py`. This matches the implementer's `build/030-judge.log` line
  for line.
- **Ruff (EXECUTED).** `All checks passed!`; `56 files already formatted`.
- **The new checks, repeated (EXECUTED, `repeat.txt`).** `10 passed` in each of six runs on the
  built runner. On the pre-fix runner, `3 failed, 7 passed` in both runs: the two
  `test_a_cancel_during_a_door_call_is_named` cases and the deadline check. The Ctrl-C guard
  passes before and after, as criterion 3 says.
- **Under load (EXECUTED, `load.txt`).** 48 of 48 children gave the expected line, 16 at a time
  on 10 cores: `cancelled None None b''` for both sizes, `deadline None None b''`, and
  `KeyboardInterrupt`.

## Findings, most severe first

1. **High. `test_ctrl_c_before_a_cancel_in_the_door` will fail the release's Windows verify
   job.** (`tests/checks/test_v1_4_embedding.py`, `CANCEL_RUN`, the `door-ctrl-c` branch.)
   - READ (`release.yml:207-243`): `verify (windows-2025)` runs
     `tests/checks/test_v1_4_embedding.py` against the release's bytes. EXECUTED (`gh run view
     39088978405`): on main's last dry run that job ran the v1.4 checks, `194 passed, 10
     skipped`. Nothing skips the new check on Windows (READ: it has no mark, and `_child` only
     needs the set).
   - READ (`context/prior_art/cpython`, 3.14, `Modules/posixmodule.c:9739-9762`, and
     `Doc/library/os.rst`): on Windows, `os.kill` sends a console event only for
     `CTRL_C_EVENT` (0) or `CTRL_BREAK_EVENT` (1). Any other value "will cause the process to be
     unconditionally killed by the TerminateProcess API, and the exit code will be set to
     *sig*". `signal.SIGINT` is 2.
   - INFERRED: so on Windows the child is terminated with exit code 2 inside the host. `_child`
     asserts `out.returncode == 0`, so the check fails. The verify job fails, and `attest` and
     both publish jobs need it, so no release goes out. I could not run Windows; this rests on
     the source above.
   - The same file already knows this. READ (`CTRL_C`, line 556): the spec 011 check raises the
     signal with `signal.raise_signal(signal.SIGINT)`, with the comment "os.kill on Windows would
     end the process". That Windows job is green with that check in the file (EXECUTED, the run
     above; INFERRED that it ran there, since it has no skip mark).
   - A second, smaller hole in the same line. EXECUTED (`ign.py`): when the child inherits
     SIGINT as ignored (a background job of a non-interactive shell does), Python keeps it
     ignored. `_deferred_ctrl_c` then defers nothing, the signal is dropped, and the child prints
     `returned cancelled`, so the check fails. The `CTRL_C` script guards this with
     `signal.signal(signal.SIGINT, signal.default_int_handler)  # as in a plain script`.
   - Fix: in the `door-ctrl-c` branch, install `signal.default_int_handler` before the call, and
     replace `os.kill(os.getpid(), signal.SIGINT)` with `signal.raise_signal(signal.SIGINT)`.
     `os` is then unused in the child's import line. EXECUTED (`cancel_run_fixed.py`, that
     two-line change): `KeyboardInterrupt` 3 of 3 normally, and `KeyboardInterrupt` with SIGINT
     inherited as ignored. INFERRED: it behaves on Windows as the `CTRL_C` check does, since it
     uses the same call.
   - This is the implementer's flag 5. The answer is yes: the check runs there, and it would
     break.

2. **Low. The deadline check can pass without meeting the door.**
   (`test_a_deadline_during_a_door_call_under_cancel_is_named`.)
   - The deadline is 50 ms. The check asserts only `deadline None None b''`. If the guest takes
     longer than 50 ms to reach `_host.call`, the callback ends it before the door, with the same
     line. The check would then pass but test nothing.
   - EXECUTED (`margin.py`, a benchmark fact): the snapshot reached the door about 5 ms in on
     this machine; the plain binary about 29 ms in. Both reached it every time. The margin is
     ample here; it is thinner on a slow runner. The other three new cases do not have this gap:
     their host sets the cancel itself, or the check waits for "started".
   - Fix, cheap: have the host print one line before it blocks (say `in the door`), and assert
     it is the first line of the child's output. Then the check fails if the door is never
     reached.

3. **Low. One mutant survives every check; three survive the v1.4 checks.**
   - EXECUTED (`mutants_unit.txt`, `repeat.txt`):

     | mutant | v1.4 checks | unit tests |
     |---|---|---|
     | M1: entry guard without `call.ended` | survives | killed (`test_an_ended_call_is_not_served`) |
     | M2: the new branch records the cause (`call.stop`) | killed (3 fail) | killed (2 fail) |
     | M3: the new branch drops `_epoch_now` | survives | killed (2 fail) |
     | M4: the branch for every exception type | survives | killed (the `KeyboardInterrupt` case) |
     | M5: the entry guard moved above the Ctrl-C check | survives | survives |

   - M1, M3 and M4 are expected to survive the integration checks. The pre-build review showed
     why: wasmtime leaves the overdue deadline in place, and a real guest makes no shared call
     between the callback's error and its next function entry. The unit tests hold them, which is
     what criterion 4 is for.
   - M5 is the pre-build review's third builder note: do not move the guard above the Ctrl-C
     check. The code obeys it, and a comment says so. No test holds it. INFERRED (READ
     `_epoch_answer`, `_deferred_ctrl_c`): M5 is nearly equivalent at the run level. A Ctrl-C left
     pending at the guard is turned into a stop by the next epoch callback, or raised by
     `_deferred_ctrl_c` on exit. So the order the comment guards is held twice elsewhere.
   - Fix (optional): one unit case. A call with `ended` set, `_ctrl_c_watched` patched to `True`
     and `_ctrl_c["pending"]` set: `_shared` returns `stopped` and records a `KeyboardInterrupt`.
     It would kill M5.

4. **Low. The CHANGELOG says "a host's own exception … still comes first".** It is true for a
   `BaseException` such as `asyncio.CancelledError`, which `test_a_stop_holds_under_cancel`
   covers. It is not true for an ordinary `Exception`: `_door` turns that into `HOST_FAULT`
   (spec 006) and records nothing. EXECUTED (`extra_cases.txt`, `raising_host_then_cancel`): a
   host that sets the cancel, then raises `ValueError`, ends `cancelled`, 3 of 3. That is the
   right outcome, and the sentence would mislead a reader. Fix: "a host's own cancellation (an
   exception such as `asyncio.CancelledError`) or a Ctrl-C still comes first".

5. **Note. The invariant has one fail-safe exception.** READ: `_epoch_answer` sets `call.ended`
   and then calls `_stop_error`. If wasmtime cannot make an error, `_stop_error` continues for one
   tick instead (spec 015's build review, F2). Then `ended` is set while the guest runs on. A real
   trap in `host_alloc` during that one tick would be named from `ended`, not recorded. INFERRED:
   that needs `wasmtime_error_new` to fail, and the name given, "cancelled" or "deadline", is
   still true of the call. No change needed. The comment could say "on every path but
   `_stop_error`'s fail-safe" if the author wants it exact.

## The implementer's flags

1. **`ended=None` in `test_runner_async.py`'s fake call: acceptable.** READ: every real `_Call`
   sets `ended` in `__init__` (spec 015), and every other fake call in the unit suite already
   has it (`test_runner_async.py:31,125,227`; `test_runner_calls.py:131-135`). The check's
   assertions are unchanged. The change gives the fake the shape the runner reads. It does not
   make a failing behaviour pass. The runner was not bent to the fake. READ: the judge-changed
   line names the file, the landing notes give the reason, and the lane must accept with
   `--accept-judge` anyway. AGENTS.md rule 4 is kept. The Design list should name the file too,
   so the specification and the diff agree.
2. **The unit fake sets `ended` while its door runs: faithful.** READ: the callback sets `ended`
   inside `host_alloc`, which `_door`'s `frame` calls after `host` returns, and the error then
   leaves `_door`. Setting `ended` before the call would test the entry guard, not the except
   branch. The landing notes record the false start honestly.
3. **"while the guest runs" in the invariant comment: correct.** READ (`_drive`): it sets
   `ended = "cancelled"` only when the event is already set, and returns before instantiation.
   No host function can run then, so the branch cannot see that case.
4. **Evidence locations: acceptable, with one caution.** Citing the worktree's `build/030-*.log`
   follows 029's practice. Those logs are deleted with the worktree when 030 lands (§4.14), and
   the scratchpad is temporary. The durable record is the numbers written into the landing
   notes, which are there. I reproduced each of them.
5. **SIGINT on Windows: it breaks.** Finding 1.

## Each Decision against the code

1. **Holds** (READ the diff; EXECUTED). With `ended` set and a `Trap` or `WasmtimeError`, the
   branch calls `_epoch_now(caller)` and records nothing. Every other cause goes to `call.stop`.
   The type tuple is built once per `_shared`, by the same lazy import `_door` uses. Mutants
   M2, M3 and M4 are each killed. `extra_cases.txt`: a guest that catches the door's fault and
   computes on ends `cancelled`; a guest that calls the door in a loop makes `3` host calls, `0`
   after the cancel.
2. **Holds.** The guard reads `call.stopped is not None or call.ended is not None`, after the
   Ctrl-C check (M1 killed by the unit test).
3. **Holds.** The comment sits at the branch, states the invariant, names `ExitTrap`, and says to
   keep the test narrow. Finding 5 is a footnote to it.
4. **Holds.** EXECUTED: the line the guest prints after the door never appears (`stdout b''`);
   `exit_code` and `fuel_used` are `None` in every new case.

## Spec 015's order and spec 011's threads

- **Order (EXECUTED, `extra_cases.txt`, 3 of 3 each).** A host's `CancelledError` →
  `CancelledError`. A host that sets the cancel, waits past the window and raises
  `KeyboardInterrupt` → `KeyboardInterrupt`. Main thread, Ctrl-C and cancel both pending at
  `host_alloc` → `KeyboardInterrupt`. Plus `test_a_stop_holds_under_cancel` and the new Ctrl-C
  guard in every judge run. READ: `_epoch_answer` is untouched, and it checks a recorded stop,
  then Ctrl-C, then the cancel, then the deadline.
- **Threads (EXECUTED).** The four-thread case, two cancelled in the door and two ending by
  deadline under `cancel=`: `[(0, 'cancelled'), (1, 'deadline'), (2, 'cancelled'), (3,
  'deadline')]`, 3 of 3. READ: the change adds no shared state; `ended` is per call and the
  callback finds its call on its own thread's stack.

## Flakiness and hang risk

- **No time is asserted.** READ: `ticks(n)` polls `runner._epoch_ticker.count()` every 1 ms and
  returns on the count alone. The `+ 2` covers the engine running one round ahead of the count.
  READ (`_epoch_ticker._tick`): the ticker catches up in a burst after a stall, and `ticks`
  compares with `<`, so a burst cannot be missed.
- **The ticker cannot stand still while a case waits.** READ: the call holds `_epoch_ticker`'s
  context for its whole run, because every new case passes `cancel=`. So the ticker is active
  while the host blocks. If its thread died, the child would spin until `_child`'s 120 s
  fail-safe, and the check would fail, not hang. That fail-safe predates 030.
- **The cancel cases cannot deadlock.** READ: the host sets "started" before it waits, and the
  check thread sets the event only after "started".
- **The one wall-clock coupling** is the deadline case's 50 ms against guest start-up
  (finding 2). It can make the check vacuous; it cannot make it fail.
- EXECUTED: 6 of 6 selection runs, 48 of 48 children under load, and two full judges (mine and
  the implementer's) are all green.

## Acceptance criteria against evidence

1. **Met.** EXECUTED: both sizes give `cancelled None None b''` in every run (6 selection runs,
   24 children under load). Seen failing first: `before` fails both in 2 of 2 runs, and the
   implementer's 3 of 3 (`build/030-checks-before.log`).
2. **Met, with finding 2.** EXECUTED: `deadline None None b''` every run; fails on `before` 2 of
   2. The host counts `ceil(deadline_s / TICK_S) + 2` ticks from its own start; the call has a
   fuel cap and `cancel=` never set.
3. **Met on macOS and Linux. Fails on Windows** (finding 1). EXECUTED: `KeyboardInterrupt` in
   every run here, before and after the fix.
4. **Met.** EXECUTED: `6 passed`. The four cases the criterion names are there, plus `Trap` as a
   second cause and a live-call control. The patches follow the pre-build review's first builder
   note.
5. **Met.** EXECUTED: `test_run_with_cancel[busy|sleeping]`, `test_a_stop_holds_under_cancel`
   and `test_a_deadline_under_cancel_is_named` pass in every selection run.
6. **Met as far as a builder can go.** EXECUTED: exit 0, lost 0, grew 0, gained 4, judge changed
   (three files). The `--accept-judge` step is the lane's.

## Constitution checks

- **§4.4, §4.6:** untouched. The change is host-side only; no import, export or artifact changes.
- **§4.5 embedder-neutral:** holds. No embedder is named.
- **§4.9 tests count:** holds. The checks count ticks; nothing asserts a duration. Finding 2 is
  about coverage, not timing. `margin.py`'s milliseconds are a benchmark fact, kept out of the
  judge.
- **§4.10 evidence:** holds. Every number in the landing notes reproduced here.
- **§4.13 tooling:** uv only; ruff clean; no dependency added.
- **§4.14 git:** one commit on the spec branch, in its own worktree outside the repository.
- **§4.15 safe by default:** no limit loosens. A cancel or deadline in the door still ends the
  call; only its name changes.
- **§5.6 review:** the judge change (three files) is reviewed here. Finding 1 must be fixed
  before landing, because the release workflow is part of what a landing must keep green.
- **AGENTS.md rule 4:** not weakened. The fake's new field is a shape fix with a stated reason
  (flag 1).

## Disposition (filled in by the author, then confirmed by the reviewer)

## Verdict

Revise, then land. The runner change is right. It is small, it matches Decisions 1 to 4, it keeps
spec 015's order and spec 011's threads, and its checks were seen failing first and are stable.
But `test_ctrl_c_before_a_cancel_in_the_door` sends SIGINT with `os.kill`, which ends the
process on Windows, so the release's Windows verify job would fail (finding 1). Use
`signal.raise_signal` and install the default handler, as the existing Ctrl-C check does. Findings
2 to 4 are cheap and optional; finding 5 needs no change.

One line: the fix is right and its checks hold, but one new check kills itself on Windows; raise
the signal the way the file already does.
