# 195: A review that waits fails no run

- **Status:** built 2026-11-15, in review. Asked for on 2026-11-15 by the owner: "stop triggering so many failed jobs. I get an email every time and it's a huge pain. Can you have some sort of pre PR, push or commit check that helps with this? At least for the vast majority of cases? I've gotten 6 failure emails today alone. Understand the problem and resolve it." (`../decisions.md`, "Failure mail is for mistakes").
- **Date:** 2026-11-15
- **Owner:** Clay Gendron
- **Kind:** build-class (the release workflow's `plan`, `review` and `ci-status` jobs, the decision job `release/ci_plan.py`, rule 17 and the review job's rules in `tests/harness/scan.py`, and a new local script `release/precheck.py`). Not structural: nothing under `src/` changes. No wasm build, and nothing the build makes changes. Not reviewed before it is built: it changes no job that holds a token or `id-token`, no permission, no upload and nothing a release signs; it changes only whether two checks nothing needs fail their run while they are red (constitution §5.6 asks a pre-build review for the guest's imports or exports, the artifact set and the build recipe).
- **Depends on:** 138 (the review job and `ci-status`'s refusals), 159 (the runs' shape and the re-use of a green run).
- **Research it stands on:** the Actions API's listing of the release workflow's runs, read 2026-11-15; each failed run's jobs and the failed job's log; GitHub's community discussion 15452 on `continue-on-error` at the job level.

Labels: EXECUTED, run and seen; READ, read from a file or a page, cited; INFERRED, reasoned.

## The problem

GitHub mails the account a run belongs to every time a workflow run fails. Every agent pushes through the owner's account, so every failed run is a mail to the owner.

On 2026-11-14 (New York time) six runs of the release workflow failed (READ, the Actions API, runs 43649195518, 43651675996, 43652810419, 43656918349, 43658743724, 43660928228). All six were pull requests into `dev`: #105 twice, #107 once, #108 twice, #109 once. In all six, exactly two jobs failed, `review` and `ci-status`, and both failed for one reason: "a pull request that is not documentation only has no review file … among its changed paths" (READ, each `review` job's log). Every build, judge, `quick` and gather job of those runs was green. The eight runs cancelled that day by a newer push to the same pull request sent no mail (INFERRED: the owner counted six mails, the number of failed runs).

The pattern is older. Of the 13 failed pull-request runs from 2026-11-01 to 2026-11-05, 11 failed on the review check: nine with no review file yet, two with a review that a later code commit left behind (READ, the same API). The other failures were a Windows checkout step that broke beside one of those, a macOS shard of the 0.1.3 release pull request, the acceptance push of a merge racing `dev`, and the 0.1.4 tag's signature check, none of which a check on the author's machine would have caught.

So the cause is the process working as written. AGENTS.md has the reviewer read the pull request's run before it writes the review, and the review file is the branch's last commit. The first run of every pull request therefore has no review, and its two review checks fail the run. A round with a fix commit leaves the review behind the code, and fails the next run the same way. The failure is by design: it is what stops an unreviewed merge. The mail is not: it reports a state every pull request passes through as if something broke.

## Decisions

### 1. Three of the review's refusals wait, and the others are mistakes

The review check refuses a pull request for one of eight reasons. Three wait on the reviewer, not on a mistake:

- no review file among the changed paths (none written yet);
- a review followed by a commit that changes code (a fix the reviewer has not read yet);
- a verdict whose first line does not begin "Lands" (a review that asks for a fix).

The others are mistakes, and stay failures: a `Reviewer:` line that is empty or names the author or the author's session, two review files of one date changed by one commit, a review file not in the head's tree, and a base that cannot be read. So are ci-status's refusals that are not the review's: a missing news file, accepted state written by a pull request, a skip word, a ledger written wrong.

The decision job writes two new outputs. `review_waiting` is true when the review job's refusals are not empty and every one waits. `waiting` is true when ci-status's refusals are not empty and every one waits.

### 2. A waiting check is red and does not fail its run

The review job takes `continue-on-error: ${{ needs.plan.outputs.review_waiting == 'true' }}`. ci-status takes `continue-on-error` when `waiting` is true and no job it needs failed or was cancelled. Each step is unchanged, so the job still fails. With `continue-on-error`, GitHub marks the failed job's check red and the workflow run green (READ, GitHub community discussion 15452: "the job is marked as failed … the whole workflow is still marked as successful"). GitHub mails on a failed run, not on a failed check, so no mail is sent (INFERRED; this pull request's own first run, which has no review yet, is the evidence, recorded in the landing notes).

What the checks guard at the merge does not move. Both required checks are still red while the review waits, so the pull request cannot merge. The run's green conclusion is read by nothing that merges or accepts: `accept-release.yml` acts only on a pull request into `main`, where no review is asked, and the re-use of a green run reads each job's conclusion and already passes over `review` and `ci-status` (READ, `find_reusable` and `reusable_after_edit`, `NOT_THE_CODES`). No job needs either check, so nothing carries on past them.

### 3. Rule 17 has one exception, and holds its exact shape

Rule 17 refused any `continue-on-error` in the workflow. It now allows exactly the two job-level lines of decision 2, on `review` and `ci-status`, each with its expression as `WAITING_CONTINUE` in `tests/harness/scan.py` holds it, and only while no job needs that job. Any other `continue-on-error`, at a job or a step, is refused as before. Dropping a line is allowed: the job then fails its run, which is stricter. The review job's rules also hold that the plan hands on both outputs.

### 4. A local precheck, and an agent rule

`release/precheck.py` runs, on the author's machine, the `run:` script of every step of the `quick` job, read out of the workflow itself so the two cannot drift. Then it reads the branch as the decision job reads a pull request into `dev` and prints the refusals: a mistake fails it, a wait is printed and does not. `--plan-only` runs only that read, in about a second. `--install` writes a `pre-push` hook that runs it, and refuses to overwrite a hook of another making.

AGENTS.md gains a rule: run `uv run python release/precheck.py` before every push. In the window measured, `quick` itself never failed a run, so the precheck would have saved no mail there (INFERRED from the failures above). It keeps it that way, and it names a missing news file or a review signed by its author before the run does.

### 5. Not chosen

- **Skipping the review check on a draft pull request.** Every open pull request of 0.1.5 is a draft, so this would have stopped the same mails. It was not chosen because a skipped job reports success: between marking the pull request ready and the new run creating its checks, the head carries two green required checks, and a run that fails to start leaves them green. Decision 2 keeps the checks red the whole time.
- **A commit status that stays pending.** The review job could post a pending status instead of failing. That needs a token that can write statuses and a ruleset that requires a new status name, both the owner's to change, for the same result.
- **Writing the review before the first push.** The reviewer reads the run; there is no run to read before the push.

## Design

The decisions are the design. `review_refusals` builds its three waiting messages from the phrases `NO_REVIEW_YET`, `REVIEW_BEHIND` and `NOT_LANDED_YET`, and `only_waiting` holds a list of refusals to them, so a message and its test cannot part. `outputs` writes `review_waiting` from the review job's refusals and `waiting` from ci-status's. The workflow reads both in `continue-on-error`, where `needs` is in reach and the results of ci-status's needs are known. The precheck imports the judge's own workflow reader (`tests/harness/scan.py`) for quick's steps and `ci_plan` for the refusals, so it holds no copy of either.

## Intent

A pull request into `dev` that waits only on its review leaves both required checks red and its run green, so its author gets no failure mail. A mistake still fails the run, and nothing merges without a review signed after the last code.

## Scope

`release/ci_plan.py` (the three waiting phrases, `only_waiting`, two outputs and a line of the step summary); `.github/workflows/release.yml` (the plan's two outputs, the review job's and ci-status's `continue-on-error` and comments); `tests/harness/scan.py` (`WAITING_CONTINUE`, rule 17, the review job's rules); `tests/unit/test_ci_plan.py`, `tests/unit/test_scan.py`, `tests/unit/test_precheck.py`; `release/precheck.py`; `AGENTS.md`; `docs/contributing/first-change.md` and `review-and-landing.md`; `../decisions.md`. Nothing else.

## Acceptance criteria

1. `tests/unit/test_ci_plan.py` covers: no review yet, a review left behind by code and a verdict that does not land yet each wait; a review signed by the author or by no one does not; a missing news file beside a waiting review leaves the review job waiting and fails ci-status; a run refused nothing and a push never wait. Each row is seen failing on `dev`'s `ci_plan.py`.
2. `tests/unit/test_scan.py` covers: the real workflow passes rule 17 with both lines; rule 17 names `continue-on-error: true` on the review job, a ci-status expression that drops the failure test or reads `review_waiting`, a job that needs `review`, and the same line on any other job; the review job's rules name a plan that hands on neither output. Each row is seen failing on `dev`'s workflow.
3. `tests/unit/test_precheck.py` covers: the precheck runs every scripted step of `quick` in order, and the hook it installs runs it and leaves another's hook alone.
4. This pull request's first run, with no review file, ends with `review` and `ci-status` red and the run's conclusion success (EXECUTED, its id in the landing notes), and the run after the review file is green.

## Landing notes

(Filled in as the pull request runs.)
