# 161: Growth is listed on dev and reconciled at the release

- **Status:** built 2026-10-30 on `spec/161-growth-is-listed-on-dev-and-reconciled-at-the-release`, not landed. Drafted 2026-10-30; the owner asked for it on 2026-10-30 ("can you implement all the recommendations").
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

- **Built (3026f557).** Decision 1: `accept_from.claimed` sets a row no claim names aside as missing; on a push to `dev` `unclaimed_row` writes it into a format-3 history line (`schema: 3`, `event`, `unclaimed` with kind, check or file, metric, old, new) and its reason field takes `unclaimed: its reason is due by the release`. The local `--accept` writes format 2 still, so the intact check reads both interleaved. Decision 2: `since_release`, `reconciled`, `removed_news` (bump's and date's deletions since the last release, read at each removing commit's parent with `news.claims_only`) and `release_claims` (ledger, removed news, the folder). Ledger renamed to `context/release-claims.toml`; `ledger_move_refusal` admits a block added before or after date's move and refuses a base block dropped or edited; new rules check `test_the_release_ledger_holds_claim_blocks_in_their_shape`.
- **Seen failing first:** 33 rows failed before the code (the worktree's `build/first-fail.log`, not committed): every new row in `test_accept_from.py`, `test_history.py`, `test_ci_plan.py`, `test_news.py`, the rename rows in `test_release_version.py`, `test_scoreboard.py` and `test_ci_plan.py`, and both touched rules checks. Two passed before, by design: `test_on_dev_a_lost_pass_and_an_unretired_absent_check_are_still_refused` (criterion 2 is behaviour kept) and `test_date_moves_a_claim_of_any_kind_under_the_version` (`date` already moved any block). Rows 10 to 13 now show their refusal on the release record.
- **Decisions made in the build.** (a) The gather and the shards' ratchets are unchanged (Decision 3), so a row no news file in the folder claims is still red after a merge; what reaches the acceptance unclaimed is a verdict-bearing judge file, or a row a folder news file claims but none changed since the last acceptance claims (150's #48). (b) A `retired` entry naming no absent check (149's #47) still refuses: it is not one of Decision 1's four kinds. (c) The release line before format 3 is found by `source: ci` and `tier: release` (history line 115). (d) The release pull request's own rows take the same widened claims. (e) Only live documents are renamed; reviews, memos, landed specifications, `CHANGELOG.md`, `accepted.json` and the history keep the old name as written. (f) The news file's heading is `For contributors`: `Changed` is not one of the six.
- **Runs:** fast tier 3446 passed, 0 fail, exit 1 only on "654 accepted pass(es) blocked" (no artifact set in the worktree); `tests/unit tests/lint tests/checks/test_rules.py` 3398 passed, red only on one pass blocked by the artifact dir; the four named unit files 384 passed; `tests/lint` 12 passed; ruff clean. `scoreboard.accept` (150 lines) and `history.errors` (89) were over 80 before and grew by 4 and 1.
