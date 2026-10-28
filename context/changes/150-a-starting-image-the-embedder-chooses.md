# 150: A starting image the embedder chooses

## Changelog

### Added

- **Start every call from your own snapshot.** Run your setup code once, imports, data and functions, with `make_snapshot`, or import every package with `make_package_snapshot()`, then pass `snapshot=` to `run` or `Session`: each call is still a fresh, sealed instance, and skips the seconds its imports took. [Snapshots](https://claygendron.github.io/wasi-python/how-to/snapshots/)

### Fixed

- **The judge keeps a restored call's fuel as a fact where it cannot repeat.** A call from a snapshot that holds numpy's random module spends a number of instructions that moves by up to a few percent from run to run, so four snapshot rows record that fuel as a fact, and the judge's exact fuel rows stay exact.

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "150"
grows = [
  "tests/checks/test_v1_4_starting_image.py::test_a_snapshot_runs_like_a_fresh_run",
  "tests/checks/test_v1_4_starting_image.py::test_a_call_sees_no_other_calls_mutations",
  "tests/checks/test_v1_4_starting_image.py::test_randomness_differs_across_calls",
  "tests/checks/test_v1_4_starting_image.py::test_the_image_of_every_package_runs_a_hello_and_a_plot",
]
growth = "the restored call's fuel is kept as a fact, no longer as the metric: a call that imports numpy's random module, as pandas and scikit-learn do, spends a number of instructions that moves by up to a few percent from run to run, even with a fixed seed, so the judge's exact fuel could not hold it"
```
