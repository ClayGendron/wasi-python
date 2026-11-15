# 190: pydantic-core and pydantic

## Changelog

### New

- **pydantic is built in: typed models over a Rust core.** `import pydantic` gives pydantic 2.14.3 with annotated-types 0.8.0 and typing-inspection 0.4.5 in the zip, over pydantic-core 2.50.4 compiled from Rust into both binaries, with native pydantic's results. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)

### For contributors

- **orjson moves to PyO3 0.30 and the system allocator.** Every Rust module shares one PyO3, so orjson carries `recipes/patches/orjson-3.13.0/0002-pyo3-0-30.patch` to build on pydantic-core's PyO3 0.30.1, and `recipes/patches/orjson-3.13.0/0003-no-global-allocator.patch` so its allocator no longer serves pydantic-core's aligned allocations. [Building from source](https://claygendron.github.io/wasi-python/contributing/building/)

## Package rows

| pydantic-core | 2.50.4 | Built in, compiled from Rust: the core of pydantic 2.14.3, which the zip carries with annotated-types and typing-inspection; validation, serialization, JSON and JSON Schema, with native pydantic's results. A recursive model nests at most 49 levels. |

## Claims

```toml
[[claim]]
spec = "190"
new = [
  "tests/checks/test_v1_3_rust.py::test_pydantic_core_is_built_in",
  "tests/checks/test_v1_3_rust.py::test_a_panic_after_pydantic_validates_is_caught",
  "tests/checks/test_v1_3_rust.py::test_pydantic_core_reads_entropy_through_the_wrap",
  "tests/checks/test_v1_3_rust.py::test_pydantic_models_job_matches_native",
  "tests/checks/test_rules.py::test_modules_txt_lists_each_rust_module",
  "tests/checks/test_rules.py::test_orjson_carries_the_patches_the_owner_chose",
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_the_rust_lock_keeps_the_packages_versions",
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_the_pinned_pydantic_requires_the_pinned_core",
]
retired = [
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_the_rust_lock_keeps_orjsons_versions",
]
changed = []
passes = []
grows = []
units = 6
[claim.judge]
"tests/harness/scan.py" = "the Rust lock holds each crate at exactly the highest version the packages' own locks name on its semver line, as 187's rule held orjson's, with two named crates the umbrella already held above them (portable-atomic 1.15.0, syn 2.0.119), and one PyO3, 0.30.1; the pydantic wheel requires the pinned core; modules.txt lists each Rust module; orjson carries its three patches"
"tests/harness/pins.py" = "pydantic-core's sdist is a source tree the tree check reads"
"tests/harness/needs.py" = "pydantic-core joins the built source components"
"tests/harness/paths.py" = "pydantic-core, pydantic, annotated-types and typing-inspection join the packages and the licence components"
"tests/upstream/packages.toml" = "the four packages' suites are later, closing with 194, since each smoke group needs its fuel measured on a built set and each expected class reasoned from a run; PyO3 is reached through pydantic-core once its suite runs"
"tests/checks/test_rules.py" = "two rules: modules.txt lists each Rust module, and orjson carries the patches the owner chose"
"tests/harness/jobs.py" = "the golden job pydantic_models joins the jobs"
```
