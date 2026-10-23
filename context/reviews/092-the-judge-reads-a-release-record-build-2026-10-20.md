# Review of 092 — the judge reads a release record: sameness against a CI run, and claim lists

- **Date:** 2026-10-20
- **Reviewer:** a fresh Claude agent (Opus 5.5), dispatched by the lane; not the author
- **Reviewed:** `spec/092-the-judge-reads-a-release-record`, `e8ba20a..6bdf84d` (code at `1a23fe0`; `6bdf84d` changes only the specification's landing notes)
- **Time box:** 35 minutes (the lane's brief; parallel-safe, judge only)
- **Run:** none of my own. The lane's brief asked me to read the builder's runs instead: 39354482605 (`2787003`, green on every job), 39357023086 (`a8a3830`, red only on `judge (windows-2025, own-guest)`, `test_an_abandoned_turn_keeps_its_session_busy`, spec 078's row, which 093 fixes) and 39359915030 (`1a23fe0`, red only on `judge (windows-2025, own-embedding)`, the two `test_the_removal_never_deletes_what_the_guest_may_not` rows; main's own dry run 39358820218 on `6006fde` failed on that job too; 094 fixes it). In both red runs the gather was skipped. READ with `gh run view <id> --json jobs` and `--log-failed`.
- **Re-ran:** `uv run pytest -q tests/unit/test_sameness.py tests/unit/test_gather.py tests/unit/test_several_cores.py` on `6bdf84d` (after `build/lane.lock` cleared) → 153 passed, exit 0; `uv run ruff check src tests` and `uv run ruff format --check src tests` → green; `sameness.py` on `build/092/e2e/`: run 39354482605's record then the re-gathered `1a23fe0` record → 18 lines, exit 1, the same two notes as `e2e.txt`; the base then 39354482605 with `claims-092.toml` (now `units = 39`) → "explained by claims: 092 1" and the suite line left, exit 1, as it must be (that record predates the last two rows; `e2e.txt` used `units = 37` then); six mutations (below). No full judge and no fast tier (rule 3a; the lane's lock held most of the box).

## Acceptance criteria against evidence

1. The checks fail first — met (READ: `build/092/first-fail.txt`, 30 failed, 50 passed; the mutations below show that the rows bite on the code they guard).
2. The merged record — met (EXECUTED: the three `test_gather.py` rows pass; the re-gathered record `build/092/e2e/regathered-39359915030.json` has `deselected`, `collected_files`, 19 `runs`, `meta.foreign`, and a `source` on 666 of 669 checks; the merged status stays the worst: four checks there have a merged status worse than their source's, two `blocked` by `descriptor limit` and two `fail`, all on Windows).
3. Sameness against a release record — met as specified (EXECUTED: the rows pass; M4 and M5 below fail them). Finding 1 is about what the specification lets pass silently.
4. Claims — met (EXECUTED: the rows pass; M1 to M3 below fail them).
5. Nothing moves — met for `ruff check` and `ruff format --check` (EXECUTED, green). The fast tier READ from `build/092/fast-rebased.txt` (lost 0, gained 0, grew 0, judge changed); not re-run by me (AGENTS.md rule 3a: the lane's lock was held for most of the box). CI: both red runs are red only on rows 093 and 094 fix (READ), not on a growth line; 39354482605 is green but predates the rebase and Decision 3's last form.
6. End to end — met (EXECUTED: I re-ran `sameness.py` on the files in `build/092/e2e/`; the outputs match `e2e.txt` where the claim list is the same; with today's `units = 39` the older comparison leaves its suite line, which is the exact-sum rule working).

## Findings, most severe first

1. **Medium: a failure on Linux or Windows is silent in sameness, and the README does not say to compare only a green gather's record** (`tests/harness/sameness.py`, `view()`, the release branch; `context/progress/README.md`, "Comparing with a release record"). The view takes each check from its `source` (darwin first) and drops the merged status, and nothing in stdout or stderr names a check whose merged status is worse than its source's. The gather writes `record.json` even when it is red (`gather.main`), and `release.yml` uploads it under `if: always()`; G4 can be red while every shard job is green (a check blocked on one system by a need outside `CI_NEEDS`, or a gap `known_gaps.toml` does not hold, on a row that is not an accepted pass, need not fail its shard's job: INFERRED, from G4 checking exactly these). And the builder's own end-to-end method, merging a red run's shard records by hand, produces such a record. Failure (EXECUTED): `sameness.py regathered-39359915030.json regathered-39359915030.json`, a record whose merged status is `fail` for both `test_the_removal_never_deletes_what_the_guest_may_not` rows (Windows), prints no line naming them and exits 0; so does the same record against a darwin record of the same judge. The spec says "the run's own red line is where a Windows failure shows", which holds only when the lane looks at the run's verdict, and no step says so. Fix (code, the builder's): in the release view, every check whose merged `status` is not its source's, other than one `blocked` by a `CI_NEEDS` need on a system that lacks it (the two `descriptor limit` rows), is a difference (`<check>: status <source's> on <platform>, <worst> elsewhere`), which no claim explains; with a unit row. The README then adds: "Compare only the record of a run whose every job, the gather included, is green." The README line alone is a process guard, not a check; I would accept it alone only with the lane's written agreement. Evidence that closes it: the row failing on `1a23fe0`'s code, passing after; the command above then printing two lines and exiting 1.

2. **Medium: a release record whose checks lack `source` is believed** (`view()`, `unrun`). A check with no `source` is set aside as "not run" whatever its merged status. `gather.merge` gives no source only when every record has the check `deselected` or `blocked` by a `CI_NEEDS` need, so a sourceless check with any other status is a malformed or hand-edited record. Failure (EXECUTED): the record above with every `source` removed and every status set to `fail`: one note, "not run on any system in the release: 669 (descriptor limit 2, fail 664, …)", no difference, exit 0. Fix (code): `view()` raises `NotComparable` (exit 2, one line) when a check without `source` has a status other than `deselected`, or `blocked` with a need outside `CI_NEEDS`; with a unit row.

3. **Low: a malformed suite in a release record is a traceback, not exit 2** (`view()`, the darwin suite sum). A non-number in a darwin run's `suite` raises `TypeError`, which `main` does not catch (EXECUTED: `TypeError: unsupported operand type(s) for +: 'int' and 'str'`). It still exits non-zero, so nothing passes, but the one-line contract is broken. Fix: sum only whole numbers (as `merge` does with `_whole`) or raise `NotComparable`.

4. **Low: `--except` without `--claims` is silently ignored** (`main`). EXECUTED: `--except 092 A A` exits 0 with no word. Fix: `ap.error` when `--except` is given without `--claims`.

5. **Low (a note): `changed` names no direction.** A `changed` claim on a check explains any status move on it, `pass` to `fail` included. The lane's own ratchet catches a lost accepted pass and a failing check keeps its judge red, so nothing lands on it; but a claim cannot say "this gap closes", only "this row moves". A later spec may let `changed` name the status expected. No change asked here.

6. **Low (a note): the self-check list is not at the top of a review request.** The landing notes carry the evidence it asks for; nothing missing that I found.

## The builder's five flags

1. **Linux fuel varies between CI runs, so release fuel is compared only from darwin.** Right. G5 holds only darwin fuel (`accepted.json` keys metrics by platform), so sameness holding Linux fuel would be stricter than the gate it stands beside, and noisy (3.5% on `cpython-b`). It is named on stderr, and `bytes` and `passes` stay compared everywhere. Mutation M4 shows the rows guard it.
2. **Unit suite by totals only across kinds; fuel only within one platform.** Right. The total and the failing count are what G4 holds; the passed/skipped split is a host fact, and it is named. Two records of one kind still compare the suite whole.
3. **A Windows-only failure is never a sameness difference.** This is Finding 1. G4 and the shard jobs see it (READ: G4 reads every record's own status: `fail`, `unrun`, a gap not held, a block by a need outside `CI_NEEDS` or not allowed on that system, each red), so the gate holds; but sameness against that record is silent, and the record exists even when the gather is red.
4. **Claims depend on the order of the records.** Acceptable: the wrong order fails loud, not quiet. `new` and `retired` are directional (M2 shows it is tested), and `units` is a signed difference, so a reversed pair leaves those lines unexplained, exit 1. `changed`, `passes` and `grows` are symmetric, which is harmless.
5. **The rebase squashed four commits and merged 085 and 091.** READ: 085's need repair now covers the merged check and its `source`; the `_whole` filter on the tally is kept; `did_run` is safe on a non-string need; 091's fuel facts follow the fuel rules (`test_a_fuel_fact_follows_the_fuel_rules`). One spot: `did_run` asks only whether the need is a key of `CI_NEEDS`, not whether it blocks on that system; a darwin row blocked by `descriptor limit` would be skipped for the next system's. G4 already makes that red (`allowed`), so it is not a silent pass.

## Can a claim swallow an unclaimed growth?

No (READ and EXECUTED). A `fuel` or `bytes` line is explained only by a `grows` entry that names that check exactly, by its file, or by a `*` prefix; `changed`, `passes`, `new` and `retired` never explain it (M1 makes `changed` explain fuel, and `test_a_claim_explains_its_own_kind_only` fails). `grows` requires `growth`. A file or prefix entry is wide by design and the spec says so; the "claimed, not seen" note shows a stale entry. `meta.foreign` is never explained.

## Is refusing a pre-092 release record right?

Yes. Without `runs`, `deselected`, `collected_files` and `meta.foreign`, the release view would print a spurious line for each and could not know the source of any check; refusing with exit 2 and one line that says what to download is the honest answer. Detection is by `meta.records`, which every gather since spec 063 writes, so a pre-092 release record is never read as a run record (EXECUTED: `test_a_release_record_from_before_092_is_refused`).

## Mutations (EXECUTED)

Each applied to the worktree's file, the two unit files run (`test_sameness.py`, `test_gather.py`, 118 rows), the file restored by copy (`git status` clean after). Every mutation was killed.

| | mutation | rows that failed |
|---|---|---|
| M1 | claims: `fuel` also explained by `changed` | 1: `test_a_claim_explains_its_own_kind_only[changed=*, fuel]` |
| M2 | claims: `new` and `retired` not directional | 2: the two directional cases of the same row |
| M3 | claims: the suite explained whatever `units` sums to | 1: `test_a_claim_explains_its_own_kind_only[units=2, suite]` |
| M4 | fuel: a release's Linux-sourced fuel held (the darwin guard off) | 3: the darwin twin, two releases, fuel facts |
| M5 | fuel: compared across platforms and from Linux sources | 8 |
| M6 | gather: `did_run` ignores `CI_NEEDS` | 6, `test_gather.py::test_a_ci_need_block_is_no_source` among them |

No row covers Findings 1 and 2: no synthetic shard record has a `fail`, `gap` or non-CI block on Linux or Windows under a darwin `pass`, and none has a sourceless check with a run status.

## Constitution checks

- §4 constraints: judge only; no `src/`, `scripts/`, `recipes/`, `downloads/` or workflow change; no check, golden, gap or allowance edited (READ: the diff's seven files). Rule 4 holds for the judge itself (G1 to G7 untouched); Findings 1 and 2 are about the comparison tool, which the lane will now trust in place of reviewers' full judges.
- §7 never-do list: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1 —
2. Finding 2 —
3. Finding 3 —
4. Finding 4 —

## Verdict

Lands once Findings 1 and 2 are fixed in code with their rows (sameness names a check whose merged status is worse than its source's beyond an allowed CI-need block, and refuses a sourceless check with a run status), and the README says to compare only a green run's record; Findings 3 and 4 are Lows with their fix text.

## Confirmation (2026-10-20, on `69c3b25`, rebased onto main `880be64`)

The same reviewer re-tried both Mediums against the builder's answer (`a10bc92..69c3b25`: `gather.py`, `sameness.py`, the two unit files, the progress README, the spec's disposition, this file). Before each pytest run, `build/lane.lock` was absent from the main tree.

- **Unit files (EXECUTED):** `test_sameness.py`, `test_gather.py`, `test_several_cores.py`, 159 passed (153 before; six new rows).
- **F1 confirmed (EXECUTED).** `regathered-39359915030-f1.json` matches the record I probed before on every check except the new `worst_platform` (669 checks, 0 others differ). Compared with itself, it prints `…test_the_removal_never_deletes_what_the_guest_may_not[home]: status 'pass' on darwin-arm64, 'fail' on win32-amd64` and the same for `[private]`, and exits 1. A claim list with `"*"` in every kind still leaves both lines, exit 1. The two `descriptor limit` rows print nothing. The old record, without `worst_platform`, is refused, exit 2. The README now says to compare only a run whose every job, the gather included, is green.
- **F2 confirmed (EXECUTED).** The same record with every `source` stripped and every status `fail` is refused, exit 2, with one line naming the first such check.
- **F3, F4:** fixed, each with a row (READ; the rows pass).
- **F5, F6:** answered in the spec's "Disposition of the build review"; I accept both answers.
- **Mutants (EXECUTED), each killed and the file restored by copy (`git status` clean):** F1 with the line off (`if False:`) fails 1 row; F1 with a CI-need block excused on any system fails 1 row; F1 with the line made a claimable `status` field fails 1 row; F2 with the refusal off fails 3 rows (`test_a_check_without_a_source_that_ran_is_refused`, each case).
- **One residual, Low (a note, no round):** `worst_platform` records one system, the worst. A check that is `blocked` by `descriptor limit` on Windows outranks a `gap` on Linux (`ORDER`), so a Linux gap under a darwin `pass` on one of those two rows is not named (EXECUTED with the unit fixtures: no difference). Between two `blocked` statuses the first record in order wins, so a Linux block by another need could be masked the same way if Windows came first. G4 reds both (a gap not held, a block not allowed on that system), and the README now asks for a green run, so nothing lands on it; a later change may have `merge` keep each system's status, or the worst status other than an allowed CI block.
- No new CI run on `69c3b25` (the builder defers to wave 03's dry run; judge-only, the lane's call).

**Confirmed:** F1 to F4 are fixed with rows that bite, F5 and F6 are answered, and the verdict is now "lands".
