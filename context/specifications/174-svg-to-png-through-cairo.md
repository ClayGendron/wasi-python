# 174: SVG to PNG through cairo

- **Status:** drafted 2026-10-31, to be reviewed before it is built (the build recipe and the artifact set). The owner chose "Approve, PNG in 0.1.3" on 2026-10-31 and approved its licences, imageio's that afternoon (decisions.md, "drawsvg, and SVG to PNG through cairo"). Amended against its pre-build review, `../reviews/174-svg-to-png-through-cairo-spec-2026-10-31.md`: every finding taken.
- **Date:** 2026-10-31
- **Owner:** Clay Gendron
- **Kind:** **build-class**, **a judge change**, no carried patch; not structural: nothing under `src/` changes.
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

To be written at the landing.
