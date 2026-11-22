# 200: Authenticate independent approval on dev

- **Status:** proposed; activation deferred while the agents share one GitHub identity.
- **Date:** 2026-11-17
- **Owner:** Clay Gendron
- **Kind:** owner-applied repository ruleset proposal.
- **Depends on:** 138 (pull requests and the acceptance identity), 160 (the three required checks).
- **Research it stands on:** the live repository rulesets and GitHub's [ruleset semantics](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets) and [review rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).

## Decisions

Defer activation. The builder and fresh reviewer use one GitHub account today. GitHub prevents that account from approving its own pull request. Requiring another approval now would block ordinary merges. The owner can revisit this proposal when a reviewer has a separately controlled GitHub account with write access.

## Intent

The current review file records a fresh reviewer's reasoning. A future GitHub approval can authenticate an independent reviewer in addition to that record.

## Design

The proposed branch ruleset applies to every pull request into `dev`, including documentation changes. It adds one required approval, dismissal of stale approvals, and approval by someone other than the most recent pusher. The author can push the review file and the reviewer can approve the final diff separately. The existing ruleset supplies the three checks. Both rulesets grant the acceptance deploy key its direct push.

## Scope

This proposal and its [request body](200-authenticate-independent-review.json) are owner records. Branch administration and the instructions governing merges are separate activation steps.

## Acceptance criteria

1. The body targets only `refs/heads/dev` and requests one independent approval, stale dismissal and last-push approval.
2. The owner can verify the checks and the acceptance bypass before and after activation.
3. After a future activation, the next ordinary pull request requires approval and its green post-merge run pushes its acceptance commit.

## Landing notes

READ on 2026-11-17: active ruleset 25925120 requires `ci-status`, `review` and the strict site build on `dev`, requires zero approvals, and bypasses `DeployKey` in `always` mode.

Before activation the owner must arrange an independently controlled reviewer account with write access and update the “Merge on green” instruction in `AGENTS.md` and the corresponding contributor guide. The builder may then merge only after the checks are green, the review verdict begins “Lands”, and GitHub shows a fresh independent approval covering the last reviewable push.

For a future rollout, the owner reads the existing policy and lists the rulesets with `gh api repos/ClayGendron/wasi-python/rulesets/25925120` and `gh api --paginate repos/ClayGendron/wasi-python/rulesets --jq '.[] | [.id, .name, .enforcement] | @tsv'`. Confirm the target, checks and sole deploy-key bypass against the record above. In **Settings → Deploy keys**, verify the acceptance workflow holds the only write-enabled key; GitHub grants that bypass to deploy keys as a class. Reconcile a changed acceptance identity with the body first.

If the list has no ruleset named **dev requires an independent approval**, the owner creates it once from the checkout and records the printed ID:

```sh
gh api -X POST repos/ClayGendron/wasi-python/rulesets --input context/specifications/200-authenticate-independent-review.json --jq .id
```

Read both rulesets back using `gh api repos/ClayGendron/wasi-python/rulesets/25925120` and `gh api repos/ClayGendron/wasi-python/rulesets/NEW_ID` with the created or listed ID. Verify the original checks and bypass, then compare the new rule's active state, target, eligibility for bypass and approval requirements with the request body. On the next ordinary pull request, verify GitHub waits for the independent approval and the post-merge acceptance push succeeds.
