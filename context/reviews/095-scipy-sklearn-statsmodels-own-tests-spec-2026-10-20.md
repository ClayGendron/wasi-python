# Review of 095 — scipy's, scikit-learn's and statsmodels' own tests in the release (the specification, before build)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I wrote none of 095 and reviewed
  none of it. I read `AGENTS.md`; the constitution §4, §5.2, §5.6, §5.7 and §7;
  `context/reviews/README.md`; `context/decisions.md` (2026-10-20: "Every test of every package we
  build", statsmodels' suite to 095, two tiers of tests, spec 102's four questions); the draft and
  its drafting folder; spec 066 and its pre-build review; spec 102 at `2cccc23`
  (`spec/102-the-release-tier`, Decisions 2 to 6, 10 and 15); spec 045's status at `7be1837`;
  `tests/upstream/package_drive.py`, `tests/harness/packages.py` (`Session`),
  `tests/harness/upstream.py` (`judge_group`), `tests/harness/guest.py` (the clock and random
  stream), `tests/upstream/packages.toml`, and, on the chain's tip `dbecd2d`,
  `tests/checks/test_rules.py`'s citation rule and `tests/harness/scan.py`'s reader of it. I read
  the three pinned sdists as data (`tarfile`, `uv run --no-project python -I`, nothing unpacked or
  imported): `downloads/scipy-1.18.1.tar.gz`, `downloads/scikit_learn-1.9.1.tar.gz` and 045's
  `statsmodels-0.15.0.tar.gz`, and pytest 9.0.3 from the kit's wheel. Time box: 60 minutes (a
  build-class specification; the lane's box).
- **Reviewed:** `spec/095-scipy-sklearn-statsmodels-own-tests` at `8978797`, drafted from main
  `dda6075`. The diff touches only `context/` (12 files, 2,252 insertions; READ).
- **Run:** none. This is a pre-build review of a context-only diff. The brief allowed no build and
  no full judge, so I dispatched no release workflow. No outcome or fuel below is mine EXECUTED
  unless it says so.
- **Re-ran:** in the worktree, `uv run pytest tests/checks/test_rules.py::test_every_package_names_its_own_suite
  tests/checks/test_v1_3_upstream_suites.py::test_upstream_files_are_well_formed -q -p no:cacheprovider`,
  with `build/lane.lock` absent → 2 passed, exit 0 (`build/095-review/node.txt`). Also EXECUTED:
  none of the three tarballs has a symlink, a hard link, two names that differ only by case, or a
  non-ASCII name (5,076, 1,550 and 2,275 members). That matters on darwin's case-insensitive disk.
  No guest probe was run.

## The owner's four questions: my recommendation on each

1. **Widen 088 to scipy's seven test-only C modules: yes.** They are the same kind of thing as
   numpy's and CPython's test modules: built with the `tests` tag, linked only into a judge-only
   binary that is never published. 088 is reserved "after the packages", so in 0.1.0 the five
   files and `test_deprecation.py`'s two calls stay not selected, each named with its closer. The
   widened line should name the seven modules and the five files.
2. **Leave the upstream modes README-only: yes, for 0.1.0, with three corrections** (L7):
   - `SM_TEST_COPY_ON_WRITE` does nothing on pandas 3, so it is not a mode here.
   - `SCIPY_XFAIL` is a mode the list leaves out.
   - "No new mechanism" is wrong for the release tier. Under 102, a group that runs the same tests
     again under another variable is not one of the named kinds, so 102 refuses it.

   The survey should also count the tests that skip only because a mode's variable is unset
   (scikit-learn's "SCIPY_ARRAY_API not set": 47 in the seven-file sample). Then the README states
   a number. A mode in the release tier would be a follow-up after 0.1.0, with a 102 change.
3. **The price: decide it now, by a rule, instead of asking after the survey** (§5.2 allows no
   open question). Keep scipy's and statsmodels' normal tiers as drafted. Write one threshold into
   Decision 7: if the survey measures more than about 15 T for the three normal tiers together
   (about 2.3 times today's 11.2 T), scikit-learn's tests move to the release tier, by 102's kind
   (b) keyword entries, until the total is under it. The order is: first `tests/test_common.py`
   (the estimator checks, 13,387 tests), then the float32 cases. Nothing is left out. This follows
   the owner's own reading ("for normal checks, we don't run the slow tests"; "we can decide what
   is slow tier"). It also bounds the lane's darwin accept at every landing. The draft's
   estimate is 15 to 35 more minutes per landing, and scikit-learn is the least certain part.
4. **statsmodels' 13 left-out datasets as a README class: yes.** The suite judges the product as
   shipped. Staging the CSVs would not reach the tests anyway, because 045's patch makes the loader
   read package resources from the zip. It would also judge data the product does not carry. Two
   corrections (L3): a file that fails at import cannot be a class member, so it is a Decision 8
   row. And the class's closer is the owner's answer to question 83: approving a dataset ships it
   and empties the class.

## Acceptance criteria against evidence

The draft is not built, so I checked each criterion for whether it can be checked, not whether it
is met.

1. The rules — checkable. But the driver-hash variant proves only that staging copies a file
   (L5), and the `env` variants need a closed list in code (L6). READ.
2. The derived run on a synthetic tarball — checkable. But "writes nothing" misses makenpz's real
   failure: with an empty input folder it writes an empty `.npz` and exits 0 (M1). READ.
3. The survey, then the baseline — checkable, and the same form as 066's (memo, delta,
   confirmation). READ.
4. Complete TOMLs give each check its stated status — checkable. READ.
5. Fuel repeats — checkable. The guest's clock and random stream come from the embedder
   (`guest.py:9-11`, `random_get`, `clock_time_get`), so even the `.npz` bytes (zip timestamps from
   the guest clock) repeat. READ, INFERRED for the bytes.
6. Nothing else moves — the ratchet part is checkable. "066's stage-manifest unit check" does not
   exist (L5). READ: `tests/unit/test_packages.py` has no such test.
7. The shards — checkable under 063's and 102's rules. READ.
8. The fetch — checkable. READ.
9. The tie and the stage — checkable. It is the right check for `package_inits` (L1). READ.
10. `packages.toml` — checkable. It passes today, with scipy and scikit-learn `later`. EXECUTED.
11. Fast tier and lint — checkable. It must include the citation rule's allowance edit (L4). READ.
12. and 13. The dry runs — not checks, but stated as 063's are. READ.

## Findings, most severe first

1. **H1. `SCIPY_XSLOW` changes more than the `xslow` skip, so the tier split is wrong under both
   readings of the draft** (Decision 7, "The variable changes only `xslow` tests' skip … normal
   rows are the same with it or without it"; Design step 3).
   - **What the variable does.** scipy's tests read it directly, outside the conftest and outside
     any marker (READ, the pinned sdist):
     - `stats/tests/test_axis_nan_policy.py:26,390` defines a block of tests only when it is set.
       Its comment says this is ">3,000 tests", kept out of pytest's sight otherwise.
     - `stats/tests/test_axis_nan_policy.py:384,907` skips the `kruskal` and `friedmanchisquare`
       cases without it.
     - `stats/tests/test_continuous.py:1142` skips sixteen distributions in `test_rv_generic`
       without it.
     - `integrate/tests/test_tanhsinh.py:265` skips two cases of `test_accuracy` without it.
     - `special/_mptestutils.py:193` uses 5,000 points in place of 500 for every mpmath
       comparison when it is set.
     - `stats/tests/test_fit.py:113` gates the very slow fits inside a `slow`-marked test.
   - **Failure, reading (a), the variable family-wide** (Design step 3, `env=ENV | family env`).
     Every normal group runs with `SCIPY_XSLOW=1`. The normal tier collects the 3,000-odd hidden
     tests and runs the skipped cases. Every mpmath comparison runs ten times the points. So the
     normal tier is not what upstream's default runs, which is the rule Decision 7 states. And the
     drafting counts (80,926 normal, 15,174 release), collected without the variable, are not this
     design's counts.
   - **Failure, reading (b), the variable on release groups only** ("A release group may carry the
     variable its tier needs"). The cases gated inside unmarked tests skip in the normal tier. The
     release tier's `-m "slow or xslow"` does not select them. So they run in neither tier, which
     breaks the owner's rule. No check sees it: 102's truth table reads only the markers, and a
     skip is a counted outcome.
   - **Fix text** for Decision 7, and a rule for Decision 14:
     - "`env` is a family key only. Every group of the family, in both tiers, runs with the same
       variables, and a group may not set its own. scipy's `SCIPY_XSLOW=1` is set for every scipy
       group."
     - "The cases that upstream runs only with `SCIPY_XSLOW`, inside tests that carry no
       `slow`/`xslow` marker, go to the release tier by 102's kind (b) `[[release_select]]`
       entries. One entry per file: `test_axis_nan_policy.py` (the functions defined under
       `if SCIPY_XSLOW:`, and the `kruskal` and `friedmanchisquare` cases), `test_continuous.py`
       (`test_rv_generic`'s sixteen distributions), `test_tanhsinh.py` (`studentized_range` and
       `levy_stable` in `test_accuracy`). Each has the reason 'upstream runs it only with
       SCIPY_XSLOW set'."
     - "The mpmath point count cannot be split by keyword. The normal tier runs scipy's mpmath
       comparisons at 5,000 points, and the README says so."
     - "The survey re-collects both tiers with the variable set. Its memo lists every direct read
       of each `env` variable in each sdist (a grep, READ), so the delta review sees what each
       variable changes."
     - Relabel the drafting counts "collected without `SCIPY_XSLOW`".

2. **M1. The derived run's row, cap, price and output handling are not stated** (Decision 5,
   Design step 2).
   - **Its fact has no fixed row.** "Facts of the family's first group" depends on which group
     first triggers `Session.prepare`. The stage is made once per session (`packages.py:376-436`),
     so once per xdist worker on darwin (`-n 3`) and once per Linux shard. The first group differs
     between workers, shards and runs, so the `derived` fact lands on different rows.
   - **It has no cap and no price.** The run parses 122 text tables, about 15.9 MB, with
     `np.loadtxt` (EXECUTED: boost 111 files and 14,188,680 bytes; gsl 3 and 400,255; local 8 and
     1,325,932). It runs in every stage that holds scipy: every scipy shard and every darwin
     worker. Its fuel is neither in the price nor in each shard's 360 s bound, and the draft gives
     it no fuel cap.
   - **"Writes nothing" is not makenpz's real failure.** makenpz finds its inputs from its own
     path (`makenpz.py:43-45`). With no input folder and no output, it calls `np.savez_compressed`
     with no arrays, so it writes an empty `.npz` and exits 0 (`makenpz.py:52-80`, READ). The
     inputs rule, "the inputs it reads are tarball members", cannot be checked as written.
   - **The host copies a file the guest wrote** into a stage that later guests read, and nothing
     says it refuses a link.
   - Failure: a darwin judge at `-n 3` records `derived` under `scipy-sparse-1` on one run and
     under `scipy-linalg-2` on the next. A Linux shard of four scipy groups spends tens of G more
     than its packing says, unmeasured. And a renamed input folder in the next scipy pin gives
     `test_data.py` an empty `boost.npz`: every case then fails as an unknown failure, not as a
     named derived failure.
   - **Fix text** for Decision 5:
     - "Each `derived` entry names its `inputs` folder. The rules check that it holds members."
     - "The run has a cap by the cap rule (`measured`, 1.5 times)."
     - "Its facts (each output's SHA-256 and its fuel) are recorded on the group that holds
       `special/tests/test_data.py`, named in the TOML, and on no other row."
     - "It runs in every stage that holds the family, whatever the tier or shard (102, Decision
       4). The survey measures its fuel, and the price and the shard packing count it once per
       scipy shard."
     - "An output that is missing, empty of arrays, not a regular file (read with `lstat`, never
       through a link), or larger than a stated bound fails every group of the family, named."

3. **L1. `package_inits` is safe because the driver imports each package first, not because of
   the "standard machinery"** (Decision 4; Decision 14's rule).
   - In pytest 9.0.3 (the kit's), importlib mode returns `sys.modules[name]` when it is there.
     Otherwise `_import_module_using_spec` runs the parent's `__init__.py` from the file it finds
     (`_pytest/pathlib.py:535-553`, READ). The product's packages win only because
     `package_drive.py:37-38` imports every `package_paths` key first.
   - So the rule "no generated entry names a package the product lacks" would quietly drop such
     an ancestor. pytest would then run the stage's copy of the sdist's `__init__.py`. The guard
     makes that red, but only after a whole run.
   - **Fix text:** "Every ancestor package of every staged folder is a package the product has,
     and is a generated `package_paths` entry. A staged folder under a package the product lacks
     is refused by the rules, never staged." Correct the paragraph's account of the mechanism to
     match.

4. **L2. Staged inits make pytest call `setup_module`.** With `sklearn/__init__.py` staged, pytest
   collects `sklearn/` as a `Package`. `Package.setup` calls the package's `setup_module`
   (`_pytest/python.py:676-685`, READ). scikit-learn's seeds `numpy.random` and `random` from
   `np.random.uniform()` unless `SKLEARN_SEED` is set (`sklearn/__init__.py:139-151`, READ). The
   seed repeats under the judge's random stream. But it depends on how many random bytes the
   product drew before the tests ran. So a product change elsewhere moves the global seed, and
   then the outcomes and fuel of every test on the global generator move with it.
   - **Fix text:** "scikit-learn's `env` sets `SKLEARN_SEED` to a fixed value, so the global seed
     does not depend on the product's earlier draws. The survey lists every `setup_module` and
     `teardown_module` in the staged ancestor inits of the three packages." scipy's inits define
     none (READ).

5. **L3. Decision 8 is incomplete.**
   - **statsmodels' "none known" is wrong.** `discrete/tests/test_constrained.py:29` loads `spector`
     at import, and `emplike/tests/test_anova.py:12` loads `star98` (READ). Both are left-out
     datasets, so both files fail to load and are not selected. Every test in them is lost, not
     only the dataset's (INFERRED until the survey).
   - **The draft does not count what is lost.** It gives no number of tests per not-selected file:
     `neighbors/tests/test_neighbors.py` alone holds 1,029 (EXECUTED by the drafting probe).
   - **Fix text:** "Decision 8 gains the two statsmodels files, with the dataset each loads. Their
     closer is `README.md` (045's list) and the owner's answer to question 83. Each not-selected
     file gives its collected count from the survey. The `left-out-datasets` class holds failures
     at run time only." The lane should consider naming scikit-learn's three `mmap` files in 074's
     roadmap line, so they have a numbered closer.

6. **L4. The chain's citation rule.** The draft must obey the chain's rule
   (`test_code_outside_src_names_no_context_document`, on `dbecd2d`). That rule reads every comment
   and docstring in the Python, TOML, shell and YAML files under `tests/` and `.github/workflows/`.
   - **Its edits retire allowance entries.** Rewriting `packages.toml`'s scipy and scikit-learn
     entries deletes the comments that `CONTEXT_CITATION_ALLOWED` names: `("tests/upstream/packages.toml",
     "spec 095")`, and probably `"Spec 044"`, `"044's"` and `"context/roadmap"`. The rule then
     fails with "allowed … is no longer there". The Changed list lacks `tests/checks/test_rules.py`.
   - **Fix text:** "`tests/checks/test_rules.py`: the allowance entries this change retires, in
     the same change (as 102 does)."
   - **What 095's code must obey:**
     - no comment or docstring in the new TOMLs, `packages.py`, `upstream.py`, `fetch.py`,
       `release_shards.toml`, the workflow's new shard lines or the unit files names a
       specification number, a section sign, a research or review document, a question number, a
       `context/` path or a finding identifier ("Decision 7", "M1", "spec 088" in a comment are
       all hits);
     - each `env` reason and each `not_selected` reason is written in words;
     - `closes_with` and `reason = "…"` values are data and keep their form;
     - the `.ini` files are not scanned, but should follow the same rule.

7. **L5. Two criteria cite or prove the wrong thing.**
   - Criterion 6 extends "066's stage-manifest unit check", which does not exist.
   - Criterion 1 and Decision 14's "staged `package_drive.py` hashes equal to
     `tests/upstream/package_drive.py`" holds by construction: `Session._prepare` copies that file.
     "The driver is not edited" is a fact of the diff, which the review reads.
   - **Fix text:** "Criterion 6: a new unit check, written first, compares each 066 family's
     staged file list and group JSON with the base's." Then either drop the hash rule, or say it
     guards only the copy.

8. **L6. `env` needs a closed list in code.** "The rules allow only listed names, each with its
   reason in the TOML" leaves unclear where the list lives. If the TOML carries its own
   allowance, the rule allows anything.
   - **Fix text:** "The allowed names are a constant in `packages.py`, per family. Today they are
     `SCIPY_XSLOW` for scipy, and `SKLEARN_RUN_FLOAT32_TESTS` and `SKLEARN_SEED` for
     scikit-learn. A name joins only by a judge change with its reason (as 102's `EXCLUDABLE`)."
     With H1: "never per group".
   - Name what stays forbidden: `TMPDIR`, `HOME`, `PYTHON*`, `SCIPY_HYPOTHESIS_PROFILE`,
     `SKLEARN_TESTS_GLOBAL_RANDOM_SEED`, `SKLEARN_SKIP_NETWORK_TESTS`.

9. **L7. The modes paragraph** (Decision 7).
   - `SM_TEST_COPY_ON_WRITE` applies only to pandas before 2.99.99 (`statsmodels/conftest.py:23-27`,
     READ). On the product's pandas 3.0.6 it does nothing.
   - `SCIPY_XFAIL` (`stats/tests/test_fit.py:112-118`) xfails the known-failing fits without
     running them. It is a mode the list omits.
   - "Each would be one more family or group with its `env`, no new mechanism" holds only for a
     separate normal-tier family. 102 refuses a release group that is none of its named kinds.
   - **Fix text:** say each of these, and count the mode-gated skips (owner's question 2 above).

10. **L8. 102's ledger and the price arithmetic.**
    - 102's Decision 6 asks a specification that adds release-tier groups to write its `[[claim]]`
      block in `context/release-tier-claims.toml`, from a branch run with `release-tier: true`.
      Neither "The claim list's shape" nor "For the lane" says so.
    - The release acceptance's added darwin cost is not stated: 4 to 12 T, about 4 to 12 minutes
      at `-n 3`, INFERRED.
    - 725 G at 0.16 to 0.31 s per G is 116 to 225 s of guest time, not "120 to 290".
    - **Fix text:** add the claim block to both sections, and correct the two figures.

11. **N1.** scipy's conftest loads its own `deterministic` hypothesis profile over the driver's
    (`scipy/conftest.py:561-574`). It has the same `derandomize=True, database=None`, so
    `_profile_ok` holds. That is why `SCIPY_HYPOTHESIS_PROFILE` belongs on L6's forbidden list.
12. **N2. Windows and macOS.** The normal tier runs on Linux in CI and on darwin at every landing.
    No system runs these suites on Windows, as with 066. That is acceptable: the guest's fuel and
    outcomes do not depend on the host, and the Windows own-guest shards cover the host's WASI file
    semantics. 095's Out line should give that reason in words, not only cite 066.
13. **N3.** Decision 7's headline ("what upstream's default runs is normal") is contradicted by
    scikit-learn's float32 choice and by H1's fix. Write it as "the rule, with these named
    choices", under the owner's "we can decide what is slow tier".
14. **N4. Order.** By default 095 is built after 045 and 102 land. That is right.
    - 045 is built natively, not yet judged, and its `python.wasm` grew past its own bound (045's
      Status), so the split path is the likely one.
    - Its rule is sound: a reserved closer, and statsmodels' sections unchanged.
    - The builder must rebase onto main after the chain 103 to 111 (`dbecd2d` or later) before
      writing code, because L4's rule exists only there.

## Constitution checks

- **§4.1:** no patch; the stage is made from the patched tree. Holds.
- **§4.2:** every new CI input is an existing pin. Holds.
- **§4.8:** makenpz runs only in the guest. Holds, once M1's copy rule is written.
- **§4.9:** no check reads a clock. Holds.
- **§4.10:** the labels are honest. The H1 counts need relabelling.
- **§4.12:** the 13 datasets stay out of the stage and the product. Holds.
- **§4.15:** `env` loosens no default. Holds, once L6's closed list is written.
- **§5.2:** H1 and the price threshold must be decided in the specification, not after.
- **§7:** nothing tripped. No upstream edit, no unpinned fetch, no number reported as run that was
  not run.
- **AGENTS.md rule 4 (never weaken the judge):** nothing in the draft edits a check, a golden
  file, an allowance or `known_gaps.toml` to turn a run green.
  - The scipy `.ini`'s one `ignore` line names pytest's own warning about the kit, not a scipy
    warning.
  - Registering `no_check_spmatrix` keeps `--strict-markers` in force.
  - Reading (b) of H1 would leave tests out of both tiers, which is why H1 is High.

## Disposition (filled in by the author, then confirmed by the reviewer)

By the author, 2026-10-20, on the branch rebased onto the chain's tip `727bd4c` (context only, no
conflict). Every finding is written into the specification; none is declined. The four owner
questions are written in as the reviewer recommended, each marked "default pending the owner's
answer" (the lane files them).

1. **H1 — fixed, as the fix text says.** Decision 7 is rewritten. `env` is a family key only:
   every scipy group, in both tiers, runs with `SCIPY_XSLOW=1`, and no group may carry `env`
   (Decision 14's rule; criterion 1's variant). The cases upstream runs only with the variable,
   inside tests with no `slow`/`xslow` marker, go to the release tier by three 102 kind (b)
   `[[release_select]]` entries, one per file (`test_axis_nan_policy.py`, `test_continuous.py`,
   `test_tanhsinh.py`), each with the reason "upstream runs it only with SCIPY_XSLOW set"; the
   survey writes the keywords from the collected ids and confirms each gated case is in exactly
   one tier. The mpmath point count runs at 5,000 points in the normal tier, stated in the README.
   The survey re-collects both tiers with the variable set and lists every direct read of each
   `env` variable in each sdist (Decision 1). The drafting counts are relabelled "collected
   without `SCIPY_XSLOW`" (the probe table and Decision 7). Decision 7's headline is now "the rule,
   with these named choices" (N3).
2. **M1 — fixed, as the fix text says.** Decision 5: each `derived` entry names its `inputs`
   folder (checked to hold members), carries `measured` and a `fuel` cap by the cap rule, and the
   family names one `derived_row` (the group holding `special/tests/test_data.py`), the only row
   its facts land on. The run happens in every stage that holds the family, whatever the tier or
   shard; Decision 12 and the price count it once per scipy shard and darwin worker. Each output is
   read with `lstat`, never through a link, and refused unless a regular file, at most 16 MiB, and
   a zip with at least one `.npy` member (makenpz's empty `.npz` is refused, named). Criterion 2
   gains the variants: the fixed row whatever group runs first, the empty `.npz`, a link, past the
   bound, past the cap. Design step 2 says the same.
3. **L1 to L8 — answered in writing.**
   - L1: Decision 4's account is corrected (the driver imports each package first; pytest 9.0.3
     returns `sys.modules[name]`); the rule is now "every ancestor package of every staged folder
     is a package the product has and a generated entry; a folder under a package the product
     lacks is refused, never staged" (Decision 14, criterion 1).
   - L2: Decision 4 gains the `setup_module` paragraph; scikit-learn's `env` sets `SKLEARN_SEED` to
     `"0"`; the survey lists every `setup_module`/`teardown_module` in the staged inits.
   - L3: Decision 8 gains `discrete/tests/test_constrained.py` (`spector`) and
     `emplike/tests/test_anova.py` (`star98`), closed by the README and the owner's answer to
     question 83; each not-selected file gives its collected count from the survey; the
     `left-out-datasets` class holds run-time failures only (Decision 9). For the lane names 074's
     line for scikit-learn's three `mmap` files.
   - L4: the Changed list gains `tests/checks/test_rules.py` (the retired allowance entries, in the
     same change); Depends on (109) states what 095's comments and docstrings must obey.
   - L5: criterion 6 is a new unit check, written first, over each 066 family's staged file list
     and group JSON; the driver-hash rule is dropped (it holds by construction) and Decision 3 says
     why.
   - L6: the allowed names are a per-family constant in `packages.py` (`SCIPY_XSLOW`;
     `SKLEARN_RUN_FLOAT32_TESTS`, `SKLEARN_SEED`), joining only by a judge change; the forbidden
     names are listed (`TMPDIR`, `HOME`, `PYTHON*`, `SCIPY_HYPOTHESIS_PROFILE`,
     `SKLEARN_TESTS_GLOBAL_RANDOM_SEED`, `SKLEARN_SKIP_NETWORK_TESTS`), "never per group".
   - L7: copy-on-write dropped (no effect on pandas 3.0.6), `SCIPY_XFAIL` added, "no new mechanism"
     corrected (a separate normal-tier family needs only its `env`; a release-tier mode would need a
     102 change, a follow-up after 0.1.0), and the survey counts mode-gated skips for the README.
   - L8: the claim list and For the lane name the `[[claim]]` block in
     `context/release-tier-claims.toml` from a `release-tier: true` branch run; the release
     acceptance's darwin cost is stated (about 4 to 12 minutes at `-n 3` for scipy's part); a 725 G
     shard is 116 to 225 s of guest time.
4. **N1 to N4 — acknowledged.** N1: `SCIPY_HYPOTHESIS_PROFILE` is on L6's forbidden list, with the
   reason. N2: the Out line gives the Windows and macOS reason in words. N3: written in with H1.
   N4: For the lane says the builder rebases onto main after the chain lands before writing code;
   the split path for statsmodels stands as drafted.
5. **The owner's four questions, as defaults pending the owner's answer:** 088 widened to scipy's
   seven test modules and five files (Decision 8); the modes README-only for 0.1.0 with your three
   corrections and the mode-gated skips counted (Decision 7); the 15 T threshold, moving
   scikit-learn's `tests/test_common.py` then its float32 cases to the release tier, nothing left
   out (Decision 7, the price); the left-out datasets as a README class, import failures under
   Decision 8 (Decisions 8 and 9).

## Verdict

Not fit to build yet: H1 (`SCIPY_XSLOW` is read by scipy's tests outside its marker, so the tier
split either runs upstream's very slow cases in the normal tier or runs them in neither); fit to
build once H1 and M1 are written in and confirmed, the Lows answered in writing.

## Confirmation

- **By:** the reviewer, on 2026-10-20, against `d9310d4`. That is the branch rebased onto the
  chain's tip `727bd4c`, with the Disposition above. I read the revised Decisions 1, 4, 5, 7, 8,
  12 and 14, the criteria, the price and *For the lane* in the specification. I checked them
  against the pinned sdists again, as data. No guest was run.
- **H1 — confirmed.**
  - `env` is a family key only, and "never per group" is now a rule with its own criterion 1
    variant. So neither failure reading remains.
  - **Do the three keyword entries cover every gated case? Yes.** I grepped every `.py` member of
    the pinned scipy sdist for `SCIPY_XSLOW` (READ). The only reads in staged test code are the
    ones Decision 7 lists. Each lands in one tier:
    - `test_axis_nan_policy.py:390`'s block is one unmarked function, `test_axis_nan_policy_full`,
      so its keyword is clean.
    - `:384`, the `kruskal` case of `test_axis_nan_policy_fast`, is unmarked. pytest names a
      function parameter by its `__name__`, so the id carries `kruskal`.
    - `:907`, `test_empty`, is `@pytest.mark.slow`. It is already release-tier by the marker, and
      102's kind (b) skips tests the marker already selected. The entry's `friedmanchisquare` part
      is harmless.
    - `test_fit.py:113` sits inside `test_cont_fit`, which is `slow`: release by the marker.
    - `test_continuous.py:1142` and `test_tanhsinh.py:265`: see the condition below.
    - So the normal tier pays for no xslow case once the keywords are right.
  - **Condition for the survey (not a new finding).** Two entries cannot be written with
    distribution names. `test_rv_generic` is parametrized over `enumerate(distcont + distdiscrete)`,
    and `test_accuracy` over `distcont`. Both lists hold lists, so pytest names them `distdataN`
    and `caseN`, not by the distribution (`_distr_params.py:6-11`, READ). Their keywords must be
    full parametrized names, such as `test_rv_generic[3-distdata3]`. pytest 9.0.3's `-k` grammar
    allows the brackets (`_pytest/mark/expression.py:10`, READ). The draft already has the survey
    write each keyword from the collected ids. A wrong keyword can only put a case in the wrong
    tier. It can never drop one, because 102 builds normal as `not (K)` and release as `(K)`.
  - **The price of mpmath at 5,000 points is small in the normal tier.** I parsed every staged test
    file that calls `assert_mpmath_equal` or `MpmathData` (`ast`, READ):
    - `test_mpmath.py`: 137 tests, all under a `slow` marker;
    - `test_cdflib.py`: 2, both `slow`;
    - `test_precompute_gammainc.py`: 1 slow and 1 unmarked.
    So the tenfold point count falls on the release tier, except one normal test. The README
    sentence stands; the normal-tier price needs no new line for it (INFERRED from the counts).
- **M1 — confirmed.** Every fixed part is written in Decision 5 and criterion 2: the `inputs`
  folder, `measured` and the cap, the one `derived_row`, a run in every stage and in the price, the
  `lstat` read, and the regular-file and `.npy`-member checks. One wording point, for the survey:
  the 16 MiB bound is INFERRED. The memo should replace it with a bound set from the measured
  sizes, for example twice the largest output. Until then a larger `boost.npz` would fail the
  family by name, so nothing passes wrongly.
- **L1 to L8 — answered in writing, confirmed.** I spot-checked each in the text:
  - L1: the mechanism is corrected and the ancestor rule refuses (Decisions 4 and 14).
  - L2: `SKLEARN_SEED = "0"`.
  - L3: the two statsmodels files are in Decision 8.
  - L4: `tests/checks/test_rules.py` is in the Changed list.
  - L5: criterion 6 is a new check.
  - L6: a per-family constant, with the forbidden names listed.
  - L7: copy-on-write dropped, `SCIPY_XFAIL` added.
  - L8: the claim block, and 116 to 225 s per shard.
- **Note for the build, no new round.** Decision 7's threshold says "keyword or path entries".
  102 has no path selection. Moving all of `sklearn/tests/test_common.py` means a kind (b) entry
  whose keyword matches every id in that file (`test_common` does, through the module's name). The
  normal group that held it must keep other files, because a normal group left selecting nothing
  fails as an empty split does.
- **N1 to N4 — acknowledged.** The four owner questions are written in as defaults pending the
  owner's answers. That matches my recommendations.
- **What blocks the survey** (Decision 1):
  - for scipy and scikit-learn, wave 09 landing, so the survey runs on main's set with numpy on
    OpenBLAS;
  - for statsmodels, 045 landed or build-reviewed;
  - the lane's grant of up to three guest sessions for the 4-hour box, never while
    `build/lane.lock` exists.

  102 need not land first: the survey's stand-in emulates the two tiers. The builder rebases onto
  main after the chain lands before writing code.

## Verdict, confirmed

Fit to build, which means the survey may start once its sets exist. H1 and M1 are written in and
confirmed, and the Lows are answered in writing. Building starts on the survey's delta review, as
Decision 1 says.

## Delta review (after the survey)

- **By:** the same reviewer, on 2026-10-21. I wrote none of the survey or its revision.
- **Reviewed:** `f4d252b4` (context only, on main `d8fc73ff`, wave 09 landed). I read the survey
  memo and its folder (`failures.txt`, `keywords.txt`, `summary.md`). I read the spec's revised
  Decisions 7 and 8, its criteria 7 to 12, the price, *For the lane* and "Delta from the survey"
  items 1 to 12. I read 102 at its tip `8fb3df7a`, Decision 3's kinds and paths rule.
- **Read again, as data:** the pinned scipy, scikit-learn and statsmodels sdists, and the kit's
  pytest 9.0.3. No guest was run. No CI run was dispatched, because the change is context only.
- **Time box:** 45 minutes.

### Each change, ruled

1. **Item 1, the measured price — sound, as a lower bound.**
   - 31.18 T for the normal markers is 2.8 times today's 11.2 T. So the drafted 15 T threshold
     could not hold.
   - The release tier is at least 53 T. `special` and `stats` stopped at the survey's 6 T caps, so
     the true figure is higher (D-L1).
2. **Item 2, the owner's rule — sound in intent.** Each suite goes to the release tier whole, with
   a smoke group per package in the normal tier. That matches the owner's words. But 102's rules
   refuse it as written (D-M1), and the smoke groups do not show what Decision 7 claims (D-M2).
3. **Item 3, the deselected clock-timed test — as written, a test left out of both tiers** (D-M3).
4. **Item 4, six statsmodels files fail at import — sound.**
   - `test_constrained.py:29` and `emplike/tests/test_anova.py:12` were READ before. The memo
     names the other four.
   - They are Decision 8 rows. Their closer is the owner's answer to question 83, through the
     README.
   - The 832 run-time failures are rightly one class, with that same closer.
5. **Item 5, two statsmodels markers registered — sound.** `thread_unsafe` and
   `skip_randomstate_check` are used and registered nowhere. Registering them keeps
   `--strict-markers` in force, as with `no_check_spmatrix`. It does not weaken the judge.
6. **Item 6, scikit-learn's own wasm skip of `callback/tests` — acceptable as a named row.** It is
   upstream's own choice for this platform: `pytest_ignore_collect` returns `_IS_WASM`. The judge
   cannot undo it without editing upstream's conftest, and §4.1 does not allow that edit. The
   README should give the folder and its 54 test functions as upstream's exclusion, not ours.
7. **Item 7, the classes — sound, with one exception** (D-L2).
   - `no-native-id` (335) is not only a test-side fact.
   - `enotsup-io` must name its call before the build review, not only "in the build".
8. **Item 8, the mode-gated skips — sound.** The numpydoc `kit_extra` candidate goes to whichever
   of 067 and 095 lands second, as drafted. Until then the 211 skips are counted and named in the
   README.
9. **Items 9 to 12 — sound.**
   - Group starts of 12 to 32 G; the family-wide `package_paths` keeps the rule.
   - The derived bound is set from measured sizes: 2,541,286 bytes, which meets my condition.
   - The keyword entries are written by full id, which meets my condition. They are now kept only
     as a record.
   - No trap was seen, and the guard held.

### Findings, most severe first

1. **D-M1. The owner's split is not one of 102's kinds, so 102's rules refuse it.**
   - **What 095 says.** Depends on still says "095 adds no tier mechanism of its own". Decision 7
     says the release tier is "everything else, by 102's kinds".
   - **What 102 says.** At `8fb3df7a` (Decision 3, READ), a release group must be one of three
     things. It is a marker group (its family has `release_marker`), a keyword group (in
     `[[release_select]]` files), or a regrtest list group. 067 adds a node-id group.
   - **102's path rule.** "the marker release groups' paths taken together are exactly the normal
     groups' paths taken together". A release group of whole paths that no normal group holds is
     none of these. It is exactly what 102 refuses: "so a whole group cannot be moved out of the
     normal tier without a selection that says why".
   - **Failure:** about 110 release groups are refused by `test_upstream_files_are_well_formed`
     on the first build. Or the builder loosens 102's rule unreviewed, which is AGENTS.md rule 4.
   - **Fix text** for Decision 7, Decision 14 and Depends on:
     - "095 adds one kind to 102's list, the **smoke kind**. A family may name its normal groups
       as smoke groups, each with a reason in words (the owner's rule of 2026-10-21). Its release
       groups by path cover every staged test path that no smoke group holds, each path whole."
     - "Over a smoke group's own paths, the release side is a marker group (scipy's
       `slow or xslow`, statsmodels' `slow`) or nothing (scikit-learn)."
     - "The rules check proves it on the real TOMLs, not only on a synthetic family:
       1. the smoke paths and the release paths together are the staged test paths, less
          `not_selected`;
       2. no path is in both, except a smoke path whose release side is marker-selected;
       3. 102's truth table holds on those paths."
     - "Decision 3 of 102 gains the kind's name, as 067 adds its own."
     - Drop the unexplained `-k "not (S)"`.
2. **D-M2. The smoke groups do not show "the package's core compiled paths"** (Decision 7's
   table).
   - **What they cover** (READ, by path):
     - scipy: SuperLU and ARPACK; trust-constr; the ODE solvers (`_ivp`, LSODA); `cluster.vq`;
       `fftpack` (ducc0 and pocketfft through `scipy.fft`); `io.matlab`'s Cython readers; LAPACK
       through f2py and Cython for Cholesky and Toeplitz.
     - scikit-learn: libsvm and liblinear, covariance, PLS and CCA, HDBSCAN.
     - statsmodels: formulas, ARIMA (statespace), the GLM family and link functions, the filters,
       the summaries.
   - **What none covers.** No smoke group covers these:
     - scipy.special: the xsf, Boost.Math and Cython ufuncs. This is the largest compiled surface,
       and the one most sensitive to the toolchain.
     - scipy.sparse's C++ `sparsetools`, where 32-bit indices are a risk.
     - scipy.spatial's qhull and `_ckdtree`.
     - scipy.optimize's HiGHS, L-BFGS-B, SLSQP, MINPACK and root finders.
     - scipy.interpolate's FITPACK and `_bspl`; scipy.signal's C filters; scipy.ndimage; scipy.stats
       (`_stats`, `_qmc`, unuran, `_boost`).
     - **Any of scipy's four carried patches' paths:** uarray in `scipy.fft`, `sqrtm`, Matrix Market
       and Sobol.
     - scikit-learn's trees and forests, `_cd_fast` and SGD, KD and ball trees, `_loss`,
       hist-gradient-boosting, pairwise reductions and `utils`' Cython.
     - statsmodels' OLS, WLS and GLS (`regression/tests`), lowess, STL and Holt-Winters.
   - The golden jobs touch most of these with a few values each: `scipy_numeric.py`,
     `scipy_solvers.py`, `scipy_edges.py`, `machine_learning.py` and 045's `statistical_models.py`
     (READ). So "the normal tier proves the core" is true of jobs and smoke together. It is not
     true of the smoke groups alone, and the selection has no stated rule.
   - **Failure:** a toolchain, numpy or OpenBLAS change that breaks `scipy.special`'s Boost.Math
     paths or `sparsetools` at 32 bits passes every normal run and every landing. It is found only
     at the release acceptance before the tag, about 55 minutes in. Then it must be traced back
     through the ledger.
   - **Fix text:** "Each smoke group's paths are chosen by a stated rule. The rule covers each
     compiled extension family of the package, from the build's own list: a smoke test file, or a
     named golden-job line. It also covers each carried patch's path with a smoke test. Decision
     7's table gains a row per family naming its cover. Each package's smoke groups total at most
     500 G (about 4.5 % of today's upstream fuel)."
   - **Candidates for the builder to measure:**
     - scipy: `special/tests/test_cython_special.py`, `sparse/tests/test_sparsetools.py`,
       `spatial/tests/test_qhull.py`, a `-k highs` slice of `optimize/tests/test_linprog.py`,
       `interpolate/tests/test_fitpack.py`, `signal/tests/test_upfirdn.py`, `stats/tests/test_qmc.py`
       (patch 0004), `io/tests/test_mmio.py` (patch 0003), `fft/tests/test_backend.py` (patch 0001;
       today in D-L2's class);
     - scikit-learn: `utils/tests/test_sparsefuncs.py`, `neighbors/tests/test_kd_tree.py`,
       `ensemble/_hist_gradient_boosting/tests/test_splitting.py`, a slice of
       `tree/tests/test_tree.py`;
     - statsmodels: `regression/tests/test_regression.py`,
       `nonparametric/tests/test_lowess.py`, `tsa/stl/tests`.
3. **D-M3. `test_choose_conv_method[numpy]` is left out of both tiers, and the fix is already in
   the harness.**
   - **Why it never ends.** `_timeit_fast` raises `number` by powers of ten until one measured
     interval reaches 0.5 ms, up to 10⁹ (`signal/_signaltools.py:1231-1250`, READ). Under the
     judge's counted clock, the interval between its two clock reads is one 1 µs step, whatever
     the work done between them. So it never reaches 0.5 ms, and the loop runs up to 10⁹ calls,
     then 10¹⁰ more for each of three repeats.
   - **The fix is one existing parameter.** `guest.run` already takes `clock_step_ns`
     (`tests/harness/guest.py:563`). At a step of 1 ms, the first interval passes at `number = 1`,
     and the test ends.
   - **As written** ("deselected by node id, never run … closer: a judge follow-up the lane
     reserves"), the test runs in no tier, which breaks the owner's rule. The roadmap reserves no
     such follow-up yet (grep, READ), so the closer is not a reserved number either.
   - **Fix text:** "The test runs alone in its own release-tier node-id group, with a clock step of
     1 ms (a group key `clock_step_ns`, its reason in words: 'the test repeats a call until the
     clock has advanced 0.5 ms; the judge's clock advances only when read'). It has a cap by the
     rule from its measured fuel. The key is allowed only on a node-id group, and only with that
     reason."
   - **Fallback, acceptable only if the key cannot be built in 095:** a named gap whose closer the
     roadmap reserves before the build starts.
   - **Same pattern, a lead for the build.** `special/_mptestutils.py:385-400` enforces mpmath's
     time limits with `sys.settrace` and `time.time()` when there is no `SIGALRM`, as in WASI. That
     reads the clock on every trace event. It may be why `special`'s slow sessions reached the 6 T
     cap. The build should measure it, and say whether a clock step belongs there too.
4. **D-L1. The release tier has no upper bound for the booking.** The lane books the release
   acceptance from Decision 11 of 102.
   - **Fix text:** "The build measures `special` and `stats` to the end with a cap of 20 T each.
     A session past it is split by `[[split]]` and recorded. The memo then states the release
     tier's measured total and its darwin minutes at `-n 3`."
5. **D-L2. `no-native-id` mixes a product defect with a test-side fact.**
   - 288 of its 335 members are in `io`'s tests: temporary names that the tests themselves make.
     That part is a README fact.
   - But `scipy/_lib/_uarray/_backend.py:270,299` calls `threading.get_native_id()` inside
     `set_backend` and `skip_backend` (READ). So `scipy.fft.set_backend` and `skip_backend` raise
     `AttributeError` in the product. That is user-facing; the members include
     `fft/tests/test_backend.py::test_backend_call[...]` (`failures.txt`).
   - **Fix text:** "`no-native-id` is split by where the call is. The tests' temporary names close
     with `README.md`. The library's call in uarray's backend is a product finding the lane gives a
     number. Its likely fix is the runtime's `threading` naming a native id, the one thread's, on
     WASI. It is not a scipy patch."
   - Likewise, `enotsup-io` names the call that answers `ENOTSUP` before the build review.
6. **D-N1. Rule (8): not 095's to make, so strike it from Decision 7 and file it with the owner.**
   - **What it says.** "A landing that changes a package's own build runs that package's release
     groups on its branch run."
   - **Against the owner's words.** It fits the second clause, "only run the tests needed to
     confirm our new edits are working". It strains the first, "We only run slow tests when we are
     trying to publish to pypi". It also binds every later specification's landing. That makes it
     a rule of the lane's process (AGENTS.md, 102's tier table), not a decision of this
     specification.
   - **It does not touch the owner's answer to 102's question 2.** It is a CI branch run (102's
     `release-tier` input), never a lane-local run, and nothing is accepted from it (102, Decision
     5).
   - **My recommendation for the question's default:** yes, and widened to the package's shared
     build inputs: the toolchain, CPython, numpy and OpenBLAS pins and recipes. D-M2's failure
     comes from exactly those changes. The cost is about 75 release shards per such run, about 20
     to 25 more minutes (INFERRED from the delta's packing), on the few landings that touch a
     build.
   - **Where it goes.** Each such run writes the specification's `[[claim]]` block (102, Decision
     6). The reviewer reads the run's tier. The rule needs no judge check.

### Verdict, delta

The survey is sound, and items 1 and 4 to 12 stand. The delta lands once D-M1 (the smoke kind
added to 102's list and proved on the real TOMLs), D-M2 (the smoke selection by a stated rule
covering each compiled family and each carried patch) and D-M3 (the clock-timed test run with its
own clock step, or a reserved closer) are written in and confirmed. D-L1, D-L2 and D-N1 are
answered in writing, and rule (8) goes to the owner as a question. Building waits for that
confirmation (Decision 1).

## Disposition of the delta review (filled in by the author, then confirmed by the reviewer)

By the builder, 2026-10-21, who took over the specification from its stopped drafter and wrote
none of the survey. Every finding is written into the specification; none is declined. New
measurements are EXECUTED on the main tree's frozen set `SHA256SUMS d0d91cef` (wave 10's), one
guest at a time, never while `build/lane.lock` existed; the memo's section *Smoke selection, the
clock-stepped test and the split* and its folder `smoke/` hold the records.

1. **D-M1 — fixed, as the fix text says, as a request to 102.** A new section, *For 102: the
   smoke kind*, gives the exact change 102 must make: a group key `smoke` (a reason in words) on
   every normal group of a smoke family; a fourth kind, `release_by = "path"`, whose groups run
   their paths whole with no `-m` and ignore by construction each smoke path under them; the
   paths rules (no path release path in a smoke path, none in two path groups, every staged test
   file under exactly one smoke path or one path release group when the tarball is present, no
   `[[release_select]]` in a smoke family; 102's marker rule unchanged over the smoke paths); a
   500 G smoke budget; and Decision 6's ledger widened to local `--tier release` runs. It lists
   102's unit rows on a three-file synthetic family. Depends on (102) now says 095 needs this kind
   and adds no other. Decision 7 drops `-k "not (S)"`. **Proved on the real stage**:
   `smoke/split.py` carries those rules and runs them on the three pinned tarballs with Decision
   7's smoke groups and one path release group per staged folder: clean for all three (scipy 329
   files, 63 smoke and 266 in 28 path groups; scikit-learn 256, 37, 219 in 32; statsmodels 285, 26,
   259 in 44), and each of six mutants per family refused with its own line (`smoke/split.txt`).
   Criterion 7 runs the same rules on the real TOMLs. The lane routes the request to 102's builder.
2. **D-M2 — fixed, as the fix text says.** Decision 7 states the selection rule: every compiled
   family from the product's own `sys.builtin_module_names` (95, 69 and 26 modules; 31, 19 and 11
   families) is touched by the cheapest file of its own tests, or by a named golden-job line where
   the file costs more than about 15 G net; the review's named families (scipy.special,
   `sparsetools`, qhull, HiGHS, scikit-learn's trees, statsmodels' OLS) and every carried patch
   (scipy's four, OpenBLAS's void LAPACK, qhull's, scikit-learn's html repr, statsmodels'
   datasets) always by a smoke file; the main entry points named; whole paths only; at most 500 G
   a package; four named release-only exceptions with their reasons (scipy `_levy_stable` and
   `_lib`, statsmodels `linbin` and `exponential_smoothing`). Your candidates were measured among
   117 probes; `test_cython_special.py`, `test_sparsetools.py`, `test_qhull.py`, `test_milp.py`
   (HiGHS), `test_qmc.py`, `test_mmio.py`, `fft/tests/test_basic.py`, `test_matfuncs.py`,
   `tree/tests/test_split.py`, `test_sparsefuncs.py`, `test_kd_tree.py`, HGB's `test_splitting.py`,
   `test_regression.py`, `test_lowess.py` and `test_stl.py` are in. The four groups, each
   measured whole: **`scipy-smoke-a` 207.4 G, `scipy-smoke-b` 221.8 G, `scikit-learn-smoke`
   205.5 G, `statsmodels-smoke` 136.0 G, 770.6 G in all**, every failure a member of a measured
   class. Decision 7's table gives each group's paths and cover, and the golden lines that stand
   in. A new `[smoke_cover]` table per TOML, checked against the compiled-family list, holds the
   rule against drift (criterion 1). Decision 12 now packs them in two normal Linux shards; the
   price section moves to 770.6 G.
3. **D-M3 — fixed, the preferred way.** With `guest.run`'s existing `clock_step_ns` at 1 ms,
   `test_choose_conv_method[numpy]` **passed**: one outcome, 37.92 G for the session (EXECUTED).
   Decision 10 now runs it in the release tier, alone, as the first split group of
   `signal/tests/test_signaltools.py`'s path release split, with a new group key
   `clock_step_ns` and its `clock_reason` in words; the key is allowed only on a release group,
   from 1 µs to 1 ms, and a run of such a group with more than one outcome is red (Decision 14,
   criterion 1). No reservation is needed; For the lane says so. Your lead on
   `_mptestutils.py`'s `sys.settrace` timer is in Decision 11 for the build to measure.
4. **D-L1 — answered in writing.** Decision 11 measures `special` and `stats` to the end under
   20 T each, splits at the file where a session reaches the cap, and the memo states the release
   tier's measured total and darwin minutes; the price states the bound (at most about 81 T).
5. **D-L2 — answered in writing.** Decision 9 splits `no-native-id` into
   `no-native-id-test-names` (`io`'s temporary names) and `no-native-id-uarray` (the library's
   call), and gives the README text in words: "`scipy.fft.set_backend` and
   `scipy.fft.skip_backend` (and every uarray `set_backend`/`skip_backend` in scipy) raise
   `AttributeError: module 'threading' has no attribute 'get_native_id'` in this build …". For the
   lane asks for a number for the product finding. `enotsup-io` names its call: numpy's
   `tofile`/`fromfile` duplicate the descriptor, which preview1 refuses; EXECUTED, a path fails
   too, so the README's advice is `tobytes`/`frombuffer`.
6. **D-N1 (rule (8)) — struck, by the owner's words**, not filed as a question: "We only run slow
   tests when we are trying to publish to pypi". Decision 7 now says no branch run runs release
   groups and the smoke groups confirm an edit (the reason D-M2's cover matters); criterion 12
   drops 095's own `release-tier: true` dispatch, its release groups measured locally by node id
   (criterion 5), its claim block written from those runs (*For 102* item 6).

**Not changed:** items 1 and 4 to 12 of the delta, which the review found sound.
