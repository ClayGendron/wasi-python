# 101 — a faster release run: reuse a proven set on branches, and macOS shards that finish together

- **Status:** **drafted 2026-10-20** on `spec/101-faster-release-run` from main `30e9b41` (the
  owner's answer on CI); **reviewed before build** the same day
  (`../reviews/101-faster-release-run-prebuild-2026-10-20.md`, verdict "build once H1, M1 and M2
  are answered"); the owner answered choice 2 (main `5feb7e9`, `decisions.md`: the build shard
  moves to Linux on every run, tags included); **revised against every finding** (*Disposition of
  the pre-build review*) and **rebased onto `origin/wave/08`** (`66cc120`: 042, then 066, on main
  `2516875`) for a stacked build in wave 09; **built 2026-10-20** at `25fcd1a`: a source run
  (39468404589) and two reuse runs (39475482749, 39481889333), every red line a growth line but
  one Linux timeout answered in Decision 9 (*Landing notes*); criteria 3 and 7 wait on the lane's
  container slot and on landing. It changes the release workflow, so it is
  build-class (§5.7). It changes neither the guest's imports nor its exports, nor a byte of the
  artifact set: `scripts/` and `recipes/` do not change, so `MANIFEST` and `SHA256SUMS` stay the
  base's. A different agent reviews the build.
- **Date:** 2026-10-20
- **Owner:** Clay Gendron
- **Kind:** **build-class** (it edits `.github/workflows/release.yml` and adds
  `.github/workflows/set-cache.yml`) **and a judge change**: the shard plan
  (`tests/release_shards.toml`), `tests/harness/shards.py`, `tests/harness/gather.py`,
  `tests/harness/sameness.py`, `tests/harness/scan.py` and the rules that read the workflows,
  with unit rows. New `release/set_key.py`. No `src/`, `scripts/`, `recipes/` or `downloads/`
  change. The lane accepts with `--accept-judge`; nothing moves, no row grows.
- **Depends on:** 066 (stacked: built on `origin/wave/08` at `66cc120`, which holds 042 and 066
  on main `2516875`; it lands after wave 08). Landed: 012, 040 and 059 (the same bytes from every
  host), 057 (the release reads only what the build made), 063 (shards and the gather), 085 (the
  gather checks what it trusts), 087 (a found set's hashes checked before use), 092 (sameness reads
  a release record). It meets 095, which will add shards (Decision 12).
- **The owner's decision it writes to:** `context/decisions.md`, "Fewer CI runs per
  specification, and a faster run (2026-10-20)": "reuse the native build when the hash of its pins
  and recipes is unchanged, and split the macOS own-guest and own-embedding shards. The lane's
  estimate, not measured: about 60 minutes to about 30." The roadmap's "Reserved: 101". And the
  owner's answer on the build shard (main `5feb7e9`, `decisions.md`, "Spec 101's build shard moves
  to Linux on every run"): "The owner chose to move it to Linux always, tags included."
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
  - `release/set_key.py` itself, every local module it imports (none: it is stdlib only, run as
    `uv run --no-project python -I release/set_key.py`, so no job syncs the judge's environment
    for it), and `release/build-constraints.txt` (named by an env value);
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
   - a job that runs `scripts/build.sh` runs it, or `scripts/00_download.sh`, with arguments;
   - a top-level file under `tests/` is named `sitecustomize`, `usercustomize`, or after a stdlib
     module (`sys.stdlib_module_names`): `constructors.sh` puts `tests/` on `PYTHONPATH` without
     `-I`, so such a file would reach the gate without any import naming it (the review's L5a).

   Seen failing first, each by a mutant the builder records: the closure without
   `tests/harness/wasm.py` (the import rule names it); without `downloads/SHA256SUMS`; a scratch
   copy of a step that names `LICENSES/x`; a top-level `env:` gaining `FOO: 1`; a scratch
   `constructors.sh` that runs `-m harness.gate2`, a module outside the closure (the review's
   L5c: the rule finds the module itself, not only its imports); a `tests/sitecustomize.py`.
2. **Once, a traced build** (criterion 3). The builder runs the arm64 Linux build under
   `strace -f -y -e trace=%file,%process,chdir,fchdir -o build/101/trace.txt scripts/build.sh`,
   resolves each relative path against its process's working folder, lists every path touched
   under the checkout outside `build/` and `downloads/` (opened, `stat`ed, `access`ed or read as
   a link: `[ -f x ]` counts; the review's L5d), and shows the list is inside the closure.
   `strace` is the container's own tool, used for this evidence only; it is never in the
   workflow. It runs in the container slot the lane grants. The list and the command go in the
   landing notes.
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
   reused set is the right set. And the three fresh builds each run the whole of
   `scripts/build.sh`, with its gates (step 60's constructor gate, `apply_patches.sh`'s drift
   refusal, step 10's host-Python gate), so an input that changes only a gate's verdict turns the
   run red too (the review's reading). A missing key input can cause a false red, never a false
   pass: the key decides speed, not the verdict.

### 4. Where reuse is allowed

The `inputs` job decides, once, and hands on `reuse`:

- **A pushed tag: never.** The published bytes are what this run built. `actions/attest` signs
  provenance that says this workflow run made each asset (spec 009); a set from another run would
  make that statement false. Enforced three times: the `inputs` job's condition, the gather (G7:
  "a tag, and the set was not built in this run"), and a rules check on the workflow's text.
- **A dispatch on `main`: never.** It is AGENTS.md rule 6b's dry run before a tag; it must be what
  the tag run will be. It is also where a `macos-15` image change that breaks the macOS build
  shows, if no source run on a branch has shown it first: a reuse run builds nothing on macOS (the
  review's N2).
- **A dispatch on any other branch** (`spec/*`, `wave/*`): reuse when the key's entry exists and
  the dispatch input `from-source` is false (its default).

**Wave dry runs may reuse.** The wave's dry run is now the check for every rebased entry (the
owner, 2026-10-20), and waves are the throughput limit. A wave holding a build-class entry
changes the key and builds from source anyway. A wave of parallel-safe entries reuses main's set,
which the same run rebuilds from the pins three times on Linux, and the lane rebuilds again in the
main tree (§5.7). On a reuse run, "the release workflow's build of the same tip" that §5.7's lane
compares its main-tree rebuild with is `build-shard`'s fresh build, whose `SHA256SUMS` G2 ties to
the set judged; the lane names `build-shard`'s job id in its notes (the review's L7). The lane
passes `from-source: true` when it wants the macOS build itself in the run, for example for the
serial confirmation every fifth landing.

The decision is one script step in the `inputs` job, its values through `env:`: `reuse=true` only
when `GITHUB_EVENT_NAME` is `workflow_dispatch`, `GITHUB_REF_TYPE` is `branch`, `GITHUB_REF` is
not `refs/heads/main`, the `from-source` input is not `true`, and the lookup found the key; any
other value, empty included, gives `reuse=false`. Every consumer compares with `== 'true'`
exactly, so a broken or empty output builds from source (the review's L3). A rules check runs the
step's own script in bash over every combination.

### 5. Every run still builds from source; the build shard moves to a fresh arm64 Linux build

The build shard reads the build tree: the 26 source trees, the compile records, `scipy-build/`,
the link map, the toolchain's `clang` and `llvm-nm` (READ, `tests/checks/test_v1_5_rebuild_from_pins.py`).
A reused set has no tree, and the tree is too large to cache. So the build shard leaves the macOS
build job for a new job, `build-shard (ubuntu-24.04-arm)`, which on every run, reused or not,
source runs and tags included (the owner, main `5feb7e9`):

1. checks out, downloads the pins, runs `scripts/build.sh` (the same two commands as the rebuild
   jobs); it sets no `WASI_PYTHON_ARTIFACTS` and downloads no artifact, so its record hashes its
   own `build/artifacts` (the review's L6);
2. runs the zero-patch step, text for text as the build job runs it today (all 26 trees against
   their tarballs, `26 passed`), with no `if:`;
3. runs `uv run pytest -p no:cacheprovider --shard=build --progress-latest …` on its own tree;
4. hands on `record-id` and `record-sha256`.

Why a new job and not a rebuild job. The two rebuild jobs must stay text-alike and hand on
exactly their two ids (spec 057, Decision 4; `scan.rebuild_gate_errors`); they are independent
votes and stay so. Linux runners cost nothing on a public repository.

**What a tag run checks now** (the review's M1, in its words, which the owner accepted):
on a tag, a dispatch on main and a `from-source` run, the build shard's checks see only
`build-shard`'s Linux tree in CI. The published macOS tree is checked by the zero-patch step, by
`same-bytes` and by G2 (equal bytes), and by the lane's darwin run at landing. The seven record
checks no longer read the published build's records in CI:
`test_every_compile_contracts_nothing` (the compile records and `clang -###`),
`test_every_build_python_is_pinned` (meson logs, `config.log`s, PATH folders, the gate line),
`test_the_backend_orders_try_tables_alike` and `test_ducc0s_fft_compiles_to_one_object` (the
SDK's `clang`), `test_one_qhull_is_linked` (the link map), and
`test_the_guests_configure_results_are_recorded` (`pyconfig.h`); with
`test_recursion_raises_under_the_wasmtime_cli`, which now runs the arm64 Linux CLI. Equal bytes
stay proven; what CI no longer reads is how the published macOS build was made, for example an
unpinned host Python on the `macos-15` image that happened to give equal bytes (§4.2). The owner
chose this over keeping the build shard on macOS for source runs.

The macOS build job keeps its own zero-patch step on a source run (`if:
steps.compile.outcome == 'success'`, the only check with an `if:`, and only because a reuse run
has no tree there), so the published tree's sources are still checked on a tag. The unconditional
copy is `build-shard`'s.

What else changes:

- None of the build shard's checks records a metric or a fact (EXECUTED: all 50 goal-check rows of
  the build shard in `accepted.json` have empty `metrics`; the review confirmed no `facts`; the
  shard's other 10 of wave 07's 60 passes are unit tests), so no ratchet comparison is lost.
- `shards.PLATFORM["build"]` becomes `linux`; `gather.JOB["build"]` becomes `build-shard`.
- **Sameness reads the build run by its shard, not its platform** (the review's H1). Spec 092's
  `sameness.view()` adds up a release record's unit suite from runs whose platform is darwin; the
  build run's 10 unit tests (`tests/unit/test_pins.py`) would fall off the darwin side and give a
  false suite difference at every landing. `view()` counts a run's suite on the darwin side when
  its key is `build/build` or its platform starts with `darwin-`; `SYSTEMS` maps `build` to
  `linux` (`{"darwin": {"macos"}, "linux": {"linux", "build"}, "win32": {"windows"}}`), so
  `_ci_block` reads a block in `build-shard` as Linux's.
- `test_recursion_raises_under_the_wasmtime_cli` uses the host's pinned CLI
  (`LINUX_AARCH64_WASMTIME_DIR`), and `test_scikit_learn_notice_carries_its_bundled_parts` the
  pinned sdist; both are on that host (READ, `scripts/line.conf`).

The build shard has never run on Linux. The review found no check that branches on darwin; a
failure (`make_openblas_void_patch.sh` runs Linux's `git` and tools) or a vacuous pass (a loop
that matches nothing) is the risk, and the self-check compares `build-shard`'s `read:` counts with
the lane's darwin lines (L6).

### 6. The gather waits for the proof, and says where the set came from

- `gather` needs `build`, `build-shard`, `same-bytes` and the three judge jobs. Today it does not
  need `same-bytes`; with reuse, `same-bytes` is a staleness backstop, so a release record must
  not exist without it. The price (the review's N1): a failed or slow x86-64 rebuild now holds back
  the release record, which today a builder could still read. Kept, because the run is red on a
  `same-bytes` failure either way, and a record beside a red `same-bytes` invites reading the
  record alone; G2 on `build-shard` would be a backstop by itself, but two are cheap.
- The build job hands on `set-source`, made from evidence, not from the decision (the review's
  L3): the `scripts/build.sh` step has `id: compile`, and the output is
  `${{ steps.compile.outcome == 'success' && 'built' || format('reused {0}', needs.inputs.outputs.key) }}`.
  A wrong `reuse` on a tag that skipped the compile reports `reused`, and G7 turns red. The gather
  writes `set-source` into the merged record's `meta.set_source` and prints it on the scoreboard.
  G7 gains: on a pushed tag, `set-source` must be `built`. The rules check holds the output's text.
- Rule 6 of spec 063 (`scan.release_shard_errors`) moves the build shard's text to
  `build-shard`; rule 7 downloads its record into `records/build-shard`; rule 8's
  `RECORD_ID_OUTPUT` matches `needs.build-shard.outputs.record-id`; rule 10 lets only `build` set
  `wasm-sha256` and `set-sums-sha256`, as now.

### 7. The cache: who writes it, who reads it, how big

GitHub scopes caches by ref: a run reads entries made on its own branch or on the default branch,
never a sibling's, never another tag's; an entry is never overwritten; entries unused for 7 days
go, and past 10 GB the least recently used go first (READ).

- **Writers.** Two, both on Linux, both writing the same folder name (`wasi-python-set`), so any
  Linux job can restore any entry:
  - `save-set` in `release.yml`: on a branch run whose `set-source` is `built`, after `same-bytes`
    passed. It downloads the release assets by id (a holder under spec 057's rules 7 to 9 and
    16), unpacks the set, runs `release/set_key.py verify`, recomputes the key from its own
    checkout, and saves. So a branch writes only a set that two fresh rebuilds matched.
  - `.github/workflows/set-cache.yml`: on every push to `main` (the lane's fast-forward) and by
    dispatch. Two jobs, both `contents: read`: `lookup` (ubuntu-24.04: the key, a lookup) and
    `seed` (ubuntu-24.04-arm, only when `lookup` found nothing: download, build, `verify`, save).
    Without it, a spec branch could reuse only its own earlier runs' sets, since branches cannot
    read each other's caches. It falls under rules of its own (the review's M2; check 2): its
    triggers exactly `push: branches: [main]` and `workflow_dispatch`; top-level `permissions:
    {}`; each job's permissions exactly `contents: read`; `setup-uv` with `version: ${{
    env.UV_VERSION }}` and `enable-cache: false`; no `${{` in a `run:`; its top-level `env:` equal,
    name for name and value for value, to the key's `env` lines in `release.yml`; its build steps
    exactly `scripts/00_download.sh` and `scripts/build.sh` with no arguments; and the save after
    the `verify` step.
- **Readers.** Only the `inputs` job (a lookup, no download) and the `build` job (the restore,
  failing on a miss).
- **Size.** About 240 MB per entry before compression (INFERRED: 100 to 200 MB stored). Ten GB
  holds about fifty. Evictions cost a rebuild, never a wrong verdict. The builder records the
  stored size from the save step's log.
- **Poisoning.** A cache entry is written by a job on the same branch or on main; both are pushed
  only by the owner and the lane, and neither workflow has a `pull_request` trigger. A poisoned
  entry would still have to match three fresh builds in the reading run (Decision 3). The one
  threat this does not stop, a pinned tool compromised the same way on every host, exists without
  a cache too.
- **Pinning.** `actions/cache` (its `restore` and `save`) is pinned by commit, its release named
  beside it, as every action is (`test_every_action_is_pinned_by_commit`). No new download, no
  new pin.

### 8. The build job on a reuse run

- `runs-on: ${{ needs.inputs.outputs.reuse == 'true' && 'ubuntu-24.04' || 'macos-15' }}`. A reuse
  run takes no macOS slot for its build.
- Only the pins' download and `scripts/build.sh` (`if: needs.inputs.outputs.reuse != 'true'`),
  the restore and the move of the restored folder into `build/artifacts/` (`if:
  needs.inputs.outputs.reuse == 'true'`), and the build job's own zero-patch copy (Decision 5)
  carry `if:` (the review's L4). The restore fails on a miss (`fail-on-cache-miss: true`).
- **"The set is this commit's"** runs on every run, with no `if:`: `release/set_key.py verify
  build/artifacts` checks every file against the set's `SHA256SUMS`, refuses any other file, and
  requires `MANIFEST`'s `pin` and `recipe` lines to equal what this checkout gives, made by the
  same selection `scripts/assemble_artifacts.py` makes (its `RESEARCH_PINS` and the `bench_` rule,
  imported from that file, not copied). On a reuse run it also requires the key it computes to
  equal the `inputs` job's. Values reach the script through `env:` (spec 057, rule 11). Every
  later step (the wheel, the hashes, the release assets, the uploads, the printed record) is the
  same for both kinds of run.
- If the entry vanished between the lookup and the restore, the job fails with one line that
  says so; the next dispatch builds from source.
- The check's script is run in bash by a rules check, as spec 057's is: a good set passes; a
  changed byte, an extra file, a missing file, a `MANIFEST` recipe line that disagrees with the
  checkout, and a key unequal to the `inputs` job's each fail.

### 9. The macOS shards: four that finish together

The shard plan changes on all three systems (every own shard runs on all three; spec 063's rule):

| shard | what | macOS test min (wave 07) |
|---|---|---|
| `own-hostile` | `tests/checks/test_v1_2_hostile_guest.py` | 9.0 |
| `own-guest` | the other thirteen files of today's `own-guest` | 8.2 |
| `own-embedding` | `tests/checks/test_v1_4_embedding.py`, but for the functions `own-embedding-a` names | about 6 |
| `own-embedding-a` | the file's first 41 functions (its first 65 checks), named | about 6 |
| `own-runner` | unchanged | under 1 |

macOS then runs seven shards and `verify` (eight jobs) where it ran five and `verify` (six). On
wave 08's plan, Linux runs 25 shards (066's 23, plus `own-hostile` and `own-embedding-a`),
Windows six.

**`own-runner` stays a shard of its own** (a departure from the reviewed draft, which folded it into
`own-guest` to save a macOS job). The builder's reuse run 39475482749 lost its Linux `own-guest`
leg, with `own-runner`'s files in it, to the 30-minute limit, with no log kept (`BlobNotFound`),
on the bytes the source run 39468404589 had judged there in 6.5 minutes. The cause is not known;
the fold was the one new thing in that leg, so it is undone, and the third run is the check.

**Splitting one file.** A shard may now name test functions in `nodes` (today only the build
shard may, and only by node id). An entry `file::function` takes every parameter case of that
function; a whole node id still works. `shards.select` already gives `nodes` precedence over
`files`. A shard that names only `nodes` runs on exactly the systems of the shard whose `files`
hold their file, so nothing falls off a system. Two rules join `plan_errors` and G3: a function
named by two shards (or a function and one of its cases) is an error, and a named entry that no
collected check matches is red (`G3 <shard>: names <node>, which no collected check is`), so a
renamed test cannot quietly unbalance the split. Moving tests into new files was rejected: it
renames node ids, which the ratchet reads as lost passes.

**Choosing the functions.** A local per-test timing of the file needs a judge slot. The first cut
comes from wave 07's macOS log instead: the file's first 36 tests took 3.45 minutes, the next 72
took 6.06, the last 70 took 2.32, so the halfway point (5.92 minutes) falls at about the 65th test
in collection order. `own-embedding-a` names the 41 functions whose checks come before it (fewer
names than the 86 after; a function added at the file's end goes to `own-embedding`). The
builder's runs measure both halves (the *Landing notes*); a boundary that leaves the halves more
than 20% apart moves. Shards are chosen by job times, as spec 065's Decision 7 chose them; no test
asserts a time.

**Width stays under 40** (the review's L1 counted 41 at once on a reuse run with 066). The three
judge matrices carry `max-parallel: 18` (one text, as rule 3 of spec 063 requires; it binds only
Linux's 25 legs). On a reuse run that gives at most 18 + 7 + 6 judge legs, 3 `verify` legs,
`build-shard`, two rebuilds and `same-bytes`: 38. On a source run the judge legs start after the
rebuilds have ended, and `save-set` runs beside them: 35. Linux's legs ran 0.6 to 8.5 minutes in
spec 066's run 39451333969, so the seven that wait add a few minutes to Linux, which ends long
before macOS.

### 10. The tail after pytest's summary

3.5 to 5 minutes of each large macOS shard is spent after pytest's summary line (the table
above). It grew from under a minute at wave 05. It may be the runner's own exit path, which every
embedder on macOS pays. This specification does not count on removing it and does not change
`src/`. The builder spends at most one hour on its cause, reading the runs it dispatches (two
strikes, AGENTS.md rule 7), and writes what it found in the landing notes. A fix is a runner
change, so it is its own specification with its own pre-build review: a follow-up the lane notes
in the roadmap and numbers (the owner's choice 4, its default).

### 11. What the run is expected to take (INFERRED, to be measured)

From the five runs' step times (the review's L1, corrected):

- **A reuse run, about 25 minutes; up to about 35 when the x86-64 rebuild runs long** (34.0
  minutes in one of five runs). `inputs` 0.5 to 1. The build job on Linux about 4 (restore,
  check, wheel, assets). The judge shards from about +5, the longest macOS shard 10 to 14 (one
  run alone: seven macOS jobs on five slots). `build-shard` near +22 to +24 (download 0.4, compile
  18.2 to 19.4, its shard 2.1 to 3.5). `same-bytes` about +20.5, or +35 with a slow x86-64
  rebuild. The gather after both.
- **A source run, about 35 to 50 minutes** (wave 07's build and queue give 44 to 54; spec 066's
  run 33 to 42). `inputs` 0.5 to 1; the macOS build job without its build shard, 21.9 to 30.6;
  a macOS queue of 0 to 7.8 when other runs are live; the longest split shard 10 to 14.5
  (own-hostile's 9.0 test minutes, about 0.5 of setup, a tail of 0.85 to 5). Today the same runs
  took 48.6 to 59.7.
- **How often each happens** (the review's L2, EXECUTED over the last 60 runs, INFERRED by each
  branch's `Kind` line): about 22 of 60 (37%) would have reused; package specifications, waves
  holding one, main and tags build from source. So the split and the moved build shard give most
  runs their gain (to 35 to 50); reuse gives a further 10 to 20 minutes to about a third of runs,
  and the owner's "about 60 to about 30" holds for those.
- **What it does not fix.** An x86-64 rebuild that runs long delays `same-bytes`, and now the
  gather. macOS queueing across live runs: with seven macOS jobs a run, two live runs already
  share five macOS slots. A run is about 38 jobs wide on a 40-job plan (Decision 9), so a second
  live run queues nearly whole; the rule of three live runs stays (the owner's choice 5, its
  default), and the lane's roadmap note carries this count.

Criterion 6 records the measured numbers beside these.

### 12. Where this meets other specifications

- **066** (in this branch's base) added fourteen Linux plot shards to the same plan, matrix and
  gather `env:`; this specification is built on it. **095** will add more. Textual conflicts only:
  each shard list is derived from the plan by rule 2 of spec 063.
- **092** reads the release record: `meta.set_source` is one more field, ignored by sameness, and
  `sameness.py` changes as Decision 5 says (H1).
- **Spec 057's table** (`scan.JOB_PERMISSIONS`) gains rows: `inputs`, `build-shard` and
  `save-set` `contents: read`. `save-set` is a holder of the build's files and follows rules 7 to
  9 and 16. `set-cache.yml`'s two jobs are `contents: read` (check 2).

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
hour, and every other run gets 35 to 50. The checks are the same; on a tag, seven of them read a
Linux tree that builds the same bytes, not the published macOS tree (the owner's answer, main
`5feb7e9`). The set judged on a reuse run is a set three fresh builds made in the same run. A tag
still builds everything itself.

## Design

| file | change |
|---|---|
| `release/set_key.py` | new, stdlib only: `closure()`, `canonical()`, `key()`; `verify <set> [--key K]` (Decision 8's check, also run by `save-set` and `set-cache.yml`); prints the canonical text to the log |
| `.github/workflows/release.yml` | the `inputs` job; `build`'s conditional runner, its reuse steps, `set-source` from evidence, no build shard; `build-shard`; `save-set`; `gather` needs `build-shard` and `same-bytes`, reads the build record from `build-shard`; the judge matrices follow the plan, with `max-parallel: 18`; the `from-source` dispatch input |
| `.github/workflows/set-cache.yml` | new: Decision 7's `lookup` and `seed` jobs |
| `tests/release_shards.toml` | Decision 9's plan; the header's words on `build` |
| `tests/harness/shards.py` | `nodes` on any shard, function-level matches; `PLATFORM["build"] = "linux"`; `plan_errors`' rules |
| `tests/harness/gather.py` | `JOB["build"] = "build-shard"`; G3's stale-name rule; G7's tag rule; `meta.set_source` |
| `tests/harness/sameness.py` | `view()` counts the build run's suite on the darwin side by its key; `SYSTEMS` maps `build` to `linux` (H1) |
| `tests/harness/scan.py` | spec 057's table; rules 1, 6, 7 and 8 of spec 063 as Decisions 6 and 9 say; new `release_reuse_errors` (Decision 4's step, Decision 8's steps, Decision 7's writers and readers, `set-cache.yml`'s rules) and `set_key_errors` (Decision 3, layer 1) |
| `tests/checks/test_rules.py` | the checks below |
| `tests/unit/test_set_key.py`, `test_shards.py`, `test_gather.py`, `test_sameness.py` | unit rows |
| `context/progress/README.md` | one paragraph: what `set-source` means, and that a reuse run's verdict is the same verdict (AGENTS.md rule 3a's line is the lane's to write: an agent does not edit the project's instructions) |
| `CHANGELOG.md` | one line under the unreleased section |

## The checks, first

Each is written before the change it judges and seen failing first on the base's tree.

1. **`test_the_set_key_names_every_build_input`** (rules, own-rest). Decision 3, layer 1, with its
   six mutants. Fails on the base: `release/set_key.py` does not exist.
2. **`test_the_release_reuses_a_set_only_on_a_branch`** (rules). `scan.release_reuse_errors` over
   both workflows finds no breach:
   - `release.yml`: only `inputs` (lookup) and `build` (restore) read the cache, only `save-set`
     writes it; `save-set` needs `same-bytes` and runs only when `set-source` is `built`;
     `build`'s conditional steps are exactly Decision 8's, with exactly its conditions; the
     restore fails on a miss; `set-source` is Decision 6's text; `build-shard` sets no
     `WASI_PYTHON_ARTIFACTS`, downloads no artifact, builds before its shard and runs the
     zero-patch step with no `if:`;
   - `set-cache.yml`: Decision 7's rules (the review's M2).

   Mutants, each seen red: a tag condition dropped; `!= 'false'` in `build`'s `runs-on`; a save
   before `same-bytes`; a restore without `fail-on-cache-miss`; in `set-cache.yml`, a
   `pull_request` trigger, `UV_VERSION` changed in one workflow only, and a save before the
   verify. Fails on the base: no `inputs` job.
3. **`test_the_reuse_decision_refuses_tags_and_main[case]`** (rules). The `inputs` job's decision
   step, run in bash: `reuse=true` only for a dispatch on a branch other than main, `from-source`
   false, the lookup hit; a pushed tag, a dispatch on a tag ref, main, `from-source: true`, a
   miss, and an empty hit value each give `reuse=false`. Fails on the base: no such step.
4. **`test_the_set_check_refuses_other_bytes[case]`** (rules). Decision 8's check, run on a fake
   set: the good set passes; a changed byte, an extra file, a missing file, a `MANIFEST` recipe
   line off by one hash, a `pin` line missing, a key unequal to the one given each fail. Fails on
   the base.
5. **The shard rules.** `test_release_shards_cover_the_judge` and `test_release_judges_in_shards`
   stay, against the new plan. Unit rows in `tests/unit/test_shards.py`: a function name takes all
   its parameter cases; a function in two shards is a plan error; a nodes-only shard on other
   systems than its file's shard is a plan error. Fail on the base.
6. **Gather rows** (`tests/unit/test_gather.py`): a build record from `build-shard` with platform
   `linux-aarch64` passes G1 and G2; one under `records/build` fails G1; a tag with `set-source`
   `reused …` is red at G7; a branch with it is not; a named function no check matches is red at
   G3; the merged record carries `meta.set_source`. Fail on the base.
7. **Sameness rows** (`tests/unit/test_sameness.py`, H1): a release record whose build run is
   `linux-aarch64` with 10 units and a local darwin record with the same units give no suite
   difference; a build run one unit short still gives one; a block in `build/build` by a CI need
   is read as Linux's. The first fails on the base (the review's probe: `suite: {'total': 100…} !=
   {'total': 90…}`).
8. **Existing checks that must stay green, unchanged in meaning:** spec 057's binding rules (with
   the new rows), spec 012's rebuild gate, spec 009's attestation rules, the zero-patch rule,
   every action pinned by commit.

## Scope

In: Decisions 1 to 9 and 12. Out: the tail's fix (Decision 10), and Decision 13's list. No check
is retired and no node id changes.

## Acceptance criteria

1. **The checks exist and were seen failing first,** each failure recorded in the landing notes,
   with the mutants of checks 1 to 4.
2. **The set does not change.** A source build on the branch gives the base's `SHA256SUMS`: no
   file under `scripts/` or `recipes/` changes.
3. **The key is whole.** The traced arm64 build of Decision 3, layer 2, touches no repository file
   outside the closure, `build/` and `downloads/`; the list and the command are in the landing
   notes. It needs the lane's container slot.
4. **A source run.** The first dispatch on the branch builds on macOS, passes every job on all
   three systems but growth lines, and `save-set` saves the entry; its log names the key and the
   stored size.
5. **A reuse run.** A second dispatch on an unchanged set, after the first completes: `inputs`
   hands on `reuse` true; the build job runs on `ubuntu-24.04`, restores, and its check passes;
   `build-shard`, both rebuilds and `same-bytes` pass; the gather passes with `meta.set_source`
   `reused <key>`; every record's `artifact` and `set_sums` equal the source run's.
6. **The numbers.** For both runs: the wall clock, every job's start and duration, each macOS
   shard's test minutes and tail, the queue before each macOS shard, the peak of concurrent jobs,
   beside Decision 11's estimates. A reuse run over 35 minutes, or a macOS shard job over 15, is
   named with its cause (queue, tail, or a slow host).
7. **The seed.** GitHub dispatches only a workflow the default branch holds (the builder's
   dispatch on the branch: `HTTP 404: workflow set-cache.yml not found on the default branch`), so
   `set-cache.yml` first runs at the push to main that lands it: with no entry for main's key, its
   `seed` job builds and saves. The lane records that run's id and the entry. Until then its rules
   (check 2) and its shared steps (the key, the verify, the save, exercised in `release.yml`'s
   `inputs` and `save-set` on the branch) are the evidence.
8. **The judge.** The fast tier green in the worktree; the lane accepts with `--accept-judge` and
   no `--accept-growth`: no row lost, grown or moved, the judge hash changed by the files named in
   *Design*. Sameness between a reviewer's release record and the lane's darwin record shows no
   suite difference from the build run (H1).
9. **The tail.** At most one hour on Decision 10; what was found, or that it was not, in the
   landing notes.

## The owner's choices

1. **Wave dry runs reuse by default** (Decision 4), with L7's wording. Default taken.
2. **The build shard runs on a fresh arm64 Linux build on every run, tags included.** Answered by
   the owner (main `5feb7e9`); Decision 5 carries the review's M1 wording.
3. **A workflow on pushes to `main`** fills main's cache (Decision 7), under M2's rules. Default
   taken.
4. **The macOS exit tail** (Decision 10): a follow-up for the roadmap. Default taken.
5. **Width.** The rule of three live runs stays; a run is about 38 jobs wide (Decision 9) and the
   lane's roadmap note carries the count. Default taken.

## Disposition of the pre-build review

The review (`../reviews/101-faster-release-run-prebuild-2026-10-20.md`) confirmed the draft's key
finding (a reuse run cannot skip a source build), that the build shard has no metrics or facts to
lose, that G2 is a real cross-host proof, and that layer 3 is stronger than drafted. Where each
finding went:

- **H1 (High), written in.** Decision 5 ("Sameness reads the build run by its shard"); *Design*
  names `tests/harness/sameness.py`; check 7 holds it, seen failing first; the `--accept-judge`
  reason names it; criterion 8.
- **M1 (Medium), answered by the owner and written in.** The owner moved the build shard to Linux
  always, tags included (main `5feb7e9`). Decision 5 carries the review's text on what a tag run
  checks; *Intent* says "the checks are the same; on a tag, seven of them read a Linux tree that
  builds the same bytes". The build job keeps its own zero-patch copy on source runs.
- **M2 (Medium), written in.** Decision 7 lists `set-cache.yml`'s rules; check 2 holds them, with
  the review's three mutants.
- **L1, written in.** Decision 11's estimates: about 25 on a reuse run, up to about 35 with a slow
  x86-64 rebuild; 35 to 50 on a source run; the `inputs` job in both. The width: Decision 9's
  `max-parallel: 18` keeps one run at 38 jobs at most, under the plan's 40.
- **L2, written in.** Decision 11, "How often each happens": about 22 of the last 60 runs (37%).
- **L3, written in.** Decision 6: `set-source` from `steps.compile.outcome`; Decision 4: the
  decision as one script, every consumer `== 'true'`; checks 2 and 3 with the two mutants.
- **L4, written in.** Decision 8: the set check runs on every run with no `if:`; only the
  download, the compile, the restore and the move carry one, and the build job's own zero-patch
  copy, whose unconditional twin is `build-shard`'s (Decision 5). The `MANIFEST` comparison imports
  `scripts/assemble_artifacts.py`'s selection rather than copying it.
- **L5, written in.** (a) the `tests/` names rule; (b) `set_key.py`'s imports (none) and its
  `uv run --no-project python -I`; (c) the `harness.gate2` mutant; (d) the strace command with
  `%file,%process`.
- **L6, written in.** Decision 5, step 1 and its last paragraph; check 2's `build-shard` rows;
  rule 8's regex; the self-check's `read:` comparison.
- **L7, written in.** Decision 4.
- **N1, answered.** Decision 6: kept, with its price stated.
- **N2, written in.** Decision 4.

## For the lane

- **Kind:** build-class (the release workflow, a new workflow), with judge changes. It changes no
  file under `scripts/`, `recipes/` or `downloads/`, so the set is the base's and its main-tree
  rebuild gives the base's `SHA256SUMS`. A wave may hold it as one of the two other build-class
  entries. Stacked on wave 08 (built on `66cc120`; the lane has since rebuilt wave 08 as
  `72bc5ed`, with 099 and on main `5805af0`): it rebases onto wave 08's landed tip at wave 09's
  entry.
- **Conflicts to expect at that rebase:** `tests/release_shards.toml` and `release.yml`'s judge
  matrices, `outputs:` and the gather's lists (all derived from the plan by rule 2 of spec 063),
  `tests/unit/test_scan.py`'s mutation rows, `CHANGELOG.md`'s unreleased section. 099 touches none
  of the workflow; its recipe change gives a new set key, so wave 09's first run builds from source.
- **AGENTS.md rule 3a** could say, in the lane's words: "a branch run may reuse a set the cache
  holds under its commit's key (spec 101); its verdict is the same verdict, and a release
  record's `meta.set_source` says which". This builder does not edit the project's instructions.
- **After the fast-forward:** the push to main starts `set-cache.yml` for the first time (GitHub
  will not dispatch a workflow main does not hold); the lane records its run id, whether `seed`
  built, and the entry's size (criterion 7).
- **Nothing moves:** no check retired, no node id changed, no fuel or byte row of this
  specification's own. The judge hash changes in `tests/release_shards.toml`,
  `tests/harness/{shards,gather,sameness,scan}.py`, `tests/checks/test_rules.py` and
  `tests/unit/test_{shards,gather,sameness,scan,set_key}.py`.
- **The claim list block** (sameness, spec 092):

  ```toml
  [[claim]]
  spec = "101"
  new = [
    "tests/checks/test_rules.py::test_the_set_key_names_every_build_input",
    "tests/checks/test_rules.py::test_the_release_reuses_a_set_only_on_a_branch",
    "tests/checks/test_rules.py::test_the_reuse_decision_refuses_tags_and_main*",
  ]
  units = 51
  ```

  (`units`: the unit rows this specification adds, by the builder's count: 33 in
  `test_set_key.py`, 7 in `test_gather.py`, 3 in `test_sameness.py`, 5 net in `test_shards.py`
  (one row replaced), 3 in `test_scan.py`; the lane's suite line is the check.)
- **The flag:**

  ```
  --accept-judge "101: a branch dispatch reuses a set the cache holds under its commit's key (release/set_key.py: every pin, every tracked file under scripts/ and recipes/, the constructor gate and its imports, the build's env); a tag or main always builds; a reused set is checked against its SHA256SUMS and MANIFEST, matched by two rebuilds and a third fresh build in the same run, and the gather needs same-bytes; the build shard runs on build-shard's fresh arm64 Linux build on every run, tags included, and sameness counts its unit tests on the darwin side (H1); own-hostile and own-embedding-a split from own-guest and own-embedding, nodes may name functions on their file's systems, G3 names a stale entry, G7 refuses a tag whose set was not built; set-cache.yml's rules; no check retired, no node id changed"
  ```

## The builder's self-check

- [x] Every check of *The checks* seen failing first on the base, recorded below; each mutant
      recorded (two of them found holes in the rules, fixed before commit).
- [x] `release/set_key.py` gave one key for one commit in the `inputs` job and `save-set` (run
      39468404589: `wasi-python-set-v1-ad003ce1…`, both); the build job's reuse check took the same
      key in runs 39475482749 and 39481889333. `set-cache.yml` has not run (criterion 7).
- [ ] The traced build (criterion 3): **not done**; it needs the lane's container slot.
- [x] The source run and two reuse runs named by id; every red line a growth line (042's, against
      the last acceptance `e9a76ce`) but one: run 39475482749's Linux `own-guest` timeout, answered
      by restoring `own-runner` (Decision 9) and cleared by run 39481889333.
- [x] The reuse runs' build job ran on `ubuntu-24.04` (1.7 minutes); no macOS job built.
- [x] `build-shard`'s record: platform `linux-aarch64`, 51 goal checks run, all passing, none
      blocked; 10 unit tests; the zero-patch step `27 passed`.
- [ ] L6's `read:` comparison with the lane's darwin lines: **not done**. Those lines go to
      pytest's captured output and show only on a failure; the record keeps no reason for a pass.
      The lane can print them with `uv run pytest -s` on the six checks in its darwin tree, and a
      reviewer from `build-shard`'s tree only by a diagnostic dispatch.
- [x] No `scripts/`, `recipes/`, `downloads/` or `src/` change.
- [x] `same-bytes` passed in every run; the gather never ran in CI (the macOS shards were red on
      growth, as every branch run on an unaccepted set is), so it was run by the builder on run
      39481889333's real records (*Landing notes*).
- [x] Every new `uses:` pinned by a 40-hex commit with its release named
      (`actions/cache/restore` and `actions/cache/save` at v6.1.0, `55cc8345…`).
- [ ] The embedding halves within 20% on macOS: in run 39468404589 only (below).
- [x] Decision 11's estimates beside the measured numbers (below).
- [x] CHANGELOG line under the unreleased section.

## One line

Branch runs reuse a set whose bytes three fresh builds in the same run must match, tags always
build their own, the build shard runs on a fresh Linux build every time, and the macOS shards
split so none sets the run's length.

## Landing notes

### What was built (on `spec/101-faster-release-run`, base `66cc120`, tip `25fcd1a`)

The *Design* table, as written, but for two departures: `own-runner` stays a shard of its own
(Decision 9, after run 39475482749), and `max-parallel` is 18, not 20 (with `own-runner` back, 20
would have allowed 40 jobs at once). The split shard is `own-embedding-a` (the file's first 41
functions), not `own-embedding-b` (the last 86): fewer names to keep. `AGENTS.md` is left to the
lane (*For the lane*). `set-cache.yml` is two jobs (`lookup`, `seed`), so `seed`'s steps carry no
`if:`.

### The checks, seen failing first (EXECUTED)

- Check 7 (sameness, H1), on `66cc120`: 3 failed, each new row
  (`test_a_build_run_on_linux_counts_on_the_darwin_side`, `…one_unit_short…`,
  `test_a_block_in_the_build_run_is_read_as_linux`).
- Check 5 (shards): 4 of the new rows failed (a nodes-only shard off its file's systems, a
  nodes-only shard, a function taking its cases, `names`); the named-twice row passed (an existing
  rule).
- Check 6 (gather): every row failed at `gather.Inputs(set_source=…)`, the 7 new among them.
- Checks 1 to 3 (rules), with `release/set_key.py` set aside and the base workflow: 9 failed
  (check 1, check 2, check 3's seven cases). `release/set_key.py` was written before its rules
  check, not after: this is the order the base gives, recorded as such.
- Check 1 then failed once on a finding of its own rule (K3 read `scripts/f2py-host`'s
  `build/tools/…` `PYTHONPATH` as a repository folder); the rule now skips the build's own roots.
- Check 1's mutant "the build with an argument" found a hole in the rule (a job whose build step
  had an argument was not read as building); fixed. Check 4's rows were written after
  `release/set_key.py` and fail on the base at import; each case's own failure is its mutation.

### The runs (EXECUTED, `gh run view <id> --json jobs`, minutes from the run's creation)

| | run 39468404589 (source) | run 39475482749 (reuse) | run 39481889333 (reuse) |
|---|---|---|---|
| commit | `827f826` | `827f826` | `25fcd1a` |
| `inputs` | 0.2, `reuse=false` (no entry) | 0.2, `reuse=true` | 0.1, `reuse=true` |
| build job | macOS, 29.2 (compile 24.9) | `ubuntu-24.04`, 1.7 | `ubuntu-24.04`, 1.7 |
| `build-shard` | 21.6 (compile 19.1, shard 1.7) | 20.5 | 21.9 |
| x86-64 / arm64 rebuild | 18.9 / 19.5 | 18.8 / 19.9 | **34.3** / 19.9 |
| `same-bytes` | +30.0, passed | +20.6, passed | +34.9, passed |
| `save-set` | +30.3, saved (85,904,392 bytes stored) | skipped (reused) | skipped |
| macOS shards end | +46.0 | +20.9 | +20.9 |
| last job | +46.0 | +37.0 (Linux `own-guest` timeout) | +34.9 |
| peak jobs at once | 33 | 35 | 34 |
| red lines | macOS growth only | macOS growth; Linux `own-guest` cancelled at 30 min | macOS growth only |

The gather was skipped in all three: the macOS shards are red on growth (042's rows: 41, 152, 6,
26 and 2 grown metrics, no lost pass, no failure), as on any branch run of an unaccepted set.
`set-source` and the build record's new path were therefore run by the builder:
`tests/harness/gather.py` on run 39481889333's 45 downloaded records
laid out as the gather job lays them, with `WASM_SHA256` and `SET_SUMS_SHA256` from its
`release-assets`, `SET_SOURCE` `reused wasi-python-set-v1-ad003ce1…`
(`regather.py` in the builder's scratchpad). Its red lines: 22 at G5, all `grew`, and one at G7
(the newest acceptance is not on this set). No line at G1, G2, G3, G4 or G6: `build-shard`'s
`linux-aarch64` record matched the reused set's `python.wasm` and `SHA256SUMS`; the merged
record's `meta.set_source` is the reused key and its `runs["build/build"]` is
`linux-aarch64`, 10 units.

**Against Decision 11's estimates:**

- **Reuse:** estimate about 25, up to about 35 with a slow x86-64 rebuild. Measured: the judge
  shards ended at +20.9 and `build-shard` at +20.6 to +22.1 in both reuse runs; the run's end was
  set by the x86-64 rebuild (+34.9 in run 39481889333, its 34.3-minute leg; the gather would have
  followed `same-bytes`), and in run 39475482749 by the Linux `own-guest` timeout. With a usual
  x86-64 rebuild (18.8 to 19.9), a reuse run ends at about +22.5.
- **Source:** estimate 35 to 50. Measured +46.0 (the gather would add about 0.4): the macOS build
  29.2, then `own-guest` 16.3 and `own-embedding` 14.9 on macOS. Wave 07 took 59.7.
- **macOS shards** (test minutes / tail after pytest's summary, runs 1, 2, 3):
  `own-hostile` 10.5/2.5, 12.3/3.0, 12.1/2.8; `own-guest` (with `own-runner` in runs 1 and 2)
  10.4/5.4, 10.3/5.6, 7.0/3.9; `own-embedding` 8.5/5.7, 9.1/6.0, 8.2/5.1; `own-embedding-a`
  7.0/3.1, 6.4/2.9, 5.0/2.1. By pytest's own times the halves of the embedding file were within
  20% in run 1 only (510 s and 424 s); runs 2 and 3 gave 552 s and 385 s, 496 s and 300 s. A
  boundary a few functions later would even them; it is left for the build review to weigh with
  the three samples, since a move is a judge change that only a run measures. The tail did
  not shrink with the split: 2 to 6 minutes on every large macOS shard, 13 to 17 minutes of macOS
  time a run (Decision 10).
- **Queue:** the reuse runs' macOS shards waited 0 to 3.3 minutes for a slot (seven macOS jobs on
  five; no other run was live).

### The Linux `own-guest` timeout (run 39475482749)

The leg ran "The shard" from 18:33:43 until the 30-minute limit cancelled the job; GitHub kept no
log for it (`gh api …/jobs/118811204280/logs`: `BlobNotFound`), while its siblings' logs exist.
The same bytes and the same plan passed there in 6.5 minutes in run 39468404589. Not attributed:
one sample, no log. The fold of `own-runner` into `own-guest` was the one new thing in the leg, so
it is undone (Decision 9); run 39481889333's Linux `own-guest` passed in 9.9 minutes and
`own-runner` in 0.5. For the build review: the fast tier's one other failure on this branch,
`tests/unit/test_async_tools.py::test_a_late_gate_skips_an_async_tool` under `-n 3`, passes alone;
it is a timing row of the runner's async tools, not code this specification touches.

### The tail (Decision 10; one reading, no second strike)

Read from the three runs' logs: nothing is printed in the tail; it follows every macOS shard that
starts many guests (not `upstream-macos`, not `own-rest`), on Linux and Windows it is 0.01 minute,
and it does not shrink when a shard is split. That points at the process's exit on macOS (the
runner's `atexit` handler dropping cached wasmtime engines and modules, on a 7 GB runner), not at
the judge. Not confirmed; the follow-up is the lane's to number.

### Not done

- Criterion 3 (the traced build): needs the lane's container slot.
- Criterion 7 (the seed): after landing.
- L6's `read:` comparison: see the self-check.
- Criterion 8's sameness line: the lane's, at wave 09.
