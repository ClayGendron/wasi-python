# 070 — The judge's small follow-ups

- **Status:** built 2026-10-18; its build review (written in the lane's scratchpad,
  `070-buildreview/`, and copied to `context/reviews/` by the lane) said
  "lands once F1 to F4 are fixed or answered in writing"; revised 2026-10-19 with F1 to F4 fixed
  and N2 done as the lane ruled (the Disposition), and rebased onto main `a0de463` (the 0.1.0a6
  release and the 0.1.0a7 bump); awaiting the delta review. Drafted and built 2026-10-18 on
  `spec/070-the-judges-small-follow-ups` from main `4a94c14` (the Landing notes). It changes
  neither the guest's imports nor its exports, the artifact set nor the build recipe, so §5.6
  asks no review before build. A different agent reviews the build.
- **Date:** 2026-10-18
- **Owner:** Clay Gendron
- **Kind:** a judge change and two README clauses; **parallel-safe**, not build-class (§5.7).
  It edits `tests/harness/scan.py` (rule 16 of `release_binding_errors`) and
  `tests/harness/history.py` (`_volume_errors`), adds unit cases to `tests/unit/test_scan.py`,
  `tests/unit/test_history.py` and `tests/unit/test_tools.py`, adds one v1.4 check to
  `tests/checks/test_v1_4_embedding.py`, and adds two clauses to `README.md`, one entry to
  `CHANGELOG.md` and one "Reserved: 075" line to `context/roadmap.md`. It touches no `src/`, `scripts/`, `recipes/`, `downloads/SHA256SUMS` or
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

1. **Rule 16 normalises the path** (057's Confirmation; this spec's build review, F1).
   `scan.download_path` reads a download's `path:` as the folder it names. It drops one pair of
   matching YAML quotes (`"…"` or `'…'`). It drops a leading `${{ github.workspace }}` and every
   slash after it (any spacing inside the braces). Then it applies `posixpath.normpath`. Rule 16
   compares the result with `release-assets`. *Reason:* in `same-bytes`, `./release-assets`,
   `rebuilds/../release-assets`, `${{ github.workspace }}/release-assets`, `"release-assets"`,
   `'release-assets'`, `"./release-assets"` and `${{ github.workspace }}//release-assets` name
   the same folder as the plain spelling, which rule 16 already refuses. The fix is the one the
   057 reviewer named, widened by this spec's build review to quotes, the likeliest spelling a
   YAML formatter writes, and to a doubled slash. One move goes the other way, and is accepted:
   `release-assets/..` and `release-assets/../other` used to be refused as text and now pass.
   Neither names release-assets (the build review's N1). Other rules that compare `path:` are not changed: in a holder job, rule
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
   for both). Two cases pin "wherever it is": a CR before the newest line's final LF, and a bare
   CR inside the newest line, where `json.loads` reads it as whitespace (the build review's F2).
   A rule narrowed to CR LF, or to the volume's end, fails the second.
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
   request budget too small for it), `from host import tools` raises `ImportError`. The frame
   checks' sentence in *The tool protocol* ("past it the guest gets `ToolBudgetExceeded` and runs
   on") gains "(an `ImportError`, if the discovery frame itself is refused; see **Limits**)", so
   the two agree (the build review's F3). The keyword lists keep their general form; they read as
   the rule for later frames. A v1.4 check holds it under both limits. *Reason:* the README said "Past either, the guest gets
   `ToolBudgetExceeded` and runs on". That is not true of the first frame, and no check held
   what is true.
6. **N1 is left out** (060's N1: an oversized tool list is built whole on every `list` frame,
   only to be measured and refused). *Reason:* the fix is in `src/wasi_python/tools.py`, the
   host's answer path. It would turn this judge change into a product change, with its own
   release note. Its only check would read an internal count of calls. Its cost is already
   bounded by `max_tool_calls`, as the README says, and the review says it "can wait". Its home
   is spec 075, "tools.py small fixes", a small follow-up reserved in `context/roadmap.md`. That
   spec also takes the 0.1.0a6 security review's F1: an async gate that raises `GeneratorExit`
   lets the call through (the lane's ruling on this spec's build review, F4).

## Design

- `tests/harness/scan.py`: `import posixpath`; `WORKSPACE_PREFIX`, a pattern for a leading
  `${{ github.workspace }}` and the slashes after it; `download_path(value)`; rule 16 compares
  `download_path(w.get("path", ""))` (Decision 1).
- `tests/harness/history.py`: one line in `_volume_errors` (Decision 3).
- `tests/unit/test_scan.py`: `OTHER_SPELLINGS` and two parametrized tests beside rule 16's
  others. `tests/unit/test_history.py`: `_next_line`, `_volume_1_ending` and `_place`, and five
  tests at its end (Decisions 2 and 3). `tests/unit/test_tools.py`: `C_SLOT_ENDS`,
  `_wrapped_chain` and one parametrized test after the bound-keyword test (Decision 4).
- `tests/checks/test_v1_4_embedding.py`: `DISCOVERY_REFUSED` and one check, parametrized over
  the two limits, after spec 060's byte-budget check (Decision 5).
- `README.md` (**Limits**, and the frame checks in *The tool protocol*), `CHANGELOG.md`
  (`0.1.0a7 — unreleased`) and `context/roadmap.md` ("Reserved: 075").

## Scope

In: rule 16's path, the boundary and CR cases with the CR rule, the `_C_SLOTS` pin, the README
clauses and their check, one CHANGELOG entry, the roadmap's reservation of 075. Out: N1
(Decision 6); rule 7's own path comparison
(Decision 1); any change to `src/`, the workflow, the history's bytes or `BUDGET`.

## Acceptance criteria

Each check was written before the code it holds, and each fails against the stand-in named
(EXECUTED, `build/reviews-evidence/070-build/standins.py` and `standins.out` in the main tree;
each stand-in applied alone to a scratch copy and run by node id).

1. `test_rule_16_reads_the_download_path_as_a_path` (unit, 9 spellings: `./release-assets`,
   `rebuilds/../release-assets`, `${{ github.workspace }}/release-assets`,
   `${{github.workspace}}/./release-assets/`, `./release-assets/wheel`, `"release-assets"`,
   `'release-assets'`, `"./release-assets"`, `${{ github.workspace }}//release-assets`) each
   name rule 16 alone. `test_rule_16_lets_another_spelling_of_a_rebuild_folder_through` (3
   spellings, one quoted) is clean, and `test_the_release_workflow_passes_every_release_scan`
   still passes on the real workflow. Stand-ins: main's text compare (S1, 9 failed); normpath
   without dropping the workspace prefix (S2, the 3 workspace spellings); no quotes dropped (S13,
   the 3 quoted); double quotes only (S14, `'release-assets'`); quotes dropped but no normpath
   (S15, 5 failed, `"./release-assets"` among them); the prefix eating one slash only (S16,
   `${{ github.workspace }}//release-assets`).
2. `test_a_line_that_ends_exactly_at_the_budget_stays_in_the_newest_volume`,
   `test_a_line_one_byte_past_the_budget_starts_a_volume` and
   `test_the_intact_check_holds_the_budget_at_its_exact_byte` (unit) pass. Stand-ins: `target`
   with `<` for `<=` (S3, the 062 review's S8); `errors` with `offset >= BUDGET` (S4); the
   begun-early test with `<` (S5). Each fails one of them.
3. `test_a_volume_that_holds_a_carriage_return` and
   `test_a_bare_carriage_return_inside_the_newest_line` (unit): a CR before the newest line's
   final LF, and a bare CR inside it, each give exactly
   `["history-…jsonl holds a carriage return"]`. Stand-ins: no CR rule, which is main (S6, both
   fail); the rule only for CR LF (S17, the review's M2) and only at the volume's end (S18, the
   review's M3), each failing the bare-CR case.
4. `test_the_bound_keyword_walk_stops_at_each_c_slot` (unit, 5 kinds) passes. Stand-ins: each
   of the four kinds the review found unpinned, removed alone (S7 to S10, each fails its own
   kind); the review's stand-in (q), the list narrowed to `WrapperDescriptorType` (S11, 4
   failed).
5. `test_a_refused_discovery_frame_is_an_import_error[calls]` and `[bytes]` (v1.4, guest):
   `ImportError the host refused the tool list (budget_exceeded): …` is printed, and the record's
   outcomes are exactly `[(None, "budget_exceeded")]`. Stand-in: `admit` exempts the first frame
   from both limits (S12, 2 failed: the import succeeds).
6. The README's **Limits** and frame-checks sentence carry Decision 5's words; the CHANGELOG
   has one entry under `0.1.0a7 — unreleased`; the roadmap has "Reserved: 075" naming 060's N1
   and the a6 security review's F1.
7. The fast tier (`-n 3`) and the full judge (serially at the build, `-n 3` at the revision),
   in the worktree, without `--accept`: no
   pass lost, nothing grows, the judge change named. `ruff check` and `ruff format --check` are
   clean on `src tests recipes/guest`.

## Disposition of the build review

The review: `070-the-judges-small-follow-ups-build-2026-10-18.md`, written in the lane's
scratchpad (`070-buildreview/`, its probes beside it) and copied to `context/reviews/` by the
lane. Verdict: "lands once F1 to F4 are fixed or answered in writing". The lane ruled on each.

- **F1 (low), a quoted `path:` read as text.** Fixed as ruled. `download_path` drops one pair
  of matching quotes, and `WORKSPACE_PREFIX` ends in `/+`. The four spellings (`"release-assets"`,
  `'release-assets'`, `"./release-assets"`, `${{ github.workspace }}//release-assets`) are in
  `OTHER_SPELLINGS`, and each reports rule 16 alone. They failed on the build before the fix (4
  failed). Each has a stand-in that fails it: S13, S14, S15 and S16 (criterion 1). Decision 1
  says so, and records N1.
- **F2 (low), the CR rule pinned at one position.** Fixed as ruled. The review's case (its
  `probes/test_cr_probe.py`, a bare CR inside the newest line) is now
  `test_a_bare_carriage_return_inside_the_newest_line`. The review's M2 and M3 now fail it (S17,
  S18).
- **F3 (low, docs), README lines 1466–1467.** Fixed as ruled: the sentence ends "(an
  `ImportError`, if the discovery frame itself is refused; see **Limits**)".
- **F4 (low, record), N1's home.** Fixed as ruled. Decision 6 now names spec 075, "tools.py
  small fixes", which also takes the a6 security review's F1. `context/roadmap.md` has a
  "Reserved: 075" line naming both.
- **N1, `release-assets/..` now passes.** Accepted by the review; recorded in Decision 1.
- **N2, the docstrings' numbering.** Done: "Decision 1", "Decisions 2 and 3", "Decision 4" and
  "Decision 5", as the spec numbers them.
- **N3 and N4.** No change: the parallel-work note stays, and the Design section stands.

## Landing notes

**Built 2026-10-18** on `spec/070-the-judges-small-follow-ups` from main `4a94c14`, in the
worktree `wasi_python-070`, against the frozen set `build/sets/s-4eb5418a2b1bb553-c353b1d9`
(the main tree's, `SHA256SUMS` `c353b1d9…`). The build is `302aa95`; `a304d3e` adds the Design
section that the first full judge found missing; these notes are the commit after it. Evidence
is in the main tree under `build/reviews-evidence/070-build/`.

- **Checks first.** Each new check was run before its code. On main's code, rule 16's 5
  spellings failed (`5 failed, 2 passed`) and the CR case failed (`[] == [...]`). The boundary
  cases, the `_C_SLOTS` cases and the discovery check pin code that is already right, so they
  pass on main; what shows they bite is their stand-ins.
- **Stand-ins** (EXECUTED, `standins.py`, `standins.out`): S1 to S12, each applied alone to an
  rsync copy of the worktree and run by node id, the file restored after. Every one fails what
  the criteria say it fails: S1 5 failed; S2 2; S3, S4, S5 and S6 1 each; S7 to S10 1 each,
  each its own kind; S11 4; S12 2 (the import succeeds).
- **The fast tier** (`fast-n3.log`; `uv run pytest -m "not slow" -n 3`, before the spec file
  was written): `wasi_python v1: 353/418 pass · 0 gap · 19 blocked · 0 fail · 46 deselected
  (unit suite 1239/1247, 8 skipped)`, `ratchet vs 2ce08a592d: lost 0 · absent 0 · unrun 0 ·
  unrun locally 17 · gained 2 · grew 0 · upstream unrun 31 · not selected 32 · judge changed:
  tests/checks/test_v1_4_embedding.py, tests/harness/history.py, tests/harness/scan.py and 3
  more`, `1592 passed, 27 skipped`, exit 0.
- **The full judge, serial, no `--accept`.** The first run on `302aa95`
  (`full-serial-1-red.log`) had `1 failed`: `test_specifications_have_their_header_and_sections`,
  "070-the-judges-small-follow-ups.md: no '## Design' section"; `lost 1` was that rule. Fixed in
  `a304d3e`. The run on `a304d3e` (`full-serial.log`): `wasi_python v1: 365/418 pass · 2 gap · 51
  blocked · 0 fail (unit suite 1239/1247, 8 skipped)`, `ratchet vs 2ce08a592d: lost 0 · absent 0
  · unrun 0 · unrun locally 37 · gained 2 · grew 0 · upstream unrun 31 · judge changed:
  tests/checks/test_v1_4_embedding.py, tests/harness/history.py, tests/harness/scan.py and 3
  more`, `1604 passed, 59 skipped, 2 xfailed`, exit 0. The blocks are the worktree's missing
  source trees, oracle, clones, `wheel` and `three systems`, as in any worktree. The 2 gained
  are criterion 5's two v1.4 checks. The real workflow passes every release scan, and main's
  two history volumes pass the intact check with the CR rule.
- `ruff check` and `ruff format --check` on `src tests recipes/guest`: clean.
- **Parallel work.** Spec 063's branch edits `tests/harness/scan.py` and
  `tests/unit/test_scan.py` too, though not rule 16's lines. Whichever lands second may meet a
  local conflict in `test_scan.py`, and keeps both.
- **Not done here:** no `--accept`, no push, no rebase. The review gets this specification and
  `git diff 4a94c14..` on this branch. The lane accepts with `--accept-judge`.

**Revised against the build review, 2026-10-19.** Rebased onto main `a0de463` (the 0.1.0a6
release and the 0.1.0a7 bump), with no conflict: the build is now `9020ba0`, the Design fix
`635a28c`, the first landing notes `9a1515f`. The CHANGELOG entry moved from the released 0.1.0a6
section to `0.1.0a7 — unreleased`. The revision is `6bdbe91` (the Disposition says what it
changes); these notes are the commit after it. Same frozen set, `s-4eb5418a2b1bb553-c353b1d9`.

- **Checks first.** F1's four spellings were added before the code: on the build, `4 failed, 7
  passed`. With the fix, all 12 rule-16 cases pass. F2's case passes on the build (the rule was
  already right). The review's M2 and M3 now fail it.
- **Stand-ins** (EXECUTED, `standins.py` extended, `standins-revised.out`): S1 to S18 each exit
  1. S1 to S12 as before, with S1 at 9 failed, S2 at 3 and S6 at 2, now that there are more
  cases. S13 fails 3, S14 1, S15 5, S16 1, S17 1 and S18 1 (criteria 1 and 3).
- **The fast tier** (`rev-fast-n3.log`, `-n 3`): `wasi_python v1: 353/418 pass · 0 gap · 19
  blocked · 0 fail · 46 deselected (unit suite 1245/1253, 8 skipped)`, `ratchet vs 2ce08a592d:
  lost 0 · absent 0 · unrun 0 · unrun locally 17 · gained 2 · grew 0 · upstream unrun 31 · not
  selected 32 · judge changed: tests/checks/test_v1_4_embedding.py, tests/harness/history.py,
  tests/harness/scan.py and 3 more`, `1598 passed, 27 skipped`, exit 0.
- **The full judge** (`rev-full-n3.log`, `uv run pytest -n 3`, no `--accept`, on `6bdbe91`):
  `wasi_python v1: 365/418 pass · 2 gap · 51 blocked · 0 fail (unit suite 1245/1253, 8
  skipped)`, `ratchet vs 2ce08a592d: lost 0 · absent 0 · unrun 0 · unrun locally 37 · gained 2 ·
  grew 0 · upstream unrun 31 · judge changed: (the same files)`, `1610 passed, 59 skipped, 2
  xfailed`, exit 0. The blocks are as before, the worktree's.
- `ruff check` and `ruff format --check` on `src tests recipes/guest`: clean.
- **Not done here:** no `--accept`, no push. The delta review gets the Disposition, `git diff
  9a1515f 6bdbe91`, stand-ins S13 to S18 and the fast tier.
