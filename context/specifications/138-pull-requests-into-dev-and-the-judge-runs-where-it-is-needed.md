# 138: pull requests into `dev`, and the judge runs where it is needed

- **Status:** **drafted 2026-10-25** from `../research/2026-10-25-a-development-process-that-runs-what-it-needs.md`, whose recommendation the owner agreed to the same day ("I agree with the recommendation", `../decisions.md`, "The development process moves to pull requests into dev"). That agreement is the owner's explicit decision for the constitution amendments of Decision 10 and for the three choices the memo put to the owner (§8). Not for build until its pre-build review: it changes the release workflow (constitution §5.6) and the process every other specification follows. It is built as the sequence of pull requests in *Design*, the first pull requests made under the process it describes.
- **Date:** 2026-10-25
- **Owner:** Clay Gendron
- **Kind:** **build-class** by the letter (`.github/workflows/release.yml`, `set-cache.yml`), a **judge change** (`tests/harness/`, `tests/checks/test_rules.py`, the plugin's flags), `release/` (one decision script, `version.py`), and the process documents (`constitution.md`, `AGENTS.md`, `reviews/README.md`, `progress/README.md`, `docs/contributing/`). **No pin, recipe, compiler flag or `src/` change**, so the artifact set's bytes do not change; the release pull request's same-bytes step is the proof. Not structural (no `src/`). Its pre-build review is required.
- **Depends on:** 101 (the set reused by the hash of its inputs), 092 (the judge reads a release record) and 102 (the release tier), all landed: the cache, the record reader and the tier split are what this specification arranges differently. It supersedes the reserved 117, 119, 120 and 121 and absorbs 118 (news files), which become this specification's Decisions 3, 2, 4 and 7; their roadmap lines are retired by it. Nothing in flight touches the workflow; 127 and 136 touch `scripts/` and `release/` and rebase cleanly.
- **Research it stands on:** the memo above and its folder (the workflow measured job by job from runs 39943021050, 39957192055, 39732496724 and 39715865231; the harness measured; the process as practised; the web survey of Pyodide, numpy and scipy, CPython, Wasmtime, Rust, Go and Debian); `../research/2026-10-22-how-other-projects-test-and-release.md` and `../research/2026-10-22-process-advice.md`; the 0.1.0 security audit's notes on the workflow (`../reviews/0.1.0-security-audit-2026-10-25.md`, h10).

## The problem

The judge is good and the process runs it far too often, in the wrong places, and makes its colour mean nothing (READ, the memo §1 and §2; every number EXECUTED there).

- The release workflow ran 177 times in seven days; 53% failed; in the sampled failures most spec-branch reds were by design: growth lines, or the gather's G7, which is red on every branch by construction because a branch's set is never the accepted one.
- Every dispatch compiles the artifact set three or four times and runs every judge leg with no path filter. A change to `context/` alone costs 52 jobs and 36 minutes on a branch, 281 jobs and 80 minutes on `main`.
- The workflow has no `pull_request` trigger. The only way to test a change is to dispatch the whole release pipeline by hand.
- One specification costs about 2.7 branch runs, two to five review files with confirmation rounds, a share of a wave's integration review and dry run, a local full judge by the lane, and 15 to 30 commits, 64% of all commits since 2026-10-16 touching only `context/` and docs.
- Only the lane accepts, locally, in the main tree, on a detached HEAD, after a full judge. That is the structural reason no pull request can merge on its own; waves, `build/lane.lock` and the integration review exist to amortise that step.
- The fast tier doubled to about nine minutes at six cores; `AGENTS.md` says four. `--accept-judge` was given on 96 of 97 landings. The documented `uv run pytest --tier release` fails to parse. A writing rule turned a research branch's fast tier red.

What has earned its keep and stays (READ, the two earlier memos; EXECUTED, the run history): Windows on every code change (14 of 24 real red runs were Windows alone); one full three-system run at one integration point (three wave dry runs caught what branches missed); the ratchet that counts passes by name and refuses a lost pass; fuel as a deterministic operation count; pinned inputs and the zero-patch rule; a fresh reader for every change; same-bytes and the attestation at a release; the release tier whole before a tag; set reuse by the hash of the build inputs.

## Decisions

### 1. The branches

- **`main`** holds released states only. It moves by the merge of a release pull request from `dev` (Decision 6) and carries the `v*` tags, made by the owner. Its ruleset stays (pull requests only, linear, no force push) and gains the required check `ci-status`.
- **`dev`** is made from `main`'s tip and becomes the repository's default branch and the integration branch. Its ruleset: pull requests only; one approving review from someone who did not author the change; the required check `ci-status`; "require branches to be up to date before merging"; linear history by **squash merge** (one specification, one commit on `dev`, its message the pull request's title and body; the owner may switch to rebase merge later without a specification). Direct pushes are allowed only to the accept job's identity (Decision 5).
- **Topic branches** branch from `dev`, carry one to three specifications, and are deleted at merge (`delete_branch_on_merge` on). Their names are free; `spec/NNN-slug` stays the convention. A worktree is the builder's convenience, not a rule.
- **No `wave/*` branches, no lane, no `build/lane.lock`.** `handoff.md` keeps state between sessions as it does now.

### 2. One decision job picks the run

A script, `release/ci_plan.py`, with unit tests beside the other `release/` tests, reads the pull request's changed files (`gh pr diff --name-only`, or `git diff --name-only <merge-base>` on a push) and writes GitHub outputs. It is the project's own code: no third-party changed-files action (the `tj-actions/changed-files` compromise of 2025 is why numpy's release repository forbids one).

| output | true when a changed path matches |
|---|---|
| `set` | `downloads/SHA256SUMS`, `scripts/**`, `recipes/**`, `release/set_key.py`, `release/build-constraints.txt`, `tests/harness/constructors*` (spec 101's key inputs, read from `set_key.py`'s own list so the two never drift) |
| `runner` | `src/**`, `pyproject.toml`, `uv.lock` |
| `harness` | `tests/harness/**`, `tests/conftest.py`, `tests/release_shards.toml`, `tests/known_gaps.toml` |
| `upstream` | `tests/upstream/**`, `tests/checks/test_v1_3_upstream_suites.py` |
| `checks` | `tests/**` not covered above |
| `workflow` | `.github/**`, `release/**` |
| `docs_only` | every changed path is under `context/`, `docs/`, or is `README.md`, `CHANGELOG.md`, `AGENTS.md`, `SECURITY.md`, `LICENSE*`, `mkdocs.yml`, `.gitignore` |
| `full` | the pull request carries the label `ci:full`, or any commit in it has a line `citest:full`, or the event is not a pull request |

The job runs on `ubuntu-24.04` in under a minute. Every later job gates on these outputs with `if:`, never with a workflow-level `paths:` filter, so a skipped job reports success and the required check never sticks at Pending.

### 3. What a pull request runs

Two stages, the second gated on the first, superseded runs cancelled (`concurrency: pr-${{ github.event.pull_request.number }}`, `cancel-in-progress: true`).

**`quick`** (ubuntu-24.04, always): `ruff check`, `ruff format --check`, `mypy`, the pure-Python unit tests (everything under `tests/unit` and `tests/checks` that needs no artifact: the harness's own tests, the build-tooling tests, the public-API rows), and **`lint`**, the writing-convention rules of Decision 8. About 5 to 8 minutes (INFERRED from own-rest's 4m42s on Linux).

**`judge`**, from the cached set (the branch's own cache scope, else `dev`'s; on a miss with `set` true, one compile on `ubuntu-24.04-arm`, saved to the branch's scope, about 20 minutes; on a miss with `set` false, the run fails with one line naming the missing `dev` cache, since `set-cache` fills it on every push to `dev`):

| shards | when | systems |
|---|---|---|
| own-runner, own-embedding, own-guest, own-hostile, own-rest (the normal tier's product checks) | unless `docs_only` | Linux and Windows always; macOS when `runner`, `set`, `harness` or `full` |
| the upstream normal-tier groups | when `set`, `upstream`, `harness` or `full` | Linux |
| `verify` (install the wheel fresh, run pandas and the CLI) | unless `docs_only` | Linux; three systems when `full` |
| `build-shard`, the two rebuilds, `same-bytes`, the release tier, the macOS publish build, the assets | never on a pull request into `dev` | — |

A `docs_only` pull request runs `quick` alone and `ci-status` passes on it. `full` runs the merge-grade set of Decision 4 on the pull request.

**The verdict on a pull request** is the gather's, narrowed and said so in the record (`meta.event: pull_request`): G1 to G4 as today; G5's lost-pass half is red and its growth half is listed under a `GROWTH` heading, each row with the reason the pull request's news file gives (Decision 7) or the word `unclaimed`; G6 is evaluated over the systems that ran; **G7 is not evaluated**. The gather's summary is posted as the job summary so a reviewer reads it without opening logs. `ci-status` is one job with `if: always()` that passes when every job in `needs` is `success` or `skipped`, as Wasmtime's does.

### 4. What a merge to `dev` runs, and the accept job

A push to `dev` (the squash merge) runs, from `dev`'s cached set (`set-cache.yml` builds and saves it first when the key misses, once, on `ubuntu-24.04-arm`; the judge waits on it):

- the full normal tier on three systems: every own-* shard on macOS, Linux and Windows, every upstream normal-tier group, `verify` on three systems, `build-shard` on arm64 Linux;
- the gather with G1 to G6 in full and **G7 in its post-merge form**: the newest acceptance is on `dev`'s set, or the run is the one that will make it;
- **`accept`**, gated on a green gather: in a checkout of the merged commit, `uv run pytest --accept-from build/ci/record.json --claims context/changes/` (Decision 5) writes `context/progress/`, and pushes one acceptance commit to `dev` whose first parent is the merged commit, with the message `Accepted: <pull request title> (#<n>)` and the reasons the news files gave. The push uses a deploy key or a GitHub App token held in the `accept` environment, which the ruleset lets bypass "pull requests only" for that identity alone.

A red post-merge run means `dev` is broken. The rule, written into `AGENTS.md`: no new merge to `dev` while its last post-merge run is red, except the fix or a revert; the author of the merged change fixes forward the same day or reverts. The accept job never runs on a red gather, so `accepted.json` never records a red state.

A scheduled run on `dev`, weekly (`schedule: cron "0 6 * * 1"`, dispatched on `dev` explicitly as Wasmtime's cron does), runs the release tier and the two rebuilds with `same-bytes`, and opens or updates one issue when red. It never accepts. The owner chose this against the standing rule that slow tests run only to publish (`../decisions.md`, 2026-10-25).

### 5. Acceptance from CI's record

The plugin gains `--accept-from <record.json>`: the record is a gather's merged record (spec 092's reader) from a run whose every job was green, for the commit checked out, from a `push` to `dev` (`meta.event`), with `meta.set_source` naming `dev`'s cache key or `built`. The acceptance applies the record's statuses and metrics as a local run's would, keyed by platform as today (fuel on darwin from the macOS shards). Every guard of today's `--accept` moves with it: a clean tree, the commit's identity, the judge-hash line, no lost pass, growth only with a reason, `fewer` only with its reason, a verdict-bearing judge file (Decision 8) changed since the last acceptance only with a reason, the history hash-chained and its volume rule. Reasons come from the news files of the pull requests merged since the last acceptance (Decision 7); an unclaimed `GREW`, `fewer` or judge change refuses the acceptance with the row named, the run is red, and the fix is a one-line news-file commit, which is itself a pull request whose merge re-runs the accept.

The local `--accept` stays, unchanged, for a machine that must accept without CI; it is not part of the normal flow and `AGENTS.md` says so. The `three systems` need (G6) is met by the record, as spec 092 arranged.

This is the choice the owner deferred on 2026-10-22 ("not yet, after three G5-clean waves"); waves 11 to 13, the 0.1.0 dry run and the tag run were G5-clean (EXECUTED, the memo), and the owner agreed on 2026-10-25.

### 6. A release is a pull request from `dev` to `main`

The pull request's title is the version; its branch is `dev` itself (or a `release/<version>` branch cut from `dev` when fixes must not wait for `dev`). Its check is today's whole workflow: the macOS `build`, both rebuilds, `build-shard`, `same-bytes`, every normal-tier shard on three systems, the release tier (229 legs), `verify` on three systems, the gather with every goal including G7's release form (the newest acceptance is on this set, clean, not partial). The security review and the structural review (constitution §5.6) are its review, written under `../reviews/` as today; the release pull request is approved by the owner. Its merge fast-forwards `main` (the ruleset requires the merge commit to be `dev`'s tip: "merge" strategy with linear history, so the commit tagged is the commit judged). The owner tags; the tag's run is today's tag run (build, judge both tiers, attest, publish, PyPI). "Tag only what a dry run passed" holds by construction: the release pull request's run is the dry run on the exact commit. The two local release acceptances of about 1.5 hours each go; the release acceptance is the release pull request's record, accepted by the same job on `main`.

A later specification may let the tag's run promote the release pull request's built assets instead of rebuilding, as Wasmtime publishes what CI built; this one keeps the rebuild.

### 7. News files

`context/changes/NNN-<slug>.md`, one per specification (or per pull request when a pull request carries no specification), holding: the CHANGELOG line under its heading (`### Added`, `### Changed`, `### Fixed`, `### Security`, as the CHANGELOG uses), the README package rows the change adds or moves, and a `claims` TOML block in spec 092's shape (`new`, `retired`, `changed`, `passes`, `grows` with `growth`, `units`, and a new `judge` list naming each verdict-bearing judge file changed with its reason). `release/version.py bump` assembles the news files into `CHANGELOG.md` and the README rows at a release and deletes them; a rules check holds that a pull request touching `src/`, `tests/`, `scripts/`, `recipes/`, `downloads/` or `.github/` carries at least one news file (the decision job sets `news` and `ci-status` requires it unless `docs_only`). The CHANGELOG's unreleased section is no longer edited by hand; the specification's "For the lane" section becomes one line naming its news file.

### 8. The judge's diet

- **`lint`.** The writing-convention rules leave the judge's verdict: specification header and sections, a specification leaves nothing undecided, landed specifications cite a review, a release has its structural review, built structural specifications cite a pre-build review, Markdown paragraphs one line each, executed memos label their claims, the README badge, code and strings name no `context/` document, no embedder name. They move to `tests/lint/` and run in `quick` as the `lint` step, which gates `ci-status` but is not a goal check and is not ratcheted. The release and supply-chain rules, the code-shape rules and the judge-integrity rules stay in `test_rules.py` as goal checks.
- **`--accept-judge`** is required only when a **verdict-bearing judge file** changed since the last acceptance: `tests/known_gaps.toml`, `tests/upstream/*.toml`, `tests/upstream/expected/**`, `tests/upstream/python/**`, `tests/release_shards.toml`, `tests/public_api.txt`, `context/release-tier-claims.toml`. Every other judge change is recorded by the judge-hash line in the history, unflagged. The list lives in `tests/harness/paths.py` beside `JUDGE_PATHS` and a rules check holds it.
- **A budget on the fast tier.** A normal-tier goal check whose own fuel exceeds a cap written in its family's TOML, or whose wall time exceeds 60 seconds in `quick`, is reported by `lint` as a budget finding, so the fast tier cannot grow by accident (scipy's `--fail-slow`). The caps are set at twice today's values; a budget finding names the specification that must move the check to the normal or release tier.
- **The `coverage` job goes.** The Linux own-rest shard runs under `coverage.py` and uploads to Codecov; the badge keeps its source.
- **The `--tier` option** is registered from a `pytest11` entry point (or `addopts` in `pyproject.toml` names `tests`), so `uv run pytest --tier release` parses; a unit row holds it.
- **`AGENTS.md`'s timings** are replaced by a sentence that points at the quick job's and the fast tier's last measured times in `docs/contributing/`, measured at the build and labelled EXECUTED.
- **The workflow's matrix** is generated: `inputs` reads `tests/release_shards.toml` and emits the matrices with `fromJSON`; the 532 matrix-output lines and the 534 gather env lines go; the gather reads the shard list from the same file; the rules that held the two equal become one rule that the workflow has no hand-written shard id. The eleven copied "these are the bytes the build job made" blocks become one composite action under `.github/actions/`.
- **Duplicate compiles.** `build-shard` and `rebuild-linux-arm64` become one job on arm64 Linux that compiles once, runs the build shard and uploads its `SHA256SUMS` and wheel for `same-bytes`; the zero-patch check runs once per compile.

### 9. Reviews

- One review per pull request, by a fresh agent or a person who did not write the change, as a GitHub review with the written record under `../reviews/NNN-<slug>-pr-DATE.md` in the build review's template (criteria against evidence, findings ranked, constitution checks, verdict). No confirmation round: the author answers in the pull request, a code fix is a new commit on the same pull request, and the reviewer approves or asks again. The reviewer reads the pull request's run (`ci-status`, the gather's summary) and never dispatches one; a Low that touches only `context/` the reviewer may commit to the pull request's branch.
- The pre-build review stays for the classes §5.6 names (the guest's imports or exports, the artifact set, the build recipe) and for structural specifications, as a review of the specification before the branch has code; a parallel-safe runner change no longer needs one unless its Kind line says structural, since its pull request review reads the code with the specification (the owner's "review follows risk", 2026-10-19, kept).
- The security review and the structural review stay per release (Decision 6).
- The integration review, the wave's review, the lane's addendum and the self-check list go; the self-check's substance (checks seen failing first, Windows read, every gap names its closer, a news file present) becomes the pull request template under `.github/PULL_REQUEST_TEMPLATE.md`.

### 10. The documents, and the owner's amendments

The owner's agreement of 2026-10-25 is the explicit decision these amendments need (constitution, Scope line). The constitution's Status line records them; the exact text:

- **§4.14** replaces "on a local branch named `spec/NNN-<slug>` made from main's tip … Main moves only by fast-forward, through the landing lane (§5.7)" with: "on a branch made from `dev`'s tip, carrying one to three specifications, merged into `dev` by a pull request behind its required check and one review (§5.7); `main` moves only by the merge of a release pull request from `dev` (§5.5) and carries the tags. No other long-lived branch unless asked." The stacked-build and `wave/NN` sentences go; the `reset --soft` exception and the never-checkout sentence stay.
- **§5.4** replaces "they land one at a time, or as one wave of up to five reviewed specifications judged and accepted once (§5.7 …)" with "each lands by its own pull request into `dev`, judged and accepted once on `dev` after its merge (§5.7)".
- **§5.5**'s release rule replaces "Before a tag, the lane accepts both tiers on main's tip (the release acceptance), and the release workflow judges both on main's exact commit and on the tag itself" with "Before a tag, the release pull request from `dev` to `main` judges both tiers on the exact commit `main` will receive and its record is accepted; the tag's own run judges both again".
- **§5.6** replaces "The reviewer re-runs the counted tests (locally, or as its own dispatch of the release workflow …)" with "The reviewer reads the pull request's run of the counted tests (its `ci-status` and the gather's summary), checks each acceptance criterion against its evidence, …" and keeps the rest; the two "owner, 2026-10-19/20" parentheses on dispatching go.
- **§5.7** is retitled **"Pull requests into `dev`"** and reads: "Builders and reviewers work in parallel on branches from `dev`. `dev` changes only by the squash merge of a pull request that passed its required check and one review by someone who did not write it. After each merge the full normal tier runs once on three systems and a job accepts its record into `context/progress/`; a red post-merge run blocks every merge but its fix or revert. `main` changes only by the merge of a release pull request from `dev`, whose check is the whole workflow, both tiers, the rebuilds and the gather's release goals, and whose review is the release's security and structural reviews. Reproducibility is proved at the release pull request, at the tag, and weekly on `dev`, not per change."
- **§7**'s bullet "make a branch or worktree beyond §4.14's" follows §4.14's new text.
- **`AGENTS.md`**'s "Working autonomously" section is rewritten to the lifecycle of nine steps: orient from the scoreboard; pick work by what it unblocks; write the check before the code; branch from `dev`; open a pull request with its news file; read `ci-status` and the gather's summary; one review; merge when green and approved; the post-merge run accepts. Rules 4 (never weaken the judge), 5 (no pass is lost quietly: on a pull request growth is listed, at acceptance it needs its reason), 7 (two strikes) and 9 (commit only what you mean) stay. Rules 3a, 6, 6a and 6b, the lane's budget and `build/lane.lock`, the waves, the three-run limit and the stale "until spec 092 lands" sentence go. "Commit or push only when asked" stays, with pushes to a pull request branch allowed once the owner has asked for the specification to be built.
- **`reviews/README.md`**: one review per pull request, the template kept, the self-check replaced by the pull request template, the structural-review section unchanged. **`progress/README.md`**: `--accept-from`, the accept job, the pull-request verdict, the local `--accept` as fallback. **`docs/contributing/review-and-landing.md`, `release-process.md`, `first-change.md`**: the new flow in the user's words.

## Intent

After this specification, a change is a pull request into `dev` that runs what its paths need, in minutes, on Linux and Windows from a cached set, and merges when its check is green and one fresh reader approved; every merge is judged once in full on three systems and accepted by a job, so `context/progress/` is written by CI, not by a person on a laptop; a release is a pull request from `dev` to `main` whose check is the whole workflow, both tiers, the rebuilds and the attestation's goals, and whose merge is the commit the owner tags. The judge keeps every check and every ratchet; what changes is where and how often it runs, and that its colour means something: red is broken, on a pull request as on `dev`.

## Design

Built as a sequence of pull requests into `dev`, each small, each green under the rules that exist when it merges; the first two under the old process (dispatched runs), the rest under the new. Each may be split further by its reviewer.

1. **The decision and the documents** (context only): this specification, its roadmap line, the retirement of 117 to 121's lines, the `decisions.md` entry; the constitution's amendments and Status line, `AGENTS.md`, `reviews/README.md`, `progress/README.md`, `docs/contributing/` (Decision 10). Lands first, so every later pull request is made under the process it describes. Its check is `quick`'s predecessor, the fast tier.
2. **`dev`, the triggers and `ci-status`** (the workflow; Decisions 1, 2, 3): `dev` made from `main` and set as default with its ruleset; `release/ci_plan.py` and its tests; `release.yml` gains `pull_request` on `dev` and `main`, `push` on `dev`, `schedule`, `concurrency` with cancellation, the `quick` and `judge` stages gated on the plan's outputs, the pull-request verdict in the gather, `ci-status`; the matrix generated and the copied blocks made one action (Decision 8); `set-cache.yml` keyed on `dev`. This is the one pull request dispatched by hand as today, since the trigger it adds does not exist yet; its run is also the first `dev` cache.
3. **News files and the accept job** (Decisions 4, 5, 7): `context/changes/`, the rules check, `version.py bump`'s assembly; `--accept-from`; the `accept` job, its environment and identity; the weekly schedule's issue.
4. **The release pull request** (Decision 6): the `pull_request` to `main` shape; G7's release form; the tag's run unchanged; `docs/contributing/release-process.md` finished.
5. **The judge's diet** (Decision 8): `tests/lint/`, the `--accept-judge` list, the budget, the `--tier` fix, the `coverage` fold, the duplicate compile folded, `AGENTS.md`'s timings.
6. **Reviews** (Decision 9): the pull request template; `reviews/README.md`'s one-review text was in step 1.

Files: `.github/workflows/release.yml` (shrinks by about 1,000 lines), `.github/workflows/set-cache.yml`, `.github/actions/verify-artifact/action.yml`, `.github/PULL_REQUEST_TEMPLATE.md`; `release/ci_plan.py`, `release/version.py`; `tests/harness/plugin.py` (`--accept-from`, the pull-request verdict), `tests/harness/gather.py` (G7's forms, the summary), `tests/harness/paths.py` (the verdict-bearing list), `tests/harness/shards.py` (the matrix), `tests/lint/`, `tests/checks/test_rules.py` (the moved rules out, the new rules in), `tests/unit/test_ci_plan.py`, `tests/unit/test_release_version.py`; the documents of Decision 10. Comments and docstrings give reasons in words and name no specification.

## Scope

In: Decisions 1 to 10 and the CHANGELOG line, which is the first news file ("Development moves to pull requests into `dev` behind a path-selected check; the full judge runs once per merge and accepts from CI; releases are pull requests from `dev` to `main`."). Out: GitHub's merge queue (the repository is user-owned; revisit if `dev` goes red from pull-request interaction more than once a week); the tag's run promoting built assets instead of rebuilding (a later specification); result reuse by input hash beyond the set (the earlier memo's E); the one-review rule for a parallel-safe runner change already follows from Decision 9; anything in `src/`.

## Acceptance criteria

1. **`dev` exists, is the default branch, and its ruleset requires `ci-status`, one review, up-to-date branches and linear history** (`gh api repos/…/rulesets`, recorded in the landing notes, EXECUTED).
2. **A `docs_only` pull request runs `quick` alone and `ci-status` passes in under 10 minutes** (one real pull request, its run id).
3. **A `src/`-only pull request runs `quick`, then own-* on Linux, Windows and macOS and `verify` on Linux, no rebuild, no upstream group, from `dev`'s cached set, in under 30 minutes**; a pull request touching only `tests/upstream/` runs the upstream groups on Linux and no macOS leg; `ci:full` on either runs the merge-grade set (three pull requests, their run ids).
4. **The pull-request verdict**: on a pull request with a known growth, the gather lists the `GROWTH` row with the news file's reason and `ci-status` is green; with a lost pass it is red and names it; G7 is absent from the record (`meta.event == "pull_request"`).
5. **A merge to `dev` runs the full normal tier on three systems and the accept job pushes one acceptance commit** whose record equals the run's (`sameness.py` between the downloaded record and `build/progress/latest.json` of a local `--accept-from` of the same record: no difference); the history stays intact (`test_progress_history_is_intact` green).
6. **An unclaimed growth refuses the acceptance** with the row named, and a one-line news-file pull request clears it (seen once, run ids).
7. **A red post-merge run never accepts** (a deliberately red pull request merged on a throwaway `dev` state during the build, or the accept job's unit row with a red record).
8. **The weekly run** dispatches on `dev`, runs the release tier and `same-bytes`, and opens an issue when red (one manual dispatch of the schedule's job proves it).
9. **The release pull request from `dev` to `main`** runs the whole workflow with every goal, its merge is `dev`'s tip (the commit tagged is the commit judged), and the tag's run is unchanged against 0.1.0's (`39957192055`'s job list, by name).
10. **Same bytes**: the first release pull request's `same-bytes` and `SHA256SUMS` equal the last accepted set's, since nothing in the build inputs changed.
11. **The judge's diet**: `uv run pytest --tier release` parses; the writing rules run in `lint` and are not goal checks; `--accept-judge` is refused as unnecessary when no verdict-bearing file changed and required when one did (two unit rows); no `coverage` job; one arm64 compile per run; the workflow has no hand-written shard id (the rules check); `release.yml` is under 1,600 lines.
12. **News files**: `version.py bump` assembles `context/changes/*.md` into the CHANGELOG and README rows and removes them (a unit row with a fixture); the rules check refuses a code pull request without one.
13. **The documents** carry Decision 10's text; the constitution's Status line names the owner's decision of 2026-10-25; `AGENTS.md` has no `lane.lock`, wave, `-n 3` or "until spec 092" sentence; `test_specifications_have_no_open_question` and the other lint rules green.
14. **No run is dispatched by hand after step 2** of the Design; every later step's evidence is a pull request's own run.

## For the lane

This specification is the last to carry this section. **Kind:** build-class by the letter (the workflow), judge change, process documents; it lands by the pull requests of its Design, the first two under the old rules (one dispatched run each, read by its reviewer), the rest under the new. **News file:** `context/changes/138-pull-requests-into-dev.md`, with the claim block: `new` the lint and plan rows, `retired` none, `changed` the rules moved to `lint` (listed), `judge` the verdict-bearing list's file, `grows` none, `units` the new unit tests' count. **Flags** for the first acceptance made by the accept job: `--accept-from` carries them; no paste-safe line is needed.

## Landing notes

Not yet built. The builder fills this section pull request by pull request: the ruleset as applied, each pull request's run id and the shape it ran, the first acceptance commit the job pushed, the sameness line of criterion 5, the sizes of criterion 11, and the owner's merge of the first release pull request.

## One line

Pull requests into `dev` behind a path-selected check on Linux and Windows from the cached set, one full three-system run and a job's acceptance after each merge, the release tier weekly, and the rebuilds, the release tier and the attestation only on the pull request from `dev` to `main` and on the tag; the judge keeps every check and its colour means red is broken.
