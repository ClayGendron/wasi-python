# Review of 187 — A Rust build pipeline, with orjson first

- **Date:** 2026-11-15
- **Reviewer:** an agent (Claude), a fresh sub-agent of https://claude.ai/code/session_01BD1pVHiZoxnwRv6JCqJKeC; not the author
- **Reviewed:** pull request #110 (draft), `origin/dev` `4bed5d73`...`cb2b25bb`: the pushed head `03097ea4` and three local commits (`d1d8888d`, `f01c1698`, `cb2b25bb`), with the specification, its landing notes and its pre-build review
- **Run:** 43664780183 on `03097ea4`, the head before the fixes, read once. Green: plan, `quick`, the build (arm64 Linux), `verify` on three systems, 42 judge legs. Red: 17 jobs. Skipped: the gather, the release tier, both rebuilds, `same-bytes`. No run on `cb2b25bb` yet (READ).
- **Re-ran:** `uv run pytest tests/lint -q -p no:cacheprovider` → 14 passed. The six changed unit files → 791 passed. `tests/checks/test_rules.py` and `test_upstream_files_are_well_formed` → 149 passed, 5 skipped. `harness.import_list.errors` on `dev`'s set at `338ed06d` → 43 imports in each binary, equal to `recipes/guest-imports.txt` (all EXECUTED).
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

## Verdict

Does not land yet: the merge waits on the owner, who must answer orjson's patch, yyjson and core's Unicode tables, and the allocator question in `decisions.md` (1), and give the full run (3). Findings 2 and 4 to 10 are closed on be6e47b1. Once the next run shows the above, it lands on that pushed head, and the merge goes ahead after those two owner steps.
