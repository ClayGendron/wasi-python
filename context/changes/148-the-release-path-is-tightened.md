# 148: the release path is tightened

## Changelog

### Security

- **The release's write token reaches only the step that creates the GitHub release, and the wheel goes to PyPI through the workflow's pinned uv** (`uv publish --trusted-publishing always`) instead of a third-party container named by a tag (spec 148). The wheel on PyPI no longer carries a PyPI-side provenance object; its GitHub attestation, which the verify page documents, is unchanged.
- **`SECURITY.md` names wasmtime's advisories of 2026-10-19**, none of which reaches the runner's wasmtime 50.0.0 (spec 148).

### Changed

- **A change to the agents' settings or instructions (`.claude/`, `.agents/`, `AGENTS.md`, `CLAUDE.md`, at any depth) is no longer documentation only**: it runs the quick check alone, and carries a news file and a review (spec 148).
- **A pull request's check refuses GitHub's `skip-checks: true` trailer** beside the skip words, reads a path git would quote by its real name, judges a pull request again when its base is edited, and re-reads an edited title or description, re-using the run before it when that run is green on the same head (spec 148).
- **The install page says what a umask of `077` changes** for the compiled-module cache, and the reviewer's checklist reads every change to the workflow and the plan as code (spec 148).

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "148"
new = ["tests/checks/test_rules.py::test_a_pull_request_is_judged_again_when_its_base_or_description_changes"]
units = 55
```
