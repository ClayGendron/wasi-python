# 043 — matplotlib, the second milestone: triangles, contours, SVG and PDF

- **Status:** built 2026-10-19 (Landing notes); build reviewed 2026-10-19 (`../reviews/043-matplotlib-second-milestone-build-2026-10-19.md`: lands once F1; F1, F4, F5 and F6 answered at `737cef6`, F2 at the rebase); rebased onto main `f7511b7`, then stacked on spec 086 and rebased onto main `ebd0449` (wave 04 landed); rebuilt under wasi-sdk 34, `SHA256SUMS` `4c7099a4…`; fast tier 0 fail; branch dry run `39369636353` red only for growth; enters wave 06 stacked with 037 (For the lane). **Spec 051's callback scan binds this build** (051, Decision 4a; written in when 051 landed): `test_callbacks_have_the_types_cpython_calls` is green, and a mismatch it finds is fixed by a carried patch or an upstream release, never by an exclusion. drafted 2026-10-17; revised 2026-10-18 against its pre-build review
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

Built 2026-10-19 by an agent (Claude Opus 5.5) in the worktree `wasi_python-043`, branch
`spec/043-matplotlib-second-milestone`, from main `08de0c8`, under **branch A** of Decision 6:
spec 037 has not landed (it is being built in its own worktree), so this links step 37's qhull as
it is, with no qhull patch and no `qhull_r.pc`; 037's builder then meets conditions a, b, d, e and
f of 037's amended Decision 8. Every number below is EXECUTED on darwin-arm64 unless marked; fuel
is the judge's driver's (fixed clock and entropy, exact). Scratch scripts and logs are in the
session scratchpad (`043/`) and under the worktree's `build/`, not in git. The judge was run in the
worktree on its own build, with `-n 3`, never with `--accept`.

**Commits.** `0f9e28c` (the judge), `38a882b` (the recipe, the patch and its facts sheet, README,
CHANGELOG, the release's tree count), and the commit carrying these notes.

### What changed

- **The pin:** contourpy 1.4.0's sdist in `downloads/SHA256SUMS` and a `get` line in
  `scripts/00_download.sh` (023 had not pinned it; the oracle already locked 1.4.0).
- **Carried patch 0002:** `recipes/patches/matplotlib-3.11.2/0002-qhull-without-devnull-on-wasi.patch`
  is `../upstream/7-matplotlib-qhull-devnull/fix.patch` byte for byte (1,138 bytes, SHA-256
  `8ea3cd41…7da20`, as Decision 3 says); its facts sheet moved unchanged by `git mv` to
  `../upstream/patches/matplotlib-3.11.2/0002-qhull-without-devnull-on-wasi.md`; the index row and
  `notes.md` say so. Carried patches: 7 → 8.
- **The stand-in:** `recipes/meson-python-stand-in/meson_python-0.dist-info/METADATA`, the three
  lines of Decision 4. The built `_build_config.py` says `mesonpy_version="0+stand.in"` (step 55
  stops if it does not).
- **Step 55** unpacks, patches (none) and builds contourpy with meson and matplotlib's cross file
  (`--buildtype=release -Db_ndebug=if-release -Db_lto=false -Dwerror=false
  -Dpython.bytecompile=-1`), the stand-in on `PYTHONPATH` for that configure alone (a subshell),
  then `ninja` and `meson install --tags python-runtime`. The extension-placing script is written
  once and run for matplotlib and for contourpy.
- **Steps 60 and `gen_inittab.py`:** `_qhull` is no longer left out (`_tkagg` still is);
  `contourpy._contourpy` is registered from its install path. `_qhull`'s `.deps` names
  `-L…/plot-libs/lib -lqhull_r`, so step 37's `libqhull_r.a` is linked once. Inittab: 2 modules
  more, no clash.
- **Step 70 and `make_stdlib_zip.py`:** contourpy's tree and METADATA; `REWRITE` gains
  `contourpy/util/_build_config.py`, whose `CONTOURPY_BUILD_KEYS` are read from the keywords of
  the `dict(...)` call `build_config()` returns, by numpy's rule; the unused-`--replace` text
  names the three members.
- **`assemble_artifacts.py`:** `PACKAGES` gains contourpy 1.4.0 and qhull 8.0.2; `LICENSES/`
  gains `contourpy.txt` (contourpy's `LICENSE`, then matplotlib's `LICENSE/LICENSE_YORICK`, GIST's
  notice for its `mpl2005` code) and `qhull.txt` (qhull's `COPYING.txt`).
- **The judge** (one judge change, for `--accept-judge`): the `plot_contour` job, its golden and
  platform file; `test_plot_contour_job_matches_native[plain|snapshot]` (v1.3, the golden, the
  SVG and normalized PDF files saved in a granted folder, and the raw PDF pin
  `9f21cc48…4f32b990`); `test_contourpy_runs_one_thread` (v1.3);
  `test_a_triangulation_leaves_every_writable_grant_as_it_was` (v1.2); 023's two gaps removed
  (their checks pass); `SOURCE_PATTERNS` and `needs.SOURCE_COMPONENTS` gain contourpy (20 trees;
  the release workflow's count is twenty); `scan.cpp_exception_errors` requires every `meson
  setup` in step 55 to name matplotlib's cross file and one of them to be contourpy's;
  `scan.MESON_BUILDS` gains `contourpy-build`; `HOST_FACT_MEMBERS` gains contourpy's member and
  `host_fact_errors` applies bare `linux` to it; `paths.PACKAGES` and `LICENCE_COMPONENTS` gain
  contourpy and qhull; `MORE_LICENCE` gains qhull's `COPYING.txt` and a new `BORROWED_LICENCE`
  holds `LICENSE_YORICK` in `LICENSES/contourpy.txt` by name, read from matplotlib's pinned
  tarball; `DISTRIBUTIONS` gains contourpy; `tests/upstream/packages.toml` gains contourpy
  (spec 063, below); the unit tests that follow (below).
- **README** (matplotlib's facts: triangulations, contours, reproducible SVG and PDF, the PDF's
  tags, one thread, `fd_renumber`; the patch count 8; Scope) and **CHANGELOG** (one entry under
  0.1.0a7, naming patch 0002).

### Amendments made at build, each with its reason (for the review)

1. **contourpy's `_build_config.py` is copied from its build folder.** meson installs a
   `configure_file` with no install tag (EXECUTED: `intro-install_plan.json` gives it `tag:
   None`), and meson-python installs every tag, so Decision 4's `meson install --tags
   python-runtime` left it out (the first build stopped at step 55's own check). Step 55 now
   checks that meson's install plan names `build/contourpy-build/lib/contourpy/util/_build_config.py`
   and copies that file into the installed package. Installing without `--tags` would also
   install the extension, whose `runtime` tag runs `install_name_tool` on a macOS host (023's
   landing notes, item 5).
2. **The zip gains 19 members, not 18.** contourpy's installed tree is 18 files, not 17 (ten in
   `contourpy/` with `py.typed`, eight in `util/` with `_build_config.py`; EXECUTED, the zip's
   new names), plus METADATA. 64,998 bytes more (Decision 4: about 63 KB). Within a tenth.
3. **Step 55 is `55_matplotlib.sh`**, the name 023 landed (Design says `55_plot_packages.sh`).
4. **`LICENSES/` is not a folder in git:** the notices are assembled by `assemble_artifacts.py`
   into the set's `LICENSES/`, as 023's are. qhull's licence is `COPYING.txt`, which the judge's
   top-level search does not match, so `MORE_LICENCE` names it.
5. **Judge changes beyond Decision 9's list, each forced by an existing check:**
   `tests/unit/test_runner_mounts.py::test_every_descriptor_import_is_shadowed` counted 28
   descriptor imports; `fd_renumber` makes 29 (it is already shadowed and counted by the runner,
   spec 068), and the stale comment in `src/wasi_python/mounts.py` that said no binary imports it
   is corrected (comment only); `tests/unit/test_scan.py`'s compile-record test names the first
   record in sorted order, now `contourpy-build`; `tests/unit/test_artifact_rules.py`'s fixtures
   gain the contourpy and qhull pins and package lines; `tests/upstream/packages.toml` gains
   `[package.contourpy]`, `kind = "later"`, `closes_with = "spec 066"` (spec 063's rule:
   contourpy's sdist carries its tests; 066, reserved in the roadmap for the compiled packages'
   own tests, should name contourpy beside matplotlib, Pillow, kiwisolver, lxml and regex when it
   is drafted); `jobs.PLATFORM_BOUND` gains `plot_contour` (Decision 8's recording-platform rule).
   Three unit tests for the `dict(...)` parse are new (`tests/unit/test_build_scripts.py`).
6. **The PDF pin is an assertion of the job's check**, not a check of its own, as 023 pins the
   PNG's bytes in `test_plot_line_job_matches_native`: a second guest run of an 11 G job for one
   hash would double its cost.
7. **The job's details** (Decision 8 leaves them open): the contour lines use `SeparateCode`
   (EXECUTED: `mpl2014` refuses `Separate`), the level is 0.25 on `exp(-x²-y²) - 0.5·exp(-(x-1)²-(y-1)²)`
   over [-3, 3]², and the sums are `math.fsum`, so no summation order is printed. The figure's
   left axes hold `contourf` and `contour` (7 levels) and `clabel`, the right `tricontourf` and
   `triplot` on the triangulation. The SVG salt is `wasi-python`. Delaunay's triangles hash to
   `89432076058c35fd…` and its neighbours to `9339a93a6b6b6bff…`, as in the drafting run.
8. **The no-host-file check uses one instance across two calls** (`guest_turns`, spec 055), so
   the host lists the root and the font cache's grant after matplotlib's import and again after
   the triangulations; on the snapshot binary. The threads check runs on the snapshot only.
9. **On 023's set the job stops at its first line**, `import contourpy` (`ModuleNotFoundError`),
   not at `_qhull`'s `ImportError` (criterion 1's wording): Decision 8 prints contourpy's version
   first. `_qhull`'s `ImportError` on that set is seen by the no-host-file check instead.

### Acceptance criteria against evidence

1. **The checks exist and were seen failing first** (EXECUTED; logs under the worktree's `build/`):
   - On 023's set (main's `build/artifacts`, copied; this worktree's own rebuild of main is byte
     for byte the same, `SHA256SUMS` `c9dcb5b8…`): `test_plot_contour_job_matches_native[plain]`
     and `[snapshot]` exit 1, `ModuleNotFoundError: No module named 'contourpy'` (the PDF pin is in
     that check); `test_contourpy_runs_one_thread`, the same; the no-host-file check, `returned 1;
     ImportError: cannot import name '_qhull' from 'matplotlib'`; the host-fact check once its
     member was added, `contourpy/util/_build_config.pyc: not in the zip`; the C++ scan, `no meson
     setup of contourpy-build`; the three `dict(...)` unit tests before the parse (5 failed).
   - On a build without patch 0002 (steps 55, 60, 80): the job on both binaries, `RuntimeError:
     Could not open devnull`. The no-host-file check also failed there, `a writable grant
     changed: /: [('dev/null', 'file', 0)]`: released matplotlib's own `fopen` creates the file
     when the root holds a `dev` folder (and raises only when it does not).
   - On a build with the memo's fallback form (`fopen` first, the discard stream only if it
     fails): the job passes on both binaries; the no-host-file check fails with `dev/null` under
     the root, as the drafting run and the review found.
   - With contourpy's member taken out of `REWRITE` (step 70 alone): the host-fact check names
     `darwin`, `aarch64` and the checkout's path (3 findings). With `build_cpu_family` removed from
     a copy of the installed member, `make_stdlib_zip.py` stops: `contourpy/util/_build_config.py:
     no build_cpu_family to make host-neutral`.
   - The threads program with `serial` at `chunk_count=4` against `threaded`'s 16: `1 1 14 940
     False` (as written: `1 1 75 1001 True`).
   After each variant the set was rebuilt from step 55 and its `SHA256SUMS` equalled the first
   M2 build's.
2. **A full build from pins in a clean clone** (EXECUTED: `git clone` of the branch at `38a882b`
   into the scratchpad, the pins copied from `downloads/`, `scripts/build.sh --plain`, 16 steps in
   14 min 28 s on the shared machine): both matplotlib patches applied (the applier refuses an
   offset or a skip; `patch --dry-run` on the tarball, no offset), contourpy built, `_qhull` and
   `_contourpy` linked, and `SHA256SUMS` equal to the worktree's. `MANIFEST` names `package
   contourpy 1.4.0`, the contourpy pin, the stand-in's recipe line and patch 0002's.
3. **The same bytes.** arm64 Linux (EXECUTED: the `linux/arm64` research container `wp040-arm64`,
   Debian 13.7, a clone of the branch at `38a882b`, `scripts/00_download.sh` then
   `scripts/build.sh --plain`, 16 steps in 18 min 52 s): `SHA256SUMS` equal to macOS's, byte for
   byte. x86_64 Linux (EXECUTED: the `linux/amd64` research container `wp040-amd64` under Rosetta,
   the same clone and commands, 16 steps in 1 h 15 min, emulated on the shared machine; the CI
   rebuild runs natively, spec 059): `SHA256SUMS` equal too. No exception. Three hosts, one
   `SHA256SUMS`: `697d8e4693314000375320b140b6047b5dad0a28c40a6d86db597ee79ee908d5`.

   The three main artifacts: `python.wasm` 42,150,234 bytes,
   `ceb870a8208df486b3f39dbaa97b435f2c7c75d49b14f64b7791aff00aa97852`; `python-snapshot.wasm`
   45,687,008 bytes, `dd7f461745ee8a85f155521a6b5ef4075adfb9892589ff4b7b9f8a61e8e5457c`;
   `python-stdlib.zip` 22,262,171 bytes,
   `73062facba3f5e608e46cd62e3ed846b5045d8678a5a9e7ef587bba450e506e0`.
4. **The judge.** `uv run pytest -n 3` on this set, with the upstream kit fetched: 543/559 pass,
   13 gaps (all existing), 3 blocked (prior-art clones, three systems, wheel: this machine's
   usual), **0 fail**; the ratchet against `9a446e03f6`: lost 0, absent 0, unrun 0, gained 7 (the
   four new checks, contourpy's tree, and 023's two gap checks now passing), grew 148, judge
   changed. RED only for growth, which the lane accepts with `--accept-growth`. Not run with
   `--accept` (only the lane accepts). The record is `build/progress/latest.json` (a copy:
   `latest-043-full.json`).
5. **The numbers, against Decision 10** (EXECUTED; base = 023's set as rebuilt here):

   | number | 023's set | this set | change | Decision 10 |
   |---|---|---|---|---|
   | `python.wasm` bytes | 41,099,661 | 42,150,234 | +1,050,573 (+2.56%) | +0.8 to +1.0 MB: 5% over the top, within a tenth |
   | snapshot bytes | 44,633,983 | 45,687,008 | +1,053,025 (+2.36%) | the same: within a tenth |
   | zip bytes | 22,197,173 | 22,262,171 | +64,998 | about +63 KB |
   | zip members | 2,421 | 2,440 | +19 | +18 (amendment 2) |
   | plain `-c pass` fuel | 167,481,449 | 167,929,331 | +447,882 (+0.27%) | spec 035's per-member cost applies: 19 × about 24,000 ≈ +0.46 M; the 1.4 M estimate predates 035 |
   | snapshot `-c pass` fuel | 15,631,800 | 15,696,620 | +64,820 (+0.41%) | INFERRED +0.05% (from 023's members); the growth is the **binary's**, not the zip's (the build review's F1, EXECUTED: each snapshot gives the same fuel with either zip) |
   | `import matplotlib.pyplot`, plain / snapshot | 8,176,669,189 / 7,866,113,188 | 8,177,597,994 / 7,866,801,340 | +0.011% / +0.009% | no change (the zip's directory only) |
   | `plot_contour` job, plain / snapshot | — | 11,217,332,307 / 10,891,553,920 | new | about 11.2 G cold (the judge's root has no font cache) |
   | constructors | 9 reviewed | 9 reviewed, none new | — | none expected |
   | `target_features` | the line's 10 | the line's 10 | — | unchanged |
   | WASI imports | 43 | 44 | `fd_renumber` | one more; `wall_errors` empty |

   **Where the other growth comes from** (corrected after the build review's F1, whose 2 × 2 runs
   mixed the two binaries and the two zips with the judge's driver; their numbers, EXECUTED there):
   - **The plain start's +447,882 is the zip's 19 members** (MEASURED): the new zip adds +437,656
     on the base binary and +456,047 on the new one, about 23,000 to 24,000 a member, spec 035's
     plain-start read; the binary alone moves it by −8,165 or +10,226.
   - **The snapshot start's +64,820 is the binary's, not the zip's** (MEASURED): each snapshot
     binary gives the same fuel with either zip (15,631,800 and 15,696,620); the snapshot holds the
     zip's directory from snapshot time, and the run imports nothing. The same goes for the v1.2
     and v1.4 snapshot probes' +65,000 or so (+0.4 to +0.9%). My first notes gave this to the
     zip's members; that was wrong.
   - **numpy-core's +1,100,008,556 (+0.54%, the same 9,519 passes) is the binary's** (MEASURED):
     on the plain binary, the 19 members change the suite by −157 M (−0.08%) and the new binary
     alone adds +921 M (+0.45%). Run here on 023's set the suite gives 203,355,540,978, the
     accepted figure within 33,473, so the growth is this change's. My first notes suggested the
     suite re-read the zip's directory at each `importlib.invalidate_caches()`; an instrumented
     run counted no directory read and no `invalidate_caches()` call, so that never happens. The
     other upstream suites' growth (+0.0 to +0.2%) is, by the same reasoning, INFERRED to be the
     binary's too.
   - **What in the binary** (MEASURED, the review): static data ends 108,944 bytes later
     (23,433,948 → 23,542,892), so every heap address moves; the inittab's two more entries make
     `_imp.is_builtin` cost 411 more a call, which explains about 240,000 of numpy-core's growth,
     not 1.1 G, and nothing of `-c pass`. INFERRED, not measured: the moved heap changes
     pointer-derived hashing and allocation (the type method cache keys on name addresses;
     obmalloc's arenas sit differently), so the same Python work costs a little more or less
     (`import importlib.util` +1.5%, the plain start −8,165 on the binary alone). The review made
     two attempts to find one call site and stopped there (AGENTS.md, rule 7).
   - The zip-directory checks (+0.5 to +0.8%) read the zip's directory, which has 19 more
     entries (INFERRED: the zip's; not measured apart). Some lxml and pandas-tslibs checks fell by
     up to 0.29%, and the plot_line job grew 0.01% / 0.04% (the binary, INFERRED as above).

   **The reason for `--accept-growth`, as the lane may write it:** "spec 043, Decision 10: the
   binary +1.05 MB with contourpy, `_qhull` and qhull linked (code and data; static data ends
   108,944 bytes later, which moves every heap address and, INFERRED, the cost of pointer-keyed
   Python work: the snapshot start +64,820, the snapshot probes, numpy-core +0.45% and the other
   upstream suites, all with their passes unchanged); the zip's 19 more members (the plain start
   +447,882 and the zip-directory checks); the new job and checks are new passes." 
6. **Branch B only:** not applicable (branch A).
7. **A release dry run:** not run. Dispatching the release workflow needs the branch pushed,
   which only the lane does (AGENTS.md, rule 6b). The x86_64 rebuild's time (spec 040) is the
   dry run's to record.

### After the build review (`../reviews/043-matplotlib-second-milestone-build-2026-10-19.md`)

The review says 043 lands once F1 is fixed in these notes and in the `--accept-growth` reason.
Fixed on the branch, before the rebase:

- **F1 (the growth's causes).** Criterion 5's snapshot row and "Where the other growth comes
  from" now give the review's measured causes: the plain start's growth is the zip's 19 members;
  the snapshot start's, the snapshot probes' and numpy-core's are the binary's (static data ends
  108,944 bytes later; how that costs fuel is INFERRED, and the review stopped after two
  attempts); no zip-directory re-read happens. The `--accept-growth` reason above says the same.
- **F4.** `../roadmap.md`'s reserved line for spec 066 names contourpy.
- **F5.** Step 55 no longer copies `_build_config.py` to a fixed path: `scripts/meson_plan.py`
  copies each file meson installs with no tag to the destination meson's install plan gives it,
  and stops unless those destinations are exactly `contourpy/util/_build_config.py`. On this
  build's plan it places the same bytes (EXECUTED, `cmp`), and it stops when asked for another
  path. Two unit tests in `tests/unit/test_build_scripts.py` (a moved file, a file outside
  site-packages, the right one) failed first on import, then passed. A recipe file is new, so the
  set is rebuilt at the rebase.
- **F6.** `tests/unit/test_artifact_rules.py::test_contourpys_notice_holds_gists_and_qhulls_its_copying`,
  with a cut of GIST's notice as its fixture. Seen failing first (EXECUTED): with
  `BORROWED_LICENCE` emptied it fails (no `LICENSE_YORICK` error); with qhull's `MORE_LICENCE`
  row removed it fails (qhull judged for presence only). With both rules it passes.

At the rebase onto main, after 039 lands (the coordinator's order): F2 (the CHANGELOG entry
moves under 0.1.0a8), F3 (the README's size row, on the rebased set), the zero-patch count 22,
a rebuild from empty and the full judge.


### For the lane

**The plan (the lane, 2026-10-19).** 043 is a stacked build on spec 086 (wasi-sdk 34, clang 23),
which lands next as wave 04 (constitution §4.14), so its one rebuild is under the new toolchain.
This branch is first rebased onto main, then onto 086's rebased tip once the lane sends it, then
rebuilt from an empty `build/`. Its growth is measured against 086's set, not main's. The builder
of record changed: the first builder is gone, and a second agent (Claude Opus 5.5) carries the
branch from `737cef6`.

**The patch's name.** Unchanged: `recipes/patches/matplotlib-3.11.2/0002-qhull-without-devnull-on-wasi.patch`,
its draft `context/upstream/patches/matplotlib-3.11.2/0002-qhull-without-devnull-on-wasi.md`.
`recipes/patches/README.md` numbers patches per tree folder (`NNNN` "unique in the folder"), and
matplotlib's folder holds only `0001-ft2font-enums-without-python.patch`, so `0002` is the next
free number there. regex's `0002-timeout-ticks.patch` (spec 087) sits in regex's own folder and
does not clash. `MANIFEST` hashes every tracked recipe file (`scripts/assemble_artifacts.py`,
`recipe <sha256> <path>`), so the patch's line comes with the rebuild; no table names it by hand
(the Apache-2.0 `MODIFIED` table is regex's alone; matplotlib's licence is not Apache-2.0).

#### Rebased onto main (`f7511b7`, wave 03)

From `08de0c8` (the build review's base) onto `f7511b7`, 150 commits. The tip before the rebase is
kept as the local branch `backup/043-pre-rebase-737cef6`. Each conflict hunk, as resolved:

1. `tests/known_gaps.toml` (commit "the judge"): main's file, less 043's two closed M1 gaps
   (`test_delaunay_triangulation_runs`, `test_contour_runs`) and their comment. 073's removal of
   the run-keeps-bytes gap and 065's CPython entries are main's and stay.
2. `tests/checks/test_v1_3_data_stack.py`, `DISTRIBUTIONS` (twice): 039's tier A names and 043's
   `contourpy`, sorted; the trailing comment names both specs (shortened to fit 100 columns).
3. `tests/checks/test_v1_2_hostile_guest.py`, the file's end: both kept, 078's guest-thread checks
   first, then 043's triangulation check; the imports it needs (`tempfile`, `Path`, `paths`,
   `_version`) are main's.
4. `README.md`, the artifact table's zip row: 039's tier A sentence with 043's `contourpy`.
5. `README.md`, the facts table's patch row (087's `CARRIED_ROW` check reads it): main's 10 plus
   043's one, **11**, keeping 043's "matplotlib's enum fix" wording, since matplotlib now carries
   two.
6. `README.md`, *Since then* and *Out*: 043's second milestone after 023's first, then main's lxml,
   regex and tier A; *Out* drops 043's two matplotlib items and keeps main's seaborn, reportlab and
   pytz.
7. `context/upstream/README.md`, rows 5 to 7: main's rows 5 and 6 (041's patches carried) and
   043's row 7 (carried, its facts sheet moved).
8. `.github/workflows/release.yml`, the zero-patch step (twice): **23** trees, "twenty-three". The
   build review predicted 22 (19, plus 039's pyyaml and markupsafe, plus contourpy); main is
   already at 22 with 041's networkx sdist (`tests/harness/pins.py` lists 22 there), so contourpy
   makes 23.

Not conflicts, but moved by hand: the CHANGELOG entry, which git placed under `## 0.1.0a7 —
2026-10-19`, now ends `## 0.1.0a8 — unreleased` (the review's F2). Two README sentences main had
left stale now count 043's patch too: "with eleven carried patches" (main: ten) and *How it is
built*'s list, "eleven today" with all eleven named (main: "seven today", stale since 087 and
041).

Read and judged sound with no change: the auto-merged `scripts/make_stdlib_zip.py` (039's tier A
and 043's contourpy host keys), `scripts/steps/70_zip.sh` (043's tree and METADATA lines beside
039's and 041's), `scripts/steps/60_link.sh`, `scripts/gen_inittab.py`,
`scripts/assemble_artifacts.py`, and the harness files. No semantic change from the merge. On the
rebased tree, before any rebuild: `ruff check` and `ruff format --check` on `src/` and `tests/`
green; `uv run pytest tests/unit -n 3`, 1779 passed, 7 skipped; `tests/checks/test_rules.py -m
"not slow"`, 43 passed, 1 skipped (the patch rules and the README's count among them).

Still to do, at 086's tip: the README's size row on the rebuilt set (F3), the CHANGELOG's byte
figures, criterion 5's numbers against 086's set, the fast tier, the branch's release dry run, and
the claim list and flags.

#### Rebased onto spec 086 (`c4af3c4`, on main `f7511b7`)

`git rebase --onto c4af3c4 f7511b7`, the stacked build (§4.14). 086's tip is the lane's
wave 04 candidate: wasi-sdk 34, the fcntl dup refusal, SipHash-1-3 and `_missing_stdlib_info.py`
in the zip. Two conflict hunks, each resolved by keeping both sides:

1. `tests/checks/test_v1_2_hostile_guest.py`, the file's end (commit "the judge"): 086's
   `DUP_PROBE`, `test_dup_is_refused_as_not_supported`, `HASH_PROBE` and
   `test_the_string_hash_is_siphash13` first, then 043's triangulation check. Nothing removed.
2. `scripts/steps/70_zip.sh`, the inputs' guard (commit "the recipe"): 086's `MISSING_INFO` lines,
   then the plot packages' loop with 043's `contourpy`.

Auto-merged and read: `scripts/steps/60_link.sh` (086's guard loop and `--wrap=fcntl` in the
reactor's link; 043's contourpy archives and `_qhull` in the module loop; separate hunks), the
README (086's sizes row restated on its set; 043's rows as rebased onto main, the patch count still
11: 086 adds a recipe file, `recipes/fcntl_dup_refusal.c`, not a patch), the CHANGELOG (043's
entry still ends 0.1.0a8), `tests/known_gaps.toml` (086's removed gap and 043's two removed gaps),
the release workflow (086 does not touch it; trees still 23). The cross file 043's contourpy uses,
`recipes/wasi-matplotlib.cross`, is not one 086 changes.

One interaction to measure at the rebuild, not a conflict. 086's SipHash-1-3 changes how `str`
and `bytes` hash. 043's PDF pin (`PDF_SHA256`) holds the guest's subset tags, which matplotlib
derives from `hash()`. INFERRED: matplotlib's backend_pdf hashes a frozenset of the subset's
character codes, which are ints, and an int's hash takes no key, so the pin should stand. The
rebuilt set's plot_contour check confirms it or names the change.

On the rebased tree, before any rebuild: `ruff check` and `ruff format --check` on `src/` and
`tests/` green; `uv run pytest tests/unit tests/checks/test_rules.py -m "not slow" -n 3`, 1822
passed, 8 skipped.

#### Rebuilt on 086's set (2026-10-20), on main `ebd0449` (wave 04 landed)

After wave 04 landed, the branch was rebased with `git rebase --onto origin/main c4af3c4`, with no
conflict: main past 086's tip is `context/` and progress files only. Built from an empty `build/`
in the worktree, on darwin-arm64: `scripts/00_download.sh` then `scripts/build.sh --plain`, 16
steps in 8 min 27 s. The old `build/`'s logs were saved first, to the session scratchpad
(`043/old-build-evidence/`).

- **The set.** `SHA256SUMS` `4c7099a4ee5d96b454b56ac296969b77662bd247e9b73c84987482307e1f2a57`.
  The branch dry run's build job, its arm64 Linux and its x86_64 Linux rebuilds give the same file
  line for line (EXECUTED: the same-bytes job passed; its printed lines `diff` equal to the local
  file). `python.wasm` 42,251,129 bytes (`1b60cc5e…`), `python-snapshot.wasm` 46,533,054
  (`d2dc6000…`), `python-stdlib.zip` 38,788,145 (`2fc59a16…`), with 4,454 members.
- **Against 086's accepted set** (`a75e5d4`, `4e0dc0cf`; its record is main's
  `context/progress/accepted.json`):

  | number | 086's set | this set | change |
  |---|---|---|---|
  | `python.wasm` bytes | 41,169,347 | 42,251,129 | +1,081,782 (+2.63%) |
  | snapshot bytes | 45,444,036 | 46,533,054 | +1,089,018 (+2.40%) |
  | zip bytes | 38,723,140 | 38,788,145 | +65,005 (+0.17%) |
  | zip members | 4,435 | 4,454 | +19 |
  | plain `-c pass` fuel (`test_guest_runs_here[plain]`) | 221,669,921 | 222,096,155 | +426,234 (+0.19%) |
  | snapshot `-c pass` fuel (`[snapshot]`) | 48,820,209 | 48,942,227 | +122,018 (+0.25%) |
  | plain start per member (`test_a_plain_start_grows_at_most_30k_fuel_per_member`) | 221,676,034 | 222,177,596 | +501,562, about 26,400 a member, under the check's 30,000 |
  | `plot_contour` job, plain / snapshot (the dry run's macOS shard) | — | 11,323,411,159 / 10,996,023,540 | new |
  | `plot_line` job, plain / snapshot | 9,192,360,472 / 8,866,215,418 | 9,195,549,688 / 8,865,969,924 | +0.035% / −0.003% |

  The binary's growth is the old base's within 3% (+1,050,573 then). The plain start's growth is
  the zip's 19 members, as the build review measured on the old base. The snapshot start's growth
  is the binary's by that review's 2 × 2; it is larger here (+122,018 against +64,820), which is
  INFERRED to be the same static-data move under the new toolchain, not measured apart.
- **The PDF pin under SipHash-1-3** (EXECUTED, by node id while the lane held its lock):
  `test_plot_contour_job_matches_native[plain]` and `[snapshot]` pass with `PDF_SHA256`
  unchanged. matplotlib's subset tags hash a frozenset of ints, which takes no string key. 043's
  other new checks and its two closed gaps pass on this set too (4 passed by node id).
- **The fast tier** (`uv run pytest -m "not slow" -n 3`, after the lane's lock cleared): 585/713
  pass, 0 gap, 3 blocked (this machine's usual three), **0 fail**, 125 deselected; unit suite
  1786/1793, 7 skipped. Ratchet against `a75e5d4`: lost 0, absent 0, unrun 0, unrun locally 1
  (the prior-art clone), gained 1 (`test_source_tree_matches_its_tarball[contourpy]`), grew 123.
  Fuel against 086's record: 159 rows move, 130 up and 29 down, median +0.096%, −0.101% to
  +0.452%.
- **The branch dry run** `39369636353` on `c448232` (the tip before these notes; only `context/`
  changes after it): every job passed but three macOS judge shards, each red **only for growth**,
  with 0 fail and lost 0. `own-guest`: grew 110, gained 7. `own-embedding`: grew 28.
  `upstream-macos`: grew 2 (`cpython-fs` 62,759,159,502 → 62,795,480,409, +0.058%; `numpy-lib`
  132,356,352,156 → 132,421,229,061, +0.049%). The gather was skipped because those shards
  failed. Windows (own-guest, own-embedding, own-runner, upstream-windows) passed with 0 fail, as
  did every Linux shard, the same-bytes job and verify on all three systems. The macOS shards'
  records against 086's: 186 fuel rows move, 151 up and 35 down, median +0.075%, −0.101% to
  +0.452%. The rows above +0.3% read the zip's directory (`test_resources_read_as_zipfile_reads_them`,
  `test_the_fast_reader_builds_zipimports_dict`) or look up many builtins
  (`test_dotted_builtins_keep_their_import_names`; the inittab has two more entries).
- **Not run here:** the full judge (`uv run pytest -n 6`). The coordinator asked for the fast tier
  and the dry run. The darwin fuel of the upstream groups that run only on Linux in the release
  (numpy-core, pandas, cpython-a to c) is therefore not yet compared with 086's; the lane's
  serial judge on the exact commit gives it.

#### The claim list (wave 06, stacked with 037)

- **New checks (5):** `tests/checks/test_v1_3_matplotlib.py::test_plot_contour_job_matches_native[plain]`
  and `[snapshot]` (fuel recorded), `::test_contourpy_runs_one_thread` (fuel recorded),
  `tests/checks/test_v1_2_hostile_guest.py::test_a_triangulation_leaves_every_writable_grant_as_it_was`,
  `tests/checks/test_v1_5_rebuild_from_pins.py::test_source_tree_matches_its_tarball[contourpy]`.
- **Gaps that now pass (2):** `tests/checks/test_v1_3_matplotlib.py::test_delaunay_triangulation_runs`
  and `::test_contour_runs`, their entries removed from `tests/known_gaps.toml`.
- **The unit suite:** six new test functions, eight new test items (`tests/unit/test_build_scripts.py`:
  the meson plan, two, and contourpy's build-config rewrite, three, one of them over three keys;
  `tests/unit/test_artifact_rules.py`: contourpy's notices and the borrowed licence rule, one), and
  one renamed, `test_host_facts_in_the_three_members_are_named` (was "two members", now with
  contourpy's member); `test_runner_mounts.py` and `test_scan.py` changed for contourpy (the delta
  review, 2026-10-20).
- **Retired:** none. **Passes moved:** none; no group's passes fall.
- **Rows that grow:** the three byte rows, and fuel rows across the board as above (the binary's
  static-data move, the zip's 19 members, the two inittab entries).
- **The judge changed in:** `tests/checks/test_v1_2_hostile_guest.py`, `test_v1_3_data_stack.py`,
  `test_v1_3_matplotlib.py`; `tests/harness/artifacts.py`, `jobs.py`, `needs.py`, `paths.py`,
  `pins.py`, `scan.py`; `tests/jobs/plot_contour.py`, `.expected`, `.platform`;
  `tests/known_gaps.toml`; `tests/upstream/packages.toml`; the four unit files.

#### The exact flags

```
--accept "043: matplotlib's second milestone: contourpy 1.4.0 built in as contourpy._contourpy with its package in the zip, matplotlib's _qhull linked with qhull 8.0.2 and carried patch recipes/patches/matplotlib-3.11.2/0002-qhull-without-devnull-on-wasi.patch (eleven carried patches), a meson-python stand-in recipe, contourpy's _build_config.py made host-neutral; the release's zero-patch count 23 trees; built stacked on 086 (wasi-sdk 34), SHA256SUMS 4c7099a4 from macOS, linux/arm64 and linux/x86_64 at 6e127e8; rebased onto 41bcc0f (090, 082) and rebuilt by the lane as SHA256SUMS <the lane's>, equal to 4c7099a4 in every file but MANIFEST (090's recipe lines)"
--accept-judge "043: five new checks (the plot_contour golden on both binaries with the guest's PDF pinned, contourpy's one thread, a triangulation leaves every writable grant as it was, contourpy's source tree) and two gaps closed (test_delaunay_triangulation_runs, test_contour_runs, removed from known_gaps); contourpy in the harness's host facts, licence, tree and distribution lists; six new unit test functions and one renamed (the meson plan, contourpy's build-config rewrite, contourpy's notices and the borrowed licence rule; the host-fact test over three members); packages.toml names contourpy's suite as later (spec 066)"
--accept-growth "043, against 086's accepted set (a75e5d4): python.wasm +1,081,782 bytes (41,169,347 to 42,251,129) and the snapshot +1,089,018 (45,444,036 to 46,533,054), with contourpy, _qhull and qhull linked; the zip +65,005 bytes (38,723,140 to 38,788,145) and 19 members (4,435 to 4,454). Fuel, the branch dry run 39369636353's macOS shards: 186 rows move, 151 up and 35 down, median +0.075%, -0.101% to +0.452%, passes unchanged. The plain start +426,234 (+0.19%) is the zip's 19 members, about 26,400 each; the snapshot start +122,018 (+0.25%) and the snapshot probes are the binary's (its static data ends later, so every heap address moves; the build review's 2 x 2 on the old base); the zip-directory and builtin-lookup checks +0.30% to +0.45% (19 more zip entries, two more inittab entries); cpython-fs +0.058%, numpy-lib +0.049%; the upstream groups the release judges only on Linux, first compared on darwin by the lane's judge (numpy-core, pandas, cpython-a to c), the binary's, as numpy-core's +0.45% on the old base, with their passes unchanged"
```

No `--retire`, no `--accept-fewer-passes`, no `--partial`.

The delta review (2026-10-20, of `08de0c8..737cef6` against `41bcc0f..047508c`) wrote in three
things above, `context/` only: the unit-suite count (six new functions and one renamed, not seven
new); in `--accept`, the lane's own `SHA256SUMS` from its rebuild at the landed commit, which
differs from `4c7099a4` in `MANIFEST` alone; and in `--accept-growth`, the upstream groups that
only the lane's darwin judge compares with 086's record. If the lane's judge shows any of those
groups growing by more than 1%, or any pass moving, the landing stops for a stated reason.

#### Rebased onto 41bcc0f (wave 05: 090 and 082)

`git rebase --onto 41bcc0f ebd0449`, from `6e127e8`. One conflict hunk:

1. `scripts/make_stdlib_zip.py`, `SKIP_NAMES` and `REWRITE` (commit "the recipe"): 090's
   `SKIP_NAMES` (litter now goes by `is_litter`, so `*OS_LITTER` is gone from the set, and
   `OS_LITTER` is no longer imported) with 043's `REWRITE`, which adds
   `contourpy/util/_build_config.py`.

Read with no change: 090's `scripts/assemble_artifacts.py` (`drop_litter` and `listed_files` by
`is_litter`; 043's notice and `MODIFIED` hunks sit apart), `scripts/litter.py`,
`scripts/steps/20_cpython.sh`, and the harness and unit files 090 and 082 touch. Nothing in 043
still uses the old `OS_LITTER` import. 043's `scripts/meson_plan.py` copies only the files meson's
install plan names, and stops unless they are exactly `contourpy/util/_build_config.py`, so no
litter can pass through it.

Not rebuilt, as the lane asked: 090 changes no artifact byte but `MANIFEST`'s recipe lines, so the
set the lane rebuilds differs from `4c7099a4` in `MANIFEST` and `SHA256SUMS` alone. On the rebased
tree: `ruff check` and `ruff format --check` on `src/` and `tests/` green; `uv run pytest tests/unit
tests/checks/test_rules.py -m "not slow" -n 3` (the lane's lock absent), 1831 passed, 8 skipped.
