# 044 — scikit-learn

- **Status:** drafted 2026-10-18. Not yet reviewed. It changes the build recipe and the artifact
  set, so it is reviewed before it is built (constitution §5.6). It is build-class: it touches
  `scripts/`, `recipes/`, `downloads/SHA256SUMS` and the release workflow (§5.7). It carries one
  upstream patch (§4.1). It is not built until the owner answers question 83 (the licences of
  what scikit-learn bundles); everything else is decided here.
- **Owner:** Clay Gendron
- **Kind:** the build recipe (one pin; a new step 58; `scripts/wasi-cc`'s per-file include map
  used for a second package; `scripts/gen_inittab.py`'s rename table; `scripts/steps/60_link.sh`;
  `scripts/steps/70_zip.sh`; `scripts/assemble_artifacts.py`; `scripts/install_from_plan.py`; a new
  `scripts/stage_scipy_cimports.sh`), recipe files (a
  cross file, eight small rename headers, a per-file include map), one carried patch to
  scikit-learn with its facts sheet, judge additions and changes (a golden job and the oracle's
  pins, a v1.3 check file, the constructor list, the package and licence lists, a source-tree
  pattern), the release workflow's tree count, `README.md`, `CHANGELOG.md`, `LICENSES/`.
- **Depends on:** specifications not yet built, each landing first (Decision 14): 037 and 038
  (scipy whole: `scipy.linalg.cython_blas`, `cython_lapack` and `scipy.special.cython_special`
  as builtins, the per-file include rule in `scripts/wasi-cc`, `scripts/install_from_plan.py`,
  the rename table in `scripts/gen_inittab.py`, the pinned oracle's scipy and the recording
  platform), 039 (joblib, cloudpickle, threadpoolctl with `ctypes.util.dllist`, narwhals,
  `jobs.run_in_guest`, `tests/checks/test_v1_3_default_profile.py`), 042 (`make_stdlib_zip.py
  --leave-out`), and through them 023, 033 and 035. Landed: 020 (each source tree equals its
  tarball plus the recorded patches), 012 (the same bytes from any host). Where one of them lands
  in another shape than its text, this specification uses what landed and says so in its
  landing notes.
- **Research it stands on:** `../research/2026-10-17-what-else-the-default-profile-carries.md`
  (tier B: scikit-learn is "Cython + C++, OpenMP optional", needs scipy, joblib, threadpoolctl
  and narwhals; its Python part 415 members; Pyodide's `.so` 6.0 MB; finding 4c, threadpoolctl
  and `ctypes`; finding 4f, joblib serial); `../research/2026-10-17-what-scipy-needs.md` (the
  0.92 Pyodide-to-ours size ratio; no threads); spec 037 (the scipy line this rides on); the
  owner's decisions 43 and 48 (`../decisions.md`: tier B approved, in 0.1.0, after scipy).
  **The drafting runs** (EXECUTED 2026-10-17 and 18 in the session's scratch folder, outside the
  repository; nothing in the repository was changed by them; tool outputs quoted are marked):
  - PyPI's JSON for scikit-learn and its dependencies; the sdist and the oracle's wheel
    downloaded and hashed (`shasum -a 256`, equal to PyPI's);
  - the sdist read: `meson.build` files, `pyproject.toml`, the OpenMP helpers, the svm sources,
    the dataset loaders, the vendored code and its notices;
  - a meson probe with the line's meson 1.12.1 and wasi-sdk 33's clang for `wasm32-wasip1`:
    `dependency('OpenMP', required: false)` is not found;
  - a native build of the sdist on the build host (macOS arm64) with the line's meson 1.12.1,
    Cython 3.3.0 and Python 3.15.0, against numpy 2.5.2 and scipy 1.18.1: all 257 targets, 69
    extension modules; then `nm` over its objects for symbols defined in more than one;
  - the golden job drafted and run natively under two hash seeds, and run again with
    scikit-learn's Python files imported **from a zip** and its extension modules loaded by
    name (a model of the guest's import path, `tools/zip_hybrid.py` in the facts sheet's
    evidence): the stock package fails at import, the patched one gives native's output byte
    for byte;
  - the zip members and bytes step 70 would add, computed with step 70's own `walk`, `pyc` and
    `member` (imported read-only from `scripts/`) under the line's Python 3.15.0.

## The problem

scikit-learn is the fourth most used library in both benchmarks the default-profile memo read,
and on every hosted code sandbox's list (memo findings 1 and 2). The owner put it in 0.1.0
(decision 48). Today `import sklearn` in the guest is `ModuleNotFoundError`.

It rides on scipy: it is a meson-python build of Cython, C and C++ like numpy, pandas and scipy,
and it calls BLAS and LAPACK only through `scipy.linalg.cython_blas` and `cython_lapack`. What is
new here is small but sharp:

- **Its extension modules collide in a static link.** 69 modules. Three pairs share an init
  name (`_gradient_boosting`, `_tree`, `_utils`), its `_cyutility` shares one with pandas' and
  scipy's, and its svm wrappers `#include` helper C files whose functions are not `static`:
  nineteen C names are defined in two or three modules (EXECUTED, the native build's objects).
  Natively each module is its own shared object, so none of this shows.
- **It reads its own files by path at import.** `sklearn/utils/_repr_html/estimator.py` reads
  three CSS files with `Path(__file__).parent / "estimator.css"` when the module is imported, and
  `sklearn.base` imports it. From the zip that path is not a folder: `import sklearn` raises
  `NotADirectoryError` (EXECUTED in the model of the guest's import path).
- **OpenMP, threads and processes do not exist here.** scikit-learn already builds without
  OpenMP and runs serially (`_openmp_helpers.pxd`); joblib already falls back to serial without
  `_multiprocessing`. Both need to be shown, not assumed.

## Decisions

1. **What goes in.** scikit-learn 1.9.1: its 69 extension modules linked into `python.wasm` as
   builtins, and its Python package (410 members, 3,269,711 bytes as step 70 packs them, plus
   one `METADATA`; Decision 11). Its requirements are already in the set by then: numpy 2.5.2,
   scipy 1.18.1 (037), joblib 1.6.0 with cloudpickle 3.1.2, threadpoolctl 3.7.0 and narwhals
   2.27.1 (039). Each meets its bound (READ, `sklearn/_min_dependencies.py` and `METADATA`:
   numpy ≥ 1.24.1, scipy ≥ 1.10.0, joblib ≥ 1.4.0, narwhals ≥ 2.0.1, threadpoolctl ≥ 3.5.0). No
   other distribution is added.

2. **The pin.** scikit-learn 1.9.1 is the current release (uploaded 2026-09-10) and the version
   the memo measured.
   - `https://files.pythonhosted.org/packages/d2/eb/eaf5e07fcc0da7149b0e084f24e54edd7441b9a89ce7e034032ae97fe3a0/scikit_learn-1.9.1.tar.gz`,
     SHA-256 `629cada3e33e2b9bf376cdc7614a47a4140b8aedc1d836579e359736fbd82977`, 7,786,908 bytes
     (EXECUTED: PyPI's digest and the downloaded bytes). It unpacks to `scikit_learn-1.9.1`, the
     tree rule's name. One `get` line in `scripts/00_download.sh`, one line in
     `downloads/SHA256SUMS`, one `pin` line in `MANIFEST` through the existing loop; and one
     more of each for numpydoc's licence text (Decision 11).
   - **Reused, not re-pinned:** Cython 3.3.0 and meson 1.12.1 (the line's) and the host numpy
     stand-in (step 40).
   - **Cython 3.3.0 against scikit-learn's `<3.2.6`.** `pyproject.toml` asks
     `cython>=3.1.2,<3.2.6`, with the comment that the cap waits for Cython issue 7846 and should
     become `!=3.2.6,!=3.2.7,!=3.2.8,!=3.2.9` once a release fixes it (READ). Issue 7846 is
     "`cyfunction.__annotate__` objects can't be unpickled", seen on 3.2.6 (READ, GitHub). Its
     fix (pull request 7852, merged 2026-07-25 into `master`) is in 3.3.0: the 3.3.0 sdist's
     `Cython/Utility/CythonFunction.c` defines `__annotate_cython__` and its test file has
     `test_pickle_unpickle` (EXECUTED: `grep` in the pinned 3.3.0 sdist, SHA-256
     `eed0d93f…88b8`). The cap is pip's; scikit-learn's `meson.build` checks Cython's version
     only when not cross-compiling (READ, `sklearn/meson.build:22-59`), and this project runs meson directly.
     The native build compiled all 69 modules with 3.3.0, and the golden job's pickling
     (`joblib.dump` of a fitted forest, read back) ran (EXECUTED). **No fallback Cython:** 3.2.9,
     037's fallback, is one of the releases the cap excludes; a failure with 3.3.0 stops the
     build and becomes a memo (AGENTS.md rule 7).
   - numpy's cap `<2.6.0` holds 2.5.2 and scipy's `<1.19.0` holds 1.18.1 (READ).

3. **No OpenMP, by the SDK, checked at build time.** scikit-learn asks
   `dependency('OpenMP', language: 'c', required: false)` (`sklearn/meson.build:104`) and, when
   it is not found, builds every module without `-fopenmp`. Its helpers then define
   `SKLEARN_OPENMP_PARALLELISM_ENABLED 0`, `omp_get_max_threads()` as 1 and the lock calls as
   no-ops (`sklearn/utils/_openmp_helpers.pxd`, READ), and Cython's `prange` compiles to a plain
   loop when `_OPENMP` is undefined.
   - **Why it is not found.** wasi-sdk 33 ships no `omp.h` and no OpenMP runtime. The probe
     (EXECUTED, the line's meson 1.12.1, wasi-sdk 33's clang, `wasm32-wasip1`): "Run-time
     dependency OpenMP for c found: NO", `has_header('omp.h', args: ['-fopenmp'])` false, though
     clang defines `_OPENMP` (202011) when given `-fopenmp`. The cross file names only the SDK's
     compilers and sysroot, and `pkg-config` is `false`, so no host library can be found.
   - **The gate.** Step 58 dies unless its `meson setup` log holds
     `Run-time dependency OpenMP for c found: NO` and no command in the build's
     `compile_commands.json` holds `-fopenmp`. So a future SDK that ships an OpenMP runtime
     cannot change the build silently: it would also need threads, which the guest does not
     have.
   - **What a guest sees** (Decision 9): `_openmp_parallelism_enabled()` is `False` and every
     `n_threads` resolves to 1.

4. **scipy's Cython declarations, staged for the build** (`scripts/stage_scipy_cimports.sh`,
   new, used by this specification and 045). scikit-learn cimports
   `scipy.linalg.cython_blas` (27 cimports across both packages), `cython_lapack` and
   `scipy.special.cython_special` (`tree/_criterion.pyx`) (EXECUTED: `grep` over both sdists).
   Cython finds a cimported module's `.pxd` on `sys.path`, and needs every folder above it to be
   a package. 037's install of scipy carries none of these: the generated `cython_blas.pxd` and
   `cython_lapack.pxd` are tagged `devel` (READ: `scipy/linalg/meson.build:10-37`), and 037's
   `install_from_plan.py` copies only `python-runtime` files.
   - The script writes `build/scipy-cimport/` fresh each time: an empty `scipy/__init__.py` (a
     package marker; `scipy/` has no `__init__.pxd`), `scipy/linalg/__init__.pxd`,
     `cython_blas.pxd` and `cython_lapack.pxd` (the last two from 037's build folder,
     `build/scipy-build/scipy/linalg/`, the first from the patched sdist), and
     `scipy/special/__init__.pxd` and `cython_special.pxd` (from the sdist). None of the five
     `.pxd` files cimports anything outside them (READ). EXECUTED while drafting: the same six
     files taken from scipy 1.18.1's wheel, with numpy's two `.pxd` files beside them on
     `PYTHONPATH`, let the line's Cython 3.3.0 cythonize a probe that cimports `blas_int`,
     `ddot`, `cython_lapack` and `xlogy`, with the empty marker as `scipy/__init__.py`. Six files, named in
     the script; it dies naming any that is missing.
   - Step 58 puts `build/scipy-cimport` and `build/numpy-host` (step 40's stand-in, which holds
     numpy's `__init__.pxd`) on `PYTHONPATH`. The empty marker means a host process that imported
     `scipy` would get an empty package; nothing in scikit-learn's build imports scipy when
     cross-compiling (READ: its version checks sit under `if not meson.is_cross_build()`,
     `sklearn/meson.build:22-59`).
   - `meson setup` then reports "scipy cython_blas blas_int compiles: YES"
     (`sklearn/utils/meson.build:1-12`), as it did natively against scipy 1.18.1's own `.pxd`
     (EXECUTED). With scipy's LP64 build `blas_int` is `int`.
   - **At run time** a module that cimports `cython_blas` imports `scipy.linalg.cython_blas`
     and takes its function pointers from the module's `__pyx_capi__` capsule. No BLAS symbol
     crosses the link, and the call reaches 037's OpenBLAS through scipy, as natively.

5. **Step 58: scikit-learn** (`scripts/steps/58_sklearn.sh`, after step 57; needing 10, 20, 40,
   57). The number is free in today's tree; if a specification drafted alongside takes 58 first,
   the lane renumbers this one and says so in the landing notes.
   - It unpacks the sdist to `build/scikit_learn-1.9.1`, applies its patch (`patch_tree`,
     Decision 7) and builds out of tree in `build/sklearn-build`.
   - **`recipes/wasi-sklearn.cross`**, from the pandas cross file: the same `[binaries]`
     (compilers through `scripts/wasi-cc` and `scripts/wasi-cxx`, `python` the target Python,
     `cython` the line's, `pkg-config = 'false'`); `[properties]`
     `numpy-include-dir` set to step 40's installed `numpy/_core/include` (scikit-learn reads
     the property instead of running Python, `sklearn/meson.build:75-78`, READ: "This uses the
     path as is, and avoids running the interpreter"); `c_args` and `cpp_args` the pandas set without
     `pandas_rename.h`. No setjmp flags: neither package calls `setjmp` (EXECUTED: `grep`).
     Standard C++ exceptions stay on, as for numpy and pandas: `neighbors/_partition_nodes.pyx`
     declares a C++ call `except +` (its one use, READ), and the C++ standard library's
     containers in the tree and neighbour modules throw through them.
   - **The configure line:** `meson setup --cross-file … --buildtype=release
     -Db_ndebug=if-release`, then `ninja`. The release build type and asserts off are
     meson-python's defaults, as scikit-learn's wheels are built.
   - **The version script** (`sklearn/_build_utils/version.py`, run by `project()`) starts
     `#!/usr/bin/env python3`; meson runs such a script with its own Python (READ:
     `mesonbuild/programs.py`, `_shebang_to_cmd`), the pinned host Python. It reads only
     `sklearn/__init__.py`. The step checks the configured version is `1.9.1`.
   - **The OpenMP gate** (Decision 3) and **the per-file include log** (Decision 6) are checked.
   - **The Python package, as an install places it.** scikit-learn installs its whole `sklearn/`
     folder with `install_subdir` (READ, `meson.build:51`), whose files meson does not tag,
     and generates no Python file. So the step copies the patched sdist's `sklearn/` to
     `build/sklearn-install/sklearn`, pandas' pattern. EXECUTED while drafting: the sdist's
     `sklearn/` and the native wheel's hold the same files once tests, sources, extension
     modules and `meson.build` are set aside, as step 70 sets them aside.
   - **The extension-module list.** 037's `scripts/install_from_plan.py` gains `--modules-only`:
     it writes `extension-modules.txt` from `meson introspect --install-plan` and copies nothing.
     Step 58 writes `build/sklearn-build/extension-modules.txt` and checks it holds 69 modules,
     none tagged `tests` (EXECUTED: the native build's 69).

6. **The links that would collide, renamed per file by recipe** (§4.1: a recipe first). The
   drafting run's objects (EXECUTED, `nm -g --defined-only` over the native build) show what a
   static link would refuse. Each is renamed in the one translation unit that defines it,
   through 037's `WASI_CC_FILE_INCLUDES` rule, by a small header of `#define`s under
   `recipes/sklearn-renames/`, listed in `recipes/sklearn_file_includes.txt` (rendered with
   `@ROOT@` into `build/sklearn-build/file-includes.txt`, as 037 renders its map).
   - **Init names.** `sklearn._cyutility` → `PyInit_sklearn__cyutility` (pandas and scipy each
     have a `_cyutility`); `sklearn.ensemble._hist_gradient_boosting._gradient_boosting`,
     `sklearn.cluster._hdbscan._tree` and `sklearn.manifold._utils` take their dotted names
     (`PyInit_sklearn_ensemble__hist_gradient_boosting__gradient_boosting` and so on); their
     partners `sklearn.ensemble._gradient_boosting`, `sklearn.tree._tree` and
     `sklearn.tree._utils` keep theirs. `scripts/gen_inittab.py`'s rename table gains the four.
     No other scikit-learn module name clashes with numpy's, pandas', scipy's, matplotlib's,
     Pillow's, kiwisolver's or contourpy's (EXECUTED: the native module lists compared).
   - **The svm helpers.** `_libsvm.pyx`, `_libsvm_sparse.pyx` and `_liblinear.pyx` each
     `#include` a helper C file (`libsvm_helper.c`, `libsvm_sparse_helper.c`,
     `liblinear_helper.c`) whose functions are global; the static libraries `libsvm-skl` and
     `liblinear-skl` and the `_newrand` module each define the random generator of
     `src/newrand/newrand.h` (`mt_rand`, `set_seed`, `bounded_rand_int`). Defined twice or more:
     `copy_intercept`, `copy_n_iter`, `copy_nSV`, `copy_probA`, `copy_probB`, `copy_support`,
     `copy_sv_coef`, `free_model`, `free_param`, `get_l`, `get_nr`, `set_parameter`,
     `set_verbosity`, `set_problem`, `csr_set_problem`, `free_problem`, `mt_rand`, `set_seed`,
     `bounded_rand_int` (19). The renames: `_libsvm`'s keep their names;
     `_libsvm_sparse`'s fifteen take `sklearn_libsvm_sparse_`; `_liblinear`'s take
     `sklearn_liblinear_`, in `_liblinear`'s generated C **and** in `src/liblinear/linear.cpp`,
     which defines the `set_seed` that `liblinear_helper.c` calls; `libsvm_template.cpp`'s
     generator takes `sklearn_libsvm_`; `_newrand`'s takes `sklearn_newrand_`.
   - **Why per file, not merged.** Natively each module holds its own copy of the generator,
     with its own state. Renaming keeps three generators, as natively. Merging them would make
     the libsvm and liblinear fits share one state. Every fit seeds its generator first
     (`svm.cpp:2378`, `:2664`, `liblinear_helper.c:187`, READ), so results would not change, but
     separate copies need no argument at all.
   - **Each entry matches exactly one compile.** A Cython module's source is the C file meson
     generates inside the module's `.p` folder; each entry's suffix is chosen to match one
     compile command, and step 58 dies unless the include log shows each entry exactly once,
     as 037's step 57 does.
   - **Step 60's detector is the authority.** The list above is the native build's. The wasm
     link may show more or fewer (a C++ inline function the native build emitted weak, a name
     shared with numpy, pandas or scipy). Each one step 60 names is fixed by a header entry,
     never ignored, and the landing notes list the final set.

7. **One carried patch: the HTML representation's styles read as package resources.**
   `recipes/patches/scikit_learn-1.9.1/0001-html-repr-styles-from-a-zip.patch` (§4.1, spec
   020's mechanism).
   - **What fails.** `sklearn/utils/_repr_html/estimator.py` sets
     `_CSS_STYLE = _get_css_style()` at import, reading `estimator.css`, `params.css` and
     `features.css` through `Path(__file__).parent`; `sklearn/base.py:24` imports it, and so does
     `sklearn/utils/__init__.py:19`. From a zip the path's parent is not a folder. In the model
     of the guest's import path (EXECUTED): `import sklearn`, `import sklearn.base` and
     `from sklearn.linear_model import LinearRegression` each raise
     `NotADirectoryError: [Errno 20] Not a directory: '…/python315.zip/sklearn/utils/_repr_html/estimator.css'`
     (tool output, path shortened). `estimator_html_repr` also opens `estimator.js` the same
     way. Upstream `main` still reads all four by path (READ, 2026-10-18).
   - **The change** (1 file, +8 −10, SHA-256
     `1aafac3873917af878a8174a3431fafdada6e05ad49cd17fb37297b5af74b12b`, applies to the pinned
     sdist with `git apply` and no offset, EXECUTED): the four reads go through
     `importlib.resources.files(__package__)`, which reads a file on disk and a member of a zip
     alike; `pathlib.Path`'s import goes. The JavaScript file, which is UTF-8 (two `✔`), is read as
     UTF-8 rather than in the locale's encoding, as upstream `main` already reads it.
   - **Why a patch and not a recipe.** The reads are scikit-learn's own lines, run at import. A
     recipe would have to replace scikit-learn's file in the zip, an unrecorded source change
     (§7).
   - **What it changes, measured** (EXECUTED): with the patch, from the zip model, scikit-learn
     imports; `estimator_html_repr` of a pipeline gives the same 55,811 characters, SHA-256
     prefix `e469424e…`, as the stock package on disk (counters normalised); `all_estimators()`
     finds the same 208; the golden job prints native's output byte for byte.
   - **Its facts sheet**, `context/upstream/10-scikit-learn-html-repr-from-a-zip/pr.md` with
     `fix.patch`, `notes.md` and `evidence/` (question 80's form: scikit-learn's policy asks that
     no AI-written text go into an issue or pull request description, READ,
     `doc/developers/contributing.rst`, "Automated Contributions Policy", and its `AGENTS.md`
     requires a disclosure). When this specification is built, `fix.patch` is copied byte for
     byte to the path above and `pr.md` moves unchanged to
     `context/upstream/patches/scikit_learn-1.9.1/0001-html-repr-styles-from-a-zip.md`, as 041
     does for its two. Nothing is sent; the owner decides whether to engage.

8. **The extension modules become builtins.** Step 60 adds `sklearn` to its package loop
   (023's install-path inittab names, from `extension-modules.txt`) and to the `_host` line:
   each module's archive and its `.deps` (the `libsvm-skl` and `liblinear-skl` archives,
   linked once though two modules list `libsvm-skl`). Nothing new is needed: `-lsetjmp`, the C++
   runtime libraries and `-lwasi-emulated-mman` are there after 023 and 037.
   - **Constructors** (023's check). Three are new and known: the C++ dynamic initialisers of
     `mt_rand` (`std::mt19937 mt_rand(std::mt19937::default_seed)`, `newrand.h:22`) in
     `libsvm_template.cpp`, `linear.cpp` and `_newrand`'s generated C++. Each seeds a generator
     and touches no Python (READ). The builder lists every constructor the build shows and reads
     its source; the reviewed list grows by exactly those names (a judge change).
   - **No new import reaches the guest** (§4.4): the svm code's two `fopen` calls
     (`save_model`, `load_model` in `linear.cpp`) are wasi-libc's, already imported; scikit-learn
     never calls them (READ).

9. **What is in, what is out, and how an absence shows.** Each line below is a check or a golden
   line (Decision 13), and each goes in the README.
   - **In:** every public submodule. The bundled datasets load from the zip through
     `importlib.resources`, unchanged (`load_csv_data`, `load_gzip_compressed_csv_data` and
     `load_descr` open the resource and pass a file object; READ, `datasets/_base.py:377-490`):
     `load_iris`, `load_digits`, `load_diabetes`, `load_breast_cancer`, `load_wine`,
     `load_linnerud`, with their descriptions.
   - **Serial, accepted, same result:** every `n_jobs`. joblib finds no `_multiprocessing`, so
     its `mp` is `None` (`joblib/_multiprocessing_helpers.py:13-19`, READ), its default backend is
     `threading`, and with `mp` `None` every backend's `effective_n_jobs` is 1, so `Parallel`
     runs in the calling thread (`_parallel_backends.py:315-318, 528-529, 653-656`, READ); the
     memo saw `n_jobs=2` give `n_jobs=1`'s result in the guest (finding 4f, EXECUTED there).
     scikit-learn's OpenMP `n_threads` is 1 (Decision 3). `threadpoolctl` finds no native pools
     (039's `dllist`), so `threadpool_limits` is a no-op, as KMeans uses it.
   - **Absent by the sandbox, documented, not gaps:**
     - `sklearn.datasets.fetch_*` (OpenML, California housing, 20 newsgroups, LFW, covtype,
       KDD, RCV1, species, Olivetti): they download (no network, §4.15) and cache under
       `~/scikit_learn_data` (no `HOME`, nothing writable by default). The build records the
       exception `fetch_california_housing()` raises; the README names it.
     - `load_sample_image` and `load_sample_images`: the two JPEGs are left out (Decision 10),
       so they raise `ModuleNotFoundError: No module named 'sklearn.datasets.images'`. They
       could not be decoded anyway: 023's Pillow has no JPEG decoder (042, Decision 8).
     - A pipeline's `memory=` cache and `joblib.Memory` need a writable folder (039, Decision 9).
   - **The 32-bit platform** (§4.11): `np.intp` is 32 bits, so scikit-learn's index arrays are
     `int32` where native ones are `int64`. Results do not depend on it; a printed dtype would,
     so the golden prints none.

10. **The zip.** Step 70 gains `--tree "$B/sklearn-install"`, `--metadata
    "$B/scikit_learn-1.9.1/PKG-INFO"` (033's option; `Name: scikit-learn`, `Version: 1.9.1`,
    READ) and `--leave-out sklearn/datasets/images/` (042's option).
    - **Why the sample images are left out.** `china.jpg` and `flower.jpg` are under Creative
      Commons Attribution 2.0 (READ: `sklearn/datasets/images/README.txt`), a licence the owner
      has not approved (§4.12), and the guest cannot decode them. The folder goes whole, its
      `__init__.py` and `README.txt` too, so the loaders fail by name rather than return an
      empty set. Question 83 asks the owner to confirm.
    - **What stays that is not code:** the six datasets' CSV files and descriptions, the HTML
      representation's CSS and JavaScript, and 24 Tempita templates (`*.tp`) and one `.pxi.in`
      that an install also carries. Members cost fuel on a plain start; trimming them needs an
      import trace (039's Scope) and is out of scope.
    - `scripts/make_stdlib_zip.py` is otherwise unchanged: tests, sources, `meson.build` and
      `.pyi` are skipped by its existing rules.

11. **Licences** (§4.12). scikit-learn is approved (decision 43, BSD-3-Clause). What its source
    bundles was read while drafting; question 83 asks the owner to approve the bundled
    components by name, and the build waits for that answer.
    - `LICENSES/scikit-learn.txt`: `COPYING` (BSD-3-Clause, its `license-files`), then each
      bundled notice, labelled with its path in the sdist: libsvm's (BSD-3-Clause style, the
      header of `svm/src/libsvm/svm.cpp`, lines 1-30, cut as `hacl_notice` cuts HACL*'s);
      liblinear's `svm/src/liblinear/COPYRIGHT` (BSD-3-Clause style); `externals/array_api_compat/LICENSE`
      and `externals/array_api_extra/LICENSE` (MIT); the MIT header of `externals/_arff.py`
      (liac-arff); the BSD-2-Clause header of `externals/_packaging/version.py` (packaging);
      and the public-domain statement of `utils/src/MurmurHash3.cpp`. `externals/_scipy` is
      scipy's code (BSD-3-Clause, already shipped with scipy's notice).
      `externals/_numpydoc/docscrape.py` is numpydoc's (BSD-2-Clause) and carries no header, so
      its notice is numpydoc's own `LICENSE.txt`, pinned by an immutable URL in the licence
      block of `00_download.sh`, as 039 pins the MPL text:
      `https://raw.githubusercontent.com/numpy/numpydoc/894c8c47646fcbb4eae4fca068c229ae761f7a62/LICENSE.txt`
      saved as `numpydoc-894c8c47-LICENSE.txt`, SHA-256
      `0b78243e9446fe949093d69a7656b3d147d6b98bc48c975c9b4c290d8159033d`, 1,298 bytes (EXECUTED:
      the last commit to touch the file, and its bytes equal `main`'s). The builder lists every vendored component
      against a part of this file, as 037 does for scipy's.
    - `scripts/assemble_artifacts.py` builds that file and adds `scikit-learn` to `PACKAGES`.
    - **Data.** The six bundled datasets ship as scikit-learn distributes them, with no notice of
      their own in the sdist (EXECUTED: no licence text in `datasets/descr/*.rst` or beside the
      CSVs). Question 83 names them so the owner's approval covers them by name.

12. **What the set costs, so growth can be told from regression.** The base is whatever main
    holds when the builder starts (037, 038, 039, 042 and 043 all move it). This
    specification's own growth, each measured by the build and recorded in the landing notes:

    | metric | expected | finding if outside |
    |---|---|---|
    | `python.wasm` bytes | about +5.5 MB (INFERRED: Pyodide 314.0.7's scikit-learn `.so` total, 6.0 MB, times the 0.92 ratio; the memo's finding 6) | +3.5 to +8.5 MB |
    | the zip's members | +411 (410 and one `METADATA`; EXECUTED while drafting, step 70's rules) | any other count without a named reason |
    | the zip's bytes | about +3.27 MB (3,269,711 as the members stand alone, EXECUTED) | ≤ +3.5 MB |
    | plain `-c pass` | +411 × 26,900 ≈ +11.1 M (039's per-member cost after 035), plus 69 inittab entries and three constructors, measured and named | ≤ +411 × 30,000 = +12.3 M, plus the named rest |
    | snapshot `-c pass` | +411 × 2,399 ≈ +1.0 M (039's review) | ≤ +411 × 3,500 = +1.44 M |
    | the snapshot's bytes | `python.wasm`'s growth plus about 366 per member | — |
    | 033's metadata check and 035's comparison | one more distribution: ≤ 25 M per read (039's row) | above it |
    | every existing golden job | the plain-start growth above only; none imports scikit-learn | more |

    The wheel grows by about the zip's growth and `python.wasm`'s, deflated; the landing notes
    record its size against PyPI's 100 MiB file limit (question 64).

13. **The checks**, each seen failing first.
    - **The oracle.** `tests/jobs/oracle/pyproject.toml` gains `scikit-learn==1.9.1`. On macOS
      arm64 PyPI has one cp315 wheel, `macosx_12_0_arm64` (SHA-256 `e1b46824…8942`, READ); it
      calls BLAS only through the oracle's scipy, which 037 pins to one LAPACK. `uv.lock` records
      it. `oracle_env` gains `OMP_NUM_THREADS=1`: the native wheel has OpenMP, and one thread
      gives one summation order (EXECUTED: the draft's output was the same with and without it
      on a 10-core host, so this is a guard, not a fix). The other goldens must still reproduce
      (`regen.py --check`).
    - **The recording platform:** darwin-arm64, by 037's rule, since PCA and the linear models
      reach LAPACK.
    - **How values are printed:** 037's rules. Floats with significant digits,
      `format(float(x) + 0.0, ".9g")` for direct results and `".6g"` for iterative ones; solvers
      given tolerances far tighter than the printed digits (`tol=1e-12` for logistic regression,
      `tol=1e-10` and `max_iter=100_000` for `LinearSVC`); no dtype, timing or iteration count
      that depends on the path; every input fixed or seeded.
    - **Golden job (v1.3), `tests/jobs/machine_learning.py`,** in `JOBS`, its golden written by
      `regen.py`. As drafted and run (EXECUTED natively under hash seeds 0 and 1, equal; and from
      the zip model with the patch, equal to native byte for byte): the versions line
      (`importlib.metadata`, scikit-learn, scipy, numpy, pandas, joblib, threadpoolctl,
      narwhals); the five datasets' shapes, iris's names and first row, a description's first
      line; a decision tree (node count, depth, importances, accuracy, confusion matrix); a
      scaled logistic regression (accuracy, coefficients, one row's probabilities); a random
      forest with `n_jobs=1` and `n_jobs=2` (accuracy, importances, the two equal); KMeans
      (inertia, cluster sizes); PCA (explained variance ratio, `|components|`); linear and ridge
      regression on diabetes; an RBF `SVC` on breast cancer (accuracy, support vector counts,
      AUC) and a `LinearSVC`; a k-d tree k-NN's five-fold scores on digits; a
      `HistGradientBoostingClassifier` on wine; a `ColumnTransformer` with `OneHotEncoder` over a
      pandas frame; TF-IDF on four sentences; a fitted forest through `joblib.dump` and `load` in
      memory, predicting the same. The draft is not repository code: the builder writes the job
      from it, clean under `ruff format` and `ruff check`.
    - **Behaviour (v1.3, `tests/checks/test_v1_3_default_profile.py`, 039's file), each on both
      binaries with nothing writable unless named:**
      - `test_scikit_learn_runs_without_threads[plain, snapshot]`: with warnings as errors,
        `_openmp_parallelism_enabled()` is `False`; `_openmp_effective_n_threads(-1)` is 1;
        `joblib.effective_n_jobs(-1)` is 1; a forest fitted with `n_jobs=-1` predicts what
        `n_jobs=1` predicts; `threadpool_info()` is `[]`; a KMeans fit returns, inside the
        call's fuel limit.
      - `test_scikit_learn_reads_its_files_from_the_zip[plain, snapshot]`: the six loaders give
        native's shapes; `estimator_html_repr(make_pipeline(StandardScaler(),
        LogisticRegression()))` holds a line of `estimator.css` (the patch's proof); `len(all_estimators())`
        equals native's 208 (EXECUTED in the zip model).
      - `test_scikit_learn_says_what_it_lacks[plain]`: `load_sample_images()` raises
        `ModuleNotFoundError` naming `sklearn.datasets.images`; `fetch_california_housing()`
        raises the exception the build recorded, inside the fuel limit.
      - `test_scikit_learn_modules_are_builtin[plain, snapshot]`: each of the 69 names in the
        build's list imports and is built in, by the form 023's and 037's checks use; the four
        renamed modules among them.
    - **Rules and artifact checks (judge changes, under `--accept-judge`):** v1.1, 023's
      constructor list gains the reviewed scikit-learn names (Decision 8); v1.1,
      `test_the_sample_images_are_not_in_the_zip` (no member under `sklearn/datasets/images/`);
      v1.5, `SOURCE_PATTERNS` and `needs.SOURCE_COMPONENTS` gain `scikit_learn`, the release
      workflow's tree count rises by one, the patched-tree check covers the patch; rules, spec
      020's `patch_errors` passes on the patch and its draft, and `scan.cpp_exception_errors`
      judges `recipes/wasi-sklearn.cross`; `paths.PACKAGES` and `LICENCE_COMPONENTS` gain
      scikit-learn; 033's `test_packages_carry_their_metadata` gains it.
    - **Build-time gates, not judge checks:** the OpenMP gate (Decision 3); the per-file include
      log (Decision 6); the module count; step 60's clash detector; the staged cimports
      (Decision 4).
    - **Unit checks** (no artifacts), each seen failing before its code exists:
      `install_from_plan.py --modules-only` on a small install plan (the list written, nothing
      copied); `gen_inittab.py`'s four new renames and its clash check on them;
      `stage_scipy_cimports.sh` against a fake scipy build folder (the six files placed; a
      missing one named).

14. **Ordering, and one builder** (§5.7: one build-class specification in flight, one landing at
    a time).
    - **It builds after 038 and 039, and after 042.** 037 and 038 bring scipy whole (and the
      machinery this reuses); 039 brings joblib, threadpoolctl with `dllist`, narwhals and the
      check file; 042 brings `--leave-out`. The queue already puts 039 after 038, and 041 and
      042 after 039 (their Decisions 9 and 13). If 042 has not landed when this is confirmed and
      everything else has, this builds first and adds `--leave-out` exactly as 042's Decision 5
      describes, and 042 then uses it.
    - **045 (statsmodels) builds right after this one.** It reuses Decision 4's staging and this
      step's pattern. If this specification stalls (AGENTS.md rule 7), 045 may build first and
      brings `stage_scipy_cimports.sh` itself.
    - **046 (lxml) and 047 (regex)**, drafted alongside: no dependency either way. Question 82
      asks whether they may build before scipy; if they have not landed when this is
      confirmed, whichever is confirmed for build first builds first. The second rebases onto
      the other's step 60, step 70, `gen_inittab.py`, `00_download.sh` and
      `assemble_artifacts.py`, and re-derives its growth bounds from what it really adds. Their
      steps (36, 53, 54) do not collide with 58.
    - **Files shared with others:** steps 60 and 70, `gen_inittab.py`, `install_from_plan.py`,
      `make_stdlib_zip.py`, `assemble_artifacts.py`, `00_download.sh` (023, 033, 035, 037,
      039, 041, 042, 043). Each is rebased onto main as it is when this builder starts.
    - **Not split; built in four stages, each green before the next:** (1) the pin, the patch
      and its facts sheet, the staged cimports, the cross file and `meson setup` alone, with the
      OpenMP gate (if meson refuses the cross build, the builder stops and writes a memo);
      (2) `ninja`, the renames and the include log; (3) step 60 with the clash detector and the
      constructors, step 70; (4) the oracle, the job, the checks, the README and the account.

## Intent

An agent's code in the default profile fits, predicts, scores, clusters, decomposes and
pipelines with scikit-learn, on its bundled datasets or its own data, and gets native
scikit-learn's answers, serially, inside the same sealed Python. One recorded, temporary patch
lets scikit-learn read its own style sheets from the zip.

## Design

| file | change |
|---|---|
| `downloads/SHA256SUMS`, `scripts/00_download.sh` | the sdist, and numpydoc's licence text in the licence block (Decisions 2, 11) |
| `scripts/steps/58_sklearn.sh` | new: unpack, patch, stage cimports, render the map, configure, the OpenMP gate, build, the include log, stage the package, the module list (Decision 5) |
| `scripts/stage_scipy_cimports.sh` | new: `build/scipy-cimport/` (Decision 4) |
| `recipes/wasi-sklearn.cross` | new (Decision 5) |
| `recipes/sklearn_file_includes.txt`, `recipes/sklearn-renames/*.h` | new: nine entries (four init names; `_libsvm_sparse`, `_liblinear` with `linear.cpp`, `libsvm_template.cpp`, `_newrand`), eight headers (Decision 6) |
| `recipes/patches/scikit_learn-1.9.1/0001-html-repr-styles-from-a-zip.patch` | new: `../upstream/10-scikit-learn-html-repr-from-a-zip/fix.patch`, byte for byte (Decision 7) |
| `context/upstream/patches/scikit_learn-1.9.1/0001-html-repr-styles-from-a-zip.md` | moved from `../upstream/10-…/pr.md`, unchanged |
| `context/upstream/README.md`, `context/upstream/10-…/notes.md` | the row says the patch is carried; `fix.patch` removed from the folder |
| `scripts/install_from_plan.py` | `--modules-only` (Decision 5) |
| `scripts/gen_inittab.py`, `scripts/steps/60_link.sh` | scikit-learn's modules and archives, four renames (Decisions 6, 8) |
| `scripts/steps/70_zip.sh` | the tree, its metadata, the images left out (Decision 10) |
| `scripts/build.sh`, `scripts/assemble_artifacts.py`, `LICENSES/` | step 58 in `ALL`; `PACKAGES`; `LICENSES/scikit-learn.txt` (Decision 11) |
| `tests/jobs/machine_learning.py`, `.expected`; `tests/jobs/oracle/pyproject.toml`, `uv.lock`; `tests/harness/jobs.py` | the golden, the oracle's pin and `OMP_NUM_THREADS=1`, `JOBS`, the recording platform (Decision 13) |
| `tests/checks/test_v1_3_default_profile.py` | the four behaviour checks |
| `tests/checks/test_v1_1_artifact_set.py`, `tests/harness/paths.py`, `pins.py`, `needs.py`, `scan.py`, `tests/checks/test_v1_3_data_stack.py` | the judge changes (Decision 13) |
| `tests/unit/…` | the three unit checks |
| `.github/workflows/release.yml` | the tree count, one more |
| `README.md`, `CHANGELOG.md` | scikit-learn in "What the default profile carries"; serial `n_jobs`, no OpenMP, the absent fetchers and images, the 32-bit index arrays; the patch by path |

## Scope

In: Decisions 1 to 14. Out:

- **statsmodels**, with formulaic, interface-meta and wrapt: spec 045.
- **OpenMP or threads.** A later SDK with an OpenMP runtime would still need threads in the
  guest.
- **The fetchers' data** as pinned files in the zip, and the sample images.
- **Pre-importing scikit-learn in the snapshot.** The landing notes record `import sklearn`'s
  fuel on both binaries and the snapshot's bytes and `pass` fuel if it pre-imported it, so the
  owner can decide later, as for scipy (question 61).
- **Trimming** templates, descriptions or `externals/_numpydoc` from the zip.
- **scikit-learn's own test suite under the runtime** (roadmap milestone 6).

## Acceptance criteria

1. **The checks exist and were seen failing first** on the set the builder starts from, each
   recorded in the landing notes: the golden and the four behaviour checks with
   `ModuleNotFoundError: No module named 'sklearn'`; `test_scikit_learn_reads_its_files_from_the_zip`
   and the golden again on a build without the patch (`NotADirectoryError` at `import sklearn`),
   which the builder runs once; the images check against a zip built without `--leave-out`;
   the unit checks before their code; the constructor list without the new names.
2. **The build** went through Decision 14's four stages. A full build from pins in a clean clone
   applies the patch with no offset, passes the OpenMP gate, the include log, the module count
   and step 60's detector, and makes a set whose binaries run the golden and the checks.
   `MANIFEST` names the pin, the recipes, the scripts and the patch.
3. **The same bytes everywhere:** a manual run of the release workflow on the reviewed commit
   passes its `rebuild`, `same-bytes` (spec 012, and 040's x86_64 rule if 040 has landed) and
   zero-patch jobs with the new tree count; its run number goes in the landing notes.
4. **The judge:** `uv run pytest` is green with `--accept`, `--accept-judge` (the new checks,
   job and golden, the oracle's pin and environment, the constructor list, the package, licence
   and source lists) and `--accept-growth` (Decision 12's account, each row measured against
   its bound), and loses no pass. `regen.py --check` reproduces every golden.
5. **The numbers recorded:** the three binaries', the zip's and the wheel's bytes; the zip's
   members; the modules linked; the final rename set; the new constructors by name; plain and
   snapshot `-c pass`; `import sklearn` and the golden's fuel on both binaries; the snapshot's
   bytes and `pass` fuel if it pre-imported scikit-learn; the guest's memory after the golden;
   the exception `fetch_california_housing()` raises.
6. **The release:** a release dry run passes every job (criterion 3's run).

## The owner's choices

None open here. One is recorded in `../questions-for-the-owner.md` as **83**: the licences of
what scikit-learn bundles (libsvm, liblinear, array-api-compat, array-api-extra, liac-arff,
packaging's version module, numpydoc's docscrape, MurmurHash3, its six datasets) and of what
spec 045's statsmodels bundles; and the sample images left out. This specification is drafted
and can be reviewed; it is not built until 83 is answered, as 043 waits on 81.

## Landing notes

Not built.
