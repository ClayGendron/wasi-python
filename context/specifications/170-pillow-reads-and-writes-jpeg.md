# 170: Pillow reads and writes JPEG

- **Status:** drafted 2026-10-31, to be reviewed before it is built (the build recipe). The owner approved the licence on 2026-10-31 (decisions.md, "The decisions of 2026-10-31 morning", on PR #72). Amended the same day against its pre-build review, `../reviews/170-pillow-reads-and-writes-jpeg-spec-2026-10-31.md` ("Fit to build"): its six Lows taken (its Disposition says where). Built 2026-10-31 on `spec/170-pillow-reads-and-writes-jpeg`, with one departure from Decision 2, `JPEG_LIB_VERSION` 62 (the landing notes say why).
- **Date:** 2026-10-31
- **Owner:** Clay Gendron
- **Kind:** **build-class**, **a judge change**, no carried patch; not structural: nothing under `src/` changes. The guest's imports, exports and exception tags do not change (EXECUTED in the spike).
- **Depends on:** landed: 020, 023 (Pillow, zlib only), 063 and 066 (Pillow's own suite), 012 (the same-bytes gate). 166 lands first (CPython 3.15.2, #67), so the measurements are against its binary. 169 also changes the package lists and the tree count; the second to land rebases. 167's Part A brings the wheel's size gate.
- **Research it stands on:** `../research/2026-10-31-pillow-with-jpeg.md` (the spike, EXECUTED: the pin, the build, setjmp under wasmtime, Pillow's tests in the guest, the cost, the licences); `../decisions.md`, "The decisions of 2026-10-31 morning" (the licence; the wheel's interim line). **Drafting reads** (READ, 2026-10-31): the spike's tree, `CMakeLists.txt:653-705` and its three configured headers; `scripts/steps/37_plot_libs.sh`, `55_matplotlib.sh`, `60_link.sh`; `tests/upstream/pillow.toml` and the five other suites' JPEG classes.

Labels: EXECUTED means run and seen; READ means read from a file, cited; INFERRED means reasoned.

## The problem

1. Pillow is built with zlib only (`scripts/steps/55_matplotlib.sh:74-77`). `Image.open` of a photo raises `OSError: decoder jpeg not available`, and `savefig(format="jpg")` fails the same way.
2. Five suites carry six classes for it: `pillow-zlib-only` in Pillow's (55 ids), matplotlib's (two classes, 8 ids), pypdf's and openpyxl's, and scikit-learn's `pillow-zlib-only-at-setup`. Each is a gap in `tests/known_gaps.toml`.
3. The packages page says "JPEG and the other codecs do not" (`docs/reference/packages.md:25`), and the matplotlib how-to says JPEG raises (`docs/how-to/matplotlib.md:23`).

## Decisions

### 1. The pin: libjpeg-turbo 3.2.0, Pillow 13.0.0's own

`libjpeg-turbo-3.2.0.tar.gz` from `https://github.com/libjpeg-turbo/libjpeg-turbo/releases/download/3.2.0/`, 2,537,858 bytes, SHA-256 `6f30092cef9fb839779646608f4ee14ae3cbac989c47fa05e841b0841f09878e` (EXECUTED in the spike). Pillow 13.0.0's `.github/dependencies.json` names this version (READ there). The page gives no hash, so the builder checks the release's signature and records it, with the key's fingerprint and where it was read, in the landing notes. `downloads/SHA256SUMS` and `scripts/00_download.sh` gain it.

### 2. Step 37 builds `libjpeg.a`, without CMake

The build has no CMake, and qhull already shows the pattern (`37_plot_libs.sh:64-79`). So step 37 compiles libjpeg's files directly:

- **The list.** The host Python reads the one `set(JPEG_SOURCES …)` statement from `CMakeLists.txt` (`:653-691`), as step 55 reads Pillow's `setup.py` (`55_matplotlib.sh:57-71`). It appends `src/jaricom.c`, `src/jcarith.c` and `src/jdarith.c`, since arithmetic coding is on by default (`CMakeLists.txt:256-262`, `:695-705`). It stops unless the list holds 101 files, the spike's count. The 88 wrapper files ship in the tarball.
- **The flags.** The spike's, which were measured: `-O2 -DNDEBUG`, the setjmp flags of the cross file (`-fwasm-exceptions -mllvm -wasm-enable-sjlj -mllvm -wasm-use-legacy-eh=false`), and `-ffile-prefix-map`, as qhull's.
- **The configuration.** No SIMD, as no wasm SIMD code exists in the tarball. `JPEG_LIB_VERSION` 80, as Pillow's own Windows build sets `WITH_JPEG8`. No TurboJPEG, tools or tests.
- **Three headers as recipe files.** `recipes/libjpeg-turbo/jconfig.h`, `jconfigint.h` and `jversion.h` are the spike's configured headers. One change: `BUILD` is the fixed string `"wasi-python"`, not CMake's date. `jcmaster.c:807` keeps it in the binary, so a date would break the same-bytes gate.
- **The headers are held to their templates.** Step 37 checks that every line of `src/jconfig.h.in`, `jconfigint.h.in` and `jversion.h.in` without an `@…@` or `#cmakedefine` appears in its recipe header, and stops if one does not. So a later pin cannot keep a stale copy.
- **The output.** The archive is made by `llvm-ar rcD` in the list's order; the include folders are `recipes/libjpeg-turbo` and the tree's `src/`. `build/plot-libs/lib/libjpeg.a`, with `jpeglib.h`, `jerror.h`, `jmorecfg.h` and `jconfig.h` in `build/plot-libs/include/`. The tree stays its tarball, so the tree check covers it. Step 37's archive check (`:84-86`) and size line name it.

### 3. Pillow's `_imaging` links it

In step 55:

- `pil_cc` (`:74-77`) gains `-DHAVE_LIBJPEG`, `-I"$B/plot-libs/include"` and the setjmp flags. Without them, `JpegDecode.c` stops at wasi-libc's `setjmp.h` (EXECUTED). With them it imports `__wasm_setjmp`, `__wasm_setjmp_test`, `__wasm_longjmp` and `__c_longjmp`, which `-lsetjmp` on the `_host` line provides (`60_link.sh:122`).
- `_imaging`'s `.deps` (`:87`) names `libjpeg.a`. Step 55's library check (`:18-20`) names it too.

Step 60 needs nothing new. The weak-duplicate gate reads every archive a `.deps` names (`60_link.sh:98`). The clash detector, the constructor check and the target-feature check run as always. The header comments of steps 37, 55 and 60 say "zlib and JPEG".

### 4. The checks

- **Golden job `jpeg_images`** (v1.3, `tests/jobs/jpeg_images.py`, joining `JOBS` at `tests/harness/jobs.py:33`). A 256 × 192 RGB image is built from numpy arithmetic, so no input file is needed. The job saves it as JPEG with the defaults, at `quality=95`, with `subsampling=0`, `progressive=True` and `optimize=True`, then as `L` and as `CMYK`. Each file's length and SHA-256 are printed, then the SHA-256 of its decoded pixels. `features.version("libjpeg_turbo")` and `features.version("jpg")` are printed first, so a version difference shows as its own line. The oracle's Pillow 13.0.0 wheel uses libjpeg-turbo's SIMD code; libjpeg-turbo's own tests expect SIMD to differ only for the float DCT (`CMakeLists.txt:1067-1130`), and Pillow uses the integer one. So the golden is regenerated twice from that wheel, once as it is and once with `JSIMD_FORCENONE=1` (`simd/jsimd.c:95`). The two must be equal, and the landing notes say so (EXECUTED). If they differ, the golden is the `JSIMD_FORCENONE=1` output, with its reason, and that goes to the review. No native build of Pillow is made.
- **Guest check `test_a_broken_jpeg_raises_and_the_next_decodes`** (v1.3, `tests/checks/test_v1_3_matplotlib.py`). It covers the longjmp path. The guest saves the job's image as JPEG, then overwrites one fixed byte of its first DHT segment's code counts (named in the check); that file raises `OSError: broken data stream when reading image file`, 300 times in a loop. The next good decode then gives the job's pixel hash. In the same guest, `features.check("jpg")` is true and `savefig(format="jpg")` writes bytes that open as a JPEG. Seen failing first on the zlib-only set.
- **Unchanged and held:** `test_imports_are_wasi_and_the_door_only` and `test_the_tag_count_is_even` (`tests/checks/test_v1_1_artifact_set.py:50`, `:67`).

### 5. The suites: the allowances leave

Pillow's `Tests/` already runs whole in the `pillow` group (`tests/upstream/pillow.toml:17-20`). Its JPEG and MPO tests now run as they are: 141 passed and 2 skipped in the spike, and about 195 more passes across the suite (EXECUTED, the spike's harness, not the judge's driver). The allowances leave:

- `pillow-zlib-only` from `pillow.toml:32-38`, with its 55 ids;
- both `pillow-zlib-only` classes from `matplotlib.toml:224-238`;
- `pillow-zlib-only-at-setup` from `scikit-learn.toml:510-516`;
- in `pypdf.toml:42-48`, the match narrows to `(jpeg2k|libtiff)`, the JPEG ids leave, and the class takes a new id and reason: `pillow-no-jpeg2k-or-tiff`, "Pillow is built with zlib and JPEG: a test that needs JPEG 2000 or TIFF's codecs without its own feature guard";
- `openpyxl.toml:78-84` does the same, or, if its one id (`TestImage::test_convert`) failed on JPEG, the class leaves with its gap row;
- the matching `[[gap]]` rows in `tests/known_gaps.toml` leave, or take their new count and digest;
- `not-pillows-wheel` keeps its ids, and its reason now says "zlib and JPEG".

Each edit only removes or narrows an allowance. Each is still a judge change, with this specification as its reason. A test that now fails for another reason gets its own class with its reason, never a wider old one. The `pillow` group's cap is 650 G, with 433 G measured. If it must rise, that is a judge change with this reason.

`tests/upstream/packages.toml` gains `[package.libjpeg-turbo]`, `kind = "via"`, `via = "pillow"`.

### 6. The files of the set and the licence

- `scripts/assemble_artifacts.py`: `PACKAGES` gains `"libjpeg-turbo": "3.2.0"`. `LICENSES/libjpeg-turbo.txt` holds `LICENSE.md` (BSD-3-Clause) and `README.ijg` (the IJG License). The SIMD code's zlib terms are not compiled, so they are not shipped.
- `tests/harness/paths.py`: `LICENCE_COMPONENTS` and `PACKAGES` gain `libjpeg-turbo`, and `MORE_LICENCE` (`:681`) gains `"libjpeg-turbo": "README.ijg"`.
- `tests/harness/pins.py` `SOURCE_PATTERNS` and `tests/harness/needs.py` `SOURCE_COMPONENTS` gain `libjpeg-turbo`.
- `.github/workflows/release.yml`: the tree count, "^28 passed" at `:383`, `:489` and `:588`, rises by one.
- `recipes/snapshot-packages.txt`: `libjpeg-turbo:`, a C library its package's line imports.

### 7. The documents

The IJG License's second condition binds a binary-only distribution: the documentation must say "this software is based in part on the work of the Independent JPEG Group". The packages page says it.

- **Packages page.** Pillow's row (`packages.md:25`) reads "Its core, with zlib and libjpeg-turbo 3.2.0: PNG and JPEG (and MPO) read and write; WebP, TIFF's compressions and JPEG 2000 do not". It carries the IJG sentence. matplotlib's row (`:24`) names JPEG among the formats it saves.
- **The matplotlib how-to.** Lines 22 and 23 say JPEG saves and Pillow's other codecs raise `OSError`.
- **Limitations page.** A line says Pillow has PNG and JPEG only, and its other codecs raise `OSError`.

### 8. Size and fuel

The binary grows by 520,798 bytes stripped, about 105 KB gzipped. The snapshot grows by about the binary's growth (INFERRED). The zip does not grow: the JPEG plugins' `.pyc` files are in it already. `import PIL.Image` costs the same fuel. A decode costs about 280 fuel per pixel (EXECUTED). The wheel grows by about 0.2 MB (INFERRED: the reactor's and the snapshot's growth).

The owner's interim line is 104,857,600 bytes. The wheel is about 100.3 MB with 165 and pandas 3.1.0. With 167's Part A (about 2 MB without plotly), 169 (about 0.5 MB) and this one, it is about 103 MB (INFERRED). The builder records the binary's, the snapshot's and the wheel's bytes. If 167's Part A has not landed, those recorded bytes are the line's only evidence, and the landing notes give the headroom left for 167 and 169. The news file claims each growth and the new upstream passes.

## Intent

A program opens a photo and saves a JPEG, and matplotlib saves `.jpg`, in the guest. The bytes and pixels are native's.

## Design

- Recipe: `downloads/SHA256SUMS`, `scripts/00_download.sh`, `scripts/steps/37_plot_libs.sh`, `scripts/steps/55_matplotlib.sh`, the comment of `scripts/steps/60_link.sh`, `recipes/libjpeg-turbo/` (three headers), `scripts/assemble_artifacts.py`, `recipes/snapshot-packages.txt`.
- Judge: `tests/jobs/jpeg_images.py` and its `.expected`; `tests/harness/jobs.py`, `paths.py`, `pins.py`, `needs.py`; `tests/checks/test_v1_3_matplotlib.py`; `tests/upstream/pillow.toml`, `matplotlib.toml`, `scikit-learn.toml`, `pypdf.toml`, `openpyxl.toml`, `packages.toml` and their `expected/` files; `tests/known_gaps.toml`; `tests/unit/test_artifact_rules.py`'s synthetic set; `.github/workflows/release.yml`'s count.
- Documents: `docs/reference/packages.md`, `docs/reference/limitations.md`, `docs/how-to/matplotlib.md`.

## Scope

In: Decisions 1 to 8. Out: WebP, TIFF's codecs, JPEG 2000, AVIF and Pillow's other libraries; libjpeg-turbo's SIMD (no wasm SIMD code exists); TurboJPEG; dropping the 12- and 16-bit copies, which needs a patch and saves little.

## Acceptance criteria

1. The pin's signature checks, the key's fingerprint recorded (EXECUTED, in the landing notes).
2. Before the pull request opens, the builder sweeps the headers of every compiled file (`Copyright|licen[cs]e`). Any licence beyond IJG and BSD-3-Clause goes to the owner first (EXECUTED, the list in the landing notes).
3. Step 37's list is 101 files, and it stops on any other count, and when a recipe header lacks a line of its template (each refusal seen once).
4. `test_a_broken_jpeg_raises_and_the_next_decodes` is seen failing first on the zlib-only set, and passes on both binaries.
5. `test_jpeg_images_job_matches_native` passes. Its golden is from the oracle (`tests/jobs/regen.py --check`), the SIMD and `JSIMD_FORCENONE=1` outputs equal, or the reviewed fallback of Decision 4.
6. The guest's import list and tag count are unchanged (their checks pass).
7. Pillow's group passes with no `pillow-zlib-only` class, and so do the four other suites with theirs removed or narrowed. Every new expected item names its reason. `test_every_package_names_its_own_suite` passes.
8. `test_source_tree_matches_its_tarball` passes for libjpeg-turbo, and the artifact-set checks pass with its notice, its package line and its `x-snapshot-package` line.
9. The bytes of Decision 8 are recorded, the wheel under 104,857,600 bytes, each growth claimed (EXECUTED).
10. The fast tier, `tests/lint` and the pull request's `ci-status` are green; the x86-64 `same-bytes` run that follows is green.

## Landing notes

Built 2026-10-31 by an agent (Claude Opus 5.5), a builder sub-agent of the orchestrating session, on `spec/170-pillow-reads-and-writes-jpeg` from `dev` at `1c36543d`. The set was built whole in the worktree from the pinned sources (`scripts/build.sh`, every step); the downloads, the oracle's cache and the upstream test kit were copy-on-write clones of 165's worktree, and only libjpeg-turbo's tarball, its signature and its key were fetched, once each. Everything below is EXECUTED on an arm64 Mac (Darwin 25.5.0) unless marked.

**One departure from Decision 2: `JPEG_LIB_VERSION` is 62, not 80.** The oracle's Pillow 13.0.0 wheel (macOS arm64) reports `features.version("jpg")` 6.2: Pillow's macOS and Linux wheels build libjpeg-turbo with its default libjpeg v6b API, and only its Windows build sets `WITH_JPEG8` (`winbuild/build_prepare.py:143`, READ). With 80 the golden's version line would differ from the oracle's on every host the oracle runs on (macOS arm64 and Linux; it has no Windows host). Pillow uses `JPEG_LIB_VERSION` only to print that version (`JpegEncode.c:410`), and in libjpeg-turbo the v7/v8 paths set fields its code does not read for 8×8 DCT (`do_fancy_downsampling` is set and never read; the scaled sizes equal `DCTSIZE`), so the bytes and pixels do not depend on it (INFERRED from the sources; the golden's hashes equal the oracle's with 62). `recipes/libjpeg-turbo/jconfig.h` is CMake's default configuration (`WITH_JPEG8=0`); the other two headers are the same either way. The reviewer is asked to confirm.

**Pin** (criterion 1): `libjpeg-turbo-3.2.0.tar.gz`, 2,537,858 bytes, SHA-256 `6f30092c…09878e`, the spike's. Its detached signature (`libjpeg-turbo-3.2.0.tar.gz.sig` on the same release page, 566 bytes) verifies (`gpg --verify`, "Good signature", made 2026-06-30) with the key 0338 C8D8 D9FD A62C F9C4 21BD 7EC2 DBB6 F4DB F434, "The libjpeg-turbo Project (Signing key for official binaries) <information@libjpeg-turbo.org>", rsa4096 of 2020-11-12, read from `https://raw.githubusercontent.com/libjpeg-turbo/repo/main/LJT-GPG-KEY` in a scratch keyring. The key is not certified by any key we trust; its fingerprint is the record.

**Licence sweep** (criterion 2): the compiler's own dependency list (`clang -MM` over the 101 files) names 157 files: 135 `.c` (the 101 and the files the wrappers include), 19 headers from the tarball and the three recipe headers. Every one of the 155 tarball files says "For conditions of distribution and use, see the accompanying README.ijg file"; the copyright holders are the IJG authors, D. R. Commander and contributors (Google, Linaro, Arm, Cendio and others) under those terms. The two configured headers carry no notice; their templates are under `LICENSE.md`'s BSD-3-Clause. No licence beyond IJG and BSD-3-Clause; the SIMD code (zlib terms) is not compiled.

**Step 37** (criterion 3): the list is the 98 files of `set(JPEG_SOURCES …)` and the three arithmetic files, 101; `libjpeg.a` 630,046 bytes, no warning from its 101 compiles. Each refusal seen once with the step's own checker: one file dropped from the list ("100 source files, not the 101 this recipe was made for"), and a recipe header without one template line ("recipes/libjpeg-turbo/jconfig.h lacks a line of its template: '#define MEM_SRCDST_SUPPORTED  1'"), the second also by `scripts/build.sh 37` itself, which stopped there. Step 55 gave only the `_XOPEN_SOURCE` warning `pyconfig.h` always gives; step 60's gates passed unchanged.

**The golden** (criterion 5): `jpeg_images` run under the oracle twice, as the wheel is and with `JSIMD_FORCENONE=1`; the two renders are equal byte for byte (SHA-256 `221f9939…f6f0`), so the golden is the wheel's output with no fallback. Its lines: libjpeg-turbo 3.2.0, API 6.2; six files (6,530, 14,130, 10,231, 6,209, 4,261 and 11,899 bytes) and their decoded pixels. `test_jpeg_images_job_matches_native` passes: the guest's plain C build gives the same bytes and pixels.

**Seen failing first** (criterion 4): on 165's set (zlib only), `test_jpeg_images_job_matches_native` and both cases of `test_a_broken_jpeg_raises_and_the_next_decodes` fail with "OSError: encoder jpeg not available". On this set they pass, plain and snapshot: 300 broken decodes each raise "broken data stream when reading image file" and the next decode gives the job's pixels. `features.check("jpg")` is true; `savefig(format="jpg")` writes a 200×150 JPEG. In the guest, TIFF saves uncompressed and WebP raises `KeyError`, as the pages now say.

**Held** (criterion 6): `test_imports_are_wasi_and_the_door_only` and `test_the_tag_count_is_even` pass. **Trees** (criterion 8): the 31 `test_source_tree_matches_its_tarball` rows pass, libjpeg-turbo's among them; `LICENSES/libjpeg-turbo.txt` holds `LICENSE.md` and `README.ijg`, and `release/licences.py check` passes on the wheel.

**The suites** (criterion 7), each run in the guest by the judge's driver on this set: pillow 4,792 passes (4,593 accepted), 605.1 G; matplotlib-render-2b 395 (392), 337.0 G; matplotlib-rest-a 971 (966), 314.8 G; scikit-learn-datasets 360 (356), 90.9 G; pypdf-r 1,703 (1,695 after 166), 358.8 G; openpyxl-r 2,143 (the same), 63.2 G. Every remaining class matches its gap. Of the six JPEG classes, four emptied and leave with their gaps; pypdf's keeps four tests (JPEG 2000 and CCITT/TIFF) and openpyxl's its one (a compressed TIFF), each under `pillow-no-jpeg2k-or-tiff`, with the gap row's id and the list file renamed to match (the review's write-in). No test failed for a new reason. The pillow group grew 39.8%, so its cap moved from 650 G to 910 G and scikit-learn-datasets' from 99 G to 140 G, each 1.5 times its new measure; `upstream-plot-b` would have measured 893.9 G, so matplotlib-render-3 moved to `upstream-plot-i` (621.1 G and 683.4 G, under the shards' 725 G).

**Size and fuel** (criterion 9), against dev's set (165's worktree, the same bytes as `dev`): `python.wasm` 99,492,553 → 100,012,947 bytes (+520,394, the spike's +520,798 within 404); `python-snapshot.wasm` 104,660,252 → 105,184,822 (+524,570); the zip unchanged, 54,960,042. **The wheel**, built by hand from each set as the release job builds it: 99,478,846 → 99,687,768 bytes (+208,922). It is 5,169,832 under 104,857,600. 167's Part A (its size gate) has not landed, so these bytes are the line's evidence: the headroom left for 167 and 169 together is 5,169,832 bytes, against their estimates of about 2 MB and 0.5 MB. Fuel outside JPEG does not move: the 136 fast-tier fuel rows of five product files, run on both sets, differ by -0.19% to +0.14% (median -0.007%); a plain start 277,790,133 to 277,713,412 and a snapshot start 54,380,360 to 54,373,605. The rest of what the fast tier lists against the last acceptance is 165's zip.

**Local runs at the head**: `ruff check` and `ruff format --check` clean; `uv run pytest tests/lint` green; the fast tier green but the prior-art row (blocked) and the growths the news file claims. The run of the pull request and the x86-64 `same-bytes` run are named here when they are read.
