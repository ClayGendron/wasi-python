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
  constitution §5.6 requires its pre-build review (done) and the delta's confirmation. **The
  delta review** (`../reviews/067-the-pure-python-packages-own-tests-delta-2026-10-21.md`, "fit
  once the named findings are answered") **is answered in writing**, every finding, H1 and H2
  included ("Disposition of the delta review"), on this branch **rebased onto main `1875d4cd`**
  (no conflict) with the review cherry-picked. Built only after 102's build review, stacked on
  102's reviewed tip. **Built 2026-10-22, in wave 12, rebased onto `origin/wave/12` `99dcd257`** (Landing notes): every family measured by node id, sympy whole, its doctests under its own runner.
- **Owner:** Clay Gendron
- **Kind:** the build recipe's pins (39 lines in `downloads/SHA256SUMS`, 39 `tests` lines in
  `scripts/00_download.sh`), the judge, and the release workflow. No line of `src/` changes;
  **`recipes/patches/` gains test-source patches: four, plus any the build's reads add (narwhals, pyparsing), each named** (pypdf's, cloudpickle's, formulaic's and
  jinja2's, Decisions 4 and 8; the delta review's M1 and M2), each touching only the test source's
  test files, never a byte the zip ships; `python.wasm`, the snapshot and the stdlib zip do not
  change; `MANIFEST` gains 39 `pin` lines, one `recipe` line per carried test-source patch, and
  its `recipe` line for `scripts/00_download.sh` changes (Decision 3, criterion 9).
  - **New:**
    - `recipes/patches/pypdf-6.21.1/0001-tests-import-ssl-where-it-is-used.patch`,
      `recipes/patches/cloudpickle-3.1.2/0001-…`, `recipes/patches/formulaic-1.2.2/0001-…`,
      `recipes/patches/jinja2-3.1.6/0001-…` (Decision 8's rule), each with its upstream pull
      request draft under `context/upstream/patches/<folder>/` (pypdf's written with this
      revision; the other three written by the build, as the build writes the patches);
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
  - **102** (the release tier; `spec/102-the-release-tier`, tip `492b4586`: built, its smoke kind
    and its workflow half included, its branch runs and baseline read; **its build review not yet
    done**): `tier`, `release_by`, the smoke kind (`smoke`, `release_by = "path"`, Decision 2(d),
    built in `tests/harness/tiers.py`), the node-id group it leaves to 067, `release_checks`, the
    release shards (the pseudo-system `release`), the ratchet's `release_tier` rows and
    `context/release-tier-claims.toml` (its Decision 6, widened for local `--tier release` runs by
    node id). 067 needs all of it: with the owner's rule nearly every 067 group is release-tier.
    **So 067 waits for 102's build review.** It is then a stacked build on 102's reviewed tip
    (§4.14), its Status naming the base, rebasing onto main or the wave's tip when 102 lands; if 102
    has landed first, it is built on main's tip. **102 owns the path release kind**; 067 uses it as
    built and widens it in three named ways, built in 067's branch on 102's tip and reviewed with
    067, never in 102's branch ("For 102's path kind: 067's widening", below; the delta review's
    H2). Neither the survey nor this revision needs anything of 102: both are context only.
  - **039** (tier A), **041** (networkx from its sdist), **042** (seaborn and reportlab): what the
    zip carries, from which pin. **023** and **033**: the four plot wheels and `METADATA`.
  - **063**, **065**, **050**, **051**, **089**, **091**, **052**, **002**, as 066 lists them.
  - **In flight:** **095** (scipy's, scikit-learn's and statsmodels' own tests) shares
    `kit-extra.txt` and the `kit_extra` key: whichever of 067 and 095 lands second rebases onto the
    first's file and rules, and no family's extras stage into another's. 095 is ordered before
    067; its family `env` key (its Decision 7, a per-family list of allowed names) is the key
    reportlab's `RL_TEST_OUTDIR` uses: 067 adds reportlab's name to 095's list, a rebase, not a
    second key. 095 builds nothing of 102's path kind and needs none of 067's widening. **101**: 067 rebases onto
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
     (tarball and patches against `MANIFEST`) covers them. Of these, only networkx carries a patch
     (`recipes/patches/networkx-3.7/0001-graph-atlas-from-a-zip.patch`, which also patches
     `test_atlas.py`); its stage is built after the patch is applied, as 066's `stage()` does.
   - **For a patched test source** (pypdf, cloudpickle, formulaic and jinja2; Decision 8's rule,
     the delta review's M1 and M2). networkx and pypdf (and the other three) carry patches;
     **pypdf's touches only `tests/`**, and each of the four touches only its source's test files,
     never a file the wheel tie compares (READ for pypdf by the delta review: no module of the
     shipped `pypdf/` imports `ssl`). §4.1's guarantee, "the release fails on any difference from a
     pinned tarball other than exactly the recorded patches", reaches the test sources this way:
     - the judge unpacks the test source and applies its patches with
       `scripts/steps/apply_patches.sh`, the same applier the build uses, before staging;
     - `pins.tree_drift` and `tie_errors` (with `repo_patches`) check the staged tree against the
       pinned tarball plus exactly its recorded patches, as for numpy's;
     - each patch is a `recipe` line in `MANIFEST` (criterion 9), named in the CHANGELOG, counted in
       the README's "upstream patches carried", and drafted as an upstream pull request under
       `context/upstream/patches/<folder>/`;
     - each patch's folder is its source's top folder (`pypdf-6.21.1/`, `cloudpickle-3.1.2/`,
       `formulaic-1.2.2/`, `jinja2-3.1.6/`), which `scan.patch_errors` requires to be a pinned
       tarball's top; the build confirms 067's test pins are in the set `patch_errors` reads, and
       names the change if they are not.

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
   - **sympy's flag, a declared family key** (the delta review's M3). sympy's own
     `sympy/conftest.py` sets `sys._running_pytest = True` as its first statement, and only
     `sympy/testing/pytest.py` reads it (`USE_PYTEST`: then `XFAIL = pytest.mark.xfail`, `slow =
     pytest.mark.slow`, `tooslow = pytest.mark.tooslow`; EXECUTED by the delta review on the pinned
     wheel). The driver's `package_paths` imports sympy before any conftest loads, so without the
     flag sympy's helpers believe they are not under pytest. So:
     - **`sys_flags`, a new family key**, a list of names the driver sets to `True` on `sys` before
       it imports anything of the package: `sympy.toml` has `sys_flags = ["_running_pytest"]`, with
       its reason in words ("sympy's conftest sets it first; the driver imports sympy earlier, for
       `package_paths`"). The allowed names are a constant in `packages.py`, today only
       `_running_pytest`; a rules row refuses any other name, and a unit row covers the driver
       setting it. **No package name appears in the driver.**
     - sympy's `.ini` registers `slow` beside upstream's `nocache_fail` and `tooslow` (upstream's
       `pyproject.toml` registers only those two; with the flag set, `@slow` is the mark `slow`, and
       the driver's `--strict-markers` would refuse every module that uses it).
     - **The driver loads the `judge` hypothesis profile again after the conftests load**, before
       it writes the `P` line: sympy's conftest loads its own `sympy_hypothesis_profile`
       (`deadline=None`), and `upstream.py` refuses a stream whose `P` line is not derandomized
       with no database. The README says so; its only cost against upstream's profile is
       determinism. The build greps every other conftest it stages for `load_profile` and treats it
       the same way, naming each.
     - upstream sets no `xfail_strict`, so an XFAIL that passes is an xpass: **each sympy group's
       `counts` carries `xfailed` and `xpassed`**, and its lists and gaps are written from runs
       with the flag, never from the survey's (which ran without it, its XFAILs failures there).
     - It is not a weakening (rule 4): no check, golden output or allowance changes; the session
       becomes upstream's own.
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
   | ~~trio~~ (tried; **not added**) | jinja2 | the survey: trio 0.34.0 raises `NotImplementedError: unsupported platform` at import under WASI (`trio/_core/_run.py`), and, as a hypothesis entry point, it is imported by hypothesis itself, so staging it ends any session at start. `tests/test_async.py` and `tests/test_async_filters.py` run their asyncio half with a recorded patch that makes trio optional, the trio cases `D` lines with that reason (Decision 8) |

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

8. **What is not selected, each with its true reason and closer.** **A file is not selected only
   when every test in it needs what the product does not have** (066's Decision 8, tightened by the
   delta review's M1). **A file that cannot load only because of a module-level import that some
   of its tests use gets a recorded test-source patch** (Decision 4's form, §4.1) that makes that
   import lazy or optional; the tests that need the module are then a class, or `D` lines with that
   reason, and every other test in the file runs. It applies to four, plus any the build's reads add (narwhals, pyparsing), each named; each patch and
   its count of tests recovered in the landing notes:
   - **pypdf**: `tests/__init__.py` imports `ssl` at module level and uses it only in
     `_get_data_from_url` (lines 46 to 48, which download); the patch moves the import into that
     function (`0001-tests-import-ssl-where-it-is-used.patch`; the survey's edit, which let 1,689
     tests pass; upstream's main still has the import, READ by the delta review);
   - **cloudpickle**: `tests/testutils.py` imports `psutil` at line 13 and uses it once, at line 166;
     `tests/cloudpickle_test.py` (139 `def test_`) fails only through `from .testutils import …`.
     The patch makes the import lazy at its one use;
   - **formulaic**: `tests/materializers/test_base.py` imports `pyarrow` at module level, used by one
     of its eight tests (line 51); the patch imports it inside that test, which then skips or fails
     as a class ("no pyarrow");
   - **jinja2**: `tests/test_async.py` (60) and `tests/test_async_filters.py` (25) import `trio` only
     to parametrize a fixture over `[_asyncio_run, trio.run]`; the patch makes trio optional, so the
     asyncio half runs (as tqdm's `tests_asyncio.py` does in the guest) and the trio cases are `D`
     lines with the reason "trio cannot import under WASI" (Decision 6).
   - **narwhals**: the build reads each of its 13 pyarrow and polars modules against the same rule
     and names, per file, a patch or a true not-selected reason.

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
   | reportlab (the survey) | `tests/charts-out/` | generated chart scripts the sdist carries from an earlier run, not tests: upstream's `runAll.py` excludes `*/charts-out/*.py`; nine do not parse | `README.md` |

   pyparsing's `test_diagram.py` and narwhals' pyarrow and polars modules stay rows only if the
   build reads that every test in each needs the missing module; otherwise the rule above gives the
   file a patch. jinja2's two async files, cloudpickle's `cloudpickle_test.py` and formulaic's
   `test_base.py` are no longer rows: the rule above recovers them (the survey had listed them).

   Selected now, against the draft (the review, H1): tqdm's `tests_perf.py` (a file that loads is
   selected, and its failures are a class) and `tests_asyncio.py`; jinja2's `test_async*.py` (their
   asyncio half, with the patch above); html5lib's conftest and its data-driven suite
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
      included (102's machinery: the tag run, the dry run on main before a tag, and the lane's
      release acceptance before a tag; **no branch run runs release groups**, `decisions.md`,
      2026-10-21). Each package keeps
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
      split it, and a keyword split is what 102's smoke kind refuses (the delta review: "pyyaml
      stays whole"). This is a named choice under the owner's rule: these twenty suites run on every
      landing because running fewer of their tests would cost about as much.
    - **102's path release kind, as built** (102's Decision 2(d), `tests/harness/tiers.py` at
      `492b4586`). 067 uses it unchanged: `smoke` (its reason in words) on each normal group,
      `release_by = "path"` on each release group over test files, `--ignore` of each smoke path
      under a path group's folder, no `[[release_select]]` in a smoke family, `tiers.SMOKE_BUDGET`
      (500 G per family). **The twenty whole-as-smoke families carry `smoke` too**, with the reason
      "the whole suite: a smaller smoke group would cost as much", so the record names every normal
      group of a package as its smoke. What 102's kind cannot yet hold, 067 widens in its own
      branch: "For 102's path kind: 067's widening", below.
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
      480 G gets the same treatment, named in the build's landing notes (Delta, item 1). Each
      node-id group's ids are `--deselect`ed by the one path group whose paths hold them (the
      widening's (iii)), so no test runs twice.
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
      where 102 runs them: **at least 95 to 110 shards** for release groups of at least 65.8 T
      (the price), plus `sympy-slow-17141` alone and any single sympy test the build finds past
      725 G; **about 110 to 125**, the INFERRED upper estimate, if sympy's four capped areas hold
      what their counts suggest (the delta review's L1). A 725 G shard is 116 to 225 s of guest time
      plus about 60 s of setup.
    - **The job count.** On a normal run the Linux matrix gains two jobs. On a release-tier run
      `judge-release` gains at least about 95 to 110 (up to about 110 to 125), which at 101's 20
      parallel jobs is about five to six more waves of four to five minutes, beside 102's twelve and
      095's about 75 (INFERRED from the packing). Only the tag run and the dry run on main before a
      tag pay it, never a landing or a branch run.
    - **The first CI run of 067's release shards is the dry run on main before 0.1.0's tag** (no
      branch run runs release groups, `decisions.md`, 2026-10-21; as 095). Each release group is
      measured once locally on darwin by node id with `--tier release` (criterion 7), and the
      packing uses that fuel. **A release shard past 360 s on that dry run is re-packed from the
      darwin fuel before the tag** (a judge change, reviewed; `sympy-slow-17141` and any other
      single-test shard allowed past it).
    - **The lane's release acceptance before a tag** (102, Decision 5) grows by at least about 2.6
      to 3.1 hours of guest time on darwin, about 0.9 to 1.1 hours of wall clock at `-n 3`; the
      INFERRED upper estimate, which the lane books its slot from, is about 3 to 3.6 hours of guest
      time, about 1 to 1.2 hours of wall clock (at 0.14 to 0.17 s per G). With 095's at least 53 T
      it is the largest single cost of a publication.
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
    product's pin; `sys_flags` names only allowed names (Decision 5); every test-source patch is
    under its source's top folder and applies cleanly (Decision 4). **The tier rules are 102's,
    as built** (its Decision 2(d): `smoke` on every normal group of a smoke family, path groups
    only in a smoke family and never over a smoke path, every staged test file in exactly one
    tier, `SMOKE_BUDGET` per family), with **067's widening** ("For 102's path kind", below), and
    **067's own bounds, scoped to the 42 families of this specification in `packages.py`** (the
    delta review's L2; 095's families are not counted): each of the 42 has exactly one normal group,
    its smoke group; each smoke group's `measured` is under 100 G, and the 42 smoke groups'
    together under 1 T. A smoke group names no marker expression of its own (a family exclusion
    with a true reason, pypdf's `enable_socket`, applies to every group alike), and **its run
    deselecting or skipping a test for an opt-in is red** (a verdict row on the stream: a skip
    whose reason is the family's opt-in, networkx's "need --runslow option to run", say). Every
    group has `measured`, and every cap is at most `rule_cap(measured)` (066's rule, unchanged).

14. **The README and the CHANGELOG.** The README's testing section names the 42 suites in one
    paragraph, the two tiers (each whole suite before a publication, a smoke group per package on
    every run), what is not run and why, and that eight come from release tags and one from pypdf's
    sample-files commit; each class closed by `README.md` has its fact there. The CHANGELOG: "The
    release runs the pure-Python packages' own tests (spec 067): each whole suite before a
    publication, a smoke group per package on every run; 39 test sources are pinned and named in
    `MANIFEST`; test-source patches are carried (four, plus any the build's reads add (narwhals, pyparsing), each named: pypdf, cloudpickle, formulaic, jinja2), each
    making one test-only import lazy or optional." The README's "upstream patches carried" count
    rises by as many.

## For 102's path kind: 067's widening

102 owns `release_by = "path"` and its rules, as built (its Decision 2(d), `tests/harness/tiers.py`
at `492b4586`, ten unit rows; asked by 095). 067 uses them unchanged and **widens three things**,
built in **067's branch, stacked on 102's reviewed tip**, reviewed with 067, never in 102's branch
(so 102's wave is not reopened). 095 needs none of them: its three suites use `test_*.py`, and
its doctests and modes stay unrun for 0.1.0.

- **(i) A smoke family's staged-test pattern is its upstream `python_files`**, read from the
  family's `.ini`, where it differs from 102's `TEST_FILE` (`test_*.py` or `*_test.py`). tqdm's
  `tests/tests_*.py`, dateutil's `docs/exercises/solutions/*_solution.py`, defusedxml's `tests.py`
  and patsy's `*.py` are then staged test files the partition sees; without it, a tqdm smoke group
  over `tests/` fails 102's "holds no staged test file", and dateutil's solutions would be in no
  tier unseen. **patsy** (`python_files = *.py`, `testpaths = patsy`): its stage holds only its six
  `patsy/test_*.py` files, which the path rule partitions as staged test files; its library
  modules are never staged (they run from the product's zip), so **`module_functions` covers
  them**, each of its 18 modules in exactly one item group under (ii), never the path rule.
- **(ii) A release group of a smoke family may be an item group**: its unit is a module or a file,
  not a test path. Four forms: `docstring_modules`, `docstring_packages`, `doctest_files` and
  `module_functions` (sympy's doctests 3.45 T and doc files 2.79 T, mpmath's doctests 2.05 T,
  networkx's, fonttools', joblib's, tabulate's, patsy's inline tests; more-itertools' smoke group
  is the item group `more_itertools.recipes`, normal). The "exactly one tier" rule covers those
  units as it covers test files: each shipped module of a `docstring_packages` entry, less its
  `docstring_not_selected`, each `docstring_modules` module, each doctest file and each
  `module_functions` module is in exactly one group, normal or release. 102's Decision 3 would
  otherwise refuse these release groups as "of no named kind".
- **(iii) A node-id group's ids lie in exactly one path group's paths, and that path group
  `--deselect`s exactly them** (`sympy-slow-17141`, and any sympy test the build finds past 480 G).
  So no test runs twice and none runs in neither.

Each of the three gets a unit row, written first and seen failing, on 102's synthetic smoke family
(criterion 2). Rows 102 already has (a path group over a smoke file, a staged file in no tier, a
smoke family with `[[release_select]]`) are 102's and are not repeated here.

## Intent

The judge runs the own test suites of the 42 pure-Python packages inside the guest, from sources
pinned by hash and tied to the bytes the product ships, doctests and opt-ins included. It counts
every pass and names every known failure and every test it does not run. Each whole suite is
release-tier: it runs on Linux in release shards before a publication (102's tag run and the dry
run on main before a tag; no branch run runs release groups) and in the lane's release acceptance.
One small smoke group per package is normal-tier: it runs on every release run in one or two
Linux shards and in the lane's darwin judge at every landing. It turns red when a pass is lost, a test
traps, an unknown failure appears, a test runs against a copy of the product's code, or a test
source is not the shipped code's.

## Design

```
downloads/SHA256SUMS                 39 lines (30 sdists, 9 *-tag.tar.gz, pypdf's sample files among them)
scripts/00_download.sh               tests(): 39 lines; --tests fetches them
recipes/patches/<source>/0001-*.patch test-source patches: four (pypdf, cloudpickle, formulaic, jinja2),
                                       plus any the build's reads add (narwhals, pyparsing), each named,
                                       applied by scripts/steps/apply_patches.sh when the judge
                                       unpacks the test source; checked by pins.tree_drift and
                                       tie_errors (repo_patches)
context/upstream/patches/<source>/   each patch's upstream pull request draft
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
tests/harness/tiers.py               102's path kind as built, and 067's widening (i) to (iii),
                                       built in 067's branch on 102's reviewed tip
tests/upstream/package_drive.py      docstring packages, doc files, module functions, marker D lines;
                                       the family's sys_flags before any import of the package; the
                                       judge hypothesis profile loaded again after the conftests
tests/harness/upstream.py            PACKAGE_SUITES += 42
tests/upstream/fetch.py              tests lines, with retries; the pinned wheel beside each test source
tests/upstream/packages.toml         42 suites
tests/release_shards.toml            upstream-pure-smoke-* (linux, normal), upstream-pure-r-* and
                                       sympy-slow-17141 (release pseudo-system, 102)
.github/workflows/release.yml        judge-linux's and judge-release's matrices (102's job); gather's inputs
context/release-tier-claims.toml     067's claim block (102, Decision 6), from local --tier release runs
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
   the product does not ship; among this specification's 42 families only, a second normal group
   in a family, a smoke group past 100 G, or smoke groups past 1 T together (a 095 family is not
   counted: the delta review's L2); a smoke group with a marker expression; a `sys_flags` name
   outside the allowed list; a test-source patch outside its source's top folder; a group without
   `measured`; a cap above `rule_cap(measured)`. **067's widening** (each on 102's synthetic smoke
   family, written first and seen failing on 102's tip): (i) a smoke family whose `.ini` names
   `python_files = tests_*.py` holds a `tests_x.py` in no group, and is red; (ii) a
   `docstring_packages` release group and a smoke group that both hold one shipped module are red,
   as is a shipped module of the entry in no group (less `docstring_not_selected`), and a
   `module_functions` or `doctest_files` release group is accepted, not refused as "of no named
   kind"; (iii) a node-id group whose id its path group does not `--deselect`, or whose id lies in
   no path group's paths, is red. **A verdict row on a fixed stream:** a smoke group whose stream
   holds a skip with the family's opt-in reason (networkx's "need --runslow option to run") is red
   (the delta review's L4). Rows 102 already has (a path group over a smoke file, a staged file in
   no tier) are 102's, not repeated.
3. **The tie.** Unit checks with synthetic archives: a wheel whose `fonttools/ttLib/ttFont.py`
   differs from the test source's fails the family, naming the file; so does a differing data file
   (a zone file, say); a file the wheel ships that the source lacks fails unless `tie_skips` names
   it; a test source whose version is not the product pin's fails; a `MANIFEST` pin that differs
   from the source's hash fails (not blocked); **a pypdf stage with its patch unapplied, or applied
   at an offset, fails the tie and names the file** (`tree_drift` with `repo_patches`; the delta
   review's M2), and so does a patch file whose hash differs from its `MANIFEST` `recipe` line.
4. **The items.** Unit checks on fixed streams and synthetic modules: a `docstring_packages` entry
   walks every shipped module in sorted order, minus `docstring_not_selected`; a `module_functions`
   module's `test_*` functions become `::functions:` items; a marker deselection writes one `D`
   line per item and the record counts them with their reason; `cwd_folders` are copied into
   `/tmp/work` before the session; **a family's `sys_flags` are set on `sys` before the driver
   imports the package** (a synthetic module that reads the flag at import sees it); **on a fixed
   stream, a sympy XFAIL is reported `xfailed`** and the group's `counts` carry `xfailed` and
   `xpassed`; **a conftest that loads its own hypothesis profile leaves the `P` line derandomized
   with no database** (the driver loads `judge` again after the conftests; the delta review's M3).
5. **The survey, then the baseline** (EXECUTED on `d0d91cef`, Decision 1): the memo exists; its
   delta has the delta review's verdict (no owner question: the owner's standing rule); each group
   check fails before its lists and gaps exist.
6. **With the TOML, the lists and the gaps complete**, each group check passes; each class and trap
   check fails as its gap says; the numbers are in the landing notes, equal to the memo's or
   explained; every cap equals or is under `rule_cap(measured)`, and each family's budget is the
   sum of its caps.
7. **Fuel repeats** (066's criterion 5). The builder runs each smoke group twice, **restaging
   between the runs**: equal outcomes and `passed_digest`, and on darwin equal fuel within
   `sameness.py`'s tolerance. **Each release group once, locally on darwin, by node id with
   `--tier release`** (102), the builder pausing while `build/lane.lock` exists; its outcomes and
   fuel in the landing notes. **067's `[[claim]]` block in `context/release-tier-claims.toml` and
   the release tier's measured total come from those runs** (102, Decision 6 as widened for local
   runs by node id), and the release shards are packed from that fuel.
8. **Nothing else moves.** The full judge's ratchet against the base: every existing row lost 0,
   grew 0; the `/upstream`, `/cpython` and 066 stages' manifests are byte-for-byte the base's.
9. **The artifact set.** The set rebuilt on the branch equals the base's in `python.wasm`, the
   snapshot, the zip and every `LICENSES` file; `MANIFEST` differs in exactly 39 added `pin`
   lines, the `recipe` line of `scripts/00_download.sh`, and one added `recipe` line per carried
   test-source patch (four, plus any the build's reads add (narwhals, pyparsing), each named: pypdf, cloudpickle, formulaic, jinja2); the set's `SHA256SUMS` only in
   `MANIFEST`'s line; 101's key changes once, for these pins and patches.
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
    12 and 13: every job green but growth lines and G7; every normal shard within 360 s. **No
    dispatch with `release-tier` true** (the owner's rule: no branch run runs release groups;
    `decisions.md`, 2026-10-21; as 095's criterion 12). The release groups are measured locally by
    node id (criterion 7). **The first CI run of 067's release shards is the dry run on main before
    0.1.0's tag**; a release shard past 360 s there is re-packed from the darwin fuel before the
    tag, `sympy-slow-17141` and any other single-test shard allowed past it.

## The price (measured by the survey, 2026-10-21; the owner's rule)

- **Normal tier: 879 G** per full judge, the 42 smoke groups (EXECUTED): 7.8 % of today's about
  11.2 T of upstream fuel. Two Linux shards on every release run; the lane's darwin judge at every
  landing grows by about 2 to 2.5 minutes of guest time, under a minute of wall clock at `-n 3`.
- **Release groups: at least 65.8 T** (EXECUTED: the 22 families' whole suites, 66.3 T, less
  their 496.5 G of smoke files); **a release-tier run, both tiers: at least 66.7 T**. A lower
  bound: four sympy sessions stopped at the survey's caps (after 70 of 144, 244 of 441, 144 of 225
  and 30 of 47 test functions), and openpyxl's conftests did not load. sympy at least 52.2 T.
- **The INFERRED upper estimate** (the delta review's L1, extrapolated by count): the capped
  areas hold about 26 T, not 15 T, so **sympy about 63 T and the release tier "at least" about
  77 T**. The lane books from this.
- **Release shards:** at least about 95 to 110 of at most 725 G, **about 110 to 125** at the upper
  estimate, plus `sympy-slow-17141` alone (INFERRED from the packing), on the tag run and the dry
  run on main before a tag only: about 20 to 30 more minutes of wall clock on those runs at 20
  parallel jobs, beside 095's about 75 shards and 102's twelve; on those runs Linux becomes the
  critical path (INFERRED). No branch run pays it.
- **The lane's release acceptance before a tag** grows by at least about 2.6 to 3.1 hours of
  guest time on darwin (0.9 to 1.1 hours of wall clock at `-n 3`), about 3 to 3.6 hours (1 to 1.2
  hours of wall clock) at the upper estimate (INFERRED at 0.14 to 0.17 s per G): the largest
  single cost of a publication, with 095's at least 53 T beside it.
- **Caps** by the rule, 1.5 times: about 1.3 T for the smoke groups; at least about 99 T (about
  115 T at the upper estimate) for the release groups.
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
  was required (§5.6) and is done; the survey is done; its delta review is done
  (`../reviews/067-the-pure-python-packages-own-tests-delta-2026-10-21.md`, "fit once the named
  findings are answered"; answered here, "Disposition of the delta review"). A package wave's
  entry in kind (pins and test-source patches), with no rebuilt binary: the lane's rebuild must
  show criterion 9. **Dry-run needs:** the branch dry run (normal tier only; **no dispatch with
  `release-tier` true**), then the wave's.
- **The pre-tag dry run on main is the first time 067's release shards run on Linux.** A shard
  past 360 s there is re-packed from the darwin fuel before the tag. The lane books the release
  acceptance from the upper estimate (about 77 T; the price).
- **Order.** After 045, and **after 102's build review**: stacked on 102's reviewed tip (or on
  main once 102 lands). 067's widening of 102's path kind is built in 067's branch, never in
  102's. 095 shares `kit-extra.txt` and the family `env` key: the second of 067 and 095 to be
  built rebases onto the first's.
- **Next:** the build, when the lane says 102 is reviewed (pins first; the delta's item 4 and the
  delta review's findings in the harness; each smoke group measured as built and each release
  group measured locally by node id).
- **The claim list skeleton** (the builder fills each value):
  - **Gained rows, normal tier:** `test_upstream_suite[<family>-smoke]` for the 42 smoke groups,
    with metrics `fuel` and `passes` and facts `counts`, `passed_digest`, `left_out`; the classes
    their failures fit, each a gap.
  - **Gained rows, release tier:** every release group's `test_upstream_suite[<group>]`, its
    classes and traps: new rows in 102's `release_tier` list on a normal accept, accepted only at
    the release acceptance before a tag (102, Decision 5); **their claim block** in
    `context/release-tier-claims.toml`, written from the builder's local `--tier release` runs by
    node id (criterion 7; 102, Decision 6 as widened).
  - **Gaps added:** their count and ids, each with its closer.
  - **Moved rows:** none (criterion 8).
  - **The artifact set:** `MANIFEST` +39 `pin` lines, one `recipe` line per test-source patch (four, plus any the build's reads add (narwhals, pyparsing), each named) for the test-source
    patches, and the changed `recipe` line of `scripts/00_download.sh`; the set's `SHA256SUMS`
    line for `MANIFEST`; nothing else (criterion 9).
  - **The judge hash changes**; **packages.toml**: 39 `later` become `suite`, three added.
- **The flags** (skeleton; each reason begins with "067:"):

  ```
  --accept "067: the pure-Python packages' own tests: 42 packages, 42 smoke groups in the normal tier (<p> passes, <s> G), each whole suite in <r> release-tier groups; <c> classes, <t> traps; 39 test sources pinned and <k> test-source patches carried, named in MANIFEST"
  --accept-judge "067: tests/upstream/<package>.toml and .ini for 42 families; kit-extra.txt; the wheel tie over patched test sources, kit_extra, cwd_folders, docstring_packages, module_functions, sys_flags, support-file group paths, marker D lines, the judge profile reloaded after conftests, the smoke bounds, and the widening of 102's path kind in packages.py, tiers.py and package_drive.py; SOURCE_PATTERNS; fetch.py's tests lines, retries, wheels and patches; packages.toml (42 suites); the normal and release shards in release_shards.toml and release.yml; the unit checks"
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
   group per package, the path partition, twenty whole suites as their own smoke groups; the path
   kind is 102's as built, with 067's widening: the delta review's H2). The marker complement of the reviewed text is gone: no group carries a
   marker expression to split the tiers.
3. **Decision 11 rewritten**: two normal Linux shards, at least about 95 to 110 release shards
   (about 110 to 125 at the upper estimate); the lane's release acceptance grows by at least about
   2.6 to 3.1 hours of guest time (about 3 to 3.6 at the upper estimate; the delta review's L1).
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
   - reportlab with `RL_TEST_OUTDIR=/tmp/work/rl-out` in its family's `env` (095's Decision 7 key,
     a per-family list of allowed names; 095 is ordered first, so reportlab's name joins 095's
     list, a rebase, not a second key) and `tests/charts-out/` not selected;
   - the guard held in every session: no module of the product's top-level names was loaded from
     outside the zip (the streams' `M` lines, EXECUTED); the only tree modules are tests, their
     helpers and pyparsing's `examples`;
   - html5lib with setuptools 66.1.1, pytest-expect from its sdist, and `-W
     ignore::pytest.PytestRemovedIn9Warning` in its family args.
5. **pypdf's `import ssl` (decided by the delta review: (a); Decisions 4 and 8).** pypdf's `tests/__init__.py` imports `ssl`
   at module level; the product has no `_ssl`; every pypdf test module imports `tests`. Options:
   (a) **a recorded patch to the test source** (constitution §4.1: under `recipes/patches/`,
   hashed in `MANIFEST`, named in the CHANGELOG, its upstream pull request drafted, "tests: import
   ssl where it is used"), which the survey's edit is and which lets 1,689 tests pass; (b) pypdf's
   suite stays `later` with the true reason, its closer a reserved number. **Recommended: (a)**,
   the owner's "every test" with the smallest recorded change; the patch touches no byte the
   product ships.
6. **Decision 6's kit-extra**: setuptools 66.1.1 (not a current release; the reason above);
   pytest-expect 1.1.0 has no wheel, so `kit-extra.txt` admits one pure sdist; trio is not added.
7. **Decision 8's new rows**: reportlab's `tests/charts-out/` (generated files). The survey had
   also listed jinja2's two async files (trio), cloudpickle's `cloudpickle_test.py` (psutil, in
   fact imported by `tests/testutils.py`) and formulaic's `test_base.py` (pyarrow); the delta
   review's M1 recovers them with recorded test-source patches (Decision 8's rule).
8. **Decision 9's classes, confirmed or added**: `no-processes`, `no-threads`, `shallow-recursion`
   and `reportlab-fonts-not-shipped` seen as predicted; **`no-mmap`** added (xlrd's 65, the drafted
   classes had no row for it), and **`errno-58`** for wrapt's 37 and tqdm's 9 `OSError: [Errno 58]
   Not supported` (the call to be named in the build, as 095's delta says for scipy's).
9. **Doctests**: the survey ran them with flags 0, so their failure counts are upper bounds; the
   build runs each with upstream's flags (Decision 5) and measures again. Their fuel is real:
   sympy's 3.45 T, mpmath's 2.05 T, networkx's 0.11 T; sympy's doc files 2.79 T.

**What remained:** this delta's review, now done and answered ("Disposition of the delta review",
below); then the build (after 102's build review, stacked on its reviewed tip), with each group
measured as built, sympy's capped areas measured to the end, and the single failures read.

## Disposition of the delta review (2026-10-21)

The review: `../reviews/067-the-pure-python-packages-own-tests-delta-2026-10-21.md` ("fit once the
named findings are answered"), reviewing `a5c4fb5b`; cherry-picked onto this branch after its
rebase onto main `1875d4cd` (no conflict). Every finding is written in, before any build:

- **H1 — written in.** No dispatch with `release-tier` true anywhere: Decision 10 ("no branch run
  runs release groups"), Decision 11 (the job count; the first CI run of the release shards is the
  dry run on main before 0.1.0's tag, a shard past 360 s there re-packed from darwin fuel),
  criterion 7 (each release group measured locally by node id with `--tier release`, the claim
  block and the release total from those runs), criterion 13 (no such dispatch), the Intent, and
  For the lane (dry-run needs, the claim block, the pre-tag line).
- **H2 — written in.** 102 owns the path kind as built (`492b4586`); "whichever of 067 and 095 is
  built first adds it" is deleted (Decision 10, For the lane, Depends on). The new section "For
  102's path kind: 067's widening" names (i) `python_files` patterns, (ii) item groups
  (`docstring_modules`, `docstring_packages`, `doctest_files`, `module_functions`) and (iii)
  node-id groups `--deselect`ed by their path group, each with a unit row on 102's synthetic smoke
  family (criterion 2), built in 067's branch on 102's reviewed tip, never in 102's. The twenty
  whole-as-smoke families carry `smoke`, with their reason (Decision 10). 102's own rows are not
  repeated.
- **M1 — written in.** Decision 8's rule: a file that cannot load only because of a module-level
  import some of its tests use gets a recorded test-source patch; a file is not selected only when
  every test in it needs what the product lacks. Applied to cloudpickle (the import is in
  `tests/testutils.py:13`, corrected), formulaic and jinja2's asyncio half; narwhals' 13 modules
  and pyparsing's `test_diagram.py` read against it by the build; each patch's recovered count in
  the landing notes.
- **M2 — written in.** pypdf takes (a): `recipes/patches/pypdf-6.21.1/0001-tests-import-ssl-where-it-is-used.patch`
  (Kind, Decision 4, Design), applied by `scripts/steps/apply_patches.sh` when the judge unpacks
  the test source, checked by `pins.tree_drift` and `tie_errors` with `repo_patches` (Decision 4),
  a `recipe` line in `MANIFEST` (criterion 9), a tie row for an unapplied or offset patch
  (criterion 3), the CHANGELOG line and the README's count (Decision 14). Its upstream pull request
  draft is `../research/2026-10-21-the-pure-python-packages-own-tests-under-the-runtime/pypdf-0001-tests-import-ssl-where-it-is-used.md`
  until the build, which commits it at `../upstream/patches/pypdf-6.21.1/` with the patch (the
  confirmation's Medium: a draft without its patch fails the carried-patch rules), written
  with this revision; the patch file itself is the build's (no file under `recipes/` changes in a
  context-only revision).
- **M3 — written in.** Decision 5: `sys_flags = ["_running_pytest"]`, a declared key in
  `sympy.toml` with its reason, an allowed-names constant in `packages.py`, no package name in the
  driver; sympy's `.ini` registers `slow`; the driver loads the `judge` profile again after the
  conftests (README); `xfailed` and `xpassed` kept in each sympy group's `counts`, its lists
  written from runs with the flag; other conftests grepped for `load_profile`. Criterion 4's rows.
- **L1 — written in.** The price, Decision 11 and the delta: release groups at least 65.8 T, a
  release-tier run at least 66.7 T; the INFERRED upper estimate, release tier "at least" about
  77 T, sympy about 63 T, 110 to 125 shards, the lane's acceptance about 3 to 3.6 hours of guest
  time, which the lane books from.
- **L2 — written in.** Decision 13 and criterion 2: 067's bounds (one normal group, 100 G a smoke
  group, 1 T together) are scoped to the 42 families of this specification in `packages.py`.
- **L3 — written in.** Depends on: 102's tip `492b4586`, built, its build review not yet done; 067
  waits for that build review (or 102's landing).
- **L4 — written in.** Decision 13 and criterion 2: a verdict row on a fixed stream, a smoke group
  whose stream holds a skip with the family's opt-in reason is red.
- **Notes for the lane** (102's Decision 1 and 15 wording; the family `env` key): 102's text is
  102's to reword; 067 adds reportlab's name to 095's `env` list (Depends on).

## Landing notes

**Built 2026-10-22, in wave 12: rebased onto `origin/wave/12` `99dcd257`** (main `c0d3a212` plus
095, reviewed). The run is the normal tier only (no `release-tier`), run id below; the build
review starts on the diff while it runs (the owner's compressed path, `decisions.md`).

### Rebases and every conflict resolved

1. **The earlier builder's tip `79d865b1` (on 102's `861d5e4b`) onto main `6411d4d5`** (wave 11):
   no conflict. Nine files changed on both sides and merged without a hunk to resolve:
   `.github/workflows/release.yml`, `CHANGELOG.md`, `README.md`, `tests/checks/test_rules.py`,
   `tests/checks/test_v1_5_rebuild_from_pins.py`, `tests/harness/packages.py`,
   `tests/harness/pins.py`, `tests/harness/scan.py`, `tests/release_shards.toml`. The rules and
   the unit files passed by node id after it (341 passed, 2 skipped; the one blocked row is the
   prior-art clones, absent in a worktree).
2. **The branch onto `origin/wave/12` `99dcd257`.** Before this, the three build commits (the
   earlier builder's two and this builder's sympy commit `aaf8a962`) were folded into one, so the
   same hunks are resolved once; the context commits before them are unchanged. Seven files had
   hunks, and every hunk keeps both sides:
   - `tests/harness/upstream.py`: 095's three suites join `COMPILED_SUITES`
     (`PACKAGE_SUITES = COMPILED_SUITES + PURE_SUITES`).
   - `tests/checks/test_v1_3_upstream_suites.py`: the `derived` fact (095) and the `deselected`
     fact (067), both kept.
   - `tests/harness/packages.py`, eight hunks: 095's `os` import, its env, clock, derived and
     smoke-cover constants and functions, and its `load()` header (`ancestors`, `_derived`,
     `_env`), merged with 067's `ini_python_files`, `load(raw, directory)`, kit-extra, items,
     `SYS_FLAGS`, the doctest constants, `smoke_findings` and `clock_findings` both, and
     `PackageRun` with both `derived` and `deselected` (passed by keyword).
     **Two keys meant the same thing on both sides, and 095's meaning is kept.**
     - **`package_inits`**: 095's generates `package_paths` from the stage folders and refuses a
       TOML that also lists them. 067's (staging the ancestors' `__init__.py`) duplicated it, so
       067's field, its load line and its staging lines are gone. Nine 067 families
       (beautifulsoup4, et-xmlfile, html5lib, joblib, mpmath, openpyxl, networkx, toolz,
       xlsxwriter) lose their `[package_paths]` tables. For each, the generated table equals the
       listed one and every ancestor is a product package (EXECUTED by a comparison script), so
       the stage is the same files.
     - **`env`**: 095's form, `[env.NAME]` with `value` and `reason`, checked by its
       `env_errors`. reportlab's `RL_TEST_OUTDIR` and narwhals' three variables are now in that
       form, each with its reason. They join 095's `ENV_ALLOWED`, and its comment names why.
       067's own env rule is dropped, and its unit row's expected message is now 095's.
   - `tests/checks/test_rules.py`: the citation allowances for `packages.toml`, `"spec 067"`
     (wave 12's side) and `"spec 095"` (067's side), are both dropped. After the merge,
     `packages.toml` names neither, since all 45 entries are suites.
   - `tests/known_gaps.toml`: 095's block and 067's block, both kept.
   - `tests/release_shards.toml` and `.github/workflows/release.yml`: wave 12's side was taken
     whole. 067's shards were then generated again from the final fuel onto those files
     (`build/067/scratch/shards.py`, base `origin/wave/12`, after 095's last shards
     `upstream-sci-smoke-b` and `upstream-sci-release-104`).
   - Merged with no hunk: `CHANGELOG.md` (095's entry and 067's both under the one unreleased
     section), `tests/upstream/packages.toml` (095's three suites and 067's 42),
     `tests/upstream/kit-extra.txt` (067's nine lines; 095 adds none) and
     `context/release-tier-claims.toml`.

### What this build did after the earlier builder's resume point

- **sympy measured whole** (EXECUTED, darwin-arm64, by node id with `--tier release`, one guest
  at a time). Round 1: 198 groups, 2 h 18 min. Round 2: 116 groups, 1 h 33 min. Round 3: 2 groups
  and the six traps.
  - The groups past 480 G or stopped at their caps were split by file (packed by test count)
    and by `[[split]]` of constructed `-k` expressions. Each `-k` term is checked against the
    names pytest matches (the test's, its module's, its folders'). A test whose name is part of
    its file's name cannot be named by `-k`, so it sits in the split's last part.
  - A host-side watcher of the guest's stream (`build/067/scratch/watch.py`, a measuring aid,
    never a check) ranked each test's share of its group's fuel, and round 2 cut the splits from
    those shares.
  - sympy now has 344 groups: the smoke group, 343 release groups (17141's node-id group
    renamed `sympy-slow-17141`) and 36 splits.
  - **A split part whose tests did not change kept its round-1 fuel even where its `-k` string
    changed** (an earlier part was cut finer, so its `and not (...)` list names the new parts).
    Its membership is the same (simulated), so its fuel is the same up to `-k` parsing.
    `sympy-r-solvers-7-9`, the rest part, is the one whose simulated list changed: three of its
    tests were removed as traps and are deselected by node id, so its run is the same.
- **Six sympy tests past the bound for one test are proposed as `[[trap]]` entries, for the
  reviewer to rule on.** Each does not end within 2.9 to 4.5 T of fuel in the guest: 3 T is the
  bound used, about the 17141 test the owner gave a shard of its own. Each is run alone to its
  50 G cap by its trap check, and is a gap with that reason, closed by the README:
  - `test_function_range1` (`@slow`; past 4.5 T);
  - `test_issue_3880` and `test_issue_15227` (`@tooslow`);
  - three of `solvers/ode/tests/test_systems.py`'s `@tooslow` tests.

  **Upstream's own runners never run `@tooslow` tests.** sympy's runner skips them as "Too slow"
  (`sympy/testing/pytest.py`), and its pytest settings deselect them (`addopts`). Decision 5
  runs them anyway, so the guest is where they are tried.
- **Twelve single sympy tests (and the doc file `bicycle_example.rst`) cost 725 G to 2.9 T
  each.** Each is a group of its own in a release shard of its own, allowed past 360 s as
  Decision 10 allows a single-test shard: 17141 (2.2 T), stats `test_uniform_P` (2.87 T),
  polys' two `@tooslow` tests that fail (2.56 T and 2.58 T), simplify's hyperexpand test
  (2.29 T), test_bicycle (1.26 T) and six others of 0.82 to 1.97 T.
- **A deviation for the reviewer to rule on: groups of 480 to 725 G with more than one test are
  kept, not split.** Each fits one 725 G release shard alone. Decision 10's text splits at
  480 G. Splitting them would cost a further round of about 10 T of measuring for no change in
  the shard count.
- **sympy's doctests now run under sympy's own runner** (a judge change; new behaviour, each
  check written first and seen failing, logs `build/067/logs/doctest-setup-red.log` and
  `doctest-runner-red.log`).
  - **The cause, found:** the stdlib's `DocTestRunner.run` resets `sys.displayhook`, which
    undoes sympy's printer. sympy's `SymPyDocTestRunner` is "modified from the doctest version
    to not reset the sys.displayhook".
  - **Three family keys, each with an allowed list in `packages.py` and a rules row:**
    `doctest_setup` (`sympy.testing.runtests:setup_pprint`, run once before the first example),
    `doctest_runner` (`SymPyDocTestRunner`) and `doctest_checker` (`SymPyOutputChecker`).
  - **The effect:** on `sympy-r-doc-1`, the failures went from 18 to 1 and the fuel from 97 G
    to 76 G; over all of sympy's doctest groups, from about 480 to 266.
  - **What remains:** the stdlib's `DocTestFinder` does not read sympy's `doctest_depends_on`
    mark (about 40 docstrings: flint, matchpy, f2py and others), so those examples run and fail
    into the class `sympy-doctest`, which says so. A follow-up could use sympy's finder too.
- **sympy's doctest blacklist** (`_get_doctest_blacklist` in `sympy/testing/runtests.py`) is
  upstream's selection: the 16 modules and 2 doc files it leaves out that the product ships are
  `docstring_not_selected` or dropped from `doctest_files`, each with upstream's reason in a
  comment in `sympy.toml`.
- **sympy's classes** (the catalog in `build/067/scratch/catalog.py`, each fact in the README):
  `sympy-doctest` (19 groups, 266 examples), `sympy-source-tree` (14),
  `sympy-tooslow-fails` (2), `sympy-solution-form` (2; its cause INFERRED: a 32-bit `hash()`
  changes sympy's set order), `no-path-variable` (1), `matplotlib-testing-not-shipped` (1,
  closed by spec 023's file). There are 26 class entries and 6 trap gaps. No sympy XFAIL is a
  failure: with `sys_flags`, `@XFAIL` is pytest's mark.
- **narwhals and pyparsing read against Decision 8's rule** (the delta review's M1).
  - narwhals: all 15 modules that import pyarrow or polars guard the import with upstream's own
    module-level `pytest.importorskip` (READ, a script over the tree), so they collect as
    counted skips. No patch and no not-selected row.
  - pyparsing: `tests/test_diagram.py` stays not selected. Every test in it draws with railroad.
  - So the patch count stays at four.

- **Two finds of the first fast tier on this base, fixed** (each was an existing check that
  failed):
  - `paths.licence_source` prefers a pinned tarball to a wheel, so it took 067's test-only
    pins as components' sources. reportlab's notice was then read from its sdist (a
    `BadZipFile`), and pypdf's notice had to carry the sample files' licence. A test source
    (`needs.TEST_SOURCES`' patterns) now never stands for a component's notice. pyyaml's,
    markupsafe's, networkx's and seaborn's sdists are their components' sources, so they are
    not affected.
  - sympy's `budget` now counts its six traps' 50 G caps, as the well-formed check sums them.
- **The first branch run's High, fixed** (run 39715865231, found by wave 12's integration
  review): `upstream-pure-smoke-a` and `-b` were red at "What the shard needs". `fetch.py`'s
  `fetch` saved each download under its URL's last part, but `fetch_trees` unpacks
  `downloads/<pinned name>`. Nine `tests` lines have a URL ending otherwise: the eight
  release-tag archives (`v0.12.1.tar.gz`, `RELEASE_3.2.9.tar.gz`, ...) and pypdf's sample
  files (`818dc013....tar.gz`). Locally `00_download.sh` had saved them under the pinned
  names, which hid it; CI's judge legs start with an empty `downloads/`.
  - **The fix:** `fetch` takes the name to save as. `fetch_trees` and `fetch_files` pass the
    pinned name. The kit's and kit-extra's files keep their URL names, which is what their
    readers use.
  - **Its check, written first and seen failing on the code before the fix**
    (`build/067/logs/fetch-name-red.log`):
    `tests/unit/test_fetch_trees.py::test_a_source_is_saved_under_its_pinned_name_not_its_urls`.
  - **Every line read** (EXECUTED, a script over `scripts/00_download.sh`): 33 of 155
    `get`/`tests` lines have a URL name other than the pinned name. The nine above; four
    `get` lines fetch.py can reach (`SheenBidi-3.0.0.tar.gz`'s URL is lowercase, and three
    `+` names whose URLs spell `%2B`), now right too; and the licence files and `.deb`
    packages, which only `00_download.sh` fetches, and it saves by the pinned name.

### The numbers (EXECUTED, darwin-arm64)

- **Normal tier:** 42 smoke groups, **853.3 G**, 12,564 passes, the largest `pyyaml-smoke`
  60.4 G; 31 of their classes are gaps. They go in two Linux shards, `upstream-pure-smoke-a` and
  `-b`.
- **Release tier: 92.84 T measured** in 420 groups of 23 families: sympy 78.53 T in 343 groups,
  the other 22 families 14.31 T. Add the six trap checks at 50 G each. Outcomes: 137,835
  passed, 707 failed and 25 errors (each a class member), 1,815 skipped, 1,098 xfailed and 5
  xpassed. They go in **110 release shards** (`upstream-pure-r-001` to `-110`), packed at
  725 G each, with each group past that in a shard of its own; the largest is 2,865 G.
- **Against the price** (the spec's "at least 65.8 T", upper estimate about 77 T): **92.8 T is
  past the upper estimate.** sympy alone is 78.5 T against its estimated 63 T. The lane's
  release acceptance before a tag grows by about 3.6 to 4.4 hours of guest time on darwin
  (INFERRED at 0.14 to 0.17 s per G), about 1.2 to 1.5 hours of wall clock at `-n 3`.
- **Smoke groups twice, restaging between** (criterion 7): pass 1 `build/067/logs/smoke-1.log`
  (42 passed, 31 xfailed), pass 2 `smoke-2.log`; 42 passed, 31 xfailed, the same outcomes and `passed_digest` in every group, and fuel equal to the unit (EXECUTED).
- **The other 41 families' groups were measured by the earlier builder** on set `d0d91cef`'s
  derived copy. Wave 11's zip (set `1556bbd5`) differs in two members. Their release groups
  were not measured again, and their smoke groups were (both passes above, on `1556bbd5`).
- **The artifact set** (criterion 9): the judging set is `1556bbd5`'s `python.wasm`, snapshot
  and zip, with `MANIFEST` rewritten the way this branch's assemble step writes it. That is 44
  lines added and 1 removed: 39 `pin` lines, four patch `recipe` lines, and the changed
  `scripts/00_download.sh` line. No rebuild was done; the lane's rebuild shows criterion 9.
- **The fast tier:** green on this base, `-n 3` (`build/067/logs/fast-tier-2.log`): 2,996 passed, 47 skipped; the ratchet lost 0, grew 0, gained 2; the blocked rows are the build host's (source trees, compile records, the prior-art clones). (Its first run found the two faults above.) After the fetch fix (`fast-tier-3.log`): 2,996
  passed, 1 failed. The failure was `test_gather.py::test_the_gathers_collection_holds_every_release_tier_check`:
  its inner collection's `litter.sealed_leftovers` walked `build/harness` while another `-n 3`
  worker removed its `unit-*` folder (`FileNotFoundError`). That is a race in the judge's own
  tooling, not this change. The check passes by node id, and it passed in `fast-tier-2.log`.
  It is named for the lane.
- **The branch run: 39720564953 on `84c5955c`** (normal tier, no `release-tier`; READ with
  `gh run view --json jobs` and the gather's log). Of 52 jobs, 46 succeeded, 5 were skipped and
  1 failed: the gather, whose **one red line is G7** ("the newest acceptance is not on the
  release's set"), a branch run's. Its tally: 853/1,871 pass, 128 gap, 7 blocked, **0 fail**.
  The set was reused from the cache under this commit's key, with `SHA256SUMS` `3339091f`, the
  local judging set's. `upstream-pure-smoke-a` and `-b` passed, in jobs of 262 s and 194 s
  (the shard steps 191 s and 95 s), within the 360 s bound. It judges 095 and 067 together.
  The first run, 39715865231 on `55d475fb`, was red only at the two smoke shards' "What the
  shard needs" (the fetch fault above, fixed); every other job was green or skipped.

### The earlier builder's notes, carried

- Its unit checks (`tests/unit/test_pure_suites.py`'s first 30) were written beside the code,
  not seen failing first. This builder's five new rows (the fetch-name row, the doctest setup, runner and checker
  rules, and their spec row) were seen failing first.
- While sympy's measuring ran, it ran three short re-measuring passes of other families beside
  it: two guest processes at once, against the one-at-a-time rule. darwin fuel is deterministic,
  so the numbers stand. This builder ran one guest at a time throughout.
- Criterion 4's driver rows (`sys_flags` set before import on a synthetic module, a sympy XFAIL
  on a fixed stream, a conftest's own hypothesis profile) have no unit check. The driver runs
  only in the guest, and the guest runs show each: no sympy XFAIL fails, every `P` line is
  derandomized with no database. **This is an open Low.**

### The self-check (`context/reviews/README.md`)

```
Before you ask for a review:
- [x] rebased onto the wave's tip today: origin/wave/12 99dcd257; every conflict named above.
- [x] CI run dispatched on the code's exact commit and read: 39720564953 on 84c5955c, its one red
      line G7 (a branch run's), 0 fail; this commit after it touches context/ only.
- [x] every number from a measured run on this base, labelled EXECUTED; sympy's on 1556bbd5,
      the other families' release groups on d0d91cef's derived copy (named above).
- [x] "For the lane": the claim block in context/release-tier-claims.toml (spec "067"; 420
      release groups, their classes, six traps; units 34), the flags below, wave kind
      build-class (pins, patches, the artifact set's MANIFEST), dry-run needs: the wave's.
- [ ] every new check seen failing first: this builder's five rows yes; the earlier builder's 30
      written beside the code, not seen failing first (said plainly above).
- [x] every gap names its closer: README.md facts, spec 023's file for matplotlib.testing.
- [x] packages.toml: the 42 are suites, none names spec 067.
- [x] CHANGELOG under the one unreleased section.
- [x] ruff check and ruff format --check clean; the fast tier: 2,996 passed,
      lost 0, grew 0 (build/067/logs/fast-tier-2.log).
```

Open for the reviewer:
1. the six traps;
2. the 480-725 G groups kept whole;
3. the round-1 fuel kept for parts whose `-k` text changed;
4. the 266 `sympy-doctest` members, and `doctest_depends_on` not read;
5. criterion 4's driver rows;
6. the price past the upper estimate.

**The flags**, the skeleton filled: `--accept "067: the pure-Python packages' own tests: 42
packages, 42 smoke groups in the normal tier (12,564 passes, 853 G), each whole suite in 420
release-tier groups (92.8 T); 117 classes, 6 traps; 39 test sources pinned and 4 test-source
patches carried, named in MANIFEST"` and the reviewed text's `--accept-judge`, plus "the doctest
setup, runner and checker keys; package_inits and env merged onto 095's meaning".

### Disposition of the build review (2026-10-22)

The review: `../reviews/067-the-pure-python-packages-own-tests-build-2026-10-22.md` (on
`review/067-build`, `0f681db0`; the lane takes the file). Its verdict: it lands at `a338f6bf`
once M1 is answered in writing. The lane's release acceptance was already running on `84c5955c`,
so every answer below is text only. This commit changes `context/`, `CHANGELOG.md` and
`README.md` and nothing else.

- **H1 — fixed in `84c5955c`**, confirmed by the reviewer: run 39720564953 has both pure smoke
  shards green.
- **M1 — descoped to a follow-up, for the lane to number and reserve, with its roadmap line**
  (`context/roadmap.md`, "Follow-ups noted").
  - **What is not built:** criterion 2's two docstring rules, each with its unit variant: (a) a
    `docstring_packages` entry the product does not ship; (b) a shipped module of an entry, or of
    the family's package, in no docstring group and not named not selected.
    `tiers.item_errors` holds "at most one group" for a module, not "at least one".
  - **Why not now:** the lane's release acceptance is running on `84c5955c`. A rule added to
    `packages.py` is a judge change, and it would move the judge hash under that acceptance.
  - **What holds meanwhile:**
    - (1) Today's data is whole. The reviewer's `doccover.py` (EXECUTED) found every shipped
      module of every family's docstring entries in a group, less its not-selected entries. The
      one exception is `more_itertools`' `__init__`, in a `docstring_modules` family, and its
      docstring has no example.
    - (2) A docstring group that runs nothing is red at run time: the empty session's
      "pytest exit code 5" is a finding of its group check (`packages.py`).
    - (3) Every later edit to a family TOML is a judge change, which a review reads.
  - **The cost of the gap:** a module dropped from a group by mistake is not caught by a static
    rule. Its group check still passes, because the other modules still run. Only the first
    error of kind (a), an unshipped entry, is caught, and only at run time in the release tier.
  - **The follow-up's closer:** the two rules in `source_rule_errors`, (a) an entry not in the
    zip's packages and (b) a shipped submodule in no group and not named not selected, each with
    a unit row seen failing first.
- **L1 — recorded, no change.** The earlier builder's 30 rows in
  `tests/unit/test_pure_suites.py` were written beside the code, not seen failing first (the
  notes above say so). The lane's `--accept-judge` reason may name it.
- **L2 — fixed** in `CHANGELOG.md` and `README.md` with the review's text. sympy's doctests run
  under sympy's own doctest runner, output checker and printer setup, with three differences
  from upstream: the setup runs once per session, the finder is the stdlib's, so module globals
  are kept, and `doctest_depends_on` is not read. "As its `bin/doctest` runs them" is gone.
  `sympy.toml`'s comment is a test file and is not changed here, because only text outside
  `tests/` may change now.
- **L3 — open Low, as the notes above say.** Criterion 4's three driver rows (`sys_flags` set
  before the import, a sympy XFAIL on a fixed stream, a conftest's own hypothesis profile) have
  no unit check. Each is held at run time: a `P` line not derandomized with no database is a
  finding (`_profile_ok`), and a sympy `@XFAIL` that were not pytest's mark would fail unlisted.
  The same follow-up may carry the rows.
- **L4 — fixed** in `README.md`'s patch row: pypdf's test-import patch has a facts sheet, not a
  drafted pull request, since pypdf asks that a person write its issues.
- **L5 — fixed** in `context/release-tier-claims.toml`: the six class patterns that meet no row
  (`packaging-r`, `xlsxwriter-r`, `beautifulsoup4-r`, `patsy-r`, `attrs-r`, `formulaic-r`) are
  dropped. 067's 86 release-tier classes are in the other 17 families.
- **N1 to N6 — noted.** For the lane:
  - N1: the largest release group is about 15 minutes of Linux guest time, against a 30-minute
    job timeout, and the release matrix is at 226 of 256.
  - N4: the price is 92.8 T, against the upper estimate of about 77 T.
  - N6: the `-n 3` race in `litter.sealed_leftovers`.

### The release acceptance's 11 red groups (2026-10-22), found and fixed

The lane's release acceptance on `855c7530` (`84c5955c` plus the bump;
`build/wave-12/release-accept.log` in the main tree) was refused. Eleven of 067's 420 release
groups failed there; the other 409 passed after the merge with 095 and the doctest keys. **They
never passed in this build either.** Each guest session ended without a trap but with no outcome,
and this builder's measuring scripts (`build/067/scratch/measure.py`, `table.py`, `fill.py`)
read a run's fuel and exit, not its group check's verdict, so each was taken as measured. Three
causes:

- **`networkx-r-doc`** ("pytest exit code 4; no P line"). An item group collects the stage's
  empty folder, so no conftest loads. The family's `args = ["--runslow"]`, an option only
  networkx's conftest registers, was still passed, and pytest refused it before collecting.
  - **The fix:** `packages.group_args` passes a family's arguments to path groups only.
  - **Its check:** `tests/unit/test_pure_suites.py::test_an_item_group_gets_no_option_of_upstreams_conftest`,
    seen failing first (`build/067/logs/item-args-red.log`).
  - **Who else it touches:** no other family has both `args` and an item group (EXECUTED: a
    script over every package family).
- **`sympy-r-utilities-5-wester-1` to `-9`** ("INTERNALERROR (pytest exit code 3)", a
  `RecursionError: Stack overflow` in pytest's `-k` compiler).
  - **The cause:** the split's first keyword named 275 tests in one `or`. pytest nests `or` and
    `and` as pairs, so it compiled to about 277 levels, and the guest's stack ran out. Every
    later part repeats it inside its `and not (...)`.
  - **The fix:** `test_wester.py`'s split is rebuilt by its tests' section prefixes
    (`test_B` ... `test_Z`), with the W section, which holds the heavy tests, last. `test_W`
    cannot be a term, because `-k` ignores case and the module is `test_wester.py`. W9, W23 and
    W25 are parts of their own. Every part's expression is now at most about 20 terms, and a
    simulation puts each of the 397 tests in exactly one part.
  - **A new rule, `packages.SPLIT_DEPTH`:** a split refuses a group whose nesting (its longest
    keyword's terms plus the parts before it) passes 150. The deepest that ran in the guest is
    108 (`sympy-r-matrices-6-3`). Its unit row,
    `test_a_split_expression_too_long_for_the_guest_is_refused`, was seen failing first
    (`build/067/logs/split-terms-red.log`). It refuses exactly the nine old wester parts, and no
    current split of any family, 095's included.
- **`sympy-r-utilities-6`** ("pytest exit code 5"). Its one file, `test_xxe.py`, holds no test:
  it is XXE test data named `test_*`. It now sits in `sympy-r-utilities-4`'s paths, so no group
  of its own collects nothing.

**Every group is judged again from its kept stream** (`build/067/scratch/verify.py`, the judge's
own `judge()` with the empty-selection rule and the split counts, no guest run). Before the fix
it named exactly these 11, and no other of the 462 groups. After the fixes, **every group of the 42 families judges clean from its stream: 461 groups, 0 with findings** (`build/067/logs/verify-2.txt`). **The groups re-run** (EXECUTED, darwin-arm64, `--tier release`, one guest at a time):
- `networkx-r-doc`: 102.6 G; 763 passed and 8 failed, and the 8 are a new `doctest-output` class (its gap in `tests/known_gaps.toml`). The earlier builder's 11.8 G was the refused session's.
- `sympy-r-utilities-4`, with `test_xxe.py`: 44.1 G; 50 passed, 1 failed (`no-path-variable`, as before), 5 xfailed, 4 skipped, 1 xpassed.
- `sympy-r-utilities-5-wester-1` to `-9`: 219.2, 295.8, 288.6, 192.9, 90.3, 503.8 (`test_W9`), 38.9 (`test_W23b`), 817.6 (`test_W23`, one test, in a shard of its own) and 293.0 G (the rest of the W section). In all: 341 passed, 177 xfailed, 2 xpassed, 3 skipped, and no failure.
- **`test_W25`** (`@tooslow`, `@XFAIL`) does not end within 3 T. **It is a seventh trap proposal**, `sympy-slow-W25`, with its gap.
- wester-9's `-k` text changed when W25 left the parts while its tests did not, and its fuel moved from 293.2 G to 293.0 G. That bears out keeping round-1 fuel where only the text changed.

**The totals now:** release tier **95.32 T** in 419 groups (sympy 80.92 T in 342, the other 22 families 14.40 T), plus seven trap checks; **113 release shards**. The normal tier is unchanged at 853.3 G. **The lesson, kept as a tool:** `verify.py` judges every kept stream the way the group check does, and a measuring pass is complete only when it names no finding.

These three commits were then rebased onto `origin/wave/12` `459e7f35` (the 0.1.0 bump and the
lane's sealed-leftovers fix after 067 at `84c5955c`), with no conflict. The fast tier there:
3,000 passed, 47 skipped, lost 0, grew 0 (`build/067/logs/fast-tier-4.log`).

### The delta-2 review's M1: `networkx-r-doc`'s eight failures (answered in writing, 2026-10-22)

`networkx-r-doc`'s new class `doctest-output` gives one reason for its eight members: "a
docstring example whose printed output differs in the guest". **For three of them that reason
is wrong.**

- **The cause:** networkx's `conftest.py` has an autouse `set_warnings` fixture that silences
  named warnings. An item group loads no conftest (above). `networkx.ini` sets
  `filterwarnings = error`. So an example whose call emits one of those warnings raises in the
  judge. That is the judge's staging, not the guest's output.
- **Staging, three** (READ: each example's call against `set_warnings`' filters, and each
  stream line ends in a traceback, not an expected output):
  - `networkx.algorithms.graph_hashing.weisfeiler_lehman_graph_hash` (the `UserWarning`
    "The hashes produced for ");
  - `networkx.algorithms.graph_hashing.weisfeiler_lehman_subgraph_hashes` (the same);
  - `networkx.algorithms.traversal.breadth_first_search.bfs_predecessors` (the
    `DeprecationWarning` "\n\nbfs_predecessors").
- **Output, five, each READ only so far as this: its example calls nothing a `set_warnings`
  filter names, so the missing filters are not its cause. Its own cause is not read:**
  - `networkx.algorithms.approximation.dominating_set.min_edge_dominating_set`: cause not read;
  - `networkx.algorithms.bipartite` (the package docstring): cause not read;
  - `networkx.algorithms.community.local.greedy_source_expansion`: cause not read (its example
    prints a set);
  - `networkx.algorithms.cycles.minimum_cycle_basis`: cause not read;
  - `networkx.utils.configs.NetworkXConfig`: cause not read.

  The stream does not keep their causes, nor any docstring item's: the driver's `R` line holds
  only the first line of the report's last 400 characters (the review's L3).
- **For 0.1.0, nothing under `tests/` changes**, since the lane's release acceptance is running
  on `eac93d0f`.
- **What holds meanwhile:**
  - The group is new in this specification, so no accepted pass is lost: its 763 passes are
    gained rows.
  - The eight are counted and named by node id in
    `tests/upstream/expected/networkx-r-doc/doctest-output.txt`, and their gap matches exactly
    those eight. A ninth failure, or one of them passing, turns the check red.
  - No pass is hidden: the 763 passes are counted and digested, and the three staging failures
    are failures, never passes.
- **The follow-up after 0.1.0** (its roadmap line in `context/roadmap.md`):
  - the class's reason text corrected, with the three staging members in a class of their own;
  - the staging cause fixed, either by staging networkx's `set_warnings` filters for its item
    group or by running that group with networkx's conftest loaded;
  - the eight measured again then, the three expected to pass;
  - the review's L3: a docstring item's `R` line keeps the doctest's cause (the failing
    example's expected and actual output, or its exception), not only the first line of the
    report's tail, so each member's cause is read.
