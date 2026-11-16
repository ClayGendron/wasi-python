# 191: pytz, rich, Faker and folium

## Changelog

### New

- **Time zones through pytz.** pytz 2026.6 is in the zip and reads every zone from it: `localize`, `normalize`, its zone lists and pickled times work, and pandas takes its zones, since it imports pytz whenever pytz is there. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)
- **Terminal text with rich.** rich 15.0.0, with markdown-it-py 4.3.0, mdurl 0.1.2 and Pygments 2.21.0, is in the zip: tables, panels, trees, Markdown, highlighted code and pretty values, exported as text, HTML or SVG. Displays that refresh themselves need a thread and raise `RuntimeError`; `Progress(auto_refresh=False)` works. [Limitations](https://claygendron.github.io/wasi-python/reference/limitations/)
- **Fake data with Faker.** Faker 40.54.0 is in the zip with its 110 locales. A seeded `Faker` gives native's values, and each call from a starting image draws afresh unless the program seeds it. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)
- **Web maps with folium.** folium 0.20.0, with branca 0.8.2 and xyzservices 2026.9.1, is in the zip: Leaflet maps as HTML pages, colour scales and tile providers. A `GeoJson` given a URL raises `ModuleNotFoundError` naming `requests`, which the set lacks; give it a dict or a file. [Limitations](https://claygendron.github.io/wasi-python/reference/limitations/)

### Upgrading

- **Your own pytz, rich, Pygments, Faker or folium is no longer reached.** The runtime now carries them, and its own modules come first, so one shipped through `import_path=` is not imported, and `import pandas` loads the runtime's pytz. Remove yours, or name your module apart. [The import path](https://claygendron.github.io/wasi-python/reference/guest-filesystem/#the-import-path)

### For contributors

- **A carried patch lets folium start without requests.** `recipes/patches/folium-0.20.0/0001-import-requests-where-a-url-is-fetched.patch` moves folium's `import requests` into the one method that fetches a URL, so a map that fetches nothing needs no requests. [Carrying a patch](https://claygendron.github.io/wasi-python/contributing/carrying-a-patch/)
- **A carried patch lets branca read its tables from the zip.** `recipes/patches/branca-0.8.2/0001-read-its-tables-as-package-data.patch` reads branca's colour tables through the package's loader instead of opening paths beside its modules. [Carrying a patch](https://claygendron.github.io/wasi-python/contributing/carrying-a-patch/)
- **Only Faker's own suite loads Faker's pytest plugin.** The guest drivers pass `-p no:faker` to every other session and report one that imported Faker anyway, so no other suite pays for it. [Adding a package](https://claygendron.github.io/wasi-python/contributing/adding-a-package/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "191"
new = [
  "tests/checks/test_v1_3_default_profile.py::test_folium_names_what_the_set_lacks",
  "tests/checks/test_v1_3_default_profile.py::test_rich_refreshes_without_a_thread*",
  "tests/checks/test_v1_3_default_profile.py::test_time_zones_job_matches_native",
  "tests/checks/test_v1_3_default_profile.py::test_terminal_text_job_matches_native",
  "tests/checks/test_v1_3_default_profile.py::test_fake_data_job_matches_native",
  "tests/checks/test_v1_3_default_profile.py::test_web_maps_job_matches_native",
  "tests/checks/test_v1_3_the_zips_directory.py::test_pytz_first_zone_is_bounded*",
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_source_tree_matches_its_tarball[folium]",
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_source_tree_matches_its_tarball[branca]",
]
passes = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pandas-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[matplotlib-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[tqdm-*",
]
grows = ["tests/checks/*"]
growth = "pytz 2026.6, rich 15.0.0, markdown-it-py 4.3.0, mdurl 0.1.2, Pygments 2.21.0, Faker 40.54.0, folium 0.20.0 (less its templates/ scripts), branca 0.8.2 and xyzservices 2026.9.1 join the zip: 1,967 members and about 6.86 MB deflated, measured in scratch with step 70's own packing under the line's Python 3.15.2 (pytz 612 members, 504,821 bytes, under the 0.6 MB line), the zip's directory over them not counted; every start reads a longer directory; pandas imports pytz whenever it is there, so every import pandas and every pandas group grows by pytz's import, and pandas' conftest parametrizes over pytz's zones too (more cases); rich's presence adds tqdm.rich's cases; both binaries change, since the per-call refresh, frozen into them, reseeds Faker's shared generator when an image holds it. Not measured on a built set: this branch's container could build none, so the first built set records every figure"
units = 1
[claim.judge]
"tests/upstream/packages.toml" = "the nine new components name their suites as later, closing with the reserved 193: no group's fuel can be measured before a built set, so none joins a shard"
"context/release-claims/191-pytz-rich-faker-and-folium.toml" = "the release groups' passes and growth move with the nine packages in the zip: pandas' release groups gain pytz's zone cases, tqdm's gains tqdm.rich's, and every release group's start reads a longer directory"
"tests/checks/test_v1_3_the_zips_directory.py" = "PANDAS_FOLDERS gains pytz, since import pandas imports it whenever it is there, as natively; test_import_pandas_loads_exactly_its_packages passes in the guest with it (run 43772062248)"
"tests/checks/test_v1_4_embedding.py" = "test_the_import_path_comes_after_the_runtime stubs pyarrow, which import pandas still looks for and the set lacks, in place of pytz, whose stub the runtime's own pytz now shadows; it counts one HIT pyarrow on both binaries and passes in the guest (run 43772062248)"
"tests/upstream/expected/tqdm-smoke/no-threads.txt" = "tests_rich.py::test_rich_no_total joins: with rich in the zip it runs instead of skipping, and tqdm.rich's Progress refreshes itself on a thread the guest cannot start; tests_synchronisation.py::test_threadpool leaves, since it now errors at setup and never runs (no-asyncio-loop-error)"
"tests/upstream/expected/tqdm-smoke/no-threads-error.txt" = "tests_rich.py::test_rich_no_total joins: the tqdm instance its failed refresh leaves is still in existence at teardown"
"tests/upstream/expected/tqdm-smoke/no-asyncio-loop-error.txt" = "tests_contrib.py::test_map[tqdm_kwargs0] (at teardown) and tests_synchronisation.py::test_threadpool (at setup) join: the set's allocations moved with this change, so the collector frees an earlier asyncio test's stray event loop during them, and its deallocator's unsupported socket close is reported; test_map[tqdm_kwargs0] still fails for want of threads"
"tests/known_gaps.toml" = "tqdm-smoke's three changed classes: no-asyncio-loop-error 12 finding(s), digest ba273df75009; no-threads-error 99, a1fb56cd7644; no-threads 116, c2531945eb68; each computed with scan.digest from its list file, whose additions and removal reproduce run 43772062248's digests c291c93d15f3, d27b32c593cc and ef521d75a97b exactly"
```
