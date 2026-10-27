# 127: the pin moves to wasmtime 50

## Changelog

### Changed

- **The upstream suites' fuel is measured afresh under wasmtime 50** (spec 127). The figures recorded under wasmtime 49 on darwin are dropped at the first release acceptance after the move, since in CI the suites run on Linux, whose fuel is not compared; the rows keep their pass counts, and fuel is recorded again when a darwin run of the release tier, local or by a later specification that takes Linux's first measurement, records them.

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
