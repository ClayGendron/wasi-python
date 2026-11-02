# Review of 166 — The pins move for 0.1.3 (the first pull request)

- **Date:** 2026-10-31
- **Reviewer:** an agent (Claude Opus 5.5), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** `a1acec5c..a7f5cee5` on `spec/166-the-pins-move-for-0-1-3` (17 commits), then the fix commit `c2083f5c` (round 1), with the specification, its pre-build review and the locally rebuilt set under the worktree's `build/`
- **Run:** 41170628147 at `a7f5cee5`, red on four legs. I read its failure log as the orchestrator saved it; I made no `gh` call. Run 41180386787 on the fix commit `c2083f5c` is green (Linux 32, macOS 15, Windows 13), every growth row carries 166's claim, and `ci-status` is red only because the review was missing. These figures come from the orchestrator's report; I made no `gh` call.
- **Re-ran:** `WASI_PYTHON_ARTIFACTS=<worktree>/build/artifacts uv run pytest -m "not slow" -n 2 -q tests/unit tests/lint tests/checks/test_rules.py` → 3,562 passed, 12 skipped, exit 0; rules 132/133, one blocked by the prior-art clones, as on `dev`; the ratchet lists `context/release-claims.toml` under "judge changed" (EXECUTED).
- **Time box:** 45 minutes (build-class); kept.

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning. No `gh` call was made and no run was dispatched.

## Acceptance criteria against evidence

1. Decision 9's rows fail first, then pass: met. Each is stated in the landing notes (READ). The new rules row and unit row pass here (EXECUTED).
2. Pins against their publishers: met for the ones I checked. 14 new local files match `downloads/SHA256SUMS` (EXECUTED). Spot checks against the publishers all agree (EXECUTED): PyPI's JSON for `numpy-2.5.4.tar.gz`, its macOS 14 arm64 wheel and both soupsieve 3.0.4 files; GitHub's asset `digest` for all three `wasmtime-v50.0.1` archives. Every `pin` line in the set's `MANIFEST` equals `SHA256SUMS`. Every `recipe` line equals the file at the head (EXECUTED). The build shard's 52 passes are READ only.
3. Patches apply at no offset with the same changed lines: met. The old and new numpy patches have the same `+`, `-` and `@@` lines. Only the `index` lines differ. pypdf's patch is byte-identical. Both numpy patches pass `patch -p1 --dry-run` on a fresh 2.5.4 tarball with no offset or fuzz (EXECUTED).
4. `-V` and the builtin versions: `MANIFEST` says `python 3.15.2` and `package numpy 2.5.4` (READ). The criterion's pandas half belongs to the second pull request.
5. The two-CLI comparison: recorded. Both CLIs write snapshot `ed740363…`, and that is the snapshot hash in the set (READ, EXECUTED).
6. Golden and `tests/upstream/**` edits: met, with Finding 3's note. See (c), (d) and (e) below.
7. Local release groups and their ledger claims: READ, with Finding 2.
8. Decision 11's table: bytes within bounds. Fuel crosses the +1% sum, and the cause is traced (Finding 3). The wheel row needs the run's figure (Finding 4). The "no own check over +5%" bound waits for the gather's darwin rows.
9. Same bytes: met locally. The set's `SHA256SUMS` hashes to `784b119d2a67…`, and every file in the set checks against it (EXECUTED). The run's asset, which the builder saved under `build/166/ci-assets/set/`, has a byte-identical `SHA256SUMS` whose files all check (EXECUTED). Which runner built it is the author's statement; I did not read the run.
10. News file shape: lint is green (EXECUTED). `ci-status` is pending.

**What the author asked about.**
- (e) The linalg golden follows native numpy, not the guest. I ran the check's program under the oracle's native numpy 2.5.4, the scipy-openblas 0.3.34 build. It prints exactly `LINALG_ERRORS_NATIVE`: `cond returns all-nan`, and one DORGQR xerbla line (EXECUTED). numpy's source shows why. 2.5.4 adds `all_finite` before `gesdd` and `gelsd`, and a `_cond_svdvals` that returns nan, for gh-32591 (READ, diff of `umath_linalg.cpp` and `_linalg.py`). This is justified.
- (d) The three new `test_name_error_with_bad_*` tests come from `SuggestionFormattingTestBase`. `CPythonSuggestionFormattingTests` runs them through `CAPIExceptionFormattingMixin`, which imports `_testcapi`. That is the class's cause, and its pattern matches. The gap's count of 143 is a mechanical result of that (READ). Right.
- (c) `test_cppext` is gone from 3.15.2's `Lib/test`. The four `test_free_threading` modules are new (EXECUTED, a diff of both tarballs' file lists). Placing them adds checks and loosens nothing. This is not one of Decision 10's three kinds of edit, but the plan's rule requires it, and the news file names it. The new `test_capi/test_build.py` and `test_slice.py` run under `test_capi`, which the plan already lists. No count falls.

## Findings, most severe first

1. **Medium: CPython moves although a licence file changed, against Decision 7's own wording** (spec 166 Decision 7; landing notes "Licence files"; `build/artifacts/LICENSES/cpython.txt:1316`). 3.15.2's `Doc/license.rst` changes mimalloc's notice from `2018-2021` to `2018-2025`, because 3.15.2 vendors mimalloc 2.5 instead of 2.1.2. That file ships as `LICENSES/cpython.txt` (EXECUTED: diffed against 3.15.0's). Decision 7 says "any moved pin whose licence files change waits for the owner (§4.12), numpy and pandas included". The pre-build review's Finding 11 added "numpy and pandas included" for this case: pins the owner chose by name. So "the owner chose 3.15.2 by name" is not an exemption the specification allows. zlib 1.3.2 was held for the same kind of change: copyright years, plus a licence file for minizip, which is not built. Holding one and moving the other is inconsistent. The terms do not change in either case: mimalloc stays MIT inside CPython's approved notice, and zlib stays zlib. §4.12 itself is therefore not broken; the specification's rule is. Failure: the merge would carry a licence-file change the owner has not seen, which Decision 7 forbids. **This waits for the owner.** Fix: before the merge, the orchestrator asks one question with AskUserQuestion. **A** (recommended): both changes are copyright years under unchanged terms, so CPython 3.15.2 moves now, and zlib 1.3.2 moves in 166's second pull request, with its news entry and its fix lines ("check for negative lengths in crc32_combine"). **B**: CPython moves, and zlib waits for 0.1.4. **C**: CPython stays at 3.15.0, and this branch is rebuilt without it. The answer goes in the landing notes and in `decisions.md`. Evidence that closes it: that record.

2. **Low: the release ledger is a verdict-bearing judge file the news file does not claim** (`context/changes/166-the-pins-move-for-0-1-3.md`, `[claim.judge]`; `tests/harness/paths.py:296-304`). The change appends a block to `context/release-claims.toml`. `paths.VERDICT_BEARING` names that file, and the local ratchet lists it as changed (EXECUTED). No `[claim.judge]` key names it. Spec 161's news file did name it when it changed the file. Failure: the acceptance after the merge records it as `unclaimed`, and the release pull request asks for the reason again. Fix: add this line to `[claim.judge]`: `"context/release-claims.toml" = "166's first pull request appends its release-tier claim block: pypdf-r's and soupsieve-r's passes, and the release groups whose fuel moves under CPython 3.15.2, numpy 2.5.4 and soupsieve 3.0.4"`. This touches only `context/`, so it needs no second signature.

3. **Low, withdrawn in round 1: I was wrong here.** `tests/harness/packages.py:1517` already bounds a smoke group at 100 G (`SMOKE_GROUP_BOUND`), and run 41170628147 failed `test_upstream_files_are_well_formed` on that bound. Under the judge's own rules a 250 G cap was not legitimate. The text below is kept as I signed it; item 4 of the CI round replaces it. **The original Low 3: soupsieve's raised cap is legitimate, but its smoke group is no longer a smoke** (`tests/upstream/soupsieve.toml:19-20`). Raising the cap does not weaken the judge. A cap limits fuel; every test must still pass. Decision 10 lets a cap rise when the measured fuel exceeds it and the former headroom is kept. Here 35 / 23.16 = 1.511, and 250 / 164.8 = 1.517. Decision 11 treats its bounds as triggers for tracing, and this growth is traced. My native timing agrees with the trace (EXECUTED, CPU time, soupsieve's `test_api.py`). In 3.0.4, `test_escape_round_trip` and `test_unescaped_non_ascii_identifiers` take 4.06 s, and the rest takes 0.42 s. In 3.0.3 the rest took 0.35 s. Holding soupsieve back would be wrong. Decision 7 sends a swept pin back only when it fails twice, and 3.0.4 changes `css_parser.py` and `css_match.py` themselves. zlib's hold was for a licence, not for cost, so the cases differ. The cost is real, though. The smoke grows about 7×, to the fourth-largest smoke group, and adds about 1.8% to the normal tier's upstream fuel on every Linux run (INFERRED, from the `measured` values). Fix, answered in writing for this pull request: (i) name the run in the landing notes once it is read, with soupsieve-smoke's Linux fuel, as Decision 10 asks ("with the run named"); (ii) record a follow-up in the roadmap. That follow-up moves those two tests to the release tier with a keyword split (`[[split]]` with `release_by = "keyword"`, as contourpy does), claimed under `[claim.moved]`, and lowers the smoke cap back toward 35 G.

4. **Low: the landing notes have open slots and a wheel figure from a hand build** (spec 166, "Landing notes"). The wheel row says 98,327,639 bytes, built by hand. The run's wheel asset in `build/166/ci-assets/` is 98,327,640 bytes, `a996caba…`: 1,672,360 bytes under 100,000,000 (EXECUTED). Decision 12's paragraph says its comparison "follows below", and the Status line has no run. Fix: write the run id, the run's wheel size, and the sentence "the run's arm64 Linux set's `SHA256SUMS` is byte-identical to this Mac's, digest `784b119d2a67…`" into the landing notes.

## Constitution checks

- §4.1: holds. Three patches were re-made, their changed lines are unchanged, `MANIFEST` hashes them, the news file names each by path, and their drafts moved.
- §4.2 (pins): holds; see criterion 2.
- §4.12: the shipped notices are current. `LICENSES/cpython.txt` carries the 2025 line. The specification's stricter rule is Finding 1.
- §5.6: the pre-build review exists, and its 13 dispositions are honoured. Medium 1's local build shard, Medium 3's `ci:full` label and Low 12's `x-wizer` clause in `SECURITY.md` were checked.
- §7: no judge file was edited to turn a run green outside Decision 10's rules. Commit trailers name Claude Opus 5.5 on all 17 commits (EXECUTED).
- Structure: nothing under `src/` changes. `paths.wasmtime_cli()` gains an optional name and folder, which are test-harness parameters only. No rubric row moves.

## Round 1: run 41170628147's four red legs and the fix commit `c2083f5c`

I read the run's failure log, as the orchestrator saved it, and the fix commit's diff. Then I re-ran its checks by node id against the worktree's rebuilt set (whose recipe files `c2083f5c` does not touch): `test_upstream_files_are_well_formed`, `test_deep_data_raises` (all cases), `test_deep_data_limits` (all cases), `test_upstream_suite[tqdm-smoke]` and its three classes, `test_upstream_suite[soupsieve-smoke]`, `test_upstream_suite[cpython-fs]` and `test_upstream_host[cpython-fs-win-logging-emit-reopen-error]`. Result: 26 passed and 4 xfailed (the three tqdm gaps and the host entry's gap), exit 0. The scoreboard reads soupsieve-smoke's 88 → 35 as CLAIMED (EXECUTED). soupsieve-r is release tier and was deselected here; its 185.8 G is the author's measurement.

Each item is a judge change. I judged it against AGENTS.md's rule: never weaken the judge to turn a run green.

1. **`[hash-tuple]` moves from the trap table to the raises table: a fair restatement, not a weakening.**
   - gh-154318 is in 3.15.2's `Misc/NEWS`: "A RecursionError is now raised instead of overflowing the C stack" (READ, from `downloads/Python-3.15.2.tar.xz`). `Objects/tupleobject.c:387` now calls `_Py_EnterRecursiveCall(" while hashing a tuple")`.
   - The run shows what failed: the *shallow* side, 30,000 levels, which raised `RecursionError: Stack overflow (used 112 kB)`. The trap side never ran.
   - I probed both sets (EXECUTED). On this head, `hash` of a nested tuple works at 3,000 levels and raises at 10,000, exactly as `repr` of a tuple or a list does. On `dev`'s 3.15.0 set it worked at 30,000.
   - The safety guarantee is that the host survives, the call ends cleanly, and the next call works. It now holds more strongly, because the guest raises instead of trapping. `test_deep_data_raises` asserts that at 400,000 levels, beside `repr` and `==`.
   - What is lost is depth: tuples nested about 10,000 to 40,000 deep hashed in 0.1.2 and now raise. That comes from upstream's new check meeting the guard window in `recipes/reactor_main.c`. That file's own comment explains why the window is 128 KiB, and widening it would spend the native stack it protects. `docs/reference/limitations.md` now lists `hash`.
   - The news file claims the retirement under `retired` and the new case under `new`. See Low 5 below.
2. **Windows `cpython-fs`: right.**
   - CPython 3.15.2 decorates `test_emit_reopen_error` with `skipIf(os.name == 'nt')` (READ). The guest is not `nt`, so the test runs, and a Windows grant refuses to remove the folder of a file that is still open.
   - The host entry has darwin and Linux `passed` and Windows `error`, like `win-spooledtemporaryfile-bound-methods`. Its gap names the closer `docs/reference/limitations.md`, whose "On Windows" section already says that a Windows grant cannot remove a file the guest holds open (line 60).
3. **tqdm's three classes: right.**
   - In the run, each class counts two more findings (13, 101, 119). That is one listed member missing and one unlisted member present: a swap.
   - The fix swaps `test_iter_basic_overhead` and `test_iter_overhead_simplebar_hard` between the classes. Counts and digests otherwise hold (11, 99, 117).
   - Each moved test meets its new class's pattern: the asyncio class matches "Exception ignored while calling deallocator", and both thread classes match "TqdmMonitorWarning" or "instances still in existence". All three class checks pass here (EXECUTED).
   - The cause is plausible: which test triggers a deterministic garbage collection depends on the interpreter's allocation counts, and 3.15.2 changes those (INFERRED).
4. **soupsieve's `test_api.py`, moved whole to the release tier, claimed under `fewer`: the right claim, and an accepted deviation.**
   - The judge row `test_upstream_suite[soupsieve-smoke]` stays in the normal tier, and `soupsieve-r` stays in the release tier. No check changes tier, so nothing belongs under `[claim.moved]`.
   - The smoke's pass count falls from 88 to 35. That is exactly what `fewer` is for, and the gather shows it as CLAIMED.
   - Every test still runs before each release, in `soupsieve-r`, which now counts 400 passes (constitution §5.5).
   - The caps keep the 1.5 rule: 23 / 15.1 and 280 / 185.8. The budget is their sum, 303 G.
   - Decision 10 says pass counts fall "only because upstream deleted or moved tests". This fall is the project's move, forced by the 100 G smoke bound, which predates this change. The landing notes say that the harness cannot split a smoke family's path groups by keyword (`tiers.kind_of`; INFERRED as plausible from `tiers.py:141-152`). So keeping test_api's cheap tests in the normal tier would need a change to the harness, not to this pull request.
   - The normal tier does lose 53 fast API tests until a later change splits the file. Recording that follow-up in the roadmap is optional and does not block this pull request.

5. **Low (new): the CHANGELOG does not tell embedders that `hash` of a deep tuple now raises at a shallower depth** (`context/changes/166-the-pins-move-for-0-1-3.md`, `### Upgrading`). The behaviour changes as item 1 describes, and only `limitations.md` says so. Fix: add this entry under `### Upgrading`: `- **Hashing a deeply nested tuple raises sooner.** CPython 3.15.2 checks the C stack while hashing a tuple, so a tuple nested more than a few thousand levels deep raises \`RecursionError\`, as \`repr\` and \`==\` already did; 0.1.2 hashed about 40,000 levels and then ended the call with a trap. [Limitations](https://claygendron.github.io/wasi-python/reference/limitations/)`. This touches only `context/`, so it needs no second signature.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Medium 1 — answered by the owner on 2026-10-31, option A. CPython 3.15.2's licence-file change (mimalloc 2.5's copyright years) is approved; #67 merges with CPython 3.15.2; and zlib 1.3.2 moves in 166's second pull request. The answer is recorded in `context/decisions.md` (line 538) and constitution §4.12 on `docs/the-owners-decisions-of-2026-10-31` (pull request 72, `415f4f29`). Reviewer: confirmed (READ, `decisions.md` at that commit).
2. Low 2 — fixed in `c2083f5c`: `[claim.judge]` names `context/release-claims.toml`. Reviewer: confirmed (READ).
3. Low 3 — withdrawn by the reviewer, as wrong (above). The author's tier move in `c2083f5c` replaces it. Reviewer: confirmed sound, as item 4 of round 1.
4. Low 4 — fixed in `c2083f5c`: the Status line names the run, the wheel row gives the run's 98,327,640 bytes, and Decision 12's sentence records the byte-identical `784b119d2a67…`. Reviewer: confirmed (READ, and EXECUTED for the digest earlier).
5. Low 5 — fixed by the reviewer in the news file's `### Upgrading` section ("Hashing a deeply nested tuple raises sooner"). It touches only `context/`, and it rides in the review's commit.

## Verdict

Lands on c2083f5c: the owner approved CPython 3.15.2's licence file with option A, run 41180386787 is green, the round-1 judge changes hold, and Low 5's entry is in the news file.
