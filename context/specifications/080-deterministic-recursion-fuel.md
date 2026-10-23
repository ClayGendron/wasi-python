# 080 — 071's recursion checks count deterministic fuel, and its guard's unit tests stand alone

- **Status:** **landed 2026-10-19** (accepted on `7f150e3` as `fae6615`, history line 73; its review, `../reviews/080-deterministic-recursion-fuel-2026-10-19.md`, said it lands once F1 was answered, and F1 and F2 were taken). Before landing: drafted and built 2026-10-19 (two items: deterministic fuel, and the guard's unit tests on Linux) on `spec/080-deterministic-recursion-fuel` from main `23f1c4f` (the Landing notes). It changes neither the guest's imports nor its exports, the artifact set nor the build recipe, so §5.6 asks no review before build. A different agent reviews the build.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** a judge change; **parallel-safe**, not build-class (§5.7). It edits two checks in `tests/checks/test_v1_2_hostile_guest.py` and two unit tests in `tests/unit/test_runner_async.py`, and nothing else: no `src/`, `scripts/`, `recipes/`, `downloads/SHA256SUMS`, workflow, README or CHANGELOG. No golden output, gap or allowance is edited. It restates the accepted fuel of the checks it changes: **the lane accepts it with `--accept-judge`, and with `--accept-growth` for the two values that rise** (the Landing notes).
- **Depends on:** 071 (landed; it added the checks).
- **Research it stands on:** spec 063's dry run 39211765022 (its own-runner shard on Linux, `build/reviews-evidence/063-build4/run7/judge__ubuntu-24_04__own-runner__.log` in the main tree: two `test_runner_async.py` tests refused by 071's guard); spec 075's build, `build/reviews-evidence/075-build/fuel_spread.py` and `fuel_spread.out` in the main tree (EXECUTED there: five runs of the plain binary's `heapq` and `lru-cache` rows spread 0.37% and 0.27%); and this spec's five-run measurement of every row (EXECUTED, the Landing notes).

## The problem

Spec 071's `test_recursion_through_python_raises` and `test_pickling_a_deep_list_raises` record fuel, and the ratchet holds fuel to one part in ten thousand. Both call `wasi_python.run`, which answers the guest's `random_get` from the host's entropy. On the plain binary that entropy is CPython's hash secret, so the work of every dict and set moves from run to run: the five plain rows spread 0.09% to 0.45% over five runs. On the snapshot, whose secret is fixed, `run` still reseeds `random` and `numpy.random` from the host's entropy at each call, and pandas' and lxml's rows spread up to 0.012%. So any judge run can find one of these rows "grown" at random. The lane's acceptance of 071 passed by chance; spec 075's builder saw three different plain rows grow in two runs.

A second defect came from the same specification (spec 063's dry run 39211765022). In 063's own-runner shard on Linux, `test_runner_async.py`'s `test_a_lost_call_stops_the_guest_and_drive_says_so` and `test_a_call_cancelled_before_it_runs_never_starts_its_guest` fail with 071's `RuntimeError: wasmtime's handler for SIGSEGV was replaced…`. Nothing replaces a handler (EXECUTED, the Landing notes): both tests call `_drive` with stand-ins for wasmtime, and in that shard no test before them has made a wasmtime engine, so wasmtime's trap handlers are not installed yet and the guard finds `SIG_DFL` (or pytest's faulthandler) where it looks for wasmtime's. They fail alone too, with or without pytest's faulthandler plugin; the full judge passed them only because earlier files had made an engine.

## Decisions

1. **The two checks run through the judge's own guest driver**, the `guest` fixture, as the other v1.2 checks that record fuel do.
   - The driver answers `random_get` from a seeded stream and `clock_time_get` from a stepped clock (spec 002, Decision 9), so the hash secret, the reseeds and every clock read are the same on every run.
   - Since spec 071 (Decision 3) the driver makes the runner's engine: fuel, epoch interruption and the 512 KiB wasm stack. So the checks still see the frames and the stack `run` gives; what the window does is unchanged, and the depth floors hold.
   - **Why not a fixed `PYTHONHASHSEED` in `run`'s env.** The guest's interpreter is configured isolated (`PyConfig_InitIsolatedConfig`, `recipes/reactor_main.c`), so it ignores `PYTHONHASHSEED`; and the snapshot's spread does not come from the hash secret at all.
   - **What `run` still covers.** Criteria 2, 4 and 11 of spec 071 call `run` and record no fuel; criterion 5's unit check holds `run`'s engine to the driver's. No other check 071 added records fuel.

2. **The two stand-in tests set 071's guard aside** (`monkeypatch.setattr(runner, "_trap_handlers_ready", lambda: None)`), each with a comment saying why.
   - They test `_drive`'s other rules (a lost call, a call cancelled before it runs) with stand-ins for wasmtime; the guard has its own checks (071's criterion 11 and its unit).
   - **Why not a product change.** In the product `_drive` runs only after `_engine` has made an engine, and wasmtime installs its handlers when the first engine is made; a session's opening, turns and shutdown come after its engine too. So no embedder reaches the guard before wasmtime's handlers exist (EXECUTED: on Linux the guard answers `SIGSEGV` before the first engine and `None` after it, faulthandler on or off). The guard need not change.
   - **Why not make an engine in the tests.** It would tie two `_drive` tests to the guard they do not test; setting the guard aside keeps them about their own rule, in any order.

## Intent

Every fuel metric spec 071 added is the same on every run, so the ratchet can hold it; and 071's guard does not fail tests that never touch wasmtime, whatever runs before them. Tests that do touch wasmtime after an inline pytest session has replaced its handlers are not in scope (the Landing notes, "The open case").

## Design

Item 1: each of the two checks takes the `guest` fixture in place of `metric` and `_run()`: it calls `guest("snapshot" | "plain", ["-c", program])`, which records the run's fuel itself, and keeps its assertions as they were (`_recursed` reads the driver's result as it read `run`'s). Item 2: the two unit tests take `monkeypatch` and replace `_trap_handlers_ready` before they call `_drive`.

## Scope

In: the two checks and the two unit tests. Out: other checks that call `run` and record no fuel; the runner itself (Decision 2 says why the guard stays).

## Acceptance criteria

1. **Five runs, identical fuel.** Each row of `test_recursion_through_python_raises` (35 rows, both binaries) and `test_pickling_a_deep_list_raises`, run five times through the path the check now uses, gives one fuel value; through `wasi_python.run`, as 071 ran them, the plain rows and pandas' and lxml's snapshot rows do not (`build/fuel_five.py`, the Landing notes).
2. **The checks still hold what 071 asked.** Every row raises as before, above its floor.
3. **The own-runner shard's order on Linux.** `pytest tests/test_api.py tests/unit/test_async_tools.py tests/unit/test_cli.py tests/unit/test_guest_tools.py tests/unit/test_runner_async.py`, and `test_runner_async.py` alone, on Linux aarch64 and x86_64 against 071's set: no failure; and the shard's whole file list in its order (445 tests) passes on aarch64.
4. **The judge.** The fast tier and one full run (`-n 3`) against `build/sets/s-c50ca51fae5eb55b`: no failure, no lost pass; the ratchet's only moves are these checks' restated fuel.

## Landing notes

### What was built

On `spec/080-deterministic-recursion-fuel` from main `23f1c4f`: `9bfffba` (the draft), `d5f7984` (item 1), `dcd7e4c` (item 2), then these notes. Evidence: `../research/2026-10-18-deep-recursion-on-the-wasm-stack/v4/`.

### Item 1: five runs, identical fuel (EXECUTED, `v4/fuel_five.py`)

Every fuel-recording row of 071, five runs each, against `build/sets/s-c50ca51fae5eb55b`:

| path | rows with a spread | largest spread |
|---|---|---|
| `wasi_python.run`, as 071 ran them (`v4/fuel_five_run.out`) | the five plain rows (0.094% to 0.447%: `setrecursionlimit` 766,721, `repr` 382,720, `pickle-partial` 356,193, `heapq` 350,607, `lru-cache` 203,337); pandas `Series.map` (557,382, 0.012%); the four lxml rows (0.003% to 0.008%) | 0.447% |
| the judge's driver, as 080 runs them (`v4/fuel_five_guest.out`) | none: all 36 rows give one value five times | 0 |

**What moves:** every restated value is the driver's, not `run`'s. 34 fall (by up to 0.43%: the driver's environment differs from `run`'s defaults: a writable root at `/`, no `HOME`, `TMPDIR` or `PYTHONTZPATH`, the seeded random and the stepped clock). Two rise: `test_recursion_through_python_raises[np-frompyfunc-snapshot]` 779,725,038 to 779,990,064 (+265,026, +0.034%; `run` gave this row the same value five times, so the change is the driver's environment, not chance) and `[heapq-plain]` +8,357 (+0.005%, within the ratchet's tolerance; the accepted value was one draw of a random hash secret, whose spread is 0.2%).

### Item 2: the cause, on Linux (EXECUTED, `v4/order-*.log`)

On Linux aarch64 and x86_64 (the `wp040-*` images, against 071's set), before the fix:
- the shard's first five files in its order: the two tests fail with the guard's message;
- `test_runner_async.py` alone: the same two fail; and the same with `-p no:faulthandler`;
- a probe: `_trap_handlers_ready()` answers `SIGSEGV` before any engine, still `SIGSEGV` after `faulthandler.enable()`, and `None` once a `wasmtime.Engine()` exists.

So no test, plugin or product path replaces a handler: the two tests reach the guard before any engine exists. After the fix (`v4/order-fixed-*.log`): 83 passed in the shard's order, 15 alone, with and without the faulthandler plugin, on both architectures; the shard's whole file list in its order, 445 passed, on aarch64 (`v4/own-runner-arm64.log`).

### The judge

Against `build/sets/s-c50ca51fae5eb55b`, in the worktree (no build; the upstream groups and the rebuild checks need source trees a build makes, so they are blocked here and run in the lane):
- fast tier (`uv run pytest -m "not slow" -n 3`): `475/550 pass · 1 gap · 23 blocked · 0 fail · 51 deselected (unit suite 1267/1275, 8 skipped)`; `1742 passed, 31 skipped, 1 xfailed`; `ratchet vs 9dad163977: lost 0 · absent 0 · unrun 0 · unrun locally 21 · gained 0 · grew 1 · upstream unrun 31 · not selected 37 · judge changed: tests/checks/test_v1_2_hostile_guest.py`;
- full (`uv run pytest -n 3`): `492/550 pass · 3 gap · 55 blocked · 0 fail (unit suite 1267/1275, 8 skipped)`; `1759 passed, 63 skipped, 3 xfailed`; `ratchet vs 9dad163977: lost 0 · absent 0 · unrun 0 · unrun locally 41 · gained 0 · grew 1 · upstream unrun 31 · judge changed: tests/checks/test_v1_2_hostile_guest.py`. The one growth is `np-frompyfunc-snapshot`, above.

The full run was made before item 2's commit; the fast tier again after it (`build/fast-080b.log`): the same lines, with `judge changed: tests/checks/test_v1_2_hostile_guest.py, tests/unit/test_runner_async.py`.

### The open case (the review's F1)

On Linux's serial unit tier, 16 calls in `test_runner_calls.py` and `test_runner_mounts.py` are refused by 071's guard. They run real engines, but after an inline pytest session (`test_landing_lane`, `test_plugin`) whose faulthandler plugin disables and re-enables faulthandler and so drops wasmtime's handler: the guard is right to refuse there. It predates 080 (it dates from 071), and the release's Linux shards keep those files in separate processes. Spec 082 is reserved for it (`context/roadmap.md`): inline pytest sessions keep wasmtime's signal handlers, by passing `-p no:faulthandler` to them or running them as subprocesses.

### Revised against the review (2026-10-19)

The review (`scratchpad/080-review/080-deterministic-recursion-fuel-2026-10-19.md`): "lands once F1 is answered in writing"; both items sound.
- **F1.** The Intent is scoped to tests that never touch wasmtime; the open case above; roadmap lines reserving 081 and 082.
- **F2.** Criterion 2 of spec 071 (`test_the_c_stack_window_is_128_kib`) passes `fuel=10**11`, so `run`'s metered engine meets a Python-through-C recursion end to end; it records no fuel, so nothing is restated.

### For the lane

- `--accept-judge "spec 080: 071's recursion checks run through the judge's driver, so their fuel is the same on every run (restated, mostly lower); two test_runner_async tests that call _drive with stand-ins set 071's guard aside, so they pass on Linux in any order; 071's window check runs run metered"`.
- `--accept-growth "spec 080: test_recursion_through_python_raises[np-frompyfunc-snapshot] is now measured through the judge's driver, whose environment differs from run's defaults: +265,026 fuel (+0.034%), deterministic over five runs"`.

**Landed 2026-10-19** through the lane, after spec 071. The branch was on main `23f1c4f`, so no rebase was needed. The lane checked the post-review commit `66bbe5a` (F1: the Intent scoped, the open case named, 081 and 082 reserved in the roadmap; F2: the window check runs `run` metered, recording no fuel). The review was committed on the detached HEAD as `7f150e3`. No build: 080 changes `tests/` and documents only, so main's set `s-c50ca51fae5eb55b` stands. The full judge, serial: `wasi_python v1: 533/550 pass · 15 gap · 2 blocked · 0 fail (unit suite 1273/1275, 2 skipped)`, `1806 passed, 4 skipped, 15 xfailed in 883.92s`, accepted with `--accept-judge` and `--accept-growth` (`np-frompyfunc-snapshot` +265,026 fuel through the driver's environment) as `fae6615`, history line 73; with the noise gone, no other row grew (EXECUTED, `build/lane-080-accept.log`). The rules tier passed (40/40, unpiped); main fast-forwarded. Release dry runs no longer go red on 071's plain rows.

