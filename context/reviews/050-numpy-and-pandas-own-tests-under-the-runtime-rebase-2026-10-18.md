# Review of 050 — numpy's and pandas' own tests under the runtime (the rebase onto 051; a judge change)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change, the specification, its pre-build review, its build review or its confirmation. This review is item 7 of the build review's list, "Rebase onto spec 051: what the lane must re-check" (`050-numpy-and-pandas-own-tests-under-the-runtime-2026-10-18.md`, not yet in git). It covers items 1 to 7. Item 8, the lane's run in the main tree, is the lane's.
- **Read:** `AGENTS.md`; constitution §4 and §7; `context/reviews/README.md`; `context/progress/README.md`; spec 050 as it stands in the worktree (status, Decisions 8 to 10, 17 to 20, criteria, Design, every landing-notes section, the last one in full); its pre-build review (C1 and the builder notes); the whole build review with its confirmation; spec 051, Decisions 10 to 13. Each claim below is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `git diff 93ccd9c 612fb70` on `spec/050-upstream-tests` in `/Users/claygendron/Git/Repos/wasi_python-050`: commits 2c043d5, 5330190 and 612fb70, based on main's `a135ea5`. I also read the rebase of the first two commits (`git range-diff 749f6c7..0d505d0 a135ea5..93ccd9c`), because the rebase changed one harness file outside that range (see "The rebase itself" below).
- **Re-ran** (EXECUTED, darwin-arm64, `uv run` only, wasmtime-py 49.0.0, the frozen set `WASI_PYTHON_ARTIFACTS=/Users/claygendron/Git/Repos/wasi_python/build/sets/s-f94dec535086b06c`, read only). That set's `python.wasm` hashes to `5648e4c5…`, the artifact in main's `accepted.json`, and its `MANIFEST` is byte-identical to `build/artifacts/MANIFEST`. Every output is under the worktree's `build/delta-review/`:
  - `judge.log`, `judge-latest.json`: the full judge, `uv run pytest`, no flags, run once. Exit 0, 588.7 s.
  - `seen_first.py` → `seen_first.txt`: 93ccd9c's `tests/upstream/` (configs, classes, lists, the seven `[[trap]]` entries), extracted with `git show` into `old-upstream/`, run on 051's set through the harness's own `upstream.Session`. Each of the seven trap entries runs alone, then each of the 11 groups, and each class is compared with its old list.
  - `recount.py` → `recount.txt`: every class list against its gap, using `scan.digest`; the closers; the caps; `upstream.rule_errors` on the new files.
  - `f6a_mutant.py` → `f6a_mutant.txt`: the confirmation's surviving mutant F6a, applied in memory (no file edited), against the new unit case.
  - `uv run ruff check` and `uv run ruff format --check` on `src tests recipes/guest`: clean.
  - I never passed `--accept`. `git status --short` in the worktree was empty after every run. I wrote nothing in the main tree.

**The judge's tail** (EXECUTED, `judge.log`):

```
wasi_python v1: 265/286 pass · 12 gap · 9 blocked · 0 fail   (unit suite 998/1006, 8 skipped)
  v1.3  data stack          45/58  gap 12 blocked 1
gaps close with: README 10 · questions-for-the-owner 2
next: README.md (unblocks 0, closes 10)
ratchet vs 614520fff6: lost 0 · absent 0 · unrun 0 · unrun locally 7 · gained 20 · grew 0 · judge changed: … and 35 more
not machine-checked: publication · copying from prior art · numpy's 25 files that need its C test modules (number 89) · pandas beyond eight groups
1263 passed, 17 skipped, 12 xfailed in 588.70s (0:09:48)
```

This equals the builder's recorded run (`build/judge-051.log`) line for line, apart from the time. `unrun locally 7` is this worktree's missing oracle, prior-art clones and five C source trees. No upstream check is among them, and there is no `upstream unrun` count.

## Acceptance criteria against evidence (the build review's items 1 to 7)

1. **The MANIFEST tie with 051's patch `recipe` lines holds.** Met. EXECUTED: the set's `MANIFEST` has `recipe f41d5f62… 0001-npy-files-without-dup.patch` (amended) and `recipe 487dfa40… 0002-callback-signatures.patch`, and `shasum -a 256` of the worktree's two patch files gives the same hashes. The judge staged both packages. Every group passed, so `Session._prepare` returned no tie error (a tie error fails every group: the build review's E4 and F1). `left_out` is `[]` for all 11 groups (`judge-latest.json` facts). The worktree changes nothing under `recipes/`, `scripts/`, `downloads/` or `.github/` against main (EXECUTED, `git diff --stat a135ea5 HEAD`), so the change is still not build-class.

2. **Seen failing first, again: it matches 051's Decision 12.** Met. I ran this myself, not just read the builder's log (EXECUTED, `seen_first.txt`, 93ccd9c's files on 051's set):
   - **All seven trap checks pass**, with `findings=[]`, so each gap would say "remove the gap". `castingimpl-casting-unittests` ran to its end with 28 Python failures, which a trap check rightly ignores (the pre-build review's builder note).
   - **The eight classes are empty**: the six `zip-code-names` classes (1 + 21 + 71 + 7 + 73 + 21 = 194 ids, 193 pandas and 1 numpy, as 051 says) and the two `patch-0001-*` classes.
   - **Every other class equals its list**, with the same count and digest as its gap.
   - **Every group had 0 findings**, with the passes the notes give for the old configs: numpy-core 8,568 (traps still deselected), numpy-lib 4,825, numpy-others 7,269, frame 10,852, groupby 22,227, reshape 2,664, io-parser 3,474, io-formats 976, tslibs 590, internals 258, libs 1,063.

   The one difference from Decision 12 is explained in the notes: numpy-lib gains two passes, not one. The second is `test_save_masked_without_dup`, which amended patch 0001 adds (READ, 051 Decision 10). Fuel per trap entry matches the builder's `upstream-051.log` to within a few hundred instructions.

3. **C1 applied as written (option (a)).** Met.
   - READ (the diff): the eight emptied classes keep their `[[expected]]` entries and their list files, now empty (`e69de29`, the empty blob). Their eight gaps are gone. The seven `[[trap]]` entries, their seven gaps, and the `not_selected` entry for `test_casting_unittests.py` and `test_arraymethod.py` are deleted.
   - No `--retire` is needed: 050 has never been accepted, so none of these checks has an accepted entry. In the run, the ratchet shows `absent 0`, and `accepted.json` holds no `test_v1_3_upstream_suites` node, in either tree (EXECUTED, `grep -c` gives 0).
   - The rules hold. EXECUTED: `upstream.rule_errors` gives `[]` on the new files, and the judge's `test_upstream_files_are_well_formed` passes. That covers "an empty list has no gap", "every trap has its gap" (there are none) and "every list names a class".
   - `test_upstream_trap` is now defined only `if TRAPS:`. READ: an empty parametrization would report a skip that names no need. The mechanism stays for the next trap, and its unit guards (U16, G1 and the F6 cases) are in the unit suite, unchanged. The judge collected no `test_upstream_trap` node (EXECUTED). That gives 32 upstream checks: 11 groups, 20 classes and 1 rule.

4. **The two returning files run in `numpy-core`.** Met.
   - EXECUTED (judge): `numpy-core` passes with 9,519 passes, `error 3, failed 40`, and no trap. A trap would end the session and fail the group.
   - The gain is +951: 904 passes from `test_casting_unittests.py`, 40 from `test_arraymethod.py`, and 1 + 3 + 1 + 1 + 1 from the five single-test entries. READ: the builder's `upstream-051.log`. My seen-first run gives the same per-entry counts.
   - The 28 new failures are `test_object_casts_NULL_None_equivalence[*]`, one for each of the 28 type codes. Each one calls `ctypes.memset(arr.ctypes.data, …)` (READ, `build/numpy-2.5.2/numpy/_core/tests/test_casting_unittests.py:821`), and the stand-in raises `OSError: ctypes is unavailable on wasm32-wasi` (`recipes/ctypes_stand_in/__init__.py:14`).
   - They form a new class, `numpy-core-no-ctypes`, closed by `README.md`. The README states that fact (READ, lines 75–78: each `ctypes` call "raises `OSError` … which is why `-V` still says 'no ctypes'"). It is the same fact, `match` and closer as the existing `numpy-others` `no-ctypes` class.
   - There is no new trap, so no new entry or follow-up is needed.

5. **New baselines.** Met.

   | group | passes | fuel, this judge | fuel, builder's judge | apart | cap | cap ÷ fuel |
   |---|---|---|---|---|---|---|
   | numpy-core | 9,519 | 203,078,172,274 | 203,078,170,200 | 0.01 ppm | 3.1×10¹¹ | 1.53 |
   | numpy-lib | 4,825 | 131,417,592,937 | 131,417,583,434 | 0.07 ppm | 2.0×10¹¹ | 1.52 |
   | numpy-others | 7,269 | 175,315,699,734 | 175,315,688,633 | 0.06 ppm | 2.7×10¹¹ | 1.54 |
   | pandas-frame | 10,852 | 344,819,798,877 | 344,819,783,016 | 0.05 ppm | 5.2×10¹¹ | 1.51 |
   | pandas-groupby | 22,227 | 478,743,981,200 | 478,743,979,551 | 0.00 ppm | 7.2×10¹¹ | 1.50 |
   | pandas-reshape | 2,664 | 103,347,423,383 | 103,347,417,535 | 0.06 ppm | 1.6×10¹¹ | 1.55 |
   | pandas-io-parser | 3,474 | 89,652,525,576 | 89,652,537,969 | 0.14 ppm | 1.35×10¹¹ | 1.51 |
   | pandas-io-formats | 976 | 54,364,790,098 | 54,364,789,367 | 0.01 ppm | 8.2×10¹⁰ | 1.51 |
   | pandas-tslibs | 590 | 38,969,565,419 | 38,969,563,583 | 0.05 ppm | 5.9×10¹⁰ | 1.51 |
   | pandas-internals | 258 | 18,266,836,728 | 18,266,840,927 | 0.23 ppm | 2.8×10¹⁰ | 1.53 |
   | pandas-libs | 1,063 | 23,065,428,607 | 23,065,428,403 | 0.01 ppm | 3.5×10¹⁰ | 1.52 |
   | **all** | **63,717** | **1,661,041,814,833** | | | **2.519×10¹²** | |

   - **Passes.** EXECUTED. They equal the notes' figures for every group, and every group's `passed_digest` equals the builder's run. So the same tests passed, not just the same number.
   - **Repeat (criterion 7).** EXECUTED: my judge against the builder's judge, two independent runs, are at most 0.23 ppm apart. The builder's "twice in one session" pairs (READ) are within 0.38 ppm. All are far inside 0.01%. For the five pandas groups, the 51's-set fuel in my seen-first run (old configs, same grant folders) is also within 0.2 ppm of the judge's.
   - **The numpy-core cap** is 3.1×10¹¹, 1.527 times its fuel, so above 1.5. Every other cap is at least 1.50 times its fuel. groupby is the tightest: 7.2×10¹¹ ÷ 4.787×10¹¹ = 1.504.
   - **The caps' sum** is 2.519×10¹² (EXECUTED, `upstream.caps`), at most 3×10¹².
   - **Spent fuel** is 1.661×10¹², under 1.8×10¹². There are no trap checks to add.
   - The seven raised caps are all needed. INFERRED: on 051's set, fuel grew 1 to 4% in the pandas groups (the zip-path code names, 051's accepted growth), and the old caps would have fallen below 1.5 times the fuel.

6. **The counts agree everywhere.** Met, with one stale status line (F2).
   - **The judge (EXECUTED):** 12 gaps, `README 10 · questions-for-the-owner 2`, and `next: README.md (unblocks 0, closes 10)`. Spec 051's 15 go to 0.
   - **`tests/known_gaps.toml`:** it holds 12 gaps in all, all upstream classes (EXECUTED).
   - **README (READ):** the Measured row says 63,717 passing and 12 gaps, "the README 10, question 89 2", no trap. The net diff from main adds no "Known defects" section; it was added and removed inside the branch, and 051 closed all three of its items. The platform paragraph gains `/dev/null` and `conftest`.
   - **CHANGELOG (READ):** 63,717 passing, 12 classes with members, no test traps.
   - **Spec 050 (READ):** consistent throughout: 12 entries, 20 classes (12 with members, 8 empty), 100 ids, 63,717, 1.661×10¹², 2.519×10¹², 32 checks and gained 20. The failure counts check out: numpy 40 + 6 + 10 = 56 failed and 3 errors; pandas 40 + 1 = 41 failed. The table of the earlier set's 18 classes stays as history, under a new paragraph.
   - **Spec 002's amendment lines** cite no gap or class counts. "numpy's 25 files" is 23 + 2 (`_simd`), unchanged by the rebase. Its line 152 uses `fact(name, value)`, matching the renamed fixture.
   - The research memo's "62,569" is the drafting run's dated fact, and it stays.

7. **Recount with `scan.digest`; the 050 checks re-run.** Met.
   - EXECUTED (`recount.txt`): every one of the 20 classes is `OK`. Each gap's match equals `"<len(list)> finding(s), digest <scan.digest(list)>"`, and each gap's `closes_with` equals its class's. Each empty list has no gap. There are no orphan gaps.
   - The total is 100 ids: 8 + 3 + 3 + 28 + 1 + 5 + 1 + 8 + 1 + 1 + 40 + 1.
   - The judge's class checks report the same counts and digests as their gaps.
   - The run was the full judge, including every slow upstream check, as stated above.

## Findings, most severe first

None of these admits a failure, loses a pass or changes a number. All three are low.

1. **F1 (low). Eight blank lines are left in `tests/upstream/numpy.toml`**, where the seven `[[trap]]` entries were, between the trap comment and the classes' comment (EXECUTED: `awk` counts 8 consecutive empty lines). Failure: none at run time; `tomllib` ignores them. The next person to add a `[[trap]]` entry reads a hole that looks like deleted content. Fix: collapse them to one blank line. It is a judge file, so the fix rides in the same `--accept-judge`.

2. **F2 (low). Spec 050's status line is stale.** It still reads "This specification rebases onto 051 and re-derives its tables…" in the future tense, and it ends "Built 2026-10-18 on `spec/050-upstream-tests`; awaiting its review (Landing notes)." Both the build review (with its confirmation) and the rebase are done. Failure: a reader orienting from the status line, as AGENTS.md's rule 1 asks, believes the build is unreviewed and the rebase still to come. Fix: one clause, for example "build-reviewed and confirmed; rebased onto 051 and re-derived on its set (landing notes, last section); rebase delta reviewed (this review)". The lane may do this when it cites the reviews.

3. **F3 (low). The eight emptied classes still name spec 051 as `closes_with`**, and spec 051 has landed. Today the field is unused, because an empty class has no gap. Failure: one of those failures returns, say a re-pin brings back a stacklevel warning. The class gains a member, and the rules check demands a gap. The person writing it copies the class's closer and names a landed specification, which would not close it. Fix (either):
   - leave it, and say in the comment above the classes that an emptied class's `closes_with` records what emptied it, not what would close a return;
   - or point the emptied classes at the regression's natural owner.

   I would take the comment.

### Notes (no change needed)

- **The rebase itself, outside the reviewed range.** `git range-diff` shows that the rebase changed commit 1 in one way: main's spec 051 had landed a `note(text)` fixture, so 050's `note(name, value)` became `fact(name, value)`, recorded under `facts` (READ). It is a mechanical rename across `plugin.py`, the check file and `test_plugin.py`, and the landing notes record it. Commit 2 is identical (`0d505d0 = 93ccd9c`). `tests/harness/` is unchanged across `93ccd9c..612fb70` (EXECUTED, empty `--stat`). Against the confirmed `3907985`, the only 050-owned harness difference is `plugin.py`; `callbacks.py`, `scan.py`, `wasm.py` and `jobs.py` are main's 051 changes.
  - The judge writes `facts` (`left_out`, `passed_digest`, `counts`) for all 11 groups (EXECUTED).
  - `test_passes_ratchet_end_to_end_with_its_own_flag` asserts the facts reach `latest.json`.
  - So the build review's mutant results carry over. Its plugin mutant P1 concerns the flag, not the fixture's name.
- **F6a is closed.** The new unit case `test_a_trap_check_whose_entry_started_but_whose_session_did_not_finish_fails` passes on the real `trap_findings`. It fails (`[]`) when the "no `E` line" branch is removed in memory (EXECUTED, `f6a_mutant.txt`). So the confirmation's last surviving non-equivalent mutant is killed.
- **Emptied classes with generic matches keep guarding.** An example is `numpy-others` `zip-code-names`, whose match is `^AssertionError: ?$`. A new bare `AssertionError` failure in that group is taken by the empty class. The group check then passes, but the class check fails with `+<node>` and no gap, so the run is red (READ, `class_findings`, `rule_errors`). That is C1(a)'s intent.
- **For the lane (item 8).** Expect the same line in the main tree without `unrun locally`: `lost 0 · absent 0 · unrun 0 · gained 20 · grew 0`, no `FEWER` and no `upstream unrun`. Use `--accept-judge` only. No `--retire`, `--accept-growth`, `--accept-fewer-passes` or `--partial`. The build review's "expect gained 12" is superseded by 20 (11 groups, 8 emptied classes and the rule).

## Constitution checks

- **§4.1 (patches).** No source change. The tests are read from the tree that 051's two recorded patches produce, and the tie proves it (EXECUTED).
- **§4.2 and §4.8 (pinned, untrusted inputs).** The kit's seven wheels match `kit.txt` by SHA-256 (EXECUTED, `shasum`). Nothing new is downloaded.
- **§4.9 (counts, never time).** Fuel and passes only. The 588.7 s is a benchmark fact here.
- **AGENTS rule 4 (never weaken the judge).** The rebase removes 15 gaps. Each removal is backed by a check that now passes, or by a check that no longer exists because its trap is gone and its tests run in their group. Each was seen first on the old files (EXECUTED). The one addition, `numpy-core-no-ctypes`, lists 28 ids, has a closer the README states, and goes red on any `+`/`-` change. No list was changed to make a run green.
- **§5.7 (class).** Not build-class (EXECUTED, `--stat`). It is a judge change and needs `--accept-judge`.
- **Artifacts never in git.** Nothing under `build/` is tracked (READ, `git status`).
- **§7 never-do list.** Nothing tripped. No commit, push, stash or acceptance was made by this review.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. F1 —
2. F2 —
3. F3 —

## Verdict

**Confirmed, it lands.** The rebase delta does what 051's Decision 12 and C1(a) say, and I re-derived every number on 051's set: the seen-first run on the old files, the full judge on the new ones, and the recount. F1 to F3 are low. They change no number and admit nothing, so the lane may fix them in the landing or take them as written follow-ups.

One line: on 051's set, 050's old files show exactly the eight emptied classes and the seven passing traps; the new files give 63,717 passes, 12 gaps with honest digests, caps 2.519×10¹² and fuel 1.661×10¹² repeating to 0.23 ppm; it lands, with three cosmetic fixes.
