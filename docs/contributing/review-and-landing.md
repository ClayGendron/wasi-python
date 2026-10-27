# Review and landing

This page explains how a change gets onto `dev`, the project's integration branch, and from there into a release on `main`: what runs on a pull request, who reviews it, what the reviewer checks, and what happens after the merge. The binding rules are in [AGENTS.md](https://github.com/ClayGendron/wasi-python/blob/main/AGENTS.md); this page explains them in words.

## Two branches

- **`dev`** is the default branch. Every change reaches it by a pull request, squashed to one commit.
- **`main`** holds released states and carries the version tags. Only the maintainer moves it, to a release that passed.

## A change is a pull request into `dev`

1. Branch from `dev`'s tip. A branch carries one to three specifications.
2. Write the check before the code. Iterate locally on the fast tier and on single tests.
3. Open a pull request into `dev`. A change that is more than documentation carries a *news file*: its changelog line, the rows of the packages page it changes, and the reason for every change in the test results it expects. `ci-status` is red on a pull request that needs one and has none. At a release the news files are assembled into the changelog, so nobody edits the changelog by hand.
4. The pull request's required check, `ci-status`, runs what the changed files need.
5. A fresh reviewer reads the change and commits a review file as the branch's last commit.
6. When `ci-status` is green and the review's verdict begins "Lands", the author merges the pull request.
7. After the merge, the normal tier runs once in full on three systems, and a job records the result.

Bring a branch up to date by rebasing it, never by a merge commit. The head of the branch is what the tests judge.

## What a pull request runs

The changed files choose the run:

- **Always**: lint, formatting, the type checker, the pure-Python unit tests and the writing rules (the `quick` job).
- **Unless the change is documentation only**: the product's own tests on Linux and Windows, from the artifact set already built for `dev`, and a fresh install of the wheel on Linux.
- **macOS**, when the runner, the build or the test harness changed.
- **The packages' own test suites**, on Linux, when the build, the suites or the harness changed.
- **Everything a merge runs**, when the pull request carries the label `ci:full`.

A pull request never rebuilds the release from the pins and never runs the release tier. Those run before a release, and weekly on `dev`.

The verdict covers what ran. A lost pass is red. Fuel or bytes that grow, fewer passes in a package's suite, and a test moved between tiers are listed under `GROWTH` with the reason the news file gives. When the news file explains one, it is not red on the pull request. When no news file explains it, it is red, named, in the part of the run that saw it. When the result is recorded, each needs its reason.

## After a merge

Each merge into `dev` runs the whole normal tier on macOS, Linux and Windows. When it is green, a job records the result in the repository's accepted state and pushes one commit to `dev`. A red run after a merge means `dev` is broken: the author of the merged change fixes it forward the same day or reverts it, and nothing else merges until `dev` is green.

The job takes every reason it needs from the news files merged since the last record: a growth, fewer passes, a changed test file, a test moved between tiers, a test removed. A test a news file removes is listed, not red, on its pull request and after its merge, so the job can record its removal. A row no news file explains stops the record, with the row named. The fix is a one-line pull request to the news file, and its merge records both.

The record is made in two jobs. The first runs the tests' own code with no secret and writes the record. The second holds the one key that may push to `dev` without a pull request, runs nothing but git, commits the two record files alone, and pushes them only while `dev` is still the commit that was tested. When another merge landed meanwhile, it pushes nothing, and the newer merge's run records both. The record's commit runs nothing that tests: the run's first job sees that only the record changed.

## Every change is reviewed by someone who did not write it

Nothing lands unreviewed. A *fresh reviewer* reads every pull request that is more than documentation: an agent or a person who wrote none of it. The author never reviews their own change.

The reason is simple. An author reads the change they meant to write. A fresh reader reads the change that is actually there. So the reviewer gets the specification and the diff, never the author's summary of them, and checks one against the other.

There is one review per pull request and no confirmation round. The author answers each finding in the pull request. A code fix is a new commit on the same branch; the reviewer reads it and signs again. The review file is committed after the last code commit, so the review covers the code that merges.

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

The pull request's description is the author's self-check. It names the author and says that:

- every new check was seen failing before the code made it pass;
- the Windows results were read;
- every known gap names what will close it;
- the news file is present.

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
    - **Low**: a small fix, written out in full. It needs no further review round once it is answered in writing.
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

## Commit only what you mean

- Before every commit, read `git diff --cached --stat`. A rename or an earlier `git add` stays staged and rides along.
- Every commit on `dev` is green on its own. When two pieces of work share a tree, check the commit in a clean clone.

## In one line

A change is a pull request into `dev` that runs what its files need and merges once a fresh reader's review says it lands; each merge is tested once in full on three systems and recorded by a job.
