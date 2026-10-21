# Review of 067 — the pure-Python packages' own tests in the release (the survey's delta, before build)

- **Date:** 2026-10-21
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I wrote none of 067, its survey,
  102 or 095, and none of their reviews.
- **Time box:** 30 minutes (the brief's; context only). Used about 25.
- **Read:** `AGENTS.md`; `context/decisions.md` on main `1875d4c`, "Fast tests and slow tests
  (2026-10-21, morning)"; constitution §4.1; `context/reviews/README.md`; spec 067 at `a5c4fb5b`
  (all of it); `git diff 9e168ab1 a5c4fb5b` (the survey's delta, after the revision the pre-build
  review asked for) and `git diff 36142729 a5c4fb5b -- context/` (everything since the draft); the
  pre-build review (`067-…-prebuild-2026-10-20.md`, which reviewed the draft `6ffda49`); the survey
  memo and its folder (`price.txt`, `configs.txt`, `sessions.txt`); spec 102 at
  `origin/spec/102-the-release-tier` `492b4586` (Decisions 1, 2(d), 3, 6, 15, the landing notes'
  item 6) and its built `tests/harness/tiers.py`; spec 095 at `67521f1f` ("For 102: the smoke
  kind", Decision 7, criterion 12, "For the lane"); `recipes/patches/README.md`,
  `scripts/steps/apply_patches.sh`, `tests/harness/scan.py` (`patch_errors`),
  `tests/harness/upstream.py` (`repo_patches`, the profile check), `tests/upstream/package_drive.py`.
- **Reviewed:** spec 067 at `a5c4fb5b` (branch `spec/067-the-pure-python-packages-own-tests`),
  its section "Delta from the survey" and every text it changed.
- **Run:** none. A context-only delta review; the brief allows no tier of the judge, and no
  dispatch is due before a build.
- **Re-ran** (no guest run):
  - EXECUTED, `awk` over `price.txt`: 42 families; whole suites 66,722 G; the smoke column
    879.5 G, its largest 60.3 G (pyyaml); the twenty whole-as-smoke families 383.0 G; the other 22
    families' whole suites 66,339 G, of which their smoke groups are 496.5 G, so their release
    groups proper are 65,842.5 G; sympy 52,205.3 G. The memo's sympy areas summed by hand: 28.36 T
    measured + 15 T capped + 3.45 T doctests + 2.79 T doc files + 2.61 T (`test_issue_17141_slow`,
    the pre-build review's measure) = 52.21 T, equal.
  - EXECUTED, the pinned `downloads/sympy-1.14.0-py3-none-any.whl` unzipped into the scratchpad and
    grepped: `sys._running_pytest` is read only by `sympy/testing/pytest.py` (line 24, `USE_PYTEST`)
    and set only by `sympy/conftest.py` (line 3, its first statement after `import sys`); under
    `USE_PYTEST`, `XFAIL = pytest.mark.xfail`, `slow = pytest.mark.slow`, `tooslow =
    pytest.mark.tooslow` (lines 39 to 45). The conftest also loads its own hypothesis profile
    (`sympy_hypothesis_profile`, `deadline=None`, lines 12 to 16) and has no `pytest_configure`.
  - EXECUTED, the pinned `downloads/pypdf-6.21.1-py3-none-any.whl`: no module of the shipped
    `pypdf/` imports `ssl`. `gh api repos/py-pdf/pypdf/contents/tests/__init__.py` (main and
    `ref=6.21.1`): both import `ssl` at line 5 and use it only at lines 46 to 48, so upstream has
    not fixed it.
  - READ as data in the survey's stage (`agent-a03cd627…/build/067/survey/stage/`):
    cloudpickle's `tests/cloudpickle_test.py` (139 `def test_`) fails only through
    `from .testutils import …`, and `tests/testutils.py` imports `psutil` at line 13 and uses it
    once, at line 166; formulaic's `tests/materializers/test_base.py` (8 tests) uses `pyarrow` once,
    at line 51; jinja2's `test_async.py` (60) and `test_async_filters.py` (25) import `trio` only to
    parametrize a fixture over `[_asyncio_run, trio.run]`; sympy's capped areas hold
    `solvers/ode` 144, the rest of `solvers` 441, `stats` 225 and `calculus` 47 test functions.
  - READ, 102's `tiers.py` at `492b4586`: `KINDS = ("marker", "keyword", "path")`, `SMOKE_BUDGET
    = 500 * 10**9`, and `TEST_FILE = (?:.*/)?(?:test_[^/]*|[^/]*_test)\.py`, the only files
    `smoke_errors` partitions.

## The questions the brief asks, answered

1. **The owner's tier rule: followed, nothing dropped, with two exceptions to fix.** Each of the
   42 suites runs whole in the release tier (a release-tier run runs both tiers, 102's
   `--tier release`), each package has one normal smoke group, and every collected test is in
   exactly one tier (Decision 10, criterion 2's unit row). The twenty whole-as-smoke families are a
   placement the lane may make under the rule (`decisions.md`: "the lane decides tier placement by
   this rule"): a session start costs about 10 G, so a smaller smoke group would save almost
   nothing; they still run before every publication. **pyyaml stays whole** (60.3 G, under 067's
   100 G and 102's 500 G): a keyword split is what 102's smoke kind refuses (`[[release_select]]`
   in a smoke family), and the rule settles thresholds. The exceptions: the branch dispatch with
   `release-tier: true` contradicts the rule as recorded (H1); and three new "not selected" rows
   leave out tests that can run (M1). **The prices agree with the survey's data** (Re-ran, above):
   879 G, each smoke group under 61 G, sympy at least 52.2 T. One wording fix: the 66.3 T is the 22
   families' whole suites with their 496.5 G of smoke files; their release groups are 65.8 T (L1).
   The shard count and the lane's added time are lower bounds like the fuel (L1).
2. **The path release kind: not what 102 built, and owned by the wrong party** (H2). 102 owns it:
   it is built on 102's branch (Decision 2(d), `tiers.py`, ten unit rows), at 095's request. 067's
   text, "whichever of 067 and 095 is built first adds it to `tests/harness/tiers.py`", would build
   it a second time, with different rules ("disjoint paths" against 102's `--ignore` of smoke paths
   under a folder; "exactly one normal group" against 095's two smoke groups for scipy). And 102's
   kind does not yet hold what 067 needs: doctest, doc-file and `module_functions` groups, upstream
   `python_files` patterns other than `test_*`/`*_test`, and node-id groups carved out of a path
   group. **Who owns what:** 102 owns the kind; 067 owns a named widening of it, built in 067's
   branch on 102's tip; 095 builds nothing of it.
3. **The sympy finding and its answer: sound, not a weakening, with three conditions** (M3). It
   is upstream's own first statement (`sympy/conftest.py:3`), and only sympy's test helpers read
   it. So setting it before the driver's `package_paths` import makes the session upstream's, and
   the XFAILs become what upstream calls them. Rule 4 forbids editing a check, a golden output or
   an allowance to turn a run green. This edits none of them. It corrects the stage, and the
   xfailed and xpassed counts stay in the record.
4. **pypdf: (a), a recorded test-source patch.** §4.1 allows exactly this. It is the right choice.
   Reasons and conditions are under M2. The same reasoning applies to the files of M1.
5. **The criteria and the order.** After H1 to M3 are written in, the criteria are complete and
   testable (the rows to add are in each fix). The order is right: after 102 lands, or stacked on
   102's reviewed tip. 102 is built (`492b4586`) but not build-reviewed, so today 067 waits for
   102's build review. The widening of H2 goes in 067's branch, never into 102's, so that 102's
   wave is not reopened.

## Acceptance criteria against evidence

1. The pins — unchanged by the delta; testable as written. M2 (and M1) add patch files beside the
   pins, which criterion 9 must count.
2. The rules — testable. Several rows are now 102's, already built (a path group over a smoke
   file, a staged file in no tier). 067 must state its widening's rows instead (H2), and scope its
   own budgets to its own families (L2).
3. The tie — testable. It must also cover a patched test source (M2).
4. The items — testable.
5. The survey — met: the memo is EXECUTED on `d0d91cef` and its delta has this verdict (READ).
6. The groups — testable. sympy's lists must be written after the flag (M3).
7. Fuel repeats — testable. It is also where the release-tier claim block comes from, once H1 is
   fixed.
8. Nothing else moves — testable.
9. The artifact set — **not met as written** if M2 is taken: `MANIFEST` also gains one `recipe`
   line per carried test-source patch (READ: the build's `MANIFEST` records each patch as a
   `recipe` line).
10. `packages.toml` — testable.
11. The shards and the fetch — testable.
12. The full judge — testable.
13. The dry runs — **contradicts the owner's rule** (H1).

## Findings, most severe first

1. **H1 — A branch run with `release-tier: true` contradicts the owner's standing rule**
   (`067-…md:676`, criterion 13; also lines 421 (Decision 10), 516 (Decision 11), 772 and 785
   ("For the lane"), and the Intent's "a branch run that asks for it").
   The defect: `decisions.md` (2026-10-21) says "No branch run runs release groups." 095 applied
   that rule (its Decision 7 and criterion 12: "No dispatch with `release-tier` true"). 102's ledger
   was widened for it: a block may come "from its builder's local `--tier release` runs by node id,
   when no branch run runs release groups". 067 still requires the dispatch, and writes its claim
   block from it.
   Failure: built as written, 067's builder dispatches about 95 to 110 release shards on a branch,
   which the owner's rule forbids.
   **Fix:** strike that dispatch in all five places. Write instead, as 095 does: "No dispatch with
   `release-tier` true. Each release group is measured once locally by node id with `--tier
   release` (criterion 7), the builder pausing while `build/lane.lock` exists. 067's `[[claim]]`
   block in `context/release-tier-claims.toml`, and the release tier's measured total, come from
   those runs (102, Decision 6 as widened). The first CI run of the release shards is the dry run
   on main before 0.1.0's tag." Criterion 13 keeps the branch's normal dry run. Add one line for
   the lane: "the pre-tag dry run is the first time 067's release shards run on Linux. A shard past
   360 s there is re-packed from the darwin fuel before the tag."

2. **H2 — The path release kind exists in 102, with rules 067 contradicts and gaps 067 needs
   filled** (`067-…md` Decision 10, the bullet "A new kind for 102"; Decision 13; Design's
   `tiers.py` line; "Depends on", 102 bullet; "For the lane", Order).
   The defect: 067 says "whichever of 067 and 095 is built first adds it to
   `tests/harness/tiers.py`". 102 has already built it (Decision 2(d), `tiers.py` at `492b4586`):
   the `smoke` key, `release_by = "path"`, `--ignore` for each smoke path under a path group's
   folder, `SMOKE_BUDGET` 500 G per family, and the partition over `TEST_FILE` only. 067's own
   wording differs: "disjoint paths", and a 1 T total across families. And 102's kind cannot hold
   five things 067's families have:
   - (a) **doctest groups** (`docstring_modules`, `docstring_packages`): sympy 3.45 T, mpmath
     2.05 T, networkx 0.11 T, fonttools, joblib, tabulate, more-itertools;
   - (b) **doc-file groups**: sympy's 103 files (2.79 T), joblib's `doc/*.rst`;
   - (c) **patsy's `module_functions`** (43.5 G). These are no path group's paths, so under 102's
     Decision 3 their release groups are "of no named kind" and refused;
   - (d) **test files outside `TEST_FILE`**: tqdm's `tests/tests_*.py` and dateutil's
     `docs/exercises/solutions/*_solution.py`, which upstream's `python_files` selects. 102's
     "in no tier" rule cannot see them. A smoke group over `tests/` in tqdm fails "holds no staged
     test file";
   - (e) **node-id groups** (`sympy-slow-17141`, and any sympy test the build finds past 480 G).
     They sit inside a path group's file, and nothing says that path group `--deselect`s them, so
     the test would run twice.
   Failure: built as written, 067 adds a second path kind or edits 102's, and 095, built on 102,
   then breaks. Or 067 builds on 102's kind as it stands, and its doctest, doc-file and
   module-function release groups are refused, as are tqdm's and dateutil's smoke groups.
   **Fix:** replace the bullet with a section "For 102's path kind: 067's widening". It says, in
   102's terms:
   - 102 owns `release_by = "path"` and its rules as built. 067 uses them unchanged: `smoke` on
     each normal group, `--ignore` of smoke paths under a folder, 500 G per family, no
     `[[release_select]]`.
   - 067 widens three things, in its own branch on 102's tip, reviewed with 067:
     - (i) a smoke family's staged-test pattern is its upstream `python_files`, read from the
       `.ini`, where it differs from `TEST_FILE`;
     - (ii) a release group of a smoke family may be an item group: `docstring_modules`,
       `docstring_packages`, `doctest_files` or `module_functions`. Its unit is the module or the
       file, and the "exactly one tier" rule covers those units as it covers test files: each
       shipped module of a `docstring_packages` entry, less `docstring_not_selected`, is in exactly
       one group;
     - (iii) a node-id group's ids lie in exactly one path group's paths, and that group
       `--deselect`s exactly them.
   - Each of the three gets a unit row seen failing first, on 102's synthetic smoke family. Add the
     rows to criterion 2. Delete the rows 102 already has.
   - Delete "whichever of 067 and 095 is built first adds it" from Decision 10 and "For the lane".
     095 needs none of (i) to (iii): its three suites use `test_*.py`, and its modes and doctests
     stay unrun for 0.1.0.
   - Say whether the twenty whole-as-smoke families carry `smoke`. I recommend they do, with the
     reason "the whole suite: smaller would cost as much", so that the record names every normal
     group of a package as its smoke.

3. **M1 — Three new "not selected" rows leave out tests that can run, against pypdf's own
   ruling** (`067-…md:378`, Decision 8's cloudpickle, formulaic and jinja2 rows; the delta's item
   7).
   The defect: Decision 8 says a file is not selected only when it cannot load, or when every test
   in it needs what the product lacks. Each of these three files cannot load only because of one
   module-level import, used by a few of its tests. That is the shape of pypdf's `import ssl`:
   - cloudpickle: the import is in `tests/testutils.py:13`, not in `cloudpickle_test.py` as the
     row says. It is used once, at line 166, and it blocks the 139 tests of "most of cloudpickle's
     suite";
   - formulaic: `pyarrow` is used by one of the file's eight tests;
   - jinja2: `trio` is only one of two fixture parameters, and the asyncio half (85 test
     functions) runs in the guest, as tqdm's `tests_asyncio.py` shows.
   Failure: the owner's "every test, never left out for convenience" is not met for about 230
   tests, while pypdf's 1,689 are recovered by the same remedy.
   **Fix:** write the rule into Decision 8: "a file that cannot load only because of a
   module-level import that some of its tests use gets a recorded test-source patch (M2's form),
   making that import lazy or optional. The tests that need the module are then a class (or `D`
   lines with that reason). A file is not selected only when every test in it needs what the
   product lacks." Apply it to these three. Correct cloudpickle's reason to `testutils.py`. Have
   the build read each of narwhals' 13 pyarrow and polars modules against the same rule. To close:
   each patch and its count of tests recovered, in the landing notes.

4. **M2 — pypdf: (a), a recorded test-source patch. The spec text does not yet carry it**
   (`067-…md` delta item 5; Kind; Decision 4 "Only networkx carries a patch"; Design; criterion 9).
   - **The decision, and why.** §4.1 governs any change to a pinned tarball's bytes. A test source
     pinned in `downloads/SHA256SUMS` is such a tarball, and networkx's carried patch already changes a
     test file (`test_atlas.py`). A patch is "unavoidable" here: the product has no `_ssl`, and
     every pypdf module imports `tests`.
   - **The alternatives are worse:**
     - a stand-in `ssl` module (§4.1's "recipe file first") would be on the product's path during
       the session. `http.client` and `urllib.request` would then see an `ssl` the product lacks,
       so pypdf would be tested in an environment that is not the product's;
     - a recorded allowance or a deselection cannot help, because nothing collects;
     - (b), leaving the suite `later`, loses 1,689 passing tests to a one-line import.
   - **Its effect.** The patch touches no byte the zip ships (no `pypdf/` module imports `ssl`;
     EXECUTED). So the wheel tie is unchanged. Upstream's main still has the import, so the pull
     request is worth drafting.
   - **The guarantee to evidence.** §4.1's "the release fails on any difference from the pinned
     tarball other than exactly the recorded patches" must reach a test source, which no build step
     unpacks.
   **Fix, all written in:**
   - The patch: `recipes/patches/pypdf-6.21.1/0001-tests-import-ssl-where-it-is-used.patch`. The
     folder is the sdist's top, which `scan.patch_errors` requires to be a pinned tarball's
     top; the build confirms 067's pins are in that set.
   - Its draft under `context/upstream/patches/pypdf-6.21.1/`, its CHANGELOG line, and the README's
     "upstream patches carried" count, plus one.
   - The judge unpacks pypdf's test source and applies the patch with
     `scripts/steps/apply_patches.sh`, the same applier the build uses. `pins.tree_drift` and
     `tie_errors` (with `repo_patches`) check the staged tree.
   - Kind: "`recipes/patches/` gains one test-source patch (and M1's)". Decision 4: "networkx and
     pypdf carry patches; pypdf's touches only `tests/`". Criterion 9: "`MANIFEST` differs in
     exactly 39 `pin` lines, the `recipe` line of `scripts/00_download.sh`, and one `recipe` line
     per carried test-source patch".
   - Criterion 3 gains a row: a pypdf stage with the patch unapplied, or applied at an offset,
     fails the tie and names the file.

5. **M3 — The sympy flag: right, but undeclared, and its consequences unnamed** (`067-…md` delta
   item 4, the sympy bullet; Decision 5's "only once `sys._running_pytest` is set").
   - **Why it is sound.** The answer mirrors `sympy/conftest.py:3`, which under upstream's pytest
     runs before any sympy import. Only `sympy/testing/pytest.py` reads the flag (EXECUTED). So it
     changes sympy's test helpers and no product path. It is not a weakening: no check, golden
     output or allowance changes, and XFAIL becomes upstream's `pytest.mark.xfail`. Of the
     delta's two options, "import nothing of sympy before the session" is not available: the
     driver's `package_paths` imports the package (`package_drive.py:37-38`). So the flag is the
     answer.
   - **What it leaves open:**
     - a hard-coded sympy branch in the shared driver;
     - two consequences that turn sympy's groups red at build. First, once the flag is set, sympy's
       `@slow` is the mark `slow`, which sympy's `pyproject.toml` does not register (`markers =
       ['nocache_fail', 'tooslow']`, `configs.txt`), so the driver's `--strict-markers` refuses
       every module that uses it. Second, sympy's conftest loads `sympy_hypothesis_profile` after
       the driver's `judge` profile, and `upstream.py` refuses a stream whose `P` line is not
       derandomized with no database;
     - upstream sets no `xfail_strict`, so an XFAIL that passes here is an xpass. It is visible
       only if the record counts it.
   **Fix:**
   - The flag is a family key in `sympy.toml` (for example `sys_flags = ["_running_pytest"]`) with
     its reason. A rules row allows only that name, and a unit row covers it. No package name goes
     in the driver.
   - sympy's `.ini` registers `slow`.
   - The driver loads `judge` again after the conftests load (before it writes the `P` line), and
     the README states it. Its only cost against upstream's profile is determinism.
   - Each sympy group's `counts` carries xfailed and xpassed. Its lists and gaps are written from
     runs with the flag, never from the survey's.
   - Add these to the delta's item 4 and to criterion 4 (a fixed stream: a sympy XFAIL reported
     xfailed, and a `P` line that stays derandomized).
   - The build greps every other conftest it stages for `load_profile` and treats it the same way.

6. **L1 — The release figures: one label, and the bound carried through** (the price; Decision
   11; delta item 1).
   - The 66.3 T is "the 22 families' whole suites", and includes their smoke files. Write "release
     groups at least 65.8 T; a release-tier run, both tiers, at least 66.7 T".
   - Four sympy sessions stopped at their caps after 70 of 144, 244 of 441, 144 of 225 and 30 of
     47 test functions. Extrapolated by count (INFERRED, mine), they hold about 26 T, not 15 T. So
     sympy may be about 63 T, the release tier about 77 T, the release shards about 110 to 125,
     and the lane's release acceptance about 3 to 3.6 hours of guest time.
   - Write "at least" on the shard count and on the lane's added time too, and name that range as
     the INFERRED upper estimate, so the lane books its slot from it.

7. **L2 — 067's own budgets are scoped to 067's families** (Decision 13; criterion 2).
   - "Smoke groups past 1 T together" would also count 095's 770.6 G (1.65 T in all) if it read
     every family. "Exactly one normal group" would refuse scipy's two smoke groups.
   - Write: "among the 42 families of this specification, in `packages.py`". The thresholds
     themselves stand; this is not reopening them.

8. **L3 — Stale facts about 102** ("Depends on", the 102 bullet: "tip `8fb3df7` … not yet landed
   or build-reviewed").
   - 102's tip is `492b4586`: its smoke kind and workflow half are built, and its branch runs and
     baseline are read; its build review is not done yet.
   - Update the bullet, and say that 067 waits for that build review (or for 102's landing).

9. **L4 — The smoke rule's run half needs its row** (Decision 13, "its run deselecting or
   skipping a test for an opt-in is red"; criterion 2).
   - Criterion 2 checks a smoke group's marker expression, but not that runtime half.
   - Add a unit row on a fixed stream: a smoke group whose stream holds a skip with the family's
     opt-in reason (networkx's "need --runslow option to run") is red.

## Notes for the lane

- **102's own text predates the rule in two places.** Decision 1's table row "a dispatch on any
  other branch … release when the dispatch input `release-tier` is true", with "Why a branch may
  ask for it … (this one, 067, 095)". And Decision 15's "067 … its families `release_marker`; its
  complement rule is Decision 2's truth table". Both are 102's to reword (context only) in its
  build review. Whether 102's own input stays for 102's machinery is the lane's call. No
  specification after 102 uses it.
- **The family `env` key** (reportlab's `RL_TEST_OUTDIR`) is 095's Decision 7 shape: a
  per-family list of allowed names. 095 is ordered before 067, so 067 adds a name to 095's list.
  That is a rebase, not a second key.

## Constitution checks

- §4.1: held by M2 and M1 once written in. A test-source patch is a recorded patch with its draft,
  hash and CHANGELOG line. No byte that ships changes.
- §4.2: unchanged; the 39 pins as reviewed before build.
- §4.6: the artifact set's bytes are unchanged. `MANIFEST` gains pin and recipe lines (criterion 9,
  corrected).
- §4.8: the archives were read as data (the survey's `tarfile` data filter). This review unzipped
  two pinned wheels into its scratchpad and only grepped them.
- §5.6: this is the delta's confirmation round. The pre-build review is done.
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

The builder's answers are spec 067's section "Disposition of the delta review (2026-10-21)", at
`ecbc5878`, on a branch rebased onto main `1875d4cd` with this review cherry-picked as `18a428b4`.

**Confirmation (2026-10-21, the same reviewer; 20-minute box, about 15 used; context only).**
- **Read:** `git diff 18a428b4 ecbc5878`, which touches the spec, the memo, and a new
  `context/upstream/patches/pypdf-6.21.1/0001-tests-import-ssl-where-it-is-used.md`; 102's
  `tiers.py` at `492b4586`; `tests/harness/scan.py`'s draft rules.
- **Run, EXECUTED:** `uv run pytest
  "tests/checks/test_rules.py::test_carried_patches_follow_the_rules"`, with `build/lane.lock`
  absent. It **failed**, 1 failed, losing an accepted pass. The finding: "a draft with no patch".

**What is answered:**
- **H1: confirmed.** There is no dispatch with `release-tier` true anywhere: not in the Intent,
  Decisions 10 and 11, criterion 13, or "For the lane". Criterion 7 measures each release group
  locally by node id, pausing on the lane lock, and writes the claim block and the release total
  from those runs. The first CI run of the release shards is the pre-tag dry run on main, with
  re-packing from the darwin fuel. That is 095's form and 102's widened ledger.
- **H2: confirmed.** The new section uses 102's kind as built: `smoke`, the `--ignore` of smoke
  paths, 500 G a family, and no `[[release_select]]`. It widens exactly the three points (i) to
  (iii), in 067's branch on 102's reviewed tip. "Whichever first" is gone, and 102's rows are not
  repeated. I checked it against `tiers.py`:
  - (i) replaces `TEST_FILE` with the `.ini`'s `python_files` in `smoke_errors`' staged set;
  - (ii) adds item units beside test files in the same exactly-one-tier loop, and lets
    `kind_of` name an item group;
  - (iii) is a new rule beside them.

  All three are expressible without changing a row 102 tests. Each has a unit row in criterion 2.
  The twenty whole-as-smoke families carry `smoke`.
- **M1: confirmed.** Decision 8's rule is written. It is applied to cloudpickle (now
  `testutils.py:13`), formulaic and jinja2's asyncio half, and narwhals and pyparsing are to be
  read against it. Criterion 9 counts the patches.
- **M2: confirmed in the spec text.** The Kind, Decision 4, the Design, the applier, `tree_drift`
  and `tie_errors`, the `recipe` line (criterion 9), the tie row (criterion 3), the CHANGELOG and
  the README count are all there. **The facts sheet is the right form.** pypdf's `CONTRIBUTING.md`,
  as the draft quotes it, asks that comments and issues be written by humans.
  `recipes/patches/README.md` already provides for this case ("the draft's body is the facts for
  the owner to write from", numpy's precedent). The draft says no agent posts anything, and it
  keeps §4.1's six header lines.
- **M3: confirmed.** The answer has the `sys_flags` key with its allowed list, sympy's `slow`
  registered, `judge` loaded again after the conftests, and `xfailed` and `xpassed` in `counts`,
  with lists written from flagged runs. Criterion 4 has rows for the flag, the XFAIL and the `P`
  line.
- **L1: confirmed.**
  - **The 3 to 3.6 hours are right.** The upper estimate of 77 T at 0.14 to 0.17 s per G is
    10,780 to 13,090 s, which is 3.0 to 3.6 hours of guest time, or 1.0 to 1.2 hours of wall
    clock at `-n 3`. The lower bound of 66.3 T gives 2.6 to 3.1 hours.
  - The caps check out: 65.8 T times 1.5 is about 99 T, and 77 T times 1.5 is about 115 T.
  - So do the shards: 77 T over 725 G is at least 106, so 110 to 125 is right.
  - Every figure is labelled INFERRED or "at least".
- **L2, L3 and L4: confirmed**, each with its text: the bounds are scoped to the 42 families,
  102's tip is `492b4586` and its build review is awaited, and the opt-in-skip verdict row is in.

**Still open:**
1. **Medium, new: the branch turns a rules check red.**
   `context/upstream/patches/pypdf-6.21.1/0001-tests-import-ssl-where-it-is-used.md` is a draft
   whose patch the build will write. `scan.patch_errors` refuses a draft with no patch (EXECUTED
   above). Its Status line, `drafted (2026-10-21, …)`, would also fail `STATUS.fullmatch` once the
   patch exists, because the rule takes exactly `drafted`, `sent <url>`, `merged <url>` or
   `released <version>`.
   **Fix:** move the facts sheet out of `context/upstream/patches/` until the build. For example,
   put it beside the survey memo, as
   `context/research/2026-10-21-the-pure-python-packages-own-tests-under-the-runtime/pypdf-ssl-facts.md`.
   The build then commits it at its rules path together with its patch, in one commit. Make its
   Status line exactly `- **Status:** drafted`, and move the date and the note into the body.
   **The evidence that closes it:** the node id above passing on the branch.
2. **Low: one sentence for patsy.** patsy's `python_files = *.py` makes (i) treat the library
   modules under `patsy/` in the tarball as staged test files, while (ii) names the same modules as
   `module_functions` units. Write: "for patsy, a member `patsy/<m>.py` that is a
   `module_functions` module counts as that group's unit, and the path partition sees only the
   staged `patsy/test_*.py`." Then the two rules cannot each claim, or each miss, the same file.
3. **Low: the patch count.** Criterion 9 and the Kind say "four" test-source patches. The narwhals
   and pyparsing reads may add more. Write "four, plus any the build's reads under Decision 8's
   rule add, each named".

**Confirmation verdict:** fit to build once open item 1 is answered and the rules check passes.
Items 2 and 3 are Lows that need only their text. H1, H2 and M1 to M3 are confirmed answered and
testable.

## Verdict

Fit once the named findings are answered. **H1** (no branch run with `release-tier: true`) and
**H2** (102 owns the path kind; 067 writes its widening in 102's terms) must be written in before
any build. **M1 to M3** must be written in with the evidence named. The Lows need only their text.
No owner question remains. The build follows 102's build review (or its landing), on 102's
reviewed tip.

One line: the survey's numbers hold and the owner's rule is followed, but 067 must drop its branch
release run, build on 102's path kind instead of a second one, and carry pypdf's (and three more)
test-import fixes as recorded patches.
