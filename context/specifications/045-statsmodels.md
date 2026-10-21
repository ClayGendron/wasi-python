# 045 — statsmodels, with formulaic, interface-meta and wrapt

- **Status:** **landed 2026-10-21 in wave 10** (045, 110, 111, and the lane's oracle-lock check) on main `b2d4ccd0`: accepted on `81155492`, history line 92, 802/889 pass, 0 fail, on a set rebuilt from the same pins in the main tree (`SHA256SUMS` `d0d91cef`, equal to CI's; the wheel 98,259,192 bytes); the integration review `../reviews/wave-10-integration-2026-10-21.md` and the lane's addendum. Before: **Built, reviewed, rebased for wave 10** (2026-10-21): on wave 09's tip `265607bd`,
  6 hunks named, rebuilt from an empty `build/`, set `SHA256SUMS` `d0d91cef`, the wheel 98,251,487
  bytes (under 100 MB); the fast tier 0 fail (growth only); no new release run (no hunk changes
  code). Built first on `dbecd2d` (set `14adfa5f`; release run 39533679276 on `7be1837`, red on
  growth on macOS and on two Windows failures the base had too). Build review
  `../reviews/045-statsmodels-build-2026-10-20.md`: "lands once Finding 1 is written in"; its
  Disposition answers all three findings. Two findings against Decision 14 are measured and
  explained in *For the lane*: `python.wasm` +6.87 MB (the bound's ratio was numpy's) and
  seaborn's job (+29.0 M on this base; metadata walks and the longer inittab). The confirming pre-build review
  (`../reviews/045-statsmodels-prebuild-confirm-2026-10-20.md`) said "build once M1 is answered";
  its Disposition answers it. Begun on `spec/045-statsmodels` from main `5805af0`, revised against main in *The builder's revision against main* (R1 to R12, written before any code; Decisions 3, 9, 12 and 13 move there, and where a Decision's text below says otherwise, the revision governs); its confirmation round is R12. Questions 80 and 83 are answered (`../decisions.md`). **Spec 051's callback scan binds this build** (051, Decision 4a; written in when 051 landed): `test_callbacks_have_the_types_cpython_calls` is green, and a mismatch it finds is fixed by a carried patch or an upstream release, never by an exclusion. **Spec 096's slot scan binds this build too** (the confirming review's L2): spec 096's slot scan is green, and a mismatch it finds is fixed by a carried patch or an upstream release, never by an exclusion. drafted 2026-10-18; revised the same day against its pre-build review
  (`../reviews/044-scikit-learn-and-045-statsmodels-spec-2026-10-18.md`): every finding that
  concerns it is fixed here, and the review's Disposition says where. It changes the build
  recipe and the artifact set, so it is reviewed before it is built (constitution §5.6). It is build-class: it touches
  `scripts/`, `recipes/`, `downloads/SHA256SUMS` and the release workflow (§5.7). It carries one
  upstream patch (§4.1). It is not built until the owner answers question 83 (the terms of what
  statsmodels bundles, its datasets above all); everything else is decided here.
- **Owner:** Clay Gendron
- **Kind:** the build recipe (four pins; a new step 59; `scripts/make_stdlib_zip.py`'s
  `--drop` widened to one exact member (revised: R3); `scripts/gen_inittab.py`'s rename table;
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
  joblib), 042 (no longer: R1, R3), 023 (`packaging` 26.3, which statsmodels requires at run time
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
   - **statsmodels 0.15.0:** its 26 extension modules as builtins, and its Python package (501
     members, 3,774,712 bytes as step 70 packs them, plus one `METADATA`; Decisions 9 and 10).
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
   - (revised: R2, spec 023's `recipes/setuptools_scm_stand_in/` gains this function; no new folder) **`recipes/statsmodels_build/setuptools_scm.py`**, ours: `get_version(root)` returns the
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
   `entry_points.txt`, and none reads a file by path or queries entry points at import (READ:
   `grep` for `__file__`, `importlib.resources` and `entry_points`; wrapt's
   `importer.discover_post_import_hooks` calls `importlib.metadata.entry_points`, but only when
   a program calls it). What a guest sees: `wrapt.__wrapt__._using_c_extension`
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
   - **The change** (2 files, +41 −6, 2,979 bytes, SHA-256
     `751e719065100f7b1373b663c9e1b4b9ebdae0a68aa3b31d1f1b8c34d5e8db58`, applies to the pinned
     sdist with `git apply` and no offset, EXECUTED): a new **private** helper,
     `statsmodels.datasets.utils._open_data_file(base_file, file_name)`, returns the data file
     beside `base_file` opened in binary mode: from disk when it is a file there, as today; when
     `base_file`'s folder lies under `statsmodels/datasets/` and the file is not on disk, as a
     package resource, `importlib.resources.files("statsmodels.datasets.<name>")`, the package
     found from that folder relative to `utils.py`'s; and otherwise from disk as before, so a
     missing file beside a user's own module still raises `FileNotFoundError` (EXECUTED: stock,
     and patched from the zip and on disk; the first draft, `a83b56a1…dd58`, fell back for every
     path and raised `ValueError` there, the review's finding 7). Being private, it adds no
     public API, so statsmodels' rule that a public function needs a docs entry does not
     apply; its numpydoc docstring's summary line ends with a period. `load_csv` and
     `elec_equip`'s loader read through it; `elec_equip`'s now unused `Path` import goes. `ruff
     check` passes on both files (EXECUTED).
   - **What it changes, measured** (EXECUTED): with the patch, all 29 datasets load from the zip
     and from disk, and each frame's digest equals the stock package's on disk; the golden job
     from the zip model prints native's output byte for byte.
   - **Why a patch and not a recipe** (041's reasoning, Decision 1 as revised there). §4.1
     prefers a recipe, a stand-in module included, and a recipe under `recipes/`, hashed in
     `MANIFEST` and reviewed, is a recorded change. So a recipe was looked for first:
     - **The CSVs as real files where `load_csv` looks.** The path lies inside the zip's own file
       name; no folder can exist there, and a preopen at that path is refused by the runner as
       the runtime's own folder (041's review, EXECUTED there).
     - **A run-time replacement could work here, unlike scikit-learn's case,** because the read
       runs when a loader is called, not at import. It is rejected on the other grounds 041
       gives: it would replace a public function, `load_csv`, and `elec_equip`'s private
       `_get_data`, with copies of upstream's code, which is wider than the patch; spec 020's tree
       check would not see it; and no upstream release would ever let it be deleted.

     A carried patch is the smallest change, checked against the tarball, and deleted once a
     pinned release carries the fix.
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
     break `import statsmodels.api`.
   - **And one table with no stated terms:** `statsmodels/sandbox/rlsdata.txt`, a 50-line table
     of a regression data set, which nothing in the package reads (EXECUTED by the review: `grep`)
     and which states no terms, the same class as cancer and heart (the review's finding 9).
   - 53 members in all leave: 36 arguments, 21 file names and 15 folders (EXECUTED: every
     argument matched a member).
   - **How it shows:** a left-out dataset's `load()` and `load_pandas()` raise
     `FileNotFoundError` (EXECUTED in the zip model, through CPython's `zipfile.Path`: `spector`
     → `FileNotFoundError: …/statsmodels/datasets/spector/spector.csv`, while `import
     statsmodels.api` and `longley` work). The message is the resource reader's, and spec 035
     replaces that reader (its `ZipDirectoryPath.open` raises `FileNotFoundError` for a missing
     name, Decision 6 there, and promises nothing about the message). So the check asserts the
     type only, and the landing notes record the message the built guest gives (the review's
     finding 8). The README lists the thirteen.
   - (revised: R3, 13 `--keep` and 9 `--drop` lines with `--drop` widened to one exact member; no new option) **A separate option, `--leave-out-file NAME`, so 042's rule and its check stay** (the
     review's finding 5, its option (a)). 042's `--leave-out PREFIX` takes folder prefixes ending
     in `/`, stops on one without it, and `test_a_left_out_folder_is_not_packed` pins that
     stop; neither changes. The new option is repeatable; its argument must equal one member's
     name **as its input gives it, before `.py` becomes `.pyc`** (so `x.py`, never `x.pyc`), and
     the build stops naming any argument that matches nothing, through the same `matched` record
     042's `left_out` keeps. Step 70 gains 15 `--leave-out` lines (the `src/` folders) and 21
     `--leave-out-file` lines, generated by no script: they are written out in `70_zip.sh`, so
     the review reads each.
   - Question 83 asks the owner whether to approve any of the thirteen; the agent recommends
     keeping them out. The golden job uses public-domain datasets only.

10. **The zip.** Step 70 gains `--tree "$B/statsmodels-install"`, `--metadata
    "$B/statsmodels-0.15.0/PKG-INFO"` (`Name: statsmodels`, `Version: 0.15.0`, READ), the three
    `--wheel` lines and Decision 9's leave-outs. What stays that is not code (EXECUTED by the
    drafting run's recount after the review's finding 9, step 70's rules with the 36
    leave-outs): the sixteen public-domain datasets' CSV files, `macrodata/macrodata.dta`, the
    R scripts beside public-domain sets (`longley/R_gls.s`, `R_lm.s`, `stackloss/R_stackloss.s`,
    `sunspots/R_sunspots.s`, `sunspots/arima_mod.R`), `stats/libqsturng/CH.r`, the licence texts
    (`factor_rotation/LICENSE.txt` and `COPYRIGHTS.txt`, `libqsturng/LICENSE.txt`), two notes in
    `sandbox/` (`tools/TODO.txt`, `stats/notes_fdr.txt`), `pyproject.toml`, and 20 templates
    (19 `*.pyx.in` and `_blas_int.pxi.in`) an install also carries. Every `.html` and `.dat`
    file the package has is under a `datasets/*/src/` folder and leaves with it (the first
    draft said otherwise). No trimming here.

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
      - `sm.datasets.get_rdataset` and `sm.datasets.webuse` download (no network). With the
        default `cache=False` they go straight to `urlopen`, and an `https` URL raises `URLError:
        unknown url type: https` in today's guest (EXECUTED by the review). With `cache=True`
        they first make a cache folder under `~/statsmodels_data`, which with no root fails as
        044's fetchers do (`FileNotFoundError` on `'~'`) and with a root is made under the
        runner's `/tmp` `HOME` before the same `URLError` (044, Decision 9; INFERRED for
        statsmodels from the same `expanduser` and `makedirs`). The check names its grant
        configuration (none) and records what is raised; the README states both cases;
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
        (the type only, Decision 9); `import statsmodels.api` works.
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
      `test_left_out_dataset_files_are_not_in_the_zip` (none of Decision 9's 21 file names and
      no member under a `datasets/*/src/` folder); v1.5, `SOURCE_PATTERNS` and
      `needs.SOURCE_COMPONENTS` gain `statsmodels`, the tree count rises by one, the patched-tree
      check covers the patch; rules, `patch_errors` on the patch and its draft;
      `paths.PACKAGES` and `LICENCE_COMPONENTS` gain the four; 033's metadata check gains the
      four.
    - **Build-time gates:** the version gate (Decision 3), the include log (Decision 5), the
      module count, step 60's detector, and 044's weak-duplicate gate and link-map check
      (044, Decision 6), which run over every package's archives and so cover statsmodels'.
    - (revised: R2 to R4, five unit checks in `tests/unit/test_statsmodels_build.py`: the stand-in twice, `test_a_drop_takes_one_file_by_its_exact_name`, `test_a_kept_dataset_folder_keeps_only_its_code`, the four renames) **Unit checks:** `test_a_left_out_file_must_match_one_member` (`--leave-out-file`: the
      named member goes and nothing else, not even a member that merely starts with the name;
      a name matching nothing is named; `x.pyc` does not match the member that comes from
      `x.py`); 042's `test_a_left_out_folder_is_not_packed` unchanged; the stand-in's `get_version` on a
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
    | the zip's members | +588 (502 statsmodels with its `METADATA`, 86 for the three wheels; EXECUTED) | any other count without a named reason |
    | the zip's bytes | about +4.12 MB (3,774,712 + 349,174, EXECUTED) | ≤ +4.5 MB |
    | plain `-c pass` | +588 × 26,900 ≈ +15.8 M, plus 26 inittab entries, measured | ≤ +588 × 30,000 = +17.6 M, plus the named rest |
    | snapshot `-c pass` | +588 × 2,399 ≈ +1.4 M | ≤ +588 × 3,500 = +2.1 M |
    | 033's metadata check, 035's comparison | four more distributions: ≤ 25 M each per read | above it |
    | 042's `statistical_plots` job and any check that imports seaborn | the plain-start growth plus `import statsmodels`, measured: seaborn's `regression.py:10-15` tries `import statsmodels` when seaborn is imported (READ by the review), and `statsmodels/__init__.py` imports only `_version` | more than the plain-start row plus 2 M |
    | every other existing golden job | the plain-start growth only | more |

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
| `recipes/setuptools_scm_stand_in/setuptools_scm/` | spec 023's stand-in gains `get_version(root)`; `__main__` calls it (Decision 3, revised: R2) |
| `recipes/wasi-statsmodels.cross` | new (Decision 4) |
| `recipes/statsmodels_file_includes.txt`, `recipes/statsmodels-renames/*.h` | new: four entries, four one-line headers (Decision 5) |
| `recipes/patches/statsmodels-0.15.0/0001-datasets-from-a-zip.patch` | new: `../upstream/11-statsmodels-datasets-from-a-zip/fix.patch`, byte for byte (Decision 7) |
| `context/upstream/patches/statsmodels-0.15.0/0001-datasets-from-a-zip.md` | moved from `../upstream/11-…/pr.md`, unchanged |
| `context/upstream/README.md`, `context/upstream/11-…/notes.md` | the row says the patch is carried; `fix.patch` removed from the folder |
| `scripts/make_stdlib_zip.py` | `--drop` also matches one member by its exact name (Decision 9, revised: R3; no new option) |
| `scripts/gen_inittab.py`, `scripts/steps/60_link.sh` | statsmodels' modules, four renames (Decisions 5, 8) |
| `scripts/steps/70_zip.sh` | the tree, its metadata, three wheels, 13 `--keep` and 9 `--drop` lines (Decisions 6, 9, 10; R3) |
| `scripts/build.sh`, `scripts/assemble_artifacts.py`, `LICENSES/` | step 59 in `ALL`; `PACKAGES`, `WHEELS`; `LICENSES/statsmodels.txt` (Decision 13) |
| `tests/jobs/statistical_models.py`, `.expected`; `tests/jobs/oracle/pyproject.toml`, `uv.lock`; `tests/harness/jobs.py` | the golden, the oracle's pins, `JOBS`, the recording platform (Decision 12) |
| `tests/checks/test_v1_3_default_profile.py` | the golden and six behaviour checks (revised: R4, `hdrboxplot` apart) |
| `tests/checks/test_v1_1_artifact_set.py`, `tests/harness/paths.py`, `pins.py`, `needs.py`, `tests/checks/test_v1_3_data_stack.py` | the judge changes (Decision 12) |
| `tests/unit/test_statsmodels_build.py` | five unit checks (revised: R2 to R4) |
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
   if it pre-imported statsmodels; the exceptions `get_rdataset` and `hdrboxplot` raise; the
   message a left-out dataset's `FileNotFoundError` carries under 035's reader; `statistical_plots`'
   fuel before and after (the seaborn row); and **which answer question 80 had** when this
   landed, as 041's condition C1 asks, with the facts sheet in that answer's form.
6. **The release:** a release dry run passes every job (criterion 3's run).

## The owner's choices

None open here. One is recorded in `../questions-for-the-owner.md` as **83**, shared with spec
044: the terms of what statsmodels bundles (the code named in `COPYRIGHTS.txt`, two folders with
their own BSD licences, and its datasets), each part decided here as recommended: the thirteen
datasets' files and `sandbox/rlsdata.txt` left out until the owner says otherwise. This
specification is not built until 83 is answered.

## The builder's revision against main (2026-10-20)

The builder is a fresh agent, not the author. It works on `spec/045-statsmodels` in its own
worktree, made from main `5805af0` (wave 07 landed: 038 and 044). This specification was drafted
on 2026-10-18. Since then 037, 038, 039, 041, 043, 044 and 086 have landed, and 042 (seaborn) is in
wave 08, not yet on main. Each change below was read against main, written here, and only then
coded. Nothing has been built yet; the native slot is the lane's to grant. Every claim is EXECUTED
unless marked.

**R1. What this builds on.** Main holds what Decision 15 waited for: 044's
`scripts/stage_scipy_cimports.sh`, `install_from_plan.py --modules-only` and step 58; 037's and
038's scipy with `cython_blas` and `cython_lapack` as builtins; 039's patsy 1.0.3, narwhals 2.27.1,
typing-extensions 4.16.0 and joblib 1.6.0; 023's packaging 26.3. 042 is not on main. This
specification therefore no longer depends on it, except for its README line on seaborn's
statsmodels fits (Decision 11). The builder writes that line when it rebases onto a wave that
holds 042. 045 enters wave 09 or 10, as the lane orders (the owner put it in 0.1.0 on 2026-10-20,
`../decisions.md`).

**R2. Decision 3: the stand-in already exists.** Spec 023 put a configure-time stand-in for
matplotlib in `recipes/setuptools_scm_stand_in/setuptools_scm/`. Its `__main__` prints PKG-INFO's
`Version:` for `python3 -m setuptools_scm`. statsmodels' `git_version.py` instead calls
`setuptools_scm.get_version(root=ROOT)` (READ, the sdist). So the existing package gains
`get_version(root)` in its `__init__.py`: the `Version:` header of `root/PKG-INFO`, with any other
case stopping the build in one line that names the file. `__main__` now calls `get_version(".")`
and prints the same answer as before. There is no `recipes/statsmodels_build/` folder; one
stand-in serves both packages (§6.4). Unit checks:
`test_the_stand_in_reads_the_version_from_pkg_info` (seen failing: `AttributeError: module
'setuptools_scm' has no attribute 'get_version'`) and
`test_the_stand_in_still_prints_the_version_for_matplotlib`. The second passed before the change
and after it; it guards matplotlib's use. Step 59 puts the stand-in's folder and the pinned
packaging wheel on `PYTHONPATH` for `meson setup` alone. The version gate stands as written.

**R3. Decision 9: `--keep` and `--drop`, not a new option.** 042's `--leave-out` never landed:
042 leaves its files out with 023's `--drop`, as 044 did (044's B2). So the reason for a separate
`--leave-out-file` (to keep 042's rule and its check intact) is gone, and the smallest form uses
what main has:
- **13 `--keep statsmodels/datasets/<name>=__init__.py,data.py` lines**, one per dataset whose
  terms are not approved. 023's `--keep` drops every member under the folder except the files it
  names. Each such folder keeps its two modules, which `statsmodels.datasets` imports, and loses
  its CSVs, R scripts and `src/` folder. A name it does not find stops the build, as before.
- **8 `--drop statsmodels/datasets/<name>/src` lines** for the public-domain sets that have a
  `src/` folder (anes96, co2, elnino, grunfeld, macrodata, modechoice, randhie, sunspots).
- **One `--drop statsmodels/sandbox/rlsdata.txt`.** `--drop` now also matches the one member
  whose name equals its argument, the name as its input gives it, before `.py` becomes `.pyc`.
  A folder's drop is unchanged, and so is the stop on an argument that matches nothing. No
  existing check pins `--drop`'s old reach (READ: no unit or rules check calls `Selection` or
  passes `--drop`).

The effect is Decision 9's exactly: 554 tree members, 501 kept, 53 left out (EXECUTED with step 70's
own `tree_members` and `Selection` on the patched sdist, over the lines `70_zip.sh` holds). Unit
checks: `test_a_drop_takes_one_file_by_its_exact_name` (the exact member goes; `rlsdata.txt.bak`,
`rlsdata.txt2` and `rls.py` stay; a folder's drop still works; `api.pyc` does not match the member
from `api.py`, and its unmatched argument stops the build). It was seen failing: `assert not
True`, since the old `--drop` kept the file. `test_a_kept_dataset_folder_keeps_only_its_code`
guards the existing `--keep` in the form step 70 now uses. 042's
`test_a_left_out_folder_is_not_packed` does not exist on main, so the review's finding 5 has no
check left to protect. Its intent holds: no existing check changes.

After wave 08 (042) lands, its `test_a_left_out_folder_is_not_packed` pins `--drop`'s folder form,
and it passes under the widened rule. The confirming review EXECUTED it on the branch's
`make_stdlib_zip.py`, and its three "matches nothing" cases, `pkg/gone`, `pkg/su` and
`pkg/sub/mod.pyc`, still stop. Old and new rules take the same members over the matplotlib,
scikit-learn, reportlab and statsmodels inputs for every drop main and wave 08 carry. The builder
re-runs that check by node id after the rebase, and reads the make_stdlib_zip docstring and 042's
check docstring together. (The confirming review's L1.)

**R4. Decision 12: the checks as written, with four changes.**
- **`hdrboxplot` gets a check of its own, `test_hdrboxplot_needs_processes`.** It creates a
  matplotlib figure before it reaches `Pool()` (`graphics/functional.py`, READ:
  `utils.create_mpl_ax` first). So it needs matplotlib's data, granted as the runner grants it,
  and a writable config folder (`MPL_ENV`, the judge's root), unlike the no-grant check.
  `test_statsmodels_says_what_it_lacks` keeps `x13_arima_analysis` and `get_rdataset("iris")`
  through `wasi_python.run` with no root and no grant, as 044's check does. Each check's expected
  exception is the drafting run's; the build records what the guest gives, and the check states
  that.
- **`test_left_out_datasets_say_so`** runs on the plain binary, as written. It loads each of the
  thirteen and expects `FileNotFoundError`, the type only. Natively, with the files present, all
  thirteen load (EXECUTED under the oracle). So the check has no native twin; the absence is this
  build's own.
- **Judge changes the text did not list** (044's B6, applied here): `scan.MESON_BUILDS` gains
  `statsmodels-build` (spec 059's rule for a new meson build). The dotted-builtins program in
  `test_v1_1_artifact_set` gives `statsmodels` a run of its own, as scipy and sklearn have; its 26
  modules are `test_statsmodels_modules_are_builtin`. The notice check reads the pinned sdist, so
  it joins the release's build shard by node id. `paths.LICENCE_COMPONENTS` gains the four.
  `tests/upstream/packages.toml` gains four entries (R6). `test_build_progress`'s step list and
  `test_artifact_rules`' synthetic set gain step 59 and the four packages.
  `shards.COMPONENT_NAMES` needs nothing: the tree's component, `statsmodels`, is the package's
  name.
- **The C-only cross file** is not in `scan.CPP_CROSS_FILES`. That list is for the cross files
  that compile C++, and statsmodels compiles none.

**R5. Decision 13: the notice sweep, done before the build, as 044's was (044's B1).** Every
shipped `.py`, `.pyx`, `.pxd`, `.pxi`, `.in`, `.c` and `.h` outside `tests/` was read for
"Copyright", "License", "public domain", "all rights reserved", GPL, and "adapted, derived, copied,
taken, borrowed, ported, translated or based on" (1,098 lines; `build/045/sweep.txt`, the builder's
scratch). Most lines are statsmodels' own SPDX-style headers ("License: BSD-3", "Simplified-BSD")
or citations of papers and manuals. Under COPYRIGHTS.txt's notices, which ship: `compat/numpy.py`
(numpy); `datasets/utils.py:318` and `sandbox/tools/cross_val.py` (scikit-learn);
`graphics/tsaplots.py` and `tools/docstring_helpers.py` (matplotlib);
`distributions/edgeworth.py`, `tsa/arima_process.py`, `tsa/filters/filtertools.py`,
`stats/robust_compare.py`, `miscmodels/nonlinls.py` and `tools/rootfinding.py` (scipy). Under the
two folder licences: `multivariate/factor_rotation/` ("ported and made available with permission
of the authors", BSD-3-Clause by Martin van der Schans) and `stats/libqsturng/` (Roger Lew,
BSD-3-Clause). **Six that question 83 does not name**, each now a part of
`LICENSES/statsmodels.txt`, and the owner is asked through the lane:
- `tools/parallel.py`, "copied from https://github.com/mne-tools/mne-python", Alexandre Gramfort,
  "License: Simplified BSD". MNE-Python's licence (BSD-3-Clause) is pinned as django's was for
  044: `https://raw.githubusercontent.com/mne-tools/mne-python/2c4a3b03968a29570f87c3d741d2adc53b35f1dc/LICENSE.txt`,
  the last commit to touch it, saved as `mne-python-2c4a3b03-LICENSE.txt`, SHA-256
  `adf6b228c93126d67e84c40ed7c1b1dbf1ec44f26d9fe224261e1d8592646b52`, 1,467 bytes.
- `tools/docstring.py`, "Substantially copied from NumpyDoc 1.0pre". It is covered by 044's
  pinned `numpydoc-894c8c47-LICENSE.txt`; no new pin.
- `stats/libqsturng/qsturng_.py`, lines 1926-1961: `_phi`, Peter John Acklam's inverse normal,
  "Modified from the author's original perl code … by dfield@yahoo-inc.com". The file says "the
  permissity of the license is not explicitly listed".
- `tsa/stl/_stl.pyx`, lines 3-13: Kevin Sheppard's port, "License: NCSA/BSD-3 Clause, Based on
  NETLIB STL code" (Cleveland, Cleveland, McRae and Terpenning). netlib states no terms. This
  file is compiled in.
- `graphics/boxplots.py`, lines 3-4: "Based on code by Flavio Coelho and Teemu Ikonen". No terms
  are named.
- `regression/quantile_regression.py`, lines 1-16: the IRLS function "written for Matlab by
  Shapour Mohammadi … with some lines based on code written by James P. Lesage … Translated to
  python with permission from original author".

The recommendation is to ship all six with their notices. Each is in every statsmodels wheel
under statsmodels' BSD-3-Clause. The judge's `test_statsmodels_notice_carries_its_bundled_parts`
holds every part against the pinned sdist's bytes, and the datasets part names the sixteen with
each module's own statement and the thirteen left out. EXECUTED: the notice step 90 would write
from the patched sdist passes the judge's rule with no finding. If the owner declines one, its
module is left out or replaced, by a revision before landing.

**R6. The packages' own tests (spec 063; the owner's rule, "every test of every package we
build").** statsmodels' suite natively, on the oracle's pinned wheels, one thread, darwin-arm64:
21,412 collected by `--co`; the full run's outcomes add up to 21,414: 20,911 passed, 1 failed, 356
skipped, 146 xfailed, in 468 s (the two counts differ by two; the confirming review's N1). The one
failure is `statsmodels/graphics/tests/test_tsaplots.py::test_plot_month`. Spec 095 states its
own run's total. In the guest that
is about 3 T of fuel (INFERRED: matplotlib's suite, of about the same native size, measured 3.35 T
in spec 066), caps of about 4.5 T, and about five more Linux shards. Running it uses spec 066's
harness (`package_drive.py`, `harness/packages.py`), which lands in wave 08. It also follows 066's
method: a survey, a confirmation round, classes and splits. The builder proposed to the lane that
statsmodels' suite closes with spec 095. 066's Decision 13 reserves 095 for "scipy's and
scikit-learn's own tests in the release (statsmodels' too if 045 adds an entry)". formulaic,
interface-meta and wrapt close with spec 067, as every other pure wheel does. `packages.toml`
says so, pending the lane's answer. No test is left out by this: the whole suite runs under 095.
**The owner's answer (2026-10-20, through the lane):** statsmodels' suite goes to spec 095, before
0.1.0; formulaic, interface-meta and wrapt go to 067. The committed `packages.toml` text stands,
and the roadmap's reserved line for 095 now names statsmodels (045) too (the confirming review's
N4).

**R7. Gates added since drafting, which bind this build.** 044's weak-duplicate gate and link-map
check run over every package's archives, statsmodels' included. 044's `gen_inittab.py --against`
stops on an init name CPython's own `config.c` registers (its B11); none of statsmodels' 26 names
is a CPython builtin's (INFERRED from the module list; the link shows it). 051's callback scan
and 096's slot scan read statsmodels' modules; a mismatch is fixed by a carried patch or an
upstream release, never an exclusion.

**R8. Counts that moved.** wasi-sdk 34 (086), not 33: the build's own logs are read, so nothing
here depends on the version. Step 59 is free on main and on every open branch (READ). The release
tree count is 27 (main's 26 plus `statsmodels`). There are 23 carried patches (main's 22 plus this
one, in its own folder), and `build.sh` runs twenty steps. On wave 08's base, which adds seaborn's
tree, the count is 28 (the confirming review's L1).

**R9. The cost table's base** (Decision 14) is main's set at `5805af0`, `SHA256SUMS` `dc6ba3a5`
(044's). 044 measured 27,240 fuel per member at a plain start, inside the table's 30,000.

**R10. The golden and the oracle.** `tests/jobs/statistical_models.py` is the drafted job, under
the line length rules. Under the pinned oracle, its output with hash seeds 0 and 1 is the
drafting run's byte for byte: 3,007 bytes, SHA-256 `6a855bc1…ad29`. `tests/jobs/oracle/uv.lock`
records statsmodels' `macosx_11_0_arm64` cp315 wheel (`24b9917a…8606`), formulaic and
interface-meta by version, and wrapt by URL to the guest's pure wheel (`c6e6c226…ac1d`).

**R11. Question 80** is answered: the facts sheet is one the owner rewrites. The sheet moved
unchanged to `../upstream/patches/statsmodels-0.15.0/0001-datasets-from-a-zip.md`, in that form,
and the patch byte for byte (`751e7190…db58`). It applies to the pinned sdist with no offset
(EXECUTED, `apply_patches.sh`).

**R5a. What each answer on R5 means, drafted now so either is a one-step write-in.** Approval
needs no further change: phase 1 already writes all six parts into `LICENSES/statsmodels.txt`
(`scripts/assemble_artifacts.py`, `STATSMODELS_LINES` and `STATSMODELS_PINNED`), and the judge holds
each part (`tests/harness/artifacts.py`, `STATSMODELS_PARTS`). A decline cannot simply leave a module
out. Here is what imports each one (READ, every shipped `.py` and `.pyx` outside `tests/`):
- `tools/docstring.py` is imported by `discrete_model`, `generalized_linear_model`, `ar_model`,
  `ardl`, `arima_process`, `descriptivestats`, `treatment_effects` and `forecasting/stl`.
- `graphics/boxplots.py` is imported by `graphics/api.py`.
- `regression/quantile_regression.py` is imported by `statsmodels/api.py` and `formula/api.py`.
- `tsa/stl/_stl` is imported by `tsa/seasonal/__init__.py` and `tsa/stl/mstl.py`.

Leaving out any of those four breaks `import statsmodels.api`. A replacement would be a rewrite of
upstream's code: a stand-in or a patch with no upstream exit, which §4.1 does not allow for this
purpose. So declining any of the four means leaving statsmodels out of the build. The other two
can each go alone:
- `tools/parallel.py` is imported only by `base/distributed_estimation.py`, at call time. Leaving
  it out (`--drop statsmodels/tools/parallel.py`) makes `DistributedModel.fit` raise
  `ModuleNotFoundError`, and the mne-python pin goes.
- `stats/libqsturng/` is imported in one place: `sandbox/stats/multicomp.py:78-89`, as a
  fallback when `scipy.stats.studentized_range` is missing (scipy older than 1.7). This build
  carries scipy 1.18.1, so statsmodels' own code never imports it. EXECUTED by the confirming
  review: with it blocked, `import statsmodels.api` and `pairwise_tukeyhsd` work. Leaving the
  folder out (`--drop statsmodels/stats/libqsturng`) costs only a user's direct `import
  statsmodels.stats.libqsturng` (`ModuleNotFoundError`). `_phi` lives inside `qsturng_.py`, so it
  cannot leave alone; its own comment names `scipy.stats.norm.isf` as an acceptable alternative.
  (Corrected by the confirming review's M1; the first text said Tukey's HSD would break.)

**The owner's answer (2026-10-20, through the lane): all six approved**, each with its notice in
`LICENSES/statsmodels.txt` as phase 1 writes it. Nothing ships differently from phase 1.

Each such leave-out would be one line in `70_zip.sh`, one part fewer in both lists, a v1.1 check
line and a README line. The builder writes them after the answer.

**R6a. `packages.toml` for each answer on R6.** If the answer is spec 095, the text is as
committed: `statsmodels` is `kind = "later"`, `closes_with = "spec 095"`. If the answer is "inside
045", then after wave 08 lands (066's harness) and 045 is rebased onto it, the entry becomes:

```toml
[package.statsmodels]
# Spec 045 runs its own suite (spec 066's design): the groups in tests/upstream/statsmodels.toml,
# driver = "package", the grant /upstream-statsmodels, each group's cap 1.5 times its measured fuel,
# a [[split]] for any file past the bound, and the groups in Linux shards (tests/release_shards.toml).
kind = "suite"
```

That path adds, in this order: a survey (066's Decision 1, about 90 minutes), its delta to a
confirmation round, `tests/upstream/statsmodels.toml` and `.ini` and `expected/` classes, about five
new Linux shards, and the statsmodels tarball as a CI input of those shards. formulaic,
interface-meta and wrapt stay `later` with spec 067 under either answer. Their wheels carry no
tests, and 067 pins their sdists as data, as it does for the rest of tier A.

**R12. The pre-build review's confirmation.** The 2026-10-20 confirmation covered 044 alone, and
says that findings 5 and 7 to 10 are not confirmed there. A confirming reviewer reads this
revision, R2 to R6 above all, before the build. The lane arranges it.

## Landing notes

### For the lane

**Rebased onto wave 09's tip `265607bd` (2026-10-21, for wave 10).** Main took wave 09 (100,
numpy on OpenBLAS; 097, host litter outside the home folder; 101). 045 goes first in wave 10. Every
number in this paragraph and its list is EXECUTED on this rebuild; the sections below keep the
`dbecd2d` build's numbers, and where they differ this list governs.

- **The rebase:** `git rebase 265607bd`, 34 commits since `dbecd2d`. It stopped four times, on
  **6 hunks in 2 files**. Each was resolved keeping both sides:
  - Phase 1 (`9d8baad`), `README.md`, the artifact table's `python.wasm` row: wave 09's "numpy
    and scipy (sharing one OpenBLAS)" with 045's "scikit-learn's and statsmodels' compiled
    modules".
  - Phase 1, `scripts/steps/60_link.sh`, two hunks: the header's list (wave 09's "scipy and numpy
    with one OpenBLAS", 045's statsmodels); and the staged-input checks (wave 09's
    `libnumpy_lapack_shims.a` line, then 045's step-59 line).
  - `7be1837` (the comment rewording), `60_link.sh`, the same place: wave 09's two lines kept,
    045's "# Step 59's modules." without the citation.
  - `3aa663a` and `78365a7`, `README.md`, the sizes row twice: wave 09's figures as the "before"
    entry ("92.6 MB / 97.4 MB / 49.8 MB before statsmodels"), this build's figures and the wheel's
    in front.
  - No hunk changes code beyond the merge (two comment lines and two `die` lines kept side by
    side), so **no new release run**: the wave's dry run is the check (AGENTS.md rule 2).
  - **Missed merge, found by the lane, not a conflict:** `tests/jobs/oracle/uv.lock`, a generated
    file git merged as text, cleanly. Wave 09's 100 split numpy into two sources (the macOS
    arm64 OpenBLAS wheel by URL, the registry elsewhere) and rewrote every dependent's numpy
    line; 045's formulaic and statsmodels entries still said `{ name = "numpy" }`, so
    `uv run --frozen --project tests/jobs/oracle` failed to parse the lock. Both lines now carry
    the two sources, as 100's own fix gave scikit-learn's and seaborn's (`8e7eac9`). Under the
    judge's `jobs.oracle_env()`, `uv lock --check` passes and `uv lock` leaves the file byte
    for byte unchanged; the oracle synced online (`jobs.oracle_command(..., offline=False)`:
    numpy 2.5.2, statsmodels 0.15.0, formulaic 1.2.2); and
    `test_v1_3_data_stack.py::test_goldens_reproduce_under_the_pinned_oracle` passes by node id
    on this set (`build/045/oracle-goldens.txt`). EXECUTED.
- **Checks:** `ruff check` and `ruff format --check` on `src` and `tests`: clean. The rules
  check ran in the fast tier: green.
- **The build:** `scripts/build.sh --plain` from an empty `build/`, 20 steps in 12 min 57 s
  (`build/045/build-3.txt`). Step 60: 297 archives (wave 09's numpy shims one more), 21,964 weak
  names, 0 unreviewed, 0 stale; the link map 0 findings; the constructors 158, none new.
- **The set:** `SHA256SUMS` hashes to **`d0d91cef…4999`**.

  | file | wave 09 (main tree, `142bdd38`) | this set | change |
  |---|---|---|---|
  | `python.wasm` | 92,553,279 | 99,421,513 | +6,868,234 |
  | `python-snapshot.wasm` | 97,445,041 | 104,511,377 | +7,066,336 |
  | `python-stdlib.zip` | 49,772,117 | 53,913,865 | +4,141,748 |
  | **the wheel** | 90,864,138 | **98,251,487** | +7,387,349 |

  The binary's growth on top of 100's numpy is the `dbecd2d` build's to 71 bytes, so the
  measured split above holds. **The wheel is 98,251,487 bytes, 1,748,513 under the owner's
  100,000,000-byte line (question 64).** Both wheels were built locally as the build job builds
  them (`uv build --wheel --build-constraints release/build-constraints.txt --require-hashes`
  over a `git archive` of the commit with the set copied into `src/wasi_python/artifacts`; the
  base from the main tree's wave 09 set). The `dbecd2d` set's CI wheel was 99,010,212; wave 09's
  smaller `python.wasm` takes about 0.76 MB off it.
- **The fast tier** `-n 3` (`build/045/fast-2.txt`): 679 of 886 pass, **0 fail**, 3 blocked (the
  prior-art clones, three systems, the wheel), 204 deselected; unit suite 2,008 of 2,015 (7
  skipped). The ratchet against main's accepted `a3bb58541b`: lost 0, absent 0, gained 12 (all
  045's), grew 211. The RED is growth only.
- **By node id** (`build/045/nodes-2.txt`): the golden on both binaries and seaborn's
  `statistical_plots`, 3 passed. Fuel: 19,764,298,509 plain and 19,376,044,261 snapshot;
  `statistical_plots` 38,704,050,829 to 38,733,076,727 (+29.0 M, against +38.8 M on the old base).
- **Rows that grow** against `a3bb58541b` (`build/045/grew-2.txt`): the three byte rows; 208 fuel
  rows, all up. The plain start (`test_guest_runs_here[plain]`) +15,086,315, the snapshot start
  +1,362,714; 67 rows in the plain-start band, 69 snapshot rows under +2.2 M (the smallest
  `test_unbuffered_output_survives_a_hard_exit[snapshot]`, +7,065); the zip-directory checks up
  to +10.1% (`test_resources_read_as_zipfile_reads_them[plain]` +1.35 G); the metadata check
  +48.2 M; the largest import row `test_scikit_learn_runs_without_threads[plain]` +166.7 M
  (+1.0%). The same classes as before. macOS's `cpython-fs` row is not in the fast tier; on the
  `dbecd2d` run it was +258 M, and the wave's dry run reads it again.
- **The flags** below are updated for this base (seaborn +29.0 M, the snapshot +7.07 MB, the
  start's figures, the wheel); each still begins "045:".

**Where it stands (2026-10-21, the second builder).** Rebased onto `dbecd2d` (main plus the
structural chain 103 to 109, which main fast-forwards to), rebuilt from an empty `build/`,
judged on the fast tier and by node id, and run once on the release workflow. Every number in
this part is EXECUTED on this build unless marked. The first build, on main `faa9c93`, is
written down further below; its numbers are that build's.

**The builder's self-check** (`../reviews/README.md`):

- [x] rebased onto the named base today: `dbecd2d` (the chain's tip on
  `claude/gallant-ride-9nxxmn`; main fast-forwards to it); the base is in the Status line;
- [x] CI run dispatched on the code tip and read: run **39533679276** on `7be1837` (the commits
  after it touch only `README.md` and `context/`). Red lines: macOS own-guest 212 GREW and
  own-embedding 33 GREW, upstream-macos 1 GREW (cpython-fs), 0 lost, no G7. **Two Windows legs
  are red and neither is 045's** (below, *Not 045's*); the gather and the publish jobs were
  skipped, so the run has no `release-record-1`;
- [x] every number from a measured run on this base, labelled; the growth list is this build's
  (`build/045/grew-1.txt`, against main's accepted record `72bc5ed6b5`);
- [x] "For the lane": the claim list, the flags (each reason begins "045:"), the wave kind, the
  dry-run needs, below;
- [x] every new check seen failing first: on the set before 045 (`build/045/seen-failing-base.txt`,
  12 failed, the first build's notes), the unit checks before their code
  (`build/045/unit-seen-failing.txt`), and the notice check on a notice without `_stl.pyx`
  lines 3-13 (the confirming review's L5; below). Windows and Linux: the guest checks run on all
  three systems in the release workflow; the notice and source-tree checks run in the build
  shard, on arm64 macOS; Linux and Windows run the zip's left-out check and every guest check;
  none is excluded;
- [x] no gap added or closed; statsmodels' own suite is reserved to spec 095 (the roadmap's line,
  `tests/upstream/packages.toml`'s `later` entry);
- [x] `packages.toml` has its reason lines (statsmodels `later`, closer spec 095; formulaic,
  interface-meta and wrapt with spec 067); README rows: the sizes row (100.7 / 105.8 / 53.9 MB,
  this build), the patch count (23), the artifact table, *statsmodels in the guest*, seaborn's
  statsmodels fits;
- [x] CHANGELOG under the one unreleased section; no new question;
- [x] `ruff check`, `ruff format --check` (src, tests), the rules check: green; the fast tier:
  0 fail, red on growth only (`build/045/fast-1.txt`).

**The rebase onto `dbecd2d`** (89 commits since `faa9c93`: the chain 103 to 109, 110's and 111's
drafts and their reviews). `git rebase dbecd2d` stopped twice. **Each conflict hunk, and how it
was resolved:**

- Phase 1 (`8258f2c`), 12 hunks in 10 files. In every one, the chain had reworded a comment
  to give its reason in words (spec 109's rule), and 045 had added statsmodels to the same
  comment or list. Each was resolved to the chain's wording with 045's addition written the same
  way:
  - `.github/workflows/release.yml`: the zero-patch step's comment, "all twenty-eight trees"
    (seaborn's sdist the twenty-seventh, statsmodels' the twenty-eighth); the `grep` for
    `^28 passed` is 045's and unchanged.
  - `scripts/assemble_artifacts.py`: `WHEELS`, reportlab's line in the chain's words, then
    045's three wheels.
  - `scripts/gen_inittab.py`: the docstring's rename paragraph (scikit-learn's **five**, as 045
    had corrected it, and statsmodels' four).
  - `scripts/make_stdlib_zip.py`: the docstring's `--drop` paragraph with 045's one-member form.
  - `scripts/steps/60_link.sh`, two hunks: the header's list of what links (statsmodels added),
    and the archives-by-import-path comment.
  - `scripts/steps/70_zip.sh`, two hunks: the header (045's statsmodels sentence after
    reportlab's; a stray duplicate line, "nothing): no JPEG decoder...", that the first rebase had
    left in 045's side, dropped) and the four `die` lines of the staged trees.
  - `tests/checks/test_v1_1_artifact_set.py`: the dotted-builtin comment (statsmodels' 26).
  - `tests/harness/needs.py`: the list, `statsmodels` after `seaborn`.
  - `tests/harness/scan.py`: the build-folder list, `statsmodels-build` with a comment in words.
  - `tests/release_shards.toml`: the node-id comment (scikit-learn's and statsmodels' notice
    checks).
- `5819ad8` (the confirming review's commit), 1 hunk: `context/roadmap.md`, the chain's new
  "Reserved" lines (102 to 111 and the two closers) kept, then 045's wording of the 095 line (statsmodels' suite,
  the owner's answer) in place of the chain's shorter one.
- The other three commits applied cleanly.
- **Found by testing, not a conflict:** the chain's new rules check
  `test_code_outside_src_names_no_context_document` failed on 32 citations in 045's own comments
  and docstrings (15 files: "spec 045", "spec 044, Decision 4", "037's" and the like). Each was
  reworded in `7be1837`, the reason in words and no document named; the decisions keep their
  numbers, as the chain's own wording does. One docstring line then ran past ruff's length and was
  rewrapped. No allowance was added.

**The build:** `scripts/build.sh --plain` from an empty `build/` at `7be1837`, all 20 steps in
17 min 50 s (`build/045/build-2.txt`). Every gate held, with the first build's counts: step 59's
26 archives; step 60's weak-duplicate gate (296 archives, 21,964 weak names, 0 unreviewed, 0
stale), the link map (4 required, 3 forbidden, 0 findings), the constructors (158, none new) and
the target features (11).

**The set:** `SHA256SUMS` hashes to **`14adfa5f…ab5c`**. The three binaries are byte for byte
the first build's: `python.wasm` 100,661,758 (`380883f22d06bbab`), `python-snapshot.wasm`
105,765,849 (`25a28831d97b8473`), `python-stdlib.zip` 53,913,735 (`142d6043de861e1c`). Only
`MANIFEST` differs from `f2a3e87d` (the recipe hashes of the reworded scripts).

**Why `python.wasm` grew 6.87 MB, past Decision 14's bound** (the build review's finding to
explain; EXECUTED unless marked). The base is main's set as the main tree holds it (`python.wasm`
93,793,595 bytes, the same size as wave 08's). Measured three ways:

- **By section** (`llvm-size -A` on both binaries, `build/045/size-sections.txt`): CODE
  +6,064,838, DATA +415,728, the `name` section +366,631, ELEM +13,600, FUNCTION +7,285, TYPE +81.
  These sum to exactly +6,868,163. No debug section ships.
- **By archive** (the two link maps, `build/link/python.map`, summed per input;
  `build/045/size-2.txt`): only 28 inputs changed, the 26 statsmodels archives, `inittab.o`
  (+1,482) and the linker's own data. **No scipy, OpenBLAS or other archive grew by one byte.**
  So the `cython_blas` and `cython_lapack` wrappers the state-space modules call were linked
  already, by scipy; the draft's second candidate is ruled out. The 16 state-space modules are
  4.50 MB of the 6.36 MB the archives add (71%), the largest `_kalman_filter` 672 KB and
  `_representation` 629 KB. Each is a Tempita template expanded four times, once per dtype
  (`s`, `d`, `c`, `z`: `TYPES` in `_kalman_filter.pyx.in`, READ).
- **By optimisation level** (each of the 26 modules compiled again from its generated C at the
  build's own command, only `-O3` swapped; `build/045/olevel/sizes.txt`): CODE 6,063,407 at
  `-O3`, 5,886,567 at `-O2` (-2.9%), 5,520,023 at `-Os` (-9.0%). The `-O3` sum equals the link's
  CODE growth to 51 bytes, so every function of every module is linked (each is reachable from its
  module's init) and nothing is dead. The level explains at most 0.54 MB.

**So the bound was wrong, not the build.** Decision 14 took Pyodide's 4.24 MB `.so` times 0.92,
the ratio numpy and pandas gave. That ratio does not hold for Cython packages: scikit-learn grew
`python.wasm` by 9.00 MB against Pyodide's 6.0 MB (044's notes), a ratio of 1.50, and statsmodels
gives 6.87 / 4.24 = 1.62. With 044's ratio the expectation is about +6.4 MB, and the build is 7%
above it. Why Pyodide's `.so` is smaller is not measured here (INFERRED: Pyodide builds at `-O2`
and strips the `name` section: about 0.55 MB of this growth together, 0.9 MB had it built at `-Os`). **Nothing is linked that
need not be:** the 26 modules are statsmodels' own compiled modules, each importable, whole. The
`name` section is a set-wide choice (14.1 MB of `python.wasm`, of which statsmodels adds
0.37 MB), not this specification's to change.

**The fast tier** `uv run pytest -m "not slow" -n 3` on this set (`build/045/fast-1.txt`): 671 of
878 pass, 0 fail, 3 blocked (the prior-art clones, three systems, the wheel), 204 deselected;
unit suite 1,984 of 1,991 (7 skipped). The ratchet against `72bc5ed6b5`: lost 0, absent 0,
gained 26 (14 are the chain's rules checks, 12 are 045's), grew 205. The RED is growth only.

**By node id** (`build/045/nodes-1.txt`): 14 passed, 0 failed, among them the golden on both
binaries, the four behaviour checks on both, `test_left_out_datasets_say_so`,
`test_hdrboxplot_needs_processes`, `test_statsmodels_says_what_it_lacks`, the two zip checks and
042's `test_statistical_plots_job_matches_native` (seaborn's statsmodels fits now run, the golden
unchanged). **`regen.py --check --online`:** all 28 goldens reproduce natively, under hash seeds 0
and 1 (`build/045/regen-check.txt`; the oracle fetched again into an empty `build/oracle/`).

**The notice check, seen failing (L5):** on a copy of this set's `LICENSES/statsmodels.txt` with
the `_stl.pyx, lines 3-13` part cut out, `statsmodels_notice_errors` returns "does not hold
statsmodels/tsa/stl/_stl.pyx, lines 3-13"; on the intact notice, nothing
(`build/045/l5_probe.py`).

**The numbers Decision 14 and criterion 5 ask for** (fuel from the judge's rows and from
`wasi-python run`, `build/045/fuel-probes.txt`):

| row | base | this set | change | bound |
|---|---|---|---|---|
| `python.wasm` | 93,793,595 | 100,661,758 | +6,868,163 | +2.5 to +5.5 MB: **outside**, explained above |
| snapshot | 98,682,976 | 105,765,849 | +7,082,873 | — |
| the zip | 49,771,987 | 53,913,735 | +4,141,748, 588 members | ≤ +4.5 MB, +588: inside |
| plain start (`test_guest_runs_here[plain]`) | 256,841,790 | 271,934,625 | +15,092,835 (25,668 per member) | ≤ +17.6 M: inside |
| snapshot start (`[snapshot]`) | 52,070,609 | 53,538,310 | +1,467,701 (2,496 per member) | ≤ +2.1 M: inside |
| `test_packages_carry_their_metadata[plain]` | 5,946,256,777 | 6,000,469,328 | +54,212,551 | four distributions, ≤ 25 M each: inside |
| 042's `statistical_plots` (macOS, run 39533679276) | 38,702,920,564 | 38,741,672,028 | +38,751,464 | plain start + 2 M = 17.1 M: **outside** |
| the golden, plain / snapshot (macOS, the run) | — | 19,847,024,185 / 19,453,687,062 | new | — |
| `import statsmodels.api`, plain / snapshot | — | 17,386,095,372 / 16,900,084,275 | new | — |
| `import statsmodels`, plain | — | 273,772,417 | +2.3 M over `pass` | — |
| the wheel (`rebuild-wheel-ubuntu-24.04`, run 39533679276; the build review's reading) | about 91.6 MB (run 39530569266's artifact on `dbecd2d`, 91,470,969 bytes zipped) | 99,010,212 | about +7.4 MB | question 64: under 100 MB by 0.99 MB; the next package crosses it |

**The seaborn row is a second finding against Decision 14**, smaller and of a known kind. The
table expected the plain start plus `import statsmodels`. Measured on both sets with the same
runner (`WASI_PYTHON_ARTIFACTS`): seaborn's own `import statsmodels` costs 0.35 M (seaborn
imported with statsmodels blocked, against present). The rest is metadata: one walk of every
distribution (`importlib.metadata.entry_points()`) costs +22.2 M more with the four new
distributions (842.2 M against 820.0 M), and the job's four `version()` reads +3.9 M. Importing
matplotlib, scipy.stats, pandas and seaborn pays +24.4 M over the start, most of it, INFERRED,
such walks inside those imports. Decision 14 counted the metadata cost for 033's and 035's checks
but not for a job that imports matplotlib.

**Decision 14's last row is outside too, for the same causes and one more** (the build review's
Finding 2, its probes EXECUTED): every import lookup costs about 8.2 k fuel more in this binary,
whose inittab is 26 entries longer (3,000 failed imports +24.7 M on 045's set against main's,
+24.4 M with 045's `python.wasm` and main's zip, so the cost is the binary's, not the zip's).
So a job that imports pandas pays +4.9 M over the start, and the golden jobs grow past the
plain-start row: `sqlite` +23.4 M, `callbacks` +20.7 M, `markup` +25.0 M, `excel` +27.3 M,
`modelling` +63.5 M and `files_from_the_zip` +63.1 M against the start's +15.1 M, by that cost,
their `version()` reads and their metadata walks. 0.64 M of the start's +15.1 M is the binary's
too (the mixed set at `pass`).

**The claim list** (against main's accepted record `72bc5ed6b5`; the chain's rows are its own):

- **New checks (14 rows, and a unit file):** `test_v1_3_default_profile.py::test_statistical_models_job_matches_native[plain]`,
  `[snapshot]` (slow); `::test_statsmodels_reads_its_datasets_from_the_zip[plain]`, `[snapshot]`;
  `::test_formula_engines_run_pure[plain]`, `[snapshot]`; `::test_statsmodels_modules_are_builtin[plain]`,
  `[snapshot]`; `::test_left_out_datasets_say_so`; `::test_hdrboxplot_needs_processes`;
  `::test_statsmodels_says_what_it_lacks`; `test_v1_1_artifact_set.py::test_statsmodels_notice_carries_its_bundled_parts`
  (the build shard); `::test_left_out_dataset_files_are_not_in_the_zip`;
  `test_v1_5_rebuild_from_pins.py::test_source_tree_matches_its_tarball[statsmodels]`; and the
  unit suite's `tests/unit/test_statsmodels_build.py`.
- **Changed checks:** `test_packages_carry_their_metadata` (four more distributions);
  `test_dotted_builtins_keep_their_import_names` (statsmodels runs apart, as scipy and
  scikit-learn); `test_stdlib_c_modules_are_builtin`'s list; the package, licence, source-tree,
  pin and metadata lists, `MESON_BUILDS`, `JOBS` and `PLATFORM_BOUND`; `packages.toml`'s four
  entries; two unit fixtures (the step list, the synthetic set); the release tree count 28.
- **Gaps:** none added, none closed. **Retired:** none. **Passes moved:** none lost.
- **Rows that grow** (`build/045/grew-1.txt`): the three byte rows above; 202 fuel rows, all up,
  none down. The largest by share are the zip-directory checks, +8.0% to +10.1%
  (`test_resources_read_as_zipfile_reads_them` +1.35 G plain: they walk every member, and the
  zip has 10% more); then each plain start's +15.1 M, 66 rows between +12.1 M and +19.9 M;
  71 snapshot rows under +2.1 M (the smallest `test_unbuffered_output_survives_a_hard_exit[snapshot]`,
  +5,671); rows that read metadata or import matplotlib or scipy, up to +162.8 M
  (`test_scikit_learn_runs_without_threads[plain]`, +1.0%). The macOS legs' 245 GREW lines are
  the same cause. **One upstream row the fast tier does not run:** macOS's
  `test_upstream_suite[cpython-fs]`, 63,199,952,331 to 63,457,910,733 (+257,958,402, +0.41%),
  the zip's directory rebuilt over 588 more members each time the suite invalidates the import
  caches (044's reading of the same row; the count of rebuilds INFERRED, about five at +52 M
  each).
- **Not 045's:** in run 39533679276, `judge (windows-2025, own-embedding)` loses
  `test_v1_4_embedding.py::test_a_forked_child_is_refused`. It fails the same way on the base's
  own run 39530569266 (`dbecd2d`) and on spec 097's run 39532775277. `judge (windows-2025,
  own-runner)` fails the unit test
  `tests/unit/test_runner_sets.py::test_a_same_size_same_mtime_replacement_is_hashed_again`
  (3 reads, not 2). It passed on the base's run and fails on spec 100's run 39535794638 too, so
  it is intermittent on Windows. 045 changes no file under `src/` and neither test. The lane
  should know both before the wave's dry run (AGENTS.md rule 6b: a check can pass the lane and
  still fail on Windows).

**The wave:** a package (§5.7: the wave's one package). **045 lands after wave 09** (100, 101,
097), rebased onto its tip. Wave 09's numpy-on-OpenBLAS change (spec 100) may grow the wheel,
and 045 leaves it 0.99 MB under the owner's 100 MB line (question 64). So **the lane
re-measures the wheel on 045's rebase onto wave 09 before accepting**, and brings question 64
back to the owner first if that wheel passes 100,000,000 bytes. **Dry-run needs:** the wave's dry run on all three systems,
its zero-patch job expecting 28 trees; the build review's own run (§5.6) unless it reviews
`7be1837`'s code exactly, where run 39533679276 is on it.

**The flags** (paste-safe):

```
--accept "045: statsmodels 0.15.0 built in with formulaic 1.2.2, interface-meta 2.0.1 and wrapt 2.5.1: 26 modules as builtins, four renamed per file, 588 zip members, the golden equal to native on both binaries, sixteen public-domain datasets read from the zip by one carried patch, the thirteen not approved left out and raising FileNotFoundError; the owner approved the six components (decisions.md, 2026-10-20)"
--accept-judge "045: the statistical_models golden with the oracle's statsmodels pins; four statsmodels behaviour checks on both binaries and three that say what it lacks; the notice check (build shard) and the left-out check; statsmodels, formulaic, interface-meta and wrapt in the package, licence, source-tree, pin and metadata lists, MESON_BUILDS, JOBS, PLATFORM_BOUND and packages.toml, its suite later with spec 095 as its closer; statsmodels' own dotted-builtin run; the release tree count 28"
--accept-growth "045: python.wasm +6.87 MB and the snapshot +7.07 MB by statsmodels' 26 modules, whole, 4.50 MB of them the four-dtype state-space modules, no other archive grown, measured on top of 100's numpy on OpenBLAS (the bound's 0.92 ratio is numpy's; Cython packages give 1.5 to 1.6); the zip +4.14 MB by 588 members; the wheel +7.39 MB to 98,251,487 bytes, under the 100 MB line; every plain start +15.1 M fuel (25,657 per member) and every snapshot start +1.36 M by those members' directory entries; the zip-directory checks walk them, and macOS's cpython-fs suite about +258 M (0.41 percent) by rebuilding the zip's directory; four more distributions' metadata, which every metadata walk reads, seaborn's job +29.0 M with it; and each import lookup about 8 k fuel more in the binary's longer inittab (26 entries; EXECUTED, 045's python.wasm with main's zip), so a job importing pandas pays +4.9 M over the start, and the golden jobs grow past Decision 14's plain-start row by that and by their version() reads and metadata walks"
```

**Remaining:** the build review is written (`../reviews/045-statsmodels-build-2026-10-20.md`,
"lands once Finding 1 is written in"; its Disposition answers each finding); the lane's
acceptance in the wave, after wave 09, with the wheel re-measured. Criterion 2's "full build in a clean
clone" is met by the release workflow's build job (run 39533679276, green, from pins on a clean
runner) and the two rebuild jobs, not by a local clone. The wheel's bytes, 99,010,212, are in the table above (the build
review's M1).

### The first build, on main `faa9c93` (superseded by the rebuild above)

**Built natively; not yet judged** (2026-10-20, darwin-arm64). The owner ran out of time for the
day. On the lane's word the builder finished the one build that was running, wrote it down here,
and stopped. No fast tier, no single node id against the new set, and no release workflow run
were started. Those, the self-check, *For the lane* and the hand-over come next. The native slot
is released. Every number below is EXECUTED unless marked.

**The rebase onto main `faa9c93`** (wave 08: 042, 066, 099). Running `git rebase origin/main`
stopped on phase 1 (`0b73a2d`) with 22 conflict hunks in 14 files; the two later commits, both
`context/`-only, applied cleanly. Each hunk and how it was resolved:
- **Wave 08's line and 045's line both kept, wave 08's first (a list, union):**
  - `scripts/00_download.sh`: seaborn's and reportlab's pins beside the three wheels' pins.
  - `scripts/steps/70_zip.sh`, four hunks: the header comment, the wheels, the `--metadata`
    lines, and reportlab's two `--drop` lines beside 045's 13 `--keep` and 9 `--drop` lines.
  - `tests/harness/needs.py` and `pins.py`: seaborn's entries beside statsmodels'.
  - `tests/jobs/oracle/pyproject.toml`: seaborn's and reportlab's pins beside 045's.
  - `tests/harness/paths.py`, two hunks: `LICENCE_COMPONENTS` and `PACKAGES`.
  - `tests/harness/jobs.py`, three hunks: `JOBS`, the `PLATFORM_BOUND` comment and the list.
  - `scripts/assemble_artifacts.py`, two hunks: `PACKAGES` and `WHEELS`.
  - `tests/checks/test_v1_1_artifact_set.py`: 042's helper and its three checks beside 045's two.
  - `tests/unit/test_artifact_rules.py`, two hunks: the synthetic pins and packages.
  - `tests/harness/artifacts.py`: 042's reportlab and seaborn rules beside 045's statsmodels
    rule.
- **Merged by hand:**
  - `.github/workflows/release.yml`: the tree count is **28**, seaborn's sdist the
    twenty-seventh and statsmodels' the twenty-eighth (the confirming review's L1).
  - `tests/upstream/packages.toml`: the entries for seaborn, reportlab, statsmodels, formulaic,
    interface-meta and wrapt. The last three lines, shared by reportlab's and wrapt's entries,
    went to both.
  - `tests/checks/test_v1_3_data_stack.py` and `tests/harness/jobs.py`: the two comments joined
    into one sentence each.
- **Found by testing, not shown as a conflict:** git gave the final `return errors` line, common
  to 042's `reportlab_notice_errors` and 045's `statsmodels_notice_errors`, to the statsmodels
  function only. So reportlab's rule returned `None`, and its unit check failed. Restored in
  `76e23ae`, and two files reformatted there.
- **Not a conflict, done by reading:** 042's README line on seaborn's statsmodels-backed fits
  now says they fit with statsmodels (Decision 11; R1). It is to be checked in the guest with the
  judge's run.
- `uv lock` on the merged oracle project changed nothing.
- Then: ruff check and format clean; unit files and the rules check, 1,910 passed and 17 skipped;
  042's `test_a_left_out_folder_is_not_packed` passes under the widened `--drop` (L1).

**The build:** `scripts/build.sh --plain` from an empty `build/`, at `76e23ae`, with all 20 steps
in 12 min 19 s on the first attempt (`build/045/build-1.txt`).
- **Step 59, 19 s.** `meson setup` configured "Project version: 0.15.0" through the stand-in, so
  the version gate held. "scipy cython_blas blas_int" was found. ninja printed 57 warnings. Each
  of the four include-map entries matched exactly one compile. 26 extension modules were listed,
  none tagged tests, and 26 archives laid out under `build/statsmodels-modules`.
- **Step 60.**
  - The weak-duplicate gate read 296 archives and 21,964 weak names, with 0 unreviewed and 0
    stale patterns. That is 26 archives and 2 weak names more than 044's first link: statsmodels
    adds no shared weak definition (the confirming review's N2).
  - `gen_inittab.py --against` passed: no init name is a CPython builtin's (R7).
  - The link map: 4 names required, 3 forbidden, 0 findings.
  - Constructors: 158 reviewed, none new. Target features: the line's 11. No clash line from
    wasm-ld.
- **Step 70:** 5,382 `.pyc` and 878 data files.
- **The set:** `SHA256SUMS` hashes to `f2a3e87d…aa49`.

  | file | bytes | sha256 (first 16) |
  |---|---|---|
  | `python.wasm` | 100,661,758 | `380883f22d06bbab` |
  | `python-snapshot.wasm` | 105,765,849 | `25a28831d97b8473` |
  | `python-stdlib.zip` | 53,913,735 | `142d6043de861e1c` |

- **Against wave 08's set**, as the main tree holds it (`SHA256SUMS` `b5a66245…23b9`, with
  seaborn), read-only:
  - `python.wasm` grows by 6,868,163 bytes and the snapshot by 7,082,873.
  - The zip grows by 4,141,748 bytes. It gains exactly **588 members**: statsmodels' 501 and its
    `METADATA`, formulaic's 58 and interface-meta's 11 and wrapt's 14, each with its `METADATA`.
    That is 4,053,246 bytes as stored and 11,495,785 raw. No other member is added, removed or
    changed. `LICENSES/statsmodels.txt` is 25,274 bytes.

**A finding against Decision 14, for the build review:** `python.wasm`'s growth of +6.87 MB is
past the table's bound of +2.5 to +5.5 MB. The table expected +3.9 MB (INFERRED from Pyodide's
4.24 MB `.so` times 0.92). The zip's rows are inside their bounds: +588 members as expected, and
+4.14 MB against a bound of ≤ +4.5 MB. The cause is not yet measured. Candidates to read from the
link map (INFERRED): the 26 Cython modules' own code, unstripped of what Pyodide's `-Os` and
`wasm-opt` remove, and the BLAS and LAPACK wrappers of `cython_blas` and `cython_lapack` that
the state-space modules now pull in. The build review gets the measured split by object.

**Next, when the lane grants it:** the fast tier `-n 3` on this set, and the remaining
checks by node id:
- the golden on both binaries;
- the behaviour checks, which record what `get_rdataset` gives with `cache=True` (no root, and a
  root) and what `hdrboxplot` raises (L4);
- the notice check, seen failing first on a notice without `_stl.pyx` lines 3-13 (L5);
- seaborn's three statsmodels fits;
- `regen.py --check`.

Then the release workflow run on the commit handed over, the claim list against main's accepted
rows with the paste-safe flags, and the self-check.
