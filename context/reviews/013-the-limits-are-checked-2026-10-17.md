# Review of 013 — The limits are checked (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the
  constitution, `context/reviews/README.md` and the 011 build review (for its format). Then I read
  specification 013 with its landing notes, and its pre-build review with the dispositions and
  the reviewer's confirmation. Then I read the diff. I did not rely on the landing notes. Each
  claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** the uncommitted working tree on top of `513455e`:
  - `src/wasi_python/runner.py`, `tests/checks/test_v1_4_embedding.py`, `README.md` and
    `CHANGELOG.md` (the diff);
  - the new `tests/unit/test_runner_limits.py`, the specification and
    `context/research/2026-10-17-what-run-does-with-its-inputs.md`.

  While I worked, other files changed in the tree: notes in specs 011 and 012, and a new spec 014
  with its review. Another piece of work owns them. I ignored them, and none of them touches the
  runner.
- **Re-ran (EXECUTED, darwin-arm64, wasmtime-py 49.0.0, the artifacts in `build/artifacts/` read
  only).** Probes, outputs and the mutation log are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev013b/`
  (`probes/*.py` with their `.txt`, `mutate.py`, `mutations.txt`, `logs/`, `pytest-full.txt`,
  `head_new_tests.txt`).
  - `uv run pytest` → `137/139 pass · 0 gap · 2 blocked · 0 fail (unit suite 254/254)`;
    `391 passed, 2 skipped`; ratchet `lost 0 · absent 0 · unrun 0 · gained 3 · grew 0 · judge
    changed: tests/checks/test_v1_4_embedding.py, tests/unit/test_runner_limits.py`; **exit 0**.
    The acceptance with `--accept-judge` is the author's.
  - `uv run ruff check src tests` → all checks passed. `uv run ruff format --check src tests` →
    42 files already formatted.
  - The probes that needed numpy ran under `uv run --with numpy`, an ephemeral environment.
    `pyproject.toml` and `uv.lock` are untouched.
  - **How I mutated.** I did not edit the tree's runner. Another agent was working in the same
    tree. So each mutation went into a scratch copy of the package (`mut/src/wasi_python/`),
    put first on `PYTHONPATH`, with `WASI_PYTHON_ARTIFACTS` set to `build/artifacts`. I checked
    that `wasi_python.runner.__file__` was the scratch copy. The copy was restored from the
    tree's bytes after each mutation and checked by SHA-256.
  - At the end, the tree's `runner.py`, both test files, the README, the CHANGELOG and the spec
    were `cmp`-equal to copies I took first.
  - I did not commit, push, run `scripts/build.sh` or touch `build/artifacts/`. My pytest runs
    rewrote untracked state under `build/progress/` and `build/harness/`. The only tracked-tree
    file I wrote is this review.

## Decisions against the code

- **Decision 1, check first (READ, EXECUTED).** `run` fills in the defaults, then calls
  `_check_limits`, and only then calls `find_artifacts`, `_engine`, `_module`, `mkdtemp` or
  `_place_stdlib` (`runner.py:179-193`). The only thing before it is `import wasmtime`, which
  creates nothing.
  - EXECUTED (`p2_refused.txt`). I passed 36 refused values, each in four forms: no root, a
    `root=`, an `artifacts=` that raises on any attribute, and both. That is 144 calls.
    - Every call raised `TypeError` or `ValueError`, and every message named the argument.
    - `tempfile.tempdir` (pointed at a fresh directory) and the root stayed empty.
    - The `cache_dir=` I passed was never created, and `find_artifacts` was never called.
- **Decision 2, the rules (READ, EXECUTED, `p1_check.txt`).**
  - Integer limits:
    - `0` and `2**63 - 1` pass. `-1`, `2**63`, `2**64 - 1`, `2**64` and `-2**63` raise
      `ValueError`.
    - `True`, `False`, `1.0`, `1.5`, `"1"`, `Fraction(1)` and `Decimal(1)` raise `TypeError`.
    - An object with `__index__` comes back as a plain `int`, and so does an `int` subclass. An
      `int` subclass whose `__index__` lies is read by its own value, because `operator.index`
      returns the exact `int`.
    - An `__index__` that returns a float gives `TypeError` naming the argument. An `__index__`
      that raises its own `ValueError` passes that error through. That is the caller's own
      object, so it is acceptable.
  - Deadlines:
    - `1e-300` and `5e-324` pass, and run for one tick.
    - `0`, `0.0`, `-0.0`, `-1`, `nan`, `inf`, `-inf`, `1.7e308`, `10**400`,
      `Fraction(10**400)` and `Fraction(-1, 2)` raise `ValueError`. No `OverflowError` escapes.
    - `Decimal`, `True`, `False`, `"1"`, `1j` and an `__index__` object raise `TypeError`.
    - A `float` subclass that overrides `__truediv__` and `__gt__` comes back as a plain
      `float`. Its overrides are never used.
    - `(NO_DEADLINE - 1) * TICK_S` is the float `4.611686018427388e16`. Its quotient rounds to
      exactly 2⁶², so it is **refused**. The largest deadline accepted is
      `4.611686018427387e16` (2⁶² − 1,024 ticks), and the next float up is refused. This is the
      specification's rule (`ceil(...) < NO_DEADLINE`) applied exactly. The message's "at most
      about 4.6e16 s" is true.
  - Numpy (EXECUTED, `p3_accepted.txt`):
    - `np.int64`, `np.int32` and `np.uint64(2**63-1)` pass as `int`. `np.uint64(2**64-1)` is
      refused with `ValueError`, and `np.bool_` with `TypeError`.
    - `np.float32(30)` and `np.int64(30)` deadlines pass as `float`. `np.float32('nan')` and
      `np.float64(0)` are refused.
- **Through `run`, the accepted boundaries behave as before (EXECUTED, `p3_accepted.txt`).** A
  spy on `_instance` recorded the types it was handed.
  - `fuel=0` gives `out of fuel` with `fuel_used` 0. `fuel=2**63-1` runs to exit 0 with
    `fuel_used` 82,015,821 (an `int`).
  - `memory_bytes=0` traps at instantiation, as today. `memory_bytes=2**63-1` runs.
  - `output_bytes=0` drops everything and names `stdout`. `2**63-1` keeps everything.
  - `deadline_s=1e-300` prints, then traps on `deadline`. The largest accepted deadline runs to
    exit 0.
  - `Index`, `Fraction`, the subclasses and numpy values reach `_instance` as plain
    `int`/`float`. `fuel_used` is an `int`. `output_bytes=Index(3)` gives `b'hel'`.
- **Decision 3, the defaults (READ, EXECUTED).**
  - `Defaults(-1, ...)`, a deadline of `0`, and `output_bytes=True` raise when the `Defaults` is
    made.
  - A `Defaults` holding `Index`, `Fraction` or numpy values is accepted and stored as given,
    since the dataclass is frozen. `run` then normalises them: with
    `DEFAULTS = Defaults(Index(1<<30), Fraction(30), Index(3))`, the call printed `b'hel'` and
    `_instance` got `int`, `float`, `int`. So the landing notes' first bullet holds.
  - `Defaults(None, None, None)` is accepted. This matches "`None` means no limit".
- **Decision 4, the checks (READ).** They all exist, with one gap. The deadline's upper bound is
  tested only at `limit * 2`, not at the bound and just past it (finding 3).
- **Decision 5, the CHANGELOG (READ).** The line is there, in the specified list.
- **`UNMETERED`'s comment (READ)** is now true. `LIMIT_MAX`'s comment gives wasmtime's
  memory reason. The fuel reason (one rule for all) is in the specification.
- **The placeholder memo (READ)** names the question, what would answer it and what it blocks,
  as `context/README.md` requires of a placeholder. It records the NUL truncation first. That
  satisfies item 5 of the pre-build confirmation.

## Mutations (EXECUTED, `mutations.txt`, `logs/`)

The tests run were `tests/unit/test_runner_limits.py`, `test_runner_calls.py`,
`test_runner_waits.py`, `tests/checks/test_v1_4_embedding.py` and `test_v1_2_hostile_guest.py`
(107 tests). The baseline, unmutated, passed 107 of 107. "Caught" means a test failed.

| mutation | result |
|---|---|
| integer limit: `bool` refusal dropped | caught: `test_an_integer_limit_refuses_other_types` ×3 |
| deadline: `bool` refusal dropped | caught: `test_a_deadline_refuses_other_types`, the `Defaults` test |
| integer limit: negative check dropped (`0 <=`) | caught: 6, the v1.4 `fuel` and `memory_bytes=-1` cases among them |
| integer limit: upper bound dropped | caught: 4, the v1.4 `memory_bytes=2**63` case among them |
| integer limit: upper bound raised to 2⁶⁴ − 1 | caught: the same 4 |
| integer limit: returns `value`, not the `int` | caught: `test_an_integer_limit_passes_on_a_plain_int` ×3 |
| deadline: no `float()` at all (`seconds = value`) | caught: `test_a_deadline_is_a_positive_finite_real` |
| deadline: returns `value`, not the `float` | caught: the same |
| deadline: overflow handling dropped (no `try`) | caught: the same (`1.7e308`, `10**400`) |
| deadline: catches `ValueError` only | caught: the same |
| deadline: upper bound dropped | caught: the same (`limit * 2`) |
| **deadline: `ticks <= NO_DEADLINE`** | **survives** (finding 3) |
| **deadline: bound raised to `ticks < 2**63`** | **survives** (finding 3) |
| deadline: `isfinite` and `<= 0` tests both dropped | survives, and is equivalent: `nan` and any value ≤ 0 give `ticks` 0, which `0 < ticks` refuses, and `inf` overflows in `ceil` (INFERRED from the code; EXECUTED, every case in `p1` is still refused by the remaining test) |
| `Defaults.__post_init__` dropped | caught: `test_the_defaults_pass_and_a_bad_default_is_refused` |
| **`run`: checks, but does not pass on the plain values** | **survives** (finding 1) |
| `run`: no check at all | caught: the 3 v1.4 cases |
| **`run`: check moved after `find_artifacts` and the compile** | **survives** (finding 2) |
| `run`: check moved into `_call` (after the root is made and the stdlib placed) | caught: the 3 v1.4 cases |

## Acceptance criteria against evidence

1. *The unit tests and the v1.4 check exist and were seen failing before the change.* **Met.**
   EXECUTED (`head_new_tests.txt`): the committed runner from `git show HEAD:` in a scratch
   package gave 16 failed. That is 13 unit tests (no `_check_limits`) and the three v1.4 cases
   (`DID NOT RAISE ValueError`: the guest ran). This matches the landing notes.
2. *`uv run pytest` is green with `--accept-judge`.* **Met, pending the acceptance run.**
   EXECUTED: exit 0, `lost 0 · absent 0`, and the judge changed in the two named files.
3. *A dry run of the release workflow passes every job.* **Not shown.** Nothing is pushed.

## Findings, most severe first

1. **Nothing checks that `run` passes on the plain values. Without that, the defect Decision 2
   names comes back, and so does a silent loss of output** (`runner.py:186-188`). Medium-low.
   - **The failure (EXECUTED, `p4_passthrough_mutant.txt`).** I kept the call to
     `_check_limits` in `run` but dropped the two lines that use its result. All 107 tests
     still pass. Through that mutant:
     - `fuel=np.int64(10**10)` returns `fuel_used=np.int64(82054938)`. That is the very defect
       Decision 2 cites ("a numpy scalar never reaches wasmtime or `fuel_used`").
     - `fuel=Index(10**10)` raises `TypeError: unsupported operand type(s) for -` after the
       guest has run.
     - `output_bytes=Index(3)` returns exit 0 with `stdout == b''` and `truncated == ()`. All the
       output is lost, and nothing says so.
   - The unit test `test_an_integer_limit_passes_on_a_plain_int` checks `_check_limits` only,
     not that `run` uses what it returns. The landing notes rely on this pass-through for a
     `Defaults` holding numpy values. No test covers that either.
   - **Fix (counts only).** Add a v1.4 case that calls `run(["-c", "print(1)"], fuel=Index(10**10),
     output_bytes=Index(1))` and asserts `type(done.fuel_used) is int` and
     `(done.stdout, done.truncated) == (b"1", ("stdout",))`. Run it a second time with
     `DEFAULTS` monkeypatched to a `Defaults` of `Index` values. The mutant then fails it.
2. **"Before it finds the artifacts or compiles" has no check** (`runner.py:186-193`;
   Decision 1). Low.
   - EXECUTED: the mutant that moves the check after `find_artifacts`, `_engine` and `_module`
     passes all 107 tests. The v1.4 check counts directory entries only. A compile writes into
     the cache directory, not into those.
   - INFERRED from `run` and `_module`: under that mutant, a bad limit on a machine without
     artifacts raises `ArtifactsMissing` instead of `ValueError`. On a cold cache, a refused call
     would also compile for about 3 s and write a `.cwasm` first.
   - **Fix.** In the v1.4 check, also pass `artifacts=` an object that raises on any attribute
     access, and assert `ValueError` still comes out. This is the option the pre-build review's
     finding 6 offered. My `p2_refused.py` does exactly this, and the current build passes it.
3. **The deadline's upper bound is not tested at the bound** (`tests/unit/test_runner_limits.py`,
   `test_a_deadline_is_a_positive_finite_real`). Low.
   - Decision 4 asks for "each bound and the value just past it". The test refuses
     `limit * 2` (about 9.2 × 10¹⁶ s) only. EXECUTED: the mutants `ticks <= NO_DEADLINE` and
     `ticks < 2**63` both survive.
   - The test's own name for the bound, `(NO_DEADLINE - 1) * TICK_S`, is not the last value
     accepted. It is the first value refused (EXECUTED, above).
   - No harm follows from either mutant. wasmtime adds a delta below 2⁶³ to an epoch that grows
     by about 100 a second, so it does not wrap in practice (INFERRED, as the pre-build review
     READ). The gap is in the judge, not in behaviour.
   - **Fix.** Assert that `4.611686018427387e16` passes and that
     `math.nextafter(4.611686018427387e16, math.inf)` raises `ValueError`.
4. **The docs leave out three facts the code now enforces** (`CHANGELOG.md`, `README.md`). Low.
   - The CHANGELOG says "a deadline is a positive finite number". It also has a ceiling, about
     4.6 × 10¹⁶ s. And it must be a real number: `Decimal` is refused, while numpy numbers and
     `Fraction` are taken.
   - Neither file says that numpy integers are accepted and passed on as `int`. A reader whose
     budget is an `np.int64` would want to know.
   - The pre-build review's finding 7 asked the README to say that a deadline's resolution is
     one tick (`TICK_S`, 10 ms), so `1e-300` runs for one tick. Disposition 7 put this in
     Decision 2 only. The README still does not say it.
   - Nits. The list item before the new CHANGELOG line still ends in "." in a list that uses
     ";". `run`'s docstring does not mention the refusal.
5. **An integer of more than 4,300 digits gets an error that does not name the argument**
   (`runner.py:78`, `:94`). Info.
   - EXECUTED: `fuel=10**5000` (and likewise `memory_bytes`, `output_bytes` and `deadline_s`)
     raises `ValueError: Exceeds the limit (4300 digits) for integer string conversion`. The
     f-string that formats the message fails before the message is built.
   - It is still a `ValueError`, raised before any work. Only Decision 1's "the message names
     the argument" fails.
   - **Fix, optional.** Format an out-of-range integer as `got {number:.3g}` or by its digit
     count when it is large, or catch the formatting error.
6. **Housekeeping at landing.** Info.
   - The specification's status line still reads "draft". 010 and 011 changed theirs to
     "landed" with both reviews cited. The landing notes say "build review pending".
   - The `isfinite` and `<= 0` tests in `_deadline_limit` are redundant with `0 < ticks`. The
     equivalent mutant above shows it. They make the rule read clearly, so keeping them is fine.

## Constitution checks

- **§4.1, zero upstream patches.** Holds. Only the runner and the judge change.
- **§4.4, two imports; §4.6, the artifact set.** Untouched. The change is host-side only.
- **§4.5, embedder-neutral.** Holds. The rules name no embedder.
- **§4.9, tests count.** Holds. The new checks compare exceptions, types and directory entries.
  None measures time.
- **§4.10, evidence.** The landing notes' claims reproduce: 16 failed before and 16 pass after
  (EXECUTED), and the probe rows (EXECUTED, `p1`, `p2`). The CHANGELOG's summary is true but
  incomplete (finding 4).
- **§4.13, tooling.** No new dependency: `numbers` and `operator` are stdlib. ruff is clean. The
  unit tests need no numpy.
- **§5.2, no open questions.** The `argv`/`env`/`stdin` cases have a placeholder memo that names
  its question, its experiment and what it blocks.
- **§7, never-do list.** Nothing tripped. The judge changed in two files, so acceptance needs
  `--accept-judge`.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. **Finding 1 — fixed.** A new v1.4 check, `test_a_limit_given_as_another_integer_type_works`,
   calls `run` with an `__index__` fuel and output cap, then again with `DEFAULTS` built from
   `__index__` values. It requires a 3-byte stdout, `truncated == ("stdout",)` and a plain-`int`
   `fuel_used`. EXECUTED: with the pass-through removed, it fails.
2. **Finding 2 — fixed.** The refusal check also passes an `artifacts=` object that fails if
   touched.
3. **Finding 3 — fixed.** The unit test accepts `4.611686018427387e16` and refuses the next
   float up (`math.nextafter`).
4. **Finding 4 — fixed.**
   - The CHANGELOG names the deadline ceiling, that a deadline is a real number (not
     `Decimal`), and that numpy integers are accepted.
   - The README says integer limits take any integer type, and that deadlines count in ticks of
     10 ms, with any positive deadline at least one tick.
5. **Finding 5 — fixed** (for the deadline too, after the confirmation). An integer over 128 bits is named by its size in the message (for
   example, "an integer of 16610 bits"); a unit test checks it.
6. **Finding 6 — fixed at landing.** The status is "landed".

## Reviewer's confirmation, 2026-10-17

I checked the uncommitted fixes in the working tree: the runner, both test files, the README,
the CHANGELOG and spec 013. Logs are in the same scratch folder: `pytest-full2.txt`,
`mutate2.py`, `mutations2.txt`, `logs2/` and `probes/confirm_huge.txt`.

**Re-ran (EXECUTED).**
- `uv run pytest` → `138/140 pass` (unit suite 255/255), `393 passed, 2 skipped`. Ratchet:
  `lost 0 · absent 0 · gained 4`. The judge changed in the same two files. Exit 0.
- `ruff check` and `ruff format --check` are clean.
- I re-ran the five surviving mutations and the new message's mutation. They ran in a scratch
  copy of the package, as before; the baseline passed 109 of 109.
- Afterwards the tree's runner, both test files, the README, the CHANGELOG and the spec were
  `cmp`-equal to copies taken first.

**Each item.**
1. **Finding 1 — confirmed.** I removed the pass-through again. It now fails
   `test_a_limit_given_as_another_integer_type_works`. The test covers an argument and
   `DEFAULTS`. It asserts the 3-byte stdout, the `truncated` value and a plain-`int` `fuel_used`.
2. **Finding 2 — confirmed.** I moved the check after `find_artifacts` and the compile. That
   mutant now fails the three refusal cases, through the `Untouched` artifacts.
3. **Finding 3 — confirmed.** The mutants `ticks <= NO_DEADLINE` and `ticks < 2**63` both fail
   `test_a_deadline_is_a_positive_finite_real`. The equivalent mutant (dropping `isfinite` and
   `<= 0`) still survives, as expected.
4. **Finding 4 — confirmed.**
   - The CHANGELOG names any integer type (numpy's included), "not `Decimal`" and the
     4.6e16 s ceiling.
   - The README names integer types, the 10 ms ticks and the one-tick minimum. The README leaves
     the ceiling to the error message, which is fine.
5. **Finding 5 — confirmed for the integer limits, disputed for `deadline_s`. Info; it does not
   block.**
   - EXECUTED (`confirm_huge.txt`). `fuel=10**5000` now says "an integer of 16610 bits", and
     `2**128 + 1` says "129 bits". The reverted message fails the new unit test.
   - But `deadline_s=10**5000` (or `-10**5000`) still raises Python's "Exceeds the limit (4300
     digits)" `ValueError`, without the argument's name. `_deadline_limit` formats the value
     with `{value!r}`. My finding named `deadline_s` too, and the disposition does not cover it.
   - It is still a `ValueError`, raised before any work. A one-line follow-up fixes it: format a
     huge `int` deadline by its size, as the integer limits now are.
6. **Finding 6 — confirmed.** The spec's status reads "landed" and cites both reviews. Its
   landing notes list the review's fixes.

**Verdict (confirmation).** It lands once the acceptance run (`--accept-judge`) is recorded. The
`deadline_s` half of finding 5 is cosmetic and can follow. Criterion 3, a dry run of the release
workflow, is still to be shown.

## Verdict

Does not land yet. The checking is right: every boundary, type and overflow case I tried gives
the specified error. Nothing is created before a refusal. And every accepted value reaches
wasmtime as a plain `int` or `float`. But the pass-through that Decision 2 and the landing notes
depend on can be removed with the judge still green (finding 1), and a removed pass-through
silently loses output. Add that check, and preferably the ones in findings 2 and 3. Then it lands
once the acceptance run is recorded.

One line: `run` now refuses every limit that would remove itself, before any work, but the judge
does not yet notice if `run` stops passing on the plain values it checked.
