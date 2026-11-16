# 194: the pydantic suites in the guest

## Changelog

### For contributors

- **pydantic's own tests run in the sandbox.** The suites of pydantic-core, pydantic, annotated-types and typing-inspection run in the guest from their sdists: a smoke group of each in every merge's run, pydantic-core's and pydantic's on Windows in the merge-grade run, and the rest in the release tier, so Rust panics are judged as they unwind. [Adding a package](https://claygendron.github.io/wasi-python/contributing/adding-a-package/)

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
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pydantic-smoke-no-asyncio-loop]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pydantic-smoke-package-in-zip]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pydantic-smoke-wasm-recursion-guard]",
]
[claim.judge]
"tests/upstream/pydantic-core.toml" = "pydantic-core's own suite from its sdist: a smoke group in the normal tier, every other test file in the release tier, benchmarks and the docstring examples left out, a no-processes class and a pydecimal-exponents class; the release group's fuel measured, 153.5 G in run 43888443839, the smoke group's 62.4 G in run 43912197491 on windows, each cap the rule's; the smoke group carries drawn_ids, since its ids carry a uuid drawn at import, an address and sets in hash order"
"tests/upstream/pydantic.toml" = "pydantic's own suite from its sdist: a smoke group in the normal tier, every other test file in the release tier, benchmarks, mypy, the installed plugin, the documentation's examples and the source-file export test left out; the smoke group's no-threads, no-asyncio-loop, package-in-zip and wasm-recursion-guard classes and the release group's no-processes and no-asyncio-loop, each written from runs 43887736757 and 43888443839 (the same findings on linux and windows); both groups' fuel measured there, 78.8 G and 190.1 G, each cap the rule's"
"tests/upstream/annotated-types.toml" = "annotated-types' own suite from its sdist, whole, as its smoke group; its fuel measured, 11.4 G in run 43912197491, its cap the rule's"
"tests/upstream/typing-inspection.toml" = "typing-inspection's own suite from its sdist, whole, as its smoke group; its fuel measured, 11.2 G in run 43912197491, its cap the rule's"
"tests/upstream/packages.toml" = "pydantic-core, pydantic, annotated-types and typing-inspection name their suites; PyO3 is reached through pydantic-core's"
"tests/upstream/expected/pydantic-core-r/no-processes.txt" = "13 tests that start Python again in another process, found natively with a stand-in that refuses to start one"
"tests/upstream/expected/pydantic-r/no-processes.txt" = "6 tests that import pydantic or pickle a model in another process, found natively the same way"
"tests/upstream/expected/pydantic-smoke/no-threads.txt" = "the test that rebuilds a model from two threads, found natively with a stand-in that refuses to start one"
"tests/upstream/expected/pydantic-smoke/no-asyncio-loop.txt" = "test_async and test_async_func fail on asyncio's loop, and test_item_method and test_field_that_is_being_validated_is_excluded_from_validator_values carry the leaked loop's report, as runs 43887736757 and 43888443839 show on linux and windows"
"tests/upstream/expected/pydantic-smoke/package-in-zip.txt" = "test_type_checking_model_dump_signature_in_sync_with_base_model loads pydantic.root_model again from its file, which is bytecode in the zip"
"tests/upstream/expected/pydantic-smoke/wasm-recursion-guard.txt" = "test_serialization_depth_exceeded_error_discriminated_union expects a depth warning from 1,000 levels that the wasm guard of 49 levels does not give"
"tests/upstream/expected/pydantic-core-r/pydecimal-exponents.txt" = "the four cases of test_decimal_three_tuple_constructor_invalid whose exponent is plus or minus 10**30, which PyPy skips for unbounded exponents, as _pydecimal's are"
"tests/upstream/expected/pydantic-r/no-asyncio-loop.txt" = "test_deprecated_validate_arguments.py's test_async fails on asyncio's loop and test_config_title carries the leaked loop's report, run 43888443839"
"tests/known_gaps.toml" = "the eight classes' gaps, each computed with scan.digest from its list file: pydantic-core-r-no-processes 13 finding(s), digest d4bce486ff96; pydantic-core-r-pydecimal-exponents 4, 69db45d68c2a; pydantic-r-no-processes 6, a243e3dc9965; pydantic-r-no-asyncio-loop 2, 07e94848cc3e; pydantic-smoke-no-threads 1, 47a860157c80; pydantic-smoke-no-asyncio-loop 4, ec4eb17ca43d; pydantic-smoke-package-in-zip 1, 9768be142ca0; pydantic-smoke-wasm-recursion-guard 1, e3cafde1091b"
"tests/release_shards.toml" = "the four smoke groups join upstream-pure-smoke-b; pydantic-core's and pydantic's also run on Windows in upstream-windows-pydantic; their release groups form upstream-release-070, 1.95 minutes measured in run 43888443839"
"tests/harness/packages.py" = "SMOKE_TOTAL_BOUND rises from 1.2 T to 1.37 T, the head's test-source smoke groups (1,346.8 G, the four new ones 163.7 G measured in runs 43887736757 and 43912197491) plus 17 G rounded up to 10 G; a group's drawn_ids key, with its reason, digests its counted passed ids (the collector's moves left out, as for every group) in their drawn form, and a rule refuses the key without its reason"
"tests/unit/test_packages.py" = "four rows: a drawn_ids group digests the same tests the same when their ids carry another uuid, address or set order, and a group without the key does not; a drawn form keeps apart parameters that only reorder; the key without its reason is a rule error; a drawn group leaves the collector's moves out of its digest"
"tests/harness/gather.py" = "G5's row for an upstream suite names each system's passes and passed digest"
"tests/unit/test_gather.py" = "a row: G5's difference names each system's passes and digest"
"tests/harness/pins.py" = "pydantic's, annotated-types' and typing-inspection's sdists are test sources"
"tests/harness/upstream.py" = "the four families join PURE_SUITES; drawn_form reads an id's uuid and repr address as one placeholder and a set display's members in sorted order, for a group whose drawn_ids says so"
"tests/upstream/kit-extra.txt" = "seven test-only wheels: dirty-equals, inline-snapshot with asttokens and executing, pytest-mock, and jsonschema 4.17.3 with pyrsistent for pydantic's schema check"
"tests/lint/budget.toml" = "the four families' caps, each twice its smoke group's measured fuel: pydantic's from run 43887736757, the other three from run 43912197491"
"context/release-claims/194-the-pydantic-suites-in-the-guest.toml" = "the two release groups and their four classes (no-processes and pydecimal-exponents in pydantic-core-r, no-processes and no-asyncio-loop in pydantic-r) are new release-tier checks"
```
