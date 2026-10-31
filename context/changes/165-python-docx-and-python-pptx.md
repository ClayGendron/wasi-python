# 165: python-docx and python-pptx

## Changelog

### New

- **Word and PowerPoint files.** python-docx 1.2.0 and python-pptx 1.0.2 are in the zip. Start a document or a deck from the default template, or open one; add text, tables, pictures, charts and notes; save it to a granted folder or to memory. `fit_text()` needs FreeType, which the set lacks. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)

### For contributors

- **Two carried patches read the templates from the zip.** `recipes/patches/python_docx-1.2.0/0001-templates-read-as-package-resources.patch` and `recipes/patches/python_pptx-1.0.2/0001-templates-read-as-package-resources.patch` read each default template through the package's loader, so `Document()` and `Presentation()` work from a zip. [Carrying a patch](https://claygendron.github.io/wasi-python/contributing/carrying-a-patch/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "165"
new = [
  "tests/checks/test_v1_3_default_profile.py::test_office_templates_read_from_the_zip*",
  "tests/checks/test_v1_3_default_profile.py::test_documents_job_matches_native",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[python-docx-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[python-pptx-smoke]",
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_source_tree_matches_its_tarball[python-docx]",
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_source_tree_matches_its_tarball[python-pptx]",
]
grows = ["tests/checks/*"]
growth = "python-docx 1.2.0 and python-pptx 1.0.2 join the zip: 214 members (212 package files and two METADATA), so every guest's zip directory is larger. Measured on darwin arm64 against the set of 166's first pull request: the zip 53,829,197 to 54,960,042 bytes (+1,130,845, +2.10%), 6,262 to 6,476 members; python-snapshot.wasm 104,576,267 to 104,660,362 (+84,095, +0.080%), the zip's directory being in the image; python.wasm unchanged; a plain start (-c pass) 272,159,309 to 277,407,635 fuel (+5,248,326, +1.93%, 24.5 k a member) and a snapshot start 53,538,500 to 54,080,242 (+1.01%); the wheel, built by hand from each set, 98,327,640 to 99,460,553 bytes (+1,132,913), 539,447 under 100,000,000 and 5,397,047 under 104,857,600"
units = 0
[claim.judge]
"tests/upstream/python-docx.toml" = "python-docx's own suite, from its patched sdist: a smoke group in the normal tier (18.6 G measured, 28 G cap) and the whole suite in the release tier (105.8 G, 160 G cap); the family's budget is the sum, 188 G"
"tests/upstream/python-pptx.toml" = "python-pptx's own suite, from its patched sdist: a smoke group in the normal tier (13.4 G measured, 21 G cap) and the whole suite in the release tier (150.0 G, 230 G cap); the family's budget is the sum, 251 G"
"tests/upstream/packages.toml" = "python-docx and python-pptx each name their own suite"
"tests/upstream/expected/python-docx-r/bytesio-mocked-in-a-fixture.txt" = "three tests patch io.BytesIO for the whole interpreter in a fixture, and pytest's sys capture, which the driver uses because the guest cannot duplicate a descriptor, asserts its buffer is an io.BytesIO; native pytest with --capture=sys fails the same three"
"tests/upstream/expected/python-pptx-r/bytesio-mocked-in-a-fixture.txt" = "one test patches io.BytesIO in a fixture; the same cause"
"tests/upstream/expected/python-pptx-r/bytesio-mocked-in-a-test.txt" = "two tests patch io.BytesIO in the test body; the same cause"
"tests/known_gaps.toml" = "the three classes' gaps, by their findings' digests"
"tests/release_shards.toml" = "the two smoke groups join upstream-pure-smoke-b; the two whole suites take a new release shard, upstream-release-066, its minutes estimated from their fuel until a release run measures them"
"context/release-claims.toml" = "165's block: the two release groups and their classes are new"
```
