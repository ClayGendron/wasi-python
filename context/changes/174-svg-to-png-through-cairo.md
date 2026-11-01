# 174: SVG to PNG through cairo

## Changelog

### New

- **SVG to PNG and PDF, drawn by cairo.** cairo 1.18.6 is built in, with CairoSVG 2.9.1 in the zip: `cairosvg.svg2png` and `svg2pdf` turn any SVG into a PNG or a PDF with native cairo's pixels, and text is drawn in matplotlib's DejaVu fonts. PostScript output is not available. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)
- **cairocffi, a 2D drawing API.** cairocffi 1.7.1 draws paths, gradients and text onto image, PDF and SVG surfaces, and reads and writes PNG. At most 128 stream surfaces are alive at once. [Limitations](https://claygendron.github.io/wasi-python/reference/limitations/)
- **Animated GIFs with imageio.** imageio 2.38.1 reads and writes images through Pillow, animated GIFs included. Its video plugins need programs or compiled packages the set does not carry, and raise when used. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)

### For contributors

- **A carried patch lets CairoSVG import from the zip.** `recipes/patches/cairosvg-2.9.1/0001-read-version-through-the-package-loader.patch` reads CairoSVG's VERSION file through the package's loader instead of a path made from `__file__`, which names no file inside the zip. [Carrying a patch](https://claygendron.github.io/wasi-python/contributing/carrying-a-patch/)
- **cairocffi runs on a stand-in for its `ffi` module.** The bindings are written in cffi's API mode at build time and linked in; `recipes/cairocffi_ffi_stand_in.py` replaces the module that would load cairo at run time, and step 56 stops if the pinned cairocffi grows past it. [Building](https://claygendron.github.io/wasi-python/contributing/building/)

## Package rows

| cairocffi | 1.7.1 | Built in, over cairo 1.18.6 with pixman 0.46.4 and libpng 1.6.59, and cffi 2.1.1's C backend: image, PDF and SVG surfaces, PNG in and out, text in matplotlib's DejaVu fonts. No PostScript. |

## Claims

```toml
[[claim]]
spec = "174"
new = [
  "tests/checks/test_v1_3_drawing.py",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[tinycss2-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cssselect2-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cairocffi-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cairosvg-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[imageio-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[cairocffi-smoke-no-pikepdf]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[cairocffi-smoke-no-ctypes-address]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[cairocffi-smoke-no-tmpfile]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[cairosvg-smoke-no-tmpfile]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[imageio-smoke-no-jpeg]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[imageio-smoke-fails-natively]",
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_source_tree_matches_its_tarball[pixman]",
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_source_tree_matches_its_tarball[libpng]",
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_source_tree_matches_its_tarball[cairo]",
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_source_tree_matches_its_tarball[cffi]",
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_source_tree_matches_its_tarball[cairocffi]",
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_source_tree_matches_its_tarball[cairosvg]",
]
grows = ["tests/checks/*"]
growth = "cairo, pixman, libpng, cffi's C backend and cairocffi's bindings are linked into python.wasm, and cairocffi, CairoSVG (with its source), tinycss2, cssselect2 and imageio join the zip. Measured on darwin arm64 against dev's set at a0f3e3b5: python.wasm 99,497,353 to 101,418,432 bytes (+1,921,079, +1.93%); python-snapshot.wasm 104,890,482 to 106,847,177 (+1,956,695); the zip 57,068,536 to 57,952,950 (+884,414, +1.55%), 6,721 to 6,840 members; a plain start (-c pass) 283,812,271 to 286,621,212 fuel (+0.99%) and a snapshot start 54,767,956 to 55,037,375 (+0.49%); the wheel, built by hand as the release workflow builds it, 103,722,443 bytes, 1,135,157 under PyPI's 104,857,600"
units = 0
[claim.judge]
"tests/upstream/tinycss2.toml" = "tinycss2's own suite from its sdist, its one test file whole as the smoke group (105.9 G measured, 159 G cap): a smoke family splits its tiers by path"
"tests/upstream/cssselect2.toml" = "cssselect2's own suite from its sdist, whole, as one smoke group (18.0 G, 27 G cap)"
"tests/upstream/cairocffi.toml" = "cairocffi's own tests, modules of its package in the sdist, staged and found through the package's path: test_cairo.py in the normal tier (14.1 G, 22 G cap), test_numpy.py and test_xcb.py in the release tier (11.1 G, 17 G cap), test_pixbuf.py not selected (gdk-pixbuf is not carried); a test-side stand-in for pikepdf lets test_cairo.py collect; classes for pikepdf, ctypes addresses and the PostScript surface's temporary file"
"tests/upstream/cairosvg.toml" = "CairoSVG's API tests from its sdist, one smoke group (16.3 G, 25 G cap), with the PostScript format's class; its non-regression suite needs a git submodule and is not in the sdist"
"tests/upstream/imageio.toml" = "imageio's own suite from its sdist with its test images pinned at one commit and staged as .test_images: test_pillow.py as the smoke group (47.0 G, 71 G cap), the rest in the release tier (275.0 G, 413 G cap), the needs_internet tests deselected, test_freeimage.py not selected (ctypes at import), a test-side cache stand-in for its test_images fixture; classes for ctypes, JPEG (until Pillow reads JPEG), processes, the wasi platform name, the legacy tifffile writer and two tests that fail natively"
"tests/upstream/packages.toml" = "cairocffi, CairoSVG, tinycss2, cssselect2 and imageio each name their own suite; pixman, libpng, cairo and cffi are reached through cairocffi's"
"tests/upstream/expected/cairocffi-smoke/no-pikepdf.txt" = "the members of the class cairocffi-smoke-no-pikepdf"
"tests/upstream/expected/cairocffi-smoke/no-ctypes-address.txt" = "the members of the class cairocffi-smoke-no-ctypes-address"
"tests/upstream/expected/cairocffi-smoke/no-tmpfile.txt" = "the members of the class cairocffi-smoke-no-tmpfile"
"tests/upstream/expected/cairocffi-r/no-ctypes-address.txt" = "the members of the class cairocffi-r-no-ctypes-address"
"tests/upstream/expected/cairosvg-smoke/no-tmpfile.txt" = "the members of the class cairosvg-smoke-no-tmpfile"
"tests/upstream/expected/imageio-smoke/no-jpeg.txt" = "the members of the class imageio-smoke-no-jpeg"
"tests/upstream/expected/imageio-smoke/fails-natively.txt" = "the members of the class imageio-smoke-fails-natively"
"tests/upstream/expected/imageio-r/no-ctypes.txt" = "the members of the class imageio-r-no-ctypes"
"tests/upstream/expected/imageio-r/no-jpeg.txt" = "the members of the class imageio-r-no-jpeg"
"tests/upstream/expected/imageio-r/no-jpeg-plugin.txt" = "the members of the class imageio-r-no-jpeg-plugin"
"tests/upstream/expected/imageio-r/no-processes.txt" = "the members of the class imageio-r-no-processes"
"tests/upstream/expected/imageio-r/fails-natively.txt" = "the members of the class imageio-r-fails-natively"
"tests/upstream/expected/imageio-r/wasi-platform.txt" = "the members of the class imageio-r-wasi-platform"
"tests/upstream/expected/imageio-r/legacy-tifffile.txt" = "the members of the class imageio-r-legacy-tifffile"
"tests/known_gaps.toml" = "the fourteen classes' gaps, by their findings' digests, within the pure-Python packages' section"
"tests/release_shards.toml" = "test_v1_3_drawing.py joins own-guest-c on all three systems; the five smoke groups join upstream-pure-smoke-b; the two release groups take a new release shard, upstream-release-069, its minutes estimated from their fuel"
"context/release-claims/174-svg-to-png-through-cairo.toml" = "174's block: the two release groups and their classes are new"
```
