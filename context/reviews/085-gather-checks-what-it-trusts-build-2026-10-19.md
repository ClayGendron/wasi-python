# Build review of 085 — `gather` checks what it trusts, 2026-10-19

- **Reviewer:** the agent that reviewed and confirmed 085's specification. I wrote none of its
  code.
- **Under review:**
  - the build commit `9128176`;
  - the landing-notes commit `0819b53`;
  - both on `spec/085-gather-checks-what-it-trusts`, over main `9d89535`.

  I read `git diff 9d89535 9128176` in full: the code, the tests, the workflow, the docs and the
  research files.
- **Measured against:**
  - the confirmed specification: Decisions 1 to 9;
  - the disposition of my F1 to F8;
  - my confirmation's builder notes c1 and c2.
- **How I ran things:**
  - **Set.** A private clone of `build/sets/s-c50ca51fae5eb55b-c9dcb5b8` (`build-review/set`),
    used through `WASI_PYTHON_ARTIFACTS`.
  - **Record.** Written to my scratch folder with `--progress-latest`, so the builder's
    `build/progress/latest.json` was not touched.
  - **"Seen failing first".** Rebuilt in an export of `9d89535` (`build-review/old/`).
  - **Forgeries.** My own, against the built gather (`work/forge_built.py`), on both runs' real
    records.
  - **Hidden-needs probe.** Against the built `hidden_ci_needs`, on planted trees (`work/fake/`).
  - **Git.** I wrote nothing in any git tree; `git status` in the worktree is clean.

Labels: **EXECUTED** (I ran it), **READ**, **INFERRED** (reasoned, not run).

## Short version

The build matches the confirmed specification, and every decision is in the code as written.

- **The forgeries are caught.** Each one from the specification, and each of mine that the
  specification covers, is red on the built gather. Each adds exactly its own line over the
  honest baseline.
- **No false red.** The honest records of both real runs give no line from the new rules.
- **The workflow agrees with the scan.** The `release.yml` changes meet scan rules 6, 7 and 10
  and the rebuild gate.
- **The shim hides nothing.**
- **The judge.** My full judge (`-n 3`) on `0819b53` matches the builder's exactly: 495/623 pass, 0 fail, lost 0, grew 0.

**One finding must be fixed first, and it is cheap.**

- **B1.** A darwin record whose fuel is `NaN` gets past the ratchet. The cause is that the
  JSON reader accepts `NaN` and the "is a number" rule accepts it as a float. This is the same
  hole as the specification's F1, reached by another road.

**Two low findings.** Both fail closed; neither blocks the landing.

- **B2.** A parametrize literal is invisible to the hidden-needs scan.
- **B3.** Two malformed shapes make the gather raise without printing a reason line.

## 1. The code against the specification (READ)

- **Decision 1 (`gather.py`).**
  - The new pieces:
    - `CI_NEEDS` maps each need to the systems that lack it, with `build` named (F6).
    - `allowed()` is used by G4 and by G5's exemption.
    - `needs_called()` reads `ast` literals in `need(…)` and `….need(…)` calls.
    - `_Collector` derives `may_block` for goal checks only.
  - G4 gives three distinct lines:
    - "blocked by X" for a need CI never lacks, as today;
    - "…which its check does not call";
    - "…which does not block on S".
  - `hidden_ci_needs` matches Decision 1 and takes c1 and c2:
    - module constants in `tests/harness/` are flagged;
    - `VOCABULARY_FILES` are skipped before parsing.
- **Decision 2.** G4 requires `suite` to be a dict holding `passed`, `skipped` and `total`. Each
  must be a whole number (`type(x) is int`, at least 0), and `total` must equal
  `meta.units.count`. A tally with the right shape but some unit tests failed keeps today's line.
  `merge` adds only whole numbers (a departure I accept: otherwise a string tally raised before
  any red line was printed).
- **Decision 3.**
  - G2 binds `meta.wasmtime` to `locked_version("wasmtime")`, which reads `uv.lock` with
    `tomllib`.
  - G5 names every darwin-arm64 metric that `accepted.json` holds and the record lacks, leaving
    out `wasmtime`.
  - G5 also flags a metric value that is not an int or a float (a bool fails). This is where B1
    lives.
- **Decision 4.**
  - `run_meta` records `set_sums`, and `scoreboard.accept` writes it into the history line.
  - G1 guards the handed-on hash and G2 compares each record with it.
  - G7 compares the newest history line with it; a missing key counts as a mismatch.
  - The merged record's `meta` and the green line both carry it.
- **Decision 5.** No schema change. `test_history.py` covers lines without `set_sums` followed by
  one with it.
- **Decision 6 (N5).** Both rebuild jobs print `python3 --version`, and the rebuild gate requires
  it.
- **Decisions 7 to 9** are prose and match the code. The documents changed are the CHANGELOG, the
  README sentence, the progress README and spec 063's amendment.

## 2. The release workflow against the scan, and what could make a release red (READ, INFERRED)

**The build job.**

- A new step with id `set-sums` runs
  `shasum -a 256 build/artifacts/SHA256SUMS | cut -c1-64`. It comes after the build and the
  build shard, and before "Release assets" and the upload.
- The job output `set-sums-sha256` is wired to it.
- Scan rule 6 now requires the hashing step, its file and its place before the upload.

**The gather job.**

- The guard step binds `SET_SUMS_SHA256`. Its `case` and length test match `WASM_SHA256`'s.
- The gather step's `env:` gains exactly that one line, which is what rule 7's exact-env test
  requires.
- Rule 10 now says only `build` sets `set-sums-sha256` and only `gather` reads it.
- The builder's extra unit test, the departure, holds the guard step's 64-hex test.

**What else could turn a real release red** (beyond the expected G7 line on the branch's dry
run), checked one by one:

- **G2 on `meta.wasmtime`.**
  - Every record of both real runs carries `49.0.0`, which is what `uv.lock` names (EXECUTED).
  - `test_locked_version` ties the lock to the installed version in `own-rest`.
  - A future wasmtime bump moves the lock and the install together.
- **G2 on `set_sums`.**
  - The build record hashes `build/artifacts/SHA256SUMS`.
  - The judge legs hash the same file, unpacked from a tarball that has already been checked
    against `sums-sha256`.
  - The tarball copies the file byte for byte (my spec review, EXECUTED). Unpacking on Windows
    does not rewrite its line endings.
- **G4 and G5's new rules.** On the honest records of both runs they add no line (§4, EXECUTED).
- **A missing `SHA256SUMS`.** If the file were missing when the step runs, `$(…)` would print an
  empty hash. The gather's guard then stops the run with a reason, so it fails closed, the same
  way the `python.wasm` step does.
- **After acceptance.** The lane's history line carries the main tree's `set_sums`. The dry run
  of main is green when CI's set equals the lane's, as it did for a7 (`c9dcb5b8` in both). Under
  037 it would not be; that is criterion 6b and question 105.

I found nothing else that can turn a real release red.

## 3. "Seen failing first", and the shim (EXECUTED)

`old_inputs.py` is a `pytest_configure` plugin. It replaces `gather.Inputs` with a wrapper that
drops the three new fields (`set_sums_sha256`, `wasmtime`, `may_block`), so that the new test
file can call today's gather.

I rebuilt the run in an export of `9d89535`: the new `test_gather.py`, the shim on
`PYTHONPATH`, and `-p old_inputs` (`build-review/old/`). The result:

- **20 forgeries fail by assertion.** Today's gather prints no matching line for any of them.
  ("A suite of strings" also fails by assertion, through the expected `TypeError` path.)
- **The good-set test fails only on its new text**, the "· set S" ending of the green line. So
  today's gather is already green on the new good set, which includes the honest blocks
  `ART`/`DESC`. That means the good set is not tuned to the new code.
- **The new helper tests fail with `AttributeError`**: `needs_called`, `hidden_ci_needs` and
  `locked_version` do not exist yet.
- **The 37 old tests still pass.** The shim breaks no existing mutation.

The shim cannot make a test pass, and it cannot change which line a test asserts. It only
removes arguments that today's gather has no field for. It hides nothing. The 12 other tests
(scan, plugin, scoreboard, history) fail on `9d89535` without any shim (`seen_failing_others.out`,
READ).

## 4. My forgeries against the built gather (EXECUTED)

**The set-up** (`work/forge_built.py`):

- the built `gather.gather`, with `collect()`'s real `may_block`, and `locked_version` from the
  worktree's `uv.lock`;
- the real records of the a7 tag run (accepted at `2737b29`) and of 065's dry run (accepted at
  `9d89535`), each given `meta.set_sums = c9dcb5b8…`, as a leg of 085 would record it;
- for each forgery, the lines it adds over that run's own honest baseline.

**The honest baselines** contain no line from the new rules.

- **a7:** G3 ×99, because its collection predates 065, and G7 ×1, the `set_sums` line.
- **065:** G3 ×2, because 085's unit tests move `own-rest`'s share, and G7 ×1.

**The forgeries.** Both runs give the same verdict on every row.

| forgery | added lines |
|---|---|
| `gap` for an accepted pass (linux) | G4 (not in `known_gaps.toml`) and G5 lost |
| descriptor `[snapshot]` blocked on macOS | G4 "…does not block on macos" |
| macOS fuel ×10, `meta.wasmtime` `48.0.0` | G2 wasmtime only |
| macOS fuel ×10, `meta.wasmtime` null | G2 wasmtime only |
| macOS fuel ×10, honest wasmtime (the control) | G5 grew ×5 |
| macOS fuel `Infinity` | G5 grew ×5 |
| **macOS fuel `NaN`, every own-guest check** | **none: green (B1)** |
| linux fuel `NaN`, or negative | none (values off darwin are not compared, Decision 9) |
| linux fuel swapped between two checks | none (Decision 9) |
| `set_sums` of another set in one record | G2 `set_sums` |
| another commit | G2 |
| a duplicated record with `meta.shard` renamed | G3 ×2 |
| suite `{540, -2, 538}` | G4 suite |
| suite given as a list | G4 suite |
| `need` given as a list | the gather raises `TypeError` (B3) |
| `metrics` given as a list (linux) | the gather raises `AttributeError` (B3) |

These match the builder's `built_on_real.out`. On both runs, each of the seven forgeries adds
exactly its own lines, and the wasmtime forgery adds only its G2 line.

## 5. The hidden-needs probe against the built scan (EXECUTED)

- **The repository.** `hidden_ci_needs` returns nothing, both on the worktree and on main's tree.
- **My earlier fake tree.** All six plants are flagged:
  - a list in `tests/conftest.py`;
  - a `NEED_OF` value;
  - `need(*("three systems",))` in a fixture;
  - an f-string `"needs: {x}"`;
  - a keyword argument `need="oracle"`;
  - a plain module constant `X = "three systems"` (c1, now taken).
- **An annotated constant** (`X: str = "oracle"`) is flagged too.
- **Not flagged** (B2):
  - `@pytest.mark.parametrize("n", ["oracle"])` on a `test_` function whose body calls
    `need(n)`;
  - a class attribute `NEED = "prior-art clones"` in a harness file;
  - an `IfExp` such as `"three systems" if … else ""`;
  - a local variable inside a harness function.

  All of these fail closed in the gather. The parametrize case slips through because `ast.walk`
  of a `FunctionDef` also visits its decorators and its default arguments, so the scan counts
  them as "inside the body". The specification's Decision 1 says a parametrize spelling is
  found before a dry run; for literals in the decorator, it is not.

## Findings, most severe first

- **B1. Medium. `NaN` fuel gets past the darwin ratchet** (EXECUTED, on both runs' records).
  - **The cause.** Python's `json.loads` accepts `NaN` and `Infinity`. G5's new rule accepts any
    float. The ratchet's `value > old × (1 + tolerance)` is false for `NaN`.
  - **The effect.** A macOS record whose every fuel value is `NaN` is green.
  - **Why it matters.** Decision 3 promises "each a number", and Decision 7 says the cheap lies
    on darwin are closed. This is F1's hole by another road.
  - **The fix** is one of these, with a forgery row for `NaN` (and one for `Infinity` if the
    first option is chosen):
    - make `_number` require `math.isfinite`;
    - or load records with `json.loads(…, parse_constant=…)` that rejects `NaN` and `Infinity`,
      so the record is red at G1 as "not a run record".
- **B2. Low. Literals in a check's decorator are invisible to the hidden-needs scan** (EXECUTED).
  - Exclude `decorator_list` and `args` (defaults included) from the "inside the body" set.
    Optionally, also flag class-level assignments in `tests/harness/`.
  - Or narrow Decision 1's sentence to say what is still left to the dry run.
  - Either way it fails closed.
- **B3. Low. Two malformed shapes raise instead of printing a reason line** (EXECUTED).
  - A `need` that cannot be hashed (a list) raises `TypeError` in the `CI_NEEDS`/`may_block`
    lookups.
  - A `metrics` value that is not a dict raises `AttributeError` in `scoreboard.compare`, which
    the G5 `try` does not catch: it catches only `KeyError` and `TypeError`.
  - Both fail closed: the job exits non-zero. Before 085 the first raised too.
  - Optional: an `isinstance` guard giving a G4 or G5 line. Not a condition.

## Notes

- **The departures are sound:** `merge` adds only whole numbers, the scan test holds the guard
  step, and the header form changed. The c1 and c2 notes were taken as asked.
- **N1. The fast tier was not run separately.** The full judge runs every fast-tier check, and
  the lane's serial judge was running on the machine, so I ran one `-n 3` judge only. The
  builder's fast tier had one failure, the specification's header; it is fixed, and its full
  judge shows 0 fail.

## The judge, re-run (EXECUTED)

**The run.**

- **Command:** `uv run pytest -n 3 -p no:cacheprovider --progress-latest <scratch>`.
- **Commit:** `0819b53` (the build `9128176` plus documents only).
- **Set:** my private clone of `s-c50ca51fae5eb55b-c9dcb5b8`, through `WASI_PYTHON_ARTIFACTS`.
- **Log:** `build-review/full-n3.log`.
- **An earlier run was killed** at 19% when the owner paused work. I discarded it and re-ran from
  the start.

**The result.**

- **Scoreboard:** `wasi_python v1: 495/623 pass · 3 gap · 125 blocked · 0 fail (unit suite
  1622/1630, 8 skipped)`.
- **Ratchet:** `lost 0 · absent 0 · unrun 0 · unrun locally 49 · gained 0 · grew 0 · upstream unrun
  99 · judge changed: tests/harness/gather.py, tests/harness/plugin.py, tests/harness/scan.py and
  6 more`.
- **pytest:** 2117 passed, 133 skipped, 3 xfailed, exit 0.
- These are the builder's numbers exactly.
- The 125 blocked checks are this worktree's missing source trees, clones, oracle and compile
  records, as in any worktree.

**The record.** `build-review/full-n3-latest.json`, kept for the lane's sameness step.

- `meta.set_sums` is `c9dcb5b84ae2…`, the set's own `SHA256SUMS`, as Decision 4 says.
- `meta.wasmtime` is `49.0.0`.
- `dirty` is false and `workers` is 3.
- Its one override, `--progress-latest`, kept the builder's `build/progress/latest.json`
  untouched.
- `git status` in the worktree is clean after the run.

## Verdict

**Lands once B1 is fixed.**

- B1 means finite fuel values only, with a `NaN` forgery row (and an `Infinity` row if
  `_number` changes), seen failing first.
- B2 and B3 are written in or answered in writing.
- The fix to B1 is a few lines and a test row. It moves no number, and it needs only a delta
  look, not a new full review.

## One line

085 is built as specified and catches every forgery it set out to catch. Close the `NaN` road
around the darwin fuel ratchet, which is F1's hole by another road, and it lands.

## Addendum: the fixes (2026-10-19)

**What I read.**

- `git diff 0819b53..337ceb5` in the -085 worktree.
- The fixes are in `c378ba2`. `337ceb5` adds only the fast-tier notes.
- The code change is `tests/harness/gather.py` and `tests/unit/test_gather.py`, plus the spec and
  the research files.

I wrote nothing in any git tree.

**B1: fixed (EXECUTED).**

- `_number` now accepts an `int`, or a `float` that `math.isfinite` accepts. A `bool` is still
  refused.
- `test_gather.py` has forgery rows for `NaN` and `Infinity`.
- `seen_failing_build_review.out` shows both rows failing on `0819b53`, and the B3 rows and the
  B2 scan test failing with them (5 failed).
- My `work/forge_built.py`, on the real records of both runs:
  - `NaN` fuel on every macos own-guest check now adds exactly 124 G5 lines ("metric fuel is not
    a number"). This matches the builder's `built_on_real.out`.
  - `NaN` fuel on Linux also adds 124 lines.
  - `Infinity` adds 129 lines (the G5 lines plus the ratchet's growth).
- **Unchanged:**
  - the honest baselines: a7 has G3 ×99 and G7 ×1; 065 has G3 ×2 and G7 ×1; neither has a line
    from the new rules;
  - every other row of my table;
  - negative fuel and swapped fuel off darwin stay green, as Decision 9 intends.

**B2: fixed (EXECUTED).**

- The scan now marks only a `test_` function's body statements as inside the body. Decorators
  and default arguments are outside it.
- In `tests/harness/` it now also flags class attributes, and constants reached through an
  `if … else` expression.
- On my planted trees the built scan flags:
  - the `parametrize("n", ["oracle"])` decorator;
  - the class attribute;
  - the `IfExp` constant;
  - all six earlier plants.
- It still misses a local variable inside a harness function. Decision 1 now says so in words.
- On the worktree and on main's tree the scan returns nothing.

**B3: fixed (EXECUTED).**

- A `need` given as a list now gives the G4 line `blocked by ['oracle']`. `allowed()` refuses any
  need that is not a string.
- `metrics` given as a list now gives `G5 …: metrics is not a mapping`.
- The ratchet's `AttributeError` is caught as "not comparable".
- `merge` turns a need that is not a string into its `repr`, so the merged record can still be
  written.
- The G5 metric loop now runs before `scoreboard.compare`. The lines it prints are the same, in a
  new order.

**The owner's answers are written in consistently** (READ).

- Question 105 is answered (b): 086 lands before 037, with no exception. Decision 8, *Scope*,
  criterion 6 and *Coordination* say this, and G7 stays exact. Criterion 6b is removed, with a
  dated note that it was superseded.
- Decision 9 is declined "not now".

**Tests (EXECUTED).**

- The five unit files touched by 085 (`test_gather`, `test_scan`, `test_plugin`,
  `test_scoreboard`, `test_history`), run with `-n 3`: 411 passed.
- **A full judge was needed.** The verdict risk is low, since only `gather.py` and its test
  changed. But my earlier record came from `0819b53`, and the four new unit tests change the
  record's `suite` (1630 to 1634), which `sameness.py` compares. So the lane's sameness step needs
  a reviewer record from the final commit.
- I re-ran the full judge with `-n 3` on `337ceb5`, against the same private set (log
  `build-review/full-n3-337ceb5.log`):
  - `495/623 pass · 3 gap · 125 blocked · 0 fail (unit suite 1626/1634, 8 skipped)`;
  - ratchet: lost 0, absent 0, unrun 0, gained 0, grew 0 (judge changed);
  - pytest: 2121 passed, 133 skipped, 3 xfailed, exit 0;
  - record `build-review/full-n3-337ceb5-latest.json`, with `set_sums` `c9dcb5b84ae2…`,
    wasmtime `49.0.0`, dirty false;
  - **this record replaces the one from `0819b53`** for the lane's sameness step.
- `git status` in the worktree is clean.

**Lands.**
