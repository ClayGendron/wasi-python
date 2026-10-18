# 045 — statsmodels, with formulaic, interface-meta and wrapt

- **Status:** drafted 2026-10-18. Not yet reviewed. It changes the build recipe and the artifact
  set, so it is reviewed before it is built (constitution §5.6). It is build-class: it touches
  `scripts/`, `recipes/`, `downloads/SHA256SUMS` and the release workflow (§5.7). It carries one
  upstream patch (§4.1). It is not built until the owner answers question 83 (the terms of what
  statsmodels bundles, its datasets above all); everything else is decided here.
- **Owner:** Clay Gendron
- **Kind:** the build recipe (four pins; a new step 59; `scripts/make_stdlib_zip.py`'s
  `--leave-out` taking exact names; `scripts/gen_inittab.py`'s rename table;
  `scripts/steps/60_link.sh`; `scripts/steps/70_zip.sh`; `scripts/assemble_artifacts.py`),
  recipe files (a cross file, a build-time stand-in for `setuptools_scm`, four one-line rename
  headers, a per-file include map), one carried patch to statsmodels with its facts sheet, judge
  additions and changes (a golden job and the oracle's pins, v1.3 checks, a v1.1 check, the
  package and licence lists, a source-tree pattern, a unit check), the release workflow's tree
  count, `README.md`, `CHANGELOG.md`, `LICENSES/`.
- **Depends on:** 044 (scikit-learn: `scripts/stage_scipy_cimports.sh`, the step-58 pattern this
  repeats, `install_from_plan.py --modules-only`), and through it 037 and 038 (scipy whole,
  `scipy.linalg.cython_blas` and `cython_lapack` as builtins, the per-file include rule, the
  rename table, the pinned oracle's scipy), 039 (patsy 1.0.3, narwhals, typing-extensions,
  joblib), 042 (`--leave-out`), 023 (`packaging` 26.3, which statsmodels requires at run time
  and its version script at build time) and 033 and 035. Landed: 020, 012. Where one of them
  lands in another shape than its text, this specification uses what landed and says so in its
  landing notes.
- **Research it stands on:** `../research/2026-10-17-what-else-the-default-profile-carries.md`
  (tier B: "statsmodels (+formulaic, interface-meta, wrapt in its pure form; after scipy)";
  Cython; scipy's `cython_blas`; 641 members with its three companions; Pyodide's `.so`
  4.24 MB); `../research/2026-10-17-what-scipy-needs.md` (the 0.92 size ratio); specs 037 and
  044 (the scipy line and the first package on it); the owner's decisions 43 and 48. **The
  drafting runs** (EXECUTED 2026-10-17 and 18 in the session's scratch folder, outside the
  repository; nothing in the repository was changed by them; tool outputs quoted are marked):
  - PyPI's JSON for statsmodels, formulaic, interface-meta and wrapt; each chosen file
    downloaded and hashed (equal to PyPI's);
  - the sdist read: `meson.build` files, `pyproject.toml`, `statsmodels/_build/`, the dataset
    loaders and each dataset's `COPYRIGHT`, `COPYRIGHTS.txt` and the licence files, the AI policy;
  - `meson setup` of the sdist natively without `setuptools_scm` (it fails in the version
    script) and with a stand-in, then a native build on the build host (macOS arm64, the line's
    meson 1.12.1, Cython 3.3.0, Python 3.15.0, against numpy 2.5.2 and scipy 1.18.1): all 120
    targets, 26 extension modules; then `nm` over its objects;
  - every bundled dataset loaded natively, stock and patched, from disk and from a zip, with a
    digest of each frame;
  - the golden job drafted and run natively under hash seeds 0 and 1, and with statsmodels'
    Python files imported **from a zip** and its extension modules loaded by name (the model of
    the guest's import path that 044 describes), with the patch and the leave-outs applied;
  - `from multiprocessing import Pool` and `Pool(2)` in today's `python.wasm` through
    `wasi-python run`;
  - the zip members and bytes step 70 would add, computed with step 70's own functions.

## The problem

statsmodels is the regression, time-series and statistical-test library agents reach for after
scipy; it is on most hosted sandboxes' lists and in the benchmarks (memo findings 1 and 2). The
owner put it in 0.1.0 (decision 48). Today `import statsmodels` in the guest is
`ModuleNotFoundError`, and seaborn's `lowess`, `logistic` and `robust` fits wait for it (042,
Decision 8).

Like scikit-learn it is a meson-python build of Cython on top of scipy, smaller: 26 modules, C
only, BLAS and LAPACK through scipy's `cython_blas` and `cython_lapack`. Four things are new:

- **Its version script needs `setuptools_scm`** at configure time, which the build has never
  had (EXECUTED: `meson setup` fails in `statsmodels/_build/git_version.py` without it).
- **Its datasets are read by path.** `statsmodels.datasets.utils.load_csv` reads
  `Path(base_file).resolve().parent / csv_name`. From the zip every dataset fails with
  `NotADirectoryError` (EXECUTED: none of the 29 loaded from a zip).
- **Some of its datasets carry terms the owner has not approved.** Each dataset module states
  its own `COPYRIGHT`, and statsmodels' `COPYRIGHTS.txt` says the datasets' statements are
  attached to them, not to its BSD licence. Sixteen say public domain; thirteen do not.
- **Its formula engines.** statsmodels 0.15.0 requires both patsy and formulaic; formulaic needs
  interface-meta and wrapt, which the memo said to take in wrapt's pure form.

## Decisions

1. **What goes in.**
   - **statsmodels 0.15.0:** its 26 extension modules as builtins, and its Python package (502
     members, 3,775,184 bytes as step 70 packs them, plus one `METADATA`; Decisions 9 and 10).
   - **formulaic 1.2.2, interface-meta 2.0.1 and wrapt 2.5.1**, pure wheels: 59, 12 and 15
     members with their `METADATA`, 86 in all, 349,174 bytes (EXECUTED while drafting, step 70's
     rules).
   - Their requirements already in the set: numpy, scipy (037), pandas, patsy 1.0.3 (039),
     `packaging` 26.3 (023), narwhals 2.27.1 and typing-extensions 4.16.0 (039). Each meets its
     bound (READ, the `METADATA` files: statsmodels `numpy<3,>=1.23.5`, `scipy!=1.9.2,>=1.8`,
     `pandas!=2.1.0,>=1.4`, `patsy>=0.5.6`, `packaging>=21.3`, `formulaic>=1.1.0`; formulaic
     `interface-meta>=1.2.0`, `narwhals>=1.17`, `scipy>=1.6`, `typing-extensions>=4.2.0`,
     `wrapt>=1.17.0rc1` on 3.13 and later).

2. **The pins.** Each is the current release on PyPI on 2026-10-18 and the version the memo
   measured; one `get` line each in `scripts/00_download.sh`, one line each in
   `downloads/SHA256SUMS` (EXECUTED: PyPI's digests, recomputed from the downloads):

   ```sh
   get https://files.pythonhosted.org/packages/a8/1f/a3cbf6ed7cf6286afec694bfef561f3e51483197716717fb8476f1f0c50e/statsmodels-0.15.0.tar.gz statsmodels-0.15.0.tar.gz
   get https://files.pythonhosted.org/packages/fc/75/0576b03f7889ad25b5385b4f6c69e0543713425a6f193b056c9b0a2e65ce/formulaic-1.2.2-py3-none-any.whl formulaic-1.2.2-py3-none-any.whl
   get https://files.pythonhosted.org/packages/a1/d3/20a61a248feb1249cd81f83ce731f0bdf5170ed96a08a298f7081cda9e90/interface_meta-2.0.1-py3-none-any.whl interface_meta-2.0.1-py3-none-any.whl
   get https://files.pythonhosted.org/packages/bc/0c/7da7513ddcc8f1d831ec4bfbedc9f7f174ecb91042bc16916fc1e0d06b22/wrapt-2.5.1-py3-none-any.whl wrapt-2.5.1-py3-none-any.whl
   ```

   ```
   5d257fe58d0772bc46a557880ca78e2a8e07fec7bfd9d11074aef8e33e1aecbc  statsmodels-0.15.0.tar.gz
   0f84ff49e3fc9dc0e68ab08a0a9427874021aa6c558e66b44dc634a35739b09b  formulaic-1.2.2-py3-none-any.whl
   f38016bef9a4429b6d0792d809be7b65e9781820c674bf7f463999086b6e6323  interface_meta-2.0.1-py3-none-any.whl
   c6e6c226b1ca5402d7ae5fb34a0d21f1b49124fe4200e5884d1e19e53c47ac1d  wrapt-2.5.1-py3-none-any.whl
   ```

   - The sdist (15,736,853 bytes, uploaded 2026-08-27) unpacks to `statsmodels-0.15.0`.
   - **wrapt in its pure form is upstream's own file.** wrapt 2.5.1 (uploaded 2026-10-14)
     publishes a `py3-none-any` wheel beside its platform wheels (READ: PyPI). It holds the
     Python implementation and `_wrappers.c` as source, no compiled module; `wrapt/__wrapt__.py`
     imports `._wrappers` in a `try` and falls back to the Python classes (READ). Step 70 skips
     the `.c` and the `wrapt-stubs/*.pyi`. Nothing of wrapt is compiled here.
   - **Cython 3.3.0** meets statsmodels' `cython>=3.0.13,<4` (READ, `pyproject.toml`); its
     `meson.build` asks `>= 3.0.10`. numpy's `<3` and scipy's `<2` hold. meson 1.12.1 meets
     `>= 1.9.0`.

3. **The version script, by a build-time stand-in** (§4.1: a recipe first). `project()` runs
   `statsmodels/_build/git_version.py` (`meson.build:7`). Meson runs it with its own Python, the
   pinned host Python (its `#!/usr/bin/env python3` is replaced by meson's interpreter, READ:
   `mesonbuild/programs.py`, `_shebang_to_cmd`). The script imports `packaging.version` and
   `setuptools_scm`, which the build's tools do not have: `meson setup` fails there (EXECUTED).
   - **`recipes/statsmodels_build/setuptools_scm.py`**, ours: `get_version(root)` returns the
     `Version:` header of `root/PKG-INFO`, the sdist's own metadata, and stops naming the file if
     there is none. That is what `setuptools_scm` itself does in an sdist with no repository; the
     stand-in has no other function.
   - **`packaging`** is 023's pinned `packaging-26.3-py3-none-any.whl`, put on `PYTHONPATH` as
     the wheel file itself (a pure wheel is importable as a zip), after `pinned`'s hash check.
     Nothing is installed.
   - Step 59 puts the stand-in's folder and that wheel on `PYTHONPATH` for `meson setup` only.
     EXECUTED while drafting: the script then prints `0.15.0`; `meson setup` reports "Project
     version: 0.15.0".
   - **The gate.** Step 59 dies unless the configured version equals `PKG-INFO`'s and the sdist's
     `statsmodels/_version.py` holds `__version__ = version = '0.15.0'` (READ: it does; meson
     installs that file rather than generating one when it exists, `statsmodels/meson.build`).
   - **Why not pin `setuptools_scm`.** It would be a new build tool with its own requirements,
     to read one header from one file. The stand-in is twelve lines of ours and the gate proves
     its answer.

4. **Step 59: statsmodels** (`scripts/steps/59_statsmodels.sh`, after step 58; needing 10, 20,
   40, 57). The number is free in today's tree; if a specification drafted alongside takes it
   first, the lane renumbers this one.
   - It unpacks the sdist to `build/statsmodels-0.15.0`, applies its patch (`patch_tree`,
     Decision 7), runs 044's `scripts/stage_scipy_cimports.sh` (or reuses its fresh output), and
     builds out of tree in `build/statsmodels-build`.
   - **`recipes/wasi-statsmodels.cross`**, from the pandas cross file without
     `pandas_rename.h`: the same compilers, target Python, Cython and `pkg-config = 'false'`;
     C only (the project's languages are `c` and `cython`), so no C++ flags matter; no setjmp
     flags (no `setjmp` in the sources, EXECUTED: `grep`).
   - **numpy's include folder.** statsmodels has no cross-file property for it; it runs
     `np.get_include()` through the target Python (`statsmodels/meson.build:1-19`). Step 59 puts
     step 40's host stand-in, `build/numpy-host`, on `PYTHONPATH`, as step 50 does for pandas,
     and the stand-in answers with the wasm build's headers. The same folder gives Cython
     numpy's `__init__.pxd`.
   - **scipy's declarations.** `build/scipy-cimport` (044, Decision 4) on `PYTHONPATH`. The
     statespace modules cimport `scipy.linalg.cython_blas` and `cython_lapack`, and
     `meson setup`'s check "scipy cython_blas blas_int compiles" is YES, as natively (EXECUTED).
     At run time each takes its function pointers from scipy's builtin modules' capsules.
   - **Tempita.** `statsmodels/_build/tempita.py` imports `Cython.Tempita`, which the line's
     Cython in `build/tools/pylib` provides (READ; EXECUTED natively: the 19 `.pyx.in` files
     expanded).
   - **The configure line:** `meson setup --cross-file … --buildtype=release
     -Db_ndebug=if-release`, then `ninja`.
   - **The Python package, as an install places it.** meson installs the package's
     subdirectories with `install_subdir`, three top-level modules, `_version.py` and the
     project's `pyproject.toml` into `statsmodels/` (READ, `statsmodels/meson.build`,
     `meson.build:43`). So the step copies the patched sdist's `statsmodels/` to
     `build/statsmodels-install/statsmodels`, removes its `_build/` (not installed) and copies
     `pyproject.toml` in. EXECUTED while drafting: that tree and the native wheel's hold the
     same files once tests, sources, extension modules and `meson.build` are set aside.
     `pyproject.toml` is read by nothing in the package (READ: `grep`); it is pytest's
     configuration, and an install carries it.
   - **The extension-module list** by `install_from_plan.py --modules-only` into
     `build/statsmodels-build/extension-modules.txt`; the step checks 26 modules.

5. **Four init names, renamed per file by recipe.** Within statsmodels three pairs share an init
   name: `tsa.statespace._filters` and `tsa.statespace._smoothers` each have `_conventional`,
   `_univariate` and `_univariate_diffuse`. `statsmodels.tsa.statespace._tools` shares
   `PyInit__tools` with scipy's `scipy.sparse.csgraph._tools` (EXECUTED: the module lists
   compared with numpy's, pandas', scipy's, the matplotlib set's and 044's).
   - The three `_smoothers` modules and `statespace._tools` take their dotted names
     (`PyInit_statsmodels_tsa_statespace__smoothers__conventional` and so on), through four
     one-line headers under `recipes/statsmodels-renames/`, listed in
     `recipes/statsmodels_file_includes.txt` and applied by 037's per-file include rule; the
     `_filters` modules keep theirs. `gen_inittab.py`'s rename table gains the four. Step 59 dies
     unless the include log shows each entry exactly once.
   - **No other symbol is defined twice within statsmodels** (EXECUTED: `nm` over the native
     objects; 69 distinct strong globals, none repeated but the init names). Step 60's detector
     remains the authority for clashes with other packages; each one it names is fixed by a
     header entry and listed in the landing notes.
   - **Constructors:** none expected (C only, no C++ static initialisers); 023's check shows
     any, and the reviewed list grows by exactly those.

6. **The pure wheels.** Step 70 gains three `--wheel "$(pinned …)"` lines. Each is packed as
   step 70 packs every wheel (tests, sources and `.pyi` skipped; `METADATA` kept). None has an
   `entry_points.txt`, and none reads a file by path (READ: `grep` for `__file__`,
   `importlib.resources` and `entry_points`). What a guest sees: `wrapt.__wrapt__._using_c_extension`
   is `False`, and formulaic builds model matrices as natively.

7. **One carried patch: datasets read as package resources when not on disk.**
   `recipes/patches/statsmodels-0.15.0/0001-datasets-from-a-zip.patch` (§4.1, spec 020's
   mechanism).
   - **What fails.** 28 of the 29 dataset modules call `du.load_csv(__file__, "<name>.csv")`,
     which reads `Path(base_file).resolve().parent / csv_name` with `read_csv`
     (`statsmodels/datasets/utils.py:427-455`, READ); `elec_equip` reads its CSV by the same kind
     of path (`elec_equip/data.py:66`). From the zip (EXECUTED, natively with statsmodels
     zipped): every loader raises
     `NotADirectoryError: [Errno 20] Not a directory: '…/statsmodels/datasets/longley/longley.csv'`
     (tool output, path shortened); none of the 29 loads (the 28 and `elec_equip`).
   - **The change** (2 files, +37 −6, SHA-256
     `a83b56a1e52e211d49c83f8380f2ae1b66b383d9729144f761318674265add58`, applies to the pinned
     sdist with `git apply` and no offset, EXECUTED): a new helper,
     `statsmodels.datasets.utils.open_data_file(base_file, file_name)`, returns the data file
     beside `base_file` opened in binary mode: from disk when it is a file there, as today, and
     otherwise as a package resource, `importlib.resources.files("statsmodels.datasets.<name>")`,
     the package found from `base_file`'s folder relative to `utils.py`'s. `load_csv` and
     `elec_equip`'s loader read through it; `elec_equip`'s now unused `Path` import goes. `ruff
     check` passes on both files (EXECUTED).
   - **What it changes, measured** (EXECUTED): with the patch, all 29 datasets load from the zip
     and from disk, and each frame's digest equals the stock package's on disk; the golden job
     from the zip model prints native's output byte for byte.
   - **Why a patch and not a recipe.** The read is statsmodels' own line. A recipe would replace
     its file in the zip, an unrecorded source change (§7).
   - **Its facts sheet**, `context/upstream/11-statsmodels-datasets-from-a-zip/pr.md` with
     `fix.patch`, `notes.md` and `evidence/`, in question 80's form: statsmodels' AI policy
     (READ, `docs/source/dev/ai-policy.rst` in the sdist) asks that no AI output be pasted into
     an issue or pull request description, that the use of AI be disclosed, and that every
     change come with a regression test and full coverage; the sheet names the test the owner
     would add. When this specification is built, `fix.patch` is copied byte for byte to the
     path above and `pr.md` moves unchanged to
     `context/upstream/patches/statsmodels-0.15.0/0001-datasets-from-a-zip.md`. Nothing is sent.

8. **The extension modules become builtins.** Step 60 adds `statsmodels` to its package loop and
   its 26 archives to the `_host` line. No new library: the modules link nothing but numpy's
   headers and, at run time, scipy's capsules. **No new import reaches the guest** (§4.4).

9. **Datasets whose terms are not approved are left out; the modules stay** (§4.12).
   - **The terms, as each module states them** (READ, each `COPYRIGHT`): public domain for 16
     (anes96, co2, danish_data, elec_equip, elnino, engel, grunfeld, longley, macrodata,
     modechoice, nile, randhie, stackloss, statecrime, strikes, sunspots); "used with express
     permission of the original author, who retains all rights" or "included with permission
     of the author" for 8 (ccard, committee, copper, cpunish, fair, scotland, spector, star98);
     the World Bank's terms of use for fertility; a citation for china_smoking; none stated for
     cancer and heart (`???`) and interest_inflation (a placeholder, `...`).
   - **What is left out:** the data files of those thirteen (their 15 CSVs, and the R scripts
     beside five of them: 20 files) and every `statsmodels/datasets/*/src/` folder (15: the
     original sources, which no loader reads, READ: `grep`; several are of the thirteen). Each
     dataset's `__init__.py` and `data.py` stay, because `statsmodels/datasets/__init__.py`
     imports 28 of the modules (all but `elec_equip`), and `statsmodels.api` imports that: leaving a folder out would
     break `import statsmodels.api`. 52 members in all leave (EXECUTED: every name matched).
   - **How it shows:** a left-out dataset's `load()` and `load_pandas()` raise
     `FileNotFoundError` naming its file (EXECUTED in the zip model: `spector` →
     `FileNotFoundError: …/statsmodels/datasets/spector/spector.csv`, while `import
     statsmodels.api` and `longley` work). The README lists the thirteen.
   - **`--leave-out` takes an exact name.** 042's option takes folder prefixes ending in `/`.
     This specification extends it: an argument that does not end in `/` must equal one member's
     name exactly, and the build stops naming any argument that matches nothing, as 042's rule
     does for folders. The unit check (Decision 12) holds both forms. Step 70 gains one
     `--leave-out` line per name and per `src/` folder, 35 lines, generated by no script: they
     are written out in `70_zip.sh`, so the review reads each.
   - Question 83 asks the owner whether to approve any of the thirteen; the agent recommends
     keeping them out. The golden job uses public-domain datasets only.

10. **The zip.** Step 70 gains `--tree "$B/statsmodels-install"`, `--metadata
    "$B/statsmodels-0.15.0/PKG-INFO"` (`Name: statsmodels`, `Version: 0.15.0`, READ), the three
    `--wheel` lines and Decision 9's leave-outs. What stays that is not code: the sixteen
    datasets' files, statsmodels' HTML templates and `.dat` tables, and 20 templates
    (19 `*.pyx.in` and `_blas_int.pxi.in`) an install also carries; no trimming here.

11. **What is in, what is out, and how an absence shows.** Each line is a check or a golden line
    (Decision 12), and each goes in the README.
    - **In:** every public submodule: `api`, `formula.api` with patsy (the default) and formulaic
      (`statsmodels.formula.options.formula_engine = "formulaic"`), regression, discrete and
      generalised linear models, robust and mixed models, `stats`, `tsa` with ARIMA, SARIMAX and
      the state-space filters, exponential smoothing, STL, `nonparametric`, `graphics` through
      matplotlib (023), `iolib`'s summaries.
    - **Serial:** `statsmodels.tools.parallel.parallel_func` uses joblib, which runs serially
      (044, Decision 9), and `multiprocessing.cpu_count()` is 1 in the guest (EXECUTED today:
      `wasi-python run`).
    - **Absent by the sandbox, documented, not gaps:**
      - `sm.datasets.get_rdataset` and `sm.datasets.webuse` download (no network); the build
        records the exception each raises inside the fuel limit;
      - `statsmodels.tsa.x13.x13_arima_analysis` runs the X-13ARIMA-SEATS program in a
        subprocess (`tsa/x13.py:96`), which the guest cannot start and does not carry: it raises
        `X13NotFoundError` (`tsa/x13.py:107`, READ);
      - `statsmodels.graphics.functional.hdrboxplot` maps over `multiprocessing.Pool()`
        (`graphics/functional.py:461`, READ): in today's guest `from multiprocessing import
        Pool` imports and `Pool(2)` raises `AttributeError: module 'os' has no attribute
        'pipe'` (EXECUTED). The build records what `hdrboxplot` raises;
      - the thirteen left-out datasets (Decision 9).
    - **seaborn** (042): `regplot(lowess=True)`, `logistic=True` and `robust=True` work once
      this lands; 042's README line changes to say so.

12. **The checks**, each seen failing first.
    - **The oracle.** `tests/jobs/oracle/pyproject.toml` gains `statsmodels==0.15.0` (on macOS
      arm64 the `macosx_11_0_arm64` cp315 wheel, SHA-256 `24b9917a…8606`, READ),
      `formulaic==1.2.2`, `interface-meta==2.0.1`, and wrapt by URL to the same pure wheel as the
      guest (`[tool.uv.sources]`, as 039 pins charset-normalizer's pure wheel), so both run the
      same wrapt code. The oracle's statsmodels reads its datasets from disk, unpatched; the
      patch changes no value (EXECUTED: the 29 digests). `uv.lock` records them.
    - **The recording platform:** darwin-arm64 (037's rule; OLS and ARIMA reach LAPACK).
    - **How values are printed:** 037's rules (`.9g` direct, `.6g` iterative, tight
      tolerances: `tol=1e-12` for Newton and IRLS, `gtol`, `xtol` and `ftol` 1e-12 with
      `maxiter=1000` for ARIMA's optimiser); the regression summary's coefficient table printed
      as its text (`summary().tables[1].as_text()`, four decimals), never the whole summary,
      whose first table holds the date and time.
    - **Golden job (v1.3), `tests/jobs/statistical_models.py`** (not `statistics.py`, which would
      shadow the standard library's module on the job's path), in `JOBS`, its golden written by
      `regen.py`. As drafted and run (EXECUTED natively under hash seeds 0 and 1, equal; from
      the zip model with the patch and the leave-outs, equal to native byte for byte): the
      versions line (statsmodels, scipy, numpy, pandas, patsy, formulaic, interface-meta,
      wrapt); longley's shape and columns; OLS on longley (params, standard errors, R² and
      adjusted, F and its p-value, AIC, BIC, condition number, confidence intervals, t and p
      values, Durbin-Watson, the coefficient table's text, HC1 standard errors); the same
      formula fitted with patsy and with formulaic, the engine named and the params equal; a
      type-2 ANOVA; a Logit on anes96 by Newton; a Poisson GLM on randhie by IRLS; a two-sample
      t-test on seeded draws; Benjamini-Hochberg; ARIMA(1,0,1) on the Nile (params, AIC, a
      three-step forecast) and the same model filtered at fixed parameters (log-likelihood and
      forecast, direct); the augmented Dickey-Fuller test, ACF and PACF on sunspots; STL on the
      monthly CO2 series; simple exponential smoothing at a fixed level; LOWESS; a univariate
      KDE.
    - **Behaviour (v1.3, `tests/checks/test_v1_3_default_profile.py`), each on both binaries
      with nothing writable:**
      - `test_statsmodels_reads_its_datasets_from_the_zip[plain, snapshot]`: each of the sixteen
        public-domain datasets loads with native's shape (the shapes written in the check).
      - `test_left_out_datasets_say_so[plain]`: each of the thirteen raises `FileNotFoundError`
        naming its file; `import statsmodels.api` works.
      - `test_formula_engines_run_pure[plain, snapshot]`: `wrapt.__wrapt__._using_c_extension` is
        `False`; for a small frame, `formulaic.model_matrix("y ~ x + C(g)", frame)` and patsy's
        `dmatrices` give the same column names and, column by column, the same values (their
        column orders differ: formulaic puts `x` before the dummies; EXECUTED natively).
      - `test_statsmodels_says_what_it_lacks[plain]`: `x13_arima_analysis` raises
        `X13NotFoundError`; `get_rdataset("iris")` and `hdrboxplot` raise the exceptions the
        build recorded, each inside the fuel limit.
      - `test_statsmodels_modules_are_builtin[plain, snapshot]`: each of the 26 imports and is
        built in, the four renamed among them.
    - **Rules and artifact checks (judge changes, under `--accept-judge`):** v1.1,
      `test_left_out_dataset_files_are_not_in_the_zip` (none of Decision 9's 20 names and no
      member under a `datasets/*/src/` folder); v1.5, `SOURCE_PATTERNS` and
      `needs.SOURCE_COMPONENTS` gain `statsmodels`, the tree count rises by one, the patched-tree
      check covers the patch; rules, `patch_errors` on the patch and its draft;
      `paths.PACKAGES` and `LICENCE_COMPONENTS` gain the four; 033's metadata check gains the
      four.
    - **Build-time gates:** the version gate (Decision 3), the include log (Decision 5), the
      module count, step 60's detector.
    - **Unit checks:** `test_a_left_out_name_must_match_one_member` (042's `left_out` with an
      exact name: the member goes; a name matching nothing is named; a name that is a folder
      prefix without `/` matches only that exact member); the stand-in's `get_version` on a
      small `PKG-INFO` (the version; a file without one named); `gen_inittab.py`'s four renames.

13. **Licences** (§4.12). statsmodels, formulaic, interface-meta (approved as MIT) and wrapt
    (BSD-2-Clause) are approved by decision 43. Question 83 asks the owner to approve what
    statsmodels bundles by name, and the build waits for the answer.
    - `LICENSES/statsmodels.txt`: `LICENSE.txt` (BSD-3-Clause), `COPYRIGHTS.txt` (the code
      statsmodels took from numpy, scipy, pandas, matplotlib, scikit-learn and qsturng-py, each
      BSD or MIT, with their notices), `statsmodels/multivariate/factor_rotation/LICENSE.txt`
      and `statsmodels/stats/libqsturng/LICENSE.txt` (both BSD-3-Clause), each labelled with its
      path; then a part listing the sixteen datasets shipped with each one's `COPYRIGHT` line.
    - formulaic's, interface-meta's and wrapt's notices from their wheels by the existing
      `wheel_licences` (each has `licenses/LICENSE` in its `.dist-info`, READ).
    - `scripts/assemble_artifacts.py`: `PACKAGES` gains the four, `WHEELS` the three.

14. **What the set costs.** The base is main when the builder starts (044 moves it last). This
    specification's own growth, each measured and recorded in the landing notes:

    | metric | expected | finding if outside |
    |---|---|---|
    | `python.wasm` bytes | about +3.9 MB (INFERRED: Pyodide 314.0.7's statsmodels `.so`, 4.24 MB, times 0.92) | +2.5 to +5.5 MB |
    | the zip's members | +589 (503 statsmodels with its `METADATA`, 86 for the three wheels; EXECUTED) | any other count without a named reason |
    | the zip's bytes | about +4.12 MB (3,775,184 + 349,174, EXECUTED) | ≤ +4.5 MB |
    | plain `-c pass` | +589 × 26,900 ≈ +15.8 M, plus 26 inittab entries, measured | ≤ +589 × 30,000 = +17.7 M, plus the named rest |
    | snapshot `-c pass` | +589 × 2,399 ≈ +1.4 M | ≤ +589 × 3,500 = +2.1 M |
    | 033's metadata check, 035's comparison | four more distributions: ≤ 25 M each per read | above it |
    | every existing golden job | the plain-start growth only | more |

    The wheel's growth is recorded against PyPI's limit (question 64).

15. **Ordering, and one builder.**
    - **Right after 044**, whose staging, step pattern and `--modules-only` this reuses; after
      038, 039, 042 and 023 through it. If 044 stalls (AGENTS.md rule 7), this may build first
      and brings `stage_scipy_cimports.sh` and `--modules-only` itself, as 044's Decisions 4 and
      5 describe them.
    - **046 (lxml) and 047 (regex)**, drafted alongside: no dependency either way (question 82
      asks whether they build before scipy). If one is still unbuilt when this is confirmed,
      whichever is confirmed first builds first, and the second rebases onto the other's steps
      60 and 70, `gen_inittab.py`, `00_download.sh`, `make_stdlib_zip.py` and
      `assemble_artifacts.py`.
    - **042's README line** on statsmodels-backed fits changes with this one.
    - **Not split.** One package and three small wheels through one seam. One builder, in three
      stages, each green before the next: (1) the pins, the patch and its facts sheet, the
      stand-in and `meson setup` with the version gate; (2) `ninja`, the renames, step 60, the
      leave-outs and step 70, with the zip's names checked against Decision 9; (3) the oracle,
      the job, the checks, the README and the account.

## Intent

An agent's code in the default profile fits regressions, generalised linear and discrete
models, runs statistical tests and models time series with statsmodels, writes its formulas in
patsy's or formulaic's syntax, and loads statsmodels' public-domain example datasets, with
native statsmodels' answers, inside the same sealed Python. One recorded, temporary patch lets
the datasets load from the zip; no data with unapproved terms ships.

## Design

| file | change |
|---|---|
| `downloads/SHA256SUMS`, `scripts/00_download.sh` | the four pins (Decision 2) |
| `scripts/steps/59_statsmodels.sh` | new: unpack, patch, stage cimports, render the map, configure with the stand-in, the version gate, build, the include log, stage the package, the module list (Decisions 3 to 5) |
| `recipes/statsmodels_build/setuptools_scm.py` | new: the configure-time stand-in (Decision 3) |
| `recipes/wasi-statsmodels.cross` | new (Decision 4) |
| `recipes/statsmodels_file_includes.txt`, `recipes/statsmodels-renames/*.h` | new: four entries, four one-line headers (Decision 5) |
| `recipes/patches/statsmodels-0.15.0/0001-datasets-from-a-zip.patch` | new: `../upstream/11-statsmodels-datasets-from-a-zip/fix.patch`, byte for byte (Decision 7) |
| `context/upstream/patches/statsmodels-0.15.0/0001-datasets-from-a-zip.md` | moved from `../upstream/11-…/pr.md`, unchanged |
| `context/upstream/README.md`, `context/upstream/11-…/notes.md` | the row says the patch is carried; `fix.patch` removed from the folder |
| `scripts/make_stdlib_zip.py` | `--leave-out` takes an exact member name (Decision 9) |
| `scripts/gen_inittab.py`, `scripts/steps/60_link.sh` | statsmodels' modules, four renames (Decisions 5, 8) |
| `scripts/steps/70_zip.sh` | the tree, its metadata, three wheels, 35 leave-outs (Decisions 6, 9, 10) |
| `scripts/build.sh`, `scripts/assemble_artifacts.py`, `LICENSES/` | step 59 in `ALL`; `PACKAGES`, `WHEELS`; `LICENSES/statsmodels.txt` (Decision 13) |
| `tests/jobs/statistical_models.py`, `.expected`; `tests/jobs/oracle/pyproject.toml`, `uv.lock`; `tests/harness/jobs.py` | the golden, the oracle's pins, `JOBS`, the recording platform (Decision 12) |
| `tests/checks/test_v1_3_default_profile.py` | the five behaviour checks |
| `tests/checks/test_v1_1_artifact_set.py`, `tests/harness/paths.py`, `pins.py`, `needs.py`, `tests/checks/test_v1_3_data_stack.py` | the judge changes (Decision 12) |
| `tests/unit/test_build_scripts.py` | the three unit checks |
| `.github/workflows/release.yml` | the tree count, one more |
| `README.md`, `CHANGELOG.md` | statsmodels and its formula engines in "What the default profile carries"; the datasets shipped and left out; the absences; seaborn's statsmodels fits; the patch by path |

## Scope

In: Decisions 1 to 15. Out:

- **The thirteen datasets' files,** unless the owner approves their terms (question 83).
- **X-13ARIMA-SEATS,** a separate Fortran program run as a subprocess.
- **statsmodels' own test suite under the runtime** (roadmap milestone 6).
- **Pre-importing statsmodels in the snapshot.** The landing notes record `import
  statsmodels.api`'s fuel on both binaries, and the snapshot's bytes and `pass` fuel if it
  pre-imported it.
- **Trimming** Tempita templates or HTML templates from the zip.

## Acceptance criteria

1. **The checks exist and were seen failing first** on the set the builder starts from (044
   landed), each recorded in the landing notes: the golden and the five behaviour checks with
   `ModuleNotFoundError: No module named 'statsmodels'`; the dataset check and the golden again
   on a build without the patch (`NotADirectoryError`), run once; the left-out check against a
   zip built without the leave-outs; `meson setup` without the stand-in (it fails in the version
   script); the unit checks before their code.
2. **The build** went through Decision 15's stages. A full build from pins in a clean clone
   applies the patch with no offset, passes the version gate, the include log, the module count
   and step 60's detector, leaves out exactly Decision 9's members, and makes a set whose
   binaries run the golden and the checks. `MANIFEST` names the four pins, the recipes, the
   scripts and the patch.
3. **The same bytes everywhere:** a manual run of the release workflow on the reviewed commit
   passes its `rebuild`, `same-bytes` and zero-patch jobs with the new tree count; its run
   number goes in the landing notes.
4. **The judge:** `uv run pytest` is green with `--accept`, `--accept-judge` and
   `--accept-growth` (Decision 14's account, each row measured against its bound), and loses no
   pass. `regen.py --check` reproduces every golden.
5. **The numbers recorded:** the three binaries', the zip's and the wheel's bytes; the zip's
   members; the modules linked and the final rename set; plain and snapshot `-c pass`; `import
   statsmodels.api` and the golden's fuel on both binaries; the snapshot's bytes and `pass` fuel
   if it pre-imported statsmodels; the exceptions `get_rdataset` and `hdrboxplot` raise.
6. **The release:** a release dry run passes every job (criterion 3's run).

## The owner's choices

None open here. One is recorded in `../questions-for-the-owner.md` as **83**, shared with spec
044: the terms of what statsmodels bundles (the code named in `COPYRIGHTS.txt`, two folders with
their own BSD licences, and its datasets), with the thirteen datasets left out until the owner
says otherwise. This specification is drafted and can be reviewed; it is not built until 83 is
answered.

## Landing notes

Not built.
