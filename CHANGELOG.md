# Changelog

One section per release of the `wasi-python` artifact set and wheel, newest first. A section's
body is the release's notes on GitHub. `release/version.py bump` adds a section; `release/version.py
release` dates it and tags the release (context/specifications/004-alpha-releases.md).

## 0.1.0a8 — unreleased

- **One module touches wasmtime-py's private API** (spec 103).
  `src/wasi_python/_wasmtime_ffi.py` is the engine seam: the runner and the mounts drive the
  engine through its named operations, it prefers wasmtime-py's public API wherever the installed
  release has it, and at the first `run()` it raises one `ImportError` naming the wasmtime-py
  version and every private name that moved. A rules check holds that no other `.py` under
  `src/` or `tests/` reaches the private API; a second holds the debt sheet
  `context/upstream/34-wasmtime-py-public-api-for-the-runner/facts.md` equal to the names the
  seam needs. No behaviour, fuel or errno changes.
- **The runner is a package** (spec 104; the runner design review's H1, M5, L1). `runner.py`
  (6,241 lines) is eleven modules, one per concern (`_limits`, `_platform`, `_artifacts`,
  `_engines`, `_private_dirs`, `_zip`, `_places`, `_home`, `_call`, `_sessions`, and `runner` as
  the thin entry), the text moved verbatim, in a written import order with no cycle;
  `__init__.py` no longer imports `runner` last; a unit check finds every module-level lock and
  proves the fork hook re-makes it; a rule holds every module under `src/` to 1,500 lines.
  Nothing the embedder sees changes: no public name, no message, no fuel count.
- **The runner's process state has one owner** (spec 105): every lock, cache, counter and
  registry of the runner is an attribute of one `_Process` object, reset for a fork by
  introspection over its locks and released at exit by one method; the judge's seams are fields
  of that object, not module globals; two rules checks keep locks and mutables out of module
  level. No public name changes.
- **The runner's checked call is a frozen typed record**, a session's and a home's life are
  transition tables the judge drives whole, and `mypy --strict` runs over `src/wasi_python` in
  the judge (spec 106).
- **The runner's mount table, platform choice, file stamps and comments explain themselves**
  (spec 107; the design review's H4, M3, M4 and M2). `mounts.py` asks nine questions of a
  call-context protocol and imports nothing from the runner; one `_platform.py` holds every
  POSIX, macOS and Windows difference behind one interface chosen once at import; the digest and
  version caches in front of the artifact check key on the full file stamp, so a same-size,
  same-time replacement is hashed again; `src/` names no specification, memo, review, finding ID
  or `context/` path, every reason kept in words, held by one rules check (the owner's rule,
  "code speaks for itself"; `tests/`, `scripts/` and `release/` follow in spec 109); and
  `mypy --strict` is clean over the whole package. No public name, artifact byte or
  guest-visible errno changes.
- **A structural review is a stage** (spec 108; the design review of 2026-10-20). A change that
  adds a module-level mutable or lock, a use of wasmtime-py's private API, a platform branch or a
  test seam outside the one place specs 103 to 107 give each, or takes a module past the size
  ceiling or a function past 80 lines, is reviewed before it is built; every release gets a
  structural review of `src/` against the design review's eight-row rubric, beside its security
  review, which the judge requires of a released version; and two rules checks hold that the
  judge patches the runner only through its process object and that no function is over 80
  lines, each with an allowance list that only shrinks. Nothing in the artifact set or the wheel
  changes.
- **Code speaks for itself outside `src/`** (spec 109). Comments and docstrings under `tests/`,
  `scripts/`, `release/` and the release workflow give their reasons in words, with no
  specification number, review, finding identifier or `context/` path; a rules check holds it,
  with the judge's allowance files, the guest's own sources and the `src/` check's own
  documentation of its shapes named as the exceptions. No code, behaviour, fuel or artifact byte
  changes; `MANIFEST`'s recipe hashes of `scripts/` move with their comments.
- **numpy's linear algebra, `dot` and `matmul` run on the set's OpenBLAS** (spec 100; questions
  106 and 107). numpy was built with no BLAS and ran its bundled `lapack_lite`, an f2c LAPACK
  3.2.2. It now finds the OpenBLAS 0.3.34 scipy uses, through numpy's own build options; a
  one-line recipe header (`recipes/numpy_lapack_abi.h`) and a file of shims
  (`recipes/numpy_lapack_shims.c`) bridge numpy's `int` declarations to OpenBLAS's `void`
  subroutines, and `lapack_lite`'s f2c code leaves the binary. A matrix of `nan` raises
  `LinAlgError` in `svd`, `lstsq` and `eigh` as natively, where it raised `ValueError: On entry
  to DLASCL …` (and `lstsq`, with spec 099 alone, `SystemError`); numpy and scipy agree on which
  matrices are singular; a 200×200 inverse, decomposition or product takes 23 to 55 percent less
  fuel, and a 3×3 product 28 percent more (OpenBLAS's call costs more than numpy's own loop at
  that size); `python.wasm` is 1,240,316 bytes smaller and the snapshot 1,237,935. A matrix
  singular only in exact arithmetic is a rounding question, and the README says how the guest
  differs there (measured on macOS arm64), and what OpenBLAS's buffer does under a
  tight memory cap. The oracle's numpy on macOS arm64 is now the OpenBLAS wheel.
- **`tools.py` is three modules behind one public facade** (spec 110). `wasi_python.tools` keeps
  every public name and nothing else of weight; the schema rules (what a tool's schema may say,
  how one is derived from a signature, how a value is checked) live in `_tool_schema.py` and the
  host side of a call (the frames, the thread, the budget, the slot table) in `_tool_host.py`,
  each under the 1,500-line ceiling, importing in one written direction; `tools.py` leaves the
  size allowance and its two functions leave the long-function allowance, split at a seam each.
  No public name, message, artifact byte or fuel count changes.
- **A singular matrix raises `LinAlgError`** (spec 099; spec 066's survey). wasm has no
  floating-point status flags, and numpy reports a failed LAPACK call by one, so
  `numpy.linalg.inv`, `solve`, `tensorinv`, `tensorsolve` and `matrix_power(a, -1)` of a singular
  matrix, and `cholesky` of one not positive definite, returned `nan`s. A recipe header,
  `recipes/npy_fenv_flags.h`, keeps the signals numpy raises itself in a software flag word: these
  raise `LinAlgError` whenever numpy's LAPACK (`lapack_lite` then; OpenBLAS since spec 100, above) finds the matrix singular;
  for a matrix singular only in exact arithmetic that is not always where native numpy does
  (LAPACKs round differently; exact parity is not a goal in wasm). The same word makes integer division by zero, integer overflow in
  division and float16 overflow warn, or raise under `np.errstate`, as natively: a widening of the
  owner's question, named here. Signals only the hardware gives (float division by zero,
  `log(0)`, invalid casts) stay silent; the README says so.

- **The release runs the compiled packages' own tests** (spec 066): matplotlib's, contourpy's,
  Pillow's, kiwisolver's, lxml's and regex's own suites, every test of each (contourpy's
  random_big, `--runslow` and `--runtext` cases included, and Pillow's `checks/` and
  `selftest.py`), in 40 groups, 17,972 passes, each package a family with its own grant, stage
  and budget (caps 1.5 times the measured fuel, 1.517×10¹³ in all, each held to its recorded
  measurement by the rules check), in fourteen new Linux release shards; known failures are 23
  classes by node id, each a gap with its closer. `tests/upstream/
  package_drive.py` drives them; numpy's and pandas' driver and verdict are unchanged.
  `tests/upstream/packages.toml`: the six are `suite`s; scipy's suite now closes with spec 095.
- **The OpenBLAS patch script no longer fails when macOS rewrites a `.DS_Store` in the unpacked
  tree** (spec 097). `scripts/make_openblas_void_patch.sh` leaves host litter out of its `git add`
  by pathspec, so git never opens a litter file, and removes a staged one with `git update-index
  --force-remove`, which a rewrite cannot refuse; the carried patches are unchanged. **The judge's
  guest folders live outside the home folder on macOS**, in the per-user temporary folder, where
  macOS's folder-size cache does not write, so a long run's writable root is no longer voided by
  host litter; the sealed stages stay under `build/harness`, and Linux and Windows are unchanged.

- **A garbage cycle holding a kiwisolver object is collected, not a trap** (spec 096; spec 066's
  survey). kiwisolver's `Variable`, `Term`, `Expression` and `Constraint` declared `tp_clear` as
  returning nothing, so the collector's call ended the guest in `indirect call type mismatch`;
  carried patch `recipes/patches/kiwisolver-1.5.1/0002-tp-clear-returns-int.patch` is upstream's
  fix (#245), until a kiwisolver release has it. **`import lxml.html.diff` works**: its
  plain-Python form lacked `cython.final` without Cython; carried patch
  `recipes/patches/lxml-6.1.3/0001-fake-cython-final.patch` is upstream's line (#477), until lxml
  7.0. **The judge's callback scan reads type slots**: static type objects and their method
  suites, `PyType_Slot` arrays and module definitions, 5,893 functions on the set with scipy, where
  spec 051's read method and getset tables.

- **statsmodels 0.15.0 built in, with formulaic 1.2.2, interface-meta 2.0.1 and wrapt 2.5.1**
  (spec 045). Its 26 compiled modules are builtins and its Python package is in the zip, with
  native statsmodels' answers on a golden job (`statistical_models`): regressions, discrete and
  generalised linear models, tests, ARIMA and the state-space models, STL, exponential smoothing,
  LOWESS and KDE, with formulas in patsy's or formulaic's syntax. formulaic, its second formula
  engine, comes with interface-meta and wrapt, all pure wheels (wrapt runs its Python classes).
  One carried patch reads the datasets as package resources when they are not files, so they load
  from the zip: `recipes/patches/statsmodels-0.15.0/0001-datasets-from-a-zip.patch` (its facts
  sheet for the owner, `context/upstream/patches/statsmodels-0.15.0/`). Sixteen public-domain
  datasets ship; the data files of thirteen whose stated terms are not approved stay out, and
  their loaders raise `FileNotFoundError`. The state-space smoothers' and `_tools`' init names are
  renamed per file (`recipes/statsmodels-renames/`). What the sandbox lacks raises: X-13ARIMA-SEATS
  (`X13NotFoundError`), `get_rdataset` and `webuse` (no network), `hdrboxplot` (no processes).
  `LICENSES/statsmodels.txt` carries its licence, the bundled code's notices and each dataset's
  terms.
- **scikit-learn 1.9.1 built in** (spec 044). Its 69 compiled modules are builtins and its
  Python package and six bundled datasets are in the zip, with native scikit-learn's answers on a
  golden job (`machine_learning`). It runs serially with the same results: no OpenMP, and every
  `n_jobs` in the calling thread. One carried patch reads its HTML representation's style sheets
  as package resources, so `import sklearn` works from the zip:
  `recipes/patches/scikit_learn-1.9.1/0001-html-repr-styles-from-a-zip.patch` (its facts sheet
  for the owner, `context/upstream/patches/scikit_learn-1.9.1/`). The names that would clash in
  one static link are renamed per file by recipe headers (`recipes/sklearn-renames/`), and step 60
  gains two checks for every package: no weak definition two archives share unless a review
  allowed it (`scripts/weak_duplicates.py`, `recipes/weak-duplicates-allowed.txt`), and the link
  map shows scikit-learn's three random generators under their own names. The `fetch_*` datasets
  fail without a network (with no root, `FileNotFoundError` on `'~'`; with a root, `URLError`);
  the two sample photographs are left out, so their loaders raise `ModuleNotFoundError`.
  `LICENSES/scikit-learn.txt` carries each bundled component's notice and the attribution of the
  three datasets UCI publishes under CC BY 4.0 (digits, breast cancer, wine).
- **scipy 1.18.1, with OpenBLAS 0.3.34 as its BLAS and LAPACK, built in** (spec 037). All of scipy
  but `scipy.odr` (it needs Fortran; importing it says so): `linalg`, `sparse` (SuperLU, ARPACK,
  PROPACK, `csgraph`), `optimize` (HiGHS's `linprog` and `milp`), `integrate`, `interpolate`,
  `signal`, `fft`, `special`, `stats`, `spatial` (qhull, `cKDTree`), `ndimage`, `cluster`, `io`
  and the rest, with native scipy's answers on three golden jobs. No Fortran compiler is used:
  OpenBLAS's own C translation of LAPACK is the LAPACK. Carried patches:
  `recipes/patches/OpenBLAS-0.3.34/0001-c-lapack-subroutines-return-void-1-of-2.patch` and
  `recipes/patches/OpenBLAS-0.3.34/0002-c-lapack-subroutines-return-void-2-of-2.patch` (OpenBLAS
  `develop`'s convention, every C LAPACK subroutine `void`, made by our own script; merged
  upstream after 0.3.34), `recipes/patches/OpenBLAS-0.3.34/0003-ilaver-returns-void.patch`, and
  `recipes/patches/scipy-1.18.1/0001-uarray-callback-signatures.patch` (five uarray callbacks) and
  `recipes/patches/scipy-1.18.1/0002-sqrtm-triu-imports-its-error-where-it-raises.patch` (so
  `scipy.linalg._matfuncs_sqrtm_triu` imports first, which pydoc's `apropos` and
  `help('modules word')` do with every builtin).
  `scipy.spatial` links the one qhull matplotlib's `_qhull` links (step 37's 8.0.2, now with a
  `qhull_r.pc`), and scipy's own fix to its vendored copy is carried for both:
  `recipes/patches/qhull-8.0.2/0001-format-strings.patch` (upstream's merged pull request 143,
  unreleased). The reactor refuses `freopen` (qhull's `TI <file>` option, its one caller, fails
  as an unopenable file does), so the `fd_renumber` import matplotlib's `_qhull` brought goes
  again. OpenBLAS's kernels use wasm SIMD: hosts need `simd128` (every supported wasmtime has it).
  Known gaps until spec 038: `mmread` and `mmwrite` raise (a thread pool); `qmc.Sobol` with nothing
  writable gives wrong numbers with exit 0 and an "Exception ignored" message (unscrambled all
  zeros, scrambled one point repeated; `differential_evolution(init='sobol')` and
  `shgo(sampling_method='sobol')` with it; give a temporary folder);
  `geninvgauss.cdf`, `genhyperbolic.cdf`, `studentized_range` and `loadarff` raise `OSError`
  from the `ctypes` stand-in. `fft`'s `workers=` runs serially; `differential_evolution` and
  `brute` with `workers` other than 1, and `cKDTree.query(workers=...)` other than 1, raise.
  numpy's own LAPACK (`lapack_lite`) now carries a symbol prefix so it cannot meet OpenBLAS's;
  numpy computes as before. (Later in this release numpy links the same OpenBLAS and `lapack_lite` leaves the binary: spec 100, above.) The set is the same bytes from every build host with no exception:
  wasi-sdk 34 (spec 086) compiles scipy's ducc0 FFT to one object, so the same-bytes exception
  this specification built on wasi-sdk 33 was withdrawn before it landed.
- **scipy's sandbox edges work** (spec 038; spec 037's three known gaps closed). With nothing
  writable and no thread: `scipy.io.mmread` and `mmwrite` read and write serially, since
  Matrix Market's default parallelism is 1 on WASI
  (`recipes/patches/scipy-1.18.1/0003-io-matrix-market-serial-without-threads.patch`);
  `stats.qmc.Sobol`, `qmc_quad`, `sobol_indices` and the Sobol options of
  `differential_evolution` and `shgo` read the direction numbers' bytes from the zip without a
  temporary file, so they no longer give wrong numbers with exit 0
  (`recipes/patches/scipy-1.18.1/0004-stats-sobol-without-a-temporary-file.patch`); and
  `geninvgauss.cdf`, `genhyperbolic.cdf`, `studentized_range`, `tukey_hsd` and `loadarff` work.
  **Changed:** the `ctypes` stand-in holds values: an instance of a numeric type
  (`c_int(5).value`, `c_ulong(-1).value == 4294967295`, `c_float` rounded to single precision)
  or of `c_void_p` (a 32-bit integer, or None), and `cast(x, c_void_p)` of an integer, None or a
  `c_void_p`, where each raised `OSError` before; numpy's `ndarray.ctypes.data` and
  `data_as(ctypes.c_void_p)` give the array's address. An instance is false when its value is
  zero and unhashable, as in CPython; `c_void_p` takes only an `int`; its bytes cannot be read
  (`bytes()` and `memoryview()` of it raise `OSError`). Nothing has an address: `byref`,
  `pointer`, `addressof`, typed pointers, strings, structures and every library load still raise
  `OSError`, and `-V` still says "no ctypes".

- **Added: seaborn 0.13.2 and reportlab 5.0.1** (spec 042; the owner's decision 43), pure
  Python, with native Python's output on two golden jobs: seaborn's relational, distribution,
  categorical, grid, matrix and `seaborn.objects` plots, its regression, kernel densities,
  violins and clustering (through scipy, whose import `import seaborn` now pays); reportlab's
  canvas and platypus PDFs, charts through `renderPDF` and `renderSVG`, Unicode text and images.
  seaborn comes from its sdist, whose `licences/` folder holds the notices of the five pieces of
  code it vendors; `LICENSES/seaborn.txt` carries them. reportlab is its wheel, **without its
  fonts** (their licences are not approved, and reportlab cannot read its own files from a zip
  on any Python from 3.13; for Unicode text register DejaVu Sans from `matplotlib.get_data_path()`)
  and, until a later change ships it, **without its barcode folder**. `LICENSES/reportlab.txt`
  carries the third-party notices its code holds only as comments: Tyler C. Sarna's (the barcode
  modules), Adobe's (the glyph list) and the QR encoder's with the MIT text. reportlab writes
  PDFs in memory with nothing writable (`invariant=1` for repeatable bytes); `renderPM` raises
  `RenderPMError` (no rlPyCairo). seaborn needs a writable `MPLCONFIGDIR`, as matplotlib does;
  `sns.load_dataset` cannot fetch (through the runner with a writable root, its cache folder
  goes under the runner's fresh `HOME` in `/tmp`, removed after the call; an embedder that gives
  a writable root and no `HOME` gets a folder `/~/.cache/seaborn` in that root): read a granted
  CSV with `pd.read_csv` instead.
- **The judge: spec 084's read-only removal rows are blocked on Windows by a named need** (spec
  094). A Windows guest deletes a read-only file itself (084's C2, settled by wave 01's dry run),
  so the rows that check a removal keeps such a file now name the need `read-only files`, unmet on
  Windows alone, instead of skipping without a need; the release's gather allows that block on
  Windows only. Nothing changes for the product.

- **A desktop's files never change the build** (spec 090). The build skips one shared list of
  names an operating system writes into folders (`.DS_Store`, AppleDouble `._x` files, `Icon\r`,
  `Thumbs.db`, `desktop.ini`, `ehthumbs.db` and a volume's own folders such as
  `.TemporaryItems`), where it skipped three: in the stdlib zip's walk, the licences and the
  artifact set's list. The release tarball packs exactly the files the set's `SHA256SUMS` lists,
  never the folder. The judge's set and wheel checks forgive those names and no others, and the
  wheel may carry nothing the list does not name. Step 20 removes the bytecode CPython's build
  writes into `Lib/` (its build-Python runs with `-E`, and its WASI interpreter under wasmtime
  sees no host variable), and the test suites' `left_out` fact no longer records bytecode or
  litter, so two trees built from the same pins record the same facts. The artifacts' bytes do
  not change.

- **Each guest runs on a stack of its own** (spec 078; question 102). The runner runs every guest
  on a thread it makes for the call, with 10 MiB of stack, 8 MiB of it for wasm (it was 512 KiB
  on the caller's thread), and checks that thread's stack before any wasm runs. Recursion in C
  over nested data (`repr`, `==`, `json` both ways), the parser, deep exception groups, expat's
  callbacks, XPath and XSLT now raise instead of ending the call in a trap; freeing nested
  structures, deep `hash`, long expressions, C14N, RelaxNG and very high recursion limits still
  trap, 10 to 16 times deeper (the README lists them). A recursing guest can no longer kill a host
  whose calling thread is small, such as musl's 128 KiB threads and `run_async`'s pool there. Your
  `host` function and providers still run on the thread that called `run`. Ctrl-C now stops a
  guest that computes without calling back, and an embedder's SIGINT handler that raises stops
  the call instead of being lost. Spec 065's nine trap entries close: their tests run in their
  groups, `test_traceback` whole. **Changed:** each running guest holds one more thread (10 MiB
  of stack reserved; committed on Windows); a door or provider call costs one thread hand-off
  each way; every call's epoch deadline is checked every 50 ms. On CPython 3.14.0 on musl every
  call is refused (use 3.14.1 or later), and so is every call on a platform whose thread stack
  the runner cannot read (FreeBSD; any but Linux, Android, macOS and Windows). No public name,
  signature or default changes; fuel does not change.
- **The release's gather checks what it trusts** (spec 085; the 0.1.0a7 security review's F5, F6,
  F7 and N5). A shard's record may report a check blocked only by a need that check's own code
  asks for, and only on a system that lacks it (F6). Its unit-test tally must equal its share,
  as whole numbers, and every passing check must carry each metric the lane accepted for it, as
  a number; every record must name the wasmtime `uv.lock` names (F7). Each acceptance's history
  line now records the hash of the artifact set's own `SHA256SUMS`, the build job hands the same
  hash on, and the gather requires the two to agree, so the lane's acceptance covers the
  snapshot, the zip, `MANIFEST` and the licences as well as `python.wasm` (F5). The rebuild jobs
  print the runner's own `python3 --version` (N5). The gather checks consistency, not
  authenticity: a compromised judge job could still write consistent records, though never
  change the bytes that are signed or published.

- **Fixed: a guest could make its private root outlive the call** (spec 084; the 0.1.0a7
  security review's F1). A guest given `root=True` that built a tree one level at a time through
  `dir_fd`, deeper than the process's free descriptors (247 levels at macOS's default soft limit
  of 256), left its private root and lock file behind, silently, and the next process's sweep
  failed the same way, so disk use added up across calls; a deep fresh `HOME` was left in the
  caller's root the same way. The runner now removes its folders with a walk that holds two
  descriptors at any depth, creates nothing, never follows a link and changes no mode, so
  content the host made read-only is left, never deleted, even when the guest moves it in. A
  folder a removal leaves is named in one `RuntimeWarning` per process; a private folder keeps
  its lock file and is retried by the next call's sweep (three times per process, then by the
  next process). A `HOME` in a caller's root, which another call on that root may be writing,
  gets a budget of about a million system calls. No public name, default or field changes.
- **Fixed: on CPython 3.11 a guest could make `run` raise `RecursionError`** and keep its
  private root's lock for the process's life (spec 084). 3.11's `shutil.rmtree` recurses one
  frame per level, so a private root of more than about 995 levels (1,010 at Linux's common soft
  limit of 1,024) made the removal raise out of `run`. The new removal does not recurse, and a
  removal that fails in any way now leaves the folder with its lock free for the sweep.
- **The abandoned-turn check holds its guest instead of racing it** (spec 093). Spec 078's check
  that a turn forced out of its home keeps its session busy read `busy` while the stopped guest
  was ending, and on Windows the guest ended first. It now holds the guest thread on a gate
  until it has looked, and checks that the teardown runs on the guest thread. The runner does
  not change.
- **The judge compares a release run with a local one** (spec 092). The release's merged record
  now carries what the comparison needs (the checks no shard ran, the files collected, each shard's
  unit tally, anything that steered a shard, and which system's run each check's row comes from),
  and `tests/harness/sameness.py` reads it as the darwin run it contains. With `--claims`, it
  prints only the differences no specification's claim list explains. Judge only: no product
  change.
- **Changed: the toolchain is wasi-sdk 34** (clang 23.1.0, wasi-libc `2e6fb9d8` with musl 1.2.6,
  libc++ 23.1.0; spec 086). wasi-sdk 33's clang nested `try_table` blocks by heap address in one
  pass of its WebAssembly backend, so some C++ (scipy's FFT, coming) compiled to different bytes on
  every run; LLVM 23 fixed it. Every artifact's bytes change once, and every build host still gives
  the same `SHA256SUMS`, with no exception. The judge compiles the reduced case 64 times with each
  pinned clang and expects one object, and records every `#define` of the guest's `pyconfig.h`.
  Programs now see `os.dup2`, `os.pipe2` and `time.pthread_getcpuclockid`, each raising
  `OSError` `ENOTSUP`, and `select.PIPE_BUF` (4096): wasi-libc 34 declares them as stubs.
  `os.dup` keeps `ENOTSUP`: wasi-libc 34's `fcntl` answers its two dup commands `EINVAL` on WASI
  preview1 while its `dup` answers `ENOTSUP`, so a new link-time refusal,
  `recipes/fcntl_dup_refusal.c`, gives `dup`'s answer (a facts sheet for wasi-libc,
  `context/upstream/25-wasi-libc-fcntl-dupfd/`). GB18030 stays refused: musl 1.2.6's decoder still
  has the bug.
- **Changed: strings hash with SipHash-1-3** (spec 086; the 0.1.0 security review's S5). CPython's
  configure falls back to 32-bit FNV when a cross build cannot run its aligned-access probe, and
  the guest hashed `str`, `bytes` and `memoryview` with FNV, which crafted keys can flood whatever
  its key (PEP 456). Step 20 now passes `--with-hash-algorithm=siphash13`, CPython's own default:
  `sys.hash_info.algorithm` is `'siphash13'` on both binaries, kept in 32 bits on wasm32. The
  snapshot's key stays fixed and public, which the README's *Not protected* list now says.
- **Fixed: a missing stdlib module says why.** The zip now carries `_missing_stdlib_info`, which
  CPython's build generates beside `_sysconfigdata`, so `import _tkinter` fails with
  "Unsupported platform for standard library module '_tkinter'" as natively, not "was not found"
  (spec 086; spec 078's build review, F2).
- **The judge's inline pytest sessions keep wasmtime's signal handlers** (spec 082; spec 080's
  review, F1). A pytest session the judge runs inside its own process ended by switching
  faulthandler off and on again, which dropped wasmtime's handlers on Linux, so the runner's
  guard refused 16 later unit tests in a serial run. The judge's `pytester` now runs every such
  session with `-p no:faulthandler`, and a check holds it. The runner does not change.
- **CPython's own tests in the judge and the release** (spec 065). The judge runs CPython's own
  regrtest suite in the guest: 542 of its 557 modules in five groups, 28,109 passing tests, each
  known failure a class by test id with its closer, each test it does not run named, each result
  that differs by host recorded per system (26, most of them Windows file rules), and the eight
  tests where freeing or parsing deep structures still traps the guest (spec 078) each a gap. The
  judge states each guest clock's resolution instead of passing the host's through. The release
  runs the five groups on Linux in its existing upstream shards, and the file-system group on
  macOS and Windows too. `python` now names its suite in `tests/upstream/packages.toml`. The
  hostile-guest checks that read MANIFEST are blocked, not failed, without an artifact set.
- **The judge answers a file's times and inode number itself** (spec 083). Its guest driver
  forwards the guest's file-stat and listing calls to wasmtime and answers the times from its own
  stepped clock and the inode numbers from a count, so guest fuel no longer moves with the host's
  file times or inode numbers (it did, in steps of 17 instructions), and a file the guest writes
  is no longer dated after the guest's clock. Each run gets its own copy of the stdlib zip instead
  of a hard link to the shared one, so no run sees another's link count. CPython's two
  `test_utime_current` tests now pass in the judge. The product runner is unchanged: programs run
  through `wasi_python.run` still see the host's real times and inode numbers.
- **Fixed: regex's `timeout=` fires past 2.1 seconds** (spec 087; the 0.1.0a7 security review's
  F3): a second carried patch, `recipes/patches/regex-2026.9.29/0002-timeout-ticks.patch`, keeps
  regex's clock ticks in 64 bits (wasm32's `Py_ssize_t` is 32 bits, and wasi-libc counts 10**9
  ticks a second); `timeout=inf` now means no timeout. Checks now hold the README's lxml
  `DENY_ALL` sentences and each 512 KiB recursion row, on an engine at wasmtime's defaults.
- **Fixed: an installed copy never loads a neighbouring artifact set** (spec 087, Decision 10;
  the 0.1.0 security review's S3). Only a source checkout of wasi-python (`src/wasi_python/`
  beside a `pyproject.toml` naming it) prefers its `build/artifacts/`; a copy installed with
  `pip install --target`, or vendored, inside a project uses its own set. `run` and `Session`
  check the set they find against its `SHA256SUMS` before using it, compile and grant only the
  bytes they checked, and raise `ArtifactsMissing` on a difference; a set passed as `artifacts=` is the caller's own, as before. No public name,
  signature or default changes.

- **Added: tier A of the default profile, thirty pure-Python packages** (spec 039; the owner's
  decisions 43 to 47). By family: Excel (openpyxl 3.1.5, et-xmlfile 2.0.0, xlsxwriter 3.2.9,
  xlrd 2.0.2); PDF (pypdf 6.21.1); HTML and XML (beautifulsoup4 4.15.0, soupsieve 3.0.3,
  html5lib 1.1, webencodings 0.6.1, defusedxml 0.7.1, xmltodict 1.0.4); text formats (pyyaml
  6.0.3, tomli-w 1.2.0, jinja2 3.1.6, markupsafe 3.0.4, tabulate 0.10.0, charset-normalizer
  3.5.2); modelling (networkx 3.7, patsy 1.0.3); symbolic (sympy 1.14.0, mpmath 1.3.0);
  utilities (attrs 26.1.0, more-itertools 11.2.1, toolz 1.2.0, tqdm 4.70.1, typing-extensions
  4.16.0, joblib 1.6.0, cloudpickle 3.1.2, threadpoolctl 3.7.0, narwhals 2.27.1). Each is pinned
  by URL and SHA-256; 28 are pure wheels (charset-normalizer's pure wheel, not its mypyc ones),
  and pyyaml and markupsafe, which publish no pure wheel, come from their sdists' pure package
  folders, so pyyaml runs without libyaml (`yaml.__with_libyaml__` is `False`, no `CLoader`) and
  markupsafe through `_native`. Each family's golden job equals native Python's output. The zip
  grows by 2,014 members and 16.5 MB (38.7 MB); the plain binary is unchanged; a plain `-c pass`
  costs 50.6M more guest instructions (218M) and a snapshot call 4.7M more (20.4M). No package is
  pre-imported. Their licence notices are in `LICENSES/`; tqdm (MPL-2.0 AND MIT) ships with the
  full MPL-2.0 text and its source, the pinned wheel unchanged, as
  `LICENSES/tqdm-4.70.1-source.whl`, and sympy's notice carries the MIT notice of its LaTeX
  grammar.
- **Changed: the `ctypes` stand-in's `ctypes.util.dllist()` answers `[]`** (spec 039): the guest
  is one statically linked module and loads no shared library, so threadpoolctl finds no native
  thread pools (`threadpool_info()` is `[]`) instead of raising `OSError`.
- **The default profile's edges, documented** (spec 039; the README's *What the default profile
  carries*): with nothing writable, `.xlsx` is written only through xlsxwriter in memory
  (`engine_kwargs={"options": {"in_memory": True}}`); a writable `/tmp` grant makes every
  writer work (decision 46). pypdf's AES needs `cryptography`, which is not carried
  (`DependencyError`). joblib runs serially. tqdm warns once that it cannot start its monitor
  thread (`tqdm.tqdm.monitor_interval = 0` silences it). Two known gaps until spec 041: pandas'
  Styler (`df.style`, `df.to_latex()`) raises `TemplateNotFound`, and networkx's graph atlas
  raises `TypeError`, each reading its files by path from the zip. With jinja2 present, `.style`
  raises `TemplateNotFound` (a `LookupError`) instead of `AttributeError`, so
  `hasattr(df, "style")`, `getattr(df, "style", None)` and `inspect.getmembers(df)` now raise
  until spec 041. `yaml.unsafe_load`, `sympy.sympify` on a string, plain jinja2 templates and
  pickle run code from their input inside the guest, as natively; the safe forms refuse. `pd.read_html` of a GB18030
  page whose tables lxml cannot read now falls back to bs4 and raises `UnicodeDecodeError`
  (`ImportError` before).
- **Fixed: pandas' Styler and networkx's graph atlas read their files from the zip** (spec 041).
  `df.style` (to HTML, LaTeX, text and Typst), `df.to_latex()`, `Styler.from_custom_template`
  and `nx.graph_atlas`, `nx.graph_atlas_g` work, with native Python's output, where they raised
  `TemplateNotFound` and `TypeError`; `hasattr(df, "style")`, `getattr(df, "style", None)` and
  `inspect.getmembers(df)` work again. Two carried patches, each an upstream bug in any Python
  that imports the package from a zip, with a facts sheet drafted for the owner under
  `context/upstream/patches/`: `recipes/patches/pandas-3.0.6/0001-styler-templates-from-a-zip.patch`
  (jinja2's `PackageLoader` when the templates folder is not a directory) and
  `recipes/patches/networkx-3.7/0001-graph-atlas-from-a-zip.patch` (open the atlas resource,
  then decompress the stream).
- **Changed: networkx is built from its sdist** (spec 041), pinned in place of its wheel, so its
  carried patch has a source tree: its package folder, `METADATA` and `entry_points.txt` are the
  wheel's byte for byte, but for `networkx/conftest.py`, pytest's configuration, which the zip no
  longer holds. `make_stdlib_zip.py --entry-points` packs an sdist's `entry_points.txt` beside
  its `METADATA`.
- **Fixed: a file a program leaves open keeps its buffered bytes, in every mode** (spec 073).
  On the snapshot, `run` lost them when `__main__` defined a function, or when the program hung
  the file on a pre-imported stdlib module or class (`json.JSONEncoder.default = …`); a script, a
  directory and `-m` lost them on both binaries. Now every program runs in a fresh `__main__`, a
  script and `-m` run in it as CPython's own entry points run them, and `run` on the snapshot
  undoes the snapshot's frozen heap before it finalizes, as a session's close does (the owner's
  answer to question 103), so the snapshot finalizes as CPython does: a `ZipFile` left open gets
  its directory written too. The price is the finalization: a bare snapshot call costs about
  43.8M guest instructions instead of 15.6M, most of it after the program has ended. So a
  `fuel=` cap on a snapshot call must cover about 28M more (more after large imports, up to
  about 90M), or the call ends `"out of fuel"`, with `exit_code` `None`, after its output was
  written.
- **Changed: a script's, a directory's and `-m`'s `__main__` are CPython's own** (spec 073). A
  script's `__package__` is `None` and its `__loader__` a `SourceFileLoader` (a
  `SourcelessFileLoader` for a `.pyc`), and its `__file__` is removed when it ends, as CPython
  does; `__builtins__` is the builtins module in every mode; an `atexit` handler finds the
  program's `__main__`, its classes and functions; `-m` of a missing module prints
  `…/python.wasm: No module named …`, a directory without `__main__.py` prints `can't find
  '__main__' module in …`, and an `-m` traceback shows runpy's `_run_module_as_main` and
  `_run_code` frames, each as CPython does. No public name, signature or default changes.
- **matplotlib's second milestone: triangulations, contours, SVG and PDF** (spec 043).
  `matplotlib.tri.Triangulation(x, y)` (Delaunay, through matplotlib's `_qhull` and qhull 8.0.2),
  and so `tricontour`, `tricontourf`, `tripcolor` and `triplot` on bare points, now work, and so
  do `contour`, `contourf` and `clabel`, through contourpy 1.4.0, built in as
  `contourpy._contourpy` with its package in the zip. A golden job saves a figure with all of them
  as SVG and PDF: the SVG's bytes are native matplotlib's, and the PDF's are too but for its font
  subset tags, which matplotlib derives from `hash()`, 32 bits wide in the guest. One more carried
  patch, `recipes/patches/matplotlib-3.11.2/0002-qhull-without-devnull-on-wasi.patch`: on WASI,
  `_qhull` sends qhull's messages to a stream that writes nowhere instead of opening `/dev/null`,
  which raised `RuntimeError: Could not open devnull` in every Delaunay triangulation and, in a
  writable root holding a `dev` folder, would have made a file there; its facts sheet is for the
  owner to send (matplotlib refuses AI-written pull requests). contourpy runs one thread
  (`max_threads()` is 1). The binary imports one more WASI preview1 call, `fd_renumber` (qhull's
  `freopen`), which the runner already shadows and counts. `python.wasm` grows by 1.08 MB and the
  zip by 19 members; `import matplotlib.pyplot` costs what it did. The notices gain contourpy's
  licence with matplotlib's `LICENSE_YORICK` (GIST's notice, for contourpy's `mpl2005` code;
  question 81) and qhull's `COPYING.txt`.

## 0.1.0a7 — 2026-10-19

- **Fixed: an async gate that raises `GeneratorExit` refuses the call** (spec 075; the 0.1.0a6
  security review's F1). An async gate (an `async def`, a function returning an awaitable, or an
  object with an async `__call__`) that raised `GeneratorExit` or a subclass used to allow the
  call, and the tool ran; an async tool that raised it was answered `ok` with `None`. Now the
  gate's call is `denied` and the tool's `tool_error`, each with the fault in the record, as a
  sync gate's and a sync tool's already were. The result of an awaitable counts only if it
  returned. Also (spec 060's build review, N1): a tool list over the 16 MiB answer cap is refused
  from its length on each `list` frame, without its answer being built. No public name, default
  or answer on the wire changes.
- **Changed: the snapshot pre-imports no package** (decision 34, spec 069). It starts with the
  interpreter and the stdlib's bootstrap modules (`encodings`, `io`, `os`, `sys`, `json`, `csv`,
  `re`, `_colorize`), for every package now and later; the judge refuses a snapshot that holds
  any other top-level module. A bare call costs 15.6M guest instructions instead of 83.5M; a call
  that imports pandas pays it, 4.60G in all instead of 83.5M (a small numpy job about 0.7G more
  than before), so a `fuel=` cap set for a pandas job on the snapshot needs that much more. The
  snapshot is 30.4 MB smaller (44.6 MB) and the wheel about 11 MB smaller. numpy, pandas and the
  other packages now import with the call's environment. A session's shutdown costs about 43M
  instructions when nothing beyond the stdlib was imported (about 306M before). `snapshot=True`
  is unchanged as an argument; no public name, signature or default changes. MANIFEST's
  `x-preimport` line is now read from the recipe. Known and unchanged: `run` on the snapshot
  loses an unclosed file's buffered bytes when `__main__` defines a function (a gap until spec
  073; close your files before a call ends).
- **Bounded sessions** (spec 055). `Session` keeps one instance of the runtime across turns:
  `session.run(code)` and `await session.run_async(code)` each run one turn in `__main__`, and
  variables, functions, classes and imports carry over. A turn echoes its final expression,
  reports an exception with `<turn N>` in its traceback, and reports `sys.exit()` as its exit
  status while the session goes on, as a Jupyter kernel does. Each turn has its own fuel,
  deadline, output cap, cancel, file-call and tool-call allowance; the session has one memory
  cap, an idle bound (`idle_s`, default 15 minutes) and a lifetime (`lifetime_s`, default 1
  hour), which caps every turn's deadline; `max_open_files` counts across a session's turns and
  its shutdown, since its store keeps what they open. A trap, `os._exit`, a bound, `close()` or a turn's
  `exit()` or `quit()` ends it; `session.ended` says which, and later turns raise
  `SessionEnded`. A session's close and expiry, and `exit()` or `quit()` in a turn, run
  Python's shutdown (`atexit`, flushes) within `shutdown_s` seconds and the session's fuel, as a
  Jupyter kernel's do; past that budget the session is stopped; `sys.exit()` keeps the session;
  `session.shutdown_outcome` says whether the shutdown finished, was stopped or did not run. Added:
  `Session`, `SessionEnded`, three `Defaults` fields (`session_idle_s`, `session_lifetime_s`,
  `session_shutdown_s`), `stats()["sessions_open"]`, and two exports in both binaries, `turn` and
  `shutdown`, whose contract the README gives for any embedder. `run` is unchanged.
- **Deep recursion raises `RecursionError`** (spec 071). A `__repr__` that calls `repr(self)`,
  `lru_cache` recursion, a recursive sort key or a numpy, pandas or lxml callback used to end the
  guest in a wasm trap; it now raises, on both binaries, at wasmtime's default 512 KiB stack.
  The guest narrows CPython's C-stack guard to 128 KiB with CPython's own
  `PyUnstable_ThreadState_SetStackProtection`, called from the reactor's recipe: no patch.
  **Changed:** such recursion stops at about half the depth it reached before trapping (214
  levels for the `__repr__` case, 40 to 250 by shape), so a program that recursed that deep and
  finished now raises. Callbacks out of expat, recursion in C over very deep data, and freeing
  very deep structures still trap, with the limits the README lists. The runner now states its
  wasm stack, 512 KiB, instead of taking wasmtime's default, and the judge's guest driver makes
  the runner's engine (fuel, epoch interruption, that stack). `python.wasm`, the snapshot and
  `MANIFEST` change; the zip does not.
- **On Linux, a host's faulthandler can no longer turn a guest trap into the host's death**
  (spec 071). If `faulthandler` was enabled or disabled after the runner's first call, a guest
  trap used to kill the host with SIGILL (and after a late `signal.signal` for `SIGILL`, hang
  it); `run` now refuses such a call with `RuntimeError` before the guest runs, says why, and
  names the remedy. Install faulthandler and crash reporters before the first call, or not at
  all.
- **The build runs only the pinned host Python** (spec 079; the 0.1.0a6 security review's
  F2). FreeType's configuration headers, HarfBuzz's generated sources and matplotlib's
  `matplotlibrc` were written by whatever `python3` the build host had first on `PATH`, and
  CPython's configure ran it once. Now step 10 puts a shim for the pinned CPython 3.15.0 first
  on every step's `PATH`. Behind it, `scripts/build.sh` puts a stand-in for every other Python
  name the host has, which fails the step if it is run. A build host needs no Python of its
  own. The artifacts are the same bytes; `MANIFEST`'s recipe lines change.

- **The release judges in parallel shards** (spec 063). The release runs numpy's and pandas' own
  test suites (eleven groups, 63,718 passing tests) on Linux, one group of them on macOS and on
  Windows, every product check and the runner's own tests on all three systems, and the rules and
  the judge's own tooling on macOS and Linux, in eighteen parallel jobs after the build. A
  `gather` job reads every shard's record by id and SHA-256 and publishes nothing unless each
  shard ran exactly its share on the release's bytes, nothing failed, the probe passed on three
  systems, and the lane's newest acceptance is on the same `python.wasm`. `uv run pytest
  --shard=<name>` runs one shard. Every package now names its own suite, or why not yet, in
  `tests/upstream/packages.toml`.
- **lxml, with libxml2 and libxslt built in** (spec 046). lxml 6.1.3's `lxml.etree` and
  `lxml.objectify` are builtins, over libxml2 2.15.4 and libxslt 1.1.45 with libexslt: XPath,
  XSLT, XInclude, C14N, DTD, XML Schema, RELAX NG and Schematron validation, the HTML parser,
  `iterparse`, and files read and written by path inside a grant. lxml's Python package
  (`lxml.html`, `lxml.builder`, `lxml.sax`, `ElementInclude`, `lxml.html.diff`) is in the zip with
  its METADATA. pandas' `read_html` with no `flavor` now works (lxml is its first flavor), and so
  do `read_xml` and `to_xml` with their default parser. The judge's golden job `lxml_xml` equals
  native lxml at the same pins. What differs from native, as the README says:
  - **Character encodings are wasi-libc's iconv**, not GNU libiconv: windows-1252, ISO-8859-2
    and -15, cp1251, KOI8-R, TIS-620 and UTF-16 round-trip every character; Shift_JIS,
    ISO-2022-JP and GB2312 read a few characters as other characters; cp932, EUC-JP, Big5 and
    cp950 documents fail to parse (in HTML and `recover=True` their text ends at the first
    unreadable character, with no exception); most CJK writes raise `LookupError`. **GB18030
    fails at its first non-ASCII byte, on purpose**, because wasi-libc decodes 1,617 of its
    characters wrongly without an error: `recipes/iconv_refusals.c`, linked into the reactor
    with `-Wl,--wrap=iconv_open`, `iconv` and `iconv_close`, until a wasi-sdk carries musl's fix
    (`context/upstream/15-wasi-libc-gb18030-decoder/`). Strict XML raises, `recover=True` keeps
    no root, the HTML parser keeps only the ASCII text before it, `read_html` of a Chinese
    table raises; no character is read wrongly in any mode. But a table that reaches the first
    non-ASCII byte comes back cut there with no exception: its last row may be all NaN, a
    column may turn float, and the rows and tables after it are missing (check `error_log`).
    The README gives the working route: decode with Python's `gb18030` codec and give lxml the
    text.
  - **XSLT reads and writes files by default.** A stylesheet without an `access_control`, or a
    document it loads with `document()`, can read any file in a grant (external entities
    included) and write into any writable grant; use `etree.XSLTAccessControl.DENY_ALL` for
    untrusted stylesheets. lxml's parser defaults stay the safe ones.
  - **Left out:** `lxml.isoschematron` (it reads its stylesheets by file path, and their terms
    are not approved; a stand-in raises `ImportError`; `etree.Schematron` works), zlib in
    libxml2 (`XMLParser(decompress=True)` raises; lxml compresses output through Python's
    `gzip`), `cssselect` and `lxml_html_clean`. A catalog is read only from a grant at `/etc/xml`.
  - **One more carried patch:**
    `recipes/patches/libxml2-2.15.4/0001-xmlio-without-dup-on-wasi.patch` lets libxml2's file
    input and output work without `dup()`, which WASI preview 1 does not have (without it
    libxml2 does not compile for `wasm32-wasip1`). Its facts sheet for the owner:
    `context/upstream/patches/libxml2-2.15.4/0001-xmlio-without-dup-on-wasi.md`.
  - **The build:** two new steps, 36 (libxml2 and libxslt, by their own configure, under an empty
    environment, with the pinned `pkgconf` and an empty search path) and 54 (lxml's two modules,
    from the Cython 3.2.9 C its sdist ships); three new pins. libxml2's default catalog is
    native Linux's `/etc/xml/catalog`, not a build folder, and a new judge check holds every
    later package to the same rule: neither binary names the checkout or the builder's home.
  - **Licences:** `LICENSES/libxml2.txt` (with the notices of `dict.c`, `list.c` and
    `timsort.h`), `LICENSES/libxslt.txt` and `LICENSES/lxml.txt`.
- **regex is built in** (spec 047). regex 2026.9.29's `regex._regex` is a builtin module and its
  Python package is in the zip with its `METADATA`: fuzzy matching, full Unicode properties from
  regex's own tables, graphemes, variable-length lookbehind and `captures()` give native regex's
  answers (the golden job `regex_features`). One carried patch,
  `recipes/patches/regex-2026.9.29/0001-callback-signatures.patch`, gives five callbacks the
  parameter CPython passes (`Pattern.groupindex`, pickling a pattern, `Match.capturesdict()`,
  `allcaptures()` and `allspans()` each trapped the guest without it); its upstream facts sheet
  is `context/upstream/patches/regex-2026.9.29/0001-callback-signatures.md`, for the owner to
  send. The init function of each of the 71 cross-built builtins now runs inside CPython's
  package context, set to its dotted name, as a native import from a shared library does, so a
  single-phase module keeps its import name (`regex._regex`, and a compiled pattern pickles);
  numpy's, pandas' and matplotlib's modules are multi-phase, or already named in full
  (`pandas._libs.json`), and do not change. The judge checks every dotted
  builtin's `__name__` on both binaries. Licence: Apache-2.0 and CNRI-Python, in
  `LICENSES/regex.txt` with a line naming the patched file. `timeout=` counts the guest's clock;
  fuel and the deadline are the limits that hold.

- **The judge's small follow-ups** (spec 070). The README's **Limits** now says that a refused
  discovery frame (`max_tool_calls=0`, or a request budget too small for it) makes `from host
  import tools` raise `ImportError`, and a check holds it. The release scan reads a download's
  `path:` as a path, so `./release-assets` is `release-assets`; the progress history's volume
  budget is tested at its exact byte, and a volume holding a carriage return is reported. Nothing
  in the artifact set, the wheel's code or the guest changes.

- **Security: a cap on files open at once** (spec 068; the 0.1.0a2 security review's F11 and spec
  055's pre-build review's F2; spec 049, Decision 8, exception 2). `max_open_files=` on `run` and
  `run_async`, `Defaults.open_files` and `wasi-python run --max-open-files`, default 1,024: the
  files and folders a guest holds open at once, in grants, the root and mounts alike. Past it an
  open answers `EMFILE` before anything is opened, and the guest can close files and go on. Until
  now a guest could open host descriptors until the process's own limit (122,870 on the
  research's Mac), and saw `EIO` there. The cap protects the embedder's process only within that
  process's soft descriptor limit: raise it, or set the cap below it (the README's *Safety*);
  `wasi-python run` raises its own. Descriptors wasmtime holds while it resolves a deep path are
  not counted (*Not protected*). Calls without mounts now pass `path_open`, `fd_close` and
  `fd_renumber` through the runner, which forwards them to wasmtime; fuel does not change.
- **Changed:** a new, tighter default (spec 068; spec 049, Decision 8, exception 1): a program
  that holds more than 1,024 files open at once passes a larger `max_open_files`, or `None`.
- **Windows judges a grant's path as Linux and macOS do** (spec 076). A grant or `root` with
  `..` after a missing folder or a file (`new\..\x`) is now refused on Windows too, before any
  work; before, Windows dropped the `..` by its text, made `x` and ran the guest. On Windows a
  host path with a name that holds `:`, ends in a space or a period, or is a reserved device
  name (`NUL`, `COM1` and the rest, and `COM¹` to `COM³` and `LPT¹` to `LPT³`; spec 077) is
  refused, since Windows rewrites such names and the runner's checks could then judge other
  folders than the ones granted (a spelling the embedder gives, never the guest). So is a name
  that holds `<`, `>`, `"`, `|`, `?`, `*` or a control character, and, out of caution, `CONIN$`
  or `CONOUT$`: the refused names are exactly those Python's `ntpath.isreserved` refuses (spec
  077), and a `root` still to be made through one is refused before any folder is made. A path rooted with no drive takes the current folder's drive. The
  README states the one errno that differs by system on a grant: a write through a descriptor
  opened only to read (or the reverse) is `EBADF` on Linux and macOS and `EACCES` on Windows,
  wasmtime's own mapping of the host's error.

## 0.1.0a6 — 2026-10-19

- **The x86_64 rebuild runs natively** (spec 059). Every compile carries `-ffp-contract=off`,
  set once in the toolchain's own `clang.cfg` and `clang++.cfg` by step 10, so wasi-sdk's x86_64
  and aarch64 builds of clang emit the same bytes, and the x86_64 Linux rebuild compiles with its
  own clang instead of the arm64 clang under qemu (an hour less per release run). Run-time
  arithmetic does not change (wasm32 fuses nothing); a constant the compiler folds moves to the
  value the run time computes. `python.wasm`, the snapshot and `MANIFEST` change once; the zip
  stays. The judge refuses any compiler option that would override the file (`-ffp-model=`,
  `-ffast-math`, `-Ofast`, `-funsafe-math-optimizations`, `--no-default-config`, `--config`,
  another `-ffp-contract=`) in the recipe and in every build record, greps the source trees for
  a pragma that turns contraction on, and probes the compiler's own `-cc1` line. Spec 040's
  emulated compiler stays in the tree, switched off by one line in `scripts/line.conf`, until
  the first alpha whose native x86_64 rebuild passed has shipped. The LLVM issue draft is
  narrowed to `llvm.fmuladd` on `fp128`.
- **Async tools and gates** (spec 053). A tool or a gate may be an `async def`, or a function
  that returns an awaitable. Under `run_async` it is awaited on the event loop that awaits
  `run_async`, so an MCP client session or an async HTTP client works as it is; under `run`, on a
  loop of the call's own, on a thread started at the call's first awaitable and closed when the
  call ends. A call answered before its coroutine started never starts it (spec 056's fix,
  extended to async tools); every later end of the call (`timeout_s`, the deadline, a cancel,
  Ctrl-C) cancels it at its next `await`. A `KeyboardInterrupt`, `SystemExit` or
  `CancelledError` a tool raises, and a loop that has closed or stopped, are faults in the record,
  never exceptions in the embedder's loop. The guest, the protocol and the artifact set do not
  change. The README's MCP recipe is now an `async def`. An async generator is refused as a tool
  or a gate.
- **Changed:** `host=` given an `async def` (or an async generator, a `partial` of one, an
  object with an async `__call__`) is refused with `TypeError` before any work. The raw door is
  synchronous; it used to answer every frame with a host fault and never await the coroutine.
- **A provider may raise `OSError`** (spec 061). Its errno, matched by name (never by number,
  which differs by host), is the guest's answer, as the `Errno` of that name would be. With no
  errno at all, `FileNotFoundError`, `FileExistsError`, `IsADirectoryError`,
  `NotADirectoryError`, `PermissionError` and `TimeoutError` answer `ENOENT`, `EEXIST`,
  `EISDIR`, `ENOTDIR`, `EACCES` and `ETIMEDOUT`. An errno outside the closed set (`EINTR`,
  `EAGAIN` and the rest), whatever the class, and any other exception stay a fault, `EIO`. A
  mapped raise leaves no fault in the record. The guest never sees the exception's message, and
  the record keeps nothing of it.
- **The judge runs on several cores** (spec 052). `uv run pytest -n 6` gives the serial
  answer in about a third of the time: pytest-xdist 3.8.0 is pinned in the development group,
  each check's record is made on its worker and carried to the controller, which alone writes the
  run record and accepts, and an upstream group runs with its classes in one worker. The lane's
  accepting run stays serial; `tests/harness/sameness.py` compares two run records. Five checks
  no longer depend on the order or speed of the run, and the judge's zips folder is safe when
  several processes make it at once. Nothing in the artifact set or the wheel changes.
- **Security: a per-run budget of tool request bytes** (spec 060; the 0.1.0a4 security review's
  F3; spec 049, Decision 8, exception 2). `max_tool_request_bytes=` on `run` and `run_async`, and
  `Defaults.tool_request_bytes`, default 16 MiB, counted from each frame's length before it is
  read, whatever its answer; a frame that would pass it is refused unread, and the guest gets
  `ToolBudgetExceeded` and runs on. Parsing a 1 MiB frame costs the host a few tenths of a second
  of CPU, so until now only the deadline bounded one call's total. The tool list is encoded once
  per call, not once per `list` frame. `tool()` finds a partial's bound keywords through a
  `__call__` chain of any depth and through a metaclass's `__call__` (the review's N8), and
  refuses a `__call__` cycle with `TypeError`, where Python 3.14 raised `RecursionError`.
- **Changed:** a new, tighter default (spec 060; spec 049, Decision 8, exception 1): a call that
  sends more than 16 MiB of tool requests passes a larger `max_tool_request_bytes`, or `None`.

- **matplotlib, the first milestone** (spec 023). matplotlib 3.11.2 is built in: `import
  matplotlib; matplotlib.use("agg")`, `plt.plot(...)` and `savefig` to PNG, PDF, PS, EPS or SVG
  in a granted folder. A fixed line plot's RGBA buffer equals native matplotlib's at the same pins,
  and its PNG decodes to those pixels (the judge's golden job `plot_line`). Linked in: FreeType
  2.14.3, HarfBuzz 14.1.0, SheenBidi 3.0.0 and libraqm 0.10.5 (matplotlib's own wrap versions, for
  native pixel parity), matplotlib's `ft2font`, `_path`, `_image`, `_backend_agg`,
  `_c_internal_utils` and `_tri`, kiwisolver 1.5.1 and Pillow 13.0.0's `_imaging`, `_imagingmath`
  and `_imagingmorph` (zlib only: JPEG and other codecs raise `OSError`). In the zip: matplotlib,
  `mpl_toolkits`, PIL, kiwisolver, fontTools 4.67.0, cycler 0.12.1, pyparsing 3.3.3 and packaging
  26.3, each with its METADATA. Not yet: Delaunay triangulation (`_qhull` is left out of the link;
  explicit triangles work) and `contour` (contourpy), both the next milestone; the snapshot does not
  pre-import matplotlib (the owner's question 34).
  - **matplotlib's data** travels inside the zip as one member, `matplotlib/mpl-data.zip`. The
    runner extracts it once per process into its private zip folder, checks every file as it
    writes it, compares the whole tree with its record on every call, and grants it read-only at
    `/usr/local/lib/python315.zip/matplotlib/mpl-data`, the path matplotlib computes. The zip
    itself now sits in that folder's `lib/`, so `/usr/local/lib` still lists only the zip
    (spec 017's Decision 2, amended). An embedder without the runner extracts and preopens it
    itself (the README says how).
  - **Three more carried patches.**
    `recipes/patches/matplotlib-3.11.2/0001-ft2font-enums-without-python.patch` is upstream's
    merged commit `8e5591bc` (pull request #30291, matplotlib 3.12): `ft2font`'s enums no longer
    take the GIL during static initialization, which hung a statically linked reactor before Python
    started. `recipes/patches/pillow-13.0.0/0001-arrow-capsule-signatures.patch` and
    `recipes/patches/kiwisolver-1.5.1/0001-callback-signatures.patch` give two Pillow methods and
    21 kiwisolver methods and getters the signatures CPython calls them with: spec 051's callback
    scan found them in the first matplotlib link, and kiwisolver's trapped the guest at
    `Solver.addConstraint`. Facts sheets for the owner: `context/upstream/17-…` (nothing to send),
    `18-pillow-arrow-capsule-signatures/` and `19-kiwisolver-callback-signatures/`.
  - **The build:** two new steps, 37 (the plot libraries) and 55 (Pillow, kiwisolver and
    matplotlib); the pinned `pkgconf` wheel in step 10; `scripts/wasi-cc` drops `-pthread`, which
    would have compiled `+atomics` in; step 60 checks the static constructors and target features
    of every link against the judge's reviewed lists and stops on a new one. Eighteen new pins,
    among them the Unicode License V3 for HarfBuzz's tables, pinned at a commit of Unicode's own
    repository.
  - **The judge:** the milestone job and its PNG decoder (stdlib only); `savefig(dpi=-1)` and a
    kiwisolver `UnsatisfiableConstraint`; the data grant refuses every write; the static
    constructor list; the ten target features; fifteen source trees judged against their tarballs
    (the release workflow's count is 15); every C++ build's exception flags; the licence notices of
    every new component. The callback scan no longer reads a record whose function sits at a parser
    rule's table index as a method definition (FreeType's BDF property table). Two known gaps,
    closed by the research memo's M2.

- **Security: the release signs and publishes only what its build job made** (spec 057; the
  0.1.0a4 security review's F4, N1 and N3's workflow side; it closes the one-release allowance the
  0.1.0a5 addendum gave F4, before this release). The build job hands on its upload's artifact id
  and the SHA-256 of its `SHA256SUMS`. Every job that checks, signs or publishes refuses an empty
  id, downloads by that id with `digest-mismatch: error`, and checks `SHA256SUMS`, every file, and
  that nothing else is there, before it acts; until now each fetched whatever artifact was named
  `release-assets`. The two Linux rebuilds are two jobs instead of a matrix, so one cannot hand on
  the other's ids. The download step fails, naming the file, when a fetched file has no pin.
  `publish` names the `release` environment, `setup-uv`'s cache is off in every job, and every job
  states its own least permissions under a workflow-level `permissions: {}`. The judge checks all
  of it, runs the workflow's own check and guard steps, and runs the download step on fake pins.
  It also refuses any other download into `release-assets` or into a job that holds it, any
  `continue-on-error:`, and a `pypi` job that could run before `publish` or outside a pushed tag.
  `python.wasm`, the snapshot and the zip do not change. `MANIFEST` changes in one line, because
  it records the download script's hash, so the set's `SHA256SUMS` and the wheel change too.

## 0.1.0a5 — 2026-10-18

**The first release since 0.1.0a3.** 0.1.0a4 was tagged but never published (see its section):
everything listed under 0.1.0a4 ships in this release too, including the security fixes of specs
048 and 056.

- **Read-only code on the import path** (spec 054). Added: `run(import_path=[…])` and
  `run_async(import_path=[…])`, and `wasi-python run --import-path GUEST`. Each entry, a folder
  or a zip file inside a read-only grant, goes on `sys.path` after the stdlib zip. The runner
  refuses, before any work, an entry the root, a writable grant or a mount serves, a writable
  grant or a mount under an entry, and a writable grant or root inside the grant serving one.
  No `.pyc` is written. A module the runtime has is always the runtime's; one it looks for and
  lacks (`_hashlib`, `pytz`, …) is taken from an entry, on the plain binary also for packages
  the snapshot pre-imported (README, *The import path*). Fixed (docs): the README no longer says
  a writable mount at `/` puts `/` on a `-c` program's `sys.path`; nothing writable is ever
  there.
- **A Windows grant renames a folder over a file** (spec 058). The 0.1.0a4 release run stopped
  on Windows, where a writable grant lets `os.rename` replace a file with a folder; a mount
  answers `ENOTDIR` (54) there as on every host, and as a Linux or macOS grant does. The judge
  now asserts that row's grant answer, and the listing that follows from it, exactly per system,
  and the mount's answer everywhere; Linux's and macOS's assertions are kept, and each gains an
  exact value. The README names it, and a second Windows difference the same run showed: a
  Windows grant cannot remove or rename a file the guest holds open, so `tempfile.TemporaryFile`
  fails there. Nothing in the runtime or the artifact set changes.
- **The public API is frozen and documented** (spec 049).
  - **Added:** `defaults()` and `set_defaults()`, which replace assigning
    `wasi_python.runner.DEFAULTS` (that still works, unpromised, until the internal name
    changes); `Defaults` and `stats()` at the top level; `PROTOCOL` in
    `wasi_python.tools.__all__`; `py.typed`, so a type checker reads the package's hints; `tool`'s
    two overloads, so a function decorated with `@tool` keeps a type; and the README's "API
    reference", generated from the same render as `tests/public_api.txt`, the judge's snapshot of
    the surface.
  - **Changed:** the seventeen other `wasi_python.tools` constants (`TOOL_REQUEST_BYTES` and the
    rest) and `wasi_python`'s `ARTIFACT_DIR`, `ARTIFACTS_ENV` and `CHECKOUT_ARTIFACT_DIR` are
    private, each with a leading `_`; the numbers stay in the README. `Defaults`' `memory_bytes`,
    `deadline_s`, `output_bytes` and `file_calls` are annotated `… | None`, `host` as returning
    `bytes | bytearray | memoryview`, and `Mount.provider` as a `FileProvider`, as the code
    already accepts. A call reads the defaults once, when it is made, so a `set_defaults` on
    another thread never gives it a mix. The README no longer names `wasi_python.runner` or
    `DEFAULTS`.
  - **The promise**, from 0.1.0, the first final release: a patch release changes nothing
    public; a minor release may add; a deprecated thing keeps working for at least two final
    minor releases (deprecated in 0.N, removable in 0.N+2); a tighter default, in a minor release,
    and a security fix, in any release, need no deprecation. The README's "API reference" says
    what is promised and what is not.

## 0.1.0a4 — 2026-10-18

**Not published.** The tag `v0.1.0a4` exists, but its release run (#46) failed on Windows: spec
034's writable-mount parity check did not hold for a Windows grant (fixed by spec 058 in
0.1.0a5). The run was cancelled; there is no GitHub release and no PyPI upload of 0.1.0a4.
Everything below ships in 0.1.0a5.

- **The zip's directory is read once** (spec 035). A start reads the stdlib zip's directory
  through the reactor's own reader, `_zip_directory`, a frozen module installed between the
  interpreter's two start phases: one read and one unpack per member, about 25,000 fuel a member
  where zipimport's took about 77,700. A plain `-c pass` falls from 242 M to 151 M fuel. Resource
  reads and `importlib.metadata` no longer parse the zip: they answer from the directory zipimport
  already holds. A first `ZoneInfo("Europe/Paris")` costs 8.6 M fuel on the snapshot instead of
  207 M, a metadata miss 11 M instead of 222 M, and `version("numpy")` 148 M instead of 361 M.
  `importlib.resources.files()` on a package in a zip gives `ZipDirectoryPath`, the runtime's own
  `Traversable`, not a `zipfile.Path` (the README names the differences); `zipfile` still reads
  any member that is not plain and small. Zip64 zips, cp437 names and every error go to
  zipimport's own reader. `python.wasm` grows by about 25 KB. No upstream file changes; a
  courtesy issue for importlib_resources is drafted
  (`context/upstream/16-importlib-resources-zip-directory/`).
- **Security: the 0.1.0a4 security review's findings** (spec 056). Two fixes in
  `wasi_python.tools`, on the host only; the artifact set is unchanged.
  - **A keyword bound with `functools.partial` is fixed** (the review's F1, high). `tool()`
    published each keyword a partial binds as an optional parameter, with the bound value as its
    `default`: `tool(partial(orders, user_id=42, api_key=KEY), name="my_orders")` sent the key to
    the guest, and the guest could call `my_orders(user_id=7)`. Now a bound keyword is left out
    of the schema, the guest's signature and `stubs()`, and a frame that names it is answered
    `invalid_arguments` as an unknown argument, so the bound value is always the one used. This
    holds wherever `inspect.signature` meets a partial (nested partials, a `__wrapped__` chain, a
    bound `partialmethod`). A given `input_schema` that names a bound keyword is refused, and so
    is a `partialmethod` reached other than through an instance. A bound value need not be JSON
    any more. A parameter's own default is still published, and the guest may still override
    it: the README says never to put authority in one.
  - **A call that ended while its gate decided never runs its tool** (F2, medium). A gate that
    allowed after its call had timed out or been cancelled, even after `run` returned, still
    started the tool. The bound now checks, under the lock that marks a call answered, between
    the gate and the tool.
  - **Documented** (F3, F5 and notes N2, N4): a large tool frame's host CPU and its per-run
    total, bounded today only by `max_tool_calls` and the deadline (a per-run byte budget is a
    later specification); a mount provider receives `\`, `:` and Windows device names as the
    guest wrote them, so one backed by a host folder must check containment; the wasmtime fixes
    live in the runner, not in the artifacts; `ToolCall.arguments` holds only what the guest
    sent.
- **What numpy's and pandas' own tests found** (spec 051). Three defects, fixed:
  - **numpy callbacks no longer trap the guest** (the second carried patch,
    `recipes/patches/numpy-2.5.2/0002-callback-signatures.patch`). Six C functions were defined
    with fewer parameters than CPython calls them with; WebAssembly checks the type of every
    indirect call, so `copy.copy` of any numpy scalar and `a.dtype = …` ended the call in a wasm
    trap. Each gains the parameter, unused. Its upstream facts sheet is
    `context/upstream/13-numpy-callback-signatures/`, for the owner to send. The judge now scans
    `python.wasm`'s referenced method and getset tables, and Cython's and CPython's single method
    definitions, for any callback whose type is not the one CPython calls it with
    (`test_callbacks_have_the_types_cpython_calls`); a mismatch is fixed by a patch or an
    upstream release, never excused.
  - **pandas' warnings point at the caller's line.** The zip's code objects now carry the name
    zipimport gives a module in it, `/usr/local/lib/python315.zip/pandas/core/frame.py`, instead
    of `pandas/core/frame.py`, so pandas' `find_stack_level` finds its own frames. Tracebacks show
    the full zip path, as native zip imports do. The zip grows by the longer names.
  - **The first carried patch, amended**
    (`recipes/patches/numpy-2.5.2/0001-npy-files-without-dup.patch`): `np.save` of a masked
    array to a path raises `NotImplementedError` again, as natively, where the patch had written
    its data and dropped its mask. A truncated `.npy` file read from a path raises numpy's
    in-memory `ValueError` message on WASI, a documented difference; the patch's tests and its
    upstream draft say so.
- **Security: the sandbox holds on wasmtime 49.0.0** (spec 048). wasmtime-py 49.0.0, the only
  49 release, bundles wasmtime 49.0.0, which carries two advisories that reach a guest; the
  runner now carries both fixes itself, on every call. **GHSA-m9f7-9w4p-gv38** (high, fixed in
  wasmtime 49.0.3): on macOS and FreeBSD a guest with a writable grant or `root=True` could
  rename a symbolic link pointing out of its sandbox with a trailing slash, `os.rename("up/",
  "stolen")`, and the kernel moved the host folder it pointed at into the sandbox. A rename with
  a trailing `/` on either path now needs a source that is a folder, judged without following
  the source's own link (`ENOTDIR` otherwise, or the source's own error, such as `ENOENT`), and
  a folder is renamed by its plain name. **GHSA-96f6-r43r-8c24** (low, fixed in wasmtime
  49.0.2): `fd_readdir` on a grant, a root or the stdlib folder gave the guest up to three bytes
  of host memory per entry; the runner now zeroes them. A call without mounts now runs on a
  guard linker that serves `fd_readdir` and `path_rename` through the runner (forwarded to
  wasmtime, fuel-neutral; `Completed.files` stays `None`); every other call stays wasmtime's.
  Once a call has stopped, these two answer `EIO`, as every runner-served call does. Each guard
  is removed when the published `wasmtime` requirement admits only fixed versions.
- **Tools in the runner** (spec 036). `run` and `run_async` take `tools=` (decorated or plain
  functions), `gate=` and `max_tool_calls=` (`DEFAULTS.tool_calls`, 1,000), checked before any
  work; `host=` and `tools=` exclude each other. The door asks the frame host to admit each frame
  by its length before it copies it, so a frame over 1 MiB costs the host the same whatever its
  size. Each tool call runs on its own daemon thread, in a copy of the caller's context, and is
  answered at the tool's `timeout_s`, two ticks before the deadline, at `cancel` or at Ctrl-C;
  a tool left running is `abandoned`, and one run may hold 4 of them. `Completed.tools` records
  every frame, on every ending; `runner.stats()` gains `tool_threads_running`. An artifact set
  without the guest package is refused (`ArtifactsMissing`). The README's "Tools" gives the
  API, its limits and their reasons, and LangChain and MCP recipes. The artifact set does not
  change.
- **x86_64 Linux rebuilds the same bytes** (spec 040). The release workflow's `same-bytes` gate
  now rebuilds the set on an x86_64 Linux runner too, beside the arm64 one, and requires the same
  `SHA256SUMS` and wheel from each; nothing is signed or published otherwise. wasi-sdk's x86_64
  clang orders two stack slots of numpy's `npy_cpowl` differently in instruction selection, so the
  x86_64 host now compiles with the pinned arm64 Linux wasi-sdk's clang under a pinned
  `qemu-aarch64` (Debian's, from `snapshot.debian.org`, with four aarch64 runtime packages), through
  the new launcher `scripts/clang-emulated`; every other tool stays native. Step 10 lays it out
  under `build/tools/` and stops unless five probes hold. Nothing changes on the arm64 hosts: the
  three artifacts and the licences keep their bytes, and `MANIFEST` gains the five pins and the
  launcher. The LLVM issue is drafted for the owner (`context/upstream/4-llvm-wasm-isel-slot-order/`);
  the emulation goes when an SDK's two compilers agree.
- **A tool protocol over the door** (spec 031). Guest code can call the host's tools with
  `from host import tools`; the stdlib zip carries the guest's half, the pure-Python package
  `host` (`host/__init__.py`, `host/tools.py`), and the wheel the host's, `wasi_python.tools`
  (`tool()`, the frame host, `stubs()`), which `import wasi_python` does not load. The binary,
  its imports and its exports are unchanged: frames are JSON, protocol 1, through the one door.
  The README's "The tool protocol" gives the frames, the kinds, the request rules, the schema
  subset and the validation budget, for an embedder in any language. `run(tools=…)` comes with
  spec 036. Costs: the zip grows by 2 members (12,963 bytes) and the snapshot by 4,197 bytes;
  a plain start by about 0.16 M fuel (+0.064%); a snapshot's start and program by nothing, its
  teardown (`Py_FinalizeEx`) by about 0.11 M (+0.14% of a `-c pass` call).
- **Writable mounts** (spec 034). `Mount(provider, guest, writable=True)` lets a guest create,
  write, append, truncate, make and remove folders and rename within a namespace your code
  serves. A writable mount's provider adds `write` (the whole file), `mkdir`, `remove`, `rmdir`
  and `rename`, each answering `None` or an `Errno`. A create or truncation reaches it at open as
  `write(path, b"")`; a file's bytes are handed over whole at close, at `fsync` and at every
  ending that returns a result (not when the call raises or the interpreter is exiting).
  `done.files.refused` and `refused_total` record every refused or unmade write, even on exit
  0 (`RefusedWrite`; `WritableFileProvider` for type checkers). Links are `ENOTSUP`; times are
  accepted and ignored; a rename to another writable preopen is `EXDEV`. Nothing is writable
  unless you say so. **`FileRecord.calls` now has eight keys** (the write half's zeros
  included) for every call with mounts, read-only ones too.
- **The stdlib zip carries package metadata** (spec 033). `importlib.metadata.version("numpy")`
  now answers `2.5.2` instead of raising `PackageNotFoundError`, and `distributions()` lists
  numpy, pandas, python-dateutil, six and tzdata at their pinned versions. A wheel keeps exactly
  `METADATA` and `entry_points.txt` of its `.dist-info`; numpy and pandas get their pinned sdists'
  `PKG-INFO` as `METADATA` (`make_stdlib_zip.py --metadata`). `files()` gives `None`: `RECORD` is
  not kept. A source tree that brings a `.dist-info` or `.egg-info` of its own now stops the
  build. Costs: the zip grows by 7 members (about 21 KB), every plain start by about 0.54 M fuel,
  and on the snapshot the first metadata lookup costs about 0.36 G fuel and `import numpy.testing`
  about 0.14 G more than before.
- **A wider `ctypes` stand-in** (spec 033). The one-function `recipes/ctypes_stub.py` becomes the
  package `recipes/ctypes_stand_in/` (`ctypes/__init__`, `ctypes/_types`, `ctypes/util` in the
  zip). It names wasm32's C types with CPython's aliases (`c_int is c_long`), sizes them, lets a
  module declare `Structure`, `POINTER`, `CFUNCTYPE` and array types, gives numpy each simple
  type's true dtype (never `dtype('O')`), and makes `ctypes.util.find_library` answer `None`. It
  loads no library, makes no instance and touches no memory: each raises
  `OSError("ctypes is unavailable on wasm32-wasi")`. So `import pandas.io.clipboard` and
  `import numpy.ctypeslib` now import, and sympy's and threadpoolctl's import-time names resolve.
  The types are built on first use, so `import numpy` does not pay for them. `help(ctypes)` and
  `np.info` of a C type work; asking numpy or pandas for the dtype of a `Structure`, `Union`,
  pointer, array or function type raises the `OSError` (no layout is computed). `-V` still says
  "no ctypes": no foreign function can be called.
- **`pip install wasi-python` runs programs** (spec 028). wasmtime-py (`wasmtime>=49,<50`) is
  now a required dependency, so the plain install runs `wasi_python.run` and `wasi-python run`;
  the `run` extra is no longer needed. It is kept, empty, so `pip install "wasi-python[run]"`
  still works. An embedder that brings its own wasmtime installs with
  `pip install --no-deps wasi-python` and uses `artifacts()`; importing the package still never
  loads wasmtime. Where wasmtime is missing or cannot load (its pure wheel on an unsupported
  platform), `run` raises one `ImportError` naming `wasmtime>=49,<50`, with wasmtime's own error
  as its cause. The release now proves the plain install on all three systems.
- **Added: read-only mounts** (spec 032). `run(..., mounts=[Mount(provider, "/work")])` serves
  a guest's ordinary file calls from the embedder's own code: a provider answers `stat`, `list`
  and `read` on normalized paths with a value or an `Errno`, never raising, and is counted and
  limited (`max_file_calls=`, default `DEFAULTS.file_calls`, 10,000; then `trapped` is `"out of
  file calls"`). A mount may sit at `/` (not with `root=`). No import is added: the runner
  shadows the guest's 29 descriptor calls on a second linker used only with mounts, and forwards
  every call it does not own to wasmtime's own WASI, fuel-neutral. `Completed.files` records the
  provider calls and faults. Exports `Mount`, `FileProvider`, `Stat`, `Errno`, `FileRecord` and
  `FileFault`. A call without mounts is unchanged.
- **The build says where it is** (spec 027; the artifact set is unchanged). `scripts/build.sh`
  runs a preflight first (the host, its tools, and 2.5 GiB free on a first build) and prints
  one line for it. Each step's line now ends with its time, `ok <step>: … [3m02s]`, and a
  passing build ends with a summary: the total time, the three artifacts with their sizes and
  hash prefixes, and the next command. On a terminal one status line below them shows the
  running step, its time against the last run, ninja's `[n/N]` and the time left; a pipe, `CI`,
  `TERM=dumb` or `--plain` gets the plain lines only, and the terminal ends showing exactly them.
- **A failure says why.** A failing step prints `FAILED <step>`, the last 20 lines of its log,
  and last one `ERROR <step>: <reason>` line, whose reason is the log's last line starting
  `ERROR` (or `exit <n>`). Before, the reason was the last line matching `error` anywhere, which
  could name a harmless `Checking for strerror... Yes.`. On GitHub Actions it is also an
  `::error` annotation.
- **New options:** `--list`, `--from STEP`, `--resume` (from the step the last run did not
  finish), `--check` (the preflight alone), `--plain` and `--help`. Nothing is skipped on its
  own. Ctrl-C stops the running step at once and exits 130; a TERM or HUP to `build.sh` alone
  waits for the running step, then exits 143 or 129. Each run's times go to
  `build/logs/timings.tsv`.
- **The download step** prints `fetched <name>` or `present <name>` per pin and ends with
  `downloads: <n> pins, <f> fetched, <v> verified`; it needs `curl` only for a pin it must fetch.
- **Fixed: a cancel during a door call is named `"cancelled"`** (spec 030). A call made with
  `cancel=` whose event was set while the `host` blocked in a door call for more than a few
  ticks ended with `trapped="error while executing at wasm backtrace:"`; so did a deadline that
  passed there under `cancel=`. They now end `"cancelled"` and `"deadline"`, with `exit_code`
  and `fuel_used` `None`, as they do while the guest computes. The door's answer is still not
  delivered then, and a host's own cancellation (an exception such as
  `asyncio.CancelledError`) or a Ctrl-C still comes first.

### Judge

- **numpy's and pandas' own tests run in the guest** (spec 050): upstream's fast selection, 11
  groups, 63,717 passing in the snapshot binary; each known failure is a gap listed by node id
  (12 classes with members: platform facts the README states, and numpy's C test modules); no
  test traps the guest. A new metric, `passes`, may fall only with `--accept-fewer-passes`. The
  artifact set does not change.

## 0.1.0a3 — 2026-10-17

- **Breaking: nothing is writable by default** (the owner's rule, constitution §4.15; spec 025).
  A call given no root and no grants has no `/`, no `/tmp` and no `HOME`: it can import,
  compute, print, read the stdlib and call the door, and nothing else. Before, it got a fresh
  private writable `/`. To keep that, pass `root=True` (`--private-root` on the command line);
  or grant the folders the program needs. `root=None` now means no root, like `False`.
- **Security: a `root` is prepared only through the folder that was checked** (the 0.1.0a3
  security review, S1). The runner made `root/usr/local/lib` and `root/tmp` by path after
  checking the root, so a guest of another call with a writable folder above it could swap that
  folder for a link in between, and the runner removed a file named `usr`, `local`, `lib` or
  `tmp`, or made folders, outside every grant. It now works through the walked folder's
  descriptor; the guest never saw the wrong folder before, and still does not. A writable grant
  at, inside or above the host Python's own `stdlib` or `site-packages` is now refused (S2). The
  patch applier refuses a source tree that holds `.git` (S3).
- **`np.save` and `np.load` of files work** (the first carried patch,
  `recipes/patches/numpy-2.5.2/0001-npy-files-without-dup.patch`): they raised `OSError` 58,
  because numpy's `tofile`/`fromfile` need `os.dup`, which WASI lacks. The patch is the fix numpy
  is asked to take (its pull request is drafted for the owner) and goes when numpy releases it.
  `ndarray.tofile`, `np.fromfile` on real files and memory maps still fail. The next §5.6 security
  review reads this patch.
- **Carried patches** (the owner's decision; constitution §4.1): a fix the project cannot wait
  for may now be carried as a patch to a pinned project's source, under `recipes/patches/`, with
  its upstream pull request drafted under `context/upstream/patches/`. Each is reviewed, hashed in
  `MANIFEST`, named here, and deleted once upstream releases the fix. None is carried yet; the
  release check is now "the source trees are their tarballs plus the recorded patches".
- **Typed grants:** `run(grants=[Grant(host, guest, writable=False), ...])` gives the guest
  more host folders, each read-only unless it says `writable=True`, nested in any order;
  `root=False` gives it no `/`, only its grants. Every grant and `root` is walked folder by folder
  and checked before any work: no link a guest could have made, no read-only grant inside a
  writable one, no writable grant at, inside or above the runtime's own folders. After wasmtime
  opens each folder, the runner checks it opened the one it checked. `HOME` is made in the folder
  the guest sees at `/tmp`, and there is none without one.
- **The stdlib zip is read-only and no longer copied into a root:** every call sees it read-only
  at `/usr/local/lib`, from one folder per process that its exit removes (a killed process's is
  swept like its other folders). A `python315.zip` that 0.1.0a2 left in a reused root is never
  read again and may be deleted.
- **Some `root=` values are now refused** (a change): a root at, inside or above the runtime's
  own folders, such as the home folder, a project folder holding `.venv` or `build/artifacts`,
  or the temporary folder itself, since its guest could change files later calls trust; a root
  holding `wasi_python`'s or wasmtime-py's own code; a root still to be made where the module
  cache will be made; and a root reached through a link in a folder you can write. A missing
  root is still made. No grant, read-only either, may hold the temporary folder, which holds
  every call's private folders and `stdin`.
- **Grants on the command line:** `wasi-python run --grant GUEST=HOST`, `--grant-writable
  GUEST=HOST`, `--root HOST` and `--no-root`, each one of `run`'s arguments.
- **`wasi-python run`:** a command that runs one program and prints its result as one line of
  JSON, so any language can run agent code by spawning it (`python -m wasi_python run` is the
  same). Each option is one of `run`'s arguments; without options the call has `run`'s defaults.
- **A killed process's files are cleaned up:** a process killed mid-call left its private root
  (the guest's files) and its stdin folder (the caller's `stdin`) in the temporary folder for
  good. Each now has a locked lock file beside it naming the kernel that made it; the next
  wasi_python process on that kernel removes them at its first call, and never touches a live
  call's folders or another kernel's. On a temporary folder without file locks, calls go on
  and such folders stay, as before.
- **`trapped` names a trap by its kind** (a change to what it says): a stack overflow now reads
  `"stack overflow"`, not wasmtime's heading `"error while executing at wasm backtrace:"`, and so
  do `"unreachable"`, `"memory out of bounds"` and every other trap with a code. An error with no
  trap code keeps its first line.
- **The released wheel is the bytes a second host rebuilt:** the release workflow rebuilds the
  wheel on arm64 Linux and publishes only a wheel equal to it, byte for byte, whose artifacts
  match the set's `SHA256SUMS`.
- **Run from async code:** `run_async` runs a call on a worker thread, so an async server's
  event loop never waits for a guest. Cancelling the awaiting task stops the guest (checked
  every 50 ms while it computes, at once when it waits or calls the door, later when other
  threads hold the GIL) and frees its worker before `CancelledError` is raised. Calls share one
  pool per process of `DEFAULTS.async_workers` threads (the CPU count, at most 8).
  `run(cancel=event)` stops a guest from any thread (`trapped == "cancelled"`). A process forked
  after it ran a guest now refuses to run guests, instead of aborting (macOS) or losing its
  deadlines; at exit, `run_async`'s guests are stopped and its queued calls dropped.
- **sqlite3, bz2 and lzma are built in**, from three new pins (SQLite 3.54.1, bzip2 1.0.8,
  liblzma from xz 5.8.4), with no upstream patch. `bz2`, `lzma` and `tarfile`'s `bz2` and `xz`
  modes write the same bytes as native; `sqlite3` gives native's results, except the last digits
  of its math functions (trigonometric, hyperbolic, `atan2`, `log10`, one-argument `log`), which
  follow the guest's C library, and what changed since native's SQLite 3.53.1, such as JSON's
  float text; it has the native feature set (FTS3/4/5, R-tree, Geopoly, math functions,
  dbstat, percentile). `shelve` and `dbm` now create `dbm.sqlite3` files, as native does. `-V`
  now says "no ctypes, mmap, sockets, ssl or zstd": `compression.zstd` is the compression module
  still missing.
- **SQLite's limits in the guest** (the README's *sqlite3 in the guest*): one connection holds
  the database, through a `<db>.lock` directory beside it, while it writes or has a statement
  open, so a second connection gets "database is locked" after its busy timeout (5 s by
  default); `journal_mode=wal` stays `delete` unless `locking_mode=exclusive`; a guest stopped
  inside a transaction (killed, out of fuel, past its deadline, or by `os._exit`) leaves the
  lock and a hot journal in a reused root for the embedder to remove; SQLite's own
  `random()`, `randomblob()` and temporary names are seeded from the clock's second, so use
  `secrets`, `uuid.uuid4()` or `os.urandom` for IDs; a database in a read-only directory opens
  only through a URI that takes no lock, such as `file:<path>?immutable=1`; no
  `load_extension`; `sqlite3.threadsafety` is 0.
- **Sizes:** the three libraries add about 2 MB to `python.wasm` (SQLite is most of it); the zip
  is unchanged. `import bz2` and `import lzma` cost nothing more on the snapshot, which already
  holds them; `import sqlite3` is not pre-imported.

## 0.1.0a2 — 2026-10-17

The second alpha moves the line to CPython 3.15.0 and wasi-sdk 33, so a C++ exception inside a
package becomes a Python exception instead of ending the guest.

- **The line:** CPython 3.15.0, built with wasi-sdk 33; numpy 2.5.2, pandas 3.0.6 and the
  pure-Python packages are unchanged. The line's versions are named once, in
  `scripts/line.conf`.
- **C++ exceptions work:** numpy and pandas' C++ is compiled for WebAssembly exception handling
  in its standard form (`exnref`). A C++ error such as pocketfft's failed allocation now raises
  `MemoryError` in the program, which goes on.
- **Hosts must support exception handling.** wasmtime 47 or later runs it by default (as
  wasmtime-py does); wasmer, wazero and Node need a switch; WAMR and wasmi cannot run it. The
  README's *Hosts* lists them. For a host without it, use `0.1.0a1`.
- **The stdlib zip's guest name is now `/usr/local/lib/python315.zip`.** An embedder that lays
  out the root by hand must follow it; `wasi_python.run` does.
- **The snapshot** is made by the pinned wasmtime's own `wasmtime wizer` (the standalone Wizer
  pin is gone), and pre-imports `_colorize`, which 3.15 loads lazily, so the first traceback in
  a run does not pay for it.
- **Measured:** a snapshot call costs about 6.6% more guest instructions than on 3.14 (81.9M
  against 76.8M: CPython 3.15's own start-up and finalization); the stdlib zip is 6% larger.
- **Safe by default** (`run` changes for existing callers):
  - with no `root`, a call runs in a fresh private directory, removed afterwards;
  - a call has a 60 s deadline, a 1 GiB memory cap and a 16 MiB output cap per stream unless it
    passes others (`None` means no limit); a longer job now ends with `trapped == "deadline"`;
  - the guest's environment starts from `TMPDIR=/tmp`, `PYTHONTZPATH=` and a `HOME` made
    fresh for each call (under `/tmp`, removed after it), with `env=` laid over it, so
    `os.environ` is no longer exactly what `env=` gave;
  - a call's store is closed when the call ends, trapped or not, so a trapped call no longer
    holds its guest memory until Python's garbage collector runs;
  - `Completed` gains `truncated`, last, defaulting to `()`.
  - `run` refuses a limit of the wrong type (`TypeError`) or out of range (`ValueError`) before
    any work, where 0.1.0a1 passed it on: a negative `fuel` or `memory_bytes`, or a
    `memory_bytes` of 2**63 or more, meant no limit; `True` meant 1; a deadline of 0 or less ran
    one tick. Integer limits take any integer type (numpy's included) from 0 to 2**63 - 1; a
    deadline is a positive real number of seconds (not `Decimal`), at most about 4.6e16.
  - `run` refuses an `argv`, `env` or `stdin` the guest would see differently, before any work: a
    NUL in an argument, key or value, or text that is not valid UTF-8 (`ValueError`); an `=` in a
    key, or an empty key (`ValueError`); a `str` as `argv`, a non-`str` item or entry, or an `env`
    that is not a `Mapping` (`TypeError`). `stdin` must be bytes-like: `""`, `0`, `False` and
    `[]`, which meant empty input, are now a `TypeError`, as any other `str` already was. Messages
    never quote a value.
- **Planted code never runs:** only the stdlib zip is on `sys.path` and `site` does not run
  (`sys.flags.no_site == 1`), so a module, `.pth` or `pyvenv.cfg` one call leaves in a root is
  never run by the next. The plain reactor ran them before.
- **The door is bounded:** a frame past guest memory, a response over 2 GiB or a failing host is
  a host fault (−2); `run` no longer raises for them.
- **Fuel counts the guest only:** `fuel_used` and the `fuel` cap start after instantiation, so
  they no longer include wasmtime's copy of the memory image (42.35M instructions for the
  snapshot, 5.05M for the plain reactor, charged on macOS when compiled in the process and on
  Windows always). Figures from 0.1.0a1 are that much higher.
- **A sleeping guest keeps its deadline:** `time.sleep` and `select` no longer hold a call past
  its deadline; the runner answers the guest's waits itself, stopping at the deadline. One
  `poll_oneoff` takes at most 4,096 subscriptions (more answer `ENOMEM`: `select.poll()` on more
  than 2,047 descriptors), and a bad pointer answers `EFAULT`.
- **Concurrent calls share nothing:** calls from many threads no longer corrupt wasmtime-py's
  callback tables (after a few hundred concurrent calls, every later call raised, and a guest
  could reach another call's host or output). The host functions are defined once per engine,
  and outputs use the runner's own table. An exception a host raises, and Ctrl-C, now come back
  to the call that caused them; Ctrl-C while a guest computed could abort the whole process. A
  trap or exit inside the guest's allocator during a door call is that call's result, and its
  `fuel_used` is `None`. Concurrent first calls compile the module once.
- **A guest cannot make `run` raise by exhausting host file descriptors:** the call's store,
  which holds every descriptor the guest opened, is now closed before anything else is cleaned
  up. Before, `run` raised `OSError` (Errno 24) and left the stdin scratch file behind.
- **Release provenance:** from this release on, every asset is attested by the release workflow
  and verified before it is published; the notes say how to verify a download.
- **The snapshot honours extra preopens** by name and in any order, as the plain reactor does;
  before, it ignored them or swapped them.
- **The same bytes from any build host:** arm64 macOS and arm64 Linux rebuild the same artifact
  set from the pins, byte for byte, and the release workflow rebuilds it on an arm64 Linux runner
  and compares `SHA256SUMS` before anything is signed. x86_64 Linux is pinned and builds, but its
  `python.wasm` is not yet byte-identical (one numpy function compiles differently there).
  Every host links wasi-sdk's
  host-neutral sysroot and builtins, and the build sorts in the C locale, so `python.wasm`'s hash
  changes. Inside the guest, `sysconfig` and `numpy.show_config()` name the build machine
  `build`. `MANIFEST`'s `pin` lines now list every supported build host's inputs.
## 0.1.0a1 — 2026-10-17

The first alpha: CPython 3.14.8 for `wasm32-wasip1` with numpy 2.5.2 and pandas 3.0.6 compiled
in, built from pinned sources with no upstream patches.

- **The artifact set:** `python.wasm` (a WASI reactor), `python-snapshot.wasm` (the same binary
  with numpy and pandas pre-imported by Wizer), the bytecode-only stdlib zip (with
  python-dateutil, tzdata and six), `MANIFEST`, `SHA256SUMS` and the licence notices. Each
  rebuilds to the same bytes on one host.
- **The guest:** two imports only, WASI preview1 and one host door (`host::call`); `run` follows
  CPython's command line (`-c`, `-m`, a script, stdin, `-u`, `-V`).
- **The runner:** `wasi_python.run(argv, root=...)` runs one program in one call, with a host
  function for the door, fuel, a deadline, a memory cap and a private compiled-module cache
  (the `run` extra).
- **Known limits:** numpy's default integer is 32-bit; no threads, sockets, ssl, sqlite3, bz2 or
  lzma; a C++ exception aborts the guest (wasi-sdk 24); compute is about 1.3 to 2.3 times slower
  than native. Built and judged on arm64 macOS; the release workflow also checks it on Linux
  and Windows.

