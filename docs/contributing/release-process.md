# The release process

This page describes how a release of wasi-python is cut: the version bump, the release pull request from `dev` to `main`, the release workflow, how the tests are split, how the assets are signed, and how they are published. Only the project's maintainer cuts a release.

## Bump the version

The version lives in one place: `__version__` in `src/wasi_python/__init__.py`. `pyproject.toml` reads it from there. The script [`release/version.py`](https://github.com/ClayGendron/wasi-python/blob/main/release/version.py) changes it:

```sh
uv run python release/version.py bump            # the next version; the news files into CHANGELOG.md
uv run python release/version.py date            # date that section, before the release pull request
uv run python release/version.py release --push  # on main's tip: tag v<version>, push the tag
```

`bump` and `date` change files on `dev`, together, in one pull request before the release pull request. `release` commits nothing: it tags the commit `main` already holds. A release is the annotated tag `v<version>` on a pushed commit of `main`. Pushing the tag starts the release workflow, `.github/workflows/release.yml`.

`bump` also assembles the changelog. Each change's lines wait in its news file until the release. `bump` puts each line under its heading in the new version's section, puts each package row into the packages page, and removes the news files. `date` does the same for any news file merged after `bump`, so a late fix still reaches the release notes.

A change that moves a test of the release tier also adds its reason to the project's list of release-tier claims, since the run after its merge judges the normal tier alone. `date` moves that list's entries under the version, and the release pull request reads them as the reasons for what changed in the release tier.

## The release pull request

Changes collect on `dev`. A release is a pull request from `dev` to `main`, titled with the version. Its branch is `dev` itself: a fix for the release is a pull request into `dev` like any other, and the release pull request runs again on the new tip.

1. **The preparation lands first.** A fresh reviewer checks the release against the threat model, and another scores the runner's structure. Their two review files, the new version (`version.py bump`) and the dated CHANGELOG section (`version.py date`) merge into `dev` by one pull request, so the release pull request's head carries them. That pull request changes only the version line outside the documentation, and its change to the list of release-tier claims must be exactly what `date` moves, so its check runs `quick` alone and asks for no news file: the release pull request judges all of it.
2. **The release pull request runs the whole workflow** on the exact commit `main` will receive. It builds its own set on arm64 macOS and never reuses a cached one. It rebuilds the set on arm64 Linux and on x86_64 Linux and requires the same bytes. It runs every normal-tier shard on three systems, the release tier, the build shard, the fresh install on three systems and `quick`. The gather judges every goal: the newest result recorded on `dev` must be on this run's set, made on a clean tree, and whole. The build job also checks that the version's CHANGELOG section is dated, that its tag does not exist yet, and that `main`'s tip is in the head's history. The gather lists each release-tier result that changed since the last release with its reason, and the result is not recorded while one has none. A test that passed before and fails now is red.
3. **When it is green, its result is recorded onto `dev`** as one commit. The release pull request's run accepts its own result. A second workflow, started when that run finishes and running on `dev`, pushes that commit onto `dev`, and only while `dev`'s tip is still the commit the run judged. If `dev` moved on, nothing is pushed, that workflow is red, and the release pull request runs again on the new tip. The release pull request's next run, on that commit, reuses the green run, since only the result changed.
4. **The maintainer moves `main` and tags.** `main` moves to that commit by a fast-forward push, `git push origin <commit>:main`; GitHub then marks the pull request merged. On `main`'s tip, `uv run python release/version.py release --push` tags it and pushes the tag. The tag's run builds, judges both tiers again, signs and publishes.

The commit tagged is the commit the release pull request judged plus one commit that records its result. The release pull request's run is the dry run for that commit.

While a release pull request runs, nothing else merges into `dev`. If something does, the release pull request runs again on the new tip, and its result is not recorded until that run is green.

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

A *dry run* builds, rebuilds and tests exactly as a release does, but it never signs and never publishes. A signature is permanent in Sigstore's public log, so only a real release signs. A release tag goes only on a commit whose dry run passed on all three systems. The release pull request's run is that dry run, on the commit tagged but for the one commit that records its result.

## The weekly run

Once a week, a run on `dev` judges the release tier, rebuilds the set from the pins on two hosts and compares each rebuild with the set the pull requests are tested on, byte for byte. When any part of it is red, it opens an issue, or adds to the one already open. It never records a result.

## After publishing

Whoever cut the release compares the published assets with the `SHA256SUMS` in the build job's log: the GitHub release's assets (`gh release download`, then `shasum -a 256 -c`) and PyPI's wheel digest. The result goes in the release's notes.

## See also

- [Building from source](building.md)
- [Review and landing](review-and-landing.md)
- [Artifacts](../reference/artifacts.md)
