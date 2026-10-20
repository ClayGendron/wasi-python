# 066 — the compiled packages' own tests in the release

- **Status:** drafted 2026-10-20 on `spec/066-the-compiled-packages-own-tests` from main `1ce7381`
  (wave 05 landed); **revised 2026-10-20 against its pre-build review**
  (`../reviews/066-the-compiled-packages-own-tests-spec-2026-10-20.md`: "ready once H1, H2 and M1
  to M3 are written in"; every finding is written in, and the Disposition section says where).
  **Surveyed 2026-10-20** (`../research/2026-10-20-the-compiled-packages-own-tests-under-the-runtime.md`,
  EXECUTED); its dated delta is the section "Delta from the survey", for the confirmation round.
  Not built: building starts on that round's verdict. It builds after spec 043 (matplotlib M2, which pins contourpy)
  lands, on 043's set. It touches the release workflow (new Linux shards, Decision 12), so it is
  build-class by AGENTS.md's definition, though no artifact byte changes. The lane asks for a
  pre-build review, as it did for 063 and 065: it changes what the release judges, and its numbers
  are INFERRED until its survey (Decision 1) runs.
- **Owner:** Clay Gendron
- **Kind:** the judge and the release workflow. No line of `src/`, `scripts/`, `recipes/` or
  `downloads/SHA256SUMS` changes: every tarball it reads is already pinned and recorded in
  `MANIFEST`.
  - **New:**
    - `tests/upstream/{matplotlib,contourpy,pillow,kiwisolver,lxml,regex}.toml`: one configuration
      per package (Decision 2), in the shape of `numpy.toml` with the keys Decision 5 adds;
    - `tests/upstream/{matplotlib,contourpy,pillow,kiwisolver,lxml,regex}.ini`: each package's
      pytest configuration, transcribed (Decision 7);
    - `tests/upstream/package_drive.py`: the guest-side driver for these families (Decision 3);
    - `tests/upstream/expected/<group>/<class>.txt`: the class lists the survey finds (Decision 9);
    - entries in `tests/known_gaps.toml`, one per class and per trap;
    - the survey memo, `context/research/2026-10-2x-the-compiled-packages-own-tests-under-the-runtime.md`
      (Decision 1).
  - **Changed:**
    - `tests/harness/upstream.py`: `PACKAGES` gains the six names; a family per package, each
      with its own grant, stage, kit copy and budget (Decision 2); the new keys (Decision 5);
      the widened guard (Decision 5); the rules (Decision 14);
    - `tests/harness/pins.py`: `SOURCE_PATTERNS` gains contourpy if 043 has not added it;
    - `tests/checks/test_v1_3_upstream_suites.py`: the needs per family;
    - `tests/upstream/fetch.py`: `--shard` fetches the trees of the families the shard runs;
    - `tests/upstream/packages.toml`: the six packages become `suite` (Decision 13);
    - `tests/release_shards.toml`: three new Linux shards (Decision 12);
    - `.github/workflows/release.yml`: the Linux judge matrix gains the three shards, with their
      record outputs, and `gather` reads them (Decision 12);
    - `tests/unit/test_upstream.py`, `tests/unit/test_shards.py`, `tests/unit/test_fetch_trees.py`;
    - `README.md`, `CHANGELOG.md`, `context/progress/README.md`, one dated line in spec 063,
      `context/roadmap.md`.
- **Depends on:**
  - **043** (matplotlib M2): contourpy's pin, its tree, its `packages.toml` entry (`later`,
    closer 066) and its README facts (one thread). 066 builds on 043's set. 043 enters wave 06
    stacked with 037.
  - **063** (shards, `packages.toml`, `fetch.py --shard`, gather's G4 and G5), **065** (a stage
    and a budget per grant family, `families()` in `upstream.py`), **050** and **051** (groups,
    `passes` and its ratchet, classes by id, traps, the stream, the tie, members only), **091**
    (fuel facts), **089** (the seal of read-only stages), **052** (the serial verdict), **002**
    (checks, gaps, needs).
  - **In flight, with an order rule each:**
    - **037** (scipy) names spec 066 as scipy's closer on its branch (`kind = "later"`,
      `closes_with = "spec 066"`). 066 does not run scipy's suite; Decision 13 says what happens to
      that entry.
    - **074** (what CPython's suite asks of the product) may change the `ctypes` and `mmap`
      stand-ins. If it lands first, the survey runs on its set.
- **Research it stands on:**
  - `../research/2026-10-18-numpy-and-pandas-own-tests-in-the-guest.md` and spec 050: pytest in
    the guest, its options on WASI (`getuid`, `/dev/null`, `dup`), the stream, the tie (EXECUTED
    there).
  - `../research/2026-10-18-cpythons-own-tests-under-the-runtime.md` and spec 065: one session per
    group, a stage and a budget per grant family (EXECUTED there).
  - `../research/2026-10-18-the-release-judges-in-parallel-shards.md` and spec 063, Decision 5:
    the stage's content moves a group's fuel (numpy-lib by 3.9e-5 with only numpy's tree staged,
    EXECUTED there).
  - `../research/2026-10-17-matplotlib-on-the-current-line.md`, `../research/2026-10-16-what-matplotlib-needs.md`
    and spec 023: matplotlib in the guest, its data grant, the writable cache it needs.
  - The release dry run `39371419248` on main `c74d0f0` (READ, `gh run view`): the job times of
    every shard (Decision 12).
  - **Read while drafting (2026-10-20), no guest run:** the six pinned sdists, each verified
    against `downloads/SHA256SUMS` (`shasum -a 256`) and read with `tar` only; the test files'
    imports, configurations and conftests read as text. The counts are in
    `../research/2026-10-20-the-packages-own-tests-drafting/` (`inventory.txt`,
    `collection-risks.txt`, and the readers in `scripts/`). Every number of outcome or fuel below
    is INFERRED until the survey measures it.

## The problem

Spec 063 made a rule: every package runs its own tests in the release. AGENTS.md says it, and
`test_every_package_names_its_own_suite` checks it. Six compiled packages are in the product and
do not yet run theirs: matplotlib, Pillow, kiwisolver, lxml and regex, and contourpy once 043
lands. `tests/upstream/packages.toml` marks each `later`, closed by spec 066.

Each of them is C or C++ compiled for `wasm32-wasip1` by this project's own recipe, with carried
patches. Their golden jobs prove one plot, one parse, one match. Their own suites prove far more:
matplotlib's renders about 1,300 reference images and compares them pixel by pixel; Pillow's opens
some 700 image files; lxml's walks libxml2's and libxslt's corners. A wrong cast, a callback of the
wrong type or a 32-bit overflow in any of them would show there first.

Five C libraries are reached only through these packages (FreeType, HarfBuzz, SheenBidi, libraqm
and qhull are `via matplotlib`; libxml2 and libxslt `via lxml`). While matplotlib and lxml are
`later`, those libraries have no suite that runs.

This specification makes the six suites judge jobs and release gates, the way spec 050 did for
numpy and pandas and spec 065 for CPython:
- a ratcheted pass count and fuel per group;
- every known failure a class, listed by test id, with its reason and closer;
- every test not run named, with its reason;
- the groups in the release's Linux shards, and on the lane's darwin judge at every landing.

## Decisions

1. **The survey comes first, as research; a confirmation round always follows** (the review,
   M1). No guest ran while drafting. The test layouts, configurations and imports are READ; the
   outcomes, the classes' members and the fuel are INFERRED. Constitution §5.2 forbids building on
   an unanswered question, so:
   - **The survey is a research step, time-boxed at 90 minutes**, run before any check, TOML or
     harness line is committed. It uses a stand-in driver kept in a scratch copy (as 065's drafting
     driver was), with this specification's staging (Decision 4), keys (Decision 5), working folder
     (Decision 6) and selection (Decisions 7 and 8), and the judge's own embedder
     (`tests/harness/guest.py`) on a private copy of main's frozen set, one guest session per
     group, at most three at once, never while `build/lane.lock` exists.
   - **It records** each group's outcomes by node id, its fuel, every trap and every collection
     error, and sorts the failures into the platform's classes by their one-line reasons.
   - **It is written up** as the memo
     `context/research/2026-10-20-the-compiled-packages-own-tests-under-the-runtime.md`, labelled
     EXECUTED, with the stand-in driver and the raw streams beside it.
   - **Its delta always goes to a confirmation round.** With the memo, the builder writes a dated
     delta to Decisions 8, 9, 11 and 12 (what is not selected, the classes and their members, the
     groups, caps and budgets, the shards). A fresh reviewer reads it as a context-only delta
     review. Building starts on that verdict, never before.
   - contourpy is measured on 043's set when 043 has landed; main's set does not hold it. Its
     numbers come to the confirmation round as a second, smaller delta, or with the build review
     if 043 lands after the confirmation.

2. **One family per package: its own grant, stage, kit copy and budget.** Spec 065 made a family
   the unit of staging: one grant, one stage, one fuel budget. Each of the six packages is its own
   family, with the grant `/upstream-<package>`.
   - **Why not the `/upstream` stage numpy and pandas share.** The stage's content moves fuel:
     numpy-lib with only numpy's tree staged moved by 3.9e-5, 500 times the residual (063,
     Decision 5, EXECUTED there). Adding matplotlib's 2,377 test files to `/upstream` would move
     every numpy and pandas row. A family of its own moves none (criterion 6).
   - **Why not one family for all six.** The same reason, one level down: a later package spec
     (scipy's, say) would move matplotlib's accepted fuel. One family per package means a package
     moves only its own rows, and a shard fetches only the trees it runs.
   - **The cost.** One stage per family per judge run (host copies; the kit unpacked once per
     family) and one pytest start per group (the kit is source, and the driver keeps
     `sys.dont_write_bytecode`; the survey measures it). Ten groups pay it ten times.
   - **The budget.** Each family's fuel caps sum to at most its budget, as 065's did. The six
     budgets together are at most 3×10¹² (Decision 11).

3. **A second pytest driver, so numpy's and pandas' sessions run the same bytes.** The guest
   executes `tests/upstream/drive.py`; editing it would change numpy's and pandas' fuel, however
   slightly. So these families get `tests/upstream/package_drive.py`, derived from `drive.py`:
   - the same stream (`C`, `S`, `R`, `X`, `P`, `M`, `E` lines), so `parse_stream` and the verdict
     are reused unchanged;
   - the grant read from its own path (`/upstream-<package>/judge/package_drive.py`), not a
     constant;
   - the kit **appended** to `sys.path`, after the product's zip, not inserted first: every module
     the product carries comes from the product (the principle of 050's Decision 4, applied to the
     kit too). The kit's `packaging` wheel is the product's own pin (both SHA-256 `d7193f7c…`), so
     pytest runs on the product's copy;
   - the keys of Decision 5 and 6 applied before pytest starts;
   - the same hypothesis profile as `drive.py`'s, registered and loaded first;
   - a skipped collection report (a module-level `importorskip` or `pytestmark` skip) written as
     `R skipped <collector node id> -- <reason>`, so a file that skips itself whole is a counted
     outcome in these families (the review, L1); `drive.py` does not, and is not changed;
   - the doctest collector of Decision 7, for lxml.

   **A family chooses its driver** with `driver = "package"` in its TOML. numpy's and pandas'
   TOMLs carry no such key; for them `upstream.py` reads today's keys with today's meaning and
   judges with today's guard, byte for byte (the review, M2; criterion 2).

4. **Where the tests come from: the pinned sdists, members only, tied to the artifact.** Each
   family's stage holds the files of its package's own pinned tarball, after its carried patches,
   exactly as 050's Decision 3 stages numpy's: tarball members and files a recorded patch
   creates, nothing else; the tie (`tie_errors`) fails the group, not blocks it, when the tarball
   or a patch is not the one `MANIFEST` records. The stage mirrors the sdist's own paths under
   `/upstream-<package>/tree/`, so node ids are the sdist's paths (`lib/matplotlib/tests/test_axes.py::…`).

   | package | tarball (pinned) | staged | kind | size (READ) |
   |---|---|---|---|---|
   | matplotlib | `matplotlib-3.11.2.tar.gz` | `lib/matplotlib/tests/` (94 test modules, `conftest.py`, `baseline_images/` with 1,219 PNGs and their PDF and SVG twins, `data/`); `lib/matplotlib/testing/` (support, Decision 5); `lib/mpl_toolkits/{axes_grid1,axisartist,mplot3d}/tests/` (10 modules, 104 PNGs) | inside the packages | 2,522 files, 32.7 MB |
   | contourpy | `contourpy-1.4.0.tar.gz` (043) | `tests/` (19 modules, `conftest.py`, helpers, 52 baseline images) | top-level package `tests` | 76 files, 12.3 MB |
   | Pillow | `pillow-13.0.0.tar.gz` | `Tests/` (166 modules with `oss-fuzz/test_fuzzers.py`, `conftest.py`, `helper.py`, `images/`, `fonts/`, `icc/`) | top-level package `Tests` | 1,279 files, 68.83 MB |
   | kiwisolver | `kiwisolver-1.5.1.tar.gz` | `py/tests/` (6 modules) | a folder | 7 files |
   | lxml | `lxml-6.1.3.tar.gz` | `src/lxml/tests/` (27 modules and their data), `src/lxml/html/tests/` (11 modules, 6 doctest files, two data folders), `doc/*.txt` (the 11 doctest files the modules' `test_suite()` names) | inside the packages | 182 files, 1.2 MB |
   | regex | `regex-2026.9.29.tar.gz` | `regex/tests/test_regex.py` | inside the package | 2 files |

   - **Every package's tests are in its sdist** (READ, `tar -tzf`). None needs another source.
   - **Not the product's zip.** Step 70 leaves out every `tests/` folder and `matplotlib/testing/`
     (`--drop matplotlib/testing`), and must keep doing so.
   - **Not kiwisolver's C++ tests.** `tests/*.cpp` (7 files) need a C++ test runner built for
     the guest; they are not Python and not staged (Scope).
   - **A new CI input.** Each tarball becomes an input of the judge runners whose shard runs its
     groups, as CPython's did in 065 (fetched by `fetch.py --shard`, verified against
     `downloads/SHA256SUMS`, unpacked with the `data` filter, patched, never run outside the
     guest). matplotlib's is 32.7 MB, Pillow's 47.1 MB. The next release's threat-model review
     sees them (§5.6).

5. **How the guest finds the tests: three new keys with new names, and a path-based guard** (the
   review, M2). numpy's and pandas' keys keep their names and meaning: `path_packages` is a list of
   product packages whose test folder is `<package path>/tests` under `/upstream/tests/`, and
   `support` a list of tarball *files* (pandas' `conftest.py` and two `__init__.py`), each checked
   as a member. The `driver = "package"` families use these instead, and the rules refuse the old
   keys in them:
   - **`package_paths`**, a map from a product package to its staged folder:
     `{"matplotlib" = "lib/matplotlib", "mpl_toolkits.mplot3d" = "lib/mpl_toolkits/mplot3d", …}`,
     `{"lxml" = "src/lxml", "lxml.html" = "src/lxml/html"}`, `{"regex" = "regex"}`. The driver
     appends `/upstream-<package>/tree/<folder>` to each package's `__path__`, so
     `matplotlib.tests` and `lxml.tests.common_imports` import from the grant, and nothing of the
     product is replaced (050, Decision 4).
   - **`extra_sys_path`**: staged folders appended to `sys.path`, for tests that are a top-level
     package or import a sibling by name: the tree root for contourpy (`tests`) and Pillow
     (`Tests`), and `Tests/oss-fuzz` for Pillow's fuzz tests (they import their sibling
     `fuzzers`). kiwisolver needs none: its six modules import only `kiwisolver`, `pytest` and the
     stdlib (the review, L8). Appended, never inserted: the stage holds no module of the product, so
     nothing can shadow one.
   - **`support_packages`**: product subpackages the zip leaves out and the tests need, as staged
     *folders*, found through `package_paths`. One today: `lib/matplotlib/testing`
     (`matplotlib.testing`: its decorators, `compare`, `conftest`, `jpl_units` and `widgets`).
     matplotlib's `tests/conftest.py` imports it first. No module of matplotlib or mpl_toolkits
     outside `tests/` and `testing/` imports it (the review's grep, READ), so no product code path
     can pass against the stage's copy.
   - **What the `M` lines report** in `package_drive.py`: (a) every module whose `__file__` is
     under `/upstream-<package>/tree/`; (b) every module whose top-level name is in the list the
     judge writes into the group's JSON (the zip's top-level names and the builtin module names)
     and whose `__file__` is neither in the zip nor absent (a builtin has none). The kit's modules
     appear only under (b), for example a `packaging` loaded from the kit instead of the zip; the
     kit's pytest and hypothesis are never reported.
   - **The guard, path-based.** For a `driver = "package"` group, a finding is any (a) module whose
     file is under neither a staged test folder (a group path, or a folder of `extra_sys_path`) nor
     a `support_packages` folder, and every (b) module. That admits Pillow's `Tests.*` and
     matplotlib's `matplotlib.testing.*` by where they live, not by their names. numpy's and
     pandas' groups keep today's name-based guard and its `pandas.conftest` exception unchanged.

6. **The working folder and the environment, per package.**
   - **`cwd`**: the folder the driver changes into. matplotlib and contourpy write their
     comparison results to `./result_images/` (`decorators._image_directories`, READ), so theirs
     is `/tmp/work`, in the guest's writable root. Pillow's tests open `Tests/images/…` by a path
     relative to the working folder (READ, `helper.py`), and some write beside what they read.
     So Pillow's `cwd` is also `/tmp/work`, and before the session the judge copies the stage's
     `Tests/` folder there, into the guest's writable root (host I/O only; the review, M3). The
     test modules still import from the read-only grant; only their relative data paths meet the
     copy. No failure is then the judge's own making, and there is no `read-only-tree` class.
   - **The environment** is the judge's (`TMPDIR=/tmp`, `HOME=/tmp`). matplotlib's cache goes to
     `$HOME/.config/matplotlib`, writable; its data is granted as the runner grants it
     (`mpl_data=True`, as 023 grants it to numpy's and pandas' groups).
   - **The freetype question is settled by the pins.** matplotlib's baseline images are made with
     FreeType 2.14.3 (`LOCAL_FREETYPE_VERSION`, and the `freetype2.wrap` matplotlib bundles, READ),
     HarfBuzz 14.1.0 and libraqm 0.10.5: the same three versions this project pins. Its
     `_init_tests` logs a warning because the build type is not `local`; that is a log line, not a
     failure. On a 32-bit `sys.maxsize`, `image_comparison` adds 0.06 to every tolerance
     (`decorators.py`, READ): wasm32 gets that allowance from matplotlib itself.

7. **Upstream's own configuration, transcribed; upstream's own conftests used as they are.**
   - The driver passes 050's options (Decision 5 there: `-p no:faulthandler`, `--capture=sys`,
     `-o log_file=/tmp/pytest.log`, `--basetemp=/tmp/pytest`, `-p no:cacheprovider`,
     `--import-mode=importlib`, `--strict-markers --strict-config`, `-q --tb=no --no-header -rN`),
     with `--rootdir=/upstream-<package>/tree -c /upstream-<package>/judge/<package>.ini`.
   - **matplotlib**: its `pyproject.toml` `[tool.pytest.ini_options]` holds only `minversion`,
     `testpaths` and `--import-mode=importlib`; its real configuration is
     `matplotlib.testing.conftest.pytest_configure` (markers, `filterwarnings = error`, the Agg
     backend), which its `tests/conftest.py` imports. Used as is. The `.ini` holds only
     `minversion`.
   - **contourpy**: its `conftest.py` registers `slow`, `text`, `image` and `threads` and skips
     `slow` and `text` unless asked (`--runslow`, `--runtext`): upstream's own default selection,
     kept. The `.ini` registers `flaky` (pytest-rerunfailures' marker, which one test carries).
   - **Pillow**: `[tool.pytest]` holds `addopts = -ra --color=auto` and `testpaths`; nothing to
     transcribe but the testpath. Its `conftest.py` used as is.
   - **lxml**: no pytest configuration. lxml's own runner (`test.py`) runs, per module, exactly
     what that module's `test_suite()` builds. pytest by itself would collect more and less (the
     review, H1): it collects every `unittest.TestCase` subclass in a module's namespace, including
     the abstract bases `test_suite()` never adds (in `test_elementtree.py`, `_ETreeTestCaseBase`
     with 274 `test_` methods, `_ElementSlicingTest`, `_XMLPullParserTest` and `_C14NTest`, each
     with `etree = None`), and builds `FeedTestCase('runTest')` where lxml builds one case per data
     file; and it collects none of lxml's doctests. So the lxml group's selection is made equal to
     `test_suite()`'s, in both directions:
     - **Classes.** The judge reads each staged module's `test_suite()` with `ast` and writes, per
       module, the `TestCase` classes it adds into the group's JSON (`keep_classes`). The driver
       deselects every collected unittest item whose class is not listed, and writes one
       `D <node id>` line per deselected item. The verdict checks both ways: every listed class
       has at least one collected item (no class lxml runs is lost), and the deselected set is
       exactly the collected classes not listed (nothing else is dropped). A class `test_suite()`
       builds from data (`FeedTestCase`) is not run: lxml's own runner builds none while
       `lxml.html.clean` is absent, and it is (`lxml_html_clean` is not shipped, README), so its
       module is not selected (Decision 8).
     - **Doctest files.** The driver's doctest collector adds the 17 doctest files `test_suite()`
       names, each with lxml's own flags: `ELLIPSIS` for the 11 `doc/*.txt` files lxml runs through
       `make_doctest`, none for the 6 `html/tests/*.txt` files it runs through `DocFileSuite`
       plainly. lxml runs `validation.txt` from five modules; the group runs it once, from one.
     - **Docstring doctests.** The same collector adds, as doctest items, the docstrings of the nine
       modules `test_suite()` passes to `DocTestSuite`: three staged as source (`selftest`,
       `selftest2`, `test_xpathevaluator`) and six product modules found by import (`lxml.etree`,
       `lxml.objectify`, `lxml.html`, `lxml.html.diff`, `lxml.cssselect`, `lxml.isoschematron`).
       A docstring survives in bytecode and in a compiled module's `__doc__`, which is how lxml's
       own runner reads them. `lxml.cssselect`'s raise `ImportError` without `cssselect` and
       `lxml.isoschematron` is the product's stand-in: those two are collection reports, sorted
       as Decision 8 says.
     - **The check of it**: the rules read every `test_suite()` and fail if it adds anything not
       accounted for here (a class, a doctest file, a docstring suite); a unit check feeds a staged
       module with an unlisted `TestCase` and expects a finding (criterion 1).
   - **regex**, **kiwisolver**: no configuration; `unittest` and plain pytest modules.

8. **What is not selected, each with its reason and closer.** A file is not selected only when it
   cannot load or every one of its tests needs what the product does not have; a file that skips
   itself is selected, and its skips are counted (Decision 3's `R skipped` lines); a single test
   that fails is a class member, never a reason to drop its file (the review, L1). READ from each
   file's imports (`collection-risks.txt`); the survey confirms each line, and the confirmation
   round sees every change.

   | package | files | reason | closes with |
   |---|---|---|---|
   | matplotlib | `test_backend_webagg.py` | it imports `backend_webagg_core`, which step 70 drops: it cannot load | `README.md` |
   | matplotlib | `test_backends_interactive.py`, `test_determinism.py` | every test starts a subprocess | `README.md` |
   | contourpy | `tests/test_codebase.py` | every test runs tools over the repository through `subprocess` | `README.md` |
   | contourpy | `tests/test_bokeh_renderer.py` | Bokeh and Selenium are not in the product (043's Scope) | `README.md` |
   | Pillow | `Tests/test_main.py` | every case runs `python -m PIL` in a subprocess | `README.md` |
   | lxml | `src/lxml/tests/test_threading.py` | every test starts threads | `README.md` |
   | lxml | `src/lxml/tests/test_isoschematron.py`, and `lxml.isoschematron`'s docstring doctests | `lxml.isoschematron` is the product's stand-in (spec 046, Decision 8) | `context/specifications/046-lxml.md` |
   | lxml | `src/lxml/html/tests/test_feedparser_data.py` | its `test_suite()` builds cases only when `lxml.html.clean` imports; `lxml_html_clean` is not shipped, so lxml's own runner runs none | `README.md` |

   Selected although they may skip whole (each confirmed by the survey): matplotlib's
   `test_backend_{nbagg,inline,gtk3,qt,macosx,tk,cairo}.py`, `test_sphinxext.py`, `test_doc.py`;
   Pillow's `Tests/oss-fuzz/test_fuzzers.py` (the review, H2: it imports only `fuzzers`,
   `packaging`, `pytest`, `PIL` and `Tests.helper`, and sends every file of `Tests/images` through
   Pillow's decoders and every file of `Tests/fonts` through FreeType; its `atheris` modules are
   not `test_*.py` and are never collected) and `Tests/test_imagegrab.py` (it skips off Windows and
   macOS, and the guest's `sys.platform` is `wasi`); lxml's `test_http_io.py` (its `needs_http`
   tests skip when libxml2 has no HTTP, as the product's has none) and `test_css.py` (skips without
   `cssselect`).

9. **Known failures are classes, by test id, each one gap.** As 050's Decision 10: a failed or
   errored test goes to the first class of its group whose outcome and `match` fit; each class is
   listed by id under `tests/upstream/expected/<group>/` and is one gap with its closer. A failure
   no class admits is a finding: the group is red. The classes below are the platform's documented
   facts, INFERRED to appear from the files' imports and the README; the survey lists each one's
   members, drops a class with none, and adds a class only with a documented reason (Decision 1).

   | class | match (searched in the one-line reason) | reason | closes with | likely in |
   |---|---|---|---|---|
   | `no-processes` | `wasi does not support processes` | no processes (README); as numpy's and pandas' class | `README.md` | matplotlib (`subprocess_run_helper` in 15 files), Pillow (EPS through Ghostscript, `test_file_palm`, `test_image_access`'s embedding test) |
   | `no-threads` | `can't start new thread` | no threads (README) | `README.md` | matplotlib (`test_figure`, `test_font_manager`), contourpy (`threads`) |
   | `no-dup` | `\[Errno 58\] Not supported` | no `dup` (README) | `README.md` | Pillow (`fileno`-based paths) |
   | `no-mmap` | `mmap is unavailable` | the `mmap` stand-in raises (README) | `README.md` | Pillow |
   | `shallow-recursion` | `Stack overflow \(used` | recursion through Python stops at 40 to 250 levels (README, "Deep recursion") | `README.md` | lxml (deep trees), matplotlib (`test_pickle`'s deep figures) |
   | `zip-no-source` | `could not get source code` | the product's modules are bytecode in a zip (README) | `README.md` | matplotlib (`test_api`'s source introspection) |
   | `zip-code-names` | as pandas' | code objects carry relative file names, so a warning's reported file differs | `README.md` | matplotlib (`_api.warn_external` tests) |
   | `wasm32-memory` | `MemoryError` | the declared maximum of `python.wasm`'s linear memory, which the survey records (the review, N2); a test that allocates more | `README.md` | Pillow (decompression-bomb and huge-image tests) |
   | `pillow-zlib-only` | `decoder \w+ not available\|encoder \w+ not available` | Pillow is built with zlib only (spec 023); a test that opens a codec without its own `skip_unless_feature` guard | `context/specifications/023-matplotlib-first-milestone.md` | Pillow |
   | `wasi-iconv` | `unknown encoding\|Unsupported encoding` | libxml2 decodes only what wasi-libc's `iconv` does (spec 046's README facts) | `README.md` | lxml |
   | `no-en-us-locale` | as the survey finds | `setlocale(LC_ALL, "en_US.UTF-8")` fails in the guest; matplotlib warns that date tests may fail | `README.md` | matplotlib (`test_dates`) |

   A class never spans packages: each is defined per group, as numpy's `no-mmap` and pandas'
   `no-mmap` are two classes.

10. **Traps.** As 050's Decision 9: a test that ends the guest in a trap is deselected from its
    group, run alone by `test_upstream_trap[<id>]`, and is a gap until fixed. The survey finds them
    by bisection. matplotlib's deep `Path` recursion and lxml's C14N or RelaxNG of very deep trees
    are the README's known traps (INFERRED: the suites' own trees are shallow, so none is
    expected). A trap found is a product defect: it gets its own specification or a gap whose
    closer names one, never a class.

11. **The groups, their caps, and the budget.** Each group is one guest session and one check,
    `test_upstream_suite[<group>]`. A group's cap is 1.5 times its survey fuel, rounded up to two
    significant figures (050's rule), so a runaway ends out of fuel, which is red. **The bound:** no
    group's survey fuel passes 480 G (pandas-groupby's, the largest group the release runs); a
    group past it is split by file, in the sdist's order, before the caps are set. A single file
    past it (likely only `test_axes.py`) stays one group and is named in the memo.
    **mpl-toolkits** is surveyed first: its three test folders each hold an `__init__.py` and a
    `conftest.py`, and with the toolkits' own `__init__.py` unstaged, `importlib` mode may load all
    three as `tests.conftest` (the review, L4, INFERRED). If it does, the fallback is decided now:
    one group per toolkit folder.

    | group | paths (under the tree) | `def test` (READ) | image comparisons (READ) | fuel (INFERRED) | provisional cap |
    |---|---|---|---|---|---|
    | `matplotlib-axes` | `lib/matplotlib/tests/test_axes.py` | 641 | 259 decorators, 204 PNGs | 350 to 500 G | 7.5×10¹¹ |
    | `matplotlib-mathtext` | `test_mathtext.py`, `test_text.py`, `test_textpath.py`, `test_font_manager.py`, `test_ft2font.py`, `test_afm.py`, `test_type1font.py`, `test_dviread.py`, `test_usetex.py`, `test_texmanager.py` | 200 | 681 + 22 PNGs | 250 to 450 G | 6.8×10¹¹ |
    | `matplotlib-render` | the image-heavy files: `test_image`, `test_collections`, `test_constrainedlayout`, `test_figure`, `test_patches`, `test_polar`, `test_legend`, `test_colorbar`, `test_contour`, `test_lines`, `test_backend_{pdf,ps,svg,pgf}`, `test_simplification`, `test_quiver`, `test_tightlayout`, `test_streamplot`, `test_bbox_tight`, `test_patheffects`, `test_arrow_patches`, `test_triangulation` | 965 | about 330 | 300 to 450 G | 6.8×10¹¹ |
    | `matplotlib-rest` | every other selected file of `lib/matplotlib/tests/` | 1,112 | about 60 | 150 to 300 G | 4.5×10¹¹ |
    | `mpl-toolkits` | `lib/mpl_toolkits/{axes_grid1,axisartist,mplot3d}/tests` | 238 | 104 PNGs | 100 to 200 G | 3.0×10¹¹ |
    | `contourpy` | `tests` | 196, 230 `parametrize` | 56 `image` | 50 to 150 G | 2.3×10¹¹ |
    | `pillow` | `Tests` | 2,408 | (reads 700 images) | 80 to 200 G | 3.0×10¹¹ |
    | `lxml` | `src/lxml/tests`, `src/lxml/html/tests`, the 17 doctest files | 1,506 and 17 doctest files | none | 30 to 80 G | 1.2×10¹¹ |
    | `regex` | `regex/tests` | 102 (`unittest`) | none | 5 to 30 G | 5.0×10¹⁰ |
    | `kiwisolver` | `py/tests` | 36 | none | under 2 G | 5.0×10⁹ |

    - **How the INFERRED fuel was made.** The accepted metrics on main: the plot golden job is
      8.87 G on the snapshot for a whole process (matplotlib's import, its font cache, one figure,
      its saves), `test_savefig_rejects_a_negative_dpi` 8.01 G; so a figure rendered and saved
      inside a running session is INFERRED at 0.3 to 1.5 G, and a test with no figure at 10 to
      100 M (numpy's groups average 16 to 27 M per pass, CPython's 17 to 48 M). mathtext's 681
      reference images are small, but each parses its expression with pyparsing in pure Python.
    - **The budget.** The six families' caps sum to at most 3×10¹², and each family's budget is
      written in `upstream.py` beside 065's; the confirmation delta states each family's budget,
      so "caps within budget" is not empty (the review, L6). The provisional caps above sum to 3.6×10¹²; that is
      why they are provisional. If the survey's caps still pass 3×10¹², Decision 1's delta goes
      to the lane before anything else is built.
    - **The plain binary is not run** (050, Decision 1).

12. **The release: three new Linux shards; the lane runs everything at every landing.**
    - **What the last dry run shows** (`39371419248`, READ). The Linux upstream shards took 161 to
      225 s of job time each (`upstream-numpy-a` 161 s, `upstream-pandas-small` 175 s,
      `upstream-numpy-b` 190 s, `upstream-groupby` 209 s, `upstream-frame` 225 s, setup and
      fetching included). The judge stage's longest leg was `own-guest` on macOS, 457 s. 16 Linux
      and Windows judge and verify jobs started at 05:00:39 while the x86_64 rebuild still ran, and
      five macOS jobs from 05:00:43: 22 jobs at once. The binding limit was macOS's five concurrent
      jobs: `own-rest` on macOS waited until 05:01:41 for a macOS slot (the review, L5). Rate: 0.16
      to 0.31 s per G of fuel past about 60 s of setup.
    - **Why new shards.** The existing Linux shards already hold 450 to 650 G each. Adding about
      2 T to them would put each past the macOS leg. New shards add matrix legs to
      `release.yml`, which makes this build-class; that is accepted (Kind).
    - **The plan** (assigned by the survey's fuel; the shard names are fixed):

      | shard | groups | fuel (INFERRED) | job time (INFERRED) |
      |---|---|---|---|
      | `upstream-plot-a` | `matplotlib-axes`, `matplotlib-mathtext` | 600 to 950 G | 160 to 355 s |
      | `upstream-plot-b` | `matplotlib-render`, `matplotlib-rest` | 450 to 750 G | 135 to 295 s |
      | `upstream-plot-c` | `mpl-toolkits`, `contourpy`, `pillow`, `lxml`, `regex`, `kiwisolver` | 270 to 660 G | 105 to 265 s |

      **The bound:** each new shard within 360 s of job time in the branch dry run (criterion 12).
      Past it, the builder moves a group to the shard with room, by a reviewed judge change; if no
      shard has room, a fourth (`upstream-plot-d`) is added the same way. A system is never
      dropped from a shard to get a pass.
    - **The job count.** The three Linux shards add Linux jobs only; macOS's five slots stay the
      binding limit, so they are INFERRED to start at once with the others and to end before the
      macOS leg (355 s < 457 s). The dry run's length is INFERRED unchanged; the landing notes
      record the branch run's gather start against `39371419248`'s 05:08:22, as a benchmark.
    - **Linux only in the release.** No group of 066 probes the host's file system the way
      `cpython-fs` does: their files go to `/tmp` in the guest's root, and their data is read from
      a read-only grant. macOS runs every group at every landing on the lane, where fuel is
      ratcheted (063, Decision 8), and G5 compares each group's `passes` and `passed_digest`
      between the Linux record and the lane's. A host difference is a host entry (065, Decision
      21), never a class on one system.
    - **The branch's dry run, before landing**, as 065's: the builder pushes the branch and
      dispatches `release.yml` on it, and deletes the branch from GitHub after landing.

13. **`packages.toml`: six suites, and no package left closing with 066.**
    - matplotlib, contourpy, Pillow, kiwisolver, lxml and regex become `kind = "suite"`.
    - FreeType, HarfBuzz, SheenBidi, libraqm and qhull stay `via matplotlib`; libxml2 and libxslt
      `via lxml`. Each now names a suite that runs. pybind11 and cppy stay `build-only`.
    - **scipy, scikit-learn and statsmodels are not 066's** (scipy's suite is larger than numpy's,
      and 037's own Scope leaves its first gaps to 038). **095 is reserved** for "scipy's and
      scikit-learn's own tests in the release" (statsmodels' too if 045 adds an entry): the lane
      adds it to `context/roadmap.md`'s `Reserved:` paragraph at this confirmation, since
      `shards.package_errors` accepts only a number reserved there (the review, L7). Every entry
      that names 066 points at 095 instead (READ on the branches at drafting):
      - `scipy` on 037's, 038's and 044's branches (`closes_with = "spec 066"`);
      - `scikit-learn` on 044's branch (`044-scikit-learn.md:722` names 066).
      The lane tells those builders; any of them that lands before 066 is built carries 095, and
      066's builder re-points whatever still names 066 when it builds.
    - **The check of it**: after 066, no entry of `packages.toml` names `spec 066` (criterion 10).

14. **The rules check, widened.** `test_upstream_files_are_well_formed` also checks, with no
    guest:
    - each new family's grant is `/upstream-<package>`, unique, and not `/upstream` or `/cpython`;
    - a `driver = "package"` family uses `package_paths`, `extra_sys_path` and
      `support_packages`, never `path_packages` or `support`; `package_paths` maps product
      packages (each in the zip or builtin) to tarball folders; `extra_sys_path` and
      `support_packages` name tarball folders; `cwd` is `/tmp/work`; numpy's and pandas' TOMLs
      pass today's rules unchanged;
    - every group path, `not_selected` file and support file is a tarball member or folder;
    - each family's caps sum to at most its budget, and the six budgets to at most 3×10¹²;
    - every lxml `test_suite()` adds only what Decision 7 accounts for: `keep_classes`, the doctest
      files, the docstring suites, and the not-selected module of Decision 8;
    - no group is in two shards on one system, and each is in exactly one Linux shard (063's rule,
      unchanged).

15. **The needs, the scoreboard, the README and the CHANGELOG.**
    - **Needs**: a group needs the artifact set, the kit and its family's tree; without the tree it
      is blocked, named (`upstream tree matplotlib`), as numpy's is. A tie mismatch fails.
    - **The scoreboard** counts the new groups under v1.3, as numpy's are.
    - **README**: the testing section names the six suites, their groups and what is not run, in
      one paragraph, and the platform facts the classes cite stay as they are.
    - **CHANGELOG**: one entry: "The release runs matplotlib's, contourpy's, Pillow's,
      kiwisolver's, lxml's and regex's own tests (spec 066)."

## Intent

The judge runs the own test suites of the six compiled packages inside the guest. It counts every
pass, and shows every known failure and every test it does not run as a gap or a named line, with
what will close it. The release runs them too, on Linux, in three new shards; the lane runs them on
darwin at every landing. The judge turns red when a pass is lost, a test traps the guest, an
unknown failure appears, a test runs against a copy of the product's code, or the tests are not the
artifact's own.

## Design

```
tests/upstream/matplotlib.toml       package, driver "package", grant /upstream-matplotlib,
                                       package_paths (map), support_packages
                                       ["lib/matplotlib/testing"], cwd /tmp/work,
                                       [groups.matplotlib-{axes,mathtext,render,rest}],
                                       [groups.mpl-toolkits], [[not_selected]], [[expected]]
tests/upstream/contourpy.toml        grant /upstream-contourpy, extra_sys_path ["."], cwd /tmp/work
tests/upstream/pillow.toml           grant /upstream-pillow, extra_sys_path [".", "Tests/oss-fuzz"],
                                       cwd /tmp/work with a copy of Tests/, one group
tests/upstream/kiwisolver.toml       grant /upstream-kiwisolver, one group
tests/upstream/lxml.toml             grant /upstream-lxml, package_paths {lxml, lxml.html}, one group;
                                       its JSON gains keep_classes, the 17 doctest files with their
                                       flags, and the nine docstring modules
tests/upstream/regex.toml            grant /upstream-regex, package_paths {regex}, one group
tests/upstream/<package>.ini         each package's pytest configuration (Decision 7)
tests/upstream/package_drive.py      guest side: the grant from its path, the kit appended, the keys,
                                       the hypothesis profile, the stream (as drive.py's)
tests/upstream/expected/<group>/<class>.txt
tests/harness/upstream.py            PACKAGES += six; Config: driver, package_paths, extra_sys_path,
                                       support_packages, cwd (read only for driver "package");
                                       a family per package; budgets per grant; the path-based
                                       guard and the D lines for driver "package" groups; numpy's
                                       and pandas' reading and guard unchanged; rule_errors widened
tests/checks/test_v1_3_upstream_suites.py
                                     _need per family; the new groups, classes and traps
tests/upstream/fetch.py              --shard: the kit, and each family's tarball for the groups the
                                       shard holds
tests/upstream/packages.toml         six suites; no closer names 066
tests/release_shards.toml            upstream-plot-a, -b, -c (systems: linux)
.github/workflows/release.yml        judge-linux's matrix and outputs; gather's inputs
tests/known_gaps.toml                one entry per class and trap
tests/unit/test_upstream.py, test_shards.py, test_fetch_trees.py
README.md, CHANGELOG.md, context/progress/README.md, spec 063 (one dated line), context/roadmap.md
```

**A group's run, in order:**
1. Stage `/upstream-<package>` once per judge run, after the tie, from the patched tree: the
   staged folders, the support folders, the kit (unpacked), the driver, the `.ini`, each group's
   JSON (with the zip's and the builtins' top-level names, and lxml's `keep_classes`). Seal it
   read-only (089). For Pillow, copy `Tests/` into the guest's root at `/tmp/work/Tests`.
2. `guest.run(snapshot, ["-u", "/upstream-<package>/judge/package_drive.py", "<package>",
   "<group>"], workdir, stdlib, env=ENV, fuel=<cap>, preopens=[("/upstream-<package>", <stage>,
   False)], mpl_data=True)`.
3. In the guest: the kit appended to `sys.path`; `package_paths`, `extra_sys_path`; `os.chdir(cwd)`; the
   hypothesis profile; pytest with 050's options, the `.ini`, the group's paths, `--ignore`s and
   marker.
4. Read the stream; sort failures into classes; check the guard; record `fuel` and `passes` and
   the facts `counts`, `passed_digest`, `left_out`.
5. Cache the result for the group's class checks; assert no finding.

**Spec 063, one dated line** in its Status: "2026-10-…: matplotlib, contourpy, Pillow,
kiwisolver, lxml and regex are `suite`s since spec 066, in three new Linux shards."

## Scope

**In:** the above.

**Out, each with its reason:**
- **scipy, scikit-learn and statsmodels.** Their own specifications (Decision 13).
- **Fixing what the suites find.** Each failure is a class with its closer, or a finding that
  returns to the lane (Decision 1). A product fix is its own specification.
- **kiwisolver's C++ tests.** They need a C++ test binary built for the guest: a build output.
- **matplotlib's PDF, EPS and SVG comparisons.** matplotlib skips them itself without Ghostscript
  and Inkscape, which the guest cannot run. They are counted skips.
- **contourpy's `slow` and `text` tests.** contourpy's own default leaves them out (Decision 7).
- **The plain binary, macOS and Windows release shards.** Decision 11 and 12.
- **Upstream facts sheets.** None is drafted here; the survey may find one worth sending, and the
  memo says so.
- **Wall-clock.** No check reads a clock (§4.9); every time above is a benchmark estimate, from a
  CI run's job times.

## Acceptance criteria

Each is counted; none times anything. Each check is written first and seen failing against today's
code or a stand-in; the builder records each failing assertion in the landing notes. A stand-in is
applied in a scratch copy, never committed.

1. **The rules.** `test_upstream_files_are_well_formed` passes with Decision 14's rules on the new
   files. `tests/unit/test_upstream.py` variants each fail with their own line: a family whose
   grant is `/upstream`; two families with one grant; a `package_paths` folder not in the tarball;
   a `support_packages` folder not in the tarball; a `driver = "package"` family with
   `path_packages` or `support`; a `cwd` other than `/tmp/work`; a family over its budget; the six
   budgets over 3×10¹²; an lxml `test_suite()` that adds a suite Decision 7 does not account for; a
   staged lxml module with a `TestCase` that `test_suite()` does not add and the JSON does not
   deselect.
2. **The stream and the verdict, on fixed streams** (no guest). `package_drive.py`'s stream parses
   with `parse_stream` to the same outcomes as `drive.py`'s for the same lines. A recorded numpy
   stream and a recorded pandas stream are judged exactly as today (same findings, same counts).
   The path-based guard: an (a) `M` line for `lib/matplotlib/colors.py` is a finding; one for
   `lib/matplotlib/testing/compare.py` is not; one for `lib/matplotlib/tests/test_axes.py` is not;
   one for `Tests/helper.py` is not; a (b) line for `packaging` from the kit is a finding. lxml: a
   `D` line for an unlisted class's item is admitted; a listed class with no collected item is a
   finding; a `D` line for a listed class is a finding. An `R skipped <collector>` line counts as
   one skipped outcome.
3. **The survey, then the baseline.** The memo exists, labelled EXECUTED, written before any check,
   TOML or harness line (Decision 1), with each group's outcomes by id, fuel, traps and collection
   errors; its delta has a confirmation verdict. Each group check, run before its TOML lists and
   gaps exist, fails with its findings.
4. **With the TOML, the lists and the gaps complete**, the run on that set gives: each group check
   passing; each class check and trap check failing as its gap says; the numbers (passes, fuel,
   classes, members) in the landing notes, equal to the memo's or explained.
5. **Fuel repeats.** The builder runs each new group twice (a one-off, as 050's criterion 7),
   **restaging between the runs** (the review, N1: `os.listdir` and `rglob` orders follow the
   host's file system): equal outcomes and `passed_digest`, and on darwin equal fuel within
   `sameness.py`'s tolerance.
6. **numpy, pandas and CPython do not move.** The full judge's ratchet against the base: every
   numpy, pandas and CPython row lost 0, grew 0; their stages' file lists are byte-for-byte the
   base's (a unit check hashes the `/upstream` and `/cpython` stage manifests).
7. **The shards.** 063's `test_release_shards_cover_the_judge` and the workflow scan pass with the
   three new shards; each new group is in exactly one Linux shard; the scan fails, in
   `tests/unit/test_scan.py`, when a new shard is in the plan but not in `release.yml`'s matrix,
   or the reverse.
8. **The fetch.** `tests/unit/test_fetch_trees.py`, a fake `urlopen` and synthetic tarballs: a
   shard with `matplotlib-axes` fetches the kit and matplotlib's tarball only; one with `lxml` and
   `regex` fetches both and nothing else; a hash mismatch deletes the `.part` file and exits 1
   naming it.
9. **The tie and the stage.** Unit checks: a `MANIFEST` whose matplotlib `pin` line differs from
   the tarball's fails the group (not blocked), naming both; a carried patch whose hash differs
   from `MANIFEST`'s fails it; a file in the tree that is not a member and no patch creates is
   left out and listed in `left_out`.
10. **`packages.toml`.** `test_every_package_names_its_own_suite` passes with the six as `suite`;
    a unit check fails if any entry names `spec 066` as its closer.
11. **The full judge.** `uv run ruff check`, `uv run ruff format --check` and `uv run pytest -n 6`
    green on the builder's worktree against 043's set, apart from the gaps this specification
    adds, each named.
12. **The branch's dry run, before landing** (Decision 12; not a check). Every job passes on all
    three systems, every red line a growth line or G7. The three new shards' job times are
    recorded in the landing notes, each within 360 s, or the move Decision 12 prescribes is made
    and recorded.
13. **The lane's dry run after landing**, on main's exact commit, as 063's criterion 13.

## The owner's choices

None is needed to build. Three defaults are the owner's to move, each decided above with its reason:
- **The release's job count** (Decision 12): three more Linux jobs, INFERRED not to lengthen the
  dry run, since macOS's five slots bind. The owner may prefer fewer, longer shards.
- **The lane's cost** (the review, L6; a benchmark estimate, INFERRED): today's accepted darwin
  upstream fuel is 2.84 T over 16 groups; 066 adds 1.3 to 2.6 T, 45 to 90% more upstream guest
  work at every landing, and more again on the serial judge every fifth landing. The survey's
  measured total replaces the range in the confirmation delta.
- **What runs per release when the survey's fuel passes the budget** (Decisions 1 and 11): the
  builder brings the numbers to the lane before building on; the choice between a fourth shard, a
  larger budget, and running a part on the lane only is then the owner's.

Everything else is decided above.

## For the lane

- **Next, before building:** the survey and its memo (Decision 1), then the confirmation round on
  their delta. The lane adds 095 to the roadmap's `Reserved:` paragraph at that round.
- **Wave kind: build-class** (the release workflow; no artifact byte changes, no `scripts/`,
  `recipes/` or `downloads/` line). It may ride in a wave as one of the two other build-class
  changes, after 043 has landed. **Dry-run needs:** the branch dry run (criterion 12), then the
  wave's.
- **Order.** After 043 (and 037 if it rides with 043). Before any later package specification
  whose suite stages into a family 066 creates.
- **The claim list skeleton** (the builder fills each value from its final run; the progress
  README's step 3a):
  - **Gained rows:** `test_upstream_suite[<group>]` for the ten groups of Decision 11 (or the
    groups the survey's split gives), each with new metrics `fuel` and `passes`, and facts
    `counts`, `passed_digest`, `left_out`; `test_upstream_class[<group>-<class>]` for each class
    with members, each a gap; `test_upstream_trap[<id>]` for each trap, each a gap.
  - **Gaps added:** one per class with members and per trap, each naming its closer; the count
    and ids from the landing notes.
  - **Moved rows:** none. numpy's, pandas' and CPython's rows: lost 0, grew 0 (criterion 6).
  - **The judge hash changes**: `judge changed` names the files of the accept-judge text.
  - **packages.toml:** six `later` become `suite`; scipy's closer re-pointed if 037 landed.
- **The flags** (skeleton; each reason begins with "066:"):

  ```
  --accept "066: the compiled packages' own tests in the release: matplotlib, contourpy, Pillow, kiwisolver, lxml and regex, <n> groups, <p> passes, <c> classes, <t> traps"
  --accept-judge "066: tests/upstream/{matplotlib,contourpy,pillow,kiwisolver,lxml,regex}.toml and .ini; package_drive.py; a family per package in upstream.py (grant, stage, kit copy, budget), driver "package" with package_paths, extra_sys_path, support_packages and cwd, the path-based guard, lxml's selection equal to test_suite()'s, numpy's and pandas' reading unchanged; fetch.py --shard per family; packages.toml (six suites); three Linux shards in release_shards.toml and release.yml; the unit checks"
  ```

  No `--accept-growth` and no `--accept-fewer-passes`: new rows are not growth, and no accepted
  pass moves. If the lane's run has a growth line, it is the base's: name it in the base's words.

## Delta from the survey (2026-10-20, for the confirmation round)

The survey (`../research/2026-10-20-the-compiled-packages-own-tests-under-the-runtime.md`,
EXECUTED on main's set, wave 05, darwin-arm64) replaces this specification's INFERRED numbers.
What it changes, by decision; the confirmation round rules on each before anything is built:

- **Two product defects, each needing its own fix first** (Decision 10's rule: a trap is a
  defect, never a class).
  - **kiwisolver's `*_clear` functions return `void`** where CPython calls `tp_clear` as
    `int (*)(PyObject *)`: any garbage collection that clears a cycle holding a kiwisolver object
    ends the guest in `indirect call type mismatch` (memo, finding 1). The kiwisolver group cannot
    run until a carried patch (with its upstream pull request) gives the four functions `int` and
    `return 0`. Proposed: a small build-class specification that lands before 066, or 066 waits on
    it; in either case the `kiwisolver` group is built after that fix and is one trap entry until
    then. matplotlib's constrained layout reaches the same functions.
  - **`import lxml.html.diff` raises `TypeError`** in the product (memo, finding 2): lxml's
    pure-Python fallback lacks `cython.final`. Proposed: a carried patch with its upstream pull
    request, in the same small specification; until then the lxml group carries one class,
    `lxml-html-diff`, of three members, closed by that specification.
- **Decision 11 (groups, caps, budget).** Measured fuel, darwin: `matplotlib-axes` 691.5 G,
  `matplotlib-mathtext` 296.2 G, `matplotlib-render` 998.1 G, `matplotlib-rest` 956.9 G,
  `mpl-axes_grid1` 72.1 G, `mpl-axisartist` 34.7 G, `mpl-mplot3d` 303.3 G, `pillow` 430.7 G,
  `lxml` 110.8 G, `regex` 16.0 G; contourpy unmeasured (043). Total 3,910 G, matplotlib 3,353 G.
  - `matplotlib-render` and `matplotlib-rest` are split by file, in the sdist's order, into groups
    under 480 G each (two each); `matplotlib-axes` stays one file and one group (Decision 11's
    rule). `mpl-toolkits` becomes `mpl-axes_grid1`, `mpl-axisartist` and `mpl-mplot3d` (the L4
    fallback, confirmed: one session over the three failed on two `tests.conftest`).
  - **The budget of 3×10¹² is broken**: caps at 1.5 times the survey's fuel come to about
    5.9×10¹². This is the owner's choice of Decision 1 and "The owner's choices": a budget of
    6×10¹² for 066's families (and the lane's cost of about +3.9 T of darwin fuel per landing,
    more than today's whole upstream 2.84 T), or a part of matplotlib's suite run on the lane only,
    or fewer files. This specification proposes the first, with the shards below, and asks the
    round to confirm or choose.
- **Decision 12 (shards).** About 3.9 T on Linux at 0.16 to 0.31 s per G is 10 to 20 minutes of
  guest time: six Linux shards of at most about 700 G each, not three, to keep each under the
  360 s bound (INFERRED). The job count becomes 27 at once; macOS's five slots still bind.
- **Decision 6 (Pillow's working folder).** The writable copy of `Tests/` in the guest's root was
  voided twice by spec 089's guard (`/.DS_Store` written by the host after the copy). The run with
  the read-only tree as the working folder completed, and at most one failure in it can come from
  the folder (`test_save_without_changing_readonly`, unread). Proposed: Pillow's `cwd` is the
  read-only tree root after all, and that one test, if the build confirms its cause, is a
  deselection closed by a judge follow-up the lane reserves (never `README.md`, as the review's
  M3 asked); the round may instead ask for the copy in a separate writable grant that the guard
  watches as a grant.
- **Decision 7 (lxml).** Confirmed: `keep_classes` deselects 360 items and keeps every listed
  class. Changed: the 17 doctest files and the docstring doctests run as stdlib
  `DocTestRunner` items, with lxml's own flags, not through pytest's doctest plugin, which breaks
  `lxml.usedoctest` (9 files failed under it); and the lxml group's `cwd` holds a copy of
  `samples/` (two files), which `selftest2` reads by a relative path.
  `test_elementsoup.py` cannot import under importlib mode (`from ...tests.common_imports`) and is
  not selected, with that reason and a judge follow-up as its closer.
- **Decision 8 (not selected).** Added: `regex/tests/test_regex.py::test_main` (regex's own
  `unittest.main()` entry point, collected by its name; its tests run as collected);
  `lxml.cssselect`'s docstring doctests and `test_css.py` stay as Decision 8 has them (skips);
  `test_elementsoup.py` (above). matplotlib's `test_typing.py::test_cm_stub_matches_runtime_colormaps`
  needs `cm.pyi`, a product file, staged: `support_packages` does not cover it, so it is a member
  of a class `stubs-not-in-zip` closed by `README.md` (the zip carries no `.pyi`).
- **Decision 9 (classes, with members, EXECUTED).** `no-processes` (matplotlib 15), `no-threads`
  (matplotlib 2), `pillow-zlib-only` (matplotlib 8, Pillow 51), `no-mmap` (Pillow 17, with the four
  `test_arrow` mapped-file cases), `wasm32-memory` (Pillow 2, `Errno 48`; `python.wasm` declares
  no maximum memory, so wasm32's 4 GiB bounds it), and new: `builtin-no-file` (Pillow 2:
  `PIL._imaging` is a builtin module without `__file__`), `zip-code-names` (matplotlib 1),
  `no-lapack-errors` (matplotlib 2), `no-ffmpeg-messages` (matplotlib 2), `open-empty-path`
  (Pillow 1), `include-dir-in-zip` (lxml 1), and the lxml doc files' 3 (`validation.txt`:
  isoschematron's stand-in; `api.txt`, `parsing.txt`: read in the build). `no-dup`,
  `shallow-recursion` and `zip-no-source` had no member and are dropped. 93 matplotlib failures
  are spec 043's (`contourpy`, `_qhull`) and vanish on 043's set, where the build re-surveys
  matplotlib and contourpy.
- **contourpy** is surveyed on 043's set before its group is built.

## Disposition of the pre-build review (2026-10-20)

The review (`../reviews/066-the-compiled-packages-own-tests-spec-2026-10-20.md`) said "ready once
H1, H2 and M1 to M3 are written in"; the Lows came with fix text. Each is written in:

- **H1 (lxml under pytest is not lxml's own): fixed, option (i).** Decision 7: the judge writes each
  module's `test_suite()` classes into the JSON (`keep_classes`); the driver deselects every other
  collected class and writes a `D` line for each; the verdict checks both ways. The 17 doctest
  files run with lxml's own per-file flags, and the nine docstring suites are collected too (none
  is left out for being in the zip). `test_feedparser_data.py` is not selected, with its true
  reason (Decision 8). Criteria 1 and 2 gain the variants.
- **H2 (Pillow's oss-fuzz reason is false): fixed.** `Tests/oss-fuzz/test_fuzzers.py` is selected,
  with `Tests/oss-fuzz` in Pillow's `extra_sys_path` for its sibling `fuzzers` (Decisions 5 and 8).
  If the survey finds a real blocker, the confirmation delta states it as measured.
- **M1 (the survey and an unconditional confirmation): fixed.** Decision 1: the survey is a
  research step, time-boxed at 90 minutes, with a stand-in driver from a scratch copy, before any
  check, TOML or harness line; its EXECUTED memo and a dated delta to Decisions 8, 9, 11 and 12
  always go to a confirmation round; building starts on its verdict. Criterion 3 says so.
- **M2 (shared keys and guard): fixed.** Decisions 3 and 5: `driver = "package"` selects the new
  reading; numpy and pandas keep `path_packages` (a list), `support` (files) and today's name-based
  guard, byte for byte, proved by judging their recorded streams (criterion 2). The new keys have
  new names (`package_paths`, `extra_sys_path`, `support_packages`); the `M` scope is specified
  (the tree, plus product top-level names loaded from outside the zip, from a list in the JSON);
  the new guard is path-based.
- **M3 (`read-only-tree` closed by the README): fixed, option (i).** Decision 6: Pillow's `cwd` is
  `/tmp/work`, holding a host copy of `Tests/` in the guest's writable root; the class is gone.
- **L1: fixed.** Self-skipping files stay selected (Decision 8's last paragraph); the cairo and
  webagg reasons are corrected; module-level skips are counted (`R skipped`, Decision 3).
- **L2: fixed.** No closer names this specification: the remaining not-selected rows close with
  `README.md` (platform or profile facts it states) or spec 046.
- **L3: fixed.** Decision 7 states the three staged docstring modules and the six product ones, and
  collects all nine; the flags follow lxml per file; `validation.txt` runs once, said so.
- **L4: written in.** Decision 11: mpl-toolkits is surveyed first; the fallback is one group per
  toolkit folder.
- **L5: fixed.** Decision 12 restates the job count: macOS's five slots bound the base run; the
  landing notes record the gather start as a benchmark.
- **L6: fixed.** The owner's choices state the lane's cost; the confirmation delta states each
  family's budget (Decision 11).
- **L7: fixed.** Decision 13: 095 is reserved for scipy's and scikit-learn's own tests (statsmodels'
  if 045 adds an entry); the lane adds it to the roadmap's `Reserved:` paragraph at this
  confirmation; every entry naming 066 (scipy on 037, 038 and 044; scikit-learn on 044) points at
  095.
- **L8: fixed.** kiwisolver has no `extra_sys_path`; Pillow's `Tests/` is 1,279 files, 68.83 MB.
- **N1: written in.** Criterion 5 restages between its two runs.
- **N2: written in.** `wasm32-memory` cites the binary's declared maximum memory, which the survey
  records.

## Landing notes

Not built yet.
