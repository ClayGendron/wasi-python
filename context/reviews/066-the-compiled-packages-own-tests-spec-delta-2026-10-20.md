# Review of 066 — the compiled packages' own tests in the release (the re-survey's delta, before build)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I wrote none of spec 066, its survey, its re-survey, or the earlier pre-build review and its confirmation. I read `AGENTS.md`, `context/constitution.md`, `context/reviews/README.md`, `context/decisions.md` on main ("Three answers for 0.1.0 (2026-10-20)"), the earlier review `066-the-compiled-packages-own-tests-spec-2026-10-20.md` with its confirmation, specs 089 and 090, `scripts/litter.py`, `tests/harness/litter.py`, `tests/checks/conftest.py`, and the pinned contourpy tree `build/contourpy-1.4.0` (as text only). Time box: 45 minutes (a build-class specification).
- **Reviewed:** `spec/066-the-compiled-packages-own-tests`, the range `b47f31c..ad3c065` (one commit, `ad3c065`, on main `958a22b`). The confirmation reviewed up to `b47f31c` (its C1 to C9 written in). The diff touches only `context/`: the spec (149 lines), the memo's last section, and the evidence folder (`caps.py`, `results-resurvey.md`, `failures-resurvey.txt`, `summary-resurvey.json`, `survey.py`, `analyze.py`) (READ).
- **Run:** none. A delta review of a context-only diff before anything is built: there is no build to re-run, so no release workflow was dispatched (the brief, and AGENTS.md rule 3a).
- **Re-ran:** `build/lane.lock` absent at each start.
  - `uv run pytest tests/checks/test_rules.py -q -p no:cacheprovider` in the 066 worktree at `ad3c065` → 43 passed, 1 skipped, exit 0 (the skip: prior-art clones, blocked).
  - `uv run python caps.py <the 19 groups>` as committed → `KeyError: 'matplotlib-render-1'` (it reads `summary.json`, wave 05's survey). The same script, in a scratch copy with `summary-resurvey.json` in place of `summary.json` → its table and totals match `results-resurvey.md` byte for byte (EXECUTED).
  - An independent sum over `summary-resurvey.json`: 8.0263 T measured; 1.5 times that is 1.2039×10¹³ unrounded; with mathtext's 296.2 G, 8.322 T and 1.2484×10¹³ (EXECUTED).
  - The accepted upstream fuel on main: the 16 `test_upstream_suite[...]` rows of `context/progress/accepted.json` (`d066695`), darwin-arm64, sum to 2.887 T (EXECUTED).
  - `importlib.util.find_spec("contourpy")` in the project's host environment → `None` (EXECUTED).

## The builder's self-check

Not applicable: nothing is built. The delta is a research step's report (constitution §5.2), and its numbers are labelled EXECUTED in the memo. No item is ranked for it.

## The brief's four questions, against evidence

1. **The numbers** — met, with two write-ins (L2, L3) and one misstatement of price (M3).
   - Each cap is 1.5 times the re-survey fuel, rounded up to two significant figures. The families' budgets are sums of caps. The rule's rounding adds about 1%: 1.217×10¹³ rounded against 1.204×10¹³ unrounded, over the 19 measured groups. That is not in the owner's words, but the confirmed Decision 14 states it. Fine.
   - Every number in the delta's table agrees with the evidence (EXECUTED):
     - matplotlib 3,306.8 G measured, plus mathtext's 296.2 G, is 3.60 T;
     - contourpy 4,155.0 G, with caps of 6.27×10¹² rounded;
     - total caps 1.217×10¹³ plus 4.5×10¹¹ is 1.262×10¹³;
     - total fuel 8.03 T plus 0.30 T is 8.32 T.
   - The random_big figure is (2,387.6 − 544.0) + (1,459.5 − 470.2) = 2,832.9 G. Option (c)'s caps are 1.262×10¹³ − 1.5 × 2.833 T ≈ 8.37×10¹². Both are right *given* the two `-k "not random_big"` measurements, but the evidence folder does not record those runs (L3).
   - The failure classes match `summary-resurvey.json` and `failures-resurvey.txt` (EXECUTED tally):
     - matplotlib's 29 failures: 15 no-processes (14 by regex plus `test_movie_writer_registry`), 8 pillow-zlib-only, 2 no-threads, 2 no-fp-exceptions, 1 wasi-errno-values, 1 stage-layout;
     - Pillow's 78: 51, 17, 5, 2, 2, 1, in seven classes once `test_save_without_changing_readonly` is split out by id (C1);
     - lxml's 2;
     - none in contourpy, regex, kiwisolver or the toolkits;
     - no guard line and no trap in any group.
2. **The three choices** — not stated correctly yet (M1, M2, M3, L1, L4). (a) cannot have "twelve shards of at most 700 G". (b)'s partition check cannot live in the rules check as written. All three understate the full judge's upstream fuel by today's 2.89 T.
3. **The other changes** — met, with one residual named (L5).
   - **contourpy's working folder as the tree root.** Sound. Its `compare_images` reads `tests/baseline_images/…` by a relative path. The 201 failures that drove this are reported, not recorded (L3).
   - **lxml's `/tmp/work` with `cwd_files`.** Sound. Decision 14's rules limit `cwd_files` to tarball members and to `cwd = "/tmp/work"`. The copy is three named files, not a folder walk. So it cannot carry litter in, and the stage writer refuses litter-named members (089).
   - **mathtext's provisional cap of 4.5×10¹¹.** Sound. 1.5 × 296.2 G = 444.3 G, rounded up. Between the two sets `mpl-mplot3d` grew 11% and `matplotlib-axes` 1.1%, so the margin holds unless mathtext grew by more than half (INFERRED). The build measures it.
   - **The litter that voided mathtext.** Not a build defect. Spec 090 and `scripts/litter.py` govern build inputs and the artifact set, and nothing there was touched. It is the residual spec 089 accepted on purpose: writable guest roots are detection-only. The surveys now show that residual is real, and 066 makes it larger (L5).
   - **No new class.** Right.
   - **097 and 099 as closers.** Right. Both are in the roadmap's `Reserved:` paragraph on main (READ). `no-fp-exceptions` closes with spec 099, and the README states the fact until then. This matches the owner's "fix before 0.1.0".
   - **`packages.toml` re-pointed to 095 at build.** Right, and now needed. 037 landed with `[package.scipy] closes_with = "spec 066"` (main's `tests/upstream/packages.toml`, the scipy entry). Decision 13 has the builder re-point it, and criterion 10 checks it. The claim list still says "if 037 landed" (L6).
4. **The earlier findings** — they stay answered.
   - **H1** (lxml's selection): the re-survey still deselects 360 items. `lxml.cssselect`'s docstrings were dropped from the stand-in driver, which matches the not-selected row that was already there.
   - **H2** (Pillow's fuzz tests): still in Pillow's 4,587 passes.
   - **M1 to M3, C1, C2 (now closed by 099), C3 (096 landed), C5, C7 (097), C9:** hold.
   - **C4** (fold the delta into the Decisions): done for Decisions 6 and 11. Decision 12, the Scope, the Intent, the README sentence and "The owner's choices" wait on the owner's new answer (L6).
   - **C8** (lxml's copy): it offered "keep the copy, with the reason it is safe". The reason is now given: two tests write `test.xml`. The copy cannot carry litter in, but its folder can receive litter at run time (L5).

## Findings, most severe first

1. **M1 — Option (a) cannot be laid out as stated** (Medium; spec, "Delta from the re-survey", (a) and "Shards").
   - Under (a), `contourpy-filled` (2,387.6 G) and `contourpy-lines` (1,459.5 G) are each one group, so each is one `test_upstream_suite[...]` node. A node cannot be split across shards. So "about twelve shards of at most 700 G" is impossible.
   - Each of the two needs a shard to itself. At Decision 12's rate (about 60 s of setup plus 0.16 to 0.31 s per G), they take about 440 to 800 s and 290 to 510 s (INFERRED).
   - The first is past criterion 12's 360 s per shard and past the 457 s macOS leg. It would become the release's critical path, and the lane's long pole at `-n 3`.
   - Failure: the owner picks (a) as "the rule as written", and the build cannot meet criterion 12 without amending it.
   - Fix text: restate (a) as "two shards of about 2.4 T and 1.5 T, each past criterion 12's 360 s, which (a) would amend; the release's judge stage grows by about 5 minutes (INFERRED)". Or drop (a) and put (b) against (c), since (b) costs the same fuel without the long pole.
2. **M2 — (b)'s partition check cannot live in the rules check, and `-k` overlaps are the norm here** (Medium; (b), and Decision 14's "with no guest").
   - The rules check runs with no guest. contourpy is not importable on the host (`find_spec` → `None`, EXECUTED). The parametrized ids come from `tests/util_test.py`, which imports contourpy. So a rules check cannot collect the file's tests. It could only compare the expressions against a hand-kept list, and that list goes stale at the next pin.
   - pytest's `-k` matches substrings, without regard to case. contourpy's ids are exactly the overlapping kind (`util_test.py:33–49`, READ):
     - `ChunkCombinedCode` also selects `ChunkCombinedCodeOffset`;
     - `ChunkCombinedOffset` also selects `ChunkCombinedOffsetOffset`;
     - `corner_mask` gives the ids `None`, `False` and `True`.
   - Failure: groups `-k "serial and ChunkCombinedCode"` and `-k "serial and ChunkCombinedCodeOffset"` both run the `ChunkCombinedCodeOffset` cases. A check against a stale list does not notice.
   - Fix text: make the partition hold by construction, not by collection.
     - A file's keyword groups are an ordered list of expressions e₁ … eₙ₋₁. The harness runs group i with `-k "(eᵢ) and not (e₁ or … or eᵢ₋₁)"`, and the last group with `-k "not (e₁ or … or eₙ₋₁)"`.
     - The rules check verifies only that form, statically. Every collected test is then in exactly one group, whatever upstream adds.
     - At judge time, a keyword group that selects no test fails (pytest's exit 5 must not pass as an empty group). Each group records its file's collected count as a fact, so the lane can see that every group collected the same file.
3. **M3 — The price leaves out the upstream fuel the judge already runs** (Medium; (a), the memo's finding 4).
   - "The lane's full judge runs about 8.3 T of upstream fuel instead of 2.84 T" counts 066's groups only. The 16 existing groups stay: 2.887 T accepted on `d066695` (EXECUTED).
   - The full judge's upstream fuel:
     - under (a) and (b): about **11.2 T**, 3.9 times today's;
     - under (c): about **8.4 T**, 2.9 times today's.
   - The owner was told "about 7 T instead of 2.84 T", which was a total. So the honest comparison with what the owner chose is 7 T against 11.2 T (+60%) or 8.4 T (+20%). The +80% is caps against caps, which is a different measure.
   - Fix text: in each option, state "the full judge's upstream fuel goes from 2.89 T to about 11.2 T (about 8.4 T under (c)), against the about 7 T in the owner's question".
4. **L1 — (b) and (c) still leave a contourpy group past 480 G, and "split by algorithm" does not reach the bound** (Low).
   - (b) says "no group past 480 G but `matplotlib-axes`". In the next line it gives `contourpy-filled`'s `not random_big` part as "544 G, itself over the bound". (c) keeps that 544 G file whole and does not name it.
   - `test_filled_random_big` has 14 (algorithm, fill type) pairs times 3 corner masks: 42 cases, 2 of them skipped. `serial` and `threaded` hold 18 run cases each. At equal cost per case, each is about 830 G of the 1,843.6 G (INFERRED). That is past 480 G, and past 700 G.
   - Fix text: (b) names the split as algorithm × corner mask (or × fill type), measured by the build. Both (b) and (c) name `test_filled.py`'s `not random_big` part as past the bound, or split it.
5. **L2 — `caps.py` does not run as committed, and it mislabels families** (Low; `caps.py:5` and its `family` line).
   - It reads `summary.json`, wave 05's survey, which has no `matplotlib-render-1` group → `KeyError` (EXECUTED).
   - It names each contourpy group its own family. The output prints `contourpy-1: budget …`, `contourpy-lines: budget …` and so on, where the delta means one contourpy family of 6.27×10¹².
   - Fix text: read `summary-resurvey.json`, and give every `contourpy-*` group the family `"contourpy"` (as `survey.py`'s `group_family` does). Re-render `results-resurvey.md`.
6. **L3 — Four EXECUTED figures have no record in the evidence** (Low; the memo's re-survey findings 3 and 6).
   - The `-k "not random_big"` runs (544.0 G and 470.2 G).
   - contourpy with `/tmp/work` (201 failures).
   - lxml with the read-only tree root (two `PermissionError`).
   - None of these appears in `results-resurvey.md`, `failures-resurvey.txt` or `summary-resurvey.json`. `survey.py`'s groups cannot produce them; only its bisection argv (line 208) can. They price (b) and (c).
   - Fix text: add each run's command line, fuel and outcome counts to `results-resurvey.md`, or relabel them as reported rather than recorded.
7. **L4 — The concurrency claim is wrong for one run** (Low; "Shards").
   - "21 + 12 jobs is past the account's concurrency" does not hold. AGENTS.md says the plan is Pro. The shards memo (`2026-10-18-the-release-judges-in-parallel-shards.md`, line 184) gives Pro as 40 standard jobs at once, 5 of them macOS. The base run already had 22 at once, which is past Free's 20.
   - One run's 33 jobs fit. What binds is macOS's five slots, which are unchanged, and a second release run live at the same time (AGENTS.md allows three).
   - Fix text: "33 jobs fit Pro's 40 for one run; with two runs live they queue; macOS's five slots still bind".
8. **L5 — Host litter in the writable guest roots is a residual that 066 enlarges; name it** (Low; the delta's last bullet, Decision 6).
   - mathtext's two voids came from `.DS_Store` in the guest's `/`, `/tmp` and `/tmp/work`. That is the writable root, `build/survey/out/<group>` (`survey.py`, `workdir=work`).
   - The judge's own writable roots are the same kind of folder: `build/harness/guest-*` (`tests/checks/conftest.py:60`).
   - Spec 089 (Decision 2) left writable roots detection-only. Its premise was that the writer had never been seen in a `guest-*` folder. The two surveys have now seen it four times: Pillow's copy twice and mathtext twice.
   - This is not a build defect. Spec 090 and `scripts/litter.py` keep litter out of build inputs and artifacts, and no artifact byte is involved.
   - But 066 roughly quadruples the judge's upstream wall time on the lane's Mac. matplotlib's groups write `result_images/` into that root, and lxml's `cwd_files` land there. Both are things that make macOS size a folder (INFERRED from the Pillow and mathtext voids).
   - Fix text:
     - Decision 6 and the delta name the residual, with a closer: a judge follow-up the lane reserves, or 097's scope widened.
     - "For the lane" says that a group stopped by a named `HostLitter` line at acceptance is a host failure, re-run after the litter is gone. It is not a measured difference, so the sameness rule's "never a re-run" does not apply.
9. **L6 — Text that waits on the owner, and one stale condition** (Low; lines 41, 438–448, 512, 573, 653–665, and the claim list).
   - "The owner's choices" still asks the answered question at "about 7 T". The Scope, the Intent, the README sentence and Decision 12 still say six shards and about 4.5 T.
   - The claim list says "scipy's closer re-pointed if 037 landed". 037 has landed.
   - Fix text:
     - rewrite "The owner's choices" as the new question, with M1, M3 and L1 to L4 applied;
     - after the answer, fold the shard count into Decision 12, the Scope, the Intent and the README sentence;
     - claim list: "`packages.toml`: six `later` become `suite`; scipy's `closes_with` re-pointed from spec 066 to spec 095".

## Constitution checks

- §4 constraints:
  - no source patch, no download, no artifact change in this delta;
  - the new key `cwd_files` copies tarball members already pinned and hashed;
  - prior art is not involved;
  - tests count fuel, not time: the shard times above are benchmark estimates, labelled INFERRED. Holds.
- §5.2: the delta is an EXECUTED research step, reported before any check, TOML or harness line. Holds, but L3's four figures need their records.
- §7 never-do list:
  - nothing tripped;
  - no judge file, golden output, `known_gaps.toml` or `context/progress/` is edited;
  - option (c) would amend AGENTS.md rule 4's spirit (no tests left out for convenience), and the delta rightly puts that to the owner rather than deciding it.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. M1 — 
2. M2 — 
3. M3 — 
4. L1 to L6 — (Lows with fix text; no further round needed)

## Verdict

Passes for build with conditions: before the lane asks the owner, the question is restated with M1 (option (a) as two long shards past criterion 12, or dropped) and M3 (the full judge's upstream fuel of about 11.2 T, or 8.4 T under (c), against the 7 T the owner was told). If the owner picks (b), its groups partition `test_filled.py` and `test_lines.py` by construction, as M2 sets out. The build then starts on the owner's answer.

## Confirmation (2026-10-20)

- **Reviewer:** the same fresh agent as above. It wrote none of the disposition.
- **Reviewed:** `spec/066-the-compiled-packages-own-tests` at `23270ff`, the section "Disposition of the delta review", Decisions 11, 12 and 14, criterion 1, "The owner's choices", and the fixed `caps.py` and `results-resurvey.md`.
  - The tip is not `bc3b98a`: the branch was rebased again, onto `21dff9d` (origin/main, which widens 097).
  - `git range-diff` shows every 066 commit unchanged (`=`). The one change is that spec 067's draft commit was dropped. That is right: a worktree's branch carries exactly one specification (AGENTS.md rule 9).
- **Run:** none. Nothing is built.
- **Re-ran:** `build/lane.lock` absent.
  - `uv run pytest tests/checks/test_rules.py -k "specifications or executed_memos"` at `23270ff` → 4 passed, exit 0.
  - The fixed `caps.py` over the 19 groups → contourpy one family at 6.270×10¹², total caps 1.217×10¹³, fuel 8.026 T (EXECUTED).
  - A probe of the constructed `-k` form with the host's pytest 9.1.1 (below; EXECUTED).

### M1 to M3

- **M1 — closed.** The owner chose (b). "The owner's choices" gives (a)'s reason in one line: each file would need a shard to itself, past criterion 12 and the macOS leg.
- **M2 — closed.** The form partitions by construction, and the check needs no collection.
  - **The logic.** pytest compiles a `-k` expression into a boolean formula. Each identifier is asked of the item's keywords separately, by substring and without regard to case. So the constructed string for group i is true exactly when eᵢ matches and no earlier e matches. The last group's string is true exactly when none matches. Each item therefore falls into one group only: the first i whose eᵢ matches, or else the last group. Substring overlaps change which group an item falls into. They cannot put it in two groups or in none.
  - **The probe.** I used pytest's own `Expression.compile` on 45 contourpy-shaped ids (the 42 `test_filled_random_big[...]` cases and three others). The expressions were the spec's eight for `test_filled.py`, plus a deliberately overlapping ninth, `ChunkCombinedCode`. Result: 0 items outside exactly one group, across 10 groups (EXECUTED). `None`, `True` and `False` parse as identifiers (pytest prefixes identifiers internally), so the corner-mask expressions are legal.
  - **No collection needed.** The TOML holds only e₁ … eₙ₋₁, and the harness builds the strings. So the rules check needs only Decision 14's points:
    - n groups and n − 1 expressions;
    - each expression non-empty and parsed by pytest's parser on the host;
    - each group's only path is the file;
    - no group in two splits. None of these needs contourpy. Criterion 1's unit check of the strings built for a three-group split covers the harness side.
  - **The judge-time checks** are what is left: an empty group fails (exit 5), and each group's collected count is recorded. They hold because every group of a file runs with the same family, `.ini` and options, so each item's keywords are the same in every session.
- **M3 — closed.** "The owner's choices" and the delta state about 11.2 T per full judge. That is 2.89 T today plus 8.32 T, against the about 7 T in the first question, and it matches my sums.

### The Lows

- **L1** (the split into 9 and 8 groups): answered. Every group is INFERRED under 480 G and the build measures each. One numeric note follows below the list.
- **L2 to L6:** answered as written. `caps.py` runs and gives one contourpy family. The four runs are recorded in `results-resurvey.md`. The concurrency line now says 33 jobs fit Pro's 40. 097 is the litter closer (on `21dff9d`), and "For the lane" says what to do on `HostLitter`. The leftover text is fixed.

**The shard table's sums.** No finding; a write-in. The rows built only from measured groups are right: a 712.3, b 737.0, c 735.5, d 737.6 and e 732.3 G (EXECUTED arithmetic). The contourpy estimates are a little high:
- The rows imply split groups of about 290 G (filled, by algorithm and mask), 197 G (filled's `random_big` rest), about 158 G (lines, by algorithm and mask) and 129 G (lines' `random_big` rest).
- Decision 11's own per-case shares give less: 46.1 G per filled case and 29.1 G per lines case. That is 276.5, 184.4, 145.5 and 116.4 G.
- So the twelve rows sum to 8,530 G against 8,322 G measured (with mathtext's 296.2 G): about 207 G too much, all of it in contourpy's split groups.
- Decision 11's text also names e₇ at "about 184 G" while the table carries 197 G.
- The error is on the safe side: every shard stays at or under about 740 G. Decision 12 already has the build re-pack from its own measured fuel.
- Write-in, for the build: lay out the contourpy rows from the per-case shares, or say that they are rounded up.

### Verdict of the confirmation

**Confirmed for build.** M1 to M3 are closed. The split-by-construction form partitions `test_filled.py` and `test_lines.py` whatever `-k`'s substring matches overlap, and its rules check needs no collection. The shard table's only error is about 207 G of slack on the safe side, which the build's re-pack from measured fuel removes.
