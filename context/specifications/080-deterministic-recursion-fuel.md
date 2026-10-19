# 080 — 071's recursion checks count deterministic fuel

- **Status:** drafted and built 2026-10-19 on `spec/080-deterministic-recursion-fuel` from main
  `23f1c4f` (the Landing notes). It changes neither the guest's imports nor its exports, the
  artifact set nor the build recipe, so §5.6 asks no review before build. A different agent
  reviews the build.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** a judge change; **parallel-safe**, not build-class (§5.7). It edits two checks in
  `tests/checks/test_v1_2_hostile_guest.py` and nothing else: no `src/`, `scripts/`, `recipes/`,
  `downloads/SHA256SUMS`, workflow, README or CHANGELOG. No golden output, gap or allowance is
  edited. It restates the accepted fuel of the checks it changes: **the lane accepts it with
  `--accept-judge`, and with `--accept-growth` for the two values that rise** (the Landing
  notes).
- **Depends on:** 071 (landed; it added the checks).
- **Research it stands on:** spec 075's build, `build/reviews-evidence/075-build/fuel_spread.py`
  and `fuel_spread.out` in the main tree (EXECUTED there: five runs of the plain binary's `heapq`
  and `lru-cache` rows spread 0.37% and 0.27%); and this spec's five-run measurement of every
  row (EXECUTED, the Landing notes).

## The problem

Spec 071's `test_recursion_through_python_raises` and `test_pickling_a_deep_list_raises` record
fuel, and the ratchet holds fuel to one part in ten thousand. Both call `wasi_python.run`, which
answers the guest's `random_get` from the host's entropy. On the plain binary that entropy is
CPython's hash secret, so the work of every dict and set moves from run to run: the five plain
rows spread 0.09% to 0.45% over five runs. On the snapshot, whose secret is fixed, `run` still
reseeds `random` and `numpy.random` from the host's entropy at each call, and pandas' and lxml's
rows spread up to 0.012%. So any judge run can find one of these rows "grown" at random. The lane's
acceptance of 071 passed by chance; spec 075's builder saw three different plain rows grow in two
runs.

## Decision

**The two checks run through the judge's own guest driver**, the `guest` fixture, as the other
v1.2 checks that record fuel do.
- The driver answers `random_get` from a seeded stream and `clock_time_get` from a stepped clock
  (spec 002, Decision 9), so the hash secret, the reseeds and every clock read are the same on
  every run.
- Since spec 071 (Decision 3) the driver makes the runner's engine: fuel, epoch interruption and
  the 512 KiB wasm stack. So the checks still see the frames and the stack `run` gives; what the
  window does is unchanged, and the depth floors hold.
- **Why not a fixed `PYTHONHASHSEED` in `run`'s env.** The guest's interpreter is configured
  isolated (`PyConfig_InitIsolatedConfig`, `recipes/reactor_main.c`), so it ignores
  `PYTHONHASHSEED`; and the snapshot's spread does not come from the hash secret at all.
- **What `run` still covers.** Criteria 2, 4 and 11 of spec 071 call `run` and record no fuel;
  criterion 5's unit check holds `run`'s engine to the driver's. No other check 071 added records
  fuel.

## Intent

Every fuel metric spec 071 added is the same on every run, so the ratchet can hold it.

## Scope

In: the two checks. Out: other checks that call `run` and record no fuel; the runner itself.

## Acceptance criteria

1. **Five runs, identical fuel.** Each row of `test_recursion_through_python_raises` (35 rows,
   both binaries) and `test_pickling_a_deep_list_raises`, run five times through the path the
   check now uses, gives one fuel value; through `wasi_python.run`, as 071 ran them, the plain
   rows and pandas' and lxml's snapshot rows do not (`build/fuel_five.py`, the Landing notes).
2. **The checks still hold what 071 asked.** Every row raises as before, above its floor.
3. **The judge.** The fast tier and one full run (`-n 3`) against `build/sets/s-c50ca51fae5eb55b`:
   no failure, no lost pass; the ratchet's only moves are these checks' restated fuel.

## Landing notes

Not built yet.
