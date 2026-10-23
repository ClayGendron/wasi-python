# Review of spec 062's build: the progress history stays small

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). It wrote none of the build. It did write the spec's pre-build review (`062-the-progress-history-stays-small-spec-2026-10-18.md`), and it checks here that the build honours what that review asked for.
- **Reviewed:** `git diff f6b3f75 0ba102b` on `spec/062-the-progress-history-stays-small` (`/Users/claygendron/Git/Repos/wasi_python-062`). `6fdd1fd` is the spec revised against the pre-build review. `0ba102b` is the build and its landing notes. That is 17 files, +1,935 −134. The worktree is clean at `0ba102b`, and this review wrote nothing in it.
- **Read:** the spec at `0ba102b` in full (Decisions 1 to 13, criteria 1 to 13, the Disposition, the landing notes); the whole of `tests/harness/history.py`; the diffs of `scoreboard.py`, `plugin.py`, `needs.py`, `scan.py`, `tests/checks/test_rules.py`, `test_v1_2_portable_and_sealed.py`, `context/progress/README.md`, `context/README.md`, and specs 002 and 029; `tests/unit/test_history.py` (criterion 2's simulation, criterion 11, the tamper cases); `test_landing_lane.py`'s lane-command tests.
- **Executed.** Scripts and outputs are beside this file, under `062-buildreview/`.
  - **The judge**, both runs with `WASI_PYTHON_ARTIFACTS=…/build/sets/s-8eb9e35734deeb21`:
    - the fast tier, `uv run pytest -m "not slow" -n 3` (`fast-n3.log`);
    - the full judge, `uv run pytest`, serial (`full-serial.log`).
  - **Stand-ins** (`standins.py`, `standins.out`). Eight edits, applied one at a time to a scratch copy of `0ba102b` (`git archive` into `copy/`), each run against the tests it should fail.
  - **Probes of the real module** (`probes.py`, `probes.out`). Main's `history.jsonl` and six format-2 volumes, written through `history.target`, then 50 tampers and misnamings checked with `history.errors` (with `SEALED`).
  - **The rotation, redone** (`rot-1.log`, `rot-2.log`, `rotverify.py`, `rotverify.out`). `history.jsonl` and `accepted.json` were copied to `rot/`. Two real `--accept` runs went from the worktree with `--progress-dir rot/`: `tests/checks/test_rules.py`, `--partial`, `--accept-judge`.
  - **The lane commands** (`lanecmds.out`). `history.ACCEPT_COMMANDS` was run verbatim through `sh -c` in a scratch repository.
  - **The README's line-N one-liner** (`oneliner.out`).
  - `ruff check` and `ruff format --check` on `src tests recipes/guest`.

## The judge

- **Fast tier** (EXECUTED, `fast-n3.log`): exit 0, `1500 passed, 26 skipped`. `wasi_python v1: 326/390 pass · 0 gap · 18 blocked · 0 fail · 46 deselected   (unit suite 1174/1182, 8 skipped)`. `ratchet vs 7c3d606d09: lost 0 · absent 0 · unrun 0 · unrun locally 16 · gained 0 · grew 0 · upstream unrun 31 · not selected 32 · judge changed: tests/checks/test_rules.py, tests/checks/test_v1_2_portable_and_sealed.py, tests/harness/history.py and 8 more`. This is the builder's line exactly.
- **Full judge, serial** (EXECUTED, `full-serial.log`): exit 0, `1512 passed, 58 skipped, 2 xfailed`. `wasi_python v1: 338/390 pass · 2 gap · 50 blocked · 0 fail   (unit suite 1174/1182, 8 skipped)`. `ratchet vs 7c3d606d09: lost 0 · absent 0 · unrun 0 · unrun locally 36 · gained 0 · grew 0 · upstream unrun 31 · judge changed: tests/checks/test_rules.py, tests/checks/test_v1_2_portable_and_sealed.py, tests/harness/history.py and 8 more`. The blocks are local tooling only: the source trees, the oracle, the prior-art clones, `wheel`, and `three systems`, which main's history has never met. This is the builder's line exactly. The run is red only by `judge changed`. Afterwards the worktree was clean, `history.jsonl` still hashed to `SEALED`, and no volume had been made.
- **ruff** (EXECUTED): `All checks passed!` and `92 files already formatted`.

## Criteria against evidence

1. **Lines stop growing.** Met (READ the test, EXECUTED in the fast tier). `test_a_line_records_what_changed_not_every_pass` checks:
   - the line is under 4,096 bytes after 5,000 unchanged passes;
   - it names exactly the 10 ids added and the 3 removed;
   - the replayed sets match.
2. **Many acceptances, the limit holds.** Met (READ, EXECUTED). The simulation follows the criterion:
   - volume 1 is a look-alike of at least 1,000,000 bytes, followed by 500 acceptances through `scoreboard.accept`, then `target`, then an append;
   - the checks grow 392 to 1,500, three systems each have five checks of their own, and the artifact changes every 30 acceptances;
   - every 50th run is partial, the probe drops on `k % 7 == 3`, and linux fails the probe on every run of `art5`.

   What it asserts:
   - the per-line offsets stay within `BUDGET`, and there are at least 4 volumes;
   - `errors` is clean against the halfway commit and the seal;
   - the replayed set equals the run's passes at every line;
   - `art5` gives `{darwin, win32}`.
3. **Main's 59 lines.** Met (EXECUTED):
   - `test_progress_history_is_intact` passes in both judge runs;
   - `git diff f6b3f75 0ba102b -- context/progress/history.jsonl context/progress/accepted.json` is empty (the diff stat lists only `README.md` in that folder);
   - no `history-*.jsonl` is tracked;
   - the rotated copy's `history.jsonl` still hashes to `SEALED` (`0a99162a…1120`).
4. **Tampering in every volume.** Met (EXECUTED, `probes.out`). Probes on all 7 volumes, one at a time:
   - a changed byte, a deleted line, two swapped lines, a deleted volume, and a volume renamed one higher are each reported, except on the newest volume, as noted in F3;
   - so are the stray or non-canonical names `history-60.jsonl`, `history-000060.jsonl`, `history-00060.jsonl.bak`, `history-00001.jsonl` and `history-00000.jsonl`;
   - so is a forged middle line, even with its digest recomputed (by its `prev` and its digest);
   - so is a first line whose `n` is `"60"`, `60.0`, `True` or `None`: each is reported, none raises.

   `volumes()` orders `history-99999.jsonl` before `history-100000.jsonl`. The test file holds cases (a) to (o) and the numeric-order case.
5. **Committed volumes only grow.** Met (READ, EXECUTED). After the newest volume is dropped, or its last line truncated, the committed snapshot reports it ("committed history volume … is missing", "… does not extend its committed version").
6. **Three systems reads every volume.** Met (READ, EXECUTED in the fast tier).
7. **The plugin writes where `target` says.** Met (EXECUTED twice, `rot-1.log` and `rot-2.log`):
   - `accepted: …/rot/history-00060.jsonl line 60`, then `… line 61` in the same volume;
   - `history.jsonl` is unchanged at 1,037,524 bytes and still hashes to `SEALED`;
   - line 60's `prev` hashes line 59;
   - `errors` over the copy is `[]`, with `f6b3f75`'s `history.jsonl` as committed and the seal;
   - the replayed set at line 61 equals run 2's 24 passes;
   - the volume holds no `\r`.

   Line 60 removes 350 ids, because a rules-only `--partial` run passes only 24. It is 32,858 bytes, as expected for that run.
8. **An oversize line is refused.** Met (READ, EXECUTED in the fast tier). `accept` checks the size before `remember`, so nothing is cached or written.
9. **Rule 1 across volumes.** Met (READ, EXECUTED). Cases (a) to (e) pass. Stand-in S4 (the newest volume picked by name) fails all seven of rule 1's volume tests: `history-00060.jsonl` sorts before `history.jsonl` by name.
10. **The lane's commands.** Met (EXECUTED, `lanecmds.out`). Run verbatim through `sh`, the two strings in `history.ACCEPT_COMMANDS` exited 0 and made one commit holding exactly `accepted.json` and `history-00060.jsonl`. They left a changed `README.md` and a staged `src/staged.py` out. The README quotes both strings, a check holds that (READ), and the unit test runs them as argument lists.
11. **Each caller verifies only what it must.** Met (READ, EXECUTED; stand-in S1 fails it). The builder's counts are in the landing notes: 999 digests and 81,137,136 bytes hashed while writing 500 acceptances, against the 7.54 GB projected. One intact check computes 500 digests. `accept` computes 2, and with a warm cache it parses only the newest line. `systems_that_passed` computes 0.
12. **A broken history.** Met (READ, EXECUTED; stand-in S6 fails it).
13. **Green.** Met: ruff is clean, the fast tier is clean, and the full judge is 338/390 with 0 fail and lost 0, red only by `judge changed`.

## The pre-build review's conditions in the build

- **F1:** criterion 3 is narrowed, and holds (above).
- **F2:** `passed_sets(lines, verify=True)`; `last_passed` checks the newest digest alone, with a one-entry cache; `systems_that_passed` uses `verify=False`; only `errors` verifies every digest. Stand-in S1 fails criterion 11.
- **F3:** `_volume_errors` reports "old format outside history.jsonl", and `SEALED` pins volume 1. Stand-in S2 fails case (l).
- **F4:**
  - names: `first_line_of` requires `volume_name(n) == name` and `n >= 2` (stand-in S7 fails 4(d));
  - order: numeric in `volumes()` and in rule 1;
  - `schema`: must be the integer 2;
  - blank lines and a missing final newline: reported;
  - a broken history: `systems_that_passed` returns the empty set.
- **F5:** the plugin writes with `encoding="utf-8", newline="\n"`, and `target` and `errors` measure bytes. Stand-in S3 (CRLF) fails criterion 7.
- **F6:** the per-line replay assertion, the `art5` strict subset, and rule-1 case (e) are all in.

## The stand-ins, re-applied (EXECUTED, `standins.out`)

| Stand-in | Result |
|---|---|
| S1 (F2): `last_passed` verifies every line | fails `test_each_caller_computes_only_the_digests_it_must` |
| S2 (F3): no old-format rule outside volume 1 | fails `test_an_old_format_line_moved_out_of_volume_1` |
| S3 (F5): the plugin writes `\r\n` | fails `test_accept_starts_a_volume_when_the_newest_is_full_and_says_where` |
| S4 (mine): rule 1 takes the newest volume by name | fails all 7 rule-1 volume tests |
| S5 (mine): no begun-early check | fails `test_volume_3_begun_early` |
| S6 (mine): an added id already passing is accepted | fails `test_three_systems_on_a_broken_history_is_not_met` |
| S7 (mine): non-canonical names accepted | fails `test_a_stray_or_non_canonical_name[history-000060.jsonl]` |
| S8 (mine): `target` rolls one byte early (`<` for `<=`) | **passes every test** (F1) |

## Findings, most severe first

1. **Low. The roll's exact boundary is untested (EXECUTED, S8).** S8 made `target` roll when a line would fill the newest volume to exactly `BUDGET`, and `test_history.py` stayed green. The begun-early check in `errors` uses `<=` too, so it would report such a volume. But no test writes a line that lands exactly on the boundary, so neither side of the rule is held there. Decision 4's "at most `BUDGET`" is the rule, and only its interior is tested. *Fix:* one unit case. Pad a line so the newest volume ends at exactly `BUDGET` bytes, and assert that `target` keeps it and `errors` is clean. Then add one byte, and assert that it rolls. It does not block landing: the rule cannot let a file pass the limit either way.

2. **Info. Writing LF is enforced; reading CR is not (EXECUTED).** A volume rewritten with `\r\n` is reported only where a later line chains to a CR-carrying line ("prev does not hash line 70"). A history written with CR from its start by a foreign writer would chain consistently, because `accept` hashes the same CR-carrying text. The plugin writes LF, and `.gitattributes` forces LF on checkout, so this needs a foreign writer. *Optional:* `_volume_errors` reports a volume that holds `\r`. That is one line and one case.

3. **Info. The newest line stays editable until it is committed, as today (EXECUTED).** One byte changed in the newest line's `platform` gave `[]` from `errors` without `committed`. So did dropping the newest volume with `accepted.json` put back, truncating the newest line, and forging the newest line with its digest recomputed. With the committed snapshot, each is reported, and after a commit rule 1 reports it. This is the pre-build review's F7, unchanged from `history_errors`. The README now says plainly what catches a deliberate edit. No change.

## Constitution checks

- §4.9: holds. Every new check counts bytes, digests or entries. `history.OPS` replaces any timing, and the landing notes record counts.
- §4.10: holds. The landing notes' numbers carry their commands and logs (`build/062-*.log`). This review's numbers are in the files beside it.
- §5.2: holds. The spec decides every choice, and the Disposition answers each pre-build finding.
- §5.6: the build is reviewed by an agent that did not write it. The counted tests were re-run, each criterion was checked against its evidence, and the stand-ins were re-applied.
- §5.7: holds. The change is parallel-safe and not build-class. It touches no `scripts/`, `recipes/`, `downloads/SHA256SUMS` or workflow (READ, the diff stat). The lane accepts with `--accept-judge`, serially. Lane step 4 changes only by the tested fixed commands.
- §7: nothing tripped. No line of the history is rewritten, no limit is raised and no file is exempted. Nothing is committed or pushed by the builder beyond its branch.
- AGENTS.md rule 4: the judge change is its own change, with its reason, and the judge-hash line names it (`judge changed: … tests/harness/history.py and 8 more`). No gap, golden or upstream allowance is edited.

## Verdict

**Lands.** F1 should be fixed: one boundary case in `test_history.py`. It can ride along with this landing as a judge-only edit, re-reviewed by diff, or come as the next small judge change. Either way it is answered here, and the rule it tests cannot let a file pass the limit. F2 is optional hardening. F3 needs no change. The lane accepts with `--accept-judge`, serially, and commits with `history.ACCEPT_COMMANDS`.

One line: the history now continues in sealed, chained volumes of change-lines. Every tamper the probes tried is caught in every volume or is today's known limit. All the stand-ins tried fail except one boundary case. The lane's commands do exactly what the README says.
