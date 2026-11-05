# 185: The wheel on PyPI carries its provenance

## Changelog

### Security

- **The wheel on PyPI carries its provenance again.** PyPI's page names the repository, workflow and commit that published it. 0.1.2 and 0.1.3 went to PyPI without it and cannot be changed; their GitHub attestation covers the same file and still verifies. [Verify a download](https://claygendron.github.io/wasi-python/how-to/verify-a-download/)

### For contributors

- **A release reads PyPI back.** After the upload, the release checks that PyPI serves the wheel's own SHA-256 with provenance from this repository, and is red otherwise. Every release-shaped run rehearses the path first, and a tag signs nothing until the rehearsal passes. [The release process](https://claygendron.github.io/wasi-python/contributing/release-process/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "185"
units = 55
[claim.judge]
"tests/harness/scan.py" = "rule 20: pypi signs the wheel with astral-sh/attest-action at its pin, on uv 0.13.5 by checksum with release/ checked out, holds dist/ to the wheel and its attestation, and uploads dist/* without --no-attestations; rule 21: pypi-verify reads PyPI's digest and provenance back and verifies the signature, fail-closed, and pypi-rehearsal runs the path short of signing and uploading on every release-shaped run; attest waits on the rehearsal; rule 14, the checkout scan and TAG_JOBS admit the two jobs; asked for by the owner on 2026-11-05"
"tests/unit/test_scan.py" = "the release fixtures gain the new pypi, pypi-verify and pypi-rehearsal and attest's need of the rehearsal; 34 more binding rows, one per clause of rules 20 and 21, among them the upload of dist/*.whl that would drop the attestation, a skipped signature or staging check, and a step between the staging check and the upload"
"tests/unit/test_pypi_readback.py" = "the read-back's verdicts on recorded PyPI answers, with the network and the waits replaced"
"tests/checks/test_rules.py" = "a pushed tag also runs pypi-rehearsal, which attest needs"
```
