# 161: Growth is listed on dev and reconciled at the release

- **Status:** drafted 2026-10-30. The owner asked for it on 2026-10-30 ("can you implement all the recommendations").
- **Date:** 2026-10-30
- **Owner:** Clay Gendron
- **Kind:** **a judge change** (`tests/harness/accept_from.py`, the acceptance's history line, the release ledger and `release/version.py`), not structural, parallel-safe with 159 and 160.
- **Depends on:** the owner's instruction. Nothing in flight.
- **Research it stands on:** `../research/2026-10-30-where-the-time-goes-since-0-1-1.md` (§2.4, §4 row 14); specification 138's Decisions 5 and 7; specification 092; `../progress/README.md`; `../changes/README.md`.

## The problem

After a merge into `dev`, the accept job refuses the record when a growth in fuel or bytes, a fall in a suite's pass count, a check moved between tiers or a changed verdict-bearing judge file has no claim in a news file (specification 138, Decision 5). In the 0.1.2 cycle this cost two pull requests whose only content was a claim (#47 and #48), each a run, a review and a merge, and held the acceptance of the merges behind them (EXECUTED, the memo §2.4). The gather already lists every such row under `GROWTH` on the pull request and after the merge, so nothing is hidden; the refusal only moves the writing of the reason to the one moment nobody can wait.

## Decisions

### 1. On `dev`, an unclaimed row is recorded, not refused

`--accept-from` on a push to `dev` accepts a record whose growth, fall, tier move or judge change has no claim. The acceptance writes each such row into the history line under a new key, `unclaimed`, with the row's kind, the check and the values, and `accepted.json` takes the new value as today. Two refusals stay, because they are losses and not growth: a lost pass (red at the gather, never accepted), and an absent check that no claim retires. The local `--accept` keeps its flags; this decision is about the job.

### 2. At the release, every unclaimed row needs its reason

The release pull request's acceptance refuses while any `unclaimed` row written since the last release's acceptance has no claim. The claims come from two places: the news files that were on `dev` at the last `version.py bump` (read from git at the commit before `bump` removed them, so a reason written at the merge still counts), and the release ledger, `context/release-tier-claims.toml`, which widens to carry any claim and is renamed `context/release-claims.toml`; `version.py date` moves its entries under the version as it does today. The release preparation pull request is where a missing reason is written, in the ledger, by the author who knows it; the preparation's plan refusal (specification 138, the ledger's move by `date` alone) admits an added claim block. The refusal names each row and the file that would clear it.

### 3. The gather is unchanged

Every run, pull request or merge, lists growth under `GROWTH` with the reason a news file gives or `unclaimed`, as today. A pull request's review still reads the rows against the diff; the reviewer's Medium for an unclaimed row stays the review's call.

### 4. The documents

`../progress/README.md` says the acceptance records what is unclaimed and the release reconciles it; `../changes/README.md` says a claim may be written at the merge or at the release preparation; `docs/contributing/review-and-landing.md`'s "After a merge" paragraph follows.

## Intent

A merge is accepted when its tests are green; the reason for a number that moved is written once, by the person who knows it, at the merge or at the release, and no release ships with an unexplained growth.

## Design

Files: `tests/harness/accept_from.py` and `tests/harness/history.py` (the `unclaimed` key; the schema number of the history line moves and the intact check reads both), `tests/unit/test_accept_from.py` and `tests/unit/test_history.py` (the rows: an unclaimed growth accepted on `dev` and written to the line; a lost pass and an unretired absent check still refused; the release acceptance refused by an unclaimed row, cleared by a ledger claim, cleared by a news-file claim read from git), `release/version.py` and `tests/unit/test_release_version.py` (the ledger's name and shape), `release/ci_plan.py` (the preparation's refusal admits an added claim), `tests/checks/test_rules.py` (the ledger's rule), the three documents, `context/changes/161-growth-is-listed-on-dev-and-reconciled-at-the-release.md`.

## Scope

In: the four decisions. Out: the gather's rows; the local `--accept`'s flags; the ratchet on lost passes.

## Acceptance criteria

1. An unclaimed growth, fall, tier move and judge change on a push to `dev` are accepted and written under `unclaimed` in the history line. Unit rows, seen failing first.
2. A lost pass and an unretired absent check are still refused on `dev`. Unit rows.
3. A release pull request's acceptance is refused by an unclaimed row since the last release and names it; a ledger claim clears it; a news-file claim read from git clears it. Unit rows.
4. The history's intact check reads lines of both schemas; the accepted history replays. The existing check.
5. The ledger is `context/release-claims.toml`, `version.py date` moves its entries, and the rules check holds its shape. Unit rows.
6. The three documents say what Decision 4 says. READ.
7. The fast tier, `tests/lint` and the pull request's `ci-status` are green; the news file names the judge files under `judge`.

## Landing notes

To be written at the landing.
