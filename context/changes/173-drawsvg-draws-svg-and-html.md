# 173: drawsvg draws SVG and HTML

## Changelog

### New

- **Vector drawings and animations as SVG and HTML.** drawsvg 2.4.2 is in the zip: shapes, paths, text on a path, gradients, markers, clip paths and masks, SMIL animations with playback controls, and frame callbacks, saved as SVG or HTML. Its PNG, GIF and video output, `drawsvg.color` and Google fonts raise by name. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)

### For contributors

- **A package that ships no tests is checked by its golden jobs.** `tests/upstream/packages.toml` gains the kind `none`: a reason saying where the absence of tests was read, and `checked_by`, golden jobs that must import the package. It is refused when the package has a suite file. [Adding a package](https://claygendron.github.io/wasi-python/contributing/adding-a-package/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "173"
new = [
  "tests/checks/test_v1_3_default_profile.py::test_vector_drawings_job_matches_native",
  "tests/checks/test_v1_3_default_profile.py::test_drawsvg_names_what_the_set_lacks*",
]
grows = ["tests/checks/*"]
growth = "drawsvg 2.4.2 joins the zip from its wheel, whole: 22 members (20 modules, its METADATA and top_level.txt), so every guest's zip directory is larger. Measured on darwin arm64 against dev's set at 9d311a0a built from the same tree: the zip 57,068,536 to 57,159,131 bytes (+90,595, +0.16%), 6,721 to 6,743 members; python-snapshot.wasm 104,890,482 to 104,909,776 (+19,294); python.wasm unchanged at 99,497,353; a plain start (-c pass, mean of two) 283,763,543 to 284,178,433 fuel (+414,890, +0.15%, 19 k a member) and a snapshot start 54,767,956 to 54,881,031 (+113,075, +0.21%); the wheel, built as the release workflow builds it, 101,659,542 to 101,758,925 bytes (+99,383), 3,098,675 under PyPI's 104,857,600"
units = 7
[claim.judge]
"tests/upstream/packages.toml" = "a fifth kind, none, for a project that ships no tests at its pinned version, refused without a reason or checked_by, with a checked_by that is not a golden job or whose job does not import the package (read with ast), or when tests/upstream/<name>.toml exists; drawsvg's entry is none, checked by vector_drawings"
```
