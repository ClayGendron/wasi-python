# 127: the pin moves to wasmtime 50

## Changelog

### Changed

- The release acceptance keeps no fuel measured under another wasmtime for a check that CI runs on Linux alone, so the upstream suites' accepted fuel, last measured on darwin under wasmtime 49, is dropped at the first release acceptance after the engine moved to 50; the next darwin run of the release tier records it again.

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "127"
grows = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[*"]
growth = "the upstream suites' fuel was last measured on darwin under wasmtime 49.0.0, and 127 moved the engine to 50.0.1; in CI the upstream groups run on Linux alone, whose fuel is not ratcheted, so the acceptance keeps no fuel of the other engine for these rows until a darwin run of the release tier measures them again"
[claim.judge]
"context/release-tier-claims.toml" = "the block that claims the upstream suites' fuel drop for the release pull request's acceptance, which reads the ledger beside the news files"
```
