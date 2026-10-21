# 095 — scipy's, scikit-learn's and statsmodels' own tests in the release

- **Status:** **drafted 2026-10-20** on `spec/095-scipy-sklearn-statsmodels-own-tests` from main
  `dda6075` (the lane's handoff; the structural chain 103 to 111, tip `dbecd2d`, is not under it:
  the branch was made from main, and moving it onto the chain's tip was refused by the session's
  permissions; this draft touches only `context/`, so the rebase is the lane's or the builder's,
  with no conflict expected). **Not yet surveyed** (Decision 1): the drafting probes below are
  calibration, not the survey. **Awaiting its pre-build review**: it changes what the release
  judges and adds a stage-time guest run (Decision 5), so the lane asks for one, as it did for 066.
- **Owner:** Clay Gendron
- **Kind:** the judge and the release workflow. No line of `src/`, `scripts/`, `recipes/` or
  `downloads/SHA256SUMS` changes: scipy's and scikit-learn's sdists are main's pins (037, 044),
  statsmodels' is 045's, and all three are recorded in `MANIFEST`. No artifact byte changes. It
  touches the release workflow (new Linux shards), so it is build-class by AGENTS.md's definition.
  - **New:**
    - `tests/upstream/{scipy,scikit-learn,statsmodels}.toml` and `.ini` (Decisions 2, 6);
    - `tests/upstream/expected/<group>/<class>.txt`, the class lists the survey finds (Decision 9);
    - entries in `tests/known_gaps.toml`, one per class and per trap;
    - the survey memo, `context/research/2026-10-2x-scipy-sklearn-statsmodels-own-tests-under-the-runtime.md`
      (Decision 1).
  - **Changed:**
    - `tests/harness/packages.py`: three keys, `package_inits`, `derived` and `env` (Decisions 4, 5,
      7), their rules, and the stage-time guest run of Decision 5;
    - `tests/harness/upstream.py`: `PACKAGES` (or `PACKAGE_SUITES`, as main names it then) gains the
      three names;
    - `tests/checks/test_v1_3_upstream_suites.py`: the needs per family;
    - `tests/upstream/fetch.py`: `--shard` fetches the three trees for the shards that run them;
    - `tests/upstream/packages.toml`: scipy, scikit-learn and statsmodels become `suite`
      (Decision 13);
    - `tests/release_shards.toml`, `.github/workflows/release.yml`: the new Linux shards, normal and
      release tier (Decision 12);
    - `tests/unit/test_packages.py`, `test_shards.py`, `test_fetch_trees.py`;
    - `README.md`, `CHANGELOG.md`, `context/progress/README.md`, `context/roadmap.md`.
  - **Not changed:** `tests/upstream/package_drive.py` (Decision 3), `drive.py`, every TOML of 066,
    numpy's, pandas' and CPython's configurations.
- **Depends on:**
  - **066** (landed, wave 08): `package_drive.py`, one family per package, its keys
    (`stage_folders`, `package_paths`, `extra_sys_path`, `support_files`, `cwd`, `cwd_files`,
    `[[split]]`, `measured`), the path-based guard, the cap rule and the rules check. 095 adds
    three keys; it changes no meaning of 066's and no family of 066's.
  - **102** (the release tier; drafted, `spec/102-the-release-tier` at `9460d14`): its `tier`,
    `release_marker`, `[[release_select]]` and release shards. 102's Decision 15 says 095 "applies
    Decision 2 to scipy, scikit-learn and statsmodels and packs its release groups into release
    shards". 095 is built after 102 lands, or stacked on 102's reviewed tip (§4.14) if 102 is
    reviewed and waiting for a wave. 095 adds no tier mechanism of its own.
  - **045** (statsmodels; built natively on `spec/045-statsmodels` at `27205a5`, set `f2a3e87d`,
    not yet judged or build-reviewed): statsmodels' family needs 045's set and pin. The roadmap
    orders 045 before 095 (wave 09, then 045, 102, 095, 067). So:
    - **By default 095 is built on main after 045 and 102 land.** Nothing is stacked.
    - **If 045 is build-reviewed but not landed** when 095's survey is due, statsmodels' part is
      surveyed on 045's set and 095 is a stacked build on 045's reviewed tip (§4.14), naming the
      base commit.
    - **If 045 is not build-reviewed by then, statsmodels' part splits off.** 095 is built for scipy
      and scikit-learn alone; `packages.toml` keeps statsmodels `later` with the closer the lane
      reserves for the split (a new number in the roadmap's `Reserved:` paragraph, since
      `shards.package_errors` accepts only a reserved number); that specification is this one's
      statsmodels sections, unchanged, built once 045 lands. No test is left out by the split:
      statsmodels' suite still closes, later.
  - **Wave 09** (100, 101, 097): 100 moves numpy's linear algebra to OpenBLAS (scipy's and
    scikit-learn's tests reach it); 101 changes the shard plan and the Linux matrix's
    `max-parallel`; 097 widens the judge's staging (its `test_elementsoup.py` is the same pytest
    naming question Decision 4 answers with `package_inits`: whichever of 097 and 095 lands second
    uses the first's key if it covers this case). 095 is surveyed on main's set after wave 09.
  - **088** (reserved: the judge-only binary, never published, linked with numpy's and CPython's
    C test modules): the closer this specification names for scipy's seven test-only C modules
    (Decision 8). The lane widens 088's roadmap line to name them, or the owner rules otherwise.
  - **067** (the pure-Python packages' own tests; drafted): shares `kit-extra.txt` and the
    `kit_extra` key if either needs one. 095 needs no extra wheel (Decision 6); if the survey
    finds one, whichever of 067 and 095 lands second rebases onto the first's file and rules.
  - **074** (reserved: the `ctypes` and `mmap` stand-ins' names at import): it may turn three of
    scipy's not-selected files into loaded files with a class each (Decision 8).
  - **109** (the structural chain: comments outside `src/` give their reasons in words, no
    document cited): every comment 095 writes in `tests/` follows it; `closes_with` values are
    data and keep their form.
  - **063**, **065**, **050**, **051**, **089**, **091**, **052**, **002**, as 066 lists them.
- **Research it stands on:**
  - 066's survey and build (`../research/2026-10-20-the-compiled-packages-own-tests-under-the-runtime.md`
    and 066's Landing notes): the family mechanism, measured; 050's and 065's memos as 066 cites
    them.
  - 037, 038, 044 and 045 (what each package carries, what is absent by the sandbox, and why).
  - The owner's rules of 2026-10-20 (`decisions.md`): "Every test of every package we build";
    statsmodels' suite to 095; two tiers of tests (102's answers: "we can decide what is slow
    tier but do not exclude anything from the full suite").
  - **Read and probed while drafting (2026-10-20)**, in
    `../research/2026-10-20-scipy-sklearn-statsmodels-own-tests-drafting/` (its `README.txt` says
    how each file was made):
    - the three sdists, each SHA-256 recomputed equal to its pin and read as text
      (`*-inventory.txt`, `*-risks.txt`, READ);
    - **guest probes** (EXECUTED, darwin-arm64, the snapshot binary through the judge's own
      embedder, on main's set rebuilt in the main tree from the chain's tip, one process at a
      time; `probes.txt`): a collection of scipy's whole suite, of its slow tier, of
      scikit-learn's whole suite, and one sample run of each. statsmodels was not probed: its
      set is 045's, not main's.

    Every number of outcome or fuel below not marked EXECUTED is INFERRED until the survey
    measures it.

## The problem

Spec 063's rule is that every package runs its own tests in the release; the owner's rule is that
every upstream test of a package we build runs, in one tier or the other, never left out for
convenience. Three compiled packages do not yet: scipy (037, 038), scikit-learn (044) and
statsmodels (045). `tests/upstream/packages.toml` marks scipy and scikit-learn `later`, closed by
spec 095; 045 does the same for statsmodels. OpenBLAS is `via scipy`, so while scipy's suite does
not run, the C LAPACK every one of them calls has no suite that runs either.

These are the product's heaviest packages. scipy alone is about 85 linked extension modules, a C
LAPACK made `void` by a carried patch, f2py wrappers called through function pointers, HiGHS,
Boost.Math, ducc0, qhull, SuperLU and ARPACK. Each was compiled for `wasm32-wasip1` by this
project's recipe, with no Fortran, no threads and a 32-bit `intp`. Their golden jobs prove a fit, a
solve and a filter. Their own suites, about 164,000 tests in all (96,100 and 46,955 collected
in the guest, EXECUTED below; statsmodels' 21,412 collected natively by 045's builder), prove the
rest: a wrong cast, a callback of the wrong type, a LAPACK path that differs at
1e-14, a 32-bit overflow in an index.

This specification makes the three suites judge jobs and release gates, as 066 did for the plot
and XML packages: a ratcheted pass count and fuel per group; every known failure a class, listed by
test id, with its reason and closer; every test not run named, with its reason; the normal tier in
Linux shards on every release run and on the lane's darwin judge at every landing; the release tier
where 102 runs it.

## What the drafting probes found (EXECUTED; calibration, not the survey)

| probe | selection | fuel | outcome |
|---|---|---|---|
| scipy, collect only | the whole staged suite | 286.5 G | 96,100 collected; 11 files fail to load (Decision 8) |
| scipy, collect only | `-m "slow or xslow"` | 293.3 G | 15,174 selected, 80,926 deselected |
| scipy, sample run | ten files, `-m "not slow and not xslow"` | 326.6 G | 5,182 outcomes: 4,861 passed, 301 skipped, 9 xfailed, 1 xpassed, 10 failed; 63.0 M a test |
| scikit-learn, collect only | the whole staged suite | 240.2 G | 46,955 collected; 2 files fail to load |
| scikit-learn, sample run | seven files, `SKLEARN_RUN_FLOAT32_TESTS=1` | 1,876.1 G | 4,222 outcomes: 3,249 passed, 877 skipped, 55 xfailed, 41 failed; 444 M a test, seven times scipy's |

- **The ten failures of scipy's sample are two classes**, both the platform's: nine
  `RuntimeError: can't start new thread` (`test_kdtree.py`'s multithreaded queries,
  `test_bsplines.py`'s concurrency tests) and one `AttributeError: module 'threading' has no
  attribute 'get_native_id'` (`TestBSpline::test_memmap`). No trap. The one xpass is
  `test_elliprj_hard`, marked "Insufficient accuracy on 32-bit": an `xfail_on_32bit` case that
  passes here.
- **scikit-learn's sample: one class, and the price.** All 41 failures are `OSError: mmap is
  unavailable on wasm32-wasi` (memory-mapped test data); 292 float32 cases ran; no trap. At 444 M
  a test it is seven times scipy's per test, and one session of seven files is 1.9 T, four times
  the 480 G bound: scikit-learn decides most of this specification's price.
- **Without `package_inits`** (Decision 4), 31 of scipy's files failed to load, 20 of them on
  pytest naming two different `tests` packages alike (`tests.test_basic` from
  `fft/_duccfft/tests` and from `linalg/tests`), and collection found 64,614 tests, not 96,100.
- **scipy's `filterwarnings = error`** made the session stop at configure until the `.ini` gained
  one `ignore` line (Decision 6).
- **scikit-learn's marker `no_check_spmatrix`** is registered nowhere in the sdist; under
  `--strict-markers` four files, `tests/test_common.py` among them, failed to collect until the
  `.ini` registered it (Decision 6). With it, collection found 46,955 tests, not 33,213.
- **The guard held:** in every probe the only module loaded from the stage outside a `tests`
  folder was the package's own `conftest.py` (`M scipy.conftest`), a staged support file; no
  staged `__init__.py` was imported.

## Decisions

1. **The survey comes first, as research; a confirmation round always follows** (066's
   Decision 1, unchanged in method).
   - **A research step, time-boxed at 4 hours of wall clock**, before any check, TOML or harness
     line is committed. It uses a stand-in driver setup kept in a scratch copy (the drafting
     probe, `probe095.py`, is its start), this specification's staging (Decisions 4 and 5), keys,
     working folder and selection (Decisions 6 to 8), the judge's own embedder, on a private copy
     of the frozen set, one guest session per group, at most three at once, never while
     `build/lane.lock` exists.
   - **Its sets:** scipy and scikit-learn on main's set after wave 09; statsmodels on main's set
     after 045 lands, or on 045's reviewed set if Depends on's stacked path applies.
   - **It records** each group's outcomes by node id, its fuel, every trap and every collection
     error, both tiers (the release tier once, on darwin), and sorts the failures into classes by
     their one-line reasons.
   - **It is written up** as the memo, labelled EXECUTED, with the scripts and raw streams beside
     it; its dated delta to Decisions 8, 9, 11 and 12 goes to a fresh reviewer as a context-only
     delta review. Building starts on that verdict, never before.
   - **The box, estimated** (INFERRED from the probes' rate on darwin-arm64, about 0.2 to 0.3 s
     per G of fuel; the samples ran at about 0.18): the normal tier of the three about 15 to 35 T,
     45 to 175 minutes of guest time in one process; the release tier about 4 to 12 T more. With
     three sessions at once, about 1.5 to 3 hours of wall clock, and about 2 to 4.5 CPU hours.
     The builder's repeat runs
     (criterion 5) cost the normal tier once more.

2. **One family per package: its own grant, stage, kit copy and budget** (066, Decision 2).
   - `scipy`, grant `/upstream-scipy`; `scikit-learn`, grant `/upstream-scikit-learn` (the
     distribution's name, as `packages.toml` names it; the import name `sklearn` is in
     `package_paths`); `statsmodels`, grant `/upstream-statsmodels`.
   - **Why three and not one:** a package moves only its own rows, a shard fetches only the trees
     it runs, and statsmodels' part can split off (Depends on) without touching the other two.
   - **The budget:** each family's caps sum to at most its budget, written in its TOML, by the
     cap rule (Decision 11).

3. **The driver is 066's, byte for byte.** `package_drive.py` is not edited: an edit would change
   the bytes every 066 family stages and could move their fuel. What 095 needs beyond it is done
   on the host: the environment of Decision 7 is passed to `guest.run` by the harness, the files of
   Decision 5 are staged by the harness. A rules check hashes the staged driver against main's
   (criterion 6).

4. **Where the tests come from: the pinned sdists, members only, tied to the artifact; and each
   test folder's ancestor `__init__.py`.**
   - **The staged folders** mirror the sdist's own paths under `/upstream-<package>/tree/`, so node
     ids are the sdist's (`scipy/linalg/tests/test_basic.py::…`):

     | package | tarball (pinned) | staged (READ; probes EXECUTED) | size |
     |---|---|---|---|
     | scipy | `scipy-1.18.1.tar.gz` (037) | every top-level `scipy/**/tests/` folder (33 folders, 340 test modules, their data: 477 non-Python files, 22.6 MB), but `odr/tests` (Decision 8); `scipy/conftest.py` | 899 files, 32 MB |
     | scikit-learn | `scikit_learn-1.9.1.tar.gz` (044) | every top-level `sklearn/**/tests/` folder (36 folders, 259 test modules, 83 data files); `sklearn/conftest.py`, `sklearn/externals/conftest.py` | 439 files, 6.5 MB |
     | statsmodels | `statsmodels-0.15.0.tar.gz` (045) | every top-level `statsmodels/**/tests/` folder (50 folders, 291 test modules, their `results/`: 482 non-Python files, 9.6 MB); `statsmodels/conftest.py` | about 940 files, 18 MB |

     The product's zip leaves out every `tests/` folder (step 70) and must keep doing so; none of
     these is in it. A tests folder nested inside another (`scipy/linalg/tests/_cython_examples/…`)
     comes with its parent.
   - **`package_inits = true` (a new key).** The stage also holds the `__init__.py` of each
     staged folder's ancestor packages, from the same tarball (`scipy/__init__.py`,
     `scipy/linalg/__init__.py`, `scipy/sparse/linalg/_dsolve/__init__.py`, …), as support files.
     **Why:** under `--import-mode=importlib`, pytest names a test module from the nearest folder
     without `__init__.py`. With only the `tests` folders staged, every `tests` folder's parent
     lacks one, so pytest names `scipy/linalg/tests/test_basic.py` `tests.test_basic`, the same
     name as `scipy/fft/_duccfft/tests/test_basic.py`'s. The drafting probe saw 20 files fail on
     that clash and on relative imports beyond `tests` (EXECUTED). With the inits staged, pytest
     names it `scipy.linalg.tests.test_basic` and imports it through the standard machinery:
     `scipy` and `scipy.linalg` come from the zip (first on each `__path__`), and `tests` from the
     grant through `package_paths`. **They are never imported:** the product's package is found
     first. The guard proves it on every run: a module loaded from a staged `__init__.py` is an
     (a) `M` line outside a test folder, a finding (066, Decision 5). The probes saw none.
   - **`package_paths`** maps the package and every ancestor of a staged folder to its folder
     (`{"scipy" = "scipy", "scipy.linalg" = "scipy/linalg", …}`), generated by the harness from
     `stage_folders` when `package_inits` is true and checked by the rules against the tarball, so
     the TOML does not list some 35 entries by hand (EXECUTED: the probe staged 35 ancestor
     `__init__.py` files for scipy's 33 folders). A package the product lacks (`scipy.odr`, a
     stand-in module, not a package) is never in it.
   - **The tie** (`tie_errors`) fails a group, never blocks it, when the tarball or a patch is not
     what `MANIFEST` records. scipy carries four patches (`recipes/patches/scipy-1.18.1/0001` to
     `0004`: uarray's callbacks, `sqrtm`'s import, matrix market without threads, Sobol without a
     temporary file) and statsmodels one (045's `0001`, two files under `datasets/`); none
     touches a staged file (READ: each patch's `+++` lines), and the stage is made from the
     patched tree, as 066's are.
   - **A new CI input** per family: each tarball is fetched by `fetch.py --shard` for the shards
     that run its groups (scipy's 30.8 MB, scikit-learn's 7.8 MB, statsmodels' as 045 pins it),
     verified against `downloads/SHA256SUMS`, unpacked with the `data` filter, patched, never run
     outside the guest. The next release's threat-model review sees them (§5.6).

5. **scipy's generated test data, made in the guest from members (a new key, `derived`).**
   scipy's build turns three folders of text tables into `scipy/special/tests/data/boost.npz`,
   `gsl.npz` and `local.npz` with its own `scipy/special/utils/makenpz.py`, and installs them with
   the tag `tests` (READ: `scipy/special/meson.build:216-249`). The product's build installs no
   `tests` file, and the sdist carries only the text. Without them `special/tests/test_data.py`
   fails to load (EXECUTED: `FileNotFoundError` for `boost.npz`).
   - **Made in the guest, never on the host.** A download runs only as a build tool under the
     build's control or as a guest (§4.8). So before the family's first group, the harness runs
     `makenpz.py` from the stage in the snapshot binary (`python -u
     /upstream-scipy/tree/scipy/special/utils/makenpz.py <name> -o /tmp/derived`, once per
     name), with the stage read-only and a fresh writable root, and copies the three files it
     writes into the stage at `scipy/special/tests/data/` before sealing it (089).
   - **The key:** `derived = [{ script = "scipy/special/utils/makenpz.py", args = ["boost"],
     output = "scipy/special/tests/data/boost.npz" }, …]`. The rules check: the script and the
     inputs it reads are tarball members; each output's folder is a staged folder; no output is a
     member.
   - **Its record:** each output's SHA-256 and the run's fuel are facts of the family's first
     group (`derived`), not ratcheted metrics. A derived run that exits non-zero or traps fails
     every group of the family, named; it never blocks them.
   - **`makenpz.py` is staged** as a support file (with `scipy/special/utils/`), never imported by
     a test.
   - **Not in the product.** The three files exist only in the stage; the zip is unchanged.
   - The survey confirms that `makenpz.py` runs in the guest (it needs numpy and `os.walk`) and
     whether any other package's tests need a generated file (READ while drafting: scikit-learn's
     and statsmodels' meson files tag no file `tests`).

6. **Upstream's own configuration, transcribed; upstream's conftests used as they are.** The
   driver passes 066's options (`--import-mode=importlib`, `--strict-markers --strict-config`,
   `-p no:faulthandler`, `-p no:cacheprovider`, …) with each family's `.ini`.
   - **scipy**: its `pytest.ini` as the sdist has it (markers, `filterwarnings = error` and its
     list, `norecursedirs`, `addopts = -l`, `junit_family`), with **one line added**:
     `ignore:Module already imported so cannot be rewritten:pytest.PytestAssertRewriteWarning`.
     The driver imports `hypothesis` before pytest starts (to load the judge's profile), so pytest
     warns that it cannot rewrite it, and scipy's `error` filter makes that warning end the
     session at configure (EXECUTED: the first probe stopped there). The line names pytest's own
     message about the kit, not any scipy warning. Its `conftest.py` is used as is: it registers
     the optional plugins' markers itself when the plugins are absent (`pytest_run_parallel`,
     `pytest_timeout`, `pytest_fail_slow`, READ), skips `xslow` unless `SCIPY_XSLOW` is set, and
     xfails `xfail_on_32bit` cases on a 32-bit `intp`, which the guest has. `SCIPY_ARRAY_API` is
     unset (Decision 7).
   - **scikit-learn**: its `pyproject.toml`'s `[tool.pytest.ini_options]`, transcribed:
     `doctest_optionflags` and `addopts = --disable-pytest-warnings`. Not transcribed, each with
     its reason in the `.ini`: `testpaths` (the group names its paths), `--color=yes` (no
     terminal), `--import-mode=importlib` (the driver passes it), `faulthandler_timeout` and
     `faulthandler_exit_on_timeout` (the driver turns faulthandler off, so `--strict-config`
     refuses the keys), `thread_unsafe_fixtures` (pytest-run-parallel's key; refused without the
     plugin). **Registered:** the marker `no_check_spmatrix`, which its tests use and the sdist
     registers nowhere (upstream runs without `--strict-markers`; EXECUTED: four files failed to
     collect without it). Its `conftest.py` is used as is: it skips every doctest on a 32-bit
     platform, skips the `fetch_*` fixtures unless `SKLEARN_SKIP_NETWORK_TESTS=0`, and sets
     `threadpool_limits`.
   - **statsmodels**: its `[tool.pytest.ini_options]`, transcribed: `minversion`, `xfail_strict =
     true`, `empty_parameter_set_mark = fail_at_collect`, `filterwarnings` and `markers`. Not
     transcribed, each with its reason: `--durations=30` and `--junitxml=test-data.xml` (reports,
     not selection), `--randomly-dont-reset-seed` (pytest-randomly's option; the plugin is neither
     in the kit nor a dependency of the tests), `--strict` (the driver's `--strict-markers` is its
     current name). Its `conftest.py` is used as is: its `--skip-*` and `--only-*` options are all
     opt-outs, unset here, so every test runs, `slow`, `example`, `matplotlib`, `smoke`, `joblib`
     and `high_memory` included.
   - **The kit is 066's.** No extra wheel is needed (READ: every import of the three suites is the
     product's, the stdlib's, the kit's, or an optional one the tests skip without: `pooch`,
     `gmpy2`, `array_api_strict`, `polars`, `pyarrow`, `pytest_run_parallel`, `scipy_doctest`).
     The survey confirms it; a needed wheel would be a `kit_extra` line shared with 067.

7. **The two tiers (102): what upstream's own default command runs is the normal tier; what it
   runs only when asked is the release tier.** The rule is the project's choice (the owner,
   2026-10-20: "we can decide what is slow tier"), written per family with its evidence:
   - **scipy: release tier `slow or xslow`, by marker** (102's kind (a)). scipy's default test task
     is `spin test`; its separate task `test-xslow` runs `spin test -m full` with `SCIPY_XSLOW=1`
     ("Test SciPy (full and x-slow)"; READ: `pixi.toml:276-290`), so the default leaves both out
     (INFERRED from the task pair; `.spin/cmds.py` is not in the sdist). Normal groups:
     `marker = "not slow and not xslow"`; release groups: `release_marker = "slow or xslow"`, with
     `SCIPY_XSLOW=1` in the family's `env`. The variable changes only `xslow` tests' skip
     (`conftest.py:108-117`, READ), which normal groups deselect, so normal rows are the same with
     it or without it. EXECUTED counts: 80,926 normal, 15,174 release (10,347 of them in
     `signal/tests/test_signaltools.py`, 2,919 in `sparse/tests/test_64bit.py`).
   - **scikit-learn: everything normal.** It has no slow marker (READ). Its float32 cases are
     opt-in (`SKLEARN_RUN_FLOAT32_TESTS=1`, `conftest.py:88-91`): they run here, in the normal
     tier, with `env = { SKLEARN_RUN_FLOAT32_TESTS = "1" }`, because they are tests of the
     product's float32 paths and nothing marks them slow. If the survey finds their cost past the
     shard plan, the confirmation round may move them to the release tier with a
     `[[release_select]]` keyword entry (102's kind (b), `float32`), a reviewed judge change,
     never out.
   - **statsmodels: everything normal.** Its `slow` tests run by default (`--skip-slow` is an
     opt-out; READ), so they are normal by the rule. The same allowance as scikit-learn's float32
     applies to `slow` if the survey prices it past the plan.
   - **`env`, a new family key**, a map of variables the harness adds to the judge's `ENV` for that
     family's guest runs. The rules allow only listed names, each with its reason in the TOML:
     `SCIPY_XSLOW` (scipy), `SKLEARN_RUN_FLOAT32_TESTS` (scikit-learn). `TMPDIR` and `HOME` stay
     the judge's. A release group may carry the variable its tier needs; a normal group's argv and
     environment are the same on a normal run and on a release run (102, Decision 4).
   - **Modes, not tests: not run, and stated in the README.** Each runs the same tests again under
     another setting, adds no test, and has no default in upstream's own command:
     scikit-learn's `SKLEARN_TESTS_GLOBAL_RANDOM_SEED=all` (each seeded test on 100 seeds; the
     default seed 42 runs), `--check-spmatrix` (patches scipy.sparse to raise on old-style matrix
     use) and `SKLEARN_WARNINGS_AS_ERRORS`; scipy's `SCIPY_ARRAY_API=1` (the array-API backends:
     the product carries none but numpy, and the variable changes scipy's own import-time
     behaviour); statsmodels' `SM_TEST_COPY_ON_WRITE` and `SM_FORMULA_ENGINE=formulaic` (the
     formula tests with formulaic in place of patsy, the default). The owner may rule any of them
     a tier's (the report that carries this draft says so); each would be one more family or
     group with its `env`, no new mechanism.
   - **Doctests.** scikit-learn's conftest skips every doctest when the default numpy integer is 32
     bits (`conftest.py:197-199`, READ): collected, they would be counted skips only, and their
     source is not staged (the modules are the zip's bytecode), so they are not collected; the
     README says so. scipy's docstring examples are checked by a separate tool, `scipy-doctest`
     (`spin smoke-docs`), not by its test suite (READ: `conftest.py:28-32` imports it only when
     present), and statsmodels runs none: none is run.

8. **What is not selected, each with its reason and closer** (066, Decision 8's rule: a file is
   not selected only when it cannot load, or every test in it needs what the product lacks; a
   single failing test is a class member). From the probes (EXECUTED) and the reads (READ); the
   survey confirms each and the confirmation round sees every change.

   | package | files | reason | closes with |
   |---|---|---|---|
   | scipy | `_lib/tests/test_ccallback.py`, `integrate/tests/test_quadpack.py`, `ndimage/tests/test_c_api.py`, `special/tests/test_dd.py`, `special/tests/test_round.py` (EXECUTED: each fails to load) | each imports one of scipy's seven `tests`-tagged C modules (`_test_ccallback`, `_test_multivariate`, `_ctest`, `_cytest`, `_test_internal`), which 037 links out of the product on purpose (its Decision 8) | spec 088 (the judge-only binary; the lane widens its line to name scipy's seven) |
   | scipy | `_lib/tests/test_deprecation.py`'s tests that call `_test_deprecation_call` and `_test_deprecation_def` | the same, at call time: a class, not a file (it loads) | spec 088 |
   | scipy | `linalg/tests/test_cython_abi.py`, `optimize/tests/test_cython_abi.py`, `special/tests/test_cython_abi.py` (EXECUTED) | they read capsule names through `ctypes.pythonapi`, which the `ctypes` stand-in lacks, at import | spec 074 (the stand-ins' names at import); after it, each loads and its tests are a `no-ctypes` class |
   | scipy | `odr/tests/` (not staged) | `scipy.odr` is out of this line for good (037, Decision 9: ODRPACK is Fortran; scipy removes it in 1.19) | `context/specifications/037-scipy.md` |
   | scipy | `linalg/tests/_cython_examples/ilp64_test_package/tests/` (EXECUTED: fails to load) | an example package `test_extending.py` would build with meson in a subprocess; scipy installs only `extending.pyx` and `meson.build` of `_cython_examples` (READ: `linalg/tests/meson.build:39-43`), so it is not part of the installed suite | `README.md` |
   | scikit-learn | `cluster/tests/test_hierarchical.py`, `metrics/tests/test_dist_metrics.py` (EXECUTED) | they build memory-mapped arrays at import (`create_memmap_backed_data`), and the `mmap` stand-in raises | `README.md` (no `mmap`); spec 074 if it changes the stand-in |
   | scikit-learn | `neighbors/tests/test_neighbors.py` (EXECUTED, the sample) | it imports a constant from `metrics/tests/test_dist_metrics.py`, which cannot load. The whole-suite collection loaded it only because pytest had kept the half-imported module from an earlier file: an order the judge does not rely on | `README.md`; spec 074 as above |
   | statsmodels | none known (READ); the survey's first run says | | |

   Selected although they may skip whole: scipy's `datasets/tests/test_data.py` (`importorskip
   pooch`), scikit-learn's dataset fetcher tests (skipped without the network variable),
   statsmodels' `base/tests/test_polars_compat.py` (`importorskip polars`).

9. **Known failures are classes, by test id, each one gap** (066, Decision 9). Expected from the
   probes and the reads, each to be measured; members per class come with the survey:

   | class (per group) | match | evidence | closes with |
   |---|---|---|---|
   | `no-threads` | `can't start new thread` | 9 in scipy's sample (EXECUTED); 31 scipy, 10 scikit-learn and 3 statsmodels files name threads (READ) | `README.md` |
   | `no-native-id` | `has no attribute 'get_native_id'` | 1 in scipy's sample (EXECUTED) | `README.md` |
   | `no-processes` | `does not support processes` and the `multiprocessing` messages the survey records | `MapWrapper` pools, `differential_evolution(workers=2)`, statsmodels' `test_package.py`, scikit-learn's `experimental` tests that start `sys.executable` (READ) | `README.md` |
   | `no-mmap` | `mmap is unavailable` | 41 in scikit-learn's sample (EXECUTED); scipy's `io` tests with `mmap=True` (READ) | `README.md` |
   | `no-fp-exceptions` | the `DID NOT WARN` and `DID NOT RAISE` lines of floating-point warnings | wasm has no floating-point exception flags; 099 keeps numpy's own software flags, not the hardware's, so a float division by zero in a ufunc loop warns nothing (READ: 099's Decision text) | `README.md` |
   | `left-out-datasets` | `FileNotFoundError` naming `statsmodels/datasets/<name>/` | 19 statsmodels test files load one of the thirteen datasets 045 leaves out for their terms (EXECUTED: `sm_datasets.py`), `test_glm.py` and `test_discrete.py` among them | `README.md` (045's list of the thirteen) |
   | `no-network` | the `URLError` of an `https` URL | statsmodels' `get_rdataset` and `webuse` tests (3 files, READ), if they are not skipped | `README.md` |
   | `wasi-errno-values`, `zip-no-source`, `open-empty-path`, `builtin-no-file` | 066's matches | 066 met each in another package | `README.md` |

   A class never spans packages. A failure no class admits is a finding: the group is red, and the
   survey brings it to the confirmation round, where it becomes a class with a closer or a
   product specification.

10. **Traps.** As 066's Decision 10: a test that traps the guest is deselected from its group, run
    alone by `test_upstream_trap[<id>]`, and is a gap until fixed; a trap is a product defect and
    gets its own specification. None was seen in the probes. The survey hunts them in every group;
    scipy's f2py and OpenBLAS paths, called through function pointers, are where 037 and 051
    looked hardest.

11. **The groups, their caps and the budget** (066, Decision 11, unchanged).
    - **The bound:** no group's measured fuel passes 480 G; a group past it is split by file, in
      the sdist's order; a file past it is split by construction with `[[split]]` (an ordered list
      of `-k` expressions), never left out.
    - **The cap rule:** each group's cap is 1.5 times its measured fuel, rounded up to two
      figures; each family's budget is the sum of its caps.
    - **The files known to need a split** (EXECUTED counts, fuel INFERRED): scipy's
      `signal/tests/test_signaltools.py` (12,370 tests, 10,347 of them release-tier),
      `sparse/tests/test_64bit.py` (10,512; 2,919 release), `sparse/tests/test_base.py` (3,698),
      `linalg/tests/test_basic.py` (3,649); scikit-learn's `tests/test_common.py` (13,387: one
      check per estimator, likely the heaviest file of the three suites) and
      `metrics/tests/test_common.py` (3,615). The survey measures each and writes its split.
    - **Groups follow the package's subpackages** (one group per subpackage or a run of small
      ones, by sdist order), so a class's members and a regression read by subpackage.

12. **The release: new Linux shards, packed from the survey's fuel.**
    - **Normal tier:** Linux shards of at most about 725 G each (066's packing), named
      `upstream-sci-*` (scipy), `upstream-skl-*` (scikit-learn) and `upstream-sm-*` (statsmodels),
      each within 360 s of job time on the branch's dry run (066's criterion 12). The lane's darwin
      judge runs every normal group at every landing.
    - **Release tier:** scipy's release groups in release shards of 102's kind, run only where 102
      runs them (the tag run and the dry run on main before a tag).
    - **The job count.** 101 sets the Linux matrix's `max-parallel` (20 in 067's reading of it);
      the new shards queue behind it. Decision 12's price below states the wall-clock cost as an
      estimate; the branch's dry run measures it.
    - **Linux only in the release**, as 066's: fuel is ratcheted on the lane's darwin judge; G5
      compares `passes` and `passed_digest` between the Linux record and the lane's.

13. **`packages.toml`: three suites, and no package left closing with 095.**
    - scipy, scikit-learn and statsmodels become `kind = "suite"` (statsmodels `later` with the
      split's closer if Depends on's third path applies).
    - OpenBLAS stays `via scipy`, now a suite that runs.
    - formulaic, interface-meta and wrapt stay with 067 (the owner, 2026-10-20).
    - **The check of it:** after 095, no entry names `spec 095` as its closer (criterion 10).

14. **The rules check, widened** (066's Decision 14, plus):
    - `package_inits` is a boolean; when true, each generated `package_paths` entry is a tarball
      folder holding an `__init__.py` member, and no generated entry names a package the product
      lacks (the zip's names and the builtins, from the artifact set's lists);
    - each `derived` entry's script is a tarball member under a staged or support folder, its
      output's folder is a staged folder, and the output is not a member;
    - `env` names only the variables listed for that family (Decision 7), each with a reason line
      in the TOML; no family sets `TMPDIR` or `HOME`;
    - the staged `package_drive.py` hashes equal to `tests/upstream/package_drive.py` (Decision 3);
    - 066's rules, 102's rules (tiers, truth table, release caps) and 063's shard rule hold for
      the three families.

15. **The needs, the scoreboard, the README and the CHANGELOG.**
    - **Needs:** a group needs the artifact set, the kit and its family's tree; without the tree it
      is blocked, named (`upstream tree scipy`). A failed derived run fails the family's groups.
    - **The scoreboard** counts the new groups under v1.3.
    - **README:** the testing section names the three suites, their groups and shards, the release
      tier's scipy groups, what is not run and why (Decision 8), the modes not run (Decision 7),
      and each class's fact closed by `README.md` that is not already there.
    - **CHANGELOG:** one entry: "The release runs scipy's, scikit-learn's and statsmodels' own
      tests (spec 095)."

## Intent

The judge runs scipy's, scikit-learn's and statsmodels' own test suites inside the guest. It counts
every pass, and shows every known failure and every test it does not run as a gap or a named line,
with what will close it. The release runs the normal tier on Linux in new shards, and scipy's slow
tests where the release tier runs; the lane runs the normal tier on darwin at every landing. The
judge turns red when a pass is lost, a test traps the guest, an unknown failure appears, a test
runs against a copy of the product's code, or the tests are not the artifact's own.

## Design

```
tests/upstream/scipy.toml            package "scipy", driver "package", grant /upstream-scipy,
                                       stage_folders (scipy/**/tests, but odr), package_inits,
                                       support_files [scipy/conftest.py, scipy/special/utils/...],
                                       derived (makenpz.py: boost, gsl, local), env {SCIPY_XSLOW},
                                       marker / release_marker (102), cwd /tmp/work, groups by
                                       subpackage, [[split]]s, [[not_selected]], [[expected]]
tests/upstream/scikit-learn.toml     grant /upstream-scikit-learn, stage_folders (sklearn/**/tests),
                                       package_inits, support_files [the two conftests],
                                       env {SKLEARN_RUN_FLOAT32_TESTS}, groups, [[split]] for
                                       tests/test_common.py
tests/upstream/statsmodels.toml      grant /upstream-statsmodels, stage_folders, package_inits,
                                       support_files [statsmodels/conftest.py], groups
tests/upstream/<package>.ini         Decision 6
tests/upstream/expected/<group>/<class>.txt
tests/harness/packages.py            package_inits (package_paths generated), derived (the
                                       stage-time guest run, its facts), env (merged into ENV);
                                       their rules
tests/harness/upstream.py            the three names
tests/checks/test_v1_3_upstream_suites.py, tests/upstream/fetch.py, tests/upstream/packages.toml,
tests/release_shards.toml, .github/workflows/release.yml, tests/known_gaps.toml,
tests/unit/test_packages.py, test_shards.py, test_fetch_trees.py,
README.md, CHANGELOG.md, context/progress/README.md, context/roadmap.md
```

**A family's run, in order:**
1. Stage `/upstream-<package>` once per judge run, after the tie, from the patched tree: the
   staged folders, the ancestor inits, the support files, the kit, the driver, the `.ini`, each
   group's JSON.
2. scipy only: the derived runs (Decision 5), each in a fresh root with the stage read-only; their
   outputs copied into the stage; the stage sealed read-only (089).
3. Each group: `guest.run(snapshot, ["-u", "/upstream-<package>/judge/package_drive.py",
   "<package>", "<group>"], …, env=ENV | family env, fuel=<cap>, preopens=[(grant, stage, False)],
   mpl_data=True)`; the stream read, classes sorted, the guard checked, `fuel` and `passes`
   recorded with 066's facts.

## Scope

**In:** the above, both tiers, every test of the three suites in one tier or the other.

**Out, each with its reason:**
- **Fixing what the suites find.** Each failure is a class with its closer, or a finding that
  returns to the lane. A product fix is its own specification.
- **scipy's seven test-only C modules.** Linking them is spec 088's (a judge-only binary, never
  published); the files that need them are named (Decision 8).
- **The modes of Decision 7**, unless the owner rules otherwise.
- **formulaic's, interface-meta's and wrapt's suites:** 067's.
- **The plain binary, and macOS and Windows release shards** (066, Decisions 11 and 12).
- **Wall-clock.** No check reads a clock (§4.9); every time below is an estimate.

## Acceptance criteria

Each is counted; none times anything. Each check is written first and seen failing against today's
code or a stand-in; the builder records each failing assertion in the landing notes.

1. **The rules.** `test_upstream_files_are_well_formed` passes with Decision 14's rules on the three
   new TOMLs. `tests/unit/test_packages.py` variants each fail with their own line: a
   `package_inits` family whose generated entry names a folder with no `__init__.py` member; one
   naming a package the product lacks; a `derived` script that is not a member; a `derived`
   output that is a member, or outside a staged folder; an `env` variable not listed for the
   family; `env` setting `HOME`; a staged driver whose hash differs from main's.
2. **The derived run, on a synthetic tarball** (no real scipy): a script that writes its output
   stages it; one that exits 1 fails every group of the family, named; one that writes nothing
   fails them, named; the output's SHA-256 is a fact of the first group.
3. **The survey, then the baseline.** The memo exists, labelled EXECUTED, written before any
   check, TOML or harness line, with each group's outcomes by id, fuel, traps and collection
   errors, both tiers; its delta has a confirmation verdict. Each group check, run before its
   TOML lists and gaps exist, fails with its findings.
4. **With the TOMLs, the lists and the gaps complete**, the run on that set gives each group check
   passing; each class and trap check failing as its gap says; the numbers (passes, fuel, classes,
   members) in the landing notes, equal to the memo's or explained.
5. **Fuel repeats.** Each new normal group run twice, restaging between the runs: equal outcomes
   and `passed_digest`; on darwin equal fuel within `sameness.py`'s tolerance. The release groups
   once each, on darwin.
6. **Nothing else moves.** The ratchet against the base: every numpy, pandas, CPython and 066 row
   lost 0, grew 0; their stages' file lists are byte for byte the base's (066's stage-manifest
   unit check, extended to the six 066 families).
7. **The shards.** 063's `test_release_shards_cover_the_judge` and the workflow scan pass with the
   new shards; each new normal group is in exactly one Linux shard and each release group in one
   release shard (102's rule).
8. **The fetch.** `tests/unit/test_fetch_trees.py`, with a fake `urlopen`: a shard with a scipy
   group fetches the kit and scipy's tarball only; a hash mismatch deletes the `.part` file and
   exits 1 naming it.
9. **The tie and the stage.** Unit checks: a `MANIFEST` whose scipy `pin` line differs fails the
   group (not blocked); a staged `__init__.py` imported during a run (a stand-in stream with its
   `M` line) is a finding.
10. **`packages.toml`.** `test_every_package_names_its_own_suite` passes with the three as `suite`;
    no entry names `spec 095`.
11. **The fast tier and the lint.** `uv run ruff check`, `uv run ruff format --check` and `uv run
    pytest -m "not slow" -n 6` green on the builder's worktree against the survey's set, apart
    from the gaps this specification adds, each named.
12. **The branch's dry run, before landing** (not a check): every job passes on all three systems,
    every red line a growth line or G7; the new shards' job times in the landing notes, each
    within 360 s, or Decision 12's move made and recorded. One dispatch with 102's `release-tier`
    input true shows the release shards once.
13. **The lane's dry run after landing**, on main's exact commit, as 063's criterion 13.

## The price (estimates, labelled; the survey replaces them)

- **Normal-tier fuel per full judge** (INFERRED from the probes): scipy about 5 to 9 T (80,926
  tests at the sample's 63 M a test is 5.1 T, before each group's start and its heavier files);
  scikit-learn about 8 to 20 T (46,955 tests; the sample's 444 M a test gives 20.8 T, but the
  sample holds forests, trees and ridge paths, likely heavier than the median file); statsmodels
  about 2 to 6 T (21,412 tests natively in 468 s by 045's builder, EXECUTED there; 045 inferred
  about 3 T). **In all about 15 to 35 T** of upstream fuel added to every full judge, on top of
  today's about 11.2 T: 2.3 to 4.1 times today's upstream fuel. scikit-learn is the largest part
  and the least certain.
- **The lane's darwin accept** (INFERRED, at the samples' 0.18 s per G): about 45 to 105 more
  minutes of guest time, so about 15 to 35 more minutes of wall clock at `-n 3`, on every landing.
- **Release-tier fuel** (scipy's slow and xslow, 15,174 tests): about 4 to 12 T, run only before a
  tag (INFERRED: slow tests are slower per test by construction; the survey measures it once).
- **Caps** by the rule, 1.5 times: about **23 to 53 T** for the normal tier.
- **Linux shards**: about **21 to 48 normal-tier shards** of at most 725 G (today 23 Linux
  shards; 066 added fourteen), and about 6 to 17 release-tier shards. At 0.16 to 0.31 s per G
  (066's reading of run `39371419248`), each shard 120 to 290 s of guest time plus about 60 s of
  setup. With the Linux matrix capped at 20 parallel jobs (101), 44 to 71 Linux jobs run in three
  or four waves of twenty where today's run in two, so the new shards add about **5 to 15
  minutes** of wall clock to a release run, and they hold Pro's 40 concurrent jobs longer when
  another run is live (INFERRED).
- **The survey:** about 2 to 4.5 CPU hours on darwin-arm64 (Decision 1), on main's set after wave
  09 for scipy and scikit-learn, and on statsmodels' set (main after 045, or 045's reviewed set).
- **What would lower it, not chosen here:** a release tier for scikit-learn's float32 cases or for
  statsmodels' `slow` (Decision 7's allowance), or for the heaviest files (scikit-learn's
  `tests/test_common.py`, the estimator checks, is the likeliest; the owner's "we can decide what
  is slow tier" allows it, by a reviewed keyword or path selection, never out); spec 092 (the judge
  reads CI's record) shortens the lane's own accept.

## The claim list's shape (for the lane, filled in by the build)

- **Gained rows:** `test_upstream_suite[<group>]` for each new group, with metrics `fuel` and
  `passes` and 066's facts (`counts`, `passed_digest`, `left_out`, `collected` for split groups),
  plus `derived` for scipy's first group; `test_upstream_class[<group>-<class>]` for each class
  with members, each a gap; `test_upstream_trap[<id>]` for each trap.
- **Release-tier rows** (scipy's release groups) are new rows in 102's `release_tier` list on a
  normal accept, accepted only at the release acceptance before a tag (102, Decision 5).
- **Moved rows: none.** numpy's, pandas', CPython's and 066's rows: lost 0, grew 0.
- **Retired: none. Passes moved: none.**
- **The judge hash changes**: the accept-judge text names the three TOMLs, `.ini`s, the expected
  lists, the harness keys, the gaps, `packages.toml`, the shards and the workflow.
- **No `--accept-growth`**, unless the base brings one.

## For the lane

- **Wave kind: build-class** (the release workflow; no artifact byte, no `scripts/`, `recipes/` or
  `downloads/` line). It may ride as one of a wave's two other build-class entries, after 045 and
  102.
- **Base.** This draft is on main `dda6075`; the structural chain (`dbecd2d`) was not under it at
  drafting (the session could not move the branch). The draft touches only `context/`.
- **Decisions the owner may want to see** (drafted as decided; the report carries them):
  088's widening to scipy's seven test modules; the modes not run (Decision 7); statsmodels'
  left-out datasets as a class, not staged data (Decision 9); the price.
