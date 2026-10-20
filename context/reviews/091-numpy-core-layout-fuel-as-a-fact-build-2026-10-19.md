# Build review of 091 — numpy-core's layout-dependent fuel as a fact, 2026-10-19

- **Reviewer:** a fresh agent. I wrote none of 091, its prototype, its pre-build review or the
  proposal it rests on.
- **Under review:** `spec/091-numpy-core-layout-fuel-as-a-fact`, tip `fdab891`, on main `b4d7c8e`.
  The diff `b4d7c8e..fdab891`: `38763bb` (the spec revised, its pre-build review copied),
  `1b58feb` (the checks first), `4002467` (the build), `fdab891` (the landing notes).
- **Read:**
  - the spec in full, with its Disposition and Landing notes;
  - the pre-build review (`context/reviews/091-numpy-core-layout-fuel-as-a-fact-spec-2026-10-19.md`);
  - the owner's decision (`context/decisions.md` on main, "numpy-core's layout-dependent fuel as a
    fact (P3), approved");
  - the whole code diff: `tests/harness/upstream.py`, `sameness.py`, `scoreboard.py`,
    `tests/checks/test_v1_3_upstream_suites.py`, `tests/upstream/numpy.toml`, the twenty new unit
    rows, `context/progress/README.md`;
  - around it: `judge_group`, `group_spec`, `trap_spec`, `rule_errors`, `Session.prepare`,
    `_prepare`, `_run`, `group`; `scoreboard.compare` and `accept`; `sameness._check` and
    `differences`; `paths.JUDGE_PATHS`; `tests/upstream/drive.py`; `gather.py` (what it reads of
    `facts`);
  - main's `upstream.py` and `plugin.py` changes since `b4d7c8e` (089 and 083), and 089's build
    review's F3 (main's own CPython noise before 083);
  - the builder's evidence in the worktree's `build/091/`.
- **How I ran things:**
  - the full judge, `uv run pytest -n 3`, in the worktree at `fdab891` (clean), against its private
    set (`python.wasm` `ab78e893…`, `shasum -c` OK, no file with nlink above 1). It started at
    21:04:48, once `build/lane.lock` was gone, and ended 21:15:40;
  - `ruff check` and `ruff format --check` on `src/` and `tests/` in the worktree;
  - the new rows and six mutants in a scratch export of `fdab891` (`git archive`, run with the
    worktree's venv, `--no-sync`). No project file, branch or worktree was changed, and the main
    tree's `build/` was not touched.

Labels: **EXECUTED** (I ran it), **READ**, **INFERRED** (reasoned, not run).

## Short version

- **It is a reasoned narrowing, not a weakening** (rule 4). The 84 cases still run on every judge
  and still count in the group's passes, classes and digest. Only their fuel leaves the ratchet. It
  leaves by a reviewed judge change with the owner's approval, never by a wider tolerance.
- **The numbers reproduce** (EXECUTED). My full judge gives exactly the builder's verdicts:
  523/623 pass · 77 gap · 23 blocked · 0 fail; lost 0 · gained 0 · grew 0; the judge changed in
  seven files. numpy-core is 155,837,134,978 (the builder's 155,837,134,689). Its fact is
  59,054,443,419. Passes are 9,519, the digest is `df21e78e7032`, and the counts are unchanged.
- **Combining the two sessions is exact, sameness is right, and the flags are right** (READ). A fall
  in fuel is accepted by itself: `--accept` and `--accept-judge` are enough.
- **091 rebases cleanly** onto main `8c07ad4`, and onto 078's branch too. On the merged tree the
  fact's `judge/<id>.json` is written before 089's seal.
- **One thing to fix before landing (F1).** The code that wires the two sessions together,
  `Session.group`, has no unit row. Three mutants of it pass both the unit tier and a clean full
  judge. One of them records the group's fuel as the fact.

**Verdict: lands once F1 is fixed.** F2 and F3 are Low. The rest are notes.

## 1. Is it a narrowing with a reason, and is the list closed? (READ)

- **What leaves the ratchet.** One number leaves: the fuel of the 84 cases. Their outcomes stay.
  - `passes` adds both sessions' passes. It is still `COUNTS_UP`, so a fall is `fewer`, which is red.
  - The classes read the members of both sessions.
  - The digest is taken over every passed id.
- **The bound that is left.** The fact has its 140 G cap, which is a finding when reached. It has
  a 10% review band and the cap's keeper, both written into the progress README and "For the lane".
- **Can a second entry slip in?** No.
  - `numpy.toml` is under `tests/`, and `JUDGE_PATHS` holds `tests`. So any new entry, in any
    package, changes the judge hash, and the lane must give `--accept-judge`.
  - `test_the_judges_one_fuel_fact_is_string_comparisons_in_numpy_core` pins the whole list
    across every config (package, id, group, node). A second entry is an edit in two files.
  - `fact_errors` asks for a reason and an evidence file under `context/reviews`, `research` or
    `specifications`. It refuses any entry in a regrtest suite.
  - Raising the cap is also a judge change. `caps()` counts the cap in the 3 T family budget.
- **The owner approved it** (P3). It is the shape rule 4 asks for: its own change, with a reason
  and an accept-judge line.

## 2. Is combining the two sessions exact? (READ, EXECUTED)

- **Passes and digest.** `combine` takes `passed` from every session's stream, in the same way
  `judge_group` does (`o == "passed"`). `passed_digest` sorts its input, so the digest equals the
  one-session digest whenever the passed set is the same.
- **Counts.** A `Counter` added over the sessions, then sorted. This is what `judge_group` gives
  for a single stream.
- **Members.** Each class's members are unioned as sets and then sorted, as `judge_group` does
  (`sorted(set(v))`). Every class key is present, because each part has every class of the group.
- **Findings.** The fact session's findings carry the prefix "fuel fact <id>: ". `fact_findings`
  is added after them.
- **`finished`.** True only if every session finished.
- **The real run** (EXECUTED, my record). Passes 9,519, digest `df21e78e7032`, counts error 3 ·
  failed 40 · passed 9,519 · skipped 439 · xfailed 12. These equal main's harness on the same set
  (`build/091/main-numpy-core.json`). The five numpy-core class checks stay gaps with the same
  finding counts and digests as the builder's (28, 3, 8, 3 and 1).
- **The selector.** The group passes `--deselect=<node>[`, relative to rootdir, just as traps'
  deselects are. The fact runs the node itself, under the group's marker and `cfg.args`. `owns()`
  is true only for `node[…]`.

## 3. sameness, the ratchet, the accept text, the seal (READ, EXECUTED)

- **sameness.py.** `FIELDS` no longer holds `facts`.
  - `_facts` splits a check's facts into two parts: the facts without `fuel_facts`, compared
    exactly, and the `fuel_facts` dict.
  - Each value of that dict is compared with `fuel_differs`, the 1e-4 tolerance.
  - A key that is in one record and not in the other is a difference.
  - `bytes` and `passes` stay exact, and `fuel` stays within the tolerance.
  - The unit row covers a value within the tolerance, one beyond it, and a renamed key together
    with a changed exact fact.
- **The ratchet.**
  - `compare` adds a fuel row to `growth` only when `value > old * (1 + FUEL_TOLERANCE)`
    (`scoreboard.py`). A fall goes in no list that turns a run red.
  - `accept` keeps `min(old, value)` for fuel when there is no growth reason and the engine is the
    same (49.0.0 both).
  - `accepted.json` keeps only `status`, `commit`, `artifact` and `metrics`. So `fuel_facts` is
    never ratcheted.
  - **No flag beyond `--accept` and `--accept-judge`.** Passes stay 9,519, so no
    `--accept-fewer-passes` is needed. No node is gained or lost.
- **The `--accept-judge` text.**
  - It is exact against the diff. It names the seven files, the one check edit (the
    `fact("fuel_facts", …)` record, in the `elif` after the regrtest facts), the two docstrings, and
    the one allowance edit.
  - "No assertion changed" is true.
  - It is paste-safe: it holds no `"`, `$`, `` ` ``, `!` or `\`, and `[[fuel_fact]]` is literal
    inside double quotes in zsh. This avoids 078's D1.
- **089's seal** (READ, `git merge-tree`).
  - `main` (`8c07ad4`) and `fdab891` merge with no conflict (tree `d4ac65e`).
  - On the merged tree, `_prepare` writes `judge/string-comparisons.json` inside the per-package
    loop. `litter.seal(self.root)` runs after every package's `_prepare`.
  - The fact's session writes nothing into the stage. Its run root is removed by 089's
    `litter.remove`, like any other run's.
  - 078's branch also merges with no conflict (`651741b`).
- **Elsewhere.** `gather.py` reads only `passed_digest` and `trap` from `facts`.
  `scoreboard.py` reads only `trap`. Names are unique across every package's groups, traps and
  facts (the `names` set covers all of `rule_errors`). So `judge/<id>.json` cannot collide.

## 4. The full judge (EXECUTED)

- `uv run pytest -n 3` at `fdab891`, clean, on the private set: **523/623 pass · 77 gap · 23
  blocked · 0 fail** (unit suite 1599/1607, 8 skipped); **ratchet vs b91e0eaa4e: lost 0 · absent 0
  · unrun 0 · unrun locally 21 · gained 0 · grew 0 · judge changed:**
  `tests/checks/test_v1_3_upstream_suites.py`, `tests/harness/sameness.py`,
  `tests/harness/scoreboard.py` and 4 more. 2122 passed, 31 skipped, 77 xfailed, 10 min 51 s.
- The scoreboard's not-machine-checked line ends "· a fuel fact's fuel below its cap (spec 091)".
- **Fuel against `accepted.json` at `b4d7c8e`.** 164 rows compare. **One** is past 1e-4:
  numpy-core, 203,355,507,505 → 155,837,134,978 (−23.37%), falling.
- **numpy-core:**

  | | builder (`build/091/latest-full.json`) | reviewer |
  |---|---|---|
  | `fuel` | 155,837,134,689 | 155,837,134,978 |
  | `fuel_facts.string-comparisons` | 59,054,444,490 | 59,054,443,419 |
  | `passes` | 9,519 | 9,519 |
  | `passed_digest` | `df21e78e7032` | `df21e78e7032` |

  The fact's run-to-run spread is 1,071 instructions (1.8e-8).
- **The cap.** 140 G is 2.37 times the fact. Criterion 5's 073 and 086 facts (63.5 G, 64.5 G) are
  both under half the cap (70 G).
- **sameness.py, builder's record against mine:** one difference,
  `test_upstream_suite[cpython-a]: fuel 268593339272 != 268560032199` (1.24e-4). This is not
  091's. 091 changes no regrtest path (`_load_regrtest` reads an empty `fuel_facts`). Both values
  are within 1e-4 of the accepted 268,583,771,926 (builder +3.6e-5, mine −8.8e-5). It is the
  base's own noise before 083, as 089's build review describes it in F3 (`cpython-c` +1.21e-4
  there). See F2.
- `ruff check` and `ruff format --check` on `src/` and `tests/`: green.
- My record: `…/scratchpad/091-buildreview/reviewer-latest.json`.

## 5. The builder's other claims (READ, EXECUTED)

- **Criteria 1 and 2.**
  - `first-fail.txt` is one run on main's harness that lists each of the twenty rows as FAILED,
    with the other 98 passing. The rows build their entries inside the row and share no state, so
    one run that names each failure is as good as twenty single runs.
  - The new rows pass in my scratch export: 20 passed.
  - `mutants.txt` shows the four mutants of criterion 2, each caught.
- **Criterion 4.** Confirmed against `main-numpy-core.json` and my run (section 4).
  - `branch-main-set.json` was recorded on a dirty tree at `1b58feb` (`meta.dirty` true): the
    build was not yet committed.
  - The clean full runs on `4002467` and `fdab891` reproduce it to within 1,071 instructions on
    the fact and 884 on the group (see N2).
- **Criterion 5.** From the JSON files: r_own +0.0245% and r_fact +7.559% on 073's set, ratio
  0.0032. On 086's set: +0.0793% and +9.18%. The claim holds against the line written in F1:
  |r_own| ≤ 0.5% and ≤ ¼·|r_fact|. Passes, digest and counts are equal on all three sets.
- **The pre-build review's F1 to F6:**
  - **F1**, the control pair and its line: fixed in criterion 5 and carried out.
  - **F2**, the residual stays red: fixed in "What 091 does not fix", Decision 10 and "For the
    lane". The landing notes measure it (+38 M and +124 M) and tell the owner.
  - **F3**, the accept text: fixed (section 3).
  - **F4**, the hidden slowdown:
    - answered. The Principle states the risk.
    - Option (a), the 10% review band, is in Decision 4, the progress README and "For the lane".
    - The 140 G cap is kept, with a reason that holds. 100 G would trip the keeper at once (the
      fact is about 59 G, above 50 G). It would also fall under 050's own 1.5× floor near 70 G.
    - I agree with keeping 140 G.
  - **F5**, the cap's keeper: in Decision 4, "For the lane" and the README.
  - **F6**, the random state: in criterion 4. The digest and counts are equal, so it did not apply.
  - **N1 to N5** are answered as the Disposition says. N2's exact overlap rule has its sibling row.

## Findings

### F1. `Session.group`'s wiring and the fact's spec file have no unit row; three mutants survive even a clean full judge. Fix before landing (EXECUTED)

- **What the twenty rows cover.** They test the parts: `group_spec`, `fact_spec`, `owns`,
  `fact_findings`, `combine`, the rules and sameness. No row tests how `Session.group` puts them
  together. No row tests that `_prepare` writes `judge/<id>.json` (the staging rows assert only
  `judge/g.json`).
- **The mutants.** Six mutants of that code, run on `test_upstream.py`, `test_several_cores.py`
  and `test_regrtest.py`: every one passes (185 passed each).

  | mutant | unit tier | full judge |
  |---|---|---|
  | M1 `combine(parts, [])`: `fact_findings` dropped | passes | passes (no overlap today) |
  | M2 `facts[f.id] = run.fuel`: the fact records the group's fuel | passes | **passes** |
  | M3 group `fuel` includes the fact | passes | red: growth |
  | M4 the fact's session left out of `combine` | passes | red: passes fewer by 84 |
  | M5 the fact's `judge/<id>.json` not written | passes | red: a finding (INFERRED) |
  | M6 the fact's findings lose their prefix | passes | passes (no finding today) |

- **Why it matters.**
  - The fact's value is the one number this specification produces, and M2 corrupts it with
    nothing to catch it. Sameness compares two runs of one commit, so both runs agree on the wrong
    value.
  - M1 removes the "exactly once" guard. That guard is what keeps the 84 cases from being counted
    twice if the deselect ever stops matching.
  - Rule 3 asks for the check before the code. The spec's Design names `Session.group`, but
    criterion 1's rows stop at its parts.
- **Fix:** one unit row. Use `_scaffold` with a `numpy` config that has a fact, and monkeypatch
  `Session._run` to return canned `(Stream, GuestRun)` pairs by name: the group's session with fuel
  A, and the fact's with fuel B. Then assert:
  - `GroupRun.fuel == A` and `GroupRun.fuel_facts == {id: B}`;
  - the combined passes;
  - a failure in the fact's stream appears as `"fuel fact <id>: unexpected …"`;
  - a fact case placed in the group's stream gives "also ran in the group";
  - `judge/<id>.json` is in the stage.

  Show it failing on M1, M2, M5 and M6. It touches only `tests/unit/test_upstream.py`, already
  one of the seven files, so the accept text does not change. The unit tier and the lane's judge
  are enough; no new full run is needed for this.

### F2. "For the lane" is written for `b4d7c8e`; on the rebased base, its expected figure and the reading of sameness both change. Low (READ, EXECUTED)

- **The expected figure.** Main's accepted numpy-core fuel is now 203,331,725,349 (the 089 and 083
  batch), not 203,355,507,505. 078 also lands before 091. The fall should be quoted from the base
  the lane accepts on. Decision 10 already says the rebase re-measures; "For the lane" should say
  the same.
- **The sameness reading.** The builder's record and mine are both on `b4d7c8e`, before 083. Rule
  6a compares a reviewer's record with the lane's. Against a run on the rebased commit, that will
  show:
  - every row that 089, 083 and 078 moved;
  - the pre-083 CPython noise. I hit it: `cpython-a` is 1.24e-4 apart between the builder's record
    and mine, and both are within 1e-4 of accepted.
- **Fix:** one sentence in "For the lane". Either the lane reads differences confined to rows the
  base moved (as it did for the 089 and 083 batch), or it asks for a reviewer's fast tier plus
  `test_upstream_suite[numpy-core]` on the rebased commit. And `cpython-*` noise on the old base is
  089's F3, not 091's.

### F3. The overlap rule matches `not_selected` files exactly, not by folder. Low (READ)

- `fact_errors` tests `f.file in taken`. A `not_selected` entry is a path that `group_spec` turns
  into `--ignore`, and it could name a folder.
- If one ever named a folder that holds the fact's file, the group would ignore the file. The
  fact's session, which has no `--ignore`, would still run the cases and count them in the passes.
- Today every `not_selected` entry in `numpy.toml` is a file, so nothing is wrong now.
- **Fix** (optional, or answer in writing): match a folder entry as a prefix too, e.g.
  `any(f.file == x or f.file.startswith(x.rstrip("/") + "/") for x in taken)`, with one more case
  in the overlap row.

### N1. The slip under `build/lane.lock` affected nothing recorded. Note (READ, INFERRED)

- **When.** The narrowed run (`branch-main-set.*`, 68.7 s, one pytest process) started near 20:06.
  The lane's batch judge of 089 and 083 ran then: its reviews were committed at 20:06:32, and it
  accepted at 20:17:25.
- **No shared state.** The worktree's run used only the worktree's own folders:
  - `build/artifacts`, a private copy at nlink 1;
  - `build/harness`, the stages;
  - `build/cwasm-cache`;
  - `build/progress`.

  `paths.BUILD` is `REPO / "build"`, per checkout. Nothing in the main tree was read or written.
- **No recorded effect.** The only recorded measure is fuel. It counts instructions and does not
  depend on host load, beyond the clock noise the tolerance exists for.
  - The lane's record for that batch was sameness-clean against both reviewers (`45b917c`'s
    message).
  - The narrowed run's own numbers reproduce in two later clean runs, within 1,071 instructions.
- **What remains.** It breached P8's rule (no other judge while the lane accepts). It cost
  nothing, and it is recorded honestly. Since rule 3a now allows a single node id under the lock,
  a one-check run like this one is arguably allowed today.

### N2. Evidence details. Note

- `branch-main-set.json` comes from an uncommitted build. `latest-full.json` (on `4002467`) and my
  run (on `fdab891`) are the committed evidence, and they agree.
- The group's own fuel varies by a few hundred to 884 instructions run to run, against a
  tolerance of 15.6 M.

### N3. Wall time. Note

My full judge took 10 min 51 s at `-n 3`; the builder's took 20 min 18 s, also at `-n 3`, with
other load on the machine. The second session costs about 11.5 G of start and collection (the
landing notes) on numpy-core's worker. Nothing here is counted by a check.

## Verdict

**Lands once F1 is fixed:** one unit row for `Session.group`'s wiring and the fact's spec file,
shown failing on M1, M2, M5 and M6. F2 is a sentence in "For the lane", and F3 is optional or
answered in writing. Both are Low. The notes need nothing.

## One line

The narrowing is exact and reasoned, and my judge reproduces the builder's verdicts (523/623, lost
0, grew 0, numpy-core 203.36 G → 155.84 G with passes, digest and counts unchanged). What is
missing is one unit row for the code that joins the two sessions.
