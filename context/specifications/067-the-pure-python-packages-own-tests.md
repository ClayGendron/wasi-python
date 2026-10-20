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
  mechanism is spec 102 (reserved by the lane). **Not yet surveyed**: the survey runs on main's set
  after wave 09 lands, and its delta goes to a confirmation round before anything is built
  (Decision 1). It pins 39 test sources in `downloads/SHA256SUMS` and `scripts/00_download.sh`, so
  it is build-class, and `MANIFEST` gains their pin lines: it changes the artifact set, so
  constitution §5.6 requires its pre-build review (done) and the confirmation.
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
    its key over `downloads/SHA256SUMS` and `scripts/`. 067 is surveyed and built from main's tip
    after wave 09, on that set; no stacked build.
  - **045** (statsmodels, formulaic, interface-meta, wrapt; in 0.1.0 with 067): the three pure
    packages it adds are 067's (the owner, 2026-10-20). 067 is built after 045 lands, so the three
    are in the set it surveys; 045 names spec 067 as their closer in `packages.toml`, as 042 did for
    seaborn and reportlab. statsmodels' own suite closes with 095.
  - **102** (reserved by the lane, 2026-10-20): the release tier's mechanism. 067 marks its
    release-tier groups (Decision 10); 102 makes the judge, the shards and the workflow skip them
    outside the publishing run and the pre-tag dry run. Order: Decision 10's last bullet.
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

    Every other number of outcome or fuel below is INFERRED until the survey measures it.

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
not run named, the groups in Linux release shards and on the lane's darwin judge at every landing,
and upstream's opt-in slow tests in release-tier groups that run before a publication.

## Decisions

1. **The survey comes first; this draft's numbers are INFERRED until it runs.** As 066's
   Decision 1: the builder's first commit after the pins is the survey memo, EXECUTED on main's set
   after wave 09 (and 045), with each group's outcomes by id, fuel, traps and collection errors.
   **Its dated delta to Decisions 2, 5, 8, 9, 10 and 11 always goes to a confirmation round** (a
   fresh reviewer), with **the price** (total fuel per tier, the number of Linux shards per tier,
   the lane's added acceptance fuel and time, and whether Linux becomes the critical path); the
   lane puts the price to the owner with the confirmation, as it did for 066's re-survey. Building
   starts on that verdict.

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
     `sympy/testing/pytest.py`, READ); networkx's and narwhals' `--runslow` tests; packaging's
     `property` tests. Each normal group keeps upstream's default selection and records a `D` line
     for every item its marker expression deselects (below).
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
   | setuptools (a release that still ships `pkg_resources`; the survey names it) | html5lib | its conftest imports `pkg_resources` |
   | pytest-expect, u-msgpack-python | html5lib | its conftest loads the plugin, which reads `.pytest.expect` |
   | mock | html5lib | `html5lib/tests/test_meta.py` imports it |
   | pytest-asyncio | tqdm | `tests/tests_asyncio.py` |
   | pytest-doctestplus | sympy | `FLOAT_CMP` in its doctest flags |
   | pympler | attrs | its tests guard it; a test-only module |
   | trio and its pure dependencies (sniffio, outcome, sortedcontainers, idna), tried | jinja2 | `tests/test_async.py` and `tests/test_async_filters.py` import trio at module level; trio is jinja2's runtime alternative, not the product's. If trio cannot import under WASI, the survey writes that as the files' reason |

   freezegun requires python-dateutil, and trio requires attrs, which the product carries (the
   product's are used). The survey confirms each version and each import.

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

10. **The groups, their caps, the tiers, and no fixed budget.** One session and one check per
    group (066's Decision 11), each group carrying `measured = <fuel>` from the survey on main's
    set, its cap at most `rule_cap(measured)` (1.5 times, rounded up to two figures), each family's
    budget the sum of its caps. **No total is fixed** (the owner, 2026-10-20). A group past 480 G
    is split by file, in the test source's order; a file past 480 G is a `[[split]]` of
    constructed `-k` expressions (066's Decision 11); its `collected` facts are compared within one
    judge process and read by the lane across shards.
    - **Two tiers** (the owner, 2026-10-20: "We do not need to run the slow tests unless we're are
      creating a new release that we publish to pypi. Otherwise, for normal checks, we don't run
      the slow tests"). A **normal** group keeps upstream's default selection, and its `D` lines
      name each item it leaves to the release tier. A **release-tier** group (`tier = "release"`
      in its TOML) runs exactly those items, over the same paths with the complementary
      expression: a normal group with `-m "not (E)"` beside a release group with `-m "E"`, so
      every collected item is in exactly one of them, by construction, as a split's are. The rules
      check that each release-tier group's expression is the complement of its normal partner's.
      - sympy: normal `-m "not slow and not tooslow"` (upstream's `addopts`); release
        `-m "slow or tooslow"` (185 `@slow` and 14 `@tooslow` lines, READ), split as the survey
        measures. `tooslow` runs too: under "every test", and in the release tier where its cost
        is paid once per publication (the lane's reading of the owner's (c)).
      - networkx and narwhals: normal without `--runslow`; release with `--runslow -m slow`.
      - packaging: normal `-m "not property"`; release `-m property`.
    - **One test past every bound** (the owner's answer (b)): sympy's `test_issue_17141_slow`,
      about 2.61 T (EXECUTED by the pre-build review), cannot be split. It is a release-tier group
      of its own, `sympy-slow-17141`, by node id, with its own Linux shard allowed past the 360 s
      bound (about 420 to 810 s of job time at 066's measured rates, INFERRED). Any other single
      test the survey finds past 480 G is named in the delta, with the same treatment proposed.
    - **INFERRED fuel, corrected by measurement.** sympy costs about 1.6 to 2.3 G a test (the
      review's two modules), so its roughly 12,500 normal tests are about 20 to 28 T, plus its
      doctests; the release tier adds its slow tests (at least 2.6 T for one). The other 41
      packages, at the 16 to 48 M a pass of numpy's, pandas' and CPython's tests, are about 1 to
      4 T together, plus doctests (INFERRED; seaborn's plotting tests and openpyxl's and
      XlsxWriter's file round trips run heavier). In all, INFERRED, 067's normal tier is about 25 to
      35 T against 066's 10 T, in some 35 to 50 groups of at most 480 G each. The survey measures
      every group; the price goes to the owner (Decision 1).
    - **The order with 102.** 067 writes `tier = "release"` on its release groups. If 102 has
      landed when 067 is built, those groups run only where 102 says. If not, the lane decides at
      the confirmation whether 067 waits for 102 or lands with its release-tier groups refused by
      the rules check until 102 lands (never run in every run in the meantime, the owner's (c)).

11. **The release: Linux shards packed from the survey, under 101's matrix.** As 066's Decision 12:
    shards packed from the survey's measured fuel at most 725 G each, Linux only, the 360 s bound
    for every normal shard, a move past the bound a reviewed judge change. They join the Linux
    judge matrix under 101's `max-parallel: 20`, so they queue and do not widen a run. **The
    survey's delta states**: the count of Linux legs (066's fourteen plus 067's normal shards), the
    queue rounds, whether Linux still ends before macOS's last shard, the release-tier shards and
    the run they add to (the publishing run and the pre-tag dry run only, by 102), and the lane's
    added acceptance fuel (the lane's darwin judge runs every normal group at every landing; INFERRED,
    25 to 35 T on top of 066's 10 T and the rest, the largest cost in the pipeline). If Linux would
    become the critical path, the delta says so, and the owner sees it with the price. No group
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
    product's pin; every `tier = "release"` group's marker expression is the complement of its
    normal partner's over the same paths; every group has `measured`, and every cap is at most
    `rule_cap(measured)` (066's rule, unchanged).

14. **The README and the CHANGELOG.** The README's testing section names the 42 suites in one
    paragraph, the release tier, what is not run and why, and that eight come from release tags and
    one from pypdf's sample-files commit; each class closed by `README.md` has its fact there. The
    CHANGELOG: "The release runs the pure-Python packages' own tests (spec 067), their slow tests
    before a publication; 39 test sources are pinned and named in `MANIFEST`."

## Intent

The judge runs the own test suites of the 42 pure-Python packages inside the guest, from sources
pinned by hash and tied to the bytes the product ships, doctests and opt-ins included. It counts
every pass and names every known failure and every test it does not run. The release runs the
normal tier on Linux in new shards at every run, and the release tier before a publication; the
lane runs the normal tier on darwin at every landing. It turns red when a pass is lost, a test
traps, an unknown failure appears, a test runs against a copy of the product's code, or a test
source is not the shipped code's.

## Design

```
downloads/SHA256SUMS                 39 lines (30 sdists, 9 *-tag.tar.gz, pypdf's sample files among them)
scripts/00_download.sh               tests(): 39 lines; --tests fetches them
tests/upstream/<package>.toml, .ini  42 families (Decision 2); grant /upstream-<package>; kit_extra;
                                       cwd_folders (xlsxwriter, reportlab); docstring_packages;
                                       module_functions (patsy); tie_skips; tier = "release" groups
tests/upstream/kit-extra.txt         the test-only wheels of Decision 6
tests/upstream/expected/<group>/<class>.txt
tests/harness/pins.py                SOURCE_PATTERNS for each test source
tests/harness/packages.py            the wheel tie; kit_extra; cwd_folders; docstring_packages;
                                       module_functions; support-file group paths; marker D lines;
                                       the tier key and its complement rule
tests/upstream/package_drive.py      docstring packages, doc files, module functions, marker D lines
tests/harness/upstream.py            PACKAGE_SUITES += 42
tests/upstream/fetch.py              tests lines, with retries; the pinned wheel beside each test source
tests/upstream/packages.toml         42 suites
tests/release_shards.toml            upstream-pure-* (linux), sympy-slow-17141 (release tier)
.github/workflows/release.yml        judge-linux's matrix and outputs; gather's inputs
tests/known_gaps.toml                one entry per class and trap
tests/unit/test_packages.py, test_upstream.py, test_shards.py, test_fetch_trees.py, test_pins.py
README.md, CHANGELOG.md, context/progress/README.md, spec 063 (one dated line), context/roadmap.md
```

**A group's run** is 066's, with the wheel tie added at staging (Decision 4) and the items of
Decision 5.

**Spec 063, one dated line** in its Status: "2026-10-…: the 42 pure-Python packages are `suite`s
since spec 067, their slow tests in the release tier (spec 102)."

## Scope

**In:** the above: every test upstream's own runners select, doctests and opt-ins included, the
slow ones in the release tier.

**Out, each with its reason:**
- **The compiled packages** (066) and **scipy, scikit-learn, statsmodels** (095).
- **Packages added after this revision** (046's line's python-docx and python-pptx, and any
  later): each specification that adds a package adds its suite (AGENTS.md).
- **The release tier's mechanism** (spec 102): 067 marks its groups; 102 decides where they run.
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
   the product does not ship; a release-tier group whose expression is not its partner's
   complement; a group without `measured`; a cap above `rule_cap(measured)`.
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
5. **The survey, then the baseline** (EXECUTED on main's set after wave 09 and 045, with 067's
   pins, Decision 1): the memo exists; its delta has a confirmation verdict and the owner's answer
   on the price; each group check fails before its lists and gaps exist.
6. **With the TOML, the lists and the gaps complete**, each group check passes; each class and trap
   check fails as its gap says; the numbers are in the landing notes, equal to the memo's or
   explained; every cap equals or is under `rule_cap(measured)`, and each family's budget is the
   sum of its caps.
7. **Fuel repeats** (066's criterion 5). The builder runs each new group twice, **restaging between
   the runs**: equal outcomes and `passed_digest`, and on darwin equal fuel within `sameness.py`'s
   tolerance.
8. **Nothing else moves.** The full judge's ratchet against the base: every existing row lost 0,
   grew 0; the `/upstream`, `/cpython` and 066 stages' manifests are byte-for-byte the base's.
9. **The artifact set.** The set rebuilt on the branch equals the base's in `python.wasm`, the
   snapshot, the zip and every `LICENSES` file; `MANIFEST` differs in exactly 39 added `pin` lines
   and the `recipe` line of `scripts/00_download.sh`; the set's `SHA256SUMS` only in `MANIFEST`'s
   line; 101's key changes once, for these pins.
10. **`packages.toml`.** The 42 are `suite`; a unit check fails if any entry names `spec 067`.
11. **The shards and the fetch** (as 066's criteria 7 and 8): each new normal group in exactly one
    Linux shard, each release-tier group in exactly one release-tier shard; the workflow scan
    passes and fails on a missing matrix entry; a shard with `six` fetches the kit,
    `six-1.17.0.tar.gz` and the six wheel, and nothing else; a shard with `dateutil` also stages
    freezegun; a fetch that fails twice and succeeds the third time passes, and one that fails three
    times names the forge and the file.
12. **The full judge** green (`ruff check`, `ruff format --check`, the fast tier, and the full judge
    on CI) apart from the gaps this specification adds, each named.
13. **The branch's dry run, before landing**, and **the lane's after landing**, as 066's criteria
    12 and 13: every job green but growth lines and G7; every normal shard within 360 s; the
    release-tier shards run where 102 says, `sympy-slow-17141` allowed past 360 s.

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
    Scope.
- **The price** is not yet a question: the survey measures it, and the lane puts it to the owner
  with the confirmation round (Decision 1), as for 066.
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
  was required (§5.6) and is done; the survey's confirmation round comes next. A package wave's
  entry in kind (pins), with no rebuilt binary: the lane's rebuild must show criterion 9.
  **Dry-run needs:** the branch dry run, then the wave's.
- **Order.** After wave 08 (066) and wave 09 (099, 100, 101), and after 045; with or after 102
  (Decision 10's last bullet). 095 shares `kit-extra.txt`: the second to land rebases onto the
  first's.
- **Next:** the survey on main's set after wave 09 and 045 (a native build slot is not needed;
  guests only, at most three, never while `build/lane.lock` exists), its delta and price to a
  confirmation round and the owner.
- **The claim list skeleton** (the builder fills each value):
  - **Gained rows:** `test_upstream_suite[<group>]` for every normal and release-tier group, with
    new metrics `fuel` and `passes` and facts `counts`, `passed_digest`, `left_out`, `collected`
    for split groups, and the marker-deselection count; a class row per class with members and a
    trap row per trap, each a gap.
  - **Gaps added:** their count and ids, each with its closer.
  - **Moved rows:** none (criterion 8).
  - **The artifact set:** `MANIFEST` +39 `pin` lines and one `recipe` line; the set's
    `SHA256SUMS` line for `MANIFEST`; nothing else (criterion 9).
  - **The judge hash changes**; **packages.toml**: 39 `later` become `suite`, three added.
- **The flags** (skeleton; each reason begins with "067:"):

  ```
  --accept "067: the pure-Python packages' own tests in the release: 42 packages, <n> normal and <r> release-tier groups, <p> passes, <c> classes, <t> traps; 39 test sources pinned and named in MANIFEST"
  --accept-judge "067: tests/upstream/<package>.toml and .ini for 42 families; kit-extra.txt; the wheel tie, kit_extra, cwd_folders, docstring_packages, module_functions, support-file group paths, marker D lines and the release tier key in packages.py and package_drive.py; SOURCE_PATTERNS; fetch.py's tests lines, retries and wheels; packages.toml (42 suites); the Linux shards in release_shards.toml and release.yml; the unit checks"
  ```

  No `--accept-growth` and no `--accept-fewer-passes`.

## Landing notes

Not built yet.
