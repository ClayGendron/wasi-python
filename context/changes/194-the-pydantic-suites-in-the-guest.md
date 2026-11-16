# 194: the pydantic suites in the guest

## Changelog

### For contributors

- **pydantic's own tests run in the sandbox.** pydantic-core's, pydantic's, annotated-types' and typing-inspection's suites run in the guest from their sdists, a smoke group of each in every pull request's run, pydantic-core's and pydantic's on Windows too, and the rest in the release tier, so Rust panics are judged unwinding. [Adding a package](https://claygendron.github.io/wasi-python/contributing/adding-a-package/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "194"
new = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pydantic-core-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pydantic-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[annotated-types-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[typing-inspection-smoke]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pydantic-smoke-no-threads]",
]
[claim.judge]
"tests/upstream/pydantic-core.toml" = "pydantic-core's own suite from its sdist: a smoke group in the normal tier, every other test file in the release tier, benchmarks and the docstring examples left out, one no-processes class; each group's fuel an upper estimate marked provisional until a built set measures it"
"tests/upstream/pydantic.toml" = "pydantic's own suite from its sdist: a smoke group in the normal tier, every other test file in the release tier, benchmarks, mypy, the installed plugin, the documentation's examples and the source-file export test left out, a no-processes and a no-threads class; each group's fuel an upper estimate marked provisional until a built set measures it"
"tests/upstream/annotated-types.toml" = "annotated-types' own suite from its sdist, whole, as its smoke group; its fuel an upper estimate marked provisional"
"tests/upstream/typing-inspection.toml" = "typing-inspection's own suite from its sdist, whole, as its smoke group; its fuel an upper estimate marked provisional"
"tests/upstream/packages.toml" = "pydantic-core, pydantic, annotated-types and typing-inspection name their suites; PyO3 is reached through pydantic-core's"
"tests/upstream/expected/pydantic-core-r/no-processes.txt" = "13 tests that start Python again in another process, found natively with a stand-in that refuses to start one"
"tests/upstream/expected/pydantic-r/no-processes.txt" = "6 tests that import pydantic or pickle a model in another process, found natively the same way"
"tests/upstream/expected/pydantic-smoke/no-threads.txt" = "the test that rebuilds a model from two threads, found natively with a stand-in that refuses to start one"
"tests/known_gaps.toml" = "the three classes' gaps: pydantic-core-r-no-processes 13 finding(s), digest d4bce486ff96; pydantic-r-no-processes 6, a243e3dc9965; pydantic-smoke-no-threads 1, 47a860157c80; each computed with scan.digest from its list file"
"tests/release_shards.toml" = "the four smoke groups join upstream-pure-smoke-b; pydantic-core's and pydantic's also run on Windows in upstream-windows-pydantic; their release groups form upstream-release-070, its minutes estimated"
"tests/harness/packages.py" = "SMOKE_TOTAL_BOUND rises from 1.2 T to 1.4 T, the head's test-source smoke groups plus 17 G rounded up to 10 G, provisionally: the four new groups record upper estimates, 193 G together"
"tests/harness/pins.py" = "pydantic's, annotated-types' and typing-inspection's sdists are test sources"
"tests/harness/upstream.py" = "the four families join PURE_SUITES"
"tests/upstream/kit-extra.txt" = "seven test-only wheels: dirty-equals, inline-snapshot with asttokens and executing, pytest-mock, and jsonschema 4.17.3 with pyrsistent for pydantic's schema check"
"tests/lint/budget.toml" = "the four families' caps, provisional: twice each smoke group's cap until a run measures it"
"context/release-claims/194-the-pydantic-suites-in-the-guest.toml" = "the two release groups and their no-processes classes are new release-tier checks"
```
