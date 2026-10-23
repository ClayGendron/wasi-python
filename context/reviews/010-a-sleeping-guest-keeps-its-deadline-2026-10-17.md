# Review of 010 — A sleeping guest keeps its deadline (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the constitution, `context/reviews/README.md`, the 009 build review (for its format), specification 010 with its landing notes, and its pre-build review with the dispositions and confirmations. Then I read the diff. I did not rely on the landing notes. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** local commit `f5cf8bb` (not pushed): `_poll_plan`, `_Waits`, `_poll_oneoff`, the ticker's count and their wiring in `_instance` (`src/wasi_python/runner.py`); the tests in `tests/unit/test_runner_waits.py`, `tests/checks/test_v1_2_hostile_guest.py` and `tests/checks/test_v1_4_embedding.py`; the README and CHANGELOG text.
- **Re-ran (EXECUTED, darwin-arm64, host CPython 3.14.2, wasmtime-py 49.0.0, the artifacts in `build/artifacts/` read only).** Probes, outputs and the mutation log are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev010b/` (`probes/p1_wat.*` to `probes/p9c_locked.*`, `mutate.py`, `run_mut.sh`, `mutations.txt`, `pytest-notslow.txt`).
  - `uv run pytest -m "not slow"` → `121/128 pass · 1 gap · 2 blocked · 0 fail · 4 deselected` (unit suite 193/193); `314 passed, 2 skipped, 4 deselected, 1 xfailed`; ratchet `lost 0 · absent 1 · gained 6 · grew 0 · judge changed: test_v1_2_hostile_guest.py, test_v1_4_embedding.py, test_runner_waits.py`; then `ABSENT …::test_a_trapped_call_without_a_root_is_removed` and `RED: 1 accepted check(s) absent`; **exit 1** (finding 2).
  - The new tests alone (the unit file, the three sleeping cases, both cases of the trapped-call check, the ordinary sleep) → `14 passed`.
  - `uv run ruff check src tests` → all checks passed; `uv run ruff format --check src tests` → 39 files already formatted.
  - 14 mutations of the runner, each applied in place, run, and restored byte for byte, with `git diff --quiet src tests` → 0 after each and at the end (table below). One run was interrupted by me; I restored that file from `git show HEAD:` bytes (the tree was clean before) and confirmed `git diff --quiet` → 0.
  - I did not push, commit, tag, run `scripts/build.sh`, touch `build/artifacts/`, or edit a tracked file other than this review. My pytest runs rewrote untracked build state under `build/progress/`.

## Decisions 1–5 against the code

- **Decision 1, the layouts (READ, EXECUTED).** The SDK's `wasi/api.h` includes `wasip1.h`, whose `_Static_assert` lines (1189–1349) give: a subscription is 48 bytes, `userdata` at 0, the tag (u8) at 8, the union payload at 16; a clock is `id` u32 at 16, `timeout` u64 at 24, `precision` at 32, `flags` u16 at 40; an fd subscription's descriptor is a u32 at 16; an event is 32 bytes, `error` u16 at 8, `type` u8 at 10, `nbytes` u64 at 16, `flags` u16 at 24. `SUBSCRIPTION = "<QB7xIxxxxQQH6x"` and `EVENT = "<QHB5xQH6x"` match field for field. Tags 0/1/2, clock ids 0–3 and `ABSTIME` = 1 match (`wasip1.h:83-101, 1143-1155, 1248`).
- **The errnos (READ).** `wasip1.h:157` BADF 8, `:222` FAULT 21, `:257` INVAL 28, `:357` NOMEM 48. The code's constants agree.
- **Bounds and masking (EXECUTED, `p1_wat.txt`).** A hand-written module imports the shadowed function and stock wasmtime's, and calls each with the same arguments.
  - n = 0 → 28; n = 4097 → 48; n = −1 (masked to 2³²−1) → 48.
  - A subscription array, event array or `nevents` past memory, at 2³²−8, or at 2³¹ (a negative i32) → 21. Stock wasmtime-py **traps** on all six (it does not answer `EFAULT`; finding 5).
  - With memory grown past 2 GiB, pointers at 2³¹+1024 work and the event is written there. So the mask is right.
- **Descriptor rules (EXECUTED, `p1_wat.txt`, `p3_behaviour.txt`).** stdin for writing, stdout for reading and fd 3 → 8, the same as stock. stdout/stderr for writing and stdin for reading → ready with `nbytes` 1, the same as stock. A descriptor that is not open (9, 2³²−1) → ready where stock answers 8: the documented difference. On the real artifacts, `select` on a directory the guest opened reports it readable (documented).
- **Clocks (EXECUTED).** A CPU-time clock and id 7 → 28, as stock. An unknown tag (3, 255) → 28, as stock. An absolute realtime target in the past → wait 0. A 2³²−1-second absolute realtime target with no deadline → 28 (finding 5).
- **The origin (READ, EXECUTED).** `origin_ns` is the statement right after `wt.WasiConfig()` (`runner.py:283-284`). On the real artifacts the guest's first `time.monotonic()` read 0.003 s (snapshot) and 0.024–0.029 s (plain), and `process_time` the same: not the host's uptime (`p3_behaviour.txt`). The mutations show no check guards the origin (finding 4).
- **The ticker's count (READ, INFERRED).** `_tick` increments every engine, then `cls._count += 1` (`runner.py:827-830`); `_instance` reads the count after `set_epoch_deadline(ticks)` (`runner.py:272-275`). Let the engine's epoch be E at `set_epoch_deadline`; at that moment it is at most one round ahead of the count, so E ≤ offset + c0 + 1. When the count reaches c0 + ticks + 1 the engine is at least offset + c0 + ticks + 1 ≥ E + ticks, the deadline. So a wait never ends before the epoch has passed the deadline, as Decision 2 states. One gap: the ticker takes its engine list once per round, so a round that started before a new engine existed advances the count without that engine (finding 6).
- **Nothing escapes (EXECUTED).** Every body path is under `try`; `KeyboardInterrupt` is re-raised. `p8_sigint.txt`: SIGINT 0.5 s into a 30 s guest sleep, with and without a deadline, made `run` raise `KeyboardInterrupt` after 0.51–0.52 s; the host's open-descriptor count was the same as before (8 → 8); the private root and `HOME` were removed (the temporary directory was empty); the next call printed `next` with exit 0, and the next trapping call reported `"deadline"`. So in single-threaded use nothing leaks into a later call.
- **Decision 2 on the real artifacts (EXECUTED, `p2_waits.txt`).** Under `deadline_s=0.2`, on both binaries, each of these ended `trapped == "deadline"` in 0.21–0.37 s with no output: `time.sleep(10**6)`, `select.select([], [], [], 10**6)`, `poll().poll(10**9)`, `select([0], …, 10**6)` in a loop, loops of `sleep(0)`, `sleep(0.001)` and `sleep(0.05)`, a sleep inside `except BaseException`, a sleep in `finally`, a sleep in an `atexit` handler, a sleep of `2**33` s, a sleep in a `sorted` key, `map(time.sleep, …)`, and `threading.Event().wait(10**6)`. `time.sleep(1e300)` and `select` with 1e15 s fail in the guest with `OverflowError` before any WASI call, as native. With fuel as well, a 0.3 s and a 10⁶ s sleep ended at 0.23–0.28 s, `"deadline"` (`p4_more.txt`).
- **Ordinary waits (EXECUTED, `p3_behaviour.txt`, `p4_more.txt`).** With no deadline, `time.sleep(1.0)` took 1.05 s and the program went on. Under a 0.5 s deadline a 0.3 s sleep finished and printed. As a benchmark fact: 50 sleeps of 0.01 s measured 0.66–0.69 s by the guest's clock with the runner and 0.63 s with stock wasmtime (macOS oversleeps both).
- **The cap (EXECUTED).** `select.poll()` with the default mask (POLLIN|POLLPRI|POLLOUT, two subscriptions a descriptor): 2,048 descriptors (fds 0–2047) → `OSError` 48; 2,047 → 8, the `EBADF` of fds 0 and 3, so under the cap. POLLIN only: 4,095 → 8, 4,096 → 48. 150,000 descriptors → 48, not the stack-overflow `EFAULT` path. A guest polling 2,000 descriptors in a loop under a 1 s deadline ended at 1.03 s, `"deadline"`.
- **Decision 3 (READ).** `_Waits` takes `now`, `sleep`, `deadline_passed`; the unit tests pass fakes and count sleeps.
- **Decision 4 (READ, EXECUTED).** The listed checks exist, except the unit tests of out-of-bounds pointers (finding 4). The v1.2 check's 120 s join is a fail-safe on a daemon thread, as specified.
- **Decision 5 (READ).** Only `poll_oneoff` is shadowed; `clock_time_get` and the judge's driver are untouched.

## Mutations (EXECUTED, `mutations.txt`)

"Caught" means a new test failed. Each mutation was restored and `git diff --quiet src tests` returned 0.

| mutation | result |
|---|---|
| `_Waits` without the deadline check | caught: `test_a_long_wait_stops_at_the_deadline`, and `test_a_sleeping_guest_ends_at_its_deadline[sleep]` through its fail-safe (120 s) |
| no shadow (stock `poll_oneoff`) | caught: `…[select]` through its fail-safe; `…[sleep(0) loop]` passes (no real wait); `test_a_trapped_call_without_a_root_is_removed[sleeping]` **hung** until killed at 240 s (finding 3) |
| the EBADF rules dropped | caught: `test_descriptors_follow_wasmtime` |
| absolute realtime and monotonic swapped | caught: `test_the_shortest_clock_wins_…` |
| a wait with no deadline sliced | caught: `test_a_wait_without_a_deadline_is_one_sleep` |
| origin taken after `set_wasi` | survives |
| origin 1 s early (every absolute wait 1 s short) | survives |
| `stop_at = count + ticks − 1` | survives |
| count updated before the engines | survives |
| the `EFAULT` bounds check removed | survives |
| the mask removed | survives |
| the catch-all narrowed to `ZeroDivisionError` | survives |
| `MAX_SUBSCRIPTIONS = 10**9` | survives (the test reads the constant; it took 19 s to build 48 GB of bytes) |

## Acceptance criteria against evidence

1. *The unit test and the v1.2 check exist; the unit test was seen failing against a class that does not check the deadline.* **Met** (EXECUTED: the first row of the table).
2. *`uv run pytest` is green with `--accept-judge`.* **Not met yet.** The run is red on an absent accepted check, which `--accept-judge` does not clear (finding 2).
3. *A dry run of the release workflow passes every job.* **Not shown**; the commit is not pushed. A regression would hang a CI job on the trapped-call check until the job's timeout (finding 3).

## Findings, most severe first

1. **Concurrent calls corrupt wasmtime-py's host-function table: `run` raises for every later call in the process, and a guest's import can run another call's host function** (`runner.py:298-307`; wasmtime-py `_slab.py:15-32`, `_linker.py:79`, `_func.py:189-223`). High. **Not introduced by this change** (the door already did it), but this change doubles the per-call slots and routes every guest wait through the corrupted table.
   - **Mechanism (READ).** Each `define_func` takes a slot in the process-wide `FUNCTIONS` slab (`allocate`); `finalize` frees it when the linker or store is dropped (`deallocate`). The slab is plain Python with no lock. Two threads interleaving `allocate`/`deallocate` can hand one slot to two functions, or leave the free-list head pointing at a live entry.
   - **What I saw (EXECUTED, `p9_runner.txt`, `p9_stock.txt`).** 12 threads ran exit, fuel, deadline and short-sleep calls for 90 s. With the runner, 26,608 of 26,861 calls raised `TypeError: list indices must be integers or slices, not tuple` from `FUNCTIONS.allocate` inside `define_func`; once the free list holds a tuple, every later call in the process raises. Stock wasmtime (`poll_oneoff` not shadowed, the door still defined) did the same: 26,558 of 26,957. So `run` raises, against spec 006's promise.
   - **Cross-wiring (EXECUTED, `p9b_runner.txt`).** In three 30 s runs, 9, 8 and 14 guest sleeps failed with `OSError: [Errno 58] Not supported` (wasi-libc's `clock_nanosleep` answer for any `poll_oneoff` error). The runner's `poll_oneoff` never answers an error for a plain clock wait, and stock had none. So the guest's import ran another function (another call's door, or a freed slot), INFERRED from the slab. One call raised `cannot unpack non-iterable int object` from the trampoline (a freed slot). The same race can hand guest B the door of call A, and with it A's host, or A's `poll_oneoff` with A's deadline (INFERRED).
   - **Confirmed cause (EXECUTED, `p9c_locked.txt`).** The same 12-thread run with one lock around the slab's `allocate`, `deallocate` and `get`: 0 wrong results in two 30 s runs.
   - **Fix (its own specification, before the next release).** Stop allocating per call: one `Linker` per engine, with `poll_oneoff` and `host::call` defined once, dispatching to the call's state looked up from the caller's store; or hold a runner lock around every `define_func` and every drop of a linker or store (weaker: the garbage collector can drop one anywhere). Report the slab upstream to wasmtime-py. Add a v1.4 check: N threads of mixed calls, every result its own.
   - Separately, and also in stock (EXECUTED, `p7c_stock_vs_runner.txt`): with 8–12 threads starting at once, the first calls of some threads took 90–225 s, blocked in `wasmtime_module_delete` of the duplicate modules that concurrent cache misses in `_module` compile and then drop. Out of this change's scope; record it with finding 1.

2. **The scoreboard is red: parametrizing the trapped-call check removed an accepted check's id** (`tests/checks/test_v1_2_hostile_guest.py:307`). Medium.
   - Failure (EXECUTED): `uv run pytest -m "not slow"` → `ABSENT tests/checks/test_v1_2_hostile_guest.py::test_a_trapped_call_without_a_root_is_removed` and `RED: 1 accepted check(s) absent (retire them with --retire)`, exit 1. The landing notes say "all pass" and do not mention it.
   - Fix: retire the old id with a reason at landing, or keep the old test as it was and add the sleeping case as a new test. Either is a judge change the landing must name.

3. **The sleeping case of the trapped-call check has no fail-safe, so a regression hangs the judge** (`tests/checks/test_v1_2_hostile_guest.py:314-319`). Medium.
   - Failure (EXECUTED): with `poll_oneoff` not shadowed, `test_a_trapped_call_without_a_root_is_removed[sleeping]` was still running after 240 s and had to be killed. The guest sleeps 10⁶ s; the call runs in the test's own thread. `pyproject.toml` pins no timeout plugin, so CI would sit until its job timeout (60/120 minutes). That is what Decision 4's daemon-thread fail-safe exists to prevent; this case did not get it.
   - Fix: run that call through the same daemon thread and 120 s join, or have its guest sleep in a loop of short sleeps that a regression would make slow rather than endless.

4. **The wrapper and the deadline arithmetic are unguarded: eight of the mutations survive** (`runner.py:272-275, 416-442, 827-830`; `tests/unit/test_runner_waits.py`). Low.
   - Failure (EXECUTED, table): removing the `EFAULT` bounds, the mask or the catch-all, raising the cap, taking the origin later or 1 s earlier, `stop_at = count + ticks − 1`, or updating the count before the engines all leave every test green. Decision 4 promised unit tests of "out-of-bounds pointers"; there are none, because the tests reach only `_poll_plan`, not `_poll_oneoff`.
   - Fix: a unit test that calls `_poll_oneoff(origin, waits)` through a small WAT module (as `p1_wat.py` does) and asserts 21 for each out-of-bounds pointer, a pointer above 2 GiB working, 48 at `MAX_SUBSCRIPTIONS + 1` with the literal 4096, and 28 for a raising `waits`; factor `stop_at` into a function of `(count, ticks)` so a unit test pins `+ 1`; give `_poll_oneoff` an injectable monotonic clock so a unit test pins "the estimate never reads high". The origin's placement and the ticker's order stay READ-only; say so in the spec.

5. **Small differences from wasmtime, stated wrongly or not at all** (`010` Decision 1, `README.md:252-255`, `CHANGELOG.md:47-48`). Low.
   - Clock events: the spec says `nbytes` 1 "as wasmtime does". wasmtime 49's general path, the one wasmtime-py takes, writes 0 (READ `p1.rs:2482-2491`; EXECUTED `p1_wat.txt`: stock `(1, 0, 0, 0, 0)`, runner `(1, 0, 0, 1, 0)`). Harmless; correct the text or the value.
   - Two clocks ready at once: stock reports both events, the runner one (EXECUTED).
   - Out-of-bounds pointers: stock wasmtime-py traps; the runner answers `EFAULT` (EXECUTED). The runner's answer is the safer one; the spec should not say wasmtime answers `EFAULT`.
   - A wait the host's `time.sleep` cannot represent (about 292 years) with no deadline answers `EINVAL` through the catch-all, where wasmtime would wait (EXECUTED). Harmless; worth a line.
   - The README says the runner answers "following wasmtime's rules" in the Enforced list; it should point at the stated differences (unopened descriptors and directories reported ready, the cap). Its "more than 2,047 descriptors" holds for `poll`'s default mask only; with `POLLIN` alone the limit is 4,095 (EXECUTED). The CHANGELOG entry does not mention the new `ENOMEM` limit, which a program can see.

6. **The count can run ahead of a newly made engine for one ticker round** (`runner.py:824-830`). Info, INFERRED.
   - The ticker copies `_engines` once per loop. If the first metered (or unmetered) call is made while another call keeps the ticker running, a round already in progress advances the count without the new engine. Such a call's waits can end up to that round's catch-up (usually one tick) before its epoch reaches the deadline. The guest then runs a little longer and traps at the epoch; every later wait answers at once. No escape from the deadline; worth one sentence in the spec.

## Constitution checks

- §4 constraints: no upstream source is touched (the shadow is a runner function; wasmtime-py is not patched). No artifact enters git. The judge counts operations: the unit tests count sleeps; the 120 s join is a fail-safe, not a timing. The checks run under `uv`.
- §7 never-do list: nothing tripped. The judge was changed (three test files) and the review sees the judge-hash line; the ratchet must still be accepted with `--accept-judge` and the absent check retired with a reason (finding 2).

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1 — Accepted as a defect that predates this change; it is specification 011 (`../specifications/011-concurrent-calls-share-nothing.md`), drafted next and built before the next release. It takes the reviewer's first fix (host functions defined once, not per call) and the v1.4 check of N threads of mixed calls. The stall of concurrent cache misses is recorded there too.
2. Finding 2 — Fixed at acceptance: the old id is retired with `--retire` and a reason; the landing notes name the judge change.
3. Finding 3 — Fixed: a helper `_returns` runs a call in a daemon thread with the 120 s join; both the trapped-call check and the sleeping check use it. EXECUTED: with the shadow renamed away, `…[sleeping]` failed after 120.25 s instead of hanging.
4. Finding 4 — Fixed: `tests/unit/test_runner_waits.py` calls `_poll_oneoff` through a one-page WAT module (`EFAULT` for five out-of-bounds pointers including 2³²−1 and 2³¹, which a missing mask turns into `EINVAL`; `EINVAL` for 0, `ENOMEM` for 4,097 and 2³²−1, with the literal 4,096; `EINVAL` for a raising wait; an absolute monotonic wait counted from the injected origin). `_stop_at(count, ticks)` is a function with its own test. `_poll_oneoff` takes injectable clocks. EXECUTED: the six mutations named in the landing notes each fail a test. The origin's placement and the ticker's order stay READ only; the spec says so.
5. Finding 5 — Fixed: clock events now carry `nbytes` 0 and every clock due by the wait is reported, as wasmtime 49 does (a unit test); the spec says wasmtime-py traps on bad pointers where the runner answers `EFAULT`, and names the `EINVAL` of an unrepresentable wait; the README points at the stated differences and gives the cap in subscriptions (2,047 descriptors with `poll`'s default mask); the CHANGELOG names the cap and `EFAULT`.
6. Finding 6 — Answered: one sentence in Decision 2. No wait escapes the deadline: the guest traps at the epoch.

## Reviewer's confirmation

Checked against the uncommitted fixes in the working tree (`runner.py`, the two test files, the README, the CHANGELOG, the specification). Re-ran (EXECUTED): `uv run pytest -m "not slow"` → `121/128 pass · … (unit suite 199/199)`, `320 passed, 2 skipped, 4 deselected, 1 xfailed`, still `ABSENT …::test_a_trapped_call_without_a_root_is_removed`, exit 1, as expected before the `--retire`; `ruff check` and `ruff format --check` clean. 15 mutations of the fixed runner, each restored and compared byte for byte with a copy taken first (`cmp` equal for all three files), log in the scratch `rev010b/mutations2.txt`.

1. Finding 1 — **confirmed.** It predates this change; a separate specification taking the once-per-engine host functions and an N-thread check is the right home. 010 should not be called safe for concurrent callers until 011 lands.
2. Finding 2 — **confirmed, conditionally.** `--retire` is the harness's mechanism (`tests/harness/plugin.py:60`), and the spec's Landing notes name the judge change. The run is red until the acceptance with `--retire` and `--accept-judge` is recorded; the spec's Status already says "landed", which is true only after that run.
3. Finding 3 — **confirmed.** With the shadow renamed away, `…[sleeping]` and `…[select]` each failed through `_returns` after 120 s (240.19 s for both) instead of hanging; with `_Waits` missing its deadline check, `…[sleeping]` failed the same way.
4. Finding 4 — **confirmed.** Every mutation that survived before now fails a unit test, except the two the spec now names READ only: no `EFAULT` bounds, no mask (also fails the count test), the catch-all narrowed, the cap at 5,000, the wrapper's cap check removed, `_stop_at` off by two and the origin ignored each fail; the origin taken after `set_wasi` and the count updated before the engines pass, as stated.
5. Finding 5 — **confirmed.** Clock events carry `nbytes` 0 and every due clock is reported (mutating either back fails `test_every_clock_due_is_reported_with_no_bytes`); the spec states the trap-versus-`EFAULT` difference, the 4,095 with `POLLIN`, and the `EINVAL` of an unrepresentable wait; the README points at the stated differences and gives the cap in subscriptions; the CHANGELOG names the cap and `EFAULT`. All match what I executed.
6. Finding 6 — **confirmed.** Decision 2 now says it, and that no wait escapes the deadline.

The verdict above stands for the build as reviewed; with these dispositions, 010 lands once the acceptance run (`--retire`, `--accept-judge`) is green and recorded.

## Verdict

Does not land yet: the fix itself holds (every wait I tried ended at its deadline, nothing leaked from a sleeping trap, Ctrl-C is clean), but the judge is red (2) and one new check can hang forever (3); fix those, add the wrapper tests (4) and correct the text (5), and open finding 1, a pre-existing defect this change makes more reachable, as its own specification before the next release.
