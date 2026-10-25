# The release process

This page describes how a release of wasi-python is cut: the version bump, the release pull request from `dev` to `main`, the release workflow, how the tests are split, how the assets are signed, and how they are published. Only the project's maintainer cuts a release.

## Bump the version

The version lives in one place: `__version__` in `src/wasi_python/__init__.py`. `pyproject.toml` reads it from there. The script [`release/version.py`](https://github.com/ClayGendron/wasi-python/blob/main/release/version.py) changes it:

```sh
uv run python release/version.py bump            # the next version, and a CHANGELOG.md section
uv run python release/version.py release --push  # date the section, tag v<version>, push: the release runs
```

A release is the annotated tag `v<version>` on a pushed commit of `main`. Pushing the tag starts the release workflow, `.github/workflows/release.yml`.

## The release pull request

Changes collect on `dev`. A release is a pull request from `dev` to `main`, titled with the version.

1. The two release reviews come first: a fresh reviewer checks the release against the threat model, and another scores the runner's structure. They merge into `dev` before the release pull request opens, so its head carries them.
2. The release pull request's check is the whole workflow on the exact commit `main` will receive: the build, both rebuilds, every shard on three systems, both tiers, the fresh install, and the gather with every goal.
3. When it is green, its result is recorded onto `dev` as one commit.
4. The maintainer moves `main` to that commit, a fast-forward, and pushes the tag.

While a release pull request runs, nothing else merges into `dev`. If something does, the release pull request runs again on the new tip.

The release pull request and the weekly run are being set up. Until they are in place, a manual dry run on `main`'s exact commit (below) is the check before a tag, and the release tier runs there and on the tag.

## What the release workflow does

The workflow runs these stages, in order:

1. **Build.** It builds the artifact set from the pins on arm64 macOS. It checks that every source tree is its pinned tarball plus exactly the recorded patches.
2. **Rebuild.** Two more jobs rebuild the set from the pins, one on an arm64 Linux runner and one on an x86_64 Linux runner. Each must produce the same `SHA256SUMS` and the same wheel, byte for byte. The set's `.tar.xz` is then unpacked and every file in it is checked against that `SHA256SUMS`: no other file, no symlink, and every published file listed. Nothing is signed or published until they match.
3. **Test in shards.** The tests run in parallel *shards* (slices of the test suite, each a job of its own) on macOS, Linux and Windows at once. The packages' own test suites run in the guest on Linux. One group of numpy's and pandas' tests, and CPython's file-system group, also run on macOS and Windows. `tests/release_shards.toml` lists the shards, and `uv run pytest --shard=<name>` runs one.
4. **Gather.** A job named `gather` reads every shard's record. Nothing is signed or published unless every shard ran exactly its share on the release's bytes and nothing failed.
5. **Attest.** An `attest` job signs build provenance for every asset and verifies it strictly.
6. **Publish.** The workflow publishes a GitHub release with the wheel, the artifact set as `.tar.xz`, and their `SHA256SUMS`. It uploads the wheel to PyPI as `wasi-python` through PyPI's trusted publishing. A version with an `a`, `b` or `rc` suffix is published as a pre-release.

## Two tiers of tests

The tests have two tiers:

- The **normal tier** runs on every change: the part a pull request's files need, and in full after each merge into `dev`.
- The **release tier** is the slow tests: numpy's and pandas' slow cases, contourpy's slow cases, CPython's tests that need the `cpu` resource, and the whole suite of every pure-Python package the product ships. It runs on the release pull request, on the tag, and once a week on `dev`.

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

A *dry run* builds, rebuilds and tests exactly as a release does, but it never signs and never publishes. A signature is permanent in Sigstore's public log, so only a real release signs. A release tag goes only on a commit whose dry run passed on all three systems. The release pull request's run is that dry run, on the exact commit tagged.

## The weekly run

Once a week a run on `dev` builds the set twice from the pins, checks that both builds give the same bytes as the set `dev`'s pull requests were tested with, and runs the release tier. It never records a result. When it is red, it opens an issue.

## After publishing

Whoever cut the release compares the published assets with the `SHA256SUMS` in the build job's log: the GitHub release's assets (`gh release download`, then `shasum -a 256 -c`) and PyPI's wheel digest. The result goes in the release's notes.

## See also

- [Building from source](building.md)
- [Review and landing](review-and-landing.md)
- [Artifacts](../reference/artifacts.md)
