# Pre-build review of 085 — `gather` checks what it trusts, 2026-10-19

- **Reviewer:** a fresh agent. I wrote none of 085, and none of the a7 security review it answers.
- **Under review:** `context/specifications/085-gather-checks-what-it-trusts.md` on `spec/085-gather-checks-what-it-trusts`, commit `31a8713` over main `a6dfc17`. Its evidence is in `context/research/2026-10-19-gather-checks-what-it-trusts/`. Its sources are F5, F6, F7 and N5 of `context/reviews/0.1.0a7-security-review-2026-10-19.md`.
- **Main moved while I worked.** Spec 065 landed: main is now `9d89535`, with history line 79, accepted as `a4b46de`. Question 105 is now in `context/questions-for-the-owner.md`. I checked the points that depend on this against `9d89535` too.
- **Read:**
  - the spec in full, and every evidence file (`forge_synthetic`, `forge_real`, `records`, `fuel_across_systems`, `prototype`, `set_sums_a7`);
  - in the code: `tests/harness/gather.py`, `needs.py`, `plugin.py` (`_judge`, `run_meta`, the controller's tally), `scoreboard.compare` and `accept`, the readers in `history.py`, `paths.artifact_dir`, `release/version.py` (`assets`), and `release.yml` (the build job, the judge jobs' unpack and verify steps, the gather, attest, publish, pypi and the rebuild tools step);
  - `tests/unit/test_gather.py`, every `need(` call site under `tests/`, constitution §5.6 and §5.7, spec 037's Decision 17, question 105, and 065's diff to `gather.py`.
- **How I ran things.**
  - I downloaded the record artifacts of run `39255794160` (the a7 tag) and run `39265738300` (065's green dry run) with `gh run download` into my scratch folder. I parsed them as JSON only.
  - My probes are in `work/` beside this file:
    - `forge_more.py` runs 20 forgeries on the a7 records. It reports today's `gather.gather` and a copy of Decisions 1 to 3 that I wrote myself from the spec text (not the author's prototype).
    - `forge_more2.py` runs the honest records alone, against any tree's collection.
    - `hidden.py` maps every `need(` call site.
  - Collections ran with `python -I -B` and `-p no:cacheprovider`. I wrote nothing in any git tree, and `git status` was unchanged before and after.
  - I re-ran the author's `forge_synthetic.py` and got the same result: 13 of 14 green. `tests/unit/test_gather.py` passes, 44 tests.

Labels: **EXECUTED** (I ran it), **READ**, **INFERRED** (reasoned, not run).

## Short version

The design is right on all four points, and the trust-boundary section is honest.

- **F6.** Reading needs from the check's own body is better than a pinned list. It fails closed everywhere that matters.
- **F7.** The tally rule holds on every honest record.
- **F5.** Hashing the set's own `SHA256SUMS` is right, and so is the author's correction of the review: the release assets' `SHA256SUMS` hash would not work.
- **No false red.** I re-executed the rules on both runs' 38 honest records: zero red lines.

Four things need writing in before the build:

1. **One field switches off the darwin fuel ratchet** (EXECUTED). If a darwin record changes its own `meta.wasmtime`, ten times the fuel stays green, today and under 085.
2. **Question 105's option (a) does not cover 085's set clause.** Under 037 the snapshot varies too, so the set's `SHA256SUMS` differs on every build. The owner should see this before answering.
3. **Criterion 6 assumes 085 lands before 037.** Say so, or give the other order its own criterion.
4. **Criteria 2 and 3 can now pass with nothing proved** (EXECUTED). Since 065 landed, the honest a7 records are red at G3 under main's gather. So "six red verdicts" on them would show nothing.

## 1. Does each fix close its finding? The forgeries the author did not list

All rows below were run on the a7 tag run's real records, re-hashed after each edit, with `accepted.json` and the history from tag `2737b29` (EXECUTED, `work/forge_more.py`, output in `work/out-a7/`).

| forgery | today | after 085 (Decisions 1–3) | what catches it |
|---|---|---|---|
| honest records | green | green | — |
| a `gap` reported for an accepted pass (linux own-guest) | red | red | G4 (not in `known_gaps.toml`), G5 `lost` |
| `blocked` by a need the body names, where CI has it (descriptor `[snapshot]` on macOS) | **green** | red | new G4 (the system clause) |
| `blocked` by `wasmtime`, a need CI meets | red | red | G4 (not a CI need) |
| fuel swapped between two checks, linux or windows own-guest | green | green | nothing: values are not compared off darwin (by design) |
| fuel swapped between two checks, macos own-guest | red | red | the ratchet (one side grows) |
| every fuel ×10, linux own-guest | green | green | nothing (by design, Decision 3) |
| every fuel ×0.01, macos own-guest | green | green | nothing: shrinking is never red (by design) |
| **every fuel ×10, macos own-guest, with `meta.wasmtime` = `"48.0.0"` or `null`** | **green** | **green** | **nothing (finding F1)** |
| another commit, or another judge hash | red | red | G2 |
| a duplicated record, unchanged | red | red | G1 (one hash handed on for two shards) |
| a duplicated record with `meta.shard` edited | red | red | G3 (other goal checks, other unit tests) |
| macos own-guest replaced by linux's, platform edited | red | red | the ratchet, only because Linux fuel runs higher |
| a shard missing (linux upstream-frame not handed on) | red | red | G1 |
| `suite` `{540, -2, 538}` | **green** | red | new G4 (the "at least 0" rule) |
| `suite.passed` = `538.0` | **green** | red | new G4 (the "whole number" rule) |
| numpy-core `passes` one higher on every system | red | red | G5 (passes against accepted) |

**What this shows.**

- Each fix closes its own finding:
  - F6's six-record forgery is red after 085.
  - F7's empty, zero, negative, float and bool tallies are red.
  - F7's dropped metric names are red (the author's rows; my copy agrees).
- The forgeries outside the author's list fall into two groups:
  - those already red today (`gap`, commit, judge, duplicate, missing shard);
  - those the spec says it leaves alone (metric values off darwin).
- One forgery is neither, and it is F7's own ground: F1 below.

## 2. Is reading `need("…")` from the source robust?

**The derivation matches CI today** (EXECUTED). On `a6dfc17` and again on `9d89535`, my copy derives exactly five nodes:

- the prior-art licence rule;
- the descriptor check's two rows;
- the same-bytes claim;
- the goldens.

**What fails closed** (red in the gather; nothing hidden):

- a need named through a helper or fixture;
- a need named through a variable, a `NEED_OF[...]` lookup, an f-string or `*args`;
- a direct `pytest.skip("needs: oracle")`, which the plugin turns into `blocked` too;
- a source that `inspect` cannot read.

**What fails open** (narrow, and acceptable once written down; F8):

- Parametrized rows share one body. A row whose own path never calls the need may still be blocked by it. Today this applies only to the descriptor rows, and both rows are rightly blocked on Windows.
- The rule asks whether the body *names* the need, not whether the call can be reached. A call in dead code or behind a condition still allows the block on every system the map allows.
- Any call spelled `.need("…")` counts, whatever the object.

**The fast-tier test is narrower than the spec says** (EXECUTED, `work/hidden.py`; finding F5). Seven call sites pass `need()` an argument that is not a literal:

- `NEED_OF[which]` in `tests/checks/conftest.py` (twice) and in `test_v1_1_artifact_set.py`;
- f-strings in `test_v1_3_upstream_suites.py` (twice) and in `test_v1_5_rebuild_from_pins.py`.

`hidden_ci_needs` as designed looks for literal CI names in calls outside `test_` bodies, so it cannot see any of these. If `"oracle"` were added to `NEED_OF`, the gather would be red only at a dry run. That is still fail-closed, but it breaks the promise "found before a dry run".

## 3. Is "no false red" proven?

**On today's records, yes** (EXECUTED). My copy of the rules gives zero red lines:

- on the a7 run's 19 records, against `2737b29`'s `accepted.json`;
- on 065's 19 records, against `5294520`'s collection and `accepted.json`.

**Windows-only blocks.** Only the descriptor rows are blocked on Windows alone, and the map allows them only there. The Windows guest record's other two blocks (`three systems`, `oracle`) are allowed everywhere.

**Upstream shards.**

- Neither run has a blocked upstream check.
- 065's nine trap entries are `gap`s with no metrics, so Decision 3 never applies to them.
- Every `test_upstream_suite[cpython-*]` pass records both `fuel` and `passes` on every system that runs it: cpython-fs on all three, the others on Linux. So once the lane's acceptance of 065 adds their darwin metrics, the name rule holds (INFERRED from the records).
- Every metric value in both runs is an `int`: 457 fuel, 9 bytes, 13 passes in a7; 464, 9 and 20 in 065. So the "is a number" rule does not fire on honest data.

**What stays inferred.** A future check that records a metric on one system only will be red. The spec accepts this on purpose (Decision 3), and I agree.

## 4. Is the F5 design right?

**The lane hashes the same file CI hashes** (EXECUTED and READ).

- `run_meta` would hash `artifact_dir()/SHA256SUMS`.
- In the main tree that is `build/artifacts/SHA256SUMS`, which is `c9dcb5b8…`. That equals the file inside the a7 tarball and the frozen set `s-c50ca51fae5eb55b-c9dcb5b8`.
- `release/version.py assets` copies `build/artifacts` into the tarball byte for byte. The build job's new step hashes that same file, before the assets are made.
- In the judge jobs, `WASI_PYTHON_ARTIFACTS` points at the unpacked tarball, which each job has already checked against `sums-sha256`. So an honest record's `set_sums` is the build's.

**`MANIFEST` makes the set hash move with build-class changes only** (EXECUTED). Its `recipe` lines hash files under `scripts/` and `recipes/` and nothing else. Its `pin` lines follow `downloads/SHA256SUMS`. It holds no version and no commit. So a non-build-class commit never changes `set_sums`, and a build-class landing already rebuilds and re-accepts.

**F5's case has really happened** (EXECUTED). The main tree's `build/sets/` holds two pairs of sets with the same `python.wasm` and the same snapshot whose `SHA256SUMS` differ: `s-c50ca51fae5eb55b` against `-c9dcb5b8`, and `s-4eb5418a2b1bb553` against `-c353b1d9`.

- In both pairs, only the `MANIFEST` line differs (the recipe hashes of `build.sh`, `10_tools.sh`, `refuse-python`, `common.sh` and `00_download.sh`).
- `test_manifest_recipes_match_the_tree` already guards `MANIFEST` at acceptance. So in practice the new clause adds the snapshot, the zip and the licences.
- That is still worth one hash.

**Spec 037's exception, and question 105** (READ; finding F2).

- Under 037, `python.wasm` **and the snapshot** differ on every build (037 Decision 17 names both as "the two artifacts it touches").
- So the set's `SHA256SUMS` differs from the lane's on every build, in two lines.
- Question 105's option (a), as written, canonicalizes only `python.wasm`. G7's `artifact` clause would then hold, but 085's `set_sums` clause would stay red on every release.
- So option (a) needs a canonical set digest as well. For example: `SHA256SUMS` with both binaries' lines replaced by their canonical digests. The lane would record it, the build job would hand it on, and G7 would compare it.
- Otherwise, while the exception holds, 085's clause must give way. The question should say this before the owner answers it, and Decision 8 should name it.

## 5. Is the trust-boundary text honest?

**Mostly yes** (READ). Decision 7 says plainly that a compromised leg can forge a passing set of records before 085 and after it. It explains why: every input the gather compares against is in that leg's hands. It names what the leg cannot do, and I checked each step:

- attest, publish and pypi run only on a pushed tag;
- they depend on `build`, `verify`, `same-bytes` and `gather`, never directly on a judge job;
- every job that reads the assets re-checks them by id and by `sums-sha256`;
- no job uses `actions/cache`, so there is no cache to poison.

Two small over-claims (F7):

- **Decision 4: "one hash names every byte a run judged".** It names every file of the artifact set. The run also judges other things, each bound in its own way:
  - the wheel (by `sums-sha256`);
  - the runner's source (by the commit, through G2);
  - the upstream kit and the source trees (by their pins).
- **Decision 7: it "closes the cheapest lies".** Two cheap lies stay open:
  - Linux and Windows metric values can be any number.
  - Until F1 is fixed, one darwin field turns off the fuel ratchet.

  Say both, or fix F1 and say the first.

## 6. Is it really exempt from a pre-build review under §5.6?

**By the letter, yes.** §5.6 asks for a second review only when a specification changes the guest's imports or exports, the artifact set, or the build recipe.

- 085 changes none of these. The recipe is what `MANIFEST` hashes (`scripts/`, `recipes/`, the pins), and `release.yml` is not among them.
- Build-class (§5.7, AGENTS.md rule 2) is a wider net. It governs how a change lands, not whether its design is reviewed.

**In substance, a review was worth holding**, and I would ask for one again on a spec like this:

- it changes what gates a release;
- its own branch dry run is red by design;
- it depends on an owner's answer that is still open;
- its F1 and F2 would have been found only at a release.

The status line should now say that a review was held before the build (this one).

## 7. Ordering

- **065 has landed** (`9d89535`, line 79). 085 now builds on it.
  - 065's `gather.py` change (`no_trap_anywhere`) is additive and touches no G rule. I read the diff.
  - Criterion 6 should name line 79, not line 78.
- **037.** Question 105 already says 037 cannot land until it is answered. If 037 lands before 085 anyway:
  - 085's branch dry run is red on two G7 lines, not one;
  - criterion 6's "the lane's first dry run of main must pass every job" cannot be met until 086 or option (a).

  The spec should say that 085 lands before 037, or give the other order its own expected lines (F3).
- **037's `scan.rebuild_gate_errors` hunk** sits beside N5's line. The plan (merge it by hand, whichever lands second) is right.
- **The first dry run after acceptance.** On the branch, an expected red line is fine. Attest and publish are skipped on a dispatch, so no other job depends on the gather there (READ). After acceptance, the dry run's green depends on the CI set equalling the lane's main-tree set, as it did for a7.

## Findings, most severe first

- **F1. Medium. A darwin record can switch off its own fuel ratchet with one field** (EXECUTED).
  - The cause:
    - `scoreboard.compare` compares fuel only when `accepted`'s `wasmtime` equals the record's `meta.wasmtime`. Otherwise it files the check under `fuel_not_compared`, which is never red.
    - G2 does not bind `meta.wasmtime`.
  - Ten times the fuel in macos own-guest, with `meta.wasmtime` set to `"48.0.0"` or to `null`, is green today and under Decisions 1 to 3.
  - This is F7's subject ("its own metrics"), and it undercuts Decision 3's "values where they are compared today".
  - **Fix:** G2 requires `meta.wasmtime` to equal the `wasmtime` version in the gather's own `uv.lock` (49.0.0 today). This also catches an honest fault, a leg that resolved another wasmtime. Add one row to the table.
  - Better not to make `fuel_not_compared` red instead: that would turn a wasmtime-bump branch's dry run red until its acceptance.
- **F2. Medium. Question 105's option (a) does not account for 085's set clause** (READ).
  - 037's exception moves the snapshot too, so the set's `SHA256SUMS` varies on every build.
  - Fix both places:
    - Decision 8 and *Coordination* should say that option (a) must also define a canonical set digest, or that the `set_sums` clause gives way while the exception holds.
    - Question 105 should say the same before the owner answers.
- **F3. Medium. Criterion 6 assumes 085 lands before 037** (READ).
  - State the order: 065, then 085, then 037.
  - Or give the other order its own criterion, with two expected G7 lines and the lane holding tags until 105 is closed.
  - Also update line 78 to line 79.
- **F4. Low–Medium. Criteria 2 and 3 can pass with nothing proved** (EXECUTED, `work/forge_more2.py` on `9d89535`).
  - Main's post-065 gather is already red on the honest a7 records (`G3 … its collection is not the gather's`, on every record). So "six red verdicts" on those records prove nothing.
  - 065's records will not match either: 085's new unit tests change own-rest's unit share digest, and 085's judge hash differs.
  - **Fix:** run the honest baseline and the six forgeries on the branch dry run's own 19 records:
    - the baseline is red only on the expected G7 line;
    - each forgery adds exactly its own rule's line.
  - Keep the a7 and 065 records for the new G4 and G5 rules alone, run as functions.
- **F5. Low. `hidden_ci_needs` misses needs named through non-literal arguments** (EXECUTED).
  - There are seven such sites today.
  - **Fix:** widen the test so that it flags:
    - any string constant equal to a CI need, anywhere under `tests/checks/` and `tests/harness/` (`needs.py`'s vocabulary aside), outside a `test_` function's body;
    - any `"needs: "` literal outside `needs.py`.
  - Add `tests/conftest.py` to the scope. This makes "found before a dry run" true for every spelling but a computed string.
- **F6. Low. "Every system" in `CI_NEEDS` should name `build`** (READ). `expected_keys` gives the build record the system `"build"`, and G4 runs over that record. The author's prototype includes `"build"`; the spec's map does not say so.
- **F7. Low. Two over-claims** (READ): "every byte a run judged" (Decision 4) and "closes the cheapest lies" (Decision 7). See §5.
- **F8. Low. The open edges of the source derivation should be written down** (READ): shared parametrized rows, unreachable or conditional calls, any `.need` attribute. All are narrow. Decision 1 should list them beside its fail-closed cases.

## Notes (no action required)

- **N1. An optional extra, not a condition.** A coarse cross-system fuel band (say 1%) on Linux and Windows would catch swaps (5.6% apart on the pair I swapped) and Linux-only fuel regressions. The worst honest gap is 0.197% (`fuel_across_systems.out`, re-read). Decision 3's "not comparable" holds for the 0.01% ratchet, not for every band. Whether it is worth the risk of a future host-dependent check is the owner's call. Leave it out of 085 unless asked.
- **N2. N5 is fine** (READ).
  - `python3 --version` in the rebuild jobs' tools step runs before step 10 installs its shim.
  - `scan.bare_python_hits` scans only `scripts/`, so the workflow line breaks no rule.
- **N3. Spec 063's amendment line and the README sentences are proportionate.** No schema bump is needed:
  - `history._step` and `history.errors` read no unknown keys (READ);
  - lines 1 to 79 read `set_sums` as null.

## Verdict

**Ready once F1 to F4 are written in**, and F5 to F8 are written in or answered in writing.

- F1 is one G2 clause and one table row.
- F2 is a sentence in Decision 8, plus a matching line in question 105.
- F3 and F4 are criteria wording.
- None of them changes the design.

## One line

The design is right and honestly bounded. Before building, close the one-field fuel bypass (bind `meta.wasmtime` in G2), tell the owner that question 105's option (a) must cover the whole set, fix the landing order against 037, and point criteria 2 and 3 at records that can still prove something.

## Confirmation (2026-10-19)

The same reviewer read the revision in the -085 worktree:

- `git diff 63d3e00..6523595`: the spec, `forge_synthetic.py` and `.out`, and the new `hidden_wide.py` and `.out`;
- 63d3e00 is the draft rebased onto main `9d89535`;
- question 105 as amended on main (`67312f3`).

I wrote nothing in any git tree. My new probes are in `work/synth2/` and `work/fake/`.

**Each finding:**

- **F1: written in, and reproduced again (EXECUTED).**
  - What the spec now says:
    - Decision 3 adds a G2 clause: each record's `meta.wasmtime` must equal `locked_version("wasmtime")` from the gather's own `uv.lock`.
    - The red line, the `Inputs.wasmtime` field and two new table rows (`"48.0.0"` and null) are written in.
    - A unit test ties the real lock to `importlib.metadata.version("wasmtime")`.
    - The reason for not making `fuel_not_compared` red is the one I gave.
  - What I re-ran: the author's updated `forge_synthetic.py` at `6523595`. It gives:
    - the control (ten times the fuel, `49.0.0`) red at G5;
    - the same forgery with `"48.0.0"` green;
    - the same forgery with null green;
    - "15 of 17 forgeries leave gather green".

    This matches my real-record rows. The new G2 clause turns both green rows red, and the synthetic good set already carries `meta.wasmtime` `"49.0.0"`.
- **F2: written in.**
  - Decision 8 names the snapshot as the second varying artifact. It says option (a) must define a canonical digest of the set, or else the set clause gives way while the exception holds, in writing, by the spec that builds the answer.
  - *Coordination* points to it.
  - Question 105's option (a) on main now says the same (`67312f3`, READ).
- **F3: written in.**
  - The order 065, 085, 037 is stated in the status, in criterion 6 and in *Coordination*.
  - Criterion 6b gives the other order its two expected G7 lines and holds tags.
  - Line 79 replaces line 78 throughout.
- **F4: written in.**
  - Criterion 2 runs on the branch dry run's own 19 records: the honest baseline must be red on exactly the G7 `set_sums` line, and each of the seven forgeries must add only its own line(s).
  - Criterion 3 runs the a7 and 065 records against the new rules only, as functions.
  - Both now prove something.
- **F5: written in, and probed (EXECUTED).**
  - `hidden_wide.py` finds nothing at `6523595`, and nothing on main `9d89535`.
  - I planted spellings of my own in a fake tree. The prototype flagged all five:
    - a CI need in a `tests/conftest.py` list;
    - a CI need as a value in a `NEED_OF` dict in a conftest;
    - `needs.need(*("three systems",))` in a fixture;
    - an f-string `pytest.skip(f"needs: {x}")` in a helper (through its `"needs: "` piece);
    - a keyword argument `need="oracle"` in a harness file.
  - It correctly left alone a `need("oracle")` inside a `test_` body.
  - `jobs.py`'s path pieces (`JOB_DIR / "oracle"`) stay unflagged, as Decision 1 says.
- **F6: written in.** The map names `build`, `macos`, `linux` and `windows`, as `expected_keys` names them.
- **F7: written in.**
  - Decision 4 says "every file of the artifact set" and how the rest is bound.
  - Decision 7 lists the cheap lies now closed, F1's among them, and the one left open: metric values off darwin.
- **F8: written in.** Decision 1 lists where the derivation fails open beside where it fails closed.
- **N1:** written down as Decision 9 (no band in 085), with the reasons and the evidence. That is a fair answer.

**Two notes for the builder, neither a condition:**

- **c1. Two more spellings the scan does not see** (EXECUTED in the fake tree). Both fail closed in the gather, so the risk is only a red line found at a dry run rather than in the fast tier.
  - **A harness module constant set by a plain assignment** (`X = "three systems"`). It is not flagged, because harness strings count only as arguments or container members. A later `need(X)` in a harness helper would therefore be seen only at a dry run.
  - **A CI need passed to a helper from inside a `test_` body** (`helper("descriptor limit")`, where `helper` skips with that need).

  So Decision 1's "only a need computed at run time from pieces stays unseen" is slightly narrow. Either add these two spellings to that sentence, or flag a plain module-level assignment of a bare CI string in `tests/harness/`. That does not touch `jobs.py`, whose pieces are inside a `BinOp`.
- **c2.** `hidden_wide.py` skips the two exempt files with a `break` inside the node walk. That works, but the built `hidden_ci_needs` should skip them before parsing, so the exemption is visible in the code.

**Confirmed for build.**
