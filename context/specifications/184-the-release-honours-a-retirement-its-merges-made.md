# 184: The release honours a retirement its merges made

- **Status:** built 2026-11-04 on `claude/trusting-gates-s02mks`, from `dev` at `0b6ce99c`, not landed. Asked for on 2026-11-02 by the owner, with the AskUserQuestion tool ("Fix it, then prepare the tag"), after the 0.1.3 release pull request's acceptance refused its own green run (`../decisions.md`, "0.1.3 goes to PyPI").
- **Date:** 2026-11-04
- **Owner:** Clay Gendron
- **Kind:** a judge change (`tests/harness/accept_from.py`). Not structural: nothing under `src/` changes. No pre-build review: it touches neither the guest's imports or exports, the artifact set nor the build recipe (constitution §5.6).
- **Depends on:** landed: 138 (the release pull request's acceptance), 161 (rows accepted unclaimed on `dev`, reconciled at the release), 181, 183. Blocks: the 0.1.3 release pull request, #96.
- **Research it stands on:** the release pull request's run 41372782687 on `0b6ce99c`, its job `accept the merge's record` (125064441448), and the history volume `../progress/history-00060.jsonl`.

Labels: EXECUTED, run and seen; READ, read from a file or a log, cited; INFERRED, reasoned.

## The problem

Run 41372782687 of the 0.1.3 release pull request was green on every shard, every rebuild and the gather (READ). Its acceptance refused the record with fifteen lines of one shape, from the news files of 155, 159, 160, 170 and 175 (READ, job 125064441448):

```
RED: --accept-from refused: 175: retired names tests/checks/test_v1_3_the_zips_directory.py::test_a_plain_start_grows_at_most_30k_fuel_per_member, which is not absent
```

Each of those checks was retired at its own merge. History lines 118, 119, 123 and 128, all after line 115, the 0.1.2 release's acceptance, list them under `retired` (READ). The release pull request's acceptance reads every claim of the release again: the release ledger, the news files `bump` removed since the last release (read back from git), and the folder's (138, 161). It then applies the merge's rule to them: a `retired` entry must name a check absent from this run. A check retired at its merge is no longer in the accepted state, so it can never be absent again, and every retirement since the last release refuses the release (INFERRED, from `claimed` in `tests/harness/accept_from.py`). The fault is in the judge, not a lost pass: nothing the run judged changed.

The rule came with the release's second reading of the news files (161). 0.1.2's release read no news file that retired a check, so no release met it until 0.1.3 (INFERRED).

## Decisions

### 1. A retirement a merge made since the last release is honoured

On the release pull request, a `retired` entry names a check when the check is absent from the run, as before, or when a history line since the last release's acceptance lists it under `retired`. The second is what a merge's acceptance writes when it consumes the claim, so the claim is the one already honoured, read again.

### 2. Only since the last release, and only on the release pull request

The lines read are those after the last release's acceptance, the same span `since_release` reads for rows accepted unclaimed. A retirement the last release already read is not this release's, and an entry naming it still refuses. On a push to `dev` the rule is unchanged: the merge's own claim must name a check absent now.

### 3. Nothing else moves

A lost pass, an absent check no claim retires, and a `retired` entry that names a check neither absent nor retired since the last release all still refuse, named. No claim, history line or accepted row is edited to turn the run green.

## Intent

The release pull request accepts the retirements its merges were accepted on, and nothing it would have refused before for any other reason.

## Design

Files: `tests/harness/accept_from.py` (`retired_since_release`, a `retired_before` argument to `claimed`, read by `accept` on the release pull request alone, and the module's docstring), `tests/unit/test_accept_from.py` (three rows), `context/progress/README.md` (rule 8), `context/changes/README.md` (the accept job's paragraph), `context/changes/184-the-release-honours-a-retirement-its-merges-made.md`.

The same pull request carries the owner's decision that 0.1.3 goes to PyPI: the 0.1.3 summary's last sentence in `CHANGELOG.md` and the decision in `../decisions.md`. The summary's hand edit belongs to the release's preparation; it rides here because the preparation already merged and the owner asked for one pull request.

## Scope

In: the release pull request's reading of `retired` entries. Out: a news file edited after its merge and read again on `dev` by a later merge's acceptance, which would meet the same refusal; no such case is known, and the release ledger's reserved fix for reconciling rows by their base (`../roadmap.md`) is the place for it.

## Acceptance criteria

1. `test_the_release_accepts_a_retirement_a_merge_since_the_last_release_made` fails before the change and passes after; it also holds that a file-wide entry is honoured and that an entry naming a check still accepted refuses. EXECUTED.
2. `test_a_retirement_before_the_last_release_is_not_honoured_again` and `test_a_merge_still_refuses_a_retirement_of_a_check_that_is_not_absent` pass before and after: the change widens nothing else. EXECUTED.
3. Read against this repository's history and the release's claims at `0b6ce99c`, every `retired` entry the release reads is honoured (fifteen of fifteen) and none is left. EXECUTED.
4. The fast tier, `tests/lint` and the pull request's `ci-status` are green; the news file is present.
5. The 0.1.3 release pull request's next run accepts its record (READ from that run, named in the landing notes then).

## Landing notes

Built 2026-11-04, before its pull request and review.

- **Seen failing first.** With the three rows written and the module unchanged, the first row failed on the refusal the release met ("retired names tests/checks/test_rules.py::test_a_rule, which is not absent"); the other two passed, as they must (EXECUTED).
- **The real history.** A script in the session's scratchpad called `release_claims` and `retired_since_release` on the repository at `0b6ce99c`, with the history unshallowed: 38 claims, 12 checks retired since line 115, and every `retired` entry among the claims named by one of them (EXECUTED).
- **The fast tier here.** In this session's container, which runs as root with no artifact set, four runner checks fail (`test_the_removal_never_deletes_what_the_guest_may_not[home]` and `[private]`, `test_a_class_tools_construction_keywords_are_fixed[a partial __init__]`, `test_the_walk_judges_links`); the same four fail on a clean checkout of `dev` at `0b6ce99c` (EXECUTED), and CI passed them on run 41372782687. None reads `tests/harness/accept_from.py`. `tests/lint` and ruff are green (EXECUTED).
