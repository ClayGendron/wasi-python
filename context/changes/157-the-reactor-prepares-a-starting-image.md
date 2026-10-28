# 157: The reactor prepares a starting image

## Changelog

### Added

- **Other engines can start every call from a starting image.** The snapshot binary exports `prepare`, which runs your setup code once and leaves memory ready to copy into each new instance. [Embed from other languages](https://claygendron.github.io/wasi-python/how-to/embed-from-other-languages/#start-each-call-from-a-starting-image)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "157"
grows = ["tests/checks/test_v1_4_prepare.py::test_the_everything_prelude_prepares"]
growth = "the restored call's fuel is kept as a fact, no longer as the metric: a call from an image that holds numpy's random module spends a number of instructions that moves by up to a tenth of a percent from run to run, even under the judge's seeded entropy and pinned clocks, so the judge's exact fuel could not hold it"
```
