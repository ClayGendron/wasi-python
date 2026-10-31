# Review of 170 — Pillow reads and writes JPEG

- **Date:** 2026-10-31
- **Reviewer:** an agent (Claude Opus), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** the specification as drafted, `context/specifications/170-pillow-reads-and-writes-jpeg.md`, uncommitted on `docs/specifications-169-and-170` from `dev` at `d64f8146`; its memo `context/research/2026-10-31-pillow-with-jpeg.md`
- **Run:** none: a specification review
- **Re-ran:** no test run. Read the spike's tree under `../wasi_python-wt/research-pillow-jpeg/build/spike-jpeg/`: the 3.2.0 tarball's listing, its `CMakeLists.txt`, the three configured headers and their `.in` templates, `simd/jsimd.c`, and CMake's `flags.make` for `jpeg-static`. Also the judge's suite files and `tests/known_gaps.toml`.
- **Time box:** 45 minutes (build-class); kept.

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning. No `gh` call was made and no run was dispatched.

**The claims checked.** All READ or EXECUTED here.

- **The file list is libjpeg-turbo's own.** `set(JPEG_SOURCES …)` at `CMakeLists.txt:653-691` names 98 distinct files (EXECUTED, a grep). The three arithmetic files are appended at `:695-705` under options that default on (`:256-262`). That makes 101, the spike's count. In 3.2.0 the 12- and 16-bit copies are separate wrapper files (`src/wrapper/jccolor-12.c` is `#define BITS_IN_JSAMPLE 12` and `#include "../jccolor.c"`). So one list, compiled once, is the whole library. No basename appears twice, so the archive's members cannot replace each other (EXECUTED). The tarball ships all 88 wrappers (EXECUTED, `tar -tzf`). The `wrappers` target is not built by default.
- **CMake adds nothing else.** `flags.make` for `jpeg-static` has empty `C_DEFINES`, one include folder (the build folder that holds the headers) and the spec's flags. No `__FILE__` appears in the sources.
- **`BUILD` is the only date.** It comes from `string(TIMESTAMP …)` (`CMakeLists.txt:91`). `COPYRIGHT_YEAR` is fixed (`:18`). `jcmaster.c:807` stores `BUILD` in `master->jpeg_version`, which is never written into a file. So the fixed string changes only the binary's bytes, never a JPEG's. The other configured values are the target's (`SIZEOF_SIZE_T 4`, `THREAD_LOCAL __thread`, `HAVE_BUILTIN_CTZL`), not the build host's.
- **The setjmp flags match the guest's set-up.** They are the cross file's C flags (`recipes/wasi-plot-libs.cross`) and qhull's (`37_plot_libs.sh:72-74`). `-lsetjmp` is on the `_host` line (`60_link.sh:122`). The weak-duplicate gate reads every `.deps` archive (`:98`). The spike saw the same imports, exports and 5-byte tag section.
- **The allowances.** `pillow.toml:32-38` (55 ids), `matplotlib.toml:224-238` (3 + 5 ids), `scikit-learn.toml:510-516` (4 ids), `pypdf.toml:42-48` (12 ids) and `openpyxl.toml:78-84` (1 id), each with its `[[gap]]` row in `known_gaps.toml`: **verified**. That is six classes in five suites.
- `pil_cc` (`55_matplotlib.sh:74-77`), `.deps` (`:87`), the library check (`:18-20`), the archive check (`37_plot_libs.sh:84-86`), `MORE_LICENCE` (`paths.py:681`), the docs lines and the tree count: **verified**. `_top_level_licence` matches `LICENSE.md`, the tarball's only top-level licence file (EXECUTED).

## Acceptance criteria against evidence

1. Signature — testable. The key is not named (Finding 6).
2. Header sweep — sound.
3. 101 files and the step's refusal — sound (READ above).
4. The longjmp check, seen failing first — testable. Its input is not specified (Finding 3).
5. `jpeg_images` against the oracle — sound for the integer DCT. The fallback should be a different one (Finding 1).
6. Imports and tag count unchanged — testable. The spike saw it.
7. The suites, with allowances removed or narrowed — sound. A class can empty (Finding 4).
8. Tree check, notice, package lines — sound.
9. Bytes and the wheel's line — recorded. No gate holds the line if this lands first (Finding 5).
10. Fast tier, lint, `ci-status`, same-bytes — sound.

## Findings, most severe first

1. **Low: a better fallback for the golden, and evidence at no cost** (Decision 4). The oracle comparison is sound. libjpeg-turbo's own tests expect different results from SIMD only for the float DCT (`CMakeLists.txt:1067-1130`). The integer DCT, colour conversion, sampling and Huffman paths share one set of checksums. Pillow uses the integer DCT by default. The fallback as written, "a native SIMD-off build of the same tarball, as the spike's probe was", is weaker. The probe was a C program. A Pillow-level golden would need Pillow built from its sdist on the host by an unpinned compiler, and the oracle project avoids that (its pyyaml note). libjpeg-turbo 3.2.0 reads `JSIMD_FORCENONE=1` at run time (`simd/jsimd.c:95`, `simd/README.md:95`). Fix text: "The golden is regenerated twice from the oracle's Pillow 13.0.0 wheel, once as it is and once with `JSIMD_FORCENONE=1`. The two outputs must be equal, and the landing notes say so (EXECUTED). If they are not equal, the golden is the `JSIMD_FORCENONE=1` output, with its reason, and that goes to the review. No native build of Pillow is made." The job also prints `features.version("jpg")`, so a `JPEG_LIB_VERSION` that differs from the wheel's shows as its own line.
2. **Low: hold the three recipe headers to their templates** (Decision 2). The headers are copies, and a later pin move could keep a stale one without anyone noticing. Fix text: "Step 37 checks that every line of `src/jconfig.h.in`, `jconfigint.h.in` and `jversion.h.in` without an `@…@` or `#cmakedefine` appears in its recipe header, and stops if one does not." Also say: the archive's member order is the list's order, `llvm-ar rcD`, and the include folders are `recipes/libjpeg-turbo` and the tree's `src/`.
3. **Low: say where the broken JPEG comes from** (Decision 4). The check builds it in the guest: the job's image saved as JPEG, then one fixed byte of its first DHT segment overwritten. Say which byte, and that the error is Pillow's `broken data stream`, as in the spike.
4. **Low: a class can empty, and its words must change** (Decision 5). openpyxl's class has one id, `TestImage::test_convert`. If that id fails on JPEG, nothing is left to narrow, and the class leaves with its gap row. A narrowed class keeps a wrong reason ("built with zlib only"). Give it a new id and reason, for example `pillow-no-jpeg2k-or-tiff`: "Pillow is built with zlib and JPEG: a test that needs JPEG 2000 or TIFF's codecs without its own feature guard". Change `not-pillows-wheel`'s reason the same way. The Problem says "six suites": there are six classes in five suites.
5. **Low: the wheel's line before 167's gate** (Decision 8, criterion 9). The binary's growth is measured (+105,224 bytes gzipped). The wheel's +0.2 MB is INFERRED: two binaries' worth, the reactor and the snapshot. No `PYPI_FILE_LIMIT` row is on `dev`. Fix text: "If 167's Part A has not landed, criterion 9's recorded bytes are the line's evidence, and the landing notes give the headroom left for 167 and 169."
6. **Low: the signing key** (Decision 1). Record the key's fingerprint and where it was read.

## Constitution checks

- §4.1: no patch. The 12- and 16-bit copies stay, rightly: removing them would need one.
- §4.12: IJG and BSD-3-Clause, approved on 2026-10-31. The IJG acknowledgement goes on the packages page. The SIMD code's zlib terms are not compiled, so they are not shipped. The header sweep (criterion 2) catches anything else.
- §5.6: the build recipe and the artifact set, reviewed before building. The guest's imports, exports and tags do not change (EXECUTED in the spike, held by two checks).
- The judge: each edit removes or narrows an allowance. A test that fails for a new reason must get its own class, so nothing is hidden. The ids leave, the gap rows leave, and each change is claimed.
- Reproducibility: the fixed `BUILD`, `-ffile-prefix-map` and the x86-64 same-bytes run (criterion 10).
- Structure: nothing under `src/`. Agreed.
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

The author's answers, 2026-10-31. Every finding is taken.

1. **Taken.** Decision 4: the golden is regenerated from the oracle's wheel twice, as it is and with `JSIMD_FORCENONE=1`. The two must be equal. If they are not, the `JSIMD_FORCENONE=1` output is used, with its reason, and goes to the review. No native Pillow build is made. The job prints `features.version("jpg")`. Criterion 5 follows.
2. **Taken.** Decision 2: step 37 holds each recipe header to its template's fixed lines. It names the archive order (`llvm-ar rcD`, the list's order) and the include folders. Criterion 3 names the refusal.
3. **Taken.** Decision 4: the guest makes the broken file itself, from the job's image with one fixed byte of the first DHT segment's code counts overwritten, which the check names. The error is Pillow's `broken data stream`.
4. **Taken.** Decision 5: pypdf's narrowed class takes the id `pillow-no-jpeg2k-or-tiff` and new words. openpyxl's class does the same, or leaves with its gap row if its one id was JPEG's. `not-pillows-wheel`'s reason now says "zlib and JPEG". The Problem now says six classes in five suites.
5. **Taken.** Decision 8: until 167's gate lands, the recorded bytes are the line's only evidence. The landing notes give the headroom left for 167 and 169. The 0.2 MB is marked INFERRED, with its basis.
6. **Taken.** Decision 1 and criterion 1: the key's fingerprint and its source.

## Verdict

Fit to build: no High or Medium. The six Lows are write-ins, and Finding 1's double golden is the one worth taking before the build.

Confirmed after amendments, 2026-10-31 (READ, the amended specification): all six findings are taken as written. Finding 1 is in Decision 4 and criterion 5, 2 in Decision 2 and criterion 3, 3 in Decision 4, 4 in the Problem and Decision 5, 5 in Decision 8, and 6 in Decision 1 and criterion 1. One write-in stays open, for the builder and no new round: when pypdf's class, and openpyxl's if it stays, takes the id `pillow-no-jpeg2k-or-tiff`, its `[[gap]]` row's check id and its `tests/upstream/expected/<group>/` list file are renamed to match. Fit to build.
