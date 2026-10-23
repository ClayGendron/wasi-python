# Review of 067 — the pure-Python packages' own tests in the release (the specification, before build)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I wrote none of 066 or 067, and none of their drafting evidence. I did not read the earlier, uncommitted 067 review draft in the session scratchpad (`067-review/`), so this review is independent of it.
- **Read:** `AGENTS.md`; the constitution (all of it); `context/decisions.md`, "Every test of every package we build (2026-10-20)", "statsmodels and the pure-Python packages' own tests in 0.1.0 (2026-10-20)", "Fewer CI runs per specification, and a faster run (2026-10-20)"; `context/reviews/README.md`; the 067 draft, `git show 6ffda49:context/specifications/067-the-pure-python-packages-own-tests.md` (drafted from `1ce7381`; its branch sits on `21dff9d`); at `66cc120` (`origin/spec/066-…` and `origin/wave/08`): spec 066, its four reviews (`-spec`, `-spec-delta`, `-build`, `-confirm`), `tests/harness/packages.py`, `tests/upstream/package_drive.py`, `tests/release_shards.toml`, `tests/upstream/packages.toml`, `downloads/SHA256SUMS`, `scripts/00_download.sh`, `scripts/assemble_artifacts.py` (the pin lines), `tests/harness/upstream.py` (`tie_errors`), `tests/harness/paths.py` (`manifest_pin_errors`); spec 101 on `spec/101-faster-release-run` (`86a870a`), Decisions 2, 9 and 12; spec 045 on main; the drafting evidence `context/research/2026-10-20-the-packages-own-tests-drafting/` (on 066's branch only, not on 067's draft commit). The 34 sdists and 8 tag archives the drafter fetched into the session scratchpad, read as data (`tar`, `grep`, `python -I` with `zipfile`/`tarfile`).
- **Reviewed:** the specification as drafted, `6ffda49`, against 066 as it now stands (`66cc120`).
- **Run:** none. A pre-build review of a context-only draft; the brief forbids a dispatch.
- **Re-ran** (every one EXECUTED on darwin-arm64; `build/lane.lock` absent before each guest probe; guests against main's frozen set `build/artifacts`, `WASI_PYTHON_ARTIFACTS` set, one guest at a time; probe scripts in `scripts/` beside this file):
  - the 34 sdists' SHA-256 against `sdists.txt`: 34 ok; the 8 tag archives' against `tag-archives.txt`: equal; `downloads/{pyyaml-6.0.3,markupsafe-3.0.4,networkx-3.7}.tar.gz` against wave 08's `SHA256SUMS`: equal;
  - every `.py` each tag-archive package's pinned wheel installs (outside `.data/`) against the tag archive (`scripts/tie.py`): cycler 1/1, openpyxl 190/190, xlsxwriter 42/42, et-xmlfile 3/3, cloudpickle 3/3, threadpoolctl 1/1, tomli-w 2/2, xlrd 10/10 same, 0 differ, 0 absent;
  - `uv run wasi-python run --grant /p=<scripts> -- /p/probe_doctest.py`: the stdlib's `DocTestFinder` on product modules (bytecode in the zip) finds `more_itertools.more` 114 doctests / 588 examples, `more_itertools.recipes` 51/140, `tabulate` 16/97, `mpmath.functions.functions` 18/184, `fontTools.misc.arrayTools` 3/41, `typing_extensions` 1/2; `patsy.desc` exposes 6 inline `test_*` functions; exit 0;
  - `… -- /p/probe_run.py`: `doctest.testmod(more_itertools.recipes)` attempted 140, failed 0; `doctest.testmod(tabulate)` attempted 97, failed 0; patsy's inline tests need `pytest` (the kit), as expected;
  - `… --fuel 3000000000000 -- /p/probe_import.py`: `import sympy` 4,225,459,488 fuel;
  - `… --fuel 3000000000000 -- /p/probe_sympy.py test_arit.py` (sympy 1.14.0's `core/tests/test_arit.py`, its plain functions called without pytest): 102 run, 100 ok, 165,383,002,004 fuel;
  - `… --deadline-s 900 --fuel 3000000000000 -- /p/probe_sympy.py test_simplify.py`: 67 run, 64 ok, 2,761,683,344,233 fuel; the same without its one `@slow` test, `test_issue_17141_slow` (`probe_sympy2.py`): 66 run, 63 ok, 152,447,072,941 fuel. Without pytest, sympy's `@slow` decorator runs the test (`sympy/testing/pytest.py:188`), so that one test cost about 2,609 G alone;
  - `gh run view 39451333969 --json jobs`: 43 jobs (40 ran, 3 publish jobs skipped); at 16:09:22Z, 35 judge and verify legs and one rebuild ran at once, 23 of them Linux judge legs.
- **Time box:** 45 minutes (a build-class specification). The guest probes took their own run time on top of that.

## What holds (READ unless labelled)

- **The versions are the shipped ones.** All 37 test sources name the version of the set's pin (wave 08's `SHA256SUMS`: 34 wheels, plus the `pyyaml-6.0.3`, `markupsafe-3.0.4` and `networkx-3.7` sdists). Each of the eight tag archives holds exactly the wheel's `.py` files (EXECUTED above). Each sdist's hash matches PyPI's (EXECUTED).
- **The pins' form fits the project.** `scripts/assemble_artifacts.py` writes a `pin` line for every `SHA256SUMS` line except `RESEARCH_PINS`, host-only wheels included. So 34 more lines in `MANIFEST` match how `MANIFEST` already lists inputs that a build on another host never fetches. A `tests()` function beside `research()` in `00_download.sh` follows the existing pattern.
- **Downloads stay data on the host.** Archives are read with `tar` and `zipfile`; tests run only in the guest (§4.8). The wheel tie (Decision 4) is the right tie for wheel-built packages: `upstream.tie_errors` ties a tarball named by `TARBALL[package]` to a `MANIFEST` pin, which a wheel-built package's test source is not. So a new tie is needed, and the draft says so.
- **Tag archives are necessary for eight packages.** Their PyPI sdists carry no tests. The forge-regeneration risk is stated, and a changed archive fails red and by name.
- **The kit order** (the kit appended after the zip) means each product module tests itself. The kit's `packaging` is the product's pin.

## Findings, most severe first

### H1 — The selection leaves tests out for convenience, against the owner's rule; two stated reasons are false

The owner's rule (decisions.md, 2026-10-20): "Every upstream test of a package we build runs in the release … The rule against leaving tests out for convenience stands, unamended." 066 applied it by turning on contourpy's `--runslow` and `--runtext` (066 Decision 7; its build review, L2) and by running lxml's docstring doctests from product modules (066 Decision 7, `docstring_modules`). 067 does neither. It also drops whole data-driven suites.

1. **Upstream's slow and opt-in tests are deselected** (READ):
   - sympy: `-m "not slow and not tooslow"` (`pyproject.toml:3`). 185 `@slow` lines and 14 `@tooslow` lines across `sympy/`.
   - networkx: `--runslow` left off (9 `mark.slow`). networkx's own `test-slow` task runs them (`pyproject.toml:359`).
   - narwhals: `--runslow` (its conftest) is not mentioned (24 `mark.slow`).
   - packaging: `-m "not property"` (14 hypothesis property tests, "opt-in").
2. **Doctests and in-library tests: the stated reason is false** (EXECUTED). Decision 8 says pytest reads doctests from source files, and the product's modules are bytecode. But the stdlib's `DocTestFinder` finds the docstrings of the zip's modules by import, and they pass: `more_itertools.recipes` 140 examples, 0 failed; `tabulate` 97, 0 failed. toolz's own `test_curried_doctests.py` already does this (`doctest.testmod(toolz)`), and 066 built the mechanism (`docstring_modules`). So doctests are not a reason to leave tests out. The draft also misses packages whose upstream runs doctests:
   - networkx: `--doctest-modules` in every test task (`pyproject.toml:356-357`); 5,181 `>>>` lines outside its tests;
   - tabulate: `pytest --doctest-modules` (`tox.ini:23`);
   - more-itertools and typing-extensions: upstream runs `unittest`. Their `load_tests` functions add `DocTestSuite('more_itertools.more')`, `('more_itertools.recipes')` and `(typing_extensions)`. pytest ignores `load_tests`. This is 066's lxml H1 again: pytest's selection is not upstream's runner's;
   - fonttools (955 `>>>` lines), joblib (53, plus `--doctest-glob='doc/*.rst'`; `doc/` is in the sdist), mpmath (3,937), sympy (32,046, plus 103 `doc/src` files with examples; `testpaths` names `doc/src`): Decision 8 lists these, for the false reason.
   - patsy: `python_files = *.py`, `testpaths = patsy` (`setup.cfg:8-9`). 109 inline `test_*` functions in 18 library modules, against 39 in its six `test_*.py` files. They are importable from the product (`patsy.desc` has 6; EXECUTED).
3. **Upstream test paths not staged** (READ):
   - pyparsing: upstream runs `pytest tests examples/tiny/tests` (`tox.ini`, `unit:`). The draft stages `examples/` as support only.
   - python-dateutil: upstream runs pytest on `tests` and `docs` with `python_files = … *_solution.py` (`tox.ini:32`, `setup.cfg`). That selects `docs/exercises/solutions/mlk_day_rrule_solution.py`.
4. **html5lib's data-driven suite is dropped with `--noconftest`.** The conftest builds the tree-construction, tokenizer and sanitizer items from `testdata/`, which is in the sdist: 1,617 `#data` cases in `tree-construction/*.dat` alone, each run per tree builder. It needs `pkg_resources` (setuptools), `pytest_expect` and `umsgpack`, and reads `.pytest.expect` (in the sdist root). These are test-only pure wheels, the same kind as freezegun. "Not in the product or kit" is a convenience, not a platform fact. The same goes for `test_meta.py`'s `mock`.
5. **fonttools' `check_table_coverage_test.py`: the stated reason is false.** The sdist ships `MetaTools/check_table_coverage.py` (`tar -tzf`, EXECUTED). The true reason exists. The script puts the source tree's `Lib/` first on `sys.path` and checks the repository's files (`Lib/…`, `Doc/source/…`). Run, it would import a copy of fontTools, not the product. It is a check of the repository, like 066's Pillow `check_release_notes.py`.
6. **Files that load are dropped for a judge fact or a test-only plugin:**
   - tqdm `tests_perf.py`: "the judge's clock is stepped" does not stop the file loading. Under 066's rule a file that loads is selected, and its failures are a class.
   - tqdm `tests_asyncio.py`: needs pytest-asyncio, a test-only plugin, so kit-extra.
   - jinja2 `test_async*.py`: trio is jinja2's runtime alternative, not the product's. The asyncio half of each parametrized case is lost with the file. The survey should try trio from kit-extra. If trio cannot import under WASI, that becomes the true written reason.
7. **pypdf's `samples` marker (33 uses).** The tests read py-pdf/sample-files, which pypdf's repository pins as a submodule at one commit. That commit's archive is a pinnable test source, like the eight tag archives. "Not in the sdist" is not a reason. `enable_socket` (318 uses) is a true reason: there is no network.

**Failure.** 067 lands, and the record claims each package's "own tests". But sympy's slow tests, every doctest of eight packages, patsy's inline tests, html5lib's data suite and pypdf's samples run nowhere. Marker deselections are not even counted: pytest's `-m` drops them silently, so `left_out` never names them (see L6). The owner's rule is broken with no line in the record.

**Fix text** (Decisions 5, 8, 9 and Scope):
> "Every test upstream's own runners select runs, opt-ins included, as 066 runs contourpy's `--runslow` (the owner, 2026-10-20). sympy runs without the `-m` deselection (its `slow` tests run; `tooslow` per the owner's answer to question Q1 below); networkx and narwhals run with `--runslow`; packaging with `-m property` removed. Doctests run as 066's lxml docstring items: the stdlib's `DocTestRunner` over the product's modules found by import, with each upstream's own option flags (fonttools, joblib, mpmath, sympy, networkx, tabulate; more-itertools and typing-extensions exactly as their `load_tests` add them). `docstring_modules` gains a package-walking form for packages with many modules (sympy, networkx, mpmath, fonttools). Doc-file doctests in the test source (joblib's `doc/*.rst`, sympy's `doc/src`) run as 066's lxml doctest files. patsy's inline `test_*` functions run as items called from the product's modules. pyparsing stages `examples/tiny/tests` as a group path; dateutil `docs/exercises/solutions/`. html5lib runs with its conftest; kit-extra adds setuptools (a release that still ships `pkg_resources`), pytest-expect, u-msgpack-python and mock; `.pytest.expect` is a support file. tqdm's `tests_perf.py` is selected and its failures are classed; pytest-asyncio joins kit-extra. trio is tried from kit-extra in the survey. pypdf's sample-files archive at the submodule's commit is a test source with its own pin, or the survey states why it cannot be. A file is not selected only when it cannot load, or every test in it needs what the product does not have (066 Decision 8's rule). fonttools' `check_table_coverage_test.py` gets its true reason."

### H2 — The budget contradicts the owner's decision, and its fuel rate is 30 to 140 times too low for sympy

1. **A fixed budget, and sympy groups dropped to fit it.** Decision 10 fixes "067's budget: 3×10¹²" and "sympy's budget: 1.2×10¹²". A sympy group that does not fit becomes `not_selected` with "fuel: past 067's sympy budget". The owner chose the opposite on 2026-10-20: "Caps follow the same rule (1.5 times measured fuel, each family's budget the sum of its caps) … A group too big for one shard is split into groups by construction … never left out." 066 Decision 11: "no total is fixed in advance". "The owner's choices" offers "sympy's share" as a default to move. It is not open: it is answered.
2. **The fuel rate.** The draft infers 16 to 48 M per pass, the rate of numpy's, pandas' and CPython's quick tests. Measured in the guest (EXECUTED, above), sympy costs:
   - about 1.58 G per test in `test_arit.py` ((165.4 − 4.2) G / 102);
   - about 2.25 G per test in `test_simplify.py` without its slow test.

   At that rate, sympy's roughly 12,500 fast tests are about 20 to 28 T (INFERRED from two modules), against the draft's 0.75 to 2.7 T. That is on top of the slow tests, the doctests (H1) and 066's 10 T.
3. **One test past every bound.** `test_issue_17141_slow` alone cost about 2.61 T. That is 5.4 times the 480 G group bound and 3.6 times 066's 725 G shard packing. At 0.16 to 0.31 s per G it is about 420 to 810 s of Linux job time, past the 360 s bound. One test cannot be split with `-k`. 066's rules have no case for it. A single test like this is the owner's to rule on (Q1).

**Failure.** The builder follows Decision 10 and the survey finds sympy at 25 T or more. Then either most of sympy is "not_selected" with a fuel reason the owner refused, or the caps follow the rule and the release gains 30 or more shards that nobody priced. Either way, the owner has not seen the price.

**Fix text** (Decision 10, criterion 6, "The owner's choices"):
> "Each group carries `measured = <fuel>` from the survey on main's set. Its cap is at most 1.5 times that, rounded up to two figures (066's `rule_cap`). Each family's budget is the sum of its caps. No total is fixed. A group past 480 G is split by file, in the test source's order. A file past 480 G is a `[[split]]` of constructed `-k` expressions (066 Decision 11). A single test past the shard bound follows the owner's answer to Q1. The survey's price (total fuel, number of shards, the lane's added acceptance time) goes to the owner with the confirmation round, before any group is built, as 066's re-survey price did."

Delete the sympy order-of-keeping paragraph, the 3×10¹² and 1.2×10¹² budgets, and "sympy's share" under "The owner's choices".

### H3 — seaborn and reportlab already close with spec 067, and the draft leaves them out

`tests/upstream/packages.toml` at `66cc120` (wave 08: spec 042 on main) has `[package.seaborn]` and `[package.reportlab]`, both `kind = "later"`, `closes_with = "spec 067"` (READ). The draft's Scope puts "042's seaborn and reportlab" out ("each specification that adds a package adds its suite"). But 042 did not add its suite: it named 067. Criterion 10 then fails on 067's own tree: "a unit check fails if any entry names spec 067". If the check were relaxed, two entries would name a landed specification, which `shards.package_errors` refuses (it accepts only a reserved number).

**Fix text** (Problem, Decision 2, Decision 3, Scope, criteria 10 and 11):
> "067 covers 39 packages: the 37 above, plus seaborn (its pinned sdist `seaborn-0.13.2.tar.gz` carries `tests/`; 050's tie, as for networkx) and reportlab (its `reportlab-5.0.1` sdist pinned as a test source, 35 pins in all; the wheel tie). Each is surveyed with the rest. After 067, no entry of `packages.toml` names spec 067."

The pin count, the `MANIFEST` line count (criterion 9) and the flags change to match.

### M1 — Every place the draft still assumes 066's older design

Each item is a fix to write in. Several would make a 067 TOML fail 066's rules check as it now stands (`tests/harness/packages.py` at `66cc120`).

1. **Keys.** The draft uses `path_packages` "as a map", `sys_path` and `support` (Depends on; Decision 2's "found by" column; Decision 5). 066 renamed them `package_paths`, `extra_sys_path`, `support_packages` and `support_files`. Its rules refuse `path_packages` and `support` in a package TOML (`REFUSED`; "a package TOML may not carry …"). 066 also requires `stage_folders`, and `cwd` is `"/tmp/work"` or `"tree"`. Fix: rename every key, add `stage_folders` per family, and write `cwd = "tree"` where the draft says "tree root".
2. **`measured`.** Every group needs `measured = <fuel>`, and a group without one is refused (066 build review M3). Decisions 10 and 13 do not name it. Fix: as H2's text.
3. **Splits.** The draft has no `[[split]]`. Its Decision 1 sends "a group past Decision 10's bound" back to the lane, where 066 splits by construction. 066 compares a split's collected counts only within one judge process; across shards, the lane reads the `collected` facts (066 confirming review, L3). Fix: "a file past 480 G is a `[[split]]` (066 Decision 11); its `collected` facts are compared within one judge process and read by the lane across shards".
4. **Shards and width.** The draft says "three Linux shards" and "With 066's three, 27 jobs start together against 20 slots". 066 has fourteen Linux shards. Run 124 had 43 jobs, 36 at once at 16:09:22Z (EXECUTED, `gh run view`). 066 packs at most 725 G a shard. The draft's `upstream-pure-a` (0.3 to 1.0 T) and `-sympy` (up to 0.8 T) pass that even on its own numbers. Fix: see M2.
5. **The survey's confirmation round.** 066 Decision 1 (its review, M1): the survey's dated delta always goes to a fresh reviewer, and building starts on that verdict. The draft sends only three findings. Fix: "the survey's delta to Decisions 2, 8, 9, 10 and 11 always goes to a confirmation round; building starts on its verdict".
6. **Fuel repeats.** 066's criterion 5 restages between the two runs (its review, N1). The draft's criterion 7 runs "twice in one judge session". Fix: copy 066's criterion 5.
7. **The base.** The draft says it is "stacked on 066", surveyed "on the frozen set of 066's tip", and committed on 066's branch. Its branch tip `6ffda49` sits on `21dff9d`. 066 lands in wave 08; 067 builds after wave 09 (099, 100 and 101, decisions.md). 100 changes `numpy.linalg`, which networkx's, sympy's and patsy's tests reach. 101 changes the shard plan and the matrix. Fix: "built from main's tip after wave 09, on that set (042's seaborn and reportlab, 066, 099, 100, 101); no stacked build; the branch is recreated from main's tip".
8. **Self-referencing closers.** fonttools, jinja2, pyparsing, html5lib and tqdm close with `context/specifications/067-…` ("the same as fonttools'"). The doctests close with `context/roadmap.md` and "a later specification". 066's review L2: "A specification that names itself means never." Fix: a `README.md` fact, or a reserved number with its roadmap line. Most of these rows go away under H1.
9. **typing-extensions' layout.** Staging `src/` stages `src/typing_extensions.py`, the product's module. That breaks the draft's own rule ("the stage holds only the files the table names"). 066's rules require a group path under a stage folder, so the two test files cannot be `support_files` group paths without a rule change. Fix: "typing-extensions stages its two files as `support_files`, with `extra_sys_path = ["src"]`; the rules admit a group path that is a staged support file (one added rule, with its unit variant)".

### M2 — CI width and the lane's time are not stated against 066 and 101

101 (wave 09, landing before 067) puts `max-parallel: 20` on the judge matrices. It binds Linux's 24 legs and keeps one run at 38 or 39 jobs (101 Decision 9, READ). So 067's shards do not widen a run; they queue in the Linux matrix. The draft's arithmetic ("27 jobs … 20 slots", "0 to 1.5 minutes") predates both 066's fourteen shards and 101. With H2's rate, 067 may add 30 to 60 Linux shards at 725 G each (INFERRED). That is 54 to 84 Linux legs, 20 at a time: three to four rounds of two to six minutes. Linux could then end after macOS's last shard and become the critical path, which 101 exists to shorten. The lane's darwin acceptance runs every group at every landing. On 066's measured ~10 T plus today's 2.89 T, tens of T more is the largest cost in the pipeline, and the draft does not name it.

**Fix text** (Decision 11):
> "Shards are packed from the survey's measured fuel at most 725 G each (066 Decision 12). They join the Linux judge matrix under 101's `max-parallel: 20`, so they queue and do not widen a run. The survey's delta states the count of Linux legs (066's 14 plus 067's), the queue rounds, whether Linux still ends before macOS's last shard, and the lane's added acceptance fuel. If Linux would become the critical path, the delta says so, and the owner sees it with Q1."

### M3 — The order rules with 045, 095 and 101 are missing

- **045** (statsmodels, formulaic, interface-meta, wrapt) is in 0.1.0 beside 067, with no order between them (decisions.md). formulaic, interface-meta and wrapt are pure-Python, 067's kind. 066 Decision 13 gives statsmodels to 095 "if 045 adds an entry". Fix: "formulaic, interface-meta and wrapt close with spec 067; statsmodels with 095. If 045 lands before 067 is built, 067 takes the three (their sdists or tags pinned as test sources, as above). If after, 045 adds their suites or names a reserved closer the lane writes."
- **095** (scipy's, scikit-learn's and statsmodels' tests) will add families and shards, and may need test-only wheels. Fix: "`tests/upstream/kit-extra.txt` and the `kit_extra` key are shared: whichever of 067 and 095 lands second rebases onto the first's file and rules, and no family's extras stage into another's".
- **101**: textual conflicts in `release_shards.toml`, `release.yml` and gather's `env:`. 101's key hashes `downloads/SHA256SUMS` and every tracked file under `scripts/` (101 Decision 2), so 067's pins invalidate it once (see L4). Fix: name 101 under "In flight" with that order: 067 rebases onto 101.

### M4 — The new writable grant duplicates 066's `/tmp/work` and invites host litter into the record

Decision 7 gives XlsxWriter a fresh writable copy of its stage, granted as a second preopen and diffed after the session. A new file is "listed in the record's facts". 066 tried a writable copy for Pillow, and host `.DS_Store` voided it twice (066 delta review L5; confirmation C1). On darwin, a `.DS_Store` would appear as a new fact and make records differ between runs. 066 already has the mechanism for this: `cwd = "/tmp/work"` with `cwd_files` written into the guest's root (lxml's three files), under spec 089's named `HostLitter` guard. The comparison tests need `xlsxwriter/test/comparison/xlsx_files/` and `images/` beside the working folder: 1,023 files, 10.8 MB (EXECUTED, `tar -tvzf`). They write `_test_<name>` there and delete it.

**Fix text** (Decision 7, criterion 4):
> "XlsxWriter's family uses `cwd = "/tmp/work"` with `cwd_files` (066 Decision 14), extended to name member folders (`cwd_folders`, each a folder of the test source, copied in before the session; rule-checked as members). No second grant, no diff of a stage. Host litter is 089's named guard, as for lxml."

## Low

- **L1 — The wheel tie compares `.py` files only.** The zip also takes data files from wheels (tzdata's zone files above all). Fix: "the tie compares every file the zip takes from the wheel, `.py` or not, or names each data file it skips and why".
- **L2 — "pyyaml, markupsafe and networkx, built from their sdists with carried patches."** Only networkx carries a patch (`recipes/patches/networkx-3.7/0001-graph-atlas-from-a-zip.patch`, which also patches `test_atlas.py`). Fix the sentence. The stage is built after the patch (066's `stage()` and `tie_errors`).
- **L3 — Forge availability in every run.** `fetch.py --shard` will fetch from github.com and foss.heptapod.net in each release run's Linux shards. A forge outage turns a release run red for a reason unrelated to the change. Fix: name it beside the regeneration risk, with the mitigation chosen (curl's `--retry 3` as `00_download.sh` has, or a cache keyed by the SHA-256).
- **L4 — 101's key.** Every 067 pin line, and any later re-pin of a test source (a Heptapod regeneration, say), changes 101's set key and the set's `MANIFEST`. That forces a source build and a new set for no product change. Fix: say so in Decision 3 and criterion 9. The alternative, `RESEARCH_PINS`-style test pins kept out of `MANIFEST`, is weighed and refused there in one line.
- **L5 — The rule for optional modules is unwritten.** Fix (Decision 6): "A module the product could ship but does not (wcwidth for tabulate, railroad-diagrams for pyparsing) gives counted skips: the product lacks that feature. A test-only module (freezegun, pretend, tomli, pytest-expect, u-msgpack-python, setuptools for `pkg_resources`, mock, pytest-asyncio, pympler) joins kit-extra."
- **L6 — Marker deselections are invisible.** pytest's `-m` drops items silently, so `left_out` and the stream never name them. 066 had none. If any `-m` remains (pypdf's `not enable_socket`), fix: "the driver writes a `D <node id>` line per item a marker deselects, and the record carries their count with the reason".

## Notes

- **numpy and pandas still run `not slow`** (`numpy.toml:18`, `pandas.toml:10`, spec 050). The owner's rule names every package we build. That is outside 067; the lane may want a reserved follow-up or a line to the owner.
- The drafter's extracted `tagsrc/XlsxWriter-RELEASE_3.2.9` holds 14 of the 963 reference `.xlsx` files; the archive holds all of them (EXECUTED, `tar -tzf`). The builder unpacks from the pinned archive, so no finding, but no count should come from that extraction.
- The drafting evidence folder lives on 066's branch, not on 067's draft commit. It lands with 066, so 067's links resolve after wave 08.

## Acceptance criteria against the draft (pre-build: nothing is measured yet)

1. Pins — sound (READ); count becomes 35 with reportlab (H3).
2. Rules — must add `measured`, the renamed keys, `cwd_folders` and the support-file group path (M1, M4).
3. Tie — sound; widen to data files (L1).
4. Writable stage — replace (M4).
5. Survey — base and confirmation round (M1.5, M1.7).
6. Budgets — contradicts the owner (H2).
7. Fuel repeats — restage (M1.6).
8. Nothing else moves — sound.
9. Artifact set — sound; line counts follow H3; name 101's key (L4).
10. `packages.toml` — fails as drafted (H3).
11. Shards and fetch — follows M2.
12. Full judge — sound.
13. Dry runs — sound; the 360 s bound needs Q1's answer for any single test past it (H2.3).

## Constitution checks

- §4.2 pinned and hashed: holds; every test source is a URL plus a SHA-256 (EXECUTED for all 42).
- §4.6 the artifact set: `MANIFEST` changes by design; criterion 9 bounds it. Holds.
- §4.8 downloads untrusted: holds (data on the host, run only under wasmtime).
- §4.9 tests count: holds; no check reads a clock.
- §4.10 claims labelled: holds in form, but Decision 10's INFERRED rate is contradicted by measurement (H2).
- §5.2 no open questions: the sympy-share "default the owner may move" is an answered question restated as open (H2). Q1 below is new and needs the owner.
- §7: nothing tripped. The draft changes no guest import or export.

## Question only the owner can answer

**Q1 — sympy under "every test".**
- (a) One test past every bound: `test_issue_17141_slow` costs about 2.61 T (EXECUTED), about 7 to 14 minutes of Linux job time, and cannot be split. Options:
  - give such a test a shard of its own, past the 360 s bound (recommended);
  - run it on the lane only, outside the release shards;
  - amend the rule to leave it out.
- (b) sympy's 14 `@tooslow` tests are never run by sympy's own runner (its `tooslow` decorator skips them, `sympy/testing/pytest.py:198`). Run them anyway, as "every test", or treat upstream's own permanent skip as upstream's selection?
- (c) The price: sympy alone is likely 20 to 28 T for its fast tests (INFERRED from two modules), plus slow tests and doctests, against 066's 10 T. The review recommends the survey measure it, and the lane put the measured total, the shard count and the lane's added time to the owner with the confirmation round, as it did for 066.

## Verdict

**Build once H1 to H3 and M1 to M4 are written in, the survey has run on main's set after wave 09 with its delta confirmed, and the owner has answered Q1.** The Lows need only their fix text.

One line: 067 has the right pins and the right tie, but as drafted it would leave out what the owner said must run, on a budget the owner refused and a fuel rate sympy breaks by two orders of magnitude.
