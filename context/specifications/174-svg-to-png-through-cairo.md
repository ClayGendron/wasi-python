# 174: SVG to PNG through cairo

- **Status:** drafted 2026-10-31, to be reviewed before it is built (the build recipe and the artifact set). The owner chose "Approve, PNG in 0.1.3" on 2026-10-31 and approved its licences, imageio's that afternoon (decisions.md, "drawsvg, and SVG to PNG through cairo"). Amended against its pre-build review, `../reviews/174-svg-to-png-through-cairo-spec-2026-10-31.md`: every finding taken.
- **Date:** 2026-10-31
- **Owner:** Clay Gendron
- **Kind:** **build-class**, **a judge change**, one carried patch (CairoSVG's, found at the build; the landing notes); not structural: nothing under `src/` changes.
- **Depends on:** 173 first. 169, 170 and 171 share files; the later rebases (171's `--metadata …=<name>` form). 167 brings the size gate.
- **Research it stands on:** `../research/2026-10-31-drawsvg-and-svg-to-png.md`.

Labels: EXECUTED run; READ read, cited; INFERRED reasoned.

## The problem

1. drawsvg cannot rasterize (173); PNG needs a C renderer, and cairo is CairoSVG's (the memo, §3).
2. cairocffi uses `ffi.dlopen` (`cairocffi/__init__.py:60`) and `ffi.callback` (`surfaces.py:30`, `:45`, `:117`); the guest has neither `dlopen` nor libffi.
3. Without fontconfig, cairo draws every family in its stroke font, twin.

## Decisions

### 1. The pins

In `downloads/SHA256SUMS`, each hash EXECUTED in the spike:

- `pixman-0.46.4.tar.xz` and `cairo-1.18.6.tar.xz` from `https://www.cairographics.org/releases/`: `a098c33924754ad43f981b740f6d576c70f9ed1006e12221b1845431ebce1239`, `1c767308174337a74694da0f3ec069c271452163a1ef4540964c50c301f157d4`.
- `libpng-1.6.59.tar.xz` from SourceForge: `d80dd2a38a37f803cb9b6ac7b14bd6e74ddc3b654780a8380bdf93523fdb4389`. Unpublished hash: the builder checks its signature.
- cffi 2.1.1's sdist; its cp315 wheels for the build hosts as `<HOST>_CFFI_WHEEL` lines in `scripts/line.conf`, and pycparser's wheel (Decision 5).
- The sdists of cairocffi 1.7.1 (`2e48ee864884ec4a3a34bfa8c9ab9999f688286eb714a15a43ec9d068c36557b`) and CairoSVG 2.9.1; the wheels of tinycss2 1.5.1, cssselect2 0.10.1 and imageio 2.38.1 (`36d23eb7423d2fb63f637098758edb3d2df3687f7125e0a5ce8596572022dcf9`).

### 2. Step 39 builds the three libraries

`scripts/steps/39_cairo_libs.sh`, in step 37's shape, into `build/cairo-libs/`; meson runs with `-Dauto_features=disabled`, so nothing a host gains later switches on.

- **pixman:** no SIMD, tests or demos. After `meson setup`, the step deletes the `TOOLCHAIN_SUPPORTS_ATTRIBUTE_CONSTRUCTOR` and `_DESTRUCTOR` lines from the generated `config.h` (the build folder's, not the tree's), so pixman picks its implementation on first use (`pixman-private.h:817-825`). The step stops if either line is absent before or present after. The constructor check (`tests/harness/constructors.py:32`) holds; the golden job, every image composited by pixman, proves it works.
- **libpng:** compiled file by file with the tarball's `scripts/pnglibconf.h.prebuilt`, SIMD off; `libpng16.pc` from `recipes/libpng16.pc.in`, as `qhull_r.pc.in`.
- **cairo:** `freetype`, `png` and `zlib` on; only `src/libcairo.a` is built.

`recipes/wasi-cairo.cross` is `wasi-plot-libs.cross` plus `build/cairo-libs/lib/pkgconfig`, with `ttx` pointed nowhere, as `cmake` is.

### 3. `tmpfile` is refused

Only cairo's PostScript surface calls `tmpfile`, which wasi-libc lacks. `recipes/tmpfile_refusal.c` returns `NULL` with `ENOTSUP`, inside `_cairocffi_api`'s archive, since step 60's guards (`:162`) reach the reactor only. `PSSurface` raises `CairoError`. A working one would need a writable folder (§4.15).

### 4. `_cffi_backend` is built in, over a libffi stand-in

`recipes/libffi_stand_in/` (about 65 lines) defines libffi's types. `ffi_prep_cif` succeeds, so `ffi.def_extern` works; `ffi_closure_alloc` returns `NULL`, so `ffi.callback` raises `MemoryError`; `ffi_call`, reached only by a function-pointer call no shipped package makes, aborts. Step 56 (`scripts/steps/56_cairocffi.sh`) compiles `src/c/_cffi_backend.c` with `-D_WASI_EMULATED_MMAN` for `gen_inittab.py` (`60_link.sh:52`). cffi's Python package stays out.

### 5. The binding is generated at build time

`recipes/cairo_build.py`, on the build host, takes cairocffi's `constants._CAIRO_HEADERS`, cut before the Windows and Quartz sections, adds Decision 6's trampolines and `wasi_cairo_ft_face_from_memory` (a face from a font's bytes), and writes `_cairocffi_api.c` in API mode. Step 56 compiles it, its `.deps` naming the three archives.

### 6. A stand-in `cairocffi/ffi.py`, not a patch

cairocffi comes from its sdist, staged as python-docx is (`70_zip.sh:104`): step 70 copies `cairocffi/` into `$B/pure-install/` without `ffi.py` and its four `test_*.py` files, then copies `recipes/cairocffi_ffi_stand_in.py` in as `ffi.py`. **The step's rule:** each left-out file must exist in the sdist, and the staged folder differs from the sdist's by exactly those five and the stand-in, or the step stops. No `--file` or `--drop` is involved. CairoSVG is staged the same way, without `test_api.py`. Neither comes from a wheel, so each takes a `--metadata` line from its sdist's `PKG-INFO`: `"$B/cairocffi-1.7.1/PKG-INFO"` and CairoSVG's beside it, each with `=<names>` once 171's rule is on `dev` (`=cairocffi`, `=cairosvg`).

The stand-in's `ffi` is `_cairocffi_api.ffi` with two methods replaced:

- **`dlopen`** returns `_cairocffi_api.lib` when the name's basename is cairo's (`__init__.py:41-47`), with `cairo_select_font_face` overridden (Decision 7) and other names bound once; any other raises `OSError`, as does `ffi_pixbuf.dlopen`.
- **`callback`**, in decorator and direct form, takes a slot from a pool of static `extern "Python"` trampolines, 128 for each of cairo's read, write and destroy types, keeping its `error=` and `onerror=`. A slot frees when cairocffi drops its pointer. A full pool runs `gc.collect()` once and retries, then raises `MemoryError` naming the cap. Another type raises `NotImplementedError`.

The destroy pool also caps buffer surfaces (`surfaces.py:731`) and `set_mime_data` (`:508`). Step 56 stops if the pinned `ffi.py` binds a module-level name the stand-in lacks, or an `ffi.callback(` type is not one of the three.

**Why not the patch.** The spike's patch ran, but §4.1 takes a recipe file first, and it would never be temporary: cairocffi binds in ABI mode by design. After two failures on one hypothesis, it returns as a reviewed amendment.

### 7. A font map over matplotlib's DejaVu fonts

The override sets a FreeType face for the family (CairoSVG passes the first, `cairosvg/text.py:54-66`), ignoring case:

- `@cairo:` families go to cairo untouched (cairocffi's `test_cairo.py:1069-1073`).
- `DejaVu Sans`, `DejaVu Serif` and `DejaVu Sans Mono` map to their own files; `serif`, `times`, `times new roman` and `georgia` to DejaVu Serif; `monospace`, `courier` and `courier new` to DejaVu Sans Mono; any other to DejaVu Sans.
- Bold takes Bold; italic or oblique takes Oblique, or Italic for Serif.

The set's `mpl-data/fonts/ttf/` holds all twelve (EXECUTED: listed). The map finds them through `importlib.util.find_spec("matplotlib")`, without importing it, in the folder the runner grants (`src/wasi_python/_zip.py:22-30`); without the grant, from the zip's `matplotlib/mpl-data.zip` member; else cairo's own selection runs. Each face is built once and keeps its bytes alive, since FreeType reads them in place.

### 8. The other packages

imageio writes drawsvg's GIFs (`video.py:5-15`) through its Pillow plugin and requires only numpy and Pillow (READ). Its plugins needing a binary or a missing package (ffmpeg, PyAV, FreeImage, OpenCV, GDAL…) fail by name.

### 9. CairoSVG ships as Python source

`scripts/make_stdlib_zip.py` gains `--source <folder>`: that folder's `.py` files are packed beside their `.pyc`. zipimport takes the `.pyc` first, so import costs no more. Step 70 uses it for `cairosvg` alone.

### 10. The licences, each text shipped

Each is a `LICENSES/<name>.txt`; `tests/harness/paths.py`, `pins.py` and `needs.py` gain the names.

- **cairo:** `COPYING` and `COPYING-MPL-1.1`, not LGPL-2.1's text; a first paragraph names the unmodified tarball's URL and SHA-256 (MPL-1.1 §3.6); then the MIT-style notices the sweep finds.
- pixman, libpng, cairocffi, tinycss2, cssselect2, imageio: each its own file.
- **cffi:** MIT No Attribution, more permissive than MIT and so within the approval; `malloc_closure.h` is CPython's, under the PSF licence already shipped.
- **CairoSVG:** LGPL-3.0, and GPL-3.0's text from a pinned file, then the facts below.

**How CairoSVG can be replaced.** It is imported by name (drawsvg's `raster.py:9`), never linked. A program or setup code grants a folder with a modified CairoSVG through `import_path` and moves it ahead of the zip on `sys.path` before CairoSVG's first import. `make_package_snapshot()` imports every `x-snapshot-package` name (`src/wasi_python/_snapshot_make.py:197-208`), so such an image leaves CairoSVG out with `packages=`, or moves the path in its code. The source is in the zip and at its pinned URL; the recipe rebuilds the zip. The notice names the clauses these facts concern (GPL-3.0 §6(d), LGPL-3.0 §4(d)(1)) and makes no claim that any of them is met.

### 11. The checks

- **Golden job `svg_to_png`** (`tests/jobs/svg_to_png.py`, platform-bound). Its native side is `tests/jobs/oracle/cairo_native.sh`: pixman, libpng, cairo, FreeType and zlib from their pins with steps 37's and 30's options, by the host compiler with SIMD off and `-ffp-contract=off`, `_cairocffi_api` from the same `cairo_build.py`, and the oracle's CPython with the stand-in. It prints the host compiler's version, then each image's size and RGBA SHA-256:
  - 173's README drawing through `svg2png` (400 × 200) and `rasterize()`;
  - text: the generic families and three DejaVu names, bold and italic, 12 and 40 px;
  - gradients, opacity, clipping, a mask, dashes, markers, an embedded PNG;
  - cairocffi directly: arcs, curves, a radial gradient, a PNG stream round trip;
  - `svg2pdf`'s page count, media box and text, through pypdf;
  - drawsvg's three-frame `save_gif`: frame count and pixel hashes.

  **Exact pixels.** Both sides run the same C and Python, and wasm contracts nothing. One difference is left: native libm against wasi-libc's, in trigonometry and gradients (INFERRED rare; `plot_contour` matches native Agg exactly). A differing line records its count and largest channel difference; at most 1 is admitted only as a claimed judge change, reason libm; more is a bug. PNG bytes are left to the same-bytes gate.
- **`test_cairo_text_is_drawn_in_dejavu`** (`tests/checks/test_v1_3_drawing.py`). "Hg" at 40 px through `select_font_face("sans-serif")` equals an explicit DejaVu Sans face made from its bytes, and differs from `@cairo:sans-serif` (twin); serif bold and monospace italic likewise.
- **`test_cairo_names_what_it_cannot_do`** (same file): `PSSurface` raises `CairoError`; the 129th live stream surface and the 129th `ImageSurface` over a buffer raise `MemoryError`, and a new one works once they drop; a function-pointer call traps and a new instance runs; a granted CairoSVG moved first on `sys.path` is imported.
- **173's:** `rasterize()` returns PNG bytes; drawsvg's `checked_by` gains `svg_to_png`.
- **Own suites (063, 067).** A survey, then five configurations from pinned sources, smoke groups in the normal tier, whole suites in the release tier. CairoSVG's reference images come from its `2.9.1` tag archive; imageio's from `imageio/test_images`' archive at one pinned commit, staged as `.test_images`, run with `-m "not needs_internet"`. cairocffi's `test_cairo.py` imports pikepdf at its top: a test-side stand-in lets it collect, and its callers form one expected class, `no-pikepdf`. `packages.toml`: `cairo`, `pixman`, `libpng` and `cffi` are `via = "cairocffi"`. `tests/release_shards.toml` takes the drawing checks (three systems) and the groups.
- **Held:** the import, tag, constructor, target-feature and snapshot checks (`tests/checks/test_v1_1_artifact_set.py:50`, `:67`).

### 12. The rest of the set

- `recipes/snapshot-packages.txt`: `cffi: _cffi_backend`, empty lines for the three C libraries, one line per package.
- `.github/workflows/release.yml`: the tree count rises by the new trees.
- **Documents:** the packages page gains the five packages, and drawsvg's row names PNG and GIF; `packages.md:91` gains that a program may move a granted folder ahead of the zip before a first import. The limitations page takes Decision 13.

### 13. What stays impossible, or differs

MP4 (imageio-ffmpeg runs a process); imageio's binary plugins; cairo's PostScript; Arabic or Indic shaping; fonts but DejaVu; over 128 live surfaces of one callback kind; `ffi.callback`; gdk-pixbuf; `drawsvg.color`; until 170, an embedded JPEG. `as_gif()` with no file opens a temporary file (`drawsvg/video.py:42-45`): pass a writable path or an `io.BytesIO`. A mapped `get_font_face()` is a `FontFace`, not a `ToyFontFace`; `ToyFontFace("serif")` draws twin; `"Inconsolata, monospace"` draws in DejaVu Sans.

### 14. Size and fuel

The binary grew by 1,849,567 bytes stripped in the spike (EXECUTED), plus trampolines. The zip gains about 150 members, about 4 M fuel on every plain start, 1 % (INFERRED; the spike read them from a grant). The builder weighs dropping imageio's plugins that cannot run (then `ModuleNotFoundError`), records every artifact's bytes and the fuel of a plain start, `import cairosvg` and one `svg2png` (about 220 M), and claims each growth. 167's `PYPI_FILE_LIMIT` gate holds.

## Intent

A program in the guest turns any SVG, or any drawsvg drawing, into a PNG, a PDF or an animated GIF with real fonts, and gets native's pixels.

## Design

The files Decisions 1 to 12 name, with `tests/release_shards.toml` and `tests/unit/`.

## Scope

In: Decisions 1 to 14. Out: Decision 13's list; fontconfig; resvg (0.1.4); pixman's and cairo's C test suites.

## Acceptance criteria

1. libpng's signature checks, its key's fingerprint and source recorded; the licence sweep finds nothing beyond Decision 10, or the owner is asked (EXECUTED).
2. `test_svg_to_png_job_matches_native` passes with exact pixels, or with Decision 11's claimed libm allowance.
3. The two drawing checks are seen failing first and pass on both binaries.
4. Imports, tags and constructors are unchanged; step 39's edit and step 70's rule each refuse once, seen.
5. The five suites pass, every expected class reasoned; `test_every_package_names_its_own_suite` passes.
6. The tree, notice and package-line checks pass; the zip's `cairosvg/*.py` equal the sdist's.
7. Decision 14's bytes and fuel are recorded and claimed, under the PyPI limit then in force (EXECUTED).
8. The fast tier, `tests/lint`, `ci-status` and the next x86-64 `same-bytes` run are green.

## Landing notes

### The first pull request

Built 2026-10-31 by an agent (Claude Opus 5.5), a builder sub-agent of the orchestrating session, on `spec/174-svg-to-png-through-cairo`, first on `dev` at `863c2929` (the whole set built from the pins, `scripts/build.sh`, every step), then rebased onto `dev` at `59013cf3` once 171 (#78) merged, steps 70 to 90 rebuilt over it. Everything below is EXECUTED on an arm64 Mac (Darwin 25.5.0) unless marked. Rebased again onto `dev` at `9c0d879e` once 166's second pull request (#71, pandas 3.1.0), 173 (#86, drawsvg) and 177 (#87, the ledger a file per pull request) merged, the whole set rebuilt from the pins: this pull request's claim block moved to `../release-claims/174-svg-to-png-through-cairo.toml`, `cairo_native.sh` follows step 30's zlib 1.3.2, and drawsvg's lines joined (below).

**Pins** (Decision 1, criterion 1). Every hash is the spike's and PyPI's or cairographics.org's. **libpng's signature:** the tarball has no signature file (SourceForge lists none for 1.6.59; its published SHA-256 is the pin's). Its 614 files are each byte-equal to the tree of the signed tag `v1.6.59` of `github.com/pnggroup/libpng` (commit `cd952f49f95bb27154ae77dbb103032d95f6e580`), and `git verify-tag v1.6.59` reports a good signature from EDDSA key `1FED507E3236B4A6E53E922BB292C64843FF5BCF` (Cosmin Truta), the key fetched from `https://github.com/ctruta.gpg` (keys.openpgp.org has none). cffi's three cp315 host wheels are `<HOST>_CFFI_WHEEL` lines in `scripts/line.conf`, with pycparser 3.12's pure wheel; step 56 installs them offline with their hashes into `build/cffi-host/`. imageio's test images are pinned at `imageio/test_images` `f676c96b` (195,639,504 bytes, a test source). GPL-3.0's text is pinned from SPDX's list at the commit MPL-2.0's already is.

**What differs from the specification as written**, each found at the build:

1. **CairoSVG carries one patch** (the specification said none). `cairosvg/__init__.py` reads its `VERSION` file by a path made from `__file__`, which names no file inside the zip, so `import cairosvg` raised before anything ran (the spike had imported CairoSVG from a grant). No recipe file can change a module's own first statements short of replacing the module, so the change is `recipes/patches/cairosvg-2.9.1/0001-read-version-through-the-package-loader.patch` (the frozen branches untouched; the plain branch reads the same file through `importlib.resources`), with its pull request drafted under `../upstream/patches/cairosvg-2.9.1/`. The zip's `cairosvg/*.py` are therefore the sdist's plus that patch (criterion 6), and the README's count of carried patches is 31.
2. **CairoSVG's non-regression suite is not run** (Decision 11 named its "reference images from its tag archive"). The tag archive holds no reference images: the suite compares 2.9.1 with an older CairoSVG from a git submodule. And the archive's top folder, `CairoSVG-2.9.1`, is the sdist's `cairosvg-2.9.1` on a case-insensitive file system, where unpacking it overwrote the patched tree. CairoSVG's suite is its sdist's `cairosvg/test_api.py`, which its README calls its deployment tests; the golden job covers its rendering against native cairo.
3. **pixman's generated header is `pixman/pixman-config.h`**, not `config.h`; step 39 deletes the two lines there and stops on either line's state (seen refusing once with a line removed first: "has no '#define TOOLCHAIN_SUPPORTS_ATTRIBUTE_DESTRUCTOR 1' to delete"). The constructor list is unchanged: "159 reviewed, none new" (criterion 4).
4. **`PSSurface` raises `OSError`**, not `CairoError`: cairocffi maps `CAIRO_STATUS_TEMP_FILE_ERROR` to `IOError`. A run-time `ffi.callback` of the real backend raises `MemoryError` ("Cannot allocate write+execute memory"), as Decision 4 says; the stand-in `ffi.py`'s own `callback` never reaches it.
5. **The callback pool, found at cairocffi's `test_target_lifetime`:** cffi keeps the function an `extern "Python"` slot last ran until the slot runs again, so a freed slot kept its file object alive. A freed slot is now given an idle function and run once from C (`wasi_cairo_run_slot`, in `recipes/cairo_build.py`; a call from Python would go through `ffi_call`, which traps), and the test passes. cffi gives `cairo_read_func_t` and `cairo_write_func_t` one C type (it ignores `const`), so the pools are found by the name cairocffi passes.
6. **An `ImageSurface` over a buffer** works for an `array.array` only: cairocffi takes a `bytearray`'s or numpy array's address through `ctypes`, which the guest's stand-in cannot give. The check's 129th buffer surface uses `array.array`; the limitations page says so.
7. **The smoke bounds rise** (`tests/harness/packages.py`, a judge change): a test-source smoke group from 100 G to 110 G, and their total from 1 T to 1.2 T. tinycss2's tests are one file, 105.9 G whole, and a smoke family splits its tiers by path only (a node id cannot be a smoke path, and `--deselect` would also take every test whose name begins with the node's), so the whole file is its smoke group; the five new families' smoke groups measure 201.3 G together, beside the 969.7 G before.
8. **A harness key for test-side stand-ins** (`tests/harness/packages.py`, `test_stand_ins`): a module a test file imports that has no build here, staged from `tests/upstream/stand-ins/` into the family's kit only, never naming a module the product's zip carries. Two exist: `pikepdf`, which `test_cairo.py` imports at its top (its five users form the class `no-pikepdf`), and `pytest_cache_stand_in`, a session cache for imageio's `test_images` fixture, which reads `config.cache` (the driver runs pytest without its cache plugin) and would otherwise try to make its folder in the read-only stage.

**The licence sweep** (criterion 1), each compiled C file's leading comment and each package's files: cairo's library files are each LGPL-2.1 or MPL-1.1 but eight under MIT-style terms (`cairo-clip-tor-scan-converter.c`, `cairo-freelist.c`, `cairo-mono-scan-converter.c`, `cairo-pattern.c`, `cairo-spans.c`, `cairo-time.c`, `cairo-tor-scan-converter.c`, `cairo-tor22-scan-converter.c`; `cairo-font-face-twin-data.c` points to `cairo-font-face-twin.c`, MPL-1.1 or LGPL-2.1), whose notices ship. pixman: its MIT `COPYING`, and the X11-style notice heading 26 of its compiled files, each shipped. libpng: its PNG Reference Library License v2; its `LICENSES/MIT*.txt` cover CI scripts only, none compiled. cffi: MIT No Attribution, and `src/c/malloc_closure.h`, CPython's, under the PSF licence `LICENSES/cpython.txt` holds. cairocffi, tinycss2, cssselect2: BSD-3-Clause; imageio: BSD-2-Clause; CairoSVG: LGPL-3.0-or-later. Nothing beyond Decision 10 and the owner's approval of 2026-10-31. `LICENSES/cairo.txt` opens with the MPL-1.1 election and the unmodified tarball's URL and SHA-256; `LICENSES/cairosvg.txt` carries its LGPL-3.0, GPL-3.0's text and the facts of Decision 10, claiming nothing.

**Seen failing first** (criterion 3). `test_cairo_text_is_drawn_in_dejavu`: in the guest with the font map undone (`cairo_select_font_face` put back to cairo's own), each family printed `False False`, its text neither the DejaVu face's nor different from the stroke font's. `test_cairo_names_what_it_cannot_do`: before the stand-in, cairocffi could not be imported (its `ffi.dlopen` loads nothing), and at its first run the stream-surface pool held its last file (the lifetime fault above). `test_svg_to_png_job_matches_native` was written before its golden existed. Step 70's staging rule refused once with a left-out name the sdist lacks ("has no test_renamed.py to leave out").

**The golden** (criterion 2): exact pixels, no allowance. `tests/jobs/oracle/cairo_native.sh` built zlib, FreeType 2.14.3, pixman, libpng and cairo with Apple clang 17.0.0 (`-O2 -ffp-contract=off`, SIMD off) and `_cairocffi_api` from the same generator; the oracle ran the job twice (hash seeds 0 and 1, the same), and the guest's output equals it on both binaries: six images' RGBA SHA-256, the PNG round trip and the PDF's page, media box and text. libm left no difference.

**Own suites** (criterion 5), on the set at the head: cairocffi-smoke 40 passes, 14.1 G, with 7 expected (5 no-pikepdf, 1 ctypes address, 1 PostScript); cairocffi-r 11.1 G (`test_numpy.py`'s one test in the ctypes class; `test_xcb.py` skips without xcffib; `test_pixbuf.py` not selected); cairosvg-smoke 6 passes, 16.3 G, its PS format expected; tinycss2-smoke, the whole file, 16,968 passes, 105.9 G; cssselect2-smoke 446 passes, 18.0 G; imageio-smoke 40 passes, 47.0 G, with 6 expected; imageio-r 100 passes, 275.0 G, with 31 expected in seven classes. Natively (CPython 3.15.2, the oracle's Pillow 13.0.0 and numpy 2.5.4), imageio's suite is 178 passed and 2 failed, the two `Invalid mode for data type` tests the guest classes as failing natively.

**Size and fuel** (criterion 7), against `dev`'s set at `a0f3e3b5`: `python.wasm` 99,497,353 → 101,418,432 bytes (+1,921,079, +1.93%); `python-snapshot.wasm` 104,890,482 → 106,847,177; the zip 57,068,536 → 57,952,950 (+884,414), 6,721 → 6,840 members; a plain start (`-c pass`) 283,812,271 → 286,621,212 fuel (+0.99%), a snapshot start 54,767,956 → 55,037,375 (+0.49%). `import cairosvg` 1,336,882,526 fuel plain and 974,906,914 from the snapshot; one 400 × 200 `svg2png` about 149 M more. **The wheel**, built by hand as the release workflow builds it: **103,722,443 bytes**, 1,135,157 under PyPI's 104,857,600. imageio's plugins that cannot run here stay: dropping them would save few members and turn each named failure into a `ModuleNotFoundError`.

**drawsvg's PNG and GIF** (Decision 11, after 173). The golden gains drawsvg's README drawing through `svg2png` and through `rasterize()` (the same 400 × 200 pixels), and three frames written to a GIF by drawsvg's `save_video` through imageio and Pillow: its frame count and each frame's RGBA SHA-256, equal to the oracle's (the oracle's `drawsvg==2.4.2` beside the native cairo). drawsvg's `checked_by` gains `svg_to_png`. 173's `test_drawsvg_names_what_the_set_lacks` now expects `rasterize()` to return PNG bytes (`89504e470d0a1a0a`), not `ImportError` naming cairosvg; it failed on this set until changed, and passes on both binaries. The limitations and packages pages say drawsvg writes PNG and GIF, not video.

**The wheel after the rebase**, built by hand as the release workflow builds it on the set at `9c0d879e` plus this change: **104,677,500 bytes, 180,100 under PyPI's 104,857,600**. dev's own wheel grew with pandas 3.1.0 and drawsvg; a further pull request that adds bytes may pass the limit before PyPI raises it.

**The rebase onto `da830491`** (175 and 176, #89; 170, #80, Pillow with JPEG), the whole set rebuilt from the pins. The tree count in `release.yml` is 39 (dev's 33 with libjpeg-turbo's, and this change's six). With JPEG in the set, imageio's three JPEG classes emptied and are removed (`imageio-smoke-no-jpeg`, `imageio-r-no-jpeg`, `imageio-r-no-jpeg-plugin`), and the limitations line on CairoSVG's embedded JPEG goes. The two `.jpg` tests the last of them held still fail, for other causes, each EXECUTED: `test_plugin_selection_success[.jpg]` fails natively too in pytest's importlib import mode, which the driver uses (class `importlib-module-names`); `test_imopen_extension_malformatted[.jpg]` sends an unknown extension hint into imageio's FreeImage plugin, which raises the ctypes stand-in's `OSError` where natively a `UserWarning` is given (class `no-ctypes-warning`). **The callback scan** (`tests/harness/callbacks.py`, a judge change): after this rebase `test_callbacks_have_the_types_cpython_calls` failed on a getter `tag_name` at table index 3. It is cairo's tag-attribute table, `{"tag_name", ATTRIBUTE_STRING = 3, 0}, {"id", 3, 0}` (`cairo-tag-attributes.c`), read as a `PyGetSetDef`; 176's reactor now puts its start-up allocator (`skipping_calloc`) at index 3, where a two-parameter function sat before. The scan already skips a single method definition whose function at index 1 to 20 is named a parser rule; it now skips a getset entry the same way, and counts the reactor's `skipping_*` functions among those names. No exclusion is added (`EXCLUDED` stays empty). imageio-smoke now 45 passes, 47.6 G; imageio-r 106 passes, 295.1 G, with 25 expected in seven classes. The golden, the drawing checks, 173's two rows and the smoke groups pass on the rebuilt set. **The wheel**, built by hand as the release workflow builds it: **104,899,641 bytes**, 42,041 over the old 104,857,600; the wheel check's limit rises to 256 MiB with #91.
