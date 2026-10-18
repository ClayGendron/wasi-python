# Review of 044 — scikit-learn, and 045 — statsmodels (the specifications, before build)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the
  constitution (§4.1, §4.2, §4.4, §4.6, §4.8, §4.10, §4.11, §4.12, §4.15, §5.2, §5.6, §5.7, §6,
  §7), both specifications, both upstream folders in full
  (`../upstream/10-scikit-learn-html-repr-from-a-zip/` and
  `../upstream/11-statsmodels-datasets-from-a-zip/`: `pr.md`, `fix.patch`, `notes.md`,
  `evidence/`), questions 80 and 83 in `../questions-for-the-owner.md`, and the specifications
  they lean on: 037 (Decisions 2, 6, 7, 8, 15), 041 (Decision 1 as revised), 042 (Decisions 5,
  9, 11), 035 (Decisions 6, 9). I read the code they change: `scripts/gen_inittab.py`,
  `scripts/steps/60_link.sh` (`clashes()`), `scripts/steps/50_pandas.sh`,
  `scripts/make_stdlib_zip.py`, `scripts/python-wasi-cross`, `recipes/wasi-pandas.cross`,
  `scripts/line.conf`, `downloads/SHA256SUMS`, and meson's `_shebang_to_cmd` in the line's
  `build/tools/pylib/mesonbuild/programs.py`. Upstream: Cython issue 7846 and pull request
  7852, scikit-learn issue 34525 and pull requests 34533 and 34584, scikit-learn's
  `pyproject.toml` history and `main`'s `estimator.py` (all with `gh`); both sdists'
  `meson.build` files, `pyproject.toml`, contributor and AI policies and `AGENTS.md`; the
  dataset modules' `COPYRIGHT` strings; UCI's dataset pages for four of scikit-learn's bundled
  datasets. Each claim below is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/044-scikit-learn.md` and
  `context/specifications/045-statsmodels.md` as drafted (committed in `7e720d8`), the two
  facts sheets, and question 83.
- **Ran (EXECUTED, darwin-arm64, macOS 26.5.2).** Nothing in `src/`, `tests/`, `scripts/`,
  `recipes/`, `downloads/`, the specifications or the upstream folders was edited;
  `scripts/build.sh` and the judge were not run. The project's scripts were imported read-only.
  Guest probes ran today's `build/artifacts` through `uv run wasi-python run`. Host runs used
  the line's CPython 3.15.0 (`build/tools/python`) in scratch venvs under `uv run`, with `HOME`
  and `XDG_CACHE_HOME` pointed at scratch. No dataset was fetched from inside a package.
  Everything is under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/044-review/`:
  - `json/`, `dl/`: PyPI's JSON for every pin; each file downloaded and hashed
    (`shasum -a 256`), and numpydoc's licence text from its pinned commit URL.
  - `src/stock/`, `src/patched/`: fresh extractions of both sdists (no link or absolute member,
    EXECUTED with `tar tzvf`); `patched/` had each `fix.patch` applied with `git apply -v`, and a
    third extraction was checked with `patch --dry-run`.
  - `venvA` (oracle-like: numpy's `macosx_14_0` Accelerate wheel, scipy's pinned
    `macosx_12_0` wheel, PyPI's scikit-learn and statsmodels wheels, the pure formulaic,
    interface-meta and wrapt wheels), `venvB` (the same with numpy's `macosx_11_0` OpenBLAS
    wheel), `venvC` (numpy 2.5.2 built from the pinned sdist with `-Dblas=none -Dlapack=none
    -Ddisable-optimization=true` and `CFLAGS=-ffp-contract=off`, then scikit-learn and
    statsmodels built from their sdists with `-ffp-contract=off`), `venvD` (no scikit-learn,
    plus pytest, for the Cython 3.3.0 test run).
  - `tools/mkzip.py`, `tools/zipmodel.py`: my own model of the guest's import path (the
    package's non-extension files in a zip first on `sys.path`; its extension modules loaded
    by name from site-packages through a meta-path finder). `tools/probe_sk.py`,
    `tools/probe_sm.py`, `tools/outside.py` → `out/sm-*.txt`; `jobs/` (both drafted goldens
    run under each venv and from the zips); `tools/sens_sk.py`, `tools/sens_sm.py` →
    `out/sens_*.txt` (1-ulp input noise); `tools/count.py` (members and bytes through
    `make_stdlib_zip.walk`, `tree_members`, `wheel_members`, `pyc` and `member`);
    `tools/modlist.py` (init names across the wheels of every package in or headed for the
    set); `out/obj-defs.tsv` (`nm -m` over the drafting run's native objects in
    `../044-spec/b-sk`, `../044-spec/b-sm`); `sk33/site` (the stock sdist's `sklearn/` with
    the 69 modules the drafting run built natively with the line's Cython 3.3.0),
    `tools/p7846.py` and `out/sk33-g1.txt` to `g6.txt` (issue 7846's shape, and scikit-learn's
    own tests, on that build); `web/` (UCI's pages).

## What holds

- **The pins.** EXECUTED (`json/`, `dl/`): scikit-learn's sdist `629cada3…2977` (7,786,908
  bytes, uploaded 2026-09-10), statsmodels' sdist `5d257fe5…ecbc`, formulaic `0f84ff49…b09b`,
  interface-meta `f38016be…6323`, wrapt's pure wheel `c6e6c226…ac1d`, numpydoc's licence text
  `0b78243e…033d` (1,298 bytes), and both oracle wheels (`e1b46824…8942`, `24b9917a…8606`)
  equal PyPI's digests and the specifications' lines. Each is the newest release on PyPI today.
  scikit-learn has exactly one cp315 arm64 macOS wheel (`macosx_12_0`, plus a `cp315t`), so its
  oracle pin has no Accelerate variant to avoid. Every requirement bound in Decision 1 of each
  specification is met (READ, PyPI `requires_dist`).
- **The Cython 3.3.0 reasoning.** READ (`gh`): pull request 34533 ("BLD Pin cython<3.2.6 to
  avoid Cython __annotate__ pickling bug", one file, `pyproject.toml`) names issue 34525 and
  nothing else; 34584 extends the exclusion to 3.2.9 because the fix "will be released in
  3.2.10", which is not on PyPI. Cython issue 7846 was closed by pull request 7852, merged into
  `master` on 2026-07-25; 3.3.0b1 followed on 2026-08-14. EXECUTED: all 92 added lines of
  7852's diff are in the 3.3.0 sdist, and all 66 lines it adds to `CythonFunction.c` are in
  the line's **pinned** wheel (`cython-3.3.0-cp315-cp315-macosx_11_0_arm64.whl`, from
  `downloads/`). So 3.3.0 is the only released Cython that carries the fix, and nothing else
  motivated the cap. `sklearn/meson.build:22-59` checks only a minimum, and only when not
  cross-compiling (READ). (See finding 12 for the evidence the text should cite.)
- **No OpenMP, serial joblib.** READ: `_openmp_helpers.pxd` defines the fallbacks under
  `#ifndef _OPENMP`; joblib 1.6.0's `_multiprocessing_helpers.py:13-19` sets `mp = None` when
  `_multiprocessing` is missing, and each backend's `effective_n_jobs` returns 1 when `mp is
  None` (`_parallel_backends.py:315-318, 528-529, 653-656`), with `DEFAULT_BACKEND =
  "threading"`. EXECUTED in today's guest: no `_multiprocessing`, `cpu_count()` 1, a thread
  cannot start. The drafting probe's setup log holds "OpenMP found but omp.h missing" and "Run-time
  dependency OpenMP for c found: NO", so the gate's text is the one meson prints.
- **scipy's declarations.** READ: the drafting run's scipy sdist hashes to 037's pin
  (`52c4b742…7307`, EXECUTED); `scipy/linalg/meson.build` installs `cython_blas.pxd` and
  `cython_lapack.pxd` from a `custom_target` with `install_tag: 'devel'`; `linalg/__init__.pxd`,
  `special/__init__.pxd` and `special/cython_special.pxd` are sdist files; the five `.pxd`
  files cimport only each other. Both packages' cimports are `cython_blas`, `cython_lapack` and
  `cython_special` only (EXECUTED: `grep`).
- **The init-name clashes are exactly the ones named.** EXECUTED (`tools/modlist.py` over the
  arm64 wheels of numpy, pandas, scipy, matplotlib 3.11.2, Pillow, kiwisolver, contourpy 1.4.0,
  scikit-learn and statsmodels, plus 046's `lxml.etree`, `lxml.objectify` and 047's
  `regex._regex` from their specifications): the only shared last names are
  `_cyutility` (pandas, scipy, scikit-learn), scikit-learn's `_gradient_boosting`, `_tree`,
  `_utils` pairs, statsmodels' three `_filters`/`_smoothers` pairs, and `_tools` (scipy's
  `csgraph._tools` and statsmodels'). 69 and 26 extension modules, none tagged tests.
- **The C-name clashes are the nineteen named.** EXECUTED (`out/obj-defs.tsv`, `nm -m` over the
  drafting run's native objects): the strong duplicates outside libc++'s inline templates,
  `__clang_call_terminate` and one OpenMP critical-section variable (absent without OpenMP)
  are exactly 18 of the 19 svm names (`mt_rand`, `set_seed`, `set_parameter`,
  `set_verbosity` three times) and the six `PyInit_` pairs; the nineteenth,
  `bounded_rand_int`, is a weak definition (finding 6). statsmodels has none but its init
  names. Against numpy's, pandas' and scipy's wheels no scikit-learn or
  statsmodels symbol name is shared beyond Cython's file-local helpers (EXECUTED: the
  intersection of `nm -U` names). The per-translation-unit plan is sound: `set_seed` is called
  inside `svm.cpp` (one translation unit with its generator) and from `liblinear_helper.c` into
  `linear.cpp`, which share one header (READ).
- **Both patches apply and do what they say.** EXECUTED: `1aafac38…b12b` (1,848 bytes) and
  `a83b56a1…dd58` (2,783 bytes) apply to fresh extractions with `git apply` ("Applied patch …
  cleanly") and `patch` (no offset). In my own zip model: stock scikit-learn fails at `import
  sklearn` with `NotADirectoryError: …/sk-stock.zip/sklearn/utils/_repr_html/estimator.css`;
  patched, it imports, `estimator_html_repr` of the pipeline has the same normalised digest
  (`e469424e…`) from the zip as stock on disk and holds `estimator.css`'s first line,
  `all_estimators()` gives 208, the six loaders give native's shapes, and with Pillow present
  and `sklearn/datasets/images/` left out both image loaders raise `ModuleNotFoundError: No
  module named 'sklearn.datasets.images'`. statsmodels from the stock zip: 0 of 29 datasets
  load (all `NotADirectoryError`); patched: 29 of 29, every frame's digest equal to stock on
  disk; with the 35 leave-outs: the 16 public-domain sets load and the 13 raise
  `FileNotFoundError` naming their CSV (`out/sm-*.txt`). Both drafted goldens print native's
  bytes from the patched zips (`22c6a48f…`, `6a855bc1…`).
- **The goldens do not depend on the arithmetic underneath.** EXECUTED (`jobs/`): each drafted
  golden prints the same bytes under numpy with Accelerate (venvA), with OpenBLAS (venvB), and
  with no BLAS, no LAPACK, no SIMD and no FMA contraction (venvC, numpy built as step 40 builds
  it, then scikit-learn and statsmodels rebuilt from their sdists with `CFLAGS` and `CXXFLAGS`
  `-ffp-contract=off`, which meson reads at setup; that build found the host's OpenMP and ran
  with it), and under hash seeds 0 and 1. Five draws of 1-ulp noise on the inputs of every iterative or ill-conditioned line
  (logistic regression, KMeans, PCA, linear and ridge, SVC with its default `tol=1e-3`,
  LinearSVC, OLS on Longley at nine digits with condition number 4.86e9, Logit, Poisson GLM,
  ARIMA) change no printed line (`out/sens_*.txt`). That is the best pre-build evidence that the
  guest's arithmetic (numpy without BLAS, wasm without FMA, a generic OpenBLAS) will reproduce
  them; it does not replace the build's run.
- **The members.** EXECUTED (`tools/count.py`, step 70's own functions under 3.15.0,
  `PYTHONHASHSEED=0`): scikit-learn's patched tree with the images left out gives 410 members
  (3,269,621 zip bytes); statsmodels' staged tree (no `_build/`, with `pyproject.toml`) with the
  35 leave-outs gives 502 (3,775,791); the three pure wheels 86 (349,130). The sdist trees equal
  the wheels' package files once sources, tests and `meson.build` are set aside (EXECUTED:
  `comm`; the wheel adds only the generated `_dist_metrics.pxd` and statsmodels'
  `pyproject.toml`).
- **The stdlib reaches.** EXECUTED: every stdlib top-level module the two goldens,
  `all_estimators()` and the four statsmodels `api` modules import natively either imports in
  today's guest or is one the packages already treat as optional (`_ctypes` behind 039's
  stand-in, `_decimal`, `_hashlib`, `_ssl`, `_multiprocessing`, `_posixsubprocess`, `pwd`,
  `grp`, `fcntl` and the like).
- **The absences.** EXECUTED in today's guest: `subprocess.check_call` raises `OSError` ("wasi
  does not support processes"), which `_find_x12` catches, so `x13_arima_analysis` raises
  `X13NotFoundError`; `multiprocessing.Pool()` raises `AttributeError: module 'os' has no
  attribute 'pipe'`; `urlopen("https://…")` raises `URLError: unknown url type: https`.
- **The datasets' terms are as stated.** READ (every `COPYRIGHT` string in the sdist): 16 public
  domain, 8 "with permission", fertility (World Bank terms), china_smoking (a citation),
  cancer and heart (`???`), interest_inflation (`...`), as Decision 9 lists them.
- **The version script and the stand-in.** READ: `meson.build:7` runs
  `statsmodels/_build/git_version.py`, whose `#!/usr/bin/env python3` meson replaces with its
  own Python (`programs.py:262-263`); the script calls `setuptools_scm.get_version(root=ROOT)`
  and `packaging.version.Version`; `_version.py` is in the sdist with `'0.15.0'`, so
  `statsmodels/meson.build:45` generates nothing. A stand-in that reads `PKG-INFO` is what
  setuptools_scm's own sdist fallback reads.
- **Step numbers 58 and 59 are free** in today's tree and in every drafted specification
  (EXECUTED: `grep` of 023, 037 to 043, 046, 047).

## Acceptance criteria against evidence

| criterion | 044 | 045 |
|---|---|---|
| 1, checks seen failing first | reproducible: stock zip fails at import, leave-out absent shows the images (EXECUTED in the model) | reproducible: stock zip loads 0 of 29; `meson setup` without the stand-in fails (READ) |
| 2, build from pins | not checkable before build; findings 3 and 6 change what it checks | not checkable; finding 5 changes the leave-out mechanism |
| 3, same bytes, release jobs | not checkable before build | not checkable before build |
| 4, the judge | not checkable before build | not checkable; finding 10 adds a growth row, finding 5 a judge change |
| 5, numbers | the fetcher's exception needs finding 11's grant | the same |
| 6, dry run | — | — |

## Findings, most severe first

1. **(044) Question 83 tells the owner the six bundled datasets carry "no notice of their
   own", but three of them are copies of sets their source publishes under CC BY 4.0, a
   licence §4.12 does not name.** Medium: §4.12 approves by component, and the owner is asked
   to decide on facts that leave this out. The specification leaves the sample photographs out
   partly because CC BY 2.0 is unapproved, so the omission also makes the two decisions look
   inconsistent.
   - EXECUTED (`web/uci-*.html`, `curl` of UCI's pages): breast cancer Wisconsin diagnostic
     (17), wine (109), optical recognition of handwritten digits (80) and iris (53) each say
     "This dataset is licensed under a Creative Commons Attribution 4.0 International (CC BY
     4.0) license". READ: `descr/digits.rst` ("a copy of the test set of the UCI ML
     hand-written digits datasets"), `breast_cancer.rst` and `wine_data.rst` ("a copy of UCI
     ML …") name UCI as the source. `iris.rst` says the data is "taken from Fisher's paper",
     and differs from UCI's copy in two points, so UCI's licence is not plainly its source's.
     Diabetes (Efron et al.) and Linnerud (Tenenhaus) state no terms.
   - True as written: the sdist has no licence text beside the CSVs. But "no notice of their own"
     reads as "no terms", which is not so for three of them.
   - Fix: in Decision 11, Q83(b) and the README, name each of the six's source and its stated
     terms (CC BY 4.0 at UCI for digits, breast cancer and wine; Fisher's 1936 paper for iris,
     with UCI's copy also CC BY 4.0; none stated for diabetes and Linnerud), and recommend an
     answer. If the owner approves, `LICENSES/scikit-learn.txt` gets an attribution part for
     the UCI sets (title, source, licence, link; the `DESCR` texts already carry the
     citations). If not, the specification needs a decision for those loaders, which the
     golden and the checks use. Say in Decision 10 how the photographs' case differs (they also
     cannot be decoded).

2. **(044) `LICENSES/scikit-learn.txt` misses two third-party notices that compilation strips.**
   Medium: §4.12 says each component "ships with its notice", and a `.pyc` drops comments, so
   the zip holds the code without its notice.
   - READ: `sklearn/utils/_pprint.py` is CPython's `pprint`, adapted, under the "PYTHON
     SOFTWARE FOUNDATION LICENSE VERSION 2" given in full in its comment header, with the "brief summary of changes" that licence's
     clause 3 asks for (lines 5-67,
     "Copyright (c) 2001 … 2018 Python Software Foundation; All Rights Reserved"). Every
     estimator's `repr` imports it (`base.py:452`). `sklearn/utils/_testing.py:575-577`: "The
     following is derived from pytest, Copyright (c) 2004-2017 Holger Krekel and others,
     Licensed under MIT License"; the module ships (it is not under `tests/`).
     `externals/_packaging/_structures.py` carries the same BSD-2-Clause header as
     `version.py`, which the list names alone.
   - Both families are approved (CPython's PSF; MIT), so this is notices, not approval.
   - READ, for the builder's sweep: other "adapted from" lines name django's `slugify`
     (`datasets/_base.py:1547`), networkx (`utils/graph.py:15`) and the Glasgow IR group's
     stop-word list (`feature_extraction/_stop_words.py:4`), with no notice text in the sdist.
   - Fix: add `_pprint.py`'s header and the pytest attribution to the file's parts, name
     `_structures.py` beside `version.py`, and name the PSF and pytest parts in Q83(a). Make
     the builder's sweep concrete: every shipped `.py`, `.pyx` and `.cpp` whose comments hold
     "Copyright", "License" or "adapted/derived/copied/taken from" is listed against a part of
     the file, or against a written reason why none is needed.

3. **(044) The carried patch fails scikit-learn's own lint, and the notes say it passes.**
   Medium: the patch is hashed into `MANIFEST` and is the change the owner would put upstream,
   where CI runs this check.
   - EXECUTED (scikit-learn's configuration in its `pyproject.toml`, with ruff 0.12.2, the
     version `sklearn/_min_dependencies.py:40` pins): the stock `estimator.py` passes; the
     patched one fails `I001 Import block is un-sorted` (ruff 0.17.1 reports the same `I001`,
     beside five newer-rule findings the stock file shares), because
     `from importlib.resources import files` sits after `from inspect import isclass`. `ruff
     format --check` passes. `notes.md` says "`ruff check` passes on the changed file".
   - Fix: put the import before `from inspect import isclass`, regenerate `fix.patch`, record
     its new hash in Decision 7 and `notes.md`, and re-run the evidence (`native-run.txt`).
     The statsmodels patch passes statsmodels' `ruff check` (EXECUTED); its two files were not
     `ruff format`-clean before it either, and it adds no new format difference.

4. **(044, 045) "Why a patch and not a recipe" repeats the reason 041's review rejected.**
   Medium: both say a recipe "would replace [the package's] file in the zip, an unrecorded
   source change (§7)". 041's review (finding 3) showed that overstates §7: a recipe under
   `recipes/`, hashed in `MANIFEST` and reviewed, is recorded, and §4.1 names "a stand-in
   module" as a recipe. 041's Decision 1 was rewritten on that basis (READ).
   - The conclusion stands, for the reasons 041 now gives. scikit-learn's read runs in the
     module body (`_CSS_STYLE = _get_css_style()` at import, READ), so no swap after import can
     run; a recipe that worked would be an import hook rewriting the module or a replacement
     module, wider than eight lines; spec 020's tree check would not see it; and it would have
     no exit. statsmodels' read runs at call time, so a run-time replacement of `load_csv` could
     technically work; it is rejected on width (it replaces a public function and
     `elec_equip`'s private `_get_data`), on 020's blindness and on the missing exit.
   - Fix: rewrite both paragraphs in 041's form, each with its own case.

5. **(045) `--leave-out NAME` reverses a rule 042's unit check pins, and the specification does
   not say it changes that check.** Medium: AGENTS.md rule 4 makes a change to an existing check
   a judge change with its own reason.
   - READ (042, Decisions 5 and 11): "The prefix must end in `/` … otherwise the build stops
     naming it", and `test_a_left_out_folder_is_not_packed` asserts "a prefix without a
     trailing `/` stops it too". Decision 9 here makes that same argument an exact member name.
   - Fix, one of: (a) keep 042's rule and its check, and add a separate option
     (`--leave-out-file NAME`, exact, repeatable, the same `matched` stop) — no existing check
     changes; or (b) keep one option and name, in Decision 12 and the acceptance criteria, the
     edit to 042's check under `--accept-judge` with its reason. (a) is the smaller judge
     change; I recommend it. Either way the unit check pins that an exact name is the name
     before compilation (`x.py`, never `x.pyc`), as 042 pins it for prefixes.

6. **(044) Step 60's detector cannot see a weak duplicate, and `bounded_rand_int` is one.**
   Medium-low: the plan already renames it, but the text says "Step 60's detector is the
   authority" and "each one step 60 names is fixed", which would not catch a miss here.
   - READ (`svm/src/newrand/newrand.h:29`): `inline uint32_t bounded_rand_int(...)` inside
     `extern "C"`. EXECUTED (`nm -m` on the native objects): it is a weak definition in
     `libsvm_template.cpp.o` and `_newrand.cpp.o`. wasm-ld keeps one weak definition and
     reports nothing (INFERRED from the ELF/wasm linkers' rules), and each copy calls its own
     translation unit's `mt_rand`; a missed rename would silently make one module draw from
     another's generator. `60_link.sh` greps only `duplicate symbol` and `signature mismatch`
     (READ).
   - Fix: add a post-link gate to step 60 (or step 58): `build/link/python.map` holds every
     renamed name (`sklearn_libsvm_mt_rand`, … ) and none of the nineteen original C names;
     or, before the link, list the weak definitions in scikit-learn's wasm objects whose names
     also occur, weak or strong, in another object, outside `std::` and the C++ runtime, and
     stop on any not in a reviewed list. Say that 045 inherits the gate.

7. **(045) `open_data_file` turns a missing file outside `statsmodels.datasets` into a
   `ValueError`.** Low: it changes behaviour on disk too, which upstream will ask about.
   - EXECUTED (`tools/outside.py`): stock `load_csv` with a `base_file` in a user's folder and
     a missing CSV raises `FileNotFoundError`; patched (from the zip) it raises `ValueError:
     … is not in the subpath of …/statsmodels/datasets` from `relative_to`. INFERRED: the same
     on disk, since `is_file()` is false there too.
   - READ (statsmodels' `AGENTS.md`): every public function needs a numpydoc docstring and a
     docs entry; `open_data_file` is new and public. Its summary line has no closing period.
   - Fix: in the patch, fall back to the package resource only when `base_file`'s folder is
     under `datasets/` (`is_relative_to`), and otherwise let the original `FileNotFoundError`
     stand; consider naming it `_open_data_file`; add the period. Say both in the facts sheet.

8. **(045) The left-out datasets' `FileNotFoundError` "naming its file" comes from `zipfile.Path`,
   which spec 035 replaces.** Low.
   - READ: the drafting run and mine used CPython's `zipimport` reader, whose
     `zipfile.Path.open` raises `FileNotFoundError(self)`, the member's full path. 035
     (Decision 6) has `ZipDirectoryPath.open` raise `FileNotFoundError` for a missing name and
     says nothing about its message; 045 builds after 035.
   - Fix: make `test_left_out_datasets_say_so` assert the type and the dataset's file name
     only if 035's text promises the name (then cite it), or have 045 say what message it
     relies on and check it against 035 as landed.

9. **(045) One data table ships with no stated terms, and Decision 10 names files that do not
   stay.** Low.
   - EXECUTED (`find` over the package): `statsmodels/sandbox/rlsdata.txt` (50 rows of a
     regression data set) ships; nothing in the package reads it (EXECUTED: `grep`) and it
     states no terms, the same class as cancer and heart. Every `.html` and `.dat` file in the
     package is under `datasets/*/src/`, which Decision 9 leaves out, so "statsmodels' HTML
     templates and `.dat` tables" do not stay.
   - Fix: leave `rlsdata.txt` out (one more exact name) or name it in Q83(d); correct Decision
     10's list (what stays that is not code: the sixteen datasets' CSV files, `macrodata.dta`,
     the R scripts of the public-domain sets, `libqsturng/CH.r`, the licence texts,
     `pyproject.toml` and the 20 templates).

10. **(045) seaborn imports statsmodels at `import seaborn`, so 042's job grows by more than the
    plain start.** Low: the growth table says every existing golden grows by "the plain-start
    growth only".
    - READ (seaborn 0.13.2's wheel, `regression.py:10-15`): `try: import statsmodels` at module
      import, setting `_has_statsmodels`. `statsmodels/__init__.py` imports `_version` only,
      so the cost is small, but it is a lost-fuel line on `statistical_plots` that the builder
      would otherwise meet unexplained.
    - Fix: add the row (042's `statistical_plots` and seaborn's import: plain start plus
      `import statsmodels`, measured).

11. **(044) What `fetch_california_housing()` raises depends on the grants.** Low.
    - EXECUTED (today's guest): with no root, `HOME` is unset and `pwd` is missing, so
      `expanduser("~/scikit_learn_data")` returns the path unchanged and `makedirs` raises
      `FileNotFoundError: [Errno 44] … '~'` before any network call. With `--root`, the runner
      provides a `HOME` under `/tmp`, the folder is made there, and the download fails with
      `URLError: unknown url type: https`.
    - Fix: the check names its grant configuration (none, as written), and the README states
      both outcomes. The same holds for statsmodels' `get_rdataset(…, cache=True)`.

12. **(044) Decision 2 cites weaker evidence than exists.** Low.
    - It cites the Cython 3.3.0 **sdist**, which is not a pinned input (READ:
      `downloads/SHA256SUMS` pins the three wheels), and "the golden job's pickling ran". The
      golden pickles a fitted forest; issue 7846 is about a cyfunction wrapped with
      `functools.update_wrapper`, seen when loky sends it to a worker process (READ: 34525),
      which the guest has no way to do.
    - EXECUTED: PR 7852's 66 added `CythonFunction.c` lines are in the pinned wheel. On the
      drafting run's Cython 3.3.0 native build (`tools/p7846.py`), a scikit-learn cyfunction
      (`murmurhash._murmurhash3_bytes_array_s32`) wrapped with `functools.wraps` has a
      `__annotate__` that pickles and unpickles; `KDTree` and `BallTree` round-trip through
      `pickle`. scikit-learn's own tests on that build: RESULT_LINE.
    - Fix: cite the pinned wheel, PR 34533 (the only reason) and 34584 (3.2.10 unreleased), and
      the test run; drop the pickling sentence as evidence.

13. **(044, 045) The facts sheets.** Low.
    - READ (scikit-learn's `AGENTS.md`): "Every summary, pull request description, or work
      description MUST include this disclosure … at the end of every summary you generate",
      with the two-line text. The sheet is a summary an agent generated about scikit-learn
      code; it tells the owner the disclosure is his to make, but does not end with it. Add the
      two lines, verbatim, at its end.
    - Question 80 is open. As with 041 (its condition C1), the landing notes must say which
      answer it had.

14. **Nits.**
    - 044's golden prints `hgb.n_iter_` ("iterations 30"). 037's rule forbids iteration counts;
      with `max_iter=30` and no early stopping (178 rows) it is fixed, so either say why it is
      safe or drop it.
    - 044, Decision 11: libsvm's header is lines 1-31 of `svm.cpp` (the closing `*/`).
    - 045, Decision 6: wrapt's `importer.py` calls `importlib.metadata.entry_points` in
      `discover_post_import_hooks` (READ); it runs only when called, so "none reads … entry
      points" should say "at import".

## On the order

- READ: 044 waits on 037, 038, 039 and 042 (and through them 023, 033, 035), none of which is
  built except 033; 045 waits on 044. Both say so, and both wait on question 83. Steps 58 and
  59 are free (EXECUTED). Both are build-class and share steps 60 and 70, `gen_inittab.py`,
  `make_stdlib_zip.py`, `assemble_artifacts.py` and `00_download.sh` with 046 and 047; §5.7's
  one-in-flight rule and the "rebase and re-derive the bounds" clause cover that.
- 045's fallback (it may build first and bring `stage_scipy_cimports.sh` and `--modules-only`)
  is sound; if it does, finding 6's gate moves with it.
- One builder each is feasible. 044's four stages are the right cut: the OpenMP gate and the
  cross `meson setup` (stage 1) are the cheapest place to stop if meson refuses.

## Constitution checks

- **§4.1, patches few, recorded, temporary:** holds in design. Each patch is small, applies with
  no offset, and is matched by a facts sheet; a recipe was rightly found wanting, but for
  finding 4's reasons. The scikit-learn patch needs finding 3 before its hash is recorded.
  045's `setuptools_scm` stand-in is a recipe file of the kind §4.1 prefers, with a gate.
- **§4.2, every input pinned:** holds (EXECUTED: every hash).
- **§4.4, two imports only:** holds. `fopen` and the rest are wasi-libc's; nothing new.
- **§4.6, the artifact set:** holds. Only `python.wasm` and the zip grow.
- **§4.8, downloads untrusted:** holds. The sdists are unpacked under `build/`, the stand-in and
  Tempita run as build tools.
- **§4.10, claims carry evidence:** mostly holds; findings 3 and 12 correct two claims.
- **§4.11, platform semantics documented:** holds (serial `n_jobs`, no OpenMP, 32-bit index
  arrays, absent fetchers, processes and X-13).
- **§4.12, licences:** not yet. Findings 1 and 2 (044) and 9 (045) must be fixed in the text and
  in question 83 before the owner answers it.
- **§4.15, safe by default:** holds. Nothing writable is added; the fetchers and the caches fail
  without a grant (finding 11 states how).
- **§5.2, no open questions:** holds; the open choices are the owner's, in question 83.
- **§5.6, reviewed before build:** this review.
- **§5.7, build-class, one in flight:** holds (044 Decision 14, 045 Decision 15).
- **§7:** no hidden change; nothing is sent upstream.

## Disposition (filled in by the author, then confirmed by the reviewer)

## Verdict

**044: Not yet — revise, then confirm.** The design is sound and reproduces: the pins, the
Cython 3.3.0 reasoning, the OpenMP gate, serial joblib, the scipy `.pxd` staging, the rename
plan (its 19 names and four init names are exactly what the objects show), the patch's effect
and the golden's robustness all hold under my own runs. What must change before build is text
and one gate: question 83 must tell the owner that three of the bundled datasets are CC BY 4.0
at their source (finding 1); two stripped notices must ship (finding 2); the patch must pass
scikit-learn's lint and be re-hashed (finding 3); the recipe reasoning must be 041's (finding
4); and a weak-symbol gate must back the renames (finding 6).

**045: Not yet — revise, then confirm.** The stand-in, the leave-outs, the patch's effect and
the golden all reproduce. Before build: the recipe reasoning (finding 4), the `--leave-out`
conflict with 042's check (finding 5), the patch's `ValueError` (finding 7), the
`FileNotFoundError` message's dependence on 035 (finding 8), `rlsdata.txt` and Decision 10's
list (finding 9), and the seaborn growth row (finding 10).

## One line

Both designs reproduce, goldens included, but 044 must tell the owner its digits, breast
cancer and wine data are CC BY 4.0 at UCI, ship two stripped notices and fix its patch's
import order, and 045 must reconcile `--leave-out NAME` with 042's check and keep a missing
file a `FileNotFoundError`, before either is built.
