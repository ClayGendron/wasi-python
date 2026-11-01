# 177: Each pull request claims in a file of its own

- **Status:** built 2026-10-31 on `spec/177-each-pull-request-claims-in-a-file-of-its-own`, not landed. The owner chose it on 2026-10-31 through the orchestrating session's question ("Split it now").
- **Date:** 2026-10-31
- **Owner:** Clay Gendron
- **Kind:** **a judge change** (the release ledger, a verdict-bearing judge file, its readers in `tests/harness/` and `release/`, and `ci-status`'s refusals). Not structural: nothing under `src/` changes. No wasm build.
- **Depends on:** 161 (the release ledger and its reconciliation), 138 (the preparation's plan refusal). Nothing in flight; pull requests #71, #80 and #81 and the branches of 172, 173–174 and 175–176 meet it (*For the pull requests open when it lands*).
- **Research it stands on:** `../changes/README.md`; `../progress/README.md`, "The release tier"; specification 161, Decision 2. Prior art in the shape, not the code: towncrier's, CPython's blurb and changesets' one fragment file per change, which this repository's news files already follow.

Labels: EXECUTED, run and seen; READ, read from a file, cited; INFERRED, reasoned.

## The problem

The release ledger, `context/release-claims.toml`, was one append-only file (READ). Every pull request that moved a release-tier row appended a `[[claim]]` block at its end, so each merge made every other open pull request that had appended one conflict. A conflicting pull request gets no run, so they merged strictly one at a time, each with a rebase and about an hour's run (INFERRED from 0.1.3's queue: 165, 166, 159, 167 and 171 each appended). `dev`'s ruleset does not require a branch to be up to date (`strict=false`), so this file was the one thing forcing the line. The news files, `context/changes/NNN-<slug>.md`, already work one file per pull request.

## Decisions

### 1. The ledger is a folder of one file per pull request

`context/release-claims/NNN-<slug>.toml`, named after the pull request's news file, holds that pull request's `[[claim]]` blocks in the same shape as before, each with `spec = "NNN"`. A later pull request of the same specification adds its blocks to that file, beside its news file. The release's preparation writes the reason for a row an acceptance on `dev` recorded as unclaimed into the file of the change the row belongs to. `context/release-claims/README.md` says the rule; it also keeps the folder in git once `date` has moved every file.

### 2. The six blocks move whole, and the single file goes

Each block of the single file at `bedf8f30` moves, byte for byte, into the file of the specification it names: 159, 165, 166 (two blocks, its first and its second pull request's, #71, in that order), 167 and 171, each file named after that specification's news file. The single file is deleted, not kept. Nothing needs it: every reader reads the folder, and its header comment now lives in the folder's README. Kept, it would be the one place a pull request could still append, which is the conflict this removes.

### 3. Every reader takes the folder in file-name order

`tests/harness/news.py` (`ledger_files`, `ledger_file_claims`, `ledger_claims`, `move_ledger`, `moved_files`), `tests/harness/accept_from.py` (the reconciliation's refusal names the folder), `tests/harness/paths.py` (the judge's paths and the verdict-bearing list: `context/release-claims/**`), `tests/harness/sameness.py` (`--claims` takes a folder), `release/version.py` (`date` moves each file under `## <version>`, under its name, and removes it) and `release/ci_plan.py` (the classification, the preparation, the preparation's plan refusal). The order is the files' names, as the news files' is. The same blocks give the same claims: in file-name order the list is equal entry for entry to the single file's in that order; against the order the blocks were appended, the claims are the same set, and every row is claimed or unclaimed alike under every kind, so what the acceptance and the release's reconciliation decide does not move. One thing can: a row two blocks name is quoted with the reason of the block that comes first, and the first is now the lower file name, not the earlier merge. Over the six real blocks, read as at 0.1.3 (without 0.1.2's section), 10 of 67 probes are quoted with another block's reason, the verdict the same: nine release-tier groups 166 names and 165's `test_v1_3_upstream_suites.py::*` names too (for example `numpy-slow-*`: 165's reason now, 166's before), and `sympy-*` (159's now, 165's before) (EXECUTED, `build/equivalence.log`). Read today, with 0.1.2's section first, none differs, since 157's block names every upstream suite.

### 4. `ci-status` holds each pull request to its own file

`ci_plan.ledger_refusals` reads the ledger at the merge base and the head (the single file among it where a commit has it) when the pull request changes a ledger path, and refuses, named: a `[[claim]]` block the head holds that the base did not, in a file not named after one of the pull request's news files (an added block or an edited one); a block dropped from another change's file; and the single file back. A block moved whole between files is neither added nor dropped, so this pull request, which moves the six, is not refused by its own check. The release's preparation is not held to it: its own check is that its change is `date`'s move with any added block, which reads the folder now (`ledger_move_refusal`: every base file moved whole under the version, none left in the folder too, an added block in a claim's shape). The rules check `tests/checks/test_rules.py::test_the_release_ledger_is_a_file_per_pull_request` holds the single file's absence, the README's presence and every file's name; `::test_the_release_ledger_holds_claim_blocks_in_their_shape` holds each file's blocks and the history's.

### 5. The history keeps each file under its name

`date` writes, under `## <version>`, each file's name in backticks and its blocks in a `toml` fence, in file-name order. The release reads every fence of the version's section, as before, so 0.1.2's single fence and those before it are read unchanged.

## For the pull requests open when it lands

A pull request or branch that appended a block to `context/release-claims.toml` (#71, #80, #81, and 172, 173–174, 175–176 while they are built) meets a modify/delete conflict on that file when it rebases onto `dev`. Resolve it by deleting the file (`git rm context/release-claims.toml`) and writing your block, unchanged, into `context/release-claims/NNN-<slug>.toml`, named after your news file, with `spec = "NNN"`; a branch with two news files writes one file for each specification whose block it carries. Your news file's `[claim.judge]` then names `"context/release-claims/NNN-<slug>.toml"` (or `"context/release-claims/*"`) instead of `"context/release-claims.toml"`. Nothing else moves: the block's shape is the same. `ci-status` refuses a block written into any other file, and the rules check refuses the single file if a rebase brings it back.

## Intent

Two pull requests that each write a reason for the release write two files, so neither conflicts with the other's merge, and the release reads the same claims as before.

## Design

Files: `tests/harness/news.py`, `tests/harness/accept_from.py`, `tests/harness/paths.py`, `tests/harness/sameness.py`, `release/version.py`, `release/ci_plan.py`; `tests/checks/test_rules.py`; `tests/unit/test_news.py`, `test_ci_plan.py`, `test_release_version.py`, `test_accept_from.py`, `test_scoreboard.py`, `test_sameness.py`; `context/release-claims/` (the five files and the README), `context/release-claims.toml` removed; `context/release-claims-history.md`, `context/changes/README.md`, `context/progress/README.md`, `docs/contributing/release-process.md`, `AGENTS.md`; the news file `../changes/177-each-pull-request-claims-in-a-file-of-its-own.md`.

## Scope

In: the five decisions. Out: which reason a row two claims name is quoted with (Decision 3; the news files have the same first-match rule); the ruleset; the news files.

## Acceptance criteria

1. The folder holds the six blocks, each in its change's file, byte for byte; the single file is gone. EXECUTED: `ledger_refusals` of the single file at `bedf8f30` against the folder is empty, and the blocks are equal as a multiset.
2. Every reader reads the folder in file-name order; `date` moves each file and removes it; the preparation's plan reads the folder. Unit rows.
3. The folder gives the release the claims the single file gave. A unit row over the same blocks in both forms (`test_news.py::test_the_folder_gives_the_release_the_claims_the_single_file_gave`).
4. `ci-status` refuses a block added to, or edited in, another change's file, a block dropped from one, and the single file back, and admits the move of the six. Unit rows, seen failing first.
5. The rules check refuses the single file and a misnamed file. Seen failing first on `dev`'s tree.
6. The documents say Decisions 1 to 5. READ.
7. `tests/lint`, the fast tier and the pull request's `ci-status` are green; the news file names the ledger under `[claim.judge]`.

## Landing notes

- **Seen failing first** (EXECUTED): with the new tests over `dev`'s code at `2ec3c1ee`, 28 rows failed, every one a ledger row: the new and changed rows of `test_news.py`, `test_ci_plan.py`, `test_release_version.py`, `test_accept_from.py`, `test_scoreboard.py` and `test_sameness.py`, the new rules check `test_the_release_ledger_is_a_file_per_pull_request` (the single file was there) and the two touched rules checks (`build/first-fail.log` in the worktree, not committed). `test_the_preparation_is_not_held_to_its_own_ledger_file` passed before, by design: it is behaviour kept.
- **Local runs** (EXECUTED): `tests/lint` 14 passed; `tests/unit`, `tests/checks/test_rules.py` and `tests/lint` together 3,655 passed, 93 skipped. The fast tier against the main tree's set ran 4,386 passed, 72 failed and 6 errors, every one a product check that the set (built 2026-10-21, CPython 3.15.0, without `turn_input` or 0.1.3's packages) is too old for, plus `test_runner_sessions.py::test_a_turns_stdin_answers_input` for the same reason; this change touches no product code, and the pull request's own run judges on the cached set.
- **Rebased onto `bedf8f30`** (#71, 166's second pull request, which appended a sixth block): its block moves after 166's first in `166-the-pins-move-for-0-1-3.toml`.
- **Equivalence over the real blocks** (EXECUTED, `build/equivalence.log`): `ci_plan.ledger_refusals` of the single file at `bedf8f30` against the five files is empty, and the six blocks are equal as a multiset. Read as today (0.1.2's section first), the claims and the quoted reasons are the same in all 69 probes. Read as at 0.1.3, the claims and verdicts are the same in all 67, and 10 are quoted with another block's reason (Decision 3).
