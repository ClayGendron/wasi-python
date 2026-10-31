# 170: Pillow reads and writes JPEG

## Changelog

### New

- **Pillow reads and writes JPEG.** Pillow is built with libjpeg-turbo 3.2.0 beside zlib, so `Image.open` of a photo, `save(..., "JPEG")` and matplotlib's `savefig(format="jpg")` work, with native Pillow's bytes and pixels. WebP, AVIF, JPEG 2000 and TIFF's compressions still raise an error. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)

### For contributors

- **libjpeg-turbo is compiled without CMake.** The plot libraries' step compiles libjpeg's 101 files from the list in its `CMakeLists.txt`, with no SIMD and the libjpeg v6b API, and its three configured headers are recipe files under `recipes/libjpeg-turbo/`, held to their templates. [Building](https://claygendron.github.io/wasi-python/contributing/building/)

## Package rows

| matplotlib | 3.11.2 | The Agg backend. PNG, JPEG, PDF, PS, EPS and SVG save. Contours through contourpy 1.4.0, and Delaunay triangulations through qhull 8.0.2. Text through FreeType 2.14.3, HarfBuzz 14.1.0, SheenBidi 3.0.0 and libraqm 0.10.5. See [matplotlib](../how-to/matplotlib.md). |
| Pillow | 13.0.0 | Its core, with zlib and libjpeg-turbo 3.2.0: PNG and JPEG (and MPO) read and write; WebP, TIFF's compressions and JPEG 2000 do not. This software is based in part on the work of the Independent JPEG Group. |

## Claims

```toml
[[claim]]
spec = "170"
new = [
  "tests/checks/test_v1_3_matplotlib.py::test_jpeg_images_job_matches_native",
  "tests/checks/test_v1_3_matplotlib.py::test_a_broken_jpeg_raises_and_the_next_decodes*",
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_source_tree_matches_its_tarball[libjpeg-turbo]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pypdf-r-pillow-no-jpeg2k-or-tiff]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[openpyxl-r-pillow-no-jpeg2k-or-tiff]",
]
retired = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pillow-pillow-zlib-only]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[matplotlib-render-2b-pillow-zlib-only]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[matplotlib-rest-a-pillow-zlib-only]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-datasets-pillow-zlib-only-at-setup]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pypdf-r-pillow-zlib-only]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[openpyxl-r-pillow-zlib-only]",
]
changed = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pillow-not-pillows-wheel]",
]
passes = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pillow]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[matplotlib-render-2b]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[matplotlib-rest-a]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[scikit-learn-datasets]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pypdf-r]",
]
grows = [
  "tests/checks/*",
]
growth = "Pillow gains JPEG: libjpeg-turbo 3.2.0 is linked into _imaging, and the JPEG tests that failed now run. Measured on darwin arm64 against dev's set (165's, the same bytes): python.wasm 99,492,553 to 100,012,947 bytes (+520,394, +0.52%); python-snapshot.wasm 104,660,252 to 105,184,822 (+524,570, +0.50%); the zip unchanged (54,960,042); the wheel, built by hand from each set, 99,478,846 to 99,687,768 (+208,922), 5,169,832 under 104,857,600. Fuel outside JPEG does not move: the 136 fast-tier fuel rows of five product files, run on both sets, differ by -0.19% to +0.14% (median -0.007%); a plain start 277,790,133 to 277,713,412 and a snapshot start 54,380,360 to 54,373,605. The rest of what the fast tier lists against the last acceptance is 165's zip. The pillow group 432.7 G to 605.1 G (+39.8%) with 4,792 passes (4,593): Pillow's JPEG and MPO tests run, and its cap moves to 910 G by the 1.5 rule; matplotlib-render-2b 337.0 G (+0.02%) with 395 passes (392) and matplotlib-rest-a 314.8 G (+1.57%) with 971 passes (966), their JPEG tests running; scikit-learn-datasets 90.9 G (65.6 G on Linux) with 360 passes (356), its cap 140 G; pypdf-r 1,703 passes (1,695 after 166); openpyxl-r 63.2 G, its passes the same"
units = 0
[claim.judge]
"tests/upstream/pillow.toml" = "the pillow-zlib-only class leaves (none of its 55 tests fails with JPEG); the group's measured fuel moves to 605.1 G and its cap and the family's budget to 910 G, 1.5 times; not-pillows-wheel's reason says zlib and JPEG"
"tests/upstream/matplotlib.toml" = "both pillow-zlib-only classes leave: their eight tests pass with JPEG"
"tests/upstream/scikit-learn.toml" = "pillow-zlib-only-at-setup leaves: the faces dataset's JPEG fixtures write and its four tests pass; scikit-learn-datasets measures 90.9 G, so its cap moves from 99 G to 140 G (1.5 times) and the family's budget by the same 41 G"
"tests/upstream/pypdf.toml" = "the class narrows to JPEG 2000 and TIFF's codecs under the new id pillow-no-jpeg2k-or-tiff: its eight JPEG tests pass, four remain"
"tests/upstream/openpyxl.toml" = "the class narrows to JPEG 2000 and TIFF's codecs under the new id pillow-no-jpeg2k-or-tiff; its one test reads a compressed TIFF and still fails"
"tests/upstream/packages.toml" = "libjpeg-turbo is reached through Pillow's suite"
"tests/upstream/expected/pillow/pillow-zlib-only.txt" = "the class leaves"
"tests/upstream/expected/matplotlib-render-2b/pillow-zlib-only.txt" = "the class leaves"
"tests/upstream/expected/matplotlib-rest-a/pillow-zlib-only.txt" = "the class leaves"
"tests/upstream/expected/scikit-learn-datasets/pillow-zlib-only-at-setup.txt" = "the class leaves"
"tests/upstream/expected/pypdf-r/pillow-zlib-only.txt" = "renamed to the class's new id"
"tests/upstream/expected/pypdf-r/pillow-no-jpeg2k-or-tiff.txt" = "the four JPEG 2000 and TIFF tests left of twelve"
"tests/upstream/expected/openpyxl-r/pillow-zlib-only.txt" = "renamed to the class's new id"
"tests/upstream/expected/openpyxl-r/pillow-no-jpeg2k-or-tiff.txt" = "its one TIFF test, as before"
"tests/known_gaps.toml" = "the four emptied classes' gaps leave; pypdf's and openpyxl's take the new id, pypdf's with its four findings' digest; not-pillows-wheel's reason says zlib and JPEG"
"tests/release_shards.toml" = "the pillow group grows to 605.1 G, so matplotlib-render-3 moves from upstream-plot-b to upstream-plot-i: 621.1 G and 683.4 G, both under the 725 G the shards are packed to"
"context/release-claims/170-pillow-reads-and-writes-jpeg.toml" = "170's block: the release groups' classes and pass counts"
```
