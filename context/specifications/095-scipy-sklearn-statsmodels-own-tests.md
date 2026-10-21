# 095 — scipy's, scikit-learn's and statsmodels' own tests in the release

- **Status:** **drafted 2026-10-20** on `spec/095-scipy-sklearn-statsmodels-own-tests` from main
  `dda6075`; **rebased 2026-10-20 onto the structural chain's tip `727bd4c`**
  (`claude/gallant-ride-9nxxmn`, landing on main that night; context only, no conflict).
  **Reviewed before build** the same day
  (`../reviews/095-scipy-sklearn-statsmodels-own-tests-spec-2026-10-20.md`: "fit to build once H1
  and M1 are written in and confirmed, the Lows answered in writing"). **Revised against every
  finding** (the review's Disposition says where); awaiting the reviewer's confirmation. Four
  choices the owner may make are written in as **defaults pending the owner's answer** (the
  lane files the questions): 088 widened to scipy's seven test modules (Decision 8); the modes
  README-only for 0.1.0 (Decision 7); a 15 T threshold for scikit-learn's release tier (Decision
  7); statsmodels' left-out datasets as a README class (Decisions 8 and 9). The owner kept all
  four (question 110, `decisions.md`); after the survey showed the threshold could not be met, the
  owner replaced it on 2026-10-21 with a standing rule: each suite in the release tier whole, a
  small smoke group per package in the normal tier (Decision 7, revised). **Confirmed fit to
  build** by the same reviewer (the review's Confirmation, `f2926ae`). **Surveyed 2026-10-21**
  (`../research/2026-10-21-scipy-sklearn-statsmodels-own-tests-under-the-runtime.md`, EXECUTED:
  scipy and scikit-learn on wave 09's set `142bdd38`, statsmodels on 045's set `14adfa5f`); its
  dated delta is the section "Delta from the survey", for a context-only delta review before any
  build. The drafting probes below were calibration, not the survey. **Delta reviewed** the same
  day (the review's *Delta review*: three Mediums, two Lows, rule (8)); **answered 2026-10-21** by
  the builder who took over from the drafter (the review's *Disposition of the delta review*; the
  smoke groups re-measured on the main tree's set `d0d91cef`); awaiting the reviewer's
  confirmation, and 102's builder's answer to *For 102*. **Build begun 2026-10-21** on 102's final
  tip `861d5e4b`, **stopped part-way at the owner's pause** (the Landing notes give the resume
  point); no CI run dispatched.
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
    - `tests/harness/packages.py`: four keys, `package_inits`, `derived` and `env` (Decisions 4, 5,
      7) and the group key `clock_step_ns` with its `clock_reason` (Decision 10), their rules, and
      the stage-time guest run of Decision 5;
    - `tests/harness/upstream.py`: `PACKAGES` (or `PACKAGE_SUITES`, as main names it then) gains the
      three names;
    - `tests/checks/test_v1_3_upstream_suites.py`: the needs per family;
    - `tests/upstream/fetch.py`: `--shard` fetches the three trees for the shards that run them;
    - `tests/upstream/packages.toml`: scipy, scikit-learn and statsmodels become `suite`
      (Decision 13);
    - `tests/release_shards.toml`, `.github/workflows/release.yml`: the new Linux shards, normal and
      release tier (Decision 12);
    - `tests/unit/test_packages.py`, `test_shards.py`, `test_fetch_trees.py`;
    - `tests/checks/test_rules.py`: the citation rule's allowance entries this change retires
      (`CONTEXT_CITATION_ALLOWED`: `packages.toml`'s "spec 095" and whatever else its rewritten
      scipy and scikit-learn comments held), in the same change, as 102 does (the review, L4);
    - `context/release-tier-claims.toml`: 095's `[[claim]]` block for scipy's release groups
      (102, Decision 6; the review, L8);
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
    reviewed and waiting for a wave. **095 needs one more kind in 102's list, the smoke kind**,
    which the owner's rule of 2026-10-21 makes necessary: whole paths in the release tier that no
    normal group holds, which 102's paths rule refuses today (the delta review, D-M1). The exact
    change is the section *For 102: the smoke kind* below, a request the lane routes to 102's
    builder; 095 does not edit 102's branch. 095 adds no other tier mechanism.
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
  - **109** (the structural chain, under this branch since its rebase onto `727bd4c`: comments
    and docstrings outside `src/` give their reasons in words; the rule
    `test_code_outside_src_names_no_context_document` reads every comment and docstring in the
    Python, TOML, shell and YAML files under `tests/` and `.github/workflows/`). No comment or
    docstring 095 writes there names a specification number, a section sign, a research or review
    document, a question number, a `context/` path or a finding identifier; each `env` and
    `not_selected` reason is written in words; `closes_with` and `reason = "…"` values are data and
    keep their form; the `.ini` files are not scanned but follow the same rule (the review, L4).
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
| scipy, collect only, without `SCIPY_XSLOW` | the whole staged suite | 286.5 G | 96,100 collected; 11 files fail to load (Decision 8) |
| scipy, collect only, without `SCIPY_XSLOW` | `-m "slow or xslow"` | 293.3 G | 15,174 selected, 80,926 deselected |
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
     their one-line reasons. It also records, for the review's findings: both of scipy's tiers
     collected with `SCIPY_XSLOW=1`, and every direct read of each `env` variable in each sdist
     (H1); the derived run's fuel and each output's size (M1); every `setup_module` and
     `teardown_module` in the staged ancestor inits (L2); each not-selected file's collected count
     (L3); and the tests that skip only because a mode's variable is unset (L7).
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
   Decision 5 are staged by the harness. That the driver is not edited is a fact of the diff,
   which the review reads; criterion 6's unit check proves that 066's families stage what they
   staged before (the review, L5).

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
     names it `scipy.linalg.tests.test_basic`.
   - **Why the staged inits are never run** (corrected by the review, L1). In the kit's pytest
     9.0.3, importlib mode returns `sys.modules[name]` when the name is there; otherwise it runs
     the parent's `__init__.py` from the file it finds (`_pytest/pathlib.py:535-553`, READ by the
     review). The product's packages win only because `package_drive.py` imports every
     `package_paths` key before pytest starts, from the zip. So **every ancestor package of every
     staged folder must be a package the product has, and a generated `package_paths` entry**; a
     staged folder under a package the product lacks is refused by the rules and never staged
     (Decision 14). The guard proves the rest on every run: a module loaded from a staged
     `__init__.py` is an (a) `M` line outside a test folder, a finding (066, Decision 5). The
     probes saw none.
   - **Staged inits make pytest call a package's `setup_module`** (the review, L2). With
     `sklearn/__init__.py` staged, pytest collects `sklearn/` as a `Package`, whose setup calls
     the product's `sklearn.setup_module`. It seeds `numpy.random` and `random` from
     `np.random.uniform()` unless `SKLEARN_SEED` is set (`sklearn/__init__.py:139-151`, READ by the
     review), so the global seed would depend on how many random bytes the product drew before the
     tests: a product change elsewhere would move every test on the global generator.
     scikit-learn's `env` therefore sets `SKLEARN_SEED` to a fixed value (`"0"`), upstream's own
     switch for a fixed global seed. The survey lists every `setup_module` and `teardown_module`
     in the
     staged ancestor inits of the three packages; scipy's define none (READ by the review).
   - **`package_paths`** maps the package and every ancestor of a staged folder to its folder
     (`{"scipy" = "scipy", "scipy.linalg" = "scipy/linalg", …}`), generated by the harness from
     `stage_folders` when `package_inits` is true and checked by the rules against the tarball, so
     the TOML does not list some 35 entries by hand (EXECUTED: the probe staged 35 ancestor
     `__init__.py` files for scipy's 33 folders). A package the product lacks (`scipy.odr`, a
     stand-in module, not a package) is never in it, and no folder under one is staged.
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
     build's control or as a guest (§4.8). So when it makes the stage, before any group of the
     family runs, the harness runs
     `makenpz.py` from the stage in the snapshot binary (`python -u
     /upstream-scipy/tree/scipy/special/utils/makenpz.py <name> -o /tmp/derived`, once per
     name), with the stage read-only and a fresh writable root, and copies the three files it
     writes into the stage at `scipy/special/tests/data/` before sealing it (089).
   - **The key** (revised for the review, M1): `derived = [{ script =
     "scipy/special/utils/makenpz.py", args = ["boost"], inputs = "scipy/special/tests/data/boost",
     output = "scipy/special/tests/data/boost.npz", measured = <fuel>, fuel = <cap> }, …]`, one
     entry per output. The rules check: the script is a tarball member; `inputs` names a tarball
     folder that holds members (makenpz finds its inputs from its own path, `makenpz.py:43-45`, so
     the folder is the one beside its output; READ by the review: boost 111 files, 14,188,680
     bytes; gsl 3, 400,255; local 8, 1,325,932); each output's folder is a staged folder; no
     output is a member; `fuel` is at most the cap rule's 1.5 times `measured`.
   - **Its fuel is capped**, by the cap rule like a group's: the survey measures each entry, and
     the run stops at its cap as a group does.
   - **The output is checked before it is staged.** makenpz's real failure is not "writes
     nothing": with an empty or missing input folder it calls `np.savez_compressed` with no arrays,
     writes an empty `.npz` and exits 0 (`makenpz.py:52-80`, READ by the review). So the host reads
     each output with `lstat`, never through a link, and refuses it unless it is a regular file, at
     most 16 MiB (about ten times boost's inputs compressed; INFERRED, the survey records each
     size), and a zip archive holding at least one `.npy` member (read with `zipfile` on the host
     as data, never loaded as numpy). A refused output, a non-zero exit or a trap fails every group
     of the family, each naming the entry; it never blocks them.
   - **Its record, on one fixed row** (the review, M1). The stage is made once per judge session:
     once per xdist worker on darwin at `-n 3`, and once per Linux shard, so "the first group"
     differs between runs. The facts (each output's SHA-256 and the run's fuel, `derived`) are
     recorded on the group that holds `scipy/special/tests/test_data.py`, named in the TOML as
     `derived_row`, and on no other row. They are facts, not ratcheted metrics.
   - **It runs in every stage that holds the family**, whatever the tier or the shard (102,
     Decision 4: the stage never depends on the tier). The survey measures its fuel; the price and
     the shard packing count it once per scipy shard and once per darwin worker that runs a scipy
     group.
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

7. **The two tiers (102): each suite in the release tier whole, and a small normal-tier smoke
   group per package** (revised 2026-10-21 by the owner's standing rule; it replaces the
   threshold of the reviewed text and the marker split as the line between the tiers).
   - **The owner's words** (2026-10-21, through the lane, answering the survey's threshold
     question): "we need to have fast tests and slow tests. We only run slow tests when we are
     trying to publish to pypi, as it is critical we check that our package is working on the
     libraries we import before we release to catch any errors, otherwise we should only run the
     tests needed to confirm our new edits are working."
   - **So:** scipy's, scikit-learn's and statsmodels' own suites run in the **release tier**, whole
     (102's machinery: the tag run, the dry run on main before a tag, and the lane's release
     acceptance). Each package keeps **one or two smoke groups in the normal tier**: a few test
     folders or files that prove the package imports and its core compiled paths work, so a
     landing that breaks a package is still caught at every landing and on every branch run.
     Nothing leaves the full suite: every test runs in exactly one tier.
   - **The smoke selection follows a stated rule** (the delta review, D-M2; it replaces the
     survey's hand-picked groups). The smoke groups are what confirms an edit to a package's build
     at every landing, so they must touch what such an edit can break:
     1. **Every compiled family of the package.** A family is a subpackage holding compiled
        modules, from the build's own list: the product's `sys.builtin_module_names` (EXECUTED
        2026-10-21 on set `d0d91cef`: 95 scipy modules in 31 families, 69 scikit-learn modules in
        19, 26 statsmodels modules in 11). Each family is touched by a **smoke test file from its
        own tests folder**, the cheapest that calls into it, unless a **named golden-job line**
        (`tests/jobs/`, which runs at every landing too) touches it and the cheapest file costs
        more than about 15 G net: then the golden line stands in for it (so `cKDTree`, `cdist`,
        `csgraph`, ARPACK's `eigsh`, `quad`, `least_squares`, `qr_update`, `RBFInterpolator`,
        `lfilter`, `KMeans`, RandomForest, HGB's binning, `_loss`, the distance metrics; each
        line named in the table).
     2. **Always by a smoke file, never by a golden line alone:** the families the review names
        (scipy.special; `sparsetools`; qhull; HiGHS; scikit-learn's trees; statsmodels' OLS) and
        **every carried patch's path**: scipy's four (uarray's callbacks, `sqrtm`'s error, Matrix
        Market without threads, Sobol without a temporary file), OpenBLAS's void C LAPACK (any
        LAPACK call through scipy.linalg), qhull's format strings, scikit-learn's html repr from
        the zip, and statsmodels' datasets from the zip.
     3. **Each package's most-used public entry points**, by a smoke file or a golden line:
        scipy's `linalg.solve`/`cholesky`/`lu`, `optimize.minimize`'s L-BFGS-B, SLSQP and TNC,
        `root_scalar`, `linear_sum_assignment`, `milp`, `fft.fft`, `integrate.odeint`/`ode`,
        `solve_ivp` (golden), `interpolate.splrep`/`griddata`, `CubicSpline` (golden),
        `spatial.Delaunay`/`ConvexHull`, `cKDTree` (golden), `cdist` (golden), `stats.qmc`,
        `stats` distributions (golden); scikit-learn's `DecisionTree*`, `SVC`/`LinearSVC`,
        `LinearRegression`, `DBSCAN`, `HDBSCAN`, `KMeans`, `PCA`, `RandomForest*`,
        `HistGradientBoosting*`, `LogisticRegression`, `KNeighbors*` (golden, `machine_learning.py`);
        statsmodels' `OLS`/`WLS`/`GLS`, `smf.ols`, `GLM` families, `ARIMA`, `lowess`, `STL`,
        `summary()` (and `Logit`, `GLM` Poisson, `SimpleExpSmoothing` in 045's golden
        `statistical_models.py`).
     4. **Whole files or folders only** (the smoke kind moves whole paths, *For 102*), each
        package's smoke groups at most 500 G together (*For 102* item 5), each group under the
        480 G bound.
     5. **Named exceptions**, release tier only, because every file of the family costs past the
        bound's reach for a smoke file (more than 100 G net in the probes) and no golden line
        touches it: scipy `stats._levy_stable` (its tests live in `test_distributions.py`, 680
        test functions); statsmodels `nonparametric.linbin` (`test_kde.py`, past 123 G net) and
        `tsa.exponential_smoothing` (`test_exponential_smoothing.py`, past 124 G net); and scipy
        `_lib`'s three, imported by every session, whose compiled-path tests are Decision 8's
        not-selected files. A later golden line or a cheaper upstream file closes an exception.
   - **How it was measured** (EXECUTED 2026-10-21, darwin-arm64, the main tree's frozen set
     `SHA256SUMS d0d91cef` copied with `cp -c -Rp` and checked, one guest at a time, never while
     `build/lane.lock` existed; the memo's *Smoke selection* section): 117 candidate files or
     folders probed one per session, and three draft groups, for their net fuel (each session less its start: 20.1 G scipy, 26.4 G
     scikit-learn, 26.4 G statsmodels), the cheapest cover chosen by the rule, then **each final
     group measured once as a whole**.
   - **The smoke groups, re-measured:**

     | group | paths (whole files or folders) | covers | fuel | outcomes |
     |---|---|---|---|---|
     | `scipy-smoke-a` | special: `test_cython_special.py`, `test_boost_ufuncs.py`, `test_ellip_harm.py`, `test_sph_harm.py`, `test_specfun.py`; sparse: `test_sparsetools.py`, `test_csr.py`, `test_construct.py`, `linalg/_dsolve/tests`, `linalg/tests/test_propack.py`; spatial: `test_qhull.py`, `test_hausdorff.py`, `test_spherical_voronoi.py`, `transform/tests`; linalg: `test_decomp_cholesky.py`, `test_solve_toeplitz.py`, `test_matfuncs.py`, `test_cython_blas.py`, `test_cython_lapack.py`, `test_cythonized_array_utils.py`, `test_decomp_lu.py` | xsf, Boost.Math, `cython_special`, `_specfun`, `_ellip_harm_2`, `_gufuncs`; `sparsetools` (its 64-bit `slow` cases in the release tier), `_csparsetools`, SuperLU, PROPACK; qhull and its patch, `_hausdorff`, `_voronoi`, the rotation modules; f2py `_flapack`/`_fblas` on OpenBLAS's void LAPACK, `cython_blas`, `cython_lapack`, `_solve_toeplitz`, `_matfuncs_sqrtm_triu` and its patch (imported only by this group's `test_matfuncs.py` among the probes, EXECUTED) | **207.4 G** | 2,033 passed, 10 skipped, 30 xfailed, 2 xpassed, 1 failed (`no-threads`) |
     | `scipy-smoke-b` | `cluster/hierarchy/tests`, `cluster/vq/tests`, `fft/tests/test_basic.py`, `fftpack/tests/test_pseudo_diffs.py`, `integrate/tests/test_integrate.py`, `interpolate/tests/test_fitpack.py`, `test_interpnd.py`, `io/tests/test_mmio.py`, `io/matlab/tests`, `ndimage/tests/test_measurements.py`; optimize: `test_minpack.py`, `test_lbfgsb_setulb.py`, `test_lbfgsb_hessinv.py`, `test_slsqp.py`, `test_zeros.py`, `test_linear_assignment.py`, `test_tnc.py`, `test_direct.py`, `test_isotonic_regression.py`, `test__numdiff.py`, `test_milp.py`, `test_trustregion_krylov.py`, `test_cython_optimize.py`; signal: `test_max_len_seq.py`, `test_upfirdn.py`, `test_splines.py`, `test_bsplines.py`; stats: `test_qmc.py`, `test_contingency.py`, `test_discrete_distns.py`, `test_sampling.py` | `_hierarchy`, `_vq`; uarray and its patch with ducc0 (`scipy.fft`'s backend); `fftpack.convolve`; `_odepack`, `_vode`, `_dop`; FITPACK, `_dierckx`, `_interpnd`; `_fmm_core` and its patch (three passes through it; the rest of `test_mmio.py` is `no-native-id-test-names`; scipy_edges' Matrix Market line too); the MATLAB readers; `_nd_image`, `_ni_label`; MINPACK, L-BFGS-B, SLSQP, `_zeros`, `_lsap`, TNC, DIRECT, `_pava`, `_group_columns`, **HiGHS** (`milp`), `_trlib`, `cython_optimize`; `_max_len_seq_inner`, `_upfirdn_apply`, `_spline`; `_sobol` and its patch, `_qmc_cy`, `_rcont` (`random_table`), the Boost discrete distributions, UNU.RAN | **221.8 G** | 2,322 passed, 43 skipped, 8 xfailed, 2 xpassed, 28 failed and 147 errors, every one a measured class: 148 `no-native-id-test-names`, 12 `no-processes`, 10 `no-threads`, 1 `DID NOT RAISE` and 3 bare asserts (two `test_threadpoolctl`, one `test_qmc`) and 1 unraisable warning from `_qmc_cy`'s threads, which are among the survey's eleven read one by one (each a class with its closer before the build review) |
     | `scikit-learn-smoke` | `tree/tests/test_split.py`; `ensemble/_hist_gradient_boosting/tests/test_splitting.py`, `test_histogram.py`, `test_predictor.py`; `cluster/tests/test_dbscan.py`, `cluster/_hdbscan/tests`; `svm/tests`; `linear_model/tests/test_base.py`, `test_sag.py`, `test_perceptron.py`; `feature_extraction/tests/test_feature_hasher.py`; `datasets/tests/test_svmlight_format.py`; `metrics/cluster/tests`; `neighbors/tests/test_kd_tree.py`, `test_ball_tree.py`, `test_quad_tree.py`; `preprocessing/tests/test_target_encoder.py`; utils: `test_sparsefuncs.py`, `test_murmurhash.py`, `test_fast_dict.py`, `test_seq_dataset.py`, `test_arrayfuncs.py`, `test_random.py`, `test_typedefs.py`, `test_weight_vector.py`, `_repr_html/tests`; `decomposition/tests/test_online_lda.py`; `tests/test_isotonic.py` | **the trees** (`_tree`, `_splitter`, `_criterion`, `_partitioner`), HGB's splitter, histograms and predictor, `_dbscan_inner`, HDBSCAN's three, libsvm and liblinear, `_sag_fast`, `_sgd_fast`, `_hashing_fast`, `_svmlight_format_fast`, `_expected_mutual_info_fast`, KD, ball and quad trees, `_target_encoder_fast`, `sparsefuncs_fast`, `murmurhash`, `_fast_dict`, `_seq_dataset`, `arrayfuncs`, `_random`, `_typedefs`, `_weight_vector`, the html-repr patch, `_online_lda_fast`, `_isotonic`; golden (`machine_learning.py`): KMeans, PCA, RandomForest, HGB's binning, LogisticRegression (`_loss`), KNeighbors (the distance metrics and pairwise reductions) | **205.5 G** | 1,467 passed, 189 skipped, 5 xfailed, 8 xpassed, 2 failed (`no-mmap` 1, `enotsup-io` 1) |
     | `statsmodels-smoke` | `regression/tests/test_regression.py`; `nonparametric/tests/test_lowess.py`; `robust/tests/test_scale.py`; `tsa/innovations/tests`; `tsa/arima/tests`; `tsa/statespace/tests/test_tools.py`, `test_simulation_smoothing.py`; `tsa/regime_switching/tests/test_markov_regression.py`; `tsa/stl/tests/test_stl.py`; `genmod/families/tests`; `formula/tests`; `iolib/tests`; `tsa/filters/tests` | **OLS, WLS, GLS** on `longley` through the datasets patch; `_smoothers_lowess`; `_qn`; `_arma_innovations`, `_innovations`; the Kalman filter, smoother and representation (ARIMA through SARIMAX), `_tools`, the simulation smoothers; `_hamilton_filter`, `_kim_smoother`; `_stl`; GLM families; formulas; summaries; filters; golden (`statistical_models.py`): `SimpleExpSmoothing` (`_exponential_smoothers`), Logit, GLM Poisson | **136.0 G** | 939 passed, 5 skipped, 1 xfailed, 4 failed and 40 errors, all `left-out-datasets` (`ccard` 41, `cpunish` 2, `fair` 1) |

     **The golden lines that stand in** (READ): `scipy_numeric.py:75` (`eigsh`, ARPACK), `:89`
     (`csgraph.shortest_path`), `:151-153` (`CubicSpline`, `make_interp_spline`), `:162`
     (`RBFInterpolator`), `:170-172` (`lfilter`, `convolve`, `_sigtools`), `:190` (`cdist`),
     `:192-194` (`cKDTree`); `scipy_solvers.py:120` (`least_squares`, `_lsq`), `:188` (`quad`,
     `_quadpack`), `:226` (`solve_ivp`); `scipy_lapack.py:102-110` (`qr_update`,
     `_decomp_update`); `scipy_edges.py`'s Matrix Market and Sobol lines (beside the patches'
     smoke files); `machine_learning.py:19-31` (KMeans, PCA, RandomForest, HGB, LogisticRegression,
     KNeighbors); 045's `statistical_models.py:26, 74, 83` (`SimpleExpSmoothing`, Logit, GLM
     Poisson). A family is counted once, at family level: a family's every module need not be
     called (scipy's `_rgi_cython`, `_decomp_interpolative` and `_batched_linalg` are reached only
     in the release tier; the reviewer may ask for one more file where that matters).

     **In all 770.6 G** (scipy 429.1 G, scikit-learn 205.5 G, statsmodels 136.0 G), each family
     within the 500 G budget, each group under the 480 G bound. Against the survey's hand-picked
     277.6 G it costs about 493 G more on every landing, about 90 s of guest time at the
     survey's 0.18 s per G, under 35 s of wall clock at `-n 3`: the price of D-M2's cover. No trap,
     no unknown failure, no collection error. The build measures each group again as built
     (criterion 5). Probes ran with a module-list hook (one `pytest_unconfigure` writing
     `sys.modules`); its cost is a few M per session, inside the repeat tolerance.
   - **Markers in the smoke groups.** scipy's smoke groups run with scipy's normal marker, `-m
     "not slow and not xslow"`; their `slow` and `xslow` tests run in the release tier in a marker
     release group over exactly the smoke paths (102's rule as written, `release_marker = "slow or
     xslow"`). scikit-learn has no `slow` marker, and none of statsmodels' smoke files carries
     one (READ, `grep mark.slow`), so those two families have no `marker`, no `release_marker`,
     and their smoke files run whole in the normal tier.
   - **The release tier is everything else, by the smoke kind** (*For 102*). Every staged tests
     folder that is not itself a smoke path is a path release group's path; a path release group
     runs with no `-m` and ignores, by construction, each smoke file under its folder. No `-k
     "not (S)"` is needed or used. **Proved on the real stage** (EXECUTED, `smoke/split.py` on
     the three pinned tarballs): scipy's 329 staged test files are 63 in smoke paths and 266 in 28
     path release groups; scikit-learn's 256 are 37 and 219 in 32; statsmodels' 285 are 26 and 259
     in 44; no file in neither tier and none in two; and each of six mutants per family (a path
     release group dropped, one over a smoke file, an empty smoke reason, path groups without a
     smoke group, a `[[release_select]]`, the budget passed) is refused with its own line. The
     build packs the path release groups by the 480 G bound and the cap rule, splitting by
     `[[split]]` where a folder passes it.
   - **scipy keeps `SCIPY_XSLOW=1` family-wide** (H1's answer stands): every scipy group, in both
     tiers, runs with it. The three keyword entries of the reviewed text are no longer needed to
     keep the gated cases out of the normal tier, since only the smoke groups are normal and none
     holds them; they stay in the survey's record (`keywords.txt`) for any later smoke group that
     would take one of those files.
   - **scikit-learn's float32 cases** run, with `SKLEARN_RUN_FLOAT32_TESTS=1` in the family's
     `env`, in whichever tier their file is in. **statsmodels' `slow` tests** run in the release
     tier with the rest.
   - **No branch run runs release groups; the smoke groups confirm an edit** (the delta's rule (8)
     struck, 2026-10-21; the delta review, D-N1). The draft had a landing that changes a package's
     own build run that package's release groups on its branch run. The owner's words decide it
     against that: "We only run slow tests when we are trying to publish to pypi". So the three
     suites' release groups run only where 102 rehearses or does a publication (the tag run, the
     dry run on main before a tag, the lane's release acceptance), and every branch run, wave dry
     run and landing runs the smoke groups. That is why the smoke selection follows a stated rule
     (below): the smoke groups are what confirms an edit to a package's build, so they must touch
     each compiled family and each carried patch. 095's own builder measures its release groups
     locally by node id (criterion 5), and dispatches no branch run with `release-tier: true`
     (criterion 12).

   - **`env`, a new family key**, a map of variables the harness adds to the judge's `ENV` for
     every guest run of that family, never per group (H1). **The allowed names are a constant in
     `packages.py`, per family** (the review, L6), as 102's `EXCLUDABLE` is: today `SCIPY_XSLOW`
     for scipy, and `SKLEARN_RUN_FLOAT32_TESTS` and `SKLEARN_SEED` (Decision 4) for scikit-learn.
     A name joins only by a judge change with its reason. Each TOML entry carries its reason in
     words. **Forbidden in every family:** `TMPDIR`, `HOME`, any `PYTHON*`,
     `SCIPY_HYPOTHESIS_PROFILE` (scipy's conftest loads its own `deterministic` profile over the
     driver's, with the same `derandomize=True, database=None`; the review, N1),
     `SKLEARN_TESTS_GLOBAL_RANDOM_SEED` and `SKLEARN_SKIP_NETWORK_TESTS`.
   - **Modes, not tests: README-only for 0.1.0** (*default pending the owner's answer*; the
     review, L7). Each runs the same tests again under another setting, adds no test, and has no
     default in upstream's own command: scikit-learn's `SKLEARN_TESTS_GLOBAL_RANDOM_SEED=all`
     (each seeded test on 100 seeds; the default seed 42 runs), `--check-spmatrix` (patches
     scipy.sparse to raise on old-style matrix use) and `SKLEARN_WARNINGS_AS_ERRORS`; scipy's
     `SCIPY_ARRAY_API=1` (the array-API backends: the product carries none but numpy, and the
     variable changes scipy's own import-time behaviour) and `SCIPY_XFAIL` (it xfails the
     known-failing fits of `stats/tests/test_fit.py:112-118` without running them); statsmodels'
     `SM_FORMULA_ENGINE=formulaic` (the formula tests with formulaic in place of patsy, the
     default). statsmodels' `SM_TEST_COPY_ON_WRITE` is not a mode here: it applies only to pandas
     before 3, and the product's pandas is 3.0.6 (`statsmodels/conftest.py:23-27`, READ by the
     review). **The survey counts the tests that skip only because a mode's variable is unset**
     (scikit-learn's "SCIPY_ARRAY_API is not set": 47 in the seven-file sample, EXECUTED), and the
     README states each number. A mode run as a separate normal-tier family would need only its
     `env`; a mode in the release tier is none of 102's named kinds, so it would need a change to
     102: a follow-up after 0.1.0, if the owner asks.
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
   | scipy | `_lib/tests/test_ccallback.py`, `integrate/tests/test_quadpack.py`, `ndimage/tests/test_c_api.py`, `special/tests/test_dd.py`, `special/tests/test_round.py` (EXECUTED: each fails to load) | each imports one of scipy's seven `tests`-tagged C modules (`_test_ccallback`, `_test_multivariate`, `_ctest`, `_cytest`, `_test_internal`), which 037 links out of the product on purpose (its Decision 8) | spec 088 (the judge-only binary, never published; *default pending the owner's answer*: the lane widens 088's roadmap line to name scipy's seven modules and these five files; 088 is "after the packages", so in 0.1.0 they stay not selected) |
   | scipy | `_lib/tests/test_deprecation.py`'s tests that call `_test_deprecation_call` and `_test_deprecation_def` | the same, at call time: a class, not a file (it loads) | spec 088 |
   | scipy | `linalg/tests/test_cython_abi.py`, `optimize/tests/test_cython_abi.py`, `special/tests/test_cython_abi.py` (EXECUTED) | they read capsule names through `ctypes.pythonapi`, which the `ctypes` stand-in lacks, at import | spec 074 (the stand-ins' names at import); after it, each loads and its tests are a `no-ctypes` class |
   | scipy | `odr/tests/` (not staged) | `scipy.odr` is out of this line for good (037, Decision 9: ODRPACK is Fortran; scipy removes it in 1.19) | `context/specifications/037-scipy.md` |
   | scipy | `linalg/tests/_cython_examples/ilp64_test_package/tests/` (EXECUTED: fails to load) | an example package `test_extending.py` would build with meson in a subprocess; scipy installs only `extending.pyx` and `meson.build` of `_cython_examples` (READ: `linalg/tests/meson.build:39-43`), so it is not part of the installed suite | `README.md` |
   | scikit-learn | `cluster/tests/test_hierarchical.py`, `metrics/tests/test_dist_metrics.py` (EXECUTED) | they build memory-mapped arrays at import (`create_memmap_backed_data`), and the `mmap` stand-in raises | `README.md` (no `mmap`); spec 074 if it changes the stand-in |
   | scikit-learn | `neighbors/tests/test_neighbors.py` (EXECUTED, the sample) | it imports a constant from `metrics/tests/test_dist_metrics.py`, which cannot load. The whole-suite collection loaded it only because pytest had kept the half-imported module from an earlier file: an order the judge does not rely on | `README.md`; spec 074 as above |
   | statsmodels | `discrete/tests/test_constrained.py` (loads `spector` at import, line 29), `emplike/tests/test_anova.py` (loads `star98` at import, line 12) (READ by the review; INFERRED to fail to load until the survey) | a dataset 045 leaves out for its terms is loaded at import, so the file cannot load and every test in it is lost, not only the dataset's | `README.md` (045's list of the thirteen) and the owner's answer to question 83: approving a dataset ships it and the file loads (*default pending the owner's answer*) |

   **Each not-selected file gives its collected count from the survey** (the review, L3): what a
   row costs is stated in tests, not only in files (`neighbors/tests/test_neighbors.py` alone holds
   1,029, EXECUTED by the drafting probe). The lane may name scikit-learn's three `mmap` files in
   074's roadmap line, so they have a numbered closer.

   Selected although they may skip whole: scipy's `datasets/tests/test_data.py` (`importorskip
   pooch`), scikit-learn's dataset fetcher tests (skipped without the network variable),
   statsmodels' `base/tests/test_polars_compat.py` (`importorskip polars`).

9. **Known failures are classes, by test id, each one gap** (066, Decision 9). Expected from the
   probes and the reads, each to be measured; members per class come with the survey:

   | class (per group) | match | evidence | closes with |
   |---|---|---|---|
   | `no-threads` | `can't start new thread` | 9 in scipy's sample (EXECUTED); 31 scipy, 10 scikit-learn and 3 statsmodels files name threads (READ) | `README.md` |
   | `no-native-id` | `has no attribute 'get_native_id'` | 335 in scipy's normal folders (the survey, EXECUTED). **Split by where the call is** (the delta review, D-L2): the 288 in `io`'s tests, whose temporary file names the tests make from `threading.get_native_id()`, are `no-native-id-test-names`; the members whose call is the library's own, in uarray's `set_backend` and `skip_backend` (`scipy/_lib/_uarray/_backend.py:270,299`, READ by the review; `fft/tests/test_backend.py::test_backend_call[…]` among them), are `no-native-id-uarray` | both `README.md`. **The README text under the class says, in words:** "`scipy.fft.set_backend` and `scipy.fft.skip_backend` (and every uarray `set_backend`/`skip_backend` in scipy) raise `AttributeError: module 'threading' has no attribute 'get_native_id'` in this build: the runtime's `threading` names no native thread id on WASI. Calling `scipy.fft`'s functions directly is unaffected; only switching backends fails." The library's call is a product finding as well: the lane gives it a number (its likely fix is the runtime's `threading` naming the one thread's native id on WASI, not a scipy patch), and that number becomes `no-native-id-uarray`'s closer when it is reserved |
   | `enotsup-io` | `OSError: [Errno 58] Not supported` | 21 in `io` (`test_fortran.py`, `test_wavfile.py`, `test_paths.py`; the survey, EXECUTED). **The call** (the delta review's D-L2): numpy's `fromfile` and `tofile` duplicate the file's descriptor (`os.dup`), which WASI preview1 refuses with `ENOTSUP` (the product's `fcntl` refusal, `recipes/fcntl_dup_refusal.c`, answers as wasi-libc's own `dup` does); `scipy.io.FortranFile` (`_fortran.py:165-168, 270`) and `wavfile` (`wavfile.py:516, 923`) call them (READ). **EXECUTED 2026-10-21** in the guest on set `d0d91cef`: `np.arange(4.0).tofile("/tmp/w/p.bin")` raises `OSError: [Errno 58] Not supported` with a path too, so it is numpy's call, not scipy's. The build confirms each member from its traceback | `README.md` ("`numpy.fromfile` and `ndarray.tofile` fail with `ENOTSUP`, given a path or a file: WASI has no `dup`. Write `a.tobytes()` to the file, and read with `numpy.frombuffer(f.read(), dtype)`. `scipy.io.FortranFile` and `scipy.io.wavfile` fail the same way, since they call them") |
   | `no-processes` | `does not support processes` and the `multiprocessing` messages the survey records | `MapWrapper` pools, `differential_evolution(workers=2)`, statsmodels' `test_package.py`, scikit-learn's `experimental` tests that start `sys.executable` (READ) | `README.md` |
   | `no-mmap` | `mmap is unavailable` | 41 in scikit-learn's sample (EXECUTED); scipy's `io` tests with `mmap=True` (READ) | `README.md` |
   | `no-fp-exceptions` | the `DID NOT WARN` and `DID NOT RAISE` lines of floating-point warnings | wasm has no floating-point exception flags; 099 keeps numpy's own software flags, not the hardware's, so a float division by zero in a ufunc loop warns nothing (READ: 099's Decision text) | `README.md` |
   | `left-out-datasets` | `FileNotFoundError` naming `statsmodels/datasets/<name>/` | 19 statsmodels test files load one of the thirteen datasets 045 leaves out for their terms (EXECUTED: `sm_datasets.py`), `test_glm.py` and `test_discrete.py` among them. **Run-time failures only:** a file that fails at import is a Decision 8 row, never a member (the review, L3). The suite judges the product as shipped; staging the CSVs would not reach the tests, since 045's patch reads package resources from the zip (*default pending the owner's answer*) | `README.md` (045's list of the thirteen) and the owner's answer to question 83: approving a dataset ships it and empties its part of the class |
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
    - **A test the judge's counted clock never lets end runs with a clock step of its own** (the
      delta review, D-M3). `signal/tests/test_signaltools.py::test_choose_conv_method[numpy]`
      calls `choose_conv_method(..., measure=True)`, whose `_timeit_fast` raises `number` by
      powers of ten until one `timeit` interval reaches 0.5 ms, up to 10⁹ calls
      (`signal/_signaltools.py:1231-1250`, READ). Under the judge's clock each read advances
      1 µs, and `timeit` reads twice per interval, so the interval never reaches 0.5 ms and the
      loop never ends (the survey: more than 600 G alone, no outcome). `guest.run` already takes
      `clock_step_ns`; at 1 ms the first interval passes at `number = 1`.
      **EXECUTED 2026-10-21** (main tree's set `d0d91cef`, the stage of Decision 4, `-k
      "test_choose_conv_method and not _2"` on the file, no `-m`, `clock_step_ns = 1_000_000`):
      **passed, 37.92 G for the session** (the start and the collection of the file's 12,370
      tests included), one outcome, exit 0.
    - **So it runs in the release tier, in its own group.** `signal/tests/test_signaltools.py`
      is split by `[[split]]` anyway (Decision 11); the split's first group is
      `scipy-signal-conv-method` with expression `test_choose_conv_method and not _2`, and it
      carries a new group key, **`clock_step_ns = 1_000_000`**, with `clock_reason = "the test
      repeats a call until the clock has advanced 0.5 ms; the judge's clock advances only when
      read"`. Its cap is the rule's from its measured fuel (37.92 G measured here; 57 G by the
      rule; the build measures the group as built). The harness passes the key to `guest.run`
      for that group's run only.
    - **The key's rules** (Decision 14): allowed only on a release-tier group, only with a
      non-empty `clock_reason`, only with a value from 1 µs to 1 ms; and **a group with the key
      whose stream holds more than one outcome is red** ("a changed clock step reaches other
      tests"), so the step can never widen to a group of ordinary tests unnoticed. The default
      step is unchanged for every other run of every family.

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
    - **scipy's `special` and `stats` release sessions, measured to the end under a 20 T cap
      each** (the delta review, D-L1). The survey stopped both at its 6 T session caps. The build
      runs each once, locally by node id with `--tier release`, capped at 20 T. A session that
      ends under it is packed into groups by the bound. A session that reaches 20 T is split by
      `[[split]]` at the file where it stopped, each part measured again under the same cap, and
      the split recorded in the landing notes. The memo then states the release tier's measured
      total and its darwin minutes at `-n 3`, so the lane can book the release acceptance. **A
      lead for it:** `special/_mptestutils.py:385-400` enforces mpmath's time limits with
      `sys.settrace` and `time.time()` where there is no `SIGALRM`, as in WASI, reading the clock
      on every trace event; the build says whether that is where `special`'s fuel goes, and
      whether a clock step (the `clock_step_ns` key, Decision 10) belongs there too.

12. **The release: two normal-tier shards for the smoke groups, and release-tier shards for the
    rest** (revised 2026-10-21 for Decision 7's owner rule and D-M2's cover).
    - **Normal tier:** the four smoke groups (770.6 G measured) in two Linux shards by 066's 725 G
      packing: `upstream-sci-smoke-a` (`scipy-smoke-a` and `-b`, 429.1 G plus the derived run's
      8.6 G) and `upstream-sci-smoke-b` (`scikit-learn-smoke` and `statsmodels-smoke`, 341.5 G);
      each about 55 to 140 s of guest time plus about 60 s of setup, on every release run; the
      lane's darwin judge runs them at every landing (about 140 s of guest time at 0.18 s per G).
    - **Release tier:** every other group of the three families in release shards of 102's kind,
      Linux only, at most about 725 G each, run only where 102 runs them (the tag run, the dry run
      on main before a tag; no branch run, Decision 7): about **74 to 80 shards**
      for the measured at least 53 T (the price below). A 725 G shard is 116 to 225 s of guest
      time plus about 60 s of setup.
    - **The derived run counts in every scipy shard** (Decision 5): 8.59 G measured, added once to
      each scipy shard's packing and to its 360 s bound.
    - **The job count.** On a normal run the Linux matrix gains one job. On a release-tier run it
      gains about 75, which at 101's 20 parallel jobs is about four more waves of four to five
      minutes: about 15 to 25 more minutes of wall clock on the tag run and the dry run on main
      (INFERRED from the packing; the branch run with `release-tier: true` measures it).
    - **Linux only in the release**, as 066's: fuel is ratcheted on the lane's darwin judge; G5
      compares `passes` and `passed_digest` between the Linux record and the lane's.

13. **`packages.toml`: three suites, and no package left closing with 095.**
    - scipy, scikit-learn and statsmodels become `kind = "suite"` (statsmodels `later` with the
      split's closer if Depends on's third path applies).
    - OpenBLAS stays `via scipy`, now a suite that runs.
    - formulaic, interface-meta and wrapt stay with 067 (the owner, 2026-10-20).
    - **The check of it:** after 095, no entry names `spec 095` as its closer (criterion 10).

14. **The rules check, widened** (066's Decision 14, plus):
    - `package_inits` is a boolean; when true, every ancestor package of every staged folder is a
      package the product has (the zip's names and the builtins, from the artifact set's lists)
      and a generated `package_paths` entry, each a tarball folder holding an `__init__.py`
      member; a staged folder under a package the product lacks is refused, never staged (the
      review, L1);
    - each `derived` entry's script is a tarball member under a staged or support folder; its
      `inputs` folder holds members; its output's folder is a staged folder and the output is not
      a member; its `fuel` is at most the cap rule's 1.5 times its `measured`; the family names one
      `derived_row`, a group of the family (the review, M1);
    - `clock_step_ns` is a release-tier group key only, with a non-empty `clock_reason` and a
      value from 1,000 to 1,000,000 ns; a run of such a group with more than one outcome is red
      (Decision 10; the delta review, D-M3);
    - `env` is a family key only (no group carries one) and names only the variables
      `packages.py`'s per-family constant allows (Decision 7), each with a reason line in the TOML;
      the forbidden names of Decision 7 are refused in every family (the review, L6);
    - (the draft's rule that the staged `package_drive.py` hashes equal to the repository's is
      dropped: `Session._prepare` copies that file, so it holds by construction, and "the driver is
      not edited" is a fact of the diff, which the review reads; the review, L5);
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
                                       derived (makenpz.py: boost, gsl, local; inputs, caps,
                                       derived_row), env {SCIPY_XSLOW} for every group,
                                       marker / release_marker (102), cwd /tmp/work, two smoke
                                       groups (normal, `smoke = "…"`), a marker release group
                                       over their paths, path release groups by subpackage
                                       (`release_by = "path"`), [[split]]s (the clock-stepped
                                       conv-method group), [smoke_cover], [[not_selected]],
                                       [[expected]]
tests/upstream/scikit-learn.toml     grant /upstream-scikit-learn, stage_folders (sklearn/**/tests),
                                       package_inits, support_files [the two conftests],
                                       env {SKLEARN_RUN_FLOAT32_TESTS, SKLEARN_SEED}, the smoke
                                       group, path release groups, [[split]] for
                                       tests/test_common.py, [smoke_cover] (Decision 7)
tests/upstream/statsmodels.toml      grant /upstream-statsmodels, stage_folders, package_inits,
                                       support_files [statsmodels/conftest.py], the smoke group,
                                       path release groups, [smoke_cover]
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
2. scipy only: the derived runs (Decision 5), each in a fresh root with the stage read-only and
   its own cap; each output read with `lstat` and checked (a regular file, under the bound, a zip
   with at least one `.npy` member) before it is copied into the stage; the stage sealed read-only
   (089); the facts kept for the `derived_row` group.
3. Each group: `guest.run(snapshot, ["-u", "/upstream-<package>/judge/package_drive.py",
   "<package>", "<group>"], …, env=ENV | the family's env (never a group's), fuel=<cap>,
   preopens=[(grant, stage, False)],
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
- **The plain binary, and macOS and Windows release shards** (066, Decisions 11 and 12). The
  reason, in words (the review, N2): the guest's fuel and outcomes do not depend on the host,
  the lane's darwin judge runs every normal group at every landing, and the Windows own-guest
  shards already cover the host's WASI file semantics; no system runs these suites on Windows,
  as with 066's.
- **Wall-clock.** No check reads a clock (§4.9); every time below is an estimate.

## Acceptance criteria

Each is counted; none times anything. Each check is written first and seen failing against today's
code or a stand-in; the builder records each failing assertion in the landing notes.

1. **The rules.** `test_upstream_files_are_well_formed` passes with Decision 14's rules on the three
   new TOMLs. `tests/unit/test_packages.py` variants each fail with their own line: a
   `package_inits` family whose generated entry names a folder with no `__init__.py` member; a
   staged folder under a package the product lacks; a `derived` script that is not a member; a
   `derived` `inputs` folder with no member; a `derived` output that is a member, or outside a
   staged folder; a `derived` cap above 1.5 times its `measured`; a family with `derived` and no
   `derived_row`; a group carrying `env`; an `env` variable not in the family's constant; `env`
   setting `HOME`, `PYTHONPATH`, `SCIPY_HYPOTHESIS_PROFILE` or `SKLEARN_SKIP_NETWORK_TESTS`;
   `clock_step_ns` on a normal group, without `clock_reason`, or at 2 ms; and a stand-in stream
   of two outcomes for a group with the key, red. **The cover, held:** each family TOML
   carries `[smoke_cover]`, one entry per compiled family of Decision 7's rule (the subpackages
   of the product's builtin module names under the package, read from the artifact set when
   present), each naming a smoke path, a golden job line, or `release-only` with its reason; a
   compiled family with no entry, a named smoke path that is in no smoke group, or a
   `release-only` entry for a family of Decision 7's item 2 is refused (a rules row over the real
   TOMLs, so a re-pin that adds a compiled family, or an edit that drops a cover, is red).
2. **The derived run, on a synthetic tarball** (no real scipy): a script that writes a valid
   output stages it, and its SHA-256 and fuel are facts of the `derived_row` group and of no other
   row, whichever group the session runs first; one that exits 1 fails every group of the family,
   named; one that writes nothing fails them, named; one that writes an `.npz` with no arrays (as
   makenpz does with an empty input folder) fails them, named; one whose output is a symbolic link
   or past the size bound fails them, named, and the link is never followed; one that passes its
   cap stops there and fails them, named.
3. **The survey, then the baseline.** The memo exists, labelled EXECUTED, written before any
   check, TOML or harness line, with each group's outcomes by id, fuel, traps and collection
   errors, both tiers; its delta has a confirmation verdict. Each group check, run before its
   TOML lists and gaps exist, fails with its findings.
4. **With the TOMLs, the lists and the gaps complete**, the run on that set gives each group check
   passing; each class and trap check failing as its gap says; the numbers (passes, fuel, classes,
   members) in the landing notes, equal to the memo's or explained.
5. **Fuel repeats.** Each smoke group run twice, restaging between the runs: equal outcomes and
   `passed_digest`; on darwin equal fuel within `sameness.py`'s tolerance. The release groups once
   each, on darwin, with scipy's `special` and `stats` slow groups measured to the end (the
   survey's caps stopped them).
6. **Nothing else moves.** The ratchet against the base: every numpy, pandas, CPython and 066 row
   lost 0, grew 0. **A new unit check, written first** (the review, L5: 066 has no such check),
   compares each of 066's six families' staged file list and group JSON with the base's, byte for
   byte, and numpy's, pandas' and CPython's stage manifests too.
7. **The shards and the partition.** 063's `test_release_shards_cover_the_judge` and the workflow
   scan pass with the new shards; each smoke group is in exactly one normal Linux shard and each
   release group in one release shard (102's rule). **A unit check, written first**, collects a
   synthetic family with a smoke group over two of its files and release groups over all of them,
   and shows every collected test in exactly one tier: none in both, none in neither (the owner's
   rule, Decision 7). Each family's smoke groups' measured fuel is at most 500 G together (102's
   `SMOKE_BUDGET`, *For 102* item 5), each group under the 480 G bound, and the four together under
   1 T (a rules check on their `measured` values). The smoke kind's rows of *For 102* are 102's;
   095 adds the same rules run on its three real TOMLs (`test_upstream_files_are_well_formed`), as
   `smoke/split.py` ran them on the plan (Decision 7).
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
    within 360 s, or Decision 12's move made and recorded. **No dispatch with `release-tier`
    true** (Decision 7: no branch run runs release groups). The release groups are measured once
    each locally by node id with `--tier release` (criterion 5); the release tier's measured total
    and 095's `[[claim]]` block in `context/release-tier-claims.toml` are written from those runs
    (102's Decision 6 as *For 102* item 6 widens it). The first CI run of the release shards is
    the dry run on main before 0.1.0's tag.
13. **The lane's dry run after landing**, on main's exact commit, as 063's criterion 13.

## The price (measured by the survey, 2026-10-21; Decision 7 as the owner ruled)

- **Normal tier: 770.6 G** per full judge, the four smoke groups chosen by Decision 7's rule
  (EXECUTED 2026-10-21, each group measured whole on set `d0d91cef`), plus the derived run's
  8.6 G per scipy stage: about 7 % of today's about 11.2 T of upstream fuel. The lane's darwin
  accept grows by about 140 s of guest time, under 60 s of wall clock at `-n 3`; a release run by
  two Linux jobs. (The survey's hand-picked smoke groups were 277.6 G; D-M2's cover costs the
  difference.)
- **Release tier: at least 53 T** (the survey, EXECUTED: scipy's normal-marker tests 7.35 T and its
  slow, xslow and keyword cases at least 22.02 T; scikit-learn 9.61 T; statsmodels 14.23 T; less
  the smoke groups' share). A lower bound: scipy's `special` and `stats` slow sessions stopped at
  the survey's 6 T caps, and the build measures them to the end under a 20 T cap each (Decision
  11, D-L1): so the release tier is at most about 81 T by that bound (53 T plus 14 T more for
  each), and the memo states the measured total before the lane books the release acceptance.
- **The release acceptance before a tag** (102, Decision 5) grows by about 160 minutes of guest
  time on darwin, about 55 minutes of wall clock at `-n 3`, or more by the bound above (INFERRED
  at the survey's 0.18 s per G).
- **Caps** by the rule, 1.5 times: about 1.16 T for the smoke groups; at least about 80 T for the
  release groups.
- **Linux shards:** two normal-tier shards (`upstream-sci-smoke-a`, `-b`), and about 74 to 80 release-tier
  shards of at most 725 G, adding about 15 to 25 minutes of wall clock to the tag run and the dry
  run on main (Decision 12; INFERRED from the packing).
- **The survey:** done, about 3 hours of guest time in one process (the memo).

## The claim list's shape (for the lane, filled in by the build)

- **Gained rows, normal tier:** `test_upstream_suite[<smoke group>]` for the four smoke groups,
  with metrics `fuel` and `passes` and 066's facts, plus `derived` on scipy's `derived_row` group
  only if that group is a smoke group (else the release tier's); the classes their failures fit,
  each a gap.
- **Gained rows, release tier:** every other group's `test_upstream_suite[<group>]`,
  `test_upstream_class[<group>-<class>]` for each class with members, and
  `test_upstream_trap[<id>]` for each trap: new rows in 102's `release_tier` list on a normal
  accept, accepted only at the release acceptance before a tag (102, Decision 5). **Their claim
  block** goes in `context/release-tier-claims.toml` (102, Decision 6), written from the builder's
  local `--tier release` runs by node id (the review, L8; no branch run runs release groups,
  Decision 7).
- **The clock-timed test** (`test_choose_conv_method[numpy]`) runs in its own release-tier split
  group with `clock_step_ns` (Decision 10): a release-tier row like any other, no gap.
- **Moved rows: none.** numpy's, pandas', CPython's and 066's rows: lost 0, grew 0.
- **Retired: none. Passes moved: none.**
- **The judge hash changes**: the accept-judge text names the three TOMLs, `.ini`s, the expected
  lists, the harness keys, the gaps, `packages.toml`, the citation rule's retired allowances, the
  shards and the workflow.
- **No `--accept-growth`**, unless the base brings one.

## For the lane

- **Wave kind: build-class** (the release workflow; no artifact byte, no `scripts/`, `recipes/` or
  `downloads/` line). It may ride as one of a wave's two other build-class entries, after 045 and
  102.
- **Base.** Rebased onto the structural chain's tip `727bd4c` on 2026-10-20 (context only, no
  conflict). The builder rebases onto main after the chain lands, before writing code, since the
  citation rule exists only there (the review, N4).
- **Release-tier claims:** the builder's local `--tier release` runs by node id write 095's block
  in `context/release-tier-claims.toml` (102, Decision 6, widened by *For 102* item 6); no branch
  run with `release-tier: true`.
- **Route *For 102* to 102's builder** (the smoke kind, its rules, its unit rows, the ledger's
  widened sentence). 095 is built on 102's tip once 102 carries it and is reviewed.
- **The owner's answers** (question 110, then the standing rule of 2026-10-21): 088 widened to
  scipy's seven test modules and five files (Decision 8); the modes README-only for 0.1.0,
  copy-on-write dropped, `SCIPY_XFAIL` added, mode-gated skips counted (Decision 7); each suite
  in the release tier whole with a smoke group per package in the normal tier, in place of the
  15 T threshold (Decision 7); statsmodels' left-out datasets a README class, with import failures
  under Decision 8 (Decisions 8 and 9).
- **No reservation for the clock-timed test**: it runs, with the existing clock step (Decision
  10). **Do reserve** a number for the uarray `get_native_id` product finding
  (`no-native-id-uarray`'s closer, Decision 9).
- **074's line:** the lane may name scikit-learn's three `mmap` files there (Decision 8).

## For 102: the smoke kind (a request; the delta review, D-M1)

The owner's rule of 2026-10-21 puts each of the three suites in the release tier whole, less a
small normal-tier smoke selection. 102 at `8fb3df7a` cannot hold that: a release group must be a
marker, keyword or regrtest-list group (067 adds node-id groups), and "the marker release groups'
paths taken together are exactly the normal groups' paths taken together" (`tiers.rule_errors`).
A release group of whole paths that no normal group holds is refused. 095 asks 102's builder for
the change below, in 102's own branch, reviewed with 102. 095 is then built on it. Nothing in it
changes a family that names no smoke group: numpy's, pandas', contourpy's and CPython's TOMLs, JSON
and checks stay byte for byte what 102 makes them.

**The change, in 102's terms** (Decision 2 gains a kind (d); Decision 3 gains it in its list; check
1 gains the rows below):

1. **A group key `smoke`** (a string): on a normal group of a pytest family, the reason in words
   that this group is the family's smoke selection. A family is a **smoke family** when any of its
   groups carries it. In a smoke family every normal group carries a non-empty `smoke`; elsewhere
   no group carries it.
2. **A fourth kind, `release_by = "path"`**: a release group of a smoke family that runs its paths
   whole. `tiers.KINDS` becomes `("marker", "keyword", "path")`. In a smoke family with no
   `release_marker`, `kind_of` returns `"path"` for a release group without `release_by`; with
   one, `release_by` is required (as for a family with two kinds today). A `release_by = "path"`
   group outside a smoke family is refused ("of no named kind").
3. **The argv, by construction.** A path release group runs with no `-m` (`marker_of` returns
   `""` for it: it runs every test of its paths, whatever upstream's markers say) and no tier `-k`
   (`tier_filter` returns `None`); its `[[split]]`'s expression only, as for any group. **It
   ignores each smoke path its paths hold**: `--ignore=<path>` for every smoke path under one of its
   paths, beside the family's `not_selected`. So a folder can be a release path while two of its
   files are smoke files, and those two files run in the normal tier only.
4. **The paths rules of a smoke family** (in place of nothing; 102's marker rule still holds over
   the smoke groups, unchanged):
   - a path release group's path is never a smoke path or inside one;
   - no path is in two path release groups, except a file split by `[[split]]` (102's rule, for
     the new kind);
   - **when the tarball is present** (as 066's member rules read it): every test file the family
     stages (a member matching `test_*.py` or `*_test.py` under a `stage_folders` entry, less
     `not_selected`) is under exactly one smoke path, or else under exactly one path release
     group's path. A file in neither is refused, named ("in no tier");
   - each smoke path holds at least one such test file;
   - a smoke family has no `[[release_select]]` (it moves whole paths; a keyword split inside a
     smoke file is not needed by 095 and stays refused until a specification asks for it);
   - with a `release_marker`, the marker release groups' paths are exactly the smoke paths (102's
     rule as written, since the smoke groups are the normal groups), so a smoke file's marked
     slow tests run in the release tier and the truth table keeps them out of the normal tier.
     Without one, the smoke files run whole in the normal tier and no marker release group exists.
5. **A budget.** A smoke family's smoke groups' `measured` sum to at most 500 G (`tiers.
   SMOKE_BUDGET`, about 4.5 % of the upstream normal tier's 11.2 T today), so "smoke" cannot grow
   into a second normal tier unnoticed. A larger selection is a judge change with its reason.
6. **Decision 6's ledger.** "writes its block from its branch run with `release-tier: true`
   (required for it)" gains "or from its builder's local `--tier release` runs by node id, when no
   branch run runs release groups" (the owner's rule of 2026-10-21: "We only run slow tests when we
   are trying to publish to pypi"). 095 writes its block that way (criterion 12).

**The unit rows** (102's check 1, each failing with its own line; and check 2 for the argv), on a
synthetic smoke family of a three-file tarball (`pkg/a/tests/test_x.py`, `test_y.py`,
`pkg/b/tests/test_z.py`), smoke group over `pkg/a/tests/test_x.py`, path release groups over
`pkg/a/tests` and `pkg/b/tests`:
- clean as given; its path release group over `pkg/a/tests` carries
  `--ignore=<grant>/tree/pkg/a/tests/test_x.py` and no `-m`, with or without a family `marker`;
- the `pkg/b/tests` group removed: refused, "pkg/b/tests/test_z.py is in no tier";
- a path release group over `pkg/a/tests/test_x.py`: refused, "lies in a smoke path";
- `smoke = " "`, or a second normal group without `smoke`: refused;
- `release_by = "path"` in a family with no smoke group: refused, "of no named kind";
- a `[[release_select]]` in the smoke family: refused;
- a smoke group whose `measured` takes the family past 500 G: refused;
- with `release_marker = "slow"` and `marker = "not slow"`: clean only with a marker release group
  over exactly `pkg/a/tests/test_x.py`.

**Proved on the real stage** (EXECUTED 2026-10-21; `../research/2026-10-21-scipy-sklearn-statsmodels-own-tests-under-the-runtime/smoke/split.py`
and its `plan.toml`, run on the three pinned tarballs, each SHA-256 checked first). The script
carries these rules as written above and runs them on the smoke groups of Decision 7 and one path
release group per staged tests folder (the survey's sessions; the build packs them by the bound),
then on six mutants of each family's plan. Its output is `split.txt` beside it; the numbers are in
Decision 7.

## Delta from the survey (2026-10-21, for the delta review)

The survey (`../research/2026-10-21-scipy-sklearn-statsmodels-own-tests-under-the-runtime.md`,
EXECUTED on darwin-arm64: scipy and scikit-learn on wave 09's set `142bdd38`, statsmodels on 045's
build-reviewed set `14adfa5f`) replaces this specification's INFERRED numbers. What it changes, by
Decision; a fresh reviewer rules on each before anything is built (Decision 1).

1. **The price, measured.** The survey's tiers, by folder: scipy's normal-marker tests 7.35 T,
   scikit-learn 9.61 T, statsmodels 14.23 T (statsmodels 4.7 times 045's inferred 3 T; together
   31.18 T, 2.8 times today's about 11.2 T); scipy's slow, xslow and keyword cases at least
   22.02 T (`special` and `stats` stopped at the survey's 6 T caps). Under the owner's rule of
   item 2 the price section now reads: **normal tier 277.6 G** (four smoke groups, measured),
   **release tier at least 53 T**, one normal Linux shard and about 74 to 80 release shards.
2. **Decision 7's 15 T threshold could not be met, and the owner replaced it** (2026-10-21, a
   standing rule; Decision 7 records the owner's words). The survey found that even all of
   scikit-learn in the release tier would leave scipy's and statsmodels' 21.6 T in the normal
   tier. The owner: "we need to have fast tests and slow tests. We only run slow tests when we are
   trying to publish to pypi, … otherwise we should only run the tests needed to confirm our new
   edits are working." So the three suites go to the release tier whole, and each package keeps a
   normal-tier smoke group, chosen from the survey and measured (EXECUTED 2026-10-21):
   `scipy-smoke-a` 80.2 G (SuperLU, ARPACK, trust-region, ODEs, k-means), `scipy-smoke-b` 67.6 G
   (fftpack, MATLAB files, Cholesky and Toeplitz through OpenBLAS), `scikit-learn-smoke` 69.4 G
   (svm, covariance, cross-decomposition, HDBSCAN), `statsmodels-smoke` 60.4 G (formulas, ARIMA,
   GLM families, filters, summaries): 277.6 G in all, each under 100 G, every failure in them a
   member of a measured class. Nothing leaves the full suite; a unit check proves the partition
   (criterion 7). Decision 7 also proposes that a landing changing a package's own build runs that
   package's release groups on its branch run, the delta review to confirm or strike.

3. **A test the judge's clock never lets end** (Decision 8 gains a row, and the spec gains a
   kind): scipy's `signal/tests/test_signaltools.py::test_choose_conv_method[numpy]` times both
   convolution methods until a fixed time passes (`measure=True`). Under the judge's counted clock
   (each read advances 1 µs) it spent more than 3 T inside one session, and 600 G alone without
   an outcome. It is deselected by node id, never run, as a trap is, with its own row: reason "it
   repeats a convolution until the guest's clock has advanced a fixed time, which the judge's
   counted clock makes take more than 600 G", closer: a judge follow-up the lane reserves (a
   clock step for timed tests). Without it `signal`'s normal tier is 250.2 G.
4. **statsmodels' import failures: six files, not two** (Decision 8's statsmodels row grows):
   `discrete/tests/test_constrained.py` and `test_margins.py`, `emplike/tests/test_anova.py`,
   `genmod/tests/test_glm_weights.py`, `stats/tests/test_oaxaca.py`,
   `tsa/vector_ar/tests/test_vecm.py`, each loading a left-out dataset at import; and the
   `left-out-datasets` class holds 832 run-time failures (`spector` 428, `cpunish` 230,
   `star98` 65, `ccard` 42, `committee` 19, `scotland` 19, `fair` 10, `cancer` 7, `heart` 7, four
   single ones). It is statsmodels' largest class by far: the owner's answer to question 83 is
   what would empty it.
5. **Two more markers for statsmodels' `.ini`** (Decision 6): `thread_unsafe` (pytest-run-parallel's,
   313 uses) and `skip_randomstate_check`, both registered nowhere in its sdist; without them
   three files of `base/` failed to collect.
6. **scikit-learn's own wasm skip** (Decision 8, a row of its own): its
   `callback/tests/conftest.py` ignores the folder on wasm (`pytest_ignore_collect` returning
   `_IS_WASM`), so its 54 test functions are never collected. Upstream's choice; the README names
   it; not a test the judge leaves out.
7. **The classes, measured** (Decision 9; the memo's table): `no-native-id` is scipy's largest
   (335: `io`'s temporary names made from `threading.get_native_id()`); `no-processes` (44, `os`
   has no `pipe`), `no-threads` (39), `no-mmap` (16), `no-fp-exceptions` (12); two new ones,
   `enotsup-io` (21 in `io`, `OSError: [Errno 58] Not supported`; the build names the call) and
   `odr-stand-in-visible` (1: scipy's public-API check finds the `scipy.odr` stand-in module);
   release-tier `wasm32-memory` (2). scikit-learn: `no-mmap` 1,536 of its 1,547 failures, and
   `pillow-zlib-only` 4. statsmodels: `left-out-datasets` 832, and one `DLASCL` (a `nan` reaching
   LAPACK). About 25 single failures across the three are read one by one in the build, each a
   class with a closer or a finding.
8. **Mode-gated skips, for the README** (Decision 7): scikit-learn 1,077 skip because
   `SCIPY_ARRAY_API` is unset and 7,011 because an array-API backend is not installed; scipy 73;
   statsmodels none. scikit-learn's 211 `numpydoc` skips name a pure test-only package the kit
   lacks: a `kit_extra` candidate shared with 067 (Decision 6's "the survey confirms it" found
   one), pinned by whichever of 067 and 095 lands second.
9. **The start of a group costs 12 to 32 G** (Decision 11): 20.1 G for scipy, 26.2 G for
   scikit-learn and 31.8 G for statsmodels with every ancestor imported first. Importing only a
   group's own ancestors cut scipy's to 12.4 G, but statsmodels' tests import other packages'
   `tests` (`statsmodels.multivariate.tests` from `sandbox`), so the generated `package_paths`
   stays the family's whole list (Decision 4's rule) and the groups are made large, near the
   480 G bound, so the starts stay a few percent of each.
10. **The derived files, measured** (Decision 5): `boost.npz` 1,270,643 bytes (111 arrays,
    5.78 G), `gsl.npz` 51,433 (3, 1.24 G), `local.npz` 203,438 (8, 1.57 G): 8.59 G per scipy
    stage. **The bound becomes 2,541,286 bytes**, twice the largest measured output (the
    confirmation's condition), in place of the INFERRED 16 MiB.
11. **The keyword entries, by full id** (Decision 7; the confirmation's condition): 19
    `test_rv_generic[<i>-distdata<i>]` ids under `TestMakeDistribution`, four `test_accuracy`
    ids (`case68`, `case100`) under `TestTanhSinh`, and `test_axis_nan_policy_full or
    (test_axis_nan_policy_fast and kruskal)`; each id checked against a collection with
    `SCIPY_XSLOW=1` (`keywords.txt`). Their release session: 3.11 T, 4,832 passes.
12. **Unchanged:** no trap; the guard held (only each package's `conftest.py` loaded from the
    stage outside `tests`); every scipy not-selected file of Decision 8 is as drafted; the three
    scikit-learn `mmap` files are as drafted.

**What remains:** this delta's review (the owner has answered item 2 and the other three
defaults); then the build, from main after wave 09 and the chain, with each group measured as
built (the survey measured folders, not the final groups), the release tier's `special` and
`stats` measured to the end, and the about 25 single failures read.

### The delta review answered (2026-10-21, the builder taking over from the drafter)

Each finding is written into the Decisions; the review's Disposition of the delta says where.
In short, and superseding items 2 and 3 above where they differ:
- **D-M1:** *For 102: the smoke kind* asks 102 for a fourth kind (`smoke` on normal groups,
  `release_by = "path"` release groups that run their paths whole and ignore the smoke files under
  them, the paths rules, a 500 G smoke budget, and Decision 6's ledger widened), with its unit
  rows; `smoke/split.py` proves the split on the three pinned tarballs and refuses six mutants per
  family (EXECUTED). Item 2's `-k "not (S)"` is dropped.
- **D-M2:** Decision 7's smoke selection follows a stated rule (every compiled family from the
  product's builtin module names, by a smoke file or a named golden line; the review's named
  families and every carried patch by a smoke file; the main entry points; named exceptions), and
  its four groups are re-measured: **770.6 G** (scipy 207.4 + 221.8, scikit-learn 205.5,
  statsmodels 136.0), in place of item 2's 277.6 G.
- **D-M3:** item 3 is reversed. `test_choose_conv_method[numpy]` **passed** in 37.92 G with a
  1 ms clock step (EXECUTED); it runs in the release tier in its own split group with the new
  `clock_step_ns` key (Decision 10). No test is left out of both tiers, and no reservation is
  needed.
- **D-L1:** `special` and `stats` are measured to the end under 20 T each (Decision 11).
- **D-L2:** `no-native-id` is split by where the call is, the README names `scipy.fft.set_backend`
  and `skip_backend` raising, and `enotsup-io` names numpy's `tofile`/`fromfile` (EXECUTED: a path
  fails too) (Decision 9).
- **D-N1 (rule (8)):** struck by the owner's words; no branch run runs release groups (Decision
  7); 095's own release groups are measured locally (criteria 5 and 12).

## Landing notes

### The build, stopped part-way (2026-10-21, at the owner's pause): the resume point

**Not built yet; not reviewable yet.** The builder stopped at the owner's word ("finish the local
step, commit, push, start nothing new"). No CI run was dispatched (the owner paused new runs).

- **Base.** Rebased onto 102's final tip `861d5e4b` (stacked on 101's `1ebb992f`): no hunk to
  resolve, the 095 commits being context only and 102's last change (`gather.COLLECT_ARGV`) touching
  no file of 095's. The one in-process `pytest.main(` 095 adds (the partition check in
  `tests/unit/test_tiers.py`) passes `-p no:faulthandler`.
- **Set.** The main tree's frozen set, `SHA256SUMS d0d91cef`, cloned into the worktree
  (`cp -c -Rp`, every file's SHA-256 checked); the twelve pinned trees unpacked and patched with
  `fetch.py`'s own functions.
- **Built (code, judge files), green on the rules and units:**
  - `tests/harness/packages.py`: `package_inits` (generated `package_paths` and staged ancestor
    inits, never in `support_files`, so the guard finds one imported), `derived` with
    `derived_row` (the guest run in `Session._make_derived`, the output read with `lstat` and as a
    zip on the host, the bound 2,541,286 bytes), `env` (per-family `ENV_ALLOWED`, `ENV_FORBIDDEN`
    and any `PYTHON*`), the group key `clock_step_ns` with `clock_reason` (release groups only,
    1 µs to 1 ms, red past one outcome), `smoke_cover` (`SMOKE_ONLY`, job lines checked for their
    word), `component`; their rules. `upstream.py`: the three names and tarball patterns, the
    product's packages passed to the rules. The check file: the needs by component, the `derived`
    fact, and a new non-slow check, `test_every_compiled_family_has_its_smoke_cover`, which lists
    the product's builtin modules in the guest and holds each family's cover to them.
  - Unit rows, each seen failing on the base harness first (39 failed, 79 passed: the record is
    `../research/2026-10-21-scipy-sklearn-statsmodels-own-tests-under-the-runtime/the-build/data/base-unit-run.txt`):
    criterion 1's every variant, criterion 2's derived run on a synthetic tarball (valid, exit 1,
    nothing, an empty archive, a link, past the bound, past its cap; the facts on `derived_row`
    whichever group runs first), criterion 6's stage digests of the nine other families against
    `tests/fixtures/upstream-stages.json` (recorded with the base's harness), criterion 7's
    partition by pytest's own collection (it passes on the base too: the mechanism is 102's),
    criterion 8's fetch rows, criterion 9's pin and staged-init rows.
  - `tests/upstream/{scipy,scikit-learn,statsmodels}.{toml,ini}`, the expected lists, the gaps,
    `packages.toml` (the three are `suite`; the three citation allowances it held retired),
    `tests/release_shards.toml` (two normal shards, 91 release shards packed from today's
    numbers) and the workflow's lists, all generated by the tools kept under
    `../research/2026-10-21-scipy-sklearn-statsmodels-own-tests-under-the-runtime/the-build/`.
- **Measured (EXECUTED, darwin-arm64, set d0d91cef, the judge by node id with `--tier release`
  and a measurement plugin that records fuel whatever the verdict):**
  - the four smoke groups once (all failures classified); pass 1, every folder of the three
    suites (62 groups, 71.7 T, `scipy-special` and `scipy-stats` each stopped at the 20 T cap);
    pass 2, 91 of the 138 regrouped release groups (lanes 1 and 3; lane 2's 47 groups were stopped
    unrun at the pause, `scipy-special-1` among them, 83 minutes into its 20 T cap).
  - Where special's fuel goes (D-L1's lead): `test_mpmath.py::TestSystematic::test_betainc`
    alone passed 16.7 T at the judge's 1 µs clock without ending. mpmath's reference values are
    time-limited by `time.time()` read on every trace event, so the counted clock lets each point
    run 500,000 events. Alone, it passes in 63.3 G at a 100 µs step (more than 2 T at 10 µs, 22.6 G
    at 1 ms); `test_betaincc` passes in 26.8 G at 100 µs and runs past 600 G at 1 µs. Both are
    their own split groups of `test_mpmath.py` with `clock_step_ns = 100_000`. The other four
    time-limited tests xfail under 23 G at the default clock.
  - The remainder of `test_mpmath.py` after them measured 9.3 T in one group; `stats`' groups
    after `test_fit.py` 7.7 T in one. Single tests past the 480 G bound: `test_cont_basic_fit`'s
    johnsonsb, gompertz and exponpow cases (0.7 to 2.3 T each), `test_cont_basic[studentized_range]`
    (1.4 T), `test_basic_fit_mle[nchypergeom_fisher]` (1.4 T).
  - Measured so far: release tier 60.5 T over 133 groups (scipy 43.0 T, scikit-learn 8.65 T,
    statsmodels 8.84 T), 48 groups unmeasured; normal tier 0.86 T (the smoke groups, once).
- **Smoke cover, by the stated rule, two changes from the reviewed table** (for the build review):
  `scipy.optimize._lsq` is covered by `test_lsq_linear.py` (added to `scipy-smoke-b`), since
  `least_squares` never calls `givens_elimination` (only `lsq_linear`'s `trf` does); and
  `sklearn.metrics._pairwise_distances_reduction` by `test_pairwise_distances_reduction.py` (added
  to `scikit-learn-smoke`), since the golden job's `KNeighborsClassifier` uses `kd_tree`, which
  never reaches `ArgKmin`. Two more release-only families, each by item 5's rule (no golden line,
  every file past a smoke file's reach): `sklearn.ensemble` (classic gradient boosting) and
  `sklearn.manifold` (t-SNE). The smoke groups' measured values in the TOMLs for `scipy-smoke-b`
  and `scikit-learn-smoke` are still the delta's figures plus an estimate; criterion 5's two
  measured runs are not done.
- **Classes found beyond the delta's** (each read one by one; closers `README.md` unless named):
  `no-threads-results`, `mpmath-tolerance` (Ai', Bi at one point each by 1.2e-4; `yv` of order
  -5.6e25 finite where mpmath gives `-inf`), `float32-rounding`, `fit-flat-likelihood`,
  `enotsup-io-file-left-open`, `enotsup-io-no-warning`, `test-only-modules` (closer the roadmap's
  088); scikit-learn `no-openmp`, `package-in-zip`, `no-dev-null`, `wasm32-int128`, `no-dup`,
  `no-mmap-estimator-checks`; statsmodels `no-processes`, `wasm-is-not-emscripten` (upstream's
  `PYTHON_IMPL_WASM` is Pyodide's only), `upstream-xfail-platform`. No trap anywhere.

**What is left, in order:**

1. Pass 2's lane 2 (`build/095/pass2-lane2.txt`, 47 groups) and the groups capped in pass 2;
   then pass 3: repack every group still past 480 G that is not one test (`scipy-stats-1`,
   `scipy-special-mpmath-8`, `scipy-stats-fit-5`, `scipy-smoke-slow-propack-*`, `scipy-sparse-linalg`,
   and the others in `the-build/data/status.txt`) from the poller's per-test times, and measure the new
   groups; name each single test past the bound in its TOML (as `matplotlib-axes` is).
2. Classify every new group's failures (`classify.py`), regenerate the TOMLs, gaps and shards.
3. Criterion 5: the four smoke groups twice, restaging between, equal `passed_digest` and fuel
   within tolerance; their measured values from those runs.
4. The README's `@@…@@` counts, the CHANGELOG's, the memo's build section (the release tier's
   measured total and its darwin minutes at `-n 3`), and the claim block in
   `context/release-tier-claims.toml` from the local `--tier release` records.
5. The fast tier through the slot; push; one normal-tier branch run when the owner resumes runs,
   read back; the self-check list; then the build review.
