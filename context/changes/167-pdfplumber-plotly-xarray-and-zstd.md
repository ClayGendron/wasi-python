# 167: pdfplumber, plotly, xarray and zstd

## Changelog

### New

- **Tables and text from PDF files.** pdfplumber 0.11.10 with pdfminer.six 20260107 is in the zip: each page's text, its words with their positions, its ruling lines and `extract_tables()`, and files encrypted with RC4. AES needs `cryptography` and page images need pypdfium2, which the set does not carry; each raises `ModuleNotFoundError` naming it. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)
- **Labelled arrays.** xarray 2026.9.0 is in the zip: named dimensions, alignment on labels, `groupby`, `rolling`, `resample`, interpolation through scipy, pandas round trips, the HTML view, and netCDF3 files through scipy. Its other file engines and its tutorial data are not carried. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)

### For contributors

- **A carried patch lets pdfminer.six start without cryptography.** `recipes/patches/pdfminer_six-20260107/0001-import-cryptography-where-aes-runs.patch` moves pdfminer's two `cryptography` imports into the one helper its AES paths call, so plain and RC4 files read without it. [Carrying a patch](https://claygendron.github.io/wasi-python/contributing/carrying-a-patch/)
- **The wheel's size is checked against PyPI's file limit.** The artifact rules refuse a wheel over 104,857,600 bytes (100 MiB), PyPI's limit until it raises the project's, on every run that builds one, so no tag makes a GitHub release whose wheel PyPI would refuse. [Release process](https://claygendron.github.io/wasi-python/contributing/release-process/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "167"
new = [
  "tests/checks/test_v1_3_default_profile.py::test_pdfplumber_needs_cryptography_only_for_aes*",
  "tests/checks/test_v1_3_default_profile.py::test_pdf_tables_job_matches_native",
  "tests/checks/test_v1_3_default_profile.py::test_labelled_arrays_job_matches_native",
  "tests/checks/test_v1_3_default_profile.py::test_xarray_reads_netcdf3_files_without_mmap*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pdfplumber-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pdfminer-six-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[xarray-smoke]",
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_source_tree_matches_its_tarball[pdfminer-six]",
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_source_tree_matches_its_tarball[xarray]",
]
# matplotlib-rest-a gains two passes: test_cbook.py::test_reshape2d_xarray and ::test_index_of_xarray use
# matplotlib's xr fixture, which skips without xarray; xarray is now in the zip (pytz stays test-only).
passes = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[matplotlib-rest-a]"]
grows = ["tests/checks/*"]
growth = "pdfplumber 0.11.10, pdfminer.six 20260107 (without its cmap folder) and xarray 2026.9.0 join the zip: 185 members (180 package files, three METADATA, two entry_points.txt), so every guest's zip directory is larger. Measured on darwin arm64 against dev's set with 165: the zip 54,960,042 to 57,051,943 bytes (+2,091,901, +3.81%), 6,476 to 6,661 members; python-snapshot.wasm 104,660,252 to 104,864,834 (+204,582), the zip's directory being in the image; a plain start (-c pass) 277,589,139 to 282,253,209 fuel (+4,664,070, +1.68%, 25.2 k a member) and a snapshot start 54,177,689 to 54,596,257 (+0.77%); the wheel, built by hand as the release workflow builds it, 101,631,881 bytes, 3,225,719 under PyPI's 104,857,600"
units = 1
[claim.judge]
"tests/upstream/pdfplumber.toml" = "pdfplumber's own suite, from its 0.11.10 release tag (its sdist lacks the PDF files the tests read), tied to the shipped wheel: a smoke group in the normal tier (41.4 G measured, 62 G cap) and the whole suite in the release tier (171.5 G, 257 G cap), with four classes: no processes, no pypdfium2 (an error and a failure), no Ghostscript"
"tests/upstream/pdfminer-six.toml" = "pdfminer.six's own suite, from its 20260107 release tag (its sdist lacks samples/ and tools/): a smoke group (11.5 G, 17 G cap) and the whole suite in the release tier (86.9 G, 130 G cap), with two classes: no cryptography for the AES samples, and the CJK character maps left out of the zip, each class's pattern its members' own messages"
"tests/upstream/xarray.toml" = "xarray's own suite, from its sdist, with pytest-asyncio and pytz as test-only wheels: a smoke group (39.7 G, 59 G cap) and eight release groups (1,536.7 G in sum, each cap 1.5 times its measure), with classes for no mmap (scipy's netCDF3 reader maps a path), no threads, asyncio's loop, the 32-bit default integer, one test that fails natively at these pins, and find_stack_level reading the staged tests folder; each class's pattern is its members' own messages, and the last two close with the roadmap, where each is a reserved line (the staging follow-up, and the next xarray pin)"
"tests/upstream/packages.toml" = "pdfplumber, pdfminer.six and xarray each name their own suite"
"tests/known_gaps.toml" = "the sixteen classes' gaps, by their findings' digests, within the pure-Python packages' section; xarray's fails-natively and staged-tests-folder close with the roadmap"
"tests/release_shards.toml" = "the three smoke groups join upstream-pure-smoke-b; the ten release groups take two new release shards, upstream-release-067 and -068, their minutes estimated from their fuel until a release run measures them"
"context/release-claims.toml" = "167's block: the ten release groups and their classes are new"
"tests/upstream/expected/pdfminer-six-r/no-cjk-cmaps.txt" = "the members of the class pdfminer-six-r-no-cjk-cmaps"
"tests/upstream/expected/pdfminer-six-r/no-cryptography.txt" = "the members of the class pdfminer-six-r-no-cryptography"
"tests/upstream/expected/pdfplumber-r/no-ghostscript.txt" = "the members of the class pdfplumber-r-no-ghostscript"
"tests/upstream/expected/pdfplumber-r/no-processes.txt" = "the members of the class pdfplumber-r-no-processes"
"tests/upstream/expected/pdfplumber-r/no-pypdfium2-in-a-test.txt" = "the members of the class pdfplumber-r-no-pypdfium2-in-a-test"
"tests/upstream/expected/pdfplumber-r/no-pypdfium2.txt" = "the members of the class pdfplumber-r-no-pypdfium2"
"tests/upstream/expected/xarray-r-arrays/no-asyncio-loop-error.txt" = "the members of the class xarray-r-arrays-no-asyncio-loop-error"
"tests/upstream/expected/xarray-r-backends/no-mmap.txt" = "the members of the class xarray-r-backends-no-mmap"
"tests/upstream/expected/xarray-r-backends/no-threads.txt" = "the members of the class xarray-r-backends-no-threads"
"tests/upstream/expected/xarray-r-coding/wasm32-int32.txt" = "the members of the class xarray-r-coding-wasm32-int32"
"tests/upstream/expected/xarray-r-dataset/fails-natively.txt" = "the members of the class xarray-r-dataset-fails-natively"
"tests/upstream/expected/xarray-r-dataset/wasm32-int32.txt" = "the members of the class xarray-r-dataset-wasm32-int32"
"tests/upstream/expected/xarray-r-rest/no-asyncio-loop-error.txt" = "the members of the class xarray-r-rest-no-asyncio-loop-error"
"tests/upstream/expected/xarray-r-rest/no-mmap.txt" = "the members of the class xarray-r-rest-no-mmap"
"tests/upstream/expected/xarray-r-rest/staged-tests-folder.txt" = "the members of the class xarray-r-rest-staged-tests-folder"
"tests/upstream/expected/xarray-r-rest/wasm32-int32.txt" = "the members of the class xarray-r-rest-wasm32-int32"
```
