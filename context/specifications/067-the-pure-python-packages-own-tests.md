# 067 — the pure-Python packages' own tests in the release

- **Status:** drafted 2026-10-20 from main `1ce7381`; on its own branch,
  `spec/067-the-pure-python-packages-own-tests`, rebased onto main `5805af0` (the owner's answer
  on 0.1.0's scope: 045 and 067 both in 0.1.0, after wave 09). **Revised 2026-10-20 against its
  pre-build review** (`../reviews/067-the-pure-python-packages-own-tests-prebuild-2026-10-20.md`:
  "build once H1 to H3 and M1 to M4 are written in, the survey has run on main's set after wave 09
  with its delta confirmed, and the owner has answered Q1"). Every finding is written in; the
  section "Disposition of the pre-build review" says where. **The owner answered Q1 the same day**
  (the lane's message, 2026-10-20; "The owner's choices" below): formulaic, interface-meta and
  wrapt join 067 and statsmodels' own suite goes to 095; sympy's one test past every bound runs on
  CI in a shard of its own past the 360 s bound; and upstream's opt-in slow tests form a
  **release tier** that runs only on the publishing run and the pre-tag dry run on main, whose
  mechanism is spec 102 (reserved by the lane). **Revised 2026-10-21 for the owner's standing
  rule** (the lane's message, 2026-10-21; Decision 10): each package's own suite goes to the
  release tier whole, and each package keeps one small smoke group in the normal tier; tier
  placement and fuel thresholds are not questions for the owner. **Rebased 2026-10-21 onto main
  `d8fc73f`**: no conflict and no hunk to resolve (the branch's three commits touch only this file,
  its review and `sdists-067-revision.txt`). **Surveyed 2026-10-21** on the main tree's set
  `d0d91cef` (main after wave 09 plus wave 10's statsmodels, which carries 045's three packages),
  copied into the builder's worktree
  (`../research/2026-10-21-the-pure-python-packages-own-tests-under-the-runtime.md`, EXECUTED); its
  delta is "Delta from the survey" below, for a context-only delta review before anything is built
  (Decision 1). It pins 39 test sources in `downloads/SHA256SUMS` and `scripts/00_download.sh`, so
  it is build-class, and `MANIFEST` gains their pin lines: it changes the artifact set, so
  constitution §5.6 requires its pre-build review (done) and the delta's confirmation.
- **Owner:** Clay Gendron
- **Kind:** the build recipe's pins (39 lines in `downloads/SHA256SUMS`, 39 `tests` lines in
  `scripts/00_download.sh`), the judge, and the release workflow. No line of `src/` or `recipes/`
  changes; `python.wasm`, the snapshot and the stdlib zip do not change; `MANIFEST` gains 39
  `pin` lines and its `recipe` line for `scripts/00_download.sh` changes (Decision 3).
  - **New:**
    - `tests/upstream/<package>.toml` and `.ini` for each of the 42 packages of Decision 2;
    - `tests/upstream/kit-extra.txt`: the test-only pure wheels some suites import (Decision 6);
    - `tests/upstream/expected/<group>/<class>.txt` and their gaps in `tests/known_gaps.toml`;
    - the survey memo, `context/research/2026-10-2x-the-pure-python-packages-own-tests-under-the-runtime.md`
      (Decision 1).
  - **Changed:**
    - `downloads/SHA256SUMS`, `scripts/00_download.sh` (a `tests` function, fetched with
      `--tests` and by `fetch.py`, never by a plain build);
    - `tests/harness/pins.py` (`SOURCE_PATTERNS` for each test source), `tests/harness/packages.py`
      (066's families, widened: the wheel tie of Decision 4, `kit_extra`, `cwd_folders`,
      `docstring_packages`, `module_functions`, the support-file group path, the marker `D` lines,
      the tier key of Decision 10), `tests/harness/upstream.py` (`PACKAGE_SUITES` += 42),
      `tests/upstream/package_drive.py` (the items of Decision 5), `tests/upstream/fetch.py`
      (`tests` lines; the wheel beside each test source);
    - `tests/upstream/packages.toml` (39 entries become `suite`, three added as `suite`),
      `tests/release_shards.toml` and `.github/workflows/release.yml` (Linux shards packed from the
      survey, Decision 11);
    - `tests/unit/test_packages.py`, `test_upstream.py`, `test_shards.py`, `test_fetch_trees.py`,
      `test_pins.py`;
    - `README.md`, `CHANGELOG.md`, `context/progress/README.md`, one dated line in spec 063,
      `context/upstream/README.md` if a class closes upstream (none expected), `context/roadmap.md`.
- **Depends on:**
  - **066** (wave 08): `package_drive.py`, one family per package with its own grant
    `/upstream-<package>`, its keys (`stage_folders`, `package_paths`, `extra_sys_path`,
    `support_packages`, `support_files`, `cwd` as `"/tmp/work"` or `"tree"`, `cwd_files`,
    `docstring_modules`, `doctest_files`, `[[split]]`, `measured`), the guard over the product's
    modules, the cap rule (`rule_cap`) and the rules check. 067 adds keys; it changes none of 066's
    meanings and none of 066's families.
  - **Wave 09: 099, 100 and 101.** 100 changes `numpy.linalg`, which networkx's, sympy's, patsy's
    and formulaic's tests reach; 101 changes the shard plan, the matrix (`max-parallel: 20`) and
    its key over `downloads/SHA256SUMS` and `scripts/`. 067 was surveyed on a set with wave 09 and
    045 (`d0d91cef`); it is built from main's tip after 102 lands, or stacked on 102's reviewed tip
    (the 102 bullet below).
  - **045** (statsmodels, formulaic, interface-meta, wrapt; in 0.1.0 with 067): the three pure
    packages it adds are 067's (the owner, 2026-10-20). 067 is built after 045 lands, so the three
    are in the set it surveys; 045 names spec 067 as their closer in `packages.toml`, as 042 did for
    seaborn and reportlab. statsmodels' own suite closes with 095.
  - **102** (the release tier; `spec/102-the-release-tier`, tip `8fb3df7`: its machinery built,
    surveyed and delta-reviewed, its workflow half waiting for 101; **not yet landed or
    build-reviewed**): `tier`, `release_by`, the node-id group it leaves to 067, `release_checks`,
    the release shards (the pseudo-system `release`), the `release-tier` dispatch input, the
    ratchet's `release_tier` rows and `context/release-tier-claims.toml`. 067 needs all of it: with
    the owner's rule nearly every 067 group is release-tier. **So 067 is built after 102 lands**
    (102's Decision 15 says so), on main's tip then. **If 102 is build-reviewed and waiting in a
    wave** when 067's build is due, 067 is a stacked build on 102's reviewed tip (§4.14), its Status
    naming the base, rebasing onto main or the wave's tip when 102 lands. Neither the survey nor
    this revision needs anything of 102: both are context only. 067 adds one kind to 102's
    Decision 3, the path release group (Decision 10), which 095 needs as well.
  - **039** (tier A), **041** (networkx from its sdist), **042** (seaborn and reportlab): what the
    zip carries, from which pin. **023** and **033**: the four plot wheels and `METADATA`.
  - **063**, **065**, **050**, **051**, **089**, **091**, **052**, **002**, as 066 lists them.
  - **In flight:** **095** (scipy's, scikit-learn's and statsmodels' own tests) shares
    `kit-extra.txt` and the `kit_extra` key: whichever of 067 and 095 lands second rebases onto the
    first's file and rules, and no family's extras stage into another's. **101**: 067 rebases onto
    it (textual conflicts in `release_shards.toml`, `release.yml` and gather's `env:`); 067's pins
    change 101's set key once (Decision 3).
- **Research it stands on:**
  - The mechanism and the platform: `../research/2026-10-18-numpy-and-pandas-own-tests-in-the-guest.md`
    (pytest in the guest), `../research/2026-10-18-cpythons-own-tests-under-the-runtime.md`
    (families), `../research/2026-10-18-the-release-judges-in-parallel-shards.md` (the stage moves
    fuel), `../research/2026-10-17-what-else-the-default-profile-carries.md` (tier A, each
    candidate imported and run in the guest, EXECUTED there), spec 066's survey and build (the
    family mechanism, measured), and the README's platform facts.
  - Run 124 of the release workflow (`39451333969`, READ by the pre-build review): 43 jobs, 36 at
    once; 066's fourteen Linux shards 100 to 246 s each.
  - **Read and compared while drafting (2026-10-20), no guest run**, in
    `../research/2026-10-20-the-packages-own-tests-drafting/` (it lands with 066):
    - `sdists.txt`: the 34 PyPI sdists, each downloaded into an empty scratch folder and its
      SHA-256 recomputed equal to PyPI's; read with `tar` only;
    - `sdists-067-revision.txt`: the same for the five packages this revision adds (formulaic,
      interface-meta, wrapt, reportlab, and seaborn, whose sdist equals 042's pin);
    - `tag-archives.txt`: the release-tag archives of the eight packages whose sdists carry no
      tests (cloudpickle, cycler, et-xmlfile, openpyxl, threadpoolctl, tomli-w, xlrd, xlsxwriter);
    - `source-equality.txt` (EXECUTED on the drafting host, archives read as data): every `.py`
      file each pinned wheel installs is byte-identical to the same path in its sdist or tag
      archive; the pre-build review repeated it for the eight tag archives (EXECUTED, 0 differ);
    - `inventory.txt`, `collection-risks.txt`, `kit-extra.txt`: test counts, imports, conftests,
      configurations, and the readers that made them.
  - **Measured by the pre-build review** (EXECUTED, darwin-arm64, main's frozen set): `import
    sympy` 4.2 G of fuel; sympy's `core/tests/test_arit.py` 102 tests, 165.4 G (about 1.58 G a
    test); `simplify/tests/test_simplify.py` without its one `@slow` test 152.4 G (about 2.25 G a
    test), and that one test, `test_issue_17141_slow`, about 2,609 G alone; doctests of
    `more_itertools.recipes` (140 examples) and `tabulate` (97) found by import from the zip's
    bytecode and passing, 0 failed.

  - **Measured by the survey** (EXECUTED, darwin-arm64, `d0d91cef`, 2026-10-21; the memo
    `../research/2026-10-21-the-pure-python-packages-own-tests-under-the-runtime.md` and its
    folder): every family's whole suite and smoke group, the price, and the stage findings
    ("Delta from the survey"). A number below marked INFERRED is a packing or time estimate from
    those measurements.

## The problem

Spec 063's rule is that every package runs its own tests in the release, and the owner's rule
(`decisions.md`, "Every test of every package we build", 2026-10-20) is that every upstream test
of a package we build runs, never left out for convenience. 42 pure-Python distributions in the
product do not yet: the seven matplotlib and pandas need (fonttools, pyparsing, cycler, packaging,
python-dateutil, six, tzdata), tier A's thirty (spec 039), 042's seaborn and reportlab, and 045's
formulaic, interface-meta and wrapt. `tests/upstream/packages.toml` marks each `later`, closed by
spec 067 (or will, when 045 lands).

Most of them are pinned as wheels, and a wheel carries no tests. Four are pinned as sdists that do
(pyyaml, markupsafe, networkx, seaborn). So 067 must first decide where each package's tests come
from, and how they are tied to the bytes the product ships.

They matter because the product runs these packages in a place their authors never tested: in a
zip, as bytecode only, with no threads, no processes, no `dup`, shallow recursion and a 32-bit
address space. Spec 039 ran one job per package. Their own suites hold some 40,000 tests, plus
their doctests.

This specification makes the 42 suites judge jobs and release gates, as 066 does for the compiled
packages: a ratcheted pass count and fuel per group, every known failure a class by id, every test
not run named. By the owner's rule of 2026-10-21, each whole suite runs in the release tier,
before a publication, and a small smoke group per package runs in the normal tier, on every
branch run and at every landing.

## Decisions

1. **The survey comes first** (done 2026-10-21, EXECUTED, on `d0d91cef`). As 066's Decision 1:
   each family's outcomes by id, fuel, traps and collection errors, before any pin, TOML or shard
   line is committed; the memo is
   `../research/2026-10-21-the-pure-python-packages-own-tests-under-the-runtime.md`. **Its dated
   delta to Decisions 2, 5, 8, 9, 10 and 11 goes to a context-only delta review** (a fresh
   reviewer) with **the price** (fuel per tier, Linux shards per tier, the lane's added
   acceptance fuel, and whether Linux becomes the critical path). The price is a fact for the
   lane and the reviewer, **not a question for the owner** (the owner's standing rule,
   2026-10-21, Decision 10). Building starts on that verdict. The survey's sessions are by folder,
   not the final groups: the build measures each group as built and sets its `measured` and cap.

2. **The 42 packages, and where each one's tests come from.** Each is its own family, with the
   grant `/upstream-<package>` (066, Decision 2), `stage_folders` naming what is staged, and
   `cwd = "tree"` unless named. READ from the archives:

   | package | test source (pinned by 067 unless marked) | staged | found by |
   |---|---|---|---|
   | fonttools 4.67.0 | sdist | `Tests/` (185 modules `*_test.py`, data; 2,092 files, 15.6 MB) | `extra_sys_path` tree root |
   | pyparsing 3.3.3 | sdist | `tests/`, `examples/` (`examples/tiny/tests` is a group path, upstream's `tox.ini`; the rest support) | `extra_sys_path` tree root |
   | cycler 0.12.1 | **tag archive** `v0.12.1` (GitHub) | `test_cycler.py` (a support-file group path) | `extra_sys_path` tree root |
   | packaging 26.3 | sdist | `tests/` (31 modules, ELF fixtures) | `extra_sys_path` tree root |
   | python-dateutil 2.9.0.post0 | sdist | `tests/` (13 modules, `conftest.py`), `docs/exercises/solutions/` (upstream's `python_files` selects `*_solution.py`) | `extra_sys_path` tree root |
   | six 1.17.0 | sdist | `test_six.py` (a support-file group path) | `extra_sys_path` tree root |
   | tzdata 2026.5 | sdist | `tests/`, `VERSION` (support: `test_version` reads it) | `extra_sys_path` tree root |
   | openpyxl 3.1.5 | **tag archive** `3.1.5` (Heptapod) | `openpyxl/**/tests/`, `openpyxl/tests/data/` (161 modules) | `package_paths` per subpackage |
   | et-xmlfile 2.0.0 | **tag archive** `2.0.0` (Heptapod) | `et_xmlfile/tests/` | `package_paths` |
   | xlsxwriter 3.2.9 | **tag archive** `RELEASE_3.2.9` (GitHub) | `xlsxwriter/test/` (1,235 modules, 998 of them comparisons against Excel's own files; 24.9 MB archive) | `package_paths`; `cwd = "/tmp/work"` with `cwd_folders` (Decision 7) |
   | xlrd 2.0.2 | **tag archive** `2.0.2` (GitHub) | `tests/`, `tests/samples/` | `extra_sys_path` tree root |
   | pypdf 6.21.1 | sdist, and **the sample-files archive** at the commit pypdf's `6.21.1` tag records for its `sample-files` submodule | `tests/`, `resources/` (85 PDFs), `sample-files/` (from the second archive) | `extra_sys_path` tree root |
   | beautifulsoup4 4.15.0 | sdist | `bs4/tests/` | `package_paths` |
   | soupsieve 3.0.3 | sdist | `tests/` (84 modules) | `extra_sys_path` tree root |
   | html5lib 1.1 | sdist | `html5lib/tests/` with its `conftest.py`, `testdata/` (92 files), `.pytest.expect` (support) | `package_paths` |
   | webencodings 0.6.1 | sdist | `tests/` | `extra_sys_path` tree root |
   | defusedxml 0.7.1 | sdist | `tests.py` (a support-file group path), `xmltestdata/` | `extra_sys_path` tree root |
   | xmltodict 1.0.4 | sdist | `tests/` | `extra_sys_path` tree root |
   | pyyaml 6.0.3 | sdist, **already pinned** (039) | `tests/legacy_tests/` (25 modules, 575 data files) | `extra_sys_path` `tests/legacy_tests` |
   | tomli-w 1.2.0 | **tag archive** `1.2.0` (GitHub) | `tests/` (264 data files) | `extra_sys_path` tree root |
   | jinja2 3.1.6 | sdist | `tests/` (23 modules, `res/`) | `extra_sys_path` tree root |
   | markupsafe 3.0.4 | sdist, **already pinned** (039) | `tests/` | `extra_sys_path` tree root |
   | tabulate 0.10.0 | sdist | `test/` (tests import `common` by name) | `extra_sys_path` `test` |
   | charset-normalizer 3.5.2 | sdist | `tests/`, `data/` (support: 20 sample files) | `extra_sys_path` tree root |
   | networkx 3.7 | sdist, **already pinned** (041; patched, Decision 4) | `networkx/**/tests/`, `networkx/conftest.py` (268 modules) | `package_paths` per subpackage |
   | patsy 1.0.3 | sdist | `patsy/test_*.py` (6 modules); the 109 inline `test_*` functions of 18 library modules run from the product (Decision 5) | `package_paths` |
   | sympy 1.14.0 | sdist | `sympy/**/tests/`, `sympy/conftest.py` (612 modules), `doc/src` (103 files with examples, upstream's `testpaths`) | `package_paths` per subpackage |
   | mpmath 1.3.0 | sdist | `mpmath/tests/` (31 modules) | `package_paths` |
   | attrs 26.1.0 | sdist | `tests/` (26 modules, `conftest.py`) | `extra_sys_path` tree root |
   | more-itertools 11.2.1 | sdist | `tests/` | `extra_sys_path` tree root |
   | toolz 1.2.0 | sdist | `toolz/tests/`, `toolz/sandbox/tests/` | `package_paths` |
   | tqdm 4.70.1 | sdist | `tests/` (`tests_*.py`, `conftest.py`) | `extra_sys_path` tree root |
   | typing-extensions 4.16.0 | sdist | `src/test_typing_extensions.py`, `src/_typed_dict_test_helper.py` as `support_files` (support-file group paths; never `src/typing_extensions.py`) | `extra_sys_path` `src` |
   | joblib 1.6.0 | sdist | `joblib/test/`, `conftest.py` (support: the root conftest), `doc/*.rst` (upstream's `--doctest-glob`) | `package_paths` |
   | cloudpickle 3.1.2 | **tag archive** `v3.1.2` (GitHub) | `tests/` (with `cloudpickle_testpkg/`, `mock_local_folder/`, `old_pickles/`) | `extra_sys_path` tree root and `tests/cloudpickle_testpkg` |
   | threadpoolctl 3.7.0 | **tag archive** `3.7.0` (GitHub) | `tests/`, `conftest.py` | `extra_sys_path` tree root |
   | narwhals 2.27.1 | sdist | `tests/` (296 modules, a `tests` package) | `extra_sys_path` tree root |
   | seaborn 0.13.2 | sdist, **already pinned** (042) | `tests/` (39 modules, `conftest.py`; 1,596 `def test`) | `extra_sys_path` tree root |
   | reportlab 5.0.1 | sdist (the product's package is the wheel) | `tests/` (77 `test_*.py`, unittest; images and data) | `extra_sys_path` tree root; `cwd = "/tmp/work"` (its tests write their PDFs beside the test folder or to reportlab's output folder; the survey names which) |
   | formulaic 1.2.2 | sdist | `tests/` (54 modules, 263 `def test`) | `extra_sys_path` tree root |
   | interface-meta 2.0.1 | sdist | `tests/` (6 modules, 36 `def test`) | `extra_sys_path` tree root |
   | wrapt 2.5.1 | sdist | `tests/` (`conftest.py`, `core/`, `mypy/`; 1,349 `def test`) | `extra_sys_path` tree root |

   - **The rule for a top-level `tests` folder.** The stage holds only the files the table names,
     never the package's own modules, so appending the tree root (or `src/` for typing-extensions,
     whose stage holds only the test and its helper) can shadow nothing. The guard of 066's
     Decision 5 proves it at every run.
   - **A support file may be a group path** (typing-extensions, cycler, six, defusedxml): 066's
     rules require a group path under a stage folder; 067 adds one rule, that a group path may also
     be a staged support file, with its unit variant.
   - **Upstream settings that would put the package's source on `sys.path` are dropped**:
     narwhals' `pythonpath = ["src"]`, attrs' and others' `--import-mode` (the driver's is
     `importlib` already). The tests must import the product.

3. **The pins: 30 sdists and 9 forge archives (8 release tags and pypdf's sample-files commit), in
   `downloads/SHA256SUMS`, recorded in `MANIFEST`.**
   - **The 39:** the 26 sdists of the draft, the 8 tag archives, the sdists of reportlab,
     formulaic, interface-meta and wrapt (4), and pypdf's sample-files archive (1). pyyaml,
     markupsafe, networkx and seaborn are pinned already.
   - **Each pin** is one line in `downloads/SHA256SUMS` (SHA-256 and name) and one line
     `tests <url> <name>` in `scripts/00_download.sh`, a new function beside `research`: a plain
     build does not fetch it; `scripts/00_download.sh --tests` and `fetch.py --shard` do. The hashes
     and URLs are in the evidence folder's `sdists.txt`, `sdists-067-revision.txt` and
     `tag-archives.txt`; the builder fetches each again and recomputes.
   - **Names.** An sdist keeps its PyPI name (`fonttools-4.67.0.tar.gz`). A tag archive is named
     `<distribution>-<version>-tag.tar.gz` (`openpyxl-3.1.5-tag.tar.gz`); pypdf's sample files are
     `pypdf-6.21.1-sample-files-tag.tar.gz`. No pattern in `SOURCE_PATTERNS` can match a wheel or an
     sdist by mistake.
   - **pypdf's sample files.** pypdf's repository pins `py-pdf/sample-files` as a submodule at one
     commit per release; the builder reads that commit from the `6.21.1` tag's tree and pins its
     GitHub archive. If the tag records no commit, or the archive cannot be fetched by a pinned
     URL, the survey states why, and the `samples` tests are named with that reason.
   - **Recorded in `MANIFEST`.** `assemble_artifacts.py` writes a `pin` line for every
     `SHA256SUMS` line but `RESEARCH_PINS`. 067 adds no exception: the artifact's record names
     every source its tests came from, and the tie works for a test source as for numpy's tarball.
     The cost: the set's `MANIFEST` changes (39 `pin` lines and the `recipe` line of
     `scripts/00_download.sh`), so its `SHA256SUMS` line changes, and nothing else (criterion 9).
     **101's key** hashes `downloads/SHA256SUMS` and every tracked file under `scripts/`, so 067's
     pins, and any later re-pin of a test source (a Heptapod regeneration, say), force one source
     build and a new set with no product change. Weighed and refused: keeping test pins out of
     `MANIFEST` as `RESEARCH_PINS` are; the record would no longer name the sources the release's
     tests came from, and the tie would need a second list.
   - **Why tag archives for eight.** Their PyPI sdists hold the package and no tests (READ). Each
     project's tag at the released version holds the tests, and its package files are the wheel's,
     byte for byte (EXECUTED, `source-equality.txt`; repeated by the pre-build review).
   - **The risks of a forge** (INFERRED). GitHub has served archive bytes unchanged since it rolled
     back its 2023 compression change; GitLab, behind Heptapod, regenerates archives and has
     changed their bytes across upgrades. A changed archive fails `fetch.py`'s hash check, red and
     named, never silently; the re-pin is one line, and Decision 4's tie proves the new archive's
     package is still the wheel's. **Availability:** `fetch.py --shard` fetches from github.com and
     foss.heptapod.net in each release run's Linux shards, so a forge outage would turn a run red
     for a reason unrelated to the change. Mitigation: `fetch.py` retries each fetch three times
     with a pause, as `00_download.sh`'s curl does (`--retry 3`), and a failure names the forge and
     the file.

4. **The tie: the tests test the bytes that ship.**
   - **For a test source**: its `MANIFEST` pin equals its hash (as 050's tie), and its version is
     the version of the product's distribution (the wheel's or sdist's pin name).
   - **For a package built from a wheel** (38 of 42): at staging, the judge compares **every file
     the zip takes from the pinned wheel** (outside `.data/`), `.py` or not, with the same path in
     the test source (as is, under `src/`, or under `lib/`). Any difference fails the family's
     groups, naming the file. A file the wheel ships that the test source lacks (a generated
     `_version.py`, tzdata's compiled zone files if the sdist builds them differently) is named in
     the family's TOML with its reason (`tie_skips`), never skipped silently. `fetch.py --shard`
     fetches the wheel beside the test source, verified by its `SHA256SUMS` line.
   - **For pyyaml, markupsafe, networkx and seaborn**, the zip's code is the sdist's: 050's tie
     (tarball and patches against `MANIFEST`) covers them. Only networkx carries a patch
     (`recipes/patches/networkx-3.7/0001-graph-atlas-from-a-zip.patch`, which also patches
     `test_atlas.py`); its stage is built after the patch is applied, as 066's `stage()` does.

5. **The driver and the guest: 066's, with three kinds of item added.** `package_drive.py`: the
   kit appended after the product's zip (so the product's `packaging`, a pin identical to the
   kit's, is the one tested), 066's keys, the stream, the guard, and the hypothesis profile `judge`
   (derandomized, no database). 050's pytest options, then each package's `.ini`: its
   `[tool.pytest.ini_options]` (or `setup.cfg`, `tox.ini`, `pytest.ini`) transcribed, markers and
   `filterwarnings` kept, `xfail_strict` kept, `addopts` that shape the report or write files
   dropped. **Every test upstream's own runners select runs, opt-ins included** (the owner's rule;
   066 runs contourpy's `--runslow` and `--runtext`), in the tier Decision 10 gives it:
   - **Opt-in slow tests run in release-tier groups** (Decision 10): sympy's `slow` and `tooslow`
     (under pytest, sympy's decorators are the markers `slow` and `tooslow`,
     `sympy/testing/pytest.py`, READ; only once `sys._running_pytest` is set before sympy is
     imported, the survey's finding); networkx's and narwhals' `--runslow` tests; packaging's
     `property` tests. With the owner's rule every such test is in a release group with its
     opt-in on, and no smoke file holds one, so no group needs a marker expression for the tiers.
   - **Doctests run as 066's lxml docstring items**: the stdlib's `DocTestRunner` over the
     product's modules, found by import (the zip's bytecode; EXECUTED by the pre-build review for
     `more_itertools.recipes` and `tabulate`), with each upstream's own option flags. For
     fonttools, joblib, mpmath, sympy, networkx and tabulate, as their `--doctest-modules`
     selects; for more-itertools and typing-extensions, exactly the `DocTestSuite`s their
     `load_tests` add (`more_itertools.more`, `more_itertools.recipes`, `typing_extensions`), since
     pytest ignores `load_tests` (066's lxml finding again). `docstring_modules` gains a
     package-walking form, `docstring_packages`, for packages with many modules (sympy, networkx,
     mpmath, fonttools): every module of the named package the product ships, in sorted order,
     minus `docstring_not_selected` entries with their reasons. sympy's flags include
     `FLOAT_CMP`, pytest-doctestplus' flag (`pyproject.toml`'s `doctest_optionflags`), so sympy's
     doctests run under pytest-doctestplus from kit-extra; the survey confirms that the run equals
     sympy's own (its `bin/doctest` uses `sympy.testing.runtests`) or states the difference.
   - **Doc-file doctests in the test source** run as 066's lxml doctest files: joblib's `doc/*.rst`
     (`--doctest-glob`), sympy's `doc/src` (its `testpaths`), each with upstream's flags.
   - **In-library test functions** (`module_functions`): patsy's `python_files = *.py` and
     `testpaths = patsy` collect 109 inline `test_*` functions in 18 library modules (READ,
     `setup.cfg`); the driver imports each named product module and runs its `test_*` functions as
     items, `::functions:<module>.<name>`, so the product's bytecode is what runs (EXECUTED by the
     pre-build review: `patsy.desc` exposes six, which need the kit's `pytest`).
   - **Marker deselections are visible**: the driver writes a `D <node id>` line for every item a
     `-m` expression deselects, and the record carries their count per reason ("release tier,
     group `<g>`" or "no network"). pytest's `-m` alone drops them silently, and `left_out` would
     never name them.
   - **Per package**: pypdf `-m "not enable_socket"` (318 uses; no network in the guest, a true
     reason, each item a `D` line), its `--disable-socket` (pytest-socket) dropped; narwhals
     `--constructors=pandas,pandas[nullable]` (its default list names pyarrow, polars, duckdb,
     sqlframe and ibis, none in the product: the other constructors' cases are named as not
     selected with that reason); html5lib with its conftest (kit-extra, Decision 6); tqdm's
     `--asyncio-mode` kept with pytest-asyncio from kit-extra, its `timeout` (pytest-timeout)
     dropped (a clock); wrapt runs its pure path, as the product has no `_wrappers` extension (the
     survey records whether wrapt's tests need `WRAPT_DISABLE_EXTENSIONS` set to match).

6. **Test-only wheels added to the kit, in a file of their own.** A module the product could ship
   but does not (wcwidth for tabulate, railroad-diagrams for pyparsing, trio for jinja2 if the
   survey cannot import it) gives counted skips, or a not-selected file whose reason is that the
   product lacks that feature. **A test-only module joins kit-extra**: `tests/upstream/kit-extra.txt`,
   in `kit.txt`'s format (SHA-256 and a `files.pythonhosted.org` URL of a pure wheel), pinned by
   the judge as 050's Decision 2 pins the kit; each family names the extras it stages
   (`kit_extra = [...]`), and no family's extras stage into another's. `kit.txt` is unchanged, so
   numpy's, pandas' and 066's stages are unchanged.

   | wheel | for | why |
   |---|---|---|
   | freezegun | python-dateutil | `tests/test_rrule.py` (562 tests) and `tests/test_utils.py` import it at module level |
   | pretend | packaging | four modules import it at module level |
   | tomli | tomli-w | every test module round-trips through it, unguarded |
   | setuptools **66.1.1** (the survey: 75.8.0's `pkg_resources` imports its vendored platformdirs, whose `unix.py` imports `os.getuid` at module level, absent under WASI; 66.1.1's vendored copy falls back; older releases call `pkgutil.ImpImporter`, gone since 3.12) | html5lib | its conftest imports `pkg_resources` |
   | pytest-expect 1.1.0, u-msgpack-python | html5lib | its conftest loads the plugin, which reads `.pytest.expect`. **pytest-expect has no wheel on PyPI** (its one file is the sdist `pytest-expect-1.1.0.tar.gz`, SHA-256 `36b44627…`): `kit-extra.txt` admits one pure sdist by name, its package copied as the wheel's would be (a rules row), or the lane names another way at the delta review |
   | mock | html5lib | `html5lib/tests/test_meta.py` imports it |
   | pytest-asyncio | tqdm | `tests/tests_asyncio.py` |
   | pytest-doctestplus | sympy | `FLOAT_CMP` in its doctest flags |
   | pympler | attrs | its tests guard it; a test-only module |
   | ~~trio~~ (tried; **not added**) | jinja2 | the survey: trio 0.34.0 raises `NotImplementedError: unsupported platform` at import under WASI (`trio/_core/_run.py`), and, as a hypothesis entry point, it is imported by hypothesis itself, so staging it ends any session at start. `tests/test_async.py` and `tests/test_async_filters.py` are not selected with that reason (Decision 8) |

   freezegun requires python-dateutil, which the product carries (the product's is used). The
   survey confirms each version and each import: every row above but trio imports and runs in the
   guest (EXECUTED, the memo).

7. **XlsxWriter's writable folder: 066's `/tmp/work`.** XlsxWriter's comparison tests write
   `_test_<name>.xlsx` beside the Excel files they compare against, by a path relative to the
   working folder, and delete it after (READ, `excel_comparison_test.py`). Its family uses
   `cwd = "/tmp/work"` (066, Decision 14) with **`cwd_folders`**, a new key: each a folder of the
   test source (`xlsxwriter/test/comparison/xlsx_files/`, `xlsxwriter/test/comparison/images/`:
   1,023 files, 10.8 MB), copied into the guest's `/tmp/work` before the session, rule-checked as
   members, as `cwd_files` are. No second grant and no diff of a stage. Host litter is spec 089's
   named `HostLitter` guard, as for lxml: a voided run is a host failure, re-run once. reportlab
   uses the same folder for the files its tests write.

8. **What is not selected, each with its true reason and closer.** A file is not selected only when
   it cannot load, or every test in it needs what the product does not have (066's Decision 8).
   READ from imports and configs (`collection-risks.txt`); the survey confirms each line or moves
   it to a class:

   | package | not selected | reason | closes with |
   |---|---|---|---|
   | fonttools | `Tests/metaTools/check_table_coverage_test.py` | it runs `MetaTools/check_table_coverage.py`, which the sdist ships, but that script puts the source tree's `Lib/` first on `sys.path` and checks the repository's own files (`Lib/…`, `Doc/source/…`): it would import a copy of fontTools, not the product, and it checks the repository, as 066's Pillow `check_release_notes.py` does | `README.md` |
   | attrs | `tests/test_pyright.py` | it runs pyright in a subprocess | `README.md` |
   | pyparsing | `tests/test_diagram.py` | it imports `railroad` (railroad-diagrams) at module level: the product lacks pyparsing's diagram feature | `README.md` |
   | joblib | `joblib/test/test_dask.py`, `joblib/test/test_memmapping.py` | dask and distributed are not in the product; memmapping needs `mmap` and worker processes | `README.md` |
   | sympy | `sympy/utilities/tests/test_autowrap.py`, `sympy/utilities/_compilation/tests/`, `sympy/external/tests/test_codegen.py`, `sympy/interactive/tests/test_ipython.py` | they compile C or Fortran, or start IPython, in subprocesses | `README.md` |
   | narwhals | modules that import pyarrow or polars at module level (13 READ; the survey lists them), and the constructors outside `pandas` and `pandas[nullable]` | none of them is in the product | `README.md` |
   | toolz | `toolz/sandbox/tests/test_parallel.py` | it uses `multiprocessing` pools | `README.md` |
   | pypdf | the `enable_socket` tests, by `D` line | they fetch PDFs over the network; the guest has none | `README.md` |
   | wrapt | `tests/mypy/` (if pytest collects it) and `tests/stress/` | the first runs mypy in a subprocess (`conftest.py`); the second are scripts run by hand with threads, not pytest tests | `README.md` |
   | jinja2 (the survey) | `tests/test_async.py`, `tests/test_async_filters.py` | they import trio at module level, and trio raises `NotImplementedError: unsupported platform` at import under WASI (Decision 6) | `README.md` |
   | cloudpickle (the survey) | `tests/cloudpickle_test.py` | it imports psutil at module level; psutil is a compiled package the product does not carry. It is most of cloudpickle's suite: the survey ran 14 of its other tests | `README.md` |
   | formulaic (the survey) | `tests/materializers/test_base.py` | it imports pyarrow at module level; the product has no pyarrow | `README.md` |
   | reportlab (the survey) | `tests/charts-out/` | generated chart scripts the sdist carries from an earlier run, not tests: upstream's `runAll.py` excludes `*/charts-out/*.py`; nine do not parse | `README.md` |

   Selected now, against the draft (the review, H1): tqdm's `tests_perf.py` (a file that loads is
   selected, and its failures are a class) and `tests_asyncio.py`; jinja2's `test_async*.py` (with
   trio from kit-extra, or the survey's reason); html5lib's conftest and its data-driven suite
   (1,617 tree-construction cases alone, per tree builder) and `test_meta.py`; pyparsing's
   `examples/tiny/tests`; dateutil's `docs/exercises/solutions/`; every doctest and doc file of
   Decision 5; patsy's inline tests; pypdf's `samples` tests.

9. **Known failures are classes, by test id, each one gap** (066's Decision 9). The classes the
   platform's documented facts predict, per group, INFERRED from the files:

   | class | reason (all close with `README.md` unless named) | likely in |
   |---|---|---|
   | `no-processes` | no processes | packaging (`test_tags`, `test_musllinux`), pypdf (11 modules run `python -m pypdf`), cloudpickle (`subprocess_pickle_echo`), typing-extensions, tabulate (`test_cli`), fonttools (`ttx_test`, `main_test`), sympy (`test_misc`), tqdm (`tests_main`), reportlab |
   | `no-threads` | no threads | more-itertools, networkx (`test_decorators`), tqdm, charset-normalizer (`test_thread_safety`), threadpoolctl, sympy (`test_symbol`), joblib (the `threading` backend), wrapt |
   | `shallow-recursion` | recursion through Python stops at 40 to 250 levels | sympy (deep expression trees), networkx (recursive DFS), jinja2, pyparsing, bs4 and soupsieve (deep documents), attrs (recursive `repr`) |
   | `zip-no-source` | the product's modules are bytecode | attrs, pyparsing, sympy (`inspect.getsource` users), toolz (`curry` signatures from source), wrapt |
   | `zip-code-names` | code objects carry relative file names | packages that check a warning's `filename` or a frame's file |
   | `no-tzset` | `time.tzset` and the host's `/usr/share/zoneinfo` are absent; zoneinfo comes from tzdata in the zip | python-dateutil (`tzlocal`, `gettz` of system zones) |
   | `wasm32` | 32-bit `sys.maxsize`, `hash()` width, 4 GiB address space | sympy, mpmath (big-integer edges), charset-normalizer (`test_large_payload`), cloudpickle (`old_pickles` made on 64-bit) |
   | `no-ctypes` | the `ctypes` stand-in: `dllist()` is `[]`, calls raise | threadpoolctl (its `_pyMylib` and OpenMP helpers are never built) |
   | `no-resource-module` | WASI has no `resource` module (066's README fact) | tqdm's perf tests, any memory measurement |
   | `reportlab-fonts-not-shipped` | 042 leaves reportlab's fonts and barcode folder out of the zip | reportlab's font and barcode tests; closes with spec 042 |

   A closer is a `README.md` fact, a landed specification's file, or a reserved number with its
   roadmap line; never spec 067 itself (066's review, L2). scipy-dependent tests are skips in a
   set without scipy and passes with it: they call `importorskip("scipy")` (networkx in 87 places,
   READ); 037 has landed, so the survey counts them as they run. A failure no class admits is a
   finding (Decision 1).

10. **The two tiers, by the owner's standing rule: each suite in the release tier whole, one small
    smoke group per package in the normal tier** (revised 2026-10-21; it replaces the reviewed
    text's marker split as the line between the tiers, and the owner's (c) in its reach).
    - **The owner's words** (2026-10-21, through the lane): "we need to have fast tests and slow
      tests. We only run slow tests when we are trying to publish to pypi, as it is critical we
      check that our package is working on the libraries we import before we release to catch any
      errors, otherwise we should only run the tests needed to confirm our new edits are
      working." Tier placement and fuel thresholds are not questions for the owner.
    - **So:** each of the 42 suites runs in the **release tier, whole**, its upstream opt-ins
      included (102's machinery: the tag run, the dry run on main before a tag, a branch run with
      `release-tier: true`, and the lane's release acceptance before a tag). Each package keeps
      **one smoke group in the normal tier**: a few files that prove the package imports from the
      zip and its core paths work, so a landing that breaks a package is still caught at every
      landing and on every branch run. Nothing leaves the full suite: every collected test is in
      exactly one tier.
    - **The partition is by path.** A smoke group names test files (or, for more-itertools, one
      docstring module); the family's release groups cover every other staged test path and only
      those. A smoke file holds no test upstream runs only on request (no `@slow`, `@tooslow`,
      `--runslow` or `property` test; READ for each chosen file), so the smoke group needs no
      marker expression, and every opt-in test is in a release group with its opt-in on: sympy's
      release groups with no `-m` (upstream's `addopts` dropped), networkx's and narwhals' with
      `--runslow`, packaging's with no `-m`. A smoke group's run that deselects or skips a test for
      an opt-in is red (Decision 13); a family exclusion with a true reason (pypdf's
      `-m "not enable_socket"`, no network, whose `D` lines name each item) applies to all of that
      family's groups alike and is not a tier. pypdf's own `slow` mark is not an opt-in: upstream
      runs those tests by default.
    - **A whole suite under about 30 G is its own smoke group** (twenty families, 383 G together:
      the table's "the whole suite" rows), and those families have no release group. A session's
      start costs about 10 G (the survey's item 2), so a smaller smoke group would save almost
      nothing, and a one-module suite (six, cycler, defusedxml, typing-extensions) cannot be split
      by path. pyyaml's suite is one generated module (`tests/legacy_tests/test_yaml.py`, 1,283
      items, 60.3 G): the one suite past 30 G kept whole in the normal tier, since no path can
      split it; the delta review may instead ask for a keyword split, which the path rule does not
      express. This is a named choice under the owner's rule: these twenty suites run on every
      landing because running fewer of their tests would cost about as much.
    - **A new kind for 102: the path release group.** 102's Decision 3 refuses a release group of
      no named kind. 067 adds the kind its suites need, beside the node-id group 102 leaves to
      067: `release_by = "path"`. Its rules: in a family with path release groups, the smoke
      group's paths and the path release groups' paths are disjoint and together are every staged
      test module; a normal group in such a family is its smoke group (Decision 13). 095 needs the
      same kind for scipy, scikit-learn and statsmodels: whichever of 067 and 095 is built first
      adds it to `tests/harness/tiers.py`, and the second rebases onto it, as for `kit-extra.txt`.
    - **The smoke groups** (normal tier; each measured on `d0d91cef`, EXECUTED; the memo's item 6):

      | package | smoke group | fuel |
      |---|---|---|
      | sympy | `sympy/core/tests/test_basic.py`, `test_sympify.py` | 34.0 G |
      | mpmath | `mpmath/tests/test_convert.py`, `test_division.py`, `test_str.py`, `test_bitwise.py` | 48.0 G |
      | networkx | `networkx/classes/tests/test_graph.py`, `networkx/algorithms/shortest_paths/tests/test_generic.py` | 29.2 G |
      | packaging | `tests/test_tags.py`, `test_utils.py`, `test_licenses.py`, `test_metadata.py` | 19.2 G |
      | seaborn | `tests/test_utils.py`, `tests/_core/test_data.py` | 37.0 G |
      | pyparsing | `tests/test_simple_unit.py`, `examples/tiny/tests` | 14.1 G |
      | fonttools | `Tests/ttLib/ttFont_test.py`, `Tests/misc/arrayTools_test.py`, `transform_test.py` | 18.9 G |
      | pypdf | `tests/test_generic.py`, `test_pagerange.py` | 28.0 G |
      | patsy | `patsy/test_state.py`, `test_regressions.py` | 19.2 G |
      | more-itertools | the docstrings of `more_itertools.recipes` | 12.0 G |
      | narwhals | `tests/frame/select_test.py`, `filter_test.py`, `group_by_test.py`, `join_test.py` | 24.3 G |
      | attrs | `tests/test_validators.py`, `test_converters.py`, `test_filters.py` | 13.3 G |
      | reportlab | `tests/test_pdfgen_general.py`, `test_platypus_paragraphs.py` | 27.4 G |
      | xlsxwriter | `xlsxwriter/test/comparison/test_simple01.py`, `test_chart_bar01.py`, `xlsxwriter/test/workbook` | 14.5 G |
      | joblib | `joblib/test/test_hashing.py`, `test_logger.py`, `test_disk.py` | 18.3 G |
      | python-dateutil | `tests/test_easter.py`, `test_relativedelta.py`, `test_isoparser.py` | 15.8 G |
      | formulaic | `tests/test_formula.py`, `tests/parser`, `tests/test_model_spec.py` | 30.4 G |
      | soupsieve | `tests/test_api.py`, `tests/test_level1` | 23.2 G |
      | beautifulsoup4 | `bs4/tests/test_soup.py`, `test_htmlparser.py`, `test_css.py` | 15.7 G |
      | jinja2 | `tests/test_api.py`, `test_filters.py`, `test_core_tags.py` | 19.8 G |
      | openpyxl | `openpyxl/cell/tests`, `openpyxl/utils/tests` | 21.4 G (the conftest finding: a lower bound) |
      | charset-normalizer | `tests/test_base_detection.py`, `test_utils.py`, `test_mess_detection.py` | 12.8 G |
      | twenty others | each whole suite: pyyaml 60.3, typing-extensions 29.0, tabulate 28.2, wrapt 25.2, tqdm 24.7, html5lib 21.9, toolz 21.8, xmltodict 19.3, cloudpickle 16.3, et-xmlfile 15.6, threadpoolctl 13.9, six 13.5, tomli-w 13.5, markupsafe 12.3, defusedxml 11.5, tzdata 11.3, interface-meta 11.3, webencodings 11.3, xlrd 11.3, cycler 10.8 | 383 G |
      | **all 42** | | **879 G** |

      Each failure in them is a member of a measured class (the memo's item 5), so each is green
      with its gaps; the build measures each again as built (criterion 7).

    - **sympy's single test past every bound** (the owner's answer (b)): `test_issue_17141_slow`,
      about 2.61 T (EXECUTED by the pre-build review), a node-id release group of its own,
      `sympy-slow-17141`, in a release shard of its own allowed past the 360 s bound. The survey
      found more sympy cost of the same shape: its `solvers/ode` and `solvers` sessions stopped at
      the survey's 4 T caps after 70 and 244 outcomes, so each heavy test the build measures past
      480 G gets the same treatment, named in the build's landing notes (Delta, item 1).
    - **Caps and splits**, unchanged in kind: each group carries `measured` from the build's own
      run, its cap at most `rule_cap(measured)`, each family's budget the sum of its caps; a release
      group past 480 G is split by file in the test source's order, a file past 480 G by
      `[[split]]` of constructed `-k` expressions (066's Decision 11).
    - **Upstream's opt-ins stay visible.** The record keeps each family's count of tests upstream
      runs only on request (sympy's 185 `@slow` and 14 `@tooslow` lines, networkx's 7 and
      narwhals' 24 `slow` marks, packaging's `tests/property/`), so a reader sees which
      release-tier tests upstream itself runs only when asked.

11. **The release: one or two normal Linux shards for the smoke groups, and release shards for the
    rest** (revised 2026-10-21).
    - **Normal tier:** the 42 smoke groups (879 G measured) in two Linux shards,
      `upstream-pure-smoke-a` and `-b`, packed at most 725 G each, each about 70 to 140 s of guest time
      plus about 60 s of setup, on every release run; the lane's darwin judge runs them at every
      landing (about 2 to 2.5 minutes of guest time at 0.14 to 0.17 s per G). Linux's normal matrix
      gains two jobs; it stays off the critical path (066's fourteen plot shards already end before
      macOS's last).
    - **Release tier:** every other group of the 22 families with release groups, in release
      shards of 102's kind (the pseudo-system `release`, Linux only), at most 725 G each, run only
      where 102 runs them: about **95 to 110 shards** for the measured at least 66.3 T (the price), plus
      `sympy-slow-17141` alone and any single sympy test the build finds past 725 G. A 725 G shard
      is 116 to 225 s of guest time plus about 60 s of setup.
    - **The job count.** On a normal run the Linux matrix gains two jobs. On a release-tier run
      `judge-release` gains about 95 to 110, which at 101's 20 parallel jobs is about five more waves of
      four to five minutes, beside 102's twelve and 095's about 75 (INFERRED from the packing; the
      branch run with `release-tier: true` measures it). That run, not a landing, pays it.
    - **The lane's release acceptance before a tag** (102, Decision 5) grows by about 2.6 to 3.1 hours of
      guest time on darwin, about 0.9 to 1.1 hours of wall clock at `-n 3` (INFERRED at 0.14 to 0.17 s
      per G): with 095's at least 53 T it is the largest single cost of a publication. The lane
      books its slot by it.
    - **Linux only in the release**, as 066's: fuel is ratcheted on the lane's darwin judge; G5
      compares `passes` and `passed_digest` between the Linux record and the lane's. No group
      probes the host's file system.

12. **`packages.toml`: 42 suites.** Every `later` entry closed by `spec 067` (39 at wave 08, the 37
    and 042's two) becomes `suite`; 045's three become `suite` (045 adds them closing with 067).
    After 067, no entry names `spec 067`. A package whose survey shows no test can pass in the
    guest stays `later` with that reason and a closer the lane reserves; none is expected.

13. **The rules, widened** (beyond 066's): every `tests` line in `00_download.sh` has a
    `SHA256SUMS` line and a `SOURCE_PATTERNS` entry, and the reverse; a tag archive's name ends
    `-tag.tar.gz`; every `kit_extra` name is in `kit-extra.txt`, and `kit-extra.txt` has 050's kit
    rules; every `cwd_folders` entry is a folder of the test source, and only with
    `cwd = "/tmp/work"`; a group path may be a staged support file; every `docstring_packages`
    entry is a package the product ships; every `module_functions` module is a product module;
    `tie_skips` names files the wheel ships; each family's test source names the version of the
    product's pin; in a family with path release groups (Decision 10), the smoke group's paths and
    the release groups' paths are disjoint and together are every staged test module; each family
    has exactly one normal group, its smoke group, unless its whole suite is its smoke group; each
    smoke group's `measured` is under 100 G and the smoke groups' together under 1 T; a smoke group
    names no marker expression of its own (a family exclusion with a true reason, pypdf's
    `enable_socket`, applies to every group alike), and its run deselecting or skipping a test for
    an opt-in is red; every group
    has `measured`, and every cap is at most `rule_cap(measured)` (066's rule, unchanged).

14. **The README and the CHANGELOG.** The README's testing section names the 42 suites in one
    paragraph, the two tiers (each whole suite before a publication, a smoke group per package on
    every run), what is not run and why, and that eight come from release tags and one from pypdf's
    sample-files commit; each class closed by `README.md` has its fact there. The CHANGELOG: "The
    release runs the pure-Python packages' own tests (spec 067): each whole suite before a
    publication, a smoke group per package on every run; 39 test sources are pinned and named in
    `MANIFEST`."

## Intent

The judge runs the own test suites of the 42 pure-Python packages inside the guest, from sources
pinned by hash and tied to the bytes the product ships, doctests and opt-ins included. It counts
every pass and names every known failure and every test it does not run. Each whole suite is
release-tier: it runs on Linux in release shards before a publication (102's tag run, the dry
run on main before a tag, a branch run that asks for it) and in the lane's release acceptance.
One small smoke group per package is normal-tier: it runs on every release run in one or two
Linux shards and in the lane's darwin judge at every landing. It turns red when a pass is lost, a test
traps, an unknown failure appears, a test runs against a copy of the product's code, or a test
source is not the shipped code's.

## Design

```
downloads/SHA256SUMS                 39 lines (30 sdists, 9 *-tag.tar.gz, pypdf's sample files among them)
scripts/00_download.sh               tests(): 39 lines; --tests fetches them
tests/upstream/<package>.toml, .ini  42 families (Decision 2); grant /upstream-<package>; kit_extra;
                                       cwd_folders (xlsxwriter, reportlab); docstring_packages;
                                       module_functions (patsy); tie_skips; one smoke group (normal)
                                       and release_by = "path" groups (Decision 10)
tests/upstream/kit-extra.txt         the test-only wheels of Decision 6 (and pytest-expect's sdist)
tests/upstream/expected/<group>/<class>.txt
tests/harness/pins.py                SOURCE_PATTERNS for each test source
tests/harness/packages.py            the wheel tie; kit_extra; cwd_folders; docstring_packages;
                                       module_functions; support-file group paths; marker D lines;
                                       the path release kind and the smoke rules (Decision 13)
tests/harness/tiers.py               (102's) release_by = "path": the path partition rule
tests/upstream/package_drive.py      docstring packages, doc files, module functions, marker D lines
tests/harness/upstream.py            PACKAGE_SUITES += 42
tests/upstream/fetch.py              tests lines, with retries; the pinned wheel beside each test source
tests/upstream/packages.toml         42 suites
tests/release_shards.toml            upstream-pure-smoke-* (linux, normal), upstream-pure-r-* and
                                       sympy-slow-17141 (release pseudo-system, 102)
.github/workflows/release.yml        judge-linux's and judge-release's matrices (102's job); gather's inputs
context/release-tier-claims.toml     067's claim block (102, Decision 6)
tests/known_gaps.toml                one entry per class and trap
tests/unit/test_packages.py, test_upstream.py, test_shards.py, test_fetch_trees.py, test_pins.py
README.md, CHANGELOG.md, context/progress/README.md, spec 063 (one dated line), context/roadmap.md
```

**A group's run** is 066's, with the wheel tie added at staging (Decision 4) and the items of
Decision 5.

**Spec 063, one dated line** in its Status: "2026-10-…: the 42 pure-Python packages are `suite`s
since spec 067: each whole suite in the release tier (spec 102), a smoke group per package in the
normal tier."

## Scope

**In:** the above: every test upstream's own runners select, doctests and opt-ins included, each
whole suite in the release tier and a smoke group per package in the normal tier.

**Out, each with its reason:**
- **The compiled packages** (066) and **scipy, scikit-learn, statsmodels** (095).
- **Packages added after this revision** (046's line's python-docx and python-pptx, and any
  later): each specification that adds a package adds its suite (AGENTS.md).
- **The release tier's mechanism** (spec 102): 067 marks its groups and adds one group kind
  (Decision 10); 102 decides where they run.
- **numpy's and pandas' slow tests** (`numpy.toml` and `pandas.toml` still run `not slow`, spec
  050): the release tier's other members, 102's or a follow-up the lane names; not 067's.
- **Fixing what the suites find.** A class with its closer, or a finding for the lane.
- **The plain binary, macOS and Windows release shards** (066's reasons).
- **Wall-clock.** No check reads a clock; every time above is a benchmark estimate.

## Acceptance criteria

Each is counted; none times anything. Each check is written first and seen failing against today's
code or a stand-in, recorded in the landing notes; a stand-in is never committed.

1. **The pins.** `scripts/00_download.sh --tests` fetches the 39 sources and each verifies; a plain
   `scripts/00_download.sh` fetches none of them (its line counts them as pins not fetched).
   `tests/unit/test_pins.py`: a `tests` line with no `SHA256SUMS` line fails, and the reverse; a
   tag archive not named `-tag.tar.gz` fails.
2. **The rules.** `test_upstream_files_are_well_formed` passes with Decision 13's rules on the new
   files and 066's unchanged; each new rule has a unit variant that fails with its own line: a
   `kit_extra` name not in the file; a `cwd_folders` entry that is not a folder of the source, or
   with `cwd = "tree"`; a support-file group path that is not staged; a `docstring_packages` entry
   the product does not ship; a path release group over a smoke group's file; a staged test
   module in neither tier; a second normal group in a family; a smoke group past 100 G, or smoke
   groups past 1 T together; a smoke group with a marker expression; a group without `measured`;
   a cap above `rule_cap(measured)`. **A unit check, written first**, collects a synthetic family
   with a smoke group over two of its files and path release groups over the rest, and shows every
   collected test in exactly one tier: none in both, none in neither (the owner's rule).
3. **The tie.** Unit checks with synthetic archives: a wheel whose `fonttools/ttLib/ttFont.py`
   differs from the test source's fails the family, naming the file; so does a differing data file
   (a zone file, say); a file the wheel ships that the source lacks fails unless `tie_skips` names
   it; a test source whose version is not the product pin's fails; a `MANIFEST` pin that differs
   from the source's hash fails (not blocked).
4. **The items.** Unit checks on fixed streams and synthetic modules: a `docstring_packages` entry
   walks every shipped module in sorted order, minus `docstring_not_selected`; a `module_functions`
   module's `test_*` functions become `::functions:` items; a marker deselection writes one `D`
   line per item and the record counts them with their reason; `cwd_folders` are copied into
   `/tmp/work` before the session.
5. **The survey, then the baseline** (EXECUTED on `d0d91cef`, Decision 1): the memo exists; its
   delta has the delta review's verdict (no owner question: the owner's standing rule); each group
   check fails before its lists and gaps exist.
6. **With the TOML, the lists and the gaps complete**, each group check passes; each class and trap
   check fails as its gap says; the numbers are in the landing notes, equal to the memo's or
   explained; every cap equals or is under `rule_cap(measured)`, and each family's budget is the
   sum of its caps.
7. **Fuel repeats** (066's criterion 5). The builder runs each smoke group twice, **restaging
   between the runs**: equal outcomes and `passed_digest`, and on darwin equal fuel within
   `sameness.py`'s tolerance. Each release group once, on darwin, by node id with `--tier
   release` (102); its outcomes and fuel in the landing notes.
8. **Nothing else moves.** The full judge's ratchet against the base: every existing row lost 0,
   grew 0; the `/upstream`, `/cpython` and 066 stages' manifests are byte-for-byte the base's.
9. **The artifact set.** The set rebuilt on the branch equals the base's in `python.wasm`, the
   snapshot, the zip and every `LICENSES` file; `MANIFEST` differs in exactly 39 added `pin` lines
   and the `recipe` line of `scripts/00_download.sh`; the set's `SHA256SUMS` only in `MANIFEST`'s
   line; 101's key changes once, for these pins.
10. **`packages.toml`.** The 42 are `suite`; a unit check fails if any entry names `spec 067`.
11. **The shards and the fetch** (as 066's criteria 7 and 8): each smoke group in exactly one
    normal Linux shard, each release group in exactly one release shard (102's rule); the workflow scan
    passes and fails on a missing matrix entry; a shard with `six` fetches the kit,
    `six-1.17.0.tar.gz` and the six wheel, and nothing else; a shard with `dateutil` also stages
    freezegun; a fetch that fails twice and succeeds the third time passes, and one that fails three
    times names the forge and the file.
12. **The full judge** green (`ruff check`, `ruff format --check`, the fast tier, and the full judge
    on CI) apart from the gaps this specification adds, each named.
13. **The branch's dry run, before landing**, and **the lane's after landing**, as 066's criteria
    12 and 13: every job green but growth lines and G7; every normal shard within 360 s. **One
    branch dispatch with 102's `release-tier` input true** runs every release shard once before
    review, each within 360 s but `sympy-slow-17141` (allowed past it); its run id, the release
    tier's measured total and the release shards' job times are in the landing notes, and 067's
    claim block in `context/release-tier-claims.toml` is written from it (102, Decision 6).

## The price (measured by the survey, 2026-10-21; the owner's rule)

- **Normal tier: 879 G** per full judge, the 42 smoke groups (EXECUTED): 7.8 % of today's about
  11.2 T of upstream fuel. Two Linux shards on every release run; the lane's darwin judge at every
  landing grows by about 2 to 2.5 minutes of guest time, under a minute of wall clock at `-n 3`.
- **Release tier: at least 66.3 T** (EXECUTED; a lower bound: four sympy sessions stopped at the
  survey's caps, and openpyxl's conftests did not load), sympy at least 52.2 T of it. About 95 to
  110 release shards of at most 725 G, plus `sympy-slow-17141` alone (INFERRED from the packing),
  on 102's release-tier runs only: about 20 to 25 more minutes of wall clock on those runs at 20
  parallel jobs, beside 095's about 75 shards and 102's twelve; on those runs Linux becomes the
  critical path (INFERRED).
- **The lane's release acceptance before a tag** grows by about 2.6 to 3.1 hours of guest time on
  darwin, about 0.9 to 1.1 hours of wall clock at `-n 3` (INFERRED at 0.14 to 0.17 s per G): the
  largest single cost of a publication, with 095's at least 53 T beside it.
- **Caps** by the rule, 1.5 times: about 1.3 T for the smoke groups; at least about 100 T for the
  release groups.
- **The survey:** done, about 3.7 hours of guest time for 85.4 T in one process.

## The owner's choices

- **Q1, answered 2026-10-20** (the lane's message):
  - (a) formulaic, interface-meta and wrapt (spec 045's pure dependencies of statsmodels) join
    067; statsmodels' own suite goes to 095. Written in: Decisions 2, 3, 12; Depends on.
  - (b) sympy's one slow test (about 2.6 T) runs on CI in a shard of its own allowed past the
    360 s bound. Written in: Decision 10, criterion 13.
  - (c) "I think we should have two concepts of tests. We do not need to run the slow tests unless
    we're are creating a new release that we publish to pypi. Otherwise, for normal checks, we
    don't run the slow tests." The lane's reading: upstream's opt-in slow tests form a release tier
    that runs only on the publishing run and the pre-tag dry run on main; branch runs, wave dry runs
    and the lane's accepts skip it; the mechanism is spec 102. Written in: Decisions 5 and 10,
    Scope. **Superseded in its reach by the standing rule below**: not only the opt-ins, every
    test of each suite but its smoke group is release-tier.
- **The standing rule, 2026-10-21** (the owner's words, through the lane): "we need to have fast
  tests and slow tests. We only run slow tests when we are trying to publish to pypi, as it is
  critical we check that our package is working on the libraries we import before we release to
  catch any errors, otherwise we should only run the tests needed to confirm our new edits are
  working." So each whole suite is release-tier and each package keeps a small normal-tier smoke
  group (about 1 T or less for all of them). Tier placement and fuel thresholds are not questions
  for the owner. Written in: Decisions 1, 10, 11, 13; criteria 2, 5, 7, 11, 13; the price.
- **The price** is no longer an owner question (the standing rule): the survey measured it and the
  delta review reads it (Decision 1).
- **Tag archives as test sources** for eight packages and one sample-files commit (Decision 3),
  with the stated risks. A default the owner may move.

## Disposition of the pre-build review (2026-10-20)

- **H1 — written in.** Every test upstream's runners select runs (Decision 5): sympy's slow and
  tooslow, networkx's and narwhals' `--runslow` and packaging's `property` tests in release-tier
  groups (Decision 10, the owner's (c)); doctests by import with upstream's flags and the
  `load_tests` suites, `docstring_packages` for the big packages; joblib's and sympy's doc files;
  patsy's inline tests as `module_functions`; pyparsing's `examples/tiny/tests` and dateutil's
  `docs/exercises/solutions/` staged; html5lib with its conftest and kit-extra; tqdm's
  `tests_perf.py` and `tests_asyncio.py` selected; trio tried; pypdf's sample files pinned;
  fonttools' `check_table_coverage_test.py` given its true reason (Decision 8). The false reasons
  are gone.
- **H2 — written in.** Decision 10: `measured` per group, caps by `rule_cap`, budgets the sums, no
  total fixed, splits by file and by `[[split]]`; the sympy order-of-keeping paragraph, the
  3×10¹² and 1.2×10¹² budgets and "sympy's share" are deleted; the review's measured rates replace
  the draft's; the price goes to the owner with the confirmation (Decision 1). The single test
  past every bound follows the owner's (b).
- **H3 — written in.** seaborn and reportlab are 067's (Decision 2): seaborn's pinned sdist, 050's
  tie; reportlab's sdist pinned as a test source, the wheel tie. With 045's three, 42 packages and
  39 pins. After 067 no entry names spec 067 (Decision 12, criterion 10).
- **M1 — written in, item by item.** (1) the keys renamed to 066's, `stage_folders` per family,
  `cwd = "tree"`; (2) `measured` (Decision 10); (3) `[[split]]` and the `collected` facts' reach;
  (4) shards and width (Decision 11, M2); (5) the confirmation round always (Decision 1); (6) fuel
  repeats restage (criterion 7); (7) the base: main after wave 09 and 045, no stacked build, the
  branch rebased onto main `5805af0`; (8) no closer names 067 (Decision 9); (9) typing-extensions
  as support files with `extra_sys_path = ["src"]`, and the support-file group path rule.
- **M2 — written in.** Decision 11 joins 101's `max-parallel: 20`, and the survey's delta states
  the legs, the rounds, the critical path and the lane's added fuel.
- **M3 — written in.** Depends on: 045's three are 067's, statsmodels 095's; `kit-extra.txt` shared
  with 095, second to land rebases; 101 named, 067 rebases onto it.
- **M4 — written in.** Decision 7: `cwd = "/tmp/work"` with `cwd_folders`; no second grant, no
  stage diff; host litter is 089's guard.
- **L1** — Decision 4: the tie covers every file the zip takes from the wheel; `tie_skips` names
  the rest. **L2** — Decision 4: only networkx carries a patch, its stage built after it. **L3** —
  Decision 3: forge availability named; `fetch.py` retries three times. **L4** — Decision 3 and
  criterion 9: 101's key changes once; `RESEARCH_PINS`-style pins weighed and refused. **L5** —
  Decision 6: the rule for optional modules and test-only modules. **L6** — Decision 5: marker
  deselections write `D` lines and are counted.
- **Notes.** numpy's and pandas' `not slow`: out of 067's scope, a release-tier member for 102 or
  a follow-up (Scope). The drafter's extraction count: no count here comes from it. The drafting
  evidence lands with 066 (wave 08); this branch adds `sdists-067-revision.txt` beside it.

## For the lane

- **Wave kind: build-class**, and it changes the artifact set (`MANIFEST`): the pre-build review
  was required (§5.6) and is done; the survey is done; **its delta review comes next** (a fresh,
  context-only reviewer; no owner question). A package wave's entry in kind (pins), with no
  rebuilt binary: the lane's rebuild must show criterion 9. **Dry-run needs:** the branch dry run
  (normal), one branch dispatch with `release-tier: true`, then the wave's.
- **Order.** After 045 and **after 102 lands** (or stacked on 102's reviewed tip, Depends on). 095
  shares `kit-extra.txt` and the path release kind (Decision 10): the second of 067 and 095 to be
  built rebases onto the first's.
- **Next:** the delta review of "Delta from the survey"; then the build (pins first, the survey's
  stage findings of the delta's item 4 in the harness, each group measured as built).
- **The claim list skeleton** (the builder fills each value):
  - **Gained rows, normal tier:** `test_upstream_suite[<family>-smoke]` for the 42 smoke groups,
    with metrics `fuel` and `passes` and facts `counts`, `passed_digest`, `left_out`; the classes
    their failures fit, each a gap.
  - **Gained rows, release tier:** every release group's `test_upstream_suite[<group>]`, its
    classes and traps: new rows in 102's `release_tier` list on a normal accept, accepted only at
    the release acceptance before a tag (102, Decision 5); **their claim block** in
    `context/release-tier-claims.toml`, written from the branch run with `release-tier: true`.
  - **Gaps added:** their count and ids, each with its closer.
  - **Moved rows:** none (criterion 8).
  - **The artifact set:** `MANIFEST` +39 `pin` lines and one `recipe` line; the set's
    `SHA256SUMS` line for `MANIFEST`; nothing else (criterion 9).
  - **The judge hash changes**; **packages.toml**: 39 `later` become `suite`, three added.
- **The flags** (skeleton; each reason begins with "067:"):

  ```
  --accept "067: the pure-Python packages' own tests: 42 packages, 42 smoke groups in the normal tier (<p> passes, <s> G), each whole suite in <r> release-tier groups; <c> classes, <t> traps; 39 test sources pinned and named in MANIFEST"
  --accept-judge "067: tests/upstream/<package>.toml and .ini for 42 families; kit-extra.txt; the wheel tie, kit_extra, cwd_folders, docstring_packages, module_functions, support-file group paths, marker D lines, the smoke rules and the path release kind in packages.py, tiers.py and package_drive.py; SOURCE_PATTERNS; fetch.py's tests lines, retries and wheels; packages.toml (42 suites); the normal and release shards in release_shards.toml and release.yml; the unit checks"
  ```

  No `--accept-growth` and no `--accept-fewer-passes`.

## Delta from the survey (2026-10-21, for the delta review)

The survey (`../research/2026-10-21-the-pure-python-packages-own-tests-under-the-runtime.md`,
EXECUTED on darwin-arm64 on `d0d91cef`) replaces this specification's INFERRED numbers. What it
changes, by Decision; a fresh reviewer rules on each before anything is built (Decision 1). No
item is a question for the owner (the standing rule of 2026-10-21).

1. **The price, measured** (the price section): **normal tier 879 G** (42 smoke groups);
   **release tier at least 66.3 T** (the 22 families with release groups; a lower bound because
   four sympy sessions (`solvers/ode`, the rest of `solvers`, `stats`, `calculus`) stopped at the survey's caps); the 42 whole suites at least 66.7 T. sympy is
   52.2 T of it (at least): its tests cost 0.35 G (core) to some 57 G (solvers' ODEs) a test, its
   doctests 3.45 T and its doc files 2.79 T. The drafted 25 to 35 T normal tier is gone: under the
   owner's rule a landing pays 879 G.
2. **Decision 10 rewritten for the owner's rule** (each suite in the release tier whole, a smoke
   group per package, the path partition, the path release kind for 102, twenty whole suites as
   their own smoke groups). The marker complement of the reviewed text is gone: no group carries a
   marker expression to split the tiers.
3. **Decision 11 rewritten**: two normal Linux shards, about 95 to 110 release shards; the lane's release
   acceptance grows by about 2.6 to 3.1 hours of guest time.
4. **What the stage needs** (the memo's item 4; each a build task, none a new decision but
   pypdf's):
   - every `.ini` with an `error` filter ignores pytest's assert-rewrite warning;
   - the markers upstream registers only in plugins (`no_cover`, `slow` for mpmath, `timeout`,
     `thread_unsafe`) are registered in the `.ini`s;
   - et-xmlfile's `norecursedirs`; wrapt's `extra_sys_path = ["tests/core"]`; the parents that
     networkx's, XlsxWriter's, openpyxl's, joblib's and fonttools' relative and sibling imports
     need;
   - openpyxl's conftests registered once (its numbers are a lower bound until then);
   - **sympy: `sys._running_pytest` set before the driver imports sympy**, so `@slow`,
     `@tooslow` and `@XFAIL` behave as under upstream's pytest (the survey ran sympy without it:
     its XFAILs are failures there, its slow tests ran in every session);
   - joblib's root conftest left out of the stage with its reason (it arms a watchdog thread),
     and upstream's own doctest skip without multiprocessing stated in the README;
   - reportlab with `RL_TEST_OUTDIR=/tmp/work/rl-out` in its family's `env` (095's Decision 7 adds
     the family `env` key with a per-family list of allowed names; whichever of 067 and 095 is
     built first adds the key, and reportlab's name joins the list) and `tests/charts-out/` not
     selected;
   - the guard held in every session: no module of the product's top-level names was loaded from
     outside the zip (the streams' `M` lines, EXECUTED); the only tree modules are tests, their
     helpers and pyparsing's `examples`;
   - html5lib with setuptools 66.1.1, pytest-expect from its sdist, and `-W
     ignore::pytest.PytestRemovedIn9Warning` in its family args.
5. **pypdf's `import ssl` (a decision for the review).** pypdf's `tests/__init__.py` imports `ssl`
   at module level; the product has no `_ssl`; every pypdf test module imports `tests`. Options:
   (a) **a recorded patch to the test source** (constitution §4.1: under `recipes/patches/`,
   hashed in `MANIFEST`, named in the CHANGELOG, its upstream pull request drafted, "tests: import
   ssl where it is used"), which the survey's edit is and which lets 1,689 tests pass; (b) pypdf's
   suite stays `later` with the true reason, its closer a reserved number. **Recommended: (a)**,
   the owner's "every test" with the smallest recorded change; the patch touches no byte the
   product ships.
6. **Decision 6's kit-extra**: setuptools 66.1.1 (not a current release; the reason above);
   pytest-expect 1.1.0 has no wheel, so `kit-extra.txt` admits one pure sdist; trio is not added.
7. **Decision 8's new rows**: jinja2's two async files (trio), cloudpickle's
   `cloudpickle_test.py` (psutil), formulaic's `test_base.py` (pyarrow), reportlab's
   `tests/charts-out/` (generated files).
8. **Decision 9's classes, confirmed or added**: `no-processes`, `no-threads`, `shallow-recursion`
   and `reportlab-fonts-not-shipped` seen as predicted; **`no-mmap`** added (xlrd's 65, the drafted
   classes had no row for it), and **`errno-58`** for wrapt's 37 and tqdm's 9 `OSError: [Errno 58]
   Not supported` (the call to be named in the build, as 095's delta says for scipy's).
9. **Doctests**: the survey ran them with flags 0, so their failure counts are upper bounds; the
   build runs each with upstream's flags (Decision 5) and measures again. Their fuel is real:
   sympy's 3.45 T, mpmath's 2.05 T, networkx's 0.11 T; sympy's doc files 2.79 T.

**What remains:** this delta's review; then the build (after 102 lands, or stacked on its reviewed
tip), with each group measured as built, sympy's capped areas measured to the end, and the single
failures read.

## Landing notes

Not built yet.
