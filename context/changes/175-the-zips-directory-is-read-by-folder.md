# 175: The zip's directory is read by folder

## Changelog

### Faster

- **A plain start reads only the packages it uses.** An empty program on the plain binary now runs in 135 million instructions, from 284 million, and on the snapshot in 42 million, from 55 million. A package added to the runtime costs a start almost nothing until a program imports it. [How it works](https://claygendron.github.io/wasi-python/explanation/how-it-works/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "175"
new = [
  "tests/checks/test_v1_3_the_zips_directory.py::test_a_plain_start_grows_at_most_2k_fuel_per_member*",
  "tests/checks/test_v1_3_the_zips_directory.py::test_a_reread_after_invalidate_caches_is_the_folder_read",
  "tests/checks/test_v1_3_the_zips_directory.py::test_a_first_resource_read_loads_its_folder*",
  "tests/checks/test_v1_3_the_zips_directory.py::test_a_read_after_invalidate_caches_reads_again_first*",
  "tests/checks/test_v1_3_the_zips_directory.py::test_pandas_styler_reads_its_templates",
  "tests/checks/test_v1_3_the_zips_directory.py::test_import_pandas_loads_exactly_its_packages",
  "tests/checks/test_v1_3_the_zips_directory.py::test_metadata_and_module_listings_match_the_whole_read",
  "tests/checks/test_v1_3_the_zips_directory.py::test_a_prefixed_zipimporter_answers_as_the_whole_read",
  "tests/checks/test_v1_3_the_zips_directory.py::test_namespaces_and_submodules_across_an_invalidation",
  "tests/checks/test_v1_3_the_zips_directory.py::test_a_zip_on_the_import_path_is_read_whole",
  "tests/checks/test_v1_3_the_zips_directory.py::test_teardown_does_not_free_the_stdlib_directory*",
  "tests/checks/test_v1_3_the_zips_directory.py::test_a_load_that_raises_is_tried_again",
]
retired = [
  "tests/checks/test_v1_3_the_zips_directory.py::test_a_plain_start_grows_at_most_30k_fuel_per_member",
  "tests/checks/test_v1_3_the_zips_directory.py::test_a_reread_after_invalidate_caches_is_the_fast_read",
]
grows = ["tests/checks/*"]
growth = "The stdlib zip gains its folder table, an archive comment of 2,815 bytes (57,492,608 to 57,495,423 against dev's set at a0b1171d), and python.wasm the folder reader's bytecode (100,638,734 to 100,660,530 with 176's hook); python-snapshot.wasm falls 97,597 bytes. Fuel falls almost everywhere: a plain start 283,901,206 to 135,278,097, a snapshot start 54,696,220 to 41,551,326 (darwin arm64, against dev's set at 2ec3c1ee built from the same tree). A plain call pays a folder's members the first time it uses the folder, about 25 k fuel a member, once per call: tzdata's 627 on its first import"
units = 23
[claim.judge]
"tests/checks/test_v1_3_the_zips_directory.py" = "Decision 8: the plain start's bound per member moves from 30,000 to 2,000 fuel, for a start, `import pandas` and a first get_data, since the padding is now three tabled folders no program touches (measured 9, 55 and 7 fuel a member; 27.1 k today); the re-read's bound too, and it expects \"folders\"; the gate expects \"folders\" on the plain binary and \"fast\" on the snapshot; the zone check's baseline imports tzdata.zoneinfo on both binaries, so a first zone less it still measures the resource read alone, its bounds unmoved; the fast reader's check compares the plain dict with zipimport's as a dict once every folder is loaded, each folder's children in order, and keeps its list equality on the snapshot. START_FACTOR stays 3: the specification moved it to 2 on a projected plain start of 113 M, and the measured ratio is 3.26 with this specification alone (135.3 M over 41.6 M) and 3.75 with 176 (132.1 M over 35.2 M), so the stricter factor holds"
"tests/harness/zips.py" = "small.zip and padded.zip get step 70's folder table, written afresh for their own directories, so each pad is one tabled folder; the cache folder moves from -v2 to -v3, so no zip made before the table is read"
```
