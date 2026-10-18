# 030 — A cancel during a door call is named "cancelled"

- **Status:** drafted 2026-10-17; revised against its pre-build review
  (`../reviews/030-a-cancel-in-the-door-is-named-spec-2026-10-17.md`), whose confirmation passed
  it for build with no conditions (its three notes for the builder are in the review).
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`: the shared host function's except branch
  and its entry guard), judge checks in `tests/checks/test_v1_4_embedding.py`, `CHANGELOG.md`.
  Not build-class.
- **Depends on:** 003 (the door), 011 (a call's recorded stop), 015 (`cancel=`, the epoch
  callback, `call.ended`).
- **Research it stands on:** `../research/2026-10-17-a-tool-protocol-over-the-door.md`, finding 5
  (EXECUTED: `door_timing_probe.py` and its output beside the memo); the owner's decisions of
  2026-10-17 (`../decisions.md`, "12 and 14": the cancel defect is fixed before the tool protocol).

## The problem

A call made with `cancel=` whose event is set while the embedder's `host` blocks in a door call
ends with `trapped="error while executing at wasm backtrace:"`, not `"cancelled"`
(EXECUTED, the memo's table). A cancel set while the guest computes is named correctly.

Why (READ): under `cancel=`, the store's epoch deadline is at most `CANCEL_TICKS` ticks after the
epoch callback last ran. A host that blocks past that window leaves the deadline overdue. After
`host` returns, the door calls the guest's exported `host_alloc` to place the answer (`runner.py`,
`_door`'s `frame`), even for an empty answer. That is guest code, so the overdue epoch check fires
there; the epoch callback records `call.ended = "cancelled"` and returns
its error; `_door` re-raises it (`except (wt.Trap, wt.WasmtimeError): raise`); the shared host
function catches it and records it as the call's stop (`call.stop(caller, cause)`); and `_drive`
reads `call.stopped` before `call.ended`, so the run is named by the raw wasmtime error. The same
path is taken by a deadline that passes during a door call made with `cancel=` (EXECUTED by the
review: the raw error 10 times in 10). A host that sees the cancel and returns within the window
is named correctly today: its answer is written into the guest's memory, and the guest stops at
its next function entry before acting on it.

The tool protocol makes this common: a blocked tool is the usual place to cancel.

## Decisions

1. **The callback's own error is not a stop.** When the shared host function catches an
   exception while `call.ended` is already set, and that exception is a `wasmtime.Trap` or
   `wasmtime.WasmtimeError` (the error the epoch callback returned, surfacing through
   `host_alloc`), it does not record it in `call.stopped`. It sets the store's epoch deadline to
   0 (`_epoch_now(caller)`, the deadline half of `call.stop`), so the guest stops by the runner's
   own act at its next function entry, and returns its `stopped` code. `_drive` then names the
   run from `call.ended`, as it does for a cancel while computing. Any other exception (a host's
   own, a `KeyboardInterrupt`) is recorded as today, and a stop recorded before `call.ended`
   still holds (spec 015's order is unchanged).
2. **The entry guard covers an ended call.** The shared host function returns `stopped` before
   serving a call when `call.stopped` **or** `call.ended` is set, so no host function runs for a
   call the callback has ended.
3. **The invariant, written in the code.** `call.ended` is set only by the epoch callback, and
   only on a path that returns an error. So a `Trap` or `WasmtimeError` that the shared function
   catches after `ended` is set is that error. `ExitTrap` is a `WasmtimeError`, and it cannot occur
   there, because the callback's error aborts `host_alloc` first. A comment at the branch says
   this, so the guard is never widened by mistake.
4. **Nothing else changes.** When the deadline is overdue the door's answer is not delivered (the
   run ends inside the door, as today); `fuel_used` stays `None` for a cancelled run, as spec 015
   says; `exit_code` stays `None`.

## Intent

A cancel is named a cancel wherever the guest is when it lands.

## Design

```
src/wasi_python/runner.py              the shared host function's except branch and entry guard
tests/checks/test_v1_4_embedding.py    the checks below, in the existing CANCEL_RUN child
tests/unit/test_runner_cancel.py       the except branch with a fake call (no artifacts)
CHANGELOG.md                           0.1.0a4: Fixed
```

## Scope

In: the naming of a run whose cancel or deadline (under `cancel=`) lands during a door call. Out:
delivering the door's answer after a cancel; the tool protocol itself; any change to how a run
without `cancel=` meets its deadline (wasmtime's interrupt trap, already named `"deadline"`).

## Acceptance criteria

Checks run the guest in a child process like the existing `CANCEL_RUN` checks. Nothing measures
time: a host that must block past the callback's window polls `runner._epoch_ticker.count()` and
returns once it has advanced a number of ticks, never after a sleep or a timeout.

1. `test_a_cancel_during_a_door_call_is_named`: the host sets a "started" event; the check then
   sets the call's `cancel`; the host, once it sees the cancel, waits until the ticker has advanced
   `runner.CANCEL_TICKS + 2` from that moment, then returns. The run ends `trapped ==
   "cancelled"`, `exit_code is None`, `fuel_used is None`, and the guest's line after the door is
   not printed. Parametrized over an answer of 2 bytes and of 0 bytes. Seen failing first (the
   review: the raw error every run with `CANCEL_TICKS + 1`).
2. `test_a_deadline_during_a_door_call_under_cancel_is_named`: with `cancel=` given and never
   set, a fuel cap, and `deadline_s=0.05`, the host waits until the ticker has advanced
   `ceil(deadline_s / TICK_S) + 2` from its own start, then returns. The run ends `trapped ==
   "deadline"`, `exit_code is None`, `fuel_used is None`. Seen failing first.
3. `test_ctrl_c_before_a_cancel_in_the_door`: on the main thread, the host sends itself SIGINT,
   sets the cancel, waits past `CANCEL_TICKS` by count and returns; the call raises
   `KeyboardInterrupt` (spec 015: Ctrl-C before cancel). A guard: it passes today.
4. `tests/unit/test_runner_cancel.py`, with a fake call and no artifacts: with `ended` set and a
   `WasmtimeError` cause, `stopped` stays `None` and the deadline is set to 0; with `ended` set and
   a `KeyboardInterrupt` cause, it is recorded; with `ended` unset and a `WasmtimeError`, it is
   recorded; with `ended` set, the entry returns `stopped` and the host function is not called.
5. `test_a_stop_holds_under_cancel`, `test_a_deadline_under_cancel_is_named` and
   `test_run_with_cancel` still pass: a stop a host records (spec 011's, as in
   `test_a_stop_holds_under_cancel`) still wins over a later cancel.
6. `uv run pytest` green with `--accept-judge`; lost 0; grew 0.

## Landing notes

Not built.
