# Pre-build review of 091 — numpy-core's layout-dependent fuel as a fact, 2026-10-19

- **Reviewer:** a fresh agent. I wrote none of 091, its prototype or the proposal it rests on.
- **Under review:** `context/specifications/091-numpy-core-layout-fuel-as-a-fact.md` on
  `spec/091-numpy-core-layout-fuel-as-a-fact`, commit `3e9d68b` over main `dc8988c`, and the
  prototype `…/scratchpad/091/prototype.diff` (636 lines, against `302df18`).
- **Read:**
  - the spec in full; the prototype diff in full; the owner's decision (`context/decisions.md`
    on main `b4d7c8e`, "numpy-core's layout-dependent fuel as a fact (P3)") and P3 of the
    proposals memo;
  - in the code: `tests/harness/upstream.py` (`group_spec`, `trap_spec`, `judge_group`,
    `_ended`, `caps`, `rule_errors`, `Session._prepare`, `_run`, `group`),
    `tests/upstream/drive.py`, `tests/harness/scoreboard.py` (`compare`, `accept`),
    `tests/harness/sameness.py`, `tests/harness/paths.py` (`JUDGE_PATHS`, `judge_files`),
    `tests/harness/gather.py` (G5), `tests/checks/test_v1_3_upstream_suites.py`,
    `tests/upstream/numpy.toml`, `tests/release_shards.toml`;
  - 089's diff of `upstream.py` and `regrtest.py` (`spec/089-host-litter-never-reaches-a-verdict`,
    `bcb9d24`); 073's build review (lane scratchpad, "Where it is"); 086's evidence memo
    (`context/research/2026-10-19-the-toolchain-move-evidence.md` on `ea9f42e`, sections 7 and 8);
  - numpy 2.5.2's `numpy/_core/tests/test_strings.py`, unpacked from the pinned tarball in
    `downloads/` into this review's scratch folder; pytest's `_pytest/main.py` (9.1.1 on the host;
    the kit pins 9.0.3, the same code for both points below).
- **How I ran things:** in the prototype's scratch tree (`…/scratchpad/091/tree`, `uv run
  --no-sync`): the twenty new unit rows, and `caps()` per family on the real configurations. No
  upstream suite, no project git tree touched, no main-tree `build/`.

Labels: **EXECUTED** (I ran it), **READ**, **INFERRED** (reasoned, not run).

## Short version

The mechanism is right, and the prototype matches the spec.

- **It is a narrowing with a stated reason, not a quiet weakening.** The cases still run and
  still count. Only their fuel leaves the ratchet, by a reviewed judge change with `--accept-judge`.
- **The selector is exact.** `node[` deselects exactly the 84 cases, and the second session runs
  exactly them (EXECUTED and READ, section 1).
- **Combining is exact.** Passes, counts, members and the digest equal one session's when nothing
  else changed. The sessions cannot overlap without a finding (READ, EXECUTED, section 2).
- **The acceptance plan is right.** No `--accept-growth`: `accept` keeps the minimum fuel by
  itself. The budget stays under 3 T (EXECUTED, section 3).

Three things to fix:

- **F1.** Criterion 5's control compares sets that differ in compiler, not only in layout. Its
  1% stop line is undefined in its base, and 086's own numbers put the residual at about 0.85%,
  a thin margin either way.
- **F2.** 091 shrinks numpy-core's moves, but it will not keep the row inside 1e-4 at a
  build-class landing. The spec should say so plainly, so the hours it promises are honest.
- **F3.** The `--accept-judge` text says no check was edited. `test_v1_3_upstream_suites.py`
  is edited.

## 1. Does `node[` select exactly the 84 cases?

Yes (READ, EXECUTED).

- `test_string_comparisons` is parametrized over six comparisons, seven dtype pairs and
  `aligned` in `[True, False]`: 6 × 7 × 2 = **84**. It has no `slow`, skip or xfail mark, so
  `-m "not slow"` keeps every case in both sessions.
- The only other name with that prefix is `test_string_comparisons_empty`: 6 × 4 = **24**
  cases. Decision 2's reason for the `[` is exactly right.
- No class in `test_strings.py` has a method of that name, and no other file defines it.
- `--deselect` is a raw prefix: `colitem.nodeid.startswith(deselect_prefixes)`
  (`_pytest/main.py:489`). A positional `file::name` matches `node.name.split("[")[0] ==
  matchparts[0]` (`:1007`), so the fact's session never picks up the `_empty` sibling.
- The driver passes `--rootdir=/upstream/tests`. So node ids are `numpy/_core/tests/…` in both
  sessions, which is the form `owns()` and the class lists expect.
- A non-parametrized entry is caught at run time: its id has no `[`, so the group runs it
  (`owns` is false there) and the fact's session reports "ran nothing of" and "outside the entry".

## 2. Is combining two sessions exact?

Yes (READ; EXECUTED for the unit rows).

- `combine` adds `passes` and `counts`, takes the union of each class's members (sorted, as
  `judge_group` sorts them), and hashes the digest over every passed id. `passed_digest` sorts
  its input, so the union gives the one-session digest whenever the passed set is the same.
- No double count: `fact_findings` turns any case seen in the group's session, or any foreign
  test in the fact's session, into a finding. A fact session that runs out of fuel part way also
  loses passes, so it is red twice over.
- The class checks call `Session.group`, which is cached. They read the combined members, so a
  failure among the 84 cases is admitted or named exactly as before.
- `gather`'s G5 compares `passes` and `passed_digest` between systems. Both are unchanged in
  meaning.
- `fuel_facts` is recorded only for a pytest suite that has facts. numpy-lib, numpy-others,
  pandas and CPython's records do not change.
- `sameness._check` removes `fuel_facts` from the exact fact comparison and compares each value
  with `fuel_differs`. A fact present in one record and absent in the other is a difference. The
  new row in `test_several_cores.py` covers within, beyond, and a renamed key.
- The twenty rows pass on the prototype: `20 passed` (EXECUTED).

## 3. The ratchet, the budget and the flags

All as the spec says (READ, EXECUTED).

- `compare` flags fuel only when it rises: `value > old * (1 + FUEL_TOLERANCE)`
  (`scoreboard.py:160`). A fall is in no red list.
- `accept` keeps `min(old, value)` for fuel when no growth reason is given and the engine is the
  same (`:254-255`). numpy-core's accepted fuel falls by itself. **No `--accept-growth`.**
- `passes` is in `COUNTS_UP` and stays at 9,519. **No `--accept-fewer-passes`.**
- `JUDGE_PATHS` contains `tests`, and not `context/`. So the seven files under `tests/` are the
  judge change. `context/progress/README.md` is not part of it. The scratch run printed `judge
  changed: tests/checks/test_v1_3_upstream_suites.py, tests/harness/sameness.py,
  tests/harness/scoreboard.py and 4 more` (EXECUTED).
- `caps()` on the real files: `/upstream` **2.659 T**, under its 3 T budget; `/cpython` 2.26 T,
  unchanged (EXECUTED).
- **The 140 G cap is sound against layout noise.** 073's bisection puts six bool conversions at
  25.8 M of about 731 M a case, about 21%. To double the test, that part would have to grow about
  5.7 times. The largest move seen is +7% of the test (+33% of that part). The cap cannot turn
  red from layout alone. Whether 2× is the right width is F4.

## 4. 089, 086 and 073

- **089** (READ on `bcb9d24`): `litter.seal(self.root)` runs once at the end of `prepare`, after
  every package's `_prepare`. 091 writes `judge/<id>.json` inside `_prepare`. So the file is
  written before the seal, as the spec says. The hunks do not touch.
- **073:** correctly stated. Its growth reason gave the cause as unknown, and its build review
  found it. Its residual (+0.19 G, the unfreeze) is real, and it stays red after 091. That is
  right; see F2.
- **086:** the "A/B in advance" needs one more sentence (N4).

## Findings

### F1. Criterion 5's control confounds layout with codegen, and its 1% stop line is undefined and thin. Blocks build: a spec edit of a few lines (READ, INFERRED)

- **The pair.** Main's set against 086's compares two compilers, not two layouts. 086's other
  fuel rows moved from −0.444% to +0.444% with the toolchain alone (its memo, section 7). The
  siphash13 flag (S5) now also rides in 086, which changes the hash of every string key. So a
  difference in the group's own fuel there says little about layout.
- **The margin.** 086 measured 798 → 1,050 fuel per bool. The test makes 84 × 6 × 32,768 ≈ 16.5 M
  conversions, so about +4.16 G of numpy-core's +5.37 G comes from the test (INFERRED). That
  leaves about **+1.2 G, roughly 0.85%** of a group near 142 G. That is 0.15 points under the
  stop line. A real toolchain effect could stop a sound build, or the control could pass
  without saying anything.
- **The rule.** "Differs by more than 1%" names no base.
- **Fix:**
  - Make the stop rule's pair **main's set against 073's** (`/Users/…/wasi_python-073/build/out`
    exists). They differ mainly in layout, plus one small known change. 073's review already gives
    the expected numbers: the fact +4.29 G (+6.99%), the rest about +0.19 G.
  - Define the measure: r_own = (own_B − own_A) / own_A, and r_fact the same way. The claim
    holds when |r_own| ≤ 0.5% **and** |r_own| ≤ ¼·|r_fact|. Pick the numbers, but write them down.
  - Keep 086's pair as information for 086's A/B. Read it against the toolchain's spread on the
    other rows, not as a stop.

### F2. Say plainly that numpy-core's row will often still be red at a build-class landing. Fix before landing: wording (READ, INFERRED)

- The tolerance on about 142 G is about 14 M. The residuals seen so far are all far past it:
  073 +0.19 G (real: the unfreeze), 086 about +1.2 G (INFERRED, F1). 047's −277 M was a fall.
- The Problem section, and P3's "1 to 2 h at each of about 12 landings", read as if the row
  stops being red. Decision 10 does treat a residual "like any other row". But the reader has to
  infer that this will be common.
- A diffuse residual has no single test to blame. It can be slower to explain than "the test
  again".
- **Fix:** one paragraph in Intent or Decision 10. What 091 removes: the address-keyed swing of
  4 to 5 G in one test. What stays: a residual of tens to hundreds of M that still needs a growth
  reason. That residual is now the product's own change or diffuse layout. Name how it is read
  (073's per-quarter split is the model), and tell the owner, since the hours estimate shrinks.

### F3. The `--accept-judge` text says "no check … edited", but a check file is edited. Fix before landing (READ)

- `tests/checks/test_v1_3_upstream_suites.py` gains the `fuel_facts` record and two docstrings.
  The history line is the permanent record of the judge change, so it must be exact.
- **Fix:** replace "no check, golden, gap, class list or other allowance edited" with: "the one
  check edit is test_upstream_suite recording the fact fuel_facts, plus two docstrings; no
  assertion, golden, gap, class list or other allowance edited". It may also name the seven files.

### F4. The fact can hide a real slowdown up to twice the test's cost. Say so, and add a review band. Low (READ, INFERRED)

- The fact is about 61 G, about 30% of numpy-core's fuel.
- About four fifths of it is not bool conversion. It is the S and U comparison ufunc loops over
  32,768 elements, `compare_chararrays`, `astype` and `tolist`. Nothing else in the judge runs
  those at that scale.
- P3's "it would also show in the group's other rows" does not hold for those loops. A compiler
  move (086) is exactly the kind of change that could slow them. After 091, a 1.9× slowdown there
  is green and needs no cause.
- **Fix:** state the risk in Principle or Decision 5, then do one of these:
  - **(a)** In the landing notes, a fact that moves more than 10% from the last quoted value
    (above the largest layout move seen, +7%) gets one sentence of cause from the reviewer. It is
    still not red.
  - **(b)** Set the cap at spec 050's 1.5× floor (100 G). Layout alone would still need the
    bool part to grow about 3.4 times.

  (a) is cheap and keeps the owner's "fact, not ratchet". (b) is optional.

### F5. Nobody keeps the cap's "at least twice" invariant after 091 lands. Low (READ)

- The rule is checked at 091's build. The unit row pins a lower bound of 2 × 65.73 G. After
  that, nothing re-reads the cap against the measured fact.
- **Fix:** one line in "For the lane" and the progress README paragraph. When a landing's
  quoted fact exceeds half the cap, that landing either raises the cap (a judge change, with its
  reason) or its reviewer says why not.

### F6. Criterion 4: name the global random state as the first suspect if the digest differs. Low (READ, INFERRED)

- The test calls `np.random.shuffle`, which draws from numpy's global `RandomState`. That state
  is seeded at import from the host's deterministic `random_get`.
- Moving the 84 cases out of the group's session changes the random state that every later test
  sees: the rest of `test_strings.py`, `test_umath_accuracy.py`, `test_umath_complex.py` and
  `test_unicode.py`.
- The outcomes will most likely be the same, but this is a real way for the digest to differ.
- **Fix:** in criterion 4, say that a digest or counts difference stops the build and is traced.
  The random state is the first suspect. Never accept it as "layout".

## Notes

- **N1. The 145 G inference** reads "plus the second session's start". 073 measured the 61.44 G
  as a session on its own, so it includes a start and the collection of `test_strings.py`. The
  group's own fuel is therefore 203.36 G − 61.44 G + that start. Say it that way: the second
  session's start is part of the fact, never part of the group's `fuel`. The fact is "the
  cases plus one session's start", not the test's cost alone.
- **N2. The overlap rule** (`t.node.startswith(f.node) or f.node.startswith(t.node)`) also
  flags a trap on a sibling such as `test_string_comparisons_empty[…]`. That is stricter than
  needed and harmless. The exact test: `t.node.startswith(f.node + "[") or (f.node + "[").startswith(t.node)`.
- **N3. A rejected alternative left unstated:** making the lookup itself stable. That could be
  a link-order recipe that fixes `PyBool_Type`'s place, or a numpy patch adding a `bool` fast
  path (§4.1 makes the patch costly). One line under Decision 1 closes the question.
- **N4. 086's "A/B in advance"** goes stale if 086 rebuilds after its rebase, and S5's flag
  makes that likely. Decision 10's 086 bullet should say the A/B is measured again on 086's
  landing base.
- **N5. Wall time.** The group's check now pays a second interpreter start and a second
  collection of `test_strings.py`, a few G in all. The work is the same check on the same
  worker and shard (`release_shards.toml`, numpy-core's shard), so nothing else changes.
- **N6. Rule 4.** This is the shape the rule asks for: its own change, a written reason, the
  owner's approval, `--accept-judge`, and a list pinned in two files. It does not turn a red run
  green; numpy-core is accepted today.

## Verdict

**Build once F1 is written in.** F2 and F3 are wording, due before landing. F4 to F6 are Low:
answer them in writing or in the spec. The mechanism, the selector, the combination, the guards,
the flags and the budget all hold as written, and the prototype matches the spec.

## One line

The design is sound and exact: the 84 cases still run and count, and only their address-keyed
fuel leaves the ratchet. Fix the layout control's pair and threshold, say that a residual stays
red, and correct the accept text.
