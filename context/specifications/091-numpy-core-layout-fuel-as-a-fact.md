# 091 — numpy-core's layout-dependent fuel as a fact

- **Status:** **built 2026-10-19** on `spec/091-numpy-core-layout-fuel-as-a-fact`, on main
  `b4d7c8e` (the Landing notes). **Build review: "lands once F1"**
  (`../reviews/091-numpy-core-layout-fuel-as-a-fact-build-2026-10-19.md`); F1 fixed, F2 and F3
  fixed (the section "Disposition of the build review"). Not yet rebased: it enters wave 1 last.
  Before that: **drafted 2026-10-19** on the same branch, from main
  `dc8988c` (the draft was written from `302df18`; the commits between them touch no file under
  `tests/`), rebased onto main `b4d7c8e`. **Revised 2026-10-19 against its pre-build review**
  ("build once F1", `../reviews/091-numpy-core-layout-fuel-as-a-fact-spec-2026-10-19.md`; the
  section "Disposition of the pre-build review"). A prototype of the whole change was tried in a
  scratch copy of `302df18` (the section "The prototype"). It changes neither the guest's imports
  nor its exports, the artifact set nor the build recipe, so §5.6 asks no review before build; the
  lane asked for a short one anyway, because the change narrows what the ratchet covers. A
  different agent reviews the build.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** a judge change; **parallel-safe**, not build-class (§5.7). It edits
  `tests/upstream/numpy.toml` (one `[[fuel_fact]]` entry and its header lines),
  `tests/harness/upstream.py`, `tests/harness/sameness.py`, `tests/harness/scoreboard.py` (one
  phrase of the "not machine-checked" line), `tests/checks/test_v1_3_upstream_suites.py` (one
  fact and two docstrings), `tests/unit/test_upstream.py` and `tests/unit/test_several_cores.py`
  (new rows), and `context/progress/README.md` (one paragraph). No `src/`, `scripts/`,
  `recipes/`, `downloads/`, workflow, README or CHANGELOG. It moves one accepted fuel row down and
  none up: **the lane accepts it with `--accept-judge` alone** (Decision 8).
- **Depends on:** nothing unlanded. It meets, textually only:
  - **089** (built, in the lane) edits `tests/harness/upstream.py` (`safe_unzip`, `stage`,
    `Session.close`, `prepare`, `_run`). 091 edits `Session._prepare` (one loop after the traps'),
    `Session.group`, and module-level code; the hunks do not touch. Whichever lands second
    rebases. One ordering matters and holds either way: the fact's `judge/<id>.json` is written in
    `_prepare`, before 089 seals the stage at the end of `prepare`.
  - **085** adds a paragraph to `context/progress/README.md` and one line to `scoreboard.py`'s
    `accept`; 091's paragraph and phrase are elsewhere in each file.
  - **073, 086, 043, 039**: no shared file. Their numpy-core growth reasons are the subject of
    Decision 10.
- **Research it stands on:** the owner's decision of 2026-10-19 (`../decisions.md`, "numpy-core's
  layout-dependent fuel as a fact (P3)"), and the traces it rests on:
  - spec 047's build review, its delta addendum (`../reviews/047-regex-build-2026-10-18.md`,
    "Where it sits" and "Why"): +1,092 M of numpy-core's +1,284 M in `test_string_comparisons`'
    84 cases; the cause in `_global_pytype_to_type_dict`;
  - spec 071's build review (`../reviews/071-deep-recursion-raises-recursionerror-build-2026-10-19.md`,
    "Where the growth lands"): +1,107 M in that test, the judge's figure +1,081 M;
  - spec 073's build review (the lane's scratchpad, to be copied with 073's landing): the test's
    84 cases alone cost **61.44 G** on main's set and 65.73 G on 073's (+4.29 G of the group's
    +4.48 G); `np.array` of 32,768 bools 25.8 M against 32.4 M; `bool` moved 0x780;
  - spec 086's evidence memo, section 8 (on its branch): `id(bool)` 0xFF0 higher; converting
    bools costs 798 against 1,050 fuel each (+31.5%);
  - spec 043's landing notes (on its branch): numpy-core +1.10 G, the binary's layout, not traced
    to one test after two attempts.

## The problem

numpy-core's group fuel moves at every build-class landing: +1.28 G at 047, +1.08 G at 071,
+1.10 G at 043's build, +4.48 G at 073's, +5.38 G (+2.645%) in 086's first measurement. The
ratchet holds it to one part in ten thousand (`FUEL_TOLERANCE`, `scoreboard.py:31`), so each of
those is red until a reviewer explains it, and each time the explanation costs 1 to 2 hours.

Four of the five traces end in the same test: `numpy/_core/tests/test_strings.py::test_string_comparisons`.

- Each of its 84 cases (six comparisons, seven dtype pairs, aligned or not) builds `expected`, a
  list of 32,768 Python bools, and passes it to `assert_array_equal` six times.
- Each call turns the list into an array. For every element numpy finds the DType of the
  element's type. `int` and `float` have pointer fast paths; `bool` is looked up in
  `_global_pytype_to_type_dict`, a dict keyed by type objects (numpy 2.5.2,
  `array_coercion.c`, `npy_discover_dtype_from_pytype`).
- A type object hashes by its address. `PyBool_Type` is static, in the data segment. Any change
  to the binary's data moves it, and with it `bool`'s place in that dict's probe sequence.
- So about sixteen million lookups (84 × 6 × 32,768) cost a few more or a few fewer
  instructions after any rebuild. The sign is chance: 073's first build moved the group −73.6 M,
  its second +4.48 G.

That number measures where a type object sits in memory. It is not a property of the product,
and a reviewer cannot act on it. It also hides real growth: a 1 G rise elsewhere in numpy-core
would read as "the layout again".

### What 091 does not fix (the review's F2)

091 removes one term: the swing of 1 to 5 G that the address-keyed lookup puts into one test. It
does not keep numpy-core's row inside the tolerance at a build-class landing.

- The tolerance on the group's own fuel, about 142 G, is about 14 M.
- The residuals seen so far are far past that: +0.19 G at 073 (real: the unfreeze, its review's
  per-quarter split), and about +1.2 G in 086's first measurement (INFERRED: its +5.37 G less the
  test's share, about +4.16 G, from 086's per-bool cost). 047's other tests net −277 M, a fall.
- So the row will often still be red at a build-class landing, and still need a growth reason.
- What changes is the reason's kind. It is now the product's own change, or a diffuse layout
  term spread over many tests, never the one test's address. A diffuse term has no single test to
  blame, so it is read as 073's review read it: the group's files in quarters on both sets, then
  per file in the quarter that carries it, two attempts, then rule 7's record.
- **The hours saved shrink.** P3 counted 1 to 2 hours at each of about 12 landings, as if the row
  stopped being red. The saving is the trace that ends in this test, and a growth reason no longer
  dominated by a few G that nobody can act on. The owner is told in the landing notes.

## Principle

A test whose fuel measures an address is still run, and still counted. Its outcomes stay in the
group's verdict. Only its fuel leaves the ratchet, and it leaves as a recorded fact with a wide
bound, by a reviewed judge change (AGENTS.md rule 4), never by widening the tolerance.

**The risk this takes (the review's F4).** The fact is about 30% of numpy-core's fuel, and about
four fifths of it is not the bool lookup: it is the S and U comparison loops over 32,768
elements, `compare_chararrays`, `astype` and `tolist`, which nothing else in the judge runs at that
scale. A real slowdown there, up to twice the test's cost, is no longer red. Two things answer it:
a review band (Decision 4: a move of more than 10% from the last quoted value gets one sentence of
cause) and the cap (Decision 5: a doubling is red).

## Decisions

1. **The mechanism: a second session inside the group's check.** The group's guest session
   deselects the entry's cases; a second guest session, in the same check, on the same stage,
   runs exactly those cases. Both sessions are judged against the group's classes and combined
   into one outcome. The check's `fuel` metric is the group's own session; the second session's
   fuel is a fact.
   - **Rejected: a check of its own per fact**, as a trap entry has. The group's `passes` would
     fall by 84, which the ratchet calls `fewer` and refuses without `--accept-fewer-passes`, and
     the cases would leave the group's count for a new node. The owner's decision keeps the
     group's passes ratcheted.
   - **Rejected: per-test fuel inside one session**, read through a door call per test line, as
     071's reviewer measured it. About 19,000 door calls a run cost fuel themselves (+54.6 M net
     in that split), `drive.py` would gain a host call, and subtracting one test's fuel from a
     session still leaves its heap effects on every later test.
   - **Rejected: deselect the test and run it nowhere.** It loses 84 passing tests of coverage.
   - **Rejected: a wider tolerance for numpy-core.** A band wide enough for +2.6% would hide a
     real regression of that size anywhere in 145 G of the group's work.
   - **Rejected: making the lookup itself stable** (the review's N3). A link-order recipe that
     pins `PyBool_Type`'s address would be a build-class change that every later recipe change
     could undo; a numpy patch adding a `bool` fast path is an upstream source change, which §4.1
     keeps few and temporary, for a cost that only the judge sees. Neither fixes the judge for the
     next address-keyed term either.
2. **The entry.** `tests/upstream/numpy.toml` gains `[[fuel_fact]]` (the singular, as `[[trap]]`
   and `[[expected]]`):

   ```toml
   [[fuel_fact]]
   id = "string-comparisons"
   group = "numpy-core"
   node = "numpy/_core/tests/test_strings.py::test_string_comparisons"
   fuel = 140_000_000_000
   reason = "each of its 84 cases turns six lists of 32,768 Python bools into arrays, and numpy finds each bool's DType in _global_pytype_to_type_dict, a dict keyed by the bool type object's address, which moves with the data segment at every rebuild: numpy-core moved +1.28 G at 047, +1.08 G at 071, +4.29 G at 073's build and with 086's toolchain, each time from this test"
   evidence = [
       "context/reviews/047-regex-build-2026-10-18.md",
       "context/reviews/071-deep-recursion-raises-recursionerror-build-2026-10-19.md",
       "context/specifications/091-numpy-core-layout-fuel-as-a-fact.md",
   ]
   ```

   - `node` is `file::function` (or `file::Class::function`) with no parameters. The group
     deselects `node[`; the fact's session runs `node`, under the group's marker
     (`-m "not slow"`), so it runs exactly the cases the group would have run.
   - **Why `node[` and not `node`.** pytest's `--deselect` is a node-id *prefix*
     (`_pytest/main.py`, `colitem.nodeid.startswith(deselect_prefixes)`). The bare node would
     also deselect `test_string_comparisons_empty`'s 24 cases, which the fact's session (a
     positional node id, matched by name) would not run, and the group would lose 24 passes.
     With `node[` the sibling stays in the group. An entry must therefore name a parametrized
     test; a plain one is caught at run time by Decision 6's findings.
   - Its fuel cap is `fuel`, which `caps()` counts in the `/upstream` family's budget: the caps
     sum from 2.519 T to 2.659 T, under the 3 T budget (spec 050, Decision 8).
3. **What the ratchet keeps.**
   - **`passes`**: both sessions' passes, added. On main's set it stays 9,519, the accepted value.
   - **`fuel`**: the group's own session only, without the 84 cases. 073's 61.44 G was measured
     as a session of its own, so it includes one interpreter start and one collection of
     `test_strings.py`. The group's own fuel is therefore 203.36 G − 61.44 G + that start and
     collection, a few G: about 145 G (INFERRED; the build measures it). The second session's start
     is part of the fact, never of the group's `fuel` (the review's N1): the fact is "the 84 cases
     plus one session's start", not the test's cost alone.
   - **The classes**: each class check reads the members of both sessions, so a failure in the
     84 cases is admitted or named exactly as before. No list file changes.
   - **`passed_digest`, `counts`, `left_out`** (facts): computed over both sessions. The digest is
     of every passed id, so it equals the one-session digest when nothing else changed: the
     build shows it unchanged against main's record.
   - **Every other row** of every check: unchanged.
4. **How the fact is recorded and shown.**
   - **In the record.** `test_upstream_suite[numpy-core]` records the fact
     `fuel_facts = {"string-comparisons": <fuel>}` in `build/progress/latest.json`. A fact is
     never ratcheted (`plugin.fact`); `accepted.json` does not keep it.
   - **Between two runs of one commit.** `sameness.py` compares facts exactly, and fuel only to the
     tolerance, because serial and parallel runs may differ by a few instructions (spec 052). The
     fuel facts are fuel, so it compares each `fuel_facts` value as it compares `fuel`; every
     other fact stays exact. Without this, a residual of a few instructions would stop a landing
     at the lane's sameness step.
   - **On the scoreboard.** The "not machine-checked" line, printed on every run and never cut,
     gains "a fuel fact's fuel below its cap (spec 091)", so no reader takes the ratchet to cover
     it.
   - **In the landing notes.** A build-class landing's notes quote the fact from the record they
     accept, in one clause ("fuel fact string-comparisons 61.4 G"). This keeps a trail across
     landings in git at the cost of one number.
   - **The review band (the review's F4).** When the quoted fact moves more than 10% from the last
     quoted value (above the largest layout move seen, +7% at 073), the reviewer gives its cause in
     one sentence. It is still not red. Below 10%, no cause is asked.
   - **The cap's keeper (the review's F5).** When a landing's quoted fact exceeds half the cap, that
     landing raises the cap (a judge change, with its reason) or its reviewer says in writing why
     not. So the "at least twice" rule of Decision 5 holds after 091 lands, not only at its build.
   - `context/progress/README.md` gains one paragraph saying all of this.
5. **The sanity bound: the cap, at 140 G.** The fact's session runs with fuel 140 G. If the
   test's cost reaches it, the session ends "out of fuel at <node>", a finding, and the group's
   check fails: red, exactly as a group that runs away.
   - 140 G is 2.28 times the 61.44 G measured on main's set and 2.13 times 073's 65.73 G. The
     rule for the entry: **the cap is at least twice the fact's fuel when last measured**; the
     build checks it with its own measurement and raises the cap to the next 10 G that keeps it.
   - **Why not 100 G, spec 050's 1.5 times** (the review's F4 (b)). It does not fit the measured
     spread with the keeper above. Today's fact (about 61 G) is already above half of 100 G, so
     the keeper would fire at once; and 073 and 086 together are expected to bring it near 70 G
     (+4.29 G and about +4.16 G), where 100 G is 1.43 times, under 050's own floor. The review
     band (Decision 4) answers the slowdown risk more cheaply than a tighter cap.
   - **Why it does not bring the noise back.** The largest move seen is +7% (073). The bool
     conversions are about a fifth of the test's cost (six of 25.8 M in about 731 M a case); to
     double the test, they would have to cost about six times as much. A layout shift changes a
     probe sequence by a few steps, not sixfold.
   - **No lower bound.** A fall is never red in this judge (the ratchet keeps the lower value);
     a collapse in the test's work shows as lost passes or findings.
6. **The checks that guard it.** In `upstream.py`:
   - `fact_findings`: the entry's cases ran exactly once. A finding if any of them ran in the
     group's session ("also ran in the group"), if its own session ran none of them ("ran
     nothing of"), or if its own session ran anything else ("outside the entry"). Each finding
     fails the group's check.
   - The second session's own findings (a trap, out of fuel, no `E` line, an unexpected failure,
     a product module from the grant) are prefixed "fuel fact <id>: " and fail the group's check.
   - **The rules** (`fact_errors`, inside `rule_errors`, so `test_upstream_files_are_well_formed`
     runs them): an entry names a group of its package, a node under that group's paths in the
     `file::function` form, a non-empty `reason`, at least one `evidence` file that exists under
     `context/reviews/`, `context/research/` or `context/specifications/`, and a positive cap;
     its id is unique among groups and traps; no `not_selected` path (a file, or a folder that
     holds the file; the build review's F3) or trap entry overlaps it (a trap overlaps when its node starts with `node[` or `node[` starts with its node, so a trap
     on the sibling `test_string_comparisons_empty` does not; the review's N2); its file is a
     tarball member (when the tarballs are present); a regrtest suite has none.
   - **The list is pinned**: `test_the_judges_one_fuel_fact_is_string_comparisons_in_numpy_core`
     asserts the whole list. A second entry is then a judge change in two files, with its reason
     and its trace, under `--accept-judge` and a review.
7. **The checks are written first.** Before any harness code, on main: the twenty unit rows of
   criterion 1 and the sameness row. Each fails on main by itself (the rows build their entry
   inside the row, so `test_upstream.py` still collects and its other rows pass).
8. **The acceptance flags, from the harness code.**
   - `scoreboard.compare` flags a fuel metric only when it **rises** past the tolerance
     (`value > old * (1 + FUEL_TOLERANCE)`); a fall is in no list that turns a run red.
   - `scoreboard.accept` keeps `min(old, new)` for fuel unless `--accept-growth` is given. So
     numpy-core's accepted fuel falls to the new value by itself. **No `--accept-growth`.**
   - `passes` is `COUNTS_UP`; it stays 9,519. **No `--accept-fewer-passes`.**
   - No node is added or removed. **No `--retire`; nothing gained.**
   - Seven files under `tests/` change, so `judge_changed` is not empty. **`--accept-judge` is
     required.**
   - Should an unrelated row grow past the tolerance on the lane's base, that is not 091's; the
     lane treats it as F8 of spec 089 says, comparing with a run of main on the same set.
9. **Caps unchanged elsewhere.** numpy-core's cap stays 310 G, 2.1 times its new fuel, above spec
   050's floor of 1.5 times. A cap is a runaway bound, not a ratchet; lowering it buys nothing.
10. **The specifications in flight.** The order between 091 and the build-class landings does
    not matter for correctness. It matters for review time.
    - **091 lands before them when the lane can** (it is parallel-safe and short; it may ride in
      a batch of parallel-safe specifications, §5.7).
    - **A build-class landing after 091** judges numpy-core without the 84 cases. Its growth
      reason drops the layout clause and quotes the fact (Decision 4). The group's own fuel will
      often still rise past the tolerance ("What 091 does not fix"): that residual is explained
      like any other row, by 073's review's quarters-then-files method (047: the other 9,923 tests
      net −277 M; 071: within ±1.0 M a test; 073: +0.19 G, which its review gives to the unfreeze;
      086: about +1.2 G, INFERRED).
    - **086.** Its Decision 9 traces any row whose A/B rise is 1% to 3%, numpy-core's
      `test_strings.py` first. After 091 its A/B table carries numpy-core's own session as the
      metric row and the fact beside it; the fact needs no trace below its cap or its review band.
      Criterion 5 measures main's set against 086's as information only; 086's A/B is measured
      again on its own landing base, since 086 rebuilds after its rebase (the siphash13 flag rides
      in it too), so 091's figures for 086 go stale (the review's N4).
    - **073.** Its `--accept-growth` reason says "upstream numpy-core +4.48 G (+2.21%) … its cause
      in the suite not established", and its build review found the cause. After 091 the lane
      rewrites that clause to the residual its rebase measures, and the fact's value.
    - **043, 039.** The same: the numpy-core clause becomes the residual, or goes.
    - **A landing before 091** keeps its reason as reviewed; 091's rebase re-measures, and its
      landing notes give the new accepted figures.
11. **No CHANGELOG or README entry.** Nothing a user of the artifact set or the wheel sees
    changes; the README quotes no numpy-core fuel.

## Intent

numpy-core's fuel row stops moving with the `bool` type's address. The 84 cases of
`test_string_comparisons` still run on every judge, and their outcomes still count in the group's
passes, classes and digest. Their fuel is reported, compared between two runs of one commit, and
red only if it doubles.

## Design

- `upstream.FuelFact` (frozen dataclass: `id`, `group`, `node`, `fuel`, `reason`, `evidence`;
  `file`; `owns(node)`, true for `node[…]` only). `Config.fuel_facts`, `Config.facts(group)`.
  `load` and `_load_regrtest` read `[[fuel_fact]]`.
- `group_spec` adds `--deselect=<node>[` for each fact of the group. `fact_spec(cfg, fact)` is
  `["-m", marker, *args, /upstream/tests/<node>]`. `Session._prepare` writes
  `judge/<id>.json` for each fact, beside the groups' and traps'.
- `Session.group` runs the group's session, then each fact's session with the fact's cap, judges
  each with `judge_group` against the group's classes, and builds the outcome with
  `combine(parts, extra)`: findings with each session's prefix, members unioned, counts and passes
  added, the digest over every passed id, finished only if every session finished. `extra` is
  `fact_findings`. `GroupRun` gains `fuel_facts: dict[str, int]`; `GroupRun.fuel` stays the
  group's own session.
- `caps()` adds the facts' caps. `rule_errors` adds the facts' ids to the unique names and calls
  `fact_errors`; the tarball-member rule includes the facts' files.
- `test_upstream_suite` records `fact("fuel_facts", run.fuel_facts)` for a pytest suite that has
  any. `metric("fuel", run.fuel)` and `metric("passes", …)` are unchanged.
- `sameness._check` compares `facts` less `fuel_facts` exactly, and each `fuel_facts` value with
  `fuel_differs`.
- `scoreboard.NOT_MACHINE_CHECKED[0]` gains "a fuel fact's fuel below its cap (spec 091)".
- **Wall time** (the review's N5): the group's check pays a second interpreter start and a second
  collection of `test_strings.py`, a few G in all, on the same worker and the same release shard
  (`tests/release_shards.toml`, numpy-core's). Nothing else moves.

### The prototype (EXECUTED, in a scratch copy of `302df18`)

The whole change above was written and tried in a scratch copy of `302df18` (no upstream suite
was run: the scratch tree has no artifacts, and main's `build/` was not used). Its diff is
`prototype.diff` in the lane's scratchpad (`…/scratchpad/091/prototype.diff`, 636 lines);
the builder starts from it.

- `ruff check` and `ruff format --check` on `src/` and `tests/`: green.
- The twenty new rows, with the build: 20 passed. On main's `upstream.py`, `sameness.py` and
  `numpy.toml`: 20 failed, one by one; the file's other rows passed.
- Four mutants, each caught: the deselect removed (two rows fail); the reason rule removed (one);
  `owns` matching the bare prefix (three); the digest over the group's session only (one).
- `tests/unit/test_upstream.py`, `test_several_cores.py`, `test_scoreboard.py` in full: one
  failure, `test_a_worker_skips_the_lanes_guards`, which needs a git checkout (the scratch copy
  has none) and fails the same way without the change.
- `test_upstream_files_are_well_formed` on the real files: passed (the tarballs absent, so the
  member rule did not run).

## Scope

In: Decisions 1 to 11, for numpy's one entry. Out: any other layout-sensitive row (043's
snapshot start and probes, the zip-directory checks); any change to `FUEL_TOLERANCE`; a lower
bound; a scoreboard line with the fact's value; fuel facts for pandas or the regrtest suites
(refused by the rules until a specification with its own trace adds one); lowering any cap.

## Acceptance criteria

1. **The checks fail first, one by one.** On main, with only the new rows added:
   `test_upstream.py`'s nineteen new rows and `test_several_cores.py`'s one fail, each by itself
   (`AttributeError` on `FuelFact` or `fact_spec`, or the sameness difference), and every other
   row of both files passes. The landing notes give the lines.
2. **The rows pass, and have power.** With the build, the twenty rows pass. The four mutants of
   the prototype (deselect removed; reason rule removed; `owns` on the bare prefix; digest over the
   group's session only) each fail at least one row; their lines are in the landing notes.
3. **The rules.** `test_upstream_files_are_well_formed` passes on the real files, with the
   tarballs present in the worktree (so the member rule runs).
4. **numpy-core, on main's frozen set** (a private `cp -c -Rp` copy, every file at nlink 1):
   `test_upstream_suite[numpy-core]` passes; `passes` is 9,519, the accepted value; `passed_digest`
   and `counts` equal those of a run of main's judge on the same set; its five class checks pass
   with their lists unchanged; the record carries `fuel_facts.string-comparisons`; the cap is at
   least twice it (Decision 5); `fuel` is the group's own session, and the landing notes give it
   with the fall from 203,355,507,505. **If the digest or the counts differ, the build stops and
   the difference is traced** (the review's F6). The first suspect is numpy's global random
   state: the test calls `np.random.shuffle`, so moving its cases out of the group's session
   changes the state every later test sees (the rest of `test_strings.py`,
   `test_umath_accuracy.py`, `test_umath_complex.py`, `test_unicode.py`). Such a difference is
   never accepted as "layout".
5. **The layout control** (the review's F1). Both judged by this branch, each a private
   `cp -c -Rp` copy at nlink 1:
   - **The stop pair: main's set (A) against 073's set (B)**, which differ mainly in layout, plus
     one small known change (073's bootstrap; its review puts the rest of the group at about
     +0.19 G and the test at +4.29 G, +6.99%). On each, `test_upstream_suite[numpy-core]`'s
     `fuel` (own_A, own_B) and its fact (fact_A, fact_B). The measures:
     r_own = (own_B − own_A) / own_A and r_fact = (fact_B − fact_A) / fact_A.
     **The claim holds when |r_own| ≤ 0.5% and |r_own| ≤ ¼ · |r_fact|.** If either fails, the
     build stops, and the builder records where it stood (AGENTS.md rule 7) before anything lands.
   - **For information only: main's set against 086's.** They differ in compiler as well as layout
     (086's other rows moved −0.444% to +0.444% with the toolchain alone), so the same two numbers
     are recorded and read against that spread, never as a stop.
   The landing notes give all eight numbers and both ratios.
6. **Nothing else moves.** `ruff check` and `ruff format --check` green. The fast tier `-n 3`,
   then the full judge once (`-n 3`) against the private copy of main's set: no failure; lost 0;
   gained 0; grew 0; fewer 0; `judge changed` names the seven files; the one accepted fuel row
   past its tolerance is numpy-core's, falling. numpy-lib, numpy-others and pandas' eight groups
   are within tolerance of their accepted fuel (the stage gains one small file outside pytest's
   root folder; the run shows it changes nothing).
7. **The scoreboard** of that run ends with the "not machine-checked" line naming the fuel fact.

## For the lane

- **Wave kind: parallel-safe** (a judge change: no `src/`, `scripts/`, `recipes/`, `downloads/`
  or workflow file). It enters wave 1 last (the lane, 2026-10-19). Its builder rebases onto the
  wave's tip when the lane sends it and names each conflict hunk it resolves. **Dry-run needs:**
  none of its own; the wave's dry run carries it (its G5 compares numpy-core's row, now the
  group's own session, with the acceptance at 1e-4 on three systems).
- **Order.** Land 091 before 086 and the other build-class specifications when the queue allows
  (Decision 10).
- **The claim list** (the rows 091 changes; the progress README's step 3a):
  - **`test_upstream_suite[numpy-core]`, fuel, falling.** It falls by the 84 cases' share less
    the second session's start, about **47.5 G (−23.4%)**, from the value the wave's other
    entries leave it at. On `b4d7c8e` the fall was 47,518,372,527 (203,355,507,505 →
    155,837,134,978, the build review's run). 091 lands after 078, whose accepted numpy-core fuel
    is **203,331,725,349**; with nothing else in the wave moving that row, expect about
    **155.81 G**. Quote the fall from the base the lane accepts on, never a fixed number: a wave
    entry that claims numpy-core growth adds its own residual to this row. A fall is accepted by
    itself (Decision 8).
  - **`test_upstream_suite[numpy-core]`, facts.** A new key, `fuel_facts`
    `{"string-comparisons": about 59.05 G}`, never ratcheted, compared by `sameness.py` to the
    fuel tolerance. Passes stay 9,519; `passed_digest` `df21e78e7032` and the counts unchanged.
  - **The judge hash changes**: `judge changed` names the seven files of the accept-judge text.
  - Nothing else: no row grows, no pass moves, no node is gained, lost or retired.
- **The exact flags:** `--accept` and `--accept-judge`, nothing else. **No `--accept-growth`, no
  `--accept-fewer-passes`, no `--retire`** (Decision 8). Each reason begins with "091:".
- **Accept with** `--accept "091: numpy-core's layout-dependent fuel as a fact (the owner's
  decision P3, 2026-10-19)"` and `--accept-judge "091: numpy's test_string_comparisons is a fuel
  fact: tests/upstream/numpy.toml's [[fuel_fact]] string-comparisons deselects its 84 cases from
  numpy-core's session and runs them alone in a second session inside
  test_upstream_suite[numpy-core] (tests/harness/upstream.py: FuelFact, fact_spec,
  fact_findings, combine, Session.group, the rules, the caps); their outcomes still count in the
  group's passes, classes and digest; their fuel is the fact fuel_facts, never ratcheted, red only
  at its 140 G cap; sameness.py compares it to the tolerance; the scoreboard names it as not
  machine-checked; new rows in tests/unit/test_upstream.py and tests/unit/test_several_cores.py;
  numpy-core's accepted fuel falls by the test's share; the one check edit is
  test_upstream_suite recording the fact fuel_facts, plus two docstrings in
  tests/checks/test_v1_3_upstream_suites.py, and no assertion changed; the one allowance edit is
  the [[fuel_fact]] entry; no golden, gap, class list or other allowance edited; seven files:
  tests/upstream/numpy.toml, tests/harness/upstream.py, tests/harness/sameness.py,
  tests/harness/scoreboard.py, tests/checks/test_v1_3_upstream_suites.py,
  tests/unit/test_upstream.py, tests/unit/test_several_cores.py"`. Both are paste-safe in zsh:
  no `"`, `$`, backquote, `!` or backslash inside the quotes.
- **The expected record:** lost 0, gained 0, grew 0, fewer 0; `judge changed`, seven files;
  numpy-core as the claim list says, passes 9,519.
- **Sameness.** Both records now carry `fuel_facts`; `sameness.py` compares it to the tolerance.
  The build review's record is on `b4d7c8e`, before 089, 083 and 078, so against the lane's record
  on the wave's tip **the lane reads as clean the rows that 089, 083 and 078 moved (their claim
  lists), checks blocked in the reviewer's worktree, and `cpython-*` fuel about 1e-4 apart, which
  is the old base's own clock noise before 083 (089's build review, F3), not 091's: 091 changes no
  regrtest path.** Any other difference, or a `fuel_facts` difference beyond the tolerance, is a
  real difference and ejects 091 (rule 6a). If the lane wants a same-base comparison, the
  reviewer's fast tier plus `test_upstream_suite[numpy-core]` on the rebased commit serves.
- **CHANGELOG: none** (Decision 11: nothing a user of the artifact set or the wheel sees changes).
  Were a line ever added, it would go under the existing unreleased section ("0.1.0a8 —
  unreleased" today; its move to 0.1.0 is its own change, since `test_rules.py` ties that section
  to `__version__`).
- **At the next build-class landings,** the notes quote the fact in one clause and drop the
  numpy-core layout clause from the growth reason (Decision 10). A move of more than 10% from the
  last quoted value gets one sentence of cause from the reviewer. When the quoted fact exceeds
  half the cap (70 G), that landing raises the cap or its reviewer says why not (Decision 4).
- **numpy-core's own row will often still be red** at those landings, by a residual that needs
  its growth reason ("What 091 does not fix"). Tell the owner the hours saved are smaller than
  P3 counted.

## Disposition of the pre-build review

The review (`../reviews/091-numpy-core-layout-fuel-as-a-fact-spec-2026-10-19.md`, on `3e9d68b`):
"build once F1 is written in; F2 and F3 before landing; F4 to F6 Low". Each is answered here.

- **F1 (the control's pair and line): fixed.** Criterion 5's stop pair is main's set against
  073's, with r_own and r_fact defined and the line written: |r_own| ≤ 0.5% and
  |r_own| ≤ ¼ · |r_fact|. The 086 pair stays, as information only.
- **F2 (the row stays red): fixed.** "What 091 does not fix" says the row will often still be red,
  how a residual is read, and that the hours saved shrink; Decision 10 and For the lane say it too.
- **F3 (the accept text): fixed.** It names the one check edit (the `fuel_facts` record and two
  docstrings), says no assertion changed, and names the seven files.
- **F4 (a slowdown hidden below 2×): answered.** The Principle states the risk. Option (a) is
  taken: a move of more than 10% from the last quoted value gets one sentence of cause (Decision 4).
  Option (b), a 100 G cap, is not: Decision 5 says why it does not fit the measured spread.
- **F5 (the cap's keeper): fixed.** Decision 4, For the lane and the progress README: a quoted
  fact above half the cap means that landing raises the cap or its reviewer says why not.
- **F6 (the random state): fixed.** Criterion 4 stops and traces a digest or counts difference,
  `np.random`'s state first, never accepted as layout.
- **N1:** Decision 3 says the start is part of the fact. **N2:** the overlap rule is the exact one,
  with a unit row for the sibling. **N3:** Decision 1 names the stable-lookup alternative and why
  not. **N4:** Decision 10's 086 bullet. **N5:** Design, wall time. **N6:** no change asked.

## Disposition of the build review

The review (`../reviews/091-numpy-core-layout-fuel-as-a-fact-build-2026-10-19.md`, on `fdab891`):
"lands once F1 is fixed; F2 and F3 Low". Each is answered here, on the same base `b4d7c8e` (not
rebased: 091 enters wave 1 last and rebases onto the wave's tip then).

- **F1 (`Session.group`'s wiring and the fact's spec file): fixed.** One unit row,
  `test_a_session_runs_the_group_then_its_fact_and_records_each_fuel` in
  `tests/unit/test_upstream.py`. It uses `_scaffold`, gives numpy a fact with its own cap, and
  replaces `Session._run` with canned sessions by name: the group's (fuel 111,000; a case of the
  fact's in it too) and the fact's (fuel 222,000; one pass and one unexpected failure). It asserts
  the two sessions' order and caps, the staged `judge/f.json` equal to `fact_spec`,
  `GroupRun.fuel` 111,000 and `fuel_facts` `{"f": 222000}`, the combined passes (3) and counts,
  the findings exactly (`fuel fact f: unexpected failed …` and `fuel fact f: … also ran in the
  group`), and that a second call is served from the cache. **Seen failing on each mutant**
  (EXECUTED; each applied to `upstream.py` alone, the row run, the file restored from a copy and
  compared with `cmp`; the lines are in the worktree's `build/091/mutants-f1.txt`):

  | mutant | how the row failed |
  |---|---|
  | M1 `combine(parts, [])` | the findings lack "also ran in the group" |
  | M2 `facts[f.id] = run.fuel` | `fuel_facts` is `{'f': 111000}`, not `{'f': 222000}` |
  | M3 group `fuel` includes the fact | `fuel` is 333,000, not 111,000 |
  | M4 the fact's session left out of `combine` | passes 2, not 3 |
  | M5 the fact's `judge/<id>.json` not written | `FileNotFoundError` on `judge/f.json` |
  | M6 the fact's findings lose their prefix | the findings start `unexpected …`, not `fuel fact f: …` |

  With the code restored, `test_upstream.py`, `test_several_cores.py` and `test_scoreboard.py`
  pass in full (168: the 167 before and this row).
- **F2 ("For the lane" written for `b4d7c8e`): fixed.** The claim list quotes numpy-core's fall
  from the base the lane accepts on (after 078's accepted 203,331,725,349, about 155.81 G), and
  one sentence says how the lane reads sameness differences: rows 089, 083 and 078 moved, checks
  blocked in the reviewer's worktree, and `cpython-*` clock noise on the old base.
- **F3 (the overlap rule matched files only): fixed.** `fact_errors` now takes a `not_selected`
  path as a folder too: an entry overlaps when its file equals the path or lies under it (a
  trailing `/` is ignored). The overlap row gains three cases: `numpy/tests` and `numpy/tests/`
  overlap, `numpy/test` does not. On the old rule the row fails at the first case
  (`('numpy/tests', [])`, EXECUTED, in `mutants-f1.txt`). The same file, `upstream.py`, so the
  seven files and the accept text stand; the text now also names `Session.group`.
- **N1 to N3:** no change asked.
- **The wave pipeline** (the owner, 2026-10-19, that night): "For the lane" now carries the
  claim list, the wave kind, the dry-run needs and the exact flags, and each reason begins with
  "091:".

## Landing notes

Built 2026-10-19 in `../wasi_python-091`, on main `b4d7c8e`, by the agent that wrote the draft (a
fresh agent reviews the build). Commits: `1b58feb` (the checks first), `4002467` (the build). The
evidence is in the worktree's `build/091/` (not tracked): `first-fail.txt`, `mutants.txt`,
`main-numpy-core.json`, `branch-main-set.json`, `branch-set-073.json`, `branch-set-086.json`,
`fuel-vs-accepted.txt`, `fast.log`, `full.log`, and the full record `latest-full.json`.

**The inputs.** Main's set is a private `cp -c -Rp` copy of `build/sets/s-c50ca51fae5eb55b-c9dcb5b8`
at `build/artifacts` (`shasum -c` OK; no file with nlink above 1; `python.wasm` `ab78e893…`, the
accepted artifact). 073's and 086's sets are private copies of their worktrees' `build/artifacts`
(`shasum -c` OK; nlink 1 after the copy, where 073's zip had 201 links). The numpy, pandas and
CPython 3.15.0 tarballs (each checked against `downloads/SHA256SUMS`), their trees and the kit's
seven wheels are APFS clones of the main tree's, with their `.DS_Store` files deleted from the
copies. Nothing in the main tree's `build/` was written.

**A slip, recorded.** The narrowed run on main's set (criterion 4, below) started while
`build/lane.lock` existed; it was one pytest process for about 70 s. Every later run waited for
the lock to clear (the control and judge scripts poll it before each run).

### What was built

As the Design says, from the prototype, with the review's N2: the overlap rule is the exact one
(`node[`), and the overlap row also checks that a trap on the sibling `test_x_empty` does not
overlap. The progress README's paragraph carries Decision 4's review band and the cap's keeper.

### Criteria 1 and 2: the checks fail first, and have power (EXECUTED)

- On main's harness with only the rows added (`1b58feb`): **20 failed**, one by one (`AttributeError`
  on `upstream.FuelFact` or `fact_spec`, and the sameness difference `p: facts {… 'f': 1000000} !=
  {… 'f': 1000090}`); the two files' other **98 passed**.
- With the build: the twenty rows pass; `test_upstream.py`, `test_several_cores.py` and
  `test_scoreboard.py` in full, **167 passed**.
- The four mutants, each caught: deselect removed, 2 rows fail; reason rule removed, 1; `owns` on
  the bare prefix, 3; digest over the group's session only, 1.

### Criterion 3: the rules (EXECUTED)

`test_upstream_files_are_well_formed` passes with the tarballs present, so the member rule ran on
the entry's file.

### Criterion 4: numpy-core on main's set (EXECUTED)

| | main's harness | this branch |
|---|---|---|
| `fuel` | 203,355,544,378 | **155,837,134,094** (−47,518,410,284, −23.37%) |
| `fuel_facts.string-comparisons` | — | **59,054,444,847** |
| `passes` | 9,519 | 9,519 |
| `passed_digest` | `df21e78e7032` | `df21e78e7032` |
| `counts` | error 3, failed 40, passed 9,519, skipped 439, xfailed 12 | the same |

- The five class checks stay gaps with their lists unchanged (28, 3, 8, 3 and 1 findings, no `+` or
  `-`). The digest and counts are equal, so F6's stop did not apply.
- The group fell by 47.52 G, not the fact's 59.05 G: the fact's session carries about 11.5 G of
  interpreter start, imports and the collection of `test_strings.py` (N1).
- **The cap**: 140 G is 2.37 times the fact here and 2.17 times its value on 086's set, so no
  raise was needed (Decision 5).

### Criterion 5: the layout control (EXECUTED)

| set | own fuel | the fact | r_own | r_fact |
|---|---|---|---|---|
| A, main's | 155,837,134,094 | 59,054,444,847 | | |
| B, 073's (the stop pair) | 155,875,288,753 | 63,518,611,360 | **+0.0245%** | **+7.56%** |
| 086's (information only) | 155,960,701,335 | 64,476,884,535 | +0.079% | +9.18% |

- **The claim holds**: |r_own| = 0.0245% ≤ 0.5%, and it is 0.003 of |r_fact|, under a quarter.
  On every set: 9,519 passes, digest `df21e78e7032`, the same counts.
- **For 086** (information): the group's own move is +124 M, not the +1.2 G the review inferred
  from 086's first measurement; the fact carries +5.42 G. 086 measures its A/B again on its own
  landing base (Decision 10).
- **The residual is still above the tolerance** ("What 091 does not fix"): +38 M on 073's set and
  +124 M on 086's, against about 15.6 M. Both rows would still need a growth reason; it is now
  tens of M, not G.

### Criteria 6 and 7: nothing else moves (EXECUTED)

- `ruff check` and `ruff format --check` on `src/` and `tests/`: green.
- **The fast tier, `-n 3`** on `4002467`, clean: 481/623 pass · 1 gap · 22 blocked · 0 fail · 119
  deselected (unit suite 1599/1607, 8 skipped); ratchet: lost 0 · absent 0 · unrun 0 · gained 0 ·
  grew 0; judge changed.
- **The full judge, `-n 3`, once**, 20:25 to 20:45, on `4002467`, clean:
  `wasi_python v1: 523/623 pass · 77 gap · 23 blocked · 0 fail (unit suite 1599/1607, 8 skipped)`;
  `ratchet vs b91e0eaa4e: lost 0 · absent 0 · unrun 0 · unrun locally 21 · gained 0 · grew 0 ·
  judge changed: tests/checks/test_v1_3_upstream_suites.py, tests/harness/sameness.py,
  tests/harness/scoreboard.py and 4 more` (the seven files; `fuel-vs-accepted.txt`). The record
  is `build/091/latest-full.json`.
- **Fuel against `accepted.json`**: 164 rows compared; **one past the tolerance, numpy-core's,
  falling** (203,355,507,505 → 155,837,134,689, −23.37%); the largest other move 0.0085%. numpy-lib,
  numpy-others and pandas' eight groups within 0.0001%. No `passes` value changed.
- The fact in the full run: **59,054,444,490**, 357 instructions from the narrowed run's: the run
  to run residual Decision 4's tolerance in `sameness.py` allows for.
- The scoreboard ends with the "not machine-checked" line naming the fuel fact.

### For the lane, confirmed

- The flags as "For the lane" says: `--accept` and `--accept-judge` only. The expected record
  holds on this base: lost 0, gained 0, grew 0, fewer 0; judge changed, seven files; numpy-core's
  accepted fuel falls to about 155.84 G, passes 9,519.
- The owner should hear the residual figures above: 091 turns numpy-core's swings from G into
  tens of M, and the row will still be red, by those tens of M, at the next build-class landings.
