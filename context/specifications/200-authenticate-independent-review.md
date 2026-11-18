# 200: Authenticate independent approval on dev

- **Status:** prepared for the owner to activate after assigning an independent reviewer.
- **Date:** 2026-11-17
- **Owner:** Clay Gendron
- **Kind:** repository ruleset proposal and contributor documentation.
- **Depends on:** 138 (pull requests and the acceptance identity), 160 (the three required checks).
- **Research it stands on:** the live repository rulesets and GitHub's [ruleset semantics](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets) and [review rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).

## Decisions

Add an independent GitHub approval to the existing review file and checks. The owner chooses the reviewer and activates the rule. Ordinary changes, including documentation, need the approval. The acceptance workflow keeps its direct push of the progress record.

## Intent

A review file written through the author's GitHub identity cannot authenticate an independent approver. GitHub can enforce this once a separately controlled account with write access is available.

## Design

Add a branch ruleset for `refs/heads/dev` beside the existing ruleset. This avoids a read-modify-write of the existing checks, branch protections and bypass actors. Require one approval, dismiss stale approvals and require approval of the most recent reviewable push. Match the existing deploy-key bypass so the acceptance push satisfies both rulesets. The owner verifies which write-enabled keys exist before activation. A reviewer who pushed the last change cannot supply this approval.

## Scope

A request body and an owner procedure in the contributor guide. The request body is inert until submitted by the owner. The guide explains the account prerequisite, application, readback and first operational checks.

## Acceptance criteria

1. The proposed body targets only `dev`, asks for one independent approval, and carries the acceptance bypass.
2. The contributor guide identifies who approves and when. The owner has the create request and a readback for both rulesets.
3. After activation the next ordinary pull request shows the GitHub approval requirement. Its acceptance push succeeds on green.

## Landing notes

READ on 2026-11-17: live ruleset 25925120 targets `dev`, requires `ci-status`, `review` and the strict site build, asks for zero approving reviews, and has one bypass of type `DeployKey`, mode `always`. Live activation and its first pull request await the owner and a separately controlled reviewer.
