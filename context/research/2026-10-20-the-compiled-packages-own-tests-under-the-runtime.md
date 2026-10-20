# The compiled packages' own tests in the guest: the survey for spec 066

- **Status:** executed, 2026-10-20 (spec 066's Decision 1: a research step, time-boxed at 90
  minutes, run before any check, TOML or harness line; it used about 20 minutes of guest time).
- **Owner:** Clay Gendron
- **Researcher:** spec 066's builder (Claude Opus 5.5), at the lane's request.
- **Feeds:** spec 066, its dated delta to Decisions 8, 9, 11 and 12, and the confirmation round.
- **Stands on:** spec 066 as revised at `d1864fb`; spec 050's mechanism; the drafting evidence in
  `2026-10-20-the-packages-own-tests-drafting/`.
- **Evidence:** beside this memo, in `2026-10-20-the-compiled-packages-own-tests-under-the-runtime/`:
  `results.tsv` (one row per group), `failures.txt` (every failed, errored and collection-error
  line of every stream, by node id), `summary.json` (counts, classes and members), the stand-in
  driver `package_drive.py`, the host runner `survey.py`, `analyze.py`, `probe.py`, and
  `kiwisolver-trap.txt` (the trap's wasm backtrace). The full streams (3.2 MB) stay in the
  builder's worktree, `build/survey/out/<group>/stream.txt`.

## How it was run (EXECUTED)

- **The set.** A private copy of main's frozen set (wave 05, `SHA256SUMS` `4eaf1c3d…`), made with
  `cp -c -Rp` into the worktree's `build/artifacts`. The snapshot binary, as the judge runs it.
- **The embedder.** The judge's own `tests/harness/guest.py`, unchanged, on darwin-arm64, under
  wasmtime only, with the judge's environment (`TMPDIR=/tmp`, `HOME=/tmp`) and matplotlib's data
  granted (`mpl_data=True`). A fuel cap of 1.5×10¹² per session. At most three guests at once;
  `build/lane.lock` checked before every run, and absent each time.
- **The tests.** Each tarball from `downloads/`, its SHA-256 checked against `downloads/SHA256SUMS`,
  unpacked into the worktree and given its carried patches with `scripts/steps/apply_patches.sh`
  (matplotlib 1, Pillow 1, kiwisolver 1, regex 2, lxml none). One stage per family under
  `build/harness/survey-stage/<group>/`, granted read-only at `/upstream-<package>`: the staged
  folders under `tree/`, the kit (`kit.txt`'s seven wheels) under `kit/`, the driver, the `.ini`,
  the group's JSON.
- **The driver.** A stand-in `package_drive.py`, spec 066's Decisions 3, 5, 6 and 7 as written at
  `d1864fb`: the grant from its own path; the kit appended after the zip; `package_paths`,
  `extra_sys_path`, `cwd`; `R skipped` for a skipped collection; lxml's `keep_classes` with `D`
  lines; lxml's doctest files and docstring doctests run by the stdlib's `DocTestRunner` with
  lxml's own flags. One survey-only option: `--continue-on-collection-errors`, so a collection error
  does not hide the rest.
- **Not measured: contourpy.** Main's set has no contourpy until 043 lands. On main's set, every
  matplotlib test that imports contourpy, or matplotlib's `_qhull` (M2's), fails to import; those
  failures are 043's, listed below and not counted as findings.

## The numbers (EXECUTED, darwin-arm64)

| group | fuel | passed | failed | skipped | other |
|---|---|---|---|---|---|
| `matplotlib-axes` | 691.5 G | 874 | 6 | 45 | |
| `matplotlib-mathtext` | 296.2 G | 985 | 2 | 1,004 | |
| `matplotlib-render` (less `test_contour.py`) | 998.1 G | 984 | 61 | 253 | |
| `matplotlib-rest` | 956.9 G | 5,462 | 40 | 193 | 28 xfailed |
| `mpl-axes_grid1` | 72.1 G | 52 | 0 | 0 | |
| `mpl-axisartist` | 34.7 G | 49 | 1 | 0 | |
| `mpl-mplot3d` | 303.3 G | 229 | 15 | 0 | |
| `pillow` (working folder the read-only tree) | 430.7 G | 4,587 | 78 | 1,054 | 3 xfailed |
| `lxml` | 110.8 G | 2,053 | 5 | 58 | 4 collection errors; 360 deselected |
| `regex` | 16.0 G | 147 | 1 | 0 | |
| `kiwisolver` | 12.5 G to the trap | 48 | 0 | 0 | **traps** |
| **all but kiwisolver** | **3,910 G** | **15,422** | 209 | 2,607 | |

Each session includes pytest's start, about 10 G (kiwisolver's first session, which collected
nothing, spent 10.06 G).

## What it found

1. **A product defect: kiwisolver traps the guest whenever the cyclic garbage collector clears one
   of its objects.** kiwisolver's four `*_clear` functions (`Term_clear`, `Expression_clear`,
   `Constraint_clear`, `Variable_clear` in `py/src/*.cpp`) return `void`, and are cast into
   `tp_clear`, which CPython calls as `int (*)(PyObject *)`. Under WebAssembly the call's type
   does not match, and the guest ends in `wasm trap: indirect call type mismatch`, at
   `gc_collect_main` (`kiwisolver-trap.txt`, frame 0). It trapped in `test_expression_creation`,
   then with that deselected in `test_term_creation`, then with both deselected in
   `test_variable_rich_compare_operations`, which calls no `gc.collect()`: wherever a collection
   meets a cycle. Three small programs that build the same objects outside pytest did not trap
   (`probe.py`; no cycle reached a kiwisolver object). The carried patch
   `0001-callback-signatures.patch` does not touch these four. matplotlib's constrained layout
   builds kiwisolver objects, so a user's program can meet the same trap. Spec 051's callback scan
   did not report it (the functions pass through kiwisolver's `void_cast`). This needs its own fix
   (a carried patch to kiwisolver, with its upstream pull request) before kiwisolver's suite can
   run; until then the whole group is a trap entry.
2. **A product defect: `import lxml.html.diff` raises `TypeError: 'str' object is not callable`.**
   The product ships `lxml/html/diff.py` as Python bytecode, where upstream compiles it with
   Cython. Its pure-Python fallback, `fake_cython`, defines `cfunc`, `cclass` and `declare` but not
   `final`, and `__getattr__` answers every other name with the string `"object"`, so
   `@cython.final` (line 949) calls a string. EXECUTED in a plain guest program as well. lxml's
   `test_diff.py`, `test_diff.txt` and `lxml.html.diff`'s docstrings fail with it. A fix is a
   carried patch (add `final` to `fake_cython`) with its upstream pull request, or compiling the
   module as upstream does.
3. **matplotlib costs far more than drafted: 3,353 G for its seven groups, against 1.3 to 2.6 T
   INFERRED.** Three groups pass the 480 G bound: `matplotlib-render` (998.1 G) and
   `matplotlib-rest` (956.9 G) must be split by file; `matplotlib-axes` (691.5 G) is one file,
   `test_axes.py`, and stays one group (Decision 11's rule). With caps at 1.5 times, the six
   families' caps come to about 5.9×10¹², twice the 3×10¹² budget. Every matplotlib PDF, EPS and
   SVG comparison skips (no Ghostscript, no Inkscape), as drafted.
4. **The mpl-toolkits conftest clash is real** (the review's L4): one session over the three
   toolkit folders stopped before collecting anything (`ValueError: Plugin already registered under
   a different name`, two `tests.conftest`). One group per toolkit folder runs cleanly.
5. **Pillow's fuzz tests run** (the review's H2): `Tests/oss-fuzz/test_fuzzers.py` gave 1,060
   passes and 37 skips, with `Tests/oss-fuzz` on `extra_sys_path`. Pillow's tests carry the
   `timeout` marker (pytest-timeout), which the `.ini` must register, or nine modules fail to
   collect under `--strict-markers`.
6. **Pillow's writable working folder (Decision 6) was voided twice by the host.** Both runs that
   copied `Tests/` (1,279 files) into the guest's writable root ended in the embedder's spec 089
   guard: `HostLitter: … /.DS_Store (after the run)`, macOS's folder-size cache writing into the
   root after the copy. The run with the read-only tree as the working folder completed; in it, at
   most one failure could come from the folder being read-only
   (`TestImage::test_save_without_changing_readonly`, `assert 0`, unread). So the copy must be made
   where the litter guard does not see a host write into the guest's root, or Decision 6 must be
   revisited; the confirmation round decides.
7. **lxml's selection works as revised.** `keep_classes` deselected 360 collected items that
   `test_suite()` never runs (the abstract bases the review named), and every listed class ran.
   Under pytest's own doctest plugin, 9 doctest files failed on
   `ValueError: check_output() requires a code object with 1 free vars, not 0`
   (`lxml.usedoctest` swaps the checker's code object, and pytest's checker is a closure); run by
   the stdlib's `DocTestRunner` with lxml's flags, as lxml's own runner does, 13 of the 17 pass,
   and of the docstring suites only `lxml.html.diff` (finding 2) and `lxml.cssselect` (not shipped)
   do not load. `selftest2.parsefile` reads `samples/simple.xml` from the working folder, so the
   group copies `samples/` (two files) there.
8. **regex: its one failure is a harness artifact.** `test_main` is regex's own entry point
   (`unittest.main()`), which pytest collects by its name; inside pytest it parses the driver's
   argv and exits 1. It is deselected by node id; its 101 tests run as collected (147 cases).

## The failures by class (EXECUTED; members in `failures.txt` and `summary.json`)

| group | class | members | reason as measured |
|---|---|---|---|
| matplotlib (all) | `m2-not-in-set` | 6 + 55 + 16 + 1 + 15 = 93 | `No module named 'contourpy'` or `cannot import name '_qhull'`: spec 043's, gone once 043 lands; not a class in the build |
| `matplotlib-mathtext` | `no-processes` | 2 | `test_fontcache_thread_safe`, `test_lockfilefailure` |
| `matplotlib-rest` | `no-processes` | 13 | `test_lazy_imports`, seven `test_backend_getattr[...]`, `test_importable_with_no_home`, `test_importable_with__OO`, `test_axeswidget_interactive`, `test_data_parameter_replacement`, `test_locale_comma` |
| `matplotlib-rest` | `pillow-zlib-only` | 5 | `encoder jpeg not available` (`test_jpeg_dpi`, four `test_animation` jpeg cases) |
| `matplotlib-render` | `pillow-zlib-only` | 3 | `test_imsave[jpg]`, `test_imsave[jpeg]`, `test_jpeg_alpha` |
| `matplotlib-render` | `no-threads` | 2 | `test_ginput`, `test_waitforbuttonpress` |
| `matplotlib-rest` | unread (6) | 6 | `test_movie_writer_registry`, `test_movie_writer_invalid_path` (no ffmpeg; messages differ), two `test_mlab` `DID NOT RAISE LinAlgError` (numpy without LAPACK errors), `test_warn_external` (code names in the zip, `zip-code-names`), `test_cm_stub_matches_runtime_colormaps` (`cm.pyi` not staged) |
| `matplotlib-render` | unread (1) | 1 | `test_tripcolor_warnings` (`DID NOT WARN`) |
| `pillow` | `pillow-zlib-only` | 51 | `decoder jpeg not available` (39), `encoder jpeg not available` (12) |
| `pillow` | `no-mmap` | 17 | `mmap is unavailable on wasm32-wasi` (PDF saves and others) |
| `pillow` | unread (10) | 10 | four `test_arrow` mapped-file cases (`assert None is not None`, the same `mmap`), two `test_pilinfo` (`PIL._imaging` is builtin: no `__file__`), two `test_file_dds` `Out of memory` (Errno 48, `wasm32-memory`), `test_empty_path` (`open('')` answers `IsADirectoryError`), `test_save_without_changing_readonly` |
| `lxml` | unread (5) | 5 | `test_include_paths` (`lxml.get_include()` points into the zip), `validation.txt` (isoschematron, the stand-in), `api.txt`, `parsing.txt`, `test_diff.txt` (finding 2) |
| `lxml` | collection | 4 | `test_diff.py` and `docstrings:lxml.html.diff` (finding 2); `test_elementsoup.py` (`from ...tests.common_imports`: three dots, beyond the `tests` package pytest's importlib mode makes); `docstrings:lxml.cssselect` (not shipped) |
| `regex` | harness | 1 | `test_main` (finding 8) |

No failure in the surveyed groups was `no-dup`, `shallow-recursion` or `zip-no-source`. No group
trapped but kiwisolver. No `M` line named a product module loaded from outside the zip: the
product's `packaging` was the one pytest used.

## For the confirmation round

The delta this memo feeds is written into spec 066 (its section "Delta from the survey"):
the two product defects and what they block; matplotlib's real cost and the budget it breaks; the
groups split; the Pillow working folder; the classes with members; lxml's runner and staging;
regex's `test_main`; contourpy measured later on 043's set.

## Addendum, for the confirmation's C2 and C6 (2026-10-20, EXECUTED)

On the same private copy of main's set, `build/lane.lock` absent:

- **C2.** A plain guest program (`probe.py`): `numpy.linalg.inv` and
  `numpy.linalg.matrix_power(a, -1)` of `a = [[1.0, 2.0], [2.0, 4.0]]` both return
  `[[nan, nan], [nan, nan]]`; neither raises `LinAlgError`. So `test_mlab`'s two failures are the
  product's missing floating-point exception flags, as numpy's own suite records by skipping them
  on wasm.
- **C6.** lxml's doctest files rerun with full reports (the driver now imports
  `lxml.doctestcompare` first, which registers `PARSE_HTML` and `NOPARSE_MARKUP`): `api.txt`
  (line 654, `XIncludeError: could not load doc/test.xml`) and `parsing.txt` (line 107,
  `failed to load "doc/test.xml"`) fail only because the survey's working folder lacked the
  tarball member `doc/test.xml`; `validation.txt` fails from line 460 on
  `ImportError: lxml.isoschematron is not in this build` (the stand-in); `test_diff.txt` on
  finding 2. No product defect beyond findings 1 and 2.

## The re-survey on 043's set with 096 (2026-10-20, EXECUTED)

Main's set after wave 06 (043, 037, 096; `SHA256SUMS` `f12cd25c…`), a private copy in the
worktree; darwin-arm64; the same stand-in driver and embedder; at most three guests at once;
`build/lane.lock` absent at every start. The groups follow the spec as confirmed: Pillow, contourpy
and lxml read their data from the tree root (lxml's two file-writing tests need a writable working
folder, below); `cm.pyi` staged; regex's `test_main` deselected; `test_elementsoup.py` not
selected. Evidence: `results-resurvey.md` (the table with each cap by the owner's rule),
`failures-resurvey.txt`, `summary-resurvey.json`, `caps.py`, and the updated `survey.py` and
`package_drive.py`.

| group | fuel | cap (1.5×, two figures) | passed | failed | skipped |
|---|---|---|---|---|---|
| `matplotlib-axes` | 699.3 G | 1.1×10¹² | 880 | 0 | 45 |
| `matplotlib-mathtext` | voided twice (host litter); 296.2 G on wave 05's set | 4.5×10¹¹ (provisional) | | | |
| `matplotlib-render-1` | 231.1 G | 3.5×10¹¹ | 248 | 0 | 120 |
| `matplotlib-render-2a` | 304.5 G | 4.6×10¹¹ | 290 | 2 | 12 |
| `matplotlib-render-2b` | 337.1 G | 5.1×10¹¹ | 392 | 3 | 76 |
| `matplotlib-render-3` | 272.9 G | 4.1×10¹¹ | 197 | 0 | 49 |
| `matplotlib-rest-a` | 309.5 G | 4.7×10¹¹ | 966 | 9 | 94 |
| `matplotlib-rest-b1` | 323.5 G | 4.9×10¹¹ | 3,367 | 14 | 89 |
| `matplotlib-rest-b2` | 384.5 G | 5.8×10¹¹ | 1,146 | 1 | 9 |
| `mpl-axes_grid1` | 72.0 G | 1.1×10¹¹ | 52 | 0 | 0 |
| `mpl-axisartist` | 35.7 G | 5.4×10¹⁰ | 50 | 0 | 0 |
| `mpl-mplot3d` | 336.8 G | 5.1×10¹¹ | 244 | 0 | 0 |
| `contourpy-1` (array … enum) | 217.4 G | 3.3×10¹¹ | 1,213 | 0 | 19 |
| `contourpy-filled` (`test_filled.py`) | **2,387.6 G** | 3.6×10¹² | 462 | 0 | 56 |
| `contourpy-lines` (`test_lines.py`) | **1,459.5 G** | 2.2×10¹² | 379 | 0 | 40 |
| `contourpy-rest` (internal … z_interp) | 90.4 G | 1.4×10¹¹ | 198 | 0 | 80 |
| `pillow` | 431.0 G | 6.5×10¹¹ | 4,587 | 78 | 1,054 |
| `lxml` (writable working folder) | 104.5 G | 1.6×10¹¹ | 2,058 | 2 | 58 (360 deselected) |
| `regex` | 16.0 G | 2.5×10¹⁰ | 147 | 0 | 0 |
| `kiwisolver` | 13.0 G | 2.0×10¹⁰ | 50 | 0 | 0 |
| **all** | **about 8.3 T** (8.03 T measured, plus mathtext) | **about 1.26×10¹³** | | | |

What it found:

1. **096 holds.** kiwisolver ran its whole suite, 50 passes, no trap. `lxml.html.diff` imports:
   `test_diff.py`, `test_diff.txt` and its docstrings pass. No group trapped.
2. **043's failures are gone.** No matplotlib test failed on `contourpy` or `_qhull`;
   `test_tripcolor_warnings` and `test_cm_stub_matches_runtime_colormaps` (with `cm.pyi` staged)
   pass. The remaining matplotlib failures are the confirmed classes: `no-processes` 15 (one new
   member, `test_pickle_load_from_subprocess[png]`, which needed contourpy to reach its subprocess)
   plus mathtext's 2 from wave 05, `pillow-zlib-only` 8, `no-threads` 2, `no-fp-exceptions` 2,
   `wasi-errno-values` 1, `stage-layout` 1.
3. **contourpy costs more than all of matplotlib: 4,155 G.** Its whole suite in one session ran
   out of a 1.5×10¹² cap. Two files dominate: `test_filled.py` 2,387.6 G and `test_lines.py`
   1,459.5 G, each one file past the 480 G bound. Their `test_*_random_big` cases (not marked
   slow upstream; parametrized over every algorithm, fill or line type and corner mask) cost about
   2.83 T: without them (`-k "not random_big"`), `test_filled.py` measured 544.0 G and
   `test_lines.py` 470.2 G. contourpy had no failure: its image comparisons pass once the working
   folder is the tree root (its `compare_images` opens `tests/baseline_images/…` by a relative path;
   with `/tmp/work`, 201 tests failed on that path alone).
4. **The owner's rule gives about 1.26×10¹³ of caps, not "about 7 T".** By the rule: matplotlib's
   family about 5.5×10¹², contourpy's about 6.3×10¹², Pillow 6.5×10¹¹, lxml 1.6×10¹¹, regex and
   kiwisolver 4.5×10¹⁰. The question put to the owner priced the rule at about 7 T before
   contourpy was measured. On Linux, 8.3 T at 0.16 to 0.31 s per G is 22 to 43 minutes of guest
   time: about twelve shards of 700 G, not six.
5. **Groups still past 480 G:** `matplotlib-axes` (699.3 G, one file, named by the rule),
   `contourpy-filled` and `contourpy-lines` (one file each). Every other group is under the bound
   after the splits (render in four, rest in three, measured).
6. **lxml writes to its working folder.** With the read-only tree root, two
   `ETreeC14NTestCase::test_python3_problem_filebased_*` tests failed on
   `PermissionError … 'test.xml'`: they write `test.xml` in the working folder. With `/tmp/work`
   holding copies of `doc/test.xml` and `samples/*.xml`, they pass; lxml's two remaining failures
   are `include-dir-in-zip` and `isoschematron-stand-in`.
7. **Pillow** is unchanged: the same 78 failures in the confirmed classes.
8. **Host litter.** `matplotlib-mathtext` was voided twice by spec 089's guard (`.DS_Store` in
   `/`, `/tmp` and `/tmp/work`, written by the host after the run); no other group was. Two
   strikes: its cap stays provisional, from wave 05's 296.2 G, and the build measures it.
