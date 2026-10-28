# 154: The first fuel under a new engine is Linux's

- **Status:** drafted 2026-10-28 on `spec/154-the-first-fuel-under-a-new-engine-is-linuxs` from `dev`'s `6bc56eeb`, from the reserved line of `../roadmap.md` ("0.1.2", the stretch paragraph) and 127's landing notes ("The first release-tier acceptance after the move"). Not yet approved to build; no pre-build review is required (Decision 8).
- **Date:** 2026-10-28
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, **not structural**, **a judge change**. It touches the harness alone: `tests/harness/scoreboard.py` (the ratchet's fuel rule and the acceptance's merge), `tests/harness/accept_from.py` (which fuel a check only another system ran is applied with), `tests/harness/gather.py` (G5's "records no" check skips a label); rows in `tests/unit/test_scoreboard.py`, `test_accept_from.py`, `test_gather.py` and `test_plugin.py`; the ledger `../release-tier-claims.toml` (127's block removed) and its history `../release-tier-claims-history.md`; the paragraph "Acceptance from CI's record" of `../progress/README.md`; and its news file. Nothing under `src/`, `scripts/`, `recipes/`, `release/`, `docs/` or `.github/`, no artifact byte, no default an embedder can see, no line of `tests/public_api.txt`. The ledger is a verdict-bearing judge file, so the news file names it under `[claim.judge]`.
- **Depends on:** landed and unchanged: 002 (the ratchet: metrics keyed by platform, fuel compared within one wasmtime version, the lower kept), 092 (fuel is compared between records of one platform; Linux fuel moves between CI runs), 102 (the release tier; "never from a CI record" for Linux fuel), 127 (the engine move and its ledger block), 138 (the acceptance from CI's record; the upstream groups run on Linux alone in CI). On nothing in flight. Reserved 156 (the judge finds an upstream test that walks a folder unsorted) is the work that could later make Linux fuel repeat; this specification does not wait for it (Decision 4).
- **Research it stands on:** no memo. 127's landing notes (READ: the 716 rows refused as `fuel is no longer recorded` at 0.1.1's release acceptance, run 40465516946); 092's landing notes, "Found on the way: Linux fuel is not stable between CI runs" (READ); the review of 066's specification, note N1, and `../roadmap.md`'s reserved listing-order line (READ: ext4's directory order differs between machines); and "What the draft measured" below (EXECUTED).

## The problem

The ratchet keeps one fuel per check, darwin's, under the key `darwin-arm64`. In CI the upstream groups of the release tier run on Linux alone. So a release-tier upstream row only ever gets a fuel from a Mac: a local `--tier release` acceptance.

When the engine moves, every fuel of the old engine stops being a measurement of the new one. The acceptance from CI drops it for a check only Linux ran, and the ratchet reads a dropped fuel as `fuel is no longer recorded`, a growth. At 0.1.1's release acceptance that was 716 rows, every `test_upstream_suite` check of the release tier. 127 cleared them with a `[[claim]]` block in the release-tier ledger whose `grows` covers every upstream suite by prefix.

Two harms follow. Today 716 upstream rows record no fuel at all, and none will until a Mac runs the release tier. And the block still sits in the ledger: `release/version.py date` would move it under 0.1.2, where its prefix would clear a real fuel growth in any upstream row darwin measured at 0.1.2's release acceptance.

The run already had the measurement. Run 40465516946's record held a Linux fuel for every one of the 716 rows under wasmtime 50.0.1. The acceptance threw it away because Linux fuel is not ratcheted.

## Decisions

### 1. The engine is already part of the record; a move is read per row

Each platform's entry in `accepted.json` names the wasmtime that measured it: `metrics: {"darwin-arm64": {"wasmtime": "50.0.1", "fuel": …, "passes": …}}` (READ: every one of the 1,065 entries today names 50.0.1; `scoreboard.accept` writes `meta.wasmtime` into each entry it touches, and `accept_from` gives `uv.lock`'s version as the run's). No new engine key is needed.

- **How a move is detected.** Per row, not per run: a row's fuel is "of the current engine" when its entry's `wasmtime` is the run's (`uv.lock`'s, which the gather already holds every shard record to). A row whose entry names another version, or has no fuel, has no fuel of the current engine. This is 002's rule, unchanged; nothing marks "the first acceptance after a move" as a special event, so a row a later pull request adds is served by the same rule.

### 2. Another system's fuel is kept in the darwin entry, labelled with the system that measured it

When the acceptance takes a fuel darwin did not measure (Decision 3), it writes it in the check's one entry, under `darwin-arm64`, with a label: `"fuel_platform": "linux-x86_64"`, the platform of the record that ran the check (its `source.platform`). An entry without the label holds fuel measured on its key's own platform, as every entry does today, so nothing already accepted is rewritten.

- **Why not an entry of its own under `linux-x86_64`.** Every Linux shard's ratchet keys its run `linux-x86_64`, so such an entry would be compared with Linux's next measurement on every pull request, at one part in ten thousand (Decision 4 says why that must not happen). And `accepted.json` keeps one entry per check, the one G5's "records no" check and its pass-count check read; the darwin entry already holds the pass count and bytes that only Linux measured (`accept_from`'s module docstring: "takes the record's counts … under the same key").
- **Labels are not metrics.** `wasmtime` and `fuel_platform` are the two labels of an entry, one tuple in `scoreboard.py`. The ratchet never compares a label or calls one "no longer recorded"; G5's "records no `<name>` (accepted.json has it)" skips both; the budget reads `fuel` alone and is unchanged.

### 3. Linux's fuel is taken only when the row has no fuel darwin measured under the current engine

At an acceptance from CI's record, for a check whose source is not darwin (in practice an upstream group Linux alone ran) and whose record carries a fuel:

- if the accepted entry holds a fuel darwin measured (no label) under the current engine, that fuel is kept, as today, and Linux's is ignored;
- otherwise (no fuel; a fuel of another engine; or a fuel already labelled with another system) the record's fuel is applied, labelled with the record's platform.

A local acceptance is unchanged: it keys its own platform, and a local Linux `--accept` writes its own `linux-x86_64` entry as it does today. A darwin-sourced check is unchanged.

- **Why only then.** Darwin's fuel is the one G5 and the ratchet hold to the instruction (092, 102); Linux's is a stand-in until darwin's exists, never a rival to it.
- **Why "no fuel" counts too.** A release-tier group a pull request adds after the last Mac acceptance has never had a darwin fuel; it gets Linux's at its first release acceptance, for the same reason.

### 4. Linux's fuel is recorded, and never compared: not with Linux's next one, not with darwin's

The ratchet compares a fuel only when the accepted one and the run's were both measured on the run's own platform under the same wasmtime. Otherwise it is listed and never red:

- the engines differ: `fuel_not_compared`, "fuel not compared (wasmtime changed) N", as today;
- the engines agree, but either fuel was measured on another system (either side carries a `fuel_platform` that is not the run's platform): a new list, `fuel_elsewhere`, "fuel not compared (measured on another system) N".

So a Linux fuel is never a growth or a fall against a Linux-first fuel or against darwin's, and a darwin fuel is never one against a Linux-first fuel. Within one system the lower is kept (Decision 5), so the accepted fuel only falls; across systems nothing is compared.

- **Why not compare Linux with Linux.** Linux fuel does not repeat across CI runs. 092 measured `cpython-b` 3.5% apart over three runs of one judge on one artifact, the values "switching between a few discrete values"; the wave-08 review saw `cpython-archives` move 1.6% between two runs; ext4 lists a folder in an order that differs between machines (066's review, N1), and 0.1.0's second dry run went red on it (`joblib-r`). This draft found the 83 normal-tier Linux rows equal to the instruction across three runs of 2026-10-25 ("What the draft measured"), which is encouraging and not enough: one red post-merge acceptance on noise stops every merge into `dev` (AGENTS.md, step 9). A wider tolerance for Linux has no evidence to set it. A later specification may ratchet Linux fuel once it is shown to repeat (after 156's listing-order work), with the runs named.
- **Why not compare Linux with darwin.** They differ by more than the tolerance and not by a constant: under wasmtime 50.0.1, Linux is from 0.99% below to 0.73% above darwin on the 83 rows both measured, 51 of them past one part in ten thousand ("What the draft measured"; 085 saw up to 0.197% on 0.1.0a7's tag run).

### 5. Darwin's fuel takes over when it comes; within one system the lower is kept

`scoreboard.accept`'s merge of one entry, for `fuel`:

- the same system measured both (the labels agree, an absent label meaning the key's platform) under the same engine, and no growth reason is given: the lower is kept, and the label with it. This is today's rule, now also for two Linux fuels.
- otherwise the new fuel is taken whole: a darwin fuel replaces a Linux-first one and drops the label; a Linux fuel under a new engine replaces any fuel of the old one and carries the label.

So the first darwin measurement under the current engine (a local Mac `--tier release` acceptance, or a CI shard on darwin if a plan ever runs one) replaces the Linux-first fuel without a comparison and without a claim, and from then on the row is compared darwin to darwin, as today. Keeping the lower of a darwin and a Linux fuel would mix two systems in one number; keeping both, each keyed by its system, would make Linux's a second ratchet, which Decision 4 refuses.

### 6. A pull request's gather compares one system with itself only

No change in what a pull request compares, and one row says so:

- a Linux shard's record is compared under `linux-x86_64`, where `accepted.json` holds nothing, so its fuel is compared with nothing, as today;
- a macOS shard's record against a Linux-first fuel is not compared (`fuel_elsewhere`), never `grew`, never listed under `GROWTH`;
- a macOS shard's record against darwin's own fuel is compared as today;
- G5's "records no `fuel_platform` (accepted.json has it)" cannot arise: the label is skipped (Decision 2).

`sameness.py` compares two records, never `accepted.json`, and a record carries no label, so it is unchanged; its rows `test_linux_fuel_is_not_compared_and_darwin_fuel_is` and `test_two_releases_compare_darwin_fuel_only` stay as they are.

### 7. 127's ledger block goes, recorded in the history under 0.1.1

`../release-tier-claims.toml` keeps its header comments and loses its one `[[claim]]` block. `../release-tier-claims-history.md`'s `## 0.1.1` section, which says "No block was in the ledger at the date", gains one paragraph: the block was appended after the date, by 127's landing documents; the release pull request's acceptance (`898bc091`) read it as its one growth reason; and 154 removed it, since an engine move no longer drops a Linux-only row's fuel. The block is quoted in a ```` ```text ```` fence: `news.ledger_claims` reads only ```` ```toml ```` fences, and the package's version is still 0.1.1 until the bump, so a `toml` fence there would still be read as a claim.

- **Removing it alone changes no verdict today** (READ, INFERRED): the ledger is read only by a release pull request's gather (`GITHUB_BASE_REF` is `main`) and by `accept_from` for a release pull request's record; no pull request into `dev` and no push to `dev` reads it. At 0.1.2's release acceptance the 716 rows have no fuel to drop (their entries already hold none), so the block would clear nothing they need; it could only clear a real growth.
- **`release/version.py date` for 0.1.2** then finds an empty ledger and writes "No block was in the ledger at the date." under `## 0.1.2`, as it did for 0.1.1. Without this removal it would move 127's block under 0.1.2.
- **The judge.** The ledger's hash changes, and it is verdict-bearing (`paths.VERDICT_BEARING`), so the first acceptance after the merge needs its reason: the news file's `[claim.judge]` names it. The three harness files are judge files that are not verdict-bearing; the judge-hash line records them and they need no claim.
- **The roadmap's one-line pull request** ("127's ledger block is removed by a one-line pull request … unless 154 lands first and takes it") is not needed once this lands; the orchestrator's roadmap line says so at the merge.

### 8. Not structural, a judge change, no pre-build review

Every change is under `tests/` and `context/`; nothing in `src/`, so none of the structural triggers (a module-level mutable or lock, a private wasmtime-py use, a platform branch, a test seam, a size ceiling in `src/`) can apply. It changes no guest import or export, no artifact and no build recipe, so constitution §5.6's pre-build review does not apply. The pull request's review sees the judge-hash line and the `[claim.judge]` entry.

### 9. The first acceptance after this needs one claim, and adds no field to a record

`accept_from` reads no new field of the gather's record: a check's `source.platform`, which it already reads, names the system. The history line gains no field. The label is written into `accepted.json` only when an acceptance meets a row without darwin's fuel of the current engine.

- **The post-merge acceptance of this pull request** is of the normal tier. Every normal-tier metered row holds darwin's fuel under 50.0.1 today (85 upstream groups and every own check; "What the draft measured"), so no label is written and no fuel moves. Its one reason is `[claim.judge]` for the ledger. No `grows`, no `passes`, no `moved`, no `retired`.
- **0.1.2's release acceptance** gives the 716 release-tier rows Linux's fuel, labelled. A check that gains a metric is no ratchet row (`scoreboard.compare` skips a name the accepted entry lacks), so it needs no claim, and this specification appends no block to the ledger.
- **The next engine move** (a future pin change) needs no `grows` for a Linux-only row, in its own post-merge acceptance or in the release's: every such row's fuel is replaced by Linux's, listed as not compared. The 83 normal-tier Linux-only groups become Linux-first then, until a Mac acceptance.

### 10. The rows first

Each new row is seen failing on `6bc56eeb`'s harness before the change, and named with its failing line in the pull request. Every row counts; none times anything.

- `tests/unit/test_scoreboard.py::test_fuel_another_system_measured_is_never_compared`, parametrized `[a darwin run against a linux fuel]`, `[a linux fuel against a linux fuel]`, `[a fall]`: no `growth`, the node in `fuel_elsewhere`, no "`fuel_platform` is no longer recorded" row, and the scoreboard's line names "fuel not compared (measured on another system) 1". Red today: the first two are a fuel growth and the label reads as a dropped metric.
- `tests/unit/test_scoreboard.py::test_accept_lets_the_keys_own_system_replace_another_systems_fuel`: an entry of fuel 100 labelled `linux-x86_64`, a darwin run of 200, no growth reason: the accepted entry is fuel 200 with no label. Red today: the lower, 100, is kept.
- `tests/unit/test_accept_from.py::test_a_check_only_linux_ran_takes_linuxs_fuel_when_none_is_of_this_engine`, parametrized `[another engine]` (the group's darwin entry holds fuel under 49.0.0) and `[none recorded]`: accepted with no claim; the group's entry is the record's fuel, `fuel_platform` `linux-x86_64`, `wasmtime` `uv.lock`'s. Red today: `[another engine]` is refused, "a growth, unclaimed: … fuel is no longer recorded"; `[none recorded]` accepts with no fuel.
- `tests/unit/test_accept_from.py::test_linux_first_fuel_keeps_the_lower_and_is_never_a_growth`: the group's entry holds 500 labelled `linux-x86_64` under the current engine; a record of 600 is accepted with no claim and keeps 500; one of 400 keeps 400. Red today: 500 to 600 is an unclaimed growth.
- `tests/unit/test_accept_from.py::test_darwin_fuel_replaces_another_systems_without_a_claim`: a check darwin ran, whose entry holds 100 labelled `linux-x86_64`, recorded at 200 by the macOS shard: accepted with no claim, 200, no label. Red today: an unclaimed growth.
- `tests/unit/test_gather.py::test_a_darwin_record_against_another_systems_fuel_is_neither_red_nor_listed`: `accepted.json`'s entry holds fuel 7 labelled `linux-x86_64`; the macOS record gives 70 and the Linux record 700; the verdict has no red line, no `GROWTH` row and no "records no fuel_platform". Red today: "G5 macos/…: grew …" and "records no fuel_platform".
- `tests/unit/test_plugin.py::test_a_local_run_replaces_fuel_another_system_measured`: after the baseline, `accepted.json`'s `test_ok` entry is given `"fuel_platform": "elsewhere-x"`; a run at fuel 5,000,000 exits 0 and prints "fuel not compared (measured on another system)"; `--accept "x"` records 5,000,000 with no label. Red today: GREW, exit 1.

Unchanged rows that hold the rest, green before and after: `test_accept_from.py::test_darwin_fuel_is_keyed_darwin_and_linux_fuel_is_not_ratcheted` (darwin's fuel of this engine is kept over Linux's), `test_scoreboard.py::test_fuel_is_not_compared_across_wasmtime_versions_or_platforms`, `::test_accept_keeps_the_minimum_metric_unless_growth_is_accepted`, `::test_accept_rebaselines_fuel_on_a_new_wasmtime`, `test_plugin.py::test_fuel_on_another_wasmtime_is_not_compared`, `test_gather.py::test_ten_times_the_fuel_under_the_locked_wasmtime_is_red_through_the_ratchet`, and the two `test_sameness.py` rows of Decision 6.

## Intent

After this specification an engine move costs the ratchet nothing it cannot recover in the same run. A check only Linux runs keeps a fuel of the current engine: darwin's when darwin measured it, Linux's otherwise, labelled so that no one compares it with the other system's. The release-tier ledger is empty again, and no claim clears every upstream suite's growth.

## Design

- `tests/harness/scoreboard.py`: `LABELS = ("wasmtime", "fuel_platform")`; `Ratchet.fuel_elsewhere`; `compare`'s fuel branch (Decision 4) and its "no longer recorded" loop skipping labels; `accept`'s merge (Decision 5); the summary's new part; the module docstring's `accepted.json` shape names the label.
- `tests/harness/accept_from.py`: `_metrics` for a source that is not darwin (Decision 3); the module docstring's last paragraph says which fuel such a check keeps.
- `tests/harness/gather.py`: G5's `want` subtracts `scoreboard.LABELS`.
- The rows of Decision 10.
- `../release-tier-claims.toml` and `../release-tier-claims-history.md` (Decision 7).
- `../progress/README.md`, "Acceptance from CI's record": the sentence "A check only another system ran … keeps darwin's accepted fuel" becomes Decisions 3 to 5 in two sentences; its first list line ("metrics (fuel, bytes) per platform") names the label.
- The news file `../changes/154-the-first-fuel-under-a-new-engine-is-linuxs.md`:

  ```markdown
  ## Changelog

  ### Changed

  - **The judge keeps a fuel for every upstream group across an engine move**: when no fuel darwin measured under the current wasmtime is recorded for a check only Linux ran, the acceptance from CI records Linux's, labelled with the system that measured it, never compared with another system's, and replaced by darwin's when a Mac measures it; the release-tier ledger's block that cleared every upstream suite's dropped fuel after the move to wasmtime 50 is removed.

  ## Package rows

  None.

  ## Claims

  [[claim]]
  spec = "154"
  new = [the ten collected rows of Decision 10, by node id]
  units = 10
  [claim.judge]
  "context/release-tier-claims.toml" = "127's block is removed: the acceptance now records Linux's fuel for a check only Linux ran when none of the current engine is recorded, so an engine move drops no fuel and no claim needs to clear the upstream suites' growth"
  ```

  (the claim block in a `toml` fence in the file itself; `units` the count of collected rows the pull request adds, ten as planned: three, one, two, one, one, one and one).
- The commits, in order: the rows, seen failing; the harness; the ledger and its history; the README paragraph and the news file.

## Scope

In: the above. Out:

- ratcheting Linux fuel against Linux fuel, at any tolerance: Decision 4, until Linux fuel is shown to repeat;
- running a release-tier upstream group on darwin in CI, which would give darwin's fuel directly: a change to the release plan's shards and its time budget, the owner's;
- Windows fuel: the rule is written for "a system other than the key's", so a check only Windows ran would take Windows' fuel by the same rule, but no metered check runs on Windows alone today, and no row is written for it;
- `sameness.py`, which compares records, not the accepted state (Decision 6);
- the roadmap's lines, which the orchestrator writes at the merge.

## Acceptance criteria

1. The ten rows of Decision 10 exist, and each was seen failing on `6bc56eeb`'s harness, named in the pull request with its failing line; the unchanged rows named there stay green.
2. `uv run pytest tests/unit/test_scoreboard.py tests/unit/test_accept_from.py tests/unit/test_gather.py tests/unit/test_plugin.py tests/unit/test_sameness.py tests/unit/test_news.py -q` is green (255 passed on the five files besides `test_gather.py` before the change; that count plus the new rows after), and `uv run pytest tests/lint` is green: no code file names a specification or a `context/` path.
3. Offline replay of 0.1.1's release acceptance, with the record kept in the main tree (`build/land/rel-record/record.json`, read only) and `accepted.json` at `898bc091^`: `accept_from.run_from_record` and `scoreboard.compare`, with no claim, give **0** growth rows (716 before the change, every one "fuel is no longer recorded"), 716 rows labelled `linux-x86_64` in the merged state, and 0 lost and 0 rows not compared, as before. The landing notes give the commands and the counts.
4. `news.ledger_claims(REPO)` returns an empty list and raises nothing (EXECUTED in the landing notes): the ledger is its header alone, and the history's `## 0.1.1` section has no `toml` fence.
5. `tests/checks/test_rules.py::test_the_news_files_have_their_shape` is green with the news file.
6. The pull request's `ci-status` is green, its `GROWTH` list is empty, and its post-merge acceptance carries the ledger's `[claim.judge]` reason and no other.

## What the draft measured

On `6bc56eeb`, in the worktree, 2026-10-28. EXECUTED unless marked.

- **The accepted record.** 1,994 checks; 1,065 metric entries, every one under `darwin-arm64` and every one naming wasmtime 50.0.1; 346 of them hold a fuel. Of 1,116 rows in `tests/checks/test_v1_3_upstream_suites.py`, the metered ones are the 801 `test_upstream_suite` rows: **716 release-tier rows hold a pass count and no fuel**, and the 85 normal-tier rows all hold darwin's fuel under 50.0.1. The other 719 entries without fuel are those 716 and three byte-only rows of `test_v1_1_artifact_set.py`.
- **The 0.1.1 release record** (run 40465516946's `release-record-1`, the copy under the main tree's `build/land/rel-record/`, read only): every one of the 716 rows has its source on `linux-x86_64` and a fuel there; 263 metered rows came from darwin and 799 from Linux.
- **The refusal, replayed.** `accept_from.run_from_record` and `scoreboard.compare` over that record and `accepted.json` at `898bc091^` (the state before 0.1.1's release acceptance), with the accepted judge: **716 growth rows, all "fuel is no longer recorded"**, 0 lost, 0 not compared. This is 127's landing notes' refusal, reproduced offline.
- **Linux fuel between runs.** The gathered records of the pull requests of 131, 132 and 137 (main tree `build/records/`, read only; one artifact, wasmtime 49.0.0): 83 normal-tier upstream rows sourced on Linux, **all equal to the instruction across the three runs**. Against wave 12's dry run of 2026-10-22 (same artifact, an older judge), 26 of the 83 differ and 10 by more than 1e-4 (up to 9.7e-4, `tomli-w-smoke`); the judge moved between them, so this is not a clean repeat (INFERRED).
- **Linux against darwin, one engine.** Run 40465516946's Linux fuel against the accepted darwin fuel, both under 50.0.1, on the 83 rows both measured: none equal, **51 past 1e-4**, from −0.99% (`cpython-b`) to +0.73% (`cpython-archives`).
- **The unit rows.** `uv run pytest tests/unit/test_scoreboard.py tests/unit/test_accept_from.py tests/unit/test_sameness.py tests/unit/test_plugin.py tests/unit/test_news.py -q -p no:cacheprovider`: **255 passed** in 25 s (`build/154/unit-before.txt`).

## Landing notes

Not yet built.
