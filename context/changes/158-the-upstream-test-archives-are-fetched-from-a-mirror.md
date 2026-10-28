# 158: the upstream test archives are fetched from a mirror the project controls

## Changelog

### Changed

- **A pinned download may name a copy the project keeps, and it is asked first**: the download script and the upstream test fetcher read a file from its mirror, an asset of a GitHub release of this repository, and from its original host second, and keep it only if its SHA-256 is the pinned one, so the hash is what is trusted, not the host; every fetch says which URL served it. openpyxl's and et-xmlfile's test archives, whose host now answers automated downloads with a challenge page, are the first two files with such a copy, so a contributor's `scripts/00_download.sh --tests` and the judge's runs of their tests work again (spec 158).

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "158"
new = [
  "tests/unit/test_pure_suites.py::test_a_mirrored_file_is_fetched_from_the_mirror_first",
  "tests/unit/test_pure_suites.py::test_a_mirror_that_serves_other_bytes_falls_back_to_the_origin",
  "tests/unit/test_pure_suites.py::test_a_mirror_that_fails_three_times_falls_back_to_the_origin",
  "tests/unit/test_pure_suites.py::test_a_file_neither_url_serves_names_both",
  "tests/unit/test_pure_suites.py::test_a_challenge_page_for_a_test_source_is_refused",
  "tests/unit/test_build_scripts.py::test_the_download_step_tries_the_mirror_first[*",
  "tests/unit/test_build_scripts.py::test_the_two_fetchers_choose_the_same_url[*",
  "tests/unit/test_build_progress.py::test_the_download_step_with_all_asks_each_mirror_first[*",
  "tests/unit/test_scan.py::test_a_mirror_is_this_repositorys_dated_release_asset_of_its_pin",
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_every_mirror_is_this_repositorys_release_asset_of_its_pin",
]
units = 20
```
