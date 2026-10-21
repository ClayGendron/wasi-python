# Review of 102 — the release tier (build)

- **Date:** 2026-10-21
- **Reviewer:** a fresh agent (Claude), which wrote none of 102 or 101 and reviewed neither before
- **Reviewed:** `git diff 1ebb992f 492b4586` (101's confirmed tip to the builder's tip); code commit
  `63a42630`, the two later commits only the specification's text
- **Run:** none of its own, by the lane's instruction: the builder's two runs are on the exact code
  commit (AGENTS.md rule 3a), read back here: run 5 normal `39610466007`, run 6 release
  `39610491729`
- **Box:** 60 minutes (build-class, and a judge change); finished inside it
- **Re-ran** (EXECUTED; wave 10's set `d0d91cef` from the main tree, linked read-only, no
  `build/lane.lock`; the fast slot was held by another agent, so single node ids only):
  - `gh run view` of both runs: run 5 has 42 success, 1 failure (`judge (macos-15,
    upstream-macos)`), 5 skipped (`judge-release`, the gather, attest, publish, pypi); run 6 has
    52 success, the same one failure, the gather skipped, the twelve release legs green (131 to
    284 s each), one rebuild leg still running when read. No `release-record-1` exists in either
    run (the gather never ran).
  - Both macOS logs: `GREW …[cpython-fs]: fuel 63478190051 -> 63521999127`, the one red line, the
    same to the instruction in both.
  - The macOS upstream shard's record in wave 10's run `39595555875` and 101's run `39596359529`:
    `cpython-fs` 63,478,190,051 in both; `numpy-lib` 132,501,631,782 in all four runs.
  - `test_upstream_suite[cpython-fs]` by keyword, locally: at `492b4586` 63,521,999,127 (CI's
    number exactly); at `bcaae57a` (the survey commit) 63,521,999,127; at `6504f3ca` (the commit
    before it) 63,478,190,051, the accepted number exactly, `grew 0`.
  - `cpython-a`, `-b`, `-c`, `-archives` at `492b4586`, `-n 3`: 4 passed; `GREW` on
    `cpython-a` 277,280,823,020 → 277,324,081,811 (+1.56e-4), `cpython-b` 296,680,018,211 →
    296,732,993,548 (+1.79e-4), `cpython-c` 417,000,959,611 → 417,074,747,886 (+1.77e-4);
    `-archives` within 1e-4.
  - **The gather replayed** at `63a42630` over each run's downloaded shard records (`gh run
    download -p "record-*"`), laid out as the workflow lays them, each record's SHA-256 handed on
    as its job would, the runner's variables of a branch dispatch: run 5 with `TIER=normal`
    (34 records), exit 1, 47 red lines; run 6 with `TIER=release` (46 records), exit 1, 71 red
    lines. Finding H1. The replay's scripts are in the reviewer's scratchpad, stdlib only, the
    records read as data.
  - The unit nodes the gather counts (`gather.collect()`): 2,088 at `1ebb992f`, 2,198 at
    `63a42630` (+110). The goal checks: 898 at the base, 881 at the tip's normal collection
    (17 moved out), 919 in every shard record (the 38 release-tier checks back in).
  - `ruff check` and `ruff format --check` on `src` and `tests`: clean.
    `tests/unit/test_tiers.py`, `test_gather.py`, `test_scoreboard.py`, `test_scan.py`:
    498 passed. `test_release_shards_cover_the_judge`, `test_code_outside_src_names_no_context_document`
    and `test_upstream_files_are_well_formed` by name: passed.

## Acceptance criteria against evidence

1. **The checks, each seen failing first** — met for what they test (READ: landing notes items 1
   to 3, 6, 8, 10, each with its failure; the guard key's row written beside its code, named). But
   no row drives the gather's own collection (`gather.collect()`) over the real tree, and that is
   where H1 lives: every gather row hands in its goal nodes by hand.
2. **The survey before the data** — met (READ: `../research/2026-10-21-the-release-tier-survey.md`,
   EXECUTED, on wave 09's set; its delta review, the "Delta review" section of
   `102-the-release-tier-spec-2026-10-20.md`, and its two Lows written in at `e746d172`).
3. **The baseline** — met, READ (landing notes item 12: every release-tier check by node id with
   `--tier release`, twice, 36 passed and 2 xfailed both times, the records equal, fuel equal to
   the instruction). Not re-run: 8.36 T is past this review's budget.
4. **Nothing normal moves but what is named** — partly. numpy's and pandas' normal fuel equal to
   the instruction (READ from the survey; `numpy-lib` EXECUTED equal on the macOS leg of all four
   runs). CPython's passes unchanged (EXECUTED, `cpython-fs` 3,712). CPython's growth is named, but
   its numbers are the survey's set's, not this base's, and its cause is localized, not separated
   (M1).
5. **A normal branch run** — not met. `tier=normal` and `judge-release` skipped (READ, run 5); the
   gather never ran, because the macOS leg was red on the claimed growth. Replayed, it is red on 46
   G3 lines and shows no G5 move line for the seventeen contourpy rows (H1).
6. **A release branch run** — the twelve release legs ran and passed (READ, run 6); the gather's
   red lines are not shown (it was skipped), and replayed it is red (H1). The landing notes give a
   range of job times, not each leg's, and no peak or wall time (L2). Whether this run should
   exist at all under the owner's rule is M2.
7. **The gather's conditions** — half. The failed-leg half is shown (READ, runs 5 and 6: a red leg
   skips the gather). The skipped-`judge-release` half is not, and, had it run, the gather would
   have been red for a reason beyond its `if:` (H1). See "The unshown gather" below.
8. **The judge** — ruff clean (EXECUTED). The builder's fast tier on the stacked tip had 16
   failures, all explained as a wave 09 set copied into a worktree judged against wave 10's
   acceptance, and green by node id on wave 10's set (READ; L3).

## Findings, most severe first

1. **H1 — The gather's own collection leaves out every release-tier check, so the gather is red
   on every run after 102, normal or release, branch, main or tag**
   (`tests/harness/gather.py:634`, `collect()`; `tests/harness/plugin.py:266-273`).
   The defect: `collect()` runs `pytest --collect-only` with neither `--shard` nor `--tier`, so the
   plugin's normal tier removes the 38 release-tier checks from `session.items` before
   `_Collector.pytest_collection_finish` reads them. Every shard record, being a shard run, keeps
   them (as `deselected` with reason `release tier`, or as run on a release shard).
   Failure, EXECUTED by the replay: on run 5's records (`TIER=normal`), 34 lines "G3 <system>/<shard>:
   its collection is not the gather's (919 goal checks)" (the difference between a record's checks
   and the gather's is exactly the record's `release_checks`, 38 nodes, checked), and 12 lines
   "G3 upstream-release-<x>: the plan selects nothing for it". On run 6's records
   (`TIER=release`), 45 collection lines, the same 12, and 13 "ran other goal checks (+n -0)" on
   the release shards. And G5's move rule (`gather.py:327`, `if node in collected and was != now`)
   can never fire for a check moved into the release tier, since such a check is never in
   `collected`: criterion 5's "G5 move line for the seventeen" cannot appear. Main's dry run and
   every tag would fail at the gather, so `attest`, `publish` and `pypi` never run. 0.1.0 could not
   be published.
   **Fix:** `collect()` collects the whole judge, both tiers (pass `--tier release`, which the
   plugin already takes), so `goal_nodes` holds every check a shard record holds. Add two rows,
   each seen failing first: a unit row that `set(upstream.release_checks(upstream.load_all()))` is
   a subset of `gather.collect()`'s goal nodes on the real tree; and a replay row: the gather over
   two records the plugin itself writes for a normal and a release shard of a small plan, green but
   for a planted move, which G5 names. Then show it before landing as this review did: the gather
   replayed over a new branch run's records on the fixed commit, its red lines listed in the
   landing notes (only the claimed growth and the seventeen G5 move lines). One line in the
   landing notes says what the CI half still waits for (below).

2. **M1 — The growth is real and localized, but its reason quotes another set's numbers and its
   mechanism is not separated** (the claim block's `growth`, the `--accept-growth` flag; *For the
   lane*).
   The defect: the claim says "cpython-fs +6.9e-4 on the branch runs' macOS leg, cpython-a, -b,
   -c +1.2e-4 to +5.3e-4 in the survey". The survey measured on wave 09's set `142bdd38`, where
   `cpython-fs` grew +5.8e-5 (about 3.7 M) and `cpython-c` +5.25e-4. On this base's set
   `d0d91cef` the same change costs `cpython-fs` +43.8 M (+6.9e-4), `cpython-a` +43.3 M
   (+1.56e-4), `cpython-b` +53.0 M (+1.79e-4), `cpython-c` +73.8 M (+1.77e-4) (EXECUTED). The
   cause is localized to one commit (EXECUTED): `6504f3ca` gives the accepted fuel to the
   instruction, `bcaae57a` gives CI's number to the instruction, and `bcaae57a` changes, of what
   the CPython guest sees, only the stage's `/cpython/judge` (thirteen release JSONs) and the
   driver (the `Z` line, nine lines). Which of the two, and why the cost is a near-constant
   43 to 74 M a group on this set but 3.7 M for `cpython-fs` on the last, is not measured.
   Answers to the three questions asked. **Why a tier change grows fuel at all:** Decision 4 stages
   both tiers' JSONs on every run, and the driver gained a line; the guest's stage is bigger and
   its driver longer, so every CPython group pays a fixed cost. **Measured or claimed:** measured
   to the commit, and by this review to the set; the split between the JSONs and the driver is
   only claimed. **Real or noise:** real. The number is the same to the instruction in run 5,
   run 6 and a local run, and Linux fuel plays no part; rule 5 makes it red until accepted with a
   reason. It is a cost of Decision 4, not a lost pass.
   **Fix:** rewrite the growth reason, in the claim block and the flag, with this base's numbers
   above, labelled EXECUTED, "localized to `bcaae57a` (the stage's release JSONs and the driver's
   `Z` line), not separated". Optionally, separate it with two local node-id runs of `cpython-fs`
   (the release JSONs not staged; the driver at the base), and say which. Either closes M1; the
   first needs no code.

3. **M2 — The specification's text still sends builders to dispatch the release tier on a branch,
   against the owner's standing rule** (`102-the-release-tier.md:139`, `:146-148`, `:331`, `:712`,
   `:754`; and its 067 lines `:223`, `:249`, `:579-580`).
   The defect: `decisions.md`, "Fast tests and slow tests" (2026-10-21): "No branch run runs
   release groups." 102 still has the table row "a dispatch on any other branch … release when the
   dispatch input `release-tier` is true", the paragraph "Why a branch may ask for it" (naming 067
   and 095), Decision 6's "writes its block from its branch run with `release-tier: true`
   (required for it; criterion 6 here)", criterion 6, and the AGENTS.md text in *For the lane*
   ("a builder whose specification changes a release-tier row dispatches its branch run with
   `release-tier: true`"). The 067 lines are stale too: "067 adds a fourth, the node-id group"
   (the path kind is now the fourth) and "its families `release_marker`" (067's families are smoke
   families, under 102's path kind and 067's widening of it).
   **Run 6.** It was dispatched at 13:43 UTC on 2026-10-21, after the rule. It conflicts with the
   rule's letter. It agrees with the rule's reason ("we should only run the tests needed to confirm
   our new edits are working"): 102's edit is the `judge-release` job, the release shards and the
   gather's release half, and its twelve legs are the only test of that edit before main's dry run.
   This review reads it as the specification's one sanctioned proof of the workflow it builds,
   provided the text says so and the owner agrees.
   **Fix:** the lane asks the owner (AskUserQuestion) whether the `release-tier` input stays for one
   use. If yes, reword: Decision 1's row "a dispatch on any other branch: normal; release only for a
   specification that changes the release tier's machinery itself (the `judge-release` job, the
   release shards' plan, the gather's release half), once, named in that specification"; strike
   "Why a branch may ask for it" for "Why the input exists"; Decision 6's first bullet takes its
   block from the builder's local `--tier release` runs by node id, as its widened second half
   already allows, and says "No dispatch with `release-tier` true"; criterion 6 names run 6 as
   that one proof; the AGENTS.md text says "a builder whose specification changes a release-tier
   row writes its block in `context/release-tier-claims.toml` from its local `--tier release` runs
   by node id; the first CI run of its release shards is the dry run on main". If no, the input and
   its scan rows go in a follow-up specification, with a roadmap line, and the dry run on main is
   the first proof. Either way: line 223 "067 widens the path kind (doctest, doc-file and
   module-function groups, test files outside `test_*` and `*_test`, node-id groups)"; lines 249
   and 579-580 to match.

4. **L1 — The claim block is incomplete** (*For the lane*, `units = 83`).
   EXECUTED: the gather's unit count is 2,088 at `1ebb992f` and 2,198 at `63a42630`: **110**, not
   83. The 27 missing are the rows after the claim was written: the smoke kind's 10
   (`tests/unit/test_tiers.py`, item 6), the workflow half's 16 (`tests/unit/test_scan.py`,
   item 8) and the shard-moves row (`tests/unit/test_scoreboard.py`, item 10). With H1's fix,
   add its rows. The growth line follows M1. Nothing else is missing: `new` holds the 19 release
   suites and 2 classes (38 release-tier checks less the 17 moved), `changed` the 17 moved and
   three normal contourpy rows, as its note says; `passes` and `retired` empty, as EXECUTED (goal
   checks 898 to 881 normal, no check retired).
   **Fix:** `units = 110` plus H1's rows, counted again on the fixed commit.

5. **L2 — Criterion 6's numbers are not all in the landing notes** (item 11).
   READ from run 6's jobs: release legs `a` 131 s, `b` 206, `c` 223, `d` 284, `e` 206, `f` 180,
   `g` 169, `h` 161, `i` 217, `j` 138, `k` 206, `l` 170; peak concurrent jobs 39 (of the plan's
   40); wall time 35 min 43 s to the last finished job, with one rebuild leg still running when
   read; run 5 peak 32, wall 55 min 23 s.
   **Fix:** write these in item 11, and the run-6 wall time once its rebuild leg ends.

6. **L3 — The self-check is present; four of its items are not quite true** (*The builder's
   self-check*).
   "The growth list is the survey's": the house list asks for this build's (M1). "The fast tier
   … ruff clean": the fast tier had 16 failures, explained and green by node id, which is not
   "green". "The survey's delta review: passed (`979d178`), its two Lows written in (`084c5eb`)":
   those commits are on no branch of this repository after the restack; on this branch they are
   `cc7e9d61` and `e746d172`. "Every red line a growth line": true of the legs; the gather, which
   carries the G-lines, never ran (H1).
   **Fix:** reword those four items as written here.

7. **Note — 067's widening of the path kind fits 102's shape.** 067's reviewer settled that 102
   owns the path kind and 067 widens it on 102's tip. Checked: nothing kind-specific lies outside
   `tiers.py` and `packages.py`. The ratchet, the gather, the shard plan, sameness, the workflow and
   the ledger read only a check's tier (READ). No check outside `tiers.py` pins `KINDS` or
   `TEST_FILE` (EXECUTED, grep over `tests/`). The widening is additive, in five places, none a
   weakening of a 102 rule:
   - `tiers.py:40`, `KINDS`: add 067's kinds (`doctest`, `docfile`, `functions`, `node`);
     `rule_errors` already refuses a `release_by` outside the tuple.
   - `tiers.py:144-145`, `kind_of`: in a smoke family without `release_marker`, a release group
     with no `release_by` reads as a path group. A doctest group over a package folder would then
     cover that folder's test files and be refused as "under two path release groups"
     (`smoke_errors`, `tiers.py:306-338`). 067 requires `release_by` for its kinds and keeps
     `path_groups` to kind `path`.
   - `tiers.py:44`, `TEST_FILE`: a family-level pattern (upstream's `python_files`), defaulting to
     today's, so tqdm's `tests_*.py` and dateutil's `*_solution.py` enter the partition, and a smoke
     path over them stops failing "holds no staged test file".
   - `packages.py:236-246`: a path group's argv takes `--deselect` only from `not_selected` and
     traps; 067 adds each node-id group's node under that path group's paths, and a rule that a
     node-id group's node is so deselected.
   - The doctest, doc-file and module-function groups' argv and selection proofs are 067's, beside
     `packages.py`'s existing `doctest_files` keys.

8. **Note — the existing families keep whole normal groups.** numpy's, pandas', contourpy's and
   CPython's normal groups stay far larger than a smoke group. `decisions.md` applies the
   2026-10-21 rule to 095 and 067 by name, and the lane is not to reopen placement; this is not a
   finding. Run 6 peaked at 39 of 40 concurrent jobs; after 095 and 067 the release legs queue.

## Rule 4 and the tier move

- **No weakening found.** No check, golden output or allowance was edited to turn a run green.
  The `test_rules.py` edit removes nineteen allowance entries the TOMLs' comments no longer need
  (a strengthening) and passes the release groups to the plan rules. The unit edits to
  `test_regrtest.py`, `test_upstream.py` and `test_packages.py` restate counts by tier. The two new
  class files belong to new release groups, are closed by the README, and name 6 and 1 members.
  Caps follow `rule_cap` (contourpy `filled-10` and `-11` 430 G to 440 G, as their fuel rose).
- **Nothing leaves the full suite.** Each family's two tiers are made complementary by
  construction (the truth table, the keyword construction, the CPython partition proved on every
  normal run, the smoke family's staged-file partition), and the guard group
  `contourpy-slow-rest` keeps the marker release paths equal to the normal ones.
- **The seventeen contourpy rows** (`filled-1` to `-7` and `lines-1` to `-7`, `random_big`;
  `filled-9` to `-11`, the slow seeds) move whole, as checks, from the normal tier to the release
  tier. The owner's answer 3 ("Move to slow teir. We can decide what is slow tier but do not
  exclude anything from the full suite") and the 2026-10-21 rule allow it. `--accept-tier-move
  "102: contourpy's slow and random_big cases move to the release tier, seventeen groups (the
  owner, 2026-10-20)"` is honest about it: it names the cases, the count and the owner's answer.
  The move keeps their accepted status and metrics until the release acceptance runs them.

## The unshown gather

Deferring the gather beside a skipped `judge-release` to the wave's dry run is **not acceptable as
the builder left it**. Had it run, it would have been red (H1); the deferral would have carried a
gather that fails every run into main, and the first sign would have been main's dry run before
0.1.0. After H1's fix, two halves remain, and they need different evidence:

- **The gather's verdict** on real records must be shown **before landing**: the replay of
  H1's fix, over a branch run's records on the fixed commit, with its red lines in the landing
  notes. No branch run can show it on CI, because the claimed `cpython-fs` growth keeps every
  branch run's macOS leg red, so `!failure()` skips the gather, until the lane accepts.
- **The `if:` semantics** (`!cancelled() && !failure()` letting the gather run beside a skipped
  `judge-release`) may wait for the wave's dry run after the lane's acceptance, as the builder
  says. That is GitHub's documented meaning, and the scan rows hold the exact text.

What a failure there looks like: on the wave's dry run, every leg green, `judge-release` skipped,
and "gather the shards' records" also **skipped**, not success. That means the `if:` does not let
the gather run beside a skipped need. A branch run then shows green legs and no verdict, and the
lane must read the gather job's conclusion, not the legs'. If instead the gather runs and is red
with "G3 …: its collection is not the gather's" or "the plan selects nothing for it", H1 is not
fixed. The lane's dry-run read names the gather job's conclusion and its red lines.

## Structure (one line)

No `src/` line changes. The diff adds no module-level mutable, test seam or platform branch to
`src/`. `tests/harness/tiers.py` is new (403 lines; `rule_errors` 86 lines, in the harness, where no
ceiling applies). Not structural; the Kind line rightly lacks the word.

## Constitution checks

- §4.1 (patches), §4.2 (pins): untouched; no `scripts/`, `recipes/` or `downloads/SHA256SUMS` line.
- §4.9 (counts, not wall-clock): the tests count fuel and outcomes; the times here are benchmark
  facts of runs, in this review only.
- §5.5 and §5.7: the amendment text is in *For the lane*, for the lane's landing commit; not made
  here.
- §5.6: a build-class change and a judge change; the pre-build review, its confirmation and the
  survey's delta review precede this build review (READ).
- §7 never-do list: nothing tripped. No judge weakened, no artifact in git, no out-of-repo memory.
  The reviewer's probes edited no file; the set was linked read-only and the links removed.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. H1 —
2. M1 —
3. M2 —
4. L1 —
5. L2 —
6. L3 —

## Verdict

Does not land yet: H1, the gather's collection leaves out every release-tier check, so the gather
is red on every run, main's dry run and the tag included. Once H1 is fixed and shown by replay,
it lands when M1 and M2 are answered in writing and L1 to L3 are written in.
