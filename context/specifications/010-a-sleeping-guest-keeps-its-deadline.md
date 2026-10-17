# 010 — A sleeping guest keeps its deadline

- **Status:** draft, 2026-10-17. It changes the runner, so it is reviewed before it is built.
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

1. **The runner answers the clocks and the waits.** It shadows two WASI calls with the linker's
   shadowing, as the judge's driver shadows two calls. Keeping wasmtime's own functions and
   calling them from the new ones does not work: wasmtime-py calls a WASI function without the
   guest's memory ("missing required memory export"; EXECUTED, scratch `sleep/delegate.py`).
   So both are answered by the runner, following wasmtime 49's own rules (READ,
   `crates/wasi/src/p1.rs`, `clock_time_get` and `poll_oneoff`):
   - `clock_time_get`: the realtime clock is the host's `time.time_ns()`, the monotonic clock
     the host's `time.monotonic_ns()` (wasmtime's are the same two host clocks); the CPU-time
     clocks answer `EBADF`, as wasmtime does; the precision argument is ignored, as wasmtime does.
     Knowing the monotonic clock is what lets the runner turn an absolute wait into a duration.
   - `poll_oneoff`: zero subscriptions answer `EINVAL`. A subscription on a CPU-time clock
     answers `EINVAL`. A call with any descriptor subscription answers at once: each descriptor
     subscription is reported ready (error 0), because every descriptor the guest can hold is a
     file or stdio, which wasmtime also reports ready at once; no clock event is reported then,
     as with wasmtime when a descriptor is ready. (One difference: wasmtime answers `EBADF` for a
     descriptor that is not open; the runner reports it ready, and the guest's next read or
     write on it answers `EBADF`.) A call whose subscriptions are all clocks computes each wait
     (absolute: the target minus the clock's current value, floored at 0; relative: the
     timeout), waits for the shortest in slices of at most `TICK_S` (10 ms), checking the call's
     deadline between slices, and writes one clock event for it (error 0), as wasmtime does.
2. **The deadline ends a wait.** If the deadline passes during a wait, the new function raises
   an internal exception; wasmtime-py carries it out of the guest's `run`, and the runner reports
   `trapped == "deadline"` and `fuel_used == None`, as for an epoch interrupt. With
   `deadline_s=None` a wait runs to its end, as before.
3. **The waiting is injectable for the judge.** The wait logic is a small class taking `now`
   (the host's monotonic clock) and `sleep` functions; the runner passes the real ones. A unit
   test passes fakes and counts what the class asks to sleep, so the bound is checked without
   measuring time (constitution: tests count operations, never wall-clock).
4. **Checks.** The unit test of Decision 3: a wait of one hour under a 0.5 s deadline asks to
   sleep at most 0.5 s in total and raises; a wait of 0.2 s under no deadline asks for 0.2 s in
   slices of at most 10 ms; an absolute wait already in the past asks for nothing. A v1.2 check,
   `test_a_sleeping_guest_ends_at_its_deadline`, runs `time.sleep(10**6)` and
   `select.select([], [], [], 10**6)` under `deadline_s=0.2` and asserts `trapped ==
   "deadline"`; without the fix it does not finish (it is seen failing by not returning, under
   pytest's own interruption when run by hand). A v1.4 check runs `time.sleep(0.05)` with no
   deadline and asserts exit 0 and output after the sleep, so ordinary sleeps still work.
5. **What it costs.** One Python call per `poll_oneoff`; a guest that does not wait pays
   nothing. The judge's driver does not change: it has no deadline.

## Intent

A call's deadline holds whatever the guest does, waiting included, so the default time limit is
a limit.

## Design

```
src/wasi_python/runner.py     _Waits (now, sleep, deadline); the shadowed poll_oneoff and
                              clock_time_get
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

(Filled in on landing.)
