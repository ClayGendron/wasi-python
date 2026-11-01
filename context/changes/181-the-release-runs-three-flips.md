# 181: The release runs three flips

## Changelog

### For contributors

- **Three test results that moved with no code change are re-recorded.** The plain reactor's fuel in the results check is reported, not ratcheted, since its hash seed is random; jinja2's two asyncio classes return to the members earlier releases held; and fontTools' `test_split` leaves the counted-clock class, as it now passes. [Two tiers of tests](https://claygendron.github.io/wasi-python/contributing/release-process/#two-tiers-of-tests)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "181"
changed = [
    "tests/checks/test_v1_4_results.py::test_both_binaries_return_the_same_records[False]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[jinja2-r-no-asyncio-loop-error]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[jinja2-r-no-asyncio-loop]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[fonttools-r-rest-counted-clock]",
]
passes = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[fonttools-r-rest]"]
grows = ["tests/checks/test_v1_4_results.py::test_both_binaries_return_the_same_records[False]"]
growth = "the plain reactor seeds CPython's hash secret from the host's random_get, so this row's fuel moves by up to about 0.3 M from run to run (266,861,498 to 267,018,014 on macOS in run 41346031022, same code and set); it is now a fact, not a metric, so its macOS fuel is no longer recorded; the snapshot row [True] stays a metric; approved by the owner on 2026-11-01"
units = 0
[claim.judge]
"tests/checks/test_v1_4_results.py" = "the plain reactor's row reports its fuel as a fact, since its hash seed is random; the snapshot row keeps its fuel metric; approved by the owner on 2026-11-01"
"tests/upstream/expected/jinja2-r/no-asyncio-loop-error.txt" = "jinja2-r's collector-timing flip, which 172's Decision 5 left uncovered: this set gives the state 0.1.0 to 0.1.2 held, so the list returns to its content before bedf8f30 (gains test_custom_async_iteratable_filter[asyncio-<lambda>0] and test_sum[<lambda>1], loses test_custom_async_filter[asyncio] and test_sum[<lambda>0]); measured in run 41346031022; 552 passes unchanged; approved by the owner on 2026-11-01, 182 to follow"
"tests/upstream/expected/jinja2-r/no-asyncio-loop.txt" = "jinja2-r's collector-timing flip, which 172's Decision 5 left uncovered: this set gives the state 0.1.0 to 0.1.2 held, so the list returns to its content before bedf8f30 (gains test_streamfilter_extension, test_balancing, test_custom_async_iteratable_filter[asyncio-<lambda>0] and test_sum[<lambda>1], loses test_extend_late and test_line_syntax); measured in run 41346031022; approved by the owner on 2026-11-01, 182 to follow"
"tests/upstream/expected/fonttools-r-rest/counted-clock.txt" = "TimerTest::test_split now passes: a GC pass, which reads the counted clock at its start and end, falls in the test's second timed interval on this set, so the second lap is the longer; the two ttx cases did not move; measured in run 41346031022; approved by the owner on 2026-11-01"
"tests/known_gaps.toml" = "three gaps re-pinned to run 41346031022's membership: jinja2-r-no-asyncio-loop-error 13, ba56b641f579 and jinja2-r-no-asyncio-loop 104, 959d6ba605ec (their content before bedf8f30, the collector-timing flip); fonttools-r-rest-counted-clock 2, 0c61ab6175e3 (test_split passes when a GC pass reads the counted clock during its second timed interval); approved by the owner on 2026-11-01"
"context/release-claims/181-the-release-runs-three-flips.toml" = "181's block: the two release-tier families' classes and fonttools-r-rest's pass count"
```
