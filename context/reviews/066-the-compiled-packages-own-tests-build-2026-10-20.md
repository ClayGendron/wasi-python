# Review of 066 — the compiled packages' own tests in the release (build review)

- **Date:** 2026-10-20
- **Reviewer:** a fresh Claude agent (Opus 5.5). It wrote none of spec 066 and reviewed none of its
  drafts.
- **Reviewed:** `spec/066-the-compiled-packages-own-tests` at `493bb0a` (the build is `f0144ca`; the
  landing notes are on top), base main `21dff9d`, judged against wave 06's set (`SHA256SUMS`
  `f12cd25c`). Read in the worktree `/Users/claygendron/Git/Repos/wasi_python-066`, read only.
- **Time box:** 45 minutes of reading (build-class), plus the wait for CI.
- **Run:** `39432793331` on `493bb0a`: completed, success; 38 jobs green on all three systems, `gather` included, 3 publish jobs skipped. Its `release-record-1`: 707/804 pass, 90 gap, 7 blocked, 0 fail; the 35 new groups 17,911 passes and 8,533.9 G on Linux (the builder's run 8,533.8 G), split counts 518 and 419 in every group, the 18 classes `gap`.
  The builder's run `39424879820` on `f0144ca` (READ: `gh run view --json jobs`, and
  `release-record-1` downloaded): every job `success`; the scoreboard is 707/804 pass, 90 gap,
  7 blocked, 0 fail. On Linux it ran all 35 new groups: 17,911 passes, 8,533.8 G of fuel, each
  group within 0.19% of the builder's darwin fuel (`build/066/fuel.json`), so every cap keeps its
  1.5 times headroom. The 18 new class checks are `gap`. Every split group recorded the same
  count: 518 for `test_filled.py` (9 groups) and 419 for `test_lines.py` (8 groups).
- **Re-ran (single node ids, `build/lane.lock` absent each time):**
  - `uv run pytest tests/unit/test_packages.py tests/unit/test_upstream.py
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_files_are_well_formed"` →
    103 passed, exit 0.
  - `uv run pytest "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[kiwisolver]"`
    → 1 passed, exit 0; its stream has 50 passes, `E 0`, and `M` lines only for
    `py/tests/*` under `/upstream-kiwisolver/tree/`.
  - The builder's kept streams (`build/harness/streams/`, READ): the 9 `contourpy-filled-*`
    streams started 518 distinct node ids between them, each exactly once; the 8 `contourpy-lines-*`
    streams started 419, each once. Each stream ends `E 0`.
  - Coverage, by a reader script over the six pinned tarballs' member lists (`tar -t`):
    every `test_*.py` of the six packages is under a group path or in `not_selected`. The only
    files outside both are matplotlib's two gallery examples named `*_test.py` and contourpy's
    `tests/util_test.py` (a helper). That check is by file name only; see M1 for what it misses.

## The builder's self-check

All present. One item reads loosely: "every new check seen failing first ... the unit checks were
written with the code". A unit check written with its code was not seen failing first. See L7.

## Acceptance criteria against evidence

1. **The rules** — partly met. READ: `packages.split_errors` enforces Decision 11's form: at least
   two groups, one expression fewer than groups, none empty, each parsed by pytest's own
   `Expression.compile`, no group in two splits, and each group's paths exactly the file.
   `Split.keyword` builds `(e_i) and not (e_1 or … or e_(i-1))`, and the last group's
   `not (e_1 or … or e_(n-1))`. That is a partition by construction. EXECUTED: unit cases for the
   grant, cwd, budget, a split with too many expressions, an empty expression, an expression
   that does not parse, a group with a second path, and `cwd_files` without `/tmp/work`.
   Not met: there is no "cap above 1.5 times its recorded fuel" rule, and a `driver = "package"`
   TOML with `path_packages` or `support` is silently ignored, not refused (M3).
2. **The stream and the verdict** — mostly met (EXECUTED, unit). A split group whose pytest exits
   with 5 gets the finding `pytest exit code 5` (`upstream.judge_group`: any code other than 0
   or 1). A missing `K` line is a finding. The guard is path-based. lxml's selection is checked
   in two directions, but not all the way (M2). No recorded numpy or pandas stream is replayed;
   `test_numpy_and_pandas_are_read_as_today` checks only how their configurations load. Criterion
   6's measurement covers this instead.
3. **The survey, then the baseline** — met (READ). The memo and its re-survey are EXECUTED.
   `build/066/run1.txt`: 10 of 35 groups failed before the class lists existed.
4. **The lists and gaps complete** — met. EXECUTED by the builder (`run3.txt`: 35 passed,
   18 xfailed), and READ from CI's record (35 pass, 18 gap).
5. **Fuel repeats** — met as reported (READ; I did not re-run it). CI's Linux fuel matches darwin
   within 0.19%.
6. **numpy, pandas and CPython do not move** — met (READ). `drive.py`, `numpy.toml` and
   `pandas.toml` are not in the diff. `upstream.Session.prepare` never stages a package family
   into `/upstream`. `test_numpy_and_pandas_are_read_as_today` asserts that `/upstream`'s family
   is exactly numpy and pandas. The builder measured `numpy-lib` and `pandas-libs` equal to
   `accepted.json`. The stage-manifest hash check that the criterion names was not written (L8).
7. **The shards** — met. EXECUTED by CI: 12 `upstream-plot-*` jobs, each group in exactly one Linux
   shard, the rules check green.
8. **The fetch** — met in behaviour (EXECUTED by CI: every plot shard fetched its trees).
   `fetch.shard_packages` is generic over families. The criterion's unit cases in
   `test_fetch_trees.py` were not written (L8).
9. **The tie and the stage** — met by reuse (READ). `packages.Session._prepare` calls
   `upstream.tie_errors`, `tarball_members` and `patch_created`. `stage` copies members only and
   lists what it left out.
10. **packages.toml** — met (READ): six `suite`s; scipy's entry closes with 095.
11. **The full judge** — met as reported (`build/066/fast.txt`, the fast tier). The full judge
    runs on CI.
12. **The branch's dry run** — met (READ: `39424879820`; the plot shards took 100 to 243 s each).
    My run `39432793331` passed every job too.
13. After landing; not this review's.

## Findings, most severe first

1. **M1 — Some tests are left out without a true reason, against Decision 8 and the owner's rule**
   (`tests/upstream/contourpy.toml`, the `test_codebase.py` row; `tests/upstream/pillow.toml`).
   - contourpy's `tests/test_codebase.py` is not selected because "every test runs tools over the
     source repository through subprocess". That is true of `test_cppcheck` and `test_mypy`. It
     is false for `test_version`, which compares `contourpy.__version__` with
     `contourpy._contourpy.__version__` and needs nothing the product lacks. Decision 8 says a
     file is left out only when it cannot load or every test needs what the product lacks. A
     single failing test is a class member, never a reason to drop its file.
   - Pillow's `selftest.py` is neither run nor named. It is Pillow's doctest self-test, with 59
     examples, and Pillow's Makefile runs it in `install` and `release-test`.
   - Pillow's `checks/check_*.py` is neither run nor named either: about 21 pytest test
     functions. Pillow's own wheel test command runs `checks/check_wheel.py`.
     `check_large_memory.py` skips itself below 64 bits, which would be a counted skip.
   - The coverage scan by file name cannot see these, because they are not named `test_*.py`.
   - Failure: the owner's decision says every upstream test of a package we build runs, never
     left out. Spec 066's Problem says every test not run is named with its reason. A test that
     would pass (`test_version`) is dropped under a reason that does not apply to it, and
     Pillow's two other test sets are not accounted for at all.
   - Fix text:
     - Select `tests/test_codebase.py`. Admit `test_cppcheck` and `test_mypy` as a contourpy
       `no-processes` class, with a gap that closes with `README.md`. (Alternatively, deselect the
       two by node id, with the subprocess reason.)
     - For Pillow, run `selftest.py`'s docstrings, as lxml's `docstring_modules` are run, or
       name it in `not_selected` with its true reason.
     - Either give `checks/` a group (its files are not `test_*.py`, so it needs pytest's
       `python_files` or explicit paths), or name each file with its true reason.
   - Evidence that closes it: the changed rows, and re-runs of the affected groups (`contourpy-1`
     or whichever group takes `test_codebase.py`, and `pillow`), with the new fuel and passes in
     the claim list.

2. **M2 — lxml's selection is not "equal to test_suite()'s both ways": 34 suite builders are
   counted as passing tests** (`tests/upstream/package_drive.py` `_keep`;
   `tests/harness/packages.py` `keep_findings`).
   - pytest collects each selected module's `def test_suite()` as a test function. The kept stream
     `build/harness/streams/lxml-lxml.txt` has 34 lines of the form
     `R passed src/lxml/tests/test_*.py::test_suite`.
   - lxml's own runner calls `test_suite()` to build its suite. It never runs it as a test.
     `_keep` deselects only `unittest.TestCase` items of unlisted classes, so these 34 items run.
   - `keep_findings` checks that every listed class ran something, and that every deselected item
     is of an unlisted class. It never checks a third thing: that every item that ran is
     something `test_suite()` adds. So a non-`TestCase` class, or a module-level function, in a
     module that has a `test_suite()` runs, and nothing notices.
   - Failure: lxml's 2,058 passes include 34 that are not tests. The total of 17,911 includes
     them too. The accept-judge flag says the selection equals `test_suite()`'s "both ways".
   - Fix text:
     - In `_keep`, deselect each module's `test_suite` item with a `D` line, and admit `D` lines
       for `::test_suite` in `keep_findings`.
     - Add the third direction in `keep_findings`: a started node `f::X::…` or `f::name` of a
       module in `keep` whose `X` is not listed (and whose entry is not `"*"`) is a finding. Give
       it a unit case.
     - Re-measure `lxml` (expected 2,024 passes), and correct the totals in the claim list, the
       flags, the CHANGELOG and the README.

3. **M3 — Decision 14's 1.5 times cap rule has no check, and forbidden keys are ignored rather
   than refused** (`tests/harness/packages.py` `rule_errors` and `load`).
   - Criterion 1 and Decision 14 name the rule: "each cap is at most 1.5 times the fuel the
     re-survey recorded for it, rounded up to two figures". No code reads a recorded fuel. A cap
     may be raised together with its family's `budget`, and only `SPLIT_MAX` (1.3×10¹³, today
     about 22 G above the sum of the budgets) stops it. Moving fuel between caps is never caught.
   - `packages.load` drops `path_packages` and `support`, where Decision 14 says a package family
     "never" uses them and criterion 1 asks for a refusal "with its own line".
   - I checked today's caps by hand against `build/066/fuel.json`. All 35 are 1.5 times the
     measured fuel, rounded up to two figures. So this is a missing guard, not a wrong number.
   - Fix text:
     - Record each group's measured fuel as data, for example `measured = 439_800_000_000` next
       to `fuel`.
     - In `rule_errors`, refuse a cap above 1.5 times `measured`, rounded up to two figures, and
       refuse `path_packages` or `support` in a `driver = "package"` TOML. Give each a unit case.
     - Or amend criterion 1 in writing, naming `SPLIT_MAX` as the stand-in and saying what it
       does not catch.

4. **L1 — Equal collected counts across a split are recorded, never compared**
   (`tests/checks/test_v1_3_upstream_suites.py`, the `collected` fact). Decision 11 chose a fact
   for the lane to read, and today's counts are equal (518 and 419, darwin and Linux). Fix text,
   optional: in `packages.Session.group`, compare each split group's `K` with the first group of
   its split that ran, and make a difference a finding. It costs nothing, and the lane no longer
   has to remember to look.

5. **L2 — contourpy's `slow` and `text` cases** (Scope, "contourpy's `slow` and `text` tests").
   They stay upstream-default skips (`--runslow`: the 10 `test_filled_compare_slow` cases on
   1000×1000 grids; `--runtext`), and they are counted. The Scope line predates the owner's
   option (b). Fix text, in Scope: "Under option (b) these remain upstream's default selection,
   counted as skips; whether 'every test' includes `--runslow` and `--runtext` is put to the owner
   with the cost of the 10 slow cases." The lane decides whether to ask.

6. **L3 — `tests/test_bokeh_renderer.py` skips itself** (`pytest.importorskip(
   "contourpy.util.bokeh_renderer")`). Decision 8 says such a file is selected and its skips are
   counted. Fix text: select it (one counted `R skipped`), or say why not.

7. **L4 — `wasm32-memory`'s fact is not in the README.** The class closes with `README.md`, but
   the README never says that python.wasm declares no maximum memory, so wasm32's 4 GiB bounds an
   allocation. Its only "4 GiB" lines are about the runner's `memory_bytes`. Decision 15 asks
   for every README-closed class's fact to be there. Fix text: one bullet in the platform facts
   saying exactly that, naming Pillow's DDS samples as an example.

8. **L5 — `_abs()` would corrupt a marker or an option's value** (`tests/upstream/package_drive.py`).
   It prefixes the tree onto every argument that does not start with `-`. So `["-m", "not slow"]`
   from a TOML `marker`, or a value-taking option in `args`, would become a path. Today every
   `marker` and `args` is empty, so nothing is wrong yet. Fix text (a code fix, the builder's):
   make only the group's paths absolute, in `group_args` on the host, and pass everything else
   through unchanged.

9. **L6 — "For the lane" omits 099's order.** 099 (in CI now) empties `matplotlib-rest-b1`'s
   `no-fp-exceptions` class. 099's spec handles both orders, but 066's lane notes should say it
   too. Fix text: "If 099 lands first, 066 drops the class, its list, its gap and the README
   bullet, and re-measures `matplotlib-rest-b1`. If 066 lands first, 099 does, as its Decision 7
   says."

10. **L7 — Self-check wording.** Write "the unit checks were written with the code; their bad
    cases each fail with their own line", and drop "seen failing first" for them.

11. **L8 — Criteria 6 and 8 name unit checks that were not written** (the stage-manifest hash;
    `test_fetch_trees.py`'s cases). The behaviour is evidenced: `numpy-lib` and `pandas-libs`
    equal to `accepted.json`, and CI's shards fetched their trees. Fix text: say so in the
    landing notes as the substitute evidence, or write the checks.

**Notes, no finding:**
- `PIL.features.pilinfo()` raises `AttributeError` in the product, because `PIL._imaging` is
  builtin and has no `__file__` (the `builtin-no-file` class). It is a user-visible function, so
  the owner may want a follow-up beyond the README fact.
- `open('')` raising `IsADirectoryError` is a WASI path-resolution fact, honestly admitted.

## Focus questions answered

- **Nothing left out:** the partition holds by construction (READ) and in the streams (EXECUTED by
  the builder: 518 and 419 distinct ids, each once). A split group that selects nothing fails at
  judge time with `pytest exit code 5`. Every split group recorded the same count on darwin and
  Linux. lxml's selection is not equal both ways (M2). Not every file is accounted for (M1).
- **Classes and gaps:** 18, each with a gap whose `match` is a digest of the exact findings, so a
  new member turns a run red despite broad patterns (`^AssertionError: assert False$`,
  `^assert 0$`). Each names its closer: `README.md`, spec 023, spec 046, or `context/roadmap.md`
  (097, 099). Only `no-fp-exceptions` is a product defect, and 099/100 fix it before 0.1.0, as
  the owner chose. `stage-layout` is the judge's own staging, with closer 097. No class hides a
  defect that should be fixed here.
- **Caps:** each is 1.5 times measured fuel, rounded up to two figures (checked by hand). Both
  contourpy raises came from a completed re-measurement, not a guess: `run1.txt` shows the two
  out-of-fuel findings, and `run2.txt` the 10 groups re-run and passing. There is no rule check
  (M3).
- **numpy and pandas unchanged:** yes (criterion 6 above).
- **The guard and the grants:**
  - Each family is one read-only preopen (`(grant, root, False)`), sealed (089).
  - The working folder is `/tmp/work`, in the run's own writable root. For contourpy and
    Pillow it is the read-only tree root, so a write there fails rather than escaping.
  - `cwd_files` are rule-checked tarball members, copied into the run root.
  - Only the stage folders are staged. So the `__path__` appends in `package_paths` cannot load
    product code from the tree, and the guard would flag one if they did.
  - Nothing lets a guest write outside its grant.
- **HostLitter:** `litter.Watch` raises `HostLitter`, an `AssertionError`, from `guest.run`. The
  check fails red, nothing is cached, and nothing passes quietly. "For the lane" says to re-run
  it once the litter is gone, with closer 097.
- **Claim list and flags:**
  - 53 gained rows (35 suites and 18 classes), 18 gaps, and the judge hash changes. All match
    the diff and CI's record.
  - Both flag reasons begin "066" and hold no `"`, `$`, backtick or `!`.
  - The accept-judge text's "lxml's selection equal to test_suite()'s both ways" and the
    17,911 passes change with M2.
- **The 067 split:** the branch's eight commits since `21dff9d` touch no 067 file. 067 is
  `6ffda49` on `spec/067-the-pure-python-packages-own-tests`, on `21dff9d`. One spec per branch.

## Constitution checks

- §4 constraints:
  - No `src/`, `scripts/`, `recipes/` or `downloads/` line changes, and no artifact byte
    changes.
  - Every input is a pinned tarball tied to `MANIFEST` (the tie).
  - Tests count fuel and passes, never wall-clock. The job times are benchmark facts in the
    notes.
  - The judge is not weakened: new checks only, numpy's and pandas' rows unchanged, and the
    judge hash moves with the accept-judge text.
  - The "never left out" rule is not fully met (M1).
- §7 never-do list: nothing tripped. No upstream patch, no copying from prior art, no edit to an
  accepted row.

## Disposition (filled in by the author, then confirmed by the reviewer)

The builder, 2026-10-20, rebuilt on main `2516875` (wave 07's set, `SHA256SUMS` `dc6ba3a5`);
every number below is EXECUTED on darwin-arm64, a private `cp -c` copy of that set, the judge's
own checks by node id, at most three guests, `build/lane.lock` absent at each start.

1. **M1 — written in and measured.**
   - contourpy: `tests/test_codebase.py` is selected in `contourpy-rest`. `test_version` passes;
     `test_cppcheck` and `test_mypy` fail with `[Errno 58] wasi does not support processes` and
     are the new `no-processes` class (2 members, a gap closing with `README.md`).
   - Pillow: `selftest.py` runs as a docstring module (`support_files`, `docstring_modules =
     ["selftest"]`): its 59 examples are one doctest item, `::docstrings:selftest.testimage`,
     which passes. The guard admits a staged support file named as a docstring module (a unit
     case).
   - Pillow's `checks/` is staged and runs in the `pillow` group (`python_files` adds `check_*.py`
     and `*_check.py`): 5 pass, 7 skip (counted), 10 fail into classes. Four are
     `pillow-zlib-only` (`check_jpeg_leaks.py`, now 55 members); `no-resource-module` (2,
     `check_imaging_leaks.py`: WASI has no `resource`; the README gains the fact);
     `not-pillows-wheel` (3, `check_wheel.py` asserts the PyPI wheel's modules, codecs and
     features; spec 023); `fli-overflow-native` (1, `check_fli_overflow.py`: the repo's oracle,
     native Pillow 13.0.0, raises the same `OSError`, and Pillow's own test commands never run
     it). Six files are named in `not_selected`, each with its reason: `check_release_notes.py`
     reads `docs/releasenotes` (a release-time script over the source tree);
     `32bit_segfault_check.py`, `check_icns_dos.py` and `check_j2k_dos.py` run their
     reproduction at import and expect the exception at module level, so pytest records a
     collection error and interrupts the session (seen in the rebuild's first run);
     `check_fli_oob.py` and `check_jp2_overflow.py` are valgrind scripts, the second's inputs not
     in the sdist.
   - Measured: `pillow` 432,950,151,677 fuel, 4,593 passes (was 4,587); `contourpy-rest`
     205,916,211,054, 277 passes (was 198, with L2's text cases and L3's file).
2. **M2 — written in and measured.** `_keep` now keeps only `TestCase` items of a listed class
   (any `TestCase` for `"*"`) in a module with `test_suite()`; every other item, the 34
   `test_suite` builders included, is deselected with a `D` line. `keep_findings` checks three
   directions: every listed class ran; every test outcome in a keep module is one `test_suite()`
   adds; no `D` line is one it adds. Unit cases for each. `lxml`: 103,449,823,065 fuel, 2,024
   passes (was 2,058), every passed node a listed class's. Totals, the accept text, the CHANGELOG
   and the README are corrected (40 groups, 17,972 passes, 9.985 T).
3. **M3 — written in.** Each group carries `measured = <fuel>` beside its cap. `rule_errors`
   refuses a group without `measured` and a cap above `rule_cap(measured)` (1.5 times, rounded up
   to two significant figures), and refuses `path_packages` and `support` in a package TOML, each
   with its own line; unit cases for each. Every cap and budget was recomputed by the rule from
   the rebuild's measurements. The stand-in `SPLIT_MAX` total is removed: the per-cap rule
   replaces it, and no total is fixed (Decision 11).
4. **L1 to L8.**
   - **L1** — written in: `Session` compares the `K` line across a split's groups; a difference is
     a finding (unit case).
   - **L2** — written in under the owner's rule: `args = ["--runslow", "--runtext"]`. The ten
     `test_filled_compare_slow` cases pass, about 91 G each, in three new split groups
     (`contourpy-filled-9` to `-11`, 946.6 G in all). `test_config.py`'s `--runtext` cases made
     its group 582 G, so it is split in two (`contourpy-config-1`, the 18 `True` cases, 377.1 G;
     `-2`, 205.1 G). Seventeen of them fail as the `text-rendering` class: contourpy's own
     image-difference log shows the same images without text match (max at most 52 of 255, mean
     at most 0.0003) and with text differ (max 255, mean 3.5 to 8.4), past contourpy's thresholds
     (max 100, mean 0.02); the text matplotlib 3.11.2 with FreeType 2.14.3 draws here differs from
     contourpy's baselines. The image I read showed the same figure with different glyph shapes.
     `test_renderer.py`'s text cases pass. `cwd` is now `/tmp/work` with the 52 baselines copied
     in, so a differing image writes its `result_images` instead of `PermissionError`. Cost:
     1.45 T of fuel in all with M1, five more groups (40), caps 1.517×10¹³, and two more Linux
     shards (fourteen, at most 725 G each).
   - **L3** — written in: `test_bokeh_renderer.py` is selected; one counted
     `R skipped tests/test_bokeh_renderer.py` (no `bokeh`).
   - **L4** — written in: the README's platform facts say `python.wasm` declares no maximum
     memory, so wasm32's 4 GiB bounds an allocation, naming Pillow's DDS samples.
   - **L5** — written in: `_abs()` is gone; `group_args` makes only paths (and `--ignore`
     values) absolute on the host, and the driver passes every argument through unchanged.
   - **L6** — written in "For the lane": 099's order both ways.
   - **L7** — written in: the self-check says the unit checks were written with the code, not
     seen failing first; their bad cases each fail with their own line.
   - **L8** — written: `test_the_upstream_stage_never_takes_a_package_family` (criterion 6) and
     `test_a_shard_fetches_only_its_families_trees` (criterion 8).
   - **The Note** — recorded in "For the lane" as a reserved follow-up for the lane, not fixed
     here.

## Verdict

Lands once M1 (test_codebase's `test_version` selected or truly accounted for, and Pillow's
`selftest.py` and `checks/` run or named), M2 (lxml's `test_suite` builders deselected, the third
direction checked, and the counts corrected) and M3 (the 1.5 times cap rule and the refusal of
`path_packages`/`support` checked, or criterion 1 amended in writing) are written in and
re-measured.
