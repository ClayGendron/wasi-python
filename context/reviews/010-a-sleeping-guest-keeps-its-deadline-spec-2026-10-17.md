# Review of 010 — A sleeping guest keeps its deadline (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read the constitution,
  `AGENTS.md`, the reviews README, the 008 pre-build review (for its format), the specification,
  the author's two prototypes, the runner, the judge's driver, and the wasmtime, wasmtime-py,
  wasi-libc and CPython code named below. I did not rely on the author's summary.
- **Reviewed:** `context/specifications/010-a-sleeping-guest-keeps-its-deadline.md` as of
  `47c9fdc`. The runner is as of the same commit.
- **Ran (EXECUTED, darwin-arm64, host CPython 3.14.2, wasmtime-py 49.0.0, the artifacts in
  `build/artifacts/`, read only).**
  - Scripts and outputs are under
    `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/review-010/`.
    Nothing under `build/` was written. No tracked file was edited.
  - `drv.py` is the runner's `_instance`, rebuilt from the runner's own helpers. With
    `mode="stock"` it is today's runner. With `mode="spec"` it shadows `poll_oneoff` and
    `clock_time_get` the way Decision 1 describes, following the author's `sleep/proto.py`.
    Two switches test this review's suggestions: `origin_per_call` (the monotonic clock counts
    from the call's start) and `on_deadline="return"` (finding 1's fix).
  - Probes `p1_observe.py` to `p6_clockcost.py`, each with its `.txt` output. They are quoted in
    the findings.
  - I did not run `uv run pytest`. It writes under `build/`, which this review must not touch.
    The scoreboard is the build review's job.
- **Read (READ):**
  - our code: `src/wasi_python/runner.py`, `tests/harness/guest.py:160-215`,
    `tests/checks/test_v1_2_hostile_guest.py:183-191, 307-321`, `recipes/reactor_main.c:31-96`,
    `recipes/wasi-numpy.cross:29`, `recipes/wasi-pandas.cross:29`;
  - wasmtime v49 (`context/prior_art/wasmtime-v49/crates`): `wasi/src/p1.rs:141-173, 1282-1322,
    2308-2595`; `wasi/src/clocks.rs:84-170`; `wasi/src/ctx.rs:161`; `c-api/src/wasi.rs:1-80`;
    `wasmtime/src/runtime/component/store.rs:27`;
  - wasmtime-py 49.0.0: `_func.py:14, 85-110, 189-250`;
  - wasi-libc (`context/prior_art/wasi-libc`, `165235b`; the SDK's copy may be older):
    `libc-bottom-half/sources/ppoll.c`, `cloudlibc/src/libc/time/clock_nanosleep.c`,
    `cloudlibc/src/libc/sys/ioctl/ioctl.c`, `clocks/clock.c`;
  - the SDK's ABI: `build/tools/wasi-sdk-33.0-arm64-macos/share/wasi-sysroot/include/wasm32-wasip1/wasi/wasip1.h:83-101, 1131-1349`;
  - CPython (`context/prior_art/cpython`, the 3.14 branch): `Modules/timemodule.c:2226-2305`.

## What holds

- **The defect is real, and shadowing the two calls closes it.**
  - EXECUTED, `p2_deadline.txt`. These five programs each ran under `deadline_s=0.2`:
    `time.sleep(10**6)`, `select.select([], [], [], 10**6)`, `poll().poll(10**9)`, a loop of
    `time.sleep(0.001)`, and a loop of `time.sleep(0)`. With the shadow, every one ended in
    0.20 s, trapped. A line after the wait writes `/tmp/after`. It never ran.
  - EXECUTED: `time.sleep(0.3)` with no deadline took 0.3 s, measured by the guest's own clock.
- **The ABI the specification relies on is right.** READ, `wasip1.h`, from its `_Static_assert`
  lines:
  - a subscription is 48 bytes: `userdata` u64 at 0, then `u` at 8, whose tag is a u8 at 8;
  - the union starts at 16. A clock subscription has `id` u32 at 16, `timeout` u64 at 24,
    `precision` u64 at 32 and `flags` u16 at 40. A descriptor subscription has the fd, a u32,
    at 16;
  - an event is 32 bytes: `userdata` u64 at 0, `error` u16 at 8, `type` u8 at 10,
    `nbytes` u64 at 16, `flags` u16 at 24;
  - the constants: tags are clock 0, fd_read 1, fd_write 2. `ABSTIME` is flag bit 1. The clock
    ids are 0 to 3.

  The prototype's `"<I4xQQH"` at offset 16 and `"<HB5xQH6x"` after `userdata` match.
- **CPython's waits are the shapes Decision 1 handles.**
  - READ, `timemodule.c:2241-2267`: `time.sleep` is `clock_nanosleep(CLOCK_MONOTONIC,
    TIMER_ABSTIME, …)`. That is one absolute monotonic clock subscription. So the runner must
    own the monotonic clock, as Decision 1 says.
  - READ, `ppoll.c`: `select` and `poll` become descriptor subscriptions plus one relative
    realtime clock.
  - EXECUTED, `p6_clockcost.txt`: `-c pass`, a pandas groupby, and 100 `logging` lines made no
    `poll_oneoff` call at all.
- **wasmtime 49's general path is the one to follow.**
  - READ, `p1.rs:2325-2347`: the single-relative-sleep shortcut runs only with
    `allow_blocking_current_thread`.
  - READ: the C API never sets that flag (`c-api/src/wasi.rs`). So wasmtime-py takes the
    general path. Its clock events have `nbytes` 0. A CPU-time clock gets `EINVAL`.
    Decision 1 matches this.
- **Waits within the deadline behave as before.** EXECUTED, `p1_observe.txt`:
  - `time.sleep(0)` then `time.sleep(0.05)` gave 0.05 s;
  - `select([], [], [], 0.05)` gave 0.05 s;
  - `sleep(-1)` and `sleep(1e300)` raised the same errors as stock.
- **Cleanup on a trap is unchanged.** READ, `runner.py:183-187` and `runner.py:134-150`: the
  store is closed, and a private root removed, in `finally` blocks. Those run whatever ends the
  call, including an exception the runner does not catch.

## Acceptance criteria against evidence

1. *The unit test and the v1.2 check exist; the unit test was seen failing against a class
   that does not check the deadline.* **Reachable for the unit test.** The v1.2 check, as
   written, fails by hanging (`10**6` s is 11.6 days). No timeout plugin is pinned (READ,
   `pyproject.toml`). So "seen failing" means a person interrupting it (finding 5).
2. *`uv run pytest` is green with `--accept-judge`.* Checkable.
3. *A dry run of the release workflow passes every job.* Checkable. A regression of the v1.2
   check would hold a CI job until the job's own timeout (finding 5).

## Findings, most severe first

1. **The deadline exception goes through a process-global slot. A concurrent call can receive it,
   and lose its own result** (`010:48-50`). High.
   - **Mechanism (READ, wasmtime-py `_func.py:212-250`).**
     - A Python exception raised in a host function is stored in the module global
       `LAST_EXCEPTION`, and the guest sees a "python exception" trap.
     - Whichever thread next leaves wasm with a trap re-raises what is stored there.
     - ctypes releases the GIL during `wasmtime_func_call`, so calls in two threads really run
       at the same time.
     - The 006 pre-build review (finding 3) noted this for the door, where it is rare. Decision 2
       makes it the path every deadline-in-a-wait takes. That is the default for every call
       (60 s).
   - **What I saw (EXECUTED, `p4_last_exception.py`, `p4b.txt`).** Two threads ran on their own
     stores for 3 s:
     - thread A's host function raises a marker exception, as Decision 2's would;
     - thread B's guest traps on its own (`unreachable`), as a fuel trap, an epoch interrupt or
       `proc_exit` would.

     | outcome | count |
     |---|---|
     | B's call raised A's marker, and lost its own trap | 3,489 of 7,986 |
     | A's call got a bare `WasmtimeError: python exception` | 3,489 |
   - **In the runner, this means:**
     - the waiting call falls into `except wt.WasmtimeError` (`runner.py:277-278`). It reports
       `trapped == "error while executing at wasm backtrace:"`, not `"deadline"`;
     - another call reports `"deadline"` for what was really out of fuel. A call that ended by
       `proc_exit` loses its exit code.
   - **Fix (EXECUTED, `p2_deadline.txt`, `on_deadline="return"`).** Raise nothing. When the
     deadline passes, the wait waits until the epoch has also passed. Then it answers the clock
     event normally. The guest traps with `TrapCode.INTERRUPT` at its next epoch check, which
     wasmtime makes at every function entry and loop head.
     - All five programs gave `trapped == "deadline"` in 0.22–0.23 s. `/tmp/after` was never
       written.
     - No Python exception crosses wasm. `fuel_used` is `None` by the existing rule. The runner
       needs no new `except`.
     - The prototype waits two extra ticks, which is a timing assumption. The built form should
       be deterministic. `_epoch_ticker` keeps a count of the epochs it has advanced. The call
       records the count when it sets its deadline. The wait returns only once the count has
       passed that value plus `ticks + 1`.
     - If the raise is kept instead, the specification must say why the misdelivery is
       acceptable. It should also add a check with two concurrent calls.

2. **A Python exception can leave the shadowed `poll_oneoff`, so `run()` raises, against spec
   006's promise** (`010:38-47`). High.
   - **What I saw (EXECUTED, `p3b_bigpoll.py`).** A guest registered 150,000 descriptors with
     `select.poll()` and called `p.poll(0)`. The shadow, built as the specification describes,
     raised `IndexError: index out of range` from `memory.write`. It came out of
     `exports["run"]`. Stock wasmtime answered with an errno, and the program went on.
   - **Cause.** wasi-libc's `ppoll` puts `2n+1` subscriptions and events on the stack as
     variable-length arrays (READ, `ppoll.c`). At this size the stack overflows, so the event
     pointer lands outside memory (INFERRED). wasmtime answers `EFAULT` for any guest pointer it
     cannot read or write.
   - **What the specification does not decide** (constitution §5.2):
     - wasmtime-py passes i32 values as signed numbers. The door masks them (`runner.py:332-333`);
       Decision 1 does not say to. Without the mask, an address above 2 GiB becomes negative,
       and `Memory.read` clamps it like a slice (006 pre-build review, finding 3). That needs
       `memory_bytes=None` or a cap above 2 GiB, both of which the runner allows.
     - What to answer for a subscription array or event array outside memory (wasmtime:
       `EFAULT`).
     - What to answer for an unknown tag, or an unknown clock id (ids 4 and up). wasmtime
       answers `EINVAL`; the prototype treats any tag above 2 as a clock, and any clock id
       other than 0 as monotonic.
     - What to answer for an array larger than wasmtime's 128 MiB budget (`ENOMEM`; READ,
       `p1.rs:158-172`, `store.rs:27`).
   - **Fix.**
     - Mask all four arguments.
     - Bounds-check both arrays and `nevents` against `data_len`, and answer `EFAULT`.
     - Answer `EINVAL` for an unknown tag or clock id.
     - Wrap the body as the door is wrapped: no exception except `KeyboardInterrupt` leaves it.
     - Do the same in the shadowed `clock_time_get`.
     - Add a WAT unit check (`tests/unit/wat.py` exists for this). It should call
       `poll_oneoff` with an array past memory and with a bad tag, and assert the errno.

3. **The guest's monotonic clock becomes the host's uptime, and `time.process_time()` with it**
   (`010:34-36`). Medium.
   - **What I saw (EXECUTED, `p5_origin.txt`, `p1_observe.txt`).**

     | binary | stock: `monotonic`, `process_time` | Decision 1: both |
     |---|---|---|
     | snapshot | 0.007, 0.007 | 3,078,204.6 s (35.6 days) |
     | plain reactor | 0.025, 0.025 | 3,078,207.1 s |

     With the clock counted from the call's start, the values were 0.004 and 0.022, as stock.
   - **Why (READ).**
     - wasmtime's monotonic clock counts from the moment its WASI context is made
       (`clocks.rs:120-170`, `initial: Instant::now()`). So "wasmtime's are the same two host
       clocks" is true for realtime and not for monotonic.
     - `process_time` is wasi-libc's emulated `clock()`, linked because of
       `-D_WASI_EMULATED_PROCESS_CLOCKS` (READ, `wasi-numpy.cross:29`). It is the monotonic
       clock minus a start that its constructor read while the snapshot's clocks were pinned at
       0 (`clock.c`, `reactor_main.c:49-56`).
   - **Consequences.**
     - A guest reads the host's uptime: a fingerprint, and a fact the sandbox did not show
       before. That is a small leak, but a new one.
     - `process_time()` reports weeks.
     - Anything the snapshot recorded from the monotonic clock at build time is now compared
       against uptime. Today it is compared against a small value (INFERRED; I found no case
       that breaks).
   - **Fix.**
     - Record `origin` once per call. Answer `now - origin`, which is wasmtime's own rule.
     - Use `time.perf_counter_ns()` as `now`.
       - On Windows hosts before CPython 3.13, `time.monotonic_ns()` is `GetTickCount64`, at
         about 15.6 ms resolution. `requires-python` is `>=3.11`.
       - `perf_counter` is `QueryPerformanceCounter` there, as Rust's `Instant` is. The
         unshadowed `clock_res_get` reports that clock's resolution.
       - This is INFERRED from CPython's documentation; I did not run it on Windows.
     - Inject the origin into Decision 3's class, so a unit test checks `now - origin` with
       fakes.

4. **One `poll_oneoff` can hold the host past the deadline for O(n) Python work**
   (`010:38-47`, `010:64-65`). Medium.
   - **What I saw (EXECUTED, `p3b_bigpoll.txt`).** A guest polled 50,000 registered descriptors
     in a loop:

     | | time per `p.poll(0)` | a 0.2 s deadline ended at |
     |---|---|---|
     | stock | 0.00019 s | 0.20 s |
     | the specification's shadow | 0.162 s (850×) | 0.33 s |

   - **Why.**
     - The callback is host code, so no epoch check runs inside it.
     - The prototype unpacks each subscription in Python, and writes each event with its own
       `memory.write`, which is one ctypes call per event.
     - The guest's stack bounds `n` today (finding 2), at a little over 100,000 subscriptions.
       So the overrun is bounded, but at a fraction of a second per call. The guest controls
       it.
   - **Fix.**
     - Read the array once, and parse it with `struct.iter_unpack`.
     - Build all the events in one `bytearray`, and write them once.
     - Cap `n` as wasmtime does (finding 2).
     - State in the specification that the deadline can be overrun by up to one call's host
       work, and give that bound.

5. **The v1.2 check fails by hanging, for 11.6 days** (`010:58-62`). Medium.
   - Without the fix, `time.sleep(10**6)` blocks inside wasmtime for 10⁶ s. No pytest timeout
     plugin is pinned. CI would hold the job until the job's own timeout.
   - "Seen failing by not returning, under pytest's own interruption when run by hand" is not
     a red result the scoreboard can record. A failing guard must fail, not stall.
   - **Fix.**
     - Run the guest in a worker thread or child process, with a hang breaker far from both the
       0.2 s deadline and the 10⁶ s sleep (for example, 120 s). Assert that it returned, and
       that `trapped == "deadline"`.
     - Write down that the breaker is a fail-safe, not a measurement (constitution §4.9). The
       check asserts a value, and the breaker only turns a hang into a failure.
     - I found no signal free of the clock that tells "cut at the deadline" from "slept to
       the end". Both end in the epoch trap (INFERRED, from finding 1's run: after a full sleep,
       the epoch has long passed). So the breaker is needed.
     - Add the sleeping case to `test_a_trapped_call_without_a_root_is_removed`. A call trapped
       inside a wait must also close its store and remove its root.

6. **Descriptor behaviour differs from wasmtime's in more ways than the one Decision 1 lists**
   (`010:39-44`). Low.
   - EXECUTED, `p1_observe.txt`. Each line is `select(…, 0)` or `poll(0)`:

     | subscription | stock | Decision 1 |
     |---|---|---|
     | stdin for write, or stdout for read | `OSError` `EBADF` | reported ready |
     | fd 3, the preopened directory | `EBADF` | ready |
     | fd 99, not open | `EBADF` (whole call) | ready |
     | `poll` on fd 99 and fd 0 | `EBADF` | `[(99, 3), (0, 3)]` |
     | an empty file, for read | not ready | ready |

   - READ, `p1.rs:2508-2569`.
     - wasmtime writes `nbytes = 1` on every descriptor event. wasi-libc's `ioctl(FIONREAD)`
       reads that field (`ioctl.c`). Decision 1 leaves it unstated; the prototype writes 0.
     - At end of file, wasmtime sets `FD_READWRITE_HANGUP`, which wasi-libc turns into
       `POLLHUP`.
   - "Every descriptor the guest can hold is a file or stdio" is not so. A directory is a
     descriptor. The runner cannot see the guest's descriptor table, so it cannot match
     wasmtime exactly. That limit is fine; it should be stated.
   - **Fix.**
     - Answer `EBADF` (the whole call, as wasmtime does) for the descriptors the runner knows:
       0 for write, 1 and 2 for read, and 3, the one preopen.
     - Write `nbytes = 1`.
     - List the remaining differences in the specification and the README: unknown descriptors
       are ready, and there is no hang-up flag. None of them lets the guest read or write
       anything it could not before.

7. **Decision 5 understates the cost: every clock read becomes a Python call** (`010:64-65`).
   Low.
   - EXECUTED, `p6_clockcost.txt`. The guest read `time.monotonic()` 200,000 times:
     - stock: 228 ns per read, 0.07 s in all;
     - with the shadow: 13,025 ns per read, 2.62 s in all.
   - Ordinary programs make few reads. `-c pass` made 9, a pandas groupby 10, and 100
     `logging` lines 109. But "a guest that does not wait pays nothing" is not true for code
     that reads the clock in a loop, such as `timeit`, timestamps, or `perf_counter` profiling.
   - Fuel is unaffected: it counts guest instructions only.
   - **Fix.** State the cost. Record it in the speed memo as a benchmark fact. Cheap ways to
     reduce it, if wanted:
     - fetch the `memory` export once after instantiation, not `caller["memory"]` per call;
     - pack with a prebuilt `struct.Struct`.

8. **Smaller points the specification should decide in words** (`010:28-65`). Low.
   - **The deadline's instant.** "The call's deadline" should be defined. It is the host
     monotonic time when `set_epoch_deadline` is called, plus `deadline_s`. With finding 1's
     fix, it is the epoch count instead, which leaves one clock, not two.
   - **`deadline_s=None` means a guest may wait forever, even with a fuel cap.** No
     instruction runs while it waits, so no fuel is spent. That is as today, but the README
     should say it next to the default.
   - **`KeyboardInterrupt` now ends a waiting call.** Today a guest's sleep is native, so
     Ctrl-C waits for the sleep to end. With the shadow, the host's `time.sleep` raises it
     inside the callback, and `run()` raises it. The store and root are still released
     (READ, the `finally` blocks). This is good behaviour; it should be stated, and the
     wrapper of finding 2 must let it through.
   - **With no deadline, slicing is not needed.** One `sleep(wait)` does. The unit test's
     "slices of at most 10 ms under no deadline" then tests a choice nothing needs.
   - **The judge's driver.** Its stepping clock answers every clock id, CPU-time ones included
     (`guest.py:175-179`), while the runner will answer `EBADF` for those. No check reads
     `process_time` through both, so nothing breaks today. It is one more way the judge and
     the runner differ.

## Constitution checks

- §4.4, two imports only: holds. Shadowing replaces two WASI functions on the host side. The
  guest's imports are unchanged.
- §4.5, embedder-neutral: holds.
- §4.9, tests count, benchmarks time: the unit test holds. The v1.2 check needs a hang breaker,
  stated as a fail-safe (finding 5).
- §4.10, claims carry their evidence: "wasmtime's are the same two host clocks" is labelled
  READ, but it is wrong for the monotonic clock (finding 3).
- §4.13, tooling: no new dependency. Holds.
- §5.2, no open questions: errno choices for bad pointers, unknown tags and clock ids, and
  `nbytes` are undecided (findings 2 and 6).
- §5.6, review before build: this review.
- §7, never-do list: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. **Fixed.** No exception: the wait stops when the ticker passes the store's deadline count and
   answers normally; the guest traps at its next epoch check (Decision 2).
2. **Fixed.** Decision 1 decides the masking, `EFAULT` bounds, `EINVAL` for an unknown tag or
   clock, `ENOMEM` past 4,096 subscriptions, and a catch-all answering `EINVAL`.
3. **Fixed by not shadowing `clock_time_get`.** The guest keeps wasmtime's clocks; the runner
   estimates the monotonic origin from just after `set_wasi`, so waits only come out longer.
4. **Fixed.** One-pass parsing and the 4,096 cap bound a call's host work.
5. **Fixed.** The v1.2 check runs each call in a thread with a 120 s fail-safe; the trapped-call
   cleanup check gains a sleeping case.
6. **Fixed.** `EBADF` for the known descriptors (0 write, 1–2 read, 3), `nbytes` 1; the
   not-open difference is documented.
7. **Fixed by not shadowing `clock_time_get`.** Clock reads are untouched.
8. **Fixed.** Decision 2 defines the deadline's start, says `deadline_s=None` waits as long as
   asked (fuel does not stop it), lets `KeyboardInterrupt` through, and does not slice without a
   deadline; Decision 5 notes the judge's CPU-time clocks are untouched.

## Verdict

Not ready to build yet: the design is right, and the shadow does end the wait at the deadline
(EXECUTED). But the specification must not carry the deadline as a Python exception through
wasmtime-py's global slot (finding 1). It must make the shadow total, so no exception escapes
(finding 2). It must keep wasmtime's per-call monotonic origin (finding 3). Findings 4 to 8 are
small edits to the specification.
