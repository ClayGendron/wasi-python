# Review of 030 — A cancel during a door call is named "cancelled" (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the constitution (§4.9, §5.2), `context/reviews/README.md`, the 015 pre-build review (for its format), the specification, the research memo's finding 5 and its probe (`context/research/2026-10-17-a-tool-protocol-over-the-door/door_timing_probe.py` and `.txt`), and the runner (`_instance`, `_drive`, `_Call`, `_shared`, `_epoch_now`, `_epoch_answer`, `_stop_error`, `_door`, `_trap_name`, `_fuel_used`, `_stop_at`, `_epoch_ticker`, `_deferred_ctrl_c`). I read the `CANCEL_RUN` child and its three checks in `tests/checks/test_v1_4_embedding.py`, and wasmtime 49's epoch libcall (`context/prior_art/wasmtime-v49/crates/wasmtime/src/runtime/vm/libcalls.rs:690-736`, `store.rs:2361-2373`). Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/030-a-cancel-in-the-door-is-named.md` as drafted (untracked), against the runner on `2af09e6`. The working tree holds other authors' uncommitted changes (`src/wasi_python/__init__.py`, spec 027's files). I read them for context only.
- **Ran (EXECUTED, darwin-arm64, host CPython from `uv run`, wasmtime-py 49, the artifacts in `build/artifacts/` read only; `scripts/build.sh` not run).** Nothing in `src/` or `tests/` was edited. The fix was prototyped in two scratch copies of the package. Scripts and outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/030-review/`:
  - `probe_rerun.txt`: the memo's probe, re-run with `uv run python -I <probe>` from the repo root.
  - `cases.py` → `today.txt`, `v1.txt`, `v2.txt`: the drafted checks and eight other cases, against today's runner and two prototypes.
    - `v1/`: Decision 1 exactly as worded (`v1.diff`): the `_shared` except branch skips `call.stop` when `call.ended` is set and the cause is a `Trap` or `WasmtimeError`.
    - `v2/`: the same, plus `_epoch_now(caller)` in that branch, and `_shared` returning `stopped` at entry when `call.ended` is set (`v2.diff`; finding 3).
  - `cancel_run.py` → `cancel_run_variants.txt`: the existing `CANCEL_RUN` child, all four cases, against both prototypes.
  - `cases_plain.py` → `plain_binary.txt`: the key cases on the plain binary (`snapshot=False`).
  - `ticked_deadline.txt`: criterion 2 rewritten to count ticks (finding 2).
  - `uv run pytest tests/checks/test_v1_4_embedding.py -k cancel -q`: 6 passed, ratchet lost 0 (today's runner).
  - I did not run the full `uv run pytest`: nothing is built.

## What holds

- **The defect is real and reproduces.** EXECUTED (`probe_rerun.txt`): identical to the memo's table. A deadline while the host blocks reads `"deadline"`. A cancel set while the host blocks reads `'error while executing at wasm backtrace:'`, for 2-byte and 0-byte answers. The control reads `"cancelled"`.
- **The diagnosis is right.** READ, then confirmed by the prototype:
  - `frame` calls the guest's `host_alloc` for every answer, even an empty one.
  - Under `cancel=`, the overdue epoch check fires there. `_epoch_answer` sets `call.ended = "cancelled"` and returns an error.
  - That error reaches Python as a `WasmtimeError` (spec 015's review, finding 3). `_door` re-raises it, and `_shared`'s except branch records it through `call.stop`.
  - `_drive` reads `call.stopped` first, so the run is named by the error's first line.
  - Changing only the except branch (v1) names every case correctly (`v1.txt`). So this is the whole path.
- **The deadline case in the spec is real.** EXECUTED (`today.txt`, `drafted_deadline`): with `cancel=` given and never set, `deadline_s=0.05`, and a host that blocks past it, today's runner reads `'error while executing at wasm backtrace:'` 6 times in 6 on the snapshot, and 2 in 2 on the plain binary (`plain_binary.txt`). Both prototypes read `"deadline"`. So the spec's INFERRED is now EXECUTED, and criterion 2's "if it passes today" branch does not arise.
- **Decision 1 is the right fix, and it is complete for the path it names.** EXECUTED on both prototypes (`v1.txt`, `v2.txt`, 2 runs each), and today for comparison:

  | case | today | v1, v2 |
  |---|---|---|
  | cancel set, host blocks past `CANCEL_TICKS`, 2 or 0 bytes | raw error | `cancelled`, `fuel_used None` |
  | deadline under `cancel=` passes while the host blocks | raw error | `deadline`, `fuel_used None` |
  | a host raises `CancelledError` (`test_a_stop_holds_under_cancel`) | `CancelledError` | `CancelledError` |
  | a host sets the cancel, then raises `ValueError` | `cancelled` | `cancelled` |
  | a host sets the cancel, waits past `CANCEL_TICKS`, raises `KeyboardInterrupt` | `KeyboardInterrupt` | `KeyboardInterrupt` |
  | main thread, deferred Ctrl-C and cancel both pending when `host_alloc` runs | `KeyboardInterrupt` | `KeyboardInterrupt` |
  | the guest catches the door's fault and computes on | raw error | `cancelled` |
  | the guest calls the door in a loop, catching faults | raw error, 0 host calls after cancel | `cancelled`, 0 host calls after cancel |
  | spec 011: four threads, two cancelled in the door, two ending by deadline | raw error ×2, `deadline` ×2 | `cancelled` ×2, `deadline` ×2 |

  `CANCEL_RUN`'s four cases (`busy`, `sleeping`, `stop`, `deadline`) give the expected lines on both prototypes (`cancel_run_variants.txt`).
- **The questions the brief asked, answered.**
  - **A host that raises.** READ: `_door` turns an `Exception` into `HOST_FAULT` before `host_alloc` runs, so no callback runs and `call.ended` stays unset. A `BaseException` (`KeyboardInterrupt`, `CancelledError`, `SystemExit`) escapes `_door`, also before `host_alloc`, so `call.ended` is unset and Decision 1 records it as today. EXECUTED: rows 3–5.
  - **Ctrl-C deferred.** READ: `_epoch_answer` checks Ctrl-C before the cancel. Its Ctrl-C branch records `call.stopped = KeyboardInterrupt()` and does not set `call.ended`. So the error that surfaces from `host_alloc` meets Decision 1's guard with `ended` unset, and `call.stop` keeps the first cause. EXECUTED: row 6 raises `KeyboardInterrupt`.
  - **Spec 015's order.** It is unchanged. `call.ended` is set only on paths where `call.stopped` was `None` when the callback ran, and the callback checks a recorded stop first. So "a recorded stop holds, then Ctrl-C, then cancel, then deadline" still holds.
  - **A guest exit inside `host_alloc`.** READ: `ExitTrap` is a subclass of `WasmtimeError` (EXECUTED: its MRO). So Decision 1's type test would cover an exit too. That is harmless: a callback that sets `ended` returns an error at once, so `host_alloc` is aborted by that error and cannot also exit in the same door call. An exit with `ended` unset is recorded as today. See finding 4 for the sentence the spec should carry.
  - **`_epoch_now` after the door.** READ: it runs only after a normal answer, in `_shared`'s `try`. It sets the deadline to 0. The callback then fires at the guest's next function entry, which is outside every host function, because the door has returned. Its error unwinds the whole guest to `exports["run"]`, never through `_shared`. So `_epoch_now` cannot make `call.ended` set while `_shared` catches a different, real error. INFERRED: the only remaining window is a second shared call before any function entry, which finding 3 closes.
  - **Threads (spec 011).** READ: `call.ended` is per call, the callback runs on the guest's own thread and finds its call on that thread's stack, and the fix adds no shared state. EXECUTED: the four-thread row.

## Acceptance criteria against evidence

1. `test_a_cancel_during_a_door_call_is_named`, "seen failing first with today's runner": not met as drafted. The check passes on today's runner 40 times in 40 (finding 1).
2. `test_a_deadline_during_a_door_call_under_cancel_is_named`: the case is real and fails today (EXECUTED). But its host waits on a timeout, which is a sleep (finding 2).
3. The three existing cancel checks still pass: EXECUTED on both prototypes, through the same child script.
4. `uv run pytest` green with `--accept-judge`, lost 0, grew 0: right. The new checks change the judge.

## Findings, most severe first

1. **Criterion 1's check, as drafted, does not fail first.** High. It would land a guard that never saw the defect.
   - EXECUTED (`today.txt`, `drafted_cancel`, 20 runs × 2 sizes): the host sets "started", the check sets the cancel, the host returns at once. Today's runner names all 40 runs `"cancelled"`, with `fuel_used None` and empty stdout.
   - READ, why: the defect needs the store's epoch deadline to have passed while the host blocks. Under `cancel=`, the deadline is at most `CANCEL_TICKS` (5) ticks after the last callback, about 50 ms. A host that returns within that window runs `host_alloc` with no callback. The answer is written, the door returns 0, and `_shared`'s `_epoch_now` names the run correctly at the guest's next entry. `CANCEL_RUN`'s `sets` host is already this case, and it passes. INFERRED: the drafted check fails only when a door call happens to start near the end of a 5-tick window. That is rare and depends on timing.
   - The Problem section has the same gap. "The overdue epoch check" is overdue only once up to `CANCEL_TICKS` ticks have passed in the door. A cancel that a host sees and answers at once is already named correctly today, and in that case the answer is written into the guest's memory before it stops. Say both, and correct Decision 2's "the door's answer is never delivered". It is not delivered in the overdue case. In the other case it is written, but the guest stops before it acts on it.
   - Fix: make the host block past the window by counting ticks, not by sleeping. After the cancel is set, the host polls `runner._epoch_ticker.count()` until it has advanced `runner.CANCEL_TICKS + 2` from when the host saw the cancel, then returns. The `+ 2` covers the engine running one round ahead of the count (`_stop_at`'s docstring), with one to spare. The outcome then depends only on counts. EXECUTED (`ticked_cancel`, which waited `CANCEL_TICKS + 1`, one less than recommended): today's runner reads the raw error 6 times in 6 on the snapshot, and 2 in 2 on the plain binary. Both prototypes read `"cancelled"` every time. Checks already reach into `runner` (`_outputs`, `_fork`, `_check_preopens`), so this is in keeping.
2. **Criterion 2 waits on a timeout, which is a sleep.** Medium-low.
   - As drafted, the host waits on an event that is set only after the call returns, so every run waits the full timeout. The result rests on the ticker reaching the deadline inside that wall-clock window. The spec's own preamble says "never on a sleep", and §4.9 asks for counts.
   - Fix: the same count. The host waits until the ticker has advanced `ceil(deadline_s / TICK_S) + 2` from its own start, then returns. That is past `stop_at`, whatever the phase. EXECUTED (`ticked_deadline.txt`, `deadline_s=0.05`, 5 runs × 2 sizes): today's runner reads the raw error 10 times in 10; v2 reads `"deadline"` 10 times in 10.
   - Assert `fuel_used is None` under a fuel cap and `exit_code is None`, as `test_a_deadline_under_cancel_is_named` does.
   - Since the case fails today (EXECUTED above), drop the "if it passes today" branch. Say "seen failing first", and cite this review in the landing notes.
3. **Decision 1 drops the stop half of `call.stop`, and the reason it gives is not the mechanism.** Low-medium. The outcome is right today, but it rests on an unstated wasmtime detail.
   - "It returns its `stopped` code as today, so the guest still stops" is not why the guest stops. `HOST_FAULT` is a value the guest's Python sees as a door error and can catch. Today the guest stops because `call.stop` sets the epoch deadline to 0. Decision 1 skips `call.stop`.
   - READ (`libcalls.rs:700-735`): when the callback returns an error, wasmtime leaves the store's deadline where it was, which is already past. So the next function entry calls the callback again, and it stops the guest by the same name. EXECUTED (`v1.txt`): a guest that catches the fault and computes on still ends `"cancelled"`, and a guest that calls the door in a loop makes no further host call.
   - Today `call.stopped` also makes later shared calls return `stopped` before the host runs. Under Decision 1, `call.stopped` stays `None`, so that guard no longer covers this call. INFERRED: only a shared call made before any function entry could slip through, which the real guest does not do (EXECUTED: 0 host calls after the cancel).
   - Fix, both cheap: in that branch call `_epoch_now(caller)` (the deadline half of `call.stop`, without recording the cause), and make `_shared`'s entry test `call.stopped is not None or call.ended is not None`. Then the guest stops by the runner's own act, not by wasmtime's choice. EXECUTED (`v2.txt`): every row as v1.
4. **State the invariant Decision 1 relies on, and name `ExitTrap`.** Low.
   - Write: "`call.ended` is set only by the epoch callback, and only on a path that returns an error. So a `Trap` or `WasmtimeError` that `_shared` catches after `ended` is set is that error. `ExitTrap` is a `WasmtimeError`, and it cannot occur there, because the callback's error aborts `host_alloc` first."
   - Then a later reader cannot widen the guard by mistake.
5. **The Kind line leaves a choice open.** Low. "The shared host function's stop, or `_drive`'s naming" reads as undecided (§5.2), but Decision 1 and Design pick `_shared`. Drop "or `_drive`'s naming". INFERRED: the `_drive` alternative would also work, but it would leave a raw cause recorded on the call, and today's `call.stopped` guard would then be the only reason later shared calls refuse.
6. **Two small checks would hold the order without artifacts, or under Ctrl-C.** Low, optional.
   - A unit test of `_shared`'s except branch with a fake call. With `ended` set and a `WasmtimeError` cause, `stopped` stays `None` and the deadline is set to 0. With `ended` set and a `KeyboardInterrupt` cause, it is recorded. With `ended` unset and a `WasmtimeError`, it is recorded. This runs on a machine without artifacts.
   - A v1.4 case in `CANCEL_RUN`: on the main thread, the host sends itself SIGINT, sets the cancel, waits past `CANCEL_TICKS` by count, and returns. The call raises `KeyboardInterrupt` (spec 015: Ctrl-C before cancel). EXECUTED (`ctrl_c_blocked`): it does, today and on both prototypes.

## Constitution checks

- §4.4 two imports, §4.6 artifacts: untouched. The change is on the host side only.
- §4.5 embedder-neutral: holds. No embedder is named.
- §4.9 tests count: criterion 1 counts, but as drafted it does not exercise the defect (finding 1). Criterion 2 waits on a timeout (finding 2). Counting ticks fixes both.
- §4.10 evidence: the memo's table reproduces (`probe_rerun.txt`). The spec's INFERRED deadline case is now EXECUTED.
- §4.13 tooling: no new dependency.
- §4.15 safe by default: no limit loosens. A deadline under `cancel=` still ends the call. Only its name changes.
- §5.2 no open questions: the Kind line's "or" (finding 5).
- §7 never-do list: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. **Accepted.** Criterion 1's host now waits `CANCEL_TICKS + 2` ticks by count after it sees the cancel. The Problem section says when the deadline is overdue, and that an answer given inside the window is written but not acted on. Decision 4 (was 2) says "when the deadline is overdue".
2. **Accepted.** Criterion 2 counts `ceil(deadline_s / TICK_S) + 2` ticks, asserts `exit_code is None` and `fuel_used is None` under a fuel cap, and is "seen failing first"; the Problem section cites this review's EXECUTED result.
3. **Accepted.** Decision 1 calls `_epoch_now(caller)`; new Decision 2 makes the entry guard test `call.stopped` or `call.ended`.
4. **Accepted.** New Decision 3 states the invariant, `ExitTrap` named, as a comment at the branch.
5. **Accepted.** The Kind line names the except branch and the entry guard only.
6. **Accepted.** Criterion 3 (Ctrl-C before a cancel in the door) and criterion 4 (the unit test of the except branch and the entry guard, no artifacts).

## Verdict

Build after a small revision. The diagnosis is right, and Decision 1 fixes every path I tried without disturbing spec 015's order: a recorded stop, then Ctrl-C, then cancel, then deadline. But criterion 1's check, as drafted, passes on today's runner, so it would never be seen failing (finding 1). Make both new checks count ticks instead of returning at once or waiting on a timeout (findings 1 and 2). Keep the deadline half of the stop and the entry guard (finding 3). Findings 4–6 are text and optional tests.

One line: the fix is right, but the check must hold the host in the door for more than `CANCEL_TICKS` ticks, counted, or it never meets the defect it guards.

## Confirmation (2026-10-17)

- **Reviewer:** the same fresh agent that wrote the review above (Claude Opus 5.5), not the author. I read the revised specification and the disposition. I edited nothing but this section.
- **Re-ran (EXECUTED, same machine and artifacts, read only).** The counted variants, as the revision now states them, ran 5 times × 2 answer sizes on today's runner and on the v2 prototype (Decision 1 with `_epoch_now`, and the entry guard). Output: `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/030-review/confirm.txt`.

  | check (as revised) | today | v2 |
  |---|---|---|
  | criterion 1: the host waits `CANCEL_TICKS + 2` counted ticks after the cancel | raw error 10/10 | `cancelled` 10/10, `fuel_used None`, stdout empty |
  | criterion 2: `deadline_s=0.05`, fuel cap, the host waits `ceil(0.05/TICK_S) + 2` ticks | raw error 10/10 | `deadline` 10/10, `fuel_used None` |
  | criterion 3: SIGINT on the main thread, cancel set, past `CANCEL_TICKS` by count | `KeyboardInterrupt` 5/5 | `KeyboardInterrupt` 5/5 |

  So criteria 1 and 2 are seen failing first and pass with the fix. Criterion 3 is a guard that passes both ways, as the specification says.

### Each finding

1. Confirmed. Criterion 1 counts `CANCEL_TICKS + 2` ticks. The Problem section states the window, and says what happens to an answer given inside it. Decision 4 is limited to the overdue case.
2. Confirmed. Criterion 2 counts ticks, asserts `exit_code is None` and `fuel_used is None` under a fuel cap, and is "seen failing first". The preamble now forbids a sleep or a timeout.
3. Confirmed. Decision 1 sets the deadline to 0 through `_epoch_now(caller)`, and Decision 2 adds the entry guard. Both are what v2 ran.
4. Confirmed. Decision 3 states the invariant and names `ExitTrap`, as a comment at the branch.
5. Confirmed. The Kind line names only the except branch and the entry guard.
6. Confirmed. Criteria 3 and 4 add the Ctrl-C guard and the unit test without artifacts.

### Notes for the builder (not conditions)

- Criterion 4's unit test cannot hand `_shared` a fake caller as it stands. `_context_address` and `_epoch_now` both reach wasmtime's `_ffi` through `caller._context()`. Monkeypatch those two module functions, and push the fake call on `_stack()`. Observe "the deadline is set to 0" as a call to the patched `_epoch_now`.
- `wasmtime.WasmtimeError("x")` and `wasmtime.Trap("y")` can be built directly in Python (EXECUTED), so the unit test needs no store.
- `_shared` checks Ctrl-C before its entry guard. So a call with `ended` set and a Ctrl-C pending records `KeyboardInterrupt`. That follows spec 015's order. Do not move the guard above that check.

### Verdict

Confirmed for build, with no remaining conditions.

One line: the revision makes both new checks meet the defect by counting ticks, keeps the runner's own stop, and was seen failing first and passing on the prototype.
