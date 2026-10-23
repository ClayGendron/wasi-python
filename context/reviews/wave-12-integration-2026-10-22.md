# Review of wave 12's integration (095, 067) and the 0.1.0 release acceptance

- **Date:** 2026-10-22
- **Reviewer:** a fresh agent (Claude Opus 5.5). I wrote none of 095 or 067 and reviewed neither before. Their pre-build, delta and build reviews belong to other agents. I am the wave's integration reviewer (AGENTS.md rule 8; constitution §5.7).
- **Reviewed:** the wave's tip **`55d475fb`** (`origin/spec/067-the-pure-python-packages-own-tests`). It is linear: main `c0d3a212`, then 095 cherry-picked (`origin/wave/12` `99dcd257`), then 067 rebased onto that by its builder. There is no merge commit. The version bump is not on it yet.
- **Read first:** AGENTS.md rules 2, 6, 6a, 6b and 8; `context/progress/README.md` (the landing steps, the release tier, the release acceptance); `decisions.md`'s two newest entries; wave 11's integration review as the model; 095's build review (`origin/review/095-build` `27eeef11`); both specifications' landing notes.
- **Ran** (in this worktree at `55d475fb`, with no artifact set; while `build/lane.lock` existed, nothing but node ids, unit files and collection):
  - `pytest --collect-only` at `c0d3a212`, `99dcd257` and `55d475fb`. The first two were run in `git archive` copies in my scratchpad. Each entry's rows, units and files were counted from these.
  - The unit files `test_packages.py`, `test_pure_suites.py`, `test_tiers.py`, `test_shards.py` and `test_scan.py`: **505 passed**.
  - `tests/checks/test_rules.py`, `test_upstream_files_are_well_formed` and `test_every_compiled_family_has_its_smoke_cover`: **70 passed, 3 skipped**. The skips are the artifact directory (2) and the prior-art clones (1), which this worktree lacks.
  - `sameness.py --claims` (Appendix A), comparing wave 11's record (`build/wave-11/lane/judge1-record.json`) with the lane's gate record (section 3).
  - Small read-only scripts over the harness: the shards' fuel, the claim patterns' coverage, the nine `package_paths` tables, the scoring of the structural review, and the test-source URLs.
  - `gh run view` and the job logs of 067's branch run `39715865231`, wave 11's dry run `39667712127`, and 095's run `39708064741`.
- **Box:** 23:33 to about 00:30. That covers the lane's gate run (23:37 to 23:52) and reading 067's branch run while it ran.

## 1. The rebase and the merge (EXECUTED)

**095's cherry-pick is its reviewed tip.** `git diff 2418c037 99dcd257` is byte for byte `git diff 2a8091d7 c0d3a212`: seven files, all `AGENTS.md` and `context/`, which are main's commits after 095's base. So the 095 that wave 12 carries is the reviewed 095. `2418c037` is `fec1661b` (the commit 095's build review read) plus the answers to that review. I read the answer to M1: each clock-stepped group's `clock_reason` (`scipy.toml:782,791`), the README and the memo now give the compared-point counts, 114 and 91 of 240. L1 and L2 are written in as the review's text gave them. The review's "lands once M1 is written in" is met.

**067's rebase keeps every line of 095.** Eleven files changed on both sides. For each one I listed 095's added lines that 067's diff removes (`c0d3a212..99dcd257` "+" lines against `99dcd257..55d475fb` "-" lines):

| file | 095's lines that 067 removes | what they became |
|---|---|---|
| `release.yml` | 6 | the two matrix lines and the four gather lines, rewritten longer; each matrix equals its system's plan in `release_shards.toml` (macOS 7, Linux 24, release 226, Windows 6) |
| `tests/harness/packages.py` | 3 | `ENV_ALLOWED`'s comment, extended with reportlab's and narwhals' reasons; `group_spec`'s `return {`, now `spec = {` with a `modules` keyword; `PackageRun(...)`, now called by keyword with `deselected` |
| `tests/harness/upstream.py` | 1 | `PACKAGE_SUITES = (` became `COMPILED_SUITES = (`, and `PACKAGE_SUITES = COMPILED_SUITES + PURE_SUITES` |
| `known_gaps.toml`, `release_shards.toml`, `packages.toml`, `release-tier-claims.toml`, `CHANGELOG.md`, `README.md`, `test_rules.py`, `test_v1_3_upstream_suites.py` | 0 | both sides kept |

So 095's rows, groups, gaps, reasons, shards and ledger block are unchanged by the merge.

**`package_inits` and `env` take 095's meaning.** I checked the builder's claim (EXECUTED). I loaded each of the nine families at the tip with 095's generator and compared the result with the `[package_paths]` table that 067's pre-rebase build commit `aaf8a962` listed. The nine families are beautifulsoup4, et-xmlfile, html5lib, joblib, mpmath, openpyxl, networkx, toolz and xlsxwriter. In every one the generated table equals the listed table. `package_inits` is true on both sides, and the stage folders are the same. The staged files are therefore the same. One behaviour is added: 095's driver imports each ancestor from the zip before pytest starts. That can only make a run stricter, and these rows are new, so nothing accepted can move. `env` is 095's form. reportlab's `RL_TEST_OUTDIR` and narwhals' three variables joined `ENV_ALLOWED`, each with a reason. `test_upstream_files_are_well_formed` passes.

**The other named conflicts.**
- `test_rules.py` drops the citation allowances for `spec 039`, `spec 042` and `spec 067`. `packages.toml` no longer names them, and the string rules pass.
- `test_v1_3_upstream_suites.py` keeps 095's `derived` fact and 067's `deselected` fact.
- The shards were generated again after 095's last shard. `test_release_shards_cover_the_judge` and `test_release_judges_in_shards` pass.

## 2. The claim lists

There are two lists. They are read at two different moments.

- **At the landing**, the normal-tier list goes with sameness between wave 11's record and the lane's records. Neither entry wrote it as a TOML block, so I wrote it from their *For the lane, as built* and from the rows I counted. It is Appendix A.
- **At the release acceptance**, the release-tier list is `context/release-tier-claims.toml` as merged. Read against a normal record, sameness compares no release-tier row ("release-tier rows not compared: 883"). Against the previous release record, it compares only release-tier rows (`--tier-rows release`). 0.1.0 is the first release acceptance, so there is no previous release record. The ledger is the stated reason for each row, and the ratchet does the comparing (progress README: "if the previous one is gone, say so in the reason and rely on the ratchet").

**The rows, counted from collection** (normal-tier rows, then release-tier rows deselected in a normal run):

| | 095 | 067 | the version bump |
|---|---|---|---|
| new normal rows | 17: four smoke suites, 12 smoke classes, `test_every_compiled_family_has_its_smoke_cover` | 74: 42 smoke suites, 31 smoke classes, `test_v1_5_rebuild_from_pins.py::test_every_test_source_is_pinned_and_named` | none |
| new release-tier rows | 333 | 512 | none |
| units, per file | 46: `test_packages.py` +42, `test_fetch_trees.py` +3, `test_tiers.py` +1 (equal to its block) | 34: `test_pure_suites.py`, a new file (equal to its block) | none |
| changed | none | none | none (the two version rules keep their ids and must still pass, M3) |
| grows | none | **23 package-driver groups, both ways (M1)** | none: `src/` and `CHANGELOG.md` are not judge files, and the guest does not read the version |
| retired, moved, fewer passes | none | none | none |

Collected at the tip: 3,319 normal and 883 release-tier rows. That is 21 rows from 102, the 17 contourpy rows 102 moved, 333 from 095 and 512 from 067. The unit suite is 2,331, which is wave 11's 2,251 plus 46 plus 34.

**The ledger as merged** (`context/release-tier-claims.toml`), checked by a script that matches each `new` pattern against every release-tier row the configurations define:
- **It is complete.** Every one of the 883 release-tier rows is matched by some claim. 102's `new` covers 21. 102's `changed` covers its 17 moved contourpy rows. 095's covers 333 and 067's covers 512. No row is claimed by two specifications.
- **No wildcard reaches past its own entry's release rows.** 095's six wildcards also match 16 normal-tier smoke rows. That is harmless, because `--tier-rows release` reads release-tier rows alone; 095's build review accepted it (N2). 067's patterns (`<family>-r*`, `sympy-slow-*`) match its 512 release rows and no normal row.
- **Units are counted per file:** 46 and 34, as above.
- **Two gaps:** 067's block has no `grows` or `growth` for M1's mechanism, and six of its class patterns match nothing. Both are L3.

## 3. The lane's normal-tier gate (EXECUTED: read `build/wave-12/gate.log` and its record)

The lane ran `uv run pytest -n 6` in the main tree on `55d475fb` with no `--accept`: 14 min 32 s, on the set rebuilt from the pins. python.wasm (`d41926055c3f8697`), the snapshot and the zip are byte for byte wave 11's. The set's `SHA256SUMS` is `3339091f`, against wave 11's `1556bbd5`, because `MANIFEST` and `LICENSES` changed with 067's pins and patches.

```
wasi_python v1: 820/1871 pass · 99 gap · 69 blocked · 0 fail · 883 deselected   (unit suite 2329/2331, 2 skipped)
ratchet vs 2598389972: lost 0 · absent 0 · unrun 0 · gained 10 · grew 11 · release tier not run 17 · judge changed: … and 306 more
RED: 11 metric(s) grew
```

- **0 fail, lost 0.** The unit suite is 2,329 of 2,331; the 2 skipped are the base's own.
- **69 blocked.** 67 are "source tree <package>" across 38 of 067's families: the main tree had not unpacked their test sources. The other 2 are the wheel and the three systems, as before. So **the gate did not judge 067's smoke rows** (M2). Only 8 of 067's 73 new upstream rows ran.
- **GREW 11**, and sameness shows 18 fuel lines past 1e-4 in both directions. All of them are M1. Section 5 says why.
- **Sameness, Appendix A** (wave 11's `judge1-record.json` first, the gate's record second): exit 0. `explained by claims: 067 94 · 095 18`; `release-tier rows not compared: 883`. Without M1's `grows`, it exits 1 on the 18 fuel lines.

**What the release acceptance should show in its normal-tier rows**, once the trees are fetched and H1 is fixed: **858 pass, 128 gap, 2 blocked, 0 fail.** That is wave 11's 810, plus 095's 4 smoke suites and its cover rule, plus 067's 42 smoke suites and its pins rule. The gaps are 85, plus 095's 12 classes, plus 067's 31. Every release-tier row should pass, or xfail as its gap says, with 0 fail. The ratchet line should read lost 0, absent 0, unrun 0, and grew 0 once the flags of section 6 are given.

## 4. The release tier on CI (EXECUTED from the TOMLs and `release.yml`; times INFERRED)

- **Shards.** There are 226 release shards: 102's 12, 095's 104 and 067's 110. There are 24 normal Linux legs, 7 macOS legs and 6 Windows legs. Each matrix equals the plan.
- **Fuel.** The release tier measures **187.4 T**. Adding the nine traps run to their caps gives 187.9 T. The caps sum to 285.5 T.
- **The 30-minute timeout.** No shard comes near it.
  - The largest shard is `upstream-sci-release-01` (`testLargeBoth`, 3,023 G measured, a 4.6 T cap). At 0.31 s per G plus 60 s of setup, that is **16.6 min** measured and **24.8 min** if it runs to its cap.
  - Next are `upstream-pure-r-001` (2,865 G; 15.8 min, or 23.2 at its cap) and `upstream-sci-release-02` (2,848 G; 15.7 min, or 23.2).
  - Not one shard passes 30 min, measured or at its cap.
  - The "4.5 T" in 067's notes is `test_function_range1`. It is a trap run alone to 50 G, not a group. A shard that ran to its cap at a rate 20% slower than 0.31 s per G would come to about 29.7 min (N1).
- **The dry run on main's width.** 274 jobs will run:
  - inputs, the build, two rebuilds, the build shard, same-bytes and save-set (main is a branch ref);
  - 7 macOS, 24 Linux, 226 release and 6 Windows judge legs;
  - the gather;
  - three verify jobs.

  Attest, publish and PyPI are skipped.
  - Each judge matrix has `max-parallel: 18`. A release run therefore asks for 18 + 18 + 7 + 6 = 49 jobs at once, past the plan's 40. The rest queue. The workflow's comment "one run stays within the plan's 40 jobs" holds only on a normal run (L2).
- **The dry run's length** (INFERRED).
  - The set is built from source on main: about 34 min, as on wave 11's dry run.
  - The release legs then take Σ(fuel × rate + 60 s) / 18. That is 43,550 s to 71,660 s of job time, or **40 to 66 min**, at 0.16 to 0.31 s per G. The normal legs, the longest about 18 min (macOS own-hostile), run beside them and take slots from them for the first 20 min or so.
  - The gather takes a few minutes over about 260 records.
  - **About 1 h 30 to 1 h 50 in all.** The tag's run is the same length again.
- **The three-run limit.** 067's branch run `39715865231` is live now, and H1 needs a second one. The dry run on main makes at most two release-workflow runs live at once, which is within the limit, provided the H1 run has finished.
- **Downloads.** Each of 226 release legs fetches its shard's kit and test sources from PyPI, GitHub, heptapod and the other pinned hosts. One failed download reds the dry run (N3).
- **The local release acceptance** (INFERRED). At `-n 6` and about 8.7 G/s per worker on darwin, 188 T takes about 60 min, plus the normal tier's 15 min. That is **about 1 h 15 to 1 h 30**, longer than 067's "1.2 to 1.5 h at `-n 3`" for its own share alone.

## 5. Why contourpy grew (EXECUTED; the mechanism READ)

python.wasm, the snapshot and the zip are wave 11's bytes. Only 067 changes the guest-side driver of the package families, `tests/upstream/package_drive.py` (+67 lines). 095 does not touch it (`git diff --stat c0d3a212 99dcd257 -- tests/upstream/package_drive.py` is empty). Every package family's guest run compiles that driver from source (`sys.dont_write_bytecode`). The driver now gains:
- `sys_flags`;
- a `FunctionItem` class;
- a `_named` resolver for the doctest runner and checker;
- the `module_functions` loop;
- a `pytest_deselected` hook that pytest calls on every deselection, contourpy's `-m 'not slow'` among them;
- a second `load_profile`.

Each group's JSON also carries 067's new keys.

The record agrees with this. Of the 39 upstream groups in both records:
- **all 23 package-driver groups moved** (contourpy, kiwisolver, lxml, matplotlib, mpl-*, pillow, regex), from **contourpy-1 +0.116%** to **mpl-axes_grid1 −0.076%**;
- **all 16 numpy, pandas and CPython groups are equal to the instruction.** They run `drive.py` and regrtest, which no entry touched;
- no status moved and no `passes` moved.

So the cause is 067's driver. It is not the staging merge: `package_inits` and `env` touch no compiled family but 095's own, whose rows are new. No claim named it (M1).

## 6. For the lane

**Before the release acceptance** (each of these is a condition, not advice):
1. **H1 fixed on the tip** by 067's builder, then a branch run (normal tier) on that exact commit with `upstream-pure-smoke-a` and `-b` green, and its build's `SHA256SUMS` `3339091f` (or the fixed tip's, if the fix moves the set; it should not, since `fetch.py` is not a build input).
2. **067's build review's verdict**, being written on `review/067-build`. Its reviewer reads the H1 fix as a delta.
3. **The trees fetched in the main tree** for every 067 family (M2). Note that the main tree's `00_download` step reported "95 pins, 0 fetched". If `downloads/` lacks the nine `-tag` archives, the lane's own fetch fails the same way until H1 is fixed.
4. **The version bump commit** (M3):
   - `__version__ = "0.1.0"`;
   - `CHANGELOG.md`'s `## 0.1.0a8 — unreleased` renamed by hand to `## 0.1.0 — unreleased`. Do not run `release/version.py bump --to 0.1.0`: it adds an empty "- (what changed)" section above and leaves the 0.1.0a8 section unreleased;
   - `context/reviews/0.1.0-structural-review-2026-10-21.md` from `origin/review/0.1.0-structural-delta` (`45e7ab19`), committed on the tip. I scored it with `scan.structural_review_errors("0.1.0", …)`: `[]`, all eight rows. With no file the rule gives "0.1.0 is a release; reviews/ has no 0.1.0-structural-review-<date>.md";
   - this review.

   Then the fast rules by node id: `test_a_release_has_its_structural_review` and `test_the_version_is_released_by_the_book`.

**The release acceptance's flags.** It is one run, `uv run pytest -n 6 --tier release --accept …`. Each reason begins with its specification's number. The lane composes the strings as in wave 11.

- `--accept "Wave 12 (095, 067) and Release 0.1.0: the release tier, on <commit>; the first release acceptance, so there is no previous release record and the release-tier rows rest on the ratchet; the record kept under build/releases/0.1.0/ (SHA-256 <…>): …"` followed by:
  - `095: scipy's, scikit-learn's and statsmodels' own tests` (its *as built*);
  - 067's string from its landing notes: `067: the pure-Python packages' own tests: 42 packages, 42 smoke groups in the normal tier (12,564 passes, 853 G), each whole suite in 420 release-tier groups (92.8 T); 117 classes, 6 traps; 39 test sources pinned and 4 test-source patches carried, named in MANIFEST`.
- `--accept-judge`:
  - `095: the three families' TOMLs, lists and gaps, their harness keys, the trap argv named under the tree, the shards and the workflow`;
  - 067's reviewed `--accept-judge` text (its *For the lane*), plus `; the doctest setup, runner and checker keys; package_inits and env merged onto 095's meaning`, plus H1's clause, for example `; fetch.py names each test source by its pin`.
- `--accept-growth`, M1's reason, which also covers the 17 accepted contourpy release rows:
  - `067: the package driver (tests/upstream/package_drive.py), which every package family's guest run compiles from source, gains sys_flags, the doctest runner and checker keys, module functions and a pytest_deselected hook; every package-driver group's fuel moves both ways (contourpy-1 +0.12% the largest rise, mpl-axes_grid1 -0.076% the largest fall), numpy's, pandas' and CPython's groups equal to the instruction, python.wasm, the snapshot and the zip byte for byte wave 11's, every pass count unchanged (the integration review's M1)`
  - The 17 contourpy release rows were last accepted before 102's driver change and 114's zip. They run now for the first time since. So append the two landed reasons the ledger holds for them: `102: the regrtest driver's Z line …; contourpy's normal groups run -m 'not slow'` and `114: the zip's two members move every release-tier group's fuel both ways; passes unchanged`.
  - A contourpy release row whose **passes** fall, or whose status moves, is a finding. It is not growth.
- `--accept-fewer-passes`: **none.** `--retire`: **none.** `--accept-tier-move`: **none.** `--partial`: **none.** The 2 blocked rows are the wheel and the three systems, as wave 11 accepted them.

**After the release acceptance**, context only:
- move the ledger's four blocks under `## 0.1.0` in a new `context/release-tier-claims-history.md`, and empty the ledger (progress README);
- write L3's lines into 067's block first;
- write 095's three lane items (its *For the lane, as built*): 088's roadmap line, a reserved number for the uarray `get_native_id` finding, and 074's line;
- write L4's README lines. They may follow the dry run (rule 6b).

**The dry run on main** (rule 6b; `decisions.md`, 2026-10-22, "dispatch first"):
- Dispatch it the moment main moves. It runs the release tier because it is on main.
- Read every one of its 274 jobs. A red release leg is either H1's family (if H1 was not fixed) or a download (N3, re-run once by hand, never polled). Anything else is a finding against its entry.
- The gather concludes success, with `meta.tier` `release` and `meta.set_source` `built`, the set matching the lane's.
- Record the release legs' longest job (N1).

## Constitution checks

- **§4.1:** 067 carries four test-source patches under `recipes/patches/`, each named in `MANIFEST` and the CHANGELOG. 095 carries none. The merge adds or changes no patch.
- **§4.2:** 067's 39 test sources are pinned in `downloads/SHA256SUMS` and `00_download.sh`. H1 is about where the judge saves them, not about whether they are verified: `fetch` still checks each SHA-256 before it renames.
- **§4.3 to §4.5:** `src/` is untouched by both entries. python.wasm, the snapshot and the zip are byte for byte main's, so no guest import or export moves.
- **Rule 4:** `tests/known_gaps.toml` and `tests/upstream/*` change only by the entries' own measured groups, classes and gaps, each a judge change with its reason. The merge removed no 095 line from either. `context/progress/` is untouched.
- **Code speaks for itself:** the string rules pass on the tip, and the merge dropped three allowances along with the strings they allowed.
- **Structure:** neither entry changes `src/`. The bump changes one `src/` line, the version string.
- **§7:** nothing tripped.

## Findings, most severe first

1. **H1 (High, 067): on CI, `tests/upstream/fetch.py` saves nine test sources under the wrong name, so both of 067's normal shards are red.**
   - The code: `fetch(sha, url, dir)` names the file by its URL, `dest = dir / url.rsplit("/", 1)[1]` (`fetch.py:70`). `fetch_trees` then unpacks `downloads/<pinned name>` (`fetch.py:172`).
   - The nine `tests` lines in `scripts/00_download.sh` whose URL name differs from the pinned name (EXECUTED): cycler (`v0.12.1.tar.gz`), cloudpickle (`v3.1.2.tar.gz`), threadpoolctl (`3.7.0.tar.gz`), tomli_w (`1.2.0.tar.gz`), xlrd (`2.0.2.tar.gz`), xlsxwriter (`RELEASE_3.2.9.tar.gz`), openpyxl (`openpyxl-3.1.5.tar.gz`), et_xmlfile (`et_xmlfile-2.0.0.tar.gz`), and pypdf's sample files (`818dc013ad1f537198e9fcfae8a6b0dffe25ffa3.tar.gz`).
   - Why only CI shows it: locally the builder's `downloads/` already held each file under its pinned name, so `fetch` found it in place and returned.
   - **Failure (EXECUTED):** run `39715865231` on `55d475fb`. `judge (ubuntu-24.04, upstream-pure-smoke-a)` and `-b` are red at "What the shard needs": `openpyxl-3.1.5-tag.tar.gz: [Errno 2] No such file or directory: …/downloads/openpyxl-3.1.5-tag.tar.gz` and `cycler-0.12.1-tag.tar.gz: …`.
   - What follows from it (INFERRED): on the dry run on main, every release shard that holds an openpyxl, xlsxwriter, cloudpickle or pypdf release group is red the same way. The fix changes a judge file, so an acceptance made before it would not be the judge of the fixed tip, and the tag would need a second release-tier acceptance.
   - **Fix (067's builder):** save to `dir / <pinned name>`. Pass the name from `fetch_trees` (and from `fetch_files`, if an extra can differ). Write a unit row first, seen failing: a `tests` line whose URL name differs from its pin, fetched into an empty folder. Then dispatch a branch run whose two pure-smoke shards are green. Then a short delta read by 067's build reviewer.
2. **M1 (Medium, 067's claim list): 067's package driver moves every package-driver group's fuel, and no claim names it.**
   - **Failure:** the gate is RED at 11 GREW lines. Sameness with the entries' claims exits 1 on 18 lines. Rule 6a reads that as an ejection, and an `--accept-growth` with no stated reason accepts growth no one explained. This is wave 09's, 10's and 11's M1 again, in the same shape.
   - **Fix (done here, context only):** Appendix A's `grows` for 067, and the `--accept-growth` reason in section 6. With them, sameness exits 0 (EXECUTED).
3. **M2 (Medium, the lane): the gate did not judge 067's normal rows, and nothing turned it red.**
   - 65 of 067's 73 new upstream rows were blocked by "source tree" in the main tree. The ratchet line shows no `upstream unrun` count, because these rows were never accepted. So an `--accept` on that record would have recorded wave 12 without one of 067's smoke groups run locally.
   - **Fix:** the trees fetched (the lane is doing it), and the release acceptance's own record read for "2 blocked" only.
   - **Follow-up (after 0.1.0, a judge change of its own):** `--accept` refuses a new upstream row blocked by a source tree in the main tree, as it already refuses an accepted one.
4. **M3 (Medium, the lane): the bump turns two rules red unless the tip also carries the structural review and the renamed CHANGELOG section.**
   - `test_a_release_has_its_structural_review` needs `context/reviews/0.1.0-structural-review-<date>.md`. Today it is only on `origin/review/0.1.0-structural-delta`.
   - `test_the_version_is_released_by_the_book` needs a `## 0.1.0` CHANGELOG section.
   - **Failure:** a red rules row in the one long release-tier run. That costs about 1.5 h, or with `version.py bump`, release notes reading "(what changed)".
   - **Fix:** section 6, item 4.
5. **L1 (Low, both entries' claim lists): each leaves out one new normal-tier rule row.**
   - 095's *as built* lists "the four smoke groups' rows and their classes", but not `test_every_compiled_family_has_its_smoke_cover`.
   - 067's skeleton omits `test_every_test_source_is_pinned_and_named`.
   - **Fix:** done in Appendix A.
6. **L2 (Low, the workflow): the release matrix is 226 legs, with little room left.**
   - GitHub caps one job's matrix at 256 (INFERRED from GitHub's documented limit), so 30 more legs remain.
   - The gather's `artifact-ids` line for the release legs is now 13,540 characters, against GitHub's 21,000-character limit on one expression (INFERRED).
   - The comment "one run stays within the plan's 40 jobs at once" is false on a release run, which asks for 49 jobs at once (the rest queue; nothing fails).
   - **Failure:** the next package's release shards break the matrix or the expression at parse time, and the run then fails before any job starts.
   - **Fix (after 0.1.0):** split `judge-release` into two jobs, or pack the release shards past 725 G, and correct the comment.
7. **L3 (Low, 067's ledger block): no growth reason for the accepted contourpy release rows, and six class patterns that match nothing.**
   - The patterns that match nothing: `[packaging-r*`, `[xlsxwriter-r*`, `[beautifulsoup4-r*`, `[patsy-r*`, `[attrs-r*`, `[formulaic-r*`, under `test_upstream_class`. Those families have no release-tier class.
   - **Fix (context only, the lane at the landing):** add to 067's block: `grows = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-filled-*", "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-lines-*"]` and `growth = "067: the package driver moves every package-driver group's fuel both ways; passes unchanged"`. Drop the six patterns, or leave them; they are harmless.
8. **L4 (Low, README): 0.1.0 is a final version, and the README still calls the releases alpha.**
   - `README.md:15`: "Status: **alpha.**" `README.md:877`: "Releases are alpha builds for now, numbered `0.1.0aN`".
   - The release job marks a GitHub release prerelease only for `*a*|*b*|*rc*` (`release.yml:2444`). So 0.1.0 becomes the repository's "Latest" release, and `pip install wasi-python` takes it without `--pre`.
   - The wheel will be `wasi_python-0.1.0-py3-none-any.whl` and the set `wasi-python-0.1.0-wasm32-wasip1.tar.xz`. Nothing else matches on the version string: every workflow glob is `wasi_python-*.whl`, and the gather's record names no version.
   - **Fix:** the owner's wording, README only. It may follow the dry run.
9. **N1:** no shard reaches the 30-minute timeout, even run to its cap (section 4). The largest shard's measured time on the dry run is the first CI figure for it. Record it.
10. **N2:** 095's ledger wildcards also match its 16 normal smoke rows. This is harmless under `--tier-rows release`, and 095's build review accepted it. Appendix A names those rows for the normal-tier comparison.
11. **N3:** the dry run makes 226 legs each fetch its own downloads. A single outage reds the run. Under the owner's rule (2026-10-21), re-run the failed jobs once, by hand, later. No polling.

## Disposition (for the lane; 067's builder where named)

1. H1: 067's builder fixes `fetch.py` with a unit row seen failing first, rebases onto the tip, and dispatches a branch run. 067's build reviewer reads the delta. The lane holds the release acceptance until then.
2. M1: Appendix A and section 6's `--accept-growth`.
3. M2: the trees fetched; the acceptance's record read for 2 blocked only. The follow-up check goes to the roadmap after 0.1.0.
4. M3: the bump commit as section 6, item 4 says.
5. L1: Appendix A. L3: the ledger edit at the landing. L4: README, after the dry run. L2: the roadmap after 0.1.0.
6. N1 to N3: as written.

## Verdict

**Not yet. Wave 12 lands once H1 is fixed.** 095 is clean as merged: its cherry-pick is its reviewed tip, and the merge kept every one of its lines. 067's rebase onto 095 is sound: the nine `package_paths` tables are equal, `env` is 095's, and no 095 row or reason changed. But 067's `fetch.py` cannot fetch nine of its test sources on CI. That red is real: it shows in 067's own branch run and would show again on the dry run on main.

The wave lands, and its acceptance is the 0.1.0 release acceptance, once all of these hold:
1. H1 is fixed on the tip, reviewed as a delta by 067's build reviewer, and a branch run on that exact commit has both pure-smoke shards green (the set `3339091f`);
2. 067's build review gives its verdict;
3. the bump commit carries the structural review and the `## 0.1.0` section (M3), and the main tree has every 067 tree (M2);
4. the one `--tier release --accept` run on that tip carries section 6's flags, M1's `--accept-growth` included, and shows 0 fail, lost 0, 2 blocked, and 858 normal-tier passes with every release row passing or a gap;
5. `sameness.py --claims` with Appendix A, comparing wave 11's record with that record, prints nothing but notes (EXECUTED on the gate record: exit 0).

If the fix cannot land tonight, the lane may eject 067 and land 095 alone with Appendix A's 095 block. 0.1.0 would then ship without the pure-Python suites. That choice is the owner's scope decision, not this review's.

In one line: the merge is clean and the paperwork needs one growth claim, but 067's fetcher saves nine test sources under their URL names, so its shards are red on CI and must be fixed before the release acceptance runs.

## Appendix A: the claim file (normal tier)

Copy to `build/wave-12/lane/claims.toml`. It was checked with `sameness.py` above: exit 0 against the gate's record.

```toml
# Wave 12's claim list (095, 067), for
#   uv run python tests/harness/sameness.py --claims <this file> \
#     build/wave-11/lane/judge1-record.json <the lane's wave-12 record>
# Written by wave 12's integration reviewer from each entry's "For the lane, as built", every row
# counted at the three commits (pytest --collect-only at c0d3a212, 99dcd257 and 55d475fb).
# Normal-tier rows only. Against a normal record no release-tier row is compared (sameness says
# so in a note); their claims are the ledger's, context/release-tier-claims.toml.

[[claim]]
spec = "095"
new = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[scipy-smoke-a]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[scipy-smoke-b]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[scikit-learn-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[statsmodels-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-smoke-a-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-smoke-b-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-smoke-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-smoke-*",
  # the integration review's L1: a normal row 095's "as built" list leaves out
  "tests/checks/test_v1_3_upstream_suites.py::test_every_compiled_family_has_its_smoke_cover",
]
units = 46  # test_packages.py +42, test_fetch_trees.py +3, test_tiers.py +1

[[claim]]
spec = "067"
new = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[fonttools-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pyparsing-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cycler-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[packaging-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[python-dateutil-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[six-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[six-smoke-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[tzdata-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[openpyxl-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[et-xmlfile-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[et-xmlfile-smoke-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[xlsxwriter-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[xlrd-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[xlrd-smoke-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pypdf-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[beautifulsoup4-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[soupsieve-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[html5lib-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[webencodings-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[defusedxml-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[defusedxml-smoke-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[xmltodict-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pyyaml-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[tomli-w-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[jinja2-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[jinja2-smoke-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[markupsafe-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[tabulate-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[tabulate-smoke-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[charset-normalizer-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[networkx-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[patsy-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[sympy-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[mpmath-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[mpmath-smoke-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[attrs-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[more-itertools-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[toolz-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[toolz-smoke-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[tqdm-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[tqdm-smoke-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[typing-extensions-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[typing-extensions-smoke-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[joblib-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[joblib-smoke-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cloudpickle-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[cloudpickle-smoke-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[threadpoolctl-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[threadpoolctl-smoke-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[narwhals-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[seaborn-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[seaborn-smoke-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[reportlab-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[reportlab-smoke-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[formulaic-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[interface-meta-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[wrapt-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[wrapt-smoke-*",
  # the integration review's L1: a normal row 067's skeleton leaves out
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_every_test_source_is_pinned_and_named",
  "tests/unit/test_pure_suites.py",
]
# the integration review's M1: 067's package_drive.py, the guest-side driver every package
# family's run compiles and runs, moves every such group's fuel both ways; passes unchanged
grows = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[kiwisolver]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[lxml]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[matplotlib-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[mpl-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pillow]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[regex]",
]
growth = "067: the package driver (tests/upstream/package_drive.py), which every package family's guest run compiles from source, gains sys_flags, the doctest runner and checker keys, module functions and a pytest_deselected hook; every package-driver group's fuel moves both ways (contourpy-1 +0.12% the largest rise, mpl-axes_grid1 -0.076% the largest fall), numpy's, pandas' and CPython's groups equal to the instruction, python.wasm, the snapshot and the zip byte for byte wave 11's, every pass count unchanged"
units = 34  # tests/unit/test_pure_suites.py, a new file
```

The version bump adds no block: it adds, changes and moves no row.

## The lane's addendum (2026-10-22)

- **H1** fixed by 067's builder in `84c5955c`, with a unit row seen failing first. Run 39720564953 on that commit had both pure-smoke shards green, and its set's `SHA256SUMS` was `3339091f`, the lane's; 067's build review (`0f681db0`) read the fix as a delta.
- **The first release acceptance** on `855c7530` (the bump on `84c5955c`), `-n 6 --tier release`, 1 h 25 min, was refused: 12 failures. Eleven were 067's release groups that had never passed in its build, because its measuring read fuel and exit codes, not each group's verdict: networkx-r-doc (a family argument given to a docstring-only group) and sympy's wester split (a 275-term `-k` that overflowed the guest's stack) plus utilities-6 (no test). 067 fixed them in `254fd3e5`, and a fresh delta review (`fce3c76b`) passed them once its M1 was answered in writing. The twelfth was the judge's own race: the sealed-leftovers scan raised on a folder another worker's guest removed. The lane fixed it in `618f891e` and `459e7f35`, each with a unit row seen failing first, reviewed fresh (`lane-sealed-leftovers-race-2026-10-22.md`: lands).
- **The release acceptance** on `eac93d0f`: history line 94, accepted in `1aa0eff7`, 1574/1872 pass, 0 fail, 296 gap, 2 blocked (the wheel and the three systems), ratchet lost 0, grew 0; 1 h 24 min at `-n 6`, peak memory under 5 GiB. M1's clause is in the `--accept-growth`, M3's bump in `855c7530`, L3's lines in 067's ledger block. The record is `build/releases/0.1.0/record.json`, SHA-256 `61386a46f4a03b2f583812493b4aa05ec8ad20cebf85207d67f293c660406029`. It is the first release acceptance, so there is no previous release record to compare with.
- **M2** (blocked rows did not turn the gate red): the lane fetched 067's sources into the main tree before the acceptance, and the 67 rows ran there (0 blocked by a source tree). That the ratchet has no count for them stays a follow-up for the lane to number.
- **After the acceptance**: the ledger's four blocks moved under `## 0.1.0` in `release-tier-claims-history.md`, and the ledger is empty. Main fast-forwarded `c0d3a212..454f8b3c`. The dry run on main is 39741960669, dispatched at once.
- **Still the owner's:** L4's README wording (the status says "alpha"); the security review's D2 (a required reviewer on the `pypi` environment, admin bypass off) before the tag.
