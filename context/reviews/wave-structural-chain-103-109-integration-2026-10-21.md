# Review of the structural chain's integration (103, 104, 105, 106, 107, 108, 109)

- **Date:** 2026-10-21
- **Reviewer:** a fresh agent (Claude). It wrote none of 103 to 109 and reviewed none of them
  before. It is the wave's integration reviewer (AGENTS.md rule 8; constitution §5.7). The file
  is named as the eight wave reviews before it, `wave-<id>-integration-<date>.md`, the chain
  standing for the number, since "wave 09" is already the roadmap's name for 100, 101 and 097.
- **Reviewed:** `claude/gallant-ride-9nxxmn` at `1b85fe1`, the same commit as `integration/full`
  in `/home/user/wt/integration`: the chain 103 → 104 → 105 → 106 → 107 → 108 → 109 rebased by
  the coordinator onto main `dda6075` (wave 08 landed), 74 commits, linear (EXECUTED:
  `git log --oneline origin/main..1b85fe1 | wc -l` → 74; `git merge-base` → `dda6075`). The
  chain's base before the rebase was `5feb7e9` (EXECUTED: `git merge-base origin/main e319829`).
- **Run:** pending: dispatched by the owner on `1b85fe1`; read back before the verdict. The
  integration's GitHub App cannot dispatch the release workflow (403), so no run of the chain's
  own exists yet: each entry's build review says "none; the chain's one dispatch on its final
  tip" (the owner, 2026-10-20, the memo's section 8). 109 is build-class by the letter (comments
  in `scripts/` and the workflow; `MANIFEST`'s recipe hashes move), so the wave needs its dry run
  on three systems before the fast-forward.
- **Re-ran** (EXECUTED, in `/home/user/wt/integration` at `1b85fe1`, the a7 set at
  `build/baseline-a7/set/wasi-python-0.1.0a7` as `WASI_PYTHON_ARTIFACTS`; no lock existed and
  none was taken; the fast tier was not re-run, the records read true):
  - `uv run python tests/harness/sameness.py build/integration/main-baseline.json
    build/integration/built.json --claims build/integration/109/claims-chain.toml` → exactly
    `note: explained by claims: 103 4 · 104 3 · 105 4 · 106 3 · 107 4 · 108 5 · 109 2`, exit 0;
  - `uv run pytest tests/checks/test_rules.py -q -p no:cacheprovider` → 1 failed, 54 passed,
    3 skipped in 24.9 s; the one red is `test_version_states_the_platform_semantics`, the older
    set's (its `VERSION` predates the platform sentence), as 109's notes say;
  - `uv run ruff check src tests` → "All checks passed!"; `uv run ruff format --check src tests`
    → "151 files already formatted"; `uv run mypy --strict src/wasi_python` → "Success: no
    issues found in 18 source files"; `uv run python tests/harness/api.py --check` → exit 0;
  - probes by node id: `uv run pytest tests/unit/test_runner_package.py tests/unit/test_process.py
    tests/unit/test_lifecycles.py tests/unit/test_wasmtime_ffi.py tests/unit/test_scan.py -q`
    → 314 passed in 2.8 s;
  - the rubric's measurement commands (section 5), each once.
- **Box:** 45 minutes for the rebases, the conflicts, the judge and the context commit; the
  structural rubric inside its own 45. Both ended with the file written; nothing was cut.

The records read: `build/integration/` in the integration worktree (git-ignored): `before.txt`
(68 commits, the chain at `d92307f` and the spec tips), `after.txt` (60, 103 to 108 rebased),
`hashes.md` (70 old → new pairs with 109's bullet), `conflicts.md`, `main-fast.log` +
`main-baseline.json` + `main-failing-nodes.txt` (the fast tier on `dda6075`, `main-fast-commit.txt`
names it), `fast.log` + `built.json` + `failing-nodes.txt` (on `1b85fe1`, `fast-commit.txt` names
it), `sameness.txt`, `109-hits-before.txt` (2,372 lines), `109-hits-after.txt` (114),
`109-yaml-compare.txt`, and `109/` (`clean.py`, `hand.py` and its batches, `same-code.py`,
`claims-chain.toml`).

## 1. Each entry's rebase against its reviewed diff (EXECUTED)

Method: for each entry, `git diff <old base> <old tip>` against `git diff <new base> <new tip>`
(the bases and tips from `hashes.md`; the old commits are still in the object store), the two
diffs compared line by line with `index` and `@@` lines dropped, and `git range-diff` beside it.
A difference is clean only when it is (a) the renumbering (spec numbers, and the upstream sheet
30 → 34), (b) a conflict resolution named in `conflicts.md` that keeps both sides, (c) 109's
regeneration, or (d) a context-only edit.

| entry | old range | new range | the interdiff | verdict |
|---|---|---|---|---|
| 103 | `5feb7e9..e319829` (17 commits) | `dda6075..287b1f8` | 36 lines: `30-wasmtime-py-…` → `34-…` and "row 30" → "row 34" in the specification (eight lines), the sheet's folder rename, `tests/checks/test_rules.py`'s one path line; the rest is context (main's `npy_fenv_*` block before the private-API rule in `scan.py`, main's rows 30, 32, 33 before row 34 in `context/upstream/README.md`) | clean: (a) and (b) only |
| 104 | `e319829..538e831` (10) | `287b1f8..67273d0` | 4 lines, all context of the roadmap hunk (main's "Reserved: 102" and its reworded 095 paragraph beside the chain's line) | clean: (b) |
| 105 | `538e831..550d79f` (5) | `67273d0..02a45c6` | empty | identical |
| 106 | `550d79f..1893ede` (9, the renumbering commit included) | `02a45c6..fd3a14c` | 32 lines: the `--accept` strings' `30-…` → `34-…` inside the renumbering's own `102:` → `103:` hunk, the sheet rename, and the same roadmap and README context as above | clean: (a) and (b) |
| 107 | `1893ede..0e145b7` (11) | `fd3a14c..c6c48db` | empty | identical |
| 108 | `0e145b7..d92307f` (8) | `c6c48db..ab84933` | empty | identical |
| 109 | `d92307f..b14b68c` (10) | `ab84933..f849c75` (13: the ten replayed, the text regenerated as `9793964`, the allowance `9b5a3f5`, the bullet `f849c75`) | 668 lines, every one a comment or docstring of a file main's nine commits of 2026-10-20 added or changed (`tests/harness/packages.py`, `tests/unit/test_packages.py`, `scripts/assemble_artifacts.py`'s seaborn and reportlab lines, the upstream allowance files, …), plus the allowance rows below | clean: (c), checked below |

Every one of the 70 old → new pairs in `hashes.md` and 109's bullet is on the branch with the
same subject (EXECUTED, a loop over the pairs: 70 pairs, 0 bad); the four branch commits outside
the pairs are the integration's own (`9793964`, `9b5a3f5`, `f849c75`, `1b85fe1`). What each
entry changed after the range its build review read is the review itself and its Disposition:
103, 105, 108 and 109 context only; 104 its three Lows in `tests/unit/test_runner_package.py`
(the per-file import map, the child's three extra imports, a tuple's elements), as its
Disposition says; 106 its one Medium in `_sessions.py` (`aa2239e`, "the join's backstop sets
`ended` on a home already in DONE", with the `(DONE, DONE)` row), as its "lands once" asks; 107
the two empty `#` of its finding 1. Every interdiff line of 103, 104 and 106 is the renumbering
or a named conflict; no hunk differs otherwise.

109's regeneration (c), checked: `same-code` over `3a4a75f..9793964` (my own copy of its token
comparison: comments dropped, docstrings blanked, `#` lines of other files dropped) → 150 files
compared, 0 differ in code; the allowance commit `9b5a3f5` changes `test_rules.py` only. The
allowance at the reviewed tip `b14b68c` was 72 rows (`JUDGE_FILE` 30, `GUEST_INPUT` 32,
`SHAPE_SHOWN` 10); at the tip 92 (41, 41, 10), as the Rebase bullet says, by twelve
`JUDGE_FILE` rows added and one removed (`packages.toml`'s "spec 043", a phrase main's file no
longer carries) and nine `GUEST_INPUT` rows added (finding 2 is the wording). Hits: the build
review read 2,239 → 81; on main 2,372 → 114 (`109-hits-after.txt`: `tests/upstream` 61,
`tests/jobs` 34, `tests/checks` 14, `known_gaps.toml` 5), every one in the allowance. The
workflow parsed with pyyaml differs from `dda6075`'s in the three `run:` scalars of 109's build
review finding 1 and, with their shell comments removed, in nothing
(`109-yaml-compare.txt`). Over the whole wave, `scripts/`, `release/` and `.github/` change in
no code line (EXECUTED, the same comparison over `dda6075..1b85fe1`: 50 files, 0 differ in
code); `recipes/`, `downloads/`, `tests/public_api.txt` and `tests/known_gaps.toml` are
untouched; `pyproject.toml` and `uv.lock` carry 106's `mypy==1.19.1` and `[tool.mypy]`.

## 2. The conflicts (READ, then EXECUTED on the tip)

`conflicts.md` names eight hunks in five commits plus a repair; each is at the tip as it says:

- `tests/harness/scan.py` (at `e517a1a`): main's spec-099 block (`NPY_FENV_*` at 2889,
  `npy_fenv_recipe_errors` … `npy_fenv_records_file_errors` to 2990) comes first, then the chain's
  private-API rule (`PRIVATE_ENGINE` 3005, `private_engine_hits`, `sheet_bindings`,
  `private_api_debt_errors` to 3073), then 109's citation rule (`CITATION_RULES` 3111 to
  `context_citation_files` 3228); 108's seam and function-length scanners (1967 to 2138) and
  105's lock and mutable scanners (2138 to 2228) sit earlier, where no conflict fell. `ruff` is
  clean on it.
- `tests/unit/test_scan.py`: main's six `npy_fenv_*` rows (2275 to 2331), then 109's four
  citation rows (2379 to 2430); 103's, 105's and 108's rows earlier in the file.
- `context/upstream/README.md`: rows 29, 30 (numpy, main's), 32 (Pillow), 33 (contourpy), 34
  (the chain's, "spec 103", thirty-one bindings).
- `context/roadmap.md`: "Reserved: 101", main's "Reserved: 102", then the chain's lines (103 to
  108, 105, 107, 108, the closer, 109), then main's 095 paragraph as main reworded it.
- `context/specifications/103-the-engine-seam.md` at the renumbering commit: the repair left the
  commit's own text, renumbered; `git grep` over the tip finds no conflict marker in any file
  (EXECUTED; the two `=======` lines it finds are pytest's banner in two research records).

No check of either side dropped (EXECUTED, the `def test_` names of each file at `5feb7e9`,
`dda6075`, the chain's old tip `b14b68c` and the tip): `tests/checks/test_rules.py` 33 at the
base and on main, 47 on the old tip and the tip, the fourteen the chain adds all present and no
name of main's missing; `tests/unit/test_scan.py` 63 at the base, 69 on main (six of 099's), 75
on the old tip (twelve of the chain's), 81 on the tip, the union exactly. Nothing retired.

## 3. The judge (READ, EXECUTED where said)

- The fast tier under the frozen a7 set: main `dda6075` 94 failed, 2,385 passed, 54 skipped
  (`main-fast.log`); the tip 94 failed, 2,500 passed, 54 skipped (`fast.log`); `diff
  main-failing-nodes.txt failing-nodes.txt` empty (EXECUTED). The +115 passes are the chain's
  claims exactly: 103's 2 + 17, 104's 1 + 4, 105's 2 + 7 (net of the one retired module-level
  fork row), 106's 1 + 49, 107's 3 + 2, 108's 4 + 4, 109's 1 + 18 = 115, and sameness says
  "explained by claims" and nothing else (EXECUTED above).
- The 94 are the a7 baseline's 83 (`build/baseline-a7/failing-nodes.txt`, EXECUTED: `comm`
  after stripping the `FAILED ` prefix, nothing on the a7-only side) plus 11 of main's checks
  newer than the chain's base `5feb7e9`, which the a7 set cannot pass: 042's seven (seaborn and
  reportlab are not in the a7 zip: `test_reportlab_notice_carries_its_third_party_parts`,
  `test_seaborn_notice_carries_its_vendored_licences`, `test_reportlab_runs_its_pure_paths[plain,
  snapshot]`, `test_seaborn_takes_its_scipy_paths[plain, snapshot]`,
  `test_reportlab_writes_a_pdf_with_nothing_writable`) and 099's four (the a7 numpy has no
  `npy_fenv_flags.h`: `test_a_singular_matrix_raises_linalgerror[plain, snapshot]`,
  `test_numpys_own_floating_point_signals_reach_errstate[plain, snapshot]`). The same 11 fail
  on main under the same set, so they are the set's, not the chain's.
- The rules checks alone, ruff, mypy and the public-API snapshot: green but the one red named
  under Re-ran.

## 4. The context commit `1b85fe1` (READ)

- The CHANGELOG lines of 103 to 109 under "## 0.1.0a8 — unreleased" are each specification's
  proposed text: 103's "CHANGELOG line (for the integrator)", 104's Design "The CHANGELOG and
  the roadmap", 105's "The CHANGELOG line", 106's and 108's "CHANGELOG line proposed", 107's
  landing-notes version (the Design's text plus "and `mypy --strict` is clean over the whole
  package", the notes' later wording), 109's "CHANGELOG line proposed"; compared phrase by
  phrase, no difference but bold on the titles.
- The roadmap: "Reserved: 103 to 108" (104's Design, 103's to write), "Reserved: 105" (105's
  Design, equal after whitespace), "Reserved: 107" (107's "The roadmap line"), "Reserved: 108"
  (108's E1, verbatim), "Reserved: a closer for spec 108's two allowances" (108's build review
  finding 1, the exact text), "Reserved: 109" (the chain's own earlier line, renumbered), and
  E2's Release-rule replacement at line 259 (the exact sentence). Main's "Reserved: 102" keeps
  its place before them. The commit removes one line only (E2's old sentence).
- 109's leftovers line is not written, and the roadmap holds no "Reserved: NNN" for it. The
  build review's finding 2 says "the lane writes it into `context/roadmap.md`", with the number
  the lane's. Leaving it out is not right: the owner's rule now has leftovers with no owner (78
  citing string literals, four of them read by a user; the 31 allowance-file and 36 guest-source
  hits), and the roadmap already carries a numberless reserved line of the same kind (108's
  closer), so the number is not what blocks it. Finding 3 below, written in.
- Status lines: each names its pre-build review (109: "none required"); 103, 105, 107, 108 and
  109 still read "awaiting the build review" or "the build review follows", the build review
  named in the landing notes instead, which is what `landed_review_errors` reads once the lane
  rewrites the Status to "landed … in wave …" at the acceptance (099's form on main). Note 6.
- The Rebase bullets' hashes match `git log` (the 70 pairs above); 109's bullet also names the
  skipped commit `26dde7b` and its regeneration.

## 5. The structural rubric on the tip's `src/wasi_python` (EXECUTED)

The wave is the structural chain itself, so the rubric is scored here as `reviews/README.md`
asks, against the memo's scorecard at `30e9b41` and the measurements at `a9064a2`.

| what (row) | at `a9064a2` | at `1b85fe1` | note |
|---|---|---|---|
| module sizes (R7) | `runner.py` 6,241; `tools.py` 2,450; `mounts.py` 2,235; 11,423 in all | 18 modules, 12,870 in all; `tools.py` 2,449, `mounts.py` 2,206, `_platform.py` 1,407, `_call.py` 1,287, `runner.py` 1,198, `_sessions.py` 1,120, the rest under 525 | the ceiling 1,500 with `ALLOWED = {mounts.py: 2206, tools.py: 2449}` held at exactly today's count |
| functions over 80 lines (R7) | 8 (`runner.py` 6, `tools.py` 2) | 9: `runner.py` 4 (`run` 151, `run_async` 176, `Session.__init__` 173, `Session.run_async` 82), `_sessions._open_session` 150, `_call._instance` 159, `_Process.__init__` 82, `tools._make` 82, `tools._ToolHost._answer` 83 | `LONG_FUNCTIONS` names the nine; only shrinks |
| module-level mutables and locks (R4) | 47 lines | **0** | |
| private-API uses (R3) | 27 lines in three modules | 84 lines, all in `_wasmtime_ffi.py` (the two other grep hits are `wasmtime.__file__` in `_places.py` and the tool host's own `self._context()`, not the engine's) | the count grew because the seam names each binding once; the sheet lists the 31 still needed |
| platform branches (R5) | 22, all in `runner.py` | 3, all in `_platform.py` | |
| private names the judge patches (R6) | 59 distinct | 30 distinct; `_home._ctrl_c_watched` 8, `T._TOOL_RESPONSE_BYTES` 6 | `SEAM_ALLOWED` holds 18 runner names; the closer reserved |
| `Any` / `type: ignore` (R7) | 349 / 12 | 338 / 25 | the 13 new ignores are `[attr-defined]` on Windows-only names in `_platform.py`; finding 2 |
| the type checker (R7) | none | `mypy --strict` clean, `UNTYPED` allowlist empty | |
| citations of the archive (R7) | 315 `spec NNN`; 37 finding IDs | 0; 0; no `context/` path | |

| row | at `30e9b41` (the memo) | now | reason |
|---|---|---|---|
| R1 Contract | Strong | Strong | `tests/public_api.txt` unchanged by the wave; `api.py --check` passes; failures still by type; the chain changes no message. |
| R2 Safety | Strong | Strong | no default, cap or check-and-use path changes; the call's checked state is a frozen `_CheckedCall`; sameness holds every verdict. |
| R3 Layering | Weak | Strong | one module touches the private API, held by a check with the debt sheet; `mounts.py` imports nothing from the runner (a `_CallContext` protocol); `__init__` → `runner` only, no cycle, the import order written. |
| R4 Process state | Weak | Strong | zero module-level mutables; `_Process` owns them, resets by introspection over its locks, releases once; the lock order written at `_process.py:10`; three lifecycle tables the judge drives whole. |
| R5 Portability | Adequate | Strong | one `_platform.py` behind one interface chosen once at import; three `sys.platform` lines. |
| R6 Testability | Adequate, trending Weak | Adequate | the seams are fields of the process object, but the judge still patches 18 private runner names (`SEAM_ALLOWED`) and 30 distinct private names in all; the closer is reserved, not built. |
| R7 Evolvability | Weak | Adequate | every module under 1,500 but the two allowed at their count; nine functions over 80 lines allowed; mypy clean; no citation of the archive; 338 `Any` and 25 ignores; the engine upgrade's cost written on sheet 34. |
| R8 Operability | Strong | Strong | `stats()`, the records and the trap strings untouched (no public name or message changes; the rows' verdicts the same). |

The memo's section 8 table, per finding: H1, M5, L1 → 104 (done: eleven modules, the
private-folder protocol its own module, the cycle gone); H2 → 103 (done, with the written debt of
31 bindings); H1, H5 → 105 (done, but for the 18 names of `SEAM_ALLOWED`, which 108's reserved
closer owns); H3, M1 → 106 (done); H4, M3, M4, M2 → 107 (done; M2's `tests/`, `scripts/`,
`release/` part → 109, done, with the leftovers of finding 3); section 5 → 108 (done). Left
open and ranked by the memo: nothing of its table; **L2** (friend-class coupling in `tools.py`)
was never in the chain and has no roadmap line (a worktree `spec/110-tools-behind-its-facade`
exists off this branch). Rule 4a: none of 103 to 107 carries the **structural** token; 108 rules
that they need none, reviewed before build under rule 8 before the token existed, and the check
binds specifications drafted after it lands; so no Medium under 4a.

## Findings, most severe first

1. **109's Rebase bullet miscounts the allowance's new rows** (`context/specifications/109-code-speaks-for-itself.md`,
   the "Rebase onto main" bullet) — **Low**, context only, written in by the reviewer. It says
   "`JUDGE_FILE` 41 (eleven new, …)" and "one row removed"; the interdiff shows twelve
   `JUDGE_FILE` rows added (`known_gaps.toml` "Spec 066"; `contourpy.toml` "L2", "build review",
   "spec 066"; `kiwisolver.toml`, `lxml.toml`, `matplotlib.toml`, `regex.toml` "spec 066";
   `packages.toml` "spec 042" and "spec 066"; `pillow.toml` "review, H2" and "spec 066") and one
   removed, net eleven. Fix text: "eleven new" → "twelve new, one removed, net eleven".
2. **The `type: ignore` count moved 12 → 25 across the chain and 107's six are unrecorded**
   (`src/wasi_python/_platform.py`, row R7) — **Low**, context only, written in by the reviewer.
   106 records 14 → 19 with each new one's code; 107 takes the count from 19 to 25 (EXECUTED:
   `git grep -c` at `26b2c64` 19, at `c6c48db` 25) and neither its notes nor its build review
   says so. All six are `[attr-defined]` on `msvcrt.locking` (2) and `winreg` (4), Windows-only
   names that mypy, configured `platform = "linux"`, cannot see, moved out of the `sys.platform`
   branches that used to hide them from the checker; each carries its code. Not a Medium: the
   rows they sit in are one module behind one interface (R5), and the number has a reason. Fix
   text: a sentence in 107's landing notes, "`type: ignore` lines 19 → 25 (EXECUTED), the six new
   `[attr-defined]` on `msvcrt` and `winreg` names in `_platform.py`, which mypy on
   `platform = "linux"` cannot see".
3. **The owner's rule's leftovers have no roadmap line** (`context/roadmap.md`) — **Low**,
   context only, written in by the reviewer. 109's build review finding 2 asks the lane for a
   reserved line (its text in 109's "Roadmap" bullet); the integration's context commit wrote
   108's numberless closer line and not this one. Fix text, one paragraph after "Reserved: 109":
   "Reserved: a closer for spec 109's leftovers (code speaks for itself, the leftovers: the 78
   citing string literals outside `src/`, held by one regex over string tokens for `spec NNN`;
   the judge's allowance files' comments; the guest's own sources, their fuel re-measured;
   whether a message a user reads falls under the rule is the owner's to say): parallel-safe,
   the judge and the guest's inputs; the number is the lane's when it is drafted."
4. **Note: `pyproject.toml` cites the archive.** Its new `[tool.mypy]` block and the dev-group
   line carry "(spec 106, Decision 5)" and "(AGENTS.md: …)". The rule names code files under
   `src/`, `tests/`, `scripts/` and `release/`, and 109's check reads those four trees and the
   workflow, so `pyproject.toml` is outside it; nothing to do unless the owner widens the rule.
5. **Note: the measurement that grew.** Private-API lines 27 → 84 is the seam naming each of the
   31 bindings in its own operation, inside the one module the rule allows; the number to watch
   is the sheet's 31, which only the engine's public API shrinks.
6. **Note: five Status lines read "awaiting the build review"** (103, 105, 107, 108; 109 "the
   build review follows") while their landing notes name it. The lane's acceptance rewrites each
   to "landed … in wave …" (099's form), which is what `landed_review_errors` then reads; no
   edit here, so that the entries' files stay what their reviews read.

## Constitution checks

- §4.1 (patches): no file under `recipes/` or `downloads/` changes; the wave carries no
  patch.
- §4.14 / §5.7 (the lane, stacked builds, a wave): seven entries past §5.7's five by the owner's
  decision of 2026-10-20 (the memo's section 8); one stacked chain, parallel-safe but for 109's
  comments in build-class files, one dispatch pending on the tip; each rebase is its reviewed
  diff plus the named conflicts; the fast tier ran after the rebase on the tip.
- Rule "code speaks for itself": `src/` 0 citations (107's check), `tests/`, `scripts/`,
  `release/` and the workflow 114 hits, all allowed (109's check); the judge's allowance files
  and the guest's sources are the stated exceptions.
- "Never weaken the judge": no golden, gap, allowance or progress file changes to turn a run
  green; `tests/known_gaps.toml` and `tests/upstream/*.toml` change in comments only (EXECUTED,
  the token comparison over `tests/`: the files whose code differs are the chain's judge files,
  `test_rules.py`, `scan.py`, `test_scan.py`, the seam-moving unit files, `release_shards.toml`
  with its two new unit files, the harness fakes, and the new unit files).
- §7: nothing tripped; no `--accept`, no push, no artifact in git (the frozen a7 set is under
  `build/`).

## Disposition

1. Finding 1 — written in by the reviewer, the commit after this review on `integration/full`.
2. Finding 2 — written in by the reviewer, the same commit (107's landing notes).
3. Finding 3 — written in by the reviewer, the same commit (`context/roadmap.md`); the number
   stays the lane's.
4. Notes 4 to 6 — no action.

## Verdict

Lands as merged at `1b85fe1` once the owner's release-workflow run on that exact commit is green
but for the lines each entry claims (the 11 set-bound reds do not occur there: CI builds its own
set), every rebase being its reviewed diff plus the renumbering and the named conflicts, the
fast tier on the tip equal to main's under the same set, sameness explained by the claims alone,
and no entry to eject.

One line: seven rebases are what was reviewed, the conflicts kept both sides, the judge on the
tip is main's plus the chain's 115 claimed rows, and the structure the memo scored Weak on three
rows now scores Strong on them, with the two allowances reserved for their closer.
