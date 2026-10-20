# 067 — the pure-Python packages' own tests in the release

- **Status:** drafted 2026-10-20 from main `1ce7381`, committed on `spec/066-the-compiled-packages-own-tests`
  beside 066's draft; it gets its own branch, `spec/067-the-pure-python-packages-own-tests`, when
  the lane confirms it. Not reviewed. It is stacked on 066 (constitution §4.14): it reuses 066's
  family per package, its driver and its rules. It pins 34 test sources in `downloads/SHA256SUMS`
  and `scripts/00_download.sh`, so it is build-class, and the artifact's `MANIFEST` gains their
  pin lines: it changes the artifact set, so constitution §5.6 requires a pre-build review.
- **Owner:** Clay Gendron
- **Kind:** the build recipe's pins (34 lines in `downloads/SHA256SUMS`, 34 `tests` lines in
  `scripts/00_download.sh`), the judge, and the release workflow. No line of `src/` or `recipes/`
  changes; `python.wasm`, the snapshot and the stdlib zip do not change; `MANIFEST` gains 34
  `pin` lines and its `recipe` line for `scripts/00_download.sh` changes (Decision 3).
  - **New:**
    - `tests/upstream/<package>.toml` and `.ini` for each of the 37 packages of Decision 2;
    - `tests/upstream/kit-extra.txt`: three pure wheels some suites import (Decision 6);
    - `tests/upstream/expected/<group>/<class>.txt` and their gaps in `tests/known_gaps.toml`;
    - the survey memo, `context/research/2026-10-2x-the-pure-python-packages-own-tests-under-the-runtime.md`
      (Decision 1).
  - **Changed:**
    - `downloads/SHA256SUMS`, `scripts/00_download.sh` (a `tests` function, fetched with
      `--tests` and by `fetch.py`, never by a plain build);
    - `tests/harness/pins.py` (`SOURCE_PATTERNS` for each test source), `tests/harness/upstream.py`
      (`PACKAGES`, the source tie of Decision 4, the writable stage of Decision 7, `kit_extra`, the
      budgets), `tests/upstream/fetch.py` (`tests` lines; the wheel beside each test source);
    - `tests/upstream/packages.toml` (37 entries become `suite`), `tests/release_shards.toml` and
      `.github/workflows/release.yml` (three Linux shards, Decision 11);
    - `tests/unit/test_upstream.py`, `test_shards.py`, `test_fetch_trees.py`, `test_pins.py`;
    - `README.md`, `CHANGELOG.md`, `context/progress/README.md`, one dated line in spec 063,
      `context/roadmap.md`.
- **Depends on:**
  - **066** (built and reviewed): `package_drive.py`, one family per package with its own grant
    `/upstream-<package>`, `path_packages` as a map, `sys_path`, `support`, `cwd`, the guard over
    the product's modules, the per-family budgets and rules. 067 builds on 066's reviewed tip and
    rebases onto main when 066 lands, with a delta review.
  - **039** (tier A, landed) and **041** (networkx from its sdist, landed): what the zip carries,
    from which pin. **023** and **033**: the four plot wheels and `METADATA`.
  - **063**, **065**, **050**, **051**, **089**, **091**, **052**, **002**, as 066 lists them.
  - **In flight:** **042** (seaborn and reportlab, not built) adds packages after 067 is drafted;
    each brings its own suite (AGENTS.md's rule), not 067. **037** (scipy) changes what some
    networkx and patsy tests skip (`importorskip("scipy")`): whichever lands second accepts the
    passes that move, with its reason.
- **Research it stands on:**
  - The mechanism and the platform: `../research/2026-10-18-numpy-and-pandas-own-tests-in-the-guest.md`
    (pytest in the guest), `../research/2026-10-18-cpythons-own-tests-under-the-runtime.md`
    (families), `../research/2026-10-18-the-release-judges-in-parallel-shards.md` (the stage moves
    fuel), `../research/2026-10-17-what-else-the-default-profile-carries.md` (tier A, each
    candidate imported and run in the guest, EXECUTED there), and the README's platform facts.
  - The release dry run `39371419248` (READ, `gh run view`): job times.
  - **Read and compared while drafting (2026-10-20), no guest run**, in
    `../research/2026-10-20-the-packages-own-tests-drafting/`:
    - `sdists.txt`: the 34 PyPI sdists, each downloaded into an empty scratch folder and its
      SHA-256 recomputed equal to PyPI's; read with `tar` only;
    - `tag-archives.txt`: the release-tag archives of the eight packages whose sdists carry no
      tests (READ, `tar -tzf`: cloudpickle, cycler, et-xmlfile, openpyxl, threadpoolctl, tomli-w,
      xlrd, xlsxwriter);
    - `source-equality.txt` (EXECUTED on the drafting host, archives read as data): every `.py`
      file each pinned wheel installs is byte-identical to the same path in its sdist or tag
      archive; the only files absent are two scripts under a wheel's `.data/scripts/`, which the
      zip does not carry;
    - `inventory.txt`, `collection-risks.txt`, `kit-extra.txt`: test counts, imports, conftests,
      configurations, and the readers that made them.

    Every number of outcome or fuel below is INFERRED until the survey measures it.

## The problem

Spec 063's rule is that every package runs its own tests in the release. 37 pure-Python
distributions in the product do not yet: the seven matplotlib and pandas need (fonttools,
pyparsing, cycler, packaging, python-dateutil, six, tzdata) and tier A's thirty (spec 039).
`tests/upstream/packages.toml` marks each `later`, closed by spec 067.

Most of them are pinned as wheels, and a wheel carries no tests. Three are pinned as sdists that
do (pyyaml, markupsafe, networkx). So 067 must first decide where each package's tests come from,
and how they are tied to the bytes the product ships.

They matter because the product runs these packages in a place their authors never tested: in a
zip, as bytecode only, with no threads, no processes, no `dup`, shallow recursion and a 32-bit
address space. Spec 039 ran one job per package. Their own suites hold some 35,000 tests.

This specification makes the 37 suites judge jobs and release gates, as 066 does for the compiled
packages: a ratcheted pass count and fuel per group, every known failure a class by id, every test
not run named, the groups in Linux release shards and on the lane's darwin judge at every landing.

## Decisions

1. **The survey comes first; this draft's numbers are INFERRED until it runs.** As 066's
   Decision 1, word for word in its rule: the builder's first commit after the pins is the survey
   memo, EXECUTED on the frozen set, with each group's outcomes by id, fuel, traps and collection
   errors. Three findings return to the lane as a dated delta before the rest is built: a group past
   Decision 10's bound; a failure that fits no class of Decision 9 and has no fix here; a budget
   passed (Decision 10, sympy's above all).

2. **The 37 packages, and where each one's tests come from.** Each is its own family, with the
   grant `/upstream-<package>` (066, Decision 2). READ from the archives:

   | package | test source (pinned by 067 unless marked) | staged | found by |
   |---|---|---|---|
   | fonttools 4.67.0 | sdist | `Tests/` (185 modules `*_test.py`, data; 2,092 files, 15.6 MB) | `sys_path` tree root |
   | pyparsing 3.3.3 | sdist | `tests/`, `examples/` (support: tests import `examples.*`) | `sys_path` tree root |
   | cycler 0.12.1 | **tag archive** `v0.12.1` (GitHub) | `test_cycler.py` | `sys_path` tree root |
   | packaging 26.3 | sdist | `tests/` (31 modules, ELF fixtures) | `sys_path` tree root |
   | python-dateutil 2.9.0.post0 | sdist | `tests/` (13 modules, `conftest.py`) | `sys_path` tree root |
   | six 1.17.0 | sdist | `test_six.py` | `sys_path` tree root |
   | tzdata 2026.5 | sdist | `tests/`, `VERSION` (support: `test_version` reads it) | `sys_path` tree root |
   | openpyxl 3.1.5 | **tag archive** `3.1.5` (Heptapod) | `openpyxl/**/tests/`, `openpyxl/tests/data/` (161 modules) | `path_packages` per subpackage |
   | et-xmlfile 2.0.0 | **tag archive** `2.0.0` (Heptapod) | `et_xmlfile/tests/` | `path_packages` |
   | xlsxwriter 3.2.9 | **tag archive** `RELEASE_3.2.9` (GitHub) | `xlsxwriter/test/` (1,235 modules, 998 of them comparisons against Excel's own files; 24.9 MB archive) | `path_packages`; a writable stage (Decision 7) |
   | xlrd 2.0.2 | **tag archive** `2.0.2` (GitHub) | `tests/`, `tests/samples/` | `sys_path` tree root |
   | pypdf 6.21.1 | sdist | `tests/`, `resources/` (support: 85 PDFs the tests open) | `sys_path` tree root |
   | beautifulsoup4 4.15.0 | sdist | `bs4/tests/` | `path_packages` |
   | soupsieve 3.0.3 | sdist | `tests/` (84 modules) | `sys_path` tree root |
   | html5lib 1.1 | sdist | `html5lib/tests/` (and `testdata/`, 92 files) | `path_packages` |
   | webencodings 0.6.1 | sdist | `tests/` | `sys_path` tree root |
   | defusedxml 0.7.1 | sdist | `tests.py`, `xmltestdata/` | `sys_path` tree root |
   | xmltodict 1.0.4 | sdist | `tests/` | `sys_path` tree root |
   | pyyaml 6.0.3 | sdist, **already pinned** (039) | `tests/legacy_tests/` (25 modules, 575 data files) | `sys_path` `tests/legacy_tests` |
   | tomli-w 1.2.0 | **tag archive** `1.2.0` (GitHub) | `tests/` (264 data files) | `sys_path` tree root |
   | jinja2 3.1.6 | sdist | `tests/` (23 modules, `res/`) | `sys_path` tree root |
   | markupsafe 3.0.4 | sdist, **already pinned** (039) | `tests/` | `sys_path` tree root |
   | tabulate 0.10.0 | sdist | `test/` (tests import `common` by name) | `sys_path` `test` |
   | charset-normalizer 3.5.2 | sdist | `tests/`, `data/` (support: 20 sample files) | `sys_path` tree root; `cwd` tree root |
   | networkx 3.7 | sdist, **already pinned** (041) | `networkx/**/tests/`, `networkx/conftest.py` (268 modules) | `path_packages` per subpackage |
   | patsy 1.0.3 | sdist | `patsy/test_*.py` (6 modules) | `path_packages` |
   | sympy 1.14.0 | sdist | `sympy/**/tests/`, `sympy/conftest.py` (612 modules) | `path_packages` per subpackage |
   | mpmath 1.3.0 | sdist | `mpmath/tests/` (31 modules) | `path_packages` |
   | attrs 26.1.0 | sdist | `tests/` (26 modules, `conftest.py`) | `sys_path` tree root |
   | more-itertools 11.2.1 | sdist | `tests/` | `sys_path` tree root |
   | toolz 1.2.0 | sdist | `toolz/tests/`, `toolz/sandbox/tests/` | `path_packages` |
   | tqdm 4.70.1 | sdist | `tests/` (`tests_*.py`, `conftest.py`) | `sys_path` tree root |
   | typing-extensions 4.16.0 | sdist | `src/test_typing_extensions.py`, `src/_typed_dict_test_helper.py` | `sys_path` `src` (holding only those two) |
   | joblib 1.6.0 | sdist | `joblib/test/`, `conftest.py` (support: the root conftest) | `path_packages` |
   | cloudpickle 3.1.2 | **tag archive** `v3.1.2` (GitHub) | `tests/` (with `cloudpickle_testpkg/`, `mock_local_folder/`, `old_pickles/`) | `sys_path` tree root and `tests/cloudpickle_testpkg` |
   | threadpoolctl 3.7.0 | **tag archive** `3.7.0` (GitHub) | `tests/`, `conftest.py` | `sys_path` tree root |
   | narwhals 2.27.1 | sdist | `tests/` (296 modules, a `tests` package) | `sys_path` tree root |

   - **The rule for a top-level `tests` folder.** The stage holds only the files the table names,
     never the package's own modules, so appending the tree root (or `src/` for typing-extensions,
     whose stage holds only the test and its helper) can shadow nothing. The guard of 066's Decision
     5 proves it at every run.
   - **Upstream settings that would put the package's source on `sys.path` are dropped**:
     narwhals' `pythonpath = ["src"]`, attrs' and others' `--import-mode` (the driver's is
     `importlib` already). The tests must import the product.

3. **The pins: 26 sdists and 8 tag archives, in `downloads/SHA256SUMS`, recorded in `MANIFEST`.**
   - **Each pin** is one line in `downloads/SHA256SUMS` (SHA-256 and name) and one line
     `tests <url> <name>` in `scripts/00_download.sh`, a new function beside `research`: a plain
     build does not fetch it; `scripts/00_download.sh --tests` and `fetch.py --shard` do. The hashes
     and URLs are in the evidence folder's `sdists.txt` and `tag-archives.txt`; the builder fetches
     each again and recomputes.
   - **Names.** An sdist keeps its PyPI name (`fonttools-4.67.0.tar.gz`). A tag archive is named
     `<distribution>-<version>-tag.tar.gz` (`openpyxl-3.1.5-tag.tar.gz`), so no pattern in
     `SOURCE_PATTERNS` can match a wheel or an sdist by mistake.
   - **Recorded in `MANIFEST`.** `assemble_artifacts.py` writes a `pin` line for every
     `SHA256SUMS` line but the research input. 067 does not add an exception: the artifact's record
     then names every source its tests came from, and the tie (`tie_errors`, MANIFEST's pin against
     the tarball's hash) works for a test source exactly as for numpy's tarball. The cost: the set's
     `MANIFEST` changes (34 `pin` lines and the `recipe` line of `scripts/00_download.sh`), so its
     `SHA256SUMS` line changes, and nothing else (criterion 9).
   - **Why tag archives for eight.** Their PyPI sdists hold the package and no tests (READ). Each
     project's tag at the released version holds the tests, and its package files are the wheel's,
     byte for byte (EXECUTED, `source-equality.txt`).
   - **The risk of a tag archive** (INFERRED). GitHub has served archive bytes unchanged since it
     rolled back its 2023 compression change; GitLab, behind Heptapod, regenerates archives and has
     changed their bytes across upgrades. A changed archive fails `fetch.py`'s hash check, red and
     named, never silently. The re-pin is one line, and Decision 4's tie proves the new archive's
     package is still the wheel's.

4. **The tie: the tests test the bytes that ship.**
   - **For a test source**: its `MANIFEST` pin equals its hash (as 050's tie), and its version is
     the version of the product's distribution (the wheel's or sdist's pin name).
   - **For a package built from a wheel** (34 of 37): at staging, the judge compares every `.py`
     file the pinned wheel installs (outside `.data/`) with the same path in the test source (as
     is, under `src/`, or under `lib/`). Any difference fails the family's groups, naming the file.
     `fetch.py --shard` fetches the wheel beside the test source, verified by its `SHA256SUMS` line.
   - **For pyyaml, markupsafe and networkx**, built from their sdists with carried patches, the zip's
     code is the sdist's: 050's tie (tarball and patches against `MANIFEST`) covers them.

5. **The driver and the guest: 066's, unchanged.** `package_drive.py`: the kit appended after the
   product's zip (so the product's `packaging`, a pin identical to the kit's, is the one tested),
   `path_packages`, `sys_path`, `support`, `cwd`, the stream, the guard, and the hypothesis profile
   `judge` (derandomized, no database). 050's pytest options, then each package's `.ini`: its
   `[tool.pytest.ini_options]` (or `setup.cfg`, `tox.ini`, `pytest.ini`) transcribed, markers and
   `filterwarnings` kept, `xfail_strict` kept, `addopts` that shape the report or write files
   dropped, upstream's own selection kept:
   - packaging: `-m "not property"`; sympy: `-m "not slow and not tooslow"`; networkx,
     contourpy-style `--runslow` options left at their defaults (slow skipped);
   - pypdf: `-m "not enable_socket and not samples"` (network, and the `sample-files` repository,
     neither in the sdist); its `--disable-socket` (pytest-socket) dropped: the guest has no
     sockets;
   - narwhals: `--constructors=pandas,pandas[nullable]` (its default list names pyarrow, polars,
     duckdb, sqlframe and ibis, none in the product);
   - html5lib: `--noconftest` (Decision 8);
   - tqdm: its `--asyncio-mode` and `timeout` (pytest-asyncio, pytest-timeout) dropped with the
     files that need them (Decision 8);
   - fonttools, joblib, mpmath, sympy: their `--doctest-modules` and `--doctest-glob` dropped
     (Decision 8).

6. **Three wheels added to the kit, in a file of their own.** Some suites import a test-only
   module at module level. `tests/upstream/kit-extra.txt`, in `kit.txt`'s format (SHA-256 and a
   `files.pythonhosted.org` URL of a pure wheel), pinned by the judge as 050's Decision 2 pins
   the kit; each family names the extras it stages (`kit_extra = [...]`). `kit.txt` is unchanged, so
   numpy's and pandas' stage is unchanged.

   | wheel | for | why |
   |---|---|---|
   | freezegun 1.5.5 | python-dateutil | `tests/test_rrule.py` (562 tests) and `tests/test_utils.py` import it at module level |
   | pretend 1.0.9 | packaging | four modules import it at module level |
   | tomli 2.5.0 | tomli-w | every test module round-trips through it, unguarded |

   freezegun requires python-dateutil, which the product carries (the product's is used).
   Optional modules a test guards (wcwidth for tabulate, pympler for attrs, trio-free parts of
   jinja2) are not added: their tests skip, as on a host without them.

7. **A writable stage for one package.** XlsxWriter's comparison tests write
   `xlsxwriter/test/comparison/_test_<name>.xlsx` beside the Excel files they compare against,
   by a path relative to the working folder, and delete it after (READ,
   `excel_comparison_test.py`). So its family's stage is granted as a fresh writable copy per
   session, `cwd` the tree root: the judge copies the sealed stage, grants the copy, and after the
   session compares every staged file's hash with the stage's. A staged file changed or removed is
   a finding; a new file is listed in the record's facts and removed with the copy. The copy holds
   the same bytes, so the fuel is the stage's. No other package needs it: the rest write under
   `tmp_path` or `/tmp`.

8. **What is not selected, each with its reason and closer** (READ from imports and configs,
   `collection-risks.txt`; the survey confirms each line or moves it to a class):

   | package | not selected | reason | closes with |
   |---|---|---|---|
   | fonttools, joblib, mpmath, sympy, patsy | doctests in the package's own modules (`--doctest-modules`), and patsy's `test_*` functions inside its library modules | pytest reads them from source files; the product's modules are bytecode in the zip, and a source copy would test itself, not the product | `context/roadmap.md` (a later specification that collects them from the product's modules) |
   | sympy | `doc/src` doctests | the documentation tree is not staged; sympy's own CI runs it apart | the same |
   | fonttools | `Tests/metaTools/check_table_coverage_test.py` | it imports a script of the repository's `MetaTools/` folder, which the sdist does not ship | `context/specifications/067-the-pure-python-packages-own-tests.md` |
   | attrs | `tests/test_pyright.py` | it runs pyright in a subprocess | `README.md` |
   | jinja2 | `tests/test_async.py`, `tests/test_async_filters.py` | they import trio at module level; trio is not in the product or kit | the same as fonttools' |
   | pyparsing | `tests/test_diagram.py` | `railroad` (railroad-diagrams) is not in the product | the same |
   | html5lib | its conftest and the tests it collects (tree construction, tokenizer, sanitizer data files); `html5lib/tests/test_meta.py` | the conftest imports `pkg_resources` and the pytest-expect plugin, neither in the product or kit, so the group runs with `--noconftest`; `test_meta.py` imports `mock` | the same |
   | tqdm | `tests/tests_asyncio.py`, `tests/tests_perf.py` | pytest-asyncio is not in the kit; the perf tests compare elapsed times, and the judge's clock is stepped (spec 002, Decision 9) | the same |
   | joblib | `joblib/test/test_dask.py`, `joblib/test/test_memmapping.py` | dask and distributed are not in the product; memmapping needs `mmap` and worker processes | `README.md` |
   | sympy | `sympy/utilities/tests/test_autowrap.py`, `sympy/utilities/_compilation/tests/`, `sympy/external/tests/test_codegen.py`, `sympy/interactive/tests/test_ipython.py` | they compile C or Fortran, or start IPython, in subprocesses | `README.md` |
   | narwhals | modules that import pyarrow or polars at module level (13 READ; the survey lists them) | neither is in the product | `README.md` |
   | toolz | `toolz/sandbox/tests/test_parallel.py` | it uses `multiprocessing` pools | `README.md` |

9. **Known failures are classes, by test id, each one gap** (066's Decision 9). The classes the
   platform's documented facts predict, per group, INFERRED from the files:

   | class | reason (all close with `README.md` unless named) | likely in |
   |---|---|---|
   | `no-processes` | no processes | packaging (`test_tags`, `test_musllinux`), pypdf (11 modules run `python -m pypdf`), cloudpickle (`subprocess_pickle_echo`), typing-extensions, tabulate (`test_cli`), fonttools (`ttx_test`, `main_test`), sympy (`test_misc`), tqdm (`tests_main`) |
   | `no-threads` | no threads | more-itertools, networkx (`test_decorators`), tqdm, charset-normalizer (`test_thread_safety`), threadpoolctl, sympy (`test_symbol`), joblib (the `threading` backend) |
   | `shallow-recursion` | recursion through Python stops at 40 to 250 levels | sympy (deep expression trees), networkx (recursive DFS), jinja2, pyparsing, bs4 and soupsieve (deep documents), attrs (recursive `repr`) |
   | `zip-no-source` | the product's modules are bytecode | attrs, pyparsing, sympy (`inspect.getsource` users), toolz (`curry` signatures from source) |
   | `zip-code-names` | code objects carry relative file names | packages that check a warning's `filename` or a frame's file |
   | `no-tzset` | `time.tzset` and the host's `/usr/share/zoneinfo` are absent; zoneinfo comes from tzdata in the zip | python-dateutil (`tzlocal`, `gettz` of system zones) |
   | `wasm32` | 32-bit `sys.maxsize`, `hash()` width, 4 GiB address space | sympy, mpmath (big-integer edges), charset-normalizer (`test_large_payload`), cloudpickle (`old_pickles` made on 64-bit) |
   | `no-ctypes` | the `ctypes` stand-in: `dllist()` is `[]`, calls raise | threadpoolctl (its `_pyMylib` and OpenMP helpers are never built) |

   scipy-dependent tests are skips, not a class: they call `importorskip("scipy")` (networkx in
   87 places, READ). A failure no class admits is a finding (Decision 1).

10. **The groups, their caps, and the budget.** One session and one check per group; a cap is 1.5
    times the survey's fuel, rounded up to two figures; the bound is 480 G per group (066's
    Decision 11). INFERRED fuel from test counts at the rates numpy, pandas and CPython show (16 to
    48 M per pass) and heavier where a test writes a file or a font:

    | group | paths | `def test` (READ) | fuel (INFERRED) | provisional cap |
    |---|---|---|---|---|
    | `sympy-core` | `core`, `logic`, `sets`, `assumptions`, `strategies`, `multipledispatch`, `unify` tests | about 2,700 | 150 to 500 G | 7.5×10¹¹ |
    | `sympy-calculus` | `solvers`, `integrals`, `series`, `simplify`, `calculus`, `concrete`, `holonomic` | about 2,170 | 200 to 600 G | 9.0×10¹¹ |
    | `sympy-algebra` | `functions`, `matrices`, `tensor`, `algebras`, `liealgebras`, `categories`, `diffgeom` | about 1,770 | 100 to 400 G | 6.0×10¹¹ |
    | `sympy-polys` | `polys`, `ntheory`, `combinatorics`, `crypto`, `discrete` | about 1,770 | 100 to 400 G | 6.0×10¹¹ |
    | `sympy-printing` | `printing`, `parsing`, `codegen`, `utilities`, `external`, `testing`, `interactive` | about 2,400 | 100 to 350 G | 5.3×10¹¹ |
    | `sympy-physics` | `physics`, `stats`, `geometry`, `vector`, `plotting`, `sandbox` | about 1,730 | 100 to 400 G | 6.0×10¹¹ |
    | `networkx-algorithms` | `networkx/algorithms/**/tests` | 2,957 | 60 to 200 G | 3.0×10¹¹ |
    | `networkx-rest` | every other `networkx/**/tests` | 1,588 | 30 to 100 G | 1.5×10¹¹ |
    | `fonttools-ttlib` | `Tests/{ttLib,ttx,misc,cffLib,t1Lib,afmLib,encodings,tfmLib,fontBuilder,merge}` and `Tests/*_test.py` | about 1,250 | 50 to 150 G | 2.3×10¹¹ |
    | `fonttools-varlib` | the other `Tests/` folders (`varLib`, `feaLib`, `ufoLib`, `pens`, `voltLib`, `subset`, `otlLib`, `colorLib`, `designspaceLib`, `cu2qu`, `qu2cu`, `svgLib`, `mtiLib`) | about 1,800 | 60 to 200 G | 3.0×10¹¹ |
    | `xlsxwriter-comparison` | `xlsxwriter/test/comparison` | 998 modules | 50 to 200 G | 3.0×10¹¹ |
    | `xlsxwriter-units` | the rest of `xlsxwriter/test` | 237 modules | 10 to 40 G | 6.0×10¹⁰ |
    | `openpyxl` | `openpyxl/**/tests` | 1,720 | 40 to 150 G | 2.3×10¹¹ |
    | `pypdf` | `tests` | 1,260 | 30 to 120 G | 1.8×10¹¹ |
    | `narwhals` | `tests` | 1,640, twice for two constructors | 40 to 150 G | 2.3×10¹¹ |
    | `mpmath` | `mpmath/tests` | 350 | 30 to 120 G | 1.8×10¹¹ |
    | `packaging`, `python-dateutil`, `attrs`, `jinja2`, `pyparsing`, `bs4`, `soupsieve`, `pyyaml`, `charset-normalizer`, `joblib` | one group each | 45 to 1,387 each | 5 to 60 G each | 1.5 times each, at most 9.0×10¹⁰ |
    | the 19 smallest (`cycler`, `six`, `tzdata`, `et-xmlfile`, `xlrd`, `html5lib`, `webencodings`, `defusedxml`, `xmltodict`, `tomli-w`, `markupsafe`, `tabulate`, `patsy`, `more-itertools`, `toolz`, `tqdm`, `typing-extensions`, `cloudpickle`, `threadpoolctl`) | one group each | 5 to 761 each | under 10 G each | 1.5×10¹⁰ each |

    - **sympy's budget: 1.2×10¹² of caps.** sympy's fast selection is about 12,500 tests, INFERRED
      at 0.75 to 2.7 T, more than numpy's and pandas' together. The survey measures all six sympy
      groups. The builder keeps them in this order while the sympy family's caps stay within
      1.2×10¹²: `sympy-core`, `sympy-calculus`, `sympy-algebra`, `sympy-polys`, `sympy-printing`,
      `sympy-physics` (what an agent's symbolic work reaches first). A group that does not fit
      becomes a `not_selected` entry naming its folders, with the reason "fuel: past 067's sympy
      budget" and the closer `context/roadmap.md`, where the lane reserves its follow-up. If
      `sympy-core` alone does not fit, Decision 1's delta goes to the lane.
    - **067's budget: 3×10¹² of caps** over its 37 families, sympy's included. The provisional
      caps above pass it (at most about 7.3×10¹² with every sympy group); they are provisional.
    - **The cost of 37 families**: one pytest start per group, INFERRED 2 to 5 G each, about 0.1
      to 0.2 T in all. It buys a pass count and a fuel row per package, and fuel that no other
      package's stage can move.

11. **The release: three Linux shards; the lane runs everything at every landing.** As 066's
    Decision 12 (its measurements, its bound of 360 s of job time, its moves past the bound):

    | shard | groups | fuel (INFERRED) |
    |---|---|---|
    | `upstream-pure-sympy` | the sympy groups the budget keeps | up to 0.8 T |
    | `upstream-pure-a` | networkx, fonttools, xlsxwriter, openpyxl, mpmath | 0.3 to 1.0 T |
    | `upstream-pure-b` | the other 31 families | 0.25 to 0.8 T |

    With 066's three, 27 jobs start together against 20 slots. The ten jobs that end within about
    two minutes (`verify`, `own-runner`, `own-rest`, `upstream-macos`) free their slots for the
    last to start; INFERRED, the judge stage grows by 0 to 1.5 minutes past the 457 s macOS leg.
    Linux only in the release; no group probes the host's file system (XlsxWriter's writable copy
    is the one write to a grant, and the dry run's G5 compares its outcomes with the lane's).

12. **`packages.toml`: 37 suites.** Every `later` entry closed by `spec 067` becomes `suite`.
    After 067 no entry names `spec 067`. A package whose survey shows no test can pass in the guest
    stays `later` with that reason and a closer the lane reserves; none is expected (cloudpickle's
    `pickle_depickle` tests and threadpoolctl's API tests run in one process, READ).

13. **The rules, widened** (beyond 066's): every `tests` line in `00_download.sh` has a
    `SHA256SUMS` line and a `SOURCE_PATTERNS` entry, and the reverse; a tag archive's name ends
    `-tag.tar.gz`; every `kit_extra` name is in `kit-extra.txt`; `kit-extra.txt` has 050's kit
    rules; a writable family is named in `upstream.py`'s list of one; each family's test source
    names the version of the product's pin.

14. **The README and the CHANGELOG.** The README's testing section names the 37 suites in one
    paragraph, what is not run and why, and that eight come from release tags. The CHANGELOG:
    "The release runs the pure-Python packages' own tests (spec 067); 34 test sources are pinned
    and named in `MANIFEST`."

## Intent

The judge runs the own test suites of the 37 pure-Python packages inside the guest, from sources
pinned by hash and tied to the bytes the product ships. It counts every pass and names every known
failure and every test it does not run. The release runs them on Linux in three new shards; the
lane on darwin at every landing. It turns red when a pass is lost, a test traps, an unknown failure
appears, a test runs against a copy of the product's code, or a test source is not the shipped
code's.

## Design

```
downloads/SHA256SUMS                 34 lines (26 sdists, 8 *-tag.tar.gz)
scripts/00_download.sh               tests(): 34 lines; --tests fetches them
tests/upstream/<package>.toml, .ini  37 families (Decision 2); grant /upstream-<package>;
                                       kit_extra; writable (xlsxwriter only)
tests/upstream/kit-extra.txt         freezegun, pretend, tomli
tests/upstream/expected/<group>/<class>.txt
tests/harness/pins.py                SOURCE_PATTERNS for each test source
tests/harness/upstream.py            PACKAGES += 37; the source tie against the wheel; the writable
                                       stage and its before-and-after hashes; kit_extra; budgets
tests/upstream/fetch.py              tests lines; the pinned wheel beside each test source
tests/upstream/packages.toml         37 suites
tests/release_shards.toml            upstream-pure-sympy, -a, -b (linux)
.github/workflows/release.yml        judge-linux's matrix and outputs; gather's inputs
tests/known_gaps.toml                one entry per class and trap
tests/unit/test_upstream.py, test_shards.py, test_fetch_trees.py, test_pins.py
README.md, CHANGELOG.md, context/progress/README.md, spec 063 (one dated line), context/roadmap.md
```

**A group's run** is 066's, with two steps added at staging: the wheel tie (Decision 4), and, for
XlsxWriter, the writable copy and its comparison after the session (Decision 7).

**Spec 063, one dated line** in its Status: "2026-10-…: the 37 pure-Python packages are `suite`s
since spec 067, in three new Linux shards."

## Scope

**In:** the above.

**Out, each with its reason:**
- **The compiled packages** (066) and **scipy, scikit-learn, statsmodels** (their own specifications).
- **Packages added after this draft** (042's seaborn and reportlab, 046's line's python-docx and
  python-pptx): each specification that adds a package adds its suite (AGENTS.md).
- **Doctests inside the product's modules**, for five packages (Decision 8): a later specification.
- **Optional test modules** (wcwidth, pympler, trio, pytest-asyncio): their tests skip or are named.
- **Fixing what the suites find.** A class with its closer, or a finding for the lane.
- **The plain binary, macOS and Windows release shards** (066's reasons).
- **Wall-clock.** No check reads a clock; every time above is a benchmark estimate.

## Acceptance criteria

Each is counted; none times anything. Each check is written first and seen failing against today's
code or a stand-in, recorded in the landing notes; a stand-in is never committed.

1. **The pins.** `scripts/00_download.sh --tests` fetches the 34 sources and each verifies; a plain
   `scripts/00_download.sh` fetches none of them (its line counts them as pins not fetched).
   `tests/unit/test_pins.py`: a `tests` line with no `SHA256SUMS` line fails, and the reverse; a
   tag archive not named `-tag.tar.gz` fails.
2. **The rules.** `test_upstream_files_are_well_formed` passes with Decision 13's rules; each rule
   has a unit variant that fails with its own line.
3. **The tie.** Unit checks with synthetic archives: a wheel whose `fonttools/ttLib/ttFont.py`
   differs from the test source's fails the family, naming the file; a test source whose version is
   not the product pin's fails; a `MANIFEST` pin that differs from the source's hash fails (not
   blocked).
4. **The writable stage.** Unit checks: a session that changes a staged file is a finding; one that
   removes one is a finding; one that adds `_test_x.xlsx` and removes it is not; the copy is gone
   after the session.
5. **The survey, then the baseline** (EXECUTED on the frozen set of 066's tip with 067's pins,
   Decision 1): the memo exists; each group check fails before its lists and gaps exist.
6. **With the TOML, the lists and the gaps complete**, each group check passes; each class and trap
   check fails as its gap says; the numbers are in the landing notes, equal to the memo's or
   explained. sympy's kept groups and their caps are within 1.2×10¹², and 067's within 3×10¹².
7. **Fuel repeats.** Each new group twice in one judge session: equal within `sameness.py`'s
   tolerance.
8. **Nothing else moves.** The full judge's ratchet against 066's tip: every existing row lost 0,
   grew 0; the `/upstream`, `/cpython` and 066 stages' manifests are byte-for-byte the base's.
9. **The artifact set.** The set rebuilt on the branch equals the base's in `python.wasm`, the
   snapshot, the zip and every `LICENSES` file; `MANIFEST` differs in exactly 34 added `pin` lines
   and the `recipe` line of `scripts/00_download.sh`; the set's `SHA256SUMS` only in `MANIFEST`'s
   line.
10. **`packages.toml`.** The 37 are `suite`; a unit check fails if any entry names `spec 067`.
11. **The shards and the fetch** (as 066's criteria 7 and 8): each new group in exactly one Linux
    shard; the workflow scan passes and fails on a missing matrix entry; a shard with `six` fetches
    the kit, `six-1.17.0.tar.gz` and the six wheel, and nothing else; a shard with `dateutil` also
    stages freezegun.
12. **The full judge** green (`ruff check`, `ruff format --check`, `uv run pytest -n 6`) apart from
    the gaps this specification adds, each named.
13. **The branch's dry run, before landing**, and **the lane's after landing**, as 066's criteria
    12 and 13: every job green but growth lines and G7; the three shards within 360 s each.

## The owner's choices

None is needed to build. Three defaults the owner may move, each decided above:
- **sympy's share** (Decision 10): 1.2×10¹² of caps, groups kept in a stated order; the rest named,
  not run, until a follow-up.
- **The release's job count** (Decision 11): six more Linux jobs with 066's.
- **Tag archives as test sources** for eight packages (Decision 3), with the stated risk that a
  forge may change an archive's bytes.

## For the lane

- **Wave kind: build-class**, and it changes the artifact set (`MANIFEST`): the pre-build review is
  required (§5.6). It is a package wave's entry in kind (pins), with no rebuilt binary: the lane's
  rebuild must show criterion 9. **Dry-run needs:** the branch dry run, then the wave's.
- **Order.** Stacked on 066's reviewed tip; lands after 066, with a delta review of the rebase.
  Its own branch, `spec/067-the-pure-python-packages-own-tests`, is made from 066's tip when the
  lane confirms it; until then its draft rides on 066's branch.
- **The claim list skeleton** (the builder fills each value):
  - **Gained rows:** `test_upstream_suite[<group>]` for every kept group (Decision 10), with new
    metrics `fuel` and `passes` and facts `counts`, `passed_digest`, `left_out`; a class row per
    class with members and a trap row per trap, each a gap.
  - **Gaps added:** their count and ids, each with its closer.
  - **Moved rows:** none (criterion 8).
  - **The artifact set:** `MANIFEST` +34 `pin` lines and one `recipe` line; the set's
    `SHA256SUMS` line for `MANIFEST`; nothing else (criterion 9).
  - **The judge hash changes**; **packages.toml**: 37 `later` become `suite`.
- **The flags** (skeleton; each reason begins with "067:"):

  ```
  --accept "067: the pure-Python packages' own tests in the release: 37 packages, <n> groups, <p> passes, <c> classes, <t> traps; 34 test sources pinned and named in MANIFEST"
  --accept-judge "067: tests/upstream/<package>.toml and .ini for 37 families; kit-extra.txt (freezegun, pretend, tomli); the wheel tie and the writable stage in upstream.py; SOURCE_PATTERNS; fetch.py's tests lines and wheels; packages.toml (37 suites); three Linux shards in release_shards.toml and release.yml; the unit checks"
  ```

  No `--accept-growth` and no `--accept-fewer-passes`. If 037 has landed, scipy's arrival may
  turn some networkx and patsy skips into passes: gains, accepted with the rest.

## Landing notes

Not built yet.
