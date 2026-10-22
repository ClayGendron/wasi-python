# Verify a download

This guide shows how to check that a release asset you downloaded is the one this project's
release workflow built. Do it before you run the artifacts in a host of your own, or before you
mirror them.

## What a release publishes

Each GitHub release carries these assets:

- the `wasi-python` wheel;
- the artifact set (`python.wasm`, `python-snapshot.wasm`, `python-stdlib.zip`, `MANIFEST`,
  `SHA256SUMS` and the licence notices) as a `.tar.xz` archive;
- a `SHA256SUMS` file listing the SHA-256 of those assets.

The same wheel is published on PyPI as `wasi-python`. See [Artifacts](../reference/artifacts.md)
for what each file holds.

## Check an asset's provenance with `gh`

Every release asset carries *build provenance*: a statement, signed by the release workflow,
that names the source and the workflow that built the file. The GitHub CLI, `gh`, checks it. Log
`gh` in first, then run this, with `<asset>` the file you downloaded and `<version>` the release's
version:

```
gh attestation verify <asset> --repo ClayGendron/wasi_python \
  --signer-workflow ClayGendron/wasi_python/.github/workflows/release.yml@refs/tags/v<version> \
  --source-ref refs/tags/v<version> --deny-self-hosted-runners
```

The command fails if any check does not hold. When it passes, it has shown that:

- the asset was signed by this repository's release workflow, `release.yml`;
- the workflow ran at the release's tag, `v<version>`, and the source it built was that tag;
- the workflow ran on a GitHub-hosted runner, not a self-hosted one.

`--signer-workflow` matches a prefix of the signer's identity. That is why it carries the `@`
and the tag: together they pin the workflow file exactly.

The first alpha, `0.1.0a1`, has no attestation. Every release after it carries one.

## Check an asset without `gh`

Without `gh`, check the asset against the release's `SHA256SUMS`: download the asset and
`SHA256SUMS` into one folder and run `shasum -a 256 -c --ignore-missing SHA256SUMS` there
(`sha256sum -c --ignore-missing SHA256SUMS` on Linux). The asset should print `OK`.

A matching hash shows that the file is the one the list names, so it catches a damaged or
partial download. The list comes from the same release page, so it does not show who built the
file. Only the attestation does.

## Check the set the wheel installed

You do not need to check the wheel's own copy of the artifact set by hand. `run` and `Session`
check the set they find against its `SHA256SUMS` before they use it, and compile only the bytes
they checked. That check catches a file changed or half-written since the build. It does not
catch a set rewritten whole together with its `SHA256SUMS`, so keep the set where only you can
write.

## In one line

Run `gh attestation verify` with the workflow and the tag pinned to prove where an asset came
from, or check it against `SHA256SUMS` to prove it arrived whole.
