# 013 — The limits are checked

- **Status:** landed, 2026-10-17. Reviewed before build
  (`../reviews/013-the-limits-are-checked-spec-2026-10-17.md`) and after
  (`../reviews/013-the-limits-are-checked-2026-10-17.md`).
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`), judge additions in `tests/`, `README.md`,
  `CHANGELOG.md`.
- **Depends on:** 006 (the defaults), 008 (fuel counts the guest).
- **Research it stands on:**
  - Spec 008's build review, finding 8 (`../reviews/008-fuel-counts-the-guest-2026-10-17.md`):
    `fuel` is not validated.
  - The author's probe, EXECUTED on the current runner and artifacts. The script is
    `limits_probe.py` in scratch; its output is quoted below.

## The defect

`run` takes four limits: `fuel`, `deadline_s`, `memory_bytes` and `output_bytes`. It passes them
on unchecked, so a wrong value can quietly mean the opposite of what the caller wanted.

| argument | what happens today (EXECUTED) |
|---|---|
| `fuel=-1` | **runs unbounded**, exit 0, `fuel_used` −18,446,744,073,627,579,482 |
| `fuel=2**64` | traps at once, `fuel_used` 2⁶⁴ |
| `fuel=True` | a budget of 1 instruction (`bool` is an `int`) |
| `fuel=1.5` | raises ctypes' `ArgumentError` from inside wasmtime-py |
| `memory_bytes=-1` | **no memory limit**: the call runs, exit 0 |
| `memory_bytes=1.5` | raises `ArgumentError` |
| `deadline_s=-1` or `0` | one tick: the program runs a little, prints, then traps |
| `deadline_s=nan`, `inf`, `"1"` | raises `ValueError`, `OverflowError` or `TypeError` from the tick arithmetic |
| `output_bytes=-1` | a cap of 0 |
| `memory_bytes` from 2⁶³ to 2⁶⁴ − 1 | **no memory limit** (wasmtime reads it as a signed 64-bit value; the review, EXECUTED) |
| `fuel` or deadline ticks at 2⁶⁴ or more | wrap around (the review, EXECUTED) |
| `output_bytes=1.5` | all output dropped, exit 0 (the review, EXECUTED) |
| `deadline_s=True` | a 1 s deadline (the review, EXECUTED) |

Three of these are unsafe for the users this project serves: a negative `fuel`, a negative
`memory_bytes` and a `memory_bytes` of 2⁶³ or more each remove the limit. A host that computes a budget, such as "what is left of
the tenant's allowance", can pass a negative number by accident, and the guest then runs
unmetered. The rest are confusing errors from deep inside the runner.

## Decisions

1. **`run` checks its limits first, before any work.** It checks before it finds the artifacts,
   compiles or makes a root. A wrong value raises at once, and nothing is created.
   - A wrong **type** raises `TypeError`.
   - A value of the right type but **out of range** raises `ValueError`.
   - The message names the argument and the rule. For example: `fuel must be an int from 0 to
     2**63 - 1, or None; got -1`.
2. **The rules.** `None` keeps its meaning: no limit, or unmetered for `fuel`. `bool` is refused
   for every limit, because `True` would quietly mean 1 (or 1 s). The check returns plain values,
   which the runner passes on, so a numpy scalar never reaches wasmtime or `fuel_used` (the
   review, EXECUTED: an `np.int64` fuel made `fuel_used` an `np.int64`).

   | argument | accepted | range |
   |---|---|---|
   | `fuel` | anything `operator.index` takes (an `int`, a numpy integer), passed on as `int` | 0 to 2⁶³ − 1 |
   | `memory_bytes` | the same | 0 to 2⁶³ − 1 |
   | `output_bytes` | the same | 0 to 2⁶³ − 1 |
   | `deadline_s` | any `numbers.Real` (an `int`, a `float`, a numpy float, a `Fraction`), passed on as `float` | finite, > 0, and `ceil(deadline_s / TICK_S) < NO_DEADLINE` |

   - **`memory_bytes`:** 2⁶³ − 1 is wasmtime's own ceiling. It reads the value as a signed 64-bit
     number, and anything negative, including 2⁶³ and above, means no limit (the review,
     EXECUTED).
   - **`fuel`:** wasmtime takes an unsigned 64-bit count, so 2⁶⁴ − 1 would work (the review,
     EXECUTED). The ceiling is 2⁶³ − 1 anyway: one rule for every integer limit, the same number
     as `UNMETERED` (which this change re-comments truthfully as the budget instantiation runs
     on), and far beyond any real budget.
   - **`output_bytes`:** an integer, so 1.5 is refused rather than read as 1.
   - **`deadline_s`:**
     - Any out-of-range value raises `ValueError`, including those whose arithmetic overflows:
       `1.7e308 / TICK_S` is infinity, and `float(10**400)` raises `OverflowError` (the
       review, EXECUTED). Both are unit-tested.
     - A deadline of 0 or less is refused because it is almost always a caller's bug. Any
       positive deadline, however small (`1e-300`), rounds up to one tick of `TICK_S`, as today.
     - The `NO_DEADLINE` bound is the epoch's own (the review, READ: wasmtime adds the ticks to
       the current epoch, and 2⁶² leaves room).

   `fuel=0`, `memory_bytes=0` and `output_bytes=0` keep today's behaviour.
3. **The defaults are checked where they are made.** `Defaults.__post_init__` applies the same
   rules, so `DEFAULTS`, or a replacement an embedder builds, can never hold a value that `run`
   would refuse. An error from `run` therefore always names an argument the caller passed.
4. **Checks.**
   - Unit tests of the checking function, row by row:
     - each wrong type, `bool` among them;
     - each bound and the value just past it;
     - `nan`, `inf`, `1.7e308`, `10**400` and `1e-300`;
     - numpy integers and floats, and a `Fraction`, which come back as plain `int` or `float`;
     - `None`.
   - A unit test that `Defaults` refuses a bad value.
   - A v1.4 check that `run(fuel=-1)`, `run(memory_bytes=-1)` and `run(memory_bytes=2**63)`
     raise `ValueError` and create nothing. It points `tempfile.tempdir` at a fresh directory, as
     `test_v1_2_hostile_guest.py` does, and also passes a `root=`. Then it counts both
     directories' entries, so it does not depend on the shared system temporary directory.
   - Each new test is seen failing first.
5. **The CHANGELOG** adds one line to 0.1.0a2's "`run` changes for existing callers" list:
   `run` now refuses a limit that is the wrong type or out of range, where 0.1.0a1 passed it on
   (a negative `fuel` or `memory_bytes` meant no limit).

## Intent

A limit means what it says. A value that would quietly remove a limit, or a type that would
quietly change it, is refused at the door of `run`.

## Design

```
src/wasi_python/runner.py   _check_limits(fuel, deadline_s, memory_bytes, output_bytes) -> the
                            plain values, called first in run; Defaults.__post_init__
tests/unit/test_runner_limits.py   the rules
tests/checks/test_v1_4_embedding.py   negative fuel and memory raise and create nothing
README.md, CHANGELOG.md
```

## Scope

In: the four limits. Out, because none of them removes a limit:
- `argv`, `env` and `stdin`. These are confusing today (the review, EXECUTED):
  - `stdin=""` or `0` silently becomes empty input;
  - a non-str value raises `AttributeError` without naming the argument;
  - a str `argv` is split into characters;
  - **a NUL in an argument or an env value silently cuts it short.**

  They are recorded in `../research/2026-10-17-what-run-does-with-its-inputs.md` (a
  placeholder) for a later specification.
- `root` and `host`.

## Acceptance criteria

1. The unit tests and the v1.4 check exist and were seen failing before the change.
2. `uv run pytest` is green with `--accept-judge`.
3. A dry run of the release workflow passes every job.

## Landing notes

Built 2026-10-17 by the author agent; reviewed in
`../reviews/013-the-limits-are-checked-2026-10-17.md`. The review's fixes:
- a v1.4 check that `run` passes on the plain values (an `__index__` fuel and output cap, and
  `DEFAULTS` of them), which fails when the pass-through is removed (EXECUTED);
- the refusal check also passes an `artifacts=` that must not be touched;
- the deadline's top edge is unit-tested;
- the docs name the deadline ceiling, the 10 ms ticks and numpy integers;
- a huge integer is named by its size in the message. The reviewer's confirmation of the
pre-build review raised two points, both taken:
- `run` runs the filled-in defaults through `_check_limits` too, so plain values reach wasmtime
  even from a `Defaults` that holds numpy values. `__post_init__` only checks them.
- The NUL truncation has a placeholder memo.

**Seen failing first** (EXECUTED): before the runner had `_check_limits`, all 16 new tests failed.
That is 13 unit tests in `tests/unit/test_runner_limits.py` and the three cases of
`test_a_limit_that_would_remove_itself_is_refused`. In those three, `run(fuel=-1)` and the two
memory caps ran the guest instead of raising.

**After** (EXECUTED): all 16 pass. The author's probe, run again:
- `fuel=-1`, `2**63` and `2**64`, `memory_bytes=-1`, `output_bytes=-1` and a deadline of `-1`,
  `0`, `nan` or `inf` raise `ValueError`;
- `fuel=True`, `fuel=1.5`, `memory_bytes=1.5` and `deadline_s="1"` raise `TypeError`;
- `fuel=0`, `memory_bytes=0` and `output_bytes=0` behave as before.
