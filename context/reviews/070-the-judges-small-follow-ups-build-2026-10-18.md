# Review of spec 070's build: the judge's small follow-ups

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). It wrote none of this build, nor the spec, nor the three reviews (057, 060, 062) whose notes it closes.
- **Reviewed:** `git diff 4a94c14..e51f35a` on `spec/070-the-judges-small-follow-ups` (`/Users/claygendron/Git/Repos/wasi_python-070`): `302aa95` (the build), `a304d3e` (the Design section), `e51f35a` (the landing notes). 9 files, +394 −2. The worktree is clean at `e51f35a`; this review wrote nothing in either git tree (only ignored `build/progress/` files, as any judge run does).
- **Main moved only in docs** (EXECUTED): `git diff 4a94c14 ef1441b --stat` is 32 files, every one under `context/` (a research memo with its evidence and scripts, a security review, the roadmap). No judging file, no `src/`, no `tests/`. The branch needs no rebase to be judged.
- **Read:** the spec in full (Decisions 1 to 6, Design, criteria 1 to 7, Landing notes); the whole diff; `release_binding_errors` (rules 1 to 18) and `step_fields` in `tests/harness/scan.py`; `target`, `_volume_errors` and `errors` in `tests/harness/history.py`; the history writer in `tests/harness/plugin.py`; `_C_SLOTS`, `_bound_keywords` and `admit` in `src/wasi_python/tools.py`; 057's Confirmation ("What rule 16 still lets through"), 062's F1/F2 and verdict, 060's N1 to N3; spec 055's scope; the README's tool-budget sentences; `.gitattributes`.
- **Executed.** Everything is beside this file, under `070-buildreview/`, with `WASI_PYTHON_ARTIFACTS=/Users/claygendron/Git/Repos/wasi_python/build/sets/s-4eb5418a2b1bb553-c353b1d9` (read only), as the builder's logs did:
  - the fast tier, `uv run pytest -m "not slow" -n 3` (`fast-n3.log`, `latest-fast.json`);
  - the full judge, `uv run pytest -n 3` (`full-n3.log`, `latest-full.json`);
  - the builder's stand-ins, re-run unchanged (`standins-rerun.out`);
  - eleven mutants of my own (`probes/mutants.py`, `mutants.out`);
  - rule 16 against nineteen spellings, on the branch and on main's rule (`probes/rule16_probe.py`, `probes/rule16_probe.out`);
  - a bare carriage return inside the newest history line, on the real rule and on a mutant (`probes/test_cr_probe.py`, `probes/cr_probe.out`);
  - `ruff check` and `ruff format --check` on `src tests recipes/guest`.

## The judge

- **Fast tier** (EXECUTED, `fast-n3.log`): exit 0, `1592 passed, 27 skipped`. `wasi_python v1: 353/418 pass · 0 gap · 19 blocked · 0 fail · 46 deselected (unit suite 1239/1247, 8 skipped)`. `ratchet vs 2ce08a592d: lost 0 · absent 0 · unrun 0 · unrun locally 17 · gained 2 · grew 0 · upstream unrun 31 · not selected 32 · judge changed: tests/checks/test_v1_4_embedding.py, tests/harness/history.py, tests/harness/scan.py and 3 more`. The same verdicts and counts as the builder's `fast-n3.log`.
- **Full judge** (EXECUTED, `full-n3.log`, `-n 3`): exit 0, `1604 passed, 59 skipped, 2 xfailed`. `wasi_python v1: 365/418 pass · 2 gap · 51 blocked · 0 fail (unit suite 1239/1247, 8 skipped)`. `ratchet vs 2ce08a592d: lost 0 · absent 0 · unrun 0 · unrun locally 37 · gained 2 · grew 0 · upstream unrun 31 · judge changed: …and 3 more`. The same counts as the builder's serial `full-serial.log`. The blocks are the worktree's missing source trees, oracle, clones, wheel and three systems. The 2 gained are the two v1.4 discovery checks. `latest.json` is kept as `latest-full.json`; the lane's serial run and `sameness.py` still follow.
- **ruff** (EXECUTED): `All checks passed!`; `92 files already formatted`.
- **The judge hash moves, on purpose.** The six judging files named are the three harness/check files above and the three unit files. The lane accepts with `--accept-judge`, as the spec says.

## Is the judge weakened? (rule 4)

- **No existing check, golden, gap or allowance is edited** (EXECUTED). The only removed line in `tests/`, `src/`, `recipes/`, `scripts/`, `downloads/` and `.github/` is rule 16's old `path = w.get("path", "").rstrip("/")`. Nothing under `src/`, `recipes/`, `scripts/`, `downloads/SHA256SUMS`, the workflow, `tests/known_gaps.toml`, `tests/upstream/` or `context/progress/` changes. Every other test line is an addition.
- **The CR rule only adds an error** (READ). It cannot make a history pass that failed. Main's two volumes hold no CR (EXECUTED, `tr -cd '\r' | wc -c`: 0 and 0, in the worktree and in main at `ef1441b`). It cannot fire on a Windows checkout: `.gitattributes` is `* text=auto eol=lf`, and the writer appends with `newline="\n"` (READ, `plugin.py` line 817).
- **Rule 16's change is the one place a spelling moves from refused to passed** (EXECUTED, `rule16_probe.out`). `release-assets/..` and `release-assets/../other` were refused by main's text compare (they start with `release-assets/`) and now pass, because `normpath` makes them `.` and `other`. Neither names release-assets. `path: .` (the same folder as `release-assets/..`) passed rule 16 on main too. So no folder that receives files into release-assets became allowed; only two false positives went away. I count it as no weakening, and record it as N1 so the lane sees it.
- **Rule 16 gains** (EXECUTED): `./release-assets`, `rebuilds/../release-assets`, `./release-assets/../release-assets`, `.//release-assets`, `${{ github.workspace }}/…` with any inner spacing, and `./release-assets/wheel` now name rule 16; on main they passed.

## The items

1. **Rule 16 normalises the path** (Decision 1). Met, as the 057 reviewer worded the fix (READ, EXECUTED). `posixpath.normpath(WORKSPACE_PREFIX.sub("", str(...)))`. The two "let through" tests guard against over-refusal of a rebuild folder. The real workflow still passes every release scan (EXECUTED, in both judge runs). What it still reads as text is F1.
2. **062 F1, the exact-BUDGET roll.** Met (READ, EXECUTED). The volume is padded so the next line ends at exactly `BUDGET` (the helper asserts the arithmetic). Both sides are tested for `target` and for `errors`, and each line placed on the wrong side by hand is reported. The 062 review's S8 (`<` for `<=` in `target`) now fails (builder's S3, re-run). My M7 (`errors` lenient by one byte), M8 (begun-early one byte too strict) and M9 (`target` rolls one byte late) each fail one of the three tests. The boundary is pinned from all six directions I could name.
3. **062 F2, a CR in a volume.** The rule is right; its test pins one position only (F2). EXECUTED: the real rule reports a bare CR placed inside the newest line's JSON (where `json.loads` reads it as whitespace and nothing chains to it). But my M2 (`b"\r\n" in data`) and M3 (`data.endswith(b"\r\n")`) both pass the builder's test, and under M3 the bare-CR probe goes unreported by the whole intact check.
4. **060 N1, left out.** The deferral is sound in substance (READ). The fix is in `src/wasi_python/tools.py`'s answer path, so it would make this a product change with its own release note; the 060 reviewer called it optional ("this can wait"); its cost is per frame and bounded by `max_tool_calls`, as the README already says; and its only check would count internal calls. But its stated home is not real yet (F4).
5. **060 N2, the README and a v1.4 check.** Met (READ, EXECUTED). The **Limits** sentence is accurate, and `test_a_refused_discovery_frame_is_an_import_error[calls|bytes]` holds it: the exact `ImportError` text and the record `[(None, "budget_exceeded")]`. The builder's S12 (first frame exempt) fails both. My M10 (a refused frame goes unrecorded) fails both, and M11 (the bytes refusal named `too_large`) fails `[bytes]`. One nearby README sentence still says the old thing (F3).
6. **060 N3, a depth pin per `_C_SLOTS` kind.** Met (READ, EXECUTED). The reasoning holds: a missing kind costs one hop and so meets the 64-hop limit at a 63-link chain. The test first asserts each end really is its kind, and pins the limit itself (63 links read, 64 refused). The builder's S7 to S11 fail as claimed. Its stand-ins left out one kind alone, `WrapperDescriptorType`; my M1 removes it, and the class case fails (without it, `type.__call__`'s own `__call__` is again a wrapper descriptor, so the walk circles to the limit). My M6 (`range(_WRAPPER_DEPTH + 1)`) fails all five.

## Stand-ins (EXECUTED)

- **The builder's twelve**, re-run unchanged with its own `standins.py` into a fresh rsync copy (`standins-rerun.out`): S1 to S12 each exit 1, and the FAILED lines are identical to the builder's `standins.out` (diff, timings removed: no difference). 21 FAILED lines in all.
- **Mine** (`mutants.out`), each alone, by `-k`:

| Mutant | Result |
|---|---|
| M1 `_C_SLOTS` without `WrapperDescriptorType` alone | fails `[wrapper_descriptor]` |
| M2 CR rule only for `\r\n` | **survives** (F2) |
| M3 CR rule only at the volume's end | **survives** (F2) |
| M4 workspace prefix with exact spacing only | fails `${{github.workspace}}/./release-assets/` |
| M5 rule 16 without the `release-assets/` subfolder clause | fails `./release-assets/wheel` |
| M6 the walk reads one hop more | fails all five slot kinds |
| M7 `errors` lenient by one byte (`> BUDGET + 1`) | fails the exact-byte intact test |
| M8 begun-early one byte too strict (`<= BUDGET + 1`) | fails the exact-byte intact test |
| M9 `target` rolls one byte late (`<= BUDGET + 1`) | fails the one-byte-past test |
| M10 a refused frame goes unrecorded | fails `[calls]` and `[bytes]` |
| M11 the bytes refusal named `too_large` | fails `[bytes]` |

## Findings, most severe first

None is a weakening of the judge. None blocks on safety. Each is a line or two.

1. **F1 (low). Rule 16 still reads a quoted `path:` as text.** EXECUTED (`rule16_probe.out`). In `same-bytes`, a rebuild download with `path: "release-assets"`, `path: 'release-assets'` or `path: "./release-assets"` passes rule 16, on the branch as on main: `step_fields` keeps YAML quotes, and `normpath` keeps them too. So does `${{ github.workspace }}//release-assets` (the prefix is dropped, leaving the absolute `/release-assets`). A quoted value is the likeliest other spelling a YAML formatter writes, and the spec's Intent says rule 16 reads `path:` "as a path, not as text". Not a regression, and the 057 reviewer did not name quotes. *Fix:* drop one pair of matching quotes before normalising, and let the prefix pattern eat `/+`; add the three spellings to `OTHER_SPELLINGS`. Or answer in writing that quoting is out of scope (rule 7 has the same text compare for holders, and a quoted path there fails rule 7, so only `same-bytes` is open).
2. **F2 (low). The CR rule is pinned at one position.** EXECUTED (M2, M3 survive; `cr_probe.out`). Decision 3 says a CR is reported "wherever it is", and the case for the rule is exactly the newest line, where nothing chains. The only test puts it before the final LF. A rule narrowed to `\r\n`, or to the end of the volume, passes it, and under the narrowed rule a bare CR inside the newest line passes the whole intact check. *Fix:* one more case, a bare CR inside the newest line (my `probes/test_cr_probe.py` is that case, and it passes on the branch).
3. **F3 (low, docs). One README sentence still says the old thing.** READ. README line 1466–1467 (under the frame checks): "Every frame counts toward the run's budget, the guest's discovery frame included; past it the guest gets `ToolBudgetExceeded` and runs on." For the discovery frame itself that is the `ImportError` the new **Limits** sentence describes. The keyword lists repeat the general form (lines 1651–1652 and 1939–1940, "the guest gets `ToolBudgetExceeded`"); those read as the rule for later frames and can stay. *Fix:* end 1467's sentence with "(an `ImportError`, if the discovery frame itself is refused; see **Limits**)", or answer that **Limits** is the one place that says it.
4. **F4 (low, record). N1's deferral has no home outside this spec.** READ. Decision 6 says N1 "belongs with the next change that touches `_answer` (spec 055 is the nearest)". Spec 055 touches `tools.py` for `_Bounded` (an abandoned-thread count), not `_answer`, and neither 055 nor the roadmap mentions 060's N1. Once 070 lands, the note lives only in a landed spec's Decisions, where the next builder of `_answer` will not look. *Fix:* correct "touches `_answer`" to "touches `tools.py`", and put one line where follow-ups are picked up (the roadmap, or 055's notes if the owner wants it there).

## Notes (no change needed)

- **N1.** Rule 16 now passes `release-assets/..` and `release-assets/../other`, which main's text compare refused (above). Neither names release-assets, and `path: .` always passed. This is the one spelling-level move from refused to passed; I record it so the judge-change review sees it, and accept it.
- **N2.** The docstrings number the items differently from the spec: `test_tools.py` and `test_v1_4_embedding.py` both say "Spec 070, item 3"; the spec has them as Decisions 4 and 5. Harmless; "Decision 4"/"Decision 5" would match.
- **N3.** The landing notes' parallel-work warning (spec 063 edits `scan.py` and `test_scan.py`, not rule 16's lines) is right to keep: the lane keeps both.
- **N4.** The first full run's red (the missing `## Design`) was the spec-shape rule doing its job, and `a304d3e` fixes it with a section that matches the diff (READ).

## Verdict

**Lands once F1 to F4 are fixed or answered in writing.** Each is a line or two. None weakens the judge, and the build already does everything its acceptance criteria say: no check got easier to pass in substance, every new check has a stand-in it catches (the builder's twelve, re-run, and nine of my eleven), and both judge tiers are green with lost 0, grew 0 and gained 2. If the fixes come as a delta, the delta review needs only the diff, the three new cases' stand-ins (M2 or M3 for F2, main's rule for F1), and the fast tier.

One line: the follow-ups are sound and tighten the judge; a quoted `path:`, a CR away from the line's end, one README sentence and N1's home are the four small gaps left to close or answer.


# Confirmation of spec 070's revision against its build review

- **Date:** 2026-10-18
- **Reviewer:** the same fresh agent that wrote `070-the-judges-small-follow-ups-build-2026-10-18.md` (beside this file). It wrote none of the build or the revision.
- **Reviewed:** `git diff 9a1515f 6bdbe91` (the revision) and `282f71a` (its landing notes) on `spec/070-the-judges-small-follow-ups`, now rebased onto main `a0de463`. The worktree is clean at `282f71a`. This review wrote nothing in either git tree.
- **Executed.** Everything is beside this file, with the frozen set `build/sets/s-4eb5418a2b1bb553-c353b1d9` as before:
  - `range-diff.txt`;
  - `confirm-fast-n3.log`, `latest-confirm-fast.json`;
  - `standins-revised-rerun.out` (the builder's S1 to S18, re-run);
  - `probes/mutants-rev.py`, `mutants-rev.out` (my M1 to M13);
  - `probes/rule16_probe-rev.out`;
  - the CR probe, re-run.

## The rebase changed nothing else

- **EXECUTED.** `git range-diff 4a94c14..e51f35a a0de463..9a1515f` shows `=` for all three commits (`302aa95 = 9020ba0`, `a304d3e = 635a28c`, `e51f35a = 9a1515f`), so the patches are identical.
- **EXECUTED.** Main moved from `ef1441b` to `a0de463` in `CHANGELOG.md` and `src/wasi_python/__init__.py` only (the a6 release and the a7 bump).
- **EXECUTED.** `282f71a` touches only the spec file (+26).
- **EXECUTED.** The whole branch against main, `git diff a0de463 282f71a --stat`, is 10 files:
  - the nine reviewed;
  - plus `context/roadmap.md` (the reservation of 075). Nothing under `src/`, `scripts/`, `recipes/`, `downloads/` or `.github/` changes.

## Each finding

- **F1, fixed.** READ and EXECUTED.
  - What changed: `download_path` drops one pair of matching quotes, then the workspace prefix, whose pattern now ends in `/+`, then `normpath`.
  - The probe (`rule16_probe-rev.out`): `"release-assets"`, `'release-assets'`, `"./release-assets"`, `'./release-assets'` and `${{ github.workspace }}//release-assets` now name rule 16. Every spelling that rule 16 named before still names it.
  - The tests: `OTHER_SPELLINGS` holds four more spellings. The let-through test holds a quoted rebuild folder, so the quote stripping cannot over-refuse.
  - Stand-ins: the builder's S13 to S16 fail as claimed. My M12 (keep the quotes) and M13 (one slash only) fail too.
  - Not a weakening: a quoted value never matched `release-assets` before, so stripping quotes can only add refusals.
  - What still passes, unchanged and never raised: absolute paths, `~`, `../<repo>/…`, a different case. These are out of the scope the 057 reviewer named.
- **F2, fixed.** EXECUTED.
  - `test_a_bare_carriage_return_inside_the_newest_line` is my probe's case.
  - My M2 (`\r\n` only) and M3 (the volume's end only) now fail it, and so do the builder's S17 and S18, which are the same two mutants.
  - The probe still passes on the real rule.
- **F3, fixed.** READ. README line 1467 now reads "…and runs on (an `ImportError`, if the discovery frame itself is refused; see **Limits**)". It agrees with the **Limits** sentence.
- **F4, fixed as the lane ruled.** READ.
  - Decision 6 and the Disposition now name spec 075, "tools.py small fixes".
  - `context/roadmap.md` has a "Reserved: 075" line. It names 060's N1 and the a6 security review's F1.
  - The wrong "touches `_answer`" wording is gone.
  - No spec 07x exists on main, so the number is free.
- **N2, fixed.** READ. The docstrings and comments now name Decisions 1 to 5.
- **The CHANGELOG** (READ). The entry moved to `0.1.0a7 — unreleased`, replacing the placeholder. That is right, since 0.1.0a6 is tagged.

## Stand-ins and mutants (EXECUTED)

- **The builder's S1 to S18**, re-run with its `standins.py` into a fresh copy: all 18 exit 1. The output matches `standins-revised.out` once timings are removed.
- **My mutants on the revision** (`mutants-rev.out`): all thirteen fail.
  - M1 and M4 to M11 are the same mutants as before. M4 is updated for `/+`.
  - M12 and M13 are new, for F1.
  - M2 and M3 now fail `test_a_bare_carriage_return_inside_the_newest_line`.
  - No mutant survives.

## The judge

- **Fast tier** (EXECUTED, `confirm-fast-n3.log`, `-n 3`): exit 0, `1598 passed, 27 skipped`.
  - Scoreboard: `wasi_python v1: 353/418 pass · 0 gap · 19 blocked · 0 fail · 46 deselected (unit suite 1245/1253, 8 skipped)`.
  - Ratchet: `ratchet vs 2ce08a592d: lost 0 · absent 0 · unrun 0 · unrun locally 17 · gained 2 · grew 0 · … judge changed: …and 3 more`.
  - The unit suite grew by 6: the four spellings, the quoted rebuild folder and the bare-CR case.
- **Full judge:** not re-run, which the coordinator allowed. The builder's `rev-full-n3.log` (READ) has `1610 passed, 59 skipped, 2 xfailed` and `365/418 · 0 fail`, with lost 0, gained 2 and grew 0. That agrees with the fast tier's six more unit tests.
- **ruff** (EXECUTED): `ruff check` and `ruff format --check` on `src tests recipes/guest` are clean.
- The lane accepts with `--accept-judge`, serially, in the main tree, and records `sameness.py`.

## Verdict

**Confirmed, it lands.**
- F1 to F4 and N2 are fixed.
- M2 and M3 now fail.
- The rebase changed nothing else.
- Every stand-in and mutant is caught.
- The fast tier is green with lost 0 and grew 0.

One line: every finding is closed, the judge only got stricter, and no mutant survives.
