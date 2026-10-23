# Review of 013 — The limits are checked (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the constitution, `context/reviews/README.md`, the 011 pre-build review (for its format), finding 8 of the 008 build review, the specification, the runner, the judge's driver (`tests/harness/guest.py`), and the wasmtime-py 49 and wasmtime 49 code named below. I did not rely on the specification's summary of wasmtime. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/013-the-limits-are-checked.md` as drafted (untracked). The runner is `src/wasi_python/runner.py` at `513455e`, clean.
- **Ran (EXECUTED, darwin-arm64, host CPython 3.14, wasmtime-py 49.0.0, the artifacts in `build/artifacts/` read only, `WASI_PYTHON_CACHE=$PWD/build/cwasm-cache`).**
  - Scripts and outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev013a/`:
    - `p1_bounds.py` → `p1_bounds.txt`: each limit at and past its boundary, on today's runner;
    - `p2_types.py` → `p2_types.txt`: numpy scalars, `Fraction`, `Decimal`, the `numbers` ABCs, and non-str `argv`/`env`/non-bytes `stdin`, on today's runner. It ran under `uv run --with numpy`, an ephemeral environment; `pyproject.toml` and `uv.lock` are untouched;
    - `p3_rule.py` → `p3_rule.txt`: the spec's deadline rule, evaluated as written, with no wasm.
  - I read the author's `limits_before.txt`. My `p1` reproduces its fuel and memory rows.
  - I did not run `uv run pytest`. Nothing is built yet, and the scoreboard is the build review's job.

## What holds

- **The defect is real, and the two unsafe rows are right.** EXECUTED (`p1_bounds.txt`): `fuel=-2**63` and `fuel=-2**64-1` run to exit 0 with a negative `fuel_used`. A negative `memory_bytes` runs with no cap. Both remove a limit. A host that computes a budget can hit them.
- **Checking first, before any work, is the right shape.** READ, `runner.py:125-138`. The defaults are filled in at lines 125-131. The artifacts are found, and the engine and module made, only after that. So a check placed after line 131 runs before anything is created, with or without `root=`. With `root=`, `_place_stdlib` writes into the root only at line 140.
- **`TypeError` for a wrong type and `ValueError` for a bad value** is the Python convention. Naming the argument and the rule in the message is right.
- **Refusing `bool` is right.** EXECUTED: `fuel=True` is a budget of 1, `output_bytes=True` keeps one byte (`out=b'o'`), and `memory_bytes=True` traps at instantiation.
- **The `memory_bytes` bound is exactly right.** READ: wasmtime-py's `set_limits` passes `memory_size` as `ctypes.c_int64` (`wasmtime/_bindings.py:2488-2492`). The C API applies the limit only when it is `>= 0` (`crates/c-api/src/store.rs:193-219` in `wasmtime-v49`). So 2⁶³ − 1 is the largest value that means "a cap".
- **The deadline cap is needed, and `NO_DEADLINE` is a sound bound.** READ: `set_epoch_deadline` takes `c_uint64` (`_bindings.py:2542-2546`). wasmtime stores `current_epoch + delta` with a plain add (`crates/wasmtime/src/runtime/store.rs:2231-2239`). EXECUTED: `deadline_s=2**64*0.01` traps at once (2⁶⁴ ticks wraps to 0), and `deadline_s=1e30` gets an arbitrary deadline. The engine's epoch grows by about 100 per second. A delta below 2⁶² cannot wrap in any real process life. `_stop_at` and the ticker's count are Python ints, so they cannot overflow (READ, `runner.py:596-600`, `1051-1104`). So `ticks < NO_DEADLINE` is the right rule. The largest deadline it accepts is about 4.6 × 10¹⁶ s, about 1.46 billion years (EXECUTED, `p3_rule.txt`).
- **No existing caller passes a value the new rules refuse.** READ, by grep of `tests/`, `src/` and `scripts/`:
  - the checks pass `fuel` from 10⁹ to 5 × 10¹⁰;
  - they pass `memory_bytes` from `1 << 20` to `560 << 20`;
  - they pass `deadline_s=0.2` or `None`;
  - `test_memory_has_a_default_cap` swaps in `Defaults(128 << 20, 60.0, 16 << 20)`, which passes. The judge's driver (`tests/harness/guest.py:146`, `220`) does not go through `run`. It calls `store.set_fuel` itself, with `DEFAULT_FUEL = 2 * 10**11`. So it is untouched by the change. Nothing else calls `_call` or `_instance` (READ).

## Acceptance criteria against evidence

1. The unit tests and the v1.4 check exist and are seen failing first. Checkable as written. Today `run(fuel=-1)` returns exit 0 (EXECUTED), so the v1.4 check fails first. The unit list misses the cases in findings 1, 2 and 4.
2. `uv run pytest` green with `--accept-judge`. Right: new checks change the judge hash.
3. A dry run of the release workflow passes. Right, since `README.md` and `CHANGELOG.md` change.

## Findings, most severe first

1. **The deadline rule, as written, raises `OverflowError` on finite inputs.** Medium.
   - EXECUTED (`p3_rule.txt`). Take the rule literally: `math.isfinite(d) and d > 0 and math.ceil(d / TICK_S) < NO_DEADLINE`. Then:
     - `deadline_s=1.7e308` is finite, but `d / TICK_S` is `inf`. `math.ceil` raises `OverflowError: cannot convert float infinity to integer`.
     - `deadline_s=10**400` is an `int`. `math.isfinite` raises `OverflowError: int too large to convert to float`, and so does `10**400 / 0.01`.
   - Today the same two inputs raise the same errors (EXECUTED, `p1_bounds.txt`). So the specification's own aim, "no confusing errors from deep inside", would miss them.
   - Fix: say that the check must turn every out-of-range value into `ValueError`. For example: convert with `float(d)`, catching `OverflowError`; test that the value is finite and positive; then compare `d / TICK_S` against `NO_DEADLINE` (an `inf` quotient fails the comparison, with no `ceil`). Add `1.7e308` and `10**400` to the unit tests.
2. **A strict `int` refuses numpy integers that work correctly today.** Medium. It breaks callers, and it buys no safety.
   - EXECUTED (`p2_types.txt`). Today `fuel=np.int64(10**8)`, `fuel=np.uint64(2**64-1)`, `memory_bytes=np.int64(1<<30)`, `output_bytes=np.int64(1)` and `deadline_s=np.int64(5)` all behave correctly. `Fraction(1, 2)` works as a deadline.
   - `np.int64` is not an `int` subclass. So `isinstance(x, int)` refuses it. This project's users are people who compute with numpy and pandas. A budget read out of a DataFrame is an `np.int64`.
   - `np.float64` is a `float` subclass, so a strict `float` already takes it. `np.float32` is not, and it works today.
   - Proposal:
     - For the three integer limits, accept anything `operator.index` takes. Refuse `bool` explicitly (`np.bool_` already fails `operator.index`). Then pass on `int(value)`.
     - For `deadline_s`, accept `numbers.Real` except `bool`, and pass on `float(value)`. That takes `int`, `float`, `np.float32`, `np.int64` and `Fraction`. It refuses `Decimal`, which is not registered as `Real` and fails today too. `str` is refused.
     - `_check_limits` should return the normalised values, and `run` should use them. Today an `np.int64` fuel makes `fuel_used` an `np.int64` (EXECUTED). Plain values also protect the rest of the runner from an `int` subclass that overrides arithmetic.
   - The unit tests need no numpy (§4.13). A small class with `__index__` stands in for `np.int64`, and `Fraction` stands in for a non-float `Real`.
   - If the author keeps the strict rule instead, the specification must say so. It must name `np.int64` as refused, and the CHANGELOG must say it. That is a break in working code.
3. **The fuel bound's reason is wrong. wasmtime takes fuel as an unsigned 64-bit count.** Medium-low.
   - READ: wasmtime-py passes `set_fuel` as `c_uint64` (`_bindings.py:2518-2522`), and `get_fuel` reads a `c_uint64` (`_store.py:77-90`). The C API takes `u64` (`crates/c-api/src/store.rs:260-275`).
   - READ: inside wasmtime, `set_fuel` puts at most `i64::MAX` into the VM's signed counter. It keeps the rest in a `u64` reserve and refuels from it when the counter runs out (`crates/wasmtime/src/runtime/store.rs:1478-1515`). The signed count is an internal detail; it is not a limit on the caller.
   - EXECUTED (`p1_bounds.txt`): `fuel=2**63` and `fuel=2**64-1` both run to exit 0. They report a correct `fuel_used` (81,968,982 and 82,057,280). The author's own probe shows the same for `2**63`.
   - So the true maximum is 2⁶⁴ − 1. The specification may still choose 2⁶³ − 1: it matches `UNMETERED`, and 2⁶³ instructions is about 290 years at 10⁹ per second. But then the "why" column must say that this is a choice, not wasmtime's limit. Refusing 2⁶³ to 2⁶⁴ − 1 is also a small break: those values work today. I lean to 2⁶⁴ − 1 for `fuel`, because it refuses nothing that works. Either is acceptable if the reason is true.
   - The comment on `UNMETERED` (`runner.py:53`, "the most fuel a store takes") is wrong for the same reason. Correct it in the same change.
4. **The defect table misses four ways a value quietly changes meaning.** Low-medium. Each one argues for the specification, and each should get a unit test at its boundary.
   - EXECUTED (`p1_bounds.txt`). ctypes masks an integer to the C type's width; it does not raise. So:
     - `memory_bytes` from 2⁶³ to 2⁶⁴ − 1 means **no memory limit** (it wraps negative). This is a third unsafe row, beside the two the table names. `memory_bytes=2**64 + (64 << 20)` becomes a 64 MiB cap.
     - `fuel` of 2⁶⁴ or more is taken modulo 2⁶⁴. `fuel=2**64+5` is a budget of 5. `fuel=10**30` runs with a meaningless `fuel_used` of about 10³⁰.
     - A deadline of 2⁶⁴ ticks or more wraps. It traps at once, or gets an arbitrary deadline (see "What holds").
   - EXECUTED: `output_bytes=1.5` drops **all** output and still returns exit 0, with `truncated == ('stdout',)`. The table lists `output_bytes=-1` only.
   - EXECUTED: `deadline_s=True` is a one-second deadline. The table should say whether `bool` is refused for `deadline_s` too. "Wherever an int is asked for" can be read either way, since the deadline asks for "int or float". I recommend refusing it, for the same reason.
5. **The scope's reason for leaving out `argv`, `env` and `stdin` is not true.** Low.
   - The specification says wasmtime-py "already type-checks them with clear errors". EXECUTED (`p2_types.txt`):
     - `stdin` never reaches wasmtime-py. The runner writes it with `Path.write_bytes`. `stdin="abc"` raises `TypeError: memoryview: a bytes-like object is required`. But `stdin=""` and `stdin=0` are falsy, so they silently become an empty stdin.
     - `env={"A": 1}` and `argv=["-c", 1]` raise `AttributeError: 'int' object has no attribute 'encode'`. `env={1: "x"}` raises `TypeError` from `sorted`. None of these name the argument.
     - `argv="-c"` (a str, not a list) is split into `["-", "c"]`. It returns exit 0 with no output.
     - A NUL truncates silently. With `env={"A": "x\0y"}` the guest sees `A='x'`. A program argument holding a NUL is cut short, and the guest exits 1.
     - With `env={"A=B": "c"}` the guest sees `A='B=c'`.
   - None of these removes a limit. So leaving them out of a specification about limits is reasonable. But give the true reason: "they do not remove a limit". Do not say "wasmtime-py checks them". The silent NUL truncation changes what the guest sees. Record it for a later specification, or as a gap with its closer.
6. **Counting "the temporary directory" can be flaky. Use the pattern that already exists.** Low.
   - `tempfile.gettempdir()` is shared by every process of this user. Another pytest run, or another agent's probe, makes `wasi-python-*` entries there at any time. Two agents have shared this tree before (the 011 review records one).
   - `test_a_call_without_a_root_shares_nothing` (`tests/checks/test_v1_2_hostile_guest.py:154`) already points `tempfile.tempdir` at a fresh directory with `monkeypatch` and asserts that it stays empty. Do the same. Also run the `root=` form and assert that the root is still empty: no stdlib zip placed. Optionally pass `artifacts=` an object that raises on any attribute access. That shows the check ran before the artifacts were looked up.
7. **Tiny positive deadlines behave as 0 did. The reason given for refusing 0 does not hold.** Low.
   - EXECUTED: `deadline_s=1e-300` and `5e-324` give one tick today, and the program prints and then traps. That is exactly what `deadline_s=0` and `-1` do. The new rule accepts the first two and refuses the last two.
   - So "a deadline of 0 or less cannot be met" is not the reason. Neither can 10⁻³⁰⁰ s. The honest reason is this: 0 or a negative value is almost always a bug in the caller's arithmetic. Any positive deadline rounds up to at least one tick of `TICK_S`. Say both. Note in the README that the deadline's resolution is one tick.
   - Pre-existing, and outside this specification: `ceil(0.07 / 0.01)` is 8 ticks, not 7, because 0.01 is not exact in binary (EXECUTED, `p3_rule.txt`). It does no harm. Leave it.
8. **The CHANGELOG line should be specified. It is a change for existing callers.** Low.
   - READ: `v0.1.0a1` is tagged. Its `run` already took `fuel`, `deadline_s` and `memory_bytes` and passed them on in the same way (`git show v0.1.0a1:src/wasi_python/runner.py`, lines 60-98). `0.1.0a2` is unreleased. Its CHANGELOG already has a "`run` changes for existing callers" list under *Safe by default*.
   - So, yes, it needs a line. The specification should give its content: `run` now checks its four limits before doing anything. A wrong type raises `TypeError`. A negative or too-large value, a deadline of 0 or less, a non-finite deadline, or a `bool` raises `ValueError` or `TypeError`; before, such a value removed a limit or failed deep inside. If finding 2 is not taken, also name `np.int64`. If finding 3 keeps 2⁶³ − 1, also name fuel above it.
9. **A bad `DEFAULTS` raises an error naming an argument the caller never passed.** Low.
   - READ: `DEFAULTS` is read at call time, and checks swap it with `monkeypatch` (`test_v1_2_hostile_guest.py:171`). An embedder can do the same.
   - After Decision 1, a broken default makes `run` raise, for example, "memory_bytes must be …; got -1". The caller never passed that argument.
   - Either add "(from `DEFAULTS`)" to the message when the value came from the defaults, or check in `Defaults.__post_init__`, so a bad default fails where it is made. Decision 3's unit test still holds either way.

## Constitution checks

- §4.4 two imports, §4.6 artifacts: untouched. The change is host-side only.
- §4.5 embedder-neutral: holds. The rules name no embedder.
- §4.9 tests count: holds. The checks count directory entries and compare exceptions. Finding 6 makes the count local to the test.
- §4.10 evidence: the specification's probe is quoted and reproducible. Two claims are not true as stated: the reason for the fuel bound (finding 3), and "wasmtime-py already type-checks" `argv`, `env` and `stdin` (finding 5).
- §4.13 tooling: no new dependency. Finding 2's tests need no numpy. My probe used numpy in an ephemeral `uv run --with numpy` environment only.
- §7 never-do list: nothing tripped. The new checks change the judge, so `--accept-judge` is needed, as acceptance criterion 2 says.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1 — Fixed (Decision 2): every out-of-range deadline raises `ValueError`, including overflowing arithmetic; `1.7e308` and `10**400` are unit-tested.
2. Finding 2 — Taken as proposed (Decision 2): integer limits through `operator.index` with `bool` refused, the deadline as any `numbers.Real` but `bool`; the check returns plain `int` and `float`, which the runner passes on.
3. Finding 3 — Kept 2⁶³ − 1 with an honest reason (Decision 2): one rule for every integer limit, equal to `UNMETERED`, whose comment is corrected; the spec states that wasmtime itself takes up to 2⁶⁴ − 1.
4. Finding 4 — Fixed: the four cases are in the defect table; `memory_bytes=2**63` is a third unsafe case and is in the v1.4 check; each has a boundary unit test; `bool` is refused for the deadline too.
5. Finding 5 — Fixed (Scope): the reason is now "none of them removes a limit", and the confusing cases, the NUL truncation first, are recorded for a later specification.
6. Finding 6 — Fixed (Decision 4): the v1.4 check points `tempfile.tempdir` at a fresh directory and also passes a `root=`, counting both.
7. Finding 7 — Fixed (Decision 2): 0 or less is refused as a caller's bug; any positive deadline rounds up to one tick.
8. Finding 8 — Fixed (Decision 5): the CHANGELOG line and its place are specified.
9. Finding 9 — Fixed (Decision 3): `Defaults.__post_init__` applies the rules, so `run`'s errors always name an argument the caller passed.

## Reviewer's confirmation, 2026-10-17

I re-read the revised specification against each disposition. I also prototyped the revised Decision 2 in scratch, outside the tree, to check that the rules are total: `rev013a/c1_rules.py` → `c1_rules.txt`, run under `uv run --with numpy`. Nothing under `build/` was touched.

1. **Finding 1 — confirmed.** Decision 2 says every out-of-range deadline raises `ValueError`, overflow included, and Decision 4 unit-tests `1.7e308` and `10**400`. EXECUTED in the prototype: convert with `float()` and catch `OverflowError`, then test that the value is finite and positive, then compare the quotient before calling `ceil`. With that order, `1.7e308`, `10**400`, `Fraction(10**400)`, `nan`, `inf` and `np.float32('nan')` all give `ValueError`, and nothing else escapes. The literal `ceil(…) < NO_DEADLINE` in the table needs that order. The required tests enforce it.
2. **Finding 2 — confirmed.** EXECUTED: `np.int64(5)` becomes `int` 5. `np.int64`, `np.float32` and `Fraction(1, 2)` become plain `float` deadlines. `True`, `np.bool_`, `1.5`, `"1"` and `Decimal` raise `TypeError`. Small wording point: Decision 1's example message says "must be an int". "An integer" fits `operator.index` better.
3. **Finding 3 — confirmed.** The reason is now true: wasmtime takes up to 2⁶⁴ − 1, and 2⁶³ − 1 is a stated choice. The `UNMETERED` comment is to be corrected. The choice refuses `np.uint64(2**64-1)` and plain 2⁶³ to 2⁶⁴ − 1, which run today (EXECUTED). Decision 5's CHANGELOG wording ("out of range") covers that.
4. **Finding 4 — confirmed.** The four rows are in the table. `memory_bytes=2**63` is counted as unsafe and is in the v1.4 check, which fails today because that call runs to exit 0. `bool` is refused for every limit.
5. **Finding 5 — confirmed.** The scope's reason is now true. Note: the constitution (§5.2) allows no backlog. So the NUL truncation should have a named home, such as a gap entry or a placeholder memo cited in the landing notes, not only this scope list. This does not block the build.
6. **Finding 6 — confirmed.** The check uses the existing `tempfile.tempdir` pattern, passes a `root=`, and counts both directories.
7. **Finding 7 — confirmed.** The reason is now "a caller's bug", and the one-tick rounding is stated. EXECUTED: the prototype accepts `1e-300` and refuses `0` and `-1`.
8. **Finding 8 — confirmed.** The CHANGELOG line and its place are given.
9. **Finding 9 — confirmed, with one clarification to make while building.** The revision dropped the words "after the defaults are filled in" from Decision 1. `__post_init__` checks a `Defaults` but does not normalise it: the dataclass is frozen. So a `Defaults` holding an `np.int64` would still pass a numpy scalar on, unless `run` also sends filled-in defaults through `_check_limits`. Either keep "called after the defaults are filled in" in the specification, or have `__post_init__` store the plain values (with `object.__setattr__`). This is INFERRED from the text. It does not block the build.

### Verdict (confirmation)

All nine dispositions are confirmed. It can be built. Two clarifications should go into the text or the build:

- the check runs after the defaults are filled in, or `Defaults` normalises its own values (item 9);
- the NUL truncation gets a named home outside this scope list (item 5).

## Verdict

Ready to build once the text is revised. The design is sound: check first, `TypeError` for a wrong type and `ValueError` for a bad value, `bool` refused, a deadline capped below `NO_DEADLINE`, and the `memory_bytes` bound exactly right. Before building:

- make the deadline check total, so no `OverflowError` escapes (finding 1);
- decide numpy integers and other `Real` values, and normalise what is passed on (finding 2);
- correct the reason for the fuel bound, or raise the bound to 2⁶⁴ − 1 (finding 3);
- add the missing rows and their boundary tests (finding 4);
- isolate the "creates nothing" check (finding 6).

The rest are wording. None of the findings needs new research.

One line: check the limits at the door as drafted, but make the check total and honest. It must never raise from inside its own arithmetic, it should take numpy integers, and fuel's real ceiling is 2⁶⁴ − 1.
