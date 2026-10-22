# 063 — The release judges in parallel shards

- **Status:** **landed 2026-10-19** (accepted on `9a446e0` as `4f89510`, history line 77; the build review, `../reviews/063-the-release-judges-in-parallel-shards-build-2026-10-18.md`, said it lands once F1 to F4 and F8, and its final branch dry run `39234703116` passed every job on all three systems, `gather` included). Before landing: built 2026-10-18; revised against its build review; the final branch dry run
  (the build review's F2) passed every job on all three systems, `gather` included, on
  2026-10-19 (run `39205611721`, the Landing notes); ready for the lane. The build review
  (in the session's scratchpad `063-buildreview/`; copied to `../reviews/` by the lane) said "lands
  once F1, F2, F3, F4 and F8"; the seven departures were accepted. F1, F3, F6, F7 and F8 are fixed,
  F5 is answered, F4 is spec 076's, and F2 waits on 076 (the Disposition of the build review).
  Rebased onto main `7307f6f` (046, 070, the 0.1.0a6 release, questions 100 to 102), to be rebased
  again after 068 lands. Confirmed for build 2026-10-18 (N1 and N2 written in at build). The
  pre-build review
  (`build/reviews-evidence/063-spec/review/063-the-release-judges-in-parallel-shards-spec-2026-10-18.md`
  in the main tree, git-ignored; copied to `../reviews/` by the lane) said "ready once F1 to F4 are
  written in"; its Confirmation (`…-spec-2026-10-18-confirmation.md` beside it) confirmed `8725120`
  with two Low notes, N1 and N2, written in at build. The owner answered questions 98 and 99 the
  same day (Decisions 18 and 15). Drafted on `spec/063-the-release-judges-in-parallel-shards` from
  main `ff5c568`.
  Amended 2026-10-18 by spec 065: `python` is a `suite`; its five groups sit in four Linux upstream
  shards, and `cpython-fs` also in `upstream-macos` and `upstream-windows`; `fetch.py --shard`
  fetches the trees of each family a shard runs.
  2026-10-20: matplotlib, contourpy, Pillow, kiwisolver, lxml and regex are `suite`s since spec
  066, in twelve new Linux shards (`upstream-plot-a` to `-l`).
- **Owner:** Clay Gendron
- **Kind:** build-class: the release workflow; a judge change. It builds after spec 057 lands.
  - It changes `.github/workflows/release.yml`: the build job judges only its own `build` shard;
    three new jobs, `judge-macos`, `judge-linux` and `judge-windows`, run the other shards; a new
    job, `gather`, merges their records; `verify` keeps only the installed-wheel check; `attest`
    and `publish` need `gather`.
  - It changes the judge: `tests/harness/plugin.py` (the `--shard` option), two new harness
    modules (`tests/harness/shards.py`, `tests/harness/gather.py`), `tests/harness/scan.py` (one
    new scan, two of spec 057's rules and one of spec 009's widened), `tests/upstream/fetch.py`
    (a `--shard` mode that fetches the two source trees), two new data files
    (`tests/release_shards.toml`, `tests/upstream/packages.toml`), `tests/checks/test_rules.py`
    and new unit tests.
  - It moves `tests/unit/test_pins.py` into the `build` shard's files (the review's F6); the
    file itself does not change.
  - It changes `README.md` (*Releasing*), `CHANGELOG.md`, `AGENTS.md` (one rule),
    `context/progress/README.md` ("Before a release"), `context/roadmap.md` (three reserved
    numbers, Decision 15) and adds one amendment line to spec 050.
  - It changes no artifact, no pin, no recipe that makes bytes, no `src/` file, not the guest,
    and not `uv run pytest` without `--shard`: the lane's judge is the same.
- **Depends on:** 057 (the release ties what it signs to what it built: downloads by id, guards,
  the check step, per-job permissions, two rebuild jobs; in build review, lands first). Also on
  004 (the release workflow), 009 (`attest` and its rules), 050 and 051 (the upstream suites),
  052 (the parallel judge: worker records, `sameness.py`, the serial verdict of record), 059
  (native rebuilds) and 062 (the history in volumes, `systems_that_passed`). All but 057 have
  landed.
- **Research it stands on:** `../research/2026-10-18-the-release-judges-in-parallel-shards.md`
  (called "the memo"). It holds today's release timeline and where the judge's time goes on a CI
  runner (EXECUTED, two runs' job records and logs), each upstream group run alone with its fuel
  and passes against `accepted.json` (EXECUTED), the fuel cost of staging one tree instead of two
  (EXECUTED), GitHub's limits (READ), the shard plan and the expected wall time (INFERRED), the
  gather's design and the risks.

## The problem

The owner's words, 2026-10-18 (paraphrased closely): the release rebuilds from the pins on three
hosts, then verifies with the judge on Ubuntu, Windows and macOS. The judge should be split so its
pieces run in parallel. Every package pulled into wasi-python should run its own test suite in the
release, numpy, pandas, scipy and the rest, as separate parallel jobs beside our own judge. The
goal is a release that moves quicker without giving up the suite's reliability.

Today (the memo, section 1):

- **The release never runs the upstream suites.** On the newest dry run, 31 checks were blocked by
  `upstream kit`, which is not a protected need, so the run stayed green. `context/progress/README.md`
  says, under "Before a release" (recorded, not yet a rule), that someone should confirm by hand
  that the history holds an accepted run of them on the release's artifact hash. Nobody has to.
- **Only one host runs the judge.** The build job runs `uv run pytest` on macOS, serially, after
  the build: 11.7 of the run's 33.4 minutes, all on the critical path. The three `verify` jobs run
  a named subset (four check files, three unit files). The judge's tooling tests have never run on
  Linux or Windows.
- **`three systems` is never established by the release.** Its check reads the lane's history,
  which holds only darwin-arm64 runs, so it is blocked everywhere.

## Decisions

1. **A shard is a named selection of the judge's own checks; nothing else is new.** `uv run pytest
   --shard=<name>` reads the plan (always the `=` form: amended at build, Landing notes), `tests/release_shards.toml`, and deselects every collected item
   outside the shard through pytest's own `pytest_deselected` hook, which the plugin already
   records. So node ids, records, gaps, needs and the ratchet are exactly the judge's: a
   deselected goal check is `deselected` in the record, as under `-m`. Without `--shard` the judge
   is unchanged, and the lane never passes it (*Reason:* the owner's "no new test framework"; the
   lane's judge stays as it is, Scope).
   - `--shard` refuses, before anything runs, a name the plan does not hold, and any of `-n`,
     `--accept`, `--retire` or a node-id argument with it: a shard is a serial, unaccepted,
     whole-plan selection (Decision 4).
   - A shard that selects no item at all ends red: `RED: shard <name> selected nothing` (today
     such a run exits 5 with no reason, the review, EXECUTED).
   - The plugin records every goal check's area before it deselects, so a deselected check is
     `deselected`, never `absent` (the review ran the same deselection through `-k`: 397 goal
     checks recorded, 377 `deselected`, the ratchet green, EXECUTED).
   - The record's `meta` gains `shard` (the name, or null). Under `--shard` only, it also gains
     `units`: the count and a SHA-256 digest of the sorted node ids of the unit tests that ran
     (the review's F6). Without `--shard` both are absent but `shard: null`, so the lane's record
     is unchanged; `sameness` never compares `meta`.

2. **What a shard can select.** Each `[shard.<name>]` has `systems` and one of three selections:
   - `files`: every item of the named test files, except the upstream file's group checks;
   - `groups`: named upstream groups, each with its suite check, its classes' checks (the map
     `plugin.upstream_scopes` already keeps for spec 052) and every trap whose file lies under one
     of the group's paths (the rule `upstream.group_spec` already uses);
   - `rest = true`: every collected item that no shard of the whole plan takes by `files` or
     `groups`. One shard is `rest`. So a new test file is never outside the release, and an
     upstream group check never falls into `rest` (the plan holds every group, rule c below).

   **The plan's rules**, a judge check that needs no artifacts (`shards.plan_errors`):
   (a) every `files` entry is a tracked test file, and no file is in two shards' `files`;
   (b) exactly one shard is `rest`, and at least one tracked test file is in no `files` list, so it
   is not empty; (c) every group of `upstream.load_all()` is in exactly one shard whose systems
   include `linux`, and every `groups` name is a group; (d) `systems` are from `macos`, `linux`,
   `windows` and `build`; `build` belongs to the shard `build` alone, which selects by `files`;
   (e) every `files` shard but `build` runs on all of `macos`, `linux` and `windows` (the owner's
   "our own judge on all three"), and the `rest` shard on `macos` and `linux` at least (amended at
   build under Decision 18: the rules and the judge's own tooling run where the lane and the
   rebuild hosts run; the Landing notes give the branch dry run's evidence); (f) on one system no
   group is in two shards, so with (a) and (c) no item runs twice on one system; (g) every product
   check file (each `tests/checks/` file but `test_rules.py`, the upstream file and the `build`
   shard's) and every runner unit file (`tests/test_api.py`, `tests/unit/test_runner_*.py`,
   `test_cli.py`, `test_tools.py`, `test_async_tools.py`, `test_guest_tools.py`) is in a `files`
   shard that runs on all three systems, so `rest` holds only the rules and the judge's own tooling
   and a new product file cannot fall off Windows by default (the build review's F1); (h) the
   `build` shard alone may also name single checks by node id (`nodes`), each once, each a check
   its tracked file defines; a named check runs there only (the confirmation's D1).

3. **The plan, from measurements** (the memo, sections 1, 2 and 5; seconds are a CI macOS runner's,
   measured for files, estimated for groups).

   | shard | selection | systems | guest time |
   |---|---|---|---|
   | `build` | `tests/checks/test_v1_5_rebuild_from_pins.py`, `tests/unit/test_pins.py` | build | 46 s |
   | `own-embedding` | `tests/checks/test_v1_4_embedding.py` | macos, linux, windows | 221 s |
   | `own-guest` | `tests/checks/test_v1_2_hostile_guest.py`, `test_v1_3_data_stack.py`, `test_v1_1_artifact_set.py`, `test_v1_3_the_zips_directory.py`, `test_v1_3_matplotlib.py`, `test_v1_3_lxml.py` (added at the rebase onto 046), `test_v1_3_regex.py` and `test_v1_4_sessions.py` (added at the rebase onto 047 and 055), `test_v1_2_portable_and_sealed.py`, `test_v1_4_public_api.py`, `tests/unit/test_runner_mounts.py`, `tests/unit/test_runner_grants.py` | macos, linux, windows | about 175 s |
   | `own-runner` | the runner's own unit files (`tests/test_api.py`, `test_cli.py`, `test_tools.py`, `test_async_tools.py`, `test_guest_tools.py`, the other `test_runner_*.py`, `test_runner_sessions.py` among them since 055) | macos, linux, windows | added at build |
   | `own-rest` | `rest = true` | macos, linux (amended at build) | about 180 s |
   | `upstream-groupby` | pandas-groupby | linux | 120 to 200 s |
   | `upstream-frame` | pandas-frame | linux | 85 to 145 s |
   | `upstream-numpy-a` | numpy-core, numpy-lib | linux | 80 to 135 s |
   | `upstream-numpy-b` | numpy-others, pandas-reshape | linux | 60 to 105 s |
   | `upstream-pandas-small` | pandas-io-parser, pandas-io-formats, pandas-tslibs, pandas-libs, pandas-internals | linux | 50 to 80 s |
   | `upstream-macos` | numpy-lib | macos | 35 to 55 s |
   | `upstream-windows` | pandas-io-parser | windows | 30 to 45 s |

   - *Our own judge on all three systems, in three shards.* The embedding file is 36% of the judge
     and the floor of any split by file; the other two are balanced against it. Splitting a file
     would need a selection by node, which a new parametrization would silently move.
   - *The package suites in full on Linux, in five shards.* Eleven jobs would spend eleven of
     Free's twenty slots and eleven fixed minutes; five keep every shard under the embedding floor.
   - *One group each on macOS and on Windows.* macOS is where the lane accepts, so its fuel is
     compared with the lane's to 1e-4; numpy-lib is cheap and does file I/O. Windows is where the
     host's file system differs most (spec 058); pandas-io-parser reads files, compressed files and
     encodings through the guest's WASI calls. Every group already runs on darwin-arm64 at every
     landing, and Decision 11 ties the release to that run.
   - *`tests/unit/test_pins.py` runs on the build host.* Its zlib round trip needs the pinned zlib
     tarball, which only the build host has; elsewhere it skips, and a unit skip is not ratcheted
     (the review's F6, EXECUTED). So the file is in `build`.
   - *Measured against the real collection* (the review, EXECUTED, `plan_counts.txt`): `build` 27
     goal checks and 0 unit tests (before `test_pins.py` moves in), `own-embedding` 151 and 0,
     `own-guest` 162 and 94, `own-rest` 26 and 1,103, each upstream shard 2 to 10 and 0. No item is
     in two shards on any system; the union is the whole collection of 1,594 items.
   - *Linux arm64 runs no shard.* The owner named three systems; ubuntu-24.04-arm rebuilds only.
   - *Changing the plan is a judge change*: the file is judged (it is under `tests/`), and a
     package spec that adds groups adds them to a shard, or rule (c) fails.

4. **Shards run serially.** No `-n` in a shard. *Reasons:* the verdict of record stays serial until
   parallel runs have their record (spec 052, Decision 11); the runners have 3 or 4 cores and macOS
   7 GB, where spec 052 measured 9 GiB at `-n 4`; and the jobs are the parallelism.

5. **An upstream shard fetches the kit and every package's tree, each verified.** Every shard runs
   `uv run python tests/upstream/fetch.py --shard "$SHARD"`. For a shard without `groups` it prints
   `nothing to fetch` and exits 0. For one with `groups` it:
   - fetches the kit as `fetch.py` does today (SHA-256 per `kit.txt` line, rename after the match);
   - fetches each upstream package's source tarball to `downloads/<name>` (where
     `pins.source_pair` looks, and git ignores): the URL from its `get` line in
     `scripts/00_download.sh` (one place for URLs, spec 003, Decision 1), the hash from
     `downloads/SHA256SUMS`, to a `.part` name, renamed only after the match; a name with no `get`
     line or no pin exits 1 naming it;
   - unpacks each into `build/` with `tarfile`'s `data` filter (an absolute name, a `..`, a link
     out of the tree or a device is refused), refuses a tree that is already there, and runs
     `sh scripts/steps/apply_patches.sh build/<top> recipes/patches/<top>`, the same applier the
     build runs.
   - *Why every tree:* numpy-lib with only numpy's tree staged moved its fuel by 3.9e-5, 500 times
     the residual (the memo, section 2, EXECUTED): the stage must be the lane's.
   - *Why not `scripts/00_download.sh`:* it fetches the host key's 35 pins and has no key for
     Windows (READ).
   - The judge then ties the tests to the artifact as it does on the lane: `tie_errors` (the
     tarball's hash is MANIFEST's pin; every patch's hash is MANIFEST's), members only.

6. **The build job judges only what needs the build host.** Its step "The judge" becomes "The
   build shard": `uv run pytest -p no:cacheprovider --shard=build --progress-latest
   "$RUNNER_TEMP/record/latest.json"`. The `build` shard is the v1.5 file: its checks need the
   build tree, its compile records and every component's source tree, which only the build host
   has, and `tests/unit/test_pins.py` needs the zlib tarball. The build job hashes and uploads that
   record like any shard, and hands on `record-id` and `record-sha256`. It also hands on
   `wasm-sha256`, the SHA-256 of `build/artifacts/python.wasm`, computed on the build's runner
   before the `release-assets` upload, as `sums-sha256` is (the review's F1): the gather compares
   records with it and never holds the assets (Decision 9). The zero-patch step stays as it is. *Reason:* the whole judge off the critical
   path, about 10 minutes (the memo, section 5).

7. **One judge job per system, a matrix over that system's shards.** `judge-macos` (macos-15),
   `judge-linux` (ubuntu-24.04), `judge-windows` (windows-2025, `shell: bash`). Each needs `build`,
   has `permissions: contents: read`, `timeout-minutes: 30`, `fail-fast: false`, no job-level `if:`
   or `continue-on-error:`. The three are the same text once the runner's name and the shard list
   are set aside. Each leg's steps, in order:
   1. checkout (`fetch-depth: 0`: `own-rest` holds the rules that need the git history;
      `persist-credentials: false`); setup-uv (`enable-cache: false`);
   2. spec 057's guard, its download of `release-assets` by id and its check step, unchanged;
   3. unpack the set into `$RUNNER_TEMP/set` (`WASI_PYTHON_ARTIFACTS`), and copy the wheel into
      `dist/`, so `wheel` is met in every shard (today it is blocked on verify);
   4. `fetch.py --shard` (Decision 5);
   5. the shard: `uv run pytest -p no:cacheprovider --shard="$SHARD" --progress-latest
      "$RUNNER_TEMP/record/latest.json"`, with `SHARD: ${{ matrix.shard }}` in `env:`;
   6. the record's SHA-256 (`id: sha`), of exactly `$RUNNER_TEMP/record/latest.json`; its upload
      (`id: record`, name `record-<system>-<shard>`, that same path, `if-no-files-found: error`);
      then one step (`id: out`) whose `env:` is exactly `SHARD: ${{ matrix.shard }}`,
      `RECORD_ID: ${{ steps.record.outputs.artifact-id }}` and
      `RECORD_SHA256: ${{ steps.sha.outputs.sha256 }}`, and whose `run:` is the one fixed text
      that writes `$SHARD-id=$RECORD_ID` and `$SHARD-sha256=$RECORD_SHA256` to `GITHUB_OUTPUT`
      (the review's F7: the indirection a matrix needs is pinned by the scan, rule 4);
   7. on failure only, the record and the scoreboard's log as a diagnostic artifact named
      `record-<system>-<shard>-failed-${{ github.run_attempt }}`, so a re-run's failure does not
      collide with the first.

   The job's `outputs:` maps, for every shard of its system, `<shard>-id` and `<shard>-sha256`
   from `steps.out`. GitHub combines a matrix's outputs when each leg writes its own names (READ,
   *Workflow syntax*, `jobs.<job_id>.outputs`, its example of one output per leg).
   - *Why a matrix is safe here, when spec 057 made the rebuilds two jobs.* 057's Decision 4 keeps
     one host's inputs from casting another host's vote. That holds: macOS, Linux and Windows are
     three jobs with their own outputs. Inside one system's job the legs share every host-side
     input: the runner image, `uv.lock`'s wheels for that platform, the same code. The upstream
     legs add only data (the kit runs in the guest; the tarballs are unpacked, not run). A leg that
     could write another leg's output could forge its own record in place as well, so per-leg
     names give nothing away (the memo, section 6, INFERRED). Seventeen separate jobs would buy
     nothing and triple the workflow.

8. **Each shard runs the ratchet against the lane's acceptance.** A shard reads the checkout's
   `context/progress/accepted.json`, as the build job's judge does today ("lost 0 · absent 0 · …
   · grew 0", the memo, section 1), and writes nothing there: it never passes `--accept`, and its
   only override is `--progress-latest` to a path under `$RUNNER_TEMP`. So a lost pass, a fall in
   `passes`, fuel growth on darwin-arm64 or a protected need that blocks an accepted pass makes the
   shard red on its own, before the gather.

9. **The gather decides, from hashed records, and writes no history.** A job `gather` (ubuntu-24.04,
   `contents: read` for its checkout alone, `timeout-minutes: 15`) needs `build` and the three
   judge jobs. **It never downloads `release-assets`** (the review's F1): the release's
   `python.wasm` hash reaches it as the build job's `wasm-sha256` output, which only the build job
   can set, as `sums-sha256` is. So 057's rules 7, 8, 9 and 16 do not apply to it, and rule 16
   stands unwidened. It guards every record id and `wasm-sha256` in one step (a `for` loop with
   057's `case`, rule 10's second form; the hash tested as 64 lower-case hex), downloads the build
   job's record by `record-id` into `records/build/`, and each judge job's records by that job's
   ids, comma-separated, one download per job into `records/<job>/`, each with
   `digest-mismatch: error`. Nothing under `records/` is run, only parsed as JSON. Then
   `uv run python tests/harness/gather.py --records records`, with `WASM_SHA256` and every
   handed-on record SHA-256 bound in `env:` as `RECORD_<SYSTEM>_<SHARD>` (upper case, `-` as `_`).
   It is red, naming each reason, unless:
   - **G1, every record, and only those, one to one** (the review's F6). The handed-on record
     hashes are all distinct and none is empty; each plan shard of each system, and `build`, has
     exactly one file, under its own job's folder, whose SHA-256 is its handed-on value; no other
     file is there. G1 is the real closure: the pinned `download-artifact` only warns on an id it
     cannot find in a list, and puts a lone artifact directly in its path (READ, the review, on
     its `download-artifact.ts`).
   - **G2, each record says what it is.** `meta.shard` is the shard its value was handed on for;
     `meta.platform` starts with the system's name (`darwin`, `linux`, `win32`); `meta.commit` is
     the gather's `HEAD`; `meta.artifact` is `WASM_SHA256`; `meta.judge.hash` is the judge hash the
     gather computes from its own checkout; `dirty` is false; `foreign` and `partial` are empty;
     `workers` is 0; `overrides` is exactly one `--progress-latest …`.
   - **G3, each shard ran exactly its share, and the shares are the whole judge.** The gather
     collects once at its commit, in process (`pytest.main(["--collect-only", "-q", …])` with a
     small collector plugin object that reads each item's `goal` marker through
     `plugin.area_of`, never guessing from the path; no artifacts are needed: the collection is
     1,594 items with or without the set, the review, EXECUTED). It applies the plan
     (`shards.select`). Then:
     - every record holds the same collected goal checks (`checks` with `deselected`), equal to
       the gather's;
     - a record's run checks (not `deselected`) are exactly its shard's goal checks, and its
       `meta.units` count and digest are exactly its shard's unit tests'. **Each count equals its
       share, which may be zero** (`build` and every upstream shard run no unit test;
       `own-embedding` none either); the shard's selection as a whole, goal checks and unit tests
       together, is not empty (the review's F2);
     - every collected goal check is run (not `deselected`) in at least one record, and every
       collected unit test is in at least one shard's share: a fault of `shards.select` that drops
       an item from every share is red here, not only for accepted passes (the review's F6).
   - **G4, nothing failed.** No record holds `fail` or `unrun`; a `gap` is in `tests/known_gaps.toml`
     at this commit; a `blocked` check names `oracle`, `prior-art clones`, `three systems` or
     `descriptor limit` (a host capability Windows lacks; added at build) and nothing else.
     (`wasmtime cli` is not allowed: 071's CLI check is in its own file in the `build` shard, on
     the host that unpacked the CLI; the confirmation's D1.) Each record's
     `suite` has no failed unit test: `total` equals `passed` plus `skipped` (the build review's F6). (An upstream group skipped for want of its kit is red here and only here:
     `upstream kit` is not a protected need, so the shard alone would stay green.)
     *Amended by spec 085:* G1, G2 and G7 also check the set's own `SHA256SUMS` hash
     (`SET_SUMS_SHA256`), and G2 each record's `meta.wasmtime` against `uv.lock`; G4 allows a
     block only by a need the check's own body names, on a system that lacks it, and requires each
     record's unit tally to equal its share; G5 requires every metric name the lane accepted.
   - **G5, the lane's acceptance holds.** `scoreboard.compare` of each record against
     `accepted.json` finds no lost, absent, fewer, grown or blocked-protected check; every accepted
     pass or gap ran (pass or gap) in at least one record, unless it is blocked by one of G4's three
     needs; and each upstream group's `passes` metric and `passed_digest` fact are equal in every
     record that ran it and equal to `accepted.json`'s darwin-arm64 `passes`.
   - **G6, three systems.** `history.PROBE` passed in a darwin, a linux and a win32 record. The
     gather prints `three systems: darwin linux win32 on <artifact>`.
   - **G7, `python.wasm` is the lane's accepted artifact** (the review's F4). The newest history
     line (`history.lines`) has `artifact` equal to `WASM_SHA256`, `dirty` false and
     `partial_reason` null. A history line records only `python.wasm`'s hash, so G7 ties that file
     alone; the snapshot, the stdlib zip, MANIFEST and the licences are judged by the release's own
     shards, on the release's own bytes. **On a pushed tag only**, the release's judge hash also
     equals `accepted.json`'s `judge.hash`: the release runs the judge the lane accepted (today
     HEAD's judge hash `c7010af…` equals it, the review, EXECUTED). A dry run (a branch's under
     Decision 18, or main's) may carry a changed judge, so the clause does not apply there; the
     gather reads the event from `GITHUB_EVENT_NAME` and `GITHUB_REF_TYPE` as the runner sets
     them (amended at build: a step cannot override a `GITHUB_*` variable, so they are not bound).

   **The merged record** (the review's F8). For each goal check, its status is the worst across
   the records that ran it, in the order `fail` > `unrun` > `blocked` > `gap` > `pass` >
   `deselected` (`deselected` ranks lowest, so a check run anywhere is never shown as deselected);
   its metrics are the darwin record's when one ran it, else the linux record's, else the only
   record's (the Confirmation's N2); `suite` is kept
   per system (`{"darwin": …, "linux": …, "win32": …}`), since skips differ by system. The gather
   prints `scoreboard.render` over it in the log and the job summary, writes
   `release-record/record.json`, and uploads it (`if: always()`; not a guard, download or check
   step). It writes nothing under `context/progress/` and accepts nothing: only the lane accepts
   (constitution §5.7; AGENTS.md rule 6a). *Reason:* this is spec 052's controller merge across
   machines, and spec 057's tie of every reader to what was made.

10. **Three systems are proven in the release, and the history stays the lane's.** G6 is the
    `three systems` claim on the release's own bytes. The need `three systems` and its check keep
    reading the lane's history, unchanged, and stay blocked locally as today. *Reason:* a history
    line is the lane's acceptance of a run on its own machine, chained and reviewed; a CI record
    entering it would make CI an acceptor. The release record is evidence the release notes can
    link, not accepted state.

11. **The release's `python.wasm` is the lane's accepted artifact (G7).** Every landing that
    changes the set is accepted, and the build reproduces the set from the pins on any host (specs
    012, 040, 059), so a release of main's commit meets G7 (INFERRED; the a5 tag run and the latest
    dry run each built the newest line's `python.wasm`, the review, READ). The other files of the
    set are not in the history; the release's shards judge them on the release's own bytes. G7, G5
    and the five Linux upstream shards replace "Before a release": the hand check becomes a rule,
    and the suites also run on the release's own runners.

12. **`verify` keeps only the installed wheel.** Its guard, download and check stay (057), then its
    one step "The wheel, installed fresh, runs a program in one call", unchanged. The unpack, the
    subset of the judge and the blocked-needs assertion go: the shards run all of it and more, and
    G4 is the stricter form of the assertion. `attest` still needs `verify` (spec 009's rule).

13. **`attest` and `publish` need `gather`.** `attest: needs [build, verify, same-bytes, gather]`;
    `publish: needs [build, verify, same-bytes, attest, gather]`. `pypi` needs `publish`, as today.
    A dry run runs everything up to `gather`, as it runs `verify` today.

14. **Recovery and flakiness.** No retry inside a shard (no rerun plugin; `--max-worker-restart`
    stays refused). A shard that fails stops the release. The README's recovery holds: re-run the
    failed jobs of the same run (spec 057, Decision 8); if a re-run stops at a guard, re-run all
    jobs. The release notes name any shard that was re-run and the check that failed. A check that
    fails once and passes on a re-run is a defect, recorded and fixed by its own change, never
    allowed for.

15. **Every package names its own suite, and the judge checks it.** `tests/upstream/packages.toml`
    has one `[package.<name>]` for each component compiled or linked into the artifact (the
    review's F5): every name in `paths.PACKAGES`, every name in `needs.SOURCE_COMPONENTS` (mapped:
    `cpython` is `python`, `sqlite` is `sqlite-autoconf`), and the linked runtimes `wasi-libc` and
    `llvm-runtimes` (libc++, libc++abi, libunwind, compiler-rt), held in a fixed tuple in
    `shards.py`. Each has a `kind`:
    - `suite`: the package has `tests/upstream/<name>.toml` with at least one group, and its name
      is in `upstream.PACKAGES` (numpy, pandas);
    - `via`: its own suite cannot run here, and `via` names what reaches it: a `suite` entry, a
      `later` entry (amended at build: matplotlib, which reaches five C libraries, is `later`),
      `python`, or a stdlib module from the file's fixed `stdlib_modules` list (`zlib`, `bz2`,
      `lzma` and `sqlite3` today; the list is judged, so adding to it is a judge change). zlib, bzip2, xz and sqlite-autoconf
      are `via` their stdlib modules; freetype, harfbuzz, sheenbidi, libraqm and qhull are `via
      matplotlib`; `wasi-libc` and `llvm-runtimes` are `via python` (every binary links them; the
      whole judge and every suite run on them);
    - `build-only`: used only to compile another package, with a `reason` (pybind11, cppy);
    - `later`: a `reason` and a `closes_with` that names a specification by number: either
      `context/specifications/<NNN>-*.md` exists, or `context/roadmap.md` reserves that number on
      a line beginning `Reserved:`. 063 reserves three, named here:
      - **065, CPython's own tests in the release**: `python`. The owner, answering question 99:
        "Gate 0.1.0 regardless". So 065 makes CPython's suite release shards before 0.1.0;
      - **066, matplotlib's, pillow's and kiwisolver's own tests in the release**: matplotlib,
        pillow, kiwisolver (their sdists are already pinned);
      - **067, the pure-Python packages' own tests in the release**: fonttools, pyparsing, cycler,
        packaging, python-dateutil, six, tzdata (pinned as wheels, which carry no tests; 067 pins
        their sdists as data).
      If another document takes one of those numbers first, the builder takes the next free ones
      and says so.

    The check `test_every_package_names_its_own_suite` fails on a component with no entry, an entry
    for no component, a `suite` with no groups, a `via` naming anything but a `suite` or `later`
    entry, `python` or a listed stdlib module, a `later` whose closer is not a specification or a reserved
    number, or an unknown `kind`. AGENTS.md gains one rule (Design). *Reason:* a judge check is
    the only one of the lane's three options that cannot be forgotten: a package spec fails the
    judge until it adds its suite to a shard or says why not. A spec 046 (lxml) or any other
    package that lands before 063 is built gets its entry from 063's builder.

16. **Spec 057's rules, widened where 063 needs it, and one new scan.**
    - 057's rule 4: `artifact-ids:` is one `${{ needs.<job>.outputs.<name> }}`, or several joined by
      commas, all of one job. Its rule 10: the guard binds and tests each of them. Its rule 14's
      table gains `judge-macos`, `judge-linux`, `judge-windows` and `gather`, each `contents: read`.
      Its rules 7 to 9 and 13 reach the judge jobs as written (they hold the build's files).
    - **057's rule 16 stands, unwidened** (the review's F1): a job that holds the build's files
      downloads nothing else, `same-bytes` alone exempt. The judge jobs download only
      `release-assets`; the gather holds no assets (Decision 9). A gather that downloads
      `release-assets` fails rule 16 and 063's scan alike (acceptance 5).
    - Spec 009's `release_attestation_errors`: `attest` needs `build`, `verify` and `gather`, and
      `publish` needs `gather`.
    - A new `scan.release_shard_errors(text, plan)`, Design.

17. **It fits the free plan's limits.** The repository is public and its runners standard, so the
    minutes cost nothing (READ, GitHub's billing page; EXECUTED, `gh repo view`). At the fan-out the
    plan holds 5 macOS jobs (Free's macOS limit) and 19 to 21 jobs in all against Free's 20; at most
    a job or two waits about a minute for a `verify` job to end (the memo, section 5). The account's
    plan is not visible to the agent; on Pro nothing waits.

18. **Its place in the queue, and the branch's dry run.** Build-class: it changes the release
    workflow (it reads `scripts/00_download.sh` and runs `apply_patches.sh`, and changes neither).
    It builds after 057 lands, on 057's workflow.
    - **0.1.0a6 may be tagged before 063 lands** (the review's F3). It waits on 057, not on 063.
    - **The branch's dry run (question 98, answered yes).** The owner, 2026-10-18: "Yes, and we
      should also change the way we push to github: push changes as a branch, create a PR to main
      that runs the tests." At build time, once the builder's local work is green, the builder
      pushes `spec/063-the-release-judges-in-parallel-shards` to GitHub and dispatches `release.yml`
      on it (`gh workflow run release.yml --ref spec/063-…`). A dispatched run is a dry run: it never
      signs or publishes (spec 004). The builder fixes what Linux and Windows find, on the branch,
      and dispatches again until every job passes; each run is linked in the landing notes. The
      branch is deleted from GitHub after landing. So Linux and Windows failures are fixed before
      landing, and the lane's dry run on main confirms.
    - **What only a dry run proves** (the review's F3 and F9). Each fails closed:
      - whether GitHub keeps each leg's own output names when other legs leave them empty (a lost id
        fails the gather's guard);
      - whether `upstream-macos` stays within 1e-4 of the lane's fuel on a CI macOS runner (growth
        fails the shard);
      - the unpack, the patch applier (`git apply` under `env -i` in Git Bash) and the staging on
        Windows (a failure fails the fetch or the shard);
      - the judge's tooling tests on Linux and Windows: `own-rest`'s 1,103 unit tests, of which
        `test_build_scripts`, `test_patches`, `test_landing_lane`, `test_build_progress`,
        `test_several_cores` and `test_clang_emulated` hold 231 that start shells, git and xdist
        workers (a failure fails the shard);
      - that the collection is the same on Windows (a difference fails G3);
      - the wall time, the queue for slots, and what a re-run of one matrix leg keeps.
    - **A goal check that fails on one system only** is fixed, or is given a real need in
      `needs.VOCABULARY` (a vocabulary change, reviewed). It is never skipped without a need: the
      plugin turns a goal check's skip whose reason names no need into a failure (`plugin._judge`).
      A unit test may use the judge's existing `skipif(not POSIX, reason=…)` pattern, with its
      reason. Removing a system from a shard's `systems` is a judge change with its reason in the
      plan file, and rule (e) needs the same amendment, so it cannot happen quietly. Each is a
      reviewed change on the branch before landing.

19. **Risks the build carries** (the review's F9, and the memo's section 7).
    - **Re-runs.** GitHub documents that a re-run of failed jobs reuses successful jobs' outputs
      (READ, the review); it says nothing about single matrix legs. A lost id fails the gather's
      guard; the recovery is to re-run all jobs. A cost, not an integrity risk.
    - **Wall time.** 18 to 22 minutes is the estimate on a normal day. `own-rest` on Windows is the
      unmeasured leg: about 135 s of process- and git-heavy tests on macOS could take two to three
      times as long there; and runners differ two to one between days, so the build alone can reach
      24 minutes. Acceptances 10 and 11 record the real numbers.
    - **The `three systems` check stays blocked.** It reads only the lane's darwin history; G6
      proves the claim in the release instead. How v1's goal counts that check is a follow-up's
      to decide; 063 leaves it as it is.
    - **New inputs on CI runners** (the kit, two tarballs, all pinned, on `contents: read`
      runners). The next release's threat-model review (constitution §5.6) sees these jobs.

## Intent

- The release runs every upstream group on its own bytes, on its own runners, every time.
- Every product check and the runner's own tests run on macOS, Linux and Windows, and the rules
  and the judge's own tooling on macOS and Linux, in parallel, from records that are hashed,
  handed on by id, and tied to the release's bytes, the commit and the judge.
- One job decides: it requires every shard, exactly its share, nothing failed, the lane's
  acceptance, three systems, and the lane's acceptance on the release's own `python.wasm`.
- The release takes about 20 minutes instead of 33 (the memo, section 5, INFERRED).
- A new package cannot land without its suite in the release or a written reason.

## Design

```
tests/release_shards.toml        the plan (Decision 3): [shard.<name>] systems, files | groups | rest
tests/upstream/packages.toml     one entry per package and CPython (Decision 15)
tests/harness/shards.py
  load(path) -> Plan
  select(nodeids, plan, scopes, traps) -> {shard: [nodeids]}       pure; Decision 2
  plan_errors(plan, tracked_test_files, groups) -> [str]           rules (a) to (f)
  package_errors(entries, components, upstream_configs, repo) -> [str]   Decision 15
  LINKED_RUNTIMES = ("wasi-libc", "llvm-runtimes"); the cpython/python, sqlite/sqlite-autoconf map
tests/harness/plugin.py          --shard NAME: refusals; areas recorded, then deselection in
                                 pytest_collection_modifyitems; "selected nothing" red; meta.shard,
                                 and meta.units under --shard only
tests/harness/gather.py          gather(records, handed_on, wasm_sha256, collection, plan, accepted,
                                 history_lines, judge_hash, head, tag) -> (merged, red lines); a CLI
                                 that collects in process with a collector reading `goal` markers
tests/upstream/fetch.py          --shard NAME: the kit and every tree for a shard with groups (Decision 5)
tests/harness/scan.py
  release_shard_errors(text, plan)       the workflow against the plan (below)
  release_binding_errors                 057's rules 4, 10 and 14 widened; rule 16 unchanged (Decision 16)
  release_attestation_errors             attest and publish need gather
.github/workflows/release.yml    build: the build shard; judge-macos, judge-linux, judge-windows;
                                 gather; verify slimmed; attest and publish need gather
README.md (Releasing), CHANGELOG.md, AGENTS.md, context/progress/README.md, spec 050 (one line),
context/roadmap.md (Reserved: 065, 066, 067)
```

**What 063 changes on top of 057's workflow.**

| job | 057 | 063 |
|---|---|---|
| `build` | the whole judge; outputs `assets-id`, `sums-sha256` | the `build` shard; also hashes and uploads its record; outputs `record-id`, `record-sha256` and `wasm-sha256` too |
| `rebuild-linux-arm64`, `rebuild-linux-x86-64`, `same-bytes` | as 057 | unchanged |
| `judge-macos`, `judge-linux`, `judge-windows` | none | new (Decision 7) |
| `verify` | the subset of the judge, the blocked assertion, the installed wheel | the installed wheel only (Decision 12) |
| `gather` | none | new (Decision 9); holds no assets |
| `attest`, `publish` | need build, verify, same-bytes (and attest) | also need `gather` |
| `pypi` | as 057 | unchanged |

**`release_shard_errors(text, plan)`**, on the workflow without comments, one line per breach:

1. Jobs `judge-macos`, `judge-linux` and `judge-windows` exist, on `macos-15`, `ubuntu-24.04` and
   `windows-2025`, each `needs: build`, `timeout-minutes: 30`, `permissions` exactly
   `contents: read`, `fail-fast: false`, with no job-level `if:` or `continue-on-error:`.
2. Each one's `matrix.shard` list is exactly the plan's shards for its system, in the plan's order.
3. The three are the same text once each runner's name, its system's name and its matrix list are
   replaced by placeholders, as `rebuild_gate_errors` compares the rebuilds.
4. Each runs, in order: 057's guard, download and check; a step that runs `fetch.py --shard
   "$SHARD"`; a step whose `run:` is `uv run pytest -p no:cacheprovider --shard "$SHARD"
   --progress-latest "$RUNNER_TEMP/record/latest.json"` with `SHARD: ${{ matrix.shard }}` in its
   `env:`; a hashing step `id: sha` whose `run:` hashes exactly `$RUNNER_TEMP/record/latest.json`;
   an upload `id: record` of that same path with `if-no-files-found: error`; the step `id: out`,
   whose `env:` is exactly Decision 7's three bindings and whose `run:` is its one fixed text. No
   step swallows a failure (`||`, `set +e`).
5. Each job's `outputs:` maps `<shard>-id` and `<shard>-sha256` from `steps.out` for every shard of
   its system, and nothing else.
6. `build` runs `--shard build` in place of the judge, hashes and uploads that record, and maps
   `record-id` and `record-sha256`; it maps `wasm-sha256` from a step, before the `release-assets`
   upload, whose `run:` hashes `build/artifacts/python.wasm`; no step of `build` runs
   `uv run pytest` without `--shard` except the zero-patch step.
7. `gather` exists on `ubuntu-24.04`, `timeout-minutes: 15`, `contents: read`, needs `build` and
   the three judge jobs, has no job-level `if:` or `continue-on-error:`, downloads nothing but
   record ids: every record id of every plan shard and of `build` (by 057's rule 4 as widened),
   each job's into `records/<job>/`, and never `release-assets`; binds `WASM_SHA256` from
   `needs.build.outputs.wasm-sha256`, every `<shard>-sha256` and `record-sha256` in its gather
   step's `env:` under Decision 9's names, with `GITHUB_EVENT_NAME` and `GITHUB_REF_TYPE`; and runs
   `tests/harness/gather.py`.
8. `attest` and `publish` need `gather`; no job but `gather` reads a record id.
9. `verify` runs no `pytest`.
10. No job but `build` sets, and no job but `gather` reads, `wasm-sha256`.

**The README's *Releasing***, replacing "runs the whole judge, and checks the same bytes on Linux,
Windows and macOS": "judges the build host's own checks, then the rest of the judge runs in
shards on macOS, Linux and Windows at once, with numpy's and pandas' own test suites on Linux and
one group of them on macOS and on Windows (`tests/release_shards.toml`). A job named `gather`
reads every shard's record by its id and hash, and nothing is signed or published unless every
shard ran exactly its share on the release's bytes, nothing failed, the probe passed on all three
systems, and the lane's newest acceptance is on the same `python.wasm` (on a tag, with the same
judge). The gather writes no history: only the lane accepts."

**AGENTS.md**, under *Rules that bind all work*: "**Every package runs its own tests in the
release** (spec 063). A specification that adds a package adds its suite's groups under
`tests/upstream/` and to a shard in `tests/release_shards.toml`, or says in
`tests/upstream/packages.toml` why not yet; the judge checks it."

**`context/progress/README.md`**, "Before a release" becomes: "The release workflow runs the
upstream suites itself, in shards (spec 063), and its `gather` job requires the newest acceptance
to be on the release's `python.wasm`, clean and not partial, and on a tag the release's judge to be
the accepted one."

**CHANGELOG.md**, under the first unreleased section (0.1.0a7), a *Release* entry: "**The release
judges in parallel shards** (spec 063). The release runs numpy's and pandas' own test suites
(eleven groups, 63,718 passing tests) on Linux, one group of them on macOS and on Windows, every
product check and the runner's own tests on all three systems, and the rules and the judge's own
tooling on macOS and Linux, in eighteen parallel jobs after the build. A `gather` job reads every
shard's record by id and SHA-256 and publishes nothing unless each shard ran exactly its share on
the release's bytes, nothing failed, the probe passed on three systems, and the lane's newest
acceptance is on the same `python.wasm`. Every package now names its own suite, or why not yet, in
`tests/upstream/packages.toml`."

## Scope

**In:** the above.

**Out, each with its reason:**

- **Landings and the lane's judge.** `uv run pytest` without `--shard` is unchanged, and the lane
  never shards (spec 052, Decision 11: the verdict of record is serial).
- **CI writing history.** Decision 10.
- **CPython's own test suite as a shard.** The owner answered question 99: "Gate 0.1.0
  regardless". It is its own specification, 065 (reserved), the closer of `python`'s `later`
  entry; 063 does not build it.
- **Pull requests.** The owner's answer to question 98 also asks that changes be pushed as a branch
  with a pull request to main that runs the tests. That is spec 064's. 063 does not build it, but
  keeps its pieces reusable as pull-request checks: `--shard`, `fetch.py --shard` and `gather.py`
  take nothing release-only but the build job's outputs (`record-id`, `record-sha256`,
  `wasm-sha256`) and the event bound in `env:`, and G7's judge clause applies to tags only, so a
  pull request's workflow can run the same judge jobs and gather against its own build.
- **The other packages' suites.** Specs 066 and 067 (reserved, Decision 15); the pure-Python
  ones need their sdists pinned as data, since their wheels carry no tests.
  (2026-10-21: 067 built, 42 `later` or new entries now `suite`, their test sources pinned as
  `tests` lines; branch `spec/067-the-pure-python-packages-own-tests`.)
- **The oracle in CI.** Its check stays blocked there, as today; it is local tooling, not a
  protected need. Running it in a shard would add a native numpy and pandas to CI's inputs for
  22 s of checking that the lane runs at every landing.
- **Splitting a test file across shards**, or `-n` inside a shard. Decisions 3 and 4.
- **A shard on ubuntu-24.04-arm.** Decision 3.
- **The repository's settings** (questions 94 and 97) and **bumping any action**.
- **Ten clean landings, or changing `sameness.py`.** Spec 052's rules for the lane.

## Acceptance criteria

Each is counted; none times anything. Each check is written first and run against today's code
(or the stand-in named) to see it fail; the builder records each failing assertion in the landing
notes. A stand-in is applied in a scratch copy, never committed.

1. **The plan's rules.** `tests/checks/test_rules.py::test_release_shards_cover_the_judge` runs
   `shards.plan_errors` on `tests/release_shards.toml` and passes. `tests/unit/test_shards.py`
   runs it on variants, each of which must fail with its own line: *an empty shard* (`files`
   naming a file that does not exist; a `groups` naming no group); two shards with one file; no
   `rest`; two `rest`; every test file listed (an empty `rest`); an upstream group in no Linux shard;
   a group in two Linux shards; an own shard missing `windows`; `build` on `linux`; an unknown
   system. Seen failing first: the check fails on today's tree (no plan file).

2. **The selection.** `tests/unit/test_shards.py` on a synthetic collection (goal checks, unit
   tests, an upstream file with two groups, their classes, one trap and the rules check): each
   shard's items are exactly the expected sets; every item is in exactly one shard per system;
   `rest` takes the upstream file's rules check and no group check; a new file lands in `rest`.
   *Stand-ins:* a `select` whose `rest` is computed per system (macOS's `rest` then takes the groups
   macOS does not run); one that matches files by prefix (`test_v1_4_embedding.py` also takes a
   `test_v1_4_embedding_more.py`).

3. **`--shard` in the plugin.** `tests/unit/test_plugin.py` self-tests on a small suite: `--shard
   a` runs exactly `a`'s items; its run checks (not `deselected`) are exactly `a`'s goal checks and
   its `deselected` is exactly the complement among the collected goal checks (the review's F8: a
   node-id run never collects the other files, so it is no comparison); it sets `meta.shard`, and
   `meta.units` holds the count and digest of exactly `a`'s unit tests; a shard that selects nothing exits non-zero with
   `RED: shard … selected nothing`; an unknown name, `-n 2`, `--accept`, `--retire` and a node-id
   argument with `--shard` are refused before collection; without `--shard`, the record is
   byte-equal to today's plugin's on the same suite, but for `at`, `host` and the new `meta.shard:
   null`, with no `meta.units`. *Stand-ins:* a plugin that drops the shard's other items from
   `items` without calling `pytest_deselected`; one that deselects before recording areas (each
   makes the ratchet report accepted checks as absent).

4. **The gather.** `tests/unit/test_gather.py` builds a good set of synthetic records (every shard
   of the plan on its system, consistent meta, hashed) with a synthetic `accepted.json`, history and
   release set. The good set passes with `three systems: darwin linux win32`. Each mutation must
   be red with its own reason:
   - **an empty shard**: a record whose run checks and unit tests are both zero (while the good set
     holds records with zero unit tests, `build` and the upstream shards, which must pass: the
     review's F2);
   - **a missing shard**: one record absent; one handed-on value empty;
   - **a forged record**: a byte changed after hashing; a record re-hashed and handed on under
     another shard's name (`meta.shard` disagrees); one hash handed on for two shards (G1's one
     to one); an extra file in `records/`; a record under another job's folder;
   - **a shard on the wrong artifact**: `meta.artifact` another hash than `WASM_SHA256`; an empty
     or non-hex `WASM_SHA256`;
   - a record of another commit; another judge hash; `dirty` true; a `foreign` entry; `partial`
     set; `workers` 2; a `--progress-dir` override;
   - `meta.platform` of another system; a record whose run checks lack one of its shard's checks;
     one with an extra check; one whose collection differs from the others'; a `meta.units` digest
     of another set; a plan whose `select` drops one goal check and one unit test from every share
     (G3's whole-judge clause);
   - a `fail`; an `unrun`; a gap not in `known_gaps.toml`; a check blocked by `upstream kit`;
   - an accepted pass that ran nowhere; an upstream group whose `passes` differs between Linux and
     Windows; one whose `passed_digest` differs; one below `accepted.json`'s;
   - the probe missing from the win32 records (three systems red);
   - the newest history line on another artifact; that line `partial`; that line `dirty`;
   - on a tag, a judge hash other than `accepted.json`'s; the same records on a dry run
     (`workflow_dispatch`) with that changed judge, which must pass.

   The merged record is checked too: the status order (a check `pass` on one system and
   `deselected` on the others is `pass`; `fail` anywhere is `fail`), the darwin record's metrics
   kept, and `suite` per system.

5. **The workflow.** `tests/checks/test_rules.py::test_release_judges_in_shards` runs
   `release_shard_errors` on `release.yml` with the plan; `tests/unit/test_scan.py` holds a good
   workflow and one variant per rule of the scan, each failing with its line: a shard missing from a
   matrix; an extra matrix entry; the shard lists in another order; a judge job without 057's check
   step; the three judge jobs differing beyond their names; a missing `<shard>-sha256` output;
   `gather` not needed by `attest`; `gather` downloading a record by `name:`; `gather` downloading
   `release-assets` (057's rule 16 fails too); `gather` with a second download into
   `release-assets/`; a judge job with `continue-on-error:`; a judge job with `contents: write`;
   `build` still running the whole judge; `build` without `wasm-sha256`, or computing it after the
   upload; the `out` step with another `env:` or `run:`; the `sha` step hashing another path;
   `verify` running `pytest`. 057's binding rules and 009's attestation rules pass on the new
   workflow, and their own variants, including the two widened rules' new cases (a list of ids from
   two jobs; a list with one id unguarded), fail as designed. Seen failing first on 057's workflow.

6. **The fetch.** `tests/unit/test_upstream.py` (or a new unit file) with a fake `urlopen` and
   synthetic tarballs, nothing fetched from the network: a shard without groups fetches nothing;
   one with groups fetches the kit and both trees, unpacks and calls the applier once per tree with
   the tree and its patch folder; a hash mismatch deletes the `.part` file and exits 1 naming the
   file; a name with no `get` line, and one with no pin, exit 1; a tarball member `../x`, an
   absolute name and a symlink out of the tree are refused; an existing tree is refused.

7. **Every package names its suite.** `tests/checks/test_rules.py::test_every_package_names_its_own_suite`
   passes on the new `packages.toml`; `tests/unit/test_shards.py` variants fail: a package of
   `paths.PACKAGES` with no entry; `qhull` (a source component, not a package) with no entry;
   `wasi-libc` with no entry; an entry for no component; `suite` for a package without groups;
   `via` empty, or naming an unlisted module, or a `later` entry; `later` whose closer is
   `context/roadmap.md` (a file, not a specification), or a number neither written nor reserved;
   an unknown `kind`.

8. **The shards together are the judge (the central criterion, EXECUTED by the builder).** On the
   frozen set of the build's base, with the kit and both trees, the builder takes criterion 9's
   full serial run as the base, then runs every shard of the macOS and Linux plans and `build` in turn, each in its own
   process (`--shard`, serially, on the one machine; Linux shards run there too, since a shard's
   selection is the same on every system), and `--shard upstream-windows` too, since no macOS
   shard matches it (the Confirmation's N1). Then `gather.py` over those records, with the Windows
   records stood in by copies of the macOS own shards' records and the `upstream-windows` record,
   each relabelled `win32` and re-hashed (G6 is then exercised, not proven), must pass; and the merged record (Decision 9's definition, with the darwin `suite`
   taken as its `suite` for the comparison) must equal the serial full run under
   `sameness.differences` except `deselected`, the order of `collected_files` and `meta`. The builder
   records the output and the count of shard runs.

9. **The judge.** `uv run pytest -m "not slow"` while building; the full `uv run pytest` once at
   the end, green, with the judge changed (`--accept-judge` is the lane's). `ruff check` and
   `ruff format --check` stay green.

10. **The branch's dry run, before landing** (question 98; not a check). The builder pushes the
    branch and dispatches `release.yml` on it; every job passes on all three systems. The landing
    notes link every dispatched run, say what each failed run found and how it was fixed (and that
    each fix is in the reviewed diff), and record the passing run's wall time against today's 33.4
    minutes, each shard's time, the longest shard, any job that waited for a slot, the
    `upstream-macos` fuel against the lane's, and the gather's three-systems line. The branch is
    deleted from GitHub after landing.

11. **The dry run after landing** (the lane's, on main's exact commit; not a check). Every job
    passes on all three systems; the landing notes link it. A failure there is fixed before any tag
    (Decision 18).

12. **The first tag run after landing** records the gather's merged scoreboard line, and its
    tag-only judge clause, in that release's notes.

## Disposition of the pre-build review (2026-10-18)

The review is in the main tree, git-ignored, at
`build/reviews-evidence/063-spec/review/063-the-release-judges-in-parallel-shards-spec-2026-10-18.md`,
with its probes. The lane ruled on each finding; each is written in as ruled.

- **F1 (Medium), the gather broke 057's rule 16.** Written in, the preferred fix: the build job
  hands on `wasm-sha256` (Decision 6), and the gather never downloads `release-assets`
  (Decision 9), so rule 16 stands unwidened (Decision 16). Scan rules 6, 7 and 10; acceptance 5's
  variants (a gather downloading `release-assets`, a second download into it).
- **F2 (Medium), G3's "both non-empty" rejected 11 good records.** Written in: each count equals
  its share, which may be zero; the selection as a whole is not empty (G3). Acceptance 4's empty
  shard is "both zero", and the good set holds zero-unit records.
- **F3 (Medium), the first Linux and Windows runs, and goal-check skips.** Written in (Decision
  18): 0.1.0a6 may be tagged before 063 lands; with question 98 answered yes, the branch's dry run
  finds Linux and Windows failures before landing (acceptance 10); a goal check that fails on one
  system is fixed or given a real need, never skipped without one; the list of what only a dry run
  proves.
- **F4 (Medium-Low), G7 claimed all the bytes.** Written in: G7 claims only `python.wasm`'s tie,
  and the other files are judged by the shards (G7, Decision 11, Intent, the README, CHANGELOG and
  progress README texts). Added, for a pushed tag only: the release's judge hash equals
  `accepted.json`'s (G7; acceptance 4's tag and dry-run cases).
- **F5 (Low), the package rule missed components.** Written in (Decision 15): the rule keys on
  `paths.PACKAGES` ∪ `needs.SOURCE_COMPONENTS` with the name map, plus `wasi-libc` and
  `llvm-runtimes`; qhull is `via matplotlib`; wasi-libc and libc++ are `via python`; a `via` names
  a `suite` entry, `python` or a listed stdlib module; a `later` names a specification, written or
  reserved (065, 066, 067). Acceptance 7's variants.
- **F6 (Low), completeness rested on `select` alone.** Written in: G3 requires every collected goal
  check run in at least one record and every unit test in a share; `meta.units` carries a digest of
  the unit node ids under `--shard` only (Decision 1); `tests/unit/test_pins.py` moves to the
  `build` shard (Decision 3); G1 is one to one, with one folder per job.
- **F7 (Low), the `sha` and `out` steps unpinned.** Written in: Decision 7, step 6, and scan rule 4
  fix their texts.
- **F8 (Low), acceptances 3 and 8 undefined.** Written in: acceptance 3 compares the run checks and
  `deselected` as the complement; Decision 9 defines the merged record (status order, metrics,
  `suite` per system); acceptance 8 uses it.
- **F9 (notes).** Written into Decision 19 (re-runs, wall time, `three systems` left blocked for a
  follow-up, the new inputs), Decision 5 (tarballs to `downloads/<name>`), Decision 9 (the `goal`
  marker read, not guessed) and Decision 7 (the diagnostic artifact's name carries
  `github.run_attempt`).

## Disposition of the build review (2026-10-18)

The build review read `5b00cca..2efcece`. The lane's rulings are written in as ruled.

- **F1 (High), a product check file could fall quietly off Windows.** Fixed. `test_v1_3_lxml.py`
  (spec 046, arrived with the rebase) is in `own-guest`. Rule (g) of Decision 2 is new:
  every product check file and every runner unit file sits in a `files` shard on all three
  systems. Seen failing first on the unfixed plan:
  `(g) tests/checks/test_v1_3_lxml.py is a product file in no files shard on all three systems`
  (`build/reviews-evidence/063-build2/f1-seen-failing.log` in the main tree). Unit variants: a new
  `test_v1_9_*.py`, a new `test_runner_*.py`, `test_cli.py` left to `rest`, and a product file in a
  shard off Windows are each named; the rules, the upstream file and tooling may stay in `rest`.
- **F2 (High), the gather never ran in CI.** Waits on spec 076. After 076 lands and this branch is
  rebased onto it, the lane says so, and a branch dry run must pass every job, `gather` included,
  with its `three systems:` line in these notes. Nothing else is left before it.
- **F3 (Medium), the Linux SIGILL is a product defect.** Recorded. A check,
  `test_a_guest_trap_cannot_kill_a_host_that_enabled_faulthandler`, runs the review's case in a
  child process (a first call, then `faulthandler.enable()`, then a guest stack overflow) and is
  red when the host dies by a signal. It needs `Linux host` (a new need; the gather allows it to
  block), and is a gap in `tests/known_gaps.toml` (`1 finding(s), digest b5a565e2e3c0`) whose
  closer is spec 071, widened by the lane (the roadmap says so). The signal is named outside the
  digest, so x86_64's and aarch64's signals match one gap. The README's *Safety* tells embedders
  not to enable faulthandler after the runner's first call on Linux until 071 closes it. The
  Landing notes' account is replaced by the review's evidence and names the case for the next
  release's threat-model review. On macOS the child prints `None stack overflow` and exits 0
  (EXECUTED, 14 s).
- **F4 (Medium), the bad-grant check hides refusals never run on Windows.** Spec 076's (being
  drafted): it makes the refusals after the check's line 685 run green on Windows, and settles the
  three errno-parity checks. 063 lands after it.
- **F5 (Low), `PYTHONUTF8` covers the product legs.** Answered, kept. The shard step is one pytest
  run holding judge reads and product checks together, so the variable cannot be scoped to the
  judge's reads without splitting the run. The product's own text reads are MANIFEST (ASCII, 0
  non-ASCII bytes in the frozen set, the review) and Linux's `boot_id`; Windows' `verify` step,
  which installs and runs the wheel, still runs without it. The follow-ups the review names (every
  text read in `src/` names an encoding, or the judge's own reads name `utf-8` and the variable
  goes) are for a later judge change.
- **F6 (Low), a failed unit test was not red in the gather.** Fixed: G4 requires each record's
  `suite.total` to equal `passed + skipped` (`G4 <system>/<shard>: N unit test(s) failed`); a
  mutation in `test_gather.py`.
- **F7 (Low), the tag detection was untested.** Fixed: `gather.is_tag(environ)`, used by `main`,
  and `test_only_a_pushed_tag_is_a_tag` (a pushed tag; a pushed branch; a dispatch on a tag ref;
  nothing).
- **F8 (Low), stale texts.** Fixed: the CHANGELOG entry (moved to 0.1.0a7; eighteen legs; product
  checks on three systems, tooling on two); the landing notes' 23 legs (18); Intent and Design's
  CHANGELOG draft; the `--shard <name>` in the plan's header and `shards.py`'s docstring; the
  tooling sentence (now naming `test_zip_directory`'s host-side recipe tests); criterion 8's suite
  convention (darwin plus `build`); Decision 2 (f) (the plugin does not assert again; rule (f) is
  stated as it is).
- **Notes.** N2 (the gather's collection prints per-file counts): `-p no:terminal` breaks
  `--collect-only -qq` (exit 4), so the counts stay; cosmetic. N3 (the three-systems line): it is
  placed before the "not machine-checked" lines since `070ee4c`. N4: `packages.toml` has `lxml`
  (`later`, closer 066), `libxml2` and `libxslt` (`via lxml`). N1 and N5 need nothing.

## Landing notes

Built 2026-10-18 on `spec/063-the-release-judges-in-parallel-shards`, on main `5b00cca`, against
the frozen set `s-4eb5418a2b1bb553-c353b1d9`. No `scripts/` or `recipes/` file changed, so no
rebuild from the pins. Evidence is in the main tree's git-ignored `build/reviews-evidence/063-build/`.
Commits: `8553753` (the build), `e163974` (`--shard=NAME`), `070ee4c` (the first dry runs' findings
judged), `0815007` (the another-platform self-test), and this one (these notes).

### What changed

- `tests/release_shards.toml`: the plan, twelve shards. `build`; `own-embedding`, `own-guest`,
  `own-runner` on all three systems; `own-rest` on macOS and Linux; five Linux upstream shards;
  `upstream-macos` (numpy-lib); `upstream-windows` (pandas-io-parser).
- `tests/harness/shards.py`: `load`, `on`, `group_of`, `select`, `units_digest`, `plan_errors` (rules
  (a) to (f)), `components`, `package_errors`.
- `tests/harness/plugin.py`: `--shard`, `--shard-plan`; the refusals before collection; deselection
  after every area is recorded; `meta.shard` (always) and `meta.units` (under `--shard` only);
  `RED: shard <name> selected nothing`.
- `tests/upstream/fetch.py --shard NAME`: the kit, then both tarballs to `downloads/` (URLs from
  the `get` lines, hashes from `SHA256SUMS`, `.part` then rename), unpacked with the `data`
  filter and refused outside their own tree, patched with `scripts/steps/apply_patches.sh`.
- `tests/harness/gather.py`: G1 to G7 and the merged record (N2: darwin, else linux, else the only
  record's metrics); a CLI that collects in process, reading `goal` markers.
- `tests/upstream/packages.toml` and `test_every_package_names_its_own_suite`: 26 components
  (`paths.PACKAGES`, the source components mapped, `wasi-libc`, `llvm-runtimes`); 2 `suite`,
  13 `via`, 2 `build-only`, 11 `later` (closers 065, 066, 067, reserved in the roadmap).
- `tests/harness/scan.py`: `release_shard_errors` (rules 1 to 10); 057's rules 4 and 10 take a
  comma list of one job's ids, rule 14's table gains four rows, rule 16 is unchanged; 009's rule
  requires `gather` of `attest` and `publish`.
- `tests/harness/needs.py`: the need `descriptor limit` (RLIMIT_NOFILE); 
  `test_mount_descriptors_are_bounded` names it instead of skipping without a need.
- `.github/workflows/release.yml`: on 057's shape, Design's table, with `PYTHONUTF8: "1"` in the
  three judge jobs.
- `tests/checks/test_rules.py`: three checks. New unit files: `test_shards.py` (33),
  `test_gather.py` (39), `test_fetch_trees.py` (8); `test_plugin.py` +8, `test_scan.py` +21 and
  its fixtures updated for `gather`.
- README (*Releasing*), CHANGELOG (0.1.0a6), AGENTS.md (one rule), `context/progress/README.md`
  ("Before a release"), spec 050 (one amendment line).

### Amended at build, each with its reason (for the build review)

- **`--shard=NAME`, never `--shard NAME`** (Decision 1, scan constants, README). The first dry run
  (`39181658205`, cancelled) failed in the build job: before the plugin loads, pytest reads a bare
  `build` as a path, collects `build/` instead of `tests/`, never loads `tests/conftest.py`, and
  reports `--shard` unknown. Loud, never silent; the `=` form avoids it.
- **`own-rest` on macOS and Linux; a new `own-runner` shard on all three** (rule (e), Decision 3).
  The second dry run (`39182550825`) failed 112 unit tests in Windows `own-rest`: 65
  `test_build_progress`, 18 `test_checks_wiring`, 10 each `test_several_cores` and
  `test_clang_emulated`, 8 rules checks, 6 `test_zip_directory`, and a few more: the judge's own
  tooling and rules, and `test_zip_directory`'s host-side tests of the zip recipe modules
  (`_zip_directory`, `_zip_resources`; path separators on the host), whose guest check,
  `test_v1_3_the_zips_directory.py`, runs on Windows in `own-guest`. No product check. Decision 18 allows removing a system from
  a shard with its reason in the plan; the reason is there. The runner's own unit files (the
  product's code, of which today's verify ran three on Windows) moved to `own-runner`, so Windows
  keeps every product check today's verify ran, and more.
- **`PYTHONUTF8: "1"` in the judge jobs.** The same run: every check that reads the repository's
  UTF-8 text failed on Windows' locale codec (the README's FreeType credit line, the CHANGELOG
  section, the specification and memo rules, the public API check). The runner itself reads no
  locale-dependent text (READ, `src/`), so the setting hides nothing of the product's.
- **The need `descriptor limit`.** `test_mount_descriptors_are_bounded` skipped on Windows without
  a need, which the plugin fails (F3's rule): it now names a real need, and the gather allows it to
  block (G4).
- **A `via` may name a `later` entry** (Decision 15). matplotlib reaches freetype, harfbuzz,
  SheenBidi, libraqm and qhull, and is itself `later`: the confirmed text's "a `suite` entry" would
  have refused the review's own example, `qhull` `via matplotlib`.
- **`GITHUB_EVENT_NAME` and `GITHUB_REF_TYPE` are read, not bound** (G7). GitHub sets them and a
  step cannot override a `GITHUB_*` variable; binding them would have been a no-op at best.
- **The another-platform self-test** (`test_plugin.py`) named `linux-x86_64` as "another
  platform", which is the host's own on Linux (the third dry run, `39184807592`, and its twin in
  `test_landing_lane`). It now names `plan9-amd64`.

### Criteria 1 to 7: the checks, seen failing first (EXECUTED)

On main `5b00cca` in a scratch clone, with the new test files copied in (`seen-failing-on-main.log`):
`test_shards.py` and `test_gather.py` fail to import (`cannot import name 'shards'`, `'gather'`);
`test_fetch_trees.py` 8 failed; `test_plugin.py -k shard` 8 failed (unrecognised `--shard`);
`test_scan.py` 26 failed; the three new rules checks fail (`ImportError`). On 057's workflow with
the new harness: `test_release_judges_in_shards` fails with 8 findings (`rule 1: no job
judge-macos` … `rule 7: no job gather`), and `test_releases_attest_and_verify_their_assets` with
`attest does not need build, verify and gather; publish does not need attest and gather`.

The stand-ins, each in a scratch copy (`stand-ins.log`):

| stand-in | caught by |
|---|---|
| `rest` takes the group checks too (computed without the plan's groups) | `test_each_shard_selects_exactly_its_items`, `test_the_real_plan_takes_every_upstream_check_by_its_group` |
| files matched by prefix | `test_each_shard_selects_exactly_its_items` |
| the shard's other items dropped without `pytest_deselected` | `test_a_shard_runs_exactly_its_items_and_deselects_the_rest` |
| deselected before the areas are recorded | the same |

Every mutation of acceptance 4 (35, plus the dry-run case, the dropping `select` and the merged
record), every variant of acceptances 1, 5, 6 and 7, pass as designed: 80 tests in the three new
unit files, 8 in `test_plugin.py`, 21 in `test_scan.py`.

### Criterion 8: the shards together are the judge (EXECUTED)

In a scratch clone of the branch at `e163974` (full history, the same judge hash), with the kit
and both trees fetched by `fetch.py --shard upstream-macos` (8.8 s), every shard of the macOS and
Linux plans, `build` and `upstream-windows` (N1) ran serially, each in its own process: 11 runs,
all exit 0 (`acc8/summary.txt`; load 24 to 168 on 10 cores). Their records, laid out as the
release lays them, 12 relabelled to `linux-x86_64` or `win32-amd64` and re-hashed, went through
`gather.py`: exit 0, `three systems: darwin linux win32 on 1655014314805b58…`. The merged record
against the full serial run below, by `sameness.differences`, with the merged `suite` taken as
darwin's plus `build`'s (the `build` shard holds `test_pins.py`'s nine unit tests): **0
differences** (`acc8/sameness.txt`). With darwin's suite alone it is one difference, the suite
itself (1330/1332 against 1339/1341), as the build review found.

### Criterion 9: the judge (EXECUTED)

- Full, serial, on `8553753` (`full-serial.log`): `wasi_python v1: 403/419 pass · 14 gap · 2
  blocked · 0 fail (unit suite 1339/1341, 2 skipped)`; `ratchet vs 2ce08a592d: lost 0 · absent 0
  · unrun 0 · unrun locally 1 · gained 4 · grew 0 · judge changed: …`; `1742 passed, 4 skipped,
  14 xfailed in 1015.38s`; exit 0. Blocked: `prior-art clones`, `three systems`.
- Fast tier, `-n 3`, on `070ee4c`'s tree (`fast-n3-2.log`): `371/419 pass · 0 gap · 2 blocked · 0
  fail · 46 deselected (unit suite 1340/1342)`, lost 0, grew 0, `1711 passed, 4 skipped`.
- `ruff check` and `ruff format --check` green on `tests/`.

### Criterion 10: the branch dry runs (EXECUTED; decision 98)

| run | commit | result |
|---|---|---|
| `39181658205` | `8553753` | cancelled: the build job's `--shard build` (above) |
| `39182550825` | `e163974` | every upstream shard green on all three systems; macOS all green; Linux `own-rest` crashed (exit 132, SIGILL, in `test_runner_calls.py`, after two failures); Windows `own-rest` 112 and `own-guest` 7 failures |
| `39184807592` | `070ee4c` | all green but Linux `own-rest` (the another-platform self-test, 2) and Windows `own-guest` (4) |
| `39186533835` | `0815007` | **all green but Windows `own-guest` (4)** |

In every run `attest`, `publish` and `pypi` were skipped, as a dispatched run must be. `gather` was
skipped too, since it needs every judge leg; it ran green locally (criterion 8).

**Timings** (`run-*-timeline.txt`; minutes from the first job's start). Today: 33.4 (`39171852747`),
29.1 (`39178357693`, main after 057). Run `39186533835`: the build job 13.3 (its `build` shard
0.5); the 18 judge legs started at 13.4 to 14.2 and ended by 18.8; the longest legs were
`own-embedding` (macOS 5.0, Windows 5.3), `own-guest` (Windows 3.7) and `upstream-groupby` (3.5);
every upstream shard on Linux took 1.4 to 3.5. The x86_64 rebuild (12.5) and `same-bytes` ran
beside them. **Wall 18.8 minutes to the last judge leg**; with the gather (about 1 minute,
INFERRED) about 20, against 29.1 to 33.4 today, inside the estimate of 18 to 22. One macOS leg
waited 0.7 minutes for a slot in `39186533835` (`upstream-macos`, at 5 macOS jobs), 1.3 in
`39184807592`. `upstream-macos`'s fuel on the CI runner passed the ratchet against the lane's
darwin-arm64 value (the shard is green, so within 1e-4).

### What the branch dry run found

- **Windows, four product checks that never ran on Windows** (today's verify ran neither file).
  All four fail the same way in three runs. Each is the product's, outside this specification:
  - `test_a_read_only_grant_refuses_every_write[plain]` and `[snapshot]`: every write-type call is
    refused with EPERM, as on POSIX, so the read-only grant holds. But a write through a read
    descriptor answers EACCES (2), not EBADF (8), and the link case answers EPERM (63), not the
    ENOENT (44) the check expected on Windows (written without a Windows run).
  - `test_a_bad_grant_is_refused_before_any_work`: `root=<base>/new/../x` does not raise "does not
    exist" on Windows.
  - `test_the_rename_rule_forward_is_fuel_neutral`: the native call and the shadow's forward end
    differently on Windows (`returned 44` against `returned 54`).

  Until they are fixed (or their Windows expectations are corrected by their own specification),
  the release workflow is red on Windows. That is the release finding a gap, not 063 adding one.
  0.1.0a6 may still be tagged before 063 lands (Decision 18).
- **Linux, a product defect the run exposed.** In `39182550825`, Linux `own-rest` (then holding
  the runner's unit files after the harness's self-tests) died with SIGILL in
  `test_runner_calls.py::test_a_trap_in_host_alloc_is_the_calls_trap[unreachable]`; in its own
  shard, `own-runner`, the same file passed in the next two runs. The build review reproduced the
  cause (EXECUTED in a Linux container, its `sigill_probe/`): on Linux wasmtime takes a guest's trap
  through signal handlers, and a `faulthandler.enable()` after the first engine exists (as an
  in-process pytest session does) puts faulthandler's handler first, which restores wasmtime's and
  raises the signal again outside wasm. A pure-Python guest's stack overflow then kills the host
  (exit -4, "Fatal Python error: Illegal instruction"); with faulthandler off, or enabled before the
  engine, it is the call's trap. macOS takes traps through Mach ports and is not affected. It is
  now a check, `test_a_guest_trap_cannot_kill_a_host_that_enabled_faulthandler` (need `Linux host`),
  admitted as a gap whose closer is spec 071, widened by the lane; the README's *Safety* names the
  case for embedders; the next release's threat-model review (constitution §5.6) should take it.
  The plan's separation keeps the release's own shards out of the order that triggers it.

### The revision after the build review (EXECUTED)

Rebased onto main `7307f6f`, then onto `6fd89e0` after spec 068 landed (its checks at the end of
`test_v1_2_hostile_guest.py` kept beside this spec's); judged against 046's frozen set
`s-ff5246a2c2f1a52b` (068 changes no artifact), with a wheel built from it in `dist/`. Evidence in
the main tree's `build/reviews-evidence/063-build2/`.

- Fast tier, `-n 3` (`fast-n3.log`): `394/446 pass · 0 gap · 3 blocked · 0 fail · 49 deselected
  (unit suite 1378/1380, 2 skipped)`; `ratchet vs 75f03ab77e: lost 0 · absent 0 · unrun 0 ·
  unrun locally 1 · gained 4 · grew 0 · …`; `1772 passed, 5 skipped`.
- Full judge, `-n 3` (`full-n3.log`; the record kept as the worktree's
  `build/progress/latest.json`): `429/446 pass · 14 gap · 3 blocked · 0 fail (unit suite
  1378/1380, 2 skipped)`; blocked by `Linux host`, `prior-art clones`, `three systems`;
  `lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 4 · grew 0 · judge changed: …`;
  `1807 passed, 5 skipped, 14 xfailed in 534.46s`; exit 0.
- `ruff check` and `ruff format --check` green on `tests/`.
- Not yet run: the final branch dry run (F2), after spec 076 lands.

### The final branch dry run (F2; EXECUTED, 2026-10-19)

Rebased onto main `3ea0582` (047 regex, 055 sessions, 076 the Windows grant checks): 047's
`test_v1_3_regex.py` and 055's `test_v1_4_sessions.py` went into `own-guest` and
`test_runner_sessions.py` into `own-runner`, as rule (g) asks; `regex` is `later` (closer 066) in
`packages.toml`; the zero-patch count is main's nineteen. Judged against main's frozen set
`s-9d43bf645dfcaa71` (evidence in the main tree's `build/reviews-evidence/063-build3/`).

- Fast tier, `-n 3`, on the final commit: `442/496 pass · 0 gap · 3 blocked · 0 fail · 51
  deselected (unit suite 1390/1392)`; `lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 4 ·
  grew 0`; `1832 passed, 5 skipped`.
- Full judge, `-n 3`, on `f6046cb` (before the lxml expectation below, a one-check change that
  applies on Windows only): `479/496 pass · 14 gap · 3 blocked · 0 fail (unit suite 1390/1392)`;
  blocked by `Linux host`, `prior-art clones`, `three systems`; `lost 0 · absent 0 · unrun 0 ·
  unrun locally 1 · gained 4 · grew 0`; `1869 passed, 5 skipped, 14 xfailed in 321.56s`; exit 0.
- Run `39203592916` (`f6046cb`): every job green but Windows `own-guest`. 076's four checks now
  pass on Windows. The one new failure was 046's
  `test_stylesheets_and_entities_reach_only_grants[plain|snapshot]`, which ran on Windows for the
  first time (rule (g) put it there): a Windows host path in a `file://` entity is refused by
  name (EPERM), so libxml2 raises `XMLSyntaxError … failed to load … Operation not permitted`
  instead of giving an empty element. Nothing outside the grants is read. The check now expects
  that refusal on Windows and still fails if the host's secret appears (commit `5715430`; a
  judge change for the review to see).
- **Run `39205611721` (`5715430`): every job green on all three systems, `gather` included;
  `attest`, `publish` and `pypi` skipped, as a dispatched run must.** Build 13.9 minutes; the 18
  judge legs started at 14.0 to 14.8 and ended by 19.9; the longest were `own-embedding`
  (Windows 5.9, macOS 5.0, Linux 4.7) and `own-guest` (macOS 5.2, Windows 4.8); `gather` 0.3;
  **wall 20.2 minutes** against 29.1 to 33.4 before 063. The gather's output:

  ```
  wasi_python v1: 476/496 pass · 14 gap · 6 blocked · 0 fail   (unit suite 3293/3316, 23 skipped)
  blocked by: descriptor limit 2 · Linux host 1 · oracle 1 · prior-art clones 1 · three systems 1
  three systems: darwin linux win32 on 18595c7f180613021bc9097b4c6cb1a8e2db5228be40e1ba06b9e2cee8b3e851
  ```

  So the matrix legs' own output names, the comma-joined `artifact-ids` downloads and the gather
  step itself all worked on the runners (the three mechanics F2 named).
- The faulthandler check on the Linux `own-guest` leg, in both runs: `gap`, `findings: 1
  finding(s), digest b5a565e2e3c0: the host process died by a signal on a guest trap, faulthandler
  enabled after the runner's first engine (signal 4)` on `linux-x86_64`, as its gap names.

### After spec 071 landed (2026-10-19)

Rebased onto main `23f1c4f` (069, 071). No new test file arrived, so rule (g) needed no change.

- **The faulthandler check is retired, not restated.** 071 added
  `test_a_faulthandler_change_cannot_kill_the_host`, whose `after` row is this specification's
  case exactly: a first run, then `faulthandler.enable()`, then the same deep `json.loads`, in a
  fresh child, the host must survive (refused on Linux, the trap returned elsewhere). It also
  covers six more orders and the session path, and cites this review's F3. Restated, ours would
  only duplicate that row, so it goes, with its gap entry, the need `Linux host` (used by nothing
  else) and the README *Safety* paragraph; 071's own README text says what embedders must do.
- **`wasmtime cli`** (071's need for `test_recursion_raises_under_the_wasmtime_cli`, in
  `own-guest`): the CLI is unpacked under `build/tools` by the build only, so it is not on the
  judge jobs' runners. The gather allows it to block (G4), as it allows the oracle; the check runs
  at every landing in the main tree.
- 046's lxml check names Windows in its docstring (the reviewer's nit).
- Fast tier, `-n 3`, on `983f8e6` against `s-c50ca51fae5eb55b`: `499/553 pass · 1 gap · 2 blocked
  · 0 fail · 51 deselected`, lost 0, grew 0, `1893 passed, 4 skipped, 1 xfailed`. Full judge, `-n
  3`: `536/553 pass · 15 gap · 2 blocked · 0 fail`, lost 0, **grew 2**, exit 1: 071's
  `test_recursion_through_python_raises[heapq-plain]` and `[lru-cache-plain]`. Run alone twice they
  move run to run (heapq-plain 177.75 M, then 177.98 M, against 177.34 M accepted): the host's hash
  seed reaches these rows, as the lane found (spec 080 makes them deterministic).
- Branch dry run `39211765022` (`983f8e6`): red in two legs, neither this specification's.
  macOS `own-guest`: the same rows grew (heapq-plain 177,381,134 and pickle-partial-plain
  247,430,229 against the accepted darwin values). Linux `own-runner`: two of
  `test_runner_async.py`'s checks met 071's new guard, `RuntimeError: wasmtime's handler for
  SIGSEGV was replaced after the first run …`, in a process that runs the runner's unit files in
  order. Those files never ran on Linux before 063; spec 071's guard and an earlier test in the
  same process meet there. Every other leg was green; `gather` was skipped. Waiting on 080 and on
  the lane's call for the Linux one.

### After spec 080 landed (2026-10-19; EXECUTED)

Rebased onto main `8f8de73` without a conflict; no new test file. 080's open case (inline pytest
sessions drop wasmtime's handler on Linux, spec 082 reserved): every file that runs one
(`test_plugin`, `test_landing_lane`, `test_several_cores`, `test_checks_wiring`, `test_upstream`)
is in `own-rest`, and rule (g) keeps every runner unit file and product check out of `rest`, so
the plan never puts them in one process with the runner's tests.

- Fast tier, `-n 3`, against `s-c50ca51fae5eb55b`: `499/553 pass · 1 gap · 2 blocked · 0 fail · 51
  deselected (unit suite 1394/1396)`; lost 0, grew 0; `1893 passed, 4 skipped, 1 xfailed`.
- Full judge, `-n 3`: `536/553 pass · 15 gap · 2 blocked · 0 fail (unit suite 1394/1396)`;
  `lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 4 · grew 0`; `1930 passed, 4 skipped,
  15 xfailed in 540.21s`; exit 0.
- **Branch dry run `39225879599` (`d538a4c`): every job green on all three systems, `gather`
  included**; `attest`, `publish` and `pypi` skipped. Build 14.4 minutes; the 18 judge legs
  started at 14.5 to 15.5 and ended by 23.0 (the longest macOS `own-guest`, 7.5); `gather` 0.3;
  wall 23.4 minutes. The gather:

  ```
  wasi_python v1: 532/553 pass · 15 gap · 6 blocked · 0 fail   (unit suite 3304/3327, 23 skipped)
  blocked by: descriptor limit 2 · oracle 1 · prior-art clones 1 · three systems 1 · wasmtime cli 1
  three systems: darwin linux win32 on ab78e8931e76aaf996d74d3b7766fcdf0249119faab4d0dfa153a6b14d6887db
  ```

### The confirmation's D1 (2026-10-19)

071's `test_recursion_raises_under_the_wasmtime_cli` was always blocked in `own-guest` (the judge
legs have no CLI), so the release no longer ran it, while main's build job did. The lane's fix was
to move it to a file of its own in the `build` shard. Moving it changes its node id, and every
shard collects every file, so every shard's ratchet then reports the accepted node `absent` and
the dry run is red until the lane retires it (EXECUTED: `ABSENT tests/checks/test_v1_2_hostile_guest.py::test_recursion_raises_under_the_wasmtime_cli`,
the fast tier on the moved tree). So the check stays where it is, and the `build` shard names it by
node id: `nodes = [...]` in `tests/release_shards.toml`, a selection the `build` shard alone may
use. `select` gives a named node to that shard only; the rest of its file stays in `own-guest`.
Plan rule (h): only `build` names nodes, each once, each a check its tracked file defines. The
gather no longer allows `wasmtime cli` to block. Coverage is main's exactly, the node id is
unchanged, nothing is retired, and the scoreboard counts the check once. Locally `--shard=build`
passes it (`45 passed`).

Then rebased onto main `59b90b6` (075, 079; `test_scan.py`'s merged tail reformatted). Fast tier,
`-n 3`, against 079's set `s-c50ca51fae5eb55b-c9dcb5b8`, without the main tree's build trees linked
in (079's `test_every_build_python_is_pinned` reads build records, which would name the main
tree's paths): `480/554 pass · 1 gap · 22 blocked · 0 fail · 51 deselected (unit suite
1497/1504)`; lost 0, absent 0, grew 0; the 22 blocked are the build host's own checks (source
trees, compile records, the CLI), which the release's `build` shard runs. **Branch dry run
`39234703116` (`b450aae`): every job green on all three systems, `gather` included**; build 16.2
minutes, the 18 judge legs from 16.4 to 22.4, wall 22.8. The `build` record shows
`test_recursion_raises_under_the_wasmtime_cli: pass` on `darwin-arm64`. The gather:

```
wasi_python v1: 534/554 pass · 15 gap · 5 blocked · 0 fail   (unit suite 3613/3636, 23 skipped)
blocked by: descriptor limit 2 · oracle 1 · prior-art clones 1 · three systems 1
three systems: darwin linux win32 on ab78e8931e76aaf996d74d3b7766fcdf0249119faab4d0dfa153a6b14d6887db
```

### For the reviewer

- The scratch clones and stand-ins are under the session's scratchpad; their logs are copied into
  `build/reviews-evidence/063-build/`.
- The branch on GitHub is left for the lane to delete after landing.

**Landed 2026-10-19** through the lane, after spec 077. The lane rebased the branch onto main
`f19fdf0` with no conflict; its diff equals the reviewed diff at `cb505e4` line for line (EXECUTED,
`build/lane-063/delta.txt`, empty). The lane then squashed the branch's nineteen reviewed commits
into one, `19427b5`, whose tree is identical to the reviewed tip's: the intermediate commits carried
a stale zero-patch count and a rebase's conflict repair, so only the whole is green on its own
(AGENTS.md rule 9). The nineteen commits are listed in the main tree's git-ignored
`build/lane-063/commits.txt`. No `scripts/` or `recipes/` file changed, so the artifact set is
main's (`s-c50ca51fae5eb55b`, unchanged) and no rebuild was needed; the release workflow the spec
changes was run whole by the branch dry run `39234703116` on `b450aae`, whose code is this tree's.
The reviews were committed as `9a446e0`, and the lane's serial `uv run pytest` there accepted it
(`--accept-judge`, the judge changed) at history line 77: 537/554 pass, 0 fail, ratchet lost 0,
grew 0. The sameness step (rule 6a) compared statuses only: the reviewer's full record
(`063-buildreview/full-n3-latest.json`, 419 checks) agrees with the accepted record on every
check both hold except the prior-art licence check, blocked in the worktree, which has no
git-ignored clones. The lane's own `latest.json` was overwritten by the rules check before
`sameness.py` ran, so the full-record comparison was not made; the lane now copies `latest.json`
aside before the rules check. The branch on GitHub is deleted.
