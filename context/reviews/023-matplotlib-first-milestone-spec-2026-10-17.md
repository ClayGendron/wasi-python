# Review of 023 — matplotlib, the first milestone (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the specification or the memo. I read `AGENTS.md`, the constitution (§2, §4.1, §4.6, §4.12, §4.15, §5.2), `context/reviews/README.md` and the 021 pre-build review (for the format). Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/023-matplotlib-first-milestone.md` as drafted (`7968e79`).
- **Read:** the memo `context/research/2026-10-17-matplotlib-on-the-current-line.md`, its scripts and patches; the scratch build `…/scratchpad/mpl-research/` (read only); the old memo `2026-10-16-what-matplotlib-needs.md` (its licence table and the owner's 2026-10-16 decisions); specs 017, 020 and 021; `scripts/steps/*.sh`, `scripts/wasi-cc`, `scripts/make_stdlib_zip.py`, `scripts/assemble_artifacts.py`, `scripts/00_download.sh`, `scripts/build.sh`; `src/wasi_python/runner.py` (`_zip_folder`, `_runtime_folders`, `_run_checked`, `_call`, `_check_preopens`, `_home_folder`); `tests/harness/` (`pins.py`, `needs.py`, `scan.py`, `guest.py`, `wasm.py`, `plugin.py`); `tests/checks/` (rules, v1.1, v1.2 hostile guest, v1.3, v1.4, v1.5); `tests/jobs/` and its oracle; `.github/workflows/` (the zero-patch step); `context/questions-for-the-owner.md`, questions 2 and 34 to 36; matplotlib 3.11.2's `meson.build` files, `lib/matplotlib/{__init__,font_manager,contour}.py`, `axes/_axes.py`, `tri/*.py`, `tests/*.py`; FreeType's `LICENSE.TXT`; HarfBuzz's `COPYING` and `src/ms-use/COPYING`.
- **Ran (EXECUTED, darwin-arm64).** Nothing in the repository was edited. I did not run `scripts/build.sh` or `uv run pytest`. Scripts and outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev023/`:
  - `shasum -a 256` of the scratch `matplotlib-3.11.2.tar.gz` equals the pin (`cec59631…`).
  - The memo's patch through the repository's `scripts/steps/apply_patches.sh` on a fresh extraction (`out/apply-memo.log`); the patch re-made in `git diff` form with the header deletion, through the same applier (`out/apply-git.log`); both through spec 020's `scan.patch_errors` with a draft of `Status: merged <url>` (`scripts/rules.py`, `out/rules-*.txt`); the re-made patch's changed lines against upstream commit `8e5591bc` (`scripts/addedlines.py`, `out/addedlines.txt`).
  - Decision 5 prototyped on the real runner: a scratch artifact set (the research `python-mplp-stripped.wasm`, `python-mplp-snapshot-nopre.wasm`, `python-stdlib-mpl.zip`, today's `MANIFEST`) with `WASI_PYTHON_ARTIFACTS` pointed at it; `mpl-data` copied into the runner's zip folder and preopened read-only at the nested path, after the zip, first and last, through `_check_preopens` (`scripts/nested_runner.py`, `out/nested-runner.txt`).
  - Fuel through the judge's driver: `-c pass`, `import numpy`, `import pandas` on today's set and the research set (`scripts/fuel.py`, `out/fuel.txt`), and the plain `pass` split between the binary and the zip (`scripts/fuel2.py`, `out/fuel2.txt`).
  - The static constructors each binary runs, read from `__wasm_call_ctors` and the name section (`scripts/ctors.py`, `out/ctors.txt`); `target_features` and the custom sections.
  - Greps and listings of the scratch trees, the installed `mpl-data`, the research zip and the research `python.wasm` (builder paths).
  - Note: while I worked, another session started `scripts/build.sh` in the main tree (`build/artifacts` was removed at about 14:06; step 40 was running). My "today" fuel numbers were taken before that. The later split used the research relink `python-base.wasm`, whose `pass` fuel equals today's exactly (241,460,036), with today's zip through a hard link.

## What holds

- **M1 is the right first cut.** It is the smallest piece that makes the product's common output, a PNG. Every part of it ran end to end through the real runner (below). It leaves the snapshot and question 34 alone. M2 adds a new upstream pull request and a host-path rewrite; keeping them out keeps this specification to one patch that upstream already merged. (INFERRED from the memo and the runs.)
- **`import matplotlib.pyplot` needs neither `_qhull`, `_tri` nor contourpy at import.** READ: `axes/_axes.py:17,34` imports the Python modules `matplotlib.contour` and `matplotlib.tri`; `_qhull` and `_tri` are imported inside functions (`tri/_triangulation.py:43,122`, `_tricontour.py:44`, `_trifinder.py:41`), and contourpy too (`contour.py:1333`). So the known gaps can be checked without breaking the import.
- **The nested data grant works with spec 017's identity check, in any order.** EXECUTED (`out/nested-runner.txt`): on both binaries, with the data preopen after the zip, first and last, `_check_preopens` passed. The guest listed `mpl-data`'s seven entries. `open(..., "w")`, `open(..., "a")` and `mkdir` all raised `PermissionError` errno 63.
- **The milestone matches through the runner.** EXECUTED: on both binaries, default root, a writable grant at `/out`: RGBA `eab6d61b37105e98`, shape (300, 400, 4); PNG bytes `b8759b7b…`, 22,439 bytes; `savefig(dpi=-1)` raised `ValueError: dpi must be positive`; 40 fonts, found at the nested path. Fuel with the runner's fresh `HOME` (a cold font cache): plain 9,470,678,396; snapshot without pre-import 7,799,452,647.
- **Decision 6's `OSError` holds.** EXECUTED: `root=False`, no grants: `import matplotlib` raised `OSError: Matplotlib requires access to a writable cache directory…` on both binaries. The memo had this as INFERRED.
- **The memo's patch is already re-made against 3.11.2.** EXECUTED: the repository's applier applied it cleanly, with no offset line, exit 0. `scan.patch_errors` gave no errors with a draft of `Status: merged https://github.com/matplotlib/matplotlib/pull/30291`.
- **Dropping `-pthread` changes nothing for today's users.** READ: only `recipes/wasi-numpy.cross` and `recipes/wasi-pandas.cross` name `wasi-cc`; steps 30 and 35 call clang directly. EXECUTED: `-pthread` appears 0 times in `build/numpy-build` and `build/pandas-build` (`compile_commands.json`, 198 and 99 commands, and `build.ninja`).
- **The `+atomics` check is concrete.** EXECUTED: `target_features` survives step 60's strip and Wizer. Today's two binaries and the research binaries list the same ten features, none of them `+atomics`.
- **The stand-ins meet §4.1 and §4.7.** READ: §4.1 names "a stand-in module" as a recipe file. The `setuptools_scm` stand-in is six original lines that print `PKG-INFO`'s version; the meson-python one is a two-line `METADATA`. Nothing is copied.
- **Step 55 does not need step 40.** EXECUTED grep: no `meson.build` in matplotlib names numpy, and no matplotlib, kiwisolver or Pillow source includes numpy's C headers. Step 55 needs steps 10, 20 (the cross Python), 30 (zlib) and 37. Placing it after 50 is harmless.
- **No new import module.** READ: `wasm.wall_errors` allows any preview1 import. The memo's `fd_renumber` (qhull's `freopen`) is preview1.

## Acceptance criteria against evidence

1. Checks exist and were seen failing first — **not reachable for one check:** the plain reactor's `-c pass` already passes today and is already checked (Finding 5).
2. A full build from pins — **not reachable as written:** the Kind and Design miss files the build must change (Finding 8), and the new trees cannot be judged by the zero-diff check (Finding 1).
3. The same-bytes rebuild — **open:** "the gate's handling decided before landing" leaves a choice to the build (Finding 10).
4. Green with `--accept-judge` and `--accept-growth` — **not as written:** the rules check fails on `recipes/patches/matplotlib-3.11.2/` (Finding 1); an accepted check breaks (Finding 2); the growth numbers are wrong (Finding 4).
5. A release dry run — **not as written:** the workflow requires exactly `7 passed` trees (Finding 1).

## Findings, most severe first

1. **High. The eight new source trees are not judged, and two pins cannot be.** (Decision 2; Decision 4, step 37; `tests/harness/pins.py:25`; `tests/harness/needs.py:108`; `tests/checks/test_v1_5_rebuild_from_pins.py:64-73`; the release workflow, lines 62-68)
   - The defect. §4.1 says the release fails on any difference from a pinned tarball other than the recorded patches. Spec 020 judges only the trees in `SOURCE_PATTERNS`, and says "a new patched project adds its `SOURCE_PATTERNS` entry and raises the workflow's count, in the specification that adds it". Spec 023 names neither.
   - Failure 1. READ: `test_carried_patches_follow_the_rules` builds its `tops` from `SOURCE_PATTERNS`. Without matplotlib there, `patch_errors` reports "recipes/patches/matplotlib-3.11.2: no pinned source tarball has this top folder". The judge is red.
   - Failure 2. EXECUTED (`tar -tf`): `sheenbidi-3.0.0.tar.gz` unpacks to `SheenBidi-3.0.0`, and `qhull-8.0.2.tgz` is not a `.tar.*` name. `test_source_tree_matches_its_tarball` asserts that the name without `.tar.*` is the top folder, so both fail once added.
   - Failure 3. READ: the workflow greps `^7 passed, [0-9]+ deselected in`. With 15 trees it fails.
   - Fix. Add FreeType, HarfBuzz, SheenBidi, libraqm, qhull, Pillow, kiwisolver and matplotlib to `SOURCE_PATTERNS` and `needs.SOURCE_COMPONENTS`; raise the workflow's count to 15. Pin the two files under names that fit the rule: `get <qhull URL> qhull-8.0.2.tar.gz` and `get <SheenBidi URL> SheenBidi-3.0.0.tar.gz` (the `get` line chooses the local name; the bytes and hashes stay). Each step unpacks to `build/<top>`. Put the harness files and the workflow in the Kind and the Design.

2. **Medium. Extracting into the zip folder breaks spec 017's layout and an accepted check.** (Decision 5, second bullet; spec 017 Decision 2; `tests/checks/test_v1_2_hostile_guest.py:567`)
   - The defect. Spec 017 says the zip folder "holds `python315.zip` alone". The zip folder is the host folder granted at `/usr/local/lib`, so anything extracted into it is also visible there.
   - Failure. EXECUTED: with `mpl-data` in the zip folder, the guest lists `/usr/local/lib` as `['mpl-data', 'python315.zip']`. READ: `test_the_zip_is_read_only_and_shared` runs `(name,) = os.listdir(os.path.join(temp, folder))`, which raises `ValueError` on two entries. Its guest also opens `os.listdir('/usr/local/lib')[0]` and expects the zip.
   - Fix. Decide the layout and say it. Either a zip folder holding `lib/python315.zip` and `mpl-data/`, with `lib/` granted at `/usr/local/lib`, so the guest sees only the zip there; or a visible `/usr/local/lib/mpl-data`, said in the README. Keep the data inside the one private folder: `_runtime_folders` then judges it with the zip, and the sweep and `_release` remove it with no new lock. A separate folder with its own lock would change other counts (READ: `test_v1_4_embedding.py:1059` asserts six held folders). Name spec 017's Decision 2 as amended, and list each check that changes, under `--accept-judge`.

3. **Medium. The per-call data check is not defined.** (Decision 5, second bullet)
   - The defect. "checks each extracted file … (size and CRC-32), records the stamps, and re-extracts on a change" does not say when CRC-32 runs, what is compared per call, or the source of the bytes. Stamps of recorded files do not see an added file, a removed folder, or a subfolder swapped for a link.
   - Failure. INFERRED: a temporary-folder cleaner that deletes `fonts/ttf/` leaves the recorded files' stamps unreadable; a check that skips missing names would grant a folder without fonts. A file added to `stylelib/` is never noticed.
   - Fix. Say: extract from the private copy after its SHA-256 check, never from the artifact path; write each member, read it back once and compare (CRC-32 is enough here: it detects accidents, the trust anchor is the zip's SHA-256 and the 0700 folder, and anyone who can write the folder can also write after any check); per call, compare the whole tree with the record (the same set of names, each a regular file and no link, each stamp equal); on any difference remove the folder's data and extract it again, with `_copy_zip`'s Windows fallback for a file a running guest holds open. Refuse member names with `..`, absolute paths or links. Say that every process pays the extraction at its first call, matplotlib or not (204 files, 9.6 MB), and put its time in the memo as a benchmark fact.

4. **Medium. Every plain-reactor call pays for the zip's new members, and criterion 4's numbers are wrong.** (Decision 5, first bullet; criterion 4)
   - The defect. zipimport reads the whole central directory at each plain start. Each member costs fuel on every plain call, whether matplotlib is used or not.
   - Failure. EXECUTED (`out/fuel.txt`, `out/fuel2.txt`): plain `pass` 241,460,036 → 293,981,873 (+21.7%). Split: today's binary with the research zip gives 293,550,056; the research binary with today's zip gives 241,907,203. So almost all of it is the zip: 681 more members, about 76,490 instructions each. The research zip has no `mpl-data`; its 204 members would add about 15.6 M more (INFERRED). Snapshot `pass` 81,938,099 → 83,578,807 (+2.0%); plain `import numpy` +4.7%; plain `import pandas` +1.3%. Criterion 4 says "the zip +6.5 MB with the data"; the memo measured +6.5 MB without it, and about +11.4 MB with it (INFERRED there).
   - Fix. Decide how the data travels. One option: one stored member (an inner archive) that the runner unpacks, which costs one directory entry instead of 204. Leaving out the 27 GUI-backend members would also help; they cannot run. Then state the expected growth per class in criterion 4 (plain start, snapshot start, the zip's and binaries' bytes), so the reviewer can tell expected growth from unexpected.

5. **Medium. The static-constructor check does not guard the class.** (Decision 7, fifth bullet)
   - The defect. The plain reactor already runs in `test_guest_runs_here[plain]` and `test_runner_runs_the_plain_reactor`. A new `-c pass` check passes today, so it cannot be seen failing first.
   - Failure. READ: the judge's driver (`tests/harness/guest.py`) does not shadow `poll_oneoff`, and the memo's hang is a 119-year `poll_oneoff`. So under the judge it is a hang, not a failure. The build hangs first: the research `wizer.log` shows Wizer killed after 681 s.
   - Fix. A static check. EXECUTED (`out/ctors.txt`): `__wasm_call_ctors` calls 5 functions in today's `python.wasm`, 10 in the patched research build, and 11 in the unpatched one, the extra being `_GLOBAL__sub_I_ft2font_wrapper.cpp`. The check compares that list, by name from the name section, with a reviewed list in the judge; a new constructor fails until reviewed. It fails first on the unpatched build, and never hangs. Run the same test at the end of step 60, so a bad build stops before step 80.

6. **Medium. The goldens are not defined well enough to reproduce.** (Decision 7, first bullet)
   - The defect. The memo's native run used a CPython 3.14.2 venv. The project's goldens are made by the pinned oracle (`tests/jobs/oracle`, Python 3.15.0, spec 002 Decision 11), and `test_goldens_reproduce_under_the_pinned_oracle` reruns them natively.
   - Failure. READ: matplotlib's own tests accept different pixels off x86_64 in 61 places (`tol=0 if platform.machine() == 'x86_64' else …`). The guest's pixels are the same on every host; the native golden may not be. A 16-hex prefix is also not a recorded golden. The judge has no PNG decoder (dev dependencies: pytest, ruff, wasmtime).
   - Fix. Add the plot job to `tests/jobs/` with matplotlib and its pins in the oracle's `pyproject.toml` and `uv.lock`. Record the full SHA-256 of the RGBA bytes, the shape, and the platform that made it. Say on which platforms the reproduce check runs for this job. Decode the PNG in the harness with the stdlib (zlib and the five PNG filters). Optionally pin the guest's PNG bytes too: they are deterministic (EXECUTED: `b8759b7b…` on both binaries).

7. **Medium. The licence list is incomplete, and the recorded approval does not cover it.** (Decision 8; §4.12; `scripts/assemble_artifacts.py`)
   - The defect. Compiled in but not listed: Agg (`extern/agg24-svn/src/copying`); FreeType's other notices, since its BDF and PCF drivers are built (EXECUTED, `ftmodule.h`), `fthash.c` is in base, and `-Dzlib=internal` compiles its zlib-licensed gzip module (READ, `LICENSE.TXT`); HarfBuzz's `src/ms-use/COPYING` (Microsoft, MIT) and the Unicode data terms of its tables. In the zip: STIX and Last Resort (OFL), DejaVu's public-domain part, the Adobe AFM terms (`pdfcorefonts/readme.txt` must travel with the AFM files), the AMS notice in `cm*.afm`, and the ColorBrewer, Yorick, Solarized and Qt-editor notices that matplotlib's `meson.build` lists.
   - Failure. READ: the 2026-10-16 decision names only FreeType's FTL, Qhull's licence, SheenBidi's Apache-2.0 and the fonts' OFL, Bitstream Vera and BaKoMa. matplotlib's PSF-style licence, Agg, HarfBuzz, libraqm, Pillow, kiwisolver, fonttools, cycler, pyparsing and packaging were in the old memo's table, not in the decision. Question 35 asks only about pybind11 and cppy.
   - Fix. Ship matplotlib's whole `LICENSE/` folder and Agg's `copying`; FreeType's `LICENSE.TXT`, `docs/FTL.TXT`, `src/bdf/README`, `src/pcf/README` and the gzip notice; HarfBuzz's `COPYING` and `src/ms-use/COPYING`. Extend question 35 to every licence not in the recorded decision. Name `scripts/assemble_artifacts.py` (licences, `PACKAGES`, `WHEELS`) in the Design. Consider `-Dzlib=system` for FreeType, so one zlib is linked and one security fix covers it (§5.5; INFERRED, not built).

8. **Medium. The Kind and the Design miss parts of the build.** (Kind; Decision 4; Design)
   - The defect and failure. Each is READ unless marked.
     - Step 10 must install the pinned `pkgconf` wheel. Step 37 needs it too: libraqm finds FreeType, HarfBuzz and SheenBidi through pkg-config (EXECUTED, the research `raqm-setup.log`, with Homebrew's `pkg-config`). The `pkgconf` wheels were never run.
     - `scripts/00_download.sh` (the `get` lines), `scripts/build.sh` (`ALL`), `gen_inittab.py`, and `scan.cpp_exception_errors`, which judges only the numpy and pandas cross files: new C++ (HarfBuzz, matplotlib, kiwisolver) would not be judged for its exception flags.
     - matplotlib's `meson.build` runs `find_program('python3', 'python')` then `-m setuptools_scm`. The memo put a `python3` link to the host Python first on `PATH`. On a host whose `python3` is the system one, the build would run an unpinned interpreter (§4.2). Say how the step finds the pinned Python and the stand-in.
     - Pillow's and kiwisolver's compile loops need a fixed object order (`LC_ALL=C` sort) for the same bytes.
     - meson looked for CMake to find qhull (EXECUTED: "Found CMake: NO" on macOS). A Linux host with CMake may take another path. Point the cross file's `cmake` at a missing program.
     - The meson-python stand-in is M2's (contourpy); Decision 2 lists it for M1.
   - Fix. Add each to the Kind and the Design, and say step 55 depends on steps 10, 20, 30 and 37.

9. **Low. The patch: the git form, the deleted header, the `ci/` file, the draft's body.** (Decision 3)
   - The defect. The memo's patch is `diff -ru` output, not spec 020's `git diff` form. It does not delete `src/_enums.h`; upstream's commit does (the `Only in` line is ignored by git). Decision 3 says the commit applies "only with offsets, so it is re-made": the memo's file is already re-made (EXECUTED, above).
   - Failure. EXECUTED: re-made by `git diff` with the deletion, it applies cleanly, the header is gone, and `patch_errors` gives no errors with `Files: ci/mypy-stubtest-allowlist.txt, src/_enums.h, src/_image_wrapper.cpp, src/ft2font_wrapper.cpp`. Its changed lines equal commit `8e5591bc`'s in all four files. With the memo's file, `Files:` must list three paths.
   - Fix. Decision 3: `git diff` form; delete `src/_enums.h` as upstream does; keep or drop the `ci/` file and say which (the memo's text says "without", its file has it); the draft's body points to the merged pull request and says there is nothing to send. Question 36 is about patch 2, which M1 does not carry: drop it from "Depends on", or say why it stays.

10. **Low. Criterion 3 leaves a choice to the build.** (criterion 3; §5.2)
    - The defect. "The difference is recorded and the gate's handling decided before landing" is an open question.
    - Failure. INFERRED: a host-dependent library would land with an exception the review never saw.
    - Fix. Criterion 3: the same `SHA256SUMS` on arm64 Linux, no exception. If a difference cannot be fixed after two tries, the build stops and a memo records it. On the memo's three risks: the font-list order does not touch M1's artifacts, since nothing is pre-imported, and the list comes from a `set` whose order already varies per process (READ, `font_manager.py:297`); `-ffile-prefix-map` is needed, since the research `python.wasm` holds 12 builder paths from pybind11's headers (EXECUTED, `strings`), and `test_artifacts_carry_no_build_path` would catch a miss; contourpy's `_build_config.py` is M2's.

11. **Low. The known gaps cannot be written as drafted.** (Decision 1; Decision 7, last bullet; `tests/checks/test_rules.py:153-157`)
    - The defect. A gap's `closes_with` must be an existing file under `context/`. "M2" is not one. The checks and their exact failures are not named.
    - Fix. Name each check and its failure: a Delaunay `Triangulation(x, y)` raises `RuntimeError: Could not open devnull` (memo); `contour` raises `ModuleNotFoundError` for contourpy. Close them with the memo, or a placeholder M2 specification written now. Simpler: leave `_qhull` out of M1's link, as `_tkagg` is left out. It cannot work without patch 2, and leaving it out drops the `fd_renumber` import and about 302 KB of qhull. `_tri` still serves triangles given explicitly.

12. **Low. Check wording and README points.** (Decisions 6 and 7)
    - The feature check should fix the whole list of ten features (EXECUTED), not only `+atomics`: `+simd128` or `+tail-call` would also be new host requirements.
    - "A program that does not import matplotlib behaves as before": say what is compared.
    - Name the kiwisolver error (the memo used `UnsatisfiableConstraint`).
    - EPERM is errno 63 in the guest (EXECUTED).
    - The README should say that a shared, writable `MPLCONFIGDIR` is trusted by later calls: its JSON names font files, so one call can make the next parse a font it chose (memo §3, READ `font_manager.py`). It should also name the new `fd_renumber` import, if `_qhull` stays.
    - Decision 6's `OSError` claim should carry its label; it is now EXECUTED (above).
    - The non-runner embedder must extract the data from the zip itself: the README line should say so.

## Constitution checks

- **§4.1:** the patch is upstream's merged change (EXECUTED: equal lines). The new trees are not yet judged (Finding 1).
- **§4.2:** the pins are complete in the memo; the `pkgconf` hashes come from PyPI and `00_download.sh` checks them on download. The `python3` on `PATH` is a risk (Finding 8).
- **§4.3, §4.4:** one target; no new import module (`fd_renumber` is preview1).
- **§4.6:** the set keeps its shape.
- **§4.7:** the stand-ins are original.
- **§4.8:** `pkgconf` runs only as a build tool.
- **§4.9, §4.10:** the checks count; one claim lacked its label (Finding 12).
- **§4.12:** incomplete (Finding 7).
- **§4.15:** the new grant is read-only (EXECUTED) and holds only the runtime's files; question 2 gave the owner's decision for a default grant. Keeping it inside the zip folder keeps it under `_runtime_folders`' rule (Finding 2).
- **§5.2:** criterion 3 and Decision 5's details are open (Findings 3 and 10).
- **§7:** nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

All twelve findings are taken into the specification; none is refused.

1. **Fixed.** Decision 8's judge changes add the eight trees to `SOURCE_PATTERNS` and `needs.SOURCE_COMPONENTS` and raise the workflow's count to 15. Decision 2 saves qhull as `qhull-8.0.2.tar.gz` and SheenBidi as `SheenBidi-3.0.0.tar.gz`. The harness files and the workflow are in the Kind and the Design.
2. **Fixed, first layout.** Decision 5 amends spec 017's Decision 2: the private folder holds `lib/python315.zip` (granted at `/usr/local/lib`, which lists only the zip) and `mpl-data/`, both inside the one folder, so no new lock or held folder. `test_the_zip_is_read_only_and_shared` is named under the judge changes, and a new v1.2 case pins `/usr/local/lib`'s listing.
3. **Fixed as suggested.** Decision 5's *Extraction* and *Per call*: from the private copy after its SHA-256 check; refused names; write, read back, CRC-32 and size; per call the whole tree against the record; re-extract with the Windows fallback; the cost named, a benchmark fact.
4. **Fixed.** The data travels as one stored inner archive, `matplotlib/mpl-data.zip`, so 204 members become one; step 70 leaves out the GUI backends, `testing`, `sphinxext`, tests and contourpy. Decision 6 states the expected growth by class from your per-member cost, and criterion 4 requires the build to land inside it. fontTools' trim is in Scope as the next lever, since its tables load by name.
5. **Fixed with your static check.** Decision 8's constructor check compares `__wasm_call_ctors`' callees with a reviewed list; step 60 runs it so a bad build stops before step 80. The plain `-c pass` check is dropped.
6. **Fixed.** The golden is a job under `tests/jobs/` made by the pinned oracle, with the full SHA-256 of the RGBA bytes, the shape and the platform; the reproduce check runs on the recording platform only; the harness decodes the PNG with the stdlib; the PNG bytes are pinned.
7. **Fixed.** Decision 9 lists each notice you named (and drops qhull's: nothing of it is linked now). Question 35 is widened to every licence outside the 2026-10-16 approval. FreeType is built with `-Dzlib=system`.
8. **Fixed.** Step 10 installs `pkgconf`; step 37 uses it for libraqm; `00_download.sh`, `build.sh`, `gen_inittab.py`, `assemble_artifacts.py` and `scan.cpp_exception_errors` are named; meson finds a step-private `python3` linked to step 10's pinned Python; the compile loops sort with `LC_ALL=C`; the cross file points `cmake` at a missing program; the meson-python stand-in is moved to M2.
9. **Fixed.** Decision 3: `git diff` form, `src/_enums.h` deleted, the `ci/` line kept so the patch is the merged commit whole, the four `Files:`, and a draft whose body says there is nothing to send. Question 36 is removed from "Depends on" (it is M2's).
10. **Fixed.** Criterion 3: no exception; two failed attempts stop the build and a memo records it.
11. **Fixed, simpler path.** `_qhull` is left out of M1's link like `_tkagg`. The two gaps are named with their failures (`ImportError` for `matplotlib._qhull`, `ModuleNotFoundError` for contourpy) and closed by the research memo.
12. **Fixed.** All ten features pinned; "behaves as before" is the existing checks passing unchanged; the kiwisolver error is `UnsatisfiableConstraint`; errno 63; Decision 7's `OSError` carries its label; the shared `MPLCONFIGDIR` note; the embedder extracts the inner archive itself. The `fd_renumber` note is moot with `_qhull` out.

## Verdict

Revise first. The design is right and every part of it ran, but the judge cannot pass as drafted (Findings 1, 2 and 4), the constructor check does not guard its class (Finding 5), and the goldens and licences need to be defined (Findings 6 and 7).

One line: M1 is the right cut and works through the real runner, pixel-equal to native, but the specification must judge the new trees, settle where the data goes and what it costs, and pin its goldens and licences before it is built.

## Confirmation

- **Date:** 2026-10-17
- **Reviewer:** the same fresh agent (Claude Opus 5.5); not the author.
- **Reviewed:** the specification as revised in `5e3e065`, the Disposition above, and question 35 as widened there (`git diff 7968e79 5e3e065`).
- **Ran (EXECUTED, darwin-arm64).** Outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev023/confirm/` (`out/`). I wrote nothing in the repository but this section. I did not commit, stage or pass `--accept`.
  - `layout_runner.py`: the revised layout on the real runner, with the scratch artifact set.
  - `members.py`: Decision 6's member arithmetic against the research zip and today's zip.
  - `backends.py`: which `matplotlib.backends` modules a plot and PNG, PDF, PS, EPS and SVG saves import, natively.
  - `meson/`: which interpreter meson's `find_program('python3', 'python')` runs in a cross build, with the pinned meson 1.12.1.
  - `out/stored-rule.txt`: the judge's zip rule on a zip with a stored member.
  - `native315/`: the milestone natively on the line's Python 3.15.0 with the pinned PyPI wheels (a scratch venv, `uv` cache in scratch).

### Each disposition against its finding

1. **The trees: closed.** READ: Decision 2 saves `qhull-8.0.2.tar.gz` and `SheenBidi-3.0.0.tar.gz`; Decision 8 adds the eight trees and `^15 passed`; the Kind and the Design name the harness files and the workflow.
2. **The zip folder: closed.** EXECUTED (`out/layout.txt`): a private folder holding `lib/python315.zip` and `mpl-data/` as siblings, `lib/` at `/usr/local/lib` and `mpl-data/` at the nested path, through `_check_preopens`. On both binaries `/usr/local/lib` lists exactly `['python315.zip']`, 42 entries in `fonts/ttf`, and the milestone gives RGBA `eab6d61b37105e98` and PNG `b8759b7b…`. Keeping both in one private folder keeps `test_v1_4_embedding.py:1059`'s six held folders (READ).
3. **The per-call check: closed.** READ: Decision 5 takes every point.
4. **Plain-start cost: closed, with condition A.** EXECUTED (`out/members.txt`): of 681 new members, the exclusions drop 65 (28 backends, 20 `testing`/`sphinxext`, 17 contourpy; the research zip already had no `tests`), leaving 617 with the inner archive. At 76,490 each that is +47.2 M (+19.5%) on plain `pass`. The specification says about 70, about 610, +47 M (+19%): inside its own tenth. Carrying `mpl-data` as 204 members instead would cost +62.7 M.
5. **The constructor check: closed.** READ: Decision 8 and step 60.
6. **The golden: closed, with condition D.** EXECUTED (`out/native315.txt`): on darwin-arm64 with Python 3.15.0 and the cp315 wheels, the RGBA hash is `eab6d61b37105e98` under hash seeds 0 and
   1. So the oracle golden will equal the guest's.
7. **Licences: closed, with condition E.** READ: Decision 9 lists each notice, and question 35 now asks about every licence outside the 2026-10-16 decision.
8. **The build's parts: closed, with condition C.**
9. **The patch: closed.** READ: Decision 3. The re-made form was EXECUTED in the review.
10. **Criterion 3: closed.** READ.
11. **The gaps: closed.** READ: `from matplotlib import _qhull` with no such builtin raises `ImportError`, as named. Nothing imports `_qhull` at import time (the review, READ).
12. **Wording: closed.** READ.

### The author's new choices

- **`lib/` and `mpl-data/`.** Sound (EXECUTED above).
- **One inner archive.** Sound for cost. But see condition A.
- **Decision 6's numbers.** The arithmetic holds (EXECUTED above). `python.wasm` about +19%: the memo's +6,247,429 bytes less qhull's 302,293 is +18.7% (INFERRED; `_qhull`'s own wrapper is not counted).
- **`_qhull` out, qhull built.** Sound. qhull stays a judged source tree; step 60 and `gen_inittab.py` must both skip it (the specification says so).
- **`-Dzlib=system`.** Sound, not built. EXECUTED `ls`: step 30 installs `build/zlib-wasi/lib/pkgconfig/zlib.pc`, so step 37 must put that folder on `pkg_config_libdir`. The matplotlib fonts are plain `.ttf`, so FreeType's gzip path does not touch the pixels (INFERRED).
- **The golden on the recording platform only.** Sound; the 3.15 run above backs it. See D.
- **The step-private `python3` shim.** Not needed, and the specification's sentence about it is wrong. See C.

### Conditions left (each a sentence or a list; none changes the design)

- **A. The stored member fails an existing rule.** EXECUTED (`out/stored-rule.txt`): `stdlib_zip_errors` reports "matplotlib/mpl-data.zip: stored, not deflated". That rule backs `test_stdlib_zip_is_bytecode_only_and_deflated`, and Decision 8 does not name it. Fix: deflate the outer member too, and have the runner read the inner archive into memory before opening it (a deflated member seeks backward slowly). Or name the rule's change under `--accept-judge`.
- **B. Step 70's keep-list breaks every import if read literally.** EXECUTED (`out/backends.txt`): a plot plus PNG, PDF, PS, EPS and SVG saves import `matplotlib.backends` (its `__init__`), `registry`, `_backend_pdf_ps`, `backend_mixed`, `backend_agg`, `_backend_agg`, `backend_pdf`, `backend_ps` and `backend_svg`. Decision 4 keeps "the Agg, PDF, PS, SVG, PGF and template modules", which leaves out the first four. Fix: list the kept files exactly: `__init__`, `registry`, `_backend_pdf_ps`, `backend_mixed`, `backend_agg`, `backend_pdf`, `backend_ps`, `backend_svg`, `backend_pgf`, `backend_template`.
- **C. meson never runs the `python3` shim.** READ (`mesonbuild/interpreter/interpreter.py`, `program_lookup`): every name is looked up in the cross file before `PATH`. EXECUTED (`meson/setup.log`): with a `python3` first on `PATH` and the cross file's `python` set, `find_program('python3', 'python')` ran the cross file's program ("Project version: cross"). In step 55 that is `scripts/python-wasi-cross`, step 20's build-Python, which is pinned and passes `PYTHONPATH` through. Fix: drop the shim. Say the `setuptools_scm` stand-in reaches meson on `python-wasi-cross`'s `PYTHONPATH`.
- **D. The oracle job must ignore system fonts.** EXECUTED (`out/native315.txt`): natively, matplotlib listed 1,378 fonts from this Mac; the guest lists 40. Here it still chose the bundled DejaVu Sans, but a host with a system DejaVu of another version could change the golden. With `MPL_IGNORE_SYSTEM_FONTS=1` it listed 40 and gave the same hash. Fix: `plot_line.py`, or `regen.py` for it, sets `MPL_IGNORE_SYSTEM_FONTS=1` and a fresh `MPLCONFIGDIR`.
- **E. Name the Unicode terms' source.** HarfBuzz's tree carries no Unicode licence file; its tables point to unicode.org (READ, `hb-unicode-emoji-table.hh`). Fix: quote the header text from the tree, or pin the licence text by URL and SHA-256 like the wasi-libc notices.

### §5.2

Nothing is left open. fontTools' trim and the M2 items are scoped out, each with its reason and measure. Conditions A to E are definitions the specification must write, not open questions.

### Verdict

**Passes for build after question 35**, once A to E are written in (no design change). Every finding is closed. The new layout, the inner archive and the golden ran as the specification says.

One line: the revision closes all twelve findings and its new choices hold up when run, with five small definitions to write first.

### The confirmation's conditions, written in by the author

- **A.** The inner archive's files are stored and the outer member deflated, so `stdlib_zip_errors` holds unchanged; the runner reads the outer member into memory whole.
- **B.** Step 70 keeps exactly the ten backend files named in the condition.
- **C.** The shim is dropped; the spec says meson runs the cross file's `python` (`scripts/python-wasi-cross`), and the stand-in reaches it on `PYTHONPATH`.
- **D.** `regen.py` makes the plot golden with `MPL_IGNORE_SYSTEM_FONTS=1` and a fresh `MPLCONFIGDIR`.
- **E.** The Unicode terms are pinned by URL and SHA-256, like the wasi-libc notices.
