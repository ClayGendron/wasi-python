# 070 — The judge's small follow-ups

- **Status:** built 2026-10-18; awaiting its build review. Drafted and built the same day on
  `spec/070-the-judges-small-follow-ups` from main `4a94c14` (the Landing notes). It changes
  neither the guest's imports nor its exports, the artifact set nor the build recipe, so §5.6
  asks no review before build. A different agent reviews the build.
- **Date:** 2026-10-18
- **Owner:** Clay Gendron
- **Kind:** a judge change and one README clause; **parallel-safe**, not build-class (§5.7).
  It edits `tests/harness/scan.py` (rule 16 of `release_binding_errors`) and
  `tests/harness/history.py` (`_volume_errors`), adds unit cases to `tests/unit/test_scan.py`,
  `tests/unit/test_history.py` and `tests/unit/test_tools.py`, adds one v1.4 check to
  `tests/checks/test_v1_4_embedding.py`, and adds one clause to `README.md` and one entry to
  `CHANGELOG.md`. It touches no `src/`, `scripts/`, `recipes/`, `downloads/SHA256SUMS` or
  workflow. No existing check, golden output, gap or allowance is edited. Every judging file it
  edits changes the judge hash: **the lane accepts it with `--accept-judge`.**
- **Depends on:** 057, 060 and 062, all landed. It closes notes their reviews left open.
- **Research it stands on:** the three reviews, each read in full:
  - `../reviews/057-the-release-ties-what-it-signs-to-what-it-built-2026-10-18.md`, the
    Confirmation's "What rule 16 still lets through";
  - `../reviews/062-the-progress-history-stays-small-2026-10-18.md`, F1 and F2;
  - `../reviews/060-a-per-run-budget-of-request-bytes-2026-10-18.md`, N1 to N3.

## Intent

Three landed specs passed their build reviews with small notes left open. Each note is a place
where the judge is a little weaker than its specification says, or where the README is a little
less exact than the code. This spec closes the ones that are small, and says why it leaves one
out.

After it:
- rule 16 reads a download's `path:` as a path, not as text;
- the history's volume budget is held at its exact byte, on both sides, by a test;
- a history volume that holds a carriage return is reported, wherever it is;
- each kind of C slot where `tool()`'s keyword walk stops is pinned by a test;
- the README says what the guest sees when its discovery frame is refused, and a check holds it.

## Decisions

1. **Rule 16 normalises the path** (057's Confirmation). A download's `path:` loses a leading
   `${{ github.workspace }}/` (any spacing inside the braces), then goes through
   `posixpath.normpath`, before it is compared with `release-assets`. *Reason:* in `same-bytes`,
   `./release-assets`, `rebuilds/../release-assets` and `${{ github.workspace }}/release-assets`
   name the same folder as the plain spelling, which rule 16 already refuses. The fix is the one
   the reviewer named. Other rules that compare `path:` are not changed: in a holder job, rule
   16's one-download clause already catches any spelling, and a non-plain spelling there fails
   rule 7 rather than passing.
2. **The roll's boundary is tested on both sides** (062's F1). One volume is padded so that the
   next line ends at exactly `BUDGET` bytes: `target` keeps it in that volume, and `errors` is
   clean. One byte more, and `target` starts a new volume, and `errors` is clean. Each line put
   on the wrong side by hand is reported: "begun early", and "past the volume budget". *Reason:*
   Decision 4 of 062 says "at most `BUDGET`"; until now only its interior was tested, and a `<`
   for `<=` in `target` passed every test (the review's S8).
3. **A volume that holds a CR is an error** (062's F2). `_volume_errors` adds "`<name>` holds a
   carriage return" when a volume's bytes contain `\r`. *Reason:* lines end in LF alone (062,
   Decision 4), and `json.dumps` writes a CR inside a value as `\r`, two bytes, so a raw CR byte
   is never part of a good line. Before, a CR was reported only where a later line's `prev`
   failed to hash the line that held it; a CR on the newest line, or in a history written with CR
   from its start, passed. Main's volumes hold no CR (EXECUTED: `tr -cd '\r' | wc -c` gives 0
   for both).
4. **Each kind of `_C_SLOTS` is pinned by depth** (060's N3). The walk stops at a C `__call__`
   in the hop that meets it, the same hop that stops at a function. With one kind left out, the
   walk takes one hop more and then stops anyway, so the result is the same, which is why the
   review's stand-in survived. What the extra hop changes is the depth limit. A chain of 63
   `__wrapped__` links that ends at a function is the deepest the walk reads (64 hops). A chain
   of 64 links is refused. So the test ends a 63-link chain at an object of each kind and asserts
   that it is read. Without that kind in `_C_SLOTS`, it is refused. The five ends are: a class
   (`type.__call__`, a wrapper descriptor); `__call__ = (1).__add__` (a method-wrapper);
   `__call__ = str.upper` (a method descriptor); `__call__ = len` (a builtin); and
   `__call__ = staticmethod(dict.__dict__["fromkeys"])` (a class-method descriptor). *Reason:* to
   pin them rather than narrow the list. Narrowing would change `src/` and move the depth limit
   by one hop for these callables. Pinning keeps the code as it is, and it makes the comment's
   claim ("the walk stops there") something the judge checks.
5. **The README says a refused discovery frame is an `ImportError`** (060's N2). **Limits**
   gains one sentence: if the discovery frame itself is refused (`max_tool_calls=0`, or a
   request budget too small for it), `from host import tools` raises `ImportError`. A v1.4
   check holds it under both limits. *Reason:* the README said "Past either, the guest gets
   `ToolBudgetExceeded` and runs on". That is not true of the first frame, and no check held
   what is true.
6. **N1 is left out** (060's N1: an oversized tool list is built whole on every `list` frame,
   only to be measured and refused). *Reason:* the fix is in `src/wasi_python/tools.py`, the
   host's answer path. It would turn this judge change into a product change, with its own
   release note. Its only check would read an internal count of calls. Its cost is already
   bounded by `max_tool_calls`, as the README says, and the review says it "can wait". It
   belongs with the next change that touches `_answer` (spec 055 is the nearest).

## Scope

In: rule 16's path, the boundary and CR cases with the CR rule, the `_C_SLOTS` pin, the README
clause and its check, one CHANGELOG entry. Out: N1 (Decision 6); rule 7's own path comparison
(Decision 1); any change to `src/`, the workflow, the history's bytes or `BUDGET`.

## Acceptance criteria

Each check was written before the code it holds, and each fails against the stand-in named
(EXECUTED, `build/reviews-evidence/070-build/standins.py` and `standins.out` in the main tree;
each stand-in applied alone to a scratch copy and run by node id).

1. `test_rule_16_reads_the_download_path_as_a_path` (unit, 5 spellings: `./release-assets`,
   `rebuilds/../release-assets`, `${{ github.workspace }}/release-assets`,
   `${{github.workspace}}/./release-assets/`, `./release-assets/wheel`) each name rule 16 alone.
   `test_rule_16_lets_another_spelling_of_a_rebuild_folder_through` (2 spellings) is clean, and
   `test_the_release_workflow_passes_every_release_scan` still passes on the real workflow.
   Stand-ins: main's text compare (S1, 5 failed); normpath without dropping the workspace prefix
   (S2, the 2 workspace spellings failed).
2. `test_a_line_that_ends_exactly_at_the_budget_stays_in_the_newest_volume`,
   `test_a_line_one_byte_past_the_budget_starts_a_volume` and
   `test_the_intact_check_holds_the_budget_at_its_exact_byte` (unit) pass. Stand-ins: `target`
   with `<` for `<=` (S3, the 062 review's S8); `errors` with `offset >= BUDGET` (S4); the
   begun-early test with `<` (S5). Each fails one of them.
3. `test_a_volume_that_holds_a_carriage_return` (unit): the newest line ending in CR LF gives
   exactly `["history-…jsonl holds a carriage return"]`. Stand-in: no CR rule, which is main
   (S6, `[] == [...]`).
4. `test_the_bound_keyword_walk_stops_at_each_c_slot` (unit, 5 kinds) passes. Stand-ins: each
   of the four kinds the review found unpinned, removed alone (S7 to S10, each fails its own
   kind); the review's stand-in (q), the list narrowed to `WrapperDescriptorType` (S11, 4
   failed).
5. `test_a_refused_discovery_frame_is_an_import_error[calls]` and `[bytes]` (v1.4, guest):
   `ImportError the host refused the tool list (budget_exceeded): …` is printed, and the record's
   outcomes are exactly `[(None, "budget_exceeded")]`. Stand-in: `admit` exempts the first frame
   from both limits (S12, 2 failed: the import succeeds).
6. The README's **Limits** has Decision 5's sentence; the CHANGELOG has one entry under
   `0.1.0a6 — unreleased`.
7. The fast tier (`-n 3`) and the full judge, serially, in the worktree, without `--accept`: no
   pass lost, nothing grows, the judge change named. `ruff check` and `ruff format --check` are
   clean on `src tests recipes/guest`.

## Landing notes
