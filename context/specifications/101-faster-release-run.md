# 101 — a faster release run: reuse a proven set on branches, and macOS shards that finish together

- **Status:** **drafted 2026-10-20** on `spec/101-faster-release-run` from main `30e9b41` (the
  owner's answer on CI). It changes the release workflow, so it is build-class (§5.7), and it is
  reviewed before it is built (constitution §5.6; AGENTS.md rule 8). It changes neither the
  guest's imports nor its exports, nor a byte of the artifact set: `scripts/` and `recipes/` do not
  change, so `MANIFEST` and `SHA256SUMS` stay main's. A different agent reviews the build.
- **Date:** 2026-10-20
- **Owner:** Clay Gendron
- **Kind:** **build-class** (it edits `.github/workflows/release.yml` and adds
  `.github/workflows/set-cache.yml`) **and a judge change**: the shard plan
  (`tests/release_shards.toml`), `tests/harness/shards.py`, `tests/harness/gather.py`,
  `tests/harness/scan.py` and the rules that read the workflow, with unit rows. New
  `release/set_key.py`. No `src/`, `scripts/`, `recipes/` or `downloads/` change. The lane accepts
  with `--accept-judge`; nothing moves, no row grows.
- **Depends on:** landed specifications only: 012, 040 and 059 (the same bytes from every host),
  057 (the release reads only what the build made), 063 (shards and the gather), 085 (the gather
  checks what it trusts), 087 (a found set's hashes checked before use). It meets 066 and 095,
  which add shards (Decision 12).
- **The owner's decision it writes to:** `context/decisions.md`, "Fewer CI runs per
  specification, and a faster run (2026-10-20)": "reuse the native build when the hash of its pins
  and recipes is unchanged, and split the macOS own-guest and own-embedding shards. The lane's
  estimate, not measured: about 60 minutes to about 30." The roadmap's "Reserved: 101".
- **Research it stands on:** this document's own measurements, below (EXECUTED: `gh run view
  <id> --json jobs,createdAt,updatedAt,headSha,headBranch` and `gh run view <id> --job <job> --log`
  on six runs, read-only, 2026-10-20; the drafting scripts `timing.py` and `files.py` in the
  drafting agent's scratchpad, summarised here in full). GitHub's documented limits (READ,
  docs.github.com, "Actions limits" and "Dependency caching", 2026-10-20).

## The problem

A release run took 21 minutes at wave 05 and takes 49 to 60 now. Every specification's builder
waits for one, and so does every wave. Two things set the length.

1. **The native build sits in front of everything.** The `build` job compiles the whole set from
   the pins on arm64 macOS, then judges its build shard. Every judge shard waits for it. At wave
   07 that took 34.1 minutes, 25.8 of them compiling, even when nothing the build reads had changed
   since the last run.
2. **Two macOS shards end last.** After the build, macOS `own-guest` ran 21.1 minutes and
   `own-embedding` 17.1. Their Linux twins ran 7.2 and 8.7. And macOS shards start late: GitHub
   gives the account five macOS jobs at once, shared by every live run.

The owner chose two levers. This specification designs both, measures what it can, and says
plainly what each buys.

## What was measured (EXECUTED unless marked)

**Five recent runs.** Minutes from the run's creation. "Build" is the macOS build job; "compile"
its `scripts/build.sh` step; "shard" its build shard. The macOS shards' columns are job durations.

| run | branch | wall | build (compile, shard) | arm64 rebuild | x86-64 rebuild | macOS own-guest | macOS own-embedding |
|---|---|---|---|---|---|---|---|
| 39371419248 | wave/05 | 21.4 | 12.7 (9.7, 0.8) | 10.8 | 16.7 | 7.6 | 6.3 |
| 39398491514 | wave/06 | 50.2 | 31.3 (22.7, 3.6) | 17.7 | 22.0 | 18.3 | 14.1 |
| 39442080658 | wave/07 | 59.7 | 34.1 (25.8, 3.5) | 19.4 | 19.9 | 21.1 | 17.1 |
| 39451333969 | spec/066 | 53.0 | 23.9 (18.2, 2.1) | 19.2 | 34.0 | 23.5 | 18.2 |
| 39448839291 | spec/100 | 48.6 † | 27.7 (21.1, 2.8) | 18.7 | 19.6 | 20.6 | 13.9 |

† red at the macOS shards; the gather was skipped.

**Wave 07's critical path** (run 39442080658). The build job ended at +34.3: checkout and uv 0.2,
download 0.4, compile 25.8, the wheel 0.2, the zero-patch step 1.5, the build shard 3.5, release
assets 2.3 (single-threaded `lzma` preset 9 over 240 MB), uploads 0.3. The macOS shards started
at +36.6 to +42.1, so 2.3 to 7.8 minutes after the build: a queue for macOS runners (two other
runs, 39439703872 and 39442912523, were live). macOS `own-embedding` ended at +59.3 and the gather
at +59.7. Every Linux and Windows shard had ended by +48.1.

**Where macOS `own-guest`'s time goes** (wave 07, from the timestamps on pytest's progress lines;
the same files on Linux for comparison):

| file | macOS min | Linux min |
|---|---|---|
| `tests/checks/test_v1_2_hostile_guest.py` | 9.00 | 2.89 |
| `tests/checks/test_v1_4_public_api.py` | 1.85 | 0.02 |
| `tests/checks/test_v1_1_artifact_set.py` | 1.64 | 1.20 |
| the other eleven files | 4.65 | 2.70 |
| **tests, total** | **17.14** | **6.81** |

`own-embedding` is one file, `tests/checks/test_v1_4_embedding.py`: 11.84 test minutes on macOS,
8.25 on Linux. Its 178 tests are not even: on macOS the first 36 took 3.45 minutes, the next 72
took 6.06, the last 70 took 2.32.

**macOS shards keep running after pytest's summary.** Between pytest's last line and the next
step's start:

| run | macOS own-guest | macOS own-embedding | Linux and Windows shards |
|---|---|---|---|
| 39371419248 (wave 05) | 0.85 min | 0.95 min | — |
| 39442080658 (wave 07) | 3.45 min | 4.74 min | 0.01 min |
| 39451333969 (spec 066) | 3.86 min | 4.96 min | — |

The build shard on macOS has no such tail (0.00). What runs there is the interpreter's exit: the
runner's `atexit` handler `_release` (removing the process's zip folders, dropping cached
wasmtime modules and engines) and session teardown (READ, `src/wasi_python/runner.py`). The cause
is not known (Decision 10).

**macOS got slower than the set grew.** At equal test counts (178 embedding tests in both),
macOS `own-embedding` ran 4.80 test minutes at wave 05 and 11.84 at wave 07; Linux ran 4.9 job
minutes and 8.7. The set grew in between (scipy, scikit-learn). INFERRED: the 3-core, 7 GB macOS
runner pays more per guest start for a larger binary.

**Width.** Wave 07's run had 26 jobs, 16 at once at its peak. Spec 066's branch run 39451333969
had 40 jobs, 23 of them Linux judge shards, 32 at once at its peak. GitHub's Pro plan allows 40
concurrent jobs, 5 of them macOS (READ).

**The set's size** (EXECUTED, `ls -la build/artifacts` in the main tree, set `dc6ba3a5…`):
`python.wasm` 93,793,855 bytes, the snapshot 98,620,293, the zip 47,730,899, with `MANIFEST`,
`SHA256SUMS` and `LICENSES/`: about 240 MB. The `release-assets` artifact (the wheel and the
`.tar.xz`) is 161,469,699 bytes (the download log of run 39442080658). The build tree is far
larger: the main tree's `build/` is 27 GB, logs and scratch included.

## Principle

**A reused set is never judged alone.** Every run, reused or not, still rebuilds the set from the
pins on two Linux hosts, and builds it once more for the build shard. A reused set counts only if
those fresh builds give its bytes. So a cache can make a run faster or make it red. It can never
make a stale set pass.

And: **only branch runs reuse.** A tag publishes what its own run built, and main's dry run
rehearses the tag exactly.

## Decisions

### 1. What is reused: the finished set, nothing else

The cache holds the set as `scripts/build.sh` leaves it in `build/artifacts/`: `python.wasm`,
`python-snapshot.wasm`, `python-stdlib.zip`, `MANIFEST`, `SHA256SUMS` and `LICENSES/`. About 240
MB before the cache action's own zstd compression. Not the build tree (27 GB locally), not the
wheel, not the release assets.

Why the set alone. The judge shards consume only the release assets, which the build job makes
from the set in under three minutes (the wheel and `release/version.py assets`). The wheel holds
`src/wasi_python/`, so caching it would key the cache on the runner's code too. The set does not
depend on the package version (`MANIFEST` names Python, the packages, the pins and the recipes,
not `wasi_python`'s version; READ, `scripts/assemble_artifacts.py`).

### 2. The key: every input of the build, by content

The key is `wasi-python-set-v1-<sha256>`, where the hash is over one canonical text that
`release/set_key.py` writes, line by line, sorted:

- `format 1` (a change to the scheme changes every key);
- `env NAME=value` for each variable the build steps see from the workflow:
  `SOURCE_DATE_EPOCH`, `UV_VERSION`, `UV_LOCKED`, `UV_PYTHON`, `UV_BUILD_CONSTRAINT` (their values
  as `release.yml` sets them; `uv pip install` in step 10 runs the uv that `UV_VERSION` names);
- `file <sha256> <path>` for every file in the closure:
  - `downloads/SHA256SUMS` (every pin, so every download by its hash);
  - every file git tracks under `scripts/` and `recipes/` (the recipes, the patches, the steps);
  - `release/set_key.py` itself and `release/build-constraints.txt` (named by an env value);
  - `tests/harness/constructors.py` and every module of `tests/harness/` it imports, directly or
    not (today `tests/harness/__init__.py` and `tests/harness/wasm.py`): step 60 runs it as a gate
    on the linked binary (`scripts/steps/constructors.sh`), so a change to the gate must not be
    skipped by a reused binary.

Not in the key, on purpose:

- **The runner image and its unpinned tools** (`cc`, `make`, `tar`, `xz`, `perl`). Every host
  builds the same bytes (specs 012, 040, 059), and every run proves it again (Decision 3). Keying
  on the image would miss weekly.
- **The rest of `release.yml`.** Only its env and the two build commands reach the build; the
  check in Decision 3 holds the commands to exactly `scripts/00_download.sh` and
  `scripts/build.sh`. A spec that adds a judge shard must not throw the cache away.
- **The commit, `src/`, `tests/` beyond the gate, `uv.lock`, the CHANGELOG.** The build reads
  none of them.

### 3. How the spec proves the key misses nothing

Three layers. The first fails early; the third is the guarantee.

1. **A standing check, before any run.** `test_the_set_key_names_every_build_input`
   (`tests/checks/test_rules.py`, own-rest, no artifacts) fails when:
   - a file git tracks under `scripts/` or `recipes/` is not in the closure;
   - a repository path that any of those files names (the same path tokens
     `test_every_repository_path_a_recipe_names_exists` reads, plus `$HERE/<path>`) lies outside
     the closure, `build/` and `downloads/` excepted (downloads are covered by
     `downloads/SHA256SUMS`);
   - a module run with `PYTHONPATH` naming a repository folder (today `harness.constructors`) has
     a local import outside the closure;
   - a variable in `release.yml`'s top-level `env:`, or in the `env:` of a job or step that runs
     `scripts/build.sh`, is not one of the key's `env` lines;
   - a repository path named by a keyed env value is not in the closure;
   - a job that runs `scripts/build.sh` runs it, or `scripts/00_download.sh`, with arguments, or
     runs anything else before them that writes under `build/` or `downloads/`.

   Seen failing first, each by a mutant the builder records: the closure without
   `tests/harness/wasm.py` (the import rule names it); without `downloads/SHA256SUMS`; a scratch
   copy of a step that names `LICENSES/x`; a top-level `env:` gaining `FOO: 1`.
2. **Once, a traced build** (criterion 3). The builder runs the arm64 Linux build in the lane's
   container slot under `strace -f -e trace=open,openat,openat2,execve`, lists every file opened
   under the checkout outside `build/` and `downloads/`, and shows the list is inside the
   closure. `strace` is the container's own tool, used for this evidence only; it is never in the
   workflow. The list and the command go in the landing notes.
3. **Every run, the backstop.** On a reuse run:
   - the build job checks the restored set before anything uses it (Decision 8): every file
     against the set's own `SHA256SUMS`, no other file, and `MANIFEST`'s `pin` and `recipe` lines
     equal to what this checkout's `downloads/SHA256SUMS`, `scripts/` and `recipes/` give;
   - `same-bytes` compares the reused set's `SHA256SUMS` with two rebuilds from the pins made in
     this run;
   - the gather's G2 requires every record's `artifact` and `set_sums` to equal the build job's,
     and the build shard's record now comes from a third fresh build (Decision 5);
   - and the gather needs `same-bytes` (Decision 6), so no release record exists without that
     proof.

   An input the key forgot, if it changes a byte, turns this run red. If it changes no byte, a
   reused set is the right set.

### 4. Where reuse is allowed

The `inputs` job decides, once, and hands on `reuse`:

- **A pushed tag: never.** The published bytes are what this run built. `actions/attest` signs
  provenance that says this workflow run made each asset (spec 009); a set from another run would
  make that statement false. Enforced three times: the `inputs` job's condition, the gather (G7:
  "a tag, and the set was not built in this run"), and a rules check on the workflow's text.
- **A dispatch on `main`: never.** It is AGENTS.md rule 6b's dry run before a tag; it must be what
  the tag run will be.
- **A dispatch on any other branch** (`spec/*`, `wave/*`): reuse when the key's entry exists and
  the dispatch input `from-source` is false (its default).

**Wave dry runs may reuse.** The wave's dry run is now the check for every rebased entry (the
owner, 2026-10-20), and waves are the throughput limit. A wave holding a build-class entry
changes the key and builds from source anyway. A wave of parallel-safe entries reuses main's set,
which the same run rebuilds from the pins three times on Linux, and the lane rebuilds again in the
main tree (§5.7). The lane passes `from-source: true` when it wants the macOS build itself in the
run, for example for the serial confirmation every fifth landing.

### 5. Every run still builds from source; the build shard moves to a fresh arm64 Linux build

The build shard reads the build tree: the 26 source trees, the compile records, `scipy-build/`,
the link map, the toolchain's `clang` and `llvm-nm` (READ, `tests/checks/test_v1_5_rebuild_from_pins.py`).
A reused set has no tree, and the tree is too large to cache. So the build shard leaves the macOS
build job for a new job, `build-shard (ubuntu-24.04-arm)`, which on every run, reused or not:

1. checks out, downloads the pins, runs `scripts/build.sh` (the same two commands as the rebuild
   jobs);
2. runs `uv run pytest -p no:cacheprovider --shard=build --progress-latest …` on its own tree;
3. hands on `record-id` and `record-sha256`.

Why a new job and not a rebuild job. The two rebuild jobs must stay text-alike and hand on
exactly their two ids (spec 057, Decision 4; `scan.rebuild_gate_errors`); they are independent
votes and stay so. Linux runners cost nothing on a public repository.

What changes for the build shard's checks:

- They examine an arm64 Linux tree, not the macOS tree. The macOS build's bytes equal that tree's
  output in every run (`same-bytes`; G2 on the build record), and the lane still runs every one of
  these checks on its darwin tree at every landing (§5.7). None of them records a metric
  (EXECUTED: all 50 goal-check rows of the build shard in `accepted.json` have empty `metrics`;
  the shard's other 10 of wave 07's 60 passes are unit tests), so no ratchet comparison is lost.
- `shards.PLATFORM["build"]` becomes `linux`; `gather.JOB["build"]` becomes `build-shard`.
- The macOS build job keeps its zero-patch step (the 26 trees against their tarballs) whenever it
  builds, so a tag's own published tree is still checked (§4.1).
- `test_recursion_raises_under_the_wasmtime_cli` uses the host's pinned CLI
  (`LINUX_AARCH64_WASMTIME_DIR`), and `test_scikit_learn_notice_carries_its_bundled_parts` the
  pinned sdist; both are on that host (READ, `scripts/line.conf`).

The build shard has never run on Linux. The builder's first dispatch is where a host-specific
assumption shows (the risks, below).

### 6. The gather waits for the proof, and says where the set came from

- `gather` needs `build`, `build-shard`, `same-bytes` and the three judge jobs. Today it does not
  need `same-bytes`; with reuse, `same-bytes` is the staleness backstop, so a release record must
  not exist without it. On today's runs this costs nothing: `same-bytes` ended at +34.9 in wave
  07, before any shard.
- The build job hands on `set-source`: `built` or `reused <key>`. The gather writes it into the
  merged record's `meta.set_source` and prints it on the scoreboard's first line. G7 gains: on a
  pushed tag, `set-source` must be `built`.
- Rule 6 of spec 063 (`scan.release_shard_errors`) moves the build shard's text to
  `build-shard`; rule 7 downloads its record into `records/build-shard`; rule 10 lets only `build`
  set `wasm-sha256` and `set-sums-sha256`, as now.

### 7. The cache: who writes it, who reads it, how big

GitHub scopes caches by ref: a run reads entries made on its own branch or on the default branch,
never a sibling's, never another tag's; an entry is never overwritten; entries unused for 7 days
go, and past 10 GB the least recently used go first (READ).

- **Writers.** Two, both on Linux, both writing the same folder name (`wasi-python-set`), so any
  Linux job can restore any entry:
  - `save-set` in `release.yml`: on a branch run that built from source, after `same-bytes`
    passed. It downloads the release assets by id (a holder under spec 057's rules 7 to 9),
    unpacks the set, checks it as Decision 8 does, recomputes the key from its own checkout, and
    saves. So a branch writes only a set that two fresh rebuilds matched.
  - `.github/workflows/set-cache.yml`: on every push to `main` (the lane's fast-forward) and by
    dispatch. One job on `ubuntu-24.04-arm`: compute the key; if main has no entry for it, build
    from the pins, check the set, save. Without it, a spec branch could reuse only its own
    earlier runs' sets, since branches cannot read each other's caches.
- **Readers.** Only the `inputs` job (a lookup, no download) and the `build` job (the restore,
  failing on a miss).
- **Size.** About 240 MB per entry before compression (INFERRED: 100 to 200 MB stored). Ten GB
  holds about fifty. Evictions cost a rebuild, never a wrong verdict. The builder records the
  stored size from the save step's log.
- **Poisoning.** A cache entry is written by a job on the same branch or on main; both are pushed
  only by the owner and the lane, and the workflow has no `pull_request` trigger. A poisoned
  entry would still have to match three fresh builds in the reading run (Decision 3). The one
  threat this does not stop, a pinned tool compromised the same way on every host, exists without
  a cache too.
- **Pinning.** `actions/cache` (its `restore` and `save`) is pinned by commit, its release named
  beside it, as every action is (`test_every_action_is_pinned_by_commit`). No new download, no
  new pin.

### 8. The build job on a reuse run

- `runs-on: ${{ needs.inputs.outputs.reuse == 'true' && 'ubuntu-24.04' || 'macos-15' }}`. A reuse
  run takes no macOS slot for its build.
- Steps that only a source build runs (`if: needs.inputs.outputs.reuse != 'true'`): download,
  compile, the zero-patch step. Steps only a reuse runs: restore (`fail-on-cache-miss: true`),
  then **"The reused set is this commit's"**: recompute the key from this checkout and require it
  equal to the `inputs` job's; `sha256sum -c` every file against the set's `SHA256SUMS` and refuse
  any other file; require `MANIFEST`'s `pin` and `recipe` lines to equal this checkout's; then
  move the folder to `build/artifacts/`. Values reach the script through `env:` (spec 057, rule
  11). Every later step (the wheel, the hashes, the release assets, the uploads, the printed
  record) is the same for both.
- If the entry vanished between the lookup and the restore, the job fails with one line that
  says so; the next dispatch builds from source.
- The check step's script is run in bash by a rules check, as spec 057's is: a good set passes; a
  changed byte, an extra file, a missing file, and a `MANIFEST` recipe line that disagrees with
  the checkout each fail.

### 9. The macOS shards: four that finish together

The shard plan changes on all three systems (every own shard runs on all three; spec 063's rule):

| shard | what | macOS test min (wave 07) |
|---|---|---|
| `own-hostile` | `tests/checks/test_v1_2_hostile_guest.py` | 9.0 |
| `own-guest` | the other thirteen files of today's `own-guest`, and today's `own-runner` files | 8.2 + about 0.5 |
| `own-embedding` | `tests/checks/test_v1_4_embedding.py`, but for the functions `own-embedding-b` names | about 6 |
| `own-embedding-b` | the named functions of that file | about 6 |

`own-runner` goes into `own-guest` because its job is mostly setup (1.4 minutes for under a minute
of tests on macOS), and a macOS job is the scarce thing. macOS then runs six shards and `verify`
(seven jobs) where it ran five and `verify` (six). Linux runs ten own and upstream shards, Windows
five.

**Splitting one file.** A shard may now name test functions in `nodes` (today only the build
shard may, and only by node id). An entry `file::function` takes every parameter case of that
function; a whole node id still works. `shards.select` already gives `nodes` precedence over
`files`. Two rules join `plan_errors` and G3: a function named by two shards is an error, and a
named function that no collected check matches is red (`G3 <shard>: names <node>, which no
collected check is`), so a renamed test cannot quietly unbalance the split. Moving tests into new
files was rejected: it renames node ids, which the ratchet reads as lost passes.

**Choosing the functions.** The builder measures per-test times of
`tests/checks/test_v1_4_embedding.py` on macOS (one `uv run pytest
tests/checks/test_v1_4_embedding.py -p no:cacheprovider --durations=0` in a judge slot the lane
grants) and names functions for `own-embedding-b` so the two halves' times are within 20% of each
other. Shards are chosen by job times, as spec 065's Decision 7 chose them; no test asserts a
time.

### 10. The tail after pytest's summary

3.5 to 5 minutes of each large macOS shard is spent after pytest's summary line (the table
above). It grew from under a minute at wave 05. It may be the runner's own exit path, which every
embedder on macOS pays. This specification does not count on removing it and does not change
`src/`. The builder spends at most one hour on its cause, on a branch dispatch (two strikes,
AGENTS.md rule 7), and writes what it found in the landing notes. A fix is a runner change, so it
is its own specification with its own pre-build review; the lane numbers it.

### 11. What the run is expected to take (INFERRED, to be measured)

From wave 07's step times, with the tail kept:

- **A reuse run, about 25 minutes.** `inputs` 0.5. The build job on Linux about 4 (restore,
  check, wheel, assets). The judge shards from about +5, the longest macOS shard 10 to 14 (one
  run alone: seven macOS jobs on five slots). `build-shard` about 24 (compile 18.7 to 19.4 on
  arm64 Linux in the runs above, then its 3.5-minute shard). `same-bytes` about +20.5. The
  gather at about +24.5. The arm64 build is the floor.
- **A source build, about 35 to 45 minutes.** The macOS build job without its build shard: 21.9
  to 30.6 in the runs above. Then the macOS shards, 10 to 14. Today the same runs took 48.6 to
  59.7.
- **What it does not fix.** An x86-64 rebuild that runs long (34.0 minutes in run 39451333969)
  delays `same-bytes`, and now the gather. macOS queueing across live runs. A run's width: with
  spec 066's 23 Linux shards, one run needs about 36 jobs of the plan's 40, so a second live run
  queues almost whole; "three live runs" no longer means three at full speed.

Criterion 6 records the measured numbers beside these.

### 12. Where this meets other specifications

- **066 and 095** add upstream groups and Linux shards to the same plan, the same matrix lists and
  the same gather `env:`. Textual conflicts only: each shard list is derived from the plan by rule
  2 of spec 063. Whichever lands second rebases its plan onto the other's.
- **092** reads the release record; `meta.set_source` is one more field, ignored by sameness.
- **Spec 057's table** (`scan.JOB_PERMISSIONS`) gains rows: `inputs`, `build-shard` and
  `save-set` `contents: read`. `save-set` is a holder of the build's files and follows rules 7 to
  9 and 16. The `seed` job of `set-cache.yml` is `contents: read`.

### 13. Not done here, and why

- **Judging a Linux rebuild's set while macOS builds.** On a source build it would bring the run
  to about 33 minutes. But it splits the bytes the shards judge from the bytes the build job
  publishes, which spec 057's binding forbids; a design change beyond the two levers.
- **Building branch runs' sets on Linux instead of macOS.** About 33 minutes on a source build
  too. It is a third lever, not the owner's choice.
- **Parallel `xz`.** It would change the published `.tar.xz` bytes.
- **More workers per shard.** G2 requires `workers == 0`: serial fuel is what the lane accepts.
- **Larger runners, or a plan with more macOS slots.** The owner's purchase, not a design.

## Intent

A builder who changed a test, not a recipe, gets the verdict in about 25 minutes instead of an
hour, and nothing the verdict means has changed: the set judged is the set three fresh builds made
in the same run. A tag still builds everything itself.

## Design

| file | change |
|---|---|
| `release/set_key.py` | new: `closure()`, `canonical()`, `key()`; `verify <set>` (Decision 8's check, also run by `save-set` and `set-cache.yml`); prints the canonical text to the log |
| `.github/workflows/release.yml` | the `inputs` job; `build`'s conditional runner, its reuse steps, `set-source` output, no build shard; `build-shard`; `save-set`; `gather` needs `build-shard` and `same-bytes`, reads the build record from `build-shard`; the judge matrices follow the plan; the `from-source` dispatch input |
| `.github/workflows/set-cache.yml` | new: Decision 7's `seed` job |
| `tests/release_shards.toml` | Decision 9's plan; the header's words on `build` |
| `tests/harness/shards.py` | `nodes` on any shard, function-level matches; `PLATFORM["build"] = "linux"`; `plan_errors`' two rules |
| `tests/harness/gather.py` | `JOB["build"] = "build-shard"`; G3's stale-name rule; G7's tag rule; `meta.set_source` |
| `tests/harness/scan.py` | spec 057's table and rules 6, 7 of spec 063 as Decision 6 says; new `release_reuse_errors` (Decision 4's conditions, Decision 8's steps, the writers and readers of Decision 7) |
| `tests/checks/test_rules.py` | the checks below |
| `tests/unit/test_set_key.py`, `tests/unit/test_shards.py`, `tests/unit/test_gather.py` | unit rows |
| `context/progress/README.md`, `AGENTS.md` rule 3a | one paragraph each: what `set-source` means, and that a reuse run's verdict is the same verdict |
| `CHANGELOG.md` | one line under the unreleased section (the release run reuses a proven set on branch dispatches; tags always build) |

## The checks, first

Each is written before the change it judges and seen failing first on today's tree.

1. **`test_the_set_key_names_every_build_input`** (rules, own-rest). Decision 3, layer 1, with its
   four mutants. Fails today: `release/set_key.py` does not exist.
2. **`test_the_release_reuses_a_set_only_on_a_branch`** (rules). `scan.release_reuse_errors`
   finds no breach: the `inputs` job's `reuse` expression is false for a pushed tag, for
   `refs/heads/main` and for `from-source: true`; only `inputs` (lookup) and `build` (restore)
   read the cache and only `save-set` and `set-cache.yml` write it; `save-set` needs `same-bytes`
   and runs only when the set was built; `build`'s source steps and reuse steps carry exactly
   Decision 8's conditions; the restore fails on a miss. Mutants: a tag condition dropped; a save
   before `same-bytes`; a restore without `fail-on-cache-miss`. Fails today: no `inputs` job.
3. **`test_the_reused_set_check_refuses_other_bytes[case]`** (rules). Decision 8's step script,
   run in bash on a fake set, as `test_the_release_check_refuses_other_bytes` runs spec 057's:
   the good set passes; a changed byte, an extra file, a missing file, a `MANIFEST` recipe line
   off by one hash, a key unequal to the `inputs` job's each fail. Fails today: no such step.
4. **The shard rules.** `test_release_shards_cover_the_judge` and `test_release_judges_in_shards`
   stay, against the new plan. New unit rows in `tests/unit/test_shards.py`: a function name takes
   all its parameter cases; a function in two shards is a plan error. Fails today: `nodes` is the
   build shard's alone.
5. **Gather rows** (`tests/unit/test_gather.py`): a build record from `build-shard` with platform
   `linux` passes G1 and G2; one from `build` fails G1; a tag with `set-source` `reused …` is red at
   G7; a branch with it is not; a named function no check matches is red at G3; the merged record
   carries `meta.set_source`. Fail today.
6. **Existing checks that must stay green, unchanged in meaning:** spec 057's binding rules (with
   the new rows), spec 012's rebuild gate, spec 009's attestation rules, the zero-patch rule,
   every action pinned by commit.

## Scope

In: Decisions 1 to 9 and 12. Out: the tail's fix (Decision 10), and Decision 13's list. No check
is retired and no node id changes.

## Acceptance criteria

1. **The checks exist and were seen failing first,** each failure recorded in the landing notes,
   with the mutants of checks 1 to 3.
2. **The set does not change.** A source build on the branch gives main's `SHA256SUMS` at the base
   (at drafting, `dc6ba3a5…`): no file under `scripts/` or `recipes/` changes.
3. **The key is whole.** The traced arm64 build of Decision 3, layer 2, opens no repository file
   outside the closure, `build/` and `downloads/`; the list and the command are in the landing
   notes.
4. **A source run.** The first dispatch on the branch (its own workflow change makes the key new
   to the branch and to main) builds on macOS, passes every job on all three systems but growth
   lines, and `save-set` saves the entry; its log names the key and the stored size.
5. **A reuse run.** A second dispatch on the same commit: `inputs` hands on `reuse` true; the build
   job runs on `ubuntu-24.04`, restores, and its check step passes; `build-shard`, both rebuilds and
   `same-bytes` pass; the gather passes with `meta.set_source` `reused <key>`; every record's
   `artifact` and `set_sums` equal the source run's.
6. **The numbers.** For both runs: the wall clock, every job's start and duration, each macOS
   shard's test minutes and tail, the queue before each macOS shard, beside Decision 11's
   estimates. A reuse run over 30 minutes, or a macOS shard job over 15, is named with its cause
   (queue, tail, or a slow host), not hidden.
7. **The seed.** `set-cache.yml`, dispatched on the branch (no push to main), finds the entry the
   source run saved and builds nothing; its log says so. Its build path is exercised by the first
   push to main after landing, and the lane records that run's id.
8. **The judge.** The fast tier green in the worktree; the lane accepts with `--accept-judge` and
   no `--accept-growth`: no row lost, grown or moved, the judge hash changed by the files named in
   *Design*.
9. **The tail.** At most one hour on Decision 10; what was found, or that it was not, in the
   landing notes.

## The owner's choices

None blocks the build. Decided until answered:

1. **Wave dry runs reuse by default** (Decision 4). The alternative, every wave from source, keeps
   waves near 35 to 45 minutes.
2. **The build shard runs on a fresh arm64 Linux build** (Decision 5), not on the macOS build, in
   every run. The lane keeps running it on darwin at every landing.
3. **A workflow on pushes to `main`** fills main's cache (Decision 7). Without it, reuse helps only
   a branch's later runs.
4. **The macOS exit tail** (Decision 10) may be a product cost for macOS embedders; a follow-up
   specification is suggested.
5. **Width.** With spec 066's shards a run is about 36 jobs wide on a 40-job plan (Decision 11).
   The rule of three live runs could become one or two.

## For the lane

- **Kind:** build-class (the release workflow, a new workflow), with judge changes. The set is
  unchanged, so a wave may hold it as one of the two other build-class entries; its rebuild in the
  main tree must give the base's `SHA256SUMS`.
- **Conflicts:** `tests/release_shards.toml`, `release.yml`'s matrices and gather `env:`, and
  `tests/harness/scan.py` with 066 and 095 (Decision 12). Order it after 066 if both are in one
  wave, so its split rebases onto 066's plan.
- **The flags:**

  ```
  --accept-judge "101: the release reuses a set on branch dispatches when its key (every pin, every tracked file under scripts/ and recipes/, the constructor gate and its imports, the build's env) has an entry; a tag or main always builds; a reused set is checked against its SHA256SUMS and MANIFEST, matched by two rebuilds and a third fresh build in the same run, and the gather needs same-bytes; the build shard runs on a fresh arm64 Linux build (build-shard); own-guest splits into own-hostile and own-guest (with own-runner's files), own-embedding into two by named functions; nodes may name functions on any shard; no check retired, no node id changed"
  ```

- **After the fast-forward:** the push to main starts `set-cache.yml`; the lane records its run id
  and whether it built (criterion 7).

## The builder's self-check (before asking for the build review)

- [ ] Every check of *The checks* seen failing first, each mutant recorded.
- [ ] `release/set_key.py` prints the same key in the `inputs` job, the build job, `save-set` and
      `set-cache.yml` for one commit (four log lines quoted).
- [ ] The traced build's list (criterion 3) attached, and empty outside the closure.
- [ ] The source run and the reuse run named by id, on the commit reviewed; every red line a
      growth line or none.
- [ ] The reuse run's build job ran on `ubuntu-24.04`; no macOS job ran a build.
- [ ] `build-shard`'s record: platform `linux-aarch64`, 60 checks run as on macOS (wave 07's
      build shard: 60 passed), none blocked.
- [ ] No `scripts/`, `recipes/`, `downloads/` or `src/` change (`git diff --stat main`).
- [ ] `same-bytes` and `gather` both pass in each run; `gather` started after `same-bytes`.
- [ ] Every new `uses:` pinned by a 40-hex commit with its release named.
- [ ] The macOS split's per-test measurement attached, the halves within 20%.
- [ ] Decision 11's estimates beside the measured numbers.
- [ ] CHANGELOG line under the unreleased section.

## Risks for the pre-build review to probe

- **Is the key whole?** Layer 1 reads paths statically; a path built at run time escapes it.
  Layer 2 is one traced build on one host. Layer 3 catches only inputs that change bytes. Is
  there an input that changes a gate's verdict but no byte, other than the constructor gate?
- **The build shard on Linux.** It has never run there. A check written for darwin may fail, or
  worse, pass vacuously. Compare its 60 results with macOS's.
- **G2 as a cross-host proof.** The design leans on G2's `artifact` and `set_sums` equality
  across the build, `build-shard` and every shard. Confirm both are computed from the bytes each
  job used, not copied from an input.
- **The conditional runner and spec 057.** `runs-on` by expression; steps with `if:` in the build
  job. Rule 15 forbids `if:` only on guards, checks and downloads; confirm none of those gains one.
- **Cache scope and lifetime.** A lookup hit followed by an evicted restore fails closed; is that
  the right failure, and is its message clear?
- **Wave reuse and §5.7.** "Compares it with the release workflow's build of the same tip": is a
  reused set, matched by three fresh builds in the run, that build?
- **The estimates.** Decision 11 is INFERRED from one run's steps. The macOS queue and the tail
  could take most of the gain on a busy day.

## One line

Branch runs reuse a set whose bytes three fresh builds in the same run must match, tags always
build their own, and the macOS shards split so none sets the run's length.
