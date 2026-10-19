# 091 — numpy-core's layout-dependent fuel as a fact

- **Status:** **drafted 2026-10-19** on `spec/091-numpy-core-layout-fuel-as-a-fact`, from main
  `dc8988c` (the draft was written from `302df18`; the one commit between them adds only
  `.claude/settings.json`). Not built. A prototype of the whole change was tried in a scratch copy
  of `302df18` (the section "The prototype"). It changes neither the guest's imports nor its
  exports, the artifact set nor the build recipe, so §5.6 asks no review before build; the lane
  asks for a short one anyway, because the change narrows what the ratchet covers. A different
  agent reviews the build.
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

## Principle

A test whose fuel measures an address is still run, and still counted. Its outcomes stay in the
group's verdict. Only its fuel leaves the ratchet, and it leaves as a recorded fact with a wide
bound, by a reviewed judge change (AGENTS.md rule 4), never by widening the tolerance.

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
   - **`fuel`**: the group's own session only, without the 84 cases. About 145 G (INFERRED:
     203.36 G, less the cases' 61.44 G, plus the second session's start and collection of
     `test_strings.py`, a few G); the build measures it.
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
     accept, in one clause ("fuel fact string-comparisons 61.4 G"). No cause is asked below the
     cap. This keeps a trail across landings in git at the cost of one number.
   - `context/progress/README.md` gains one paragraph saying all of this.
5. **The sanity bound: the cap, at 140 G.** The fact's session runs with fuel 140 G. If the
   test's cost reaches it, the session ends "out of fuel at <node>", a finding, and the group's
   check fails: red, exactly as a group that runs away.
   - 140 G is 2.28 times the 61.44 G measured on main's set and 2.13 times 073's 65.73 G. The
     rule for the entry: **the cap is at least twice the fact's fuel when last measured**; the
     build checks it with its own measurement and raises the cap to the next 10 G that keeps it.
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
     its id is unique among groups and traps; no `not_selected` file or trap entry overlaps it;
     its file is a tarball member (when the tarballs are present); a regrtest suite has none.
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
      reason drops the layout clause and quotes the fact (Decision 4). If the group's own fuel
      still rises past the tolerance, that is a residual to explain like any other row: the traces
      so far put it well under the test's moves (047: the other 9,923 tests net −277 M; 071:
      within ±1.0 M a test; 073: +0.19 G, which its review gives to the unfreeze).
    - **086.** Its Decision 9 traces any row whose A/B rise is 1% to 3%, numpy-core's
      `test_strings.py` first. After 091 its A/B table carries numpy-core's own session as the
      metric row and the fact beside it; the fact needs no trace below its cap. Criterion 5
      gives 086 that A/B in advance.
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
   with the fall from 203,355,507,505.
5. **The layout control.** On two sets that differ in layout, main's and the newest build-class
   set at hand (086's today, copied read-only), both judged by this branch:
   `test_upstream_suite[numpy-core]`'s `fuel` and its fact, on each. The landing notes give the
   four numbers. The claim this spec stands on is that the group's own fuel moves far less than
   the fact: **if the group's own fuel still differs by more than 1% between the two sets** (086's
   trace threshold), the build stops, and the builder records where it stood (AGENTS.md rule 7)
   before anything lands.
6. **Nothing else moves.** `ruff check` and `ruff format --check` green. The fast tier `-n 3`,
   then the full judge once (`-n 3`) against the private copy of main's set: no failure; lost 0;
   gained 0; grew 0; fewer 0; `judge changed` names the seven files; the one accepted fuel row
   past its tolerance is numpy-core's, falling. numpy-lib, numpy-others and pandas' eight groups
   are within tolerance of their accepted fuel (the stage gains one small file outside pytest's
   root folder; the run shows it changes nothing).
7. **The scoreboard** of that run ends with the "not machine-checked" line naming the fuel fact.

## For the lane

- **Order.** Land 091 before 086 and the other build-class specifications when the queue allows
  (Decision 10). It is parallel-safe and may be batched.
- **Accept with** `--accept "spec 091: numpy-core's layout-dependent fuel as a fact (the owner's
  decision P3, 2026-10-19)"` and `--accept-judge "spec 091: numpy's test_string_comparisons is a
  fuel fact: tests/upstream/numpy.toml's [[fuel_fact]] string-comparisons deselects its 84 cases
  from numpy-core's session and runs them alone in a second session inside
  test_upstream_suite[numpy-core] (tests/harness/upstream.py: FuelFact, fact_spec,
  fact_findings, combine, the rules, the caps); their outcomes still count in the group's passes,
  classes and digest; their fuel is the fact fuel_facts, never ratcheted, red only at its 140 G
  cap; sameness.py compares it to the tolerance; the scoreboard names it as not machine-checked;
  new rows in tests/unit/test_upstream.py and tests/unit/test_several_cores.py; numpy-core's
  accepted fuel falls by the test's share; the one allowance edit is the [[fuel_fact]] entry; no
  check, golden, gap, class list or other allowance edited"`.
- **No `--accept-growth`, no `--accept-fewer-passes`, no `--retire`** (Decision 8).
- **The expected record:** lost 0, gained 0, grew 0, fewer 0; `judge changed`, seven files;
  numpy-core's accepted fuel about 145 G (from 203,355,507,505), passes 9,519.
- **Sameness.** Both records now carry `fuel_facts`; `sameness.py` compares it to the tolerance.
  A difference there beyond the tolerance is a real difference, and rule 6a applies.
- **At the next build-class landings,** the notes quote the fact in one clause and drop the
  numpy-core layout clause from the growth reason (Decision 10).

## Landing notes

(To be filled at build and landing.)
