# Review of 008 — Fuel counts the guest only (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the constitution, `context/reviews/README.md`, the 006 build review (for its format), specification 008 with its landing notes, its pre-build review with the dispositions and the confirmation, and the research memo with its experiment. Then I read the diff. I did not rely on the landing notes. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** commit `f6b67ac` (12 files). Added at the coordinator's request: the uncommitted change to `tests/harness/scoreboard.py` and `tests/unit/test_scoreboard.py` (`accept()` drops a metric no longer recorded when growth is accepted), which is to land with 008. The artifacts in `build/artifacts/` (reactor `4e2b2470…`, the same build spec 006 was accepted on).
- **Re-ran (EXECUTED, darwin-arm64, wasmtime-py 49.0.0).** Probes and outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev008b/` (`probes/`, `mutations.txt`, `mutations-m4m5.txt`, `metric-deltas.txt`, `p1_*.txt`, `p2_*.txt`).
  - `uv run pytest -m "not slow"` → `114/121 pass · 1 gap · 2 blocked · 0 fail · 4 deselected` (unit 161/161); `275 passed, 2 skipped, 4 deselected, 1 xfailed`; ratchet `lost 0 · gained 3 · grew 1 · judge changed`; `RED: 1 metric(s) grew` (the C++ check's fuel, "no longer recorded").
  - `uv run pytest` (full) → `118/121 pass · 1 gap · 2 blocked · 0 fail`; `279 passed, 2 skipped, 1 xfailed`; the same single GREW line; **exit 1**. The new checks (`test_no_start_section[plain|snapshot]`, `test_fuel_does_not_depend_on_the_module_cache`, the two unit tests) all pass.
  - Mutations on a scratch mirror of the tree (`git archive HEAD`, run with `uv run --project <repo>` and `WASI_PYTHON_ARTIFACTS`), each restored and compared with `cmp`. Table below.
  - The pre-change runner (`git archive f6b67ac^`) against the same probes, for "before".
  - `uv run ruff check src tests` → all passed; `uv run ruff format --check src tests` → 38 files already formatted.
  - I did not run `scripts/build.sh`, touch `build/artifacts/`, edit a tracked file, commit or push. My pytest runs rewrote `build/progress/latest.json` (untracked build state). I did not run the release workflow (criterion 3).

### Mutations (EXECUTED)

| mutation | check run | result |
|---|---|---|
| M1 runner sets the cap before `instantiate` (the old code) | the v1.4 cache check | **fails**: `compiled 124,214,355, loaded 81,808,101` |
| M2 driver sets the cap before `instantiate` | `test_fuel_counts_no_memory_image_copy` | **fails**: `16388 == 3` |
| M3 `start_section_errors` never fires | `test_start_section_rule_names_a_start_function` | **fails** |
| M4 runner sets the cap after `_initialize` | all of v1.4, v1.2 hostile, `test_api.py` | **passes** (finding 2) |
| M5 driver sets the cap after `_initialize` | `tests/unit/test_guest.py`, v1.4 | **passes** (finding 2) |
| S1 remove the new `elif` in `scoreboard.accept` | `tests/unit/test_scoreboard.py` | **fails** the new test only |

## Acceptance criteria against evidence

1. *The cache check was seen failing before the change; the start-section rule was seen failing on its WAT module.* **Met.** EXECUTED: M1 reproduces the cache check's failure by the image charge (42,406,254 apart; the notes saw 124,252,680 vs 81,846,084). M3 and the WAT module show the rule failing. M2 shows the driver's unit test failing by one host page (16,385).
2. *`uv run pytest` green; the fuel metrics drop as Decision 4 says, the exceptions named; accepted with `--accept-judge`.* **Not met yet.**
   - The run is red until the C++ check's dropped metric is accepted. That needs `--accept-growth` as well as `--accept-judge`, and the scoreboard fix below (finding 4).
   - The drops hold. Against `accepted.json`: 36 fuel metrics; 34 drop by exactly their charge (16 by 42,352,641, 18 by 5,046,273); 2 miss it by tens. But the two named are not the notes' three (finding 3).
3. *A dry run of the release workflow passes every job.* **Not shown.** The landing notes do not report one for this change, and I did not run it.

### Decisions 1–4 against the diff

- **Decision 1 (READ, EXECUTED).** Both `runner._instance` and `guest.run` set `2**63 - 1` before `linker.instantiate` and the cap straight after, before `exports` and `_initialize`. The runner does both only when `fuel is not None`; the driver always meters, as the decision says. Nothing between `instantiate` and `set_fuel` can run guest code: the only call is `set_fuel` itself. `instance.exports(store)` is after it. `_initialize` runs after the cap, so it is metered: M4 makes plain `-c pass` read 240,845,185 against 241,415,896 as built, about 570,000 instructions the cap would otherwise miss. `fuel_used` is still `cap - get_fuel()`. But when `instantiate` itself fails, that formula now reads the unmetered budget (finding 1).
- **Decision 1, the deadline.** `set_epoch_deadline` and the ticker are set before `instantiate`, as before; instantiation is still under the deadline. EXECUTED (`probes/p4_start_loop.py`): a start function that loops forever under `2**63 - 1` fuel traps with `INTERRUPT` after 0.011 s. Its fuel reads 2 spent, so the epoch path does not bring fuel up to date, which the runner already handles by reporting `None` on "deadline".
- **Decision 2 (READ, EXECUTED).** `START_SECTION = 8` is right (the core spec's section id). The rule parses the binary and checks the section ids; it passes on both shipped binaries and fails on `WITH_START`.
- **Decision 3 (READ, EXECUTED).** The check runs two fresh `-I` processes on one private cache, asserts the writer compiled and wrote and the loader loaded, and bounds the difference at 1,000,000. It fails under M1 by 42.4M and passes as built.
- **Decision 4.** See criterion 2 and finding 3.

## Findings, most severe first

1. **When `instantiate` fails, `fuel_used` is about −9.2 × 10¹⁸** (`src/wasi_python/runner.py` `_instance`, lines 264–312; `tests/harness/guest.py` 146–228). Medium.
   - The store holds `UNMETERED` until `instantiate` returns. If it raises, the cap is never set. The `except wt.WasmtimeError` reports the trap, and `counted` is true, so `fuel_used = fuel - get_fuel()` subtracts the unmetered budget.
   - **Failure (EXECUTED, `probes/p1_instantiate_fails.py`).** `run(["-c", "pass"], fuel=10**9, memory_bytes=1<<20 or 16<<20, deadline_s=None)` on either binary returns `trapped='memory minimum size of 902 pages exceeds memory limits'` (640 on the plain reactor) and `fuel_used=-9223372035854775807`. The pre-change runner returns `fuel_used=0` for the same calls (`p1_old.txt`).
   - **Why it matters.** It is reachable with a public argument: a `memory_bytes` below the module's minimum (57.7 MiB for the snapshot). A caller that bills or budgets by `fuel_used` gets a huge negative number, which can credit an account or overflow a signed 64-bit column. The driver's `Result.fuel` has the same flaw, though no current check reaches it.
   - **Fix.** Count only once the cap is set. For example, set a flag after `store.set_fuel(fuel)` and report `0` (nothing of the guest ran) when it is unset. Do the same in the driver. Add a check: the call above returns `fuel_used == 0` with the limit's message. It counts and times nothing (§4.9). AGENTS.md rule 3: a failure mode, once seen, becomes a check.

2. **"`_initialize` stays metered" is true but unguarded** (`runner.py:296–301`, `guest.py:218–227`). Low.
   - EXECUTED: M4 (runner) passes every v1.4, v1.2-hostile and API check. M5 (driver) passes `test_guest.py` and v1.4. The new unit test uses a command module, which has no `_initialize`.
   - In the judge, M5 would make every plain-reactor metric drop by `_initialize`'s cost. The ratchet treats a drop as fine, so it would be accepted unnoticed.
   - **Fix.** A unit test on the driver with a WAT reactor whose `_initialize` spends a known amount (a counted loop), asserting the reported fuel includes it. Optionally the same through the runner with a test artifact set; the driver test alone closes the judge side.

3. **The landing notes' named exceptions are one pair of runs, not a stable list.** Low.
   - EXECUTED (`metric-deltas.txt`), my full run against `accepted.json`: `test_nothing_is_a_shared_library` drops 5,046,239 (−34 from the charge) and `test_numpy_and_pandas_are_builtin_at_manifest_versions[plain]` drops 5,046,239 (−34). `test_numpy_csv_job_matches_native` and `test_random_matches_native` drop exactly.
   - The author's own `latest.json` (copied before my runs) against `accepted.json`: the same two, but the shared-library check is −17.
   - The notes name a different three (shared-library −34, numpy CSV +34, random +17) against a re-measured "before".
   - So the per-check residue moves from run to run by tens, as Decision 4 predicted for inode hashing. The decision holds. But "programs that write files" is too narrow: `numpy_and_pandas_are_builtin[plain]` only imports (INFERRED: it `stat`s files, and wasmtime hashes inode numbers).
   - **Fix.** Restate the notes as: 36 fuel metrics; all drop by their charge to within tens of instructions; which ones miss it, and by how much, varies between runs. Then list the pair that the acceptance run actually shows against `accepted.json`.

4. **The landing needs `--accept-growth` and the scoreboard fix, and the notes do not say so.** Low.
   - EXECUTED: both runs are red on `GREW test_a_cpp_exception_reaches_python: fuel is no longer recorded`. Criterion 2 names only `--accept-judge`.
   - READ: with `HEAD`'s `accept()`, an accepted check that records nothing keeps its old metrics, so the GREW line could never clear. The coordinator's change fixes that (S1 below).
   - **Fix.** Accept with `--accept-judge` (naming the 008 judge files and `scoreboard.py`) and `--accept-growth` (naming the C++ metric, removed in 006 for real-clock noise). Say so in the landing notes and in criterion 2.

5. **The new fuel guards are live on macOS and Windows only, and the README's "on every operating system" is inferred for Linux and Windows** (`README.md:177–181`; `test_v1_4_embedding.py`, `test_guest.py`). Low.
   - INFERRED from the research's source reading: on Linux, wasmtime maps the image through a `memfd` whether compiled or loaded. So both fuel checks pass on Linux with or without the change. The verify job runs on `ubuntu-24.04`, `windows-2025` and `macos-15` (`.github/workflows/release.yml:91`, READ), so two of three hosts guard it.
   - Nothing here ran on Linux or Windows. The README states the cross-OS sameness as fact and cites the memo, which labels it INFERRED.
   - **Fix.** Say in the cache check's docstring that it is vacuous on Linux. Let the dry run (criterion 3) on all three hosts be the evidence for the README's sentence, and cite it in the landing notes.

6. **The CHANGELOG's "5.5% more instructions than on 3.14" was measured under the old count** (`CHANGELOG.md:26`). Low.
   - READ: 124.0M vs 117.6M (both with the image copy) is about 5.4%. Under the new definition the memo's guest-only figures are 81.9M vs 76.8M (3.14, loaded from the cache): about 6.6% (arithmetic on READ figures; not re-measured on 3.14).
   - The same section now says fuel "counts the guest only", so a reader takes 5.5% as the guest's figure.
   - **Fix.** Restate it as about 6.6% of guest instructions, citing the memo, or label the 5.5% as including the image copy.

7. **The no-start-section rule is enforced on the shipped binaries only, not at run time.** Low, for the record.
   - READ: `run(artifacts=…)` loads whatever module the caller names. With a start section, that module's start function would run before the cap is set.
   - EXECUTED (`probes/p4_start_loop.py`): such code is stopped by the epoch deadline. With `deadline_s=None` and only a `fuel` cap, nothing would stop it.
   - The guest cannot add a start section or a data segment. It does not control the artifact, and the unmetered work for the shipped set is wasmtime's memory fill, bounded by the artifact's size. So for the shipped set, `fuel` remains a hard bound on the guest's instructions (READ, EXECUTED: caps of 0, 1 and 1,000 trap "out of fuel" at exactly the cap).
   - **Fix (optional).** One sentence in the README: `fuel` bounds the guest only for artifacts without a start section, which the shipped ones are judged to be.

8. **Pre-existing, not this change: `fuel` is not validated.** Low, out of scope.
   - EXECUTED (`p2_old.txt`, `p2_new.txt`): `fuel=-1` runs unbounded and reports `fuel_used=-18446744073…`. `fuel=2**64` traps at once and reports `fuel_used=2**64`. The behaviour is the same before and after 008.
   - A billing-minded caller would want `0 <= fuel < 2**63` enforced. This is for a later specification, not for this landing.

### The scoreboard change (uncommitted; the coordinator's addition)

S1. **The condition is right.** No defect found. One Low note.
   - **The change.** In `accept()`, when a check's run recorded no metrics, the check `pass`ed, and `--accept-growth` was given, its metrics for this platform are dropped. Otherwise they are kept, as before.
   - EXECUTED: the new unit test passes. Removing the `elif` fails it and nothing else (S1 in the table).
   - EXECUTED: an edge probe in the mirror (removed afterwards). One run had three checks:
     - one that passed and recorded nothing: dropped;
     - one `blocked` on `artifact dir`: kept, because blocked and deselected checks skip the loop before the new branch;
     - one that grew: replaced.

     A `fail` that records nothing keeps its figure.
   - So a check that "passed without recording because a need was unmet" cannot happen: an unmet need is `blocked`, never `pass`.
   - READ: metric recording is unconditional per call site (the `guest` fixture's static `record=`, and the two `bytes` sites). So a passing check with no metrics is a code change. `compare()` lists it as growth first, so a drop is never silent before acceptance.
   - **The Low note.** The scoreboard prints only the first three GREW lines (`scoreboard.py:349`), and the history line records `growth_reason` but not which metrics were dropped. Suppose a future edit stopped the `guest` fixture recording fuel. One `--accept-growth` would then drop every fuel metric at once, with three shown and none listed in the history. **Fix (optional).** Print the GREW count with "and N more", or list the dropped `(node, metric)` pairs in the history line.
   - This is a judge change: name `scoreboard.py` in the `--accept-judge` reason. AGENTS.md rule 4 makes a judge change its own change; landing it beside 008, with the reason stated, satisfies that.

## Constitution checks

- §4.1 zero patches, §4.2 pins, §4.3 one target, §4.4 two ways out: untouched. No recipe, source tree or import changes; `test_no_start_section` adds a guard on the binaries.
- §4.6 artifact set: unchanged; no `.cwasm` published.
- §4.9 tests count: the new checks count instructions and assert equality or a fixed bound; none times anything.
- §4.10 claims carry evidence: mostly. Findings 3, 5 and 6 are claims that need restating or labelling.
- §4.13 tooling: ruff clean; no dependency added.
- §7: nothing tripped.

## Disposition (filled in by the author)

1. **Fixed.** Runner and driver count fuel only once the cap is set; a failed instantiation reports 0. `test_a_failed_instantiation_reports_no_fuel` (v1.4) fails without the fix (EXECUTED); the unit test `test_a_failed_instantiation_spends_nothing` covers the driver.
2. **Fixed.** `test_initialize_is_metered`: a reactor whose `_initialize` loops 1,000 times costs at least 3,000 more than one that does not.
3. **Fixed.** The landing notes say the missing few change between runs and that any `stat` sees inode numbers.
4. **Fixed.** The landing notes name both flags and the scoreboard fix.
5. **Fixed.** The README says macOS was measured, Linux never charged, Windows is expected. The dry run is dispatched after landing; its result goes in the next landing notes.
6. **Fixed.** The CHANGELOG says 6.6% (81.9M against 76.8M).
7. **Noted.** A caller's own module through `artifacts=` is outside the shipped set's rules; the README's `artifacts` is for the artifact set.
8. **Noted** for a later change: `fuel` is not validated (negative or too large).

S1: confirmed by the review; the `--accept-judge` reason names `scoreboard.py`.

## Verdict

**Does not land yet.** Finding 1 must be fixed first: a reachable argument makes `fuel_used` about −9.2 × 10¹⁸ where it was 0, and it needs a check. Findings 2 to 6 are small: one more unit test, and corrections to the notes, the CHANGELOG and the README. They can be fixed or answered in writing. The core change is right:
- both drivers meter from the end of instantiation;
- nothing of the guest runs before the cap is set;
- the cap still bounds the guest exactly;
- the new checks fail when the change is undone.

The scoreboard fix is sound and may land with it.

One line: the meter now starts at the right place; fix the garbage count when instantiation fails, guard `_initialize`, accept with `--accept-growth`, then land.
