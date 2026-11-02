# Review of 164 — Output while the guest runs: the growth its bootstrap brings, claimed after the merge

- **Date:** 2026-10-31
- **Reviewer:** an agent (Claude Opus 5.5), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** `be87f12a`..`04969f91` (one commit, pull request #68, branch `changes/164-the-growth-its-bootstrap-brings`): 106 lines added to `context/changes/164-output-while-the-guest-runs.md`, none removed
- **Run:** not read by this reviewer, by the orchestrator's brief (no `gh` calls); the pull request's `ci-status` is the orchestrator's to read before the merge.
- **Re-ran:** `uv run pytest tests/lint -q` → 14 passed, exit 0; `uv run pytest -q -n 2 tests/unit/test_news.py tests/unit/test_accept_from.py` → 120 passed, exit 0; `uv run pytest -q tests/checks/test_rules.py::test_the_news_files_have_their_shape` → 1 passed, exit 0; two scratch scripts, below. Box: 25 minutes, a claim on a news file.

## Acceptance criteria against evidence

1. The 103 names are exactly the history line's `unclaimed` checks — met, EXECUTED: the last line of `context/progress/history-00060.jsonl` (the acceptance `be87f12a` of `b6ff1675`) has 103 `unclaimed` rows, 103 distinct checks; the claim's `grows` parsed with `tomllib` has 103 distinct entries; the two sets are equal and in the same order, nothing on either side alone.
2. Every row is kind `grows` — met, EXECUTED: 103 `grows`, 101 on `fuel` and 2 on `bytes`; every `new` exceeds its `old`. The line's `growth_reason` is "unclaimed: its reason is due by the release".
3. The growth is 164's — met, READ and EXECUTED. The previous acceptance is `d4b7d928` (of 160, `b6c4c899`); the range since holds 161 (`8983e64a`) and its fix (`041c078b`), the 0.1.3 specifications (`0070b04e`), 159 (`a1acec5c`), 168 (`ae695e15`), the Pillow memo (`6697225e`), 164 (`10a722a1`), 155 (`3bfd4c5f`) and the orjson memo (`b6ff1675`). Only 164 touches `recipes/` (`reactor_bootstrap.py`, `reactor_main.c`); 161, 159 and 155 change the harness, workflow and `release/`, 168 the host's platform modules, the others `context/` and `docs/` alone. The history lines' `artifact` and `set_sums` change between the two acceptances and `wasmtime` (50.0.1) and the platform do not. The two byte rows end at 99,433,677 and 104,550,499, the sizes 164's pull request recorded from its own build.
4. The reason is true — met in substance, READ: Decision 13 of spec 164 says both binaries grow and calls may grow "since the plain binary unmarshals the bootstrap at every start and the snapshot's heap shifts with it". The wording has three slips, finding 1.
5. The claim parses — met, EXECUTED: `news.load` takes the file (one claim, keys `spec`, `new`, `units`, `grows`, `growth`, `judge`); `grows` comes with its `growth`, as `news.py` requires; the shape rule passes.
6. The release's reconciliation finds it — met, READ and EXECUTED. `accept_from.reconciled` asks `news.reason(claims, kind, check)` of each row `since_release` collects after the last release line; `release_claims` gives the ledger's claims and each news file `bump` removed, read by `removed_news` at the parent of the removing commit, so a claim added on `dev` after the merge and before `bump` is the one read. A scratch script over the whole history: 103 rows since the 0.1.2 release line (`193c9996`); with the ledger and this head's 164 claim, 0 refusals; with the ledger and 164's file as `be87f12a` has it, 102 (the 103rd, `test_upstream_suite[cpython-fs]`, is matched today by 157's prefix claim in the 0.1.2 history block, which leaves the ledger once the version moves to 0.1.3; this claim names that row too). The unit rows `test_the_release_reads_the_news_files_bump_removed_from_git` and `test_a_news_file_claim_read_from_git_clears_a_row_accepted_unclaimed` pass in the 120.
7. Nothing else in the claim changed — met, EXECUTED: the diff is 106 inserted lines between `units = 30` and `[claim.judge]`; `spec`, `new`, `units` and both `judge` entries are as on `be87f12a`.
8. The commit's trailer — met, READ: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Findings, most severe first

1. **The reason's wording is loose in three places** (`context/changes/164-output-while-the-guest-runs.md:127`) — Low. The output feed is host-side (`_outputs.py`); the bootstrap carries the turn's stdin alone, and `reactor_main.c` the export `turn_input`. The fuel range is 0.010 to 13.2 percent; 0.002 percent is the plain binary's bytes. "Every start loads it" holds for the plain binary; the snapshot's rows move because its heap shifts (Decision 13), and the 13 percent row, `test_a_trapped_prepare_leaves_nothing_callable` (454 to 514), is the reactor's `prepare` now freeing a held stdin, not the bootstrap. The rows and their reconciliation are right; only the sentence a release reader sees is off. Fix text, for the `growth` line: `growth = "the reactor gains the export turn_input and its bootstrap's turn takes the turn's stdin: the plain binary unmarshals the larger bootstrap at every start and the snapshot's heap shifts with it, so every call's fuel moves a little (0.01 to 0.4 percent, and 13 percent on the 454-instruction trapped prepare, which now frees a held stdin), and the binaries grow by 1,963 and 4,191 bytes; the acceptance after the merge recorded them, at be87f12a"`. It touches only `context/` and needs no second signing.

## Constitution checks

- §4 constraints: no source, pin, patch, artifact or judge file is touched; the judge is not weakened, since a claim gives a reason and clears no lost pass (`claimed` still refuses a loss, an unrun pass and an absent check no `retired` names). Writing a missed reason into the news file while it is on `dev` is the path `context/changes/README.md` ("When to write a claim") names.
- §7 never-do list: nothing tripped. One note: the merge's acceptance will read 164's file again as changed since the last acceptance, so a growth that run sees on one of these 103 checks would take 164's reason; nothing in this pull request's paths moves fuel, so none is expected.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1 — fixed in the review's commit, a Low touching only `context/`: the reason now says the reactor carries a turn's stdin (bootstrap, `turn_input`, `prepare` freeing a held one), the fuel range 0.01 to 13 percent with its largest row named, and the bytes 0.002 and 0.004 percent.

## Verdict

Lands on 04969f91: the 103 claimed rows are exactly the growth `be87f12a` recorded unclaimed, all from 164's recipe change, and the release's reconciliation clears them; finding 1 is a Low on the reason's wording.
