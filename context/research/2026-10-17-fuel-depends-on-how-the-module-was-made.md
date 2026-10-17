# Fuel depends on how the module was made

- **Status:** placeholder with an executed finding, 2026-10-17. The cause is not found.
- **Owner:** Clay Gendron
- **Researcher:** the author agent (Claude Opus 5.5), from the spec 005 build review's finding 3
  (`../reviews/005-the-3-15-line-2026-10-17.md`).
- **Feeds:** the runner's `fuel_used` contract (README, "Running it"); any later use of fuel as
  a price or a budget (the principal engineer's memo, direction "fuel-priced execution").
- **Blocks:** nothing today. The judge's driver (`tests/harness/guest.py`) always compiles in
  its own process, so the judge's fuel figures are consistent; the one runner check that
  records fuel (`test_a_cpp_exception_reaches_python`) passes `cache_dir=False`.

## The finding (EXECUTED: wasmtime-py 49.0.0, the 3.15 artifacts, `wasi_python.run` with
`fuel=10**12`, each line a fresh process; the cache directory private, as the runner requires)

| binary | program | compiled in the process | loaded from the `.cwasm` | difference |
|---|---|---|---|---|
| snapshot | `pass` | 124,130,225 | 81,823,271 | −42.3M |
| snapshot | `sum(range(10**6))` | 1,014,156,397 | 971,797,080 | −42.4M |
| plain | `pass` | 246,595,679 | 241,639,813 | −5.0M |
| plain | `sum(range(10**6))` | 1,143,525,783 | 1,138,165,581 | −5.4M |

- The difference is about constant per binary, not proportional to the work, so it sits in
  start-up or shutdown, not in the program's own loop (INFERRED).
- The guest's output is the same either way; the `.cwasm` bytes are identical across runs (the
  review, EXECUTED).
- The 3.14 artifacts show the same: snapshot `-c pass` 117.6M compiled, 76.8M loaded (the
  review, EXECUTED).

## The question

Why does a deserialized module consume less fuel than the same module compiled in the
process? Candidates to test, cheapest first: wasmtime's handling of the memory image
(copy-on-write from the `.cwasm` versus initialised at instantiation) and whether any fuel is
charged while it is initialised; a difference in which functions are compiled with fuel checks
(lazy or inlined trampolines); and whether the runner's two engines' configurations match
exactly when a module is serialised and read back. The experiment: the same module compiled,
serialised with `Module.serialize`, and deserialised in one process, with fuel read after
`instantiate` and after `run`, separately.

## What it decides now

`fuel_used` is comparable only between calls whose module came the same way. The README says
so. Checks that record fuel through the runner pass `cache_dir=False`.

## One line

A module loaded from the `.cwasm` cache counts a constant few tens of millions fewer
instructions than one compiled in the process, with the same output; until the cause is known,
fuel from the runner is compared only like with like.
