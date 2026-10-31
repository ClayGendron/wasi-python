# Where the time goes since 0.1.1, and the shape the runs should take

- **Status:** research with a recommendation, 2026-10-30; the owner adopted it the same day ("can you implement all the recommendations", `../decisions.md`), and it becomes specifications 159, 155, 160 and 161.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Fable 5.1), with three reader agents whose extraction scripts ran in a scratch folder outside the repository; their outputs are summarised here and the run data they read is saved beside this memo (`2026-10-30-where-the-time-goes-since-0-1-1/`).
- **Stands on:** `2026-10-25-a-development-process-that-runs-what-it-needs.md` (the process this memo measures, built as specification 138 and released in 0.1.1); `AGENTS.md`; the constitution §4.14, §5.5 to §5.7; `reviews/README.md`; `changes/README.md`; `.github/workflows/release.yml` and `release/ci_plan.py` at `32affe68`.
- **Labels:** EXECUTED (a `gh` or `git` read, or a script over saved data, by me or a reader), READ (a file), INFERRED (reasoning, including every saving estimate).

## 1. The question

The 0.1.2 release landed sixteen specifications in 27 hours of wall time and the owner judged the process too slow: "the ci runs and all the steps that go into making code changes and getting ready for a release slow us down way more than they should" (the owner, 2026-10-29). The owner keeps the project's own checks and CPython's suite, is open to any other change, wants the full Linux run, build and every test, at or under one hour, and wants a process that works when many people contribute. This memo measures where the time went in the ten days since the pull-request process landed and says what to change.

## 2. The data

Three readers, one each over: the release workflow's run history (the 250 most recent runs, 2026-10-20 12:46Z to 2026-10-29 05:30Z, with job-level timing for 99 of them and for the 0.1.2 release pull request's run; `gh run list`, `gh api .../runs/<id>/jobs`); the 52 pull requests and the git history of `dev` and `main` (`gh api graphql`, `git log`); and the seventeen Claude Code session transcripts of the project (509,950 records, streamed by a script). Every number below is EXECUTED unless labelled otherwise.

### 2.1 Runs and outcomes

| run kind | runs | green | red | cancelled | wall, median | wall, p90 |
|---|---|---|---|---|---|---|
| pull request into dev | 112 | 48 | 29 | 35 | 18.6 min green, 37.6 min red | 46.6 min |
| post-merge on dev | 29 | 18 | 8 | 3 | 24.8 min | 38.4 min |
| release pull request, dev to main | 6 | 4 | 1 | 1 | 97.5 min (0.1.2), 87.8 min (0.1.1) | |
| tag | 3 | 3 | 0 | 0 | 110 min (0.1.2), 137 min (0.1.1) | |

On 2026-10-28 alone there were 93 runs and 187 job-hours for 12 merges, about 6 runs and 15 job-hours per merge. Of all job-hours in the 99 runs with job data, 46% went to runs that ended red and 14% to runs that were cancelled; 40% to runs that ended green. 50 of the 74 red jobs were `ci-status` itself, red by design because the pull request's review file was not yet on the branch. The one real recurring failure, 14 times, was the `upstream-pure-smoke-a` leg, whose archive fetch an upstream host refused (fixed by specification 158).

### 2.2 Where a pull request's wall time goes

With judges on three systems, the last leg to finish was a macOS leg in 13 of 17 green runs, and that leg had waited a median 11 minutes for a runner (the account has five macOS runners, shared by every run at once; macOS queue p90 22 minutes, max 46). Without macOS the critical path is own-guest on Windows or Linux (13.7 and 11.3 minutes, 461 checks), then the gather. `quick` runs first and gates the build and every judge by 2.5 minutes. The own shards, each system's median leg: own-guest 11.3 / 10.7 / 13.7 minutes (Linux / macOS / Windows), own-hostile 7.2 / 6.6 / 9.1, own-embedding-a 7.0 / 6.4 / 8.8, own-embedding 6.4 / 6.1 / 8.2, own-rest 5.1 / 7.0 / none, own-runner 2.1 / 2.5 / 3.0.

### 2.3 Where the release run's time goes

The 0.1.2 release pull request's run, 40796204102, 280 jobs, 97.5 minutes:

| phase | starts | ends | note |
|---|---|---|---|
| quick | +0.3 | +2.8 | gates the build |
| build on macOS | +2.9 | +44.5 | the compile step 34.6 min; the arm64 Linux build shard in the same run compiled in 18.4 min; the x86-64 Linux rebuild in 34.5 |
| normal tier, three systems | +44.5 | +60.1 | 37 legs |
| release tier | +44.5 | +96.4 | 229 legs, 18 at a time, 14.4 job-hours; median leg 3.6 min, longest 18.6 (`upstream-pure-r-001`, one sympy group) |
| gather, accept | +96.4 | +97.5 | |

The release legs' own judge steps sum to 12.6 job-hours and their setup to 1.8. Packed by the measured judge step into shards of at most 12 minutes, the same work is 65 shards and 13.7 job-hours (INFERRED from the measured legs; the 18-minute group is one shard on its own until its suite's groups are split). The tag's run repeated all of it, 110 minutes, then attested and published. The 0.1.2 release, from the preparation merge to the tag run's end, was 3.7 hours, 3.4 of them CI, after three release reviews.

### 2.4 Per change, from git

43 merged pull requests, 38 into `dev`. Median first authored commit to merge 4.9 h, mean 7.3 h. Median open to merge 1.9 h (the 0.1.2 cycle alone: 1.5 h), mean 6.7 h. Median 3 runs per branch, max 11. 32 of 38 pull requests into `dev` carried rework commits after opening, median 2, each one a fresh run. 25 of 43 were rebased after opening: `dev` requires an up-to-date head, so every merge sends every other open pull request back to the runners, which is why the owner regrouped nine open pull requests into three on the afternoon of 10-28 ("dev's strict up-to-date rule lands single merges about an hour apart", `../decisions.md`). Once the accept job existed (10-27 02:32Z) a merge was accepted a median 0.8 h later, max 8.6 h; the maximum is the morning of 10-28, when seven consecutive post-merge runs were red from the one fetch failure and merges waited under the rule that nothing merges while `dev` is red.

### 2.5 Reviews and documents

The 37 pull-request reviews found 14 Highs and 26 Mediums and led to a code fix in 30 cases; 12 carried a second signing. The 109 pre-build reviews found 62 Highs. In the week of 10-26 the tree gained 80 documents for 18 landed specifications, about 4.4 per specification; the 0.1.2 cycle wrote 54,000 words of reviews and 64,000 words of specifications in three days. `context/` holds 142,808 lines of Markdown against 15,993 of `src/`.

### 2.6 The agents' time

Across every session the agents spent a de-duplicated 84 hours in stretches that only polled CI or slept, 33 of them on CI and 59 on a local judge or build; nearly all of the local waiting is from the lane era before 10-25. They polled 301 distinct run ids. On the 68 spec branches there were 151 rounds of push, red run, edit, push again.

## 3. What is slow, in order

1. **The release run's shape.** A macOS compile of 35 to 42 minutes gates every judge, then 229 release legs run 18 at a time for 52 minutes. The Linux compile is 18 to 23 minutes and the same work at the plan's parallelism is about 25 minutes (INFERRED, §2.3).
2. **macOS on pull requests.** Five shared macOS runners put a queue of up to 46 minutes on the critical path of a run whose Linux and Windows legs are done at 19 minutes.
3. **Runs per change.** Three to six runs per merged change: a rework commit per review finding, a run that is red by design until the review file lands, and a re-run of every open pull request after every merge under the up-to-date rule.
4. **The merge freeze.** One red leg on `dev` stopped every merge for eight hours.
5. **Documents per change.** Not a CI cost, but the largest agent-time cost after waiting.

The tests themselves are not slow. The longest own leg is 14 minutes and the whole normal tier on Linux is 3.2 job-hours; the release tier is 12.6 job-hours of judge steps that run in parallel.

## 4. What to change, and what each saves

Baseline per change: about 90 minutes open to merge on the critical path in the 0.1.2 cycle, about 900 job-minutes of CI, plus a share of the release. Savings are INFERRED from the measured parts.

| # | change | saves per change, wall | saves per change, CI job-min | specification |
|---|---|---|---|---|
| 1 | The build and the judges run beside `quick`, not behind it | 8 min | 0 | 159 |
| 2 | No macOS legs on a pull request; macOS stays post-merge, weekly and at the release | 15 to 30 min, and the p90 tail | 200 | 159 |
| 3 | own-guest split in three, own-hostile and own-embedding-a in two | 20 min | small cost | 159 |
| 4 | A missing review file fails a separate `review` check, never `ci-status` | removes 50 red reads and re-polls | 0 | 159 |
| 5 | The post-merge run without a fresh compile; the build shard runs weekly and at the release | 5 min per merge | 23 | 159 |
| 6 | The release judges from the arm64 Linux build; the macOS compile votes on same-bytes off the critical path; same-bytes leaves the gather's needs | 20 min per release run | 0 | 159 |
| 7 | The release legs repacked to at most 12 minutes each; the judge jobs run at the plan's parallelism | 30 min per release run | 180 | 159 |
| 8 | The tag's run rebuilds, proves the same bytes as the release pull request judged, attests and publishes; it does not re-judge | 80 to 100 min per release | 1,000 | 155 |
| 9 | Fix-forward replaces the freeze: a red post-merge run opens an issue, the author fixes or reverts the same day, unrelated merges continue | bounds stalls like 10-28's 8 h | 0 | 160 |
| 10 | `dev` no longer requires an up-to-date head; the post-merge run catches what two pull requests do together | about 2 runs on a busy day, 40 min and 240 job-min | 240 | 160 |
| 11 | One fix commit per review round; the reviewer signs once, and a Low needs no second signature | 25 min, one run fewer | 120 | 160 |
| 12 | The release reviews run in parallel with the last specifications in 45-minute boxes; the release-notes read folds into the security review | 1 to 2 h per release | 0 | 160 |
| 13 | A specification is held to about 1,500 words and its landing notes to ten lines; the news file carries the rest | 30 to 60 min of agent time | 0 | 160 |
| 14 | Growth on `dev` is listed, never refused; claims are reconciled at the release | a one-line news-file cycle, 2 of 16 changes in 0.1.2 | 60 | 161 |

Considered and not taken: dropping Windows from pull requests (3 minutes, and Windows found 14 of 24 real reds in the lane era); test-impact selection of own shards (5 minutes a run, a missed dependency reaches `dev`; later); larger hosted runners for the compile (paid); a per-component build cache (a recipe change, later); a nightly matrix in place of the per-merge run (only with many contributors); GitHub's merge queue, which needs an organization-owned repository and is the right end state for many contributors.

## 5. The arithmetic for the one-hour run

INFERRED from §2.3. Build on arm64 Linux, 22 minutes including the zero-patch check and the assets; then the normal tier and the repacked release tier side by side, 13.7 plus 3.2 job-hours at the plan's forty jobs at once, about 25 minutes, with the 18-minute group starting first; then the gather, one minute: about 50 minutes. The x86-64 rebuild, 36 minutes, and the macOS rebuild, 35 to 42, start at the plan and finish before the judges do; same-bytes gates attest and publish, not the gather. On a pull request: quick beside a 2-minute restore of the cached set, the split own shards on Linux and Windows under 7 minutes each, the gather: about 12 minutes.

## 6. Many contributors

The required checks must be ones an outside contributor can satisfy from a fork: `quick`, the Linux judge, the Windows judge, each reading the cached set, which a fork's pull request can restore from `dev`'s cache scope. The review becomes a GitHub review by a maintainer or a maintainer's agent, with the review record generated from it at merge time, because an outsider cannot be asked to commit a fresh-agent review file into the tree. Fuel claims stay at the release. The per-merge three-system run stays until the queue is busy; then the repository moves to an organization and the merge queue batches it. The organization move is the owner's; specification 160 records it as the next step and changes nothing that would need to be undone.

## 7. One line

The tests are fine; the runs around them wait on a macOS compile, a macOS queue, a throttle, a rule that re-runs every neighbour, and a freeze; take those away and a pull request is twelve minutes, the full Linux run fifty, and a release an afternoon.
