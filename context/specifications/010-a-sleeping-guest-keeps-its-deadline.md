# 010 — A sleeping guest keeps its deadline

- **Status:** landed, 2026-10-17. Reviewed before build
  (`../reviews/010-a-sleeping-guest-keeps-its-deadline-spec-2026-10-17.md`) and after
  (`../reviews/010-a-sleeping-guest-keeps-its-deadline-2026-10-17.md`).
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`), judge additions in `tests/`, `README.md`,
  `CHANGELOG.md`.
- **Depends on:** 006 (the default deadline), 008 (the runner as it stands).
- **Research it stands on:** spec 009's pre-build review
  (`../reviews/009-release-security-spec-2026-10-17.md`, finding 1, EXECUTED): with a 1 s
  deadline, `time.sleep(15)` held `run` for 15.0 s. The author reproduced it (EXECUTED:
  `time.sleep(5)` and `select.select([], [], [], 5)` under a 1 s deadline each returned after
  about 5 s, `trapped == "deadline"`) and prototyped the fix below on the real snapshot
  (EXECUTED: the 5 s sleep and the 5 s `select` ended at 1.00 s; `time.sleep(0.2)`, five 0.05 s
  sleeps and a 0.3 s sleep timed with `time.monotonic()` behaved as native; scratch
  `sleep/proto.py`).

## The defect

wasmtime's deadline is an epoch interrupt: it is checked only while guest code runs. A guest that
asks to wait (`time.sleep`, `select` with a timeout; both become one WASI call, `poll_oneoff`,
with a clock subscription) blocks inside wasmtime's own `poll_oneoff` for as long as it asked,
and the interrupt fires only when the call returns. So a call that names no limit, or a deadline,
can be held for as long as the guest likes, which defeats spec 006's default ("a call that names
no limit still has one for time"). Fuel does not help: no instruction runs while it waits.

## Decisions

1. **The runner answers `poll_oneoff`, and only that.** It shadows
   `wasi_snapshot_preview1::poll_oneoff` with the linker's shadowing, as the judge's driver
   shadows two calls. wasmtime's own functions cannot be called from the new one: wasmtime-py
   calls a WASI function without the guest's memory ("missing required memory export";
   EXECUTED, scratch `sleep/delegate.py`). `clock_time_get` is not shadowed: answering it from
   Python costs 13 µs a read against 0.23 µs (57 times), and the first design's host clock leaked
   the host's uptime as the guest's monotonic clock (the review, EXECUTED). The new function
   follows wasmtime 49's `poll_oneoff` (READ, `crates/wasi/src/p1.rs`):
   - **Bounds.** Pointers and counts are unsigned 32-bit (masked). Zero subscriptions answer
     `EINVAL`; more than `MAX_SUBSCRIPTIONS` (4,096) answer `ENOMEM`, so one call's host work is
     bounded (the review measured 0.16 s for one call at 50,000 descriptors, EXECUTED). The
     subscriptions (48 bytes each), the events (32 bytes each) and the event count must lie
     inside guest memory, or the call answers `EFAULT` (where wasmtime-py traps; the build review,
     EXECUTED; the runner's answer is the safer one). Subscriptions are read in one pass with
     `struct.iter_unpack`. An unknown tag answers `EINVAL`. The cap is a stated limit: `select`
     (at most 1,024 descriptors, so at most 2,049 subscriptions) is unaffected, but
     `select.poll()` with more than 2,047 descriptors (its default mask, two subscriptions a
     descriptor; 4,095 with `POLLIN` alone) answers `ENOMEM` where wasmtime works.
   - **Descriptors.** wasmtime fails the whole call with `EBADF` for a descriptor it cannot
     poll; the runner does the same for the descriptors it knows: stdin (0) for writing,
     stdout and stderr (1, 2) for reading, and the preopened root (3). Any other descriptor
     subscription is reported ready (error 0, `nbytes` 1, no flags), as wasmtime reports a file.
     The differences from wasmtime, all about the guest's own descriptors and none reaching the
     host (the confirmation, EXECUTED), are documented: a directory the guest opens, and a
     descriptor that is not open, are reported ready where wasmtime answers `EBADF` (the guest's
     next read or write on it answers `EBADF`); a file the guest opens can take a number 0 to 3
     that it closed (the guest has no `dup2`, but a closed number is reused), and the fixed rule
     then answers `EBADF` for it; no hang-up flag is set at the end of a file. A call with any descriptor
     subscription answers at once, with the descriptor events only, as wasmtime does when a
     descriptor is ready.
   - **Clocks.** A subscription on a clock other than realtime (0) or monotonic (1) answers
     `EINVAL`, as wasmtime does. A relative wait is its timeout. An absolute realtime wait is the
     target minus `time.time_ns()`, floored at 0. An absolute monotonic wait is the target minus
     the guest's monotonic clock, which the runner estimates as `time.perf_counter_ns()` minus
     its value just after `wt.WasiConfig()` is created (wasmtime fixes its monotonic origin
     there; the confirmation, EXECUTED: within 0.02 ms, where an origin taken after `set_wasi`
     made every sleep 0.63 ms too long, 61 ms with 64 MiB of stdin). The estimate's
     origin is taken after wasmtime's, so it reads low and a wait can only come out longer than
     asked, never shorter. The call waits for the shortest subscription and writes a clock event
     (error 0, `nbytes` 0) for every clock due by then, as wasmtime does (the build review:
     wasmtime 49's path writes `nbytes` 0 and reports every due clock; the first build wrote 1 and
     reported one). A wait the host's `time.sleep` cannot represent (about 292 years) with no
     deadline answers `EINVAL` through the catch-all, where wasmtime would wait.
   - **Nothing escapes.** The body is wrapped: any Python exception answers `EINVAL` (and a
     `KeyboardInterrupt` is let through, so Ctrl-C still ends the call; the store is still closed
     and a private root removed, spec 006). That one exception still travels by wasmtime-py's
     process-wide `LAST_EXCEPTION`, so in a rare race another thread's call could receive it;
     Ctrl-C ends the process's work anyway.
2. **The deadline ends a wait without an exception.** Raising from the host function would carry
   the exception through wasmtime-py's process-wide `LAST_EXCEPTION`, where a concurrent call can
   take it (the review, EXECUTED: 3,489 of 7,986 traps crossed threads). Instead the wait loop
   sleeps in slices of at most `TICK_S` and stops when the requested wait is over or when the
   epoch ticker has advanced past the store's deadline (the ticker counts its increments; the
   runner records the count at which the store's deadline falls when it sets it). Precisely: the
   ticker updates its count after it advances the engines; the runner reads the count `c0` after
   `set_epoch_deadline(ticks)`; the wait stops once the count is at least `c0 + ticks + 1`, so it
   never answers before the epoch has passed the deadline (`_stop_at`). One exception, INFERRED
   in the build review: the ticker copies its engine list once a round, so for the round in which
   a new engine first joins, the count can run one round ahead of that engine, and a wait can end
   up to a tick early; the guest then runs on and traps at the epoch, so no wait escapes the
   deadline. It then answers
   the clock event normally, and the guest traps at its next epoch check, so the call reports
   `trapped == "deadline"` as for any other overrun (the review, EXECUTED: 0.22 s on a 0.2 s
   deadline, and nothing after the wait ran). With `deadline_s=None` a wait is one sleep of its
   full length, not sliced: a guest can then wait as long as it asks, and a fuel cap does not stop
   it (no instruction runs while it waits); the README says so. The deadline is counted from the
   moment the epoch ticker starts for the call, just before instantiation.
3. **The waiting is injectable for the judge.** The wait logic is a small class taking `now`,
   `sleep` and `deadline_passed` functions; the runner passes the real ones. A unit test passes
   fakes and counts what the class asks to sleep, so the bound is checked without measuring time
   (constitution §4.9).
4. **Checks.** Unit tests of Decision 3 (a one-hour wait under a deadline that passes after 50
   slices asks for at most 50 slices of `TICK_S`; a 0.2 s wait with no deadline asks for one
   sleep of 0.2 s; an absolute wait in the past asks for nothing) and of Decision 1's parsing
   (zero subscriptions, too many, out-of-bounds pointers, an unknown tag, a CPU-time clock, each
   descriptor rule) on hand-built subscription bytes; the wrapper's pointer bounds, masking, cap,
   catch-all and clock origin are tested through a one-page WAT module, and `_stop_at` pins the
   `+ 1`, with the clocks injected (added after the build review). Two things stay READ only: the
   origin is taken right after `wt.WasiConfig()`, and the ticker updates its count after the
   engines; neither can be checked without measuring time. A v1.2 check,
   `test_a_sleeping_guest_ends_at_its_deadline`, runs `time.sleep(10**6)`,
   `select.select([], [], [], 10**6)` and a loop of `time.sleep(0)` under `deadline_s=0.2` and
   asserts `trapped == "deadline"`; it runs each call in a thread and, as a fail-safe and not a
   timing, fails if the thread (a daemon, so a stuck call cannot keep the test process alive)
   has not returned after 120 s (without the fix the call would wait
   11.6 days; §4.9 forbids measuring time, not refusing to wait forever). The spec 006 check
   `test_a_trapped_call_without_a_root_is_removed` gains a sleeping case, under the same
   fail-safe (the build review saw it hang without one); its accepted id is retired for the
   `[busy]` and `[sleeping]` ids. A v1.4 check runs
   `time.sleep(0.05)` with no deadline and asserts exit 0 and the output after it, so ordinary
   sleeps still work.
5. **What it costs.** One Python call per `poll_oneoff`, bounded by `MAX_SUBSCRIPTIONS`; clock
   reads are untouched. The judge's driver does not change: it has no deadline, and it answers
   the CPU-time clocks in `clock_time_get` itself, which this specification does not touch.

## Intent

A call's deadline holds whatever the guest does, waiting included, so the default time limit is
a limit.

## Design

```
src/wasi_python/runner.py     _Waits (now, sleep, deadline_passed); the shadowed poll_oneoff;
                              the ticker's count
tests/unit/test_runner_waits.py   the injectable class, with fakes
tests/checks/…                the sleeping-guest check (v1.2); an ordinary sleep (v1.4)
README.md, CHANGELOG.md
```

## Scope

In: the above. Out: `asyncio`, which fails in the guest for another reason (it needs a
socketpair; EXECUTED: `asyncio.run` of a coroutine that sleeps exits 1); its own research.

## Acceptance criteria

1. The unit test and the v1.2 check exist; the unit test was seen failing against a class that
   does not check the deadline.
2. `uv run pytest` is green with `--accept-judge`.
3. A dry run of the release workflow passes every job.

## Landing notes

Built 2026-10-17 by the author agent (local commit `f5cf8bb`); reviewed in
`../reviews/010-a-sleeping-guest-keeps-its-deadline-2026-10-17.md`. Its fixes: the trapped-call
check's sleeping case runs under the 120 s fail-safe (EXECUTED: without the shadow it now fails
after 120.25 s, where it hung); the wrapper is tested through a one-page WAT module and
`_stop_at` is a function (EXECUTED: six mutations the review saw survive, namely no `EFAULT`
bounds, no mask, a narrowed catch-all, a cap of 5,000, `stop_at` off by two and the origin
ignored, each now fail a unit test); clock events carry `nbytes` 0 and every due clock is
reported, as wasmtime does; the text states the differences from wasmtime. The concurrency
defect the review found in wasmtime-py's host-function table (finding 1, not introduced here)
is specification 011.

**Seen failing first** (EXECUTED): the eight unit tests of `tests/unit/test_runner_waits.py`
failed before the runner had `_Waits` and `_poll_plan`; `test_a_sleeping_guest_ends_at_its_deadline[sleep]`
failed through its fail-safe ("the call did not return", after 120 s).

**After the change** (EXECUTED): all pass, with the three sleeping cases, the sleeping case of
`test_a_trapped_call_without_a_root_is_removed`, and `test_an_ordinary_sleep_still_works`. As a
benchmark fact (not a check): under a 1 s deadline, `time.sleep(5)` ended at 1.16 s and
`select.select([], [], [], 5)` at 1.03 s, where both ran the full 5 s before.

`asyncio` still fails in the guest (it needs a socketpair), as the Scope says.

**The dry run** (EXECUTED: https://github.com/ClayGendron/wasi_python/actions/runs/39014444311,
on `29702cb`): every job it runs passed (build and judge, verify on ubuntu-24.04, windows-2025
and macos-15); `attest`, `publish` and PyPI were skipped, as a dry run must (criterion 3).
