# The release process

This page describes how a release of wasi-python is cut: the version bump, the release workflow, how the tests are split, how the assets are signed, and how they are published. Only the project's maintainer cuts a release.

## Bump the version

The version lives in one place: `__version__` in `src/wasi_python/__init__.py`. `pyproject.toml` reads it from there. The script [`release/version.py`](https://github.com/ClayGendron/wasi-python/blob/main/release/version.py) changes it:

```sh
uv run python release/version.py bump            # the next version, and a CHANGELOG.md section
uv run python release/version.py release --push  # date the section, tag v<version>, push: the release runs
```

A release is the annotated tag `v<version>` on a pushed commit of `main`. Pushing the tag starts the release workflow, `.github/workflows/release.yml`.

## What the release workflow does

The workflow runs these stages, in order:

1. **Build.** It builds the artifact set from the pins on arm64 macOS. It checks that every source tree is its pinned tarball plus exactly the recorded patches.
2. **Rebuild.** Two more jobs rebuild the set from the pins, one on an arm64 Linux runner and one on an x86_64 Linux runner. Each must produce the same `SHA256SUMS` and the same wheel, byte for byte. Nothing is signed or published until they match.
3. **Test in shards.** The tests run in parallel *shards* (slices of the test suite, each a job of its own) on macOS, Linux and Windows at once. The packages' own test suites run in the guest on Linux. One group of numpy's and pandas' tests, and CPython's file-system group, also run on macOS and Windows. `tests/release_shards.toml` lists the shards, and `uv run pytest --shard=<name>` runs one.
4. **Gather.** A job named `gather` reads every shard's record. Nothing is signed or published unless every shard ran exactly its share on the release's bytes and nothing failed.
5. **Attest.** An `attest` job signs build provenance for every asset and verifies it strictly.
6. **Publish.** The workflow publishes a GitHub release with the wheel, the artifact set as `.tar.xz`, and their `SHA256SUMS`. It uploads the wheel to PyPI as `wasi-python` through PyPI's trusted publishing. A version with an `a`, `b` or `rc` suffix is published as a pre-release.

## Two tiers of tests

The tests have two tiers:

- The **normal tier** runs on every check of a change.
- The **release tier** is the slow tests: numpy's and pandas' slow cases, contourpy's slow cases, CPython's tests that need the `cpu` resource, and the whole suite of every pure-Python package the product ships. It runs only before a publication.

Together the tiers hold every test of every package built. The project's rules check that each test lands in exactly one tier, so nothing is left out of both.

## Every job uses the bytes the build made

Every job that checks, signs or publishes uses exactly the bytes the build job made. The build job hands on its upload's artifact id and the SHA-256 of its `SHA256SUMS`, and prints both in its log. Each later job downloads by that id and checks:

- `SHA256SUMS` against the hash;
- every file against `SHA256SUMS`;
- that nothing else is there.

Only then does the job act. Each job holds only the permissions it uses, and every action is pinned by a full commit.

## Signing

Build provenance is signed by the release workflow at the release's tag, and recorded in Sigstore's public log. If the `attest` job fails, nothing is published. Re-run the failed jobs of the same workflow run; its artifacts are kept for 90 days. Never push the tag again. If a re-run stops at a guard ("handed on no artifact id"), re-run all jobs: the build makes the same bytes again.

Users check a signed asset as [Verify a download](../how-to/verify-a-download.md) describes.

## Dry runs

A *dry run* is a manual run of the release workflow. It builds, rebuilds and tests exactly as a release does, but it never signs and never publishes. A signature is permanent in Sigstore's public log, so only a real release signs. A release tag goes only on a commit whose dry run passed on all three systems.

## After publishing

Whoever cut the release compares the published assets with the `SHA256SUMS` in the build job's log: the GitHub release's assets (`gh release download`, then `shasum -a 256 -c`) and PyPI's wheel digest. The result goes in the release's notes.

## See also

- [Building from source](building.md)
- [Review and landing](review-and-landing.md)
- [Artifacts](../reference/artifacts.md)
