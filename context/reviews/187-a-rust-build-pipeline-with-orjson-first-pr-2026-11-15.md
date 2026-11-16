# Review of 187 — A Rust build pipeline, with orjson first

- **Date:** 2026-11-15
- **Reviewer:** an agent (Claude), a fresh sub-agent of https://claude.ai/code/session_01BD1pVHiZoxnwRv6JCqJKeC; not the author
- **Reviewed:** round one: pull request #110 (draft), `origin/dev` `4bed5d73`...`cb2b25bb`: the pushed head `03097ea4` and three local commits (`d1d8888d`, `f01c1698`, `cb2b25bb`), with the specification, its landing notes and its pre-build review. Round two: `2183d5d5..e026a6ee` after the rebase onto `dev` `7deb6043`, six commits, the pushed `29162515` and one local commit, `e026a6ee`. Round three: `d4761c4e..fb4a1bc6` after the rebase onto `dev` `d4761c4e`, then, once #113's squash put this branch on `dev`, the merge of `dev` `8c34c02f` (its tree is `dev`'s) and `a746d5e4`, the whole pull request now. Round four: the branch rebuilt linearly on `dev` `cbfe00cd` with no merge, `3aac2e7c` (`a746d5e4` cherry-picked) and `aff4aeab` (round three's review, `23ab3e6e` cherry-picked).
- **Run:** 43664780183 on `03097ea4`, the head before the fixes, read once. Green: plan, `quick`, the build (arm64 Linux), `verify` on three systems, 42 judge legs. Red: 17 jobs. Skipped: the gather, the release tier, both rebuilds, `same-bytes`. No run on `cb2b25bb` yet (READ). Round two: 43771983479 on `29162515`, below. Round three: 43865484595, the owner's release-shape dispatch on `fb4a1bc6`, below. Round four: none of the rebuilt head; the merged head's run failed on rule 3 alone, by the author's word (not read here).
- **Re-ran:** `uv run pytest tests/lint -q -p no:cacheprovider` → 14 passed. The six changed unit files → 791 passed. `tests/checks/test_rules.py` and `test_upstream_files_are_well_formed` → 149 passed, 5 skipped. `harness.import_list.errors` on `dev`'s set at `338ed06d` → 43 imports in each binary, equal to `recipes/guest-imports.txt` (all EXECUTED). Round two: below. Round three: on `fb4a1bc6` and on `a746d5e4`, below. Round four: on `aff4aeab`, below.
- **Box:** 45 minutes (build-class).

Labels: EXECUTED, I ran it; READ, I read the file or log; INFERRED, my reasoning. Nothing was dispatched, pushed or labelled.

## The run's five causes

| Cause | In the log (READ) | Fix |
|---|---|---|
| orjson's tag archive | `upstream-pure-smoke-a`: SHA-256 `f2f65003…`, the pin `e314b660…` | `cb2b25bb` drops the pin and its fetch; no reference is left (EXECUTED) |
| no measured fuel | `own-rest`, Linux and macOS: `orjson-smoke records no measured fuel` | `cb2b25bb` drops the groups; the check passes (EXECUTED); finding 2 |
| panic-in-C read the wrong line | `own-guest-c`, three systems: `trapped` is the backtrace header; `trap_cause` holds `unreachable` | `d1d8888d` reads `trap_cause` (READ) |
| unclaimed growth | nine macOS shards red only on `GREW`, and `own-guest-c` | `f01c1698`; its figures match the log: +422,605 and +421,766 bytes, +0.17 % and +0.43 % fuel (EXECUTED arithmetic) |
| review | `review`, `ci-status` | this file |

All 17 red jobs fall under these five (READ). The next run on the pushed head confirms the fixes.

## Acceptance criteria against evidence

1. Pins and toolchain lines on each host — met on arm64 Linux (READ) and x86_64 locally (landing notes). macOS's toolchain is not fetched here (finding 3).
2. Step 52 offline; its gates seen refusing — the build is met (`panic=unwind, 2 objects kept, 1 dropped, 1 entropy imports shimmed`, READ). The refusals are not (finding 4).
3. Step 60's gates refuse once each — not met (finding 4). They pass on the kept archive: step 60 is `ok` (READ).
4. Imports, tags, constructors, features unchanged — met: imports are `dev`'s 43 (EXECUTED). The rest pass in step 60 and `verify` (READ).
5. A green `ci:full` run — not met: not `ci:full`, and orjson's suite does not run (findings 2, 3). `PanicException` and the entropy check passed on three systems (READ), but were never seen failing (finding 4).
6. Same bytes — two folders met (landing notes); across hosts not run (finding 3).
7. Bytes and fuel claimed; nothing new in the sweep — bytes and four figures claimed. Step 90 requires the notice tables to equal step 52's build graph, and passed (READ). Three figures are missing (finding 6).
8. Prior-art rows, `tests/lint`, news file — met (EXECUTED). `ci-status` and `review` wait on the next run.

The `imports` gate fails on any import outside `env` but `random_get`, so a direct clock import cannot pass; the link-map gate cannot pass empty (READ). One `-Cpanic=$RUST_PANIC`, held by a rule (READ). Notices: orjson's two licences, yyjson's header, the std crates, PyO3, and `COPYRIGHT-library.html` with core's Unicode tables (READ, `scripts/assemble_artifacts.py`). The allocator: finding 10.

## Findings, most severe first

1. **High, held from the pre-build review: the owner has not answered** (`context/decisions.md`; Decisions 3 and 12). orjson's carried patch can never go upstream, which §4.1 requires. yyjson's MIT and core's Unicode-3.0 tables are not named in a recorded approval (§4.12). Both defaults are the session's, not the owner's. Failure: a merge ships a standing patch and two notices on silence. Fix: none in code. The answers go in `decisions.md`, and §4.12 names yyjson and the tables if approved. Merging waits on them.
2. **Medium: orjson's own suite runs nowhere, and its `later` row closes with the specification that lands it** (`tests/upstream/packages.toml:451`; spec 063; criterion 5). `shards.py`'s rule takes any written specification as a closer, landed or not. Failure: once 187 merges, the gap names a closed closer, and `rust-std` and `pyo3` are `via` a suite that does not run. Fix: before the merge, restore the groups from the sdist, as the landing notes plan, with the smoke group's `measured` fuel read against the next run's `release-assets`. Or reserve a new specification in `roadmap.md` and close with it. Evidence: a run on which `orjson-smoke` passes.
3. **Medium: the run that judges this is not `ci:full`** (criteria 1, 5 and 6). The release tier, both rebuilds and `same-bytes` were skipped. Failure: macOS's Rust toolchain, cross-host bytes and `COPYRIGHT-library.html` are untested. Decision 12 asked that file be checked equal across hosts; the code reads one host's (`scripts/assemble_artifacts.py`, `rust_parts`). Fix: a `citest:full` line on the next commit, or the owner's label. The landing notes then name the green run.
4. **Medium: the new gates and checks were not seen failing first** (criteria 2, 3 and 5; the self-check's first box). `foreign` and `inits` have no planted refusal anywhere. The landing notes' "a `round` from the Rust archive" is the link-map row, not `foreign`'s. The entropy check, the only proof the shim routes, was never run without the shim. Failure: a gate that cannot fail would pass the same. Fix: unit rows for `foreign` and `inits` with a stand-in `llvm-nm`, and correct that note. Plant the rest once a build tree exists, or record why not.
5. **Low: stale texts.** The PR's description still lists the rules, golden job, claims and prior-art rows as to build, and says the smoke group runs. Its Windows box is unchecked. Run 43664780183's Windows legs are read: 11 of 12 green, and `own-guest-c` fails only on the panic-in-C check, which `d1d8888d` fixes. The spec's Status still says "not built". Fix: update all three.
6. **Low: three of Decision 16's figures are not recorded** (spec, landing notes). The fuel of a plain start, of `import orjson` and of the 20,000-record `dumps` is missing. "Fuel under half a percent" is not shown by the log, which prints three `GREW` rows a shard (110 grew in `own-guest-c` alone). Fix: record them from the gather of the next run, or say they are not measured.
7. **Low: step 52's line loses its byte count** (`scripts/steps/progress.sh:100` cuts at 120 columns). Fix: shorten the line, e.g. `rust: orjson 3.13.0, _rust_probe, panic=unwind, 2 kept, 1 dropped, 1 shimmed, <n> bytes`.
8. **Low: `docs/contributing/adding-a-package.md` names the wrong line form.** It says `<module>=PyInit_<name>`; `modules.txt` takes `<dotted name> PyInit_<name>`. Fix: that text.
9. **Low: our two crates say `license = "MIT"`** (`recipes/rust/modules/Cargo.toml`, `probe/Cargo.toml`). The project is Apache-2.0, and Decision 9 says the probe's licence is the project's. Fix: `license = "Apache-2.0"`.
10. **Low: the allocator question lives only in the landing notes.** AGENTS.md asks it of the owner with AskUserQuestion. For 187 the risk is not live. wasi-libc's dlmalloc defines `MALLOC_ALIGNMENT 16` (READ, `dlmalloc/src/dlmalloc.c:31`, the clone's `main`). The types above 16 in 187's crates are orjson's `SmallFixedBuffer` (64) and `ContainerSerializer` (128), zmij's table (64) and simdutf8's temporaries (32). None is put in a `Box` or a `Vec`: each is a local or a static, aligned by the compiler and the linker, not the allocator. hashbrown's tables align to 8. So no heap allocation above 16 happens today (INFERRED from a grep of orjson `bd00937c` and the crates, READ; PyO3 0.29.3's source was not here, and 0.30.1's two such types are in its tests). Fix: ask the owner before pydantic-core's specification, with this reading as the evidence.

## Constitution checks

- §4.1: waits on the owner (finding 1). The crate trees carry per-file checksums and join the tree check; 42 trees pass (READ).
- §4.2: every Rust input pinned and verified (READ). §4.4: one direct import, routed; no new import (EXECUTED). §4.12: notices ship; two approvals wait.
- §7 and "never weaken the judge": `dev`'s judge only gains; the removed suite files never reached `dev` (EXECUTED diff). The claim `tests/checks/*` is a prefix: read the next gather for any row it would hide.
- 4a: no `src/` change; not structural. 4b: `release.yml` changes comments and the tree count, 41 to 42; runs, refusals and tokens unchanged. `release/set_key.py`'s `GATES` adds `harness.import_list`. All 23 trailers name Claude Opus 5.5 (EXECUTED).

## Disposition (filled in by the author, then confirmed by the reviewer)

1. **The owner's; left.** Nothing in code. The spec's "Open for the owner" line holds both questions, and the pull request stays a draft until `decisions.md` has the answers.
2. **Fixed by a reservation, not by measurement** (`be6e47b1`). Measuring the smoke group here was tried: run 43664780183's `release-assets` artifact could not be fetched, since the proxy refused the artifact store's host, and no set is built in this container. So `roadmap.md` reserves 192 for orjson's own suite, and `packages.toml`'s `later` row closes with `spec 192`, which the rule accepts as reserved (`test_every_package_names_its_own_suite`, EXECUTED). 192 restores the groups from the sdist with the smoke group's `measured` fuel and expected classes, read against a set 187 built, and names orjson a suite again. The landing notes say so. The number is a proposal: the coordinator may renumber it.
3. **The owner's; waits.** The merge-grade run waits for the owner: a `ci:full` label, or their go-ahead for a `citest:full` commit line (`AGENTS.md` step 6; `release/ci_plan.py`, `FULL_LINE`). A first full run of the Rust pipeline is not yet known to pass, so the round-1 commit carries no such line, and the landing notes say so. They name that run once it is green.
4. **Fixed at unit level** (`be6e47b1`). `tests/unit/test_rust_objects.py` gains eight rows with `llvm-nm` and `llvm-cxxfilt` stood in. `inits` covers an init the list does not name and a listed one missing. `foreign` covers `round` and `__multi3` defined beside libc and compiler-rt. `imports` covers an entropy import entry the shim would miss and an undefined name that is not `random_get`. Each was seen red with its check removed from `scripts/rust_objects.py`, then green with the check restored (EXECUTED). The landing note now credits the `round` row to the link map. The guest's entropy check needs a set linked without the shim, so it waits for a build tree, and the landing notes record why.
5. **The coordinator's** (the description and its Windows box). The spec's Status line is updated in `be6e47b1`.
6. **Fixed in the text** (`be6e47b1`). The landing notes give the two fuel rows the log shows and leave the rest to the next run's gather. A plain start, `import orjson` and the 20,000-record `dumps` are said to be not measured here.
7. **Fixed** (`be6e47b1`). Step 52's line is `rust: orjson <v>, _rust_probe, panic=<s>, <k> kept, <d> dropped, <n> shimmed, <bytes> bytes`, under 120 columns. It is a deviation from the design's form, recorded in the landing notes.
8. **Fixed** (`be6e47b1`). The page says `<dotted name> PyInit_<name>`.
9. **Fixed** (`be6e47b1`). Both crates say `license = "Apache-2.0"`.
10. **Moved to the owner's questions** (`be6e47b1`). The spec's "Open for the owner" line asks it as a third question, for before pydantic-core, with this review's reading that it is not live in 187.

## Reviewer's confirmation (round one, on be6e47b1)

be6e47b1 is 497714b8 with one landing-notes line of the spec reworded and no `citest` line; the code is the same, so the checks run on 497714b8 hold (EXECUTED: `test_rust_objects.py` and `test_build_scripts.py` 95 passed, `test_rules.py` 148 passed and 5 skipped).

1. Open; the owner's.
2. Confirmed: 192 is reserved in `roadmap.md` and `closes_with = "spec 192"` passes the rule. orjson's tests ship with 192, not before.
3. Accepted as answered in writing: the full run is the owner's step. Criteria 1, 5 (the release half) and 6 stay unevidenced until it is green, and it must be green before the merge.
4. Confirmed at unit level: the eight rows were each seen red. The guest entropy check's seen-red waits on a build tree, as the landing note says; accepted.
5. Confirmed for the spec's Status line; the PR description is the coordinator's.
6. to 10. Confirmed: the figures are labelled, step 52's line fits 120 columns, the line form reads `<dotted name> PyInit_<name>`, both crates say Apache-2.0, and the allocator question is the owner's third.

The next run on the pushed head must show:
- quick and the build green, with the new step-52 line and its bytes;
- own-guest-c green on all three systems, including the panic-in-C row (`trap_cause`, and stderr holding "probe in c");
- own-rest and upstream-pure-smoke-a green;
- macOS's GREW rows under GROWTH with 187's reason;
- review and ci-status green.

## Round two, on `e026a6ee`

Re-ran on `e026a6ee` (EXECUTED, each):
- `uv run python release/precheck.py` → fails only `tests/unit/test_runner_grants.py::test_the_walk_judges_links` (root-only, as on `dev`) and the plan's two notes that the review waits; ruff, mypy, the rules checks, their times and lint are ok.
- `tests/unit/test_budget.py`, `tests/unit/test_gather.py` and `tests/lint` → 217 passed. `tests/checks/test_rules.py` → 149 passed, 4 skipped.
- A mutant without the gather's `fresh` line → the new gather row fails.
- Unit collection: `dev` 3,758, `2183d5d5` 3,801, `e026a6ee` 3,803.
- `new_family_fuel` with an upstream node of a new package, in an accepted file → `[]`.

Run 43771983479 on `29162515`, read once (READ). 81 jobs: 66 green, 13 skipped, 2 red. Green: plan, `quick`, the build (built, not reused; step 52 printed `rust: orjson 3.13.0, _rust_probe, panic=unwind, 2 kept, 1 dropped, 1 shimmed, 603470 bytes`), `verify` on three systems, 31 Linux, 14 macOS and 12 Windows judge legs, `own-guest-c` on all three among them, `own-rest`, `upstream-pure-smoke-a` and the gather. Red: `review` and `ci-status`; `ci-status` names only this file's two refusals. Skipped: both rebuilds, the release tier, `same-bytes` and the publish and accept jobs. Gather: `1240/2377 pass · 132 gap · 7 blocked · 0 fail`; macOS's `GREW` rows under GROWTH with 187's reason; three `budget:` lines report `test_v1_3_rust` as a new family, largest fuel 1,467,206,264, by `test_orjson_json_job_matches_native`. Every item round one asked of this run is there.

What changed:
- `10d4a6e7`, `1f334255`, `2fa07ac4`: three entries in `decisions.md`. The spec's Status, Decisions 3 and 12, its landing notes and the facts sheet now cite them, with no provisional wording left (READ, grep). They agree: the patch stands and is checked at each orjson version; the maintainer's address is in the facts sheet; the crate type stays; yyjson and `core`'s tables ship under the approved MIT and Unicode-3.0; patch 0003 is pydantic-core's.
- `c1e8034b`: one blank line in `tests/unit/test_scan.py`; format only (READ).
- `29162515`: the judge changes and only reports. `new_family_fuel`'s lines join `reported`, never `red`. `findings`, `run_fuel_over` and lint's caps are untouched (READ; the mutant above). Neither the new function nor the header note raises a cap. The cap of 100,000,000,000 lived only on this commit and its run, the family's first.
- `e026a6ee`: the cap is 2,934,412,528, twice 1,467,206,264 (EXECUTED arithmetic), the same figure on three systems (READ). Lint passes with it.

### Findings, round two

11. **Medium, held from round one: the merge-grade run has not run** (finding 3; criteria 1, 5's release half and 6). The release tier, both rebuilds and `same-bytes` were skipped again. Failure: macOS's toolchain build and the cross-host bytes are unseen. `COPYRIGHT-library.html` is read from one host (`scripts/assemble_artifacts.py:1087`), and `same-bytes` is the only check that the hosts agree. Evidence that closes it: a green `ci:full` run on the pushed head. Or the owner's word, recorded in `decisions.md`, that this pull request merges on the normal tier and those criteria move to 0.1.5's release pull request.
12. **Low: the news file's `units` is 43, and the branch adds 45** (`context/changes/187-a-rust-build-pipeline-with-orjson-first.md`). `29162515` adds two unit rows. Fix: `units = 45`.
13. **Low: a new upstream package is never reported** (`tests/harness/budget.py`, `new_family_fuel`). It treats a family as seen by its file. Every upstream check shares one accepted file, so orjson's suite under 192 would get no line. The docstring and `budget.toml`'s header promise every family. It only reports, so nothing passes that would fail. Fix: `seen = {family(n) for n in accepted.get("checks", {})}`, with a unit row of an upstream node whose package is new. Or narrow both texts to "a check file".
14. **Low: §4.12 does not name yyjson or `core`'s Unicode tables** (`context/constitution.md`). Round one's fix asked that it should. The new decision says §4.12's text covers them, but that text names Unicode-3.0 only for ICU4X. Fix: after "foldhash (Zlib)", add "; yyjson, vendored in orjson (MIT), and the Unicode tables in Rust's `core` (Unicode-3.0), approved 2026-11-15 (`decisions.md`, "yyjson and Rust's Unicode tables are covered")". Add the matching Status line.
15. **Low: stale texts.** The spec's Status says pull request #105 is "not yet on `dev`"; it is `8d85302a`. The description still opens "Provisional defaults, waiting on the owner". Its first two boxes are unchecked, and "Still to build" lists built work. The 12 Windows legs of 43771983479 are green (READ). Fix: drop "not yet on `dev`", and update the description (the coordinator's).

### Round one's findings

1. Closed (READ), apart from finding 14.
2. Holds: 192 is reserved and `closes_with = "spec 192"`.
3. Open: finding 11.
4. Holds. The guest's entropy check has still not been seen failing; its landing note says why.
5. Closed for the spec. The description is finding 15.
6. to 10. Hold.

## Round three, on `fb4a1bc6`, then `a746d5e4`

Reviewer: an agent (Claude), two fresh sub-agents of https://claude.ai/code/session_01BD1pVHiZoxnwRv6JCqJKeC; not the author. The first read `d4761c4e..fb4a1bc6` and stopped before the verdict. The second read the branch as it now stands and wrote the verdict. Nothing was dispatched, pushed or labelled.

Read. First, `d4761c4e..fb4a1bc6`: 35 commits after the rebase onto `dev` `d4761c4e` (191, #112), and the four since round two, `ae8934db` (Lows 12 to 15), `5801a25c` (the crates' identity), `28c9cfe5` (the units count) and `fb4a1bc6` (the getset tables). Then the branch now:
- The owner squash-merged #113, which was stacked on this branch, into `dev` as `cbfe00cd`. So `dev` holds every commit here through `fb4a1bc6`. `dev` also holds #114 (182, `92d5d6b5`).
- `8c34c02f` merges `dev`. Its tree equals `dev`'s: `git diff 8c34c02f origin/dev` is empty (EXECUTED).
- `a746d5e4` is finding 16's fix. `git diff origin/dev a746d5e4` is the whole pull request now: two files, 4 lines added and 1 removed (EXECUTED).
- Both new commits carry Claude Opus 5.5's trailer (EXECUTED). GitHub's head is still `fb4a1bc6`, so the two are not pushed (READ, `git ls-remote`).

Re-ran on `fb4a1bc6` by the first sub-agent (EXECUTED, each):
- `uv run python release/precheck.py` → fails only `tests/unit/test_runner_grants.py::test_the_walk_judges_links` (root-only, as on `dev`; 1 failed, 3,713 passed, 104 skipped) and the plan's two notes that the review waits; ruff, mypy, the rules checks (149 passed, 4 skipped), their times and lint (14 passed) are ok.
- The touched unit files (`test_rust_ids`, `test_rust_objects`, `test_budget`, `test_callbacks`, `test_scan`, `test_gather`) → 848 passed.
- Two mutants. The getset scan given the old references again → 2 rows of `test_callbacks.py` fail (the stray word and the stray constant). `rust_ids` naming a host dependency by its id, not `host` → `test_a_guest_crates_id_is_the_same_from_every_host_and_checkout` fails. Both restored.
- Unit collection: `dev` `d4761c4e` 3,759, `fb4a1bc6` 3,818: 59, the news file's `units`.
- Trees: `test_source_tree_matches_its_tarball` collects 44; `recipes/patches` holds 36 patches (35 on `dev`, and orjson's). `release.yml` asks for 44 in its three places.
- The old and the new getset scans on the pre-187 `python.wasm` of the scratch set `pytz-start/z1`, the kept tables compared → old 449 tables, new 448; coverage the same, 2,948 getset entries, 5,665 method-array entries, 4,293 single definitions, 842 members, no finding in either. The one table dropped is a one-entry table whose entry is `tag_name`, cairo's, which the parser-rule check already skipped. So the narrowing keeps every table it checked.

Re-ran on `a746d5e4` by the second sub-agent (EXECUTED, each):
- `uv run python release/precheck.py` → fails only `test_the_walk_judges_links` (root-only; 1 failed, 3,736 passed, 104 skipped). ruff, mypy, the rules checks (151 passed, 4 skipped), their times and lint (14 passed) are ok. The plan has one note, that the review waits: this file is not yet among the changed paths against `dev`. The author's commit of it clears that.
- `test_callbacks_have_the_types_cpython_calls` on the scratch set `pytz-start/z1`, with the 2,900 floor → 1 passed. Its coverage is 2,948 getset entries, so the floor sits 48 under it.
- Class digests rebuilt from run 43865484595's three red messages with `upstream.class_findings` and `scan.digest`, below. As a control, `fb4a1bc6`'s list of `jinja2-r-no-asyncio-loop` gives its gap's `104 finding(s), digest 959d6ba605ec`.

What changed:
- `ae8934db`: `new_family_fuel` sees a family by its name (`family(node)`), with a unit row of a new upstream package beside an accepted one (finding 13). §4.12 names yyjson (MIT) and `core`'s Unicode tables (Unicode-3.0), with the Status line (finding 14). The spec's Status reads #105 as on `dev` as `8d85302a` (finding 15's spec half). All READ.
- `5801a25c`: `scripts/rust_ids.py`, a `RUSTC_WRAPPER`, replaces each compile's `-C metadata` with a hash of the compile: arguments with the root made one word, cargo's hashes, output and search folders and reporting flags left out, each guest dependency by its `.rustc-id`, a host dependency by its name alone. `-C extra-filename` stays cargo's. `keep` writes the umbrella's object as `wasi_python_rust.o` and refuses two umbrella objects. Step 52 writes the wrapper and passes `RUSTC_WRAPPER` after the host's is unset (READ). The two `STEP_52_WORDS` rows are a judge change that only adds refusals; `scan.py` is not verdict-bearing (`paths.VERDICT_BEARING`), so it needs no claim, and the news file's scan row covers it. The cause in the landing notes (a host compile's `rustc -vV` reaching a guest crate's hash through its build scripts and proc macros) was EXECUTED there. That a real arm64 or macOS rustc writes the same code was INFERRED until `same-bytes`; run 43865484595's `same-bytes` is green (READ, below).
- `28c9cfe5`: `units = 59` (finding 12, then the later rows).
- `fb4a1bc6`: a judge change, claimed in `[claim.judge]`. A getset table counts only where CPython reaches one: a static type's `tp_getset` (124 bytes past an immortal reference count), a `Py_tp_getset` (73) slot, or an `i32.const` stored at offset 124. Method and member tables keep the old rule. It narrows what is read, so it could weaken the judge; on the 0.1.4-era binary it does not (above), and two of its four new rows hold that a real table is still read.
- `a746d5e4`: `CALLBACK_MINIMUMS` sets `"getsets": 2_900`, with a comment that says why in words. Its `[claim.judge]` row names `tests/checks/test_v1_3_data_stack.py` (READ). The judge only gains: the floor rises, and nothing else moves.

Run 43865484595, the owner's release-shape dispatch on `fb4a1bc6`, read once (READ, `actions_list` and three job logs). 148 jobs: 135 green, 3 red, 10 skipped.
- Green: plan, `quick`, the build (arm64 Linux), both rebuilds from the pins (x86_64 Linux, with the build shard, and macOS 15), `the same bytes from every host`, `verify` on three systems, the PyPI rehearsal (`rehearse PyPI's signer and read-back`), every normal-tier judge leg (31 Linux, 14 macOS, 12 Windows), and 66 of the 68 release-tier legs.
- Red: `upstream-release-039` and `upstream-release-041`, then `ci-status`. Its only line is `a job this check needs neither succeeded nor was skipped: judge-release`, with `REFUSALS: []`.
- Skipped: `review` (a dispatch has no pull request to read), the gather, and the publishing, attesting and acceptance jobs.
- Each red leg fails only on a class gap whose count moved, with `lost 0 · absent 0 · unrun 0 · gained 0 · grew 0` against `80d725a9a3`:
  - 039: `jinja2-r-no-asyncio-loop-error` is 19 findings, digest `54478dcb2e88`; its gap holds 13, `ba56b641f579`.
  - 039: `jinja2-r-no-asyncio-loop` is 112 findings, digest `7623e94ffbea`; its gap holds 104, `959d6ba605ec`.
  - 041: `fonttools-r-rest-counted-clock` is 4 findings, digest `02b4b38a0999`; its gap holds 2, `0c61ab6175e3`.

These are the classes spec 182 (#114, now on `dev`) gives `collector_moves`. A class's findings are its members, plus `+id` for each that joined its list and `-id` for each that left. The log cuts each message at five members, so the members were rebuilt from the digests (EXECUTED):
- `fonttools-r-rest-counted-clock`: one membership gives `02b4b38a0999`. `TimerTest::test_split` joined; nothing left. Under 182's rule (`test_split` left out) it gives `2 finding(s), digest 0c61ab6175e3`, `dev`'s gap. Clears.
- `jinja2-r-no-asyncio-loop-error`: 19 = 13 + 2 × 3, so three joined. One membership gives `54478dcb2e88`. `test_simple_reject[<lambda>0]`, `test_simple_select_attr[<lambda>1]` and `test_sum_attributes[<lambda>0]` joined. `test_join_attribute[<lambda>1]`, `test_simple_select_attr[<lambda>0]` and `test_sum[<lambda>1]` left. All six are among the nine named moves. Under 182's rule it gives `9 finding(s), digest 1891e18dfe2d`, `dev`'s gap. Clears.
- `jinja2-r-no-asyncio-loop`: 112 = 104 + 2 × 4, so four joined. For 182's rule to pass, the four named moves not in the list must be the ones that joined, and only the two named moves in the list may leave. Every membership of that kind was tried, and also those where up to four of any listed tests leave. None gives `7623e94ffbea`. So on `fb4a1bc6`'s bytes a test outside the six named moves joined this class, or a stable member left it. 182's rule holds this class red there (finding 18).

### Findings, round three

16. **Low: the getset floor is far below what is checked** (`tests/checks/test_v1_3_data_stack.py:789`). The scan now reads a getset table only through three patterns. A table reached another way (a store whose address is a constant and whose offset is 0, say) would drop out without a word: the floor is 1,000 and the binary checks 2,948. Fix: `"getsets": 2_900` in `CALLBACK_MINIMUMS`, so a narrowing that loses real tables is red. A judge change: claim it. **Closed on `a746d5e4`:** the floor is 2,900, 48 under the 2,948 the scratch set checks, and the check passes there (EXECUTED). Its claim row is in `[claim.judge]` (READ).
17. **Low: the description is stale** (finding 15's half, the coordinator's). It still opens "Provisional defaults, waiting on the owner". Its first two boxes are unchecked. "Still to build" lists work that is built and on `dev`. The replacement text is in the report, not in this file.
18. **Medium, on `dev`, not on this diff: `jinja2-r-no-asyncio-loop` moves beyond its named tests on 187's bytes** (`tests/upstream/jinja2.toml`, the class's `collector_moves`; run 43865484595, `upstream-release-039`). The rebuilt digests show that 182's six named moves do not cover how this class moved on `fb4a1bc6`'s set (above). 187's code reached `dev` in #113's squash merge, and `dev` now links pydantic-core too, so the next set's allocations differ again. No post-merge run judges the release tier. Failure: the 0.1.5 release pull request is red on this class, and nobody has looked at it until then. Fix: on `dev`, not here. The next release-tier run's moved line names the tests. Then a change to the class (more named moves, with their reason), which is a judge change of its own, or a reason in the release ledger. This pull request's diff cannot fix it: it is the getset floor alone.
19. **Low: the branch carries a merge commit** (`8c34c02f`; AGENTS.md step 4 says "never by a merge commit"). A rebase would have replayed 35 commits that `dev` already holds as one squash. The merge's tree is `dev`'s exactly, the head's diff is `a746d5e4` alone, and the squash merge keeps `dev` linear. Answered in writing; no fix.

### Round two's findings

11. Closed for this pull request (READ, run 43865484595). Criterion 1: macOS's toolchain built the set; the macOS rebuild is green. Criterion 6: `same-bytes` is green. Its `SHA256SUMS` lists the licences, so `COPYRIGHT-library.html` agrees across the three hosts (READ, `release.yml`'s comment). Criterion 5's release half: 66 of 68 legs are green. The other two are red only on three collector-timing classes. Two of those clear under 182's rule, now on `dev` (EXECUTED, above). The third moves to finding 18, on `dev`.
12. Closed: `units = 59`, which the collection shows (EXECUTED).
13. Closed: a family is seen by its name, with its unit row (READ, EXECUTED in the 848).
14. Closed: §4.12 and the Status line name both (READ).
15. Closed for the spec. The description is finding 17.

## Round three verdict (2026-11-16; replaced)

Lands on `a746d5e4`. The pull request is now `a746d5e4` alone: it raises the getset floor to 2,900 and claims it, so the judge only gains (16, closed). The merge-grade run 43865484595 is green apart from three collector-timing classes (11, closed). 182 on `dev` clears two of them. The third is finding 18, a Medium carried to `dev` and the 0.1.5 release pull request, because 187's code is on `dev` already and this diff cannot fix it. 17 is the description, the author's. 19 is answered in writing. This file is committed after `a746d5e4` as the branch's last commit.

## Round four, on `3aac2e7c`

Reviewer: an agent (Claude), a fresh sub-agent of https://claude.ai/code/session_01BD1pVHiZoxnwRv6JCqJKeC; not the author. Nothing was dispatched, pushed or labelled.

Read. The merged head's pull-request run failed on rule 3 alone, `test_this_repository_is_linear`, on the merge `8c34c02f`, by the author's word (not read here). The author rebuilt the branch on `origin/dev` `cbfe00cd` with no merge. The old head is kept as the local branch `backup/187-merge` (`23ab3e6e`). GitHub's head is still `23ab3e6e`, so the rebuild is not pushed (READ, `git ls-remote`). The shas, old to new: `8c34c02f`, the merge, is dropped, and the new commits sit on `cbfe00cd`, which is that merge's tree. `a746d5e4` becomes `3aac2e7c`, and `23ab3e6e` becomes `aff4aeab`. Round three's shas are the old ones; read them through this map.

Re-ran (EXECUTED, each):
- Trees: `HEAD^{tree}` and `backup/187-merge^{tree}` are both `41855d86`, and `3aac2e7c`'s tree is `a746d5e4`'s (`f2bebf94`).
- Merges: `git rev-list --merges origin/dev..HEAD` is empty. Rule 3 skips here with "needs: git history", because this clone is shallow. So I ran its query, `git rev-list --merges HEAD`, by hand. It finds no merge among the 64 commits it reaches. On `backup/187-merge` it finds `8c34c02f`, as a control.
- The change: `git diff origin/dev 3aac2e7c` equals `git diff 8c34c02f a746d5e4`, line for line. `3aac2e7c`'s own diff equals `a746d5e4`'s, and `aff4aeab`'s equals `23ab3e6e`'s. That is two files, 4 lines added and 1 removed: the getset floor of 2,900 and its `[claim.judge]` row. Both commits' trailers are Claude Opus 5.5.
- `uv run python release/precheck.py` → exit 1 on the allowed root-only `test_the_walk_judges_links` alone: unit 3,736 passed, 104 skipped (round three's count); ruff, mypy, the rules checks (151 passed, 4 skipped), their times and lint (14 passed) ok; the plan refuses nothing.

### Findings, round four

None. Round three's findings stand as they were, but for 19:
- 16: closed, as before. 17: the description, the author's, as before.
- 18: **Medium, on `dev`, not on this diff**, as round three wrote it. It is carried to `dev` and to the 0.1.5 release pull request.
- 19: **Low, the merge commit** — moot. The branch carries no merge, so AGENTS.md step 4 holds. Round three's reason for the merge was that a rebase would replay 35 commits `dev` already holds. The rebuild avoided that by replaying only the getset floor onto `dev`.

## Verdict

Lands on `3aac2e7c`. The branch is rebuilt linearly on `dev` `cbfe00cd` with no merge, so rule 3 holds. Its tree is the merged head's, and its diff against `dev` is `a746d5e4`'s alone, the getset floor, so the judge only gains. The precheck holds but for the allowed root-only test. 19 is moot. 18 is a Medium carried to `dev` and the 0.1.5 release pull request, which this diff cannot fix. 17 is the description, the author's. No run of this head was read.
