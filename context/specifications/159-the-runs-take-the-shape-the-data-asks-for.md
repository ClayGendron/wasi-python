# 159: The runs take the shape the data asks for

- **Status:** drafted 2026-10-30, to be reviewed before it is built (constitution §5.6: it changes the build recipe's class, the release workflow). The owner asked for it on 2026-10-30 ("can you implement all the recommendations").
- **Date:** 2026-10-30
- **Owner:** Clay Gendron
- **Kind:** **build-class** (the release workflow and the plan script), **a judge change** (`tests/release_shards.toml`, the rules checks that hold the workflow), not structural, parallel-safe with 160 and 161; 155 stacks on it.
- **Depends on:** the owner's instruction to build it; the research memo. Nothing in flight.
- **Research it stands on:** `../research/2026-10-30-where-the-time-goes-since-0-1-1.md` (§2.2, §2.3, §4 rows 1 to 7, §5); `../research/2026-10-25-a-development-process-that-runs-what-it-needs.md`; specification 138's Decisions 2 to 4 and 8.

## The problem

The 0.1.2 release pull request's run took 97.5 minutes: a 42-minute macOS compile gated every judge, then 229 release legs ran 18 at a time for 52 minutes (EXECUTED, the memo §2.3). A pull request's run took a median 18.6 minutes when green and 46.6 at the ninetieth percentile, and in 13 of 17 runs with three systems the last leg to finish was a macOS leg that had waited a median 11 minutes for one of the account's five macOS runners (EXECUTED, §2.2). Every judge waits 2.5 minutes for `quick`. Fifty of the 74 red jobs in ten days were `ci-status` red by design, waiting for a review file (EXECUTED, §2.1). Every post-merge run's longest job is a 23-minute compile whose only consumer is the build shard. The owner wants the full Linux run, build and both tiers, at or under one hour.

## Decisions

### 1. The build and the judges run beside `quick`

The `build` job needs `plan` and `inputs`; `quick` leaves its needs. `ci-status` keeps `quick` in its needs, so a lint-red tree still cannot merge. A docs-only pull request still runs `quick` alone (the plan's `judge` output is false there). The cost is a few job-minutes on a tree that fails lint; the saving is 2.5 minutes on every run.

### 2. No macOS leg on a pull request

`select()` takes an own shard on macOS only when the run is `full` (the merge-grade set: a push to `dev`, the `ci:full` label, a `citest:full` commit line, the workflow changed, the release pull request). The `runner`, `set` and `harness` flags no longer add macOS on a pull request. The `upstream-macos` shard follows the same rule. A macOS-only defect reaches `dev` and is found by the post-merge run within the hour, and fixed forward or reverted under specification 160's rule; in the ten days measured no red post-merge run was a macOS-only defect (EXECUTED, the memo §2.1, the failing jobs by group: one macOS failure, `own-runner`, beside fourteen on one Linux leg).

### 3. The own shards are split so no leg runs past seven minutes on Windows

`own-guest` (461 checks, 11.3 minutes on Linux and 13.7 on Windows) becomes `own-guest-a`, `own-guest-b` and `own-guest-c`, its files divided so the three legs are within two minutes of each other, read from the pull request's run. `own-hostile` (218 checks in one file, 9.1 minutes on Windows) becomes `own-hostile-a` and `own-hostile-b`, divided by `file::function` entries under `nodes`, as `own-embedding-a` already is. `own-embedding-a` (8.8 minutes on Windows) is divided once more the same way. The shard plan's invariants (`tests/unit/test_shards.py`: every item in exactly one shard per system, every product file in a files shard on all three systems, a node taken from its file's shard) hold unchanged; a check's node id does not move, so the ratchet sees no retirement. The builder divides by the leg times of the pull request's own run and records the times in the landing notes. The budget: no own leg over seven minutes on Windows and over six on Linux.

### 4. The review file has its own check

A new job `review` (name `review`), needing `plan` alone, runs on a pull request into `dev` that is not documentation only and fails when the plan's new output `review_refusals` is not empty. `ci_plan.py` splits what `refusals()` returns into the refusals `ci-status` keeps (accepted state written by a pull request, a missing news file, a skip word, the release preparation's ledger move) and `review_refusals` (everything `review_refusals()` returns today). `ci-status` no longer reads the review refusals. The repository ruleset for `dev` gains `review` as a required check beside `ci-status`, a change the owner runs (specification 160 carries the command). A run whose code is green is then green at `ci-status` and red only at `review` until the review file lands, and the review file's push re-uses the green run as today (138's Decision 2 is unchanged). The display is the point: `gh pr checks` shows one check for the code and one for the review, and no agent reads a red run to find the code passed.

### 5. The build shard runs only where the set is rebuilt

`select()` sets `build` true only when the plan's `rebuild` is true (the release pull request, a tag, the weekly run, a dispatch), never on a push to `dev`. The post-merge run's set is the cached one; the build shard's checks (the trees of every component, the compile records, the zlib tarball) are proved weekly and at every release, where the set is compiled from the pins anyway. The post-merge run loses its 23-minute compile and ends when its last judge leg does.

### 6. The build is arm64 Linux; macOS rebuilds and votes

The `build` job runs on `ubuntu-24.04-arm` whenever it compiles (it keeps `ubuntu-24.04` when it reuses a cached set); it never runs on `macos-15`. The macOS compile becomes a rebuild job, `rebuild-macos-arm64`, on `macos-15`, in the shape of `rebuild-linux-x86-64`: it compiles from the pins, uploads its `SHA256SUMS` and wheel, and runs only when `rebuild` is true. `same-bytes` needs `build`, `rebuild-linux-x86-64` and `rebuild-macos-arm64`, and compares both rebuilds with the build's bytes; the three-host vote stays three hosts. The `build-shard` job goes: its compile was a second arm64 Linux compile of the same pins; the build shard's checks run in the `build` job after the compile when the plan's `build` is true, and the build job hands on the record's id and SHA-256 as `build-shard` did. The published bytes are the build job's, as today; `set-cache.yml` already compiles on `ubuntu-24.04-arm`, so the cached set and the release's set come from the same host.

### 7. same-bytes gates publishing, not the gather

`gather` needs `plan`, `build` and the four judge jobs. `same-bytes` stays in the needs of `ci-status`, `save-set`, `attest` and `publish`, so nothing is signed, published or cached that the three hosts did not agree on, and a release pull request is still red when they disagree. The gather no longer waits for the slowest rebuild (the x86-64 one, 36 minutes) before reading records that were complete at 25.

### 8. The judges run at the plan's parallelism, and the release legs are repacked

The `max-parallel: 18` lines leave the four judge jobs; GitHub's plan limit throttles a run that asks for more. The release shards in `tests/release_shards.toml` are repacked by the judge-step minutes measured in the 0.1.2 release pull request's run (`../research/2026-10-30-where-the-time-goes-since-0-1-1/release-leg-minutes.json`): each shard's groups sum to at most 12 minutes, which gives about 65 shards and 13.7 job-hours against 229 and 14.4 (INFERRED from the measured legs). Each shard's comment names its measured minutes in place of the fuel figure. The one group past the cap, `sympy-r-stats-4-continuous-rv-2` at 18 minutes, is a shard of its own; splitting it is a change to sympy's groups and out of scope. The repacking is a judge change: the shards' names change, the groups and their checks do not, and the plan's rules (`test_release_shards_hold_the_release_groups_alone`, `test_every_item_is_in_one_shard_per_system`) hold it.

### 9. The two times are read from runs, not asserted by tests

The pull request's own run and one release-shape run on the branch head (`workflow_dispatch` with `release-tier: true`, allowed once for this specification by the owner's instruction, in place of `AGENTS.md`'s rule against dispatching a run by hand) give the two wall times; the landing notes record them EXECUTED with the run ids. No test measures time (constitution §4.9); the `lint` step's budget warnings stay as they are.

## Intent

A pull request's run ends when its Linux and Windows legs do, about twelve minutes; the release pull request's run ends about fifty minutes after it starts; the post-merge run ends when its last judge leg does; and a green run means the code is green.

## Design

Files: `.github/workflows/release.yml` (Decisions 1, 4, 6, 7, 8), `release/ci_plan.py` (2, 4, 5), `tests/release_shards.toml` (3, 8), `tests/unit/test_ci_plan.py`, `tests/unit/test_shards.py` and `tests/checks/test_rules.py` (the rules that hold the workflow's needs, the job names, the required check and the shard plan), `docs/contributing/review-and-landing.md` and `docs/contributing/release-process.md` (what runs where), `AGENTS.md` step 6 (the run's shape in one sentence), `context/changes/159-the-runs-take-the-shape-the-data-asks-for.md`.

The workflow after the change, by event:

| event | build | rebuilds and same-bytes | judges | gather needs |
|---|---|---|---|---|
| pull request into dev | cached set, or one compile on arm64 Linux | none | own shards on Linux and Windows; upstream groups on Linux when their inputs changed; verify on Linux | plan, build, the judges |
| push to dev | cached set | none | the normal tier on three systems, verify on three | plan, build, the judges |
| release pull request, weekly, dispatch, tag | compile on arm64 Linux, the build shard inside it | x86-64 Linux and arm64 macOS, same-bytes | both tiers on their systems | plan, build, the judges |

The `review` job and `ci-status` are two checks on a pull request; the ruleset requires both. The new rows in the unit files are seen failing before the workflow changes (the plan's outputs, the needs lists, the absence of `max-parallel` and of `macos-15` in the build job's `runs-on`, the shard times' comments).

## Scope

In: the nine decisions. Out: splitting sympy's long group; test-impact selection of own shards; larger runners; a per-component build cache; the ruleset change itself (160, the owner runs it); the tag's run (155).

## Acceptance criteria

1. On a pull request into `dev` that changes `src/`, the plan's `macos` output is `[]`; on a push to `dev` and with the `ci:full` label it names every own shard. Unit rows in `test_ci_plan.py`.
2. `build.needs` holds `plan` and `inputs` and not `quick`; `ci-status.needs` holds `quick`. A rules row.
3. The `review` job exists with the `if` and the output of Decision 4; `ci-status`'s refusals exclude the review refusals; `review_refusals` is a plan output. Unit rows for the split.
4. On a push to `dev` the plan's `build` output is false; on the release pull request, a tag, the weekly run and a dispatch it is true. Unit rows.
5. The `build` job's `runs-on` names no macOS runner; `rebuild-macos-arm64` exists, runs on `macos-15` only when `rebuild` is true, and is in `same-bytes`'s needs; `build-shard` is no job. A rules row.
6. `gather.needs` is `plan`, `build` and the four judge jobs; `same-bytes` is in the needs of `ci-status`, `save-set`, `attest` and `publish`. A rules row.
7. No `max-parallel` line in the workflow. A rules row.
8. Every release shard's measured minutes, in its comment, are at most 12, except the one named group; the number of release shards is at most 70. A rules row reads the comments.
9. No own shard's leg in the pull request's run exceeds seven minutes on Windows or six on Linux, and the three `own-guest` legs are within two minutes of each other (EXECUTED in the landing notes from the run's job times).
10. The pull request's run ends within 15 minutes of its creation, and the one dispatched release-shape run within 60 (EXECUTED in the landing notes, run ids named).
11. The fast tier, `tests/lint` and the pull request's `ci-status` are green; the news file names the shard plan under `judge` with its reason.

## Landing notes

To be written at the landing: the branch, the pull request, the run ids of criterion 10, the leg times of criterion 9, the review file, the acceptance.
