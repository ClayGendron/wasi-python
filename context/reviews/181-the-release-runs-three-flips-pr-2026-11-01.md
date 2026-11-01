# Review of 181 — the release runs three flips

- **Date:** 2026-11-01
- **Reviewer:** an agent (Claude), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** `84c39c62..21622c80`, the description and the diagnosis of run 41346031022; as the change's readers, `release/version.py`, `release/ci_plan.py` and `tests/harness/{accept_from,gather,plugin,scoreboard,news}.py`.
- **Run:** 41354593539 on `21622c80`. Every judge shard is green, the 18 normal-tier upstream groups on Linux and the own shards among them; only `review` and `ci-status` are red, and the plan's sole refusal is this missing file (the orchestrator's reading; this reviewer made no `gh` call on it). The run has no release tier and no macOS leg: jinja2-r's and fonttools-r-rest's restored classes are first judged by #96's re-run, and the `[False]` row's fact by `dev`'s macOS post-merge run.
- **Windows legs:** all 11 windows-2025 legs of run 41354593539 green (the orchestrator's reading, as above).
- **Re-ran:** the judge's `upstream.class_findings` and `scan.digest` over the lists at `84c39c62` and the head → the old gaps (`13 af97922d3b81`, `106 c7177c5b2367`, `3 5f05fa61a255`), the run's three red digests (`17 a9e51a8343b8`, `110 500e70e2e2ed`, `3 a5888c38d28b`) and the new gaps (`13 ba56b641f579`, `104 959d6ba605ec`, `2 0c61ab6175e3`); `git diff bedf8f30^ HEAD` on the jinja2-r lists → empty; three `--log-failed` reads (jobs 124972147192, 124972147292, 124972146466); `version.py`'s `date` steps on this tree, and `check --tag v0.1.3` → `ok 0.1.3`; the records rows twice on a stale local set; `tests/lint` → 14 passed; `tests/checks/test_rules.py` → 146 passed, 2 skipped, 0 fail (two rows blocked in a worktree); the accept, news and version unit files → 167 passed; ruff clean.
- **Box:** 25 minutes; about 40 used, for item 5.

## Acceptance criteria against evidence

1. `[False]` records its fuel as a fact, `[True]` as a metric — met in the code, the records assertions unchanged (READ); the record is first read on `dev`'s macOS post-merge run, since this run has no macOS leg.
2. The lists reproduce the run's findings and give the new gaps — met (EXECUTED). A finding set holds every member and every `+`/`-`, so a matching digest fixes the membership. Nothing else moved: shard 039 failed only the two jinja2-r classes, 041 only `counted-clock`, both `lost 0 · grew 0`; macOS `grew 1`, the `[False]` row alone (READ).
3. jinja2-r 552 and fonttools-r-rest 2,635 — not read by this pull request's run, which judges the normal tier; both are release tier, so #96's next run reads it. jinja2-r's two leavers pass and two joiners fail, at the run's 552 (READ, the diagnosis).
4. The claims — met (READ). `changed` names the four checks, `passes` fonttools-r-rest (a rise, so no `fewer`), `grows` the `[False]` row (the ratchet lists a dropped metric as "no longer recorded", a growth), and `[claim.judge]` each verdict-bearing file, the ledger file among them. The ledger file holds the release-tier block.
5. Lint, rules and fast tier — lint and rules green (EXECUTED); run 41354593539's judge shards green, `ci-status` red only for this file (READ, through the orchestrator).

The hash-seed cause is sound. `src/` sets no hash seed, so the plain reactor draws CPython's secret through the host's `random_get`; the snapshot's was fixed when it was taken. The 0.01% tolerance is about 27 K here; the steps seen were 109 K to 271 K. On a stale local set, `[True]` gave 166,860,516 twice and `[False]` 723,636,201 then 724,019,392 (EXECUTED; the program failed on that set, but the counts show the noise). The row above already reports a plain fuel with `fact`.

**Item 5, the sequence.** No reader refuses a release while 181's news file stands. `check --tag v0.1.3` reads the version, `pyproject.toml` and the CHANGELOG, and passes on this tree (EXECUTED); `ci_plan` refuses a release pull request only an accepted-state commit not in an acceptance's shape (READ). `date` cannot run again: `add_section` says "already has a section for 0.1.3, dated 2026-11-01", `date_section` "no unreleased section", `move_ledger` "already has a section for 0.1.3" (EXECUTED); undating by hand edits the section outside the preparation. And `date` here would defeat the fix: the news file would leave in this commit, so this pull request's macOS leg, and #96's run on the merge commit before `dev`'s acceptance, would find no `grows` claim. Ranked: (1) merge as is; `dev`'s acceptance takes the claims and drops the `[False]` row's macOS fuel; #96 runs again; its shards read the news file in the folder, its acceptance the folder, the ledger file and the files `bump` removed. (2) `date` again: refused, and harmful. (3) After the tag, nothing: 181's line joins 0.1.4's notes, and its ledger file moves under `## 0.1.4`.

## Findings, most severe first

1. **181's claims outlive 0.1.3 into 0.1.4's reconciliation** (`context/changes/181-the-release-runs-three-flips.md`, `[claim.judge]` "tests/known_gaps.toml") — Low. Failure: a 0.1.4 merge changes `tests/known_gaps.toml` with no claim; `dev` records it unclaimed; 0.1.4's release acceptance reads 181 again (removed by 0.1.4's `bump`, and its ledger file under `## 0.1.4`) and clears that row with 181's reason, which is not its reason. The diagnosis saw the same in earlier broad claims. Nothing changes for 0.1.3. Fix text, for the post-0.1.3 list in `context/roadmap.md`: "The release reconciles a row written unclaimed only with a claim merged after that row's base; a news file merged after `date` (181) is read for its own release alone."
2. **The release page says a late fix reaches the notes, and after `date` it does not** (`docs/contributing/release-process.md:17`) — Low. Failure: 181's "For contributors" line, merged after 0.1.3's `date`, is in 0.1.4's notes while its change ships in 0.1.3. The description says so; the page does not. Fix text, appended to line 17: "A fix merged after `date` keeps its news file until the next `bump`; its line reaches the next release's notes."
3. **A self-check box is unticked** (the description, "The Windows legs … were read") — Low, answered in writing: the run starts with the pull request, and the orchestrator reads it.

## Constitution checks

- §4: no patch, input or `src/` change; a judge change, each verdict-bearing file claimed with the owner's approval and the run's id. The check's docstring names no specification or `context/` path.
- §7: no pass lost: jinja2-r stays 552, fonttools-r-rest gains one. `[True]` keeps its ratchet; `[False]` keeps its assertions and loses only a ratchet on noise. No other plain-reactor row moved; their sweep is out of scope.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1 — carried as a roadmap line, in the post-0.1.3 list of `context/roadmap.md`.
2. Finding 2 — answered: fixed in a docs pull request after 0.1.3's tag; its roadmap line carries the sentence.
3. Finding 3 — fixed: the orchestrator ticked the Windows box after reading run 41354593539.

## Verdict

Lands on `21622c80`: the three re-recordings are exactly run 41346031022's membership, lose no pass and are claimed where every reader looks, and run 41354593539's judge shards are green.
