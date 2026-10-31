# 160: The rules follow the data

- **Status:** drafted 2026-10-30. The owner asked for it on 2026-10-30 ("can you implement all the recommendations") and agreed the same day to the three rule changes it carries (constitution §4.14, §5.7; the repository ruleset for `dev`).
- **Date:** 2026-10-30
- **Owner:** Clay Gendron
- **Kind:** documents and the repository's settings: `AGENTS.md`, the constitution, `context/README.md`, `reviews/README.md`, `changes/README.md`, `docs/contributing/`, the pull request template, one job of the release workflow (the issue on a red post-merge run), one lint warning; not structural; parallel-safe with 159 and 161.
- **Depends on:** the owner's instruction and decisions of 2026-10-30; the owner runs the ruleset command (Decision 2). Nothing in flight.
- **Research it stands on:** `../research/2026-10-30-where-the-time-goes-since-0-1-1.md` (§2.4, §2.5, §4 rows 9 to 13, §6).

## The problem

Four rules cost more than they protect (EXECUTED, the memo). The rule that nothing merges while `dev`'s last post-merge run is red held every merge for eight hours on 2026-10-28 over one fetch failure. The ruleset's requirement that a pull request be up to date with `dev` before it merges sent every open pull request back to the runners after every merge: 25 of 43 were rebased after opening, and the owner regrouped nine into three to escape it. A review's Low findings cost a fix commit and a second signing each, and a pull request carried a median two rework commits, each a run. The three release reviews ran one after another on the release day, and the 0.1.2 cycle wrote 64,000 words of specifications and 54,000 of reviews in three days.

## Decisions

### 1. Fix-forward replaces the freeze

Constitution §5.7's sentence "a red post-merge run blocks every merge but its fix or revert" becomes: a red post-merge run means `dev` is broken on the lines it names; the author of the merged change fixes forward the same day or reverts; other pull requests keep merging, and the next post-merge run judges everything since the last acceptance, so a second red names both causes. The release workflow's weekly issue job becomes the red-run issue job: on a push to `dev` whose gather or any judge leg is red, it opens one issue titled by the red lines, or adds a comment to the one open, as the weekly run does today; the issue closes when a post-merge run is green. `AGENTS.md` step 9 and `docs/contributing/review-and-landing.md` say the same. The acceptance is unchanged: it follows a green gather only, so a red `dev` is never recorded.

### 2. The up-to-date rule goes, and `review` is required

The ruleset `dev takes pull requests` (id 25925120) changes in two places: `strict_required_status_checks_policy` becomes false, and `required_status_checks` gains `review` (specification 159's job) beside `ci-status` and the docs site's strict build. A pull request then merges on its own green head whether or not `dev` moved since; what two pull requests do together is the post-merge run's to find, under Decision 1. Constitution §4.14's words "the up-to-date rule makes the head the tree the squash puts on `dev`" are replaced by: the head is judged as it is, and the merge's tree is judged by the post-merge run. The change is a permission change the agent may not make (`AGENTS.md`): the builder writes the ruleset's full body to `build/rulesets/dev.json`, gives the owner the one line `gh api -X PUT repos/ClayGendron/wasi-python/rulesets/25925120 --input build/rulesets/dev.json`, reads it back with `gh api`, and records the read in the landing notes.

### 3. One signature

`reviews/README.md`: the reviewer signs once. A Low is written out in full and needs no second signing; the author answers it in the pull request or fixes it in the same commit as any other finding. A High or a Medium that needs code is fixed in one commit for the whole round, and the reviewer reads that commit and signs once more. The pull request template gains the line "Fix commits: one per review round". `ci-status` and `review` are unchanged: the review file still follows the last code commit.

### 4. The release reviews run beside the last changes

`docs/contributing/release-process.md` and `reviews/README.md`: the security review and the structural review begin when the last specification of the release opens its pull request, each in a 45-minute box, reading `dev` at that point and re-reading only the diff since; the release-notes review becomes a section of the security review (the CHANGELOG section read once against the news files), and `tests/harness/scan.py`'s rule that a release has a release-notes review file is replaced by a rule that the security review has a "Release notes" section. The preparation pull request then carries two files, not three.

### 5. Caps on the documents

`context/README.md`'s lifecycle rules: a specification says its decisions in about 1,500 words; its landing notes are at most ten lines (status, branch, pull request, run ids, review, acceptance); the history of how it was built belongs in the pull request and the news file, and a measurement belongs in a memo. A pull-request review is at most 800 words outside its findings. `tests/lint` gains a warning, not a failure, in the shape of the fast-tier budget's time warnings: a specification over 2,000 words or a landing-notes section over 15 lines is named in the quick job's summary. Existing documents are not rewritten.

### 6. Many contributors, written down

`docs/contributing/review-and-landing.md` gains "From a fork": what runs on a fork's pull request (`quick`, the Linux and Windows judges, from `dev`'s cached set), who reviews (a maintainer or a maintainer's agent, whose review file the maintainer commits to the branch), and that the merge is the maintainer's. `context/decisions.md` records that the organization move and the merge queue are the owner's next step when the queue is busy, and that nothing in this specification would need undoing then.

### 7. `AGENTS.md`

Steps 6 to 9 of "Working autonomously" are rewritten in the fewest words that hold the new rules: what a pull request runs, the two checks, one fix commit per round and one signature, merge on green, fix-forward. The timings sentence points at the memo's measured numbers.

## Intent

A merge is held only by its own checks and its review; a red `dev` is an issue with an owner, not a gate on everyone; a review costs one round; a release's reviews are done before the release day; and a specification is read in ten minutes.

## Design

Files: `context/constitution.md` (§4.14, §5.7, the Status line), `context/decisions.md`, `context/README.md`, `context/reviews/README.md`, `AGENTS.md`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/workflows/release.yml` (the issue job's trigger), `tests/harness/scan.py` and `tests/checks/test_rules.py` (the release-notes rule), `tests/lint/` (the warning), `docs/contributing/review-and-landing.md`, `docs/contributing/release-process.md`, `build/rulesets/dev.json` (not committed), `context/changes/160-the-rules-follow-the-data.md`.

## Scope

In: the seven decisions. Out: the organization move; the merge queue; rewriting existing specifications or reviews; a lint failure on length.

## Acceptance criteria

1. The constitution's §4.14 and §5.7 say what Decisions 1 and 2 say, and its Status line records the amendment of 2026-10-30. READ.
2. The ruleset, read back with `gh api`, has `strict_required_status_checks_policy` false and `review` among its required checks. EXECUTED in the landing notes.
3. The red-run issue job runs on a red push to `dev` and on the weekly run, and on nothing else. A rules row.
4. `reviews/README.md`, the template, `AGENTS.md` and the two contributing pages carry Decisions 1, 3, 4, 6 and 7. READ, and the writing rules green.
5. The release-notes rule is the security review's section rule; the 0.1.2 files pass it unchanged. A unit row.
6. The length warning names a scratch specification of 2,001 words and is silent on one of 1,999. A unit row.
7. The fast tier, `tests/lint` and the pull request's `ci-status` are green; the news file is present.

## Landing notes

To be written at the landing.
