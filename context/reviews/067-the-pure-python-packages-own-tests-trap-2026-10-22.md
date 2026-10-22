# Review of 067 — the pure-Python packages' own tests: the asadpour trap

- **Date:** 2026-10-22
- **Reviewer:** a fresh agent (Claude Opus 5.5) that reviewed none of 067's earlier changes.
- **Reviewed:** `git diff 148529ae 1a0761a0` (one commit, `tests/` data and `context/` only: the
  trap `networkx-r-trap-asadpour-integral-held-karp`, its gap, the group's cap and budget, the
  repacked `tests/release_shards.toml`, the claim block, the README, roadmap and spec lines).
- **Kind:** judge-only (parallel-safe). Time box: 25 minutes, overrun to read the Linux records.
- **Run:** none of my own. The change touches only release-tier rows. A branch run judges the
  release tier only with `release-tier: true`, which AGENTS.md rule 3a keeps for a change to the
  release-tier CI job. So the first CI run of the new rows is the next dry run on main. The
  evidence read instead: the dry run 39741960669 on `454f8b3c`, its Linux release records
  (`gh run download 39741960669 -p "record-linux-upstream-*"`, 247 records, read while the run
  was still in progress).
- **Re-ran (EXECUTED, darwin-arm64, single node ids, no guest groups; `build/lane.lock` present):**
  `uv run pytest tests/checks/test_rules.py
  tests/checks/test_v1_3_upstream_suites.py::test_upstream_files_are_well_formed
  tests/unit/test_pure_suites.py::test_the_well_formed_family_has_no_error
  tests/unit/test_packages.py::test_the_well_formed_split_has_no_error` → 72 passed, 2 skipped
  (blocked: the artifact dir, the prior-art clones), 0 failed. `test_release_shards_cover_the_judge`,
  `test_release_judges_in_shards` and `test_known_gaps_are_well_formed` are among the passes.

## The four questions against evidence

1. **Rule 4: does the trap weaken the judge more than its reason justifies?** Mostly no; one
   Medium on the reason's words (M1).
   - The judge loses one fact: that this test passes on darwin in about 442 to 470 G. The spec
     says so plainly ("The cost, plainly"). READ.
   - The trap still guards the test's existence: its finding is `out of fuel at <node id>`, so a
     renamed or deleted test changes the digest and goes red. READ (`upstream.trap_findings`,
     `scan.digest`).
   - The gap's digest, `9176e2e5af8c`, is the digest the Linux leg printed for the same one
     finding text, so it matches on both hosts. EXECUTED (the job log,
     `build/wave-12/dryrun-r040.log`, line 462).
   - The gap says "the cause is not read". That is honest. What it does not say is in M1.
2. **The caps.**
   - 150 G against 100.2 G is 1.497 times: inside the owner's 1.5 rule. The rules check passes.
     EXECUTED.
   - darwin is deterministic here (two equal runs, the builder's). Linux, for the other 800
     release checks with fuel on both hosts, is within 2.3% of darwin, and within 1% for all
     but two. EXECUTED (the dry run's Linux records against `build/releases/0.1.0/record.json`).
   - The 44 tests that stay include six `held_karp_ascent` tests and the asadpour tests (M2).
     On Linux 43 of them passed, before the trapped test, and each asserts the ascent's exact
     output. So their path on Linux is very likely darwin's, and so is their fuel. INFERRED. Their
     Linux fuel alone is not measured; the next dry run is the check.
   - The trap's 50 G cap: the session's start costs less than 29.3 G (networkx's smallest
     release group, whole), and the test needs about 442 G or more on every host seen. So it runs
     out of fuel inside the test's node on every host, with the same one finding and the same
     digest. INFERRED from the measured groups; the spec does not record the trap's own run (L4).
   - Windows: no release-tier leg runs on Windows (`judge-release` is `ubuntu-24.04` only;
     READ, `.github/workflows/release.yml`). So the trap runs on Linux CI and in the lane's darwin
     acceptance. Where it runs, its verdict is the same: a gap.
3. **The shard repack.** Every group still sits where it did, by count, and none is dropped or
   added. EXECUTED (a comparison of the two files by `tomllib`):
   - 801 groups before and after. No group dropped, none added.
   - 256 shards before and after; 113 `upstream-pure-r-*` before and after; no other shard
     changed.
   - The three groups in two shards (`numpy-lib`, `cpython-fs`, `pandas-io-parser`) were in two
     before. No group's systems changed.
   - `networkx-r-approximation-1` moves to `upstream-pure-r-101`, with its trap.
   - The workflow's matrix names `upstream-pure-r-001` to `-113`, unchanged; the renumbered
     names still cover it. The rules checks hold this. EXECUTED.
4. **Other groups on the same code, or other host-dependent float loops.**
   - Outside `test_traveling_salesman.py`, no networkx file calls `held_karp_ascent`,
     `asadpour_atsp` or `spanning_tree_distribution`, and no other networkx module calls
     `linprog` or HiGHS. READ (`grep -rl` over `build/networkx-3.7/networkx`).
   - Inside that file, the group's other 44 tests do (M2).
   - scipy's own HiGHS and `linprog` tests run in `scipy-optimize-*` groups. On Linux they cost
     the same as on darwin, within 0.02%. EXECUTED (the Linux records).
   - Across 800 release checks the largest Linux difference is cpython-b's +2.27%, then
     `scipy-stats-1-stats-2`'s +2.23%. None is past 5%. EXECUTED. This is the Linux evidence the
     darwin variance file could not give.
   - So this one test is alone. Its Linux cost is at least about 38% over darwin's, while every
     other check agrees within 2.3%.

## Findings, most severe first

1. **Medium M1: the reason calls a different path "a fuel difference"**
   (`tests/upstream/networkx.toml`, the trap's `reason`; `tests/known_gaps.toml`, the gap's
   `reason`; `README.md`'s networkx sentence).
   - The Linux leg and the darwin acceptance ran the same artifact set (`set_sums 3339091f…`,
     `artifact d4192605…`) under the same wasmtime (49.0.0). EXECUTED (both records' `meta`).
     Fuel is a count of wasm operations. With the same bytes and the same engine, a different
     count means the guest took a different path.
   - The test's loop is `direction_of_ascent`'s `while True`. It ends only when
     `linprog(method="highs-ipm")` reports `success`. READ
     (`networkx/algorithms/approximation/traveling_salesman.py`, lines 677 to 716). If HiGHS
     answers otherwise on Linux, the loop goes on, and may never end.
   - So on Linux the test is not known to end at all. And the same `python.wasm` computes
     something different on x86_64 Linux than on arm64 darwin. That may be the product's: for
     example, NaN bit patterns, which wasm leaves to the host and which this engine does not
     canonicalize (no `cranelift_nan_canonicalization` in `src/`; INFERRED, a hypothesis only).
   - "Its fuel is not the same on every host" and "past 638 G on Linux" read as a slow test and a
     measurement nuisance. A trap should not hide a failure that is the product's. Here it may.
   - The trap itself is right for 0.1.0: the cause is not read, and a group that cannot pass on
     Linux would hold every release. The words should say what is known.
   - **Fix text** (the builder's; the same in the trap's `reason` and the gap's `reason`): "on
     Linux x86_64 it did not end within its group's 710 G cap (past about 610 G in the test, dry
     run 39741960669), against about 442 to 470 G on darwin-arm64, two runs equal; the same
     artifact set and wasmtime, so the guest takes a different path on Linux, which may be the
     product's (the held-Karp ascent loops until a HiGHS interior-point solve reports success);
     the cause is not read; run alone to its 50 G cap, so its verdict is the same on every
     host". The README sentence and the roadmap follow-up say the same, and the follow-up names
     its first probe: the test alone on Linux with a large cap and HiGHS's `success` flags
     traced, then the same run with NaN canonicalization on.
   - **Closes with:** the reworded reason (data only; the gap's digest does not change).
2. **Low L1: "no other test calls held_karp_ascent or asadpour_atsp" is false as written**
   (`context/specifications/067-the-pure-python-packages-own-tests.md`, "The same code
   elsewhere"). The group's other 44 tests include `test_held_karp_ascent`,
   `test_ascent_fractional_solution`, `test_ascent_method_asymmetric`,
   `test_ascent_method_asymmetric_2`, `test_held_karp_ascent_asymmetric_3`,
   `test_held_karp_ascent_fractional_asymmetric`, `test_spanning_tree_distribution`,
   `test_asadpour_tsp`, `test_asadpour_real_world`, `test_asadpour_real_world_path`,
   `test_asadpour_small_graphs` and `test_directed_tsp_impossible`. **Fix text:** "No test
   outside `test_traveling_salesman.py` calls `held_karp_ascent` or `asadpour_atsp` (READ). Inside
   it, the group's other 44 tests do, under the new 150 G cap: on Linux 43 of them passed in the
   dry run, each asserting the ascent's exact output; their Linux fuel is not measured, and the
   next dry run is the check." (Ranked Low because the cap is sound on the evidence above; it is
   M2 in the questions.)
3. **Low L2: the spec contradicts itself on the lost pass.** "No accepted pass is lost: the
   group is new, and its rows are not yet accepted" sits above "It costs an accepted pass".
   The second is right (0.1.0's release acceptance accepted the group at 45 passes). **Fix
   text:** delete the first bullet.
4. **Low L3: `measured` is a round number, not a run's figure** (`tests/upstream/networkx.toml`,
   `measured = 100_000_000_000`). The field is "the fuel a judge run recorded"; the run said
   100.2 G. **Fix text:** the exact integer from the run. The cap stays 150 G, under
   `rule_cap(100.2 G)` = 160 G. The spec's "about 470 G" for the test and "past 638 G" assume
   the rest costs 72 G; the rest alone costs 100.2 G, so the test is about 442 G on darwin and
   past about 610 G on Linux. Say "about 442 to 470 G" and "past about 610 G".
5. **Low L4: the trap's own run is not recorded.** The spec says the trap "reaches [50 G] on
   every host" without an EXECUTED run of `test_upstream_trap[networkx-r-trap-asadpour-integral-held-karp]`.
   **Fix text:** its node id run once on darwin, with its fuel and digest, labelled EXECUTED;
   or name the lane's release acceptance as that run.
6. **Low L5: the CHANGELOG still says six traps.** 0.1.0's 067 entry says "six sympy tests …
   are traps". With W25 and this one there are eight. **Fix text:** "six sympy tests that do not
   end within 2.9 to 4.5 T of fuel, sympy's `test_W25`, and networkx's
   `test_asadpour_integral_held_karp`, whose path is not the same on Linux, are traps, named
   with their reason."
7. **Low L6: the self-check list is not written** for this commit (`context/reviews/README.md`).
   The items that apply: no CI run on this exact commit (the release-tier rows cannot run on a
   branch run, so say that), the numbers' EXECUTED labels (L3, L4), the CHANGELOG (L5).
8. **Note N1: the claim block is right.** The new trap row is in `new`; the group's falling
   pass count is in `passes`; nothing grows. The `--accept-fewer-passes` flag exists
   (`tests/harness/plugin.py`, line 99) and its reason begins with the spec number.
9. **Note N2: the family budget falls by 510 G** (4,708 G to 4,198 G): 710 G less 150 G, plus
   the trap's 50 G. The rules check's cap sum holds. EXECUTED.

## Constitution checks

- §4 constraints: no `src/`, `scripts/`, `recipes/` or pins touched; no upstream patch; no
  artifact in git. The judge change is a change with a reason, and the judge-hash line names
  `tests/known_gaps.toml`, `tests/release_shards.toml` and `tests/upstream/networkx.toml`
  (EXECUTED, the scoreboard's ratchet line).
- §7 never-do list: rule 4 not tripped. The gap is narrow (one finding, one digest), it names
  its closer, and the follow-up has its roadmap line. M1 is about its words, not its scope.
- Structure (4a): no `src/` change; no rubric row moves.

## Verdict

Lands once M1's reason is reworded to say that on Linux the test did not end and the guest takes
a different path there, which may be the product's; the Lows are write-ins.
