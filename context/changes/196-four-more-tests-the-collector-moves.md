# 196: Four more tests the collector moves

## Changelog

### For contributors

- **Four more jinja2 tests the collector moves are named.** The 0.1.5 release run saw two tests join jinja2's asyncio-loop class and two leave it with no change to the code, so the four join the six already named, and the rest of the class is still held exactly. [Two tiers of tests](https://claygendron.github.io/wasi-python/contributing/release-process/#two-tiers-of-tests)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "196"
changed = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[jinja2-r-no-asyncio-loop]"]
passes = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[jinja2-r]"]
fewer = "jinja2-r 548 to 546: TestExtensions::test_debug and TestModuleLoader::test_weak_references, which pass when no leaked event loop is freed during them, are now named collector moves, so their passes leave the count as 182's named tests' did; seen joining no-asyncio-loop in run 43982122112; the owner's choice for such tests, 2026-11-16, \"Stop counting them\""
units = 0
[claim.judge]
"tests/upstream/jinja2.toml" = "no-asyncio-loop names four more collector moves, each seen moving in the 0.1.5 release pull request's run 43982122112 (job 133714403059's moved line): test_debug and test_weak_references joined, test_groupby_tuple_index[<lambda>1] and test_simple_select_attr[<lambda>1] left; 182's \"What is inferred\" provides for adding each test a release run names; the owner's choice, 2026-11-16, \"Stop counting them\""
"tests/upstream/expected/jinja2-r/no-asyncio-loop.txt" = "the two named tests that left in run 43982122112 leave the list, since a named test may not also be listed (182's rules): test_groupby_tuple_index[<lambda>1] and test_simple_select_attr[<lambda>1]"
"tests/known_gaps.toml" = "jinja2-r-no-asyncio-loop 102, ea1eb2ac4985 to 100, 3576e7515999: the judge's class_findings over run 43982122112's members and over the accepted list both give it, once the four moves are left out; the run's red digest, 106 b6be1b9ee02b, was reproduced first"
"context/release-claims/196-four-more-tests-the-collector-moves.toml" = "196's block: jinja2-r's class and its pass count, both release tier"
```
