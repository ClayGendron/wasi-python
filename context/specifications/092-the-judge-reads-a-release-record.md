# 092 — the judge reads a release record: sameness against a CI run, and claim lists

- **Status:** **built 2026-10-19** on `spec/092-the-judge-reads-a-release-record`, rebased onto main
  `e8ba20a` (wave 01) at `1a23fe0`; CI run 39359915030 on that tip red only on wave 01's two
  Windows removal rows (main's own dry run 39358820218 the same; spec 094 fixes them); before the
  rebase, run 39354482605 green on every job (the Landing notes). Drafted 2026-10-19 from main `97be88a`
  (spec 078's acceptance). It changes neither
  the guest's imports nor its exports, the artifact set nor the build recipe, and it is judge-only,
  so §5.6 and AGENTS.md rule 8 ask no review before build. A different agent reviews the build.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** a judge change; **parallel-safe**, not build-class (§5.7). Edits to
  `tests/harness/gather.py` (`merge`) and `tests/harness/sameness.py`; new rows in
  `tests/unit/test_gather.py`; new `tests/unit/test_sameness.py`; `context/progress/README.md`
  (how to compare against a release record, and the claim list). No `src/`, `scripts/`,
  `recipes/`, `downloads/`, workflow or README. It moves no check and no fuel: the lane accepts it
  with `--accept-judge`.
- **Depends on:** nothing unlanded. It is spec A of the wave pipeline (the design memo of
  2026-10-19, sections 3.2, 3.3 and 5, adopted by the owner that night).
- **Research it stands on:** the wave-pipeline design memo (the lane's scratchpad, 2026-10-19,
  §3.2: "the merged record lacks `deselected`, `collected_files`, `suite` per run and
  `meta.foreign`"); `context/decisions.md`, "Waves, judging on CI"; spec 052, Decisions 11 and
  12; spec 063, Decision 9 (the gather). EXECUTED here: the merged record of run 39346796670
  (5 checks blocked, 2 of them `descriptor limit` on Windows only; `suite` per system only).

## The problem

The wave pipeline moves every full judge but the lane's to GitHub Actions. A builder or a reviewer
pushes its branch, dispatches `release.yml`, and reads back the gather job's merged record,
`release-record-1` (`gh run download <id> -n release-record-1`). The lane then compares that record
with its own acceptance (`context/progress/README.md`, step 3a; spec 052, Decisions 11 and 12).

Today it cannot, for four reasons:

1. **The merged record lacks the run fields.** `gather.merge` writes `meta`, `checks` and a
   per-system `suite`. It has no `deselected`, no `collected_files`, no per-shard suite and no
   `meta.foreign`, so `sameness.py` prints a spurious difference for each.
2. **A merged check is the worst status across systems.** A check that passes on darwin and Linux
   and is blocked on Windows by `descriptor limit` (two rows today) is `blocked` in the merged
   record. The lane's darwin run says `pass`: a spurious difference.
3. **Some checks run in no shard.** The gather allows a check to be blocked by a need CI lacks by
   nature (`oracle`, `prior-art clones`, `three systems`, `descriptor limit`: `gather.CI_NEEDS`).
   The lane runs the oracle; CI cannot. Comparing those rows says nothing about either run.
4. **Fuel from Linux is not the lane's fuel.** Upstream groups that run on Linux only in CI give
   the merged record Linux metrics. The ratchet compares fuel per platform (`accepted.json` keys
   metrics by platform); sameness should too.

And one problem of scale: a wave lands up to five specifications at once. A reviewer's record
lacks the other entries' changes, so the lane's record differs from it in every row another entry
changed. Today the lane sorts those differences by eye.

## Principle

A release record is a record of the same judge, run in shards. Sameness reads it as the darwin run
it contains: each check as the darwin record that ran it saw it, else the first other system that
ran it. A row no shard ran is not compared, and is named. And a difference is explained only by a
claim written before the comparison, by kind: a fuel claim never explains a lost pass.

## Decisions

1. **The merged record carries the run fields** (`gather.merge`):
   - `deselected`: the goal checks no record ran (their merged status is `deselected`). Empty
     in a release G3 passes.
   - `collected_files`: the union of every record's `collected_files`.
   - `runs`: for each record, `"<system>/<shard>": {"platform": …, "suite": {…}}` (the suite per
     run). `suite` stays per system as before, for the scoreboard.
   - `meta.foreign`: the sorted union of every record's `meta.foreign`. Empty in a release G2
     passes.
   - per check, `source`: the entry of the record that ran it, darwin first, then Linux, then
     Windows, with that record's `platform`, and without its metrics (those stay in the check's
     `metrics`, from the same record). A record *ran* a check when its status is neither
     `deselected` nor `blocked` by a need in `CI_NEEDS`. A check no record ran has no `source`.
     The check's `metrics` now come from the same choice; before, a check blocked by a CI need on
     darwin gave its empty metrics even when Linux ran it.

   The merged check's own fields stay the worst status across records: the scoreboard and the
   gather's verdict are unchanged.
2. **Sameness reads either kind of record.** A record whose `meta` has `records` is a release
   record. A release record without `runs` is from before this spec: `sameness.py` refuses it,
   exit 2, one line. Its view of a release record:
   - each check with a `source`: the source entry with the check's metrics;
   - each check without one: not compared. It is named on stderr, counted by need ("not run on
     any system in the release: 3 (oracle 1, prior-art clones 1, three systems 1)"), never a
     difference. A check present in one record and absent from the other is still a difference,
     whatever its status.
   - `suite`: the sum of the suites of the runs on darwin (the build shard and the macOS shards),
     which between them run every unit test a darwin run does (EXECUTED: 1632 in both, base run
     39351481374 against spec 078's worktree record). **Between a release record and a run
     record** the suite's `total` and its number of failing unit tests are compared, not the split
     between passed and skipped: a unit test may skip on one host and pass on the other (one did,
     in that comparison: 1625 and 7 skipped in CI, 1624 and 8 locally). The split is named on
     stderr. Between two records of one kind the suite is compared whole, as before;
   - `deselected`, `collected_files`, `meta.foreign`: as written.
3. **Fuel is compared between records of one platform, and a release's only where darwin gave
   it.** For a run record the platform is `meta.platform`; for a release record's check, its
   source's. Where they differ the fuel is not compared, and stderr counts the rows ("fuel not
   compared across platforms: 2 (darwin-arm64 against linux-x86_64)"). A release record's fuel
   from a Linux or Windows source is never compared, even against another release's Linux fuel,
   and stderr counts it ("release fuel not from darwin, not compared: 14 (linux-x86_64 14)"):
   G5 holds only darwin fuel to the acceptance (`accepted.json` keys metrics by platform, and has
   darwin's alone), and Linux fuel is not stable between runs. EXECUTED (the build): three CI runs
   of one judge on one artifact, 39346796670, 39351481374 and 39354482605, gave `cpython-b`
   291,676,466,266, 301,981,930,936 and 292,482,708,525 (3.5% apart), `cpython-archives`
   163.08e9, 165.80e9, 163.08e9, and the pandas groups up to 4e-4 apart; every darwin-sourced
   row (`cpython-fs`, `numpy-lib`, all the own checks) was equal to the instruction. `bytes` and
   `passes` are compared everywhere: the artifact is one, and G5 already holds `passes` equal on
   every system. For two run records of one machine nothing changes.
4. **One line per item for the run fields.** `deselected` and `collected_files` differences print
   one line per node or file (`collected_files: tests/unit/test_x.py only in the second record`),
   not one line holding both lists, so a claim can explain one of them. `suite` and
   `meta.foreign` stay one line each.
5. **`--claims <toml>`** prints only the differences no claim explains, and exits 1 if any
   remain. The claim list is the set of rows a specification changes, read as what the **second**
   record has that the **first** lacks. The shape:

   ```toml
   [[claim]]
   spec = "092"                       # required: the specification's number, as a string
   new = ["tests/unit/test_sameness.py",
          "tests/checks/test_v1_4_embedding.py::test_x[plain]"]   # checks or files it adds
   retired = []                       # checks or files it removes (each check also --retire)
   changed = []                       # checks whose status, need, reason, closer, area, facts
                                      #   or set of metrics it changes (a gap closed, say)
   passes = []                        # upstream checks whose passes (and passed_digest) move
   grows = []                         # checks whose fuel or bytes move
   growth = ""                        # required when grows is not empty: the growth reason
   units = 0                          # unit tests added (negative: removed)
   ```

   Every key but `spec` may be left out. An entry with `::` is a check; one without is a file and
   stands for every check in it; one ending in `*` stands for every check or file that begins
   with what precedes it (`"*"` alone: every row, for a toolchain change). A claim explains, and
   only explains:

   | difference | explained by |
   |---|---|
   | `<check>: only in the second record` | `new` |
   | `<check>: only in the first record` | `retired` |
   | `collected_files: <file> only in the second record` / `… the first record` | `new` / `retired`: the file itself, or a check in it |
   | `<check>: status`, `need`, `area`, `closer`, `reason`, `metrics`, `facts`; `deselected: <check> …` | `changed` |
   | `<check>: passes`, `facts` | `passes` |
   | `<check>: fuel`, `bytes` | `grows` |
   | `suite` | the claims' `units` sum: the total moved by exactly it, and the number of failing unit tests is equal |
   | `meta.foreign` | never |

   A wave's file is the concatenation of its entries' blocks: `[[claim]]` tables append. A key the
   shape does not name, a wrong type, a missing `spec` or `growth`, or an unreadable file: exit 2,
   one line. `--except <spec>` (repeatable) drops that spec's claims: the lane passes the entry
   whose record is the first one, since its changes are in both records. stderr names how many
   differences each spec's claims explained and every claimed entry that matched nothing ("claimed,
   not seen"): a stale claim is visible, not red.
6. **What stays the same.** `differences(a, b)` keeps its meaning for two run records of one
   platform, except Decision 4's line format. The gather's red lines, G1 to G7, are untouched.
   Nothing in `scoreboard`, the plugin or the ratchet changes.

## Intent

The lane can compare its acceptance with any CI run of the same judge, and with five reviewers'
records in one wave, and see only what no specification claimed.

## Design

`gather.merge` picks, per check, the record that ran it (`did_run`: not `deselected`, not
`blocked` by a `CI_NEEDS` need), darwin first, and writes it as `source` beside the worst
status; it adds `deselected`, `collected_files`, `runs` and `meta.foreign`. `sameness.py` turns
either record into a `View` (the checks compared, each one's platform, the checks no shard ran,
the run fields) and compares two views into structured `Diff`s, each with its line and what a
claim must name to explain it. `differences()` returns the lines, as before; `notes()` what was
not compared; `load_claims()` and `explain()` read a claim list and split the differences into
explained and not. The command prints notes on stderr and differences on stdout.

## Scope

In: Decisions 1 to 6. Out: spec B of the design (the lane accepts from a release record); a
`judge_only` dispatch input; any change to `release.yml`. The gather still writes `record.json`
under the artifact `release-record-<attempt>`.

## Acceptance criteria

1. **The checks fail first.** On main's code: the new rows of `tests/unit/test_gather.py` and
   `tests/unit/test_sameness.py` fail (the merged record has no `runs`; `sameness` has no
   release view and no claims), and the landing notes give the count.
2. **The merged record** (`test_gather.py`): it has `deselected`, `collected_files`, `runs` (a
   suite per record), `meta.foreign` (a union), and per check a `source` that prefers darwin and
   skips a CI-need block; a check no record ran has none; the merged status stays the worst.
3. **Sameness against a release record** (`test_sameness.py`, records built by `gather.merge` from
   synthetic shard records): no difference against the darwin twin run record; a Windows-only
   `descriptor limit` block is no difference; a check no shard ran is not compared and is named;
   a darwin `pass` against a local `fail` is a difference; Linux fuel is not compared, darwin fuel
   is, between a release and a run record and between two releases; the darwin suite sum is
   compared, and across kinds only its total and failing count; a shard's `meta.foreign` is a
   difference; an old release record is refused, exit 2.
4. **Claims** (`test_sameness.py`): each kind explains its own lines and no other (a `grows`
   claim leaves a status line); `new` and `retired` are directional; a file entry and a `*` entry;
   `units` explains the suite line only when the sum is exact; `--except`; a bad file exits 2; the
   command prints only unexplained lines and exits by them.
5. **Nothing moves.** `ruff check`, `ruff format --check` and the fast tier `-n 3` green; the
   existing sameness rows in `test_several_cores.py` and `test_landing_lane.py` pass unchanged.
   The full judge is this branch's release-workflow run (the wave pipeline, section 3.1): every
   red line is a GREW line or G7.
6. **End to end.** That run's `release-record-1` is downloaded, and `sameness.py` is run against
   it with a local record and with another CI run's record; the landing notes give the output.

## For the lane

- **Wave kind:** parallel-safe (judge only). No rebuild, no dry-run needs beyond the wave's.
- **Accept with** `--accept-judge "092: sameness reads a release record and a claim list (gather.merge writes deselected, collected_files, a suite per run, meta.foreign and each check's source; sameness.py compares the darwin view and takes --claims and --except); new tests/unit/test_sameness.py and rows in tests/unit/test_gather.py; no check, golden, gap or allowance edited"`.
- **The expected record:** lost 0, gained 0, grew 0, `judge changed`; the unit suite grows by the
  new rows (the claim's `units`).
- **The claim list:**

  ```toml
  [[claim]]
  spec = "092"
  new = ["tests/unit/test_sameness.py"]
  units = 39   # 36 rows in test_sameness.py, 3 in test_gather.py
  ```

## Landing notes

Built 2026-10-19 in `../wasi_python-092` on `spec/092-the-judge-reads-a-release-record`, from
main `97be88a`, rebased onto main `7d0649d` (context only; no conflict), by the agent that wrote the
draft (a fresh agent reviews the build). Evidence under `build/092/` in the worktree:
`first-fail.txt`, `fast-a8a3830.txt` (and its record `fast-a8a3830.json`), and `e2e/` (both CI
records, the re-gathered base record, the claim list and every comparison's output, `e2e.txt`).

### What was built

- `gather.merge`: `did_run`; per check `source` (darwin, then Linux, then Windows, among the
  records that ran it) with the check's `metrics` from the same record; `deselected`,
  `collected_files`, `runs` (each record's platform and suite) and `meta.foreign` (Decision 1).
  The merged status, the scoreboard and G1 to G7 are unchanged.
- `sameness.py`: `View` and `view()` for either kind of record; structured `Diff`s; fuel only
  between one platform's rows and a release's darwin rows (Decision 3); one line per item for
  `deselected` and `collected_files` (Decision 4); the suite across kinds by total and failing
  count (Decision 2); `notes()`; `load_claims()`, `explain()`, `unexplained()`; the command's
  `--claims` and `--except`, notes on stderr, exit 2 on an unreadable record or claim list.
- `tests/unit/test_sameness.py` (36 rows) and three rows in `tests/unit/test_gather.py`.
- `context/progress/README.md`: "Comparing with a release record, and claim lists".

### Criterion 1: the checks fail first (EXECUTED, `first-fail.txt`)

On main's code with the new rows: **30 failed, 50 passed** (27 of `test_sameness.py`'s 30 rows
then, and the three new `test_gather.py` rows: no `runs`, no `source`, no `load_claims`). The two
rows added during the build were each seen failing before their code: the suite across kinds
(1 failed, 33 passed) and darwin-only release fuel (2 failed, 33 passed).

### Criteria 2 to 4 (EXECUTED)

`tests/unit/test_sameness.py`, `tests/unit/test_gather.py` and `tests/unit/test_several_cores.py`
(the existing sameness rows, unchanged): **116 passed**.

### Criterion 5: nothing moves (EXECUTED)

- `ruff check` and `ruff format --check`: green.
- **The fast tier, `-n 3`, on `a8a3830`** (a worktree with no artifact set, so `--partial`): `74/656
  pass · 0 gap · 471 blocked · 0 fail · 111 deselected (unit suite 1655/1670, 15 skipped)`;
  `lost 0 · absent 0 · gained 0 · grew 0 · judge changed`; 1729 passed, 486 skipped.
- **The full judge is CI.** Run **39354482605** on `2787003` (the build before Decision 3's
  darwin-only fuel): **green on every job**, all 18 judge legs, both rebuilds, `verify` on three
  systems, `same-bytes` and the gather (`582/656 pass · 69 gap · 5 blocked · 0 fail`, unit suite
  3964/3987; "three systems: darwin linux win32 on ab78e893…"). **No red line**: no GREW line, no
  G7. Run **39357023086** on `a8a3830`, the tip: **red on one line, not a growth line**:
  `judge (windows-2025, own-guest)`, `FAIL tests/checks/test_v1_2_hostile_guest.py::test_an_abandoned_turn_keeps_its_session_busy`
  (`RED: 1 accepted pass(es) lost`); every other job green, so the gather was skipped. That row is
  spec 078's, red on Windows in 078's own dry run 39351481374 on `97be88a` with the same message,
  green in this branch's first run, and fixed forward by spec 093 in wave 1 (`roadmap.md`). This
  spec touches neither the runner nor that check; the code between the two runs is Decision 3's
  sameness change and its unit row. The lane may ask for the failed job to be re-run, or read it
  as 078's.

### Criterion 6: end to end (EXECUTED, `e2e/e2e.txt`)

Run 39354482605's `release-record-1` was downloaded (`gh run download 39354482605 -n
release-record-1`). Its gather wrote the new fields: `deselected` empty, 60 `collected_files`, 19
`runs`, `meta.foreign` empty, a `source` on 653 of 656 checks (the other three: the oracle, the
prior-art clones, three systems). The base had no record of the new shape (78's dry run
39351481374 on `97be88a` was red on a Windows row, so its gather was skipped), so its 19 shard
records were downloaded and merged by this build's `gather.merge` (a scratch script, not
committed). Then:

1. **This run against itself:** no difference, exit 0.
2. **The base, then this run:** exactly two differences, both 092's own:
   `collected_files: tests/unit/test_sameness.py only in the second record` and the suite (1632 to
   1669 unit tests, the base record being from before the last row). Notes: 3 checks not run on any
   system; 14 rows of Linux fuel not compared.
3. **With the claim list** below (`units` as then, 37): exit 0, "explained by claims: 092 2".
4. **With `--except 092`:** the same two lines, exit 1.
5. **This run against spec 078's worktree record** (a local `-n 3` full judge, `e145f6c`, 656
   checks): 142 lines, every row line one of 53 checks blocked in that worktree (the source trees,
   the compile records, the wheel, the wasmtime CLI), plus 092's own file and suite lines; no
   status, fuel or bytes difference on a check both ran. The suite split (1625 passed, 7 skipped
   in CI against 1624 and 8 locally, at the same total in the base comparison) is a note.
6. **The tip's run, 39357023086**, has no gather record (above), so its 19 shard records, the
   failed Windows one included, were merged the same way. Against run 39354482605's own record:
   one line, the suite (1669 to 1670, the row added between the two). The tip's red Windows row
   is no difference: the darwin view reads that check from darwin, where it passed; the run's own
   red line is where a Windows failure shows.
7. **The base, then the tip, with the claim list as it was then** (`units = 38`): exit 0,
   "explained by claims: 092 2".
8. **Spec 078's worktree record, then the tip, with the claim list:** 140 lines, every one a row
   blocked in that worktree; the file and suite lines explained by 092's claim (1632 to 1670: 38).

**Found on the way: Linux fuel is not stable between CI runs.** Before Decision 3 took its final
form, comparison 2 listed ten Linux-sourced upstream rows past 1e-4 between two runs of one judge
on one artifact (`cpython-b` 301.98e9 against 292.48e9; the pandas groups up to 4e-4). Three runs
(39346796670, 39351481374, 39354482605) show the Linux values switching between a few discrete
values, while every darwin-sourced row matched to the instruction. G5 never sees this: it compares
each record with `accepted.json`, whose metrics are darwin's alone. This spec does not compare that
fuel; a later spec may ask why Linux fuel moves, and whether G5 should hold it.

### Rebased onto main `e8ba20a` (wave 01: 087, 085, 084, 091)

Wave 01 changed `gather.py`, `sameness.py`, `test_gather.py` and `test_several_cores.py`. The four
build commits were squashed into one on the rebase, with each file merged once (three-way, from
`7d0649d`). The resolved hunks:

- **`gather.merge` against spec 085:** 085's `need` repair (a non-string need written as its
  `repr`, already red at G4) now applies to the merged check and to its `source`; 085's whole-number
  filter on the suite tally is kept; `meta.set_sums` (085) sits beside `meta.foreign`. `CI_NEEDS`
  is now a map from need to systems; `did_run` asks only whether the need is one of its keys, and
  is safe on a non-string need (085's B3). The per-system `allowed()` stays G4's.
- **`sameness.py` against spec 091:** `facts` left `FIELDS` for 091's `_facts`. A `fuel_facts`
  value is fuel here too: compared to the tolerance only where the fuel itself is (one platform,
  a release's darwin rows), and explained by a `grows` claim; a change in the fuel facts' names or
  in the other facts is a `facts` line (`changed` or `passes`). New row
  `test_a_fuel_fact_follows_the_fuel_rules` (36 rows now; `units` 39); with the darwin guard
  removed it fails (EXECUTED).
- `test_gather.py`'s `Case.inputs()` carries 085's three new `Inputs` fields; the synthetic inputs
  of `test_sameness.py` carry `set_sums_sha256`.
- **After the rebase (EXECUTED):** the three unit files, 152 passed; `ruff` green; **the fast tier
  `-n 3`: `74/669 pass · 0 gap · 484 blocked · 0 fail · 111 deselected (unit suite 1758/1773, 15
  skipped)`, lost 0, gained 0, grew 0, judge changed** (`build/092/fast-rebased.txt`).
  **CI on the rebased tip `1a23fe0`: run 39359915030, red on one job, not a growth line:**
  `judge (windows-2025, own-embedding)`, `FAIL tests/checks/test_v1_4_embedding.py::test_the_removal_never_deletes_what_the_guest_may_not[home]`
  and `[private]` (`skipped without a known need: … a Windows guest deletes a read-only file
  itself (spec 084, C2)`; `RED: 2 accepted pass(es) lost`). Wave 01's own dry run on main's
  `6006fde`, 39358820218, failed on exactly these two rows; spec 094 (the removal rows name their
  Windows need) is its fix. Every other job was green, so the gather was skipped again. Spec 078's
  Windows row passed this time.
- **End to end on the rebased tip (EXECUTED):** its 19 shard records merged by this build's
  `gather.merge` (669 checks, `source` on 666), compared with run 39354482605's own record (before
  wave 01): 18 lines, every one wave 01's (eleven new checks of 084 and 087, `test_runner_sets.py`,
  the two binaries' `bytes` +202, numpy-core's new fuel fact name, the suite 1669 to 1773); the two
  Windows-only failures are no difference (read from darwin). That is the list the wave's claim
  lists would explain.

### Departures

- Decision 3 was widened during the build (release fuel from darwin only), from the evidence above.
  Decision 2's suite rule was added during the build, from comparison 5.
- The worktree's `build/progress/latest.json` is overwritten by every narrowed run, so the fast
  tier's record was kept as `build/092/fast-a8a3830.json`.

One line: sameness now reads the release workflow's merged record as the darwin run it contains,
and with a claim list prints only what no specification said it changes.
