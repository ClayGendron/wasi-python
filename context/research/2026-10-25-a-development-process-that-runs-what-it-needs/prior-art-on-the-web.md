# How long-build projects split CI into PR, merge, nightly and release: a web survey

A reader agent's report (Claude Opus, 2026-10-25), from each project's default branch on that date, web pages only, nothing cloned; it extends `../2026-10-22-how-other-projects-test-and-release.md` and does not repeat it. Labels: READ (a URL in the source key), nothing measured. Durations only where a document states them.

**A correction to the earlier memo's premise.** There is no `[wheel build]` commit-message trigger in numpy's or scipy's current main. Both build wheels on every PR; nightlies and releases moved to separate `*-release` repositories.

## 1. Pyodide

| Stage | What runs | Source |
|---|---|---|
| PR checks | `build-core` on ubuntu-latest and macos-15: emsdk, CPython, `tag:core`, the test packages and numpy, then compressed sizes. `test-core` runs Safari tests with a 180-min job timeout (core 90 min, numpy 30). A command-line runner test on Linux, macOS and Windows from the Linux artifact; then DB, Bun and Deno smoke tests. | P1 |
| How it decides | `test-scipy-trigger` sets an output on a push, `[scipy]` in the subject, or the `scipy` label; other jobs use `if: needs.test-scipy-trigger.outputs.test-scipy`. No `paths` filter. | P1 |
| Superseded runs | `concurrency: main-${{ github.head_ref \|\| github.ref }}`, `cancel-in-progress: true`. | P1 |
| Post-merge | A push to `main`, `stable` or release branches runs the same workflow with scipy on. | P1 |
| Packages | `pyodide-recipes`: a PR builds the changed recipes (`tools/calc_diff.py`) plus `tag:core`; the `full build` label, a push, a dispatch or cron `0 0 * * 1,4` builds all. | P4 |
| Build tool | `pyodide-build`: unit tests on 3 OSes on every event; integration tests only on a push to main, `[integration]` in the commit, or the `integration` label. | P5 |
| Nightlies | The main-branch build at `cdn.jsdelivr.net/pyodide/dev/full/`, re-deployed per commit on main; recipes upload to the anaconda `pyodide-nightly` channel through the `deploy-nightly` environment with `--skip-existing`. | P4, P6 |
| Release | A maintainer runs `bump_version.py --tag` and pushes the tag, which triggers the release CI; docs-only fixes to `stable` carry `[skip ci]`. `deploy_release.yml` runs on `release: published`, builds, publishes to PyPI from a `PyPi` environment with `id-token: write`, and runs no tests. | P2, P3, P4 |

## 2. numpy and scipy, with the scientific-python nightly channel

| Stage | What runs | Source |
|---|---|---|
| PR checks (numpy) | `linux.yml`: a cheap `smoke_test` job gates about ten through `needs: [smoke_test]`; `paths-ignore` skips `**.md`, `**.rst`, `**.pyi` and stubtest; several jobs are PR-only through `if: github.event_name != 'push'`. | N2 |
| PR wheel builds | numpy's `wheels.yml` runs on every PR: 12 platforms, cp313 only, uploaded as artifacts, nothing published; `emscripten.yml` builds a pyodide wheel per PR. scipy's `wheels.yml` runs on each PR; its `get_commit_message` job skips only on `[lint only]` or `[docs only]`. | N1, N3, S1, S2 |
| Post-merge (numpy) | `linux.yml` also runs on a push to main, for the coverage comparison. | N2 |
| Nightly | Release and nightly builds live in `numpy-release` and `scipy-release`, whose main tracks upstream main. Cron `42 2 * * SUN,WED` builds wheels; `scientific-python/upload-nightly-action` uploads on `schedule`. SPEC 4 asks for builds at least weekly to `anaconda.org/scientific-python-nightly-wheels`. | N4, N5, S3, SP4 |
| Downstream use | pandas' `unit-tests.yml` has a `numpy-nightly` environment and a `python-dev` job that installs numpy from the nightly index, not allowed to fail. | PD |
| Release | A `workflow_dispatch` with input `pypi` or `testpypi` uses the environment of that name; `check_version` fails unless `SOURCE_REF_TO_BUILD` is an exact tag; `pypa/gh-action-pypi-publish` with trusted publishing and attestations; the release manager inspects the build logs before the upload. | N4, N5 |
| Why a separate repo | "O(5) rather than O(30) people with access"; the `tj-actions/changed-files` compromise is cited; caching is disabled in the release repo against cache poisoning, while the main repo keeps its looser approach. | N6, N4 |

## 3. CPython

| Stage | What runs | Source |
|---|---|---|
| Change detection | `build.yml`'s first job calls `reusable-context.yml`, which runs `Tools/build/compute-changes.py`; its outputs (`run-tests`, `run-docs`, `run-windows-tests`, `run-macos`, `run-ubuntu`, `run-wasi`, …) gate jobs with `if:`. | C1, C2 |
| Rules | Only on `pull_request` are paths consulted; any other event runs every platform. Docs-only changes run docs only; platform directories narrow the run to that platform; `RUN_TESTS_IGNORE` lists files that never trigger tests; fuzzing runs on C changes and only on the default branch. No labels or commit messages are read. | C3 |
| Required check | One aggregate job, `all-required-green` (`re-actors/alls-green`, `if: always()`), with `allowed-skips` from the context outputs and `allowed-failures` for a few jobs that may be red without blocking. | C1 |
| Flaky tests | Both CI modes set `rerun = True` and `fail_env_changed`; `--fail-rerun` is not set, so a test that passes on re-run does not fail CI. | C4 |
| Post-merge | Buildbots run on each push; commits close together share a build; core developers must "fix or revert" on stable buildbots; on a PR, buildbots run only with the `test-with-buildbots` label or a `!buildbot <regex>` comment. | C5 |
| Release | The release manager checks the stable buildbots; the release workflow does a clean build of the source tarball, which must pass the tests; platform experts give a "green light". | C6 |

## 4. Wasmtime

| Stage | What runs | Source |
|---|---|---|
| Triggers | `pull_request` to `main` and `release-*`, `merge_group`, a push to `release-*` only, `workflow_dispatch`. "CI doesn't run on pushes to main." | W1 |
| `determine` job | Any non-PR event sets `run_full=true`, as does a PR whose base is not `main`; otherwise it reads the commit messages and changed paths through `gh pr view` and `gh pr diff`; markers `prtest:full`, `prtest:debug`, `prtest:miri`, `prtest:capi`, `prtest:platform-checks`; paths add jobs (`crates/c-api`, `fuzz`, `pulley`, `Cargo.lock`, `gc`, `.isle`). Some path patterns are unanchored greps and can over-match. | W1 |
| PR checks | "A sample of the full CI test suite", by default on x86_64 Linux; authors fix failures unless systemic. | W2 |
| Merge queue | Entry requires green CI on the PR; the full suite then runs once; `fail-fast` on in the queue and off on PRs; `cargo vet` fails a PR but not the queue. | W1, W2 |
| Required check | `ci-status` runs `jq 'all(.result == "success" or .result == "skipped")'` over `toJson(needs)`, because skipped job names differ between PR and queue runs. | W1 |
| Nightly | A daily cron dispatches `main.yml` on main to prime caches; a weekly cron runs release-branch CI; a failed dispatch opens an issue. | W3, W1 |
| Release | On a push to `release-*`, if `ci-status` passed and a commit says `automatically-tag-and-release-this-commit`, the run creates the tag. `publish-artifacts.yml` **does not rebuild**: it finds the CI run for the commit, downloads its artifacts, attests `dist/*` and updates a rolling `dev` prerelease or creates a versioned release. | W1, W4 |

## 5. Rust (bors) and GitHub's merge queue

| Item | Detail | Source |
|---|---|---|
| PR build | Five Linux jobs, about 40 minutes; running everything on each push "would take too many resources". | R1 |
| auto build | Tens of jobs, several hours; at most one `auto` build at a time; about 10 merges a day; rollups batch trivial PRs. | R1 |
| Late finds | PR CI does not run `./x doc`, so broken doc links surface late in the queue; bors exists because breakage "usually happens when another, incompatible PR is merged after the build happened". | R1 |
| Flaky | Jobs prefixed `optional-` with `continue_on_error: true`; a failed merge must be re-approved. | R1 |
| Release | "Copying those artifacts from rust-lang-ci2 to the production endpoint"; `promote-release` takes 75 to 90 min; rebuilding is a recovery step; beta publishes daily. | R1, R2 |
| GitHub merge queue | Workflows need the `merge_group` trigger; each PR is tested with the base and the PRs ahead of it on `gh-readonly-queue/*` branches; build concurrency and group sizes 1 to 100; wildcard branch rules cannot use a queue. Available to public repos owned by an organization, or Enterprise Cloud private repos. | G1, G2 |

## 6. Reproducible-build verification

| Project | When rebuild-equality is checked | Source |
|---|---|---|
| Go | Before each release, a Linux and a Windows host "must produce bit-for-bit identical archives or else we do not proceed"; after release, `gorebuild` runs nightly against go.dev/dl; no PR check. | RB1 |
| Debian (variance testing) | Two builds differing in TZ, locale, uid, HOME, shell, umask, kernel and a date 398 days ahead, continuously over the archive, not per change. | RB2 |
| Debian (rebuilders) | reproduce.debian.net rebuilds archive binaries from their `.buildinfo` files. | RB3 |
| NixOS | Reports on the closures of the minimal and GNOME ISOs; "building a package twice can't prove it is reproducible". | RB4 |

## 7. GitHub Actions features that bear on this

- **Workflow-level `paths` filters:** a filtered-out workflow's required checks stay Pending and block merging; "avoid requiring workflows that can be skipped"; a job skipped by `if:` reports Success. Diffs are two-dot for pushes and three-dot for PRs. (G3, G4)
- **Skip markers** (`[skip ci]` and friends) apply only to `push` and `pull_request`, and leave checks Pending. (G5)
- **Required checks:** "up to date before merging" is the default; skipped and neutral results satisfy a required check. (G6)
- **`dorny/paths-filter`:** job-level filtering through a `changes` job; on PRs it uses the API with no checkout; it handles merge-queue events. (G7) **`tj-actions/changed-files`** was compromised in March 2025 (CVE-2025-30066), which numpy cites. (G8, N6)
- **`concurrency`:** a pending run in the group is always cancelled; `cancel-in-progress: true` also cancels the running one. (G4)
- **`schedule`** runs on the default branch's latest commit, may be delayed, and is disabled after 60 days without activity in a public repo; `workflow_run` triggers only if the file is on the default branch. (G9)
- **Reusable workflows** up to ten levels; **environments** with required reviewers, wait timers, branch and tag rules; environment secrets released only after the rules pass. (G10, G11)

## Synthesis

Patterns common to all: a light PR set and a full set at one later point (Rust's `auto`, Wasmtime's merge queue, CPython's push plus buildbots, Pyodide's push or label or cron, numpy's twice-weekly release-repo builds); one decision job computes the run from paths and, in Pyodide and Wasmtime, markers and labels; one aggregate required check that counts a skip as a pass; a cheap gate first and superseded runs cancelled; opt-in escalation by the author (`prtest:full`, `[scipy]`, `full build`, `test-with-buildbots`, `@bors try`); the release promotes what CI built (Wasmtime, Rust) or rebuilds in a clean locked place (numpy, scipy), publishing through environments and trusted publishing; rebuild equality checked at release and continuously afterwards, never per PR.

| Pattern | What can slip into the target branch | How they catch it |
|---|---|---|
| Light PR, full after merge (CPython, Pyodide) | Platform-only or slow-test breakage lands on main | Buildbots with "fix or revert"; cron full builds; the release manager waits for green bots |
| Full suite in a merge queue (Wasmtime, Rust) | Little reaches main; the price is throughput (about 10 merges a day for Rust) and a late ejection | Rollups and groups; the author fixes what the queue finds |
| Path-based selection | Missed dependencies; over-matching | Any non-PR event runs everything; daily or twice-weekly full crons |
| Allowed-failure or optional jobs | A broken platform stays red unnoticed | Explicit lists in the aggregate; Rust forbids toolstate breakage a week before release |
| Rerun-on-failure | Real intermittent bugs masked | CPython leaves `--fail-rerun` off and asks for transient failures on the tracker |
| Twice-weekly nightlies | Breakage found 3 to 4 days late | Downstream projects test against the nightlies |
| Release without re-testing | Whatever the final CI run missed | The tag or commit must have passed CI first |
| Separate release repo | The release ref can drift from tested main | `check_version` requires an exact tag; TestPyPI first; a human approves |
| Workflow-level `paths` or `[skip ci]` on required checks | Merges blocked by Pending checks | Job-level `if:` plus an aggregate check |

## Source key

P1 <https://github.com/pyodide/pyodide/blob/main/.github/workflows/main.yml>; P2 <https://github.com/pyodide/pyodide/blob/main/.github/workflows/deploy_release.yml>; P3 <https://github.com/pyodide/pyodide/blob/main/docs/development/maintainers.md>; P4 <https://github.com/pyodide/pyodide-recipes/blob/main/.github/workflows/build.yml>; P5 <https://github.com/pyodide/pyodide-build/blob/main/.github/workflows/main.yml>; P6 <https://pyodide.org/en/latest/usage/downloading-and-deploying.html>; N1 <https://github.com/numpy/numpy/blob/main/.github/workflows/wheels.yml>; N2 <https://github.com/numpy/numpy/blob/main/.github/workflows/linux.yml>; N3 <https://github.com/numpy/numpy/blob/main/.github/workflows/emscripten.yml>; N4 <https://github.com/numpy/numpy-release>; N5 <https://github.com/numpy/numpy-release/blob/main/.github/workflows/wheels.yml>; N6 <https://github.com/numpy/numpy/issues/29178>; S1 <https://github.com/scipy/scipy/blob/main/.github/workflows/wheels.yml>; S2 <https://github.com/scipy/scipy/blob/main/.github/workflows/commit_message.yml>; S3 <https://github.com/scipy/scipy-release>; SP4 <https://scientific-python.org/specs/spec-0004/>; PD <https://github.com/pandas-dev/pandas/blob/main/.github/workflows/unit-tests.yml>; C1 <https://github.com/python/cpython/blob/main/.github/workflows/build.yml>; C2 <https://github.com/python/cpython/blob/main/.github/workflows/reusable-context.yml>; C3 <https://github.com/python/cpython/blob/main/Tools/build/compute-changes.py>; C4 <https://github.com/python/cpython/blob/main/Lib/test/libregrtest/cmdline.py>; C5 <https://devguide.python.org/testing/buildbots/>; C6 <https://peps.python.org/pep-0101/>; W1 <https://github.com/bytecodealliance/wasmtime/blob/main/.github/workflows/main.yml>; W2 <https://github.com/bytecodealliance/wasmtime/blob/main/docs/contributing-ci.md>; W3 <https://github.com/bytecodealliance/wasmtime/blob/main/.github/workflows/ci-cron-trigger.yml>; W4 <https://github.com/bytecodealliance/wasmtime/blob/main/.github/workflows/publish-artifacts.yml>; R1 <https://rustc-dev-guide.rust-lang.org/tests/ci.html>; R2 <https://forge.rust-lang.org/release/process.html>; G1 <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue>; G2 <https://github.blog/changelog/2023-07-12-pull-request-merge-queue-is-now-generally-available/>; G3 <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks>; G4 <https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions>; G5 <https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-workflow-runs/skipping-workflow-runs>; G6 <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches>; G7 <https://github.com/dorny/paths-filter>; G8 <https://db.fluidattacks.com/adv/github_actions/tj-actions/changed-files/CVE-2025-30066>; G9 <https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows>; G10 <https://docs.github.com/en/actions/sharing-automations/reusing-workflows>; G11 <https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment>; RB1 <https://go.dev/blog/rebuild>; RB2 <https://tests.reproducible-builds.org/debian/index_variations.html>; RB3 <https://reproduce.debian.net/>; RB4 <https://reproducible.nixos.org/>.

Not verified: typical PR wall-clock durations for numpy, scipy, CPython and Pyodide; the PyPI environments' reviewer settings; Wasmtime's `trigger-release-branch-ci.rs`.

One line: every project studied runs a selected, light set per PR, decided by one job reading paths and labels, with one required aggregate that counts a skip as a pass; the full set runs once, in a merge queue, after merge, or on a cron; releases publish from an approval-gated environment, and reproducibility is checked at release and continuously afterwards, never per PR.
