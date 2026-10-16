# 004 — Alpha releases: the version, the tag and the release workflow

- **Status:** draft, 2026-10-16
- **Owner:** Clay Gendron
- **Kind:** release machinery (`src/wasi_python/__init__.py`, `pyproject.toml`, `release/`,
  `CHANGELOG.md`, `.github/workflows/release.yml`, `README.md`, judge edits in `tests/`). It
  changes neither the guest nor the artifact set nor the build recipe: the workflow runs the
  build that spec 003 landed, as it is.
- **Depends on:** 003 (the build and the artifact set), 001 (the runner the wheel carries), 002
  (the judge the workflow runs).
- **Research it stands on:** `../research/2026-10-16-what-the-scripted-build-needs.md` (the
  pins the workflow's build downloads, all for arm64 macOS, so the build job runs on Apple
  silicon); the rest is convention: PEP 440 versions, hatchling's dynamic version, PyPI's
  trusted publishing.
- **The owner's instructions** (2026-10-16): releases are alpha builds numbered `0.1.0aN`;
  set up tagging for creating a release, and scripts that bump the package's version; pushing
  to git is authorized; the repository is public. Cutting a release (pushing a release tag),
  publishing it and uploading to PyPI each still need the owner's instruction (constitution §7).

## Decisions

1. **One version, in one place.** `__version__` in `src/wasi_python/__init__.py` is the only
   place the version is written. `pyproject.toml` declares `dynamic = ["version"]` and reads
   it through hatchling (`[tool.hatch.version] path = …`). Versions follow PEP 440, in the
   forms `X.Y.Z`, `X.Y.ZaN`, `X.Y.ZbN` and `X.Y.ZrcN` (N ≥ 1); the alpha line is `0.1.0aN`.
2. **The tag is `v` plus the version**, annotated, on a commit of `main` that is already
   pushed: `v0.1.0a1`. A tag whose name is not `v{__version__}` of the commit it points to
   fails the release workflow at its first step.
3. **`CHANGELOG.md`** has one section per version, newest first, headed `## <version> —
   <YYYY-MM-DD>` once released and `## <version> — unreleased` before. Its body is the
   release's notes on GitHub.
4. **`release/version.py`**, run as `uv run python release/version.py <command>`. It lives
   outside `scripts/`, so release tooling never becomes one of the artifact set's `recipe`
   lines (003 Decision 9) and a version bump never makes a built set stale.
   - `show`: prints the version.
   - `bump [--to <version>]`: the next alpha by default (`0.0.0` → `0.1.0a1`, `0.1.0aN` →
     `0.1.0a(N+1)`), or the given version, which must be greater by PEP 440's order. It
     rewrites `__version__` and adds an `unreleased` section to `CHANGELOG.md`, editing both
     in place, so any other change in them is kept. It does not commit.
   - `check [--tag <tag>]`: the version is valid, `pyproject.toml` reads it dynamically from
     `__init__.py`, `CHANGELOG.md` has its section, and, with `--tag`, the tag is
     `v{version}`. The release workflow runs it first.
   - `release [--push]`: for the version in the tree, with a clean working tree on `main`
     level with `origin/main`: dates its `CHANGELOG.md` section today (UTC), commits
     `Release <version>`, and creates the annotated tag `v<version>`. With `--push` it pushes
     `main` and the tag, which starts the release workflow; without it, it prints that
     command. Pushing the tag is cutting the release: done only on the owner's instruction.
   - `notes <version>`: prints that version's `CHANGELOG.md` section (the release notes).
   - `assets <artifact dir> <wheel> <out dir>`: writes the release's assets (Decision 6).
5. **`.github/workflows/release.yml`** runs on a pushed tag `v*` and on `workflow_dispatch`
   (a dry run: build and verify, never publish). Every third-party action is pinned by commit
   SHA, with its release named in a comment, and uv by version (`0.9.22`, the version this
   repository is developed with).
   - **build** (`macos-15`, Apple silicon: the pinned toolchain is arm64 macOS): `version.py
     check` (with `--tag` on a tag); `scripts/00_download.sh`; `scripts/build.sh`; the wheel
     (the artifact set copied to `src/wasi_python/artifacts/`, `uv build --wheel` with
     `SOURCE_DATE_EPOCH` fixed); the zero-patch check
     (`test_source_tree_matches_its_tarball`, constitution §4.1) as its own step; then the
     whole judge, `uv run pytest -p no:cacheprovider`, which must exit 0 against the
     accepted state in `context/progress/`; then `version.py assets`. It uploads the assets
     for the jobs after it.
   - **verify** (`ubuntu-24.04`, `windows-2025`, `macos-15`): on each system, the v1.1 to v1.4
     checks against the built set (`$WASI_PYTHON_ARTIFACTS`), and the wheel installed into a
     fresh environment with the `run` extra, running `wasi_python.run` once. The build is not
     repeated: the same bytes are checked on three systems.
   - **publish** (tags only, after build and verify): a GitHub release named for the tag,
     marked a pre-release for `a`, `b` and `rc` versions, with the assets and the version's
     `CHANGELOG.md` section as notes.
   - **pypi** (tags only, after publish, and only when the repository variable
     `PYPI_PUBLISH` is `true`): the wheel uploaded by PyPI's trusted publishing (OpenID
     Connect, no stored token), from the `pypi` environment. The owner sets up the trusted
     publisher on PyPI and the variable; until then the job is skipped.
6. **The release's assets**: the wheel; `wasi-python-<version>-wasm32-wasip1.tar.xz`, the
   artifact set under one top-level directory `wasi-python-<version>/`, written
   deterministically (sorted members, mode 0644, owner 0, the time `SOURCE_DATE_EPOCH`); and
   `SHA256SUMS` of those two. No `.cwasm` (constitution §4.6).
7. **The wheel carries the artifact set.** The artifacts are git-ignored, and hatchling leaves
   ignored files out unless told otherwise, so the wheel target names
   `src/wasi_python/artifacts` as an artifact to include. The judge's
   `test_wheel_carries_the_artifact_set` checks every file against the set.
8. **Judge edits** (accepted with `--accept-judge`):
   - the gap `test_release_workflow_runs_the_zero_patch_check` is removed, since the workflow
     closes it;
   - a new `rules` check, `test_the_version_is_released_by_the_book`, runs `version.py check`
     against the tree;
   - unit tests of `version.py`'s parsing, ordering, bumping and changelog edits
     (`tests/unit/test_release_version.py`).
9. **The tree starts at `0.1.0a1`**, set by `version.py bump` (the first use of the script),
   with an `unreleased` section. Cutting it is the owner's call.

## Intent

After this specification, cutting an alpha is two commands, `version.py release --push` and
the workflow it starts, and every release is the same pinned build, judged, checked on three
systems, and published with its notes and hashes.

## Design

```
src/wasi_python/__init__.py   __version__ = "0.1.0a1", the one place the version is written
pyproject.toml                dynamic = ["version"]; [tool.hatch.version]; the wheel includes artifacts/
CHANGELOG.md                  one section per version; its body is the release's notes
release/version.py            show, bump, check, release [--push], notes, assets
.github/workflows/release.yml build (macos-15) -> verify (ubuntu, windows, macos) -> publish -> pypi
tests/unit/test_release_version.py, tests/checks/test_rules.py::test_the_version_is_released_by_the_book
```

## Scope

In: the above. Out: recording the three systems' runs into `context/progress/history.jsonl`
(the three-systems check stays blocked until a specification decides how CI evidence is
accepted); Linux and Windows builds (the reproducible-builds memo); signing.

## Acceptance criteria

1. `version.py bump` takes the tree from `0.0.0` to `0.1.0a1`; `uv build --wheel` names the
   wheel `wasi_python-0.1.0a1-py3-none-any.whl`, and it carries the artifact set (the judge's
   wheel check passes with it in `dist/`).
2. `version.py check` passes on the tree, and fails, each with one line naming why, on a wrong
   tag, a missing changelog section and a static version in `pyproject.toml` (unit tests).
3. A `workflow_dispatch` run of the release workflow on `main` passes every job it runs:
   build (with the zero-patch step and the judge green) and verify on all three systems.
   The run's URL is in the landing notes.
4. `uv run pytest` is green; the gap is removed; ruff is clean on `src`, `tests` and
   `release`.

## Landing notes

(Filled in on landing.)
