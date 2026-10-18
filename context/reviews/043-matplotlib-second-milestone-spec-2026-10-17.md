# Review of 043 — matplotlib, the second milestone (the specification, before build)

- **Date:** 2026-10-17 (the runs finished after midnight, 2026-10-18)
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the
  constitution (§4.1, §4.4, §4.9, §4.10, §4.12, §4.15, §5.2, §5.6, §5.7, §6, §7), the
  specification, its upstream folder in full (`../upstream/7-matplotlib-qhull-devnull/`:
  `notes.md`, `pr.md`, `fix.patch`, `evidence/`), questions 80 and 81, spec 023 (Decisions 1
  and 4), spec 037 (status; Decision 6's rename header and per-file includes; Decision 8's init
  names, constructors and "One qhull"; the cross file, `pkgconf` and configure bullets; Design;
  ordering), and the research memo's tables. Code read: `scripts/make_stdlib_zip.py`
  (`REWRITE`, `NUMPY_BUILD_KEYS`, `_host_items`, `host_neutral`, the `--replace` check),
  `scripts/steps/70_zip.sh`, `scripts/gen_inittab.py`, `scripts/python-wasi-cross`,
  `recipes/reactor_main.c` (`init_interpreter`), `tests/harness/artifacts.py`
  (`HOST_FACT_MEMBERS`, `host_fact_errors`), `tests/unit/test_artifact_rules.py`,
  `tests/harness/wasm.py` (`wall_errors`), `tests/harness/guest.py` (`random_get`),
  `tests/harness/scan.py` (`DRAFT_FIELDS`, `STATUS`, `_draft_errors`). Upstream sources read
  from the research's downloads (hashes below): matplotlib 3.11.2 (`src/_qhull_wrapper.cpp`,
  `src/meson.build`, `extern/meson.build`, `lib/matplotlib/backends/backend_pdf.py`,
  `_backend_pdf_ps.py`, `doc/devel/contribute.rst`, `LICENSE/`), contourpy 1.4.0 (`meson.build`,
  `src/meson.build`, `lib/contourpy/util/meson.build`, `src/util.cpp`, `src/threaded.cpp`,
  `src/mpl2005_original.cpp`, `pyproject.toml`, `LICENSE`), qhull 8.0.2 (`libqhull_r/`,
  `user_r.h`), scipy 1.18.1 (037's scratch tree: `meson.build:272-281`,
  `subprojects/qhull_r/`, `scipy/spatial/meson.build`, `qhull_misc.[ch]`), and wasi-sdk 33's
  sysroot (`stdio.h`, `libc.a`). matplotlib `main` (`493abb1b63`) read with `gh api`:
  `doc/devel/contribute.rst`, `.github/PULL_REQUEST_TEMPLATE.md`, `AGENTS.md` (absent). Each
  claim below is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/043-matplotlib-second-milestone.md` as drafted
  (committed in `92df832`), and the draft it moves.
- **Ran (EXECUTED, darwin-arm64).** Nothing in `src/`, `tests/`, `scripts/`, `recipes/`,
  `downloads/`, the specification or the upstream folder was edited; `scripts/build.sh` and the
  judge were not run. The harness was imported read-only under `uv run`. Everything is under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/043-review/`:
  - `set/`: a copy of `build/sets/s-8d84b3b190fe9bce`; `imports.py` counts its imports.
  - `src/`: fresh extractions of the research's downloads, hashed: contourpy 1.4.0
    `20156f5a…d500e1` (equal to the spec's pin), matplotlib 3.11.2 `cec59631…9ea4`, qhull
    8.0.2 `8774e9a1…4f8b`. matplotlib had the memo's patch 0001 and then `fix.patch` applied
    (`patch -p1`, no offset, no fuzz); qhull had the drafting's format-string hunk dry-run.
  - `obj-fix.o`: `src/_qhull_wrapper.cpp` from that tree, compiled with the research's own
    compile command (from `b-mplp/compile_commands.json`); `d1.txt`, `d2.txt` its disassembly
    against the drafting's relinked object.
  - `nat-{0,1,12345,random}/`, `nat-*.txt`: the drafting's `plot_contour.py` natively, on the
    line's CPython 3.15.0 with the PyPI wheels (042's scratch venv: matplotlib 3.11.2,
    contourpy 1.4.0, numpy 2.5.2), `MPL_IGNORE_SYSTEM_FONTS=1`, at `PYTHONHASHSEED` 0, 1, 12345
    and random; `norm.py` normalizes the PDFs' tags.
  - `drive_seed.py`, `guest-seed-*.txt`, `guest-rand-*.txt`: the same program in the guest (the
    drafting's relinked `python-m2.wasm`, plain reactor) through `tests/harness/guest.py`, once
    with the judge's seeded `random_get` (twice) and twice with `random_get` replaced by
    `os.urandom`, so the guest's string-hash secret differed; it prints the full SHA-256 of the
    SVG and PDF.
  - `devnull_probe.py`: the drafting's probe plus 300 failing triangulations, on
    `python-m2.wasm` (this spec's patch) and on the memo's `python-mplp.wasm` (fallback form),
    with a writable root holding `dev/keep`.
  - `prog_threads.py` with the drafting's `threads.py`, in the guest and natively.
  - `mapsum.py` → `mapsum.txt`: the drafting relink's map, summed by output section for each
    input; object `DATA` sections summed with `llvm-objdump -h`.

## What holds

- **fopencookie is in the SDK, and the patch compiles to what was linked.** EXECUTED:
  `wasm32-wasip1/stdio.h:226-233` declares `cookie_io_functions_t` and `fopencookie` under
  `_GNU_SOURCE`; `clang++ --target=wasm32-wasip1 -dM -E` defines `_GNU_SOURCE 1`;
  `libc.a(fopencookie.c.obj)` defines `T fopencookie`. `fix.patch` is 1,138 bytes,
  `8ea3cd41…7da20`, 12 lines added and none removed, as Decision 3 says; it applies after the
  memo's 0001 with no offset (the two touch different files). My compile of the patched file
  imports `fopencookie` and not `fopen`. Its disassembly equals the drafting's relinked
  `_qhull_wrapper.cpp.o` (`01f8515f…`) once numbers are masked (0 differing lines of 61,437); the
  raw bytes differ only in string offsets, because the two compiles named pybind11's include
  folder differently (`share/pkgconfig/../..//include` against `include`), which `__FILE__`
  strings carry. (`obj/ours.o` in the drafting folder is the memo's form, equal to
  `research.o`, `264819ce…`, and still imports `fopen`; the evidence's claim is about
  `_qhull_wrapper.cpp.o`, which is what `relink/_qhull.a` holds.)
- **No file opens on the host, and qhull's error path still raises.** EXECUTED
  (`devnull_probe.py`): with this spec's patch, collinear points raise `Error in qhull Delaunay
  triangulation calculation: singular …`, four points give `(2, 3)`, 300 more failing
  triangulations raise each time, and `dev/` stays `['keep']`; no host file named `null`. With
  the memo's form, the same run makes `run-0/root/dev/null` (0 bytes). READ: the stream is
  closed by `QhullInfo`'s destructor (`error_file != stderr`), also on the throw, so no `FILE`
  leaks; musl's `fopencookie` allows a null close function. The verbose path (`stderr`) cannot
  be reached in the guest: `init_interpreter` uses `PyConfig_InitIsolatedConfig` with
  `parse_argv = 0` (READ), so `sys.flags.verbose` is 0.
- **One more import, `fd_renumber`, and nothing else.** EXECUTED: today's set imports 43
  functions and the drafting relink 44, the extra one `wasi_snapshot_preview1::fd_renumber`;
  `wall_errors` is empty for both. The memo's other links with qhull (`python-mpl`,
  `python-notri`, `python-mplp`) import it too; its link map pulls
  `libc.a(__wasilibc_fd_renumber.c.obj)`. READ: matplotlib's command is the fixed `"qhull d Qt
  Qbb Qc Qz"`, so qhull's `TI`/`TO` `freopen` cannot be reached from matplotlib.
- **One qhull is the same source scipy links, but for one hunk.** EXECUTED: `diff -r` of scipy
  1.18.1's `subprojects/qhull_r/libqhull_r` against qhull 8.0.2's `src/libqhull_r` finds only
  `poly2_r.c:2283` (the `trace1` arguments) and files scipy does not vendor; the hunk dry-runs
  on the qhull tree with no offset. scipy compiles the same 17 `libqhull_r` sources the memo's
  step 37 compiled (`b-qhull/*.o`, 17 objects; READ `subprojects/qhull_r/meson.build`). READ:
  `meson.build:272-281` asks `dependency('qhull_r', version : '8.0.2')` under
  `use-system-libraries=qhull`, which only a `qhull_r.pc` answers once `cmake` is disabled;
  matplotlib's `extern/meson.build:72-77` falls back to `find_library('qhull_r')`, which is why
  023's step 37 needs none. READ: matplotlib's `PYBIND11_MODULE(_qhull, …)`
  (`_qhull_wrapper.cpp:299`) and scipy's Cython `extension_module('_qhull', …)` both define
  `PyInit__qhull`. scipy's `qhull_misc.c` defines only `qh_new_qhull_scipy`, so no user hook of
  qhull (`qh_fprintf` and the like) is overridden for matplotlib.
- **The PDF tags are the only difference, and every PDF and SVG byte is deterministic.**
  EXECUTED: natively at hash seeds 0, 1, 12345 and random, every line is equal, SVG
  `1513d079…d613` (58,400 bytes), PDF `a3270ab3…` (15,856 bytes), normalized `87d654b4…`, six
  tags each time. In the guest, with the judge's seeded secret and with two `os.urandom`
  secrets (`hash("wasi-python")` was -1273124320, -2050025054 and -220627816), every line is
  equal: SVG `1513d079…d613`, raw PDF
  `96eb6c55ce5b19ad3dd71aefb8db92cd361008c08d06ec36a26fe124cd32d7b2`, normalized
  `87d654b4…`. The guest's tags are `/GTTGKY+`, `/HXABZP+`, native's `/CRSDXP+`, `/GXDUII+`
  (DejaVuSans); normalized, the compression-0 PDFs agree too (`f8960bc3…`). READ: the tag is
  `hash(frozenset(charmap.values())) % ((sys.maxsize + 1) * 2)`, and `charmap`'s values are
  glyph indices (`CharacterTracker.used: dict[str, list[dict[CharacterCodeType,
  GlyphIndexType]]]`), so the hash is of ints, which no secret touches, and a frozenset's hash
  does not depend on order. The guest's `sys.maxsize` is 2147483647 and `hash_info.width` 32
  (EXECUTED). Normalizing is honest: the tag is a function of the glyph set, and the glyph set
  is written in full elsewhere in the file, so nothing real can hide behind it. Pinning the
  guest's raw bytes as well is right.
- **contourpy's thread claim holds.** EXECUTED (201 × 201 grid): guest `max_threads()` 1 and
  every `thread_count` reports 1; native reports 1, 2, 4 and 10. Points and sums are equal at
  each chunk count (659, 664, 704). READ: `limit_n_threads` caps at
  `max(hardware_concurrency(), 1)`, and the worker loop starts `_n_threads - 1` threads, so
  none. contourpy's `meson.build` has no `dependency('threads')`, so no `-pthread` arrives
  (READ).
- **`_build_config.py` is as Decision 4 says.** READ: the memo's file records `python_path`,
  `build_dir`, `source_dir`, `compile_command`, the cross file in `build_options`, and
  `build_cpu*` `aarch64`/`darwin`; contourpy's `util/meson.build` runs the target Python for
  `importlib.metadata.version("meson-python")` with `check: true`, and nothing else reads it.
  The native wheel's file (042's venv) records `b_ndebug="if-release"`, so Decision 4's
  `-Db_ndebug=if-release` matches the wheel (the memo's build had `b_ndebug="false"`).
  contourpy's `.cpp` files hold 142 `assert(` (EXECUTED, `grep -o`), as Decision 4 says.
- **The oracle and the pins.** EXECUTED: the contourpy sdist's hash equals Decision 2's; a cp315
  wheel installs on the line's 3.15.0. The job's fuel: 9,236,815,441 on the plain relink with a
  warm cache (11,225,967,512 cold), as Decision 10 says.

## Acceptance criteria against evidence

1. Seen failing first: on 023's set every new check fails at import, which is honest but
   cheap; the two failures that prove something are the fallback-form run (EXECUTED here: it
   makes `dev/null`) and the host-fact run with the rewrite off. Holds as written, with
   finding 7.
2. Full build from pins: the patch and both trees check out (EXECUTED); the configure line is
   the wheel's (READ). Holds.
3. Same bytes: holds in design if `_build_config.py` is rewritten (finding 4 is about how).
4. The judge: holds, with finding 4's unit test in the judge-change list.
5. The numbers: holds, but finding 3's estimate will trip its own ±10% band.
6. Branch B: holds with finding 1.
7. Dry run: nothing to check before build.

## Findings, most severe first

1. **Spec 037 must change, and 043 leaves that to prose in another specification.** Medium:
   037 is confirmed, and under the plan (branch A) its builder builds from 037's text, which
   now contradicts what 043 needs.
   - READ (037): Decision 8 already says that if M2 lands first, step 57 uses
     `-Duse-system-libraries=qhull` and 037 carries the qhull patch. But the same text says
     "`pkgconf` sees exactly three folders" (OpenBLAS, numpy, pybind11), the configure line
     says `-Duse-system-libraries=none`, Decision 8's init-name bullet says no scipy name
     clashes "with matplotlib M1's", and its Design table has no `recipes/qhull_r.pc.in`, no
     `scripts/steps/37_plot_libs.sh` and no qhull patch. 043's Decision 6 says "037's text does
     not yet say either; its builder takes both from here." A builder of 037 reads 037.
   - INFERRED: both misses fail loudly (meson stops on the missing `qhull_r.pc`; step 60's
     clash check stops on `PyInit__qhull`), so nothing wrong would ship, but 037 would be built
     against a text that §5.2 says must decide every choice, and its reviewer would review the
     wrong text.
   - READ: the qhull patch is specified twice, differently: 037 gives `Status: merged`,
     upstream commit `1b67ec90`; 043 gives `Status: merged
     https://github.com/qhull/qhull/pull/143` (which `scan.STATUS` needs, `merged \S+`).
   - INFERRED (from 023's step 55: matplotlib finds FreeType and libraqm through `pkgconf` in
     step 37's prefix): the day a `qhull_r.pc` appears in that prefix, matplotlib's
     `dependency('qhull_r', version: '>=8.0.2', required: false)` succeeds instead of
     `find_library`, so `_qhull`'s `.deps` line changes form in whichever spec adds the file.
   - Fix, as conditions written into 037 now (a revision note in its status, seen by its
     reviewer), whichever of the two lands second:
     a. step 37 writes `qhull_r.pc` (`Version: 8.0.2`, `Libs: -L${libdir} -lqhull_r`,
        `Cflags: -I${includedir}` with `libqhull_r/` under it) from `recipes/qhull_r.pc.in`;
     b. step 57's `PKG_CONFIG_PATH`/`PKG_CONFIG_LIBDIR` gain step 37's `pkgconfig` folder (four
        folders, still none of the host's), and the configure line says
        `-Duse-system-libraries=qhull`;
     c. `scipy_rename.h` renames `PyInit__qhull` to `PyInit_scipy_spatial__qhull` and
        `gen_inittab.py`'s table maps `scipy.spatial._qhull` to it (a global rename is right:
        scipy has one `_qhull`);
     d. one qhull patch file, specified once: 043's name and header
        (`recipes/patches/qhull-8.0.2/0001-format-strings.patch`, `Status: merged
        https://github.com/qhull/qhull/pull/143`, `Files: src/libqhull_r/poly2_r.c`), the
        hunk made against the qhull tarball as 043 made it;
     e. the builder checks that `_qhull`'s `.deps` still names step 37's archive once after the
        `.pc` appears, and that 043's `plot_contour` job and `Triangulation` checks still pass
        on the patched qhull;
     f. 037's acceptance gains 043's criterion 6 (`nm` finds one copy of qhull's functions).
     043 then cites 037's revision instead of "its builder takes both from here".

2. **The facts sheet states matplotlib's AI policy incompletely.** Medium, for the reason
   spec 041's review gave: the owner sends this under his own name.
   - READ (3.11.2 `doc/devel/contribute.rst`, "Use of Generative AI"): besides the two items
     `pr.md` quotes, the unacceptable uses include "Solving topics that you wouldn't be able to
     solve yourself without AI", and the section ends: "we will flag and reject low-value
     contributions that we believe are AI generated. We may ban and/or report users to GitHub
     if they harm the project or its community through irresponsible use of AI."
   - READ (`main`, `gh api`): the section now says "the responsibility of the human
     contributor" and adds an unacceptable use: "Increasing breadth of contributions, i.e.
     simultaneously contributing to several projects". That bears on this project, whose owner
     is asked to send drafts to numpy, pandas, networkx, qhull and matplotlib. The pull request
     template on `main` asks for the summary "in your own words (no AI please)" and has an "AI
     Disclosure" section. `main` has no `AGENTS.md` (404).
   - INFERRED (not checked against their sources here): FreeBSD's libc (since 11.0) and
     Android's bionic (API 23) also have `fopencookie`, so "Only glibc, musl and wasi-libc have
     `fopencookie`" (`pr.md` and `notes.md`) is wrong as written.
   - Fix (in `pr.md` and `notes.md`, before Decision 3 moves the sheet unchanged): quote the
     whole list and the reject/ban clause from 3.11.2, add `main`'s breadth item and the
     template's two sections, and say plainly that the owner decides whether to engage at all;
     reword the platform claim to "not every platform matplotlib supports has it (macOS has
     `funopen`, Windows neither)".

3. **The growth numbers leave out data and one zip member.** Low-Medium: Decision 10 makes a
   number off by more than a tenth a build-review finding, so the estimate should be right.
   - EXECUTED (`mapsum.py` → `mapsum.txt`): +0.7 MB is code only (`CODE`: contourpy 383,527,
     qhull 302,109, `_qhull` 13,287 bytes in the relink's map; the memo's 388,785 and 302,293
     are the same within 2%). Only 5,866 bytes of `.rodata` are attributed to them, because
     string literals are merged into `<internal>:(.rodata)`; its 17 objects carry 109,831 bytes of `DATA`,
     contourpy's 14 carry 138,068 (some merged at link, some assert text). INFERRED: the
     binary grows by about 0.8 to 0.95 MB, less contourpy's asserts' code (the memo built with
     `b_ndebug=false`; 043 builds without).
   - EXECUTED: the installed contourpy tree is 17 files (`py.typed` included), 61,732 bytes
     deflated; Decision 4 also adds `contourpy-1.4.0.dist-info/METADATA`, so the zip gains 18
     members, and plain `-c pass` grows by 18 members' cost.
   - Fix: state the binary's growth as "about +0.8 to +1.0 MB, code and data", or measure it
     before the build as the difference of two links of the memo's objects; say +18 members
     and recompute the `-c pass` estimate; note the job's 9.2 G was on an asserts-on build.

4. **The host-fact machinery needs three code paths the text does not name.** Low.
   - READ: `make_stdlib_zip.py`'s `_host_items` finds numpy's keys in a `"Machine
     Information"` dict literal; contourpy's keys are keyword arguments of a `dict(...)` call
     returned by `build_config()`. A new parse is needed, with the same "absent stops, reads
     back fixed" rule. The `--replace` error text names only `_sysconfigdata` and numpy.
   - READ: `artifacts.host_fact_errors` applies the bare `linux` word only when the member
     `startswith("numpy/")`; Decision 9 wants contourpy judged with numpy's list, so that
     condition changes too. `tests/unit/test_artifact_rules.py:351` unpacks
     `sysconfig, config = rules.HOST_FACT_MEMBERS`, which fails with a third member; the Design
     table does not list that file.
   - READ (memo's file): the remaining values are host-neutral once `$HERE` is replaced
     (`compiler_version="22.1.0"`, `linker_id="ld.lld"`, `python_install_dir` under
     `/usr/local`), and the `meson-python` stand-in is found through `PYTHONPATH`, which
     `python-wasi-cross` puts before the build-Python's own paths.
   - Fix: say that `CONTOURPY_BUILD_KEYS` are read from `build_config()`'s `dict(...)` keywords;
     widen the word-list condition; add `tests/unit/test_artifact_rules.py` to Design and the
     judge-change list.

5. **The threads check must fix the chunk count.** Low. EXECUTED: the lines' point counts
   depend on `chunk_count` (659, 664 and 704 at 0, 4 and 16), so "gives the `serial`
   algorithm's lines" holds only when `serial` runs with the same `chunk_count` as `threaded`.
   Fix: name it in Decision 9 (for example `chunk_count=16` for both, and compare point arrays,
   not sums).

6. **The PDF normalization: make it visible, and say what moves the pin.** Low.
   - INFERRED from `_get_subset_prefix`: in the guest a tag has fewer than six letters when the
     32-bit hash is below 26^5, about 0.28% of glyph sets (natively 6e-13); `/[A-Z]{6}\+` would
     then miss it and the golden would fail for no real reason. For this job it matched all six
     tags (EXECUTED), but a later job could hit it.
   - Fix: normalize `/[A-Z]{1,6}\+` and print the number of tags replaced (6) beside the hash,
     so a change in fonts shows as a line, not only as a hash.
   - READ: the raw-bytes pin also moves with the guest's zlib (step 30), since the default
     compression is 6; a zlib security bump (§5.5) then needs a judge change. Say so beside the
     pin. (The `usetex` path hashes `dict_values` by identity, `backend_pdf.py:998`, so it would
     not be deterministic; it is out of scope, with no TeX.)
   - The spec's "at hash seeds 0 and 1 natively" has no record in the drafting folder (its
     `-0`/`-6` files are compression levels). It holds (above); cite this review's runs.

7. **The no-host-file check should watch the whole writable root, not only `dev/`.** Low.
   INFERRED: a later qhull or matplotlib change could open another path (a log, a temp file).
   Fix: list every file under each writable grant before and after the triangulations (the
   font cache's folder excluded or listed separately) and require equality.

8. **contourpy's `mpl2005` code carries an older notice.** Low (§4.12). READ:
   `src/mpl2005_original.cpp` says its routines "came from gcntr.c, part of the GIST package";
   contourpy ships only its BSD-3-Clause `LICENSE`. matplotlib ships `LICENSE/LICENSE_YORICK`
   (Regents of the University of California, 1996, "this entire notice is included in all
   copies of any software which is or includes a copy or modification"). INFERRED: that notice
   covers this code too. Fix: Decision 11 says `LICENSE_YORICK` ships (it does through 023's
   matplotlib notices, if 023 keeps the whole `LICENSE/` folder) and question 81 mentions it, so
   the owner approves knowingly.

## On 037 and the order

Decision 13's order (023, then 043, then 037) is right: 043 is small and the roadmap puts M2
before scipy. Under that order 043 itself adds no qhull patch and no `.pc`, which is the
smallest change, and matplotlib's linked qhull matches its PyPI wheel's (unpatched; the
`trace1` hunk is unreachable without a `T` option, READ). The cost is that 037 must absorb
finding 1's items, and they belong in 037's text before its builder starts. If 037 is already
in flight, branch B is complete as written once finding 1's single patch definition is used.
One note for 037, not a condition here: scipy's `qhull_options` lets user code pass `TO
<path>` (READ, qhull's `freopen`, `global_r.c:1386, 1406`), so after 037 `fd_renumber` is
reachable from Python on a path the code names; the hostile-guest grants already bound it.

## Constitution checks

- **§4.1, patches few, recorded, temporary:** holds. A recipe was weighed and rightly refused
  (no path works; a link-time wrap changes every caller; a forced header hides upstream code).
  The patch is the smallest change, `#ifdef __wasi__` only. Its draft needs finding 2.
- **§4.2, every input pinned:** holds (EXECUTED: contourpy's hash; meson-python is a stand-in,
  not a download).
- **§4.3, one target / §4.4, two channels:** holds. `fd_renumber` is preview1 (EXECUTED:
  `wall_errors` empty).
- **§4.9, tests count:** holds. The goldens compare bytes and hashes; fuel is the ratchet's.
- **§4.10, claims carry evidence:** holds, with finding 3's numbers and finding 6's missing
  record.
- **§4.11, platform semantics documented:** holds (Decision 12: the tags, one thread,
  `fd_renumber`).
- **§4.12, licences:** waits on question 81, as the spec says; finding 8.
- **§4.15, safe by default:** holds, and the patch is better than the memo's for it (EXECUTED).
- **§5.2, no open questions:** holds in 043; finding 1 is an open edge in 037.
- **§5.6 and §5.7:** this review; one build-class spec in flight (Decision 13).
- **§6.2 to §6.4:** the one-qhull design is the plain, smallest form.
- **§7:** nothing posted upstream; the owner sends.

## Disposition (filled in by the author, then confirmed by the reviewer)

By the author, 2026-10-18. Every finding is fixed in the text; none is answered by argument.

1. **Fixed, in 037 and 043.** Spec 037 is amended (its status line: "Amended 2026-10-18 by spec
   043's pre-build review"). Decision 7: a fourth `pkgconf` folder, step 37's, and
   `-Duse-system-libraries=qhull`, when 043 has landed first. Decision 8: the
   `scipy.spatial._qhull` → `PyInit_scipy_spatial__qhull` rename in `scipy_rename.h` and the
   inittab table, in either order; "One qhull" now lists your conditions a to f (the
   `qhull_r.pc` from `recipes/qhull_r.pc.in` at step 37; the fourth folder; the rename; one
   qhull patch with 043's name and `Status: merged https://github.com/qhull/qhull/pull/143`
   header; the `.deps` and `plot_contour` checks once the `.pc` exists; one copy of qhull).
   Design gains a conditional row; acceptance gains criterion 8. Nothing else in 037 changed.
   043's Decision 6 now cites 037's amended Decision 8 instead of restating it: branch A leaves
   a, b, d, e and f to 037's builder; branch B does them; the rename is 037's in both. 043's
   Kind, Design row and criterion 6 follow.
2. **Fixed, in the facts sheet.** `pr.md` quotes the whole "Use of Generative AI" section from
   `main` (`493abb1b63`), the "breadth" item included, says how 3.11.2's differs, quotes the
   template's "PR summary" ("in your own words (no AI please)") and "AI Disclosure" sections,
   notes `main` has no `AGENTS.md`, and says the owner decides whether to engage at all. The
   platform claim now reads "not every platform matplotlib supports has `fopencookie` (macOS
   has `funopen`, Windows neither)", in `pr.md` and `notes.md`; the wasi-sdk facts cite your
   `stdio.h`/`libc.a` check. `notes.md` records the revision.
3. **Fixed.** Decision 10: `python.wasm` and the snapshot +0.8 to +1.0 MB, code and data, with
   your map numbers and `DATA` sizes, and the asserts-off note; the zip +18 members (17 files
   with `py.typed`, plus `METADATA`; Decision 4 says so too); plain `-c pass` about +1.4 M; the
   job's fuel marked as from an asserts-on build, with your warm and cold figures.
4. **Fixed.** Decision 4 names the three code paths: a second `_host_items` parse for
   `build_config()`'s `dict(...)` keywords with numpy's absent/read-back rule and a three-member
   `--replace` error text; `host_fact_errors`' bare-`linux` condition widened to contourpy's
   member; `tests/unit/test_artifact_rules.py:351`. Design and the judge-change list carry them;
   criterion 1 adds a removed-key run.
5. **Fixed.** Decision 9: `thread_count=4, chunk_count=16` against `serial` with the same
   `chunk_count=16`, comparing point arrays; criterion 1 shows the check fails at another count.
6. **Fixed.** Decision 8: the pattern is `/[A-Z]{1,6}\+`, the number of tags replaced is
   printed, and why normalizing hides nothing is stated; Decision 9 says the raw pin moves with
   step 30's zlib and needs a judge change then. The seeds claim now cites your runs.
7. **Fixed.** Decision 9's no-host-file check lists every path under each writable grant,
   before and after, the font cache's grant included.
8. **Fixed.** Decision 11 names `gcntr.c`/GIST and `LICENSE_YORICK` and makes the judge's
   licence list hold it by name; question 81 names it so the owner approves knowingly.

Checked: `uv run pytest -q tests/checks/test_rules.py -k specification` passes (3). The whole
rules file has one failure not from this change: `boomslang`, a prior-art clone another agent
added, has no licence row in `context/prior_art/README.md`.


## Verdict

Not yet: revise, then confirm. The design is sound and reproduces. The patch exists in the
SDK, compiles to the linked object, opens no file, keeps qhull's error path, and adds only
`fd_renumber`. The SVG and the normalized PDF equal native at four native seeds and three guest
secrets, and the guest's raw PDF is deterministic. One qhull is scipy's source but for one
reachable-only-when-tracing hunk. Two Medium findings are text: 037 must carry finding 1's
conditions in its own words before either lands second, and the matplotlib facts sheet must
quote the whole policy and fix its platform claim. The Low findings can be written in at the
same time. It is built only after question 81.

## One line

The fopencookie patch, the PDF and SVG goldens and the one-qhull plan all hold up in the guest
and natively, but 037 must be amended with the `.pc`, the fourth `pkgconf` folder, the
`PyInit__qhull` rename and one qhull patch, and the facts sheet must quote matplotlib's AI
policy in full, before 043 is built.
