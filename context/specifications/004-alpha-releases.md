# 004 — Alpha releases: the version, the tag and the release workflow

- **Status:** landed, 2026-10-16
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
   - `bump [--to <version>]` (it writes both files or neither): the next alpha by default (`0.0.0` → `0.1.0a1`, `0.1.0aN` →
     `0.1.0a(N+1)`), or the given version, which must be greater by PEP 440's order. It
     rewrites `__version__` and adds an `unreleased` section to `CHANGELOG.md`, editing both
     in place, so any other change in them is kept. It does not commit.
   - `check [--tag <tag>]`: the version is valid, `pyproject.toml` reads it dynamically from
     `__init__.py`, `CHANGELOG.md` has its section, and, with `--tag`, the tag is
     `v{version}`. The release workflow runs it first.
   - `release [--push]`: for the version in the tree, with no uncommitted change to a
     tracked file (untracked files are left alone) on `main`
     level with `origin/main`: dates its `CHANGELOG.md` section today (UTC), commits
     `Release <version>`, and creates the annotated tag `v<version>`. With `--push` it pushes
     `main` and the tag, which starts the release workflow; without it, it prints that
     command. Pushing the tag is cutting the release: done only on the owner's instruction.
   - `notes <version>`: prints that version's `CHANGELOG.md` section (the release notes).
   - `assets <artifact dir> <wheel> <out dir>`: writes the release's assets (Decision 6).
5. **`.github/workflows/release.yml`** runs on a pushed tag `v*` and on `workflow_dispatch`
   (a dry run: build and verify, never publish, even when started on a tag: the publishing
   jobs require `github.event_name == 'push'`). The judge's environment is the one
   `uv.lock` pins (`UV_LOCKED=1`), on Python 3.14.2 (`UV_PYTHON`). Checkouts do not keep
   the token (`persist-credentials: false`). Every third-party action is pinned by commit
   SHA, with its release named in a comment, and uv by version (`0.9.22`, the version this
   repository is developed with).
   - **build** (`macos-15`, Apple silicon: the pinned toolchain is arm64 macOS): `version.py
     check` (with `--tag` on a tag); `scripts/00_download.sh`; `scripts/build.sh`; the wheel
     (the artifact set copied to `src/wasi_python/artifacts/`, `uv build --wheel` with
     `SOURCE_DATE_EPOCH` fixed); the zero-patch check
     (`test_source_tree_matches_its_tarball`, constitution §4.1) as its own step, which
     requires exactly four passes, so a skipped tree fails it; on a tag, the tagged commit
     must be in `origin/main`'s history; the wheel's build backend is pinned with hashes
     (`release/build-constraints.txt`, compiled from `release/build-backend.in`); then the
     whole judge, `uv run pytest -p no:cacheprovider`, which must exit 0 against the
     accepted state in `context/progress/`; then `version.py assets`. It uploads the assets
     for the jobs after it.
   - **verify** (`ubuntu-24.04`, `windows-2025`, `macos-15`): on each system, the v1.1 to v1.4
     checks against the built set (`$WASI_PYTHON_ARTIFACTS`), and the wheel installed into a
     fresh environment with the `run` extra, running `wasi_python.run` once. The build is not
     repeated: the same bytes are checked on three systems. These runs judge pass and fail
     only, against an empty baseline (`--progress-dir` pointed at an empty directory, which
     the scoreboard announces): the ratchet against the accepted state is the build job's,
     and fuel differs slightly between hosts even on the same bytes (the landing notes). A
     following step reads `latest.json` and fails unless the only needs that blocked
     anything are the oracle, the three systems and the wheel, which a verify job cannot
     provide. The wheel is installed as `wasi-python[run] @ <wheel>`, so the `run` extra's
     own pin (`wasmtime>=49,<50`) is what is tested. **Amended by spec 028:** the wheel is
     installed by its plain name and runs a program; a `[run]` install asserts the metadata.
   - **publish** (tags only, after build and verify): a GitHub release named for the tag,
     marked a pre-release for `a`, `b` and `rc` versions, with the assets and the version's
     `CHANGELOG.md` section as notes.
   - **pypi** (tags only, after publish, and only when the repository variable
     `PYPI_PUBLISH` is `true`): the wheel uploaded by PyPI's trusted publishing (OpenID
     Connect, no stored token), from the `pypi` environment. The owner sets up the trusted
     publisher on PyPI and the variable; until then the job is skipped.
6. **The release's assets** (the licence notices include HACL\*'s MIT notice, which CPython's
   `Doc/license.rst` does not cover; a v1.1 check asserts it): the wheel; `wasi-python-<version>-wasm32-wasip1.tar.xz`, the
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

Built 2026-10-16 by the author agent; review pending (see below).

**The dry runs** (EXECUTED: `gh workflow run release.yml --ref main`, five runs):
1. https://github.com/ClayGendron/wasi_python/actions/runs/38978211049, failed in the build
   job's judge: the wiring self-test assumed no wheel in `dist/`, and the release build puts
   one there. Fixed: the self-test now expects the wheel check to fail against its synthetic
   set when a wheel is present, and to be blocked on the wheel need when not.
2. https://github.com/ClayGendron/wasi_python/actions/runs/38979164440: build and Linux
   passed. On macOS two checks spent more fuel than the accepted figures on the same bytes
   (+0.032% and +0.0101%, against a tolerance of 0.01%), so verify now judges pass and fail
   only (Decision 5). On Windows two first calls
   sharing one root raced: Windows refuses a rename over a file another guest has open. The
   runner now keeps the zip already in place when it is the right one (spec 001, amended).
3. https://github.com/ClayGendron/wasi_python/actions/runs/38980695810: **every job passed.**
   - build and judge (arm64 macOS, 12 min): every step `ok`; the zero-patch step `4 passed`;
     the judge `89/93 pass · 1 gap · 3 blocked · 0 fail` (blocked: the oracle and the
     prior-art clones, which are local, and the three-systems check), `238 passed, 8 skipped,
     1 xfailed`.
   - verify on ubuntu-24.04, windows-2025 and macos-15: `63/66 pass · 0 gap · 3 blocked · 0
     fail` each, and the installed wheel ran `pandas.Series([1, 2, 3]).sum()` to
     `Completed(exit_code=0, stdout=b'6\n', …)` on all three.
   - publish and pypi: skipped, as a dry run must.
4. After the review's fixes, https://github.com/ClayGendron/wasi_python/actions/runs/38983729244:
   all passed but Windows' concurrent-calls check, where one call read the zip while another
   renamed over it, which Windows refuses. Calls in one process now place a root's zip one at
   a time (spec 001, amended).
5. https://github.com/ClayGendron/wasi_python/actions/runs/38985113082: **every job passed.**
   The build rebuilt `d77dc946…` and `b450c7a6…` again; the zero-patch step `4 passed`; the
   judge `90/94 pass · 1 gap · 3 blocked · 0 fail`, `240 passed, 8 skipped, 1 xfailed`; verify
   `64/67 pass · 0 fail` on all three systems, each blocked only by the oracle, the three
   systems and the wheel, which the new step confirmed; the installed wheel printed `b'6\n'`
   on all three; publish and pypi skipped.

**A second host rebuilt the binaries byte for byte** (EXECUTED: the build job's log): GitHub's
macOS runner produced the reactor `d77dc946962d2154…` and the snapshot `b450c7a6892bf9e3…`,
the accepted set's hashes. CPython's own interpreter from step 20, which is not shipped,
differed (`64f94066…` there, `307b29e2…` here), so something host-specific reaches that build
and not ours; the reproducible-builds memo takes it up.

**Locally** (EXECUTED): `uv run pytest` with the release wheel in `dist/`: `91/94 pass · 1
gap · 1 blocked · 0 fail`; `version.py bump` took the tree from `0.0.0` to `0.1.0a1`. The
reviewer rebuilt run 3's wheel and `.tar.xz` locally from its commit and got CI's bytes
exactly (`02f83128…`, `bc51b406…`). After the review the licence notices changed (HACL\*),
so the wheel's hash changed with them; the pinned build backend gives the same wheel each
time: the reviewer's local rebuild at the confirmation's commit matched run 5's wheel
(`ef759b98…`) and `.tar.xz` byte for byte.

**Judge edits.** The gap `test_release_workflow_runs_the_zero_patch_check` is removed; the
new rules check and the unit tests of Decision 8; `pyproject.toml` (the dynamic version, the
`run` extra's `<50`); the wiring self-test (above); `test_cpython_notice_covers_hacl`; and
two checks made to hold on Windows: `test_runner_refuses_a_cache_others_can_write` asserts the
POSIX refusal on POSIX and records the documented Windows behaviour there, and
`test_runner_never_follows_a_link_a_guest_left` requires the guest's link on POSIX and lets
link creation fail only where the host forbids it, still requiring the next call to repair
the root.

**Review.** `../reviews/004-alpha-releases-2026-10-16.md`: "the machinery doesn't land yet",
then, after the dispositions, "confirmed, and spec 004 can land". After the confirmation the
author fixed its cosmetic slip in `release`'s message, pinned the backend for every build in
the workflow (`UV_BUILD_CONSTRAINT`) and corrected spec 001's cross-process sentence; the
per-root lock's lifetime and the krml headers' explicit mention are left as recorded.
