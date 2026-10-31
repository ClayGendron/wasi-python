# 170: Pillow reads and writes JPEG

- **Status:** drafted 2026-10-31, to be reviewed before it is built (the build recipe). The owner approved the licence on 2026-10-31 (decisions.md, "The decisions of 2026-10-31 morning", on PR #72). Amended the same day against its pre-build review, `../reviews/170-pillow-reads-and-writes-jpeg-spec-2026-10-31.md` ("Fit to build"): its six Lows taken (its Disposition says where).
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

To be written at the landing.
