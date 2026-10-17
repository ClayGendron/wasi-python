# Issue 1: wasmtime-py's `LAST_EXCEPTION` crosses threads

Status: **ready for the owner's review.** Nothing was posted. Base:
`bytecodealliance/wasmtime-py` main at `280ce73` (2026-09-24).

## The fix

`fix.patch` (4 files, +107 −14):

- `wasmtime/_func.py`: `LAST_EXCEPTION` becomes a `threading.local` subclass
  with one attribute, `exn`. The trampoline writes `LAST_EXCEPTION.exn`;
  `maybe_raise_last_exn` reads and clears it.
- `wasmtime/component/_enter.py`: the same change for the component path
  (`catch_exceptions` writes, `maybe_raise_last_exn` reads).
- One test in `tests/test_func.py` and one in `tests/component/test_func.py`.

Why thread-local is right (INFERRED from READ code): every reader and writer
of the slot runs on the thread that called into wasm. The writers are the
core `trampoline` and the component `catch_exceptions` (used by `func_impl`
and `resource_dtor_impl`). The readers are `maybe_raise_last_exn`, called
only from the two `enter_wasm`s. Wasmtime runs host functions synchronously
on the calling thread in the sync API. The one callback that runs on other
threads, the WASI custom output (`_wasi.py:197`), never touches the slot.

## Every reader and writer (READ)

| file | line (main) | role |
|---|---|---|
| `wasmtime/_func.py` | 14 | definition |
| `wasmtime/_func.py` | 213–214 | write, in `trampoline` |
| `wasmtime/_func.py` | 244–250 | read and clear, `maybe_raise_last_exn` |
| `wasmtime/_func.py` | 237, 240 | callers, in `enter_wasm` |
| `wasmtime/component/_enter.py` | 7 | definition |
| `wasmtime/component/_enter.py` | 18–19 | write, in `catch_exceptions` |
| `wasmtime/component/_enter.py` | 37–43 | read and clear |
| `wasmtime/component/_enter.py` | 33 | caller, in `enter_wasm` |

`enter_wasm` (core) is used by `Func.__call__`, `Instance.__init__`,
`Linker.instantiate` and `InstancePre.instantiate`; the component
`enter_wasm` by `Func.__call__`, `Func.post_return` and `ResourceAny.drop`.
`catch_exceptions` is used by `func_impl` and `resource_dtor_impl`.

## Evidence (all EXECUTED, macOS arm64, Python 3.14.2)

Dev setup: wasmtime-py expects `wasmtime/<host>/_libwasmtime.dylib`; CI gets
it with `ci/download-wasmtime.py`, pinned to v49.0.0. I copied the library
from the installed wasmtime 49.0.0 wheel instead (sha256 `2cc7e377…7c13`);
main's `_bindings.py` is identical to the wheel's. Test tools at the
`uv.lock` versions: pytest 9.0.1, pytest-mypy 1.0.1, mypy 1.18.2. With
mypy 2.4.0, unpinned, main itself fails 7 mypy checks, so the pin matters.

- `evidence/baseline-tests.txt`: unmodified main, 226 passed.
- `evidence/crossing-before.txt`: `crossing_posted.py` on unmodified main,
  2738, 2636 and 2620 of 20000 calls crossed.
- `evidence/crossing-after.txt`: with the fix, 0 of 20000, five runs.
- `evidence/tests-after.txt`: with the fix, 228 passed, mypy clean.
- `evidence/new-tests-on-unfixed-main.txt`: both new tests fail on
  unmodified main.
- `evidence/race-on-main.txt`: `race.py` (the `FUNCTIONS` slab race) gives
  0 failures on main, and 2759 of 4000 on the 49.0.0 wheel.

## What I tried and rejected

- **A per-store slot.** It would also work, but a store has no Python object
  that the trampoline can reach cheaply (it gets a `wasmtime_caller_t *`),
  and a store is meant to be used from one thread at a time anyway (#322).
  Thread-local is the smaller change.
- **A lock around the global.** It cannot help: the problem is that the slot
  is shared, not that a write is torn.
- **A behaviour-only test.** I looked for a way to hold one thread between
  "host function raised" and "caller read the slot" without patching
  internals. There is no hook in that window (the trampoline's `except`,
  `Trap(...)._consume()`, then Wasmtime's unwind and `Trap._from_ptr`). So
  the tests set the slot directly, as the brief suggested. The weakness:
  on unmodified main they fail with `AttributeError` (the old slot is
  `None`), not by crossing. The reproducer covers the behaviour.

## Findings beyond the brief

- **The slab race is already fixed upstream** (READ, EXECUTED). PR #344,
  merged 2026-09-23, replaced the `Slab` free list with a dict and a
  counter. `race.py` gives 0 failures on main. It is not in a release yet:
  49.0.0 (2026-09-21) predates it. The spec 011 issue draft's first half
  (FUNCTIONS and CUSTOM_OUTPUTS corrupt) is therefore stale; only the
  `LAST_EXCEPTION` and Ctrl-C parts still apply.
- **Our own repo reads the slot** (READ): `tests/unit/test_runner_calls.py:116`
  asserts `_func.LAST_EXCEPTION is None`. If this PR lands and the pin moves
  past it, that assertion must become `_func.LAST_EXCEPTION.exn is None`. Not
  changed here: the brief forbids editing the main repo.
- Open issue #254 ("Make bindings threadsafe", by a maintainer) is the
  umbrella; the PR says it is one piece of it.

## Licence and process (READ)

- wasmtime-py is `Apache-2.0 WITH LLVM-exception` (`LICENSE`,
  `pyproject.toml`). Contributions go in under the same licence (Apache-2.0
  §5).
- No CLA and no DCO sign-off: `CONTRIBUTING.md` and Wasmtime's
  `docs/contributing*.md` mention neither, and no PR template exists.
- No AI-use policy found in `CONTRIBUTING.md` or Wasmtime's contributing
  docs. The squash commit of #344 (main's HEAD) carries a
  `Co-authored-by: Claude` trailer, so at least one AI-assisted PR was
  accepted. The owner should still say in the PR that it was prepared with
  an AI agent.
- CI runs `uv run --all-extras pytest` on Linux, macOS and Windows with
  Python 3.x, 3.9 and PyPy 3.11. I ran only macOS 3.14. INFERRED: the change
  works on 3.9 and PyPy, since `threading.local` subclasses with class
  defaults are long-standing.

## Open risks

- The private name keeps its meaning but changes its type (see above).
- Windows, Linux, 3.9 and PyPy are not run here (INFERRED to pass).

## One line

The slot that carries a host function's exception back to its caller is
now per thread, so a trap on one thread can no longer raise another
thread's exception; 0 crossings in 100,000 calls, tests green.
