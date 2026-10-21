# Review of 112 — Strings speak for themselves (before the build)

- **Date:** 2026-10-21
- **Reviewer:** a fresh agent, started by the lane; wrote none of 112 and reviewed none of it
- **Reviewed:** the specification as drafted, `3496fadb` on `spec/112-strings-speak-for-themselves`
  (on main `d8fc73f`)
- **Run:** none. The reviewed commit changes only `context/`; there is no code to judge yet. The
  builder's run is criterion 9's, and the build review reads it.
- **Box:** 45 minutes (build-class by the letter); finished inside it.
- **Re-ran:** `build/lane.lock` was present, so single node ids only.
  - `uv run pytest -q tests/checks/test_rules.py::test_code_outside_src_names_no_context_document
    tests/checks/test_rules.py::test_src_names_no_context_document` → 2 passed (EXECUTED): 109's
    and 107's checks are green on the base, as criterion 3 needs.
  - An independent scanner of my own (scratchpad, not committed), written from Decisions 2 to 4
    before I opened the drafter's `measure2.py`: **92** distinct `(line, rule, phrase)` hits in
    scope and **108** in the judge's allowance files on `d8fc73f`. Its hit set is identical to the
    drafter's `hits-proposed.tsv` (`diff` empty) (EXECUTED). The same scanner on wave 10's tip
    (`e64508e4`, through `git archive`) finds the same 92 phrases per file (EXECUTED), so the
    wave's rebase moves no hit.
  - A wider read (bare three-digit numbers, `Decision N`, `criterion N`, `review NNN`,
    `finding N`, `AGENTS.md`, `decisions.md`, `roadmap`, `research/`) over the same strings,
    plus `recipes/` and `pyproject.toml` (EXECUTED). Its finds are findings 2 to 4.
  - `uv run pytest --markers` → the `goal` marker is listed twice, once with "(spec 002)" from
    `pyproject.toml` and once from `plugin.py` (EXECUTED; finding 1).

## Acceptance criteria against evidence

1. Seen failing first — checkable: a count in `build/112/seen-failing.txt`; the 75 is the
   prototype's, and my scanner agrees on the 92 it comes from (EXECUTED).
2. Measured on the base — checkable; on wave 10's tip the population is unchanged (EXECUTED).
   It only re-runs the forms. A citation the forms miss is not "a hit not in the table" (findings
   2 and 3).
3. Passes, fourteen rows, 109's and 107's green — checkable. Both are green on the base
   (EXECUTED). The count moves to fifteen if finding 2 is taken as written.
4. Thirteen unit rows — checkable: 9 + 1 + 1 + 1 + 1 by the Design (READ).
5. Strings only — checkable but wrong as written: `tests/unit/test_scan.py` gains thirteen rows,
   so its `ast` changes (finding 5).
6. No protected file changes — checkable; the list covers rule 4's files and the guest's sources
   (READ).
7. Kind B by node id — checkable. I checked every test that matches a reworded text: an exact
   copy (`test_pins.py:86`, `:88`, `test_landing_lane.py:395`, `:676`, `test_build_progress.py:1086`,
   `test_patches.py:267`, `test_scan.py:2102`) or a substring that survives the cut
   (`test_history.py:301`, `:347`, `:504`, `test_patches.py:277`, `test_host_litter.py:100`,
   `test_guest.py:301`, `test_scoreboard.py:391`) (READ, grep). Only `test_several_cores.py:434`
   changes what it anchors on (finding 6).
8. Rule (b) traced — checkable from the landing notes.
9. The artifact set — checkable on CI. The INFERRED claim is stronger than the draft says:
   `scripts/steps/60_link.sh:234` runs `llvm-strip --strip-debug` on `python.wasm`, so even a moved
   line could not reach its bytes. A C comment compiles to nothing, and the comment stays one line
   (READ). `refuse-python` runs only when a build step calls an unpinned Python (READ). No check
   reads a workflow step's name except `workflow_step_script`'s three callers. They name
   `CHECK_STEP`, "The build job handed on an artifact id" and the gather's guard step, none of the
   eight. `needs:` and `if:` use job and step ids, which do not change (EXECUTED, grep). See
   finding 7 for which run it is compared with.
10. The fast tier — checkable; see finding 7 for `test_manifest_recipes_match_the_tree`.
11. Ruff — checkable.

**The owner's answer to question 111** ("Before 0.1.0": citing string literals outside `src/` are
reworded; the allowance files' comments and the guest's own sources wait for the closer): met for
every file 109 reads. It is not met for `pyproject.toml` (finding 1). `recipes/` is not named
either way (finding 4).

**Structure (4a):** the change is one scanner block, one check, its rows and string edits. It adds
no lifecycle flag, module-level mutable, seam or platform branch, and nothing in `src/`. It is not
structural, and the Kind line rightly does not say so.

## Findings, most severe first

1. **Medium — the `goal` marker's help keeps "(spec 002)" in `pyproject.toml`**
   (`pyproject.toml:101`). The specification rewords the marker's copy in `plugin.py:204`. The
   same marker is also registered in `pyproject.toml`, and that file is outside the files read
   (109's list plus `src/`).
   Failure: after the build, `uv run pytest --markers` still prints
   `@pytest.mark.goal(area): a v1 progress check (spec 002); area is v1.1 to v1.5 or rules`
   (EXECUTED today: both lines print). So the Intent's "every string a person reads … gives its
   reason in words" is false on the first screen a user asks for.
   Fix text: Decision 3's files add `pyproject.toml` (its non-comment lines, as for any TOML).
   Decision 7's table gains the row "`pyproject.toml:101`, the `goal` marker | `a v1 progress
   check (spec 002); area is …` | `a v1 progress check; area is v1.1 to v1.5 or rules`".
   Criterion 5's non-Python lines become "the eight step names, the one `echo` and the one marker
   line". The file is not in `MANIFEST`, `SHA256SUMS` or the wheel, so the artifact claims do not
   change. It is judged (the xdist refusal's docstring says so), so the `--accept-judge` reason
   names it.

2. **Medium — a citation in a guest program whose check records fuel is missed by the forms**
   (`tests/checks/test_v1_3_data_stack.py:528`, inside `CTYPES`). The line reads `# Introspection
   with numpy loaded (review 033, finding 1): …`. Neither `review` followed by a specification's
   number nor `finding N` is among Decision 2's forms. `CTYPES` runs in the guest through the
   `guest` fixture, which records the run's fuel as the check's metric (`tests/checks/conftest.py:96`;
   `test_ctypes_stand_in_names_what_packages_import[plain]` and `[snapshot]`) (READ).
   Failure, one of two ways. (a) The build follows the table: the check passes, but a string still
   cites a review, against the owner's answer and the Intent. (b) The builder finds it in the read
   and rewords it: the guest's input bytes change, so both rows' fuel moves (109's `GUEST_INPUT`
   reason records that a 25-byte docstring change moved a guest job's fuel past the tolerance).
   That is a fuel row the claim list says cannot move: "Rows that grow: none".
   Fix text: Decision 2's `review` rule adds the form "a review followed by a specification's
   number, `review 033`" (`\breviews?\s+0\d{2}\b`, case-insensitive). Decision 5 adds one row,
   `("tests/checks/test_v1_3_data_stack.py", "review 033", GUEST_FUEL)`. Its reason: "a guest
   program in a check that records fuel: its bytes are the guest's input, so it changes with the
   closer that re-measures the guest's fuel". The roadmap's closer line names it, and the row count
   becomes fifteen. The population table gets a fifth kind, "E. kept for the closer: 1". The
   "Decision 2" sentence about the four extra finds adds this one, "found by the review". Do not
   reword it in 112.

3. **Low — a test id cites a specification by its bare number** (`tests/unit/test_gather.py:420`,
   the case id `the newest line with no set (from before 085)`, used as a pytest id at `:485`). A
   person reads it in pytest's output, and none of the forms matches a bare `085`. Unit ids are not
   progress rows (claims count units), so rewording moves no pass.
   Fix text: add it to Decision 7's table "found by the review": `(from before 085)` becomes
   `(from before a history line named its set)`.

4. **Low — `recipes/` is not named in or out** (`recipes/npy_fenv_flags.h:31`). This header
   holds `#error "… remove recipes/npy_fenv_flags.h (spec 099)"`, a message a builder reads. The
   stand-in modules' docstrings under `recipes/` cite specifications too. Neither 109 nor 112 reads
   `recipes/`. The owner's exception, "the guest's own sources", plausibly covers them: they are
   compiled or frozen into the guest. But the specification never says so, and its Intent claims
   every string outside the allowance files.
   Fix text: Scope's "Out" adds "`recipes/` (the guest's own sources, compiled or frozen into the
   guest; the reserved closer)". The Intent's first sentence adds "and the guest's sources under
   `recipes/`" to its exception. The roadmap's closer line names `recipes/`.

5. **Low — criterion 5 cannot pass as written** (criterion 5). It excludes only the check's file
   and the scanner's. `tests/unit/test_scan.py` gains thirteen unit rows, so its `ast` with strings
   blanked differs.
   Fix text: "for every Python file changed but `tests/harness/scan.py`,
   `tests/checks/test_rules.py` and `tests/unit/test_scan.py`, …; in those three, every top-level
   statement present on the base has the same blanked `ast`, apart from `SET_SUMS_STEP`'s string".

6. **Low — `test_several_cores.py:434` changes its anchor, not only its text** (Decision 7, the
   `REFUSAL` row). Today `"spec 052"` singles out the xdist refusal's line. The proposed
   `"refused:"` is a prefix any refusal may carry (`plugin.py:295`'s `refused: --shard … with -n`
   is one). So the assertion becomes looser, against Decision 6(c) ("in the same way it matched the
   old").
   Fix text: the test matches the refusal's whole new shape. Build a regex from `plugin.REFUSAL`
   with each `{}` as `.+`, and match it against the line that names the option, so it still
   proves the line is `REFUSAL`'s.

7. **Low — the comparison runs in criteria 9 and 10 are loosely named** (criteria 9, 10).
   Criterion 9 compares with "main's last dry run on the base". `d8fc73f` is context-only, so its
   last dry run may be on an earlier commit, and after wave 10 (045 adds statsmodels) on another
   set entirely. Criterion 10's "exactly the baseline's nodes" holds only if
   `tests/checks/test_v1_1_artifact_set.py::test_manifest_recipes_match_the_tree` already fails on
   the frozen set used ("stale artifact: … changed since the build"). Against a set built on the
   base, that check passes on the base and fails on the built commit, by design (INFERRED from
   `paths.manifest_recipe_errors`).
   Fix text: criterion 9 reads "… the SHA-256 of a release workflow run on the base, or on the
   latest commit whose `recipes/`, `scripts/` (but the two files) and `downloads/SHA256SUMS` are the
   base's; its run id in the landing notes". Criterion 10 adds "against a frozen set built on the
   base, `test_manifest_recipes_match_the_tree` is the one expected difference, its message naming
   exactly the two files".

8. **Note — the skips need exact edges** (Decision 3). They are not a hole today. The only
   `*_ALLOWED` tuples are three in `tests/checks/test_rules.py`. The only citing strings given to a
   `re` call are the rule tables' own patterns (both EXECUTED). Three edges keep it that way.
   (a) A "docstring" means exactly 109's set: the first statement of a module, class or function,
   and a plain constant. A bare string statement elsewhere, or an f-string in that position, is not
   read by 109, so 112 must read it. (b) The `re` skip covers the pattern argument of the functions
   that take a pattern (`compile`, `search`, `match`, `fullmatch`, `findall`, `finditer`, `sub`,
   `subn`, `split`). It does not cover `re.escape`, whose argument is text: a test may escape a
   message to match it. (c) The `*_ALLOWED` skip covers only the phrase column. The reasons stay
   named constants, read like any string, so a reason cannot hide a citation. A negative unit row
   for each of these three edges costs little.

9. **Note — line attribution across implicit concatenation** (Decision 3, "the line being where
   the phrase starts"). `ast` joins `"a "` and `"spec 052"` into one constant at the first token's
   line. The line of a phrase in a later token needs `tokenize`'s string tokens (and 3.12's
   f-string tokens) mapped back. The unit row for the reported line should include a phrase on the
   second line of an implicitly concatenated literal.

10. **Note — bare labels left for the closer.** By Decision 2, bare forms are not refused, and these
    are not: `WRITE_PARITY`'s guest-side comment "Decision 12's deliberate differences, asserted as
    its table says" (`test_v1_4_embedding.py:4212`, a guest program, no specification beside it),
    and the parametrize ids `steer052` and `spoof052` (`test_landing_lane.py:638`). They are
    consistent with the rule. The closer may want them.

## Constitution checks

- §4.1 (few, recorded patches): no patch and no recipe step changes. Two `scripts/` files change
  one string each, recorded by `MANIFEST`'s recipe lines (READ).
- §4 pins: no input changes. `SHA256SUMS` moves only through `MANIFEST` (READ).
- AGENTS.md rule 4 (the judge not weakened): no golden, expected file, allowance file or progress
  file changes (criterion 6). The new check only adds refusals, and its allowance is fourteen named
  rows, each used, a stale one failing. The one place a test loosens is finding 6.
- §5.6: a pre-build review is required (the build recipe's `scripts/`), and this is it.
- §7 never-do list: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. —
2. —
3. —
4. —
5. —
6. —
7. —

## Verdict

The specification can be built once findings 1 and 2 are written into it: `pyproject.toml`'s
marker read and reworded, and `CTYPES`'s "review 033" caught by a form and kept by a fuel-reasoned
row. The Lows are answered by their fix text.
