# 127: the pin moves to wasmtime 50

## Changelog

### For contributors

- **Upstream suites keep their pass counts under wasmtime 50.** Their fuel, last measured under wasmtime 49, is recorded again by a later release-tier run; until then only their passes are compared. [Two tiers of tests](https://claygendron.github.io/wasi-python/contributing/release-process/#two-tiers-of-tests)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "127"
grows = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[*"]
growth = "the upstream suites' fuel was last measured on darwin under wasmtime 49.0.0, and 127 moved the engine to 50.0.1; in CI the upstream groups run on Linux alone, whose fuel is not ratcheted, so the acceptance keeps no fuel of the other engine for these rows until a darwin run of the release tier, local or by a later specification that takes Linux's first measurement, records them again"
[claim.judge]
"context/release-tier-claims.toml" = "the block that claims the upstream suites' fuel drop for the release pull request's acceptance, which reads the ledger beside the news files"
```
