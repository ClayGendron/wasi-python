# Review of 067 — the pure-Python packages' own tests: the release acceptance's 11 red groups (delta)

- **Date:** 2026-10-22
- **Reviewer:** a fresh agent. It wrote none of 067 and reviewed nothing else in wave 12.
- **Reviewed:** `git diff 459e7f35 eac93d0f`. That is the build-review answers `bde7e8c9`
  (context, CHANGELOG and README only), the fix `254fd3e5`, and the notes `eac93d0f`. The code is
  `254fd3e5`'s.
- **Box:** 45 minutes (build-class). It ran over: the wait for the run, and reading networkx's
  conftest.
- **Run:** the builder's branch run 39732496724 on `eac93d0f`, the exact commit reviewed (read
  below; not re-run, not dispatched). It is a normal-tier run: the release-tier job is skipped, so
  none of the 11 groups runs there.
- **Re-ran (EXECUTED, darwin-arm64, single node ids only; the lane held `build/lane.lock`):**
  - `uv run pytest tests/unit/test_pure_suites.py tests/checks/test_rules.py` gave 105 passed and
    2 skipped. Exit 1 is the ratchet's "1 accepted pass blocked" on a worktree with no artifacts.
    The unit suite is 36/36.
  - `test_upstream_files_are_well_formed` with `tests/unit/test_shards.py` and
    `tests/unit/test_packages.py`: 132 passed, exit 0.
  - The two new rows on `459e7f35`'s `packages.py`: 2 failed (`build/067-delta2/red.log`).
  - A simulation of the wester split with pytest's own `Expression` and its case-insensitive
    matcher, over the 397 `test_*` functions of sympy 1.14.0's `test_wester.py`.
  - The real AST depth of every split's `-k` expression in every family, compared with the
    rule's estimate.

## What the delta claims, against evidence

1. **Item groups get no family arguments** (`packages.group_args`). Met.
   - READ: `cfg.args` now goes only to groups with `paths`.
   - EXECUTED: the new row fails on the old code, which passed `['--runslow', '/upstream-demo/judge/none']`.
   - READ: a scan of every `tests/upstream/*.toml` finds one family with both `args` and an item
     group, networkx, as the notes say.
   - This is a fix, not a weakening. The group used to be refused before it collected anything.
2. **The wester split is rebuilt by section prefixes.** Met.
   - EXECUTED: each of the 397 tests matches exactly one of the nine groups. The counts are 105,
     97, 93, 33, 41, 1, 1, 1 and 25.
   - The `W` section is the remainder, and `test_W25` is in it. Its trap deselects it there.
   - No keyword can match the module name `test_wester.py`. `test_W` is never a term, as the notes
     say.
3. **The new split rule, `SPLIT_DEPTH` 150.** Met.
   - EXECUTED: the estimate `i + max(terms)` is within 4 levels of the real depth of pytest's AST
     in every split of every family. The deepest current split is `sympy-r-matrices-6-3` (real
     108, estimate 111). The old wester parts were real 278 to 286.
   - The rule adds a refusal. It loosens nothing.
4. **utilities-6 joins utilities-4.** Met.
   - READ: `test_xxe.py` is XXE test data with no test function.
   - READ: the builder's kept stream for utilities-4 is green apart from its listed class.
5. **The seventh trap, `sympy-slow-W25`.** Met.
   - READ: upstream marks W25 `@XFAIL @tooslow`.
   - READ: the builder's timing run (`build/067/timing/1792628527-170.log` in its worktree) ends
     with `S ...::test_W25` and no `R` line.
   - READ: the trap's stream is "out of fuel" at 50 G.
   - The same class of trap, with the same reason, as the six before it.
6. **461 groups judged clean from their streams.** Met, for the group checks.
   - READ: `verify.py` calls the judge's own `packages.judge`, the selects-nothing rule and the
     split counts.
   - READ: `verify-1.txt` names exactly the 11, and `verify-2.txt` reads "461 groups judged; 0
     with findings".
   - READ: the streams of the re-run groups are dated after the fix (01:45 to 02:00).
   - It does not judge the class or trap checks, the list files or the gap digests. Those were
     shown by node id (`fix-3.log`).
7. **The new rows were seen failing first.** Met, with a caveat (Note 2).
8. **Code speaks for itself.** Met.
   - READ: the added comments, docstrings and strings in `tests/` and `.github/` name no
     specification, review or `context/` path.

## Findings, most severe first

1. **M1. The `doctest-output` class on `networkx-r-doc` gives a cause its evidence contradicts**
   (`tests/upstream/networkx.toml`, the `[[expected]]` `doctest-output` block; its gap in
   `tests/known_gaps.toml`). The reason says each example's printed output differs in the guest.
   At least three of the eight raise instead. The cause is how the judge stages the group, not the
   guest's output:
   - networkx's `conftest.py` has an autouse `set_warnings` fixture. It ignores the UserWarning
     "The hashes produced for " and the DeprecationWarning "\n\nbfs_predecessors".
   - An item group loads no conftest.
   - `tests/upstream/networkx.ini` sets `filterwarnings = error`.
   - So the warning raised in `weisfeiler_lehman_graph_hash`, `weisfeiler_lehman_subgraph_hashes`
     and `bfs_predecessors` becomes an exception.
   - The stream agrees. Its fragments are traceback lines ("in _call_if_no_backends_installed",
     "`...bfs_predecessors[12]>`, line 1, in <module>"), not an Expected/Got diff.
   - Upstream, these examples pass.
   - The other five are not read either. The driver keeps one line of the last 400 characters of
     the report, so neither the stream nor the builder's logs hold the cause.

   **Failure:** the class admits eight failures under a reason that blames the guest. Any of them
   could be a real guest fault, and the reason would hide it. For at least three it is the wrong
   answer. A class must name its cause, or say plainly that the cause was not read, as
   `sympy-tooslow-fails` does.

   **Fix:** read the eight reports. Either:
   - (a) give `networkx-r-doc` the conftest's warning filters, for example as `-W ignore:...`
     lines for item groups or as an ini of its own. The three then pass as they do upstream, and
     the class shrinks; or
   - (b) split the class by cause, with true reasons. "upstream's conftest, which an item group
     does not load, ignores the warning the example raises; the ini makes warnings errors" for
     these three. The rest by what is read, or "the cause is not read".

   Either way, the list file, the gap's count and digest, and the README's class line move with
   it. **Evidence that closes it:** the eight reports quoted in the landing notes, and the class
   or classes re-judged by node id.
2. **L1. The self-check was not brought up to date for the delta, and does not name the slip**
   (`context/specifications/067-...md`, "Before you ask for a review"). It still says:
   - rebased onto `99dcd257`;
   - CI run 39720564953 on `84c5955c`;
   - 420 release groups, six traps, units 34.

   The process slip, which measured fuel and exit codes instead of the group check's verdict, is
   described in the notes but not in the list.

   **Fix text:**
   - "rebased onto origin/wave/12 459e7f35, no conflict";
   - "CI run 39732496724 on eac93d0f, read: <its red lines>";
   - "419 release groups, seven traps, units 37";
   - a new item: "every group's measured fuel taken only from a session its group check judges
     clean (verify.py over every kept stream, 0 findings); the first build took fuel and exit
     codes for verdicts, and 11 groups that never ran were recorded as measured".
3. **L2. No check in the repository catches a group that never passes before the release tier.**
   - The release tier itself catches it: that is how the 11 were found.
   - `verify.py`, the "lesson kept as a tool", lives under `build/067/scratch/`. The repository
     ignores that folder, so the next builder will not have it.
   - **Fix:** move the tool into `tests/harness/` (or a `scripts/` helper) that the measuring
     step calls, so a `measured` value is written only from a session with no findings. Or name
     it as a follow-up with a roadmap line. Text-only is acceptable for 0.1.0.
4. **L3. The stream drops a failed doctest's cause** (`tests/upstream/package_drive.py`,
   `DoctestItem.runtest`). `first_line("".join(report)[-400:])` keeps one line of a window
   taken from the middle of the report. A reader can tell neither an Expected/Got diff from an
   exception, nor which exception. That is why M1 was not seen. **Fix:** keep the report's
   last line (the exception line), or the first Expected/Got line, in the `R` text. This can go
   with M1 or be a follow-up.

## Notes

- **N1.** The trap `sympy-slow-W25` gives its group as `sympy-r-utilities-5-wester-1`, but by the
  split its node falls in `-wester-9`.
  - It is harmless: the deselect goes by file to every wester group, and the tier and shard are
    the same.
  - `-wester-9` would say where it lives.
- **N2.** The split row's red on the old code is an `AttributeError`: `packages.SPLIT_DEPTH` did
  not exist. It is not the assertion. The assertion would also fail there: the old `split_errors`
  has no message containing "terms" (EXECUTED: `grep -c terms` on `459e7f35` gives 0).
- **N3.** The bound 150 lies between the deepest split known to run (108) and the shallowest known
  to overflow (about 277). Depths in between have not been tried in the guest, and the comment
  says so.
- **N4.** `-wester-8` (`test_W23`, 817.6 G) is the delta's largest group. At the build review's
  0.31 s per G that is about 4.2 minutes on Linux, well within the 30-minute job (INFERRED).
  - The release matrix is now 229 of 256.
- **N5.** The landing notes say "W9, W23 and W25 are parts of their own". The parts that are their
  own are W9, W23b and W23. W25 is the trap.

## Constitution checks

- §4: no source patch, pin or recipe changed. Every new number is fuel, labelled EXECUTED and
  measured on darwin-arm64.
- Rule 4 (never weaken the judge):
  - The argument fix, the split rebuild, the move of utilities-6 and the new rule all tighten or
    repair the judge.
  - The trap follows six precedents.
  - The new class pins its eight members, so no new failure can hide behind it. But for at least
    three of them its reason is wrong (M1).

## The run

Run 39732496724 on `eac93d0f`. READ with `gh run view --json jobs,conclusion` and the gather's
failed log.

- Of 52 jobs, 46 succeeded, 5 were skipped and 1 failed. The skipped jobs include the release
  tier.
- The failed job is the gather. **Its one red line is G7**, "the newest acceptance is not on the
  release's set (SHA256SUMS)". That is a branch run's red line.
- Tally: 853/1,872 pass, 128 gap, 7 blocked, **0 fail**. The unit suite is 5,370/5,400, with 30
  skipped.
- The set was reused (`wasi-python-set-v1-87caffda…`).

The run's verdict is green but for G7. It does not run 067's release groups. Those are judged by
the lane's release acceptance, which is running on `eac93d0f` now.

## The lane's question: does a written answer close M1 for 0.1.0?

**Yes.** For 0.1.0, an answer in writing under `context/` closes M1. It does not need a code fix
first. There are four reasons:

- **The judge's verdict is right, even though the reason is wrong.** The class pins its eight
  members by node id, with a gap of fixed count and digest. A ninth failure in the group is red,
  and so is a member that changes.
- **No pass is lost or hidden.** `networkx-r-doc` is a new group. It never passed in an accepted
  record, because its only earlier session was refused at its arguments.
- **The flaw is the text of the reason, not the check.** Fixing it in `tests/` would move the
  judge hash and void the release acceptance running on `eac93d0f`. That would buy no stronger
  verdict.
- **It is what rule 8 allows.** A finding may be "fixed or answered in writing first". A
  Medium's written answer must hold the evidence that closes it.

**The written answer must:**

- (a) Name the three staging failures (`weisfeiler_lehman_graph_hash`,
  `weisfeiler_lehman_subgraph_hashes`, `bfs_predecessors`) and their cause. networkx's conftest
  `set_warnings` fixture is not loaded in an item group, and `networkx.ini` sets
  `filterwarnings = error`.
- (b) Label each of the other five READ, with its cause, or say plainly "cause not read". The
  stream holds too little to read them (L3). A guest re-run to read them is not required for
  0.1.0.
- (c) Reserve the follow-up, with its roadmap line. It gives item groups the conftest's warning
  filters, or splits the class with true reasons, and it carries L3's fuller `R` text.
- (d) Say what holds meanwhile. The eight are counted and named, a ninth is red, and no pass is
  hidden.
- (e) Keep the release's prose honest. The README's `doctest-output` line should not be read as
  saying that networkx's three are the guest's output. One clause in `README.md` (context-class
  text) is enough: "for networkx, also examples that raise a warning its conftest silences, which
  an item group does not load".

The wrong reason string stays in `tests/upstream/networkx.toml` and `tests/known_gaps.toml`
until the follow-up. That is the cost of this answer, and it is acceptable for one release.

## Verdict

**Lands once M1 is answered in writing as above (a to e). No code change is needed before 0.1.0.**
The Lows need only their text.
