# Review and landing

This page explains how a built change gets onto `main`: who reviews it, what the reviewer checks, and how reviewed changes land together. The binding rules are in [AGENTS.md](https://github.com/ClayGendron/wasi_python/blob/main/AGENTS.md); this page explains them in words.

## Every built change is reviewed by someone who did not write it

Nothing lands unreviewed. When a change is built, a *fresh reviewer* reads it: an agent or a person who wrote none of it. The author never reviews their own change.

The reason is simple. An author reads the change they meant to write. A fresh reader reads the change that is actually there. So the reviewer gets the specification and the diff, never the author's summary of them, and checks one against the other.

The review is written down and kept in the repository. Each finding is fixed, or answered in writing, before the change lands, and the notes written at landing cite the review.

## Some changes are reviewed before they are built

A few kinds of change are reviewed twice: once as a design, before any code is written, and once as code. A wrong design is cheaper to catch before it is built. These are:

- a change to the guest's imports or exports;
- a change to the artifact set;
- a change to the build recipe;
- a change to the runner's code;
- a *structural* change: one that adds shared module-level state, a platform branch or a use of the engine's private API outside the one module meant for it, a test seam that is not on the process object, or that takes a module or a function past its size limit.

A specification that only changes the tests' checks, or only the project's written records, may skip the review before it is built.

## Before asking for a review

The builder writes a short self-check at the top of the review request. It says, among other things, that:

- the branch is rebased onto `main`'s tip, and the base commit is named;
- the release workflow ran on this exact commit, and its result was read;
- every number in the change was measured on this base;
- every new check was seen failing before the code made it pass;
- `ruff check`, `ruff format --check` and the fast tier of the tests are green.

A reviewer who finds an item unchecked says so in the review.

## What the reviewer does

Reviews are time-boxed, and each review states its box. Within it, the reviewer:

1. **Re-runs the counted tests.** It reads the builder's run of the release workflow when that run is on the exact commit reviewed, and otherwise dispatches its own. Locally it runs only the fast tier or single tests.
2. **Checks each acceptance criterion against its evidence**, one line each, and labels each line: *executed* (it ran it), *read* (it read the code or document) or *inferred* (it reasoned it).
3. **Checks the diff against the project's [principles](principles.md)**: the hard constraints and the list of things never to do.
4. **Checks the structure.** Does the change add a concern, a lifecycle flag, shared state, a test seam, a platform branch or an overlong function that would make the code harder to keep?
5. **Probes.** It runs one to three tests of its own choosing.
6. **Ranks its findings**:
    - **High**: a wrong answer or an unsafe default. The change does not land.
    - **Medium**: a guarantee without evidence. The review says what evidence would close it.
    - **Low**: a small fix, written out in full. It needs no further review round once it is answered in writing.
7. **Gives a verdict in one sentence**: it lands, it lands once the Medium findings are closed, or it does not land yet, naming the High finding.

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

## How reviewed changes land

`main` changes in one place only, through the *landing lane*: one agent or person who rebases reviewed branches, judges them, records the result, and fast-forwards `main`. Builders and reviewers work in parallel, each in a worktree of its own. Only the lane records an accepted result.

Reviewed changes land in *waves*: a group of up to five reviewed specifications, landed together. A wave holds at most one new package, at most two other changes to the build, and the rest changes that cannot interfere with each other. In a wave:

1. Each builder rebases its branch onto the wave's tip, in the order the lane sets, and names every conflict it resolved.
2. The lane rebuilds the artifact set once, runs the tests once on the wave's tip, and records the result once, with every specification's reasons.
3. A fresh reviewer, who reviewed none of the wave's entries, reads the integration: each rebase against what was reviewed, the conflicts each builder named, and every change in the test results against what the specifications claimed.
4. A red entry, an unexplained difference or an unclaimed change in the results removes that entry from the wave, never the whole wave. The entry comes back once it is fixed.

The test results are a *ratchet*: a run that loses an accepted pass, or grows the fuel or bytes a check uses without a stated reason, is red. New passes never pay for a lost one.

## Commit only what you mean

- Before every commit, read `git diff --cached --stat`. A rename or an earlier `git add` stays staged and rides along.
- Every commit on `main` is green on its own. When two pieces of work share a tree, check the commit in a clean clone.
- A worktree's branch carries exactly one specification.

## In one line

A fresh reader reviews every built change against its specification, risky changes are reviewed before they are built too, and reviewed changes land together through one lane that tests and records them once.
