# 188: soupsieve 4.1.1

## Changelog

### Security

- **CSS selectors no longer slow down on deeply nested pages.** soupsieve moves to 4.1.1, which fixes two advisories, GHSA-mmhr-3c5m-f64f (descendant selectors on nested documents) and GHSA-8jvp-3x96-xpqw (`:has()`), where a small hostile page could keep `select()` busy for seconds to minutes. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)

### Upgrading

- **soupsieve 4.1.1 inside, from 3.0.4.** A selector no longer matches inside an HTML `template`, and an `iframe`'s contents are no longer a separate document. Check code that selects inside either. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)
- **Some selectors now match as a browser does.** Attributes HTML treats as case insensitive (`rel`, `method`, `lang`, `dir`) match that way; `[attr=value]` no longer ignores a trailing newline; `:checked`, `:lang()`, `:enabled`, `:disabled`, `:in-range` and `:out-of-range` follow the HTML specification. Read soupsieve's 4.0 to 4.1.1 notes. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)

## Package rows

| HTML and XML | beautifulsoup4 4.15.0, soupsieve 4.1.1 | parse messy HTML, CSS selectors |

## Claims

```toml
[[claim]]
spec = "188"
passes = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[soupsieve-smoke]",
]
grows = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[soupsieve-smoke]",
  "tests/checks/test_v1_3_default_profile.py::test_markup_job_matches_native",
]
growth = "soupsieve 4.1.1 replaces 3.0.4: test_level1's files run 36% more Python calls natively (the pre-build review) and 4.x caches matches per element, so the smoke group's and the markup job's fuel move; the run's figures are in the specification's landing notes"
[claim.judge]
"tests/upstream/soupsieve.toml" = "the wheel moves to soupsieve 4.1.1; soupsieve-r gains the no-threads row for 4.1's test_threads.py, matched on the guest's own message"
"tests/upstream/expected/soupsieve-r/no-threads.txt" = "the five thread tests of soupsieve 4.1.1 that start a thread, which the guest cannot"
"tests/known_gaps.toml" = "soupsieve-r-no-threads, 5 finding(s), digest 61cf3b317d0f, computed with scan.report from the list file's five node ids"
"context/release-claims/188-soupsieve-4-1-1.toml" = "soupsieve-r's rows move with soupsieve 4.1.1"
```
