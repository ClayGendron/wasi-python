# 172: a class for tests the collector moves

## Changelog

### For contributors

- **Two tqdm tests that trade causes no longer fail a run.** Which of the two meets a leftover asyncio event loop depends on the build's memory layout; they now share one failure class that names them, so either order passes, and each must still fail for a known cause. [Two tiers of tests](https://claygendron.github.io/wasi-python/contributing/release-process/#two-tiers-of-tests)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "172"
new = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[tqdm-smoke-collector-timing]"]
changed = [
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[tqdm-smoke-no-asyncio-loop-error]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[tqdm-smoke-no-threads-error]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[tqdm-smoke-no-threads]",
]
units = 11
[claim.judge]
"tests/harness/upstream.py" = "a class may name its tests (nodes) and claim more than one outcome (outcomes): it claims those tests alone, before any other class, and only for its own causes; a pass, a skip or another cause of a named test is a finding, and its list is its nodes; the rules refuse a node-limited class with no node, unsorted or repeated nodes, a node two such classes name, outcome and outcomes together, outcomes without nodes and nodes in CPython's family; approved by the owner on 2026-10-31"
"tests/upstream/tqdm.toml" = "the class collector-timing names test_iter_basic_overhead and test_iter_overhead_simplebar_hard, which the collector's timing sorts into no-threads, no-threads-error or no-asyncio-loop-error by the set's allocations (flipped on #67, #71 and #81); it takes failed and error, and its pattern is the union of no-threads' and no-asyncio-loop-error's, the three causes the owner named on 2026-10-31; neither test passes in either state"
"tests/upstream/expected/tqdm-smoke/no-asyncio-loop-error.txt" = "test_iter_basic_overhead leaves for collector-timing"
"tests/upstream/expected/tqdm-smoke/no-threads-error.txt" = "test_iter_overhead_simplebar_hard leaves for collector-timing"
"tests/upstream/expected/tqdm-smoke/no-threads.txt" = "test_iter_overhead_simplebar_hard leaves for collector-timing"
"tests/known_gaps.toml" = "the new class collector-timing is a gap (2 findings, digest 972ddf3843c5) closed by docs/reference/limitations.md as its siblings are; no-asyncio-loop-error (10, 5e4afad71ed0), no-threads-error (98, 77e1b0dfaea7) and no-threads (116, 53093d631048) lose one test each; the same digests in both of the collector's states, measured on three sets; approved by the owner on 2026-10-31"
```
