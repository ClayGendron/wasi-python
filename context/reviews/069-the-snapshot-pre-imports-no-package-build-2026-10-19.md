# Review of 069 — The snapshot pre-imports no package (build)

- **Date:** 2026-10-19
- **Reviewer:** a fresh agent (Claude). I wrote the pre-build review of 069 and its confirmation, and none of the code.
- **Reviewed:**
  - `spec/069-the-snapshot-pre-imports-no-package` at `3e00057`, rebased onto main `b413192`.
  - `git diff b413192..3e00057`: 18 files, +1,337 −60.
  - The commits are `f20e311` (the checks first), `fbcae4a` (the code and the documents) and `3e00057` (the landing notes). The spec commits were replayed as `44aac79` and `fca6fe3`.
  - I read it against the spec at `fca6fe3`, the review and its confirmation (F1 to F9, N1 to N4), `tests/harness/scoreboard.py`, `tests/harness/plugin.py` (gaps), and `tests/harness/upstream.py`.
  - I also read the builder's evidence in `069-build/`: the logs, `metrics-full-1.md`, the stand-ins, `linux/` and the cost probes.
- **Re-ran.** The probes are in `probes/` beside this file. Nothing was written in either git tree or in the main tree's `build/`.
  - The fast tier, `uv run pytest -m "not slow" -n 3`: 1,704 passed, 10 skipped, 1 xfailed. The ratchet: lost 0, absent 1 (the retired check), gained 5, grew 20. `ruff check` and `ruff format --check` are clean on `src/` and `tests/`. Log: `fast-review.log`.
  - The full judge, `uv run pytest -n 3`, in the worktree against the builder's set, with the run record sent to this folder (`--progress-latest`): 1,740 passed, 11 skipped, 15 xfailed, in 546.6 s. The ratchet: lost 0, absent 1, unrun 0, unrun locally 2 (the oracle and the prior-art clones), gained 5, grew 38. That is the builder's result line for line (`full-review.log`, `latest-full-review.json`). **B5** `compare_runs.py` finds the same 38 GREW nodes as the builder. No `[plain]` metric grows. The largest difference between the two runs is 0.00006% (`pandas-tslibs`).
  - **B1** `numpy_groups_history.py`: the accepted fuel of the upstream groups at each of main's last 14 acceptances (read-only git).
  - **B2** `numpy_group_freeze.py`: each numpy group staged as the judge stages it, run with `drive.py` as it is and with `gc.collect(); gc.freeze()` added right after it imports numpy.
  - **B3** `shutdown_cost.py`: the builder's probe, re-run on the built set.
  - **B4**: stand-in S8 re-run through checks (a), (b) and (c) (`s8-rerun.txt`).
  - The artifacts against their `SHA256SUMS`, and the linux/arm64 container's `SHA256SUMS` against the builder's.

## What was verified

- **The set is the one stated (EXECUTED).**
  - Every file in `build/artifacts` matches `SHA256SUMS`.
  - `SHA256SUMS` is `4530b6ce387db3c9…` both in the worktree and in the container's `linux/out/SHA256SUMS`.
  - The snapshot is 44,633,705 bytes (`1a7242a7a8b518f4`). `python.wasm` is 41,099,442 bytes (`5ab6bc5d0637000a`).
  - MANIFEST's line is `x-preimport encodings, io, os, sys, json, csv, re, _colorize`.
- **The code is what the spec says (READ).**
  - The `#define` is the one source. `preimport_list` exits naming the recipe on zero or two matches.
  - Check (c) holds the `#define` to `paths.PREIMPORT`, and check (e) holds MANIFEST to it. Together they make the two agree, whatever the writer does.
  - The comments in `reactor_main.c` and step 80 say what the spec says. The freeze stays, with its measured reason.
- **(f) and (g) are not weaker (READ, EXECUTED).**
  - (f) still asserts both binaries' exact stdout. It tells them apart by `csv`, which is in the snapshot's list and not in the plain start. It is seen failing against S7.
  - (g) pins `HIT pytz` at 2 on both binaries, where it used to be 0 or 2. The plain case is unchanged. The snapshot case gets stronger in two ways:
    - pandas' optional lookups now run under the import path, so they are tested;
    - the same check's `numpy` shadow now takes effect on the snapshot. Before, numpy was already imported there, so the shadow could never be tried.
  - (g) was seen failing on main's set (`b''`, 0 hits).
- **Gap (h) is well formed (EXECUTED in the confirmation; READ here).**
  - The entry's `match` is `1 finding(s), digest 7da6e52329c1`, which `scan.report` gives for `snapshot: a file left open kept 0 of 100 bytes`.
  - The check's finding string is built the same way (`f"{which}: a file left open kept {kept} of 100 bytes"`).
  - The closer `context/roadmap.md` exists, and the roadmap's 073 paragraph is on the branch.
  - (h) `[snapshot]` is xfailed by the gap in the builder's run and in mine; `[plain]` passes.
- **Check (b)'s factor (EXECUTED).** 167,464,294 / 15,622,338 = 10.72 (`start_cost.txt`; my judge run records the same snapshot fuel).
  - The memo's margin holds: 25% under 10.7.
  - The coupling with the freeze is written in the recipe's comment, in the check's docstring and in the roadmap's 073 paragraph.
- **The stand-ins (READ, and S8 EXECUTED).**
  - `judge_standins.txt`, `source_standins.txt` and `s9.txt` give every outcome that Decision 6 lists.
  - S8 re-run here: (a) fails with "modules at start that are not the stdlib's: six", and (b) and (c) pass.
  - Relinking without `-DPREIMPORT` gives the built `python.wasm` byte for byte, so the method reproduces the set.
- **The session-close figures (EXECUTED, B3).**

  | binary | first turn | shutdown fuel |
  |---|---|---:|
  | snapshot | `pass` | 42,888,965 |
  | snapshot | `import pandas` | 308,435,842 |
  | plain | `pass` | 29,507,295 |
  | plain | `import pandas` | 303,765,892 |

  These are the builder's figures. The two snapshot ones are exact; the plain ones differ by at most 18 K, the plain binary's usual spread across runs. The README's "about 43 million" and "about 308 million" are right.
- **No stale "pre-imported stack" text remains** in `src/`, `tests/`, `recipes/`, `scripts/` or `README.md` (grep).
- **N1 to N4 are taken or answered,** as the landing notes say (READ).

## Departure 2 measured: what a numpy group's growth is

The builder inferred that a numpy group grows by "its import of numpy plus the collector's work over a heap no longer frozen with pandas in it", and that the numpy groups grow less than in the draft because "the base moved". I measured both claims. Fuel figures are in G (10^9).

**Why the numpy groups grow less than the draft said (EXECUTED, B1, against the draft's A run).** After 069 each group's fuel equals the draft's A run almost exactly:

| group | draft's A run | this build | difference |
|---|---:|---:|---:|
| numpy-lib | 132.073 G | 132.036 G | −0.03% |
| numpy-others | 176.695 G | 176.701 G | +0.003% |
| numpy-core | 203.805 G | 203.382 G | −0.21% |

So what moved is the value each group is compared against, the accepted fuel before 069. It rose by 0.09 to 0.12 G when 046, 047 and 055 landed. Those were relinks that did not touch numpy. numpy-core's accepted fuel also swings by up to 1.28 G between landings: 202.35 G, 203.63 G at 047, then 202.36 G at 055. That is the address-dependent layout effect that 047 and 071 describe. So the difference from the draft is the baseline plus layout. It is not a change in what 069 costs.

**What the growth itself is (EXECUTED, B2 and `start_cost.txt`).** I split it into three parts:
- **The import, net of teardown:** about 0.69 G. The snapshot's `import numpy` is 776.3 M now against 83.5 M before (+692.8 M).
- **The collector's work over numpy's now-unfrozen heap:** 0.20 to 0.37 G. To measure it, the same group was run with numpy frozen right after its import. The figure is the drop.
- **A residue I did not split:** −0.23 to +0.44 G. It is the collector's timing, which changes with how much of the heap is frozen, together with layout.

| group | growth | import | collector (B2) | residue |
|---|---:|---:|---:|---:|
| numpy-lib | +0.702 G | 0.693 G | 0.243 G | −0.233 G |
| numpy-others | +1.333 G | 0.693 G | 0.200 G | +0.441 G |
| numpy-core | +1.024 G | 0.693 G | 0.371 G | −0.039 G |

The "growth" column is the judge's own figure. The probe's unmodified run of numpy-lib gave 132,036,381,086, within 0.000006% of the judge's (`numpy_group_freeze-first-attempt.txt`). In the frozen runs every group kept its `passes` (4,825, 7,269 and 9,519) with no findings. So the answer to the lane's question is this:
- **The growth** is the import plus collector work, both measured. It is not mainly address-dependent.
- **Its difference from the draft** is address-dependent: the baseline moved, as it did in 047 and 071.
- **The builder's wording is wrong in one detail.** A numpy group's heap no longer holds pandas at all. What is no longer frozen is numpy's own heap. (F1.)

## Findings, most severe first

1. **F1 (low): departure 2 states the wrong mechanism, and the growth reason leaves the collector out.** (Landing notes, departure 2 and "the upstream groups"; the `--accept-growth` text.) See the section above.
   - **Fix,** in the landing notes and the reason:
     - the numpy groups pay numpy's import (about 0.69 G) and the collector's work over numpy's now-unfrozen heap (0.20 to 0.37 G, measured by freezing it after import);
     - their difference from the draft is the accepted baseline, which moved with 046, 047 and 055's layouts;
     - in the reason, write "each numpy group pays numpy's import and the collector's work over its unfrozen heap (+0.70 to +1.33 G)".
   - It changes no number and no check.
2. **F2 (low): check (a)'s zip-derived assertion can no longer fail.** (Departure 7, `test_the_snapshot_pre_imports_no_package`.)
   - The stdlib rule runs first.
   - Any name in `tops & packages` is, by how `packages` is built, neither the stdlib's nor the reactor's. So it is already in `foreign`, and the first assertion has already failed.
   - The `held` assertion is therefore unreachable. The landing notes' "its failure is shown by S9" is not right: S9 shows the guard (numpy, pandas, host present) failing, not `held`.
   - Nothing is weaker, because the rule names the package anyway. But the zip derivation now serves only its own guard.
   - **Fix,** either of:
     - drop `held` and say the derivation is kept as a guard of the zip's shape;
     - or use the zip names in the rule's own message ("six (a package in the zip)"), so that the derivation earns its place.
   - Either may also be answered in writing.
3. **F3 (nit): the growth reason's pandas range.** It says "+4.49 to +4.53 G (10 checks)". The largest of the ten is +4,524,377,786 (`test_dotted_builtins_keep_their_import_names[snapshot]`), so the range is "+4.49 to +4.52 G". Every other figure in the reason matches the measured list.
4. **F4 (nit): one new comment line in `recipes/reactor_main.c` is 128 columns** (line 63, the pinned block's "(and anything a pre-imported module reads …)"). The file keeps to 99 elsewhere, apart from three old lines at 100 to 102.

## The acceptance arguments, word for word

- **`--retire tests/checks/test_v1_3_data_stack.py::test_snapshot_preimports_the_stack`:** right.
  - It is the only ABSENT node in both runs.
  - `scoreboard.accept` refuses without it.
- **`--accept-judge`:** it covers every file in the run's "judge changed" list:
  - `test_rules.py` (c), `test_v1_1_artifact_set.py` (e) and `test_v1_3_data_stack.py` (a, b);
  - `test_v1_4_embedding.py` (f, g, h), `tests/known_gaps.toml` (h's gap) and `tests/unit/test_build_scripts.py` (i);
  - `tests/harness/paths.py`, for the constants. It would be complete with `is_stdlib_or_reactor` named too (optional).
- **`--accept-growth`:** it covers the 38 GREW lines of both runs (B5).
  - Ten pandas runs.
  - Three numpy and matplotlib runs.
  - Seven lxml runs, at +55 to +98 M.
  - Seven stdlib-module runs: debugging tools, resources, zone, traceback (the uncaught errors), metadata, regex, and kiwisolver/Pillow callbacks (`test_patched_callbacks_run`), at +8 to +391 M.
  - Eleven upstream groups.

  The figures match, apart from F3. F1 adds a clause about the collector. "30.4 MB smaller" (30,449,983 bytes) and "5.3 times cheaper" (83.48 M against 15.62 M) are right. No plain metric grows, so the reason rightly drops the draft's plain-binary sentence.
- **`--accept`:** fine.

## Constitution and rules

- **§4.1 and §4.2 hold.** No patch and no pin. `downloads/SHA256SUMS` is unchanged.
- **§4.6 holds.** The set has the same members. Its hashes are recorded and reproduced on a second host.
- **§4.9 holds.** The checks count fuel and bytes. The README's times are labelled as benchmark facts.
- **§4.10 holds.** The INFERRED labels are kept. Departure 2's mechanism is now measured (F1).
- **§4.15 holds.** No default changes. The imports happen in the call, as on the plain binary.
- **§5.6:** this review re-ran the counted tests.
- **AGENTS.md rule 3 holds.** (h) is a gap with its closer.
- **AGENTS.md rule 4 holds.**
  - Each judge change is named in `--accept-judge`.
  - Neither the removed check nor (f) nor (g) was weakened.
  - No allowance was edited except to add (h).
- **Rule 9:** the branch carries one specification, and the tree is clean.

## Verdict

**Lands once F1** is written into the landing notes and the `--accept-growth` reason. That is one clause, and it changes no number. F2 to F4 may be fixed or answered in writing. Nothing else is open:
- lost 0;
- the retirement is right;
- (f) and (g) are not weaker;
- the gap and its digest are exact;
- (b) is 10.72 times;
- the set is reproduced on two hosts and its judge result on two runs.

One line: the stdlib-only snapshot is built as specified, reproduced on two hosts and judged green apart from its stated growth, which the lane can accept with the arguments as written, after one clause is corrected in the notes and the reason.

## Confirmation of the revision (addendum, 2026-10-19)

- **Reviewed:** `git diff 3e00057..0fa9f60` (3 files: the spec, `recipes/reactor_main.c` and `tests/checks/test_v1_3_data_stack.py`), against F1 to F4 above.
- **Re-ran (EXECUTED, `probes/f2-rerun.txt`).** No git tree was touched.
  - On the built set: check (a), check (c), check (e) and `test_manifest_recipes_match_the_tree` all pass (4 passed).
  - Check (a) on stand-in S2 fails with "modules at start that are not the stdlib's: six (a package in the zip)".
  - Check (a) on S7 fails with "the pre-import list did not run: ['io', 'json', 'csv', 're', '_colorize'] …".
  - The built binaries are unchanged: `python.wasm` `5ab6bc5d…`, the snapshot `1a7242a7…`. `SHA256SUMS` is now `1889459ead8b9b93…`.

**Verdict: confirmed, it lands.**

- **F2: check (a) is not weaker.** Its assertions after the change:
  - **The stdlib rule is the same.** It uses the same predicate over the same set of names, and it fails on exactly the same starts. It now writes "(a package in the zip)" beside each refused name the zip carries.
  - **The removed `held` assertion could never fail** after the rule, so nothing it caught is lost.
  - **The guard now runs before the rule.** If the zip's derivation were broken, the check would stop there before naming any package. It would still fail, so that is a safe order.
  - **The pre-import-list assertion is unchanged.**
  - **The stand-ins fail as `f2_message.txt` lists:** S1 names numpy, S2 and S8 name six, S7 fails because the list did not run, and main's set names `dateutil` and `numpy` among the others. S9 (the guard) is unchanged. `--accept-judge` describes the new message.
- **F1, written in correctly.** The mechanism and the measured figures are in three places: departure 2, the upstream line of "Grew 38" and `--accept-growth`. Those figures are about 0.69 G for numpy's import and 0.20 to 0.37 G for the collector's work over numpy's unfrozen heap. The baseline moving with 046, 047 and 055 explains the gap from the draft. The wrong "pandas heap" wording is gone.
- **F3, written in.** "+4.49 to +4.52 G" is used everywhere.
- **F4, written in.** The new comment lines are at most 99 columns. Only MANIFEST's recipe hash moved, and `test_manifest_recipes_match_the_tree` passes on the rebuilt set.
