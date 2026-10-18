# 043 — matplotlib, the second milestone: triangles, contours, SVG and PDF

- **Status:** drafted 2026-10-17; not yet reviewed. It changes the build recipe and the artifact
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
  57, a second carried patch (to qhull) and scipy's rename table (Decision 6).
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
     step 70's rules: 17 members, 61,732 bytes deflated in the research zip (EXECUTED by the memo;
     the count, by 023's review). The two `bokeh_*` modules go in too: they import `bokeh`, which
     the profile does not carry, so they fail at import as they would natively without it, and
     leaving them out would save two members only. contourpy's `METADATA` goes in as 033 and 023
     put matplotlib's (from `PKG-INFO`).
   - **`_build_config.py` is made host-neutral** (spec 012, Decision 5). It records the builder's
     paths (`build_dir`, `source_dir`, `python_path`, `compile_command`, the cross file in
     `build_options`) and the build host (`build_cpu`, `build_cpu_family`,
     `build_cpu_system`: EXECUTED, the memo's file says `aarch64` and `darwin`).
     `make_stdlib_zip.py`'s `REWRITE` gains `contourpy/util/_build_config.py`. Its three host
     keys are set to `build`, as numpy's are (`CONTOURPY_BUILD_KEYS`); `build_cpu_endian` stays
     `little`. Step 70's existing `--replace` rules turn every path into `/wasi-python-build/…`.
     A key absent stops the build, as for numpy; a host word left fails the judge's host-fact
     check (Decision 9).

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

6. **One qhull, in either order with spec 037.** 037 links scipy's vendored qhull, and its
   Decision 8 says the second of the two to land makes them share one.
   - **The end state, whichever lands first.** One qhull: step 37's, from the pinned qhull 8.0.2
     tarball, which both matplotlib (`-Dsystem-qhull=true`) and scipy
     (`-Duse-system-libraries=qhull`) link. It carries scipy's one change to qhull as a recorded
     patch, `recipes/patches/qhull-8.0.2/0001-format-strings.patch` (037's name). EXECUTED while
     drafting: scipy 1.18.1's vendored `libqhull_r` is qhull 8.0.2's, file for file, except one
     hunk of `poly2_r.c`: a `trace1` call missing its three arguments, upstream qhull's pull
     request 143 (merged 2025-08-07 as `1b67ec90`; no qhull release since, only `v8.1-alpha1` of
     2021; EXECUTED, GitHub's API). The hunk, made against the qhull tarball, applies with no
     offset. So scipy links the same source it would have linked.
   - **Init names, in either order.** scipy's `scipy.spatial._qhull` (Cython) and matplotlib's
     `_qhull` both define `PyInit__qhull` (READ: `scipy/spatial/meson.build:13`, matplotlib's
     `src/meson.build`). 037's comparison was with M1's list, which had no `_qhull`. scipy's is
     renamed, to `PyInit_scipy_spatial__qhull`, in 037's `scipy_rename.h` and `gen_inittab.py`'s
     rename table, because 037 already has both mechanisms and matplotlib has neither.
     matplotlib keeps upstream's name.
   - **A: this lands before 037 (the plan, Decision 13).** This specification links step 37's
     qhull as it is; matplotlib never traces, so the format-string hunk is unreachable for it.
     It adds no qhull patch. 037 then takes its own "if M2 lands first" branch, and also: step
     37 writes a `qhull_r.pc` (`Version: 8.0.2`), because scipy asks
     `dependency('qhull_r', version : '8.0.2')` (READ: `meson.build:272-281`), which 023's
     recipe-built qhull does not answer; and the rename above. 037's text does not yet say
     either; its builder takes both from here.
   - **B: 037 has landed first.** This specification does what A leaves to 037: the qhull patch
     and its draft (`Status: merged https://github.com/qhull/qhull/pull/143`; `Files:
     src/libqhull_r/poly2_r.c`), step 37's `qhull_r.pc` (from a recipe file,
     `recipes/qhull_r.pc.in`), step 57's `-Duse-system-libraries=qhull` with step 37's
     `pkgconfig` folder on its `PKG_CONFIG_LIBDIR`, and the rename. 037's checks must then
     pass unchanged: its spatial goldens and its `QhullError` check run on the shared qhull.

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
   - `savefig` to PDF with `metadata={"CreationDate": None}`: size, and the full SHA-256 of the
     file with each font subset tag (`/` then six capitals then `+`) replaced by `/XXXXXX+`;
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
   `pdf.compression` 0. The guest's own bytes are deterministic (hash seeds do not touch int
   hashes; equal on the plain reactor and the snapshot), so a check pins them too (Decision 9).

   **The drafting run.** Every line above but the PDF's raw hash was equal, guest and native, on
   two scratch binaries and at two hash seeds natively: Delaunay `(48, 3)` `8131bfe18b9fc320…`
   (sorted) and `89432076058c35fd…` / `9339a93a6b6b6bff…` (unsorted, neighbours), the three
   algorithms' sums, the levels, the SVG (58,400 bytes,
   `1513d0794da9b7547652301f648f4b5a2b3b75035b407f8c21f1d835c4b6d613`), the normalized PDF
   (15,856 bytes, `87d654b405dfbd42…`) and the RGBA buffer (`c7c9f6d76874a4d2…`). The guest's
   raw PDF was `96eb6c55ce5b19ad3dd71aefb8db92cd361008c08d06ec36a26fe124cd32d7b2` on both.
   The line's pinned host Python 3.15.0, which the oracle runs, has zlib 1.2.12, as the drafting
   run's had (EXECUTED); the guest's is 1.3.1, and the compressed streams were equal. **If the oracle's compressed
   streams ever differ** (a zlib difference, as 023 found for PNG), the job sets
   `pdf.compression` to 0 and the landing notes say why; that is a change to the job before it
   is accepted, not a weakening after.

   The PostScript, EPS and PGF backends stay unjudged (Scope).

9. **The checks**, each seen failing first (Acceptance criterion 1 says how):
   - **v1.3, the milestone:** the `plot_contour` job against its golden (Decision 8), on both
     binaries.
   - **v1.3:** the guest's raw PDF bytes from the job equal a pinned SHA-256, the same on both
     binaries (as 023 pins the PNG's bytes). The value is the build's; the drafting run's is in
     Decision 8.
   - **v1.3:** `contourpy.max_threads()` is 1, and `threaded` with `thread_count=4` reports one
     thread and gives the `serial` algorithm's lines on Decision 7's grid.
   - **v1.2, no host file:** in a call whose writable root holds a `dev` folder, a Delaunay
     triangulation and a qhull error leave that folder as it was. It fails on the memo's patch
     form (EXECUTED while drafting) as well as on M1's set.
   - **v1.5:** `test_stdlib_zip_names_no_build_host` covers contourpy's member:
     `HOST_FACT_MEMBERS` gains `contourpy/util/_build_config.pyc`, judged with numpy's word list
     (bare `linux` included).
   - **The known gaps.** 023's two entries (`_qhull`'s `ImportError`, contourpy's
     `ModuleNotFoundError`) are removed: their checks pass, and a gap whose check passes fails
     the run until removed.
   - **Judge changes**, under `--accept-judge`: the two gaps; `SOURCE_PATTERNS` and
     `needs.SOURCE_COMPONENTS` gain contourpy (one tree more; the release workflow's count rises
     by one); `scan.cpp_exception_errors` judges contourpy's flags; `HOST_FACT_MEMBERS`; the
     jobs list and its recording platform; the judge's package and licence lists. In branch B,
     the qhull patch's tree is qhull's, already judged.
   - **Unchanged, and still run:** 023's constructor check, `target_features` check, import
     wall, and every v1.2 and v1.4 probe that does not import matplotlib.

10. **What it costs, stated so growth can be told from regression.** Each number is measured by
    the build and recorded in the landing notes; one outside its range by more than a tenth is a
    finding for the build review, not a reason to accept.
    - **`python.wasm`:** about +0.7 MB (about +2%). The link map's function sizes: contourpy
      388,785 bytes, qhull 302,293, `_qhull` 13,923 (EXECUTED by the memo's map, summed while
      drafting). libc++'s streams are already in M1 (Decision 5). The memo's full build, M1 and
      M2 together, was 38,008,426 bytes stripped.
    - **The snapshot:** about the same +0.7 MB; matplotlib is not pre-imported (question 34).
    - **The zip:** +17 members, about +62 KB (Decision 4).
    - **Plain `-c pass`:** +17 members at 023's review's 76,490 instructions each, about +1.3 M
      fuel (+0.5%; INFERRED). If spec 035 has landed, its own per-member cost applies instead.
      Snapshot `-c pass`: about +0.05% (INFERRED from 023's review: +2.0% for 681 members).
    - **`import matplotlib.pyplot`:** no change. contourpy and `_qhull` load only when a contour
      or a triangulation is made (READ by 023's review).
    - **The new job:** about 9.2 G fuel on a plain reactor with a warm font cache (EXECUTED on
      the scratch build; the judge's run records its own). It is a new pass, accepted with
      `--accept`; the growth to accept is the existing checks' (above).

11. **Licences** (§4.12). `LICENSES/` gains contourpy's `LICENSE` (BSD-3-Clause; question 81)
    and, now that qhull is linked, qhull's `COPYING.txt` (the Qhull licence, approved by the
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
      makes the qhull, `qhull_r.pc` and rename changes of Decision 6.
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
| `scripts/steps/70_zip.sh`, `scripts/make_stdlib_zip.py` | contourpy's tree; `REWRITE` and `CONTOURPY_BUILD_KEYS` (Decision 4) |
| `scripts/assemble_artifacts.py`, `LICENSES/` | contourpy and qhull (Decision 11) |
| `tests/jobs/plot_contour.py`, `plot_contour.expected`; `JOBS` in `tests/harness/jobs.py` | the golden (Decision 8) |
| 023's matplotlib check file under `tests/checks/`, `tests/checks/test_v1_2_hostile_guest.py` | Decision 9's v1.3 and v1.2 checks |
| `tests/harness/artifacts.py`, `pins.py`, `needs.py`, `scan.py`, `tests/known_gaps.toml` | the judge changes (Decision 9) |
| `.github/workflows/release.yml` | the tree count, one more |
| `README.md`, `CHANGELOG.md` | Decision 12 |
| **Branch B only:** `recipes/patches/qhull-8.0.2/0001-format-strings.patch`, `context/upstream/patches/qhull-8.0.2/0001-format-strings.md`, `recipes/qhull_r.pc.in`, `scripts/steps/37_plot_libs.sh`, `scripts/steps/57_scipy.sh`, `recipes/scipy_rename.h`, `gen_inittab.py`'s rename table | one qhull (Decision 6) |

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
     `dev/null` (the drafting run did; the builder repeats it once);
   - with the `_build_config.py` rewrite turned off: the host-fact check names `darwin` or
     `aarch64`.
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
6. **Branch B only:** 037's scipy goldens and its `QhullError` check pass unchanged on the shared
   qhull, and `nm` finds one copy of qhull's functions in `python.wasm`.
7. **A release dry run** passes every job.

## The owner's choices

None open here. One approval this specification needs is recorded as **81** in
`../questions-for-the-owner.md`: contourpy's licence (BSD-3-Clause) is not yet named in §4.12,
so it is built only after the answer (the agent recommends approving it, as kiwisolver's was).
The upstream draft follows question 80's recommendation (a facts sheet, since matplotlib refuses
AI-made pull requests); if the owner answers 80 otherwise, the sheet is rewritten before the
build moves it.

## Landing notes

Not built.
