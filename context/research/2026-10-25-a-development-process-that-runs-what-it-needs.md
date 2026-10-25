# A development process that runs what it needs

- **Status:** research with a recommendation, 2026-10-25; **the owner agreed the same day** ("I agree with the recommendation", `../decisions.md`), and the recommendation is `../specifications/138-pull-requests-into-dev-and-the-judge-runs-where-it-is-needed.md`, which supersedes §7's list of seven with one specification built as a sequence of pull requests. The owner asked for a review of the testing harness and the CI/CD workflows "as a principal engineer, allowed to question everything": the whole suite is too slow to run on every commit, and the owner wants a usual flow (branch from `dev`, one to three specifications per branch, a pull request into `dev`, a release built from `dev` to `main`), running "only the tests we need when we need to run them", with the full workflow only before a release is published to PyPI. Nothing in `src/`, `tests/`, `scripts/`, CI, `AGENTS.md` or the constitution changed. No build or full judge ran.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Fable 5.1), with four Opus reader agents whose reports are the folder of the same name beside this file: `the-workflow-as-measured.md`, `the-harness-as-measured.md`, `the-process-as-practised.md`, `prior-art-on-the-web.md`. Every number below is theirs or mine and names its source.
- **Stands on:** `2026-10-22-how-other-projects-test-and-release.md` and `2026-10-22-process-advice.md` (the earlier study, whose five reserved specifications 117 to 121 were never built); `AGENTS.md`; the constitution §4.14, §5.4 to §5.7; `progress/README.md`; `decisions.md`; `reviews/README.md`; specs 002, 029, 052, 092, 101, 102; `.github/workflows/release.yml` at `20fbf294`.
- **Labels:** EXECUTED (a `gh` or `git` read, or a bounded local run, by me or a reader), READ (a file), INFERRED (reasoning, including every saving estimate).

## 1. The short version

The judge is good. The process around it runs the judge far too often, in the wrong places, and makes its colour mean nothing. Fix the second, keep the first.

What the measurements say (EXECUTED, the readers' reports): the release workflow has run 177 times in seven days and 53% of those runs failed; in the sampled failures most spec-branch reds were red by design, growth lines and the "newest acceptance is not on this set" goal G7. Every dispatch compiles the artifact set three or four times and runs every judge leg with no path filter, so a change to `context/` alone costs 52 jobs and 36 minutes on a branch and 281 jobs and 80 minutes on `main`. One specification costs about 2.7 branch runs, two to five review files with confirmation rounds, a share of a wave's integration review and dry run, a local full judge by the lane, and 15 to 30 commits, 64% of all commits since 2026-10-16 touching only `context/` and docs. The workflow has no `pull_request` trigger at all: the only way to test a change is to dispatch the whole release pipeline by hand. The fast tier has doubled to about nine minutes and `AGENTS.md` still says four. The acceptance flag for a changed judge was given on 96 of 97 landings, so it no longer distinguishes anything.

What is worth keeping, because it has caught real defects or because it is cheap and right (READ, the two earlier memos; EXECUTED, the run history): the Windows legs on code changes (14 of 24 real red runs were Windows alone); one full three-system run at one integration point (three wave dry runs caught what branches missed); the ratchet that counts passes by name and refuses a lost pass (agents solve what the verifier asks); fuel as a deterministic operation count; pinned inputs and the zero-patch rule; a fresh reader for every change; same-bytes rebuilds and the attestation at a release; set reuse by the hash of the build inputs (spec 101), which is the one piece that makes cheap pull-request checks possible.

**The recommendation** is the pattern every studied project converged on, applied here: a `dev` branch that pull requests merge into behind required checks; one decision job that reads the changed paths and picks a light set (minutes, Linux and Windows, the cached set, no rebuilds); one full three-system normal-tier run after each merge to `dev`, which is also where acceptance happens, from CI's own record, by a job instead of a person; the full workflow with rebuilds, the release tier and the attestation only on the pull request from `dev` to `main` and on the tag. Waves, the local lane judge, the `build/lane.lock` budget, confirmation rounds and integration reviews go. One fresh review per pull request stays, and the pre-build review stays for the classes the constitution names. The judge keeps every check it has; its writing-convention rules move out of the product's verdict into a lint job, and its `--accept-judge` flag is required only for a change that moves a verdict.

INFERRED savings: a pull-request check of 15 to 25 minutes and about 60 to 120 runner-minutes against today's 36 to 46 minutes and 300 runner-minutes; one light run plus a share of one full run per specification against about three full runs; no local full judge for anyone; one review file per specification against two to five. The cost: a platform-only or slow-tier failure can reach `dev` and is found by the post-merge run within the hour or by the weekly release-tier run, and is fixed forward or reverted, as CPython's buildbots and Pyodide's crons work.

## 2. What is actually slow, and why

The earlier memo said it in one line: "the slow part is not the tests, it is running every test, on three systems, about three times per change, and then having an agent read a run that is red on purpose" (READ, process advice §4). The readers measured where each minute goes.

**The compile is paid three or four times per run** (EXECUTED, the workflow report §2 and §3). `build` compiles on macOS (23 minutes), `rebuild-linux-arm64` and `rebuild-linux-x86-64` compile from the pins for the same-bytes vote (20 and 21 to 37 minutes), and `build-shard` compiles once more on arm64 Linux because a reused set has no build tree. On a branch run that reuses the cached set, the judges are done at 25 minutes and the run still waits ten more for the x86-64 rebuild, because the gather needs same-bytes. Reproducibility is proved on every branch dispatch. Go proves it before each release and nightly afterwards, never per change (READ, prior art §6).

**The macOS legs are the long pole of the judge** (EXECUTED): own-guest, own-hostile and own-embedding take 16 to 21 minutes each, against 7 to 13 for the Linux and Windows legs. They are also where the by-design reds appear, because fuel is compared only on darwin (READ, the harness report §2).

**The release tier adds 33 minutes and 850 runner-minutes** on every `main` dispatch (EXECUTED): 229 legs throttled to 18 at a time. It found two real regressions at the pre-tag dry runs (networkx and joblib, runs 39741960669 and 39764234616), each 80 minutes in, which is the argument for running it on a schedule rather than only at the tag.

**Nothing selects by path.** A `context/`-only change runs the same 52 jobs as a recipe change (READ, the workflow report §4). CPython, Wasmtime, Pyodide and numpy each have one job that decides the run from the changed files (READ, prior art §7 and the earlier memo §2).

**The process multiplies the runs.** A builder's branch run, a reviewer's own run when the commit differs, another run after every fix, the wave's dry run, the lane's local full judge, the pre-tag dry run, the tag's run (READ, the process report §6). About three full three-system runs per specification plus a local one per wave.

**Red means nothing.** 38 of 62 red runs in the earlier sample were growth lines or G7 (READ, the earlier memo §1); the readers' sample agrees. A branch set is never the accepted one, so G7 is red on every branch by construction, and fuel growth is red until the lane accepts it. An agent has to open logs to know whether a run failed. No automation can act on the colour.

**The judge spends time on itself.** About 1,217 unit tests test the harness against about 879 for the runner; 106 test the Markdown line wrapper; the rules run inside every CI shard called own-rest on two systems and in every local fast tier; the `coverage` job re-runs the whole fast tier a third time and nothing needs it (EXECUTED, the harness report §3 and §7; the workflow report §6). A writing rule turned the research branch's fast tier red this week (EXECUTED).

**The acceptance is a person on a laptop.** Only the lane accepts, locally, in the main tree, on a detached HEAD, after a full judge (READ, `progress/README.md`). This is the structural reason the project cannot merge pull requests: every landing needs a serial local step that no pull request can perform. Waves exist to amortise that step; the `build/lane.lock` budget exists because that step saturated the machine; the integration review exists because waves need one. Remove the local step and the three go with it.

## 3. What I question, and what I would keep

The owner allowed everything to be questioned. Here is each big rule, what it was for, and my verdict.

| rule as it stands | what it buys | verdict |
|---|---|---|
| Three systems on every branch run | Windows finds real defects (14 of 24); macOS legs are long and mostly by-design red | **Keep Windows and Linux on every code change. Run macOS on a pull request only when `src/`, `recipes/`, `scripts/` or the harness change; always after merge.** |
| Same-bytes rebuilds on every run | Reproducibility | **Release and a weekly schedule only** (Go, Debian). A reused set is already verified against its key and `SHA256SUMS`. |
| The fuel ratchet at 1e-4 as a hard gate | Agents cannot slow the guest quietly; fuel is deterministic so the gate is cheap in principle | **Keep at acceptance; advisory on a pull request** (red only on a lost pass; growth is a listed row with the reason the pull request's news file gives). |
| Only the lane accepts, locally | A trusted write to `context/progress/` | **A post-merge job on `dev` accepts from CI's record.** Spec 092 already reads one; G5 has held CI's darwin fuel to `accepted.json` at 1e-4 on every green run since, which is the evidence the owner asked for before trusting it. |
| Waves, the integration review, `build/lane.lock` | Amortise the local full judge | **Go.** With acceptance on CI there is nothing to amortise. Pull requests merge one at a time behind required checks. |
| 2.7 branch runs, the reviewer's own run, no run after a rebase | A measured run on the exact commit | **One light run per push, cancelling the one before.** The reviewer reads the pull request's run; the post-merge run is the measurement. |
| Pre-build review, build review, confirmation rounds, integration review | A fresh reader catches design and code defects (113's M1, 129's High) | **One review per pull request by someone who did not write it; the pre-build review stays for §5.6's classes** (imports and exports, the artifact set, the recipe, structural). Confirmation rounds become comments on the pull request. |
| Release tier only to publish | Slow tests run once | **Also weekly on `dev`, scheduled.** Two release-tier regressions were found at the pre-tag dry run, 80 minutes in, and cost the release hours. The owner's rule stands if they prefer; then the pre-tag run is the first look. |
| `--accept-judge` on every change under `tests/` | A changed judge is named | **Required only for a change to a verdict-bearing file** (`known_gaps.toml`, `tests/upstream/*.toml`, `expected/`, the CPython plan, the shard plan). Every other judge change is recorded by its hash, not flagged. 96 of 97 landings carried the flag; a flag always given protects nothing. |
| Rules checks inside the product's judge | Conventions hold | **Split**: release and supply-chain rules stay in the judge; code-shape and judge-integrity rules stay; writing conventions (one-line paragraphs, spec sections, open questions, memo labels, badge) move to a `lint` job that gates a pull request but never colours the product's verdict. |
| The `coverage` job | A badge | **Make it the Linux own-rest leg with coverage on**, or drop it. It is a third run of the fast tier. |
| A 2,602-line workflow, 41% hand-wired shard ids | The gather proves every shard handed its record on | **Generate the matrix from `tests/release_shards.toml`** (`fromJSON`), keep the gather's rule, delete 1,000 lines. |
| 10,000-word specifications with "For the lane" claim blocks | The lane's acceptance reasons | **The claim and the CHANGELOG line move to `context/changes/NNN.md`** (spec 118), read by the accept job. A specification says its decisions; the news file says what moved. |
| Hard constraints | | **Unchanged**: pinned inputs, patches few and recorded, uv only, prior art studied not copied, artifacts never in git, nothing lands unreviewed, code speaks for itself, the release tier whole before a tag, the owner makes every tag. |

## 4. The recommended process

### 4.1 Branches

- **`main`** holds released states only. It is protected; it moves by the merge of a release pull request from `dev`, and tags `v*` are made on it by the owner. Rulesets stay.
- **`dev`** is the default branch and the integration branch. Protected: pull requests only, one required aggregate check (`ci-status`), one review from someone who did not write the change, linear history (rebase or squash merge, the owner's choice; squash makes one specification one commit).
- **Topic branches** (`spec/NNN-slug`, or any name) branch from `dev` and carry one to three specifications. A worktree is the builder's convenience, not a rule.
- There are no `wave/*` branches and no lane. `handoff.md` records state between sessions as it does now.

### 4.2 What runs where

| event | what runs | where the set comes from | wall time (INFERRED) |
|---|---|---|---|
| Push to a pull request into `dev` | **quick**: ruff, ruff format, mypy, the pure-Python unit tests (harness, build tooling), the lint job (writing rules). Then, gated on quick: **judge-light**: the runner unit tests and the own-* shards on Linux and Windows; macOS own-* when `src/`, `recipes/`, `scripts/` or `tests/harness/` changed; the upstream normal-tier groups when the set, `tests/upstream/` or `tests/harness/` changed. `verify` on Linux. Superseded runs cancelled. | The cache, by spec 101's key; a pull request whose key misses (it changed a build input) compiles once on arm64 Linux and saves to its own cache scope. | 5 to 8 minutes for quick; 15 to 25 for the whole check |
| Merge to `dev` | **full normal tier on three systems**, from the cached set (`set-cache` builds it on a key miss, once); then **accept**: the gather's record is judged against `accepted.json` with the pull request's news-file claims, and a green verdict commits the acceptance to `dev` (`context/progress/`). Red means broken: fix forward within the day or revert. | The cache, keyed on `dev` | 30 to 45 minutes |
| Weekly, scheduled on `dev` | the release tier (229 legs) and the same-bytes rebuilds | built from the pins | about 80 minutes |
| Pull request from `dev` to `main` (a release) | the whole of today's workflow: macOS build, two rebuilds, same-bytes, every tier, `verify` on three systems, the gather with G7 | built from the pins | 80 to 90 minutes |
| Tag `v*` on `main` | the same, then attest, publish, PyPI | built from the pins (or, later, promoted from the release pull request's run, as Wasmtime does) | 85 minutes |

The decision job is one Python script under `release/` (the project owns its scripts; no third-party path-filter action, after the `tj-actions/changed-files` compromise that numpy cites) that reads the pull request's changed files and writes outputs: `set-changed`, `runner-changed`, `harness-changed`, `upstream-changed`, `docs-only`. Every job gates on an output with `if:`, and `ci-status` passes when every needed job succeeded or was skipped, as Wasmtime's does. A label `ci:full` or a commit line `citest:full` asks for the merge-grade run on a pull request, as `prtest:full` does.

### 4.3 The judge on a pull request

The gather's seven goals stay for the merge and release runs. On a pull request the verdict is narrower, and said so in the record: G4 (nothing failed) and the lost-pass half of G5 are red; growth rows are listed under a `GROWTH` heading with the reason the news file gives, or "unclaimed"; G7 is not evaluated, because a branch set is never the accepted one by construction. A pull request whose news file leaves a growth row unclaimed still merges if its reviewer accepts the reason in the review; the accept job on `dev` then refuses with the unclaimed row named, and the fix is a one-line news-file commit. That keeps rule 5's substance (no pass is lost quietly, growth has a written reason) and gives up only the place where the reason is demanded.

### 4.4 Acceptance from CI

The accept job on `dev` runs `uv run pytest --accept-from <record.json> --claims context/changes/` in a checkout of the merged commit, writes `context/progress/`, and pushes the acceptance commit to `dev` with the merge commit as its parent, as the lane does today by hand. The guards move with it: the record must be from a run whose every job is green (progress README's rule), the judge-hash line is recorded, a verdict-bearing judge file changed since the last acceptance needs its reason in a news file, and the history stays hash-chained. The owner deferred this on 2026-10-22 until three G5-clean waves; waves 11 to 13 and the 0.1.0 dry run and tag run were G5-clean (EXECUTED, the run list). The local `--accept` stays as a fallback for a machine that must accept without CI, and is otherwise unused.

### 4.5 Releases

A release is a pull request from `dev` to `main` whose title is the version. Its check is the full workflow. The security and structural reviews are its review. Merging it fast-forwards `main`; the owner tags; the tag's run publishes. "Tag only what a dry run passed" holds because the release pull request's run is the dry run on the exact commit, and `main` cannot move otherwise. The release tier runs on the release pull request and on the tag, whole, as §5.5 asks. The two local release acceptances of 1.5 hours each go: the record comes from the release pull request's run.

### 4.6 Local work

A builder runs `uv run pytest -m "not slow"` when it helps and single node ids when iterating; nothing requires either. The judge is on CI. `build/lane.lock` and the slot rules go. The fast tier's own growth (2,009 to 3,184 tests, 4 to 9 minutes) gets a budget: a normal-tier check past a fuel or wall cap in the quick job is a lint failure, scipy's `--fail-slow` idea (the earlier memo's K).

### 4.7 Reviews and documents

- One review per pull request, by a fresh agent or a person, in the pull request itself (GitHub review) with the written record under `context/reviews/NNN-<slug>-pr-DATE.md` as today's build review, without a confirmation round: the author answers in the pull request, the reviewer approves or asks again.
- The pre-build review stays for §5.6's classes and structural specifications, as a review of the specification before the branch has code.
- The security review and the structural review stay per release.
- A specification keeps Status, Kind, Decisions, Intent, Design, Scope, Acceptance criteria and Landing notes; "For the lane" becomes "The news file", one paragraph naming `context/changes/NNN.md`. The CHANGELOG and README package rows are assembled from the news files at the release (spec 118).
- The lifecycle in `AGENTS.md` shrinks to: research, specify, review the specification where §5.6 asks, branch from `dev`, build with checks first, open a pull request, one review, merge, the post-merge run accepts; a release is a pull request to `main`.

## 5. What this gives up, and how it is caught

| what can slip onto `dev` | how it is caught | precedent |
|---|---|---|
| A macOS-only failure in a pull request that did not touch `src/` | The post-merge full run, within the hour; fix forward or revert | CPython's buildbots, "fix or revert" |
| A release-tier regression | The weekly scheduled run (or the release pull request, if the owner keeps slow tests to publishing) | Wasmtime's daily cron; Pyodide's twice-weekly builds |
| A reproducibility break (a recipe change that makes the three compiles differ) | The weekly same-bytes run, and the release pull request | Go: verified at release and nightly after |
| Two pull requests that pass alone and fail together | The post-merge run of the second; `dev` protected with "up to date before merging" so the second is rebased first | Rust's reason for bors; GitHub's required-checks default |
| A missed dependency in the path rules (a harness file that changes upstream behaviour) | Any merge runs everything; `ci:full` for a pull request the author doubts | CPython: "otherwise, just run the tests" |
| An unclaimed growth merged | The accept job refuses and names the row; a one-line news-file commit | Rust's weekly perf triage, which may revert |
| A red `dev` that stays red | A rule: no new merge while `dev`'s last post-merge run is red, except the fix | CPython's stable-buildbot rule |

The one thing I would not trade: the ratchet's refusal of a lost pass, at every level, on every system where the check ran. It is the control that made autonomous ports converge (READ, the ports memo) and it costs nothing to keep.

## 6. Prior art, in one table

| pattern | who | here |
|---|---|---|
| A light PR set, the full set once later | Rust `pr` and `auto`; Wasmtime PR and merge queue; CPython PR and buildbots; Pyodide PR and push or cron | §4.2 |
| One decision job from paths and labels | CPython `compute-changes.py`; Wasmtime `determine`; Pyodide `test-scipy-trigger`; pyodide-recipes `calc_diff.py` | §4.2's script under `release/` |
| One aggregate required check that counts a skip as a pass | CPython `all-required-green`; Wasmtime `ci-status` | `ci-status` |
| A cheap gate first, superseded runs cancelled | numpy `smoke_test`; every project's `concurrency` | `quick`, `cancel-in-progress` |
| Acceptance and publishing by a job, not a person | Wasmtime publishes what CI built; numpy's release repo with an approval environment | §4.4, §4.5 |
| Reproducibility at release and on a schedule | Go, Debian, NixOS | §4.2's weekly run |
| News fragments per change | CPython `Misc/NEWS.d/next/`; numpy `upcoming_changes/` | spec 118 |
| A fuel or time budget on the fast tier | scipy `--fail-slow` | §4.6 |

Not taken: GitHub's merge queue. It needs an organization-owned repository (READ, prior art §5), and with one or two agents merging at a time the post-merge run with "up to date before merging" catches the same integration failures. Revisit if `dev` goes red from pull-request interaction more than once a week.

## 7. The specifications this becomes

In dependency order. The reserved numbers 117 to 121 are reused where the subject matches; the rest are the lane's to number. Each is parallel-safe except where said.

1. **The branches and the triggers** (new; build-class by the letter, the workflow): `dev` created from `main` and made the default; rulesets for `dev` (pull requests, one review, `ci-status`, linear, up to date); `release.yml` gains `pull_request` on `dev` and `main`, `push` on `dev`, `schedule`, and `cancel-in-progress: true` on pull requests; the decision script under `release/` with its unit tests; `ci-status`. The matrix generated from `tests/release_shards.toml`. The `coverage` job folded into own-rest. Spec 117's "red means broken" is this specification's pull-request verdict (§4.3).
2. **The light set by changed paths** (119 and 120 merged): which jobs each output enables; the `ci:full` escalation; the macOS rule; the upstream rule; the pull-request verdict's `GROWTH` listing; the record says its tier and its event.
3. **News files** (118): `context/changes/NNN.md` with the claim block and the CHANGELOG line; the CHANGELOG and README rows assembled at a release by `release/version.py`; the rules check that a pull request touching `src/`, `tests/`, `scripts/` or `recipes/` carries one.
4. **Acceptance from CI's record** (new; the owner's deferred item C): `--accept-from`, the accept job on `dev`, the guards, the fallback. Depends on 1 and 3.
5. **The release as a pull request to `main`** (121 widened): the release workflow's full shape on `pull_request` to `main` and on tags; the tag's run may promote the release pull request's built assets (a later step; first keep the rebuild).
6. **The judge's diet** (new; a judge change): writing rules to a `lint` job; `--accept-judge` only for verdict-bearing files; the fast-tier budget; the `--tier release` parse fix; `AGENTS.md`'s timings; the harness's own tests kept but run in `quick`.
7. **The process documents** (new; context only, the owner's amendments): the constitution's §5.6 (the reviewer reads the pull request's run), §5.7 (pull requests into `dev` replace the one landing lane; `main` receives releases), §4.14 (branches from `dev`); `AGENTS.md`'s "Working autonomously" rewritten to the lifecycle of §4.7; `reviews/README.md` to one review per pull request; `docs/contributing/review-and-landing.md` and `release-process.md`.

Order of value: 1 and 2 give most of the saving and change no verdict; 3 and 4 remove the local lane; 5 and 6 are hygiene; 7 is the owner's text and can be written first as the decision that authorises the rest.

## 8. For the owner

Three decisions are yours, each with my recommendation.

1. **Amend §5.7 and §5.6** so that pull requests into `dev` behind required checks and one fresh review replace the landing lane, waves and the integration review, and the reviewer reads the pull request's CI run. Recommended: yes; it is what the request asks for and every studied project does.
2. **Let a job accept from CI's record** (your 2026-10-22 "not yet, after three G5-clean waves"). The condition is met. Recommended: yes; without it a person still has to run a full judge locally for every merge, and the pull-request flow does not work.
3. **Run the release tier weekly on `dev`** against your rule that slow tests run only to publish. Recommended: yes, weekly, because two release-tier regressions each cost a release 80 minutes to find and hours to fix; if no, the release pull request is the first look and the plan stands.

## One line

Keep the judge, stop running it three times per change: `dev` behind a light path-selected pull-request check on Linux and Windows, one full three-system run and the acceptance after each merge by a job, the release tier weekly, and the rebuilds, the release tier and the attestation only on the pull request from `dev` to `main` and on the tag.
