# drawsvg, and SVG to PNG through cairo: a spike

- **Status:** research, 2026-10-31. The owner asked "can we Add drawsvg to 0.1.3?", then, of its PNG output: "If it makes sense to add all the dependancies in, then I want to do it, it it provides minimal value, then don't. I want to be able to create high quality images, animations, interactive html, and svgs." drawsvg's MIT licence is approved; the wheel's size is not a constraint for 0.1.3. Nothing under `src/`, `recipes/`, `scripts/`, `tests/` or `downloads/SHA256SUMS` changes.
- **Date:** 2026-10-31
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), a spike sub-agent of the orchestrating session
- **Evidence:** `build/spike-drawsvg/` in the worktree of `research/drawsvg-png` (from `dev` `54c1cd5b`), git-ignored: `prog/` (guest scripts, `probe.c`, `probe_pdf.c`, `cairo_build.py`, `patch_cairocffi.py`, `imports.py`), `stub/` (the libffi stand-in), `link/cmd.txt`, `out/` (logs, `cairocffi.diff`, the PNGs). Read only: the main tree's wasi-sdk 34, wasmtime 49.0.3, meson 1.12.1, FreeType, zlib and link objects (the build of 2026-10-21), and the set in `wasi_python-wt/163-the-result-an-agent-reads/build/artifacts`. Downloads, fetched once: the PyPI files checked against PyPI's SHA-256 (drawsvg 2.4.2, CairoSVG 2.9.1, cairocffi 1.7.1, cffi 2.1.1, tinycss2 1.5.1, cssselect2 0.10.1, svglib 2.3.2, imageio 2.38.1, rl_renderPM 4.0.3); `cairo-1.18.6.tar.xz` (`1c767308…`) and `pixman-0.46.4.tar.xz` (`a098c339…`) from cairographics.org, each matching its published hash; `libpng-1.6.59.tar.xz` (`d80dd2a3…`) from SourceForge, with no published hash to check.
- **Stands on:** `2026-10-31-pillow-with-jpeg.md`; `2026-10-31-orjson-on-pyo3-as-a-builtin.md`; `scripts/steps/37_plot_libs.sh`, `60_link.sh`; `recipes/wasi-plot-libs.cross`; `tests/upstream/packages.toml`; `../constitution.md` §4.1, §4.12.

Labels: EXECUTED means run here; READ means read from a page or file, cited; INFERRED means the researcher's reasoning. Fuel is wasmtime's count on the plain reactor, one run each; run-to-run noise was about 2 %.

## The short version

1. **drawsvg's core works in the guest as it is.** SVG, HTML, native SVG animations and frame callbacks work. Anything that rasterizes raises `ImportError`. drawsvg has no test suite anywhere. EXECUTED, READ.
2. **cairo builds for wasm32-wasip1 with no source change.** pixman and cairo build with meson and the project's cross file; libpng compiles directly. EXECUTED.
3. **Without fontconfig, text falls back to cairo's built-in stroke font.** A FreeType face from matplotlib's DejaVu bytes renders properly. A font map of about 25 lines fixes it. READ, EXECUTED.
4. **The whole chain ran in a relinked `python.wasm`.** CairoSVG wrote PNG and PDF; drawsvg wrote `save_png` and a GIF. The binary grows by 1.86 %; imports and exports do not change. EXECUTED.
5. **No route reaches PNG without a C renderer.** svglib's PNG needs libart or cairo. EXECUTED, READ.
6. **Recommendation:** drawsvg's core in 0.1.3 now. The cairo route as a second, build-class specification, reviewed before it is built: in 0.1.3 if the owner approves its licences (CairoSVG's LGPL-3.0 above all), else 0.1.4. INFERRED.

## 1. drawsvg's core in the guest (EXECUTED, READ)

drawsvg 2.4.2's wheel went on the import path from a read-only grant (`prog/g_core.py`). The drawing was its README example: lines, shapes, a path, text on a path, arcs, a marker and a gradient.

| call | result |
|---|---|
| `as_svg`, `save_svg`, `_repr_svg_`, `display_inline` | work |
| `as_html`, `save_html` | work |
| native animation with playback controls, saved as SVG and HTML | works |
| `FrameAnimation` with a callback | works |
| `rasterize`, `save_png`, `save_gif`, `save_mp4`, `save_spritesheet` | `ImportError`: "CairoSVG will need to be installed … pip install" |
| `embed_google_font` | `URLError: unknown url type: https` |
| `drawsvg.color` | `ImportError` (needs pwkit) |
| `drawsvg.widgets` | `ModuleNotFoundError: ipywidgets` |

Each failure is a clean exception. The pip advice misleads in the guest, so the package page should say what raises.

Importing drawsvg cost 739 M fuel over an empty program, compiled from source with no `.pyc`. A 1,000-circle drawing cost 207 M to become 45,584 bytes of SVG.

**Tests (spec 063).** The sdist has no tests. The repository's tree at `master` has none either (READ: GitHub's tree API, once). So its `packages.toml` entry cannot be `suite`. The honest check is a project golden: the README drawing's SVG bytes equal to a native run. Which kind names that is a judge question for the specification. INFERRED.

## 2. The PNG route

### What builds (EXECUTED)

All three with wasi-sdk 34, static, with the cross file's setjmp flags.

| library | how | result | code + data bytes |
|---|---|---|---|
| pixman 0.46.4 | meson, SIMD, tests, demos, gtk, libpng, openmp off | 3 s; 32 warnings, all `-Wunsupported-floating-point-opt` | 439,530 |
| libpng 1.6.59 | 15 files compiled directly, prebuilt `pnglibconf.h`, SIMD off | no warning | 174,931 |
| cairo 1.18.6 | meson: freetype, png, zlib on; fontconfig, xlib, xcb, quartz, dwrite, tee, glib, lzo, spectre, symbol-lookup, tests off | `libcairo.a`, 9 warnings | 951,840 |

cairo found the main tree's FreeType 2.14.3 and zlib through the pinned pkgconf. What broke:

- **Two cairo-script tools did not link** (no `-lsetjmp`, no `tmpfile`). A recipe builds only `src/libcairo.a`.
- **wasi-libc has no `tmpfile`.** Only cairo's PostScript surface calls it. A one-line stand-in failing with `ENOTSUP` makes PS fail cleanly while PNG, PDF and SVG work. One that opens and unlinks a file under `$TMPDIR` would make PS work. INFERRED.
- **Threads.** cairo's `pthread_mutex_*` calls resolve to wasi-libc's single-threaded stubs. No atomics feature appeared in the binary.
- **A host leak.** meson found a `ttx` on the machine's PATH. A recipe points it at nothing, as the cross file does for `cmake`.

A C probe (`prog/probe.c`, `probe_pdf.c`) under the wasmtime CLI drew a gradient, an arc, a curve and text, and wrote a PNG and a PDF with no error.

### Fonts without fontconfig: the key risk (READ, EXECUTED)

CairoSVG draws text through cairo's *toy* font API (`select_font_face` with a family name). cairo's FreeType backend answers toy requests only when fontconfig is built (`cairo-ft-font.c`, `_cairo_ft_font_face_backend` under `#if CAIRO_HAS_FC_FONT`). Otherwise cairo falls back to its *twin* font, a stroked sans in its own code. The probe saw this: the scaled font was type 4 (user), drawn in twin. Twin is legible but plain, and every `font-family` looks the same.

A FreeType face needs no fontconfig. The spike's build-time module adds one C helper, `wasi_cairo_ft_face_from_memory`, which makes a cairo face from a font file's bytes. In the guest it read `DejaVuSans.ttf` (756,072 bytes) through matplotlib's data path, which the set serves from `mpl-data.zip`. CairoSVG then drew the README drawing in DejaVu Sans (`out/core-ft.png`). A specification maps the generic families and their bold and oblique to the twelve DejaVu Sans, Serif and Mono files already there. That is about 25 lines and no new font. INFERRED for the count.

CairoSVG's text has no shaping (`cairo_show_text`): Latin is fine, Arabic or Indic is not, on every platform. READ.

### cffi and cairocffi (EXECUTED)

cairocffi 1.7.1 binds cairo at run time with `ffi.dlopen` (`cairocffi/__init__.py`). The guest has no `dlopen` and no libffi.

- **`_cffi_backend`** from cffi 2.1.1 compiled with `-D_WASI_EMULATED_MMAN` and a 45-line stand-in for libffi (`stub/`), since libffi has no wasm32-wasip1 port. The stand-in builds function types. A call through a C function pointer, which only ABI mode makes, aborts. The first stand-in refused function types, and `@ffi.def_extern` raised `SystemError`; building them fixed it. 140,011 bytes.
- **The bindings.** `prog/cairo_build.py` runs on the host (cffi through `uv run --with`). It writes cairocffi's own declarations in cffi's out-of-line API mode, cut before the Windows and Quartz sections. It adds three `extern "Python"` callbacks and the font helper. The 785 KB C file compiled with no warning, so every declaration exists in this cairo. 266,727 bytes.
- **The cairocffi change** (`out/cairocffi.diff`: 43 lines added, 36 removed, two files). `__init__.py` takes `ffi` and `lib` from the built module. `surfaces.py` replaces three run-time `ffi.callback` closures (read, write, keep-alive destroy) with the static callbacks and `ffi.new_handle`. A first version passed the user-data arguments in the wrong order and trapped "table out of bounds" when a surface was freed. Fixed, it ran.
- **A patch-free alternative**, not tried: a stand-in `cffi` module answers `dlopen` with the built `lib`, and `callback` with a fixed pool of static trampolines. No cairocffi patch, but a cap on live stream surfaces. §4.1 prefers the recipe file; the pre-build review chooses. INFERRED.

The relink (`link/cmd.txt`) used the main tree's reactor link line. It added both modules to a copy of the inittab and one archive with the cairo chain. In the guest (`prog/g_cairo.py`) these worked:

- `cairocffi` imports and reports cairo 1.18.6;
- PNG to and from streams; a `PDFSurface` with text;
- CairoSVG 2.9.1's `svg2png`, `svg2pdf`, `svg2svg`, and `svg2png` of the animated SVG (its first frame);
- drawsvg's `save_png`;
- a five-frame GIF through `drawsvg.video.save_video` and imageio's Pillow plugin.

`PSSurface` failed as expected. tinycss2 and cssselect2 are pure Python; defusedxml, webencodings and Pillow are in the set already.

### Cost (EXECUTED; INFERRED where marked)

- **Binary.** Stripped as step 60 strips it: 101,271,078 bytes against 99,421,511 for the same link without the additions. That is +1,849,567 bytes (1.86 %), +541,383 gzipped. The 50 imports and exports, the tag and table sections and the target features are unchanged.
- **Zip.** Sources: drawsvg 131 KB, CairoSVG 142 KB, cairocffi 257 KB without tests, tinycss2 103 KB, cssselect2 53 KB, imageio 1,175 KB. About 0.6 MB compressed as `.pyc`. INFERRED.
- **Fuel elsewhere.** An empty program: 343.3 M on the base binary, 343.5 M on the spike's. `import numpy, PIL.Image`: 1,306 M and 1,308 M. Within noise.
- **Fuel of the feature.** Importing CairoSVG and drawsvg from source: 2.15 G, mostly compiling (INFERRED). One `svg2png` of the README drawing at 400×200: 219 M to 225 M. A 1,000-circle drawing rasterized at 400×400: 1.06 G above its SVG. A ten-frame 200×200 GIF: 3.3 G with imageio's import. For scale, a small matplotlib plot's `savefig` to PNG: 483 M.

### Licences (READ)

| component | licence | status |
|---|---|---|
| drawsvg | MIT | approved |
| cairo | each file LGPL-2.1 or MPL-1.1 (`COPYING`); ten `src/` files under MIT-style terms | **to approve**; electing MPL-1.1 avoids LGPL's relinking terms for a static link |
| pixman | MIT | to approve |
| libpng | PNG Reference Library License v2 | to approve |
| cffi | MIT No Attribution | to approve |
| cairocffi, tinycss2, cssselect2 | BSD-3-Clause | to approve |
| **CairoSVG** | **LGPL-3.0-or-later** | **to approve: the flag** |
| imageio | BSD-2-Clause | to approve |

CairoSVG is the one to weigh. LGPL-3.0 §4 asks that a user can combine the work with a modified library. In the guest, a module the set carries always wins over one a user adds (`docs/reference/packages.md`). So a user cannot swap CairoSVG at run time through the runner's order alone. (Corrected 2026-10-31, at specification 174's pre-build review: a program may move a granted folder ahead of the zip on `sys.path` before CairoSVG's first import, and then imports its own copy.) They can rebuild the set from its public, pinned recipe with their own copy. Whether that meets §4 is the owner's call, or counsel's. svglib, the alternative, is LGPL-3.0-or-later too.

## 3. Routes without cairo (EXECUTED, READ)

- **svglib with reportlab.** svglib imports over the set's reportlab 5.0.1 and lxml, converts the README SVG, and `renderPDF` writes it. `renderPM` refuses: "cannot import desired renderPM backend rlPyCairo". Its backends are pycairo (cairo again) and rl_renderPM, a C extension whose `setup.py` downloads libart (LGPL) at build time. svglib's README lists no masks and limited CSS. No gain over cairo.
- **matplotlib.** Agg rasterizes well but cannot read SVG. A converter would be new code covering a fraction of SVG. INFERRED.
- **A pure-Python rasterizer.** None is maintained with CairoSVG's coverage; Pillow cannot read SVG. INFERRED.
- **resvg (Rust).** The most complete static renderer, with fonts from files and no fontconfig. It follows orjson's PyO3 path, which waits for 0.1.4. Revisit then. INFERRED.

## 4. Value against the owner's four aims (EXECUTED, INFERRED)

| aim | the set today | drawsvg core adds | the cairo route adds |
|---|---|---|---|
| high-quality images | matplotlib PNG, SVG, PDF of charts; Pillow | free-form vector drawing, as SVG | PNG and PDF of any drawsvg drawing or SVG; cairocffi, a general 2D API |
| animations | matplotlib `FuncAnimation` to GIF via `PillowWriter` (ran here: 10 frames, 19,804 bytes) and `to_jshtml`; MP4 refused | SMIL animations in one SVG, with playback controls | drawsvg GIFs and spritesheets |
| interactive HTML | `to_jshtml`; plotly in spec 167 | `as_html` with browser playback | none |
| SVGs | matplotlib charts | hand-built SVG | `svg2svg` cleaning |

MP4 stays impossible: imageio_ffmpeg runs an ffmpeg process. pwkit, for one colour helper, and ipywidgets, with no kernel, stay out. INFERRED.

So drawsvg's core serves SVG and interactive HTML fully, and animation in the browser. The cairo route turns a drawing into an image a person can paste anywhere. That is most of "high quality images", and it adds a vector drawing API beside matplotlib's.

## 5. Recommendation and plan (INFERRED)

**Specification A, drawsvg's core, for 0.1.3.** Pure Python, licence approved, no build change, about 131 KB of source. The package page says what works and what raises. The open question is the judge's kind for a project golden, since drawsvg has no suite.

**Specification B, PNG through cairo.** Build-class, reviewed before it is built (§5.6). Not structural: `src/` does not change. It carries:

- **Pins:** pixman, libpng, cairo; the cffi, cairocffi, CairoSVG, tinycss2, cssselect2 and imageio sdists.
- **Build:** a step like step 37 (meson for pixman and `libcairo.a`), libpng compiled directly, `_cffi_backend` with the libffi stand-in, and `cairo_build.py` as a recipe file.
- **Stand-ins:** `tmpfile`, and the DejaVu font map.
- **cairocffi:** a recorded patch with its upstream pull request drafted, or the stand-in `cffi` module.
- **Checks:** a golden `svg2png` against a native cairo without fontconfig; text in DejaVu, not twin; `save_png`, a GIF and a PDF; imports and tags unchanged; the same bytes on Linux, untried here.
- **Spec 063:** cairocffi's `test_cairo.py` (47 tests) imports pikepdf at module level, so it needs a stand-in or an allowance. CairoSVG's sdist has only `test_api.py` (4 tests); its reference-PNG suite is in the repository only. tinycss2 and cssselect2 ship `tests/`.

B waits on licence approval: CairoSVG's LGPL-3.0, and cairo under MPL-1.1. With it, B fits 0.1.3, since every hard part ran end to end here. Without it, or if the lane is full, B moves to 0.1.4 unchanged.

**Left out:** svglib and rl_renderPM, pwkit, ipywidgets, imageio_ffmpeg.

## What the spike did not do

- It did not rebuild the snapshot, run the judge's driver, or build on Linux.
- It did not write the font map or the stand-in `cffi` module.
- It did not run cairocffi's or CairoSVG's tests in the guest.
- It compared PNGs by eye, not pixel for pixel with a native build.
- No hypothesis failed twice.

**One line:** drawsvg's core works in the guest today and belongs in 0.1.3. PNG, PDF and GIF through cairo also work end to end, for 1.9 % more binary and a 25-line font map, and earn a second, reviewed specification once the owner approves CairoSVG's LGPL-3.0 and the other licences.
