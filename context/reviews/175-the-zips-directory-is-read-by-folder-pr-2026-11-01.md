# Review of 175 and 176 — The zip's directory is read by folder; the end of a call frees nothing

- **Date:** 2026-11-01
- **Reviewer:** an agent (Claude), a fresh sub-agent of Claude Code session 0672b924-ca3c-4b6c-91ca-f834537cb1bc; not the author
- **Reviewed:** `7e1ac554..70bed2f1` (pull request #89) with both specifications, their pre-build reviews, both news files, the release ledger's block and the self-check; then the rebase onto `9c0d879e` (`git range-diff 7e1ac554..70bed2f1 9c0d879e..78028179`: only the ledger block moved, to `context/release-claims/176-the-end-of-a-call-frees-nothing.toml`) and the round's fix commit `78028179..b69627d7`
- **Run:** 41274232306 on `b69627d7`: the gather and every judge shard green, all 11 windows-2025 legs included (relayed by the coordinator; one `gh pr checks 89` by the reviewer: 45 passed, red only `ci-status`, waiting on this file). The earlier run, 41263314354 on `70bed2f1`, was superseded before it finished. No flip of tqdm-smoke's `tests_perf.py` tests was reported.
- **Re-ran:** EXECUTED on the worktree's rebased set (`build/artifacts`), arm64 Mac:
  - `test_v1_4_the_end_of_a_call.py`, `test_v1_3_the_zips_directory.py` and `test_v1_3_data_stack.py` (`-n 6`) → 222 passed, 1 skipped (171's oracle: "needs: oracle"), exit 0; `tests/lint` with both reader and writer unit files → 137 passed; ruff clean on `src` and `tests`.
  - A scratch driver: a bare call and a pandas groupby, whole and ended by `os._exit(0)`, on `artifacts-dev2`, `-175`, `-176` and the final set, each equal to the landing notes' figure; an allocation churn (Finding 2); a load that raises (Finding 1); a crafted table on the host (Finding 3).
  - Both binaries' imports with the judge's parser: `host` and `wasi_snapshot_preview1` only; the plain binary's one memory has flags 0.
  - On `b69627d7`, with the set rebuilt from it (its frozen reader holds `_fits`): the unit, lint and both release-ledger rules rows → 141 passed; `test_v1_3_the_zips_directory.py`, `test_v1_4_the_end_of_a_call.py` and the callback and start-factor rows (`-n 6`) → 183 passed, exit 0, the two new guest rows among them. My audit-hook probe now gives `second {'a': 1}` on the plain binary, and my crafted table falls back to the full read, its phantom entry gone.
- **Box:** 45 minutes; overran to read the run; the round's re-read 20 minutes.

## Acceptance criteria against evidence

**175.** 1, the writer's rows, and 2, the reader's rows: met (EXECUTED); no row has a load that raises anything but `OSError` (Finding 1). 3, the guest's readers: met (EXECUTED, 36 rows), 171's oracle row left to the run. 4, the per-member bounds and the pop row: met (EXECUTED). 5, the numbers: met (EXECUTED): plain start 284.4 → 132.4 M with both (47.6% with 175 alone), snapshot 54.8 → 35.2 M (−13.1 M alone); import pandas READ. 6: see **Run**.

**176.**
1. (a) Met: every export refuses under 10,000 fuel after `run` and `shutdown` (EXECUTED); `src/` is unchanged, so the host paths READ before stand.
2. (b) Met (EXECUTED): every growth and room row, the failed `new` without a trap, the no-limit churn. The Pillow row proves R1's case: a 4 MiB `calloc`, outside Python's domains, with 1 MiB of room, after a 10 MiB block teardown keeps. Only the wrappers drain in time; a pass-through variant failed it.
3. (c) Met (EXECUTED). The 64 KiB pieces sit under the budget, so an early hook shows as growth (917,504 bytes on that variant, READ).
4. (d) Met (EXECUTED above).
5. Met (EXECUTED): 45 probes, three tracemalloc probes and the session equal native on both binaries. Tracing at the end installs no hook; tracemalloc started in a finalizer wraps the hook soundly and puts it back.
6. Met as written (EXECUTED). The 22 M and 36 M bounds are honest: Decision 8 set the restatement rule before the build, and both fail on 175's set (23.3 M, 40.1 M), so the check still tells 176 from 175. The wrappers cost +0.61% on the snapshot's bare call, so the L3 rule applies. Each of its four whole calls is cheaper: 135.3 → 132.1 M and 41.6 → 35.2 M bare, 5,039.9 → 5,005.7 M and 4,766.1 → 4,730.3 M grouped. A fifth is not (Finding 2).
7. See **Run**.

**Asked.** Only the wrappers call the five C allocators. None of the five is in the table, a `ref.func` or an export. Only `sbrk` grows memory, called by dlmalloc and by mimalloc, never selected (`obmalloc.c:431-444`) (EXECUTED). The budget counts dlmalloc chunks. It drains before a request would cross it. A NULL drains and retries once, `realloc(p, 0)` excepted (READ). `skipping_hooks` types each hook by its `PyMemAllocatorEx` field, so CPython's indirect calls match (READ). Moving them to data changed only the table's order; the scan passes, its coverage unchanged (EXECUTED; Finding 4). `START_FACTOR` 3 is the stricter gate. At the measured ratio, 3.76, a snapshot start may grow 8.9 M before the check turns red; at the specification's 2 it could grow 31 M. Recorded in the landing notes and the claim.

## Findings, most severe first

1. **Medium: a folder load that raises anything but `OSError` loses the folder for the rest of the call** (`recipes/zip_directory.py`, `_load`: `state[1].pop(folder, None)` runs before the read). EXECUTED on the plain binary: an audit hook raises `RuntimeError` once, on the `open` inside `_load`. The first `import tomllib` raises it. The second `import tomllib` raises `ModuleNotFoundError: No module named 'tomllib._parser'` for a member that exists. On the snapshot the second import succeeds, as it does natively. A `MemoryError` from `fp.read` near the cap is the same path (INFERRED). So is an audit hook that imports from the folder being loaded: it finds the folder no longer pending and not yet merged. Fix text: "`_load` reads the run with `get` and pops it only after `_merge`. A load that raises anything but `OSError` leaves the folder pending, so the next trigger loads it." Add a unit row in `test_zip_directory.py`: a stub `open_code` that raises `RuntimeError` once, after which the load succeeds and the dict equals `_fast`'s. Closed by that commit with the row green.
2. **Low: 176 is not a net saving for a call that allocates much and holds little at its end.** EXECUTED, the churn, from 175's set to 176's (same tree): plain 4,153,737,054 → 4,169,801,552 (+0.39%); snapshot 4,166,800,598 → 4,176,852,980 (+0.24%). The unarmed wrappers cost more there than teardown saves. Against `dev`, 175's start saving still covers it: snapshot 4,180,056,929 → 4,176,864,591. The specification accepted up to 0.5% on a call's body, so this is no Medium. But the news file's CHANGELOG line and `fuel.md` say only that a call ends cheaper, and the PR description says "every whole call measured uses less fuel than before". Fix text, appended to 176's CHANGELOG line and to `fuel.md`'s Finalization bullet: "Every allocation now checks one flag, so a long call that allocates much and holds little at its end costs up to about 0.4% more." The landing notes record the churn row beside the four.
3. **Low: a crafted table can add an entry the full read lacks** (`_by_table`). The init run's offset is never checked to fall on an entry boundary, and a load re-adds only the names it parses. EXECUTED on the host: an `init` offset that points into a member's extra field, at a forged central header, puts `pkg/__init__.py` into the dict. `_load` leaves it there. Only the stdlib zip is tabled, and it is ours and hashed, so this cannot be reached, but Decision 5's "a wrong table never yields a wrong dict" is too strong. Fix text: "`_load` checks that each `__init__` entry read at start equals its entry in the loaded run, and falls back otherwise."
4. **Low: the recipe orders its function table for the judge's scan.** `callbacks.py`'s docstring says table indices 1 to 20 are parser rules. Index 1 is `let_go`, and the scan passes FreeType's BDF record only because `let_go` happens to have a method's type. A write-in for a later judge change: recognise that record by its first name (`ADD_STYLE_NAME`), so no recipe has to keep its hooks in data for the scan's sake.
5. **Low: the self-check's Windows box is unticked.** Fix text: tick it once the orchestrator has read run 41263314354's Windows legs, naming the run.
6. **Low: the news files' growth figures are the pre-rebase set's** (python.wasm 99,511,775 → 99,516,652; the zip 57,068,536 → 57,071,318). Fix text: give the rebased figures from the landing notes (the zip +2,815 bytes, python.wasm +20,644, the snapshot −90,865, against `dev` at `a0b1171d`). Context only.

## Constitution checks

- §4.1: recipes only; nothing under `recipes/patches/` and no new download. §4.6, §4.9: the bytes claimed; every row counts fuel, bytes or outcomes. §5.6: both pre-build reviews signed and cited.
- Not structural: nothing under `src/` changes. The new comments name no specification, memo, review or `context/` path; `tests/lint` passes.
- The judge: every moved bound, harness field, shard and budget line is claimed with its reason; the retired pair returns renamed with tighter bounds. §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Fixed in `b69627d7`: `_load` takes the run with `get` and pops it after `_merge`, so any exception but `OSError` leaves the folder pending, and a re-entrant load of the same folder merges harmlessly twice. A unit row (`test_a_load_that_raises_leaves_its_folder_pending`) and a guest row (`test_a_load_that_raises_is_tried_again`). Confirmed (READ, EXECUTED).
2. Fixed: the CHANGELOG line and `fuel.md` state the up to 0.4%, and the claim's growth reason carries the churn rows. Confirmed (READ).
3. Fixed: `_fits` checks each `__init__` entry the start read against the loaded run, at a load and at a re-read, and the docstring names the stdlib zip as the only tabled archive; a unit row with a forged header. Confirmed (READ, EXECUTED).
4. Answered with a judge row instead of a scanner change: `test_no_hook_sits_where_the_callback_scan_reads_a_method` finds the hooks by name, keeps them off index 1 and asks a method's type there, so the arrangement is held, not left to luck. Accepted; the scanner's stale docstring stays a write-in.
5. Fixed: the self-check's Windows box is ticked with run 41274232306. Confirmed (READ).
6. Fixed: both news files give the rebased bytes (the zip +2,815, `python.wasm` 100,660,530, the snapshot −97,597, against `dev`'s set at `a0b1171d`). Confirmed (READ).

## Verdict

Lands on `b69627d7`: the round's fix commit closes Finding 1 and Findings 2 to 6, run 41274232306 is green on every judge shard and every Windows leg, and nothing stands.

In one line: both changes measure as claimed and hold their caps and probes, 175's lazy load now survives an exception, and 176 earns its place on short calls with its trade written down.
