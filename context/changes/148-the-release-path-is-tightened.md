# 148: the release path is tightened

## Changelog

### Security

- **The release's write token reaches only the step that publishes.** Only the step that creates the GitHub release holds it, and the wheel goes to PyPI through the workflow's pinned uv instead of a third-party container. [Verify a download](https://claygendron.github.io/wasi-python/how-to/verify-a-download/)
- **The security policy names wasmtime's advisories of 2026-10-19.** None of them reaches the wasmtime this release runs, 50.0.0, the critical [GHSA-mghf-wjfp-p5xm](https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-mghf-wjfp-p5xm) included. [Three wasmtime fixes, in wasmtime itself](https://claygendron.github.io/wasi-python/explanation/security-model/#three-wasmtime-fixes-in-wasmtime-itself)

### Fixed

- **The install page says what a umask of `077` changes.** It now says how that umask affects the compiled module's cache folder. [Where the compiled module is kept](https://claygendron.github.io/wasi-python/get-started/install/#where-the-compiled-module-is-kept)

### Upgrading

- **The wheel on PyPI no longer carries PyPI's own provenance.** Check a download by its GitHub attestation, which is unchanged. [Verify a download](https://claygendron.github.io/wasi-python/how-to/verify-a-download/)

### For contributors

- **Changes to the agents' settings are reviewed like code.** A change to `.claude/`, `.agents/`, `AGENTS.md` or `CLAUDE.md` needs a news file and a review, and a pull request's check refuses GitHub's `skip-checks: true` trailer and judges an edited base or description again. [What a pull request runs](https://claygendron.github.io/wasi-python/contributing/review-and-landing/#what-a-pull-request-runs)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "148"
new = ["tests/checks/test_rules.py::test_a_pull_request_is_judged_again_when_its_base_or_description_changes"]
units = 62
```
