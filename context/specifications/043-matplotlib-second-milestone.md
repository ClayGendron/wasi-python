# 043 — matplotlib, the second milestone: triangles, contours, SVG and PDF

- **Status:** **Spec 051's callback scan binds this build** (051, Decision 4a; written in when 051 landed): `test_callbacks_have_the_types_cpython_calls` is green, and a mismatch it finds is fixed by a carried patch or an upstream release, never by an exclusion. drafted 2026-10-17; revised 2026-10-18 against its pre-build review
  (`../reviews/043-matplotlib-second-milestone-spec-2026-10-17.md`): all eight findings written in, and its Disposition says where. Finding 1 also
  amended spec 037 (its status line says so). Confirmed for build 2026-10-18 with no new conditions; it builds only after the owner answers question 81. It changes the build recipe and the artifact
  set, so it is reviewed once more before it is built (constitution §5.6). It is build-class: it
  touches `scripts/`, `recipes/`, `downloads/SHA256SUMS` and the release workflow (§5.7). It is
  built only after the owner answers question 81 (contourpy's licence, §4.12), as spec 023 waited
  on question 35.
- **Owner:** Clay Gendron
- **Kind:** the build recipe (one pin; steps 55, 60 and 70; `scripts/gen_inittab.py`,
  `scripts/make_stdlib_zip.py`, `scripts/assemble_artifacts.py`), one recipe file (the
  meson-python stand-in), one carried patch to matplotlib and its upstream facts sheet, judge
  additions and changes (`tests/`, one golden job), the release workflow's tree count,
  `README.md`, `CHANGELOG.md`, `LICENSES/`. If spec 037 (scipy) lands first, also step 37, step
  57, a recipe file (`qhull_r.pc.in`) and a second carried patch (to qhull), as 037's amended
  Decision 8 defines them (Decision 6).
- **Depends on:** 023 (matplotlib M1), landed first: its pins, steps 37 and 55, its cross file
  and stand-ins, its step 60 and 70 machinery, its judge (the constructor and `target_features`
  checks, the recording-platform rule, the two known gaps this closes). Landed: 020 (carried
  patches), 012 (the same bytes from any host). If it has landed by then, 040 (x86_64 in the
  same-bytes gate). The owner's answer to question 81. Spec 037's Decision 8 and this
  specification's Decision 6 together fix one qhull in either order. Where 023 or 037 lands in
  another shape than its text, this specification uses what landed and says so in its landing
  notes.
- **Research it stands on:** `../research/2026-10-17-matplotlib-on-the-current-line.md` and its
  folder (contourpy 1.4.0 and `_qhull` built and run for `wasm32-wasip1`; finding 5, patch 2;
  finding 2, contourpy's meson-python question and `_build_config.py`; its sizes and link map);
  `../research/2026-10-16-what-matplotlib-needs.md` (contourpy's build, the `devnull` property,
  the one-pybind11 rule); spec 023's pre-build review
  (`../reviews/023-matplotlib-first-milestone-spec-2026-10-17.md`: 17 contourpy members, the
  per-member cost, the constructor lists). **The drafting runs** (EXECUTED 2026-10-17 in a
  scratch folder outside the repository, on the research memo's scratch builds, which are
  still there; nothing in the repository changed but this file, question 81 and the upstream
  draft):
  - a golden program (Delaunay, contourpy's three algorithms, `contourf`, `clabel`,
    `tricontourf`, `triplot`, SVG and PDF saves) natively under CPython with the PyPI wheels of
    matplotlib 3.11.2 and contourpy 1.4.0, at hash seeds 0 and 1, and in the guest on three
    scratch binaries (Decision 8);
  - the `/dev/null` probe with and without a `dev` folder in a writable root, on the memo's
    patched binary and on a binary relinked with this specification's patch
    (`../upstream/7-matplotlib-qhull-devnull/evidence/`);
  - this specification's patch made against the pinned tarball, applied with no offset, compiled
    and relinked into a scratch reactor with the memo's own link command;
  - contourpy's `threaded` algorithm with 1, 2, 4 and all threads, native and guest;
  - the import list, the PDF difference, the libc++ stream references (`llvm-nm`), scipy's
    vendored qhull against qhull 8.0.2 (`diff -r`), and the qhull format-string hunk made
    against the qhull tarball;
  - PyPI's JSON for contourpy (1.4.0 is the newest), GitHub's API for qhull pull request 143
    and qhull's releases, and matplotlib's `main` (`493abb1b63`).

## The problem

Spec 023 brings matplotlib in with line plots saved as PNG. Two common plots still fail, and two
common formats are not judged:

- **A triangulation from points** raises `ImportError` for `matplotlib._qhull`, because M1 leaves
  `_qhull` out of the link. It cannot be linked as it is: in a WASI guest its
  `fopen("/dev/null")` fails, so every Delaunay triangulation raises `RuntimeError: Could not
  open devnull` (EXECUTED by the memo, and again while drafting).
- **`contour` and `contourf`** raise `ModuleNotFoundError` for `contourpy`, the C++ package
  matplotlib draws every contour with. M1 does not build it.
- **SVG and PDF** are saved by M1, but no golden says their bytes are native matplotlib's.

023 names all three as this milestone (its Scope). Agents draw contour maps, heat maps with
contour lines, and triangulated surfaces; and they hand SVG and PDF to people.

## Decisions

1. **The milestone (M2).** `matplotlib.tri.Triangulation(x, y)` (Delaunay, through `_qhull`),
   `contour`, `contourf`, `clabel`, `tricontour`, `tricontourf`, `tripcolor` and `triplot` on
   points, and SVG and PDF saves whose bytes equal native matplotlib's (the PDF up to its font
   subset tags, Decision 8). Built in: matplotlib's `_qhull`, linked against step 37's qhull,
   with one carried patch (Decision 3); contourpy's `_contourpy` (Decision 4); contourpy's Python
   package in the zip. It closes both of 023's known gaps. Nothing else of 023 changes: the data
   grant, the font cache, step 80 and question 34 (pre-import) are as 023 leaves them.

2. **The versions and pins.**
   - **contourpy 1.4.0**, the sdist:
     `https://files.pythonhosted.org/packages/83/5a/a55177dd22553a277388e8a1b3220e92de91bacb28356cdc73caa240121d/contourpy-1.4.0.tar.gz`,
     SHA-256 `20156f5a1ac4f8ce02656e39a61e82164a3d359796dc8026f75b062783d500e1` (EXECUTED:
     PyPI's JSON while drafting, and the research's downloaded bytes). It is the newest release
     (EXECUTED, PyPI), it meets matplotlib 3.11.2's `contourpy >= 1.0.1` (READ, its
     `pyproject.toml`), and it has cp315 wheels, so the oracle runs it. It unpacks to
     `contourpy-1.4.0`, the tree rule's name. Its one runtime requirement, `numpy>=2.0`, holds
     the line's 2.5.2. If 023 landed this pin already (its
     Decision 2 takes the memo's list, which names it), it stays as it is; otherwise this adds it
     to `downloads/SHA256SUMS` and a `get` line to `scripts/00_download.sh`.
   - **Reused, not re-pinned:** qhull 8.0.2, pybind11 3.1.0 and `pkgconf` (023's); meson 1.12.1
     (the line's). One pybind11 in the binary, as 023 and 037 require.
   - **Not pinned: meson-python.** contourpy's `meson.build` asks the target Python for
     meson-python's version and writes it into `_build_config.py`; nothing else reads it (READ:
     `lib/contourpy/util/meson.build:28-34`). A stand-in answers (Decision 4).
   - **The oracle** (`tests/jobs/oracle`) already has contourpy 1.4.0 after 023 (matplotlib
     requires it; 023 pins its dependencies at the same versions). If 023's lock holds another
     version, this pins 1.4.0 there; the job's first line prints it, so a mismatch fails the
     golden.

3. **One carried patch: `_qhull` opens no file on WASI.**
   `recipes/patches/matplotlib-3.11.2/0002-qhull-without-devnull-on-wasi.patch`, 1,138 bytes,
   SHA-256 `8ea3cd418abad7d50ccb29f0514a1eddf430530ce967fdb6099fa2a160f7da20`, is
   `../upstream/7-matplotlib-qhull-devnull/fix.patch` byte for byte. `Files:
   src/_qhull_wrapper.cpp`. 12 lines added, none removed.
   - **What it does.** Under `__wasi__`, `delaunay_impl` makes its error stream with
     `fopencookie` and a write function that returns the size it is given and keeps nothing.
     It opens no path. Every other platform keeps `fopen(MPL_DEVNULL)`, unchanged.
   - **Why not the memo's form** (`fopen` first, the discard stream only if it fails). EXECUTED
     while drafting: with a writable root holding a `dev` folder, the memo's form creates a
     regular file `dev/null` in the host's folder. That is a write to the host no Python code
     asked for (§4.15's spirit). With this patch, the same run leaves `dev` as it was.
   - **Why a patch and not a recipe.** The path is a cross-file property, and no path is
     writable on every call (the memo, finding 5). Wrapping `fopen` at link time would change
     every caller. A force-included header would reimplement upstream code out of sight, which
     §6.2 ranks below a reviewed patch.
   - **Evidence** (EXECUTED, `../upstream/7-matplotlib-qhull-devnull/evidence/guest-run.txt`):
     it applies to the pinned tarball with no offset (`patch --dry-run`, `git apply --check`);
     the object compiled from it imports `fopencookie` and no longer `fopen`; relinked into the
     research's reactor, collinear points raise qhull's `singular input data` error (qhull's
     `longjmp` path), four points give two triangles, and Decision 8's program equals native.
     Without the patch, the program stops at `RuntimeError: Could not open devnull`.
   - **Upstream.** matplotlib's guide refuses pull requests made by AI tools (READ:
     `doc/devel/contribute.rst`, "Use of Generative AI"). So the draft is a facts sheet, as
     question 80 recommends for such projects: `../upstream/7-matplotlib-qhull-devnull/pr.md`,
     with spec 020's six header lines (`Status: drafted`). The builder moves it unchanged to
     `../upstream/patches/matplotlib-3.11.2/0002-qhull-without-devnull-on-wasi.md` (`git mv`),
     copies `fix.patch` byte for byte to the patch path, and updates
     `../upstream/README.md`'s row. The change is still needed on `main` (`493abb1b63`, READ)
     and applies there with a 3-line offset (EXECUTED). The patch goes when the pin moves to a
     release that carries an equal fix.
   - It joins 023's `0001-ft2font-enums-without-python.patch`; spec 020's applier applies both, in
     order, and the release workflow's zero-diff check judges the tree with both.

4. **contourpy: how a C++ extension becomes a builtin**, by 023's pattern for kiwisolver and
   matplotlib's own extensions.
   - **Step 55** (023's plot packages) gains contourpy after matplotlib. It unpacks the pinned
     sdist into `build/contourpy-1.4.0`, applies patches (none) and is judged by spec 020 like
     every tree. It configures with the line's meson and **023's matplotlib cross file**
     (`scripts/wasi-cxx`, the C++ exception flags, `-ffile-prefix-map`, the pinned `pkgconf`,
     pybind11's `pkgconfig` folder; `cmake` set to a program that does not exist), and:
     `--buildtype=release -Db_ndebug=if-release -Db_lto=false -Dwerror=false
     -Dpython.bytecompile=-1`. `werror=false` because contourpy's `meson.build` turns
     `werror` on and the SDK's headers warn (the memo, 6.7). `b_ndebug=if-release` because that
     is meson-python's default, so the code is the wheel's code (contourpy's `.cpp` files hold
     142 `assert`s, READ). Then `ninja`, then `meson install --tags python-runtime`, as 023 installs
     matplotlib.
   - **No numpy at build time.** contourpy compiles against pybind11 alone; pybind11's numpy
     support binds numpy's C API when the module is imported (EXECUTED by the memo: its configure
     found only pybind11 and python, and the guest ran).
   - **The meson-python stand-in.** `recipes/meson-python-stand-in/meson_python-0.dist-info/METADATA`,
     three lines: `Metadata-Version: 2.1`, `Name: meson-python`, `Version: 0+stand.in`. Step 55
     puts its folder on `PYTHONPATH` for contourpy's `meson setup` alone; the cross file's
     `python`, `scripts/python-wasi-cross`, passes it through (023, Decision 4). The version
     says what is true: meson-python never ran. `_build_config.py` then reports
     `mesonpy_version="0+stand.in"`. The memo's stand-in claimed `0.22.1`, which never ran.
   - **The link.** `scripts/wasi-cxx` writes `_contourpy.cpython-315-wasm32-wasi.so` as an
     archive of its 14 objects and a `.deps` file, as for every extension. Step 60 takes the
     inittab name `contourpy._contourpy` from the install path (023's `gen_inittab.py`), and its
     clash check runs. No init name clashes: `PyInit__contourpy` is new (READ: the memo's list).
   - **The zip.** Step 70 drops 023's exclusion of contourpy and packs the installed tree by
     step 70's rules: 17 files, `py.typed` among them, 61,732 bytes deflated in the research
     zip (EXECUTED by the memo and by the review), plus `contourpy-1.4.0.dist-info/METADATA`:
     18 members. The two `bokeh_*` modules go in too: they import `bokeh`, which
     the profile does not carry, so they fail at import as they would natively without it, and
     leaving them out would save two members only. contourpy's `METADATA` goes in as 033 and 023
     put matplotlib's (from `PKG-INFO`).
   - **`_build_config.py` is made host-neutral** (spec 012, Decision 5). It records the builder's
     paths (`build_dir`, `source_dir`, `python_path`, `compile_command`, the cross file in
     `build_options`) and the build host (`build_cpu`, `build_cpu_family`,
     `build_cpu_system`: EXECUTED, the memo's file says `aarch64` and `darwin`).
     Three code paths change (the review, finding 4, READ):
     - `make_stdlib_zip.py`'s `REWRITE` gains `contourpy/util/_build_config.py`. Its keys are
       keyword arguments of the `dict(...)` call `build_config()` returns, not numpy's
       `"Machine Information"` dict literal, so `_host_items` gains a second parse for them,
       with numpy's rule: `CONTOURPY_BUILD_KEYS` (`build_cpu`, `build_cpu_family`,
       `build_cpu_system`) are set to `build`, and a key absent, or not reading back as
       `build`, stops the build. `build_cpu_endian` stays `little`. Step 70's existing
       `--replace` rules turn every path into `/wasi-python-build/…`; the error text for an
       unused rule names the three members, not two. The rest is host-neutral once paths are
       replaced (`compiler_version="22.1.0"`, `linker_id="ld.lld"`, `python_install_dir`
       under `/usr/local`; READ in the memo's file).
     - `tests/harness/artifacts.py`: `HOST_FACT_MEMBERS` gains
       `contourpy/util/_build_config.pyc`, and `host_fact_errors` applies the bare-`linux`
       word to it as to numpy's member (today's condition is `startswith("numpy/")`).
     - `tests/unit/test_artifact_rules.py:351` unpacks `sysconfig, config =
       rules.HOST_FACT_MEMBERS`, which a third member breaks; it is changed with them.
     A host word left fails the judge's host-fact check (Decision 9).

5. **`_qhull` joins the link.**
   - Step 60 no longer leaves `_qhull` out (023 left it out with `_tkagg`; `_tkagg` stays out).
     Its `.deps` names `-L<step 37's prefix>/lib -lqhull_r`, which 023's step 60 already honours,
     so step 37's `libqhull_r.a` is linked once. `-lwasi-emulated-process-clocks` is already in
     CPython's link, for qhull's `clock()` (023 compiles qhull with
     `-D_WASI_EMULATED_PROCESS_CLOCKS`). Its reads go through the wrapped `clock_time_get`, so
     fuel stays exact.
   - **One more WASI import:** `fd_renumber`, from qhull's `freopen` (`global_r.c:1386, 1406`,
     for the `TI` and `TO` options, which matplotlib never passes; READ). It is a preview1 call,
     so §4.4 holds. EXECUTED: the relinked scratch reactor imports 44 functions against today's
     43, and the judge's `wall_errors` finds nothing. The hostile-guest checks already exercise
     `fd_renumber` (`tests/unit/test_runner_grants.py`).
   - **Constructors: none expected.** The research build that linked contourpy, `_qhull` and
     qhull had ten constructors (023's review). By the link map, none is from them: they are
     CPython's, the inittab's, `_path`'s two, kiwisolver's and libc++'s streams (READ while
     drafting). libc++'s streams are already in M1: `_tri`, `ft2font` and kiwisolver reference
     them too (EXECUTED, `llvm-nm`). So 023's reviewed list should not change. If the build
     shows a new one, its source is read before the list grows, as 023 and 037 require.
   - `target_features` should not change either: the memo's build with both had today's list
     (023's review, EXECUTED there).

6. **One qhull, in either order with spec 037.** 037 links scipy's vendored qhull. Its
   Decision 8, as amended on 2026-10-18 by this specification's pre-build review (finding 1;
   037's status line says so), defines the shared qhull once, in conditions a to f. This
   decision follows it; it does not restate a second version.
   - **The end state, whichever lands first.** One qhull: step 37's, from the pinned qhull 8.0.2
     tarball, which both matplotlib (`-Dsystem-qhull=true`) and scipy
     (`-Duse-system-libraries=qhull`) link. It carries scipy's one change to qhull as a recorded
     patch, defined in 037's condition d: `recipes/patches/qhull-8.0.2/0001-format-strings.patch`,
     its draft with `Status: merged https://github.com/qhull/qhull/pull/143` and `Files:
     src/libqhull_r/poly2_r.c`. EXECUTED while drafting and again by the review: scipy 1.18.1's
     vendored `libqhull_r` is qhull 8.0.2's, file for file, except that one hunk of `poly2_r.c`
     (a `trace1` call missing its three arguments, qhull's pull request 143, merged 2025-08-07 as
     `1b67ec90`, unreleased: only `v8.1-alpha1` of 2021 since; EXECUTED, GitHub's API). The hunk
     applies to the qhull tarball with no offset. So scipy links the same source it would have.
   - **Init names, in either order.** scipy's `scipy.spatial._qhull` and matplotlib's `_qhull`
     both define `PyInit__qhull`. 037 now renames scipy's to `PyInit_scipy_spatial__qhull` in
     every order (its Decision 8, "Init names"), so this specification renames nothing.
   - **A: this lands before 037 (the plan, Decision 13).** This specification links step 37's
     qhull as it is, with no qhull patch and no `qhull_r.pc`: matplotlib never traces, so the
     hunk is unreachable for it (READ, its fixed command `"qhull d Qt Qbb Qc Qz"`), and its
     configure finds qhull with `find_library` (`extern/meson.build:72-77`, READ by the review).
     matplotlib's linked qhull is then its PyPI wheel's. 037's builder does conditions a, b, d,
     e and f.
   - **B: 037 has landed first.** This specification does conditions a, b, d, e and f, as 037
     words them: step 37's `qhull_r.pc` from `recipes/qhull_r.pc.in`; step 57's fourth
     `pkgconf` folder and `-Duse-system-libraries=qhull`; the qhull patch and its draft; once the
     `.pc` exists, a check that `_qhull`'s `.deps` names step 37's archive once (matplotlib's
     configure may then find qhull through `pkgconf`); and acceptance criterion 6 (one copy of
     qhull's functions). 037's checks must pass unchanged on the shared qhull.

7. **No threads in contourpy.** contourpy's `threaded` algorithm asks
   `std::thread::hardware_concurrency()`. In the guest that is 1, so `contourpy.max_threads()`
   is 1 and any `thread_count` runs as one thread: no `std::thread` is started. EXECUTED while
   drafting, a 201 × 201 grid: native gave thread counts 1, 2, 4 and 10; the guest gave 1 each
   time, with the same lines (659, 664 and 704 points, equal sums). This is the platform's "no
   threads", stated in the README. contourpy's default algorithm and matplotlib's
   (`mpl2014`) are serial.

8. **The goldens: one job, natively matched.** `tests/jobs/plot_contour.py` is a job like 023's
   `plot_line.py`, run on both binaries, its golden written by `regen.py` under the oracle with
   `MPL_IGNORE_SYSTEM_FONTS=1` and a fresh `MPLCONFIGDIR`, recorded on darwin-arm64 and
   reproduced under the oracle on that platform only (023's rule). It prints, in order:
   - the versions of matplotlib, contourpy and numpy;
   - a Delaunay triangulation of 30 points from `default_rng(7)`: the shape, and the SHA-256 of
     its triangles and of its neighbours, unsorted;
   - collinear points' `RuntimeError` message;
   - contourpy's `serial`, `mpl2014` and `mpl2005` lines at one level on a 41 × 41 grid: line
     count, point count, and the sums rounded to nine digits (as the numpy jobs print floats);
   - a 6 × 3 inch figure at 100 dpi: `contourf` and `contour` with seven levels, `clabel`,
     `tricontourf` on the triangulation, `triplot`; the levels;
   - `savefig` to SVG with `rcParams["svg.hashsalt"]` fixed and `metadata={"Date": None}`: size
     and full SHA-256;
   - `savefig` to PDF with `metadata={"CreationDate": None}`: size, the number of font subset
     tags replaced (6 in the drafting run), and the full SHA-256 of the file with each tag
     (`/[A-Z]{1,6}\+`) replaced by `/XXXXXX+`;
   - the RGBA buffer's shape and SHA-256.

   **Why each fixed setting.** SVG ids come from a random salt unless `svg.hashsalt` is set; SVG
   and PDF carry the time unless `Date` or `CreationDate` is `None` (or `SOURCE_DATE_EPOCH` is
   set, which matplotlib honours in both; READ, `backend_svg.py:409-411`,
   `backend_pdf.py:146-148`). The job passes them explicitly so the oracle's environment cannot
   change it.

   **Why the PDF's tags are normalized.** matplotlib names a font subset from
   `hash(frozenset(...)) % (2 * (sys.maxsize + 1))` (`backend_pdf.py:794-814`, READ). In the
   guest `hash()` is 32 bits wide and `sys.maxsize` is 2**31-1 (EXECUTED), so the six tags
   differ from a 64-bit Python's. EXECUTED while drafting: they are the only difference. With
   them normalized the guest's PDF equals native's at the default compression and with
   `pdf.compression` 0. A tag is shorter than six letters when the hash is below 26**5, about
   0.28% of glyph sets in the guest (INFERRED by the review from `_get_subset_prefix`), so the
   pattern takes one to six letters; the count is printed so a change in fonts shows as a line,
   not only as a hash. Normalizing hides nothing real: the tag is a function of the glyph set,
   which the file writes in full elsewhere. The guest's own bytes are deterministic: the hash
   is of glyph indices (ints), which no hash secret touches, and a frozenset's hash does not
   depend on order (READ by the review); so a check pins them too (Decision 9).

   **The drafting run and the review's.** Every line above but the PDF's raw hash was equal,
   guest and native, on two scratch binaries; the review repeated it natively at
   `PYTHONHASHSEED` 0, 1, 12345 and random, and in the guest with the judge's seeded secret and
   two `os.urandom` secrets (EXECUTED there; the drafting folder holds compression levels, not
   seeds): Delaunay `(48, 3)` `8131bfe18b9fc320…`
   (sorted) and `89432076058c35fd…` / `9339a93a6b6b6bff…` (unsorted, neighbours), the three
   algorithms' sums, the levels, the SVG (58,400 bytes,
   `1513d0794da9b7547652301f648f4b5a2b3b75035b407f8c21f1d835c4b6d613`), the normalized PDF
   (15,856 bytes, `87d654b405dfbd42…`) and the RGBA buffer (`c7c9f6d76874a4d2…`). The guest's
   raw PDF was `96eb6c55ce5b19ad3dd71aefb8db92cd361008c08d06ec36a26fe124cd32d7b2` on both.
   The line's pinned host Python 3.15.0, which the oracle runs, has zlib 1.2.12, as the drafting
   run's had (EXECUTED); the guest's is 1.3.1, and the compressed streams were equal. **If the
   oracle's compressed streams ever differ** (a zlib difference, as 023 found for PNG), the job sets
   `pdf.compression` to 0 and the landing notes say why; that is a change to the job before it
   is accepted, not a weakening after.

   The PostScript, EPS and PGF backends stay unjudged (Scope).

9. **The checks**, each seen failing first (Acceptance criterion 1 says how):
   - **v1.3, the milestone:** the `plot_contour` job against its golden (Decision 8), on both
     binaries.
   - **v1.3:** the guest's raw PDF bytes from the job equal a pinned SHA-256, the same on both
     binaries (as 023 pins the PNG's bytes). The value is the build's; the drafting run's is in
     Decision 8. The pin moves with the guest's zlib (step 30), since the PDF's streams are
     deflated at level 6: a zlib release (§5.5) then needs a judge change, with its reason,
     and the normalized golden must still equal native.
   - **v1.3:** `contourpy.max_threads()` is 1, and on Decision 7's grid `threaded` with
     `thread_count=4, chunk_count=16` reports one thread and gives point arrays equal to
     `serial`'s with the same `chunk_count=16`. The chunk count is fixed for both, because the
     lines' points depend on it (659, 664 and 704 at 0, 4 and 16; EXECUTED by the review).
   - **v1.2, no host file:** in a call whose writable root holds a `dev` folder, a Delaunay
     triangulation and a qhull error leave every writable grant as it was: the check lists
     every path under each writable grant, with its type and size, before and after, and
     requires them equal. The font cache's folder (`MPLCONFIGDIR`) is its own grant, listed
     before the triangulations (after matplotlib's import) and after, and must not change
     either. It fails on the memo's patch form (EXECUTED while drafting and by the review) as
     well as on M1's set.
   - **v1.5:** `test_stdlib_zip_names_no_build_host` covers contourpy's member (Decision 4's
     three code paths), judged with numpy's word list, bare `linux` included.
   - **The known gaps.** 023's two entries (`_qhull`'s `ImportError`, contourpy's
     `ModuleNotFoundError`) are removed: their checks pass, and a gap whose check passes fails
     the run until removed.
   - **Judge changes**, under `--accept-judge`: the two gaps; `SOURCE_PATTERNS` and
     `needs.SOURCE_COMPONENTS` gain contourpy (one tree more; the release workflow's count rises
     by one); `scan.cpp_exception_errors` judges contourpy's flags; `HOST_FACT_MEMBERS`,
     `host_fact_errors` and `tests/unit/test_artifact_rules.py`; the jobs list and its recording platform; the judge's package and licence lists. In branch B,
     the qhull patch's tree is qhull's, already judged.
   - **Unchanged, and still run:** 023's constructor check, `target_features` check, import
     wall, and every v1.2 and v1.4 probe that does not import matplotlib.

10. **What it costs, stated so growth can be told from regression.** Each number is measured by
    the build and recorded in the landing notes; one outside its range by more than a tenth is a
    finding for the build review, not a reason to accept.
    - **`python.wasm`:** about +0.8 to +1.0 MB (about +2.5%), code and data. Code: contourpy
      383,527 bytes, qhull 302,109, `_qhull` 13,287 (EXECUTED by the review, the drafting
      relink's map summed by output section; the memo's map gave 388,785 and 302,293). Data:
      string literals are merged at link, so the map attributes only 5,866 bytes of `.rodata`
      to them; their objects carry 109,831 (qhull) and 138,068 (contourpy) bytes of `DATA`
      before merging (EXECUTED by the review, `llvm-objdump -h`). contourpy's asserts' code and
      text leave with `-Db_ndebug=if-release` (the memo built with asserts on), which pulls the
      number toward the low end. libc++'s streams are already in M1 (Decision 5). The memo's
      full build, M1 and M2 together, was 38,008,426 bytes stripped.
    - **The snapshot:** about the same +0.8 to +1.0 MB; matplotlib is not pre-imported
      (question 34).
    - **The zip:** +18 members, about +63 KB (Decision 4).
    - **Plain `-c pass`:** +18 members at 023's review's 76,490 instructions each, about +1.4 M
      fuel (+0.5%; INFERRED). If spec 035 has landed, its own per-member cost applies instead.
      Snapshot `-c pass`: about +0.05% (INFERRED from 023's review: +2.0% for 681 members).
    - **`import matplotlib.pyplot`:** no change. contourpy and `_qhull` load only when a contour
      or a triangulation is made (READ by 023's review).
    - **The new job:** about 9.2 G fuel on a plain reactor with a warm font cache, 11.2 G cold
      (EXECUTED on the scratch build, which had contourpy's asserts on; the review measured
      9,236,815,441 and 11,225,967,512). The judge's run records its own. It is a new pass, accepted with
      `--accept`; the growth to accept is the existing checks' (above).

11. **Licences** (§4.12). `LICENSES/` gains contourpy's `LICENSE` (BSD-3-Clause; question 81).
    contourpy's `mpl2005` code came from `gcntr.c`, part of the GIST package
    (`src/mpl2005_original.cpp:7`, READ), and contourpy ships only its own `LICENSE`. The
    notice that covers GIST's code is the Regents of the University of California's (1996),
    which asks that it be "included in all copies of any software which is or includes a copy
    or modification of this software"; matplotlib ships it as `LICENSE/LICENSE_YORICK`, and
    023 ships matplotlib's whole `LICENSE/` folder (its Decision 9). This specification checks
    that `LICENSE_YORICK` is in the release's `LICENSES/` and names it beside contourpy's in
    the judge's licence list, so it stays if 023's list changes. Question 81 names it, so the
    owner approves knowingly. Also, now that qhull is linked, qhull's `COPYING.txt` (the Qhull licence, approved by the
    2026-10-16 decision and question 35). In branch B, scipy's `LICENSES_bundled` already names
    qhull; the file from step 37's tree is still the one shipped, since that is what is linked.
    `assemble_artifacts.py`'s `PACKAGES` and licence lists gain contourpy.

12. **Documentation.**
    - **README.** matplotlib's section: triangulation, contours and SVG and PDF saves work; for
      reproducible files, set `svg.hashsalt` and pass `metadata` with `Date` or `CreationDate`
      `None` (or set `SOURCE_DATE_EPOCH`), as natively; a PDF's font subset tags differ from a
      64-bit Python's because `hash()` is 32 bits wide; contourpy runs one thread
      (`max_threads()` is 1); the import list's one new WASI call, `fd_renumber`. The
      `upstream patches carried:` count rises by one (two in branch B).
    - **CHANGELOG.** One entry: M2, naming
      `recipes/patches/matplotlib-3.11.2/0002-qhull-without-devnull-on-wasi.patch` (and in
      branch B `recipes/patches/qhull-8.0.2/0001-format-strings.patch`).

13. **Ordering, and one builder** (§5.7: one build-class specification in flight).
    - **After 023**, which this extends. The roadmap puts matplotlib's M2 before scipy
      (milestones 2 and 3), so the plan is **043 right after 023, before 037**. It is small next
      to 037: one pin, one patch, one package, one job. Under branch A, 037's builder then
      meets conditions a to f of 037's amended Decision 8 (Decision 6).
    - **If 037 is already in flight** when this is confirmed, 043 waits for it to land and
      builds under branch B.
    - **040:** once landed, its rule binds here: the three hosts' sets are equal, with no
      exception, and the landing notes record the x86_64 rebuild's time. contourpy's 14 C++
      files and `_qhull_wrapper.cpp` compile through the cross file's `scripts/wasi-cxx`, which
      reaches `$SDK/bin/clang++`, the launcher on x86_64. Nothing here needs a change for it.
    - **042 (seaborn):** its bivariate `kdeplot` draws through `contour` (INFERRED from
      seaborn's design), so 042 after 043 avoids a known gap there.
    - **Files shared with others:** steps 55, 60 and 70, `gen_inittab.py`, `make_stdlib_zip.py`,
      `assemble_artifacts.py`, `00_download.sh` (023, 033, 035, 037, 039, 041); `README.md`'s
      patch count (041). Each is rebased onto main as it is when this builder starts.
    - **One builder.** One package and one patch, against 023's five libraries, four packages
      and a runner change (INFERRED: a fraction of 023's work). It is not split.

## Intent

An agent's code triangulates scattered points, draws filled and labelled contours, and saves the
figure as SVG or PDF in a granted folder, inside the same sealed Python, and gets the bytes
native matplotlib gives, with no file made anywhere it did not ask for.

## Design

| file | change |
|---|---|
| `downloads/SHA256SUMS`, `scripts/00_download.sh` | the contourpy sdist, unless 023 pinned it (Decision 2) |
| `recipes/patches/matplotlib-3.11.2/0002-qhull-without-devnull-on-wasi.patch` | new: `../upstream/7-matplotlib-qhull-devnull/fix.patch`, byte for byte (Decision 3) |
| `context/upstream/patches/matplotlib-3.11.2/0002-qhull-without-devnull-on-wasi.md` | moved from `../upstream/7-matplotlib-qhull-devnull/pr.md`, unchanged (Decision 3) |
| `context/upstream/README.md` | the row says the patch is carried and where its sheet moved |
| `recipes/meson-python-stand-in/meson_python-0.dist-info/METADATA` | new: three lines (Decision 4) |
| `scripts/steps/55_plot_packages.sh` | contourpy: unpack, patch, configure, build, install (Decision 4) |
| `scripts/gen_inittab.py`, `scripts/steps/60_link.sh` | `_qhull` linked; `contourpy._contourpy` (Decisions 4, 5) |
| `scripts/steps/70_zip.sh`, `scripts/make_stdlib_zip.py` | contourpy's tree; `REWRITE`, `CONTOURPY_BUILD_KEYS` read from `build_config()`'s `dict(...)` keywords, the `--replace` error text (Decision 4) |
| `scripts/assemble_artifacts.py`, `LICENSES/` | contourpy and qhull (Decision 11) |
| `tests/jobs/plot_contour.py`, `plot_contour.expected`; `JOBS` in `tests/harness/jobs.py` | the golden (Decision 8) |
| 023's matplotlib check file under `tests/checks/`, `tests/checks/test_v1_2_hostile_guest.py` | Decision 9's v1.3 and v1.2 checks |
| `tests/harness/artifacts.py`, `pins.py`, `needs.py`, `scan.py`, `tests/known_gaps.toml` | the judge changes (Decision 9); `HOST_FACT_MEMBERS` and `host_fact_errors`' word-list condition (Decision 4) |
| `tests/unit/test_artifact_rules.py` | line 351's two-member unpack, for the third member (Decision 4) |
| `.github/workflows/release.yml` | the tree count, one more |
| `README.md`, `CHANGELOG.md` | Decision 12 |
| **Branch B only:** `recipes/patches/qhull-8.0.2/0001-format-strings.patch`, `context/upstream/patches/qhull-8.0.2/0001-format-strings.md`, `recipes/qhull_r.pc.in`, `scripts/steps/37_plot_libs.sh`, `scripts/steps/57_scipy.sh` | one qhull, 037's conditions a, b, d, e, f (Decision 6) |

## Scope

In: Decisions 1 to 13. Out:

- **Pre-importing matplotlib in the snapshot:** question 34, decided from 023's numbers.
- **Goldens for PostScript, EPS and PGF.** PS and EPS save (023), unjudged. PGF needs a TeX
  install, which the sandbox does not have.
- **Type 42 PDF fonts and mathtext in a golden.** They go through fontTools' subsetter and the
  mathtext parser; a later job can add them once fontTools is trimmed (023's Scope).
- **contourpy's bokeh renderer** (no bokeh in the profile) and **threads** (none on this
  target).
- **Trimming fontTools:** 023's Scope.

## Acceptance criteria

1. **The checks exist and were seen failing first,** each recorded in the landing notes:
   - on 023's set: the `plot_contour` job (`ImportError` for `matplotlib._qhull`), the PDF pin,
     the threads check (`ModuleNotFoundError`), the no-host-file check (`ImportError`), and the
     host-fact check once its member is added (no member yet);
   - on a build without patch 0002: the job stops at `RuntimeError: Could not open devnull`;
   - on a build with the memo's fallback form of the patch: the no-host-file check finds
     `dev/null` under the writable root (the drafting run and the review did; the builder
     repeats it once);
   - with the `_build_config.py` rewrite turned off: the host-fact check names `darwin` or
     `aarch64`; with a `CONTOURPY_BUILD_KEYS` key removed from the member: step 70 stops;
   - the threads check with `serial` at another `chunk_count` than `threaded`'s: it fails
     (the points differ), which shows the fixed count matters.
2. **A full build from pins in a clean clone** applies matplotlib's two patches with no offset,
   builds contourpy, links `_qhull` and `_contourpy`, and makes a set whose binaries run the job
   and the checks. `MANIFEST` names the contourpy pin, the stand-in and patch 0002 (and in
   branch B the qhull patch and `qhull_r.pc.in`).
3. **The same bytes.** The arm64 Linux rebuild gives the same `SHA256SUMS` as macOS (spec 012);
   once 040 has landed, the x86_64 rebuild does too. No exception. If a difference cannot be
   fixed after two attempts, the build stops and a memo records it (AGENTS.md rule 7).
4. **The judge.** `uv run pytest` is green with `--accept "<reason>"`, `--accept-judge "<the
   judge changes>"` and `--accept-growth "<Decision 10's classes>"`.
5. **The numbers recorded** in the landing notes: `python.wasm`'s, the snapshot's and the zip's
   bytes; the zip's members; plain and snapshot `-c pass`; the job's fuel on both binaries; the
   constructor list (and any new name with its source read); the import count; and, once 040
   has landed, the x86_64 rebuild's wall time. Each against Decision 10.
6. **Branch B only** (037's conditions e and f): 037's scipy goldens and its `QhullError` check
   pass unchanged on the shared qhull; `_qhull`'s `.deps` names step 37's archive once after
   `qhull_r.pc` exists; and `llvm-nm` on the unstripped link finds each of qhull's functions
   (`qh_new_qhull` among them) defined once in `python.wasm`.
7. **A release dry run** passes every job.

## The owner's choices

None open here. One approval this specification needs is recorded as **81** in
`../questions-for-the-owner.md`: contourpy's licence (BSD-3-Clause) is not yet named in §4.12,
so it is built only after the answer (the agent recommends approving it, as kiwisolver's was).
The entry also names `LICENSE_YORICK`, the notice for contourpy's GIST-derived `mpl2005` code
(Decision 11).
The upstream draft follows question 80's recommendation (a facts sheet, since matplotlib refuses
AI-made pull requests); if the owner answers 80 otherwise, the sheet is rewritten before the
build moves it.

## Landing notes

Not built.
