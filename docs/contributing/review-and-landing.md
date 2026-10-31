# Review and landing

This page explains how a change gets onto `dev`, the project's integration branch, and from there into a release on `main`: what runs on a pull request, who reviews it, what the reviewer checks, and what happens after the merge. The binding rules are in [AGENTS.md](https://github.com/ClayGendron/wasi-python/blob/main/AGENTS.md); this page explains them in words.

## Two branches

- **`dev`** is the default branch. Every change reaches it by a pull request, squashed to one commit.
- **`main`** holds released states and carries the version tags. Only the maintainer moves it, to a release that passed.

## A change is a pull request into `dev`

1. Branch from `dev`'s tip. A branch carries one to three specifications.
2. Write the check before the code. Iterate locally on the fast tier and on single tests.
3. Open a pull request into `dev`. A change that is more than documentation carries a *news file*: its changelog entry, written for someone who uses wasi-python and did not follow the change (what it gives them, the one fact that changed, and a link to the page that explains it, under New, Faster, Security, Fixed, Upgrading or For contributors), the rows of the packages page it changes, and the reason for every change in the test results it expects. `ci-status` is red on a pull request that needs one and has none. At a release the news files are assembled into the changelog, so nobody edits the changelog by hand.
4. Two checks are required: `ci-status`, which runs what the changed files need, and `review`, which holds the review file.
5. A fresh reviewer reads the change and commits a review file as the branch's last commit.
6. When the checks are green and the review's verdict begins "Lands", the author merges the pull request.
7. After the merge, the normal tier runs once in full on three systems, and a job records the result.

A branch need not be up to date with `dev` to merge. Its head is judged as it is, and the run after the merge judges the tree the merge makes. To bring a branch up to date, rebase it, never merge `dev` into it.

## What a pull request runs

The changed files choose the run:

- **Always**: lint, formatting, the type checker, the pure-Python unit tests and the writing rules (the `quick` job).
- **Unless the change is documentation only**: the product's own tests on Linux and Windows, from the artifact set already built for `dev`, and a fresh install of the wheel on Linux.
- **A change to the agents' settings or instructions** (`.claude/`, `.agents/`, `AGENTS.md`, `CLAUDE.md`) runs the `quick` job alone, as documentation does, but it is not documentation only: it carries a news file and gets a review.
- **macOS**, when the runner, the build or the test harness changed.
- **The packages' own test suites**, on Linux, when the build, the suites or the harness changed.
- **Everything a merge runs**, when the pull request carries the label `ci:full`.

A pull request never rebuilds the release from the pins and never runs the release tier. Those run before a release, and weekly on `dev`.

The verdict covers what ran. A lost pass is red. Fuel or bytes that grow, fewer passes in a package's suite, and a test moved between tiers are listed under `GROWTH` with the reason the news file gives. When the news file explains one, it is not red on the pull request. When no news file explains it, it is red, named, in the part of the run that saw it. After the merge such a row is listed as unclaimed, not red, and the release asks for its reason.

## After a merge

Each merge into `dev` runs the whole normal tier on macOS, Linux and Windows. When it is green, a job records the result in the repository's accepted state and pushes one commit to `dev`. A red run after a merge means `dev` is broken on the lines it names. The run opens an issue titled by those lines, or comments on the one already open. The author of the merged change fixes it forward the same day or reverts it. Other pull requests keep merging meanwhile: the next run after a merge judges everything since the last record, so a second red names both causes. The next green run after a merge closes the issue. A red run is never recorded.

The job takes every reason it needs from the news files merged since the last record: a growth, fewer passes, a changed test file, a test moved between tiers, a test removed. A test a news file removes is listed, not red, on its pull request and after its merge, so the job can record its removal. A growth, fewer passes, a changed test file or a move between tiers that no news file explains does not stop the record. The record names it as unclaimed. The release asks for the reason of each unclaimed row and waits until it has one. Write the reason in the news file at the merge, or in the release ledger in the release's preparation. A lost pass, or a removed test no news file names, still stops the record.

The record is made in two jobs. The first runs the tests' own code with no secret and writes the record. The second holds the one key that may push to `dev` without a pull request, runs nothing but git, commits the two record files alone, and pushes them only while `dev` is still the commit that was tested. When another merge landed meanwhile, it pushes nothing, and the newer merge's run records both. The record's commit runs nothing that tests: the run's first job sees that only the record changed.

## Every change is reviewed by someone who did not write it

Nothing lands unreviewed. A *fresh reviewer* reads every pull request that is more than documentation: an agent or a person who wrote none of it. The author never reviews their own change.

The reason is simple. An author reads the change they meant to write. A fresh reader reads the change that is actually there. So the reviewer gets the specification and the diff, never the author's summary of them, and checks one against the other.

There is one review per pull request, one fix commit per review round, and one signature. The author answers each finding in the pull request and fixes a round's findings in one commit on the same branch. A Low finding answered in writing, or one that changes only the project's records, needs no second signing. Every finding fixed in code, a Low among them, goes into the round's one fix commit, and the reviewer reads that commit before signing once more. The review file is committed after the last code commit, so the review covers the code that merges. A review is at most 800 words outside its findings.

`ci-status` holds the review. It is red unless the branch carries a review file, named after its news file, committed after the last code, whose reviewer is not the author and whose verdict begins "Lands". The author is the one the pull request's description names, and the session on each code commit. A reviewer that the author's session started fresh, given only the specification and the diff, says so on its reviewer line. This guards the process, not identity: it holds that nothing merges without a review signed after the last code.

The review file's own push runs only the `quick` job. Every other job's result is the run of the head it follows, which is re-used, since nothing but documentation changed.

## Some changes are reviewed before they are built

A few kinds of change are reviewed twice: once as a design, before any code is written, and once as code. A wrong design is cheaper to catch before it is built. These are:

- a change to the guest's imports or exports;
- a change to the artifact set;
- a change to the build recipe;
- a *structural* change: one that adds shared module-level state, a platform branch or a use of the engine's private API outside the one module meant for it, a test seam that is not on the process object, or that takes a module or a function past its size limit.

Every other change is reviewed once, on its pull request, where the reviewer reads the code with the specification.

## The author's self-check

The pull request's description is the author's self-check. It starts from the pull request template, `.github/PULL_REQUEST_TEMPLATE.md`. Opened with `gh pr create --body` or `--body-file`, as an agent without a terminal must, it starts from a copy of that file. Its `Author:` line names the author, a session's link or a name, and `ci-status` reads that line to tell the author from the reviewer. The name goes on that line, or on the next line when the `Author:` line is left empty; another field, a list item, a heading or a table row there names no one. It names the specifications the branch carries, one to three, and says that:

- every new check was seen failing before the code made it pass;
- the Windows results of the newest run on this head were read;
- every known gap names what will close it;
- the news file is present.

An edit of the description re-uses the newest run on the same head when it is green, and otherwise starts the check again, so tick every box in one edit.

A reviewer who finds an item unchecked says so in the review.

## What the reviewer does

Reviews are time-boxed, and each review states its box. Within it, the reviewer:

1. **Reads the pull request's run.** It reads `ci-status` and the summary of the test results, and starts no run of its own. Locally it runs single tests.
2. **Checks each acceptance criterion against its evidence**, one line each, and labels each line: *executed* (it ran it), *read* (it read the code or document) or *inferred* (it reasoned it).
3. **Checks the diff against the project's [principles](principles.md)**: the hard constraints and the list of things never to do. It checks the news file's reasons against the diff and the `GROWTH` list.
4. **Checks the structure.** Does the change add a concern, a lifecycle flag, shared state, a test seam, a platform branch or an overlong function that would make the code harder to keep?
5. **Probes.** It runs one to three tests of its own choosing.
6. **Ranks its findings**:
    - **High**: a wrong answer or an unsafe default. The change does not land.
    - **Medium**: a guarantee without evidence. The review says what evidence would close it.
    - **Low**: a small fix, written out in full. Answered in writing, it needs no second signing; fixed in code, it goes into the round's one fix commit, which the reviewer reads.
7. **Gives a verdict in one sentence**: it lands, or it does not land yet, naming what stands.

## How structure is judged

Behaviour is not the only thing reviewed. The runner's structure is scored against eight qualities, each Strong, Adequate or Weak with a one-line reason:

- **Contract**: few public names, each promise checked by a test, failures promised by type.
- **Safety**: safe defaults, every channel to the host bounded, arguments checked before any side effect.
- **Layering**: one module touches the engine's private API; policy is apart from mechanism.
- **Process state**: shared state is owned by one object and reset in one place.
- **Portability**: operating-system differences live in one module behind one interface.
- **Testability**: seams are constructor parameters or protocol objects, and tests drive public behaviour.
- **Evolvability**: one person can hold each module and each function in their head, and the code says why without the project's records open.
- **Operability**: the results and messages still say what the guest did.

Before every release, a fresh reviewer scores the runner's code this way and compares the scores with the last release. A second fresh reviewer checks the release against the written threat model. The release waits on the High findings of both.

## The ratchet

The test results are a *ratchet*: a run that loses an accepted pass is red, and growth in the fuel or bytes a check uses needs a stated reason. New passes never pay for a lost one.

## From a fork

A pull request from a fork runs what a pull request from this repository runs: the `quick` job, and the product's own tests on Linux and Windows from the artifact set already built for `dev`, which a fork's run restores from `dev`'s cache. A fork's author is not asked to commit a fresh reviewer's file. A maintainer, or an agent a maintainer runs, reviews the change, and the maintainer commits the review file to the pull request's branch, which GitHub allows when the author lets maintainers edit it. The merge is the maintainer's.

## Commit only what you mean

- Before every commit, read `git diff --cached --stat`. A rename or an earlier `git add` stays staged and rides along.
- Every commit on `dev` is green on its own. When two pieces of work share a tree, check the commit in a clean clone.

## In one line

A change is a pull request into `dev` that runs what its files need and merges once a fresh reader's review says it lands; each merge is tested once in full on three systems and recorded by a job, and a red one is fixed forward the same day while other merges go on.
