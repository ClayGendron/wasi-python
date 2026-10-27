# 144: A session is always ended

- **Status:** drafted 2026-10-27 from `../research/2026-10-27-a-code-review-of-the-runner-for-production-use.md` (§2); not yet built. It waits for the owner's instruction to build.
- **Date:** 2026-10-27
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, **not structural**: `src/wasi_python/runner.py` (`Session._claim`, `_release_claim`, `run_async`, `close`, `_stop_async_calls`; 1,213 of 1,500 lines, about 40 added), `src/wasi_python/_sessions.py` (`_session_turn`, `_start_closer`, `_end_dropped`, `_abandon_turn`, `_sessions_at_exit`; 1,091 lines, about 40 added), `src/wasi_python/_outputs.py` (`_write_output`; 370 lines, two lines), rows in `tests/unit/test_runner_sessions.py`, `tests/unit/test_runner_async.py` and `tests/unit/test_runner_outputs.py`, one paragraph in `docs/how-to/sessions.md`. No new lock, no new module-level state, no platform branch, no seam off the process object; every lock taken is a leaf or a pair the lock order already names. No change to `tests/public_api.txt`.
- **Depends on:** nothing in flight. Landed and unchanged: the session phase table and its invariants (055, 082), `run_async` and the runner's pool (015, 053), the reaper and the closers (055).
- **Research it stands on:** `../research/2026-10-27-a-code-review-of-the-runner-for-production-use.md`, §2 (High 1, High 2, Medium 1, Medium 2, Medium 3 and the two Low rows); the researcher re-read High 1 and High 2 against the code.

## The problem

A session's phase table (`_sessions.py:115-128`) and its invariants (`_sessions.py:196-216`) say that `holder` is the turn's thread while a turn runs, and that a marked session is ended by whoever marks it or by a closer. Five paths break that promise, all under `Session.run_async` or at exit (READ, the memo's §2).

- `run_async` claims on the event-loop thread (`runner.py:1145`), so `holder` is that thread, while the turn runs on a worker (`_session_turn`, `_sessions.py:858`), which never rebinds it. A `close()` from a tool or a host function, which runs on the worker, finds `holder != me` at `runner.py:1205` and waits on `done` (`runner.py:1213`) for a turn that cannot return until the tool does: a deadlock. The docstring promises `Session.run`'s behaviour, which holds there alone.
- A queued turn cancelled after a concurrent `close()` moves STOPPING to MARKED (`_sessions.py:123`), and nothing ends a MARKED session: the reaper and `_end_dropped` act on OPEN alone (`_sessions.py:347`, `:395`), and `_claim` raises `SessionEnded` without ending it. The `close()` caller waits until exit; the store and the pipe reader thread stay. The path through `_submit` raising (`runner.py:1157-1160`) is the same hole.
- A closer thread that fails to start (`thread.start()` at `_sessions.py:319`, outside the lock) leaves the ending claimed by `_CLOSER` and the phase ENDING; the reaper swallows the exception (`_sessions.py:388`) and skips ENDING ever after; `close()` and exit wait without bound.
- At exit, `_stop_async_calls` cancels queued futures (`runner.py:541`) and the coroutine never resumes to `_release_claim`; `_sessions_at_exit` then waits on `done` (`_sessions.py:434`) for a turn that never ran.
- `_abandon_turn` (`_sessions.py:914-922`) leaves a session MARKED at the guest thread's end, and a dropped `Session` then gets no ending.

Two Low rows ride along: `_write_output` drops bytes without setting `dropped` (`_outputs.py:300-306`), and `process().pools` grows by one pool at every `set_defaults` resize (`runner.py:507`).

## Decisions

### 1. The thread that runs a turn is its holder

`_session_turn` rebinds `state.holder` to its own thread under `state.lock` as its first step, through a new event `TAKE_TURN` in the phase table, allowed from TURN and from STOPPING (a `close()` may have come between the claim and the start) and leaving the phase as it is. Invariant 2 then holds as written. A `close()` from the turn's home thread returns at once, as it does for `Session.run`; a `close()` from the loop thread or any other waits for the ending, as the docstring promises. Reason: the invariant is the right one, and the claim is the only place it was broken; rebinding at the start of the turn is one assignment under the lock the invariant names.

### 2. A session that is marked and held by no one gets a closer

Every path that leaves a session MARKED with no thread about to end it claims the ending for `_CLOSER` and starts a closer, under the same lock-then-start shape `_reap` uses: `_release_claim` when it moves STOPPING to MARKED, the `_submit`-raises path through it, and `_abandon_turn`. `_end_dropped` and `_reap` also act on MARKED when no ending is claimed, so a session that reaches MARKED by any path not listed here is still ended by the next tick or the next drop. Reason: the table already names the STOPPING-to-MARKED move; what was missing is the rule that MARKED is never a resting state for a session nobody holds. The abandoned turn's session ends through the same closer, with the ending deciding whether to run shutdown from the session's recorded end, as it does today for a stopped turn.

### 3. A closer that cannot start runs where it was started

`_start_closer` wraps `thread.start()`; on any exception it runs `_end_quietly` on the calling thread and returns, so the ending always runs and the phase always reaches ENDED. For the reaper this blocks its loop for at most one ending's `shutdown_s`; for `_claim(here=False)` and `_end_dropped` it blocks the caller the same way. Reason: a thread that cannot start is a host under pressure, and under pressure the one thing the runner may not do is lose an ending; a retry on the next tick would need a new state to remember, and an ending run inline needs none.

### 4. A claim whose turn never started is released by whoever cancelled it

`run_async` registers, beside the event in `process().live`, the release of its claim (a bound method of the session), and `_stop_async_calls` runs each release for a future its cancel refused to start. The coroutine's own cancel path (`runner.py:1166-1167`) keeps its release and the registration is removed when the turn starts or the await returns, so a release runs once. Reason: the claim belongs to the turn, and the turn's cancellation is the one event the coroutine cannot see at exit.

### 5. The two Low rows

`_write_output` sets the stream's `dropped` before it returns `size` on a failure, when it reached the stream. `_pool` shuts down and removes a replaced pool from `process().pools` once its futures are done, instead of keeping every pool ever made. Reason: each is one line, in a file this specification touches, and each is a truth the result or the exit hook reads.

### 6. The rows first

- `tests/unit/test_runner_sessions.py`: a `close()` from a tool during a `run_async` turn returns at once and the session ends when the turn returns (red today: a deadlock, bounded by the row's own deadline); a `close()` from the loop thread during a `run_async` turn waits for the ending and `shutdown_outcome` is set when it returns (red today: it returns at once); a queued turn cancelled after a concurrent `close()` ends the session and `close()` returns (red today); a closer whose `thread.start()` raises, through a seam on `process().observers.start_ending`, still ends the session and `close()` returns (red today); an abandoned turn's session, dropped, is ended by the reaper (red today).
- `tests/unit/test_runner_async.py`: a program that exits with a `run_async` turn still queued in a busy pool exits, with the session ended "closed" (red today, bounded by the row's deadline).
- `tests/unit/test_runner_outputs.py`: a stream whose write raises reports `dropped` (red today).
- Every row counts operations and uses the stepped clock; the bound on a row that would hang is pytest's own timeout, not a measurement.

## Intent

After this specification, every session reaches ENDED by exactly one ending, whoever claimed its turn, whichever thread calls `close()`, and whether the turn ran, was cancelled before it started, was abandoned, or was still queued at exit. An embedder that runs many sessions from async code and closes them from tools or from other tasks never waits on a session that nobody will end.

## Design

- `src/wasi_python/_sessions.py`: `TAKE_TURN` in `_SESSION_TABLE` and `_HOLDER_EVENTS` (Decision 1); `_session_turn` takes it first; `_start_closer` runs the ending inline on a failed start (Decision 3); `_reap`, `_end_dropped` and `_abandon_turn` claim and start a closer for a MARKED session nobody holds (Decision 2); the invariants' docstring gains one line for MARKED.
- `src/wasi_python/runner.py`: `_release_claim` starts a closer when it lands on MARKED (Decision 2); `run_async` registers its release beside its event and `_stop_async_calls` runs it for a cancelled queued turn (Decision 4); `_pool` prunes the pools (Decision 5); `close`'s docstring says which thread waits.
- `src/wasi_python/_outputs.py`: `_write_output` sets `dropped` (Decision 5).
- `docs/how-to/sessions.md`: one paragraph, that `close()` from inside a turn's tool returns at once and the session ends as the turn returns, from anywhere else it waits for the ending.
- The news file `../changes/144-a-session-is-always-ended.md`: under Fixed, "A session is always ended: a `close()` from a tool during a `run_async` turn no longer deadlocks, a queued turn cancelled after a `close()` is ended by a closer, a closer that cannot start runs where it was started, and a turn still queued at exit releases its claim."
- The commits, in order: the rows seen failing; the holder and the closers; the exit release; the two Low rows; the docs and the news file.

## Scope

In: the above. Out:

- a cancellable tool thread, or any change to how an abandoned tool is counted: specification 146;
- a benchmark of many sessions at once (the reader threads, the stack-size lock, the reaper's scan): a research memo first, as the memo's §6 says;
- the duplication of `_instance` and `_open_session`: a structural specification of its own;
- any change to `Defaults`, `Session`'s signature or `tests/public_api.txt`.

## Acceptance criteria

1. The seven rows of Decision 6 exist and were seen failing before the change, each named with its failing output in the pull request.
2. `uv run pytest tests/unit/test_runner_sessions.py tests/unit/test_runner_async.py tests/unit/test_runner_outputs.py` is green on Linux, macOS and Windows in the pull request's run.
3. The fast tier and the pull request's shards lose no accepted pass, and the session rows of `tests/checks/test_v1_4_embedding.py` keep their fuel within the ratchet's tolerance.
4. `_sessions.py`'s invariants docstring names MARKED as a state no session rests in while nobody holds it, and every path the problem lists is either covered by a row or named in the landing notes as untestable with the reason.
5. No new lock, no new module-level state outside `_process.py`, and `tests/checks/test_rules.py` stays green.
6. The news file exists and `ci-status` is green.

## Landing notes

Not yet built.
